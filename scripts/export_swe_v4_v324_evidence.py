"""Export the public record of the v3.24 Claude Haiku 5.5 effort sweep on Frontier v4.

Adapted from the v3.23 Claude Sonnet 5.5 export, with the same publication
scope: per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and cost. Raw prompts, patches, quirk answer
keys and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v324_evidence.py --harness-root ../VulcanBench \\
        --docs-root ../VulcanBench-sonnet55 --recovered-protocols ../VulcanBench-sonnet55/docs/judging/recovered

--harness-root holds the frozen run directories (runs-code-quality-maintenance-v3.24
and runs-effort-haiku55). --docs-root is a harness checkout carrying the
population record docs/results/swe-v4-haiku55-2026-10/comparison.json, the
card tables beside it and the frozen suite lock.

What differs from the Sonnet 5.5 export, all forced by the sweep or its judging:

- No hash bridge. The sweep ran from the tagged worktree
  bench/2026-10-07-haiku55-frontier-v4, so every run summary carries a clean
  source block and records the suite lock's task hash; the export asserts both.
- Three exclusions. paddockcore at medium, extra-high and max: a safety
  classifier stopped each session while the model probed the legacy binary and
  it ended with an empty patch, so there is no code to review. They count as
  failed tasks, are priced and timed, and carry no Code quality score.
- One unpublished row. Max codeccore (submission-030): Grok 4.6's intent probe
  had no valid response (attempt 1 quoted a line absent from the run, attempt 2
  was not valid JSON), so the frozen summary publishes no Code quality score,
  as for the same task under v3.7 and v3.17. The run passed its tests; it counts
  as passed, priced and timed.
- Tiered pricing. Haiku 5.5 costs five times as much on every line for prompts
  over 100,000 tokens, and run receipts hold session totals, not per-request
  prompt sizes. Each run carries Claude Code's own list-price total
  (cli_reported_cost_usd) plus a floor (every request at the standard tier) and
  a ceiling (every request at the over-100k tier) from the stream's final
  modelUsage, with cache writes at the 5-minute rate as on the harness cards.
- Cursor pinned by version. v3.24 judges Grok through the versioned launcher of
  Cursor CLI 2026.10.01-e373342 for the whole round and freezes a digest of
  that version directory; the export asserts it and, when the directory is on
  this host, recomputes it.
- Calibration: both judges passed every gate with no allowance used.
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
DEST = SITE / "assets/data/swe-v4-haiku55-v324"
SCORES = SITE / "assets/data/swe-v4-haiku55-v324-scores.csv"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
MODEL = "haiku55"
NAMES = {MODEL: "Claude Haiku 5.5"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.24"
MAIN_MODEL = "claude-haiku-5-5"
SWEEP = "runs-effort-haiku55"
RESULTS = "docs/results/swe-v4-haiku55-2026-10"
COMPARISON = f"{RESULTS}/comparison.json"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SOURCE_TAG = "bench/2026-10-07-haiku55-frontier-v4"
SOURCE_COMMIT = "d8ddcedc81a4aa30bac736b09dd939c606747a7b"
V34_PROTOCOLS = SITE / "assets/data/swe-v4-astra-fable51-v34/judge-protocols.json"
ORIGINAL_PROTOCOLS = {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                      "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"}
CURSOR_VERSION = "2026.10.01-e373342"
CURSOR_DIGEST = "dedbb877a8405b20e38a3dc32f38bf614bcd96d6e557f73eb6e99ff8c87b8a73"
CURSOR_LAUNCHER_SHA = "2ccc9a8e167797641448b5e5c936f006ba137a2555f117f38c5eb76a5238a233"
CURSOR_VERSIONS_DIR = Path.home() / ".local/share/cursor-agent/versions"
DISPLAY_FROZEN, DISPLAY_REPORTED = "Cursor Grok 4.6 Medium", "Grok 4.6 Medium"
DISPLAY_RENAMES = 426  # selected Grok calls whose operator_review records the accepted rename
RETRIES = {"muse": 9, "grok": 5}  # calls with a second attempt under the frozen single-retry rule
# Claude Code version per run, from each stream's init event (harness DECISIONS.md, 2026-10-10).
CLI_VERSIONS = {"low": {"2.1.293": 22, "2.1.294": 1}, "medium": {"2.1.294": 3, "2.1.295": 20}, "high": {"2.1.295": 23},
                "extra-high": {"2.1.295": 2, "2.1.296": 21}, "max": {"2.1.296": 23}}
# platform.claude.com pricing page, checked 2026-10-07: USD per MTok for uncached input, 5-minute cache write, 1-hour cache write,
# cache read and output, for prompts up to 100,000 tokens and over 100,000 tokens.
PRICING_VERIFIED = "2026-10-07"
RATES_PER_MILLION = {MAIN_MODEL: {
    "up_to_100k": {"input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_hit": 0.01, "output": 0.50},
    "over_100k": {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_hit": 0.05, "output": 2.50}}}
TIERS = {"floor": "up_to_100k", "ceiling": "over_100k"}
PRICING_METHOD = ("Claude Code's own list-price total for the session (economics.cli_reported_cost_usd, equal to the stream's total_cost_usd); "
                  "floor and ceiling price the final modelUsage entirely at the up-to-100k and the over-100k tier, cache writes at the 5-minute rate")
# The sweep was stopped between tasks twice (harness DECISIONS.md, 2026-10-10 and 2026-10-12), UTC.
PAUSES = (("2026-10-09T15:43:00+00:00", "2026-10-10T09:20:00+00:00"), ("2026-10-10T19:48:00+00:00", "2026-10-11T15:50:00+00:00"))
RESUME_STUBS = 25  # summary-less extra-high folders written as the first pause ended; never read by the sweep or the population
EXCLUDED = {("medium", "legacy-paddockcore-binary-parity"), ("extra-high", "legacy-paddockcore-binary-parity"),
            ("max", "legacy-paddockcore-binary-parity")}
EXCLUDED_NOTE = ("not judged: a safety classifier stopped the session while the model probed the legacy binary and it ended with an empty "
                 "patch, so there is no code to review; the run counts as a failed task and is priced and timed")
INVALID_MARKER = "operator-invalid.json"
SUPERSEDED_MARKER = "operator-invalid.superseded.json"
EXPECTED_INVALID = {("grok", "probe", "submission-030"): "invalidate_unrecoverable_probe"}
UNPUBLISHED = {"submission-030": ("max", "legacy-codeccore-binary-parity")}
UNPUBLISHED_NOTE = ("unpublished: Grok 4.6's intent probe gave no valid answer after the protocol's single retry (attempt 1 quoted a line "
                    "absent from the run, which no recovery rule accepts; attempt 2 was not valid JSON), so no answer-key match was made and "
                    "the v3.24 summary publishes no Code quality or combined score for this run, as under v3.7 and v3.17 for the same task; "
                    "the run passed its tests, counts as a passed task and is priced and timed")
# The one recovery: Grok's primary review of extra-high vaultcore (submission-087) quoted a hard-wrapped line joined into one; the standing
# recover_excerpts rule (since v3, September 7) selected attempt 1 with the quote re-wrapped to the source's line breaks.
EXPECTED_RECOVERIES = {("grok", "primary", "submission-087"): "recover_excerpts"}
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")


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


def tier_cost(per_model, tier):
    rate = RATES_PER_MILLION[MAIN_MODEL][TIERS[tier]]
    total = 0.0
    for model, u in per_model.items():
        if model != MAIN_MODEL:  # never happens in this sweep (asserted); kept as the harness card prices it
            total += u["cli_cost_usd"]
            continue
        total += (u["input_tokens"] * rate["input"] + u["cache_creation_tokens"] * rate["cache_write_5m"]
                  + u["cache_read_tokens"] * rate["cache_hit"] + u["output_tokens"] * rate["output"]) / 1e6
    return total


def stream_facts(run_dir):
    """Replies by serving model, final modelUsage, final CLI cost and the init event's Claude Code version."""
    replies, final, version = Counter(), None, None
    for line in (run_dir / "cli-agent-stream.jsonl").open(errors="replace"):
        if '"assistant"' not in line and '"result"' not in line and '"init"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            replies[event["message"].get("model")] += 1
        elif event.get("type") == "result":
            final = event
        elif event.get("type") == "system" and event.get("subtype") == "init":
            version = event.get("claude_code_version")
    assert final is not None and version is not None, run_dir.name
    usage = final.get("modelUsage") or {}
    per_model = {m: {"input_tokens": u.get("inputTokens", 0), "cache_read_tokens": u.get("cacheReadInputTokens", 0),
                     "cache_creation_tokens": u.get("cacheCreationInputTokens", 0), "output_tokens": u.get("outputTokens", 0),
                     "cli_cost_usd": u.get("costUSD", 0.0)} for m, u in sorted(usage.items())}
    raw = sum(v["input_tokens"] + v["cache_read_tokens"] + v["cache_creation_tokens"] + v["output_tokens"] for v in per_model.values())
    return dict(sorted(replies.items())), per_model, raw, final["total_cost_usd"], version


def call_records(out):
    """Operator markers, superseded markers and recoveries the v3 wrapper left under calls/, keyed (panel, stage, submission)."""
    def key(p):
        return (p.parents[1].parent.name, p.parents[1].name, p.parent.name)
    invalid = {key(p): read(p) for p in (out / "calls").glob(f"*/*/*/{INVALID_MARKER}")}
    superseded = {key(p): read(p) for p in (out / "calls").glob(f"*/*/*/{SUPERSEDED_MARKER}")}
    recoveries = {}
    for p in (out / "calls").glob("*/*/*/selected.json"):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries[key(p)] = selected["operator_recovery"]
    return invalid, superseded, recoveries


def solver_facts(run_dir, task, lock):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    replies, per_model, raw, cli_total, init_version = stream_facts(run_dir)
    assert abs(solver["economics"]["cli_reported_cost_usd"] - cli_total) < 1e-9, run_dir.name
    assert solver["economics"]["api_equivalent_cost_usd"] is None
    assert replies == {MAIN_MODEL: sum(replies.values())} and list(per_model) == [MAIN_MODEL], run_dir.name
    assert solver["cli_agent"]["harness_version"] == f"{init_version} (Claude Code)", run_dir.name
    assert solver["cli_agent"]["requested_model"] == solver["cli_agent"]["reported_model"] == MAIN_MODEL
    assert solver["finished"] is True and solver["duration_s"] < 10800, run_dir.name
    source = solver["source"]  # tagged run worktree, clean: no hash bridge needed
    assert source["harness"]["describe"] == SOURCE_TAG and source["harness"]["commit"] == SOURCE_COMMIT, run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_id"] == task and solver["task_hash"] == lock[task], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"]
    assert audit["filesystem"]["benchmark_data_paths"] == [] and audit["filesystem"]["answer_key_paths"] == []
    hidden = solver["verifier"]["fail_to_pass"]
    floor, ceiling = tier_cost(per_model, "floor"), tier_cost(per_model, "ceiling")
    return solver, {
        "solver_fallback": False, "replies_by_model": replies,
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
        "task_hash": solver["task_hash"], "source_commit": SOURCE_COMMIT,
        "raw_tokens": raw, "token_usage": {"output_tokens": sum(v["output_tokens"] for v in per_model.values()), "by_model": per_model},
        "estimated_usd": cli_total, "usd_floor": floor, "usd_ceiling": ceiling, "pricing_method": PRICING_METHOD,
        "solver_cli_version": solver["cli_agent"]["harness_version"],
    }


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    parser.add_argument("--docs-root", type=Path, default=None)
    parser.add_argument("--recovered-protocols", type=Path, default=None,
                        help="folder holding code-quality-maintenance-v3.3-protocol.json and -v3.4-protocol.json (harness docs/judging/recovered)")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    docs = (args.docs_root or args.harness_root).resolve()
    out = root / "runs-code-quality-maintenance-v3.24"
    sweep = root / SWEEP
    summary = read(out / "summary.json")
    manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
    protocol = read(out / "protocol.json")
    comparison_path = docs / COMPARISON
    comparison = read(comparison_path)
    lock = read(docs / LOCK)["tasks"]

    # The frozen protocol, population and judges.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == len(manifest) == 112
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    assert comparison["missing"] == [] and len(comparison["rows"]) == 112
    assert {(x["effort"], x["task"]) for x in comparison["excluded"]} == EXCLUDED
    assert {(x["effort"], x["task"]) for x in protocol["population"]["excluded"]} == EXCLUDED and protocol["population"]["missing"] == []
    assert comparison["cells"] == protocol["population"]["cells"] == {f"{MODEL}/{e}": 23 - sum(x == e for x, _ in EXCLUDED) for e in EFFORTS}
    assert protocol["sensitivity_panels"] == {} and protocol["scored_siblings"] == {}
    public_reviewers = {p: {k: v for k, v in protocol["reviewers"][p].items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}
                        for p in PANELS}
    assert public_reviewers == read(V34_PROTOCOLS)["scored_panel"]
    assert protocol["reviewers"]["muse"]["binary_sha256"] == read(V34_PROTOCOLS)["scored_panel"]["muse"]["binary_sha256"]
    pins = protocol["judge_pins"]
    assert {v: s["sha256"] for v, s in pins["settings_sources"].items()} == ORIGINAL_PROTOCOLS
    recovered_checked = False
    if args.recovered_protocols:  # the original files: published hashes, and the same reviewer settings as v3.24
        for version, sha in ORIGINAL_PROTOCOLS.items():
            original = args.recovered_protocols / f"code-quality-maintenance-{version}-protocol.json"
            assert digest(original) == sha, version
            for p, settings in read(original)["reviewers"].items():
                if p in PANELS:
                    assert {k: v for k, v in settings.items() if k not in ("muse", "cursor")} == public_reviewers[p], (version, p)
        recovered_checked = True
    # Cursor pinned by version: the frozen pin names the version and its directory digest, and the launcher hash is the one every release ships.
    cursor_pin = pins["cursor_version"]
    assert cursor_pin["version"] == CURSOR_VERSION and cursor_pin["digest"] == CURSOR_DIGEST
    assert Path(cursor_pin["directory"]).name == CURSOR_VERSION
    assert protocol["binaries"][cursor_pin["launcher"]]["sha256"] == CURSOR_LAUNCHER_SHA
    cursor_rechecked = False
    if (CURSOR_VERSIONS_DIR / CURSOR_VERSION).is_dir():
        assert cursor_version_digest(CURSOR_VERSIONS_DIR / CURSOR_VERSION) == CURSOR_DIGEST
        cursor_rechecked = True

    invalid, superseded, recoveries = call_records(out)
    assert set(invalid) == set(EXPECTED_INVALID) and superseded == {}, (invalid, superseded)
    marker = invalid[("grok", "probe", "submission-030")]
    assert set(marker["unsupported_excerpts"]) == {"1"} and set(marker["malformed_attempts"]) == {"2"}
    assert not (out / "calls/grok/probe/submission-030/selected.json").exists() and not (out / "calls/grok/match/submission-030").exists()
    assert {k: (EXPECTED_RECOVERIES[k], v["method"]) for k, v in recoveries.items()} == {
        ("grok", "primary", "submission-087"): ("recover_excerpts", "excerpt re-wrapped to source line breaks")}
    grok_calls = [read(q) for q in (out / "calls/grok").glob("*/*/selected.json")]
    assert {c["model_reported"] for c in grok_calls} == {DISPLAY_REPORTED} and protocol["reviewers"]["grok"]["display_name"] == DISPLAY_FROZEN
    assert sum("label renamed by the provider" in json.dumps(c.get("operator_review")) for c in grok_calls) == DISPLAY_RENAMES
    calls = {p: {s: sum(1 for d in (out / "calls" / p / s).iterdir() if d.is_dir()) for s in
                 ("calibration", "primary", "repeat", "pairwise", "probe", "match")} for p in PANELS}
    assert calls == {"muse": {"calibration": 80, "primary": 112, "repeat": 5, "pairwise": 8, "probe": 112, "match": 112},
                     "grok": {"calibration": 80, "primary": 112, "repeat": 5, "pairwise": 8, "probe": 112, "match": 111}}, calls
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in PANELS}
    assert retries == RETRIES, retries
    assert not list((out / "reconstruction").glob("*.json"))

    # Every finished solver summary in the sweep folder is a population row or an exclusion: 115 in all. The only summary-less run
    # folders are the 25 extra-high resume stubs from the first pause, which the sweep and the population never read.
    summaries = {p.parent.name: p for p in sweep.glob("*/legacy-*/summary.json")}
    record = {r["run_id"]: r for r in comparison["rows"]}
    excluded_ids = {x["run_id"]: x for x in comparison["excluded"]}
    assert len(summaries) == 115 and set(summaries) == set(record) | set(excluded_ids)
    stubs = [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    assert len(stubs) == RESUME_STUBS and {p.parent.name for p in stubs} == {"extra-high"}
    assert all(sorted(q.name for q in p.iterdir()) == ["trace.jsonl"] for p in stubs)
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
        run_dir = sweep / run["effort"] / run["run_id"]
        assert digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
        solver, facts = solver_facts(run_dir, run["task"], lock)
        assert run["fallback_replies"] == facts["replies_by_model"] and not run["fallback"]
        assert run["solver_cli_version"] == facts["solver_cli_version"]
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS) and not any(panels[p]["reviewer_fallback"] for p in PANELS)
        if entry["id"] in UNPUBLISHED:
            assert not entry.get("published") and panels["grok"]["l2"] is None and panels["muse"]["l2"] is not None
            assert (run["effort"], run["task"]) == UNPUBLISHED[entry["id"]] and run["functional"] == 1.0
            l1 = l2 = code_quality = combined_33 = combined_20 = redistributed = panel_record = None
            judged = UNPUBLISHED_NOTE
        else:
            published = entry["published"]
            l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
            redistributed = published["l2_redistributed"]
            assert not redistributed and all(panels[p]["l2"] is not None for p in PANELS)
            l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
            code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
            assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
            combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
            combined_20 = composite(run, code_quality, 0.20)
            assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
            panel_record = {p: {"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                                "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                                "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} for p in PANELS}
            judged = "published"
        rows.append({
            "model": MODEL, "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": judged, "scored_panels": list(PANELS) if panel_record else [], "finished": True,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]), "duration_s": run["duration_s"],
            "started_at": run["started_at"], "finished_at": run["finished_at"], "evidence_sha256": run["evidence_sha256"], **facts,
        })
    for run_id, ex in excluded_ids.items():  # the three classifier-stop runs: not judged, counted, priced and timed
        run_dir = sweep / ex["effort"] / run_id
        solver, facts = solver_facts(run_dir, ex["task"], lock)
        assert solver["scores"]["functional"] == ex["functional"] == 0.0 and abs(solver["duration_s"] - ex["duration_s"]) < 1e-6
        assert solver["scores"]["quality"] is None and solver["scores"]["security"] is None  # empty patch: nothing to lint or scan
        assert (run_dir / "final.patch").read_text().strip() == ""
        rows.append({
            "model": MODEL, "effort": ex["effort"], "task": ex["task"], "run_id": run_id, "judged_under": PROTOCOL_ID, "judged": EXCLUDED_NOTE,
            "scored_panels": [], "finished": True, "functional": solver["scores"]["functional"],
            "automated_quality": solver["scores"]["quality"], "security": solver["scores"]["security"], "reviewed_score": None,
            "intent_recovery": None, "intent_recovery_redistributed": None, "code_quality": None, "combined_33": None,
            "combined_20_profile": None, "panels": None, "passed_quirk_families": None, "duration_s": solver["duration_s"],
            "started_at": solver["started_at"], "finished_at": solver["finished_at"], "evidence_sha256": None, **facts,
        })
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and len({(r["effort"], r["task"]) for r in rows}) == 115
    assert summary["published_submissions"] == sum(r["judged"] == "published" for r in rows) == 111 and not summary["ready_for_publication"]
    for effort, versions in CLI_VERSIONS.items():
        got = Counter(r["solver_cli_version"].split()[0] for r in rows if r["effort"] == effort)
        assert got == Counter(versions), (effort, got)
    # The two pauses fall between tasks: no run was in progress across either.
    spans = sorted((datetime.fromisoformat(r["started_at"]), datetime.fromisoformat(r["finished_at"])) for r in rows)
    for start, end in PAUSES:
        s, e = datetime.fromisoformat(start), datetime.fromisoformat(end)
        assert not any(a < e and b > s for a, b in spans), (start, end)
    gaps = [(b[0] - a[1]).total_seconds() / 3600 for a, b in zip(spans, spans[1:])]
    assert sum(g > 1 for g in gaps) == 2

    save("runs.json", {"runs": len(rows), "published": 111, "unpublished": 1, "excluded": 3, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where the v3.24 summary publishes a Code quality score from both judges; the "
                                      "other four rows carry the reason they have none: three classifier-stop exclusions and one unpublished row",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator; no Haiku 5.5 run "
                                               "needed that rule",
                       "fallback_rule": "Claude Code's refusal fallback was on (its default). solver_fallback would be true if any assistant reply "
                                        "came from a model other than claude-haiku-5-5; replies_by_model counts them. No Haiku 5.5 run used it.",
                       "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts "
                                                  "those the run passed",
                       "cost_fields": {"estimated_usd": "Claude Code's own list-price total for the session",
                                       "usd_floor": "the final modelUsage priced entirely at the up-to-100k tier",
                                       "usd_ceiling": "the final modelUsage priced entirely at the over-100k tier, cache writes at the 5-minute rate"},
                       "token_fields": {"raw_tokens": "input, cache reads, cache writes and output from the final modelUsage",
                                        "token_usage.output_tokens": "output tokens, reasoning included"},
                       "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    def pct(value):  # the classifier-stop runs have no patch, so no lint or security score
        return None if value is None else 100 * value

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile",
                         "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed", "hidden_behaviours", "code_quality",
                         "reviewed_score", "intent_recovery", "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "grok_reviewed", "grok_readability", "grok_maintainability", "grok_intent_recovery", "passed_quirk_families",
                         "solver_fallback", "all_replies", "duration_s", "raw_tokens", "output_tokens", "estimated_usd", "usd_floor", "usd_ceiling",
                         "started_at", "finished_at", "solver_cli_version", "task_hash", "evidence_sha256"])
        for r in rows:
            status = "published" if r["judged"] == "published" else ("unpublished" if r["judged"].startswith("unpublished") else "not judged")
            p = r["panels"] or {q: {} for q in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], status, fmt(r["combined_33"]),
                             fmt(r["combined_20_profile"]), f'{100 * r["functional"]:.2f}', fmt(pct(r["automated_quality"]), 2), fmt(pct(r["security"]), 2), r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]),
                             fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             *[fmt(p[q].get(k)) for q in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             "" if r["passed_quirk_families"] is None else r["passed_quirk_families"], r["solver_fallback"],
                             sum(r["replies_by_model"].values()), r["duration_s"], r["raw_tokens"], r["token_usage"]["output_tokens"],
                             fmt(r["estimated_usd"], 6), fmt(r["usd_floor"], 6), fmt(r["usd_ceiling"], 6), r["started_at"], r["finished_at"],
                             r["solver_cli_version"], r["task_hash"], r["evidence_sha256"] or ""])

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        judged = [r for r in rs if r["judged"] == "published"]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(judged), "runs": len(rs),
            "excluded_runs": sum(r["judged"] == EXCLUDED_NOTE for r in rs), "unpublished_runs": sum(r["judged"] == UNPUBLISHED_NOTE for r in rs),
            "combined_33": mean_se(r["combined_33"] for r in judged), "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
            "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
            "intent_recovery": mean_se(r["intent_recovery"] for r in judged), "intent_recovery_redistributed_runs": 0,
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in judged), "automated_quality": mean_se(100 * r["automated_quality"] for r in judged),
            "security": mean_se(100 * r["security"] for r in judged),
            # passed counts judged runs; passed_all_runs counts all 23 and is the one to read.
            "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            # Runtime, tokens and cost are facts of the sweep and cover every run; the harness cards average the judged runs.
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_judged_runs": mean_se(r["duration_s"] / 60 for r in card_runs(rs)),
            "solver_fallback_runs": 0, "priced_runs": len(rs),
            "cli_versions": dict(sorted(Counter(r["solver_cli_version"].split()[0] for r in rs).items())),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            "usd_judged_runs": mean_se(r["estimated_usd"] for r in card_runs(rs)),
            "usd_floor": mean_se(r["usd_floor"] for r in rs), "usd_ceiling": mean_se(r["usd_ceiling"] for r in rs),
            "usd_floor_total": sum(r["usd_floor"] for r in rs), "usd_ceiling_total": sum(r["usd_ceiling"] for r in rs),
        }
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9, (effort, field)
            assert abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        assert entry["l2_redistributed"] == 0
        for p in PANELS:
            assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"] and abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
        groups.append(g)
    # Facts of the sweep (harness DECISIONS.md, 2026-10-12): pass@1 0.565, 0.565, 0.739, 0.957 and 0.957.
    assert [g["passed_all_runs"] for g in groups] == [13, 13, 17, 22, 22]
    assert [g["n"] for g in groups] == [23, 22, 23, 22, 21] and [g["excluded_runs"] for g in groups] == [0, 1, 0, 1, 1]
    assert [round(g["combined_33"]["mean"], 2) for g in groups] == [84.42, 84.03, 88.01, 91.83, 92.16]  # high is 88.01499, so 88.01 (the harness ops log rounds it to 88.02)
    assert [f'{g["usd"]["mean"]:.2f}' for g in groups] == ["1.04", "1.36", "1.25", "0.84", "1.54"]
    assert [f'{g["usd_judged_runs"]["mean"]:.2f}' for g in groups] == ["1.04", "1.41", "1.25", "0.87", "1.55"]

    # The harness card tables carry the same figures; cards time and price the judged runs.
    with (docs / RESULTS / "haiku55-v324-efforts.csv").open(newline="") as source:
        card = {r["effort"]: r for r in csv.DictReader(source)}
    for g in groups:
        c = card[g["effort"]]
        # The score card counts passes over the judged runs (21 of 21 at max); the comparison tables below count all 23 (22 at max).
        assert int(c["n"]) == g["n"] and int(c["passed"]) == g["passed"] and c["fallbacks"] == "0"
        for column, value in (("combined_v3", g["combined_33"]["mean"]), ("combined_v3_se", g["combined_33"]["se"]),
                              ("combined_20pct", g["combined_20_profile"]["mean"]), ("code_quality", g["code_quality"]["mean"]),
                              ("code_quality_se", g["code_quality"]["se"]), ("readability", g["readability"]["mean"]),
                              ("maintainability", g["maintainability"]["mean"]), ("intent_recovery", g["intent_recovery"]["mean"]),
                              ("muse_l1", g["by_panel"]["muse"]["mean"]), ("grok_l1", g["by_panel"]["grok"]["mean"]),
                              ("minutes", g["minutes_judged_runs"]["mean"])):
            assert abs(float(c[column]) - value) < 1e-4, (g["effort"], column)
    card_tables = {}
    for name in ("haiku55-vs-sonnet55", "haiku55-vs-gpt61sol", "haiku55-vs-luna"):
        path = docs / RESULTS / f"{name}-efforts.csv"
        card_tables[name] = path
        with path.open(newline="") as source:
            mine = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == MODEL}
        for g in groups:
            c = mine[g["effort"]]
            assert int(c["n"]) == g["runs"] and int(c["judged"]) == g["n"] and int(c["passed"]) == g["passed_all_runs"]
            assert abs(float(c["combined"]) - g["combined_33"]["mean"]) < 1e-4 and abs(float(c["usd_per_task"]) - g["usd_judged_runs"]["mean"]) < 1e-4
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "readability", "maintainability", "muse_reviewed", "grok_reviewed", "functional",
                         "automated_quality", "security", "passed_of_23", "hidden_behaviours_fixed_of_231", "mean_minutes", "mean_minutes_se",
                         "mean_raw_tokens", "mean_usd", "mean_usd_se", "mean_usd_floor", "mean_usd_ceiling", "total_usd", "cli_versions"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"],
                             *[f'{g[k]["mean"]:.4f}' for k in ("combined_33",)], f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}',
                             f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}',
                             f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}',
                             f'{g["usd"]["se"]:.6f}', f'{g["usd_floor"]["mean"]:.6f}', f'{g["usd_ceiling"]["mean"]:.6f}', f'{g["usd_total"]:.6f}',
                             " ".join(f"{v}x{k}" for k, v in g["cli_versions"].items())])

    above = [r for r in rows if r["estimated_usd"] > r["usd_ceiling"] + 1e-9]
    below = [r for r in rows if r["estimated_usd"] < r["usd_floor"] - 1e-9]
    assert below == [] and {(r["effort"], r["task"]) for r in above} == {("medium", "legacy-lodgecore-binary-parity"), ("max", "legacy-depotcore-binary-parity")}
    assert all(r["estimated_usd"] <= 1.005 * r["usd_ceiling"] for r in above)
    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "usd_floor": sum(r["usd_floor"] for r in rows),
                      "usd_ceiling": sum(r["usd_ceiling"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    assert f'{totals[MODEL]["usd"]:.2f}' == "138.31" and f'{totals[MODEL]["usd_floor"]:.2f}' == "31.10" and f'{totals[MODEL]["usd_ceiling"]:.2f}' == "155.50"
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a Claude Max subscription through Claude Code "
                 "(--billing subscription), so these are estimates, not bills. Judging is excluded. Every run in the sweep is priced, "
                 "including the three classifier-stop runs and the unpublished max codeccore run.",
        "pricing_verified": PRICING_VERIFIED, "sources": {"anthropic": "https://platform.claude.com/docs/en/about-claude/pricing"},
        "rates_per_million": RATES_PER_MILLION, "pricing_method": PRICING_METHOD,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "usd_judged_runs": g["usd_judged_runs"], "usd_floor": g["usd_floor"], "usd_ceiling": g["usd_ceiling"],
                    "usd_floor_total": g["usd_floor_total"], "usd_ceiling_total": g["usd_ceiling_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "minutes_judged_runs": g["minutes_judged_runs"], "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "runs_above_ceiling": [{"effort": r["effort"], "task": r["task"], "estimated_usd": r["estimated_usd"], "usd_ceiling": r["usd_ceiling"]}
                               for r in above],
        "limitations": [
            "Haiku 5.5 is priced by prompt length: prompts over 100,000 tokens cost five times the standard rate on every line. Claude Code "
            "receipts hold cumulative session usage, not per-request prompt sizes, so a run's true API price cannot be split between the "
            "tiers. Each run carries Claude Code's own list-price total, which prices each request at its own tier, beside a floor (every "
            "request at the standard tier) and a ceiling (every request at the over-100k tier).",
            "Floor and ceiling price cache writes at the 5-minute rate, as the harness cards do. Two runs (medium lodgecore and max "
            "depotcore) wrote cache entries with the 1-hour TTL, which costs more, so Claude Code's total for them sits up to 0.4% above "
            "the ceiling.",
            "Cost per task covers all 23 runs in a cell. The harness cards average the judged runs, so their figures at medium, extra-high "
            "and max ($1.41, $0.87 and $1.55) differ slightly from this bundle's ($1.36, $0.84 and $1.54).",
            "No Batch, Fast or priority pricing is applied.",
        ],
        "comparison_sha256": digest(comparison_path),
    })

    calibration = {}
    for panel in PANELS:
        result = read(out / f"calibration-{panel}.json")
        assert result["passed"] and result["failing_gates"] == [] and not result["allowance_used"] and result["call_count"] == 80
        assert all(g["passed"] for g in result["gates"].values()) and result["protocol_sha256"] == digest(out / "protocol.json")
        calibration[panel] = {k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                     "gates", "control_means")}
    save("calibration.json", calibration)

    save("judge-protocols.json", {
        "scored_panel": public_reviewers,
        "protocol_ids": {p: protocol["id"] for p in PANELS}, "protocol_sha256": {p: digest(out / "protocol.json") for p in PANELS},
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": {k: v for k, v in protocol["population"].items() if k != "excluded"},
        "not_judged": [{"effort": e, "task": t, "reason": EXCLUDED_NOTE} for e, t in sorted(EXCLUDED, key=lambda x: EFFORTS.index(x[0]))],
        "judge_pins": {
            "settings_sources": {v: {"file": s["file"], "sha256": s["sha256"]} for v, s in pins["settings_sources"].items()},
            "originals": "The judge settings are read from the original v3.3 and v3.4 protocol files, recovered from the owner's private backup; "
                         "their sha256 equal the published values.",
            "originals_checked_by_this_export": recovered_checked,
            "muse": "same binary as every earlier round (sha256 match)", "muse_binary_sha256": protocol["reviewers"]["muse"]["binary_sha256"],
            "cursor_version": {"version": CURSOR_VERSION, "digest": CURSOR_DIGEST, "launcher_sha256": CURSOR_LAUNCHER_SHA,
                               "rule": cursor_pin["rule"], "rechecked_by_this_export": cursor_rechecked,
                               "note": "Grok 4.6 was judged through the versioned launcher of this Cursor CLI for the whole round, with a digest "
                                       "of its version directory re-checked before every stage; it is the CLI that judged Sonnet 5.5 under v3.23."},
        },
        "display_name": {"frozen": DISPLAY_FROZEN, "reported": DISPLAY_REPORTED, "model_id": "cursor-grok-4.6-medium",
                         "accepted_renames_recorded": DISPLAY_RENAMES,
                         "note": "Cursor has reported the display name \"Grok 4.6 Medium\" for the pinned model id since 2026-09-21; the frozen "
                                 "settings say \"Cursor Grok 4.6 Medium\". The wrapper accepts the rename and records it per call."},
        "counted_calls": calls, "second_attempts": RETRIES,
        "unpublished": [{"effort": e, "task": t, "panel": "grok", "stage": "probe", "rule": EXPECTED_INVALID[("grok", "probe", i)],
                         "finding": marker["finding"], "action": marker["action"],
                         "attempt_1_unsupported_excerpts": len(marker["unsupported_excerpts"]["1"]), "attempt_2_error": marker["malformed_attempts"]["2"]}
                        for i, (e, t) in UNPUBLISHED.items()],
        "operator_recoveries": [{"panel": k[0], "stage": k[1], "submission": k[2], "effort": manifest[k[2]]["effort"], "task": manifest[k[2]]["task"],
                                 "rule": EXPECTED_RECOVERIES[k], "method": v.get("method"), "source_attempt": v.get("source_attempt"),
                                 "respelled_excerpts": len(v.get("original_excerpts", {})),
                                 "checks": "both attempts failed only the excerpt rule; every rejected excerpt matches the source once whitespace "
                                           "and line breaks are collapsed; scores untouched, original excerpt kept in the receipt"}
                                for k, v in sorted(recoveries.items())],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.24/{n}": digest(out / n) for n in ("summary.json", "protocol.json", "private-manifest.json",
                                                       "calibration-muse.json", "calibration-grok.json")},
            "v3.24/calls/grok/probe/submission-030/operator-invalid.json": digest(out / "calls/grok/probe/submission-030" / INVALID_MARKER),
            "comparison.json": digest(comparison_path), "suite.lock.json": digest(docs / LOCK),
            "haiku55-v324-efforts.csv": digest(docs / RESULTS / "haiku55-v324-efforts.csv"),
            **{f"{name}-efforts.csv": digest(path) for name, path in card_tables.items()},
        },
        "export_checks": ["115 solver summaries in the sweep folder: 112 population rows and the 3 classifier-stop exclusions, all finished "
                          "inside the 3-hour bound; the only summary-less run folders are the 25 extra-high resume stubs",
                          "every run summary carries a clean source block from bench/2026-10-07-haiku55-frontier-v4 and records the frozen suite "
                          "lock's task hash; every integrity audit is clean",
                          "every reply in every stream came from claude-haiku-5-5; no other model appears in any final modelUsage",
                          "every run's Claude Code version matches its stream's init event and the per-level mix in the decision record",
                          "no run was in progress across either pause",
                          "both scored panels passed calibration under v3.24 with no allowance used; no reviewer fallbacks",
                          "the reviewer settings equal those published in the v3.4 bundle and, when supplied, the recovered original protocols",
                          "the Cursor pin names version 2026.10.01-e373342 and its frozen directory digest, recomputed on this host when present",
                          "the one unpublished row is exactly the submission whose Grok probe folder carries the operator-invalid marker",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary; cell means and standard "
                          "errors matched, per-judge means included",
                          "combined score, Code quality and its components, pass counts and runtime matched to the harness score card table, and "
                          "the Haiku rows of the three comparison card tables matched",
                          "every run's cost equals Claude Code's final total_cost_usd in its stream and the run summary's cli_reported_cost_usd",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["Three runs are not judged: paddockcore at medium, extra-high and max. A safety classifier stopped each session while the "
                   "model probed the legacy binary, and it ended with an empty patch. They count as failed tasks and are priced and timed.",
                   "Max codeccore has no published Code quality score: Grok 4.6's intent probe gave no valid answer after the single retry "
                   "(attempt 1 quoted a line absent from the run; attempt 2 was not valid JSON). The run passed its tests and counts as passed.",
                   "One operator recovery: Grok 4.6's primary review of extra-high vaultcore quoted a hard-wrapped line joined into one on "
                   "both attempts; the standing recover_excerpts rule selected attempt 1 with the quote re-wrapped, scores untouched. "
                   "Invalid-response retries under the frozen rule: Muse Spark 1.3 9, Grok 4.6 5.",
                   "Claude Code versions: low 22 on 2.1.293 and 1 on 2.1.294; medium 3 on 2.1.294 and 20 on 2.1.295; high on 2.1.295; "
                   "extra-high 2 on 2.1.295 and 21 on 2.1.296; max on 2.1.296. Earlier Claude columns used older Claude Code releases.",
                   "Judge settings are the recovered original v3.3 and v3.4 protocols; Muse Spark 1.3 ran the same binary; Grok 4.6 ran "
                   "through Cursor CLI 2026.10.01-e373342, pinned by version for the whole round, the same CLI that judged Sonnet 5.5. Cursor "
                   "reports the display name \"Grok 4.6 Medium\" (frozen: \"Cursor Grok 4.6 Medium\"), a rename the wrapper accepted and "
                   "recorded 426 times.",
                   "The sweep was stopped between tasks twice, 2026-10-09 15:43 to 2026-10-10 09:20 UTC and 2026-10-10 19:48 to "
                   "2026-10-11 15:50 UTC; no run was in progress across either pause, so run timings are intact. The host's clock moved from "
                   "PDT to CEST during the sweep; all times here are UTC.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level. The sweep ran 2026-10-08 10:40 to 2026-10-11 22:49 UTC on the owner's Mac, local "
                   "sandbox, flat 3-hour task bound, one task at a time. Judging ran 2026-10-11 22:52 to 2026-10-12 10:11 UTC with no sweep "
                   "running."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens, replies by serving model, Claude Code's list-price cost and the tier floor "
                             "and ceiling.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "the unused Grok probe attempts on max codeccore", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


def card_runs(rs):
    """The runs the harness cards time and price: the published ones (no exclusion, not the unpublished max codeccore)."""
    return [r for r in rs if r["judged"] == "published"]


if __name__ == "__main__":
    main()
