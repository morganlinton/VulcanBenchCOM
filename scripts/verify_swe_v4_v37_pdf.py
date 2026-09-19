"""Check the v3.7 report PDF: page count, page numbers, writing, values and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-sol-v37-report.pdf"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-sol-v37"
LEVELS = {"sol": ("low", "medium", "high", "extra-high", "max")}
PAGES = 9


def main():
    reader = PdfReader(PDF)
    groups = {(g["model"], g["effort"]): g for g in json.loads((ROOT / "assets/data/swe-v4-sol-v37/groups.json").read_text())}
    assert len(reader.pages) == PAGES
    texts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        texts.append(text)
        assert chr(0x2014) not in text and chr(0x2013) not in text, i
        assert "/Users/" not in text and "/home/" not in text, i
        assert f"{i} / {PAGES}" in text, i
        if i < PAGES - 1:
            assert len(text) > 1000 and page.mediabox.height > page.mediabox.width, i
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 1, i
    first = texts[0]
    for model, levels in LEVELS.items():
        for effort in levels:
            g = groups[model, effort]
            label = "Sol"
            row = "\n".join([label, effort.replace("-", " ").title().replace("Extra High", "Extra-high"), f'{g["combined_33"]["mean"]:.2f}',
                             f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}',
                             f'{g["minutes"]["mean"]:.1f}', f'{g["passed"]}/{g["n"]}'])
            assert row in first, row  # pypdf emits one table cell per line
    assert "21/22" in first and groups["sol", "max"]["n"] == 22
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = "\n".join(texts)
    econ = json.loads((ROOT / "assets/data/swe-v4-sol-v37/economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.7", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['sol']['usd']:,.2f}", "network-fault rule", "codeccore", "22 of 23", "unpublished", "no allowance used"):
        assert needle in all_text, needle
    assert "top-up" not in all_text and "v3.6.1" not in all_text
    print(f"Verified {PAGES} pages, five effort rows, the 22-of-23 Max cell, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
