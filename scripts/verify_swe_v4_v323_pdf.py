"""Check the v3.23 report PDF: page count, page numbers, writing, values, the disclosures and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-sonnet55-v323-report.pdf"
DATA = ROOT / "assets/data/swe-v4-sonnet55-v323"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-sonnet55-v323"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PAGES = 10  # keep equal to PAGES in render_swe_v4_v323_report.py
CARD_PAGES = 2


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
        assert "SWE v4" not in text and "ultra" not in text.lower() and "TBD" not in text, i
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
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = " ".join(texts).replace("\n", " ")
    econ = json.loads((DATA / "economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.23", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['sonnet55']['usd']:,.2f}", "Claude Code 2.1.291 to 2.1.293", "tagged-worktree rule",
                   "task-hash-bridge-sonnet55.json", "107 cached .pyc files", "Judge settings and versions", "private backup",
                   "2026.10.01-e373342", "2026.09.02-c22c1a3", "launcher script", "g11_repeatability", "g04_formatting_is_presentation", "one-gate allowance",
                   "two cache-read prices", "no run used it", "paddockcore on 2.1.293", "Routine v1 Code quality",
                   "Beside Claude Opus 5.5 and Claude Fable 5.1", "of the board's", "06:49 PDT", "03:38 PDT"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, five effort rows, the disclosures, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
