"""Export a bounded public record without raw prompts, patches or host paths."""

import argparse
import hashlib
import json
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-astra-fable51"
PANELS = {
    "astra": ("runs-astra-cii-v4-judging-v2", "runs-astra-cii-v4-claude-judging-v1"),
    "fable": ("runs-fable51-cii-v4-panel-v1/astra", "runs-fable51-cii-v4-panel-v1/claude"),
}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert not any(mark in text for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/"))
    (DEST / name).write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    source = root / "docs/results/swe-v4-astra-fable51-2026-09"
    comparison = read(source / "comparison.json")
    costs = read(source / "api-equivalent-costs.json")
    accounting = read(source / "reviewer-accounting.json")
    assert comparison["complete"] and comparison["runs"] == 230
    assert costs["source_sha256"] == digest(source / "comparison.json")
    DEST.mkdir(parents=True, exist_ok=True)
    rows, votes, calls, protocols = [], [], [], {}
    row_fields = ("model", "effort", "task", "run_id", "astra", "claude", "panel", "combined",
                  "functional", "quality", "security", "fallback", "claude_reviewer_models",
                  "duration_s", "source_hashes", "started_at", "finished_at", "solver_cli_version")
    for row in comparison["rows"]:
        stream = Path(row["source_directory"]) / "cli-agent-stream.jsonl"
        assert digest(stream) == row["solver_receipt"]["stream_sha256"]
        public = {key: row[key] for key in row_fields}
        public["solver_receipt"] = row["solver_receipt"]
        rows.append(public)
        for reviewer, panel in zip(("astra", "claude"), PANELS[row["model"]]):
            folder = root / panel / row["effort"] / row["run_id"]
            record = read(folder / "judging.json")
            assert record["run_id"] == row["run_id"] and record["source_hashes"] == row["source_hashes"]
            assert record["human_like"] == row[reviewer]
            for vote in record["votes"]:
                stream = folder / vote.get("raw_stream_relative", f'{vote["persona"]}.stream.jsonl')
                votes.append({"solver": row["model"], "effort": row["effort"], "task": row["task"],
                              "run_id": row["run_id"], "reviewer": reviewer,
                              **{key: vote[key] for key in ("persona", "score", "judge_model_requested",
                                                          "judge_effort_requested", "prompt_sha256",
                                                          "duration_s", "completed_at")},
                              "raw_stream_sha256": digest(stream),
                              "format_recovered": bool(vote.get("format_recovery"))})
    for panel_key, value in accounting.items():
        solver, reviewer = panel_key.split("/")
        for call in value["calls"]:
            path = Path(call["path"])
            assert digest(path) == call["sha256"]
            calls.append({"solver": solver, "reviewer": reviewer, "effort": path.parent.parent.name,
                          "run_id": path.parent.name, "artifact": path.name,
                          **{k: v for k, v in call.items() if k not in {"path", "session_id"}}})
        protocol = read(root / PANELS[solver][0 if reviewer == "astra" else 1] / "protocol.json")
        protocols[panel_key] = {key: protocol[key] for key in
                               ("protocol", "model", "effort", "system", "personas", "cli_version")
                               if key in protocol}
        protocols[panel_key]["rubric"] = protocol.get("instruction", protocol.get("rubric"))
    assert len(rows) == 230 and len(votes) == 1380 and len(calls) == 1386
    assert sum(c["included_in_score"] for c in calls) == 1380
    # Session identifiers add no public analytical value and can link private traces.
    public_costs = json.loads(json.dumps(costs))
    for row in public_costs["rows"]:
        for part in row.get("parts", []):
            part.pop("session_id", None)
    save("runs.json", {"suite": comparison["suite"], "weights": comparison["weights"],
                       "checked_at": comparison["checked_at"], "rows": rows})
    save("ratings.json", votes)
    save("reviewer-calls.json", calls)
    save("review-protocols.json", protocols)
    save("costs.json", public_costs)
    save("groups.json", comparison["groups"])
    save("provenance.json", {
        "source_artifacts_sha256": {name: digest(source / name) for name in
                                    ("comparison.json", "reviewer-accounting.json", "api-equivalent-costs.json")},
        "original_audit": {key: comparison[key] for key in
                           ("source_hashes_unchanged", "raw_votes_and_prompts_verified")},
        "export_checks": {"solver_streams_hash_verified": len(rows), "reviewer_streams_hash_verified": len(calls)},
        "publication_scope": "Run metrics, selected ratings, all reviewer-call dispositions, accounting and source hashes.",
        "withheld": "Raw trajectories, task-specific prompts, solution patches, reviewer rationales, hidden graders, host paths and session identifiers.",
        "integrity_limit": "Hash consistency does not prove absence of contamination, prohibited solver access or training-data overlap.",
    })
    print(f"Exported {len(rows)} runs, {len(votes)} ratings and {len(calls)} reviewer calls")


if __name__ == "__main__":
    main()
