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

Earlier suite results live in their own report pages and keep their original
scoring conventions; do not pool them with Frontier v4.
