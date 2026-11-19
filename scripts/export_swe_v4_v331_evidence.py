"""Export the public record of the GPT-6.2 Sol effort sweep on Frontier v4, judged under v3.31.

Adapted from the v3.29 GPT-6.1 Terra export (the same harness, Codex CLI on a
ChatGPT subscription, and the same panel, Muse Spark 1.3 and Grok 4.6, on the
same Cursor pin) with the v3.18 GPT-6.1 Sol export's handling of a row scored
by one judge. Same publication scope: per-run scores, per-panel sub-scores,
aggregates, judge protocol text, calibration verdicts, raw tokens and
API-equivalent cost. Raw prompts, patches, quirk answer keys and host paths are
withheld. Run from the site root:

    python3 scripts/export_swe_v4_v331_evidence.py --harness-root ../VulcanBench \\
        --judging ../VulcanBench-runs/<v3.31 run worktree>/runs-code-quality-maintenance-v3.31

--harness-root holds the sweep (runs-effort-gpt62-sol), the population record
and card in docs/results/swe-v4-gpt62-sol-2026-11, the suite lock, the sweep
launcher and its log. --judging is the v3.31 round directory, which lives in
its run worktree.

What differs from the GPT-6.1 Terra export, all forced by the sweep or its judging:

- Codex CLI 0.166.0, the earliest release that runs gpt-6.2-sol on the
  ChatGPT login; the login reported plan prolite, where earlier GPT columns
  ran on ChatGPT Pro.
- Every run passed every hidden test, at every level.
- One one-panel row. Grok 4.6's primary review of submission-069 (low
  granarycore) has no valid response: both attempts quoted code the
  submission does not contain, and the wrapper rule
  invalidate_unrecoverable_primary (the owner's v3.14 precedent) marked the
  call invalid. The frozen summary publishes that submission from Muse alone,
  reviewed layer and intent recovery both, as it does for any submission
  without two valid reviews (the v3.18 GPT-6.1 Sol precedent).
- No operator recovery, no evidence rebuild, no timeout, no Codex notice.
- Grok 4.6's calibration paused on a Cursor usage limit (the signed-in Cursor
  account was on the free plan); the same call was resumed under the quota
  rule after the owner signed in to the paid account, and the archived
  attempts are kept in that call's quota-stops folder.
- Muse Spark 1.3 passed calibration with the one-gate allowance (g11
  repeatability, 0.1 short); Grok 4.6 passed every gate, after failing the
  v3.30 exam.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-gpt62-sol-v331"
SCORES = SITE / "assets/data/swe-v4-gpt62-sol-v331-scores.csv"
CARD_STEM = "gpt62sol-vs-frontier"
CARDS = {f"{CARD_STEM}.png": SITE / "assets/cards/swe-v4-gpt62-sol-v331.png"}
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PROVIDER_EFFORT = {"low": "low", "medium": "medium", "high": "high", "extra-high": "xhigh", "max": "max"}
MODEL = "gpt62sol"
NAMES = {MODEL: "GPT-6.2 Sol"}
SOLVER = "codex:gpt-6.2-sol"
API_MODEL = "gpt-6.2-sol"
PANELS = ("muse", "grok")
JUDGES = {"muse": "Muse Spark 1.3", "grok": "Grok 4.6"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
# developers.openai.com/api/docs/pricing and the model page, checked 2026-11-17: standard tier, short context.
RATES_PER_MILLION = {MODEL: {"input": 2.00, "cached_input": 0.10, "output": 10.00}}
PRICING_VERIFIED = "2026-11-17"
PROTOCOL_ID = "code-quality-maintenance-v3.31"
RESULTS = "docs/results/swe-v4-gpt62-sol-2026-11"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEP = "runs-effort-gpt62-sol"
LAUNCHER = "scripts/run_gpt62_sol_v4.sh"
SWEEP_LOG = "logs/gpt62-sol-v4.log"
TAG, COMMIT = "bench/2026-11-17-gpt62-sol-frontier-v4", "49a64e957d745f1bd3bad86f55c1fbb840b4ed2f"
CLI_VERSION = "codex-cli 0.166.0"
V324_PROTOCOLS = SITE / "assets/data/swe-v4-haiku55-v324/judge-protocols.json"
ORIGINAL_PROTOCOLS = {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                      "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"}
CURSOR_VERSION = "2026.10.01-e373342"
CURSOR_DIGEST = "dedbb877a8405b20e38a3dc32f38bf614bcd96d6e557f73eb6e99ff8c87b8a73"
CURSOR_LAUNCHER_SHA = "2ccc9a8e167797641448b5e5c936f006ba137a2555f117f38c5eb76a5238a233"
CURSOR_VERSIONS_DIR = Path.home() / ".local/share/cursor-agent/versions"
DISPLAY_FROZEN, DISPLAY_REPORTED = "Cursor Grok 4.6 Medium", "Grok 4.6 Medium"
DISPLAY_RENAMES = 439  # selected Grok calls whose operator_review records the accepted rename
RETRIES = {"muse": 8, "grok": 4}  # calls with a second attempt under the frozen single-retry rule
INVALID_MARKER = "operator-invalid.json"
SUPERSEDED_MARKER = "operator-invalid.superseded.json"
ONE_PANEL = {"submission-069": ("low", "legacy-granarycore-binary-parity")}
ONE_PANEL_NOTE = ("published from Muse Spark 1.3 alone: Grok 4.6's primary review has no valid response (both attempts quoted code "
                  "the submission does not contain), so the v3.31 summary scores the reviewed layer and intent recovery from Muse only, "
                  "as it does for any submission without two valid reviews")
QUOTA_CALL = ("grok", "calibration", "control-7-r2")
FORBIDDEN = (chr(0x2014), chr(0x2013), chr(0), "/Users/", "/home/", "/private/", "/var/folders/")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cursor_version_digest(version_dir):
    """The v3.24 runner's digest: sha256 over every shipped file in a Cursor version directory, skipping its transient lock folder."""
    h = hashlib.sha256()
    for p in sorted(version_dir.rglob("*")):
        rel = p.relative_to(version_dir)
        if not p.is_file() or rel.parts[0] == ".running":
            continue
        h.update(rel.as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


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


def code_quality_of(reviewed, intent):
    """The pre-registered 24 plus 9 split; with no intent denominator the 9 points move to the reviewed layer."""
    return reviewed if intent is None else (SPLIT_WITHOUT_L3["l1"] * reviewed + SPLIT_WITHOUT_L3["l2"] * intent) / WEIGHTS["code_quality"]


def priced(usage):
    """The API-equivalent cost of one Codex receipt at the published list rates, cached input at the cache-read rate."""
    rate = RATES_PER_MILLION[MODEL]
    cached = min(usage["cached_input_tokens"], usage["input_tokens"])
    return ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6


def codex_notices(run_dir):
    """Codex's own error items in the run's event stream (the model-metadata fallback notice), and whether the turn completed."""
    notices, completed = [], 0
    for line in (run_dir / "cli-agent-stream.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "item.completed" and event["item"].get("type") == "error":
            notices.append(event["item"]["message"])
        elif event.get("type") == "turn.completed":
            completed += 1
    return notices, completed


def solver_facts(run_dir, effort, task, lock, receipt):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    provider = PROVIDER_EFFORT[effort]
    assert solver["model"] == SOLVER and solver["task_id"] == task, run_dir.name
    assert solver["effort"]["requested"] == effort and solver["effort"]["provider_value"] == provider, run_dir.name
    agent = solver["cli_agent"]
    assert (agent["harness"], agent["harness_version"], agent["billing"]) == ("codex", CLI_VERSION, "subscription"), run_dir.name
    assert agent["requested_model"] == API_MODEL and agent["reported_model"] is None and agent["model_identity_confidence"] == "requested-only"
    assert agent["subtype"] == "success" and agent["execution_boundary"] == "host-workspace; sandbox=workspace-write", run_dir.name
    source = solver["source"]  # tagged run worktree, clean: no hash bridge needed
    assert source["harness"]["describe"] == TAG and source["harness"]["commit"] == COMMIT, run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_hash"] == lock[task], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"] and not audit["web"].get("contaminated"), run_dir.name
    assert audit["filesystem"]["benchmark_data_paths"] == [] and audit["filesystem"]["answer_key_paths"] == [], run_dir.name
    assert solver["finished"] is True and solver["duration_s"] < 10800 and not solver["scores"].get("budget_exceeded"), run_dir.name
    tokens, usage = solver["tokens"], receipt["usage"]
    assert (tokens["prompt"], tokens["cached_input"], tokens["completion"], tokens["reasoning_output"]) == (
        usage["input_tokens"], usage["cached_input_tokens"], usage["output_tokens"], usage["reasoning_output_tokens"]), run_dir.name
    assert usage["cache_write_input_tokens"] == 0 and receipt["result_receipts"] == 1, run_dir.name
    assert solver["total_tokens"] == tokens["total"] == usage["input_tokens"] + usage["output_tokens"] == receipt["raw_tokens"]
    assert digest(run_dir / "cli-agent-stream.jsonl") == receipt["stream_sha256"], run_dir.name
    # The sweep stamped each run's cost at run time from the same receipt and rates; recompute it.
    cost = priced(usage)
    assert abs(cost - solver["cost_usd"]) < 1e-5 and solver["economics"]["api_equivalent_cost_usd"] == solver["cost_usd"], run_dir.name
    assert solver["economics"]["cli_reported_cost_usd"] is None and solver["cost_detail"]["cache_pricing_applied"], run_dir.name
    notices, completed = codex_notices(run_dir)
    assert completed == 1, run_dir.name
    assert notices == [], (run_dir.name, notices)
    hidden = solver["verifier"]["fail_to_pass"]
    return solver, {
        "solver_cli_version": CLI_VERSION, "source_tag": TAG, "task_hash": solver["task_hash"],
        "requested_model": API_MODEL, "requested_effort": provider, "model_identity": "requested-only",
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "codex_notices": [],
        "raw_tokens": receipt["raw_tokens"],
        "token_usage": {"input_tokens": usage["input_tokens"], "cached_input_tokens": usage["cached_input_tokens"],
                        "uncached_input_tokens": usage["input_tokens"] - usage["cached_input_tokens"],
                        "output_tokens": usage["output_tokens"], "reasoning_output_tokens": usage["reasoning_output_tokens"]},
        "estimated_usd": solver["cost_usd"],
    }


def call_records(out):
    """Live and superseded operator markers, recoveries, rename reviews, counted calls and second attempts under calls/."""
    def key(p):
        return (p.parents[1].parent.name, p.parents[1].name, p.parent.name)
    invalid = {key(p): read(p) for p in (out / "calls").glob(f"*/*/*/{INVALID_MARKER}")}
    superseded = {key(p): read(p) for p in (out / "calls").glob(f"*/*/*/{SUPERSEDED_MARKER}")}
    recoveries = {}
    for p in (out / "calls").glob("*/*/*/selected.json"):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries[key(p)] = selected["operator_recovery"]
    counts = {p: {s: sum(1 for d in (out / "calls" / p / s).iterdir() if d.is_dir())
                  for s in ("calibration", "primary", "repeat", "pairwise", "probe", "match")} for p in PANELS}
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in PANELS}
    completed = sorted(t for t in (read(p).get("completed_at") for p in (out / "calls").glob("*/*/*/attempt-*.json")) if t)
    return invalid, superseded, recoveries, counts, retries, completed


def main():  # noqa: PLR0912, PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    parser.add_argument("--judging", type=Path, required=True, help="the runs-code-quality-maintenance-v3.31 directory")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    out = args.judging.resolve()
    lock = read(root / LOCK)["tasks"]
    results = root / RESULTS
    summary, protocol = read(out / "summary.json"), read(out / "protocol.json")
    manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
    comparison_path = results / "comparison.json"
    comparison = read(comparison_path)

    # The round: one protocol, both judges passing, all 115 submissions published, every binding hash intact.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["expected_submissions"] == summary["published_submissions"] == len(manifest) == len(summary["rows"]) == 115
    assert summary["ready_for_publication"] and summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
    assert not summary["human_calibrated"] and not summary["humans_involved"]
    assert protocol["source_comparison_sha256"] == digest(comparison_path)
    assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
    assert protocol["scored_siblings"] == {} and protocol["sensitivity_panels"] == {}
    assert comparison["cells"] == protocol["population"]["cells"] == {f"{MODEL}/{e}": 23 for e in EFFORTS}
    assert comparison["excluded"] == comparison["missing"] == protocol["population"]["excluded"] == protocol["population"]["missing"] == []
    assert comparison["levels"] == {MODEL: list(EFFORTS)} and len(comparison["rows"]) == 115
    record_by_run = {r["run_id"]: r for r in comparison["rows"]}

    # The judges: the v3.24 settings, rubric and pins as published, read from the recovered v3.3 and v3.4 protocols.
    public_reviewers = {p: {k: v for k, v in protocol["reviewers"][p].items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}
                        for p in PANELS}
    v324 = read(V324_PROTOCOLS)
    assert public_reviewers == v324["scored_panel"]
    for key in ("rubric", "system", "pair_instruction", "probe_instruction", "match_instruction", "schemas", "seed", "repeats",
                "gate_allowance", "weights", "invalid_response_retries", "control_source_hashes"):
        assert protocol[key] == v324[key], key
    pins = protocol["judge_pins"]
    assert {v: s["sha256"] for v, s in pins["settings_sources"].items()} == ORIGINAL_PROTOCOLS
    recovered_checked = True
    for version, sha in ORIGINAL_PROTOCOLS.items():
        original = root / f"docs/judging/recovered/code-quality-maintenance-{version}-protocol.json"
        assert digest(original) == sha, version
        for p, settings in read(original)["reviewers"].items():
            if p in PANELS:
                assert {k: v for k, v in settings.items() if k not in ("muse", "cursor")} == public_reviewers[p], (version, p)
    cursor_pin = pins["cursor_version"]
    assert cursor_pin["version"] == CURSOR_VERSION and cursor_pin["digest"] == CURSOR_DIGEST
    assert Path(cursor_pin["directory"]).name == CURSOR_VERSION and cursor_pin["same_as"] == "code-quality-maintenance-v3.24"
    assert protocol["binaries"][cursor_pin["launcher"]]["sha256"] == CURSOR_LAUNCHER_SHA
    cursor_rechecked = False
    if (CURSOR_VERSIONS_DIR / CURSOR_VERSION).is_dir():
        assert cursor_version_digest(CURSOR_VERSIONS_DIR / CURSOR_VERSION) == CURSOR_DIGEST
        cursor_rechecked = True
    muse_binary = protocol["reviewers"]["muse"]["binary_sha256"]
    assert muse_binary == v324["scored_panel"]["muse"]["binary_sha256"] == v324["judge_pins"]["muse_binary_sha256"]

    # Operator records: one live marker, Grok's primary review of submission-069; no recovery and no superseded marker.
    invalid, superseded, recoveries, counts, retries, completed = call_records(out)
    assert set(invalid) == {("grok", "primary", i) for i in ONE_PANEL} and superseded == {} and recoveries == {}, (invalid, superseded, recoveries)
    assert {(manifest[i]["effort"], manifest[i]["task"]) for i in ONE_PANEL} == set(ONE_PANEL.values())
    marker = invalid["grok", "primary", "submission-069"]
    assert marker["rule"] == "invalidate_unrecoverable_primary" and marker["malformed_attempts"] == {}
    assert marker["owner_decision"] == "2026-09-23 (v3.14 precedent)" and set(marker["unsupported_excerpts"]) == {"1", "2"}
    assert not (out / "calls/grok/primary/submission-069/selected.json").exists()
    # Grok's calibration call control-7-r2 stopped on a Cursor usage limit and was resumed under the quota rule.
    quota_dir = out / "calls" / "/".join(QUOTA_CALL) / "quota-stops"
    quota_notes = sorted(quota_dir.glob("*-note.json"))
    assert len(quota_notes) == 5 and [d for d in (out / "calls").glob("*/*/*/quota-stops")] == [quota_dir]
    assert (out / "calls" / "/".join(QUOTA_CALL) / "selected.json").is_file()
    grok_calls = [read(q) for q in (out / "calls/grok").glob("*/*/selected.json")]
    assert {c["model_reported"] for c in grok_calls} == {DISPLAY_REPORTED} and protocol["reviewers"]["grok"]["display_name"] == DISPLAY_FROZEN
    assert sum("label renamed by the provider" in json.dumps(c.get("operator_review")) for c in grok_calls) == DISPLAY_RENAMES == len(grok_calls)
    assert counts == {p: {"calibration": 80, "primary": 115, "repeat": 5, "pairwise": 10, "probe": 115, "match": 115} for p in PANELS}, counts
    assert retries == RETRIES, retries
    assert not (out / "reconstruction").exists()

    # Every solver summary in the sweep folder is a population row: 115, 23 per level, no orphan attempt folder.
    sweep = root / SWEEP
    found = {}
    for p in sorted(sweep.glob("*/legacy-*/summary.json")):
        effort = p.parent.parent.name
        assert effort in EFFORTS, p
        key = (effort, read(p)["task_id"])
        assert key not in found, key
        found[key] = p.parent
    assert len(found) == 115 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    assert not [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    assert {d.name for d in found.values()} == set(record_by_run)
    launcher, log = (root / LAUNCHER).read_text(), (root / SWEEP_LOG).read_text()
    assert "codex-cli 0.166.0" in launcher and "MODEL=gpt-6.2-sol" in launcher
    assert f"({TAG})" in log and log.count("COMPLETE (23/23)") == 5 and "GPT-6.2 SOL CHAIN DONE" in log
    assert all(f"effort={e} attempt 1, 0/23 done" in log and f"effort={e} attempt 2" not in log for e in EFFORTS)
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        key = (run["effort"], run["task"])
        assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
        assert not run.get("fallback") and not entry["fallback"] and run["solver_cli_version"] == CLI_VERSION
        run_dir = found[key]
        assert run_dir.name == run["run_id"] and digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
        solver, facts = solver_facts(run_dir, *key, lock, run["solver_receipt"])
        assert run["duration_s"] == solver["duration_s"] and run["api_equivalent_cost_usd"] == solver["cost_usd"]
        assert (run["functional"], run["quality"], run["security"]) == (solver["scores"]["functional"], solver["scores"]["quality"],
                                                                         solver["scores"]["security"])
        record = record_by_run[run["run_id"]]
        assert {k: v for k, v in record.items() if k != "source_directory"} == {k: v for k, v in run.items() if k in record and k != "source_directory"}
        panels = entry["panels"]
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
        valid = [p for p in PANELS if panels[p]["l1"] is not None]
        assert valid == (["muse"] if entry["id"] in ONE_PANEL else list(PANELS)), entry["id"]
        published = entry["published"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in valid)
        assert all((panels[p]["l2"] is None) == (panels[p]["l2_denominator"] == 0) for p in PANELS), entry["id"]
        intents = [panels[p]["l2"] for p in valid if panels[p]["l2"] is not None]
        assert len(intents) in (0, len(valid)), entry["id"]
        l2 = statistics.mean(intents) if intents else None
        assert published["l2_redistributed"] == (l2 is None) == (len(run["passed_families"]) == 0), entry["id"]
        assert abs(l1 - published["l1"]) < 1e-9 and (l2 is None and published["l2"] is None or abs(l2 - published["l2"]) < 1e-9)
        code_quality = code_quality_of(l1, l2)
        assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        combined_20 = composite(run, code_quality, 0.20)
        assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
        single = {p: composite(run, code_quality_of(panels[p]["l1"]["score"], panels[p]["l2"]), WEIGHTS["code_quality"])
                  if p in valid else None for p in PANELS}
        rows.append({
            "model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"], "finished": True,
            "judged_under": PROTOCOL_ID, "judged": "published", "scored_panels": valid,
            "one_panel_note": ONE_PANEL_NOTE if entry["id"] in ONE_PANEL else None,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": l2 is None, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "combined_single_judge": single,
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} if p in valid else
                       {"readability": None, "maintainability": None, "reviewed_score": None, "intent_recovery": None,
                        "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False,
                        "invalid": "primary review has no valid response (invalidate_unrecoverable_primary); intent probe not counted"}
                       for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"], "started_at": run["started_at"], "finished_at": run["finished_at"],
            "evidence_sha256": run["evidence_sha256"], **facts,
        })
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and {(r["effort"], r["task"]) for r in rows} == set(found)
    assert not any(r["codex_notices"] for r in rows) and all(r["functional"] == 1 for r in rows)
    redistributed = sum(r["intent_recovery_redistributed"] for r in rows)
    assert redistributed == 0

    save("runs.json", {
        "runs": len(rows), "published": 115, "unpublished": 0, "timeouts": 0, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
        "judges": JUDGES,
        "judged_rule": "every run is published: Code quality is the equal mean of both judges, except low granarycore, which is scored "
                       "from Muse Spark 1.3 alone because Grok 4.6's primary review of it has no valid response",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator and its 9 points move to the "
                                f"reviewed score for that submission (intent_recovery_redistributed); {redistributed} GPT-6.2 Sol runs needed it",
        "one_panel_rule": "one_panel_note marks the one run scored from a single judge: Grok 4.6's primary review of low granarycore quoted "
                          "code the submission does not contain on both attempts and was marked invalid under invalidate_unrecoverable_primary "
                          "(owner precedent 2026-09-23); scored_panels lists the judges that count for each run",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run passed",
        "cost_fields": {"estimated_usd": "API-equivalent at the published list rates, stamped by the sweep at run time and recomputed from the "
                                         "Codex receipt with cached input at the cache-read rate"},
        "token_fields": {"raw_tokens": "Codex raw total: input (cached included) plus output",
                         "token_usage.reasoning_output_tokens": "the part of output Codex reports as reasoning"},
        "codex_notice_rule": "codex_notices lists Codex's own warnings in the run's event stream; no GPT-6.2 Sol run printed one",
        "model_identity": "requested-only: Codex does not report the serving model, so identity is the model requested (gpt-6.2-sol)",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "combined_33", "combined_20_profile", "combined_muse_only",
                         "combined_grok_only", "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed",
                         "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "grok_reviewed", "grok_readability", "grok_maintainability", "grok_intent_recovery", "passed_quirk_families",
                         "scored_panels", "codex_notices", "duration_s", "raw_tokens", "cached_input_tokens", "output_tokens",
                         "reasoning_output_tokens", "estimated_usd", "started_at", "finished_at", "solver_cli_version", "task_hash",
                         "evidence_sha256"])
        for r in rows:
            u = r["token_usage"]
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], fmt(r["combined_33"]),
                             fmt(r["combined_20_profile"]), fmt(r["combined_single_judge"]["muse"]), fmt(r["combined_single_judge"]["grok"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]), r["intent_recovery_redistributed"],
                             *[fmt(r["panels"][p][k]) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], "+".join(r["scored_panels"]), "+".join(r["codex_notices"]), r["duration_s"],
                             r["raw_tokens"], u["cached_input_tokens"], u["output_tokens"], u["reasoning_output_tokens"],
                             fmt(r["estimated_usd"], 6), r["started_at"], r["finished_at"], r["solver_cli_version"], r["task_hash"],
                             r["evidence_sha256"]])

    with (results / f"{CARD_STEM}-efforts.csv").open(newline="") as source:
        table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == MODEL}

    def panel_mean(r, key):
        return statistics.mean(r["panels"][p][key] for p in r["scored_panels"])

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(rs), "runs": len(rs), "timeouts": 0, "unpublished_runs": 0,
            "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in rs if r["combined_single_judge"][p] is not None)
                                      for p in PANELS},
            "one_panel_runs": sum(1 for r in rs if r["scored_panels"] != list(PANELS)),
            "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
            "intent_recovery": mean_se(r["intent_recovery"] for r in rs if r["intent_recovery"] is not None),
            "intent_recovery_redistributed_runs": sum(r["intent_recovery_redistributed"] for r in rs),
            "readability": mean_se(panel_mean(r, "readability") for r in rs),
            "maintainability": mean_se(panel_mean(r, "maintainability") for r in rs),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs if p in r["scored_panels"]) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
            "security": mean_se(100 * r["security"] for r in rs),
            "passed": sum(r["functional"] == 1 for r in rs), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "priced_runs": len(rs), "cli_versions": {CLI_VERSION: len(rs)},
            "codex_notice_runs": sum(1 for r in rs if r["codex_notices"]),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "reasoning_output_tokens": mean_se(r["token_usage"]["reasoning_output_tokens"] for r in rs),
            "reasoning_output_tokens_median": statistics.median(r["token_usage"]["reasoning_output_tokens"] for r in rs),
            "cached_input_share": mean_se(r["token_usage"]["cached_input_tokens"] / r["token_usage"]["input_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
        }
        # The round's own summary aggregates this level; it must match exactly.
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"] == 23 and g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert g[field]["n"] == entry[key]["n"], (effort, field)
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        for p in PANELS:
            assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"]
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9 and abs(g["by_panel"][p]["se"] - entry["by_panel"][p]["se"]) < 1e-9
        # The harness card's per-level table carries the same figures.
        t = table[effort]
        assert (int(t["n"]), int(t["judged"]), int(t["passed"]), t["protocol"]) == (g["runs"], g["n"], g["passed_all_runs"], PROTOCOL_ID), effort
        for column, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]),
                              ("code_quality", g["code_quality"]["mean"]), ("minutes", g["minutes"]["mean"]),
                              ("usd_per_task", g["usd"]["mean"])):
            assert abs(float(t[column]) - value) <= 5e-5, (effort, column)
        groups.append(g)
    FINAL_CHECKS(groups)
    best_level = max(groups, key=lambda g: g["combined_33"]["mean"])["effort"]
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "combined_muse_only",
                         "combined_grok_only", "code_quality", "code_quality_se", "reviewed_score", "intent_recovery",
                         "intent_recovery_redistributed_runs", "readability", "maintainability", "muse_reviewed", "grok_reviewed", "functional",
                         "automated_quality", "security", "passed_of_23", "hidden_behaviours_fixed", "hidden_behaviours", "mean_minutes",
                         "mean_minutes_se", "median_minutes", "mean_raw_tokens", "mean_output_tokens", "mean_usd", "total_usd", "cli_version"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}',
                             f'{g["combined_20_profile"]["mean"]:.4f}', f'{g["combined_single_judge"]["muse"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["grok"]["mean"]:.4f}', f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}',
                             f'{g["reviewed_score"]["mean"]:.4f}', f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"],
                             f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}',
                             f'{g["by_panel"]["grok"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}',
                             f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"], g["hidden_behaviours"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["minutes_median"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}',
                             f'{g["output_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd_total"]:.6f}', CLI_VERSION])

    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a ChatGPT subscription through Codex, so these are "
                 "estimates, not bills. Judging and local infrastructure are excluded. Every run in the sweep is priced.",
        "pricing_verified": PRICING_VERIFIED,
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing",
                    "model_page": "https://developers.openai.com/api/docs/models/gpt-6.2-sol"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "output_tokens": g["output_tokens"],
                    "reasoning_output_tokens": g["reasoning_output_tokens"], "cached_input_share": g["cached_input_share"],
                    "minutes": g["minutes"], "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "limitations": [
            "Codex receipts report input, cached input, output and reasoning tokens per run; cached input is billed at the cache-read rate and "
            "the rest of the input at the standard rate. Reasoning tokens are part of output and are not billed twice.",
            "Standard tier, short-context rates; Codex keeps each request within its context window, so no long-context premium is modelled.",
            "No Batch, Flex, Fast or priority pricing is applied.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "The sweep stamped each run at run time at the published GPT-6.2 Sol list rates; the export recomputes every run from its "
            "receipt and matched every stamp.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        result = read(out / f"calibration-{panel}.json")
        assert result["protocol_sha256"] == digest(out / "protocol.json") and result["passed"] and result["call_count"] == 80
        assert len(result["gates"]) == 20
        if panel == "muse":  # the one-gate allowance, as Muse used under v3.23 and v3.29
            assert result["allowance_used"] and result["failing_gates"] == ["g11_repeatability"]
            assert abs(result["gates"]["g11_repeatability"]["shortfall"] - 0.1) < 1e-9
            assert all(g["passed"] for k, g in result["gates"].items() if k != "g11_repeatability")
        else:
            assert not result["allowance_used"] and result["failing_gates"] == [] and all(g["passed"] for g in result["gates"].values())
        calibration[panel] = {"judge": JUDGES[panel], "taken_under": PROTOCOL_ID,
                              **{k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                        "gates", "control_means")}}
    save("calibration.json", calibration)

    # Only Muse's calls carry completed_at; Grok's, through Cursor, record no completion time.
    assert completed[0].startswith("2026-11-19T00:05") and completed[-1].startswith("2026-11-19T07:27"), (completed[0], completed[-1])
    save("judge-protocols.json", {
        "scored_panel": public_reviewers, "judge_names": JUDGES,
        "protocol_id": PROTOCOL_ID, "protocol_sha256": digest(out / "protocol.json"),
        "same_as_v324": "rubric, system text, pair, probe and match instructions, schemas, seed, repeats, gate allowance, weights, retry rule, "
                        "control hashes, both judges' settings, the Muse binary and the Cursor pin equal the published v3.24 record",
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": {k: protocol["population"][k] for k in ("description", "cells", "excluded", "missing")},
        "planned_calls": protocol["planned_calls"],
        "judge_pins": {
            "settings_sources": pins["settings_sources"], "originals_checked_by_this_export": recovered_checked,
            "muse_binary_sha256": muse_binary,
            "cursor_version": {"version": CURSOR_VERSION, "digest": CURSOR_DIGEST, "launcher_sha256": CURSOR_LAUNCHER_SHA,
                               "rule": cursor_pin["rule"], "rechecked_by_this_export": cursor_rechecked,
                               "note": "Grok 4.6 was judged through the versioned launcher of this Cursor CLI for the whole round, the one "
                                       "v3.23 and v3.24 used, with a digest of its version directory re-checked before every stage; Cursor "
                                       "had since updated itself to 2026.11.19-f005e9d"},
        },
        "display_name": {"frozen": DISPLAY_FROZEN, "reported": DISPLAY_REPORTED, "model_id": "cursor-grok-4.6-medium",
                         "accepted_renames_recorded": DISPLAY_RENAMES,
                         "note": "Cursor reports the display name \"Grok 4.6 Medium\" for the pinned model id; the frozen settings say "
                                 "\"Cursor Grok 4.6 Medium\". The wrapper accepts the rename and records it on every selected Grok call."},
        "counted_calls": counts, "second_attempts": retries,
        "unpublished": [],
        "operator_recoveries": [],
        "one_panel": [{"submission": i, "effort": e, "task": t, "invalid_panel": "grok", "stage": "primary", "rule": marker["rule"],
                       "reason": marker["reason"], "effect": marker["effect"], "owner_decision": marker["owner_decision"],
                       "scored_from": "muse", "note": ONE_PANEL_NOTE,
                       "reviewed_score": next(r["reviewed_score"] for r in rows if (r["effort"], r["task"]) == (e, t)),
                       "code_quality": next(r["code_quality"] for r in rows if (r["effort"], r["task"]) == (e, t))}
                      for i, (e, t) in ONE_PANEL.items()],
        "quota_stops": {"panel": QUOTA_CALL[0], "stage": QUOTA_CALL[1], "call": QUOTA_CALL[2], "archived_attempts": len(quota_notes),
                        "cause": "Cursor usage limit: the signed-in Cursor account was on the free plan",
                        "resolution": "the owner signed in to the paid account and the same call resumed under the quota rule (identical "
                                      "inputs, archived attempts kept in quota-stops); no answer was discarded"},
        "judging_window_utc": {"chain": "2026-11-19T00:04Z to 2026-11-19T13:39Z, from the operator's chain log",
                               "first_muse_call_completed": completed[0], "last_muse_call_completed": completed[-1],
                               "note": "Muse Spark 1.3's calls record a completion time; Grok 4.6's, through Cursor, do not",
                               "summary_generated": summary["generated_at"]},
    })

    # The card is copied byte for byte from the harness.
    for name, target in CARDS.items():
        assert target.read_bytes() == (results / name).read_bytes(), name
    card = read(results / f"{CARD_STEM}.json")
    assert card["final"] and card["png_sha256"] == digest(results / f"{CARD_STEM}.png") and card["best"][MODEL] == best_level
    assert card["sources"]["v3.31_summary_sha256"] == digest(out / "summary.json")
    # The comparators on the card are published board rows; they must equal this site's board as rebuilt.
    with (SITE / "assets/data/swe-v4-board.csv").open(newline="") as handle:
        board = {(r["model"], r["effort"]): r for r in csv.DictReader(handle)}
    with (results / f"{CARD_STEM}-efforts.csv").open(newline="") as handle:
        compared = [r for r in csv.DictReader(handle) if r["model"] != MODEL]
    assert {r["model"] for r in compared} == set(card["comparators"]) and len(compared) == 5 * len(card["comparators"])
    for r in compared:
        b = board[card["comparators"][r["model"]], r["effort"]]
        assert (int(r["judged"]), int(r["n"])) == (int(b["n"]), int(b["passed_of"])), (r["model"], r["effort"])
        for column, source in (("combined", "combined_33"), ("combined_se", "combined_33_se"), ("code_quality", "code_quality"),
                               ("usd_per_task", "mean_usd"), ("minutes", "mean_minutes")):
            assert abs(float(r[column]) - float(b[source])) <= 5e-5, (r["model"], r["effort"], column)

    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.31/{f}": digest(out / f) for f in ("summary.json", "protocol.json", "private-manifest.json", "calibration-muse.json",
                                                       "calibration-grok.json")},
            f"v3.31/calls/grok/primary/submission-069/{INVALID_MARKER}": digest(out / "calls/grok/primary/submission-069" / INVALID_MARKER),
            **{name: digest(results / name) for name in ("comparison.json", f"{CARD_STEM}-efforts.csv", f"{CARD_STEM}.json",
                                                         f"{CARD_STEM}.png")},
            "suite.lock.json": digest(root / LOCK),
            "run_gpt62_sol_v4.sh": digest(root / LAUNCHER),
        },
        "export_checks": ["115 solver summaries in the sweep folder, 23 per level, no task twice and no orphan attempt folder; the sweep "
                          "log shows each level complete on its first attempt",
                          "every run is codex:gpt-6.2-sol at its requested level (Extra high as xhigh) on Codex CLI 0.166.0 with the "
                          "workspace-write sandbox, from bench/2026-11-17-gpt62-sol-frontier-v4 with a clean source block and every task "
                          "hash equal to the frozen suite lock",
                          "every integrity audit: no web, no benchmark data or answer-key paths, not contaminated",
                          "each run's token totals equal its Codex receipt, whose stream hash equals the archived stream; every run's "
                          "API-equivalent cost recomputed at the published list rates and matched to the sweep's run-time stamp",
                          "no run printed a Codex notice, and every run passed every hidden test",
                          "the population record's hash and the manifest's hash equal the ones frozen in the protocol, and every run's "
                          "summary hash equals its manifest entry",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control hashes, both judges' settings "
                          "and the Muse binary equal the published v3.24 record; the settings equal the recovered v3.3 and v3.4 protocols, "
                          "whose hashes match the published values; the Cursor pin names version 2026.10.01-e373342 and its frozen "
                          "directory digest, recomputed on this host when present",
                          "both judges passed calibration under v3.31 (Muse Spark 1.3 with the one-gate allowance on g11, Grok 4.6 on every "
                          "gate); no reviewer fallback; every selected Grok call records the accepted display rename",
                          "the one live operator marker is Grok's primary review of low granarycore (invalidate_unrecoverable_primary), "
                          "and that row's published scores are reproduced from Muse alone; no recovery and no superseded marker; the one "
                          "quota-stopped call (Grok calibration) resumed with its archived attempts kept",
                          "per-row Code quality, both combined scores and each judge's single-judge score recomputed and matched to the "
                          "frozen summary, with intent recovery redistributed where no quirk family passed; each level's means and standard "
                          "errors, per-judge means included, matched to the summary's groups",
                          "combined score, its standard error, Code quality, tasks passed, minutes and cost per level matched to the harness "
                          "card table; the card is byte-identical to the harness copy and its record names this summary and the comparator "
                          "tables",
                          "no dashes, NUL characters or host paths in exported text"],
        "limits": ["Low granarycore is scored from Muse Spark 1.3 alone: Grok 4.6's primary review has no valid response (both attempts "
                   "quoted code the submission does not contain), so the summary uses Muse's reviewed score and intent recovery for that "
                   "run, as the frozen protocol does for any submission without two valid reviews. Every other run is the equal mean of "
                   "both judges.",
                   "Muse Spark 1.3 passed calibration with the one-gate allowance: repeatability (g11) fell 0.1 short, within the "
                   "half-point the protocol allows for one gate.",
                   "Grok 4.6's calibration stopped on a Cursor usage limit (the signed-in account was on the free plan) and resumed on the "
                   "same call after the owner signed in to the paid account; the stopped attempts are archived, not counted.",
                   "The ChatGPT login reported plan prolite; earlier GPT columns ran on ChatGPT Pro. The plan sets usage limits, not the "
                   "model served.",
                   "Model identity is requested-only: Codex does not report the serving model.",
                   "The sweep ran on release day and the day after, through Codex CLI 0.166.0 pinned by version; it cannot pin what OpenAI serves "
                   "under the model id.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound, one task at a time."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "solver event streams", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


# The summary's figures as the report prints them: combined, its standard error, Code quality, tasks passed,
# runs with intent recovery redistributed and runs scored from one judge, per level.
PUBLISHED = {"low": (88.44, 0.35, 70.31, 23, 0, 1), "medium": (88.94, 0.47, 71.78, 23, 0, 0), "high": (88.86, 0.33, 71.43, 23, 0, 0),
             "extra-high": (89.01, 0.43, 71.91, 23, 0, 0), "max": (88.74, 0.40, 71.06, 23, 0, 0)}


def FINAL_CHECKS(groups):  # noqa: N802
    assert [g["effort"] for g in groups] == list(EFFORTS)
    for g in groups:
        combined, se, code_quality, passed, redistributed, one_panel = PUBLISHED[g["effort"]]
        assert (round(g["combined_33"]["mean"], 2), round(g["combined_33"]["se"], 2), round(g["code_quality"]["mean"], 2)) == (
            combined, se, code_quality), g["effort"]
        assert (g["passed_all_runs"], g["intent_recovery_redistributed_runs"], g["one_panel_runs"], g["codex_notice_runs"]) == (
            passed, redistributed, one_panel, 0)
    assert round(sum(g["usd_total"] for g in groups), 2) == 45.38


if __name__ == "__main__":
    main()
