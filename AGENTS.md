# VulcanBench site writing rules

Use plain hyphens, commas, colons or separate sentences. Never introduce em
dash or en dash characters (U+2014 or U+2013), including HTML entities for
those characters, in page copy, code, comments, reports or commit messages.
Keep headings plain. Preserve historical measurements and scoring caveats.

Run `python3 scripts/check_benchmark_index.py` for benchmark index changes.
Run `python3 scripts/verify_swe_v4_evidence.py` for the public SWE v4 bundle.
Keep the current preview PR unmerged until the user approves a merge.
