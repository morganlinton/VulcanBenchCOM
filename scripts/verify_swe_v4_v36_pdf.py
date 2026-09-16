"""Check the v3.6 report PDF: page count, page numbers, writing, values and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-terra-v36-report.pdf"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-terra-v36"
LEVELS = {"terra": ("low", "medium", "high", "extra-high", "max")}
PAGES = 9


def main():
    reader = PdfReader(PDF)
    groups = {(g["model"], g["effort"]): g for g in json.loads((ROOT / "assets/data/swe-v4-terra-v36/groups.json").read_text())}
    assert len(reader.pages) == PAGES
    texts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        texts.append(text)
        assert chr(0x2014) not in text and chr(0x2013) not in text, i
        assert f"{i} / {PAGES}" in text, i
        if i < PAGES - 1:
            assert len(text) > 1000 and page.mediabox.height > page.mediabox.width, i
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 1, i
    first = texts[0]
    for model, levels in LEVELS.items():
        for effort in levels:
            g = groups[model, effort]
            label = "Terra"
            row = "\n".join([label, effort.replace("-", " ").title().replace("Extra High", "Extra-high"), f'{g["combined_33"]["mean"]:.2f}',
                             f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}',
                             f'{g["minutes"]["mean"]:.1f}', f'{g["passed"]}/{g["n"]}'])
            assert row in first, row  # pypdf emits one table cell per line
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = "\n".join(texts)
    econ = json.loads((ROOT / "assets/data/swe-v4-terra-v36/economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.6", "g11_repeatability", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['terra']['usd']:,.2f}", "network-fault rule", "top-up"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, five effort rows, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
