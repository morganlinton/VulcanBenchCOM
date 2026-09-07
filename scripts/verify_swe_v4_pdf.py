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
    assert len(reader.pages) == 9
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        assert chr(0x2014) not in text and chr(0x2013) not in text
        assert f"{i} / 9" in text
        if i < 9:
            assert len(text) > 1200 and page.mediabox.height > page.mediabox.width
        else:
            assert page.mediabox.width > page.mediabox.height and len(page.images) >= 2
    for index, model in ((6, "astra"), (7, "fable")):
        page = reader.pages[index].extract_text()
        subset = [r for r in rows if r["model"] == model]
        labels = {r["task"].removeprefix("legacy-").split("-")[0] for r in subset}
        assert len(labels) == 23 and all(label in page for label in labels)
        expected = Counter(f'{r["combined"] * 100:.2f}' + ("*" if r["fallback"] else "") for r in subset)
        found = Counter(re.findall(r"\b\d+\.\d{2}\*?", page))
        assert not (expected - found), expected - found
        # Validate task-to-effort bindings, not only the multiset of scores.
        for task in sorted({r["task"] for r in subset}):
            label = task.removeprefix("legacy-").split("-")[0]
            start = page.index(label) + len(label)
            actual = re.findall(r"\b\d+\.\d{2}\*?", page[start:])[:5]
            expected_row = [next(f'{r["combined"] * 100:.2f}' + ("*" if r["fallback"] else "")
                                 for r in subset if r["task"] == task and r["effort"] == e)
                            for e in ("low", "medium", "high", "extra-high", "max")]
            assert actual == expected_row, (task, actual, expected_row)
    links = [a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in page.get("/Annots", [])]
    assert GITHUB in links
    all_text = "\n".join(p.extract_text() for p in reader.pages)
    assert all(value in all_text for value in ("70.75", "$225.04", "$419.42", "$1,159.10", "1,380", "1,386"))
    sensitivity = json.loads((ROOT / "assets/data/swe-v4-astra-fable51/sensitivity.json").read_text())
    appendix = reader.pages[4].extract_text()
    for r in sensitivity["rows"]:
        assert f'{r["paired_bootstrap_95_low"]:+.2f} to {r["paired_bootstrap_95_high"]:+.2f}' in appendix
    print("Verified nine pages, 230 task/effort scores, sensitivity, page numbers, GitHub link and writing.")


if __name__ == "__main__":
    main()
