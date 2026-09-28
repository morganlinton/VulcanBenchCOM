"""Export the public record of the v3.16 GPT-6 Luna effort sweep on Frontier v4.

Adapted from the v3.7 Sol export, with the same publication scope: per-run
scores, per-panel sub-scores, aggregates, judge protocol text, calibration
verdicts, raw tokens and API-equivalent cost. Raw prompts, patches, quirk
answer keys and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v316_evidence.py --harness-root ../VulcanBench

Differences from the Sol export, all forced by the sweep:

- Six timeouts. Six runs hit the flat 3-hour task bound while still working
  (extra-high depotcore and paddockcore; max cellarcore, depotcore, lodgecore
  and paddockcore). They have no finished submission, so v3.16 excludes them
  from judging. They stay in the bundle as rows with ``finished`` false,
  count as failed tasks in every pass count, and count in runtime at their
  recorded duration. Codex reported no usage before the bound, so they are
  unpriced: cost and tokens are null, never $0.
- Two combined figures. Each cell carries the standard combined score over
  its judged runs (``combined_33``, comparable with every other board column)
  and ``combined_timeouts_zero``, which counts each timeout as a combined
  score of 0 over all 23 runs (owner decision, harness DECISIONS.md,
  2026-09-28).
- Both judges passed calibration with the pre-registered one-gate allowance.
- Fourteen judged runs passed no quirk family, so intent recovery has no
  denominator and Code quality is the reviewed score alone, under v3's
  pre-registered rule.
- Pricing needs no long-context branch: Codex keeps each request within its
  272K window, so the short-context list rates apply to every token.
"""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-gpt6-luna-v316"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
LEVELS = {"gpt6luna": EFFORTS}
NAMES = {"gpt6luna": "GPT-6 Luna"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
# developers.openai.com/api/docs/pricing, checked 2026-09-25: standard tier, short context.
RATES_PER_MILLION = {"gpt6luna": {"input": 0.10, "cached_input": 0.01, "output": 0.50}}
PROTOCOL_ID = "code-quality-maintenance-v3.16"
CLI_VERSION = "codex-cli 0.155.0"
TIMEOUTS = {("extra-high", "legacy-depotcore-binary-parity"), ("extra-high", "legacy-paddockcore-binary-parity"),
            ("max", "legacy-cellarcore-binary-parity"), ("max", "legacy-depotcore-binary-parity"),
            ("max", "legacy-lodgecore-binary-parity"), ("max", "legacy-paddockcore-binary-parity")}
TIMEOUT_NOTE = ("timeout: the run hit the flat 3-hour task bound while still working, so there is no finished submission and "
                "v3.16 excludes it from judging; it counts as a failed task in every pass count, as a combined score of 0 in "
                "combined_timeouts_zero, and in runtime at its recorded duration; Codex reported no usage before the bound, so it is unpriced")
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


def public_excluded(entry):
    """The population record's excluded entry without its host path."""
    return {k: v for k, v in entry.items() if k != "reason"} | {"reason": "Incomplete source run: stopped at the flat 3-hour task bound"}


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    v316 = root / "runs-code-quality-maintenance-v3.16"
    summary = read(v316 / "summary.json")
    manifest = {r["id"]: r for r in read(v316 / "private-manifest.json")}
    protocol = read(v316 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-gpt6-luna-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == summary["published_submissions"] == 109 and summary["ready_for_publication"]
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert len(comparison["rows"]) == 109 and comparison["missing"] == [] and len(comparison["excluded"]) == 6
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    assert comparison["cells"] == {"gpt6luna/low": 23, "gpt6luna/medium": 23, "gpt6luna/high": 23, "gpt6luna/extra-high": 21, "gpt6luna/max": 19}
    priced_record = {r["run_id"]: r for r in comparison["rows"]}
    # Every solver summary in the sweep folder is either a population row or an excluded timeout: 115 in all.
    sweep = root / "runs-effort-gpt6-luna"
    summaries = {p.parent.name: p for p in sweep.glob("*/legacy-*/summary.json")}
    excluded = {e["run_id"]: e for e in comparison["excluded"]}
    assert len(summaries) == 115 and set(summaries) == set(priced_record) | set(excluded)
    assert {(e["effort"], e["task"]) for e in excluded.values()} == TIMEOUTS
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        receipt = run["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        record = priced_record[run["run_id"]]
        assert record["model"] == entry["model"] == "gpt6luna" and record["effort"] == entry["effort"] and record["task"] == entry["task"]
        # The population record carries the cost the sweep stamped at run time; recompute it from the receipt.
        assert abs(priced(receipt, entry["model"]) - record["api_equivalent_cost_usd"]) < 1e-5, run["run_id"]
        assert abs(run["api_equivalent_cost_usd"] - record["api_equivalent_cost_usd"]) < 1e-9, run["run_id"]
        assert run["solver_cli_version"] == CLI_VERSION and not run.get("fallback")
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS) and not any(panels[p]["reviewer_fallback"] for p in PANELS)
        published = entry["published"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
        redistributed = published["l2_redistributed"]
        if redistributed:
            assert all(panels[p]["l2"] is None and panels[p]["l2_denominator"] == 0 for p in PANELS)
            assert len(run["passed_families"]) == 0
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
            "solver_fallback": False,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "combined_timeouts_zero": combined_33,
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]} for p in PANELS},
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
    for ex in excluded.values():
        s = read(summaries[ex["run_id"]])
        assert ex["finished"] is False and s["finished"] is False and ex["functional"] == 0.0 and s["scores"]["functional"] == 0.0
        assert s["scores"]["budget_exceeded"] and s["verifier"]["budget_exceeded"]
        assert abs(s["duration_s"] - ex["duration_s"]) < 1e-9 and s["duration_s"] >= 10800
        assert s["total_tokens"] == 0 and s["cli_agent"]["harness_version"] == CLI_VERSION
        rows.append({
            "model": ex["model"], "effort": ex["effort"], "task": ex["task"], "run_id": ex["run_id"],
            "judged_under": PROTOCOL_ID, "judged": TIMEOUT_NOTE, "finished": False, "solver_fallback": False,
            "functional": 0.0, "automated_quality": None, "security": None,
            "reviewed_score": None, "intent_recovery": None, "intent_recovery_redistributed": None, "code_quality": None,
            "combined_33": None, "combined_20_profile": None, "combined_timeouts_zero": 0.0, "panels": None,
            "passed_quirk_families": None, "duration_s": s["duration_s"],
            "raw_tokens": None, "token_usage": None, "cli_summary_units": None, "estimated_usd": None,
            "pricing_method": "unpriced: Codex reported no usage before the 3-hour bound",
            "started_at": s["started_at"], "finished_at": s["finished_at"], "solver_cli_version": s["cli_agent"]["harness_version"],
            "evidence_sha256": None,
        })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and len({(r["effort"], r["task"]) for r in rows}) == 115
    assert sum(r["judged"] == "published" for r in rows) == 109
    save("runs.json", {"runs": len(rows), "published": 109, "timeouts": 6, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where the v3.16 summary publishes a Code quality score; the six other rows "
                                      "are timeouts and carry the reason their judge-derived, token and cost fields are null",
                       "timeouts_rule": "combined_timeouts_zero equals combined_33 for a judged run and 0 for a timeout; pass counts treat a "
                                        "timeout as a failed task",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                               "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
                       "token_fields": {"raw_tokens": "Codex raw total including cache reads",
                                        "cli_summary_units": "the CLI's own summary count, which for Codex is the same raw total"},
                       "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "finished", "combined_33", "combined_timeouts_zero",
                         "combined_20_profile", "functional_pct", "automated_quality_pct", "security_pct", "code_quality", "reviewed_score",
                         "intent_recovery", "intent_recovery_redistributed", "muse_reviewed", "muse_readability", "muse_maintainability",
                         "muse_intent_recovery", "grok_reviewed", "grok_readability", "grok_maintainability", "grok_intent_recovery",
                         "passed_quirk_families", "duration_s", "raw_tokens", "estimated_usd", "started_at", "finished_at",
                         "solver_cli_version", "evidence_sha256"])
        for r in rows:
            panels = r["panels"] or {p: {} for p in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], "published" if r["judged"] == "published" else "timeout",
                             r["finished"], fmt(r["combined_33"]), fmt(r["combined_timeouts_zero"]), fmt(r["combined_20_profile"]),
                             f'{100 * r["functional"]:.2f}', "" if r["automated_quality"] is None else f'{100 * r["automated_quality"]:.2f}',
                             "" if r["security"] is None else f'{100 * r["security"]:.2f}',
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]),
                             "" if r["intent_recovery_redistributed"] is None else r["intent_recovery_redistributed"],
                             *[fmt(panels[p].get(k)) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             "" if r["passed_quirk_families"] is None else r["passed_quirk_families"], r["duration_s"],
                             "" if r["raw_tokens"] is None else r["raw_tokens"], fmt(r["estimated_usd"], 6),
                             r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"] or ""])

    groups = []
    for model, levels in LEVELS.items():
        for effort in levels:
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            assert len(rs) == 23
            judged = [r for r in rs if r["judged"] == "published"]
            scored = [r for r in judged if r["intent_recovery"] is not None]
            timeouts = [r for r in rs if not r["finished"]]
            costed = [r for r in rs if r["estimated_usd"] is not None]
            groups.append({
                "model": model, "effort": effort, "n": len(judged), "runs": len(rs), "timeouts": len(timeouts),
                "timeout_tasks": [r["task"] for r in timeouts],
                "combined_33": mean_se(r["combined_33"] for r in judged),
                "combined_timeouts_zero": mean_se(r["combined_timeouts_zero"] for r in rs),
                "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
                "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
                "intent_recovery": mean_se(r["intent_recovery"] for r in scored),
                "intent_recovery_redistributed_runs": len(judged) - len(scored),
                "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
                "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
                "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
                "functional": mean_se(100 * r["functional"] for r in judged), "automated_quality": mean_se(100 * r["automated_quality"] for r in judged),
                "security": mean_se(100 * r["security"] for r in judged),
                # Timeouts are failed tasks, so both pass counts are the same; passed_all_runs is the one to read against 23.
                "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
                # Runtime covers every run in the cell, timeouts at their recorded duration; tokens and cost cover the priced runs.
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": 0,
                "priced_runs": len(costed), "unpriced_timeouts": len(rs) - len(costed),
                "raw_tokens": mean_se(r["raw_tokens"] for r in costed), "raw_tokens_total": sum(r["raw_tokens"] for r in costed),
                "usd": mean_se(r["estimated_usd"] for r in costed), "usd_total": sum(r["estimated_usd"] for r in costed),
            })
            g = groups[-1]
            entry = summary["groups"][f"{model}/{effort}"]
            assert g["n"] == entry["n"] == entry["composite_v3"]["n"] == comparison["cells"][f"{model}/{effort}"]
            assert abs(g["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
            assert abs(g["combined_33"]["se"] - entry["composite_v3"]["se"]) < 1e-9
            assert abs(g["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
            assert g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            for p in PANELS:
                assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
            assert g["passed"] == g["passed_all_runs"] and g["timeouts"] == g["unpriced_timeouts"] == 23 - g["n"]
    assert [g["n"] for g in groups] == [23, 23, 23, 21, 19] and [g["timeouts"] for g in groups] == [0, 0, 0, 2, 4]

    # The harness card tables carry the same two combined figures, pass counts, runtime and cost; match them.
    results = root / "docs/results/swe-v4-gpt6-luna-2026-09"
    with (results / "gpt6-luna-v316-efforts.csv").open(newline="") as source:
        card = {r["effort"]: r for r in csv.DictReader(source)}
    with (results / "gpt6-luna-v316-economics-efforts.csv").open(newline="") as source:
        card_econ = {r["effort"]: r for r in csv.DictReader(source)}
    for g in groups:
        c, ce = card[g["effort"]], card_econ[g["effort"]]
        assert int(c["n"]) == g["n"] and int(c["passed"]) == g["passed_all_runs"] and int(c["timeouts"]) == g["timeouts"]
        for column, value in (("combined_v3", g["combined_33"]["mean"]), ("combined_v3_se", g["combined_33"]["se"]),
                              ("combined_timeouts_zero", g["combined_timeouts_zero"]["mean"]),
                              ("combined_timeouts_zero_se", g["combined_timeouts_zero"]["se"]), ("code_quality", g["code_quality"]["mean"]),
                              ("minutes_all_runs", g["minutes"]["mean"])):
            assert abs(float(c[column]) - value) < 1e-4, (g["effort"], column)
        assert int(ce["priced_runs"]) == g["priced_runs"] and int(ce["unpriced_timeouts"]) == g["unpriced_timeouts"]
        assert abs(float(ce["total_usd"]) - g["usd_total"]) < 1e-6 and int(ce["total_tokens"]) == g["raw_tokens_total"]
    save("groups.json", groups)

    with (SITE / "assets/data/swe-v4-gpt6-luna-v316-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "timeouts", "combined_33", "combined_33_se", "combined_timeouts_zero",
                         "combined_timeouts_zero_se", "combined_20_profile", "code_quality", "code_quality_se", "reviewed_score",
                         "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability", "muse_reviewed",
                         "grok_reviewed", "functional", "automated_quality", "security", "passed_of_23", "mean_minutes_all_runs",
                         "priced_runs", "mean_raw_tokens", "mean_usd", "total_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], g["timeouts"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}',
                             f'{g["combined_timeouts_zero"]["mean"]:.4f}', f'{g["combined_timeouts_zero"]["se"]:.4f}',
                             f'{g["combined_20_profile"]["mean"]:.4f}', f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}',
                             f'{g["reviewed_score"]["mean"]:.4f}', f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"],
                             f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}',
                             f'{g["by_panel"]["grok"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}',
                             f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], f'{g["minutes"]["mean"]:.4f}', g["priced_runs"],
                             f'{g["raw_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd_total"]:.6f}'])

    costed = [r for r in rows if r["estimated_usd"] is not None]
    totals = {"gpt6luna": {"runs": len(rows), "priced_runs": len(costed), "unpriced_timeouts": len(rows) - len(costed),
                           "usd": sum(r["estimated_usd"] for r in costed), "raw_tokens": sum(r["raw_tokens"] for r in costed),
                           "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    econ_card = read(results / "gpt6-luna-v316-economics.json")
    assert abs(econ_card["totals"]["usd"] - totals["gpt6luna"]["usd"]) < 1e-6 and econ_card["totals"]["tokens"] == totals["gpt6luna"]["raw_tokens"]
    assert abs(econ_card["totals"]["hours"] - totals["gpt6luna"]["solver_hours"]) < 1e-9 and econ_card["pricing_verified"] == "2026-09-25"
    assert econ_card["prices_per_million"] == {"input": 0.1, "cached": 0.01, "output": 0.5}
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a ChatGPT Pro subscription through Codex, "
                 "so these are estimates, not bills. Judging and local infrastructure are excluded. 109 of 115 runs are priced; the six "
                 "runs that hit the 3-hour bound ended before Codex reported usage and are unpriced, not $0, so extra-high and max "
                 "spend is understated. Runtime covers all 115 runs.",
        "pricing_verified": "2026-09-25",
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["priced_runs"], "runs": g["runs"],
                    "unpriced_timeouts": g["unpriced_timeouts"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "unpriced": [{"effort": r["effort"], "task": r["task"], "duration_s": r["duration_s"]} for r in rows if r["estimated_usd"] is None],
        "limitations": [
            "Codex receipts report input, cached input, output and reasoning tokens per run; cached input is billed at the cache-read rate and "
            "the rest of the input at the standard rate. Cache writes are free on this API and are not modelled.",
            "Standard tier, short-context rates. OpenAI bills prompts over 272K input tokens at a higher rate, but Codex keeps each request "
            "within its 272K context window, so no long-context premium applies and none is modelled.",
            "No Batch, Flex, Fast or priority pricing is applied.",
            "The six timed-out runs have no usage receipt. They are unpriced and excluded from cost and token means and totals; level means "
            "cover priced runs only, so extra-high and max spend is understated.",
            "The estimate covers the solver's exposed receipts, not an independently observed API invoice.",
            "The sweep stamped each run at run time at the published GPT-6 Luna list rates; the export recomputes every priced run from its "
            "receipt and matched every stamp.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    expected_failing = {"muse": (["g11_repeatability"], 0.06), "grok": (["g04_formatting_is_presentation"], 0.10)}
    for panel in PANELS:
        record = read(v316 / f"calibration-{panel}.json")
        gates, shortfall = expected_failing[panel]
        assert record["passed"] and record["allowance_used"] and record["failing_gates"] == gates
        assert abs(record["gates"][gates[0]]["shortfall"] - shortfall) < 1e-9 and shortfall <= record["allowance"]["max_shortfall"]
        assert sum(not g["passed"] for g in record["gates"].values()) == 1
        calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used")}
        calibration[panel]["gates"] = record["gates"]
        calibration[panel]["control_means"] = record["control_means"]
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    population = dict(protocol["population"])
    population["excluded"] = [public_excluded(e) for e in population["excluded"]]
    save("judge-protocols.json", {
        "scored_panel": {p: public_reviewer(protocol["reviewers"][p]) for p in PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS},
        "protocol_sha256": {p: digest(v316 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"],
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": population,
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.16/summary.json": digest(v316 / "summary.json"), "v3.16/protocol.json": digest(v316 / "protocol.json"),
            "v3.16/private-manifest.json": digest(v316 / "private-manifest.json"),
            "v3.16/calibration-muse.json": digest(v316 / "calibration-muse.json"), "v3.16/calibration-grok.json": digest(v316 / "calibration-grok.json"),
            "comparison.json": digest(comparison_path),
            **{f"runs-effort-gpt6-luna/{r['effort']}/{r['run_id']}/summary.json": digest(summaries[r["run_id"]]) for r in rows if not r["finished"]},
            "gpt6-luna-v316-efforts.csv": digest(results / "gpt6-luna-v316-efforts.csv"),
            "gpt6-luna-v316-economics-efforts.csv": digest(results / "gpt6-luna-v316-economics-efforts.csv"),
        },
        "export_checks": ["115 solver summaries in the sweep folder: 109 population rows and 6 excluded timeouts, none missing",
                          "every timeout is finished false, scored 0 functional with the budget exceeded, ran at least 10800 s and reported no tokens",
                          "all 109 population rows carry a published Code quality score; the frozen summary is ready for publication",
                          "both scored panels passed calibration under v3.16, each with exactly one failing gate inside the 0.5 allowance",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "five-cell means and standard errors matched to the frozen summary's groups",
                          "both combined figures, pass counts, timeouts, runtime, cost and token totals matched to the harness card tables",
                          "every priced run's API-equivalent cost recomputed from its Codex receipt at the published list rates and matched to "
                          "the population record's run-time stamp",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["Six runs hit the flat 3-hour task bound while still working (extra-high 2, max 4). They have no finished submission, so "
                   "the extra-high cell's Code quality and standard combined score cover 21 of its 23 runs and the max cell's 19 of its 23. "
                   "combined_timeouts_zero counts each timeout as 0 over all 23. Pass counts treat every timeout as a failure.",
                   "The timeouts are unpriced: cost and token figures cover the 109 priced runs, so extra-high and max spend is understated.",
                   "One attempt per task and level; the extra-high pacecore run was stopped by the operator after an 88-minute Codex client "
                   "stall and retried, and the retry is the counted run."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
