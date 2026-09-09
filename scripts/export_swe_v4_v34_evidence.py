"""Export the public record of the v3.4 neutral-panel Code quality comparison.

Reads the frozen harness artifacts (summary, manifest, protocol, calibration)
and writes a bounded bundle without raw prompts, patches, quirk answer keys or
host paths. Run from the site root:

    python3 scripts/export_swe_v4_v34_evidence.py --harness-root ../VulcanBench
"""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-astra-fable51-v34"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    v34 = root / "runs-code-quality-maintenance-v3.4"
    v33 = root / "runs-code-quality-maintenance-v3.3"
    summary = read(v34 / "summary.json")
    manifest = {r["id"]: r for r in read(v34 / "private-manifest.json")}
    protocol = read(v34 / "protocol.json")
    grok_protocol = read(v33 / "protocol.json")
    assert summary["ready_for_publication"] and summary["published_submissions"] == 230
    assert summary["passing_panels"] == ["muse", "grok"]
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None and panels[p]["l2"] is not None for p in PANELS)
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
        l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
        code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - entry["published"]["code_quality"]) < 1e-9
        rows.append({
            "model": entry["model"], "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "solver_fallback": bool(run.get("fallback")),
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "code_quality": code_quality,
            "combined_33": composite(run, code_quality, WEIGHTS["code_quality"]),
            "combined_20_profile": composite(run, code_quality, 0.20),
            "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
                       for p in PANELS},
            "duration_s": run["duration_s"], "reported_tokens": run.get("reported_tokens"),
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "solver_cli_version": run.get("solver_cli_version"),
            "evidence_sha256": run["evidence_sha256"],
        })
        assert abs(rows[-1]["combined_33"] - entry["published"]["composite_v3"]) < 1e-9
    rows.sort(key=lambda r: (r["model"], EFFORTS.index(r["effort"]), r["task"]))
    save("runs.json", {"runs": len(rows), "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3, "rows": rows})
    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "combined_33", "combined_20_profile", "functional_pct", "automated_quality_pct",
                         "security_pct", "code_quality", "reviewed_score", "intent_recovery", "muse_reviewed", "muse_readability",
                         "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability", "grok_maintainability",
                         "grok_intent_recovery", "solver_fallback", "duration_s", "reported_tokens", "started_at", "finished_at",
                         "solver_cli_version", "evidence_sha256"])
        for r in rows:
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], f'{r["combined_33"]:.4f}', f'{r["combined_20_profile"]:.4f}',
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             f'{r["code_quality"]:.4f}', f'{r["reviewed_score"]:.4f}', f'{r["intent_recovery"]:.4f}',
                             *[f'{r["panels"][p][k]:.4f}' for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["solver_fallback"], r["duration_s"], r["reported_tokens"], r["started_at"], r["finished_at"],
                             r["solver_cli_version"], r["evidence_sha256"]])

    groups = []
    for model in ("astra", "fable"):
        for effort in EFFORTS:
            rs = [r for r in rows if r["model"] == model and r["effort"] == effort]
            assert len(rs) == 23
            groups.append({
                "model": model, "effort": effort, "n": len(rs),
                "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
                "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
                "intent_recovery": mean_se(r["intent_recovery"] for r in rs),
                "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs),
                "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs),
                "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs) for p in PANELS},
                "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
                "security": mean_se(100 * r["security"] for r in rs), "passed": sum(r["functional"] == 1 for r in rs),
                "minutes": mean_se(r["duration_s"] / 60 for r in rs), "solver_fallback_runs": sum(r["solver_fallback"] for r in rs),
            })
    save("groups.json", groups)
    with (SITE / "assets/data/swe-v4-astra-fable51-v34-scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "readability", "maintainability", "muse_reviewed", "grok_reviewed",
                         "functional", "automated_quality", "security", "passed", "mean_minutes", "solver_fallback_runs"])
        for g in groups:
            writer.writerow(["GPT-6 Astra" if g["model"] == "astra" else "Fable 5.1", g["effort"], g["n"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}',
                             f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}',
                             f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed"], f'{g["minutes"]["mean"]:.4f}',
                             g["solver_fallback_runs"]])

    calibration = {}
    for panel, run_dir in (("muse", v34), ("grok", v33), ("glm", v33)):
        path = run_dir / f"calibration-{panel}.json"
        if path.exists():
            record = read(path)
            calibration[panel] = {k: record[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256") if k in record}
            calibration[panel]["allowance_used"] = record.get("allowance_used")
            calibration[panel]["gates"] = record.get("gates")
            calibration[panel]["control_means"] = record.get("control_means")
            calibration[panel]["operator_record"] = record.get("operator_record")
    save("calibration.json", calibration)

    def public_reviewer(settings):
        return {k: v for k, v in settings.items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}

    save("judge-protocols.json", {
        "scored_panel": {"muse": public_reviewer(protocol["reviewers"]["muse"]), "grok": public_reviewer(grok_protocol["reviewers"]["grok"])},
        "protocol_ids": {"muse": protocol["id"], "grok": grok_protocol["id"]},
        "protocol_sha256": {"muse": digest(v34 / "protocol.json"), "grok": digest(v33 / "protocol.json")},
        "system": protocol["system"], "rubric": protocol["rubric"], "pair_instruction": protocol["pair_instruction"],
        "probe_instruction": protocol["probe_instruction"], "match_instruction": protocol["match_instruction"],
        "schemas": protocol["schemas"], "weights": protocol["weights"], "gate_allowance": protocol["gate_allowance"],
        "repeats": protocol["repeats"], "seed": protocol["seed"], "single_panel_rule": protocol["single_panel_rule"],
        "control_source_hashes": protocol["control_source_hashes"],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            "v3.4/summary.json": digest(v34 / "summary.json"), "v3.4/protocol.json": digest(v34 / "protocol.json"),
            "v3.4/private-manifest.json": digest(v34 / "private-manifest.json"), "v3.3/protocol.json": digest(v33 / "protocol.json"),
            "v3.3/calibration-grok.json": digest(v33 / "calibration-grok.json"), "v3.4/calibration-muse.json": digest(v34 / "calibration-muse.json"),
        },
        "export_checks": ["230 published submissions", "both scored panels passed calibration", "every row has both panels' reviewed and intent-recovery scores",
                          "per-row Code quality and combined score recomputed and matched to the frozen summary", "no dashes or host paths in exported text"],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "the retired Astra and Opus 5 reviews"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
