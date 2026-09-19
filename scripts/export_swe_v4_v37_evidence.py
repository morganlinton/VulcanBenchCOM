"""Export the public record of the v3.7 GPT-5.6 Sol effort sweep.

Reads the frozen harness artifacts (summary, manifest, protocol, calibration)
and writes a bounded bundle without raw prompts, patches, quirk answer keys or
host paths. Run from the site root:

    python3 scripts/export_swe_v4_v37_evidence.py --harness-root ../VulcanBench
"""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-sol-v37"
LEVELS = {"sol": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["sol"]
NAMES = {"sol": "GPT-5.6 Sol"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
RATES_PER_MILLION = {"sol": {"input": 4.00, "cached_input": 0.40, "output": 20.00}}
PROTOCOL_ID = "code-quality-maintenance-v3.7"
INVALID_MARKER = "operator-invalid.json"
# The one submission the frozen v3.7 summary leaves unpublished: Grok 4.6's intent probe quoted an excerpt absent
# from the code on both attempts and no recovery rule accepts an invented character, so no match call was made
# and the protocol publishes no Code quality score for the run. Its tests, timing and receipt are facts of the sweep.
UNPUBLISHED = {("sol", "max", "legacy-codeccore-binary-parity")}
UNPUBLISHED_NOTE = ("unpublished: Grok 4.6's intent probe quoted an excerpt absent from the code on both attempts "
                    "(a character inserted inside a string literal), which no recovery rule accepts, so no answer-key match "
                    "was made and the v3.7 summary publishes no Code quality or combined score for this run; both judges' "
                    "reviews and the Muse probe are retained in the harness archive; the run passed its tests and is priced")
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/")


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
    v37 = root / "runs-code-quality-maintenance-v3.7"
    summary = read(v37 / "summary.json")
    manifest = {r["id"]: r for r in read(v37 / "private-manifest.json")}
    protocol = read(v37 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-sol-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == 115 and summary["published_submissions"] == 114
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert comparison["excluded"] == [] and comparison["missing"] == [] and len(comparison["rows"]) == 115
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    priced_record = {r["run_id"]: r for r in comparison["rows"]}
    # The summary is not marked ready only because of its strict count: exactly one row is unpublished, and it is the
    # one whose Grok probe folder carries the operator-invalid marker.
    invalid = {p.parent.name for p in (v37 / "calls").glob(f"*/probe/*/{INVALID_MARKER}")}
    unpublished = {r["id"] for r in summary["rows"] if not r.get("published")}
    assert unpublished == invalid == {"submission-023"}, (unpublished, invalid)
    assert {(manifest[i]["model"], manifest[i]["effort"], manifest[i]["task"]) for i in unpublished} == UNPUBLISHED
    assert not summary["ready_for_publication"] and summary["published_submissions"] + len(unpublished) == summary["expected_submissions"]
    marker = read(v37 / "calls/grok/probe/submission-023" / INVALID_MARKER)
    assert set(marker["unsupported_excerpts"]) == {"1", "2"} and "no match call is made" in marker["action"]
    entries = summary["rows"]
    assert len(entries) == 115
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in entries:
        run = manifest[entry["id"]]
        receipt = run["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        # The population record carries the cost the sweep stamped at run time at the published list rates; recompute it.
        record = priced_record[run["run_id"]]
        assert record["model"] == entry["model"] and record["effort"] == entry["effort"] and record["task"] == entry["task"]
        assert abs(priced(receipt, entry["model"]) - record["api_equivalent_cost_usd"]) < 1e-5, run["run_id"]
        assert abs(run["api_equivalent_cost_usd"] - record["api_equivalent_cost_usd"]) < 1e-9, run["run_id"]
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS)
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
        published = entry.get("published")
        if entry["id"] in unpublished:
            assert panels["grok"]["l2"] is None and panels["muse"]["l2"] is not None
            l1 = l2 = code_quality = combined_33 = combined_20 = None
            redistributed = None
            panel_record = None
            judged = UNPUBLISHED_NOTE
        else:
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
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": judged,
            "solver_fallback": bool(run.get("fallback")),
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20,
            "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"],
            "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
            "cli_summary_units": run.get("reported_tokens"),
            "estimated_usd": record["api_equivalent_cost_usd"],
            "pricing_method": "List rates checked 2026-09-11, stamped by the sweep at run time and recomputed from the Codex receipt "
                              "with cached input billed at the cache-read rate",
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run.get("solver_cli_version"),
            "evidence_sha256": run["evidence_sha256"],
        })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert not any(r["solver_fallback"] for r in rows)
    assert sum(r["judged"] != "published" for r in rows) == 1 and len(rows) == 115
    save("runs.json", {"runs": len(rows), "published": sum(r["judged"] == "published" for r in rows), "weights": WEIGHTS,
                       "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where the v3.7 summary publishes a Code quality score; the one other row "
                                      "carries the reason its judge-derived fields are null",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                               "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
                       "token_fields": {"raw_tokens": "Codex raw total including cache reads",
                                        "cli_summary_units": "the CLI's own summary count, which for Codex is the same raw total"},
                       "rows": rows})
    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile", "functional_pct",
                         "automated_quality_pct", "security_pct", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability",
                         "grok_maintainability", "grok_intent_recovery", "passed_quirk_families", "duration_s", "raw_tokens", "estimated_usd",
                         "started_at", "finished_at", "solver_cli_version", "evidence_sha256"])

        def fmt(value):
            return "" if value is None else f"{value:.4f}"

        for r in rows:
            panels = r["panels"] or {p: {} for p in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], "published" if r["judged"] == "published" else "unpublished",
                             fmt(r["combined_33"]), fmt(r["combined_20_profile"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             "" if r["intent_recovery_redistributed"] is None else r["intent_recovery_redistributed"],
                             *[fmt(panels[p].get(k)) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["duration_s"], r["raw_tokens"], f'{r["estimated_usd"]:.6f}',
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
                "security": mean_se(100 * r["security"] for r in judged), "passed": sum(r["functional"] == 1 for r in judged),
                "passed_all_runs": sum(r["functional"] == 1 for r in rs),
                # Runtime, tokens and cost are facts of the sweep and cover every run in the cell, judged or not.
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": sum(r["solver_fallback"] for r in rs),
                "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
                "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            })
            entry = summary["groups"][f"{model}/{effort}"]
            assert groups[-1]["n"] == entry["n"] == entry["composite_v3"]["n"]
            assert abs(groups[-1]["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
            assert abs(groups[-1]["combined_33"]["se"] - entry["composite_v3"]["se"]) < 1e-9
            assert abs(groups[-1]["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
            assert groups[-1]["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            for p in PANELS:
                assert abs(groups[-1]["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
    assert [g["n"] for g in groups] == [23, 23, 23, 23, 22] and all(g["runs"] == 23 for g in groups)
    save("groups.json", groups)
    with (SITE / "assets/data/swe-v4-sol-v37-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability",
                         "muse_reviewed", "grok_reviewed", "functional", "automated_quality", "security", "passed", "mean_minutes",
                         "mean_raw_tokens", "mean_usd", "total_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"], f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd_total"]:.6f}'])
    totals = {m: {"runs": sum(1 for r in rows if r["model"] == m),
                  "usd": sum(r["estimated_usd"] for r in rows if r["model"] == m),
                  "raw_tokens": sum(r["raw_tokens"] for r in rows if r["model"] == m),
                  "solver_hours": sum(r["duration_s"] for r in rows if r["model"] == m) / 3600}
              for m in LEVELS}
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a ChatGPT subscription through Codex, "
                 "so these are estimates, not bills. Judging and local infrastructure are excluded. Every run in the sweep is priced, "
                 "including the one Max run whose Code quality score is unpublished.",
        "pricing_verified": "2026-09-11",
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": g["solver_fallback_runs"]} for g in groups],
        "totals": totals,
        "limitations": [
            "Codex receipts report input, cached input, output and reasoning tokens per run; cached input is billed at the cache-read rate and "
            "the rest of the input at the standard rate. Cache writes are free on this API and are not modelled.",
            "Standard tier, short-context rates. Per-request context sizes are not exposed by the receipts, so no long-context premium is applied.",
            "No Batch, Flex, Fast or priority pricing is applied.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "The sweep stamped each run at run time at the published Sol list rates; the export recomputes every run from its receipt and "
            "matched every stamp.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        record = read(v37 / f"calibration-{panel}.json")
        assert record["passed"] and record["failing_gates"] == [] and not record["allowance_used"]
        calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used")}
        calibration[panel]["gates"] = record["gates"]
        calibration[panel]["control_means"] = record["control_means"]
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    save("judge-protocols.json", {
        "scored_panel": {p: public_reviewer(protocol["reviewers"][p]) for p in PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS},
        "protocol_sha256": {p: digest(v37 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"],
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": protocol["population"],
        "unpublished": [{"effort": e, "task": t, "panel": "grok", "stage": "probe",
                         "finding": marker["finding"], "unsupported_excerpts": marker["unsupported_excerpts"], "action": marker["action"]}
                        for _, e, t in sorted(UNPUBLISHED)],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.7/summary.json": digest(v37 / "summary.json"), "v3.7/protocol.json": digest(v37 / "protocol.json"),
            "v3.7/private-manifest.json": digest(v37 / "private-manifest.json"),
            "v3.7/calibration-muse.json": digest(v37 / "calibration-muse.json"), "v3.7/calibration-grok.json": digest(v37 / "calibration-grok.json"),
            "v3.7/calls/grok/probe/submission-023/operator-invalid.json": digest(v37 / "calls/grok/probe/submission-023" / INVALID_MARKER),
            "comparison.json": digest(comparison_path),
        },
        "export_checks": ["115 runs across five complete effort cells, none missing or excluded; 114 carry a published Code quality score",
                          "the one unpublished row is exactly the submission whose Grok probe folder carries the operator-invalid marker",
                          "both scored panels passed calibration under v3.7 with no allowance used",
                          "every published row has both panels' reviewed scores and intent recovery; no row passed zero quirk families",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "five-cell means and standard errors matched to the frozen summary's groups",
                          "every run's API-equivalent cost recomputed from its Codex receipt at the published list rates and matched to the "
                          "population record's run-time stamp",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["The Max cell's Code quality and combined score cover 22 of its 23 runs: the codeccore run has no published score because "
                   "Grok 4.6's intent probe quoted an excerpt absent from the code on both attempts and the frozen protocol accepts no invented "
                   "characters. The run passed its tests; its runtime, tokens and cost are included in every economics figure.",
                   "The frozen summary's ready_for_publication flag is false only because of that strict count (114 of 115); the export asserts "
                   "the shortfall is exactly that row."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
