"""Export the public record of the v3.6 GPT-5.6 Terra effort sweep.

Reads the frozen harness artifacts (summary, manifest, protocol, calibration)
and writes a bounded bundle without raw prompts, patches, quirk answer keys or
host paths. Run from the site root:

    python3 scripts/export_swe_v4_v36_evidence.py --harness-root ../VulcanBench
"""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-terra-v36"
LEVELS = {"terra": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["terra"]
NAMES = {"terra": "GPT-5.6 Terra"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
RATES_PER_MILLION = {"terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00}}
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
    v35 = root / "runs-code-quality-maintenance-v3.6"
    v361 = root / "runs-code-quality-maintenance-v3.6.1"
    summary = read(v35 / "summary.json")
    manifest = {r["id"]: r for r in read(v35 / "private-manifest.json")}
    protocol = read(v35 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-terra-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["ready_for_publication"] and summary["published_submissions"] == 114
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert comparison["excluded"] == []
    missing = comparison["missing"]
    assert [(m["model"], m["effort"], m["task"]) for m in missing] == [("terra", "max", "legacy-paddockcore-binary-parity")]
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    # v3.6.1: the run v3.6 recorded missing, judged under the v3.6 calibration once it existed.
    topup = read(v361 / "summary.json")
    topup_protocol = read(v361 / "protocol.json")
    topup_path = root / "docs/results/swe-v4-terra-2026-09/comparison-topup.json"
    assert topup["ready_for_publication"] and topup["published_submissions"] == 1 and topup["protocol"] == "code-quality-maintenance-v3.6.1"
    assert topup["passing_panels"] == ["muse", "grok"]
    assert topup_protocol["top_up_of"]["protocol_sha256"] == digest(v35 / "protocol.json")
    assert topup_protocol["top_up_of"]["summary_sha256"] == digest(v35 / "summary.json")
    assert all(topup_protocol["top_up_of"]["calibration"][p]["sha256"] == digest(v35 / f"calibration-{p}.json") for p in PANELS)
    assert digest(topup_path) == topup_protocol["source_comparison_sha256"]
    assert read(topup_path)["missing"] == [] and read(topup_path)["excluded"] == []
    for r in read(v361 / "private-manifest.json"):
        manifest["topup:" + r["id"]] = r
    entries = summary["rows"] + [{**r, "id": "topup:" + r["id"]} for r in topup["rows"]]
    assert [(r["model"], r["effort"], r["task"]) for r in topup["rows"]] == [("terra", "max", "legacy-paddockcore-binary-parity")]
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in entries:
        run = manifest[entry["id"]]
        entry_protocol = "code-quality-maintenance-v3.6.1" if entry["id"].startswith("topup:") else "code-quality-maintenance-v3.6"
        receipt = run["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        # The frozen record's cost stamp used a stale Terra list price; the run summaries were re-priced at the
        # 2026-09-11 list on 2026-09-16 (originals kept under "repriced"). Publish the receipt price and check it.
        live = read(Path(run["source_directory"]) / "summary.json")
        assert live.get("repriced") and live["repriced"]["original_cost_usd"] == run["api_equivalent_cost_usd"], run["run_id"]
        assert abs(priced(receipt, entry["model"]) - live["economics"]["api_equivalent_cost_usd"]) < 1e-5, run["run_id"]
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS)
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
        redistributed = entry["published"]["l2_redistributed"]
        if redistributed:
            assert all(panels[p]["l2"] is None and panels[p]["l2_denominator"] == 0 for p in PANELS)
            l2, code_quality = None, l1
        else:
            assert all(panels[p]["l2"] is not None for p in PANELS)
            l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
            code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - entry["published"]["code_quality"]) < 1e-9
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": entry_protocol,
            "solver_fallback": bool(run.get("fallback")),
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": composite(run, code_quality, WEIGHTS["code_quality"]),
            "combined_20_profile": composite(run, code_quality, 0.20),
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
                       for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"],
            "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
            "cli_summary_units": run.get("reported_tokens"),
            "estimated_usd": live["economics"]["api_equivalent_cost_usd"],
            "frozen_record_usd": run["api_equivalent_cost_usd"],
            "pricing_method": "List rates checked 2026-09-11; cached input billed at the cache-read rate from the Codex receipt; "
                              "re-priced 2026-09-16 from the sweep's stale run-time stamp",
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run.get("solver_cli_version"),
            "evidence_sha256": run["evidence_sha256"],
        })
        assert abs(rows[-1]["combined_33"] - entry["published"]["composite_v3"]) < 1e-9
        assert abs(rows[-1]["combined_20_profile"] - entry["published"]["composite_v2_profile"]) < 1e-9
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert not any(r["solver_fallback"] for r in rows)
    save("runs.json", {"runs": len(rows), "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                               "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
                       "token_fields": {"raw_tokens": "Codex raw total including cache reads",
                                        "cli_summary_units": "the CLI's own summary count, which for Codex is the same raw total"},
                       "rows": rows})
    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "combined_33", "combined_20_profile", "functional_pct", "automated_quality_pct",
                         "security_pct", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed", "muse_reviewed",
                         "muse_readability", "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability", "grok_maintainability",
                         "grok_intent_recovery", "passed_quirk_families", "duration_s", "raw_tokens", "estimated_usd",
                         "started_at", "finished_at", "solver_cli_version", "evidence_sha256"])

        def fmt(value):
            return "" if value is None else f"{value:.4f}"

        for r in rows:
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], f'{r["combined_33"]:.4f}', f'{r["combined_20_profile"]:.4f}',
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             f'{r["code_quality"]:.4f}', f'{r["reviewed_score"]:.4f}', fmt(r["intent_recovery"]), r["intent_recovery_redistributed"],
                             *[fmt(r["panels"][p][k]) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["duration_s"], r["raw_tokens"], f'{r["estimated_usd"]:.6f}',
                             r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"]])

    groups = []
    for model, levels in LEVELS.items():
        for effort in levels:
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            assert len(rs) == 23
            scored = [r for r in rs if r["intent_recovery"] is not None]
            groups.append({
                "model": model, "effort": effort, "n": len(rs),
                "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
                "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
                "intent_recovery": mean_se(r["intent_recovery"] for r in scored),
                "intent_recovery_redistributed_runs": len(rs) - len(scored),
                "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs),
                "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs),
                "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs) for p in PANELS},
                "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
                "security": mean_se(100 * r["security"] for r in rs), "passed": sum(r["functional"] == 1 for r in rs),
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": sum(r["solver_fallback"] for r in rs),
                "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
                "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            })
            if (model, effort) != ("terra", "max"):
                entry = summary["groups"][f"{model}/{effort}"]
                assert abs(groups[-1]["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
                assert abs(groups[-1]["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
                assert groups[-1]["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            else:  # the max cell merges the 22 v3.6 rows with the v3.6.1 top-up
                base, extra = summary["groups"]["terra/max"], topup["groups"]["terra/max"]
                merged = (base["composite_v3"]["mean"] * base["n"] + extra["composite_v3"]["mean"] * extra["n"]) / (base["n"] + extra["n"])
                assert abs(groups[-1]["combined_33"]["mean"] - merged) < 1e-9
    save("groups.json", groups)
    with (SITE / "assets/data/swe-v4-terra-v36-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability",
                         "muse_reviewed", "grok_reviewed", "functional", "automated_quality", "security", "passed", "mean_minutes",
                         "mean_raw_tokens", "mean_usd", "total_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"],
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
                 "so these are estimates, not bills. Judging and local infrastructure are excluded.",
        "pricing_verified": "2026-09-11",
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["n"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": g["solver_fallback_runs"]} for g in groups],
        "totals": totals,
        "limitations": [
            "Codex receipts report input, cached input, output and reasoning tokens per run; cached input is billed at the cache-read rate and "
            "the rest of the input at the standard rate. Cache writes are free on this API and are not modelled.",
            "Standard tier, short-context rates. Per-request context sizes are not exposed by the receipts, so no long-context premium is applied.",
            "No Batch, Flex, Fast or priority pricing is applied.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "Paddockcore at max ran on September 17, 2026 on a second ChatGPT account after the first account's quota window "
            "closed; it is priced like every other run and judged under the v3.6.1 top-up.",
            "The sweep stamped each run at run time with a stale Terra list price ($2.50 input, $0.20 cached, $15 output); the frozen "
            "population record carries those stamps (frozen_record_usd per run). Every run was re-priced from its receipt at the "
            "2026-09-11 list on 2026-09-16, and estimated_usd is the re-priced value.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        record = read(v35 / f"calibration-{panel}.json")
        calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used")}
        calibration[panel]["gates"] = record["gates"]
        calibration[panel]["control_means"] = record["control_means"]
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    save("judge-protocols.json", {
        "scored_panel": {p: public_reviewer(protocol["reviewers"][p]) for p in PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS},
        "protocol_sha256": {p: digest(v35 / "protocol.json") for p in PANELS},
        "top_up": {"protocol_id": topup_protocol["id"], "protocol_sha256": digest(v361 / "protocol.json"),
                   "rows": [(r["effort"], r["task"]) for r in topup["rows"]], "rule": topup_protocol["top_up_of"]["rule"],
                   "population": topup_protocol["population"]},
        "amends": protocol["amends"],
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": protocol["population"],
        "missing_at_v36": missing,
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.6/summary.json": digest(v35 / "summary.json"), "v3.6/protocol.json": digest(v35 / "protocol.json"),
            "v3.6/private-manifest.json": digest(v35 / "private-manifest.json"),
            "v3.6/calibration-muse.json": digest(v35 / "calibration-muse.json"), "v3.6/calibration-grok.json": digest(v35 / "calibration-grok.json"),
            "comparison.json": digest(comparison_path),
            "v3.6.1/summary.json": digest(v361 / "summary.json"), "v3.6.1/protocol.json": digest(v361 / "protocol.json"),
            "v3.6.1/private-manifest.json": digest(v361 / "private-manifest.json"), "comparison-topup.json": digest(topup_path),
        },
        "export_checks": ["115 published submissions across five effort cells: 114 under v3.6 plus the v3.6.1 top-up of the one run v3.6 recorded missing", "both scored panels passed calibration under v3.6",
                          "every row has both panels' reviewed scores; intent recovery is null only where the submission passed no quirk family",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "every run's API-equivalent cost recomputed from its Codex receipt at the published list rates and matched to the re-priced run summary",
                          "both population records' hashes match the ones frozen in their protocols, and the top-up protocol pins the v3.6 protocol, summary, manifest and calibration hashes", "no dashes or host paths in exported text"],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
