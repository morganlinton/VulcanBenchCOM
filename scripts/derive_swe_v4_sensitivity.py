"""Deterministic public sensitivity appendix and flat run export. No model calls."""

import argparse
import csv
import hashlib
import io
import json
import random
import statistics
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "assets/data/swe-v4-astra-fable51"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
SEED = 20260906
RESAMPLES = 20000


def derive():
    raw = (DATA / "runs.json").read_bytes()
    rows = json.loads(raw)["rows"]
    costs = {(r["model"], r["run_id"]): r for r in json.loads((DATA / "costs.json").read_text())["rows"]}
    rng = random.Random(SEED)
    records = []
    for effort in EFFORTS:
        paired = {m: {r["task"]: r for r in rows if r["model"] == m and r["effort"] == effort}
                  for m in ("astra", "fable")}
        tasks = sorted(paired["astra"])
        assert len(tasks) == 23 and set(tasks) == set(paired["fable"])
        diff = [100 * (paired["fable"][t]["combined"] - paired["astra"][t]["combined"]) for t in tasks]
        boot = sorted(sum(rng.choices(diff, k=23)) / 23 for _ in range(RESAMPLES))
        quantiles = statistics.quantiles(boot, n=40, method="inclusive")
        record = {"effort": effort, "n": 23, "fable_minus_astra_points": statistics.mean(diff),
                  "paired_bootstrap_95_low": quantiles[0], "paired_bootstrap_95_high": quantiles[-1]}
        retained = [t for t in tasks if not paired["fable"][t]["fallback"] and not paired["astra"][t]["fallback"]]
        record["matched_nonfallback_n"] = len(retained)
        record["excluded_tasks"] = sorted(set(tasks) - set(retained))
        for model in ("astra", "fable"):
            rs = [paired[model][t] for t in tasks]
            record[model + "_official"] = statistics.mean(100 * r["combined"] for r in rs)
            for judge in ("astra", "claude"):
                record[model + "_" + judge + "_only"] = statistics.mean(
                    100 * (.5 * r["functional"] + .15 * r["quality"] + .15 * r["security"] + .2 * r[judge]) for r in rs)
            record[model + "_matched_nonfallback"] = statistics.mean(100 * paired[model][t]["combined"] for t in retained)
            record[model + "_median_minutes"] = statistics.median(r["duration_s"] / 60 for r in rs)
        records.append(record)
    result = {"status": "Exploratory sensitivity, not replacement official scores",
              "source_runs_sha256": hashlib.sha256(raw).hexdigest(),
              "method": "Paired task bootstrap, Fable minus Astra total score points; 23 task pairs sampled with replacement independently at each effort; percentile interval using linear interpolation. Python random.Random choices, sorted task order.",
              "seed": SEED, "resamples": RESAMPLES,
              "limits": "Task-sampling sensitivity only, not repeated-run or judge uncertainty. No multiple-comparison adjustment; curated tasks are not a random sample of all software work. Nonfallback subsets are post-hoc and differ by effort; both models lose the same tasks. They are not unbiased pure-model estimates. Reviewer-only variants retain the 20% review weight.",
              "rows": records}
    buffer = io.StringIO(newline="")
    fields = ["model", "effort", "task", "run_id", "total_score_pct", "functional_pct", "automated_quality_pct",
              "security_pct", "code_quality_pct", "astra_reviewer_pct", "claude_reviewer_pct", "solver_fallback",
              "duration_s", "raw_tokens", "estimated_api_usd", "astra_long_context_upper_usd", "started_at",
              "finished_at", "solver_cli_version", "solver_stream_sha256", "patch_sha256"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        c = costs[r["model"], r["run_id"]]
        flat = {k: r[k] for k in ("model", "effort", "task", "run_id", "duration_s", "started_at", "finished_at", "solver_cli_version")}
        flat.update({dst: 100 * r[src] for dst, src in (("total_score_pct", "combined"), ("functional_pct", "functional"),
                    ("automated_quality_pct", "quality"), ("security_pct", "security"), ("code_quality_pct", "panel"),
                    ("astra_reviewer_pct", "astra"), ("claude_reviewer_pct", "claude"))})
        flat.update(solver_fallback=r["fallback"], raw_tokens=r["solver_receipt"]["raw_tokens"],
                    estimated_api_usd=c["estimated_usd"], astra_long_context_upper_usd=c.get("long_context_upper_usd", ""),
                    solver_stream_sha256=r["solver_receipt"]["stream_sha256"], patch_sha256=r["source_hashes"]["patch"])
        writer.writerow(flat)
    return {"sensitivity.json": json.dumps(result, indent=2) + "\n", "runs.csv": buffer.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in derive().items():
        path = DATA / name
        if args.check:
            assert path.read_bytes() == content.encode(), f"Stale derived file: {name}"
        else:
            path.write_bytes(content.encode())
    print("Verified sensitivity and 230 flat run rows." if args.check else "Generated sensitivity and 230 flat run rows.")


if __name__ == "__main__":
    main()
