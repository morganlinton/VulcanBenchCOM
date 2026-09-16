# VulcanBench site writing rules

Use plain hyphens, commas, colons or separate sentences. Never introduce em
dash or en dash characters (U+2014 or U+2013), including HTML entities for
those characters, in page copy, code, comments, reports or commit messages.
Keep headings plain. Preserve historical measurements and scoring caveats.

Run `python3 scripts/check_benchmark_index.py` for benchmark index changes.
Run `python3 scripts/build_sitemap.py` after adding or editing pages; CI checks it is current.
Run `python3 -m unittest discover -s scripts -p 'test_*.py'` for regression tests,
including the SWE v4 bundle and report page checks.
Run the matching `python3 scripts/verify_swe_v4_v3N_pdf.py` (needs pypdf) after regenerating a PDF.
Run `python3 scripts/build_swe_v4_board.py --check` after touching any SWE v4 bundle; the leaderboard block is generated from them.
Run `python3 scripts/check_writing.py --base origin/main` before committing.
Keep the current preview PR unmerged until the user approves a merge.
