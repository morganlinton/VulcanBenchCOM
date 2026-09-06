"""Check final PDF text, score matrices, links and page geometry; requires pypdf."""

import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/reports/vulcanbench-swe-v4-astra-fable51-report.pdf"
GITHUB = "https://github.com/morganlinton/VulcanBenchCOM/tree/9bc9a25cf7d26d75ed5b8f5fa9ccd472bf093c8d/assets/data/swe-v4-astra-fable51"


def main():
    reader = PdfReader(PDF)
    rows = json.loads((ROOT / "assets/data/swe-v4-astra-fable51/runs.json").read_text())["rows"]
    assert len(reader.pages) == 7
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        assert chr(0x2014) not in text and chr(0x2013) not in text
        assert f"{i} / 7" in text
        if i < 7:
            assert len(text) > 1200 and page.mediabox.height > page.mediabox.width
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 2
    for index, model in ((4, "astra"), (5, "fable")):
        page = reader.pages[index].extract_text()
        subset = [r for r in rows if r["model"] == model]
        labels = {r["task"].removeprefix("legacy-").split("-")[0] for r in subset}
        assert len(labels) == 23 and all(label in page for label in labels)
        expected = Counter(f'{r["combined"] * 100:.2f}' + ("*" if r["fallback"] else "") for r in subset)
        found = Counter(re.findall(r"\b\d+\.\d{2}\*?", page))
        assert not (expected - found), expected - found
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links
    all_text = "\n".join(p.extract_text() for p in reader.pages)
    assert all(value in all_text for value in ("70.75", "$225.04", "$419.42", "$1,159.10", "1,380", "1,386"))
    print("Verified seven pages, all 230 task scores, page numbers, GitHub link and no em/en dashes.")


if __name__ == "__main__":
    main()
