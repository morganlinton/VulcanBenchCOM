# VulcanBench.com

Static marketing + results site for [VulcanBench](https://github.com/morganlinton/VulcanBench), the open-source coding benchmark.

## Pages
- `index.html`: homepage: what VulcanBench is, an animated live-run terminal, the five newest reports (a test keeps them in step with `benchmarks.html`) and the ways to work with VulcanBench
- `benchmarks.html`: suite-separated results, with the current Frontier v4 comparison first and all earlier reports in a labeled archive
- `benchmarks/safety-v1-opus55.html`: Claude Opus 5.5 on VulcanBench Safety v1 (harmful instructions hidden in the repository), with the standalone card and per-level and per-kind tables
- `benchmarks/swe-v4-gpt61-terra-v329.html`: GPT-6.1 Terra through Codex CLI 0.159.0 at all five effort levels under Code quality protocol v3.29 (judged by Muse Spark 1.3 and Grok 4.6), with the comparison with Claude Opus 5.5, GPT-6.1 Sol and GPT-6 Astra and with GPT-5.6 Terra, cost and tokens, calibration record, the Max settlecore recovery and Codex notice disclosures, evidence links and the redacted traces repository
- `benchmarks/swe-v4-beam-v328.html`: Reflection Beam through Mirror CLI 0.1.1 at all five effort levels under Code quality protocol v3.28 (judged by Muse Spark 1.3 and GPT-6.1 Sol), with both combined figures for the runs that left no code, time and tokens (no price exists), the comparison with Claude Opus 5.5, GPT-6.1 Sol and GPT-6 Astra, calibration record, the judge-panel, exclusion and harness disclosures and evidence links
- `benchmarks/swe-v4-deepseek-flash-v327.html`: DeepSeek V4.1 Flash through DeepSeek Harness 0.2.1-rc.2 at Low, High and Max under Code quality protocol v3.27 (judged by Muse Spark 1.3 and GPT-6.1 Sol), with list and billed cost, the comparison with Claude Opus 5.5 and GPT-6.1 Sol, calibration record, the judge-panel and harness disclosures and evidence links
- `benchmarks/swe-v4-musewonder-full-v326.html`: Muse Wonder Full through Muse Code in Contributor mode at every effort level it offers under Code quality protocols v3.26 to v3.26.3 (judged by Claude Opus 5.5 and GPT-6.1 Sol), with both combined figures for the two timeouts, the estimated cost, calibration record, the judge-panel and Muse Code version disclosures, evidence links and the traces repository
- `benchmarks/swe-v4-haiku55-vs-frontier.html`: Claude Haiku 5.5 vs Claude Sonnet 5.5, GPT-6.1 Sol and GPT-6 Luna on Frontier v4, every effort level side by side from the four published bundles, with the three comparison cards, methods and caveats and links to every evidence bundle
- `benchmarks/swe-v4-haiku55-v324.html`: Claude Haiku 5.5 through Claude Code at every effort level under Code quality protocol v3.24, with PDF, calibration record, the price-tier floor and ceiling, the classifier-stop and unpublished-probe disclosures, and evidence links
- `benchmarks/swe-v4-sonnet55-vs-frontier.html`: Claude Sonnet 5.5 vs Claude Opus 5.5 vs GPT-6.1 Sol on Frontier v4, every effort level side by side from the three published bundles, with the methods and caveats and links to every evidence bundle
- `benchmarks/swe-v4-sonnet55-v323.html`: Claude Sonnet 5.5 through Claude Code at every effort level under Code quality protocol v3.23 (judged by Muse Spark 1.3 and Grok 4.6, Grok on a newer Cursor CLI), with PDF, calibration record, the card beside Claude Opus 5.5 and Claude Fable 5.1, the task hash bridge and Claude Code version disclosures, and evidence links
- `benchmarks/swe-v4-grok47-cursor-v320.html`: Grok 4.7 through Cursor at every effort level Cursor offers under Code quality protocol v3.20 (judged by Muse Spark 1.3 and GPT-6.1 Sol), with PDF, calibration record, the shared-judge check, cards beside the leaders and on Safety v1, and evidence links
- `benchmarks/swe-v4-gpt61-sol-v318.html`: GPT-6.1 Sol through Codex at every effort level under Code quality protocol v3.18, with PDF, calibration record, the three-generation Sol comparison card and evidence links
- `benchmarks/swe-v4-gpt6-sol-v317.html`: GPT-6 Sol through Codex at every effort level under Code quality protocol v3.17, with PDF, calibration record, GPT-5.6 Sol and GPT-6 family comparison cards and evidence links
- `benchmarks/swe-v4-gpt6-luna-v316.html`: GPT-6 Luna through Codex at every effort level under Code quality protocol v3.16, with both combined figures (judged runs, and timeouts counted as 0), PDF, calibration record and evidence links
- `benchmarks/swe-v4-sol-v37.html`: GPT-5.6 Sol through Codex at every effort level under Code quality protocol v3.7, with PDF, calibration record and evidence links
- `benchmarks/swe-v4-terra-v36.html`: GPT-5.6 Terra through Codex at every effort level under Code quality protocol v3.6, with PDF, calibration record and evidence links
- `benchmarks/swe-v4-gpt55-luna-v35.html`: GPT-5.5 vs. GPT-5.6 Luna through Codex at every effort level under Code quality protocol v3.5, with PDF, calibration record and evidence links
- `benchmarks/swe-v4-astra-fable51-v34.html`: the same runs rescored under Code quality protocol v3.4 (33% weight, neutral Muse Spark 1.3 and Grok 4.6 panel), with PDF, calibration record and evidence links
- `benchmarks/NN-*.html`: one journal-style page per report (abstract, findings, table, figure, downloads)
- `leaderboard.html`: directs readers to suite-specific results and the frozen earlier-suite archive
- `methodology.html`: how VulcanBench measures (decontamination, grading, metrics, sandbox, effort, economics)
- `404.html`: styled not-found page
- `style.css`: shared stylesheet (serif journal look with an ember accent)
- `site.js`: homepage terminal animation + scroll reveals

## Assets
- `assets/logo.png`: the VulcanBench mark (used in masthead, footer, favicon)
- `assets/og-image.png`: 1200×630 social share image
- `assets/cards/reportN-*.png`: per-report model cards and evals cards (3200×1800)
- `assets/reports/*.pdf`: full technical report PDFs
- `assets/leaderboard/v3-*.png`: leaderboard cards (rankings, speed, cost, effort curves, plus a 16:9 OG variant), generated by `scripts/rankings-chart/make_cards.py` and `make_efforts.py` in the harness repo

Every report page and the leaderboard carry a "Share on X" button (an `x.com/intent/post` link prefilled with the page title and URL; the OG card is the preview) next to the card download.

The cards, PDFs, and OG image are generated by scripts that render HTML with headless Chrome; the model/eval data
in them is sourced from the VulcanBench harness run output. Regenerate with `vulcanbench leaderboard` / the harness,
not by editing the images.

## SEO / social
Each page carries a canonical URL, Open Graph + Twitter card tags, and the homepage includes JSON-LD. `sitemap.xml`
and `robots.txt` are at the root. **All absolute URLs are hardcoded to `https://vulcanbench.com`; update them if the
domain changes.**

## Local preview
    python3 -m http.server 8899
Then open http://localhost:8899

The benchmark index uses `benchmarks-suites.css` for page-scoped styles.
Keep new suite results in their own section, never in a pooled ranking with
older suites. Use the original report links and scoring conventions in the
archive. Run `python3 scripts/check_benchmark_index.py` after index edits.

The Muse Wonder Full record, `assets/data/swe-v4-musewonder-full-v326/`, has no PDF; it is exported
by `python3 scripts/export_swe_v4_v326_evidence.py --harness-root ../VulcanBench`, which reads the four
judging rounds, the two run roots and the harness card, and refuses to write if any number differs.

The GPT-6.1 Terra record, `assets/data/swe-v4-gpt61-terra-v329/`, has no PDF; it is exported
by `python3 scripts/export_swe_v4_v329_evidence.py --harness-root ../VulcanBench --judging <v3.29 round>`, which reads the
v3.29 judging round, the sweep's run summaries and the harness card table, and refuses to write if any number differs.

The Reflection Beam record, `assets/data/swe-v4-beam-v328/`, has no PDF; it is exported
by `python3 scripts/export_swe_v4_v328_evidence.py --harness-root ../VulcanBench`, which reads the v3.28
judging round, the sweep's run summaries and the harness card table, and refuses to write if any number differs.

The DeepSeek V4.1 Flash record, `assets/data/swe-v4-deepseek-flash-v327/`, has no PDF; it is exported
by `python3 scripts/export_swe_v4_v327_evidence.py --harness-root ../VulcanBench`, which reads the v3.27
judging round, the sweep's run summaries and the harness card data, and refuses to write if any number differs.

Each Frontier v4 report PDF is generated directly from its public record in
`assets/data/swe-v4-astra-fable51-v34/`, `assets/data/swe-v4-gpt55-luna-v35/`,
`assets/data/swe-v4-terra-v36/`, `assets/data/swe-v4-sol-v37/`,
`assets/data/swe-v4-gpt6-luna-v316/`, `assets/data/swe-v4-gpt6-sol-v317/`, `assets/data/swe-v4-gpt61-sol-v318/`, `assets/data/swe-v4-grok47-cursor-v320/`, `assets/data/swe-v4-sonnet55-v323/` and `assets/data/swe-v4-haiku55-v324/`, which the matching `scripts/export_swe_v4_v3N_evidence.py`
(`--harness-root ../VulcanBench`) export from the frozen harness results; the v3.20 exporter also takes
`--conduct-root ../VulcanConduct` to re-derive its Safety v1 aggregates, and the v3.23 and v3.24 exporters take `--docs-root`, a harness
checkout that carries the population record (and, for Sonnet 5.5, the task hash bridge and judge settings file); `--recovered-protocols` optionally checks the recovered v3.3 and v3.4 protocol files. The renderers
use ReportLab and the Geist, Chakra Petch and IBM Plex Mono TTF files already used
by the harness chart generator:

```sh
python3 scripts/check_benchmark_index.py
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_writing.py --base origin/main
python3 scripts/render_swe_v4_v34_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-astra-fable51-v34
python3 scripts/verify_swe_v4_v34_pdf.py
python3 scripts/render_swe_v4_v35_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt55-luna-v35
python3 scripts/verify_swe_v4_v35_pdf.py
python3 scripts/render_swe_v4_v36_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-terra-v36
python3 scripts/verify_swe_v4_v36_pdf.py
python3 scripts/render_swe_v4_v37_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-sol-v37
python3 scripts/verify_swe_v4_v37_pdf.py
python3 scripts/render_swe_v4_v316_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt6-luna-v316
python3 scripts/verify_swe_v4_v316_pdf.py
python3 scripts/render_swe_v4_v317_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt6-sol-v317
python3 scripts/verify_swe_v4_v317_pdf.py
python3 scripts/render_swe_v4_v318_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt61-sol-v318
python3 scripts/verify_swe_v4_v318_pdf.py
python3 scripts/render_swe_v4_v320_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-grok47-cursor-v320
python3 scripts/verify_swe_v4_v320_pdf.py
python3 scripts/render_swe_v4_v323_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-sonnet55-v323
python3 scripts/verify_swe_v4_v323_pdf.py
python3 scripts/render_swe_v4_v324_report.py --fonts /path/to/VulcanBench/scripts/rankings-chart --github-url https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-haiku55-v324
python3 scripts/verify_swe_v4_v324_pdf.py
```

Rasterise all rendered pages and check the extracted text for forbidden
dash characters before publishing a regenerated PDF. The model card is
preserved as a full-page appendix, without image edits.

The public evidence includes a flat 230-run CSV, deterministic sensitivity
analysis, a reproduction guide with pinned sources and explicit execution
limits, and a proposed future review-calibration plan. The plan is not used
to score this comparison. Keep the agreed 20% Code quality weight unchanged.
Publication CI validates the evidence, prices token receipts, tests negative
cases, checks the PDF, and rejects new forbidden dash characters or entities.
Historical archived reports are not rewritten by the writing guard.

Pure static HTML/CSS/JS, no build step. Deploys as-is to Netlify, Vercel, GitHub Pages, or any static host
(the root `404.html` is picked up automatically by all three).
