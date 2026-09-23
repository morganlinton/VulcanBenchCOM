"""Check the v3.11 report PDF: page count, page numbers, writing, values and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-devin-swe2-v311-report.pdf"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-devin-swe2-v311"
LEVELS = {"swe2": ("medium", "high", "max")}
PAGES = 9


def main():
    reader = PdfReader(PDF)
    groups = {(g["model"], g["effort"]): g for g in json.loads((ROOT / "assets/data/swe-v4-devin-swe2-v311/groups.json").read_text())}
    assert len(reader.pages) == PAGES
    texts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        texts.append(text)
        assert chr(0x2014) not in text and chr(0x2013) not in text, i
        assert "/Users/" not in text and "/home/" not in text, i
        assert "SWE v4" not in text and "ultra" not in text, i
        assert f"{i} / {PAGES}" in text, i
        if i < PAGES - 1:
            assert len(text) > 1000 and page.mediabox.height > page.mediabox.width, i
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 1, i
    first = texts[0]
    for model, levels in LEVELS.items():
        for effort in levels:
            g = groups[model, effort]
            row = "\n".join(["SWE-2", effort.capitalize(), f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}',
                             f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}',
                             f'{g["minutes"]["mean"]:.1f}', f'{g["passed"]}/{g["n"]}'])
            assert row in first, row  # pypdf emits one table cell per line
    assert "15/20" in first and groups["swe2", "high"]["n"] == 20
    assert "21/22" in first and groups["swe2", "max"]["n"] == 22
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = "\n".join(texts)
    econ = json.loads((ROOT / "assets/data/swe-v4-devin-swe2-v311/economics.json").read_text())
    totals = econ["totals"]["swe2"]
    for needle in ("Muse Spark 1.3", "Grok 4.6", "GPT-5.6 Sol", "code-quality-maintenance-v3.11", "code-quality-maintenance-v3.9",
                   "code-quality-maintenance-v3.10", "gate 16", "single-panel rule", "24 reviewed plus 9 intent recovery",
                   "unavailable", f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h',
                   "cellarcore", "snapcore", "vaultcore", "freightcore", "65 of the 69 runs are judged", "20 of 23", "22 of 23"):
        assert needle in all_text, needle
    # Cost is unavailable, never a zero and never a rate table.
    for banned in ("$0", "cost tier Free", "free on Devin", "list rates", "rates checked"):
        assert banned not in all_text, banned
    assert totals["usd"] is None
    assert "no per-token rate" in all_text
    print(f"Verified {PAGES} pages, three effort rows, the judged-cell counts, the single-judge disclosure, the unavailable "
          "cost with no zero anywhere, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
