"""Export the public record of the v3.17 GPT-6 Sol effort sweep on Frontier v4.

Adapted from the v3.16 GPT-6 Luna export and the v3.7 GPT-5.6 Sol export, with
the same publication scope: per-run scores, per-panel sub-scores, aggregates,
judge protocol text, calibration verdicts, raw tokens and API-equivalent cost.
Raw prompts, patches, quirk answer keys and host paths are withheld. Run from
the site root:

    python3 scripts/export_swe_v4_v317_evidence.py --harness-root ../VulcanBench

What differs from the Luna export, all forced by the sweep:

- No timeouts. Every one of the 115 runs finished inside the flat 3-hour
  bound (the longest took 129 minutes), so the population excludes nothing
  and there is no second, timeouts-as-0 combined figure.
- One unpublished row, handled as the v3.7 Sol export handled its own:
  Grok 4.6's intent probe on medium codeccore (submission-061) has no valid
  answer after the single retry (one malformed attempt, one quoting code
  absent from the run), so no answer-key match was made and the frozen
  summary publishes no Code quality score for that run. Medium is judged on
  22 of 23; the run still counts for tasks passed, time and cost.
- One operator recovery: Grok's primary review of submission-035 (high
  payrollcore) was a complete JSON review followed by a stray closing brace
  on both attempts; the formatting-only wrapper rule recover_trailing_braces
  kept attempt 1 with every normal check applied. It is recorded in
  judge-protocols.json.
- One infrastructure retry in the sweep: the first max depotcore attempt
  ended when the API answered "Selected model is at capacity"; the harness
  re-queued it and the retry is the counted run. The failed attempt left no
  summary and is not part of any cell.
- Both judges passed calibration with no allowance used.
- Pricing needs no long-context branch: Codex keeps each request within its
  272K window, so the short-context list rates apply to every token.
"""

import argparse
import csv
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-gpt6-sol-v317"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
LEVELS = {"gpt6sol": EFFORTS}
NAMES = {"gpt6sol": "GPT-6 Sol"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
# developers.openai.com/api/docs/pricing, checked 2026-09-25: standard tier, short context.
RATES_PER_MILLION = {"gpt6sol": {"input": 2.00, "cached_input": 0.20, "output": 10.00}}
PROTOCOL_ID = "code-quality-maintenance-v3.17"
CLI_VERSION = "codex-cli 0.155.0"
INVALID_MARKER = "operator-invalid.json"
UNPUBLISHED = {("gpt6sol", "medium", "legacy-codeccore-binary-parity")}
UNPUBLISHED_NOTE = ("unpublished: Grok 4.6's intent probe gave no valid answer after the protocol's single retry (attempt 1 was not "
                    "valid JSON; attempt 2 quoted code absent from the run, which no recovery rule accepts), so no answer-key match "
                    "was made and the v3.17 summary publishes no Code quality or combined score for this run; both judges' reviews "
                    "and the Muse probe are retained in the harness archive; the run failed its tests and is priced")
RECOVERED = {"submission-035": ("gpt6sol", "high", "legacy-payrollcore-binary-parity")}
CAPACITY_RETRY = ("max", "legacy-depotcore-binary-parity")
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert not any(mark in text for mark in FORBIDDEN), name
    (DEST / name).write_text(text)


def mean_se(values):
    values = list(values)
    return {"n": len(values), "mean": statistics.mean(values),
            "se": statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0}


def composite(row, code_quality, weight):
    other = (0.5 - weight) / 2
    return 100 * (.5 * row["functional"] + other * row["quality"] + other * row["security"] + weight * code_quality / 100)


def priced(receipt, model):
    """Recompute the API-equivalent cost from the receipt at the published list rates."""
    usage, rate = receipt["usage"], RATES_PER_MILLION[model]
    cached = min(usage["cached_input_tokens"], usage["input_tokens"])
    return ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    v317 = root / "runs-code-quality-maintenance-v3.17"
    summary = read(v317 / "summary.json")
    manifest = {r["id"]: r for r in read(v317 / "private-manifest.json")}
    protocol = read(v317 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-gpt6-sol-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == 115 and summary["published_submissions"] == 114
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert comparison["excluded"] == [] and comparison["missing"] == [] and len(comparison["rows"]) == 115
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    assert comparison["cells"] == {f"gpt6sol/{e}": 23 for e in EFFORTS}
    assert protocol["population"]["excluded"] == [] and protocol["population"]["missing"] == []
    priced_record = {r["run_id"]: r for r in comparison["rows"]}
    # The summary is not marked ready only because of its strict count: exactly one row is unpublished, and it is the
    # one whose Grok probe folder carries the operator-invalid marker.
    invalid = {p.parent.name for p in (v317 / "calls").glob(f"*/probe/*/{INVALID_MARKER}")}
    unpublished = {r["id"] for r in summary["rows"] if not r.get("published")}
    assert unpublished == invalid == {"submission-061"}, (unpublished, invalid)
    assert {(manifest[i]["model"], manifest[i]["effort"], manifest[i]["task"]) for i in unpublished} == UNPUBLISHED
    assert not summary["ready_for_publication"] and summary["published_submissions"] + len(unpublished) == summary["expected_submissions"]
    marker_path = v317 / "calls/grok/probe/submission-061" / INVALID_MARKER
    marker = read(marker_path)
    assert set(marker["malformed_attempts"]) == {"1"} and set(marker["unsupported_excerpts"]) == {"2"}
    assert "no match call is made" in marker["action"]
    # The one operator recovery: trailing braces after a complete JSON review, nothing edited.
    recovered_path = v317 / "calls/grok/primary/submission-035/selected.json"
    recovered = read(recovered_path)
    recovery = recovered["operator_recovery"]
    assert recovery["removed"] == "\n}" and recovery["source_attempt"] == 1 and "no field edited" in recovery["method"]
    assert abs(recovered["score"] - 79.16666666666667) < 1e-9
    assert {(manifest[i]["model"], manifest[i]["effort"], manifest[i]["task"]) for i in RECOVERED} == set(RECOVERED.values())
    recoveries = [p.parent.name for p in (v317 / "calls").glob("*/*/*/selected.json") if "operator_recovery" in read(p)]
    assert recoveries == ["submission-035"], recoveries
    # Every solver summary in the sweep folder is a population row: 115 in all. One extra folder, the max depotcore
    # attempt the API refused at capacity, has no summary and is not part of any cell.
    sweep = root / "runs-effort-gpt6-sol"
    summaries = {p.parent.name: p for p in sweep.glob("*/legacy-*/summary.json")}
    assert len(summaries) == 115 and set(summaries) == set(priced_record)
    orphans = [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    assert len(orphans) == 1 and (orphans[0].parent.name, orphans[0].name.rsplit("-", 1)[0]) == CAPACITY_RETRY
    stream = (orphans[0] / "cli-agent-stream.jsonl").read_text().strip().splitlines()
    assert "Selected model is at capacity" in stream[-1]
    capacity_trace = [json.loads(line) for line in (orphans[0] / "trace.jsonl").read_text().strip().splitlines()]
    capacity_minutes = round((datetime.fromisoformat(capacity_trace[-1]["ts"]) - datetime.fromisoformat(capacity_trace[0]["ts"])).total_seconds() / 60)
    assert capacity_minutes == 8, capacity_minutes
    entries = summary["rows"]
    assert len(entries) == 115
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in entries:
        run = manifest[entry["id"]]
        receipt = run["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        record = priced_record[run["run_id"]]
        assert record["model"] == entry["model"] == "gpt6sol" and record["effort"] == entry["effort"] and record["task"] == entry["task"]
        # The population record carries the cost the sweep stamped at run time; recompute it from the receipt.
        assert abs(priced(receipt, entry["model"]) - record["api_equivalent_cost_usd"]) < 1e-5, run["run_id"]
        assert abs(run["api_equivalent_cost_usd"] - record["api_equivalent_cost_usd"]) < 1e-9, run["run_id"]
        assert run["solver_cli_version"] == CLI_VERSION and not run.get("fallback")
        solver = read(summaries[run["run_id"]])
        assert solver["finished"] is True and solver["duration_s"] < 10800
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS) and not any(panels[p]["reviewer_fallback"] for p in PANELS)
        if entry["id"] in unpublished:
            assert panels["grok"]["l2"] is None and panels["muse"]["l2"] is not None and run["functional"] < 1
            l1 = l2 = code_quality = combined_33 = combined_20 = redistributed = panel_record = None
            judged = UNPUBLISHED_NOTE
        else:
            published = entry["published"]
            l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
            redistributed = published["l2_redistributed"]
            if redistributed:
                assert all(panels[p]["l2"] is None and panels[p]["l2_denominator"] == 0 for p in PANELS)
                l2, code_quality = None, l1
            else:
                assert all(panels[p]["l2"] is not None for p in PANELS)
                l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
                code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
            assert abs(code_quality - published["code_quality"]) < 1e-9
            combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
            combined_20 = composite(run, code_quality, 0.20)
            assert abs(combined_33 - published["composite_v3"]) < 1e-9
            assert abs(combined_20 - published["composite_v2_profile"]) < 1e-9
            panel_record = {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                                "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                                "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
                            for p in PANELS}
            judged = "published"
        if entry["id"] in RECOVERED:
            assert abs(panels["grok"]["l1"]["score"] - recovered["score"]) < 1e-9
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": judged, "finished": True, "solver_fallback": False,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"],
            "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
            "cli_summary_units": run.get("reported_tokens"),
            "estimated_usd": record["api_equivalent_cost_usd"],
            "pricing_method": "List rates checked 2026-09-25, stamped by the sweep at run time and recomputed from the Codex receipt "
                              "with cached input billed at the cache-read rate",
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run["solver_cli_version"],
            "evidence_sha256": run["evidence_sha256"],
        })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and len({(r["effort"], r["task"]) for r in rows}) == 115
    assert sum(r["judged"] != "published" for r in rows) == 1
    save("runs.json", {"runs": len(rows), "published": 114, "unpublished": 1, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where the v3.17 summary publishes a Code quality score; the one other row "
                                      "carries the reason its judge-derived fields are null",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                               "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
                       "token_fields": {"raw_tokens": "Codex raw total including cache reads",
                                        "cli_summary_units": "the CLI's own summary count, which for Codex is the same raw total"},
                       "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile", "functional_pct",
                         "automated_quality_pct", "security_pct", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability",
                         "grok_maintainability", "grok_intent_recovery", "passed_quirk_families", "duration_s", "raw_tokens", "estimated_usd",
                         "started_at", "finished_at", "solver_cli_version", "evidence_sha256"])
        for r in rows:
            panels = r["panels"] or {p: {} for p in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], "published" if r["judged"] == "published" else "unpublished",
                             fmt(r["combined_33"]), fmt(r["combined_20_profile"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             "" if r["intent_recovery_redistributed"] is None else r["intent_recovery_redistributed"],
                             *[fmt(panels[p].get(k)) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["duration_s"], r["raw_tokens"], fmt(r["estimated_usd"], 6),
                             r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"]])

    groups = []
    for model, levels in LEVELS.items():
        for effort in levels:
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            assert len(rs) == 23
            judged = [r for r in rs if r["judged"] == "published"]
            scored = [r for r in judged if r["intent_recovery"] is not None]
            groups.append({
                "model": model, "effort": effort, "n": len(judged), "runs": len(rs), "unpublished_runs": len(rs) - len(judged),
                "combined_33": mean_se(r["combined_33"] for r in judged), "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
                "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
                "intent_recovery": mean_se(r["intent_recovery"] for r in scored),
                "intent_recovery_redistributed_runs": len(judged) - len(scored),
                "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
                "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
                "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
                "functional": mean_se(100 * r["functional"] for r in judged), "automated_quality": mean_se(100 * r["automated_quality"] for r in judged),
                "security": mean_se(100 * r["security"] for r in judged),
                # passed counts judged runs; passed_all_runs counts all 23 and is the one to read (the unpublished run failed, so they agree).
                "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
                # Runtime, tokens and cost are facts of the sweep and cover every run in the cell, judged or not.
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_judged_runs": mean_se(r["duration_s"] / 60 for r in judged),
                "solver_fallback_runs": 0, "priced_runs": len(rs),
                "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
                "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            })
            g = groups[-1]
            entry = summary["groups"][f"{model}/{effort}"]
            assert g["n"] == entry["n"] == entry["composite_v3"]["n"]
            assert abs(g["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
            assert abs(g["combined_33"]["se"] - entry["composite_v3"]["se"]) < 1e-9
            assert abs(g["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
            assert g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            for p in PANELS:
                assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
            assert g["passed"] == g["passed_all_runs"]
    assert [g["n"] for g in groups] == [23, 22, 23, 23, 23] and all(g["runs"] == 23 for g in groups)
    assert [g["passed_all_runs"] for g in groups] == [4, 13, 15, 18, 19]

    # The harness card tables carry the combined score, Code quality, pass counts, runtime and cost; match them.
    results = root / "docs/results/swe-v4-gpt6-sol-2026-09"
    with (results / "gpt6-sol-v317-efforts.csv").open(newline="") as source:
        card = {r["effort"]: r for r in csv.DictReader(source)}
    with (results / "gpt6-sol-v317-economics-efforts.csv").open(newline="") as source:
        card_econ = {r["effort"]: r for r in csv.DictReader(source)}
    for g in groups:
        c, ce = card[g["effort"]], card_econ[g["effort"]]
        assert int(c["n"]) == g["n"] and int(c["passed"]) == g["passed_all_runs"]
        # The score card times judged runs (17.9 min at medium); the economics card and this bundle time all 23 (17.5).
        for column, value in (("combined_v3", g["combined_33"]["mean"]), ("combined_v3_se", g["combined_33"]["se"]),
                              ("combined_20pct", g["combined_20_profile"]["mean"]), ("code_quality", g["code_quality"]["mean"]),
                              ("minutes", g["minutes_judged_runs"]["mean"])):
            assert abs(float(c[column]) - value) < 1e-4, (g["effort"], column)
        assert int(ce["n"]) == g["priced_runs"] == 23 and abs(float(ce["total_usd"]) - g["usd_total"]) < 1e-6
        assert int(ce["total_tokens"]) == g["raw_tokens_total"] and abs(float(ce["mean_minutes"]) - g["minutes"]["mean"]) < 1e-4
    # The GPT-6 vs. GPT-5.6 comparison tables carry the same GPT-6 Sol figures, runtime over all runs.
    versus = root / "docs/results/swe-v4-gpt6-vs-gpt56-2026-09"
    for name in ("gpt6-vs-gpt56-sol-efforts.csv", "gpt6-vs-gpt56-all-efforts.csv"):
        with (versus / name).open(newline="") as source:
            table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == "gpt6sol"}
        for g in groups:
            t = table[g["effort"]]
            assert int(t["judged"]) == g["n"] and int(t["passed"]) == g["passed_all_runs"] and t["timeouts"] == "0"
            assert abs(float(t["combined"]) - g["combined_33"]["mean"]) < 1e-4 and abs(float(t["mean_usd"]) - g["usd"]["mean"]) < 1e-6
            assert abs(float(t["mean_minutes"]) - g["minutes"]["mean"]) < 1e-4
    save("groups.json", groups)

    with (SITE / "assets/data/swe-v4-gpt6-sol-v317-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability",
                         "muse_reviewed", "grok_reviewed", "functional", "automated_quality", "security", "passed_of_23", "mean_minutes",
                         "mean_raw_tokens", "mean_usd", "total_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"], f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}',
                             g["passed_all_runs"], f'{g["minutes"]["mean"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}',
                             f'{g["usd_total"]:.6f}'])

    totals = {"gpt6sol": {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                          "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    econ_card = read(results / "gpt6-sol-v317-economics.json")
    assert abs(econ_card["totals"]["gpt6sol"]["usd"] - totals["gpt6sol"]["usd"]) < 1e-6
    assert econ_card["totals"]["gpt6sol"]["tokens"] == totals["gpt6sol"]["raw_tokens"]
    assert abs(econ_card["totals"]["gpt6sol"]["hours"] - totals["gpt6sol"]["solver_hours"]) < 1e-9 and econ_card["pricing_verified"] == "2026-09-25"
    assert f'{totals["gpt6sol"]["usd"]:.2f}' == "221.38"
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a ChatGPT Pro subscription through Codex, "
                 "so these are estimates, not bills. Judging and local infrastructure are excluded. Every run in the sweep is priced, "
                 "including the one Medium run whose Code quality score is unpublished.",
        "pricing_verified": "2026-09-25",
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "limitations": [
            "Codex receipts report input, cached input, output and reasoning tokens per run; cached input is billed at the cache-read rate and "
            "the rest of the input at the standard rate. Cache writes are free on this API and are not modelled.",
            "Standard tier, short-context rates. OpenAI bills prompts over 272K input tokens at a higher rate, but Codex keeps each request "
            "within its 272K context window, so no long-context premium applies and none is modelled.",
            "No Batch, Flex, Fast or priority pricing is applied.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "The sweep stamped each run at run time at the published GPT-6 Sol list rates; the export recomputes every run from its "
            "receipt and matched every stamp.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        record = read(v317 / f"calibration-{panel}.json")
        assert record["passed"] and record["failing_gates"] == [] and not record["allowance_used"]
        assert all(g["passed"] for g in record["gates"].values())
        calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used")}
        calibration[panel]["gates"] = record["gates"]
        calibration[panel]["control_means"] = record["control_means"]
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    save("judge-protocols.json", {
        "scored_panel": {p: public_reviewer(protocol["reviewers"][p]) for p in PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS},
        "protocol_sha256": {p: digest(v317 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"],
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": protocol["population"],
        "unpublished": [{"effort": e, "task": t, "panel": "grok", "stage": "probe", "finding": marker["finding"],
                         "malformed_attempts": marker["malformed_attempts"], "unsupported_excerpts": marker["unsupported_excerpts"],
                         "action": marker["action"]} for _, e, t in sorted(UNPUBLISHED)],
        "operator_recoveries": [{"effort": e, "task": t, "panel": "grok", "stage": "primary", "rule": "recover_trailing_braces",
                                 "method": recovery["method"], "removed": recovery["removed"], "source_attempt": recovery["source_attempt"],
                                 "reviewed_score": recovered["score"],
                                 "checks": "every transport and frozen-validator check applied after the removal: session, subscription guard, "
                                           "no tool use, usage, display label, schema and excerpts"}
                                for _, e, t in RECOVERED.values()],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.17/summary.json": digest(v317 / "summary.json"), "v3.17/protocol.json": digest(v317 / "protocol.json"),
            "v3.17/private-manifest.json": digest(v317 / "private-manifest.json"),
            "v3.17/calibration-muse.json": digest(v317 / "calibration-muse.json"), "v3.17/calibration-grok.json": digest(v317 / "calibration-grok.json"),
            "v3.17/calls/grok/probe/submission-061/operator-invalid.json": digest(marker_path),
            "v3.17/calls/grok/primary/submission-035/selected.json": digest(recovered_path),
            "comparison.json": digest(comparison_path),
            "gpt6-sol-v317-efforts.csv": digest(results / "gpt6-sol-v317-efforts.csv"),
            "gpt6-sol-v317-economics-efforts.csv": digest(results / "gpt6-sol-v317-economics-efforts.csv"),
            "gpt6-vs-gpt56-sol-efforts.csv": digest(versus / "gpt6-vs-gpt56-sol-efforts.csv"),
            "gpt6-vs-gpt56-all-efforts.csv": digest(versus / "gpt6-vs-gpt56-all-efforts.csv"),
        },
        "export_checks": ["115 solver summaries in the sweep folder, one per population row, all finished inside the 3-hour bound; none missing or excluded",
                          "the one sweep folder without a summary is the max depotcore attempt whose Codex stream ends with the API's "
                          "\"Selected model is at capacity\" error; its retry is the counted run",
                          "the one unpublished row is exactly the submission whose Grok probe folder carries the operator-invalid marker",
                          "the one operator recovery is the Grok primary review of submission-035, trailing braces only, no field edited",
                          "both scored panels passed calibration under v3.17 with no allowance used",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "five-cell means and standard errors matched to the frozen summary's groups",
                          "combined score, Code quality, pass counts, runtime, cost and token totals matched to the harness card tables and "
                          "to the GPT-6 vs. GPT-5.6 comparison tables",
                          "every run's API-equivalent cost recomputed from its Codex receipt at the published list rates and matched to the "
                          "population record's run-time stamp",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["The Medium cell's Code quality and combined score cover 22 of its 23 runs: the codeccore run has no published score because "
                   "Grok 4.6's intent probe gave no valid answer after the single retry (one malformed attempt, one quoting code absent from "
                   "the run). The run failed its tests; it counts as a failed task, and its runtime, tokens and cost are in every economics figure.",
                   "The frozen summary's ready_for_publication flag is false only because of that strict count (114 of 115); the export asserts "
                   "the shortfall is exactly that row.",
                   "Grok 4.6's primary review of high payrollcore is published through the formatting-only recover_trailing_braces rule "
                   "(score 79.17). The owner may still invalidate it and score that submission from Muse alone before any republication.",
                   "One attempt per task and level. The first max depotcore attempt ended after "
                   f"{capacity_minutes} minutes when the API reported the model at capacity; the harness re-queued it as an "
                   "infrastructure error and the retry is the counted run.",
                   "The solver sweep ran September 28, 00:31 PDT, to September 29, 14:53 PDT, while GPT-6 Luna's v3.16 judging ran on "
                   "September 28, 00:32 to 14:32 PDT, at the owner's request; that overlap may affect the wall-clock runtime figures."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
