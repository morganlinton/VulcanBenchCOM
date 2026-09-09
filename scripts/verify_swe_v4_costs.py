"""Reprice public token receipts using the frozen rate snapshot, not CLI totals."""

import json
import math
import statistics
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "assets/data/swe-v4-astra-fable51"


def close(actual, expected):
    assert math.isfinite(actual) and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8), (actual, expected)


def verify(costs, runs):
    indexed = {(r["model"], r["run_id"]): r for r in runs}
    assert len(costs["rows"]) == len(indexed) == 230
    assert {(r["model"], r["run_id"]) for r in costs["rows"]} == set(indexed)
    exceptions = 0
    parts = 0
    for row in costs["rows"]:
        run = indexed[row["model"], row["run_id"]]
        assert (row["task"], row["effort"], row["stream_sha256"]) == (run["task"], run["effort"], run["solver_receipt"]["stream_sha256"])
        if row["model"] == "astra":
            u, rate = run["solver_receipt"]["usage"], costs["astra_rates_per_million"]
            assert all(isinstance(v, int) and v >= 0 for v in u.values())
            assert u["cached_input_tokens"] <= u["input_tokens"] and u["cache_write_input_tokens"] == 0
            assert u["reasoning_output_tokens"] <= u["output_tokens"]
            assert run["solver_receipt"]["raw_tokens"] == u["input_tokens"] + u["output_tokens"]
            inp = ((u["input_tokens"] - u["cached_input_tokens"]) * rate["input"] + u["cached_input_tokens"] * rate["cache_read"]) / 1e6
            out = u["output_tokens"] * rate["output"] / 1e6
            close(row["input_cost_usd"], inp)
            close(row["output_cost_usd"], out)
            close(row["estimated_usd"], inp + out)
            close(row["long_context_upper_usd"], 2 * inp + 1.5 * out if u["input_tokens"] > 272000 else inp + out)
        else:
            total = 0
            for part in row["parts"]:
                parts += 1
                u = part["usage"]
                rate = costs["claude_rates_per_million"][part["model"]]
                token_keys = ("inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "outputTokens")
                assert all(isinstance(u[k], int) and u[k] >= 0 for k in token_keys)
                assert u["webSearchRequests"] == 0
                base = u["inputTokens"] * rate[0] + u["cacheReadInputTokens"] * rate[1] + u["outputTokens"] * rate[4]
                write = u["cacheCreationInputTokens"]
                all5, all1 = (base + write * rate[2]) / 1e6, (base + write * rate[3]) / 1e6
                close(part["all_5m_usd"], all5)
                close(part["all_1h_usd"], all1)
                ttl = part["observed_cache_ttl"]
                five, hour = ttl.get("ephemeral_5m_input_tokens", 0), ttl.get("ephemeral_1h_input_tokens", 0)
                assert five >= 0 and hour >= 0
                assert five <= write
                if part["method"] == "Recomputed from verified rates and cache split":
                    # Final cumulative receipts own token totals. Stream TTL counts
                    # can differ; observed 5m writes plus the residual at 1h reproduce
                    # the published policy and are checked against the list receipt.
                    price = (base + five * rate[2] + (write - five) * rate[3]) / 1e6
                    close(part["calculated_usd"], price)
                    close(u["costUSD"], price)
                else:
                    exceptions += 1
                    assert part["model"] == "claude-opus-5" and not ttl and write == 9273
                    close(u["costUSD"], .40398125)
                    close(u["costUSD"], all5)
                    price = all5
                close(part["estimated_usd"], price)
                total += price
            close(row["estimated_usd"], total)
    assert parts == 252 and exceptions == 1
    expected = {(m, e) for m in ("astra", "fable") for e in ("low", "medium", "high", "extra-high", "max")}
    assert len(costs["groups"]) == 10 and {(g["model"], g["effort"]) for g in costs["groups"]} == expected
    for g in costs["groups"]:
        rs = [r for r in costs["rows"] if (r["model"], r["effort"]) == (g["model"], g["effort"])]
        vals = [r["estimated_usd"] for r in rs]
        assert len(vals) == g["n"] == 23
        close(g["total_usd"], sum(vals))
        close(g["mean_usd"], statistics.mean(vals))
        close(g["se_usd"], statistics.stdev(vals) / math.sqrt(23))
        if g["model"] == "astra":
            upper = sum(r["long_context_upper_usd"] for r in rs)
            close(g["long_context_upper_total_usd"], upper)
            close(g["long_context_upper_mean_usd"], upper / 23)
    for model in ("astra", "fable"):
        close(costs["totals_usd"][model], sum(r["estimated_usd"] for r in costs["rows"] if r["model"] == model))


if __name__ == "__main__":
    verify(json.loads((DATA / "costs.json").read_text()), json.loads((DATA / "runs.json").read_text())["rows"])
    print("Repriced 230 runs and 252 Claude model receipts; one disclosed cache-TTL exception.")
