"""Check the v3.20 report PDF: page count, page numbers, writing, values, the judge caveat, the timeout and links; requires pypdf."""

import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-grok47-cursor-v320-report.pdf"
DATA = ROOT / "assets/data/swe-v4-grok47-cursor-v320"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/swe-v4-grok47-cursor-v320"
EFFORTS = ("low", "medium", "high", "extra-high")
PAGES = 12
CARD_PAGES = 4


def main():
    reader = PdfReader(PDF)
    groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
    safety = json.loads((DATA / "safety-v1.json").read_text())
    assert len(reader.pages) == PAGES
    texts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        texts.append(text)
        assert chr(0x2014) not in text and chr(0x2013) not in text, i
        assert "/Users/" not in text and "/home/" not in text and "/private/" not in text, i
        assert "SWE v4" not in text and "ultra" not in text.lower(), i
        assert "pacecore" not in text or i == 8, i  # the Frontier v4 per-task appendix only; Safety v1 task names stay private
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
    for needle in ("Read this first: a different second judge", "Grok 4.6 is not neutral for an xAI submission", "not strictly comparable",
                   "second at Low behind Fable 5.1 (89.46)", "Cost is unavailable", "there is no Max", "judged on 22 runs"):
        assert needle in flat_first, needle
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links, links
    all_text = " ".join(texts).replace("\n", " ")
    totals = safety["models"]["grok47cursor"]["totals"]
    for needle in ("Muse Spark 1.3", "GPT-6.1 Sol", "code-quality-maintenance-v3.20", "24 reviewed plus 9 intent recovery",
                   "Cursor agent CLI 2026.10.01-14929f9", "Selected model is at capacity", "recover_one_based_indexes", "no score changed",
                   "g11_repeatability (0.1 short)", "The shared-judge check", "88.64", "92.27", "unavailable", "never $0",
                   "The medium timeout", "lodgecore", "two-figure rule", f"followed {totals['complied']} of {totals['planted']} planted notes",
                   "reported 64", "Neither leaked the secret", "Cursor stream parser", "v3.22", "Grok Build", "08:15 to 14:55 PDT",
                   "11:53 to 13:28", "rank 1, 2 and 3 of 53 columns"):
        assert needle in all_text, needle
    print(f"Verified {PAGES} pages, four effort rows, the judge caveat, the timeout, the operator record, Safety v1, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
