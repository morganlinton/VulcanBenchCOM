# Public data files

`swe-v4-astra-fable51-v34/` is the public record of the September 9, 2026
Astra and Fable 5.1 comparison under Code quality protocol v3.4. It is exported
from the frozen harness results by `scripts/export_swe_v4_v34_evidence.py`,
which recomputes every row and refuses to write on any mismatch. The folder's
README lists each file. `swe-v4-astra-fable51-v34-scores.csv` holds the ten
model/effort aggregates for spreadsheets.

`swe-v4-sol-v37/` is the public record of the September 19, 2026 GPT-5.6 Sol
report under Code quality protocol v3.7, exported by
`scripts/export_swe_v4_v37_evidence.py` on the same terms; its README explains
the one Max run without a published Code quality score.
`swe-v4-sol-v37-scores.csv` holds its five effort aggregates.

`swe-v4-gpt6-luna-v316/` is the public record of the September 28, 2026 GPT-6
Luna report under Code quality protocol v3.16, exported by
`scripts/export_swe_v4_v316_evidence.py` on the same terms; its README explains
the six runs stopped at the 3-hour bound and the two combined figures.
`swe-v4-gpt6-luna-v316-scores.csv` holds its five effort aggregates.

`swe-v4-gpt6-sol-v317/` is the public record of the September 30, 2026 GPT-6
Sol report under Code quality protocol v3.17, exported by
`scripts/export_swe_v4_v317_evidence.py` on the same terms; its README explains
the one Medium run without a published Code quality score and the one
formatting-only recovery of a judge review.
`swe-v4-gpt6-sol-v317-scores.csv` holds its five effort aggregates.

`swe-v4-gpt61-sol-v318/` is the public record of the October 1, 2026 GPT-6.1
Sol report under Code quality protocol v3.18, exported by
`scripts/export_swe_v4_v318_evidence.py` on the same terms; its README explains
the one Medium run scored from Muse Spark 1.3 alone, the one escaping recovery
of a judge probe and the three evidence rebuilds.
`swe-v4-gpt61-sol-v318-scores.csv` holds its five effort aggregates.

`swe-v4-grok47-cursor-v320/` is the public record of the October 4, 2026
Grok 4.7 report under Code quality protocol v3.20, exported by
`scripts/export_swe_v4_v320_evidence.py`; its README explains the different
judge pair (Muse Spark 1.3 and GPT-6.1 Sol), the shared-judge check, the one
Medium timeout, why there is no cost, and the Safety v1 aggregates.
`swe-v4-grok47-cursor-v320-scores.csv` holds its four effort aggregates.

`swe-v4-sonnet55-v323/` is the public record of the October 8, 2026
Claude Sonnet 5.5 report under Code quality protocol v3.23, exported by
`scripts/export_swe_v4_v323_evidence.py`; its README explains the sweep that
predates the tagged-worktree rule and the task hash bridge that admitted it,
the judge settings and Cursor version, the Claude Code version mix, and why cost is Claude
Code's own reported total.
`swe-v4-sonnet55-v323-scores.csv` holds its five effort aggregates.

Earlier suite results live in their own report pages and keep their original
scoring conventions; do not pool them with Frontier v4.
