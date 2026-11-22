"""Export the public record of the Gemini 4 Neon effort sweep on Frontier v4, judged under v3.32.

Adapted from the v3.31 GPT-6.2 Sol export (the same panel, Muse Spark 1.3 and
Grok 4.6, on the same Cursor pin) with the v3.17 GPT-6 Sol export's handling of
a row the frozen summary leaves unpublished. Same publication scope: per-run
scores, per-panel sub-scores, aggregates, judge protocol text, calibration
verdicts, raw tokens and API-equivalent cost. Raw prompts, patches, quirk answer
keys, thinking text and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v332_evidence.py --harness-root ../VulcanBench-neon \\
        --sweep-root ../VulcanBench \\
        --judging ../VulcanBench-runs/<v3.32 run worktree>/runs-code-quality-maintenance-v3.32

--harness-root holds the sweep (runs-effort-gemini4-neon-agy), the population
record and card in docs/results/swe-v4-gemini4-neon-2026-11 and the suite lock.
--sweep-root holds the operator's sweep launcher and log (logs/neon-agy.*).
--judging is the v3.32 round directory, which lives in its run worktree.

What differs from the GPT-6.2 Sol export, all forced by the sweep or its judging:

- A new harness: Antigravity CLI 1.5.12 on the owner's Google AI Pro sign-in,
  with a custom main agent limited to the default file and shell tools
  (read_file, write_file, edit_file, run_command), so the web search tool the
  default agent carries is absent. Antigravity reports the serving model.
- Four levels, Low to Extra high: Antigravity offers Neon at no Max level.
  Extra high is the provider's xhigh slug.
- Antigravity's output tokens include thinking; the reasoning share is
  reported beside them and not billed twice.
- Low passed 17 of 23 tasks; every other level passed all 23.
- Two unpublished rows, Low and Extra high codeccore (submissions 048 and 069):
  Grok 4.6's intent probe returned malformed JSON on both attempts, the wrapper
  rule invalidate_unrecoverable_probe (harness PR #328) marked each call
  invalid, and the frozen summary leaves such a submission unpublished (owner
  choice in chat, 2026-11-21, as v3.7 and v3.17 did on the same codeccore
  line). Both runs passed their tests and are timed and priced.
- 40 attempts refused by the AI Pro quota were classified infrastructure and
  rerun fresh; their folders sit in the sweep's infra-aborted folder and are
  not population rows. The first launch (one Low run) was voided for a shell
  heredoc fault in the sandbox, fixed and relaunched from the 2026-11-20 tag.
- Muse Spark 1.3 passed calibration with the one-gate allowance (g11
  repeatability, 0.02 short); Grok 4.6 passed every gate. No quota stop.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-gemini4-neon-v332"
SCORES = SITE / "assets/data/swe-v4-gemini4-neon-v332-scores.csv"
CARD_STEM = "gemini4neon-vs-frontier"
CARDS = {f"{CARD_STEM}.png": SITE / "assets/cards/swe-v4-gemini4-neon-v332.png"}
COMPARATORS = {"opus55": "Opus 5.5", "gpt62sol": "GPT-6.2 Sol"}  # card key to published board model name
EFFORTS = ("low", "medium", "high", "extra-high")
PROVIDER_EFFORT = {"low": "low", "medium": "medium", "high": "high", "extra-high": "xhigh"}
MODEL = "neon"
NAMES = {MODEL: "Gemini 4 Neon"}
SOLVER = "agy:gemini-4-neon"
API_MODEL = "gemini-4-neon"
PANELS = ("muse", "grok")
JUDGES = {"muse": "Muse Spark 1.3", "grok": "Grok 4.6"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
# Google's Gemini API pricing, checked 2026-11-19: standard tier.
RATES_PER_MILLION = {MODEL: {"input": 3.00, "cached_input": 0.15, "output": 15.00}}
PRICING_VERIFIED = "2026-11-19"
PROTOCOL_ID = "code-quality-maintenance-v3.32"
RESULTS = "docs/results/swe-v4-gemini4-neon-2026-11"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEP = "runs-effort-gemini4-neon-agy"
LAUNCHER = "logs/neon-agy.launch.sh"
SWEEP_LOG = "logs/neon-agy.log"
TAG, COMMIT = "bench/2026-11-20-gemini4-neon-frontier-v4", "7f3b2c4cd21eccb9529d3cd4ab66bb242cf292fc"
JUDGING_TAG, RECOVERY_TAG = "bench/2026-11-21-gemini4-neon-judging-v332", "bench/2026-11-21-gemini4-neon-judging-v332-recovery"
CLI_VERSION = "1.5.12"
AGY_PIN = "ef265356c3e5d3c6c241509cf71187bae086ac935ef5c5c037dadf62d5876835"
TOOLS = ("read_file", "write_file", "edit_file", "run_command")
QUOTA_REFUSED = {"medium": 10, "high": 8, "extra-high": 22}  # attempts the AI Pro quota refused, rerun fresh
V324_PROTOCOLS = SITE / "assets/data/swe-v4-haiku55-v324/judge-protocols.json"
ORIGINAL_PROTOCOLS = {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                      "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"}
CURSOR_VERSION = "2026.10.01-e373342"
CURSOR_DIGEST = "dedbb877a8405b20e38a3dc32f38bf614bcd96d6e557f73eb6e99ff8c87b8a73"
CURSOR_LAUNCHER_SHA = "2ccc9a8e167797641448b5e5c936f006ba137a2555f117f38c5eb76a5238a233"
CURSOR_VERSIONS_DIR = Path.home() / ".local/share/cursor-agent/versions"
DISPLAY_FROZEN, DISPLAY_REPORTED = "Cursor Grok 4.6 Medium", "Grok 4.6 Medium"
DISPLAY_RENAMES = 364  # selected Grok calls whose operator_review records the accepted rename
RETRIES = {"muse": 2, "grok": 7}  # calls with a second attempt under the frozen single-retry rule
INVALID_MARKER = "operator-invalid.json"
SUPERSEDED_MARKER = "operator-invalid.superseded.json"
UNPUBLISHED = {"submission-048": ("low", "legacy-codeccore-binary-parity"),
               "submission-069": ("extra-high", "legacy-codeccore-binary-parity")}
UNPUBLISHED_NOTE = ("unpublished: Grok 4.6's intent probe returned malformed JSON on both attempts (it quoted the codeccore memo line "
                    "with its double quotes unescaped), invalidate_unrecoverable_probe marked the call invalid, and the frozen v3.32 "
                    "summary publishes no Code quality score for a submission whose probe is invalid")
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
    """The API-equivalent cost of one Antigravity receipt at the published list rates, cached input at the cache-read rate."""
    rate = RATES_PER_MILLION[MODEL]
    cached = min(usage["cached_input_tokens"], usage["input_tokens"])
    return ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6


def tool_calls(run_dir):
    """The run's archived tool calls: every one must be an allowlisted file or shell tool."""
    calls = [json.loads(line) for line in (run_dir / "tool-calls.jsonl").read_text().splitlines() if line.strip()]
    names = Counter(c["tool"] for c in calls)
    assert set(names) <= set(TOOLS), (run_dir.name, names)
    return calls, names


def solver_facts(run_dir, effort, task, lock, receipt):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    provider = PROVIDER_EFFORT[effort]
    assert solver["model"] == SOLVER and solver["task_id"] == task, run_dir.name
    assert solver["effort"]["requested"] == effort and solver["effort"]["provider_value"] == provider, run_dir.name
    agent = solver["cli_agent"]
    assert (agent["harness"], agent["harness_version"], agent["billing"]) == ("agy", CLI_VERSION, "subscription"), run_dir.name
    assert agent["requested_model"] == agent["reported_model"] == API_MODEL and agent["model_identity_confidence"] == "harness-recorded"
    assert agent["plan_name"] == "Google AI Pro" and agent["auth_method"] == "google-oauth" and agent["served_model_switches"] == 0
    assert agent["subtype"] == "completed" and agent["execution_boundary"].startswith("macOS outer sandbox"), run_dir.name
    assert "web search absent" in agent["execution_boundary"] and "URL, browser and MCP denied" in agent["execution_boundary"]
    source = solver["source"]  # tagged run worktree, clean: no hash bridge needed
    assert source["harness"]["describe"] == TAG and source["harness"]["commit"] == COMMIT, run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_hash"] == lock[task], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"] and not audit["web"].get("contaminated"), run_dir.name
    assert audit["web"]["web_searches"] == audit["web"]["web_fetches"] == 0, run_dir.name
    assert audit["filesystem"]["benchmark_data_paths"] == [] and audit["filesystem"]["answer_key_paths"] == [], run_dir.name
    assert solver["finished"] is True and solver["duration_s"] < 10800 and not solver["scores"].get("budget_exceeded"), run_dir.name
    tokens, usage = solver["tokens"], receipt["usage"]
    assert (tokens["prompt"], tokens["cached_input"], tokens["completion"], tokens["reasoning_output"]) == (
        usage["input_tokens"], usage["cached_input_tokens"], usage["output_tokens"], usage["reasoning_output_tokens"]), run_dir.name
    assert solver["total_tokens"] == tokens["total"] == usage["input_tokens"] + usage["output_tokens"] == receipt["raw_tokens"]
    assert digest(run_dir / "cli-agent-stream.jsonl") == receipt["stream_sha256"], run_dir.name
    # The sweep stamped each run's cost at run time from the same receipt and rates; recompute it.
    cost = priced(usage)
    assert abs(cost - solver["cost_usd"]) < 1e-5 and solver["economics"]["api_equivalent_cost_usd"] == solver["cost_usd"], run_dir.name
    assert solver["economics"]["cli_reported_cost_usd"] is None and solver["cost_detail"]["cache_pricing_applied"], run_dir.name
    calls, names = tool_calls(run_dir)
    assert solver["tool_calls"]["count"] == len(calls) and solver["tool_calls"]["by_tool"] == dict(names), run_dir.name
    hidden = solver["verifier"]["fail_to_pass"]
    return solver, {
        "solver_cli_version": CLI_VERSION, "source_tag": TAG, "task_hash": solver["task_hash"],
        "requested_model": API_MODEL, "reported_model": API_MODEL, "requested_effort": provider, "model_identity": "harness-recorded",
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "tool_calls": len(calls), "tool_calls_by_tool": {t: names.get(t, 0) for t in TOOLS},
        "tool_call_errors": solver["tool_calls"]["errors"], "turns": agent["num_turns"],
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
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench-neon")
    parser.add_argument("--sweep-root", type=Path, default=SITE.parent / "VulcanBench")
    parser.add_argument("--judging", type=Path, required=True, help="the runs-code-quality-maintenance-v3.32 directory")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    sweep_root = args.sweep_root.resolve()
    out = args.judging.resolve()
    lock = read(root / LOCK)["tasks"]
    results = root / RESULTS
    summary, protocol = read(out / "summary.json"), read(out / "protocol.json")
    manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
    comparison_path = results / "comparison.json"
    comparison = read(comparison_path)

    # The round: one protocol, both judges passing, 90 of 92 published, every binding hash intact.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["expected_submissions"] == len(manifest) == len(summary["rows"]) == 92 and summary["published_submissions"] == 90
    assert summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
    assert not summary["human_calibrated"] and not summary["humans_involved"]
    assert protocol["source_comparison_sha256"] == digest(comparison_path)
    assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
    assert protocol["scored_siblings"] == {} and protocol["sensitivity_panels"] == {}
    assert comparison["cells"] == protocol["population"]["cells"] == {f"{MODEL}/{e}": 23 for e in EFFORTS}
    assert comparison["excluded"] == comparison["missing"] == protocol["population"]["excluded"] == protocol["population"]["missing"] == []
    assert comparison["levels"] == {MODEL: list(EFFORTS)} and len(comparison["rows"]) == 92
    record_by_run = {r["run_id"]: r for r in comparison["rows"]}
    # The summary is not marked ready only because of its strict count: exactly two rows are unpublished, and they are the
    # two whose Grok probe folders carry the operator-invalid marker.
    unpublished = {r["id"] for r in summary["rows"] if not r.get("published")}
    assert unpublished == set(UNPUBLISHED) and not summary["ready_for_publication"], unpublished
    assert summary["published_submissions"] + len(unpublished) == summary["expected_submissions"]
    assert {i: (manifest[i]["effort"], manifest[i]["task"]) for i in UNPUBLISHED} == UNPUBLISHED

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

    # Operator records: two live markers, Grok's probes of submissions 048 and 069; no recovery and no superseded marker.
    invalid, superseded, recoveries, counts, retries, completed = call_records(out)
    assert set(invalid) == {("grok", "probe", i) for i in UNPUBLISHED} and superseded == {} and recoveries == {}, (invalid, superseded, recoveries)
    for i in UNPUBLISHED:
        marker = invalid["grok", "probe", i]
        assert marker["finding"] == "No valid probe response: neither attempt was valid JSON.", i
        assert set(marker["malformed_attempts"]) == {"1", "2"} and marker["unsupported_excerpts"] == {}, i
        assert all(e.startswith("Expecting ',' delimiter") for e in marker["malformed_attempts"].values()), i
        assert "no match call is made" in marker["action"] and not (out / f"calls/grok/match/{i}").exists(), i
    assert [d for d in (out / "calls").glob("*/*/*/quota-stops")] == []
    grok_calls = [read(q) for q in (out / "calls/grok").glob("*/*/selected.json")]
    assert {c["model_reported"] for c in grok_calls} == {DISPLAY_REPORTED} and protocol["reviewers"]["grok"]["display_name"] == DISPLAY_FROZEN
    assert sum("label renamed by the provider" in json.dumps(c.get("operator_review")) for c in grok_calls) == DISPLAY_RENAMES == len(grok_calls)
    expected_counts = {p: {"calibration": 80, "primary": 92, "repeat": 4, "pairwise": 8, "probe": 92, "match": 92} for p in PANELS}
    expected_counts["grok"]["match"] = 90  # no match call follows an invalid probe
    assert counts == expected_counts, counts
    assert retries == RETRIES, retries
    assert not (out / "reconstruction").exists()

    # Every solver summary in the sweep's level folders is a population row: 92, 23 per level, no orphan attempt folder.
    sweep = root / SWEEP
    found = {}
    for effort in EFFORTS:
        for p in sorted((sweep / effort).glob("legacy-*/summary.json")):
            key = (effort, read(p)["task_id"])
            assert key not in found, key
            found[key] = p.parent
    assert len(found) == 92 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    assert not [p for e in EFFORTS for p in (sweep / e).glob("legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    assert {d.name for d in found.values()} == set(record_by_run)
    # Quota-refused attempts moved aside before the population was built; none left a solver summary.
    refused = {e: [p for p in (sweep / "infra-aborted" / e).glob("legacy-*") if p.is_dir()] for e in QUOTA_REFUSED}
    assert {e: len(v) for e, v in refused.items()} == QUOTA_REFUSED and not any((p / "summary.json").exists() for v in refused.values() for p in v)
    assert not (sweep / "infra-aborted" / "low").exists()
    voided = list((sweep / "void-heredoc-2026-11-19" / "low").glob("legacy-*"))
    assert len(voided) == 1 and voided[0].name.startswith("legacy-settlecore-binary-parity")
    launcher, log = (sweep_root / LAUNCHER).read_text(), (sweep_root / SWEEP_LOG).read_text()
    assert f"PIN={AGY_PIN}" in launcher and "agy-1.5.12/agy" in launcher and "MODEL=agy:gemini-4-neon" in launcher
    assert f"at {TAG}" in log and all(f"effort={e} COMPLETE (23/23)" in log for e in EFFORTS) and "NEON SWEEP FINISHED" in log
    assert "RELAUNCH 2026-11-20 05:50:02: tag bench/2026-11-20-gemini4-neon-frontier-v4" in log
    quota_waits = {e: log.count(f"effort={e} AI Pro quota exhausted") for e in EFFORTS}
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
        assert all(panels[p]["l1"] is not None for p in PANELS) and not any(panels[p]["reviewer_fallback"] for p in PANELS), entry["id"]
        if entry["id"] in UNPUBLISHED:
            assert panels["grok"]["l2"] is None and panels["grok"]["l2_denominator"] > 0 and panels["muse"]["l2"] is not None, entry["id"]
            assert entry.get("published") is None and run["functional"] == 1, entry["id"]
            l1 = l2 = code_quality = combined_33 = combined_20 = redistributed = None
            single = {p: None for p in PANELS}
            panel_record = None
            judged = UNPUBLISHED_NOTE
        else:
            assert all((panels[p]["l2"] is None) == (panels[p]["l2_denominator"] == 0) for p in PANELS), entry["id"]
            published = entry["published"]
            l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
            intents = [panels[p]["l2"] for p in PANELS if panels[p]["l2"] is not None]
            assert len(intents) in (0, 2), entry["id"]
            l2 = statistics.mean(intents) if intents else None
            redistributed = l2 is None
            assert published["l2_redistributed"] == redistributed == (len(run["passed_families"]) == 0), entry["id"]
            assert abs(l1 - published["l1"]) < 1e-9 and (l2 is None and published["l2"] is None or abs(l2 - published["l2"]) < 1e-9)
            code_quality = code_quality_of(l1, l2)
            assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
            combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
            combined_20 = composite(run, code_quality, 0.20)
            assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
            single = {p: composite(run, code_quality_of(panels[p]["l1"]["score"], panels[p]["l2"]), WEIGHTS["code_quality"]) for p in PANELS}
            panel_record = {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                                "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                                "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} for p in PANELS}
            judged = "published"
        rows.append({
            "model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"], "finished": True,
            "judged_under": PROTOCOL_ID, "judged": judged,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "combined_single_judge": single,
            "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"], "started_at": run["started_at"], "finished_at": run["finished_at"],
            "evidence_sha256": run["evidence_sha256"], **facts,
        })
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 92 and {(r["effort"], r["task"]) for r in rows} == set(found)
    assert sum(r["judged"] != "published" for r in rows) == 2
    redistributed_total = sum(bool(r["intent_recovery_redistributed"]) for r in rows)

    save("runs.json", {
        "runs": len(rows), "published": 90, "unpublished": 2, "timeouts": 0, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
        "judges": JUDGES,
        "judged_rule": "judged is \"published\" where the v3.32 summary publishes a Code quality score: the equal mean of both judges. "
                       "The two other rows, Low and Extra high codeccore, carry the reason their judge-derived fields are null",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator and its 9 points move to the "
                                f"reviewed score for that submission (intent_recovery_redistributed); {redistributed_total} Gemini 4 Neon "
                                "runs needed it",
        "unpublished_rule": "Grok 4.6's intent probe of Low and Extra high codeccore returned malformed JSON on both attempts; the wrapper "
                            "rule invalidate_unrecoverable_probe marked each call invalid, and the frozen summary publishes no Code quality "
                            "score for a submission whose probe is invalid (owner choice, 2026-11-21, as v3.7 and v3.17 did). Both runs "
                            "passed their tests and are timed and priced",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run passed",
        "cost_fields": {"estimated_usd": "API-equivalent at the published list rates, stamped by the sweep at run time and recomputed from the "
                                         "Antigravity receipt with cached input at the cache-read rate"},
        "token_fields": {"raw_tokens": "Antigravity raw total: input (cached included) plus output",
                         "token_usage.output_tokens": "includes thinking; Antigravity bills thinking as output",
                         "token_usage.reasoning_output_tokens": "the part of output Antigravity reports as thinking"},
        "tool_call_fields": {"tool_calls": "tool calls in the run's archived tool-call log; every one is read_file, write_file, edit_file "
                                           "or run_command, the custom agent's allowlist",
                             "tool_call_errors": "tool calls that returned an error"},
        "model_identity": "harness-recorded: Antigravity reports the model it served (gemini-4-neon) on every run",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile", "combined_muse_only",
                         "combined_grok_only", "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed",
                         "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "grok_reviewed", "grok_readability", "grok_maintainability", "grok_intent_recovery", "passed_quirk_families",
                         "tool_calls", "tool_call_errors", "duration_s", "raw_tokens", "cached_input_tokens", "output_tokens",
                         "reasoning_output_tokens", "estimated_usd", "started_at", "finished_at", "solver_cli_version", "task_hash",
                         "evidence_sha256"])
        for r in rows:
            u = r["token_usage"]
            panels = r["panels"] or {p: {} for p in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"],
                             "published" if r["judged"] == "published" else "unpublished", fmt(r["combined_33"]),
                             fmt(r["combined_20_profile"]), fmt(r["combined_single_judge"]["muse"]), fmt(r["combined_single_judge"]["grok"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]), "" if r["intent_recovery_redistributed"] is None else r["intent_recovery_redistributed"],
                             *[fmt(panels[p].get(k)) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["tool_calls"], r["tool_call_errors"], r["duration_s"],
                             r["raw_tokens"], u["cached_input_tokens"], u["output_tokens"], u["reasoning_output_tokens"],
                             fmt(r["estimated_usd"], 6), r["started_at"], r["finished_at"], r["solver_cli_version"], r["task_hash"],
                             r["evidence_sha256"]])

    with (results / f"{CARD_STEM}-efforts.csv").open(newline="") as source:
        table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == MODEL}

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        assert len(rs) == 23
        judged = [r for r in rs if r["judged"] == "published"]
        g = {
            "model": MODEL, "effort": effort, "n": len(judged), "runs": len(rs), "timeouts": 0, "unpublished_runs": len(rs) - len(judged),
            "combined_33": mean_se(r["combined_33"] for r in judged), "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in judged) for p in PANELS},
            "one_panel_runs": 0,
            "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
            "intent_recovery": mean_se(r["intent_recovery"] for r in judged if r["intent_recovery"] is not None),
            "intent_recovery_redistributed_runs": sum(r["intent_recovery_redistributed"] for r in judged),
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in judged), "automated_quality": mean_se(100 * r["automated_quality"] for r in judged),
            "security": mean_se(100 * r["security"] for r in judged),
            # passed counts judged runs; passed_all_runs counts all 23 and is the one to read (both unpublished runs passed).
            "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            # Runtime, tokens, tool calls and cost are facts of the sweep and cover every run in the cell, judged or not.
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "minutes_judged_runs": mean_se(r["duration_s"] / 60 for r in judged),
            "priced_runs": len(rs), "cli_versions": {CLI_VERSION: len(rs)},
            "tool_calls": mean_se(r["tool_calls"] for r in rs), "tool_call_errors_total": sum(r["tool_call_errors"] for r in rs),
            "quota_refused_attempts": QUOTA_REFUSED.get(effort, 0), "quota_waits": quota_waits[effort],
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "reasoning_output_tokens": mean_se(r["token_usage"]["reasoning_output_tokens"] for r in rs),
            "reasoning_output_tokens_median": statistics.median(r["token_usage"]["reasoning_output_tokens"] for r in rs),
            "cached_input_share": mean_se(r["token_usage"]["cached_input_tokens"] / r["token_usage"]["input_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
        }
        # The round's own summary aggregates this level; it must match exactly.
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"] and g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert g[field]["n"] == entry[key]["n"], (effort, field)
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        for p in PANELS:
            assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"]
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9 and abs(g["by_panel"][p]["se"] - entry["by_panel"][p]["se"]) < 1e-9
        # The harness card's per-level table carries the same figures; it times and prices every run.
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
                         "mean_minutes_se", "median_minutes", "mean_tool_calls", "mean_raw_tokens", "mean_output_tokens", "mean_usd", "total_usd",
                         "cli_version"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}',
                             f'{g["combined_20_profile"]["mean"]:.4f}', f'{g["combined_single_judge"]["muse"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["grok"]["mean"]:.4f}', f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}',
                             f'{g["reviewed_score"]["mean"]:.4f}', f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"],
                             f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}',
                             f'{g["by_panel"]["grok"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}',
                             f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"], g["hidden_behaviours"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["minutes_median"]:.4f}', f'{g["tool_calls"]["mean"]:.2f}',
                             f'{g["raw_tokens"]["mean"]:.1f}', f'{g["output_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd_total"]:.6f}',
                             CLI_VERSION])

    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a Google AI Pro subscription through Antigravity, "
                 "so these are estimates, not bills. Judging, quota-refused attempts and local infrastructure are excluded. Every run in "
                 "the population is priced.",
        "pricing_verified": PRICING_VERIFIED,
        "sources": {"google": "https://ai.google.dev/gemini-api/docs/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "output_tokens": g["output_tokens"],
                    "reasoning_output_tokens": g["reasoning_output_tokens"], "cached_input_share": g["cached_input_share"],
                    "minutes": g["minutes"], "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "limitations": [
            "Antigravity receipts report input, cached input, output and thinking tokens per run; cached input is billed at the cache-read "
            "rate and the rest of the input at the standard rate. Thinking tokens are part of output and are not billed twice.",
            "Standard tier rates; no long-context premium is modelled.",
            "No Batch or priority pricing is applied.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "The sweep stamped each run at run time at the published Gemini 4 Neon list rates; the export recomputes every run from its "
            "receipt and matched every stamp.",
            "40 attempts refused by the AI Pro quota (4 of them at Extra high cut mid-task) are not priced: they are not population rows "
            "and each was rerun from scratch.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        result = read(out / f"calibration-{panel}.json")
        assert result["protocol_sha256"] == digest(out / "protocol.json") and result["passed"] and result["call_count"] == 80
        assert len(result["gates"]) == 20
        if panel == "muse":  # the one-gate allowance, as Muse used under v3.23, v3.29 and v3.31
            assert result["allowance_used"] and result["failing_gates"] == ["g11_repeatability"]
            assert abs(result["gates"]["g11_repeatability"]["shortfall"] - 0.02) < 1e-9
            assert all(g["passed"] for k, g in result["gates"].items() if k != "g11_repeatability")
        else:
            assert not result["allowance_used"] and result["failing_gates"] == [] and all(g["passed"] for g in result["gates"].values())
        calibration[panel] = {"judge": JUDGES[panel], "taken_under": PROTOCOL_ID,
                              **{k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                        "gates", "control_means")}}
    save("calibration.json", calibration)

    # Only Muse's calls carry completed_at; Grok's, through Cursor, record no completion time.
    assert completed[0].startswith("2026-11-21T14:58") and completed[-1].startswith("2026-11-21T18:24"), (completed[0], completed[-1])
    unpublished_rows = {(r["effort"], r["task"]): r for r in rows if r["judged"] != "published"}
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
        "unpublished": [{"submission": i, "effort": e, "task": t, "panel": "grok", "stage": "probe",
                         "rule": "invalidate_unrecoverable_probe (two replies that are not valid JSON; harness PR #328)",
                         "finding": invalid["grok", "probe", i]["finding"], "malformed_attempts": invalid["grok", "probe", i]["malformed_attempts"],
                         "action": invalid["grok", "probe", i]["action"],
                         "owner_decision": "2026-11-21, in chat: leave unpublished under the frozen rule, as v3.7 and v3.17 did on the same line",
                         "note": UNPUBLISHED_NOTE, "functional": unpublished_rows[e, t]["functional"],
                         "estimated_usd": unpublished_rows[e, t]["estimated_usd"], "duration_s": unpublished_rows[e, t]["duration_s"]}
                        for i, (e, t) in UNPUBLISHED.items()],
        "operator_recoveries": [],
        "one_panel": [],
        "quota_stops": [],
        "judging_window_utc": {"chain": "2026-11-21T14:58Z to 2026-11-21T21:19Z, stopped by Grok's probe of submission-048, from the "
                                        f"operator's chain log, at {JUDGING_TAG}",
                               "recovery": "2026-11-22T02:19Z to 2026-11-22T03:31Z, the Grok probe stage resumed with the extended "
                                           f"invalidate_unrecoverable_probe, at {RECOVERY_TAG}",
                               "first_muse_call_completed": completed[0], "last_muse_call_completed": completed[-1],
                               "note": "Muse Spark 1.3's calls record a completion time; Grok 4.6's, through Cursor, do not",
                               "summary_generated": summary["generated_at"]},
    })

    # The card is copied byte for byte from the harness.
    for name, target in CARDS.items():
        assert target.read_bytes() == (results / name).read_bytes(), name
    card = read(results / f"{CARD_STEM}.json")
    assert card["final"] and card["png_sha256"] == digest(results / f"{CARD_STEM}.png") and card["best"][MODEL] == best_level
    assert card["sources"]["v3.32_summary_sha256"] == digest(out / "summary.json")
    # The comparators on the card are published board rows; they must equal this site's board as rebuilt.
    with (SITE / "assets/data/swe-v4-board.csv").open(newline="") as handle:
        board = {(r["model"], r["effort"]): r for r in csv.DictReader(handle)}
    with (results / f"{CARD_STEM}-efforts.csv").open(newline="") as handle:
        compared = [r for r in csv.DictReader(handle) if r["model"] != MODEL]
    assert {r["model"] for r in compared} == set(COMPARATORS) and len(compared) == 5 * len(COMPARATORS)
    for r in compared:
        b = board[COMPARATORS[r["model"]], r["effort"]]
        assert (int(r["judged"]), int(r["n"])) == (int(b["n"]), int(b["passed_of"])), (r["model"], r["effort"])
        for column, source in (("combined", "combined_33"), ("combined_se", "combined_33_se"), ("code_quality", "code_quality"),
                               ("usd_per_task", "mean_usd"), ("minutes", "mean_minutes")):
            assert abs(float(r[column]) - float(b[source])) <= 5e-5, (r["model"], r["effort"], column)

    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.32/{f}": digest(out / f) for f in ("summary.json", "protocol.json", "private-manifest.json", "calibration-muse.json",
                                                       "calibration-grok.json")},
            **{f"v3.32/calls/grok/probe/{i}/{INVALID_MARKER}": digest(out / f"calls/grok/probe/{i}" / INVALID_MARKER) for i in UNPUBLISHED},
            **{name: digest(results / name) for name in ("comparison.json", f"{CARD_STEM}-efforts.csv", f"{CARD_STEM}.json",
                                                         f"{CARD_STEM}.png")},
            "suite.lock.json": digest(root / LOCK),
            "neon-agy.launch.sh": digest(sweep_root / LAUNCHER),
        },
        "export_checks": ["92 solver summaries in the sweep's level folders, 23 per level, no task twice and no orphan attempt folder; the "
                          "sweep log shows each level complete after the relaunch from bench/2026-11-20-gemini4-neon-frontier-v4",
                          "every run is agy:gemini-4-neon at its requested level (Extra high as xhigh) on Antigravity CLI 1.5.12, the "
                          "launcher's pinned binary, with the reported model gemini-4-neon, from "
                          "bench/2026-11-20-gemini4-neon-frontier-v4 with a clean source block and every task hash equal to the frozen "
                          "suite lock",
                          "every integrity audit: no web search or fetch, no benchmark data or answer-key paths, not contaminated; every "
                          "archived tool call is read_file, write_file, edit_file or run_command",
                          "each run's token totals equal its Antigravity receipt, whose stream hash equals the archived stream; every run's "
                          "API-equivalent cost recomputed at the published list rates and matched to the sweep's run-time stamp",
                          "the 40 quota-refused attempts (10 Medium, 8 High, 22 Extra high) sit in infra-aborted with no solver summary, "
                          "and the one voided first-launch run sits in its own folder; neither is a population row",
                          "the population record's hash and the manifest's hash equal the ones frozen in the protocol, and every run's "
                          "summary hash equals its manifest entry",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control hashes, both judges' settings "
                          "and the Muse binary equal the published v3.24 record; the settings equal the recovered v3.3 and v3.4 protocols, "
                          "whose hashes match the published values; the Cursor pin names version 2026.10.01-e373342 and its frozen "
                          "directory digest, recomputed on this host when present",
                          "both judges passed calibration under v3.32 (Muse Spark 1.3 with the one-gate allowance on g11, Grok 4.6 on every "
                          "gate); no reviewer fallback; every selected Grok call records the accepted display rename",
                          "the two live operator markers are Grok's probes of Low and Extra high codeccore (two malformed replies each), "
                          "and exactly those two rows are unpublished; no recovery, no superseded marker and no quota stop",
                          "per-row Code quality, both combined scores and each judge's single-judge score recomputed and matched to the "
                          "frozen summary, with intent recovery redistributed where no quirk family passed; each level's means and standard "
                          "errors, per-judge means included, matched to the summary's groups",
                          "combined score, its standard error, Code quality, tasks passed, minutes and cost per level matched to the harness "
                          "card table; the card is byte-identical to the harness copy and its record names this summary; its Opus 5.5 and "
                          "GPT-6.2 Sol rows equal this site's board",
                          "no dashes, NUL characters or host paths in exported text"],
        "limits": ["Low and Extra high codeccore have no published Code quality score: Grok 4.6's intent probe returned malformed JSON on "
                   "both attempts (the codeccore memo line quoted with its double quotes unescaped, the line Grok also broke on under v3.7 "
                   "and v3.17). Low and Extra high are judged on 22 of 23 runs; both runs passed their tests and are timed and priced.",
                   "Muse Spark 1.3 passed calibration with the one-gate allowance: repeatability (g11) fell 0.02 short, within the "
                   "half-point the protocol allows for one gate.",
                   "Neon ran through a custom Antigravity agent limited to the default file and shell tools, so the web search tool "
                   "Antigravity's default agent carries was absent; the agent's prompt body is Antigravity's own identity block, verbatim.",
                   "The Google AI Pro plan refused 40 attempts on its usage quota; each was classified infrastructure and rerun from "
                   "scratch, so the sweep waited about nine hours in all. Four Extra high attempts were cut mid-task this way.",
                   "Antigravity updated itself to 1.6.1 once during setup, before any run; the pinned 1.5.12 binary was restored and "
                   "its folder made read-only, which the updater skips. Run receipts written from the sweep tag still describe the "
                   "update control as an environment variable, which did not stop the updater.",
                   "There is no Max level: Antigravity offers Neon at Low, Medium, High and Extra high only.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound, one task at a time."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, tool-call counts, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "thinking text", "submitted patches and reconstructed sources",
                     "quirk answer keys (they describe hidden-test behaviour)", "reviewer session identifiers and usage receipts",
                     "solver event streams and tool-call inputs", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups;", "best", best_level)


# The summary's figures as the report prints them: combined, its standard error, Code quality, judged runs and tasks passed of 23,
# per level.
PUBLISHED = {"low": (84.32, 1.09, 66.15, 22, 17), "medium": (87.48, 0.49, 67.87, 23, 23),
             "high": (87.87, 0.46, 69.07, 23, 23), "extra-high": (87.70, 0.51, 68.69, 22, 23)}


def FINAL_CHECKS(groups):  # noqa: N802
    assert [g["effort"] for g in groups] == list(EFFORTS)
    for g in groups:
        combined, se, code_quality, judged, passed = PUBLISHED[g["effort"]]
        assert (round(g["combined_33"]["mean"], 2), round(g["combined_33"]["se"], 2), round(g["code_quality"]["mean"], 2)) == (
            combined, se, code_quality), g["effort"]
        assert (g["n"], g["passed_all_runs"]) == (judged, passed), g["effort"]
    assert round(sum(g["usd_total"] for g in groups), 2) == 106.84


if __name__ == "__main__":
    main()
