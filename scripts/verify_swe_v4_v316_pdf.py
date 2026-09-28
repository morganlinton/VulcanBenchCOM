"""Check the v3.16 report PDF: page count, page numbers, writing, values, both combined figures and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-gpt6-luna-v316-report.pdf"
DATA = ROOT / "assets/data/swe-v4-gpt6-luna-v316"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-gpt6-luna-v316"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PAGES = 9


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
        if i < PAGES - 1:
            assert len(text) > 1000 and page.mediabox.height > page.mediabox.width, i
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 1, i
    first = texts[0]
    for effort in EFFORTS:
        g = groups[effort]
        row = "\n".join([effort.replace("-", " ").title().replace("Extra High", "Extra-high"), f'{g["combined_33"]["mean"]:.2f}',
                         f'{g["combined_33"]["se"]:.2f}', f'{g["combined_timeouts_zero"]["mean"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                         f'{g["code_quality"]["mean"]:.2f}', f'{g["minutes"]["mean"]:.1f}', str(g["n"]), f'{g["passed_all_runs"]}/23'])
        assert row in first, row  # pypdf emits one table cell per line
    assert "71.94 at Extra-high and 67.26 at Max" in first.replace("\n", " ")
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = " ".join(texts).replace("\n", " ")
    econ = json.loads((DATA / "economics.json").read_text())
    for needle in ("Muse Spark 1.3", "Grok 4.6", "code-quality-maintenance-v3.16", "24 reviewed plus 9 intent recovery",
                   f"${econ['totals']['gpt6luna']['usd']:,.2f}", "Codex CLI 0.155.0", "0.153.4", "88 idle minutes", "GPT-6 Sol",
                   "unpriced, not $0", "paddockcore", "cellarcore", "lodgecore", "depotcore", "g11_repeatability", "g04_formatting_is_presentation",
                   "one-gate allowance", "counts timeouts as failures", "no long-context premium"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, five effort rows with both combined figures, the six timeouts, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
