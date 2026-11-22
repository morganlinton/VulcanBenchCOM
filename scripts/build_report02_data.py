"""Data for Report 02: how Gemini 4 Neon thinks on VulcanBench Frontier v4.

Reads private run records and writes derived numbers only (no thinking text,
no task content) to assets/data/report-02/:

- summary.json: per effort level means, shares and counts for Gemini 4 Neon,
  the same rows for Claude Fable 5.2 copied from Report 01's data, keyword
  theme counts over Neon's thinking summaries, and the activity timelines of
  one task (blendcore) for the timeline chart;
- runs-traces.csv: one row per Neon run, in Report 01's columns.

Inputs: the Neon sweep (runs-effort-gemini4-neon-agy, Antigravity CLI 1.5.12),
assets/data/report-01/summary.json for the Fable 5.2 rows, and the Fable 5.2
sweep (runs-effort-fable52) for three order measures this report adds to both
models: whether a run ran the reference before reading its machine code,
whether it ran a script (a batch of inputs through the reference, the old module or both) before its first edit, and whether it read both the
macOS and the Linux binary.

Neon's Antigravity stream is shaped differently from Claude Code's, so each run
is first mapped onto Report 01's vocabulary and then measured by Report 01's
own code: run_command is Bash, read_file is Read, edit_file is Edit and
write_file is Write, and every tool call goes through the same classify() rules
(reading, binary inspection, probing the binary, building a harness, testing,
editing the module, review). Thinking needs no estimate here. Each model
response step reports its own thinking tokens, and those go to the first tool
call that response made (a response that makes no call is the closing report).
Antigravity's output tokens include thinking, as Claude Code's do.

Thinking summaries are read from each run's Antigravity session database for
their count, length and keyword themes (Report 01's THEMES rules, via VulcanBench
PR 298). They are never written out.

Only completed runs count: the 40 attempts refused by the AI Pro quota were
discarded and rerun, so runs without summary.json are skipped.

    python3 scripts/build_report02_data.py \
        --neon-runs <VulcanBench>/runs-effort-gemini4-neon-agy \\
        --fable52-runs <VulcanBench>/runs-effort-fable52
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report01_data as r01  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/data/report-02"
LEVELS = ["low", "medium", "high", "extra-high"]
TOOL_MAP = {"run_command": "Bash", "read_file": "Read", "edit_file": "Edit", "write_file": "Write"}

# Report 01's themes come from VulcanBench scripts/cii-v4-board/fable52_vs_fable51_behaviour.py:
# a run counts once per theme if any thinking summary in it matches (lower-cased).
THEMES = {
    "disassembly": r"disassembl|otool|objdump|assembly|instruction",
    "black_box_probing": r"black.box|probe|experiment|test input|try (it|a few)",
    "differential_fuzzing": r"fuzz|differential|random(ized)? (input|test)|"
    r"compare (against|with) the (legacy|binary|original)",
    "spec_distrust": r"spec(ification)? (is|may be) (stale|wrong|out of date|drift)|drift|"
    r"doesn.t match the spec|spec says",
    "hypotheses": r"hypothes|my guess|i suspect|likely|probably",
    "self_checks": r"double.check|verify|confirm|make sure|sanity",
    "scope_restraint": r"minimal|smallest|surgical|only change|keep (the|my) (change|patch|diff)|"
    r"don.t (need|want) to (rewrite|refactor)",
    "edge_cases": r"edge case|corner case|overflow|boundary|off.by.one|negative|empty",
    "cleanup": r"clean ?up|scratch|remove (the|my) (temp|debug)|leave the (repo|workspace)",
}

PLANNER = 15  # Antigravity step type of a model response
THINKING_PATH = (20, 3)  # field path of the thinking summary inside a response payload


def _varint(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def _strings(b: bytes, path: tuple = (), depth: int = 0) -> list[tuple[tuple, bytes]] | None:
    """Length-delimited leaves of a protobuf message, or None if b is not one."""
    out, i = [], 0
    try:
        while i < len(b):
            key, i = _varint(b, i)
            field, wire = key >> 3, key & 7
            if wire == 0:
                _, i = _varint(b, i)
            elif wire == 1:
                i += 8
            elif wire == 5:
                i += 4
            elif wire == 2:
                n, i = _varint(b, i)
                v = b[i:i + n]
                i += n
                sub = _strings(v, path + (field,), depth + 1) if n and depth < 8 else None
                out.extend(sub if sub else [(path + (field,), v)])
            else:
                return None
    except IndexError:
        return None
    return out if i == len(b) else None


def thinking_texts(run: Path) -> dict[int, str]:
    """Thinking summary per response step index, from the session database."""
    dbs = sorted((run / "agy-session").glob("*.db"))
    if len(dbs) != 1:
        raise SystemExit(f"{run.name}: expected one session database, found {len(dbs)}")
    con = sqlite3.connect(f"file:{dbs[0]}?mode=ro&immutable=1", uri=True)
    texts = {}
    for idx, payload in con.execute("select idx, step_payload from steps where step_type = ?", (PLANNER,)):
        for path, value in _strings(payload or b"") or []:
            if path == THINKING_PATH:
                texts[idx] = value.decode("utf-8", errors="replace")
    con.close()
    return texts


def run_timeline(run: Path) -> tuple[dict, list[str]]:
    r01.DISASM_FILES.clear()
    summary = json.loads((run / "summary.json").read_text())
    patch = (run / "final.patch").read_text(errors="replace") if (run / "final.patch").exists() else ""
    patched = {ln[6:] for ln in patch.splitlines() if ln.startswith("+++ b/")}
    start = r01.stamp(summary["started_at"])
    ends = {}
    for line in (run / "tool-calls.jsonl").open():
        c = json.loads(line)
        ends[str(c["call_id"])] = r01.stamp(c["ended_at"])
    texts = thinking_texts(run)
    workspace = ""
    calls: list[dict] = []
    pending_think, pending_blocks = 0, []
    output_total = thinking_total = 0
    result_usage = None
    for line in (run / "cli-agent-stream.jsonl").open():
        e = json.loads(line)
        if e.get("event") == "init":
            workspace = e["init"].get("cwd", "")
            continue
        if e.get("event") == "result":
            result_usage = e["result"].get("usage")
            continue
        s = e.get("step_update")
        if not s:
            continue
        if s["step_type"] == "agent_response" and s["state"] == "DONE":
            u = s.get("usage") or {}
            pending_think += u.get("thinking_tokens", 0)
            thinking_total += u.get("thinking_tokens", 0)
            output_total += u.get("output_tokens", 0)
            if texts.get(s["step_index"]):
                pending_blocks.append(len(texts[s["step_index"]]))
        elif s["step_type"] == "tool" and s["state"] == "ACTIVE":
            name = TOOL_MAP[s["tool_name"]]
            p = s["tool_info"].get("parameters", {})
            inp = {"command": p.get("CommandLine", "")} if name == "Bash" else {"file_path": p.get("Path", "")}
            prev = calls[-1]["activity"] if calls else None
            act = r01.classify(name, inp, workspace, patched, prev, any(x["activity"] == "edit" for x in calls))
            calls.append({
                "tool": name,
                "activity": act,
                "think": pending_think,
                "think_blocks": pending_blocks,
                "text": r01.text_of(name, inp),
                "end": ends.get(str(s["step_index"])),
            })
            pending_think, pending_blocks = 0, []
    if result_usage and result_usage.get("thinking_tokens", thinking_total) != thinking_total:
        raise SystemExit(f"{run.name}: step thinking {thinking_total} != result {result_usage['thinking_tokens']}")
    prev_end = start
    for c in calls:
        if c["end"] is None:
            c["end"] = prev_end
        c["t_end_min"] = (c["end"] - start) / 60
        prev_end = max(prev_end, c["end"])
    duration_min = summary["duration_s"] / 60
    tl = {
        "run_id": run.name,
        "effort": run.parent.name,
        "task": summary.get("task_id") or run.name.rsplit("-", 1)[0],
        "duration_min": duration_min,
        "output": output_total,
        "thinking": thinking_total,
        "trailing_think": pending_think,
        "trailing_blocks": pending_blocks,
        "calls": calls,
        "patched": sorted(patched),
        "solved": summary.get("scores", {}).get("functional", summary.get("functional", 0)) >= 1,
    }
    return tl, [texts[k].lower() for k in sorted(texts)]


ARM = re.compile(r"darwin|arm64")
X86 = re.compile(r"linux|amd64|x86")


def order_measures(calls: list[dict]) -> dict:
    """Measures of what comes before what, added in this report for both models."""
    acts = [c["activity"] for c in calls]
    fe = next((i for i, a in enumerate(acts) if a == "edit"), len(acts))
    fi = next((i for i, a in enumerate(acts) if a == "inspect"), len(acts))
    inspected = " ".join(c["text"] for c in calls if c["activity"] == "inspect")
    return {
        "probe_before_inspect": "probe" in acts[:fi],
        "check_before_edit": any(a in ("test", "harness") for a in acts[:fe]),
        "both_binaries": bool(ARM.search(inspected) and X86.search(inspected)),
    }


ORDER_KEYS = ("probe_before_inspect", "check_before_edit", "both_binaries")


def level_rows(traces: list[dict]) -> list[dict]:
    out = []
    for e in LEVELS:
        tr = [t for t in traces if t["effort"] == e]
        row = {"model": "neon", "effort": e, "n": len(tr), "n_traces": len(tr), "solved": sum(t["solved"] for t in tr)}
        row["minutes"], row["minutes_se"] = r01.mean_se(t["minutes"] for t in tr)
        row["output"], row["output_se"] = r01.mean_se(t["output"] for t in tr)
        row["thinking"], row["thinking_se"] = r01.mean_se(t["thinking"] for t in tr)
        row["thinking_share"] = sum(t["thinking"] for t in tr) / sum(t["output"] for t in tr)
        row["tool_calls"], row["tool_calls_se"] = r01.mean_se(t["tool_calls"] for t in tr)
        for key in ("test_runs", "probe_runs", "inspect_calls", "edit_calls", "edit_tool_calls", "cycles",
                    "biggest_burst_share", "thinking_blocks"):
            row[key] = statistics.mean(t[key] for t in tr)
        for key in ("calls_before_inspect", "min_to_inspect", "min_to_edit", "share_before_edit",
                    "longest_block_chars"):
            row["median_" + key] = r01.median(t[key] for t in tr)
        row["median_thinking"] = r01.median(t["thinking"] for t in tr)
        row["median_tool_calls"] = r01.median(t["tool_calls"] for t in tr)
        row["median_minutes"] = r01.median(t["minutes"] for t in tr)
        row["inspected_before_edit"] = sum(t["inspected_before_edit"] for t in tr)
        row["never_inspected"] = sum(t["never_inspected"] for t in tr)
        row["burst_after_inspect"] = sum(t["burst_after"] == "inspect" for t in tr)
        row["burst_before_edit"] = sum(t["burst_before"] == "edit" for t in tr)
        row["burst_before_test"] = sum(t["burst_before"] in r01.GROUPS["testing"] for t in tr)
        row["burst_before_reading"] = sum(t["burst_before"] in r01.GROUPS["reading"] for t in tr)
        row["runs_test_files"] = sum(bool(t["shape"]["test_files"]) for t in tr)
        row["median_module_added"] = r01.median(t["shape"]["module_added"] for t in tr)
        row["comment_share"] = statistics.mean(t["shape"]["comment_share"] for t in tr)
        row["runs_module_only"] = sum(len(t["patched"]) == 1 for t in tr)
        for key in ORDER_KEYS:
            row[key] = sum(t[key] for t in tr)
        total = sum(t["thinking"] for t in tr)
        calls = sum(t["tool_calls"] for t in tr)
        for g, acts in r01.GROUPS.items():
            row["think_" + g] = sum(t["think_by"][a] for t in tr for a in acts) / total
            row["calls_" + g] = sum(t["calls_by"][a] for t in tr for a in acts) / calls
        for key in ("mutation", "cross_build", "interpreters", "performance"):
            row["verify_" + key] = sum(t["verify"][key] for t in tr)
        row["deciles"] = [sum(t["deciles"][i] for t in tr) / total for i in range(10)]
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--neon-runs", type=Path, required=True)
    ap.add_argument("--fable52-runs", type=Path, required=True,
                    help="runs-effort-fable52, for the order measures Report 01 did not compute")
    ap.add_argument("--timeline-task", default="legacy-blendcore-binary-parity")
    args = ap.parse_args()

    traces, themes = [], []
    for e in LEVELS:
        runs = sorted(p.parent for p in (args.neon_runs / e).glob("*/summary.json"))
        if len(runs) != 23:
            raise SystemExit(f"{e}: {len(runs)} completed runs, expected 23")
        hits = dict.fromkeys(THEMES, 0)
        for run in runs:
            tl, texts = run_timeline(run)
            m = r01.run_measures(tl)
            m |= {"task": tl["task"], "solved": tl["solved"], "patched": tl["patched"]} | order_measures(tl["calls"])
            m["shape"] = r01.patch_shape((run / "final.patch").read_text(errors="replace"))
            m["thinking_blocks"] += len(tl["trailing_blocks"])
            traces.append(m)
            joined = " ".join(texts)
            for k, rx in THEMES.items():
                hits[k] += bool(re.search(rx, joined))
        themes.append({"effort": e, "n": len(runs)} | hits)

    fable = json.loads((ROOT / "assets/data/report-01/summary.json").read_text())
    fable_rows = [r for r in fable["levels"] if r["model"] == "fable52"]
    for r in fable_rows:
        runs = sorted(p.parent for p in (args.fable52_runs / r["effort"]).glob("*/summary.json"))
        if len(runs) != r["n_traces"]:
            raise SystemExit(f"fable52 {r['effort']}: {len(runs)} runs against {r['n_traces']} traces")
        measured = [order_measures(r01.run_timeline(run)["calls"]) for run in runs]
        for key in ORDER_KEYS:
            r[key] = sum(m[key] for m in measured)
    levels = level_rows(traces) + fable_rows
    timelines = {
        f"neon/{t['effort']}": {"minutes": round(t["minutes"], 3), "thinking": t["thinking"], "calls": t["timeline"]}
        for t in traces
        if t["task"] == args.timeline_task
    } | {k: v for k, v in fable["timelines"].items() if k.startswith("fable52/")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(
        {"levels": levels, "themes": themes, "fable52_themes": fable["themes"],
         "timeline_task": args.timeline_task, "timelines": timelines},
        indent=1, default=lambda v: round(v, 6) if isinstance(v, float) else v,
    ) + "\n")
    fields = ["model", "effort", "task", "run_id", "solved", "minutes", "output", "thinking", "tool_calls",
              "calls_before_inspect", "min_to_inspect", "inspected_before_edit", "min_to_edit", "edit_calls",
              "edit_tool_calls", "test_runs", "probe_runs", "cycles", "biggest_burst_share", "thinking_blocks",
              *("verify_" + k for k in ("mutation", "cross_build", "interpreters", "performance")), *ORDER_KEYS]
    with (OUT / "runs-traces.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for t in sorted(traces, key=lambda t: (LEVELS.index(t["effort"]), t["task"])):
            row = t | {"model": "neon"} | {"verify_" + k: v for k, v in t["verify"].items()}
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(traces)} Neon traces")


if __name__ == "__main__":
    main()
