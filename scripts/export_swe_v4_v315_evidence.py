"""Export the public record of the v3.15 Claude Opus 5.5 effort sweep on Frontier v4.

Adapted from the v3.7 Sol export, with the same publication scope: per-run
scores, per-panel sub-scores, aggregates, judge protocol text, calibration
verdicts, raw tokens and API-equivalent cost. Raw prompts, patches, quirk
answer keys and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v315_evidence.py --harness-root ../VulcanBench

Differences from the Sol export, all forced by the sweep:

- Refusal fallback. Opus 5.5 ran in Claude Code with the refusal fallback on
  (the Artificial Analysis "Default Fallback" convention), so 30 runs were
  partly served by claude-opus-4-8. Every run counts. Each row carries
  ``solver_fallback`` and replies by serving model, and each cell carries
  the Opus 4.8 share of replies.
- Cost. The harness's receipt-based estimate omits fallback-model usage, so
  cost is Claude Code's own list-price total for every serving model
  (``cli_reported_cost_usd``), asserted equal to the stream's final
  ``total_cost_usd``. Raw tokens sum every model in the final ``modelUsage``.
- One run is not judged. High depotcore is excluded from the judged
  population as an incomplete source run: a safeguard classifier stop cut
  off the turn that would have written the module, so the patch is empty.
  It stays in runtime, tokens, cost and tasks passed.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-opus55-v315"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
LEVELS = {"opus55": EFFORTS}
NAMES = {"opus55": "Claude Opus 5.5"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.15"
MAIN_MODEL = "claude-opus-5-5"
RATES_PER_MILLION = {  # platform.claude.com/docs/en/about-claude/pricing, checked 2026-09-22
    "claude-opus-5-5": {"input": 4.00, "cache_hit": 0.20, "cache_write_5m": 5.00, "cache_write_1h": 8.00, "output": 20.00},
    "claude-opus-4-8": {"input": 5.00, "cache_hit": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.00, "output": 25.00},
    "claude-opus-5": {"input": 5.00, "cache_hit": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.00, "output": 25.00},
}
EXCLUDED_NOTE = ("not judged: a safeguard classifier stop cut off the turn that would have written the module, so the patch is empty "
                 "and there is no code to review; the run scores 0 functional and is included in runtime, tokens, cost and tasks passed")
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


def stream_facts(run_dir):
    """Replies by serving model, final modelUsage and final CLI cost, from the Claude Code stream."""
    replies, final = Counter(), None
    for line in (run_dir / "cli-agent-stream.jsonl").open(errors="replace"):
        if '"assistant"' not in line and '"result"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            replies[event["message"].get("model")] += 1
        elif event.get("type") == "result":
            final = event
    assert final is not None, run_dir.name
    usage = final.get("modelUsage") or {}
    per_model = {m: {"input_tokens": u.get("inputTokens", 0), "cache_read_tokens": u.get("cacheReadInputTokens", 0),
                     "cache_creation_tokens": u.get("cacheCreationInputTokens", 0), "output_tokens": u.get("outputTokens", 0),
                     "cli_cost_usd": u.get("costUSD", 0.0)} for m, u in sorted(usage.items())}
    raw = sum(v["input_tokens"] + v["cache_read_tokens"] + v["cache_creation_tokens"] + v["output_tokens"] for v in per_model.values())
    return dict(sorted(replies.items())), per_model, raw, final["total_cost_usd"]


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    v315 = root / "runs-code-quality-maintenance-v3.15"
    summary = read(v315 / "summary.json")
    manifest = {r["id"]: r for r in read(v315 / "private-manifest.json")}
    protocol = read(v315 / "protocol.json")
    comparison_path = root / "docs/results/swe-v4-opus55-2026-09/comparison.json"
    comparison = read(comparison_path)
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == summary["published_submissions"] == 114 and summary["ready_for_publication"]
    assert summary["passing_panels"] == ["muse", "grok"] and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert len(comparison["rows"]) == 114 and comparison["missing"] == [] and len(comparison["excluded"]) == 1
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        run_dir = Path(run["source_directory"])
        replies, per_model, raw, cli_total = stream_facts(run_dir)
        run_summary = read(run_dir / "summary.json")
        assert abs(run_summary["economics"]["cli_reported_cost_usd"] - cli_total) < 1e-9, run["run_id"]
        assert replies == run["fallback_replies"], run["run_id"]
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None for p in PANELS) and not any(panels[p]["reviewer_fallback"] for p in PANELS)
        published = entry["published"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
        redistributed = published["l2_redistributed"]
        if redistributed:
            l2, code_quality = None, l1
        else:
            l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
            code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - published["code_quality"]) < 1e-9
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        assert abs(combined_33 - published["composite_v3"]) < 1e-9
        rows.append({
            "model": "opus55", "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": "published",
            "solver_fallback": bool(run["fallback"]), "replies_by_model": replies,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": composite(run, code_quality, 0.20),
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]} for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]),
            "duration_s": run["duration_s"], "raw_tokens": raw,
            "token_usage": {"output_tokens": sum(v["output_tokens"] for v in per_model.values()), "by_model": per_model},
            "estimated_usd": cli_total,
            "pricing_method": "Claude Code's own list-price total for every serving model (result.total_cost_usd)",
            "started_at": run["started_at"], "finished_at": run["finished_at"], "solver_cli_version": run["solver_cli_version"],
            "evidence_sha256": run["evidence_sha256"],
        })
    (ex,) = comparison["excluded"]
    assert ex["effort"] == "high" and ex["task"] == "legacy-depotcore-binary-parity" and ex["functional"] == 0
    ex_dir = root / "runs-effort-opus55" / ex["effort"] / ex["run_id"]
    ex_summary = read(ex_dir / "summary.json")
    replies, per_model, raw, cli_total = stream_facts(ex_dir)
    assert abs(ex_summary["economics"]["cli_reported_cost_usd"] - cli_total) < 1e-9
    rows.append({
        "model": "opus55", "effort": ex["effort"], "task": ex["task"], "run_id": ex["run_id"], "judged_under": PROTOCOL_ID,
        "judged": EXCLUDED_NOTE, "solver_fallback": any(m != MAIN_MODEL for m in replies), "replies_by_model": replies,
        "functional": ex_summary["scores"]["functional"], "automated_quality": ex_summary["scores"]["quality"],
        "security": ex_summary["scores"]["security"], "reviewed_score": None, "intent_recovery": None,
        "intent_recovery_redistributed": None, "code_quality": None, "combined_33": None, "combined_20_profile": None, "panels": None,
        "passed_quirk_families": None, "duration_s": ex_summary["duration_s"], "raw_tokens": raw,
        "token_usage": {"output_tokens": sum(v["output_tokens"] for v in per_model.values()), "by_model": per_model},
        "estimated_usd": cli_total, "pricing_method": "Claude Code's own list-price total for every serving model (result.total_cost_usd)",
        "started_at": ex_summary["started_at"], "finished_at": ex_summary["finished_at"],
        "solver_cli_version": ex_summary["cli_agent"]["harness_version"], "evidence_sha256": None,
    })
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and sum(r["judged"] != "published" for r in rows) == 1
    save("runs.json", {"runs": len(rows), "published": 114, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where the v3.15 summary publishes a Code quality score; the one other row carries the reason it was not judged",
                       "fallback_rule": "Claude Code's refusal fallback was on. solver_fallback is true when any assistant reply came from a model other than claude-opus-5-5; replies_by_model counts them. Every run counts.",
                       "token_fields": {"raw_tokens": "every serving model's input, cache reads, cache writes and output from the final modelUsage",
                                        "token_usage.output_tokens": "output tokens summed over every serving model"},
                       "rows": rows})
    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged", "combined_33", "functional_pct", "code_quality", "reviewed_score",
                         "intent_recovery", "muse_reviewed", "grok_reviewed", "solver_fallback", "opus48_replies", "all_replies",
                         "duration_s", "raw_tokens", "estimated_usd", "solver_cli_version"])

        def fmt(v):
            return "" if v is None else f"{v:.4f}"

        for r in rows:
            p = r["panels"] or {q: {} for q in PANELS}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], "published" if r["judged"] == "published" else "not judged",
                             fmt(r["combined_33"]), f'{100 * r["functional"]:.2f}', fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]), fmt(p["muse"].get("reviewed_score")), fmt(p["grok"].get("reviewed_score")),
                             r["solver_fallback"], r["replies_by_model"].get("claude-opus-4-8", 0), sum(r["replies_by_model"].values()),
                             r["duration_s"], r["raw_tokens"], f'{r["estimated_usd"]:.6f}', r["solver_cli_version"]])

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        judged = [r for r in rs if r["judged"] == "published"]
        scored = [r for r in judged if r["intent_recovery"] is not None]
        replies = Counter()
        for r in rs:
            replies.update(r["replies_by_model"])
        g = {
            "model": "opus55", "effort": effort, "n": len(judged), "runs": len(rs), "unpublished_runs": len(rs) - len(judged),
            "combined_33": mean_se(r["combined_33"] for r in judged), "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
            "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
            "intent_recovery": mean_se(r["intent_recovery"] for r in scored), "intent_recovery_redistributed_runs": len(judged) - len(scored),
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in judged), "passed": sum(r["functional"] == 1 for r in judged),
            "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": sum(r["solver_fallback"] for r in rs),
            "opus48_reply_share_pct": 100 * replies.get("claude-opus-4-8", 0) / sum(replies.values()),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
        }
        entry = summary["groups"][f"opus55/{effort}"]
        assert g["n"] == entry["n"] and abs(g["combined_33"]["mean"] - entry["composite_v3"]["mean"]) < 1e-9
        assert abs(g["code_quality"]["mean"] - entry["code_quality"]["mean"]) < 1e-9
        groups.append(g)
    assert [g["n"] for g in groups] == [23, 23, 22, 23, 23] and all(g["runs"] == 23 for g in groups)
    assert [g["solver_fallback_runs"] for g in groups] == [0, 3, 7, 8, 12]
    save("groups.json", groups)
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a Claude Max subscription through Claude Code, so these "
                 "are estimates, not bills. Judging is excluded. Every run is priced, including the unjudged high depotcore run.",
        "pricing_verified": "2026-09-22", "sources": {"anthropic": "https://platform.claude.com/docs/en/about-claude/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": g["solver_fallback_runs"], "opus48_reply_share_pct": g["opus48_reply_share_pct"]} for g in groups],
        "totals": {"opus55": {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                              "solver_hours": sum(r["duration_s"] for r in rows) / 3600}},
        "limitations": [
            "Cost is Claude Code's own list-price total for the session, covering every serving model: claude-opus-5-5, claude-opus-4-8 after a "
            "refusal fallback, and claude-opus-5 for auxiliary CLI calls. The harness's receipt-based estimate omits fallback-model usage and is not used.",
            "Claude Code prices cache writes by their observed TTL; the export takes its total as reported and checks it against each run summary.",
            "No Batch, Fast or priority pricing is applied.",
        ],
        "comparison_sha256": digest(comparison_path),
    })
    calibration = {}
    for panel in PANELS:
        record = read(v315 / f"calibration-{panel}.json")
        assert record["passed"] and record["failing_gates"] == [] and not record["allowance_used"]
        calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                     "gates", "control_means")}
    save("calibration.json", calibration)
    save("judge-protocols.json", {
        "scored_panel": {p: {k: v for k, v in protocol["reviewers"][p].items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}
                         for p in PANELS},
        "protocol_ids": {p: protocol["id"] for p in PANELS}, "protocol_sha256": {p: digest(v315 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": {k: v for k, v in protocol["population"].items() if k != "excluded"},
        "not_judged": [{"effort": ex["effort"], "task": ex["task"], "reason": EXCLUDED_NOTE}],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {f"v3.15/{n}": digest(v315 / n) for n in ("summary.json", "protocol.json", "private-manifest.json",
                                                                               "calibration-muse.json", "calibration-grok.json")}
                                   | {"comparison.json": digest(comparison_path)},
        "export_checks": ["115 runs across five effort cells; 114 judged and published, the high depotcore run not judged",
                          "both scored panels passed calibration under v3.15 with no allowance used; no reviewer fallbacks",
                          "per-row Code quality and combined score recomputed and matched to the frozen summary; cell means matched",
                          "every run's cost equals Claude Code's final total_cost_usd in its stream and the run summary's cli_reported_cost_usd",
                          "replies by serving model recounted from each stream and matched to the population record",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["Claude Code's refusal fallback was on, so 30 runs were partly served by claude-opus-4-8; they count, and each cell reports the "
                   "Opus 4.8 share of replies.",
                   "The high cell's Code quality and combined score cover 22 of 23 runs (depotcore not judged, empty patch)."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "raw tokens, replies by serving model and API-equivalent cost.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources",
                     "quirk answer keys (they describe hidden-test behaviour)", "reviewer session identifiers and usage receipts"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
