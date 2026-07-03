# VulcanBench.com

Static marketing + results site for VulcanBench, the open-source coding benchmark.

## Structure
- `index.html` — homepage (what VulcanBench is + the two primary CTAs: benchmarks, repo)
- `benchmarks.html` — index of every published run, newest first
- `benchmarks/NN-*.html` — one dedicated journal-style page per benchmark (model card + findings + table + downloads)
- `style.css` — shared journal stylesheet (serif, paper-white, matches the model cards)
- `assets/cards/` — model card PNGs
- `assets/reports/` — downloadable full-report PDFs

## Adding a new benchmark
1. Drop the model card PNG in `assets/cards/` and any PDF in `assets/reports/`.
2. Copy the newest `benchmarks/NN-*.html` as a template, update the numbers/findings.
3. Add a `.report-row` entry at the top of `benchmarks.html`.

## Local preview
    python3 -m http.server 8899
Then open http://localhost:8899

Pure static HTML/CSS, no build step. Deploys as-is to Netlify, Vercel, GitHub Pages, or any static host.
