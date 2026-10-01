"""Check the v3.18 report PDF: page count, page numbers, writing, values, the one-panel row and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-gpt61-sol-v318-report.pdf"
DATA = ROOT / "assets/data/swe-v4-gpt61-sol-v318"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt61-sol-v318"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PAGES = 11
CARD_PAGES = 3


def main():
    reader = PdfReader(PDF)
    groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
    assert len(reader.pages) == PAGES
    texts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        texts.append(text)
        assert chr(0x2014) not in text and chr(0x2013) not in text, i
        assert "/Users/" not in text and "/home/" not in text and "/private/" not in text, i
        assert "SWE v4" not in text and "ultra" not in text.lower(), i
        assert f"{i} / {PAGES}" in text, i
        if i <= PAGES - CARD_PAGES:
            assert len(text) > 1000 and page.mediabox.height > page.mediabox.width, i
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 2, i  # the logo and a card
    first = texts[0]
    for effort in EFFORTS:
        g = groups[effort]
        row = "\n".join([effort.replace("-", " ").title().replace("Extra High", "Extra-high"), f'{g["combined_33"]["mean"]:.2f}',
                         f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}',
                         f'{g["minutes"]["mean"]:.1f}', str(g["n"]), f'{g["passed_all_runs"]}/23'])
        assert row in first, row  # pypdf emits one table cell per line
    flat_first = first.replace("\n", " ")
    assert "every cell is judged on 23 runs" in flat_first and "scored from Muse Spark 1.3 alone" in flat_first
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = " ".join(texts).replace("\n", " ")
    econ = json.loads((DATA / "economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.18", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['gpt61sol']['usd']:,.2f}", "$0.39 per task", "Codex CLI 0.159.0", "0.155.0, 0.157.0 and 0.158.0",
                   "GPT-6 Sol's v3.17 judging", "The one-panel Medium row", "invalidate_unrecoverable_primary", "recover_escaped_excerpts",
                   "54.00", "78.4", "paddockcore", "codeccore", "Three generations of Sol", "no allowance used", "no long-context premium",
                   "April 30, 2026", "saturation-pruning", "231 of the 231", "ranks 13 of the board's 49 columns", "index diff"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, five effort rows, the one-panel Medium row, the operator record, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
