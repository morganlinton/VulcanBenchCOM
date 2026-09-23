"""Export the public record of the v3.11 Devin SWE-2 effort sweep.

Reads the frozen harness artifacts (summary, manifest, protocol, the two
population records and the three calibration verdicts) and writes a bounded
bundle without raw prompts, patches, quirk answer keys or host paths. Run from
the site root:

    python3 scripts/export_swe_v4_v311_evidence.py --harness-root ../VulcanBench
"""

import argparse
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-devin-swe2-v311"
LEVELS = {"swe2": ("medium", "high", "max")}
EFFORTS = LEVELS["swe2"]
NAMES = {"swe2": "Devin SWE-2"}
PANELS = ("muse",)
FAILED_PANELS = ("grok", "sol")
PANEL_NAMES = {"muse": "Muse Spark 1.3", "grok": "Grok 4.6", "sol": "GPT-5.6 Sol"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.11"
INVALID_MARKER = "operator-invalid.json"
# Cognition publishes no per-token rate for SWE-2, and its catalog's "Free" tier is a promotion dated through
# 2026-10-10 rather than a price, so cost is reported as unavailable, never as zero. Every run's cost field is null,
# matching the population record. What is measured instead is tokens, runtime and Devin's own credit and ACU counters.
COST_UNAVAILABLE = None
PRICING_METHOD = ("unavailable: Cognition publishes no per-token rate for SWE-2, and the catalog's Free tier is a "
                  "promotion dated through 2026-10-10 rather than a rate, so no cost is estimated; the receipts' own "
                  "Devin credit and ACU counters are recorded per run instead")
# The four runs the v3.11 population builder excludes rather than judges. Each one counts as a functional fail in the sweep.
EXCLUDED_TASKS = {
    ("high", "legacy-cellarcore-binary-parity"): "reached the 3-hour task budget before verification",
    ("high", "legacy-snapcore-binary-parity"): "changed no recognized source file",
    ("high", "legacy-vaultcore-binary-parity"): "changed no recognized source file",
    ("max", "legacy-freightcore-binary-parity"): "changed no recognized source file",
}
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/")
HOST_PATH = re.compile(r"(?:/Users|/home)/[^/]+/(?:dev/)?VulcanBench/")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scrub(value):
    """Strip the operator's host prefix from any recorded path, keeping the repository-relative part."""
    if isinstance(value, str):
        return HOST_PATH.sub("", value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def save(name, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert not any(mark in text for mark in FORBIDDEN), name
    assert "SWE v4" not in text, name
    (DEST / name).write_text(text)


def mean_se(values):
    values = list(values)
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "se": statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0}


def composite(row, code_quality, weight):
    other = (0.5 - weight) / 2
    return 100 * (.5 * row["functional"] + other * row["quality"] + other * row["security"] + weight * code_quality / 100)


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    v311 = root / "runs-code-quality-maintenance-v3.11"
    v39 = root / "runs-code-quality-maintenance-v3.9"
    v310 = root / "runs-code-quality-maintenance-v3.10"
    results = root / "docs/results/swe-v4-devin-swe2-2026-09"
    summary = read(v311 / "summary.json")
    manifest = {r["id"]: r for r in read(v311 / "private-manifest.json")}
    protocol = read(v311 / "protocol.json")
    judged_path = results / "comparison-judged.json"
    sweep_path = results / "comparison.json"
    judged_record = read(judged_path)
    sweep_record = read(sweep_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == summary["published_submissions"] == 65
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0} and summary["ready_for_publication"]
    assert set(protocol["reviewers"]) == set(PANELS)
    # No submission is left unpublished under v3.11: the four runs that carry no judgeable submission were excluded
    # from the population before any judge call, and no probe was marked invalid.
    assert not list((v311 / "calls").glob(f"*/probe/*/{INVALID_MARKER}"))
    assert all(r.get("published") for r in summary["rows"])
    assert digest(judged_path) == protocol["source_comparison_sha256"]
    assert judged_record["missing"] == [] and len(judged_record["rows"]) == 65
    assert judged_record["cells"] == protocol["population"]["cells"] == {"swe2/high": 20, "swe2/max": 22, "swe2/medium": 23}
    assert judged_record["levels"] == {"swe2": list(EFFORTS)}
    assert len(sweep_record["rows"]) == 68 and len(sweep_record["excluded"]) == 1
    excluded = {(e["effort"], e["task"]): e for e in judged_record["excluded"]}
    assert set(excluded) == set(EXCLUDED_TASKS) and len(excluded) == 4
    assert all(e["functional"] == 0.0 for e in excluded.values())
    unfinished = [e for e in excluded.values() if not e["finished"]]
    assert len(unfinished) == 1 and unfinished[0]["task"] == "legacy-cellarcore-binary-parity"
    judged_by_run = {r["id"]: r for r in summary["rows"]}
    manifest_by_run = {r["run_id"]: r for r in manifest.values()}
    assert len(manifest_by_run) == 65
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for record in sweep_record["rows"]:
        receipt = record["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        # SWE-2 is unpriced: the population record carries no API-equivalent cost for any run.
        assert record["api_equivalent_cost_usd"] is None, record["run_id"]
        assert (receipt.get("devin_credit_cost") or 0) == 0 and (receipt.get("devin_acu_cost") or 0.0) == 0.0
        assert record["solver_cli_version"].startswith("devin ")
        run = manifest_by_run.get(record["run_id"])
        if run is None:
            key = (record["effort"], record["task"])
            assert key in EXCLUDED_TASKS and excluded[key]["finished"], record["run_id"]
            assert record["quality"] is None and record["security"] is None and record["functional"] == 0.0
            rows.append({
                "model": record["model"], "effort": record["effort"], "task": record["task"], "run_id": record["run_id"],
                "judged_under": PROTOCOL_ID, "judged": f"excluded: {EXCLUDED_TASKS[key]}, so the sweep's automated quality and "
                                                       "security metrics are undefined and there is no submission to judge; "
                                                       "the run counts as a functional fail",
                "finished": True, "solver_fallback": bool(record.get("fallback")),
                "functional": record["functional"], "automated_quality": None, "security": None,
                "reviewed_score": None, "intent_recovery": None, "intent_recovery_redistributed": None, "code_quality": None,
                "combined_33": None, "combined_20_profile": None, "panels": None, "passed_quirk_families": None,
                "duration_s": record["duration_s"], "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
                "cli_summary_units": record.get("reported_tokens"),
                "devin_credits": receipt.get("devin_credit_cost") or 0, "devin_acu": receipt.get("devin_acu_cost") or 0.0,
                "estimated_usd": COST_UNAVAILABLE, "pricing_method": PRICING_METHOD,
                "started_at": record["started_at"], "finished_at": record["finished_at"],
                "solver_cli_version": record["solver_cli_version"], "evidence_sha256": None,
            })
            continue
        entry = judged_by_run[run["id"]]
        assert (entry["model"], entry["effort"], entry["task"]) == (record["model"], record["effort"], record["task"])
        assert abs(run["duration_s"] - record["duration_s"]) < 1e-9 and run["solver_receipt"]["raw_tokens"] == receipt["raw_tokens"]
        panels = entry["panels"]
        published = entry["published"]
        assert all(panels[p]["l1"] is not None for p in PANELS)
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
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
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": "published", "finished": True,
            "solver_fallback": bool(run.get("fallback")),
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20,
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
                       for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"],
            "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
            "cli_summary_units": record.get("reported_tokens"),
            "devin_credits": receipt.get("devin_credit_cost") or 0, "devin_acu": receipt.get("devin_acu_cost") or 0.0,
            "estimated_usd": COST_UNAVAILABLE, "pricing_method": PRICING_METHOD,
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run.get("solver_cli_version"),
            "evidence_sha256": run["evidence_sha256"],
        })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert not any(r["solver_fallback"] for r in rows)
    assert len(rows) == 68 and sum(r["judged"] == "published" for r in rows) == 65
    not_finished = [{"model": e["model"], "effort": e["effort"], "task": e["task"], "run_id": e["run_id"],
                     "judged_under": PROTOCOL_ID, "judged": f"excluded: {EXCLUDED_TASKS[k]}; the run did not finish, so it has "
                                                            "no receipt and no tokens, and it counts as a functional fail",
                     "finished": False, "functional": e["functional"], "duration_s": e["duration_s"],
                     "reason_recorded": scrub(e["reason"])}
                    for k, e in sorted(excluded.items()) if not e["finished"]]
    save("runs.json", {
        "runs_attempted": len(rows) + len(not_finished), "runs_finished": len(rows),
        "published": sum(r["judged"] == "published" for r in rows), "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
        "panel": [PANEL_NAMES[p] for p in PANELS],
        "judged_rule": "judged is \"published\" where the v3.11 summary publishes a Code quality score; the other rows carry the "
                       "reason the population builder excluded them before any judge call",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
        "cost_rule": "estimated_usd is null on every run: Cognition publishes no per-token rate for SWE-2, and the catalog's "
                     "Free tier is a promotion dated through 2026-10-10 rather than a rate, so a cost figure would be invented. "
                     "devin_credits and devin_acu are the receipts' own counters, recorded as measured",
        "token_fields": {"raw_tokens": "Devin CLI raw total including cache reads, deduplicated by request id",
                         "cli_summary_units": "the CLI's own summary count, which for Devin is the same raw total"},
        "rows": rows, "did_not_finish": not_finished})
    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile", "functional_pct",
                         "automated_quality_pct", "security_pct", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery", "passed_quirk_families", "duration_s",
                         "raw_tokens", "devin_credits", "devin_acu", "estimated_usd", "started_at", "finished_at", "solver_cli_version",
                         "evidence_sha256"])

        def fmt(value):
            return "" if value is None else f"{value:.4f}"

        def pct(value):
            return "" if value is None else f"{100 * value:.2f}"

        for r in rows:
            panels = r["panels"] or {p: {} for p in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"],
                             "published" if r["judged"] == "published" else "excluded",
                             fmt(r["combined_33"]), fmt(r["combined_20_profile"]),
                             pct(r["functional"]), pct(r["automated_quality"]), pct(r["security"]),
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             "" if r["intent_recovery_redistributed"] is None else r["intent_recovery_redistributed"],
                             *[fmt(panels[p].get(k)) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             "" if r["passed_quirk_families"] is None else r["passed_quirk_families"], r["duration_s"], r["raw_tokens"],
                             r["devin_credits"], f'{r["devin_acu"]:.1f}', "",  # cost is unavailable, never zero
                             r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"] or ""])

    groups = []
    for model, levels in LEVELS.items():
        for effort in levels:
            # Runtime and tokens cover every finished run in the cell; scores cover the judged ones.
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            judged = [r for r in rs if r["judged"] == "published"]
            scored = [r for r in judged if r["intent_recovery"] is not None]
            attempted = len(rs) + sum(1 for r in not_finished if r["effort"] == effort)
            groups.append({
                "model": model, "effort": effort, "n": len(judged), "runs": len(rs), "runs_attempted": attempted,
                "excluded_runs": attempted - len(judged),
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
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": sum(r["solver_fallback"] for r in rs),
                "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
                "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
                "output_tokens_total": sum(r["token_usage"]["output_tokens"] for r in rs),
                "usd": None, "usd_total": None, "cost": "unavailable",
            })
            entry = summary["groups"][f"{model}/{effort}"]
            assert groups[-1]["n"] == entry["n"] == entry["composite_v3"]["n"]
            assert abs(groups[-1]["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
            assert abs(groups[-1]["combined_33"]["se"] - entry["composite_v3"]["se"]) < 1e-9
            assert abs(groups[-1]["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
            assert groups[-1]["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            for p in PANELS:
                assert abs(groups[-1]["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
    assert [g["n"] for g in groups] == [23, 20, 22] and [g["runs"] for g in groups] == [23, 22, 23]
    assert [g["runs_attempted"] for g in groups] == [23, 23, 23]
    assert [g["passed"] for g in groups] == [15, 15, 21]
    # Every excluded run is a functional fail, so the sweep's pass counts equal the judged cells' pass counts.
    assert [g["passed_all_runs"] for g in groups] == [g["passed"] for g in groups]
    save("groups.json", groups)
    with (SITE / "assets/data/swe-v4-devin-swe2-v311-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs_finished", "runs_attempted", "combined_33", "combined_33_se", "combined_20_profile",
                         "code_quality", "code_quality_se", "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs",
                         "readability", "maintainability", "muse_reviewed", "functional", "automated_quality", "security", "passed",
                         "mean_minutes", "mean_raw_tokens", "mean_output_tokens", "cost_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], g["runs_attempted"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"], f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}', f'{g["output_tokens"]["mean"]:.1f}',
                             "unavailable"])
    totals = {m: {"runs_attempted": sum(1 for r in rows if r["model"] == m) + len(not_finished),
                  "runs": sum(1 for r in rows if r["model"] == m),
                  "usd": None,
                  "raw_tokens": sum(r["raw_tokens"] for r in rows if r["model"] == m),
                  "output_tokens": sum(r["token_usage"]["output_tokens"] for r in rows if r["model"] == m),
                  "solver_hours": sum(r["duration_s"] for r in rows if r["model"] == m) / 3600}
              for m in LEVELS}
    save("economics.json", {
        "scope": "Tokens and runtime for solver inference only, over the 68 finished runs of the sweep. Judging and local "
                 "infrastructure are excluded. No cost is reported: see the cost field.",
        "cost": "unavailable",
        "cost_reason": "Cognition publishes no per-token rate for SWE-2. Its catalog cost tier Free is a promotion dated through "
                       "2026-10-10, not a rate, so any figure derived from it would read as a measured price and would stop being "
                       "true when the promotion ends. The population record carries a null cost for every run. What is measured "
                       "instead is tokens, runtime and Devin's own credit and ACU counters, which read zero throughout.",
        "cost_revisit": "If Cognition publishes a per-token API rate for SWE-2, these runs can be repriced from their receipts and "
                        "the column stops being unavailable.",
        "sources": {"devin": "Devin CLI receipts (the per-request usage records in the CLI's agent stream)"},
        "rates_per_million": None,
        "pricing_verified": None,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "runs_attempted": g["runs_attempted"],
                    "usd": None, "usd_total": None, "cost": "unavailable",
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"],
                    "output_tokens": g["output_tokens"], "output_tokens_total": g["output_tokens_total"],
                    "minutes": g["minutes"], "solver_fallback_runs": g["solver_fallback_runs"]} for g in groups],
        "totals": totals,
        "limitations": [
            "SWE-2 has no public API price, so no cost is estimated and the cost column reads unavailable; the sweep ran on a "
            "Devin subscription. The catalog's Free tier is a promotion dated through 2026-10-10, not a published rate.",
            "Tokens are the Devin CLI's per-request usage receipts, deduplicated by request id: uncached input, cache reads and output.",
            "Devin's own credit and ACU counters are recorded from the receipts and were zero for every run of this sweep. A zero "
            "counter on a subscription is not a price, so it is reported as a counter and not as a cost.",
            "The 68 finished runs are all counted here, the three that changed no source file included. The one run that did not finish "
            "has no receipt and is listed separately; its 3.0 hours of wall clock are not in these totals.",
            "Runtime is solver wall clock as the harness recorded it, judging excluded.",
        ],
        "comparison_sha256": digest(sweep_path),
        "comparison_judged_sha256": digest(judged_path),
        "note": "Per-run records are in runs.json (raw_tokens, token_usage, devin_credits, devin_acu; estimated_usd is null "
                "throughout). Judging is excluded.",
    })

    # Calibration: Muse's passing v3.9 verdict gates this pass, and both failed verdicts are published beside it.
    muse = read(v39 / "calibration-muse.json")
    assert muse["passed"] and muse["failing_gates"] == ["g11_repeatability"] and muse["allowance_used"]
    assert protocol["calibration"]["muse"]["sha256"] == digest(v39 / "calibration-muse.json")
    calibration = {"rule": scrub(protocol["calibration"]["rule"]), "panels": {}}
    for panel, path, source in (("muse", v39 / "calibration-muse.json", "runs-code-quality-maintenance-v3.9/calibration-muse.json"),
                                ("grok", v39 / "calibration-grok.json", "runs-code-quality-maintenance-v3.9/calibration-grok.json"),
                                ("sol", v310 / "calibration-sol.json", "runs-code-quality-maintenance-v3.10/calibration-sol.json")):
        record = read(path)
        assert record["panel"] == panel
        assert record["passed"] is (panel == "muse")
        if panel in FAILED_PANELS:
            assert record["failing_gates"] == ["g16_probe_recovers_documented_intent"] and not record["allowance_used"]
        entry = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used")}
        entry["judge"] = PANEL_NAMES[panel]
        entry["scored"] = panel in PANELS
        entry["source"] = source
        entry["source_sha256"] = digest(path)
        entry["gates"] = record["gates"]
        entry["control_means"] = record["control_means"]
        calibration["panels"][panel] = entry
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    save("judge-protocols.json", {
        "scored_panel": {p: public_reviewer(protocol["reviewers"][p]) for p in PANELS},
        "single_panel_note": "Code quality here is Muse Spark 1.3 alone, not the two-judge mean behind every other Frontier v4 entry. "
                             "Grok 4.6 failed the v3.9 calibration exam and GPT-5.6 Sol failed the v3.10 exam, both on gate 16 "
                             "(invented departures on the clear control), so the protocol's pre-registered single-panel rule applies.",
        "failed_panels": {p: {"judge": PANEL_NAMES[p], "record": calibration["panels"][p]["source"],
                              "failing_gates": calibration["panels"][p]["failing_gates"]} for p in FAILED_PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS},
        "protocol_sha256": {p: digest(v311 / "protocol.json") for p in PANELS},
        "amends": scrub(protocol["amends"]),
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": scrub(protocol["population"]),
        "unpublished": [],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.11/summary.json": digest(v311 / "summary.json"), "v3.11/protocol.json": digest(v311 / "protocol.json"),
            "v3.11/private-manifest.json": digest(v311 / "private-manifest.json"),
            "v3.9/calibration-muse.json": digest(v39 / "calibration-muse.json"),
            "v3.9/calibration-grok.json": digest(v39 / "calibration-grok.json"),
            "v3.10/calibration-sol.json": digest(v310 / "calibration-sol.json"),
            "comparison-judged.json": digest(judged_path), "comparison.json": digest(sweep_path),
        },
        "export_checks": ["69 runs attempted across the three effort levels SWE-2 offers, 68 finished, 65 judged and published",
                          "the four excluded runs are exactly the four the population record lists, each with its reason, and each is a "
                          "functional fail, so the sweep's pass counts equal the judged cells' pass counts",
                          "no probe was marked invalid and the frozen summary publishes a score for all 65 judged submissions",
                          "Muse Spark 1.3 is the only scored panel; both failed calibration verdicts are exported beside its passing one",
                          "every published row has the panel's reviewed score, and the one row that passed no quirk family carries the "
                          "pre-registered redistribution instead of an intent-recovery score",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "three-cell means and standard errors matched to the frozen summary's groups",
                          "no run carries a cost: every cost field is null, matching the population record, and the credit and ACU "
                          "counters are exported as the receipts recorded them",
                          "the judged population record's hash matches the one frozen in the protocol",
                          "no dashes or host paths in exported text"],
        "limits": ["Code quality on this page comes from one judge. Grok 4.6 (v3.9) and GPT-5.6 Sol (v3.10) both failed gate 16 of the "
                   "calibration exam, so under the protocol's pre-registered single-panel rule Devin SWE-2 is scored by Muse Spark 1.3 "
                   "alone rather than by the two-judge panel behind every other Frontier v4 entry.",
                   "Muse passed its exam using the pre-registered one-gate allowance on the repeatability gate, as recorded in "
                   "calibration.json.",
                   "The high cell's Code quality and combined score cover 20 of its 23 runs and the max cell's cover 22 of 23. The "
                   "excluded runs produced no judgeable submission and all count as functional fails.",
                   "The one run that did not finish has no receipt, so it appears in did_not_finish rather than in the token and runtime "
                   "aggregates.",
                   "Cost is unavailable, not zero. Cognition publishes no per-token rate for SWE-2, and the catalog's Free tier is a "
                   "promotion dated through 2026-10-10 rather than a rate, so these runs cannot be priced and are not compared on cost "
                   "with the priced models on this board."],
        "publication_scope": "Per-run scores, the judge's sub-scores, aggregates, judge protocol text, all three calibration verdicts and "
                             "control means, raw tokens, runtime and Devin's own credit and ACU counters. No cost is published.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "finished runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
