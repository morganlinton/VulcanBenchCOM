"""Export the public record of the v3.18 GPT-6.1 Sol effort sweep on Frontier v4.

Adapted from the v3.17 GPT-6 Sol export, with the same publication scope:
per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and API-equivalent cost. Raw prompts,
patches, quirk answer keys and host paths are withheld. Run from the site
root:

    python3 scripts/export_swe_v4_v318_evidence.py --harness-root ../VulcanBench

What differs from the GPT-6 Sol export, all forced by the sweep or its judging:

- Every row is published. The frozen summary publishes all 115 submissions
  and is marked ready for publication, so every cell is judged on 23 runs.
- One one-panel row. Grok 4.6's primary review of submission-054 (medium
  paddockcore) has no valid response: both attempts quoted a changed line, and
  the wrapper rule invalidate_unrecoverable_primary (the owner's v3.14
  precedent) marked the call invalid. The frozen summary publishes that
  submission from Muse alone, reviewed layer and intent recovery both, as it
  does for any submission without two valid reviews. The export reproduces the
  summary's published Code quality and combined scores for every row,
  including this one, from the panels with a valid review.
- One operator recovery: Muse's probe on submission-083 (high codeccore) was
  recovered by the owner-approved escaping rule recover_escaped_excerpts (an
  excerpt whose string escapes were decoded into control characters is
  respelled with the source's escapes and must then be verbatim). The earlier
  invalidation marker is kept beside it, superseded.
- Three evidence rebuilds: three runs add test fixtures that the saved text
  patch cannot re-apply (two binary fixtures, low payrollcore and medium
  lodgecore, and one fixture altered by the text-mode capture, low
  cellarcore), so the v3.18 runner rebuilt them from the saved workspace's
  index diff after checking it against the run's patch. The three method
  records are hashed in provenance.json.
- No infrastructure retry and no timeout: the sweep folder holds exactly the
  115 population runs, all finished inside the 3-hour bound.
- Both judges passed calibration with no allowance used.
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
DEST = SITE / "assets/data/swe-v4-gpt61-sol-v318"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
LEVELS = {"gpt61sol": EFFORTS}
NAMES = {"gpt61sol": "GPT-6.1 Sol"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
# developers.openai.com/api/docs/pricing and the model page, checked 2026-09-29: standard tier, short context.
RATES_PER_MILLION = {"gpt61sol": {"input": 2.00, "cached_input": 0.10, "output": 10.00}}
PRICING_VERIFIED = "2026-09-29"
PROTOCOL_ID = "code-quality-maintenance-v3.18"
CLI_VERSION = "codex-cli 0.159.0"
INVALID_MARKER = "operator-invalid.json"
SUPERSEDED_MARKER = "operator-invalid.superseded.json"
ONE_PANEL = {"submission-054": ("gpt61sol", "medium", "legacy-paddockcore-binary-parity")}
ONE_PANEL_NOTE = ("published from Muse Spark 1.3 alone: Grok 4.6's primary review has no valid response (both attempts quoted a line "
                  "the code does not contain), so the v3.18 summary scores the reviewed layer and intent recovery from Muse only, as it "
                  "does for any submission without two valid reviews")
RECOVERED = {"submission-083": ("gpt61sol", "high", "legacy-codeccore-binary-parity")}
REBUILDS = {"legacy-cellarcore-binary-parity-bdca534c": ("low", "legacy-cellarcore-binary-parity"),
            "legacy-lodgecore-binary-parity-08b754d0": ("medium", "legacy-lodgecore-binary-parity"),
            "legacy-payrollcore-binary-parity-51181245": ("low", "legacy-payrollcore-binary-parity")}
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
    v318 = root / "runs-code-quality-maintenance-v3.18"
    summary = read(v318 / "summary.json")
    manifest = {r["id"]: r for r in read(v318 / "private-manifest.json")}
    protocol = read(v318 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-gpt61-sol-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == summary["published_submissions"] == 115 and summary["ready_for_publication"]
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert comparison["excluded"] == [] and comparison["missing"] == [] and len(comparison["rows"]) == 115
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    assert comparison["cells"] == {f"gpt61sol/{e}": 23 for e in EFFORTS}
    assert protocol["population"]["excluded"] == [] and protocol["population"]["missing"] == []
    priced_record = {r["run_id"]: r for r in comparison["rows"]}
    # Exactly one live invalidation marker: Grok's primary review of submission-054. Muse's probe on submission-083 carries
    # only a superseded marker, replaced by the escaping recovery.
    invalid = {(p.parents[1].parent.name, p.parents[1].name, p.parent.name) for p in (v318 / "calls").glob(f"*/*/*/{INVALID_MARKER}")}
    assert invalid == {("grok", "primary", "submission-054")}, invalid
    superseded = {(p.parents[1].parent.name, p.parents[1].name, p.parent.name) for p in (v318 / "calls").glob(f"*/*/*/{SUPERSEDED_MARKER}")}
    assert superseded == {("muse", "probe", "submission-083")}, superseded
    assert {(manifest[i]["model"], manifest[i]["effort"], manifest[i]["task"]) for i in ONE_PANEL} == set(ONE_PANEL.values())
    marker_path = v318 / "calls/grok/primary/submission-054" / INVALID_MARKER
    marker = read(marker_path)
    assert marker["rule"] == "invalidate_unrecoverable_primary" and marker["malformed_attempts"] == {}
    assert set(marker["unsupported_excerpts"]) == {"1", "2"} and marker["unsupported_excerpts"]["2"] == ["self.standing[pony] += 2"]
    assert not (v318 / "calls/grok/primary/submission-054/selected.json").exists()
    # The one operator recovery: string escapes respelled in one Muse probe excerpt, nothing else edited.
    recovered_path = v318 / "calls/muse/probe/submission-083/selected.json"
    recovered = read(recovered_path)
    recovery = recovered["operator_recovery"]
    assert recovery["source_attempt"] == 2 and "no other field edited" in recovery["method"] and list(recovery["original_excerpts"]) == ["11"]
    assert "Invalid \\escape" in recovery["other_attempt_error"]
    superseded_path = v318 / "calls/muse/probe/submission-083" / SUPERSEDED_MARKER
    assert {(manifest[i]["model"], manifest[i]["effort"], manifest[i]["task"]) for i in RECOVERED} == set(RECOVERED.values())
    recoveries = sorted(f"{p.parents[1].parent.name}/{p.parents[1].name}/{p.parent.name}" for p in (v318 / "calls").glob("*/*/*/selected.json")
                        if "operator_recovery" in read(p))
    assert recoveries == ["muse/probe/submission-083"], recoveries
    # Three evidence rebuilds from the saved workspace's index diff, each checked against the run's patch.
    rebuild_paths = sorted((v318 / "reconstruction").glob("*.json"))
    assert {p.stem for p in rebuild_paths} == set(REBUILDS)
    for path in rebuild_paths:
        record = read(path)
        if path.stem.startswith("legacy-cellarcore"):  # fixture text altered by the text-mode capture: the saved index diff matched exactly
            assert record["method"] == "saved index diff with exact original text-mode normalization match"
        else:  # fixtures git treats as binary: the binary diff applied after its text diff matched the run's patch
            assert "--binary diff applied" in record["method"] and "equals the run's patch" in record["method"]
        assert priced_record[path.stem]["effort"] == REBUILDS[path.stem][0] and priced_record[path.stem]["task"] == REBUILDS[path.stem][1]
    # Every solver summary in the sweep folder is a population row: 115 in all, no orphan attempt folder.
    sweep = root / "runs-effort-gpt61-sol"
    summaries = {p.parent.name: p for p in sweep.glob("*/legacy-*/summary.json")}
    assert len(summaries) == 115 and set(summaries) == set(priced_record)
    assert not [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    entries = summary["rows"]
    assert len(entries) == 115
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in entries:
        run = manifest[entry["id"]]
        receipt = run["solver_receipt"]
        assert type(receipt["raw_tokens"]) is int and receipt["raw_tokens"] > 0
        record = priced_record[run["run_id"]]
        assert record["model"] == entry["model"] == "gpt61sol" and record["effort"] == entry["effort"] and record["task"] == entry["task"]
        # The population record carries the cost the sweep stamped at run time; recompute it from the receipt.
        assert abs(priced(receipt, entry["model"]) - record["api_equivalent_cost_usd"]) < 1e-5, run["run_id"]
        assert abs(run["api_equivalent_cost_usd"] - record["api_equivalent_cost_usd"]) < 1e-9, run["run_id"]
        assert run["solver_cli_version"] == CLI_VERSION and not run.get("fallback")
        solver = read(summaries[run["run_id"]])
        assert solver["finished"] is True and solver["duration_s"] < 10800
        assert solver["cli_agent"]["harness_version"] == CLI_VERSION
        audit = solver["integrity_audit"]
        assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"]
        assert audit["filesystem"]["benchmark_data_paths"] == [] and audit["filesystem"]["answer_key_paths"] == []
        hidden = solver["verifier"]["fail_to_pass"]
        panels = entry["panels"]
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
        scored = [p for p in PANELS if panels[p]["l1"] is not None]
        if entry["id"] in ONE_PANEL:
            assert scored == ["muse"] and panels["grok"]["l1"] is None
            judged = ONE_PANEL_NOTE
        else:
            assert scored == list(PANELS)
            judged = "published"
        published = entry["published"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in scored)
        assert abs(l1 - published["l1"]) < 1e-9
        redistributed = published["l2_redistributed"]
        assert not redistributed  # every run passed at least one quirk family
        assert all(panels[p]["l2"] is not None for p in scored)
        l2 = statistics.mean(panels[p]["l2"] for p in scored)
        assert abs(l2 - published["l2"]) < 1e-9
        code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - published["code_quality"]) < 1e-9
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        combined_20 = composite(run, code_quality, 0.20)
        assert abs(combined_33 - published["composite_v3"]) < 1e-9
        assert abs(combined_20 - published["composite_v2_profile"]) < 1e-9
        if entry["id"] in ONE_PANEL:
            assert abs(code_quality - 54.0043) < 1e-4
        panel_record = {}
        for p in PANELS:
            if p in scored:
                panel_record[p] = {"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                                   "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                                   "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
            else:
                # No valid review, so nothing from this panel enters the score; its probe answer is not used and not published.
                panel_record[p] = {"scored": False, "readability": None, "maintainability": None, "reviewed_score": None, "intent_recovery": None,
                                   "scored_quirks": None, "reviewer_fallback": False}
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": judged, "scored_panels": scored, "finished": True, "solver_fallback": False,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]),
            "evidence_rebuilt_from_index_diff": run["run_id"] in REBUILDS,
            "integrity_audit": {"web": audit["web"]["verdict"], "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
            "duration_s": run["duration_s"],
            "raw_tokens": receipt["raw_tokens"], "token_usage": receipt["usage"],
            "cli_summary_units": run.get("reported_tokens"),
            "estimated_usd": record["api_equivalent_cost_usd"],
            "pricing_method": f"List rates checked {PRICING_VERIFIED}, stamped by the sweep at run time and recomputed from the Codex receipt "
                              "with cached input billed at the cache-read rate",
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run["solver_cli_version"],
            "evidence_sha256": run["evidence_sha256"],
        })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and len({(r["effort"], r["task"]) for r in rows}) == 115
    assert sum(r["judged"] != "published" for r in rows) == 1 and sum(r["evidence_rebuilt_from_index_diff"] for r in rows) == 3
    save("runs.json", {"runs": len(rows), "published": 115, "unpublished": 0, "one_panel": 1, "weights": WEIGHTS,
                       "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where both judges have a valid review; the one other row is also published, "
                                      "from the one judge with a valid review, and its judged field says why",
                       "panel_rule": "reviewed_score and intent_recovery are the equal mean of the panels in scored_panels; a panel with no valid "
                                     "review has scored false and null fields, and nothing from it enters the score",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, "
                                               "intent_recovery is null, intent_recovery_redistributed is true and Code quality equals the reviewed score; "
                                               "no GPT-6.1 Sol run needed this rule",
                       "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests (the documented behaviours the "
                                                  "fix must produce); hidden_behaviours_fixed counts those the run passed",
                       "token_fields": {"raw_tokens": "Codex raw total including cache reads",
                                        "cli_summary_units": "the CLI's own summary count, which for Codex is the same raw total"},
                       "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "scored_panels", "combined_33", "combined_20_profile",
                         "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed", "hidden_behaviours", "code_quality",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability",
                         "grok_maintainability", "grok_intent_recovery", "passed_quirk_families", "evidence_rebuilt_from_index_diff", "duration_s",
                         "raw_tokens", "estimated_usd", "started_at", "finished_at", "solver_cli_version", "evidence_sha256"])
        for r in rows:
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"],
                             "published" if r["judged"] == "published" else "published, one panel", "+".join(r["scored_panels"]),
                             fmt(r["combined_33"]), fmt(r["combined_20_profile"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"],
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]), r["intent_recovery_redistributed"],
                             *[fmt(r["panels"][p][k]) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["evidence_rebuilt_from_index_diff"], r["duration_s"], r["raw_tokens"],
                             fmt(r["estimated_usd"], 6), r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"]])

    def panel_mean(r, key):
        return statistics.mean(r["panels"][p][key] for p in r["scored_panels"])

    groups = []
    for model, levels in LEVELS.items():
        for effort in levels:
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            assert len(rs) == 23
            groups.append({
                "model": model, "effort": effort, "n": len(rs), "runs": len(rs), "unpublished_runs": 0,
                "one_panel_runs": sum(len(r["scored_panels"]) == 1 for r in rs),
                "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
                "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
                "intent_recovery": mean_se(r["intent_recovery"] for r in rs),
                "intent_recovery_redistributed_runs": 0,
                "readability": mean_se(panel_mean(r, "readability") for r in rs),
                "maintainability": mean_se(panel_mean(r, "maintainability") for r in rs),
                # Each judge's mean covers the runs it reviewed validly: Grok 4.6 at medium covers 22.
                "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs if r["panels"][p]["scored"]) for p in PANELS},
                "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
                "security": mean_se(100 * r["security"] for r in rs),
                "passed": sum(r["functional"] == 1 for r in rs), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
                "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_judged_runs": mean_se(r["duration_s"] / 60 for r in rs),
                "solver_fallback_runs": 0, "priced_runs": len(rs),
                "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
                "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
            })
            g = groups[-1]
            entry = summary["groups"][f"{model}/{effort}"]
            assert g["n"] == entry["n"] == entry["composite_v3"]["n"] == 23
            for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
                assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9, (effort, field)
                assert abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
            assert g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
            for p in PANELS:
                assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"]
                assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
    assert [g["n"] for g in groups] == [23] * 5 and [g["one_panel_runs"] for g in groups] == [0, 1, 0, 0, 0]
    assert [g["passed_all_runs"] for g in groups] == [20, 22, 23, 23, 23]
    assert [g["hidden_behaviours_fixed"] for g in groups] == [225, 228, 231, 231, 231] and all(g["hidden_behaviours"] == 231 for g in groups)
    assert [round(g["combined_33"]["mean"], 2) for g in groups] == [86.22, 86.44, 88.23, 88.78, 88.35]
    assert [round(g["code_quality"]["mean"], 2) for g in groups] == [70.79, 70.25, 73.67, 74.99, 73.80]
    assert [round(g["minutes"]["mean"], 1) for g in groups] == [6.9, 10.6, 10.2, 15.4, 14.5]

    # The harness card tables carry the combined score, Code quality and its components, pass counts, runtime and cost; match them.
    results = root / "docs/results/swe-v4-gpt61-sol-2026-09"
    with (results / "gpt61-sol-v318-efforts.csv").open(newline="") as source:
        card = {r["effort"]: r for r in csv.DictReader(source)}
    with (results / "gpt61-sol-v318-economics-efforts.csv").open(newline="") as source:
        card_econ = {r["effort"]: r for r in csv.DictReader(source)}
    for g in groups:
        c, ce = card[g["effort"]], card_econ[g["effort"]]
        assert int(c["n"]) == g["n"] and int(c["passed"]) == g["passed_all_runs"] and c["fallbacks"] == "0"
        for column, value in (("combined_v3", g["combined_33"]["mean"]), ("combined_v3_se", g["combined_33"]["se"]),
                              ("combined_20pct", g["combined_20_profile"]["mean"]), ("code_quality", g["code_quality"]["mean"]),
                              ("code_quality_se", g["code_quality"]["se"]), ("readability", g["readability"]["mean"]),
                              ("maintainability", g["maintainability"]["mean"]), ("muse_l1", g["by_panel"]["muse"]["mean"]),
                              ("grok_l1", g["by_panel"]["grok"]["mean"]), ("minutes", g["minutes"]["mean"]),
                              # Intent recovery over validly reviewed panels only, as published (Muse alone on medium paddockcore).
                              ("intent_recovery", g["intent_recovery"]["mean"])):
            assert abs(float(c[column]) - value) < 1e-4, (g["effort"], column)
        assert int(ce["n"]) == g["priced_runs"] == 23 and abs(float(ce["total_usd"]) - g["usd_total"]) < 1e-6
        assert int(ce["total_tokens"]) == g["raw_tokens_total"] and abs(float(ce["mean_minutes"]) - g["minutes"]["mean"]) < 1e-4
        assert abs(float(ce["mean_usd"]) - g["usd"]["mean"]) < 1e-6 and ce["fallbacks"] == "0"
    # The three-generation Sol card carries the same GPT-6.1 Sol figures.
    family_dir = root / "docs/results/swe-v4-gpt6-vs-gpt56-2026-09"
    with (family_dir / "sol-family-combined-efforts.csv").open(newline="") as source:
        family = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == "gpt61sol"}
    for g in groups:
        t = family[g["effort"]]
        assert int(t["judged"]) == g["n"] and int(t["passed"]) == g["passed_all_runs"] and t["timeouts"] == "0" and int(t["priced_runs"]) == 23
        assert abs(float(t["combined"]) - g["combined_33"]["mean"]) < 1e-4 and abs(float(t["mean_usd"]) - g["usd"]["mean"]) < 1e-6
        assert abs(float(t["mean_minutes"]) - g["minutes"]["mean"]) < 1e-4
    family_card = read(family_dir / "sol-family-combined.json")
    assert family_card["sources"]["gpt61sol"]["summary"] == digest(v318 / "summary.json")
    assert family_card["sources"]["gpt61sol"]["ledger"] == digest(comparison_path)
    save("groups.json", groups)

    with (SITE / "assets/data/swe-v4-gpt61-sol-v318-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability",
                         "muse_reviewed", "grok_reviewed", "functional", "automated_quality", "security", "passed_of_23",
                         "hidden_behaviours_fixed_of_231", "mean_minutes", "mean_raw_tokens", "mean_usd", "total_usd"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"], f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}',
                             g["passed_all_runs"], g["hidden_behaviours_fixed"], f'{g["minutes"]["mean"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}',
                             f'{g["usd"]["mean"]:.6f}', f'{g["usd_total"]:.6f}'])

    totals = {"gpt61sol": {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                           "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    econ_card = read(results / "gpt61-sol-v318-economics.json")
    assert abs(econ_card["totals"]["gpt61sol"]["usd"] - totals["gpt61sol"]["usd"]) < 1e-6
    assert econ_card["totals"]["gpt61sol"]["tokens"] == totals["gpt61sol"]["raw_tokens"]
    assert abs(econ_card["totals"]["gpt61sol"]["hours"] - totals["gpt61sol"]["solver_hours"]) < 1e-9
    assert econ_card["pricing_verified"] == PRICING_VERIFIED and econ_card["ledger_sha256"] == digest(comparison_path)
    assert f'{totals["gpt61sol"]["usd"]:.2f}' == "44.33" and f'{totals["gpt61sol"]["usd"] / 115:.2f}' == "0.39"
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a ChatGPT Pro subscription through Codex, "
                 "so these are estimates, not bills. Judging and local infrastructure are excluded. Every run in the sweep is priced.",
        "pricing_verified": PRICING_VERIFIED,
        "sources": {"openai": "https://developers.openai.com/api/docs/pricing",
                    "model_page": "https://developers.openai.com/api/docs/models/gpt-6.1-sol"},
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
            "The sweep stamped each run at run time at the published GPT-6.1 Sol list rates; the export recomputes every run from its "
            "receipt and matched every stamp.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        record = read(v318 / f"calibration-{panel}.json")
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
        "protocol_sha256": {p: digest(v318 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"],
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": protocol["population"],
        "unpublished": [],
        "one_panel": [{"effort": e, "task": t, "invalid_panel": "grok", "stage": "primary", "rule": marker["rule"],
                       "reason": marker["reason"], "effect": marker["effect"], "owner_decision": marker["owner_decision"],
                       "attempt_2_excerpt": marker["unsupported_excerpts"]["2"][0], "code_reads": "self.standing[parts[1]] += 2",
                       "scored_from": "muse", "reviewed_score": rows[[r["task"] == t and r["effort"] == e for r in rows].index(True)]["reviewed_score"],
                       "code_quality": rows[[r["task"] == t and r["effort"] == e for r in rows].index(True)]["code_quality"]}
                      for _, e, t in ONE_PANEL.values()],
        "operator_recoveries": [{"effort": e, "task": t, "panel": "muse", "stage": "probe", "rule": "recover_escaped_excerpts",
                                 "method": recovery["method"], "source_attempt": recovery["source_attempt"],
                                 "other_attempt_error": recovery["other_attempt_error"], "respelled_excerpts": len(recovery["original_excerpts"]),
                                 "owner_decision": "2026-10-01, treated as a JSON-escaping slip rather than an invented quote",
                                 "superseded_marker": SUPERSEDED_MARKER,
                                 "checks": "the respelled excerpt must be verbatim in the code and the attempt must pass the frozen validator otherwise"}
                                for _, e, t in RECOVERED.values()],
        "evidence_rebuilds": [{"effort": REBUILDS[p.stem][0], "task": REBUILDS[p.stem][1], "method": read(p)["method"]} for p in rebuild_paths],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.18/summary.json": digest(v318 / "summary.json"), "v3.18/protocol.json": digest(v318 / "protocol.json"),
            "v3.18/private-manifest.json": digest(v318 / "private-manifest.json"),
            "v3.18/calibration-muse.json": digest(v318 / "calibration-muse.json"), "v3.18/calibration-grok.json": digest(v318 / "calibration-grok.json"),
            "v3.18/calls/grok/primary/submission-054/operator-invalid.json": digest(marker_path),
            "v3.18/calls/muse/probe/submission-083/selected.json": digest(recovered_path),
            "v3.18/calls/muse/probe/submission-083/operator-invalid.superseded.json": digest(superseded_path),
            **{f"v3.18/reconstruction/{p.name}": digest(p) for p in rebuild_paths},
            "comparison.json": digest(comparison_path),
            "gpt61-sol-v318-efforts.csv": digest(results / "gpt61-sol-v318-efforts.csv"),
            "gpt61-sol-v318-economics-efforts.csv": digest(results / "gpt61-sol-v318-economics-efforts.csv"),
            "sol-family-combined-efforts.csv": digest(family_dir / "sol-family-combined-efforts.csv"),
        },
        "export_checks": ["115 solver summaries in the sweep folder, one per population row, all finished inside the 3-hour bound on Codex CLI "
                          "0.159.0; none missing, excluded or retried",
                          "every run's integrity audit is clean: no web access, no benchmark-data or answer-key paths",
                          "the frozen summary publishes all 115 submissions and is marked ready for publication",
                          "the one live invalidation marker is Grok's primary review of submission-054, and that row's published scores "
                          "are reproduced from Muse alone",
                          "the one operator recovery is Muse's probe of submission-083, escapes respelled only, with the earlier marker superseded",
                          "the three evidence rebuilds are the three method records under reconstruction/",
                          "both scored panels passed calibration under v3.18 with no allowance used",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "five-cell means and standard errors matched to the frozen summary's groups, per-judge means included",
                          "combined score, Code quality components (intent recovery included), pass counts, runtime, cost and token totals matched to the harness card "
                          "tables and to the three-generation Sol comparison table",
                          "every run's API-equivalent cost recomputed from its Codex receipt at the published list rates and matched to the "
                          "population record's run-time stamp",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["Medium paddockcore is scored from Muse Spark 1.3 alone: Grok 4.6's primary review has no valid response (both attempts quoted "
                   "a changed line), so the summary uses Muse's reviewed score and intent recovery for that run, as the frozen protocol does for "
                   "any submission without two valid reviews. Every other run is the equal mean of both judges.",
                   "Muse Spark 1.3's probe on high codeccore is published through the owner-approved recover_escaped_excerpts rule: attempt 2 had "
                   "decoded the string escapes in one quoted line into control characters, and the rule wrote them back as the source's escapes.",
                   "Three runs add test fixtures the saved text patch cannot re-apply: low payrollcore and medium lodgecore add fixtures git "
                   "treats as binary, and low cellarcore's fixture text was altered by the text-mode capture. Their judging evidence was rebuilt "
                   "from the saved workspace's index diff (the binary diff for the first two, after checking that its text diff equals the run's "
                   "patch; for cellarcore, the index diff whose normalized text matches the patch exactly). Only test fixtures differ; the "
                   "reviewed module is rebuilt as for every other run.",
                   "One attempt per task and level.",
                   "The solver sweep ran September 29, 19:18 PDT, to September 30, 17:21 PDT. Its first 11.5 hours, to September 30, 06:51 PDT, "
                   "overlapped GPT-6 Sol's v3.17 judging on the same machine at the owner's request; every Low, Medium and High run and the "
                   "first five Extra-high runs started inside that window, which may affect the wall-clock runtime figures."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens and API-equivalent cost estimates.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "the unused Grok probe answer on medium paddockcore"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
