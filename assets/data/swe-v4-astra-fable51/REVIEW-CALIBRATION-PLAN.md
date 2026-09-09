# Code quality calibration plan

Status: proposed follow-up protocol. Not used to score the published Astra and
Fable comparison. The published ratings and fixed 20% weight remain unchanged.

## What the current measurement means

The exact current rubric requests a 0 to 100 judgment of how human-like and
high-quality the solution is. Correctness, readability and maintainability
personas each provide one rating per reviewer model. This is model-reviewed
Code quality, not human validation or an authorship detector. The original
rubric has no anchored score bands. Equal weighting of two model panels does
not remove calibration differences or establish an objective quality scale.

## Proposed operational anchors

| Dimension | Observable evidence |
| --- | --- |
| Correctness reasoning | Coherent handling of the stated behavior, edge cases and consistency with the supplied verifier outcome. No new functional pass is inferred. |
| Readability | Names, control flow and decomposition make the actual logic understandable without avoidable indirection. |
| Maintainability | Changes are localized and coherent, avoid duplication and task-specific hacks, and make future behavior changes practical. |

Proposed score anchors for each dimension:

- 0: submitted changes fundamentally unrelated to the task.
- 25: major unexplained defects or structure that obstructs understanding.
- 50: partly understandable and useful, but substantial concrete weaknesses.
- 75: sound overall, with specific nontrivial improvements still warranted.
- 90: strong implementation with only minor, evidenced concerns.
- 100: no material issue found within the supplied evidence, not a guarantee
  of perfection or production readiness.

Require evidence tied to code locations and distinguish missing evidence from
an observed defect. Do not reward verbosity, a particular language style,
comments alone or resemblance to a reviewer's own output. Missing artifacts
must be recorded as unavailable, not assigned an invented score.

## Calibration before adoption

1. Select a separate, stratified calibration set before seeing model rankings.
2. Have at least two qualified engineers score it independently with solver
   identity, effort and prior scores withheld. Keep a held-out audit set.
3. Compare human inter-rater agreement, model-to-human absolute error,
   systematic score offsets and ordering stability. Inspect disagreements
   using code evidence, not a target leaderboard spread.
4. Freeze the rubric, illustrative code examples, reviewer versions, aggregation,
   missing-data policy and success thresholds before any new scored sweep.
5. Use repeated independent runs, fixed CLI versions, counterbalanced task and
   effort order, recorded host load and per-request usage/model receipts.

Adoption needs a separately identified scoring protocol. Do not silently apply
new anchors to old ratings or pool results from different review protocols.
Open questions include how strongly these ratings predict maintenance effort,
how correlated the dimensions are with automated grading, and how stable
scores remain across reviewer versions.
