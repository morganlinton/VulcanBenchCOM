"""Data for Report 01: how Claude Fable 5.2 thinks on VulcanBench Frontier v4.

Reads private run records and writes derived numbers only (no thinking text,
no task content) to assets/data/report-01/:

- summary.json: per model and effort level means, shares and counts, the
  thinking-theme counts from VulcanBench PR 298, and the activity timelines of
  one task (blendcore) for the timeline chart;
- runs-traces.csv: one row per Claude Code run (Fable 5.2, Opus 5.5);
- runs-records.csv: one row per run from the frozen Code quality populations,
  all four models, with receipt tokens and patch shape.

Inputs: the Fable 5.2 sweep (runs-effort-fable52), the Opus 5.5 sweep restored
from the private backup (runs-effort-opus55), and the judging rounds that froze
each population: v3.4 (Fable 5.1, GPT-6 Astra), v3.15 (Opus 5.5), v3.30 and
v3.30.1 (Fable 5.2). GPT-6 Astra's and Fable 5.1's raw streams did not survive
the September host reset, so they enter through records only.

Trace measures skip runs in which Claude Code's refusal fallback answered part
of the session (Opus 5.5: 0, 3, 7, 8 and 12 runs from Low to Max; Fable 5.2:
none), since those streams mix two models. Record measures keep every run.

Every tool call in a Claude Code stream is put in one activity class by rules
over its tool name, command and paths (reading, binary inspection, probing the
binary, building a harness, testing, editing the module, review). Thinking is attributed to the action it preceded: the streamed
thinking-token estimates between two tool calls go to the second call's class,
rescaled so each run's total equals its result receipts.

    python3 scripts/build_report01_data.py \
        --fable52-runs <VulcanBench>/runs-effort-fable52 \
        --opus55-runs <restored>/runs-effort-opus55 \
        --v34 <judging>/runs-code-quality-maintenance-v3.4 \
        --v315 <judging>/runs-code-quality-maintenance-v3.15 \
        --v330 <run worktree>/runs-code-quality-maintenance-v3.30 \
        --v3301 <run worktree>/runs-code-quality-maintenance-v3.30.1 \
        --themes <VulcanBench>/docs/results/swe-v4-fable52-2026-11/fable52-vs-fable51-levels.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/data/report-01"

ACTIVITIES = ["orient", "inspect", "probe", "harness", "test", "edit", "review", "report"]

BINARY_INSPECT = re.compile(
    r"\b(otool|objdump|llvm-objdump|nm|strings|xxd|hexdump|gdb|lldb|r2|radare2|"
    r"ghidra|readelf|capstone|disas|od)\b"
)
TESTISH = re.compile(r"\bcmp\b|_cmp|cmp_|fuzz|differential|\bdiff(test|_test|check)?\b|mutant|mutation|xcheck|compare|parity|harness|corpus|edge(s)?\.py|check\.py|verify", re.I)
WRITE_SEM = re.compile(r"open\([^)]*['\"][wa]b?['\"]|write_text|write_bytes|\bsed -i|\bperl -i|\btee\b|\bgit apply\b")
CLEANUP = re.compile(r"\brm -r?f?\b|\bdocker (rm|rmi)\b|git status|git diff|git stash list|git ls-files|git log")
SCRATCH = re.compile(r"/tmp/|\$TMPDIR|\{TMPDIR|/var/folders/|scratch")
RUN_SCRATCH = re.compile(r"python3?\s+(-[A-Za-z]+\s+)*[\"']?(\$\{?\w+\}?|/tmp|/var|/private)[^\s]*\.py|python3?\s+(-[A-Za-z]+\s+)*-(\s|$)|python3?\s+(-[A-Za-z]+\s+)*[\w-]+\.py|bash\s+/tmp|sh\s+/tmp")
LEGACY = re.compile(r"legacy/|/legacy\b|bin/legacy|\blegacy\b")
VERIFY_KINDS = {
    "mutation": re.compile(r"mutant|mutation", re.I),
    "cross_build": re.compile(r"(^|[;&|\n(]\s*)(docker (run|build|exec|create)|qemu-x86_64(-static)? [\"$/\w])", re.I),
    "interpreters": re.compile(r"uv python|uv run --python|python3\.\d+\b|pyenv|--python 3", re.I),
    "performance": re.compile(r"throughput|timeit|perf_counter|\btime python|\btime \./|hyperfine|/usr/bin/time", re.I),
}


def stamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def text_of(name: str, inp: dict) -> str:
    if name == "Bash":
        return inp.get("command", "")
    return " ".join(str(v) for v in inp.values() if isinstance(v, str))


DISASM_FILES: set[str] = set()


def classify(name: str, inp: dict, workspace: str, patched: set[str], prev: str | None, edited: bool = False) -> str:
    path = inp.get("file_path", "") or inp.get("notebook_path", "")
    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        in_ws = path.startswith(workspace) or not path.startswith("/")
        rel = path[len(workspace):].lstrip("/") if path.startswith(workspace) else path
        if in_ws and not SCRATCH.search(rel):
            return "edit"
        return "harness"
    if name == "Read":
        if "tool-results" in path:
            return prev or "orient"
        if re.search(r"disas|\.s$|\.asm$|objdump|otool", path, re.I) or Path(path).name in DISASM_FILES:
            return "inspect"
        if path.startswith(workspace):
            return "review" if edited else "orient"
        return "harness" if SCRATCH.search(path) else "orient"
    if name in ("Grep", "Glob", "LS"):
        return "orient"
    if name != "Bash":
        return "orient"
    cmd = inp.get("command", "")
    if workspace:
        cmd = cmd.replace(workspace, "WS")
    cmd = re.sub(r"[a-z]+-binary-parity-[0-9a-f]{8}(-[a-z0-9]+)?", "TASKDIR", cmd)
    cmd = re.sub(r"\bwhich\b[^;&|\n]*", "which", cmd)
    lead = re.sub(r"^(\s*(set -e|[A-Z_]+=\S*|cd \S+)\s*(;|&&|\n))*\s*", "", cmd)
    mentions_module = any(Path(f).name in cmd for f in patched)
    ws_ref = False
    for f in patched:
        for m in re.finditer(re.escape(Path(f).name), cmd):
            before = cmd[max(0, m.start() - 24):m.start()]
            tok = re.split(r"[\s'\"(=,]", before)[-1]
            if re.search(r"tmp|scratch|\$S\b|\$\{?S[A-Z]*\}?/|orig|HEAD:|:", tok):
                continue
            ws_ref = True
    if re.match(r"sleep \d", lead):
        return prev or "orient"
    if BINARY_INSPECT.search(cmd):
        for target in re.findall(r">\s*[\"']?([\w./${}-]+)", cmd):
            DISASM_FILES.add(Path(target).name)
    if any(f and re.search(r"(cat|sed|grep|awk|head|tail|less)\b[^|;\n]*" + re.escape(f), cmd) for f in DISASM_FILES):
        return "inspect"
    if re.search(r"\bcat\s+\S*\.s\b|\bdis\w*\.txt", cmd):
        return "inspect"
    if re.match(r"(rm |docker (rm|rmi)|git (status|diff|stash))", lead):
        return "review" if edited else "orient"
    if (BINARY_INSPECT.search(cmd) or "disasm" in cmd) and not RUN_SCRATCH.search(cmd):
        return "inspect"
    redirect_to_module = any(
        re.search(r">\s*[\"']?(\$\{?W\w*\}?/|WS/|\./)?" + re.escape(Path(f).name) + r"\b", cmd) for f in patched
    )
    if redirect_to_module or ws_ref and WRITE_SEM.search(cmd) and not re.search(r"\bcp\b[^\n]*WS[^\n]*(tmp|scratch|\$S)", cmd):
        return "edit"
    if RUN_SCRATCH.search(cmd) or TESTISH.search(cmd):
        return "test"
    if re.search(r"\|\s*[\"']?\$\{?[A-Z][A-Z_0-9]*\}?[\"']?", cmd) and (LEGACY.search(cmd) or "bin/" in cmd):
        return "test" if mentions_module else "probe"
    if re.search(r"(printf|echo)\b[^|\n]*\|\s*(?!\s*(python|grep|head|tail|sed|awk|wc|tr|cat|sort|xxd|od|cut|uniq|diff)\b)[\"']?[\w./$\{\}-]+", cmd) and not re.search(r"\|\s*(sh|bash)\b", cmd):
        return "test" if mentions_module else "probe"
    if re.search(r"(printf|echo|cat)\b[^|\n]*\|\s*[\"']?(\$\{?\w+\}?|\.?/?[\w./-]*legacy[\w./-]*)", cmd) or re.search(r"<<<|<\s*\S+\s*$", cmd) and LEGACY.search(cmd):
        return "probe"
    if re.search(r"cat\s*>\s*\S*(/tmp|\$|scratch)", cmd) or (SCRATCH.search(cmd) and "mkdir" in cmd):
        return "harness"
    if CLEANUP.search(cmd) and edited:
        return "review"
    return "orient"


def run_timeline(run: Path) -> dict:
    DISASM_FILES.clear()
    summary = json.loads((run / "summary.json").read_text())
    patch = (run / "final.patch").read_text(errors="replace") if (run / "final.patch").exists() else ""
    patched = {ln[6:] for ln in patch.splitlines() if ln.startswith("+++ b/")}
    start = stamp(summary["started_at"])
    workspace = ""
    calls: list[dict] = []
    open_calls: dict[str, dict] = {}
    pending_think = 0.0
    pending_blocks: list[int] = []
    think_total_receipt = 0
    output_total = 0
    for line in (run / "cli-agent-stream.jsonl").open():
        e = json.loads(line)
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            workspace = e.get("cwd", "")
        elif t == "system" and e.get("subtype") == "thinking_tokens":
            pending_think += e.get("estimated_tokens_delta", 0)
        elif t == "assistant":
            for b in e["message"]["content"]:
                if b["type"] == "thinking":
                    n = len(b.get("thinking") or "")
                    pending_blocks.append(n)
                elif b["type"] == "tool_use":
                    prev = calls[-1]["activity"] if calls else None
                    act = classify(b["name"], b.get("input") or {}, workspace, patched, prev, any(x["activity"] == "edit" for x in calls))
                    c = {
                        "tool": b["name"],
                        "activity": act,
                        "think_est": pending_think,
                        "think_blocks": pending_blocks,
                        "text": text_of(b["name"], b.get("input") or {}),
                        "end": None,
                    }
                    pending_think, pending_blocks = 0.0, []
                    calls.append(c)
                    open_calls[b["id"]] = c
        elif t == "user":
            ts = e.get("timestamp")
            msg = e.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            if ts and isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "tool_result":
                        c = open_calls.pop(part.get("tool_use_id"), None)
                        if c is not None:
                            c["end"] = stamp(ts)
        elif t == "result":
            u = e["usage"]
            output_total += u["output_tokens"]
            think_total_receipt += u.get("output_tokens_details", {}).get("thinking_tokens", 0)
    trailing = pending_think
    est_total = sum(c["think_est"] for c in calls) + trailing
    scale = think_total_receipt / est_total if est_total else 0.0
    prev_end = start
    for c in calls:
        c["think"] = c["think_est"] * scale
        if c["end"] is None:
            c["end"] = prev_end
        c["t_end_min"] = (c["end"] - start) / 60
        c["span_min"] = max(0.0, (c["end"] - prev_end) / 60)
        prev_end = max(prev_end, c["end"])
    duration_min = summary["duration_s"] / 60
    return {
        "run_id": run.name,
        "effort": run.parent.name,
        "task": summary.get("task") or run.name.rsplit("-", 1)[0],
        "duration_min": duration_min,
        "output": output_total,
        "thinking": think_total_receipt,
        "trailing_think": trailing * scale,
        "trailing_min": max(0.0, duration_min - (prev_end - start) / 60),
        "calls": calls,
        "patched": sorted(patched),
    }


# ---------------------------------------------------------------- aggregation

LEVELS = ["low", "medium", "high", "extra-high", "max"]
GROUPS = {
    "reading": ("orient", "inspect"),
    "probing": ("probe",),
    "editing": ("edit",),
    "testing": ("harness", "test"),
    "wrapup": ("review", "report"),
}
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--|;|\"\"\"|''')")


def run_measures(tl: dict) -> dict:
    calls = tl["calls"]
    acts = [c["activity"] for c in calls]
    dur = tl["duration_min"] or 1e-9

    def first(a):
        return next((i for i, x in enumerate(acts) if x == a), None)

    fi, fe = first("inspect"), first("edit")
    bash = " \n".join(c["text"] for c in calls if c["tool"] == "Bash")
    names = " \n".join(c["text"].split(" ", 1)[0] for c in calls if c["tool"] == "Write")
    cycles, seen_edit = 0, False
    for a in acts:
        if a == "edit":
            seen_edit = True
        elif a == "test" and seen_edit:
            cycles += 1
            seen_edit = False
    think_by = {a: 0.0 for a in ACTIVITIES}
    calls_by = {a: 0 for a in ACTIVITIES}
    for c in calls:
        think_by[c["activity"]] += c["think"]
        calls_by[c["activity"]] += 1
    think_by["report"] += tl["trailing_think"]
    deciles = [0.0] * 10
    for c in calls:
        deciles[min(9, int(10 * c["t_end_min"] / dur))] += c["think"]
    deciles[9] += tl["trailing_think"]
    gaps = [c["think"] for c in calls] + [tl["trailing_think"]]
    k = max(range(len(gaps)), key=gaps.__getitem__)
    blocks = [n for c in calls for n in c["think_blocks"]]
    return {
        "run_id": tl["run_id"],
        "effort": tl["effort"],
        "minutes": dur,
        "output": tl["output"],
        "thinking": tl["thinking"],
        "tool_calls": len(calls),
        "calls_before_inspect": fi,
        "min_to_inspect": calls[fi]["t_end_min"] if fi is not None else None,
        "inspected_before_edit": fi is not None and (fe is None or fi < fe),
        "never_inspected": fi is None,
        "min_to_edit": calls[fe]["t_end_min"] if fe is not None else None,
        "share_before_edit": calls[fe]["t_end_min"] / dur if fe is not None else None,
        "edit_calls": calls_by["edit"],
        "edit_tool_calls": sum(c["activity"] == "edit" and c["tool"] in ("Edit", "Write", "MultiEdit") for c in calls),
        "test_runs": calls_by["test"],
        "probe_runs": calls_by["probe"],
        "inspect_calls": calls_by["inspect"],
        "cycles": cycles,
        "biggest_burst_share": max(gaps) / tl["thinking"] if tl["thinking"] else 0.0,
        "burst_after": (calls[k - 1]["activity"] if 0 < k <= len(calls) else "start"),
        "burst_before": (calls[k]["activity"] if k < len(calls) else "report"),
        "thinking_blocks": len(blocks),
        "longest_block_chars": max(blocks) if blocks else 0,
        "think_by": think_by,
        "calls_by": calls_by,
        "deciles": deciles,
        "verify": {key: bool(r.search(bash) or (key == "mutation" and r.search(names))) for key, r in VERIFY_KINDS.items()},
        "timeline": [[round(c["t_end_min"], 3), c["activity"], round(c["think"])] for c in calls],
    }


def patch_shape(patch: str) -> dict:
    cur, files, new = None, {}, set()
    for ln in patch.splitlines():
        if ln.startswith("diff --git"):
            cur = ln.split(" b/")[-1]
            files[cur] = [0, 0, 0]
        elif ln.startswith("new file mode") and cur:
            new.add(cur)
        elif cur and ln.startswith("+") and not ln.startswith("+++"):
            files[cur][0] += 1
            files[cur][2] += bool(COMMENT.match(ln[1:]))
        elif cur and ln.startswith("-") and not ln.startswith("---"):
            files[cur][1] += 1
    tests = [f for f in files if "test" in f.lower()]
    added = sum(v[0] for v in files.values())
    return {
        "files": len(files),
        "module_only": len(files) == 1,
        "test_files": len(tests),
        "new_test_files": sum(f in new for f in tests),
        "added": added,
        "removed": sum(v[1] for v in files.values()),
        "module_added": sum(v[0] for f, v in files.items() if f not in tests),
        "test_added": sum(files[f][0] for f in tests),
        "comment_share": sum(v[2] for f, v in files.items() if f not in tests)
        / max(1, sum(v[0] for f, v in files.items() if f not in tests)),
    }


def records(rounds) -> list[dict]:
    rows = []
    for directory, models in rounds:
        for r in json.loads((directory / "private-manifest.json").read_text()):
            if r["model"] not in models:
                continue
            ev = json.loads((directory / "evidence" / f"{r['id']}.json").read_text())
            u = r["solver_receipt"].get("usage", {})
            rows.append(
                {
                    "model": models[r["model"]],
                    "effort": r["effort"],
                    "task": r["task"],
                    "run_id": r["run_id"],
                    "solved": r["functional"] >= 1,
                    "fallback": bool(r.get("fallback")),
                    "minutes": r["duration_s"] / 60,
                    "output": u.get("output_tokens"),
                    "reasoning": u.get("reasoning_output_tokens"),
                }
                | patch_shape(ev["candidate_patch"])
            )
    return rows


def mean_se(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None
    return statistics.mean(xs), (statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0)


def median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def level_table(traces: dict, recs: list[dict]) -> list[dict]:
    out = []
    for model in ("fable52", "opus55", "fable51", "astra"):
        for e in LEVELS:
            rec = [r for r in recs if r["model"] == model and r["effort"] == e]
            row = {"model": model, "effort": e, "n": len(rec), "solved": sum(r["solved"] for r in rec)}
            row["minutes"], row["minutes_se"] = mean_se(r["minutes"] for r in rec)
            for key in ("module_only", "test_files"):
                row["runs_" + key] = sum(bool(r[key]) for r in rec)
            for key in ("added", "module_added", "test_added"):
                row["median_" + key] = median(r[key] for r in rec)
            row["max_added"] = max(r["added"] for r in rec)
            row["comment_share"] = statistics.mean(r["comment_share"] for r in rec)
            if model == "astra":
                row["output"], row["output_se"] = mean_se(r["output"] for r in rec)
                row["thinking"], row["thinking_se"] = mean_se(r["reasoning"] for r in rec)
                row["thinking_share"] = sum(r["reasoning"] for r in rec) / sum(r["output"] for r in rec)
            elif model == "fable51":
                row["output"], row["output_se"] = mean_se(r["output"] for r in rec)
            row["fallback_runs"] = sum(r["fallback"] for r in rec)
            tr = [t for t in traces.get(model, []) if t["effort"] == e]
            if tr:
                if len(tr) != len(rec) - row["fallback_runs"]:
                    raise SystemExit(f"{model} {e}: {len(tr)} traces against {len(rec)} records")
                row["n_traces"] = len(tr)
                row["output"], row["output_se"] = mean_se(t["output"] for t in tr)
                row["thinking"], row["thinking_se"] = mean_se(t["thinking"] for t in tr)
                row["thinking_share"] = sum(t["thinking"] for t in tr) / sum(t["output"] for t in tr)
                row["tool_calls"], row["tool_calls_se"] = mean_se(t["tool_calls"] for t in tr)
                for key in ("test_runs", "probe_runs", "inspect_calls", "edit_calls", "edit_tool_calls", "cycles",
                            "biggest_burst_share", "thinking_blocks"):
                    row[key] = statistics.mean(t[key] for t in tr)
                for key in ("calls_before_inspect", "min_to_inspect", "min_to_edit", "share_before_edit",
                            "longest_block_chars"):
                    row["median_" + key] = median(t[key] for t in tr)
                row["inspected_before_edit"] = sum(t["inspected_before_edit"] for t in tr)
                row["never_inspected"] = sum(t["never_inspected"] for t in tr)
                row["burst_after_inspect"] = sum(t["burst_after"] == "inspect" for t in tr)
                row["burst_before_edit"] = sum(t["burst_before"] == "edit" for t in tr)
                row["burst_before_test"] = sum(t["burst_before"] in GROUPS["testing"] for t in tr)
                total = sum(t["thinking"] for t in tr)
                calls = sum(t["tool_calls"] for t in tr)
                for g, acts in GROUPS.items():
                    row["think_" + g] = sum(t["think_by"][a] for t in tr for a in acts) / total
                    row["calls_" + g] = sum(t["calls_by"][a] for t in tr for a in acts) / calls
                for key in ("mutation", "cross_build", "interpreters", "performance"):
                    row["verify_" + key] = sum(t["verify"][key] for t in tr)
                row["deciles"] = [sum(t["deciles"][i] for t in tr) / total for i in range(10)]
            out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fable52-runs", type=Path, required=True)
    ap.add_argument("--opus55-runs", type=Path, required=True)
    ap.add_argument("--v34", type=Path, required=True)
    ap.add_argument("--v315", type=Path, required=True)
    ap.add_argument("--v330", type=Path, required=True)
    ap.add_argument("--v3301", type=Path, required=True)
    ap.add_argument("--themes", type=Path, required=True, help="fable52-vs-fable51-levels.csv from VulcanBench PR 298")
    ap.add_argument("--timeline-task", default="legacy-blendcore-binary-parity")
    args = ap.parse_args()

    recs = records([
        (args.v34, {"fable": "fable51", "astra": "astra"}),
        (args.v315, {"opus55": "opus55"}),
        (args.v330, {"fable52": "fable52"}),
        (args.v3301, {"fable52": "fable52"}),
    ])
    traces = {}
    for model, root in (("fable52", args.fable52_runs), ("opus55", args.opus55_runs)):
        traces[model] = []
        for r in recs:
            # Runs where the refusal fallback answered part of the session mix two models'
            # behaviour, so the trace measures use runs served by the model alone.
            if r["model"] == model and not r["fallback"]:
                m = run_measures(run_timeline(root / r["effort"] / r["run_id"]))
                m["task"] = r["task"]
                traces[model].append(m)
    levels = level_table(traces, recs)
    themes = [
        {k: row[k] for k in ("effort", "n")} | {k[6:]: int(v) for k, v in row.items() if k.startswith("theme_")}
        for row in csv.DictReader(args.themes.open())
        if row["model"] == "fable52"
    ]
    timelines = {
        f"{model}/{t['effort']}": {"minutes": round(t["minutes"], 3), "thinking": t["thinking"], "calls": t["timeline"]}
        for model in traces
        for t in traces[model]
        if t["task"] == args.timeline_task
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(
        {"levels": levels, "themes": themes, "timeline_task": args.timeline_task, "timelines": timelines},
        indent=1, default=lambda v: round(v, 6) if isinstance(v, float) else v,
    ) + "\n")
    fields = ["model", "effort", "task", "run_id", "minutes", "output", "thinking", "tool_calls",
              "calls_before_inspect", "min_to_inspect", "inspected_before_edit", "min_to_edit", "edit_calls",
              "edit_tool_calls", "test_runs", "probe_runs", "cycles", "biggest_burst_share", "thinking_blocks",
              *("verify_" + k for k in ("mutation", "cross_build", "interpreters", "performance"))]
    with (OUT / "runs-traces.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for model in traces:
            for t in sorted(traces[model], key=lambda t: (LEVELS.index(t["effort"]), t["task"])):
                row = t | {"model": model} | {"verify_" + k: v for k, v in t["verify"].items()}
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    rfields = ["model", "effort", "task", "run_id", "solved", "fallback", "minutes", "output", "reasoning", "files",
               "module_only", "test_files", "new_test_files", "added", "removed", "module_added", "test_added",
               "comment_share"]
    with (OUT / "runs-records.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, rfields, lineterminator="\n")
        w.writeheader()
        for r in sorted(recs, key=lambda r: (r["model"], LEVELS.index(r["effort"]), r["task"])):
            w.writerow({k: (round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in rfields})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(recs)} records, " + ", ".join(f"{m} {len(v)} traces" for m, v in traces.items()))


if __name__ == "__main__":
    main()
