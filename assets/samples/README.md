# Routing policy: what it is and how to wire it

This folder is the shape of what a VulcanBench stack benchmark delivers. The
file that matters is `routing-policy.yaml`: one row per class of engineering
work, each row naming the model and reasoning effort to send it to, what to do
when that misses, and the measured numbers that justify the choice.

Everything in the sample is illustrative. The classes, routes, and figures are
from a fictional engagement so the structure is concrete; yours come out of a
matrix run on a suite built from your own merged pull requests.

## The one-paragraph version

Most teams send every task to one frontier model at high or max effort. The
policy replaces that with a table: routine fixes and test writing go to a
cheaper route that measured at parity, feature work gets medium effort because
high did not move the score, refactors go to the frontier at low effort with
high held back as the escalation, and genuinely novel cross-cutting work keeps
the expensive route plus a human. The `cost_model` block prices your task
volume through that table against what you pay today.

## File layout

| Block | What it holds |
| --- | --- |
| `engagement` | Which private suite and which model x effort matrix produced this policy, plus the baseline you were running before. |
| `constraints` | Hard limits the measurement respected: allowed providers, data residency, wall-clock ceiling, barred routes. Nothing in `routes` violates these. |
| `classifier` | Ordered rules that map a request to a class. First match wins. Signals are whatever your gateway can see at request time: tracker labels, touched paths, diff size, services involved. |
| `routes` | One entry per class: `route` (first attempt), `escalate` (tried in order on a miss), `budget`, the `measured` cell behind it, and a one-line `why`. |
| `escalation` | What counts as a miss. Hidden-test failure, wall-clock exceeded, or no patch produced re-route; lint-only failures do not. |
| `cost_model` | Your class mix by volume, projected spend through the table, baseline spend, and the break-even note. |
| `review` | When to rerun the matrix: new model, a class escalating too often, or quarterly. |

## Reading a route

```yaml
routine_fix:
  route:    {provider: openai, model: gpt-5.6-terra, effort: low}
  escalate:
    - {provider: anthropic, model: claude-fable-5, effort: low}
  budget:   {max_wall_clock_s: 900, max_attempts: 2}
  measured: {pass_at_1: 0.88, pass_pow_3: 0.79, cost_per_task_usd: 0.14, p50_minutes: 2.6}
  why: "Accuracy parity with the frontier baseline (0.89) at a fraction of the cost."
```

- `route` is the cell in the matrix that won for this class under the
  constraints. It is a single model at a single effort; the policy never asks
  a gateway to blend.
- `escalate` is ordered. Step one is tried only when the first attempt misses
  per the `escalation.on` list; step two only when step one misses. A
  `{human_review: true}` step ends automation.
- `budget` caps attempts and wall-clock per task so an escalation chain cannot
  run away.
- `measured` is copied from the matrix: `pass_at_1` is the mean per-task
  success rate, `pass_pow_3` is the share of tasks solved on all three
  repeats (reliability, the bar for high-volume classes), cost is list-price
  API spend per task run, and `p50_minutes` is sandbox wall-clock. These are
  the evidence; they are not re-evaluated at request time.
- `why` is the sentence you say when someone asks why this class is not on the
  frontier model.

## Wiring it into a gateway

The policy is deliberately gateway-agnostic. Any router that can (a) evaluate
the classifier signals and (b) call a named provider/model with an effort
parameter can execute it. In practice that is one of:

1. **A routing gateway you already run.** Load the file at startup, classify
   each request with the `classifier` block, call `routes[class].route`,
   and on a miss walk `routes[class].escalate`. Map `effort` to the
   provider's own parameter (`reasoning_effort`, `thinking.budget`, and so
   on; the engagement report lists the exact mapping per provider).
2. **A thin shim in front of the SDK.** Same logic as a small function that
   wraps your existing client: `resolve(class) -> (provider, model, effort)`,
   with the escalation loop around your task runner.
3. **Per-team policies.** Teams that do not share a stack get their own
   `routing-policy.yaml`; the gateway picks the file by team. The schema does
   not change.

A minimal reference implementation of the classify / route / escalate loop
ships with the engagement report, along with the provider effort mapping and a
test that replays the suite through the policy to confirm the gateway makes
the same choices the matrix did.

## Keeping it honest

- The `measured` numbers are from the suite run on the date in
  `engagement.generated`. They are a measurement of that suite under those
  constraints, not a guarantee on every future task.
- `review.rerun_when` is the maintenance contract. A new model, a class whose
  escalation rate climbs past the threshold, or a quarter passing are all
  reasons to rerun the matrix. The suite already exists, so a rerun is the
  cheap part.
- If the `default` class starts carrying real volume, the classifier is
  missing a class. Add one and measure it rather than letting unclassified
  work sit on a middle route.
- No model vendor pays for a row in this table. The routes are bought by you
  and graded by hidden tests.

## What you send to get one

Your stack (languages, frameworks, repo shape), the model and effort your team
defaults to today, and a rough monthly API spend. That is enough to propose a
suite shape, a matrix, and a price. vulcanbench.com/benchmark-your-stack.html
