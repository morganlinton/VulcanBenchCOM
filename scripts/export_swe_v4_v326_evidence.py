"""Export the public record of the Muse Wonder Full effort sweep on Frontier v4, judged under v3.26 to v3.26.3.

Adapted from the v3.24 Claude Haiku 5.5 export, with the same publication
scope: per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and an estimated cost. Raw prompts, patches,
quirk answer keys and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v326_evidence.py --harness-root ../VulcanBench

--harness-root holds the frozen run directories (runs-effort-musewonder-full-v2,
runs-effort-musewonder-full-v2-149, runs-code-quality-maintenance-v3.25 and
v3.26 to v3.26.3), the population records and card in
docs/results/swe-v4-musewonder-full-2026-10, and the per-minute overlap logs.

What differs from the Haiku 5.5 export, all forced by the sweep or its judging:

- Two Muse Code versions, two run roots. Low and 21 Medium tasks ran on Muse
  Code 1.4.6 from bench/2026-10-13-musewonder-full-v2-low; after the Muse Code
  weekly limit stopped Medium and Meta reset the quota, the last two Medium
  tasks, High and Extra-high ran on Muse Code 1.4.9 from
  bench/2026-10-16-musewonder-full-149, which continues the first root.
- Four judging rounds, one panel. v3.26 seats Claude Opus 5.5 (Muse Spark 1.3
  is a Meta model, so it is not neutral for a Meta submission, and Grok 4.7's
  Cursor account ran out of usage on its first exam call under v3.25) with
  GPT-6.1 Sol's v3.25 work attached as a scored sibling. v3.26.1 (the two
  Medium top-up runs), v3.26.2 (High) and v3.26.3 (Extra-high) reuse both exam
  verdicts with no new exam. The export checks every hash that binds them.
- Two timeouts. High paddockcore and Extra-high depotcore hit the flat 3-hour
  task bound with no finished code to judge. They count as failed tasks, are
  timed and priced (Muse Code reported usage before the bound), and each
  level carries a second combined figure with the timeout counted as 0 over
  all 23 runs (harness DECISIONS.md, 2026-09-28).
- An estimated cost. Meta lists no API price for Muse Wonder Full, so tokens
  are priced at the Muse Wonder 1.0 list price, and Muse Code 1.4.9's goal and
  verify reminder observers, which run on Muse Spark 1.3 and are recorded
  apart, at Muse Spark 1.3's list price, exactly as the harness card does.
- Every number the harness card shows is matched: combined score and its
  standard error, the timeouts-as-0 figure, functional score, tasks passed,
  minutes, cost and each judge's reviewed score per level.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-musewonder-full-v326"
SCORES = SITE / "assets/data/swe-v4-musewonder-full-v326-scores.csv"
EFFORTS = ("low", "medium", "high", "extra-high")
MODEL = "musewonderfull"
NAMES = {MODEL: "Muse Wonder Full"}
SOLVER = "muse-code:muse-wonder-full-1.0-contributor"
REPORTED_MODEL = "muse-wonder-full-1.0-contributor"
PANELS = ("claude", "sol")
JUDGES = {"claude": "Claude Opus 5.5", "sol": "GPT-6.1 Sol"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
RESULTS = "docs/results/swe-v4-musewonder-full-2026-10"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEPS = {  # run root: (Muse Code version, bench tag, commit)
    "runs-effort-musewonder-full-v2": ("Muse Code 1.4.6 (1.4.6-R6000.1)", "bench/2026-10-13-musewonder-full-v2-low", "1f2e3a72d4"),
    "runs-effort-musewonder-full-v2-149": ("Muse Code 1.4.9 (1.4.9-R6297.1)", "bench/2026-10-16-musewonder-full-149", "fe63022c01"),
}
SOLVER_BINARIES = {"Muse Code 1.4.6 (1.4.6-R6000.1)": "c713165a287d64afb8816f8351a240b457a23524f4ade06bca0e41dfde410460",
                   "Muse Code 1.4.9 (1.4.9-R6297.1)": "2b856618ae3de3a63956e6d510b849ad707b16e5d2ed196299f3fe5ef2e3ff5e"}
VERSIONS = {"low": {"1.4.6": 23}, "medium": {"1.4.6": 21, "1.4.9": 2}, "high": {"1.4.9": 23}, "extra-high": {"1.4.9": 23}}
# The judging rounds: (round, directory, population record beside the card, efforts it judges).
ROUNDS = (("v3.26", "runs-code-quality-maintenance-v3.26", "comparison.json"),
          ("v3.26.1", "runs-code-quality-maintenance-v3.26.1", "comparison-topup.json"),
          ("v3.26.2", "runs-code-quality-maintenance-v3.26.2", "comparison-high.json"),
          ("v3.26.3", "runs-code-quality-maintenance-v3.26.3", "comparison-extra-high.json"))
SOL_ROUND = "runs-code-quality-maintenance-v3.25"  # GPT-6.1 Sol's exam and its Low and Medium votes, the v3.26 scored sibling
JUDGED_IN = {"low": {"v3.26": 23}, "medium": {"v3.26": 21, "v3.26.1": 2}, "high": {"v3.26.2": 22}, "extra-high": {"v3.26.3": 22}}
TOPUP = {"legacy-cellarcore-binary-parity", "legacy-paddockcore-binary-parity"}
TIMEOUT_S = 10800
TIMEOUTS = {("high", "legacy-paddockcore-binary-parity"), ("extra-high", "legacy-depotcore-binary-parity")}
TIMEOUT_NOTE = ("timeout: the run hit the flat 3-hour task bound while still working, so there is no finished submission and it is excluded "
                "from judging; it counts as a failed task in every pass count, as a combined score of 0 in combined_timeouts_zero, and in "
                "runtime and cost at its recorded duration and the usage Muse Code reported before the bound")
# Meta's pricing page, checked 2026-10-15 (Muse Wonder 1.0) and 2026-10-16 (Muse Spark 1.3); harness pricing-check.json. USD per million.
WONDER_RATES = {"input": 4.00, "cached_input": 0.20, "output": 20.00}
SPARK_RATES = {"input": 1.25, "cached_input": 0.15, "output": 4.25}
PRICING_METHOD = ("estimate: Muse Wonder Full main-model tokens at the Muse Wonder 1.0 list price (uncached input $4.00, cached input $0.20, "
                  "output $20.00 per million) plus, on Muse Code 1.4.9 runs, the Muse Spark 1.3 reminder-observer tokens at Muse Spark 1.3's "
                  "list price ($1.25, $0.15, $4.25 per million)")
# Per-minute logs of any other local benchmark process beside the sweep (timing caveat only); they start with Medium.
OVERLAP_LOGS = ("logs/musewonder-full-v2-medium-overlap.log", "logs/musewonder-full-v2-149-overlap.log")
OVERLAPS = {"low": None, "medium": 9, "high": 14, "extra-high": 5}
INFRA_ABORTED = {"high-legacy-snapcore-binary-parity-1098fab2"}
QUOTA_ABORTED = {"medium-legacy-cellarcore-binary-parity-cb3eb4d6"}
RECOVERY_METHOD = "one-based departure indexes moved to zero-based; statuses untouched"
EXPECTED_RECOVERIES = {"v3.25": 5, "v3.26": 0, "v3.26.1": 1, "v3.26.2": 2, "v3.26.3": 1}  # all GPT-6.1 Sol answer-key matches
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert not any(mark in text for mark in FORBIDDEN), name
    assert "SWE v4" not in text and "ultra" not in text.lower(), name
    (DEST / name).write_text(text)


def mean_se(values):
    values = list(values)
    return {"n": len(values), "mean": statistics.mean(values),
            "se": statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0}


def composite(row, code_quality, weight):
    other = (0.5 - weight) / 2
    return 100 * (.5 * row["functional"] + other * row["quality"] + other * row["security"] + weight * code_quality / 100)


def usage(run_dir):
    """The run's one muse_usage record: main-model totals and the reminder observers recorded apart under auxiliary."""
    found = [json.loads(line) for line in (run_dir / "trace.jsonl").read_text().splitlines() if '"muse_usage"' in line]
    found = [e for e in found if e.get("type") == "muse_usage"]
    assert len(found) == 1, run_dir.name
    return found[0]["data"]


def price(tokens, rates):
    cached = tokens["cached_tokens"]
    return ((tokens["input_tokens"] - cached) * rates["input"] + cached * rates["cached_input"] + tokens["output_tokens"] * rates["output"]) / 1e6


def solver_facts(root, run_dir, effort, lock):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    version, tag, commit = SWEEPS[root]
    assert solver["model"] == SOLVER and solver["effort"]["requested"] == effort, run_dir.name
    assert solver["cli_agent"]["harness_version"] == version, run_dir.name
    assert solver["cli_agent"]["requested_model"] == solver["cli_agent"]["reported_model"] == REPORTED_MODEL
    source = solver["source"]
    assert source["harness"]["describe"] == tag and source["harness"]["commit"].startswith(commit), run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_hash"] == lock[solver["task_id"]], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"] and not audit["web"]["contaminated"]
    fs = audit["filesystem"]
    assert fs["benchmark_data_paths"] == [] and fs["answer_key_paths"] == [] and not fs["contaminated"]
    # Muse Code keeps its own session store and scratch files in a per-run temporary folder outside the workspace; nothing else is touched.
    assert fs["verdict"] == "out_of_workspace" and all("/vb-muse-session-" in p for p in fs["out_of_workspace_paths"]), run_dir.name
    timeout = (effort, solver["task_id"]) in TIMEOUTS
    if timeout:
        assert not solver["finished"] and solver["scores"]["budget_exceeded"] and solver["duration_s"] >= TIMEOUT_S - 5
        assert solver["scores"]["functional"] == 0.0 and solver["scores"]["quality"] is None and solver["scores"]["security"] is None
    else:
        assert solver["finished"] and solver["duration_s"] < TIMEOUT_S and not solver["scores"].get("budget_exceeded"), run_dir.name
    data = usage(run_dir)
    tokens = solver["tokens"]
    assert (data["input_tokens"], data["cached_tokens"], data["output_tokens"], data["reasoning_tokens"]) == (
        tokens["prompt"], tokens["cached_input"], tokens["completion"], tokens["reasoning_output"]), run_dir.name
    cd = solver["cost_detail"]
    assert cd["agent_input_tokens"] == tokens["prompt"] and cd["agent_cached_input_tokens"] == tokens["cached_input"]
    assert cd["agent_uncached_input_tokens"] == tokens["prompt"] - tokens["cached_input"]
    assert solver["total_tokens"] == tokens["prompt"] + tokens["completion"] == tokens["total"]
    aux = data.get("auxiliary") or {}
    assert set(aux) <= {"muse-spark-1.3"}, run_dir.name
    if version.startswith("Muse Code 1.4.6"):
        assert not aux, run_dir.name  # 1.4.6 ran its reminder observers on the main model
    reminder = aux.get("muse-spark-1.3")
    main_usd = price(data, WONDER_RATES)
    reminder_usd = price(reminder, SPARK_RATES) if reminder else 0.0
    verifier = solver.get("verifier") or {}
    hidden = verifier.get("fail_to_pass")
    return solver, {
        "solver_cli_version": version, "solver_binary_sha256": SOLVER_BINARIES[version], "source_tag": tag,
        "task_hash": solver["task_hash"],
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False,
                            "outside_workspace": "Muse Code's own per-run session folder only"},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v) if hidden else (0 if timeout else None),
        "hidden_behaviours": len(hidden) if hidden else None,
        "model_calls": {"muse-wonder-full-1.0": data["calls"], **({"muse-spark-1.3 (reminder observers)": reminder["calls"]} if reminder else {})},
        "raw_tokens": solver["total_tokens"],
        "token_usage": {"input_tokens": tokens["prompt"], "cached_input_tokens": tokens["cached_input"],
                        "uncached_input_tokens": tokens["prompt"] - tokens["cached_input"], "output_tokens": tokens["completion"],
                        "reasoning_output_tokens": tokens["reasoning_output"]},
        "reminder_observer_usage": None if not reminder else {
            "model": "muse-spark-1.3", "calls": reminder["calls"], "input_tokens": reminder["input_tokens"],
            "cached_input_tokens": reminder["cached_tokens"], "output_tokens": reminder["output_tokens"],
            "reasoning_output_tokens": reminder["reasoning_tokens"]},
        "main_model_usd": main_usd, "reminder_usd": reminder_usd, "estimated_usd": main_usd + reminder_usd, "pricing_method": PRICING_METHOD,
    }


def overlap_minutes(root, start, end):
    """Minutes in which the per-minute overlap log recorded another local benchmark process during this run."""
    stamps = []
    for name in OVERLAP_LOGS:
        for line in (root / name).read_text().splitlines():
            if "overlap_procs=" in line:
                stamps.append(datetime.fromisoformat(line.split()[0].replace("Z", "+00:00")))
    a, b = datetime.fromisoformat(start), datetime.fromisoformat(end)
    return sum(1 for t in stamps if a <= t <= b)


def call_records(out):
    """Counted calls per stage, calls with a second attempt, operator markers and recoveries under calls/."""
    counts = {p.name: {s.name: sum(1 for d in s.iterdir() if d.is_dir()) for s in sorted(p.iterdir()) if s.is_dir()}
              for p in sorted((out / "calls").iterdir()) if p.is_dir()}
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in counts}
    markers = [str(p.relative_to(out)) for p in (out / "calls").glob("*/*/*/operator-*.json")]
    recoveries = []
    for p in sorted((out / "calls").glob("*/*/*/selected.json")):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries.append((p.parents[2].name, p.parents[1].name, p.parent.name, selected["operator_recovery"]["method"]))
    return counts, retries, markers, recoveries


def public_settings(settings):
    return {k: v for k, v in settings.items() if k not in ("claude", "codex", "native_binary", "cursor")}


def main():  # noqa: PLR0912, PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    lock = read(root / LOCK)["tasks"]
    card_path = root / RESULTS / "musewonder-full-vs-frontier.json"
    card = read(card_path)
    assert card["final"] is True
    card_groups = card["groups"]["wonder"]
    assert list(card_groups) == list(EFFORTS)  # Max is not offered in Contributor mode

    # GPT-6.1 Sol's round (v3.25): its exam, its protocol and the Grok seat that stopped before any vote.
    sol_dir = root / SOL_ROUND
    sol_protocol = read(sol_dir / "protocol.json")
    assert sol_protocol["id"] == "code-quality-maintenance-v3.25"
    assert sol_protocol["source_comparison_sha256"] == digest(root / RESULTS / "comparison.json")
    sol_calibration = read(sol_dir / "calibration-sol.json")
    assert sol_calibration["protocol_sha256"] == digest(sol_dir / "protocol.json")
    assert not (sol_dir / "summary.json").exists()  # published only through the v3.26 sibling

    rounds = {}
    for name, directory, population in ROUNDS:
        out = root / directory
        summary, protocol = read(out / "summary.json"), read(out / "protocol.json")
        manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
        assert summary["protocol"] == protocol["id"] == f"code-quality-maintenance-{name}"
        assert summary["ready_for_publication"] and summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
        assert summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
        assert summary["expected_submissions"] == summary["published_submissions"] == len(manifest) == len(summary["rows"])
        assert protocol["source_comparison_sha256"] == digest(root / RESULTS / population)
        assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
        assert protocol["sensitivity_panels"] == {}
        for key in ("rubric", "system", "pair_instruction", "probe_instruction", "match_instruction", "schemas", "seed", "repeats",
                    "gate_allowance", "weights", "invalid_response_retries", "control_source_hashes"):
            assert protocol[key] == sol_protocol[key], (name, key)
        assert set(protocol["reviewers"]) == ({"claude"} if name == "v3.26" else set(PANELS))
        assert protocol["reviewers"]["claude"]["claude_version"] == "2.1.300" and protocol["reviewers"]["claude"]["model"] == "claude-opus-5-5"
        rounds[name] = {"dir": out, "summary": summary, "protocol": protocol, "manifest": manifest, "population": population}
    v326 = rounds["v3.26"]["protocol"]
    sibling = v326["scored_siblings"]["sol"]
    assert sibling["protocol_id"] == "code-quality-maintenance-v3.25" and sibling["protocol_sha256"] == digest(sol_dir / "protocol.json")
    assert sibling["calibration_sha256"] == digest(sol_dir / "calibration-sol.json")
    assert v326["shares_evidence_with"] == {"protocol_sha256": digest(sol_dir / "protocol.json"),
                                            "manifest_sha256": digest(sol_dir / "private-manifest.json")}
    assert set(v326["excluded_judges"]) == {"muse"} and set(v326["replaced_seats"]) == {"grok"}
    claude_calibration = read(rounds["v3.26"]["dir"] / "calibration-claude.json")
    assert claude_calibration["protocol_sha256"] == digest(rounds["v3.26"]["dir"] / "protocol.json")
    exam = {"claude": {"sha256": digest(rounds["v3.26"]["dir"] / "calibration-claude.json"), "protocol_sha256": digest(rounds["v3.26"]["dir"] / "protocol.json")},
            "sol": {"sha256": digest(sol_dir / "calibration-sol.json"), "protocol_sha256": digest(sol_dir / "protocol.json")}}
    gate = rounds["v3.26.1"]["protocol"]["top_up_of"]
    assert gate["protocol_sha256"] == exam["claude"]["protocol_sha256"] and gate["summary_sha256"] == digest(rounds["v3.26"]["dir"] / "summary.json")
    for name in ("v3.26.1", "v3.26.2", "v3.26.3"):
        protocol = rounds[name]["protocol"]
        record = protocol["top_up_of"] if name == "v3.26.1" else protocol["extends"]
        for p in PANELS:
            assert record["calibration"][p]["sha256"] == exam[p]["sha256"] and record["calibration"][p]["protocol_sha256"] == exam[p]["protocol_sha256"]
        assert protocol["planned_calls"]["calibration_per_panel"] == 0
        assert public_settings(protocol["reviewers"]["sol"]) == public_settings(sol_protocol["reviewers"]["sol"])
        assert public_settings(protocol["reviewers"]["claude"]) == public_settings(v326["reviewers"]["claude"])
        if name != "v3.26.1":
            assert all(record["protocol_sha256"][d] == digest(root / d / "protocol.json") for d in record["directories"])
    excluded = [x for name in ("v3.26.2", "v3.26.3") for x in rounds[name]["protocol"]["population"]["excluded"]]
    assert {(x["effort"], x["task"]) for x in excluded} == TIMEOUTS and all(not x["finished"] for x in excluded)
    assert rounds["v3.26"]["protocol"]["population"]["excluded"] == [] and rounds["v3.26.1"]["protocol"]["population"]["excluded"] == []
    assert {x["task"] for x in v326["population"]["missing"]} == TOPUP

    # Every finished solver summary in the two sweep roots: 92 runs, 23 per level, none duplicated; aborted attempts kept apart.
    found = {}
    for sweep in SWEEPS:
        for p in sorted((root / sweep).glob("*/legacy-*/summary.json")):
            effort = p.parent.parent.name
            assert effort in EFFORTS, p
            key = (effort, read(p)["task_id"])
            assert key not in found, key
            found[key] = (sweep, p.parent)
        assert all((d / "summary.json").exists() for d in (root / sweep).glob("*/legacy-*") if d.parent.name in EFFORTS)
    assert len(found) == 92 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    assert {p.name for p in (root / "runs-effort-musewonder-full-v2/quota-aborted").iterdir()} == QUOTA_ABORTED
    assert {p.name for p in (root / "runs-effort-musewonder-full-v2-149/infra-aborted").iterdir()} == INFRA_ABORTED
    for parent in ("runs-effort-musewonder-full-v2/quota-aborted", "runs-effort-musewonder-full-v2-149/infra-aborted"):
        for folder in (root / parent).iterdir():
            assert not (folder / "summary.json").exists(), folder.name  # an interrupted attempt is never scored
    DEST.mkdir(parents=True, exist_ok=True)

    behaviours = {}
    facts_by_key = {}
    for key, (sweep, run_dir) in found.items():
        solver, facts = solver_facts(sweep, run_dir, key[0], lock)
        facts_by_key[key] = (solver, facts, run_dir)
        if facts["hidden_behaviours"] is not None:
            assert behaviours.setdefault(key[1], facts["hidden_behaviours"]) == facts["hidden_behaviours"]
    for key in TIMEOUTS:  # no verifier ran before the bound: the task's behaviour count comes from its other levels, none fixed
        facts_by_key[key][1]["hidden_behaviours"] = behaviours[key[1]]

    rows = []
    judged_keys = set()
    for name, r in rounds.items():
        for entry in r["summary"]["rows"]:
            run = r["manifest"][entry["id"]]
            key = (run["effort"], run["task"])
            assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
            assert key not in judged_keys and key not in TIMEOUTS, key
            judged_keys.add(key)
            solver, facts, run_dir = facts_by_key[key]
            assert run_dir.name == run["run_id"] and digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
            assert run["solver_cli_version"] == facts["solver_cli_version"] and not run["fallback"] and not entry["fallback"]
            assert (run["functional"], run["quality"], run["security"]) == (solver["scores"]["functional"], solver["scores"]["quality"], solver["scores"]["security"])
            if facts["reminder_observer_usage"] or "reminder_observer_usage" in run:
                mine = facts["reminder_observer_usage"]
                theirs = run["reminder_observer_usage"]["muse-spark-1.3"]
                assert (mine["calls"], mine["input_tokens"], mine["output_tokens"]) == (theirs["calls"], theirs["input_tokens"], theirs["output_tokens"])
            panels = entry["panels"]
            assert all(panels[p]["l1"] is not None and panels[p]["l2"] is not None and not panels[p]["reviewer_fallback"] for p in PANELS)
            published = entry["published"]
            assert not published["l2_redistributed"]
            l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
            l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
            code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
            assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
            combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
            combined_20 = composite(run, code_quality, 0.20)
            assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
            single = {p: composite(run, (SPLIT_WITHOUT_L3["l1"] * panels[p]["l1"]["score"] + SPLIT_WITHOUT_L3["l2"] * panels[p]["l2"])
                                   / WEIGHTS["code_quality"], WEIGHTS["code_quality"]) for p in PANELS}
            rows.append({
                "model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"],
                "judged_under": f"code-quality-maintenance-{name}", "judged": "published", "scored_panels": list(PANELS), "finished": True,
                "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
                "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": False, "code_quality": code_quality,
                "combined_33": combined_33, "combined_timeouts_zero": combined_33, "combined_20_profile": combined_20,
                "combined_single_judge": single,
                "panels": {p: {"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                               "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                               "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} for p in PANELS},
                "passed_quirk_families": len(run["passed_families"]), "duration_s": run["duration_s"],
                "started_at": run["started_at"], "finished_at": run["finished_at"], "evidence_sha256": run["evidence_sha256"], **facts,
            })
    for key in sorted(TIMEOUTS):
        solver, facts, run_dir = facts_by_key[key]
        rows.append({
            "model": MODEL, "effort": key[0], "task": key[1], "run_id": run_dir.name, "judged_under": None, "judged": TIMEOUT_NOTE,
            "scored_panels": [], "finished": False, "functional": 0.0, "automated_quality": None, "security": None, "reviewed_score": None,
            "intent_recovery": None, "intent_recovery_redistributed": None, "code_quality": None, "combined_33": None,
            "combined_timeouts_zero": 0.0, "combined_20_profile": None, "combined_single_judge": None, "panels": None,
            "passed_quirk_families": None, "duration_s": solver["duration_s"], "started_at": solver["started_at"],
            "finished_at": solver["finished_at"], "evidence_sha256": None, **facts,
        })
    assert len(rows) == 92 and {(r["effort"], r["task"]) for r in rows} == set(found)
    for r in rows:
        r["overlap_minutes_logged"] = None if r["effort"] == "low" else overlap_minutes(root, r["started_at"], r["finished_at"])
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    for effort, versions in VERSIONS.items():
        got = Counter(r["solver_cli_version"].split()[2] for r in rows if r["effort"] == effort)
        assert got == Counter(versions), (effort, got)
        judged_in = Counter(r["judged_under"].removeprefix("code-quality-maintenance-") for r in rows if r["effort"] == effort and r["judged_under"])
        assert judged_in == Counter(JUDGED_IN[effort]), (effort, judged_in)
    assert {r["task"] for r in rows if r["effort"] == "medium" and r["solver_cli_version"].startswith("Muse Code 1.4.9")} == TOPUP
    for effort, expected in OVERLAPS.items():
        got = None if expected is None else sum(1 for r in rows if r["effort"] == effort and r["overlap_minutes_logged"])
        assert got == expected, (effort, got)

    save("runs.json", {
        "runs": len(rows), "published": 90, "timeouts": 2, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
        "judged_rule": "judged is \"published\" where a v3.26, v3.26.1, v3.26.2 or v3.26.3 summary publishes a Code quality score from both "
                       "judges (judged_under names the round); the two timed-out rows carry the reason they have none",
        "timeouts_rule": "combined_timeouts_zero is the combined score with each timed-out run counted as 0 (harness DECISIONS.md 2026-09-28); "
                         "for every judged run it equals combined_33",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator; no Muse Wonder Full run needed "
                                "that rule",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run "
                                   "passed (a timed-out run reached no verification, so it fixed none)",
        "cost_fields": {"estimated_usd": "main_model_usd plus reminder_usd, an estimate (Meta lists no API price for Muse Wonder Full)",
                        "main_model_usd": "Muse Wonder Full tokens at the Muse Wonder 1.0 list price",
                        "reminder_usd": "Muse Code 1.4.9's Muse Spark 1.3 reminder-observer tokens at Muse Spark 1.3's list price; 0 on 1.4.6"},
        "token_fields": {"raw_tokens": "Muse Wonder Full input (cached included) plus output, as Muse Code reports it; reminder-observer "
                                       "tokens are recorded apart in reminder_observer_usage",
                         "token_usage.output_tokens": "output tokens, reasoning included"},
        "overlap_field": "overlap_minutes_logged counts the minutes in which the per-minute overlap log recorded another local benchmark "
                         "process during the run (a timing caveat; scores are unaffected); the log started with Medium, so Low is null",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    def pct(value):
        return None if value is None else 100 * value

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_timeouts_zero", "combined_20_profile",
                         "combined_claude_only", "combined_sol_only", "functional_pct", "automated_quality_pct", "security_pct",
                         "hidden_behaviours_fixed", "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery",
                         "claude_reviewed", "claude_readability", "claude_maintainability", "claude_intent_recovery",
                         "sol_reviewed", "sol_readability", "sol_maintainability", "sol_intent_recovery", "passed_quirk_families",
                         "wonder_calls", "reminder_calls", "duration_s", "raw_tokens", "output_tokens", "reminder_input_tokens", "reminder_output_tokens",
                         "main_model_usd", "reminder_usd", "estimated_usd", "overlap_minutes_logged", "started_at", "finished_at",
                         "solver_cli_version", "task_hash", "evidence_sha256"])
        for r in rows:
            p = r["panels"] or {q: {} for q in PANELS}
            single = r["combined_single_judge"] or {}
            rem = r["reminder_observer_usage"] or {}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"] or "",
                             "published" if r["judged"] == "published" else "timeout", fmt(r["combined_33"]), fmt(r["combined_timeouts_zero"]),
                             fmt(r["combined_20_profile"]), fmt(single.get("claude")), fmt(single.get("sol")), f'{100 * r["functional"]:.2f}',
                             fmt(pct(r["automated_quality"]), 2), fmt(pct(r["security"]), 2), r["hidden_behaviours_fixed"], r["hidden_behaviours"],
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             *[fmt(p[q].get(k)) for q in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             "" if r["passed_quirk_families"] is None else r["passed_quirk_families"],
                             r["model_calls"]["muse-wonder-full-1.0"], rem.get("calls", 0), r["duration_s"], r["raw_tokens"],
                             r["token_usage"]["output_tokens"], rem.get("input_tokens", 0), rem.get("output_tokens", 0),
                             fmt(r["main_model_usd"], 6), fmt(r["reminder_usd"], 6), fmt(r["estimated_usd"], 6),
                             "" if r["overlap_minutes_logged"] is None else r["overlap_minutes_logged"], r["started_at"], r["finished_at"],
                             r["solver_cli_version"], r["task_hash"], r["evidence_sha256"] or ""])

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        judged = [r for r in rs if r["judged"] == "published"]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(judged), "runs": len(rs), "timeouts": len(rs) - len(judged),
            "timeout_tasks": sorted(r["task"] for r in rs if r["judged"] != "published"),
            "combined_33": mean_se(r["combined_33"] for r in judged),
            "combined_timeouts_zero": mean_se(r["combined_timeouts_zero"] for r in rs),
            "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in judged) for p in PANELS},
            "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
            "intent_recovery": mean_se(r["intent_recovery"] for r in judged), "intent_recovery_redistributed_runs": 0,
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in judged), "functional_all_runs": mean_se(100 * r["functional"] for r in rs),
            "automated_quality": mean_se(100 * r["automated_quality"] for r in judged), "security": mean_se(100 * r["security"] for r in judged),
            # passed counts judged runs; passed_all_runs counts all 23 and is the one to read.
            "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            # Runtime, tokens and cost are facts of the sweep and cover every run, timeouts included, as on the harness card.
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "priced_runs": len(rs),
            "cli_versions": dict(sorted(Counter(r["solver_cli_version"] for r in rs).items())),
            "judged_in": dict(sorted(Counter(r["judged_under"] for r in judged).items())),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            "reminder_usd_total": sum(r["reminder_usd"] for r in rs),
            "overlapping_runs": None if effort == "low" else sum(1 for r in rs if r["overlap_minutes_logged"]),
        }
        # The harness card (musewonder-full-vs-frontier.json) carries the same figures; they must match exactly.
        c = card_groups[effort]
        assert (c["n"], c["n_judged"], c["passed"], c["timeouts"]) == (g["runs"], g["n"], g["passed_all_runs"], g["timeouts"]), effort
        assert c["versions"] == g["cli_versions"], effort
        for field, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]),
                             ("functional", g["functional_all_runs"]["mean"]), ("functional_se", g["functional_all_runs"]["se"]),
                             ("usd", g["usd"]["mean"]), ("minutes", g["minutes"]["mean"]),
                             ("combined_timeouts_zero", g["combined_timeouts_zero"]["mean"] if g["timeouts"] else None)):
            assert (value is None and c[field] is None) or abs(c[field] - value) < 1e-9, (effort, field, c[field], value)
        for p in PANELS:
            assert abs(c["by_judge_l1"][p] - g["by_panel"][p]["mean"]) < 1e-9, (effort, p)
        groups.append(g)
    # Each round's own summary aggregates its level; Low and High, Extra-high are whole levels within one round.
    for effort, name in (("low", "v3.26"), ("high", "v3.26.2"), ("extra-high", "v3.26.3")):
        entry = rounds[name]["summary"]["groups"][f"{MODEL}/{effort}"]
        g = next(x for x in groups if x["effort"] == effort)
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
    assert [g["passed_all_runs"] for g in groups] == [18, 21, 19, 19]
    assert [g["n"] for g in groups] == [23, 23, 22, 22] and [g["timeouts"] for g in groups] == [0, 0, 1, 1]
    assert [round(g["combined_33"]["mean"], 2) for g in groups] == [86.95, 88.27, 88.19, 87.59]
    assert [round(g["combined_timeouts_zero"]["mean"], 2) for g in groups] == [86.95, 88.27, 84.36, 83.78]
    assert [f'{g["usd"]["mean"]:.2f}' for g in groups] == ["3.93", "4.09", "4.72", "5.08"]
    # Analysis No. 02 publishes the single-judge figures to one decimal.
    assert [(round(g["combined_single_judge"]["claude"]["mean"], 1), round(g["combined_single_judge"]["sol"]["mean"], 1)) for g in groups] == [
        (85.0, 88.9), (86.2, 90.3), (86.1, 90.2), (85.7, 89.5)]
    with (root / RESULTS / "musewonder-full-vs-frontier-efforts.csv").open(newline="") as source:
        table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == "wonder"}
    for g in groups:
        t = table[g["effort"]]
        assert int(t["n"]) == g["runs"] and int(t["passed"]) == g["passed_all_runs"]
        assert abs(float(t["combined"]) - g["combined_33"]["mean"]) < 1e-4 and abs(float(t["usd_per_task"]) - g["usd"]["mean"]) < 1e-4
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "timeouts", "combined_33", "combined_33_se", "combined_timeouts_zero", "combined_20_profile",
                         "combined_claude_only", "combined_sol_only", "code_quality", "code_quality_se", "reviewed_score", "intent_recovery",
                         "readability", "maintainability", "claude_reviewed", "sol_reviewed", "functional_all_runs", "automated_quality", "security",
                         "passed_of_23", "hidden_behaviours_fixed", "hidden_behaviours", "mean_minutes", "mean_minutes_se", "mean_raw_tokens",
                         "mean_usd", "mean_usd_se", "total_usd", "reminder_usd_total", "cli_versions"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], g["timeouts"], f'{g["combined_33"]["mean"]:.4f}',
                             f'{g["combined_33"]["se"]:.4f}', f'{g["combined_timeouts_zero"]["mean"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["claude"]["mean"]:.4f}', f'{g["combined_single_judge"]["sol"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}',
                             f'{g["by_panel"]["claude"]["mean"]:.4f}', f'{g["by_panel"]["sol"]["mean"]:.4f}', f'{g["functional_all_runs"]["mean"]:.4f}',
                             f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"],
                             g["hidden_behaviours"], f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}',
                             f'{g["usd"]["mean"]:.6f}', f'{g["usd"]["se"]:.6f}', f'{g["usd_total"]:.6f}', f'{g["reminder_usd_total"]:.6f}',
                             " ".join(f"{v}x{k.split()[2]}" for k, v in g["cli_versions"].items())])

    pricing = read(root / RESULTS / "pricing-check.json")
    meta = pricing["models"]
    assert (meta["muse-wonder-1.0"]["input"], meta["muse-wonder-1.0"]["cached_input"], meta["muse-wonder-1.0"]["output"]) == tuple(WONDER_RATES.values())
    assert (meta["muse-spark-1.3"]["input"], meta["muse-spark-1.3"]["cached_input"], meta["muse-spark-1.3"]["output"]) == tuple(SPARK_RATES.values())
    assert meta["muse-wonder-full-1.0"]["price"] is None
    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "reminder_usd": sum(r["reminder_usd"] for r in rows),
                      "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "reminder_tokens": sum(r["reminder_observer_usage"]["input_tokens"] + r["reminder_observer_usage"]["output_tokens"]
                                             for r in rows if r["reminder_observer_usage"]),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    save("economics.json", {
        "scope": "Solver inference only, an API-equivalent estimate; the model ran on the owner's Muse Code subscription in Contributor mode, "
                 "so these are estimates, not bills. Judging is excluded. Every run is priced, including the two timeouts, from the usage Muse "
                 "Code reported.",
        "pricing_verified": {"muse-wonder-1.0": pricing["checked_at"], "muse-spark-1.3": meta["muse-spark-1.3"]["checked_at"]},
        "sources": {"meta": meta["muse-wonder-1.0"]["source"]},
        "rates_per_million": {"muse-wonder-1.0 (applied to Muse Wonder Full)": WONDER_RATES, "muse-spark-1.3 (reminder observers)": SPARK_RATES},
        "pricing_method": PRICING_METHOD,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "reminder_usd_total": g["reminder_usd_total"], "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"],
                    "output_tokens": g["output_tokens"], "minutes": g["minutes"]} for g in groups],
        "totals": totals,
        "limitations": [
            "Meta lists no API price for Muse Wonder Full: it is not served on the Model API and is available through the Muse Code "
            "subscription only. Its tokens are priced at the Muse Wonder 1.0 list price, so every cost here is an estimate.",
            "Muse Code 1.4.9 runs its end-of-run goal and verify reminder observers on Muse Spark 1.3; their tokens are recorded apart and "
            "priced at Muse Spark 1.3's Standard list price. Muse Code 1.4.6 ran them on the main model, so on Low and 21 Medium runs they "
            "are inside the Muse Wonder Full totals.",
            "Meta charges the same rate at any context length, so no long-context tier applies.",
            "Cost per task covers all 23 runs at every level, timeouts included, as on the harness card.",
        ],
        "pricing_check_sha256": digest(root / RESULTS / "pricing-check.json"),
    })

    calibration = {}
    for panel, result, protocol_id in (("claude", claude_calibration, "code-quality-maintenance-v3.26"), ("sol", sol_calibration, "code-quality-maintenance-v3.25")):
        assert result["passed"] and result["failing_gates"] == [] and not result["allowance_used"] and result["call_count"] == 80
        assert all(g["passed"] for g in result["gates"].values())
        calibration[panel] = {"judge": JUDGES[panel], "taken_under": protocol_id,
                              **{k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                        "gates", "control_means")},
                              "gates_later_rounds": "v3.26.1, v3.26.2 and v3.26.3 reuse this verdict with no new exam; each records its sha256"}
    save("calibration.json", calibration)

    counted, second, recoveries = {}, {}, []
    for name, out in [("v3.25", sol_dir)] + [(n, r["dir"]) for n, r in rounds.items()]:
        counts, retries, markers, recs = call_records(out)
        assert markers == [], (name, markers)
        assert len(recs) == EXPECTED_RECOVERIES[name] and all(p == "sol" and s == "match" and m == RECOVERY_METHOD for p, s, _, m in recs), (name, recs)
        recoveries += [{"round": name, "panel": p, "stage": s, "submission": i, "method": m} for p, s, i, m in recs]
        for panel in PANELS:
            if panel in counts:
                counted.setdefault(panel, {}).setdefault(name, counts[panel])
                second.setdefault(panel, {})[name] = retries[panel]
        if name == "v3.25":
            grok_calls = counts.get("grok")
    assert grok_calls == {"calibration": 7} and "claude" not in counted.get("claude", {}).get("v3.25", {})
    assert counted["claude"]["v3.26"] == counted["sol"]["v3.25"] == {"calibration": 80, "match": 44, "pairwise": 4, "primary": 44, "probe": 44, "repeat": 2}
    for name, n, repeats in (("v3.26.1", 2, 2), ("v3.26.2", 22, 1), ("v3.26.3", 22, 1)):
        for panel in PANELS:
            assert counted[panel][name] == {"match": n, "primary": n, "probe": n, "repeat": repeats}, (name, panel)
    assert second == {"claude": {"v3.26": 0, "v3.26.1": 0, "v3.26.2": 1, "v3.26.3": 0}, "sol": {"v3.25": 7, "v3.26.1": 1, "v3.26.2": 2, "v3.26.3": 2}}, second

    sol_settings = public_settings(sol_protocol["reviewers"]["sol"])
    claude_settings = public_settings(v326["reviewers"]["claude"])
    save("judge-protocols.json", {
        "scored_panel": {"claude": claude_settings, "sol": sol_settings},
        "protocol_ids": {name: f"code-quality-maintenance-{name}" for name in ("v3.25",) + tuple(rounds)},
        "protocol_sha256": {"v3.25": digest(sol_dir / "protocol.json"), **{n: digest(r["dir"] / "protocol.json") for n, r in rounds.items()}},
        "rounds": {
            "v3.25": "GPT-6.1 Sol's exam and its Low and Medium votes (44 runs); the Grok 4.7 seat stopped on its first exam call when the Cursor "
                     "account ran out of usage, a stop and not an exam failure, so no Grok 4.7 vote exists",
            "v3.26": "Claude Opus 5.5 replaces the Grok 4.7 seat and takes the exam; Low and Medium (44 runs) with GPT-6.1 Sol's v3.25 work "
                     "attached as a scored sibling on byte-identical inputs",
            "v3.26.1": "the two Medium runs made on Muse Code 1.4.9 after the quota reset (cellarcore, paddockcore), no new exam",
            "v3.26.2": "High, 22 judged runs (paddockcore hit the 3-hour bound), no new exam",
            "v3.26.3": "Extra-high, 22 judged runs (depotcore hit the 3-hour bound), no new exam",
        },
        "excluded_judges": v326["excluded_judges"], "replaced_seats": v326["replaced_seats"],
        "scored_sibling": {"panel": "sol", "protocol_id": sibling["protocol_id"], "protocol_sha256": sibling["protocol_sha256"],
                           "calibration_sha256": sibling["calibration_sha256"], "role": sibling["role"],
                           "shared_evidence": "v3.26 refuses to prepare unless the manifest, evidence, signals, controls, quirk keys, diagnostic "
                                              "selection and calibration order are byte-identical to v3.25's"},
        "amends": v326["amends"], "system": v326["system"], "rubric": v326["rubric"],
        "pair_instruction": v326["pair_instruction"], "probe_instruction": v326["probe_instruction"],
        "match_instruction": v326["match_instruction"], "schemas": v326["schemas"], "weights": v326["weights"],
        "gate_allowance": v326["gate_allowance"], "repeats": v326["repeats"], "seed": v326["seed"],
        "single_panel_rule": v326["single_panel_rule"], "invalid_response_retries": v326["invalid_response_retries"],
        "comparability": v326["comparability"], "control_source_hashes": v326["control_source_hashes"],
        "population": {name: {"cells": r["protocol"]["population"]["cells"], "excluded": len(r["protocol"]["population"]["excluded"])}
                       for name, r in rounds.items()},
        "not_judged": [{"effort": e, "task": t, "reason": TIMEOUT_NOTE} for e, t in sorted(TIMEOUTS, key=lambda x: EFFORTS.index(x[0]))],
        "judge_pins": {
            "claude": {"cli": "Claude Code", "version": "2.1.300", "sha256": v326["judge_pins"]["claude"]["sha256"],
                       "note": "a copy of the 2.1.300 binary, re-hashed before every stage, because Claude Code updates itself in place"},
            "sol": {"cli": "Codex", "version": sol_protocol["judge_pins"]["codex"]["version"],
                    "launcher_sha256": sol_protocol["judge_pins"]["codex"]["launcher"]["sha256"],
                    "native_sha256": sol_protocol["judge_pins"]["codex"]["native"]["sha256"], "rule": sol_protocol["judge_pins"]["codex"]["rule"]},
        },
        "exam_verdicts_reused": {name: {p: (r["protocol"]["top_up_of"] if name == "v3.26.1" else r["protocol"]["extends"])["calibration"][p]["sha256"]
                                        for p in PANELS} for name, r in rounds.items() if name != "v3.26"},
        "counted_calls": counted, "grok_calls_before_stop": grok_calls, "second_attempts": second,
        "operator_recoveries": recoveries,
        "operator_recovery_rule": "recover_one_based_indexes: both attempts of a GPT-6.1 Sol answer-key match failed only because the departure "
                                  "indexes were one-based (every cited index between 1 and the departure count, the largest equal to the count); "
                                  "the indexes are moved to zero-based, statuses untouched, and the original indexes are kept in the receipt",
    })
    overlap_logs = {Path(n).name: digest(root / n) for n in OVERLAP_LOGS}
    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"{n}/{f}": digest(r["dir"] / f) for n, r in rounds.items() for f in ("summary.json", "protocol.json", "private-manifest.json")},
            "v3.26/calibration-claude.json": digest(rounds["v3.26"]["dir"] / "calibration-claude.json"),
            "v3.25/protocol.json": digest(sol_dir / "protocol.json"), "v3.25/private-manifest.json": digest(sol_dir / "private-manifest.json"),
            "v3.25/calibration-sol.json": digest(sol_dir / "calibration-sol.json"),
            **{name: digest(root / RESULTS / name) for name in ("comparison.json", "comparison-topup.json", "comparison-high.json",
                                                                "comparison-extra-high.json", "musewonder-full-vs-frontier.json",
                                                                "musewonder-full-vs-frontier-efforts.csv", "musewonder-full-vs-frontier.png",
                                                                "pricing-check.json")},
            "suite.lock.json": digest(root / LOCK),
            **{f"{s}/protocol.json": digest(root / s / "protocol.json") for s in SWEEPS},
            **overlap_logs,
        },
        "export_checks": ["92 solver summaries across the two run roots, 23 per level, no task twice; the quota-stopped Medium cellarcore "
                          "attempt and the transport-stopped High snapcore attempt hold no summary and are not part of the population",
                          "every run is muse-code:muse-wonder-full-1.0-contributor at its requested level; Low and 21 Medium runs on Muse Code "
                          "1.4.6 from bench/2026-10-13-musewonder-full-v2-low, the last two Medium runs, High and Extra-high on 1.4.9 from "
                          "bench/2026-10-16-musewonder-full-149, every source block clean, every task hash equal to the frozen suite lock",
                          "every integrity audit: no web, no benchmark data or answer-key paths, nothing outside the workspace but Muse "
                          "Code's own per-run session folder",
                          "each run's token totals equal its trace's muse_usage record; reminder-observer usage appears only on 1.4.9 runs, "
                          "only on muse-spark-1.3, and equals the population record",
                          "the four population records' hashes equal the ones frozen in their protocols, and every judged run's summary "
                          "hash equals its manifest entry",
                          "v3.26 binds GPT-6.1 Sol's v3.25 protocol, calibration and manifest by hash; v3.26.1 to v3.26.3 bind both exam "
                          "verdicts by hash and plan no calibration calls",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule and control hashes are identical in "
                          "v3.25 and every v3.26 round",
                          "both judges passed calibration with no failing gate and no allowance used; no reviewer fallbacks in any round",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summaries; Low, High and "
                          "Extra-high cell means and standard errors matched to their round's summary",
                          "combined score, its standard error, the timeouts-as-0 figure, functional score, tasks passed, minutes, cost and each "
                          "judge's reviewed score per level matched to the harness card",
                          "the rates applied equal the pricing check; no dashes or host paths in exported text"],
        "limits": ["Muse Wonder Full is judged by Claude Opus 5.5 and GPT-6.1 Sol, not by Muse Spark 1.3 and Grok 4.6 like the other "
                   "Frontier v4 columns except Grok 4.7 (Muse Spark 1.3 and GPT-6.1 Sol): Muse Spark 1.3 is a Meta model and is not neutral "
                   "for a Meta submission. Scores from different panels are not calibrated against each other.",
                   "Claude Opus 5.5 rates Muse Wonder Full's reviewed Code quality about 17 points below GPT-6.1 Sol at every level. The "
                   "published score is their mean; combined_single_judge gives each judge alone.",
                   "Claude Opus 5.5 judged these runs and is also a compared model on the harness card and the board; its own column comes "
                   "from its own round, judged by Muse Spark 1.3 and Grok 4.6.",
                   "High paddockcore and Extra-high depotcore hit the 3-hour bound and have no Code quality score; each level carries a "
                   "second figure with the timeout counted as 0.",
                   "Two Muse Code versions: Low and 21 Medium runs on 1.4.6, the last two Medium runs, High and Extra-high on 1.4.9, which "
                   "Meta released with a quota reset and which runs its reminder observers on Muse Spark 1.3.",
                   "Cost is an estimate at the Muse Wonder 1.0 list price; Meta publishes no price for Muse Wonder Full.",
                   "Contributor mode: Meta may train on submitted content, so Frontier v4 task content may enter future Meta training data. "
                   "The owner accepted this. Max is not offered in Contributor mode, so these are all the levels.",
                   "The per-minute overlap log recorded another local benchmark process during 9 Medium, 14 High and 5 Extra-high runs "
                   "(overlap_minutes_logged); this can lengthen minutes, and Extra-high depotcore hit the 3-hour limit with 145 of its 180 "
                   "minutes overlapped, so its timeout may be partly due to the load. A clean rerun is scheduled after the "
                   "2026-10-19 Muse quota reset. The log started with Medium.",
                   "One High snapcore attempt stopped on a Meta API transport error 8 minutes in; it is unscored and kept apart, and the "
                   "task was rerun.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens, model calls by model, the estimated cost and the logged overlap minutes.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "the quota-stopped and transport-stopped attempts", "host binary paths"],
        "traces": "https://github.com/morganlinton/vulcanbench-musewonder-full-traces",
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
