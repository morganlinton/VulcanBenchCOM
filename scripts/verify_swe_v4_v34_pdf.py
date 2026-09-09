"""Check the v3.4 report PDF: page count, page numbers, writing, values and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-astra-fable51-v34-report.pdf"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-astra-fable51-v34"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PAGES = 10


def main():
    reader = PdfReader(PDF)
    groups = {(g["model"], g["effort"]): g for g in json.loads((ROOT / "assets/data/swe-v4-astra-fable51-v34/groups.json").read_text())}
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
    for model in ("astra", "fable"):
        for effort in EFFORTS:
            g = groups[model, effort]
            label = "Astra" if model == "astra" else "Fable 5.1"
            row = "\n".join([label, effort.replace("-", " ").title(), f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}',
                             f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}', f'{g["minutes"]["mean"]:.1f}', f'{g["passed"]}/23'])
            assert row in first, row  # pypdf emits one table cell per line
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = "\n".join(texts)
    econ = json.loads((ROOT / "assets/data/swe-v4-astra-fable51-v34/economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.4", "code-quality-maintenance-v3.3", "g01_validity", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['astra']['usd']:,.2f}", f"${econ['totals']['fable']['usd']:,.2f}", f"${econ['totals']['astra']['long_context_upper_usd']:,.2f}"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, ten effort rows, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
