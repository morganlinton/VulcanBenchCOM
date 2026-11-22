"""Regression checks for the build-off pages and the playable builds they host."""

import re
import unittest
from urllib.parse import unquote, urlsplit

from check_benchmark_index import ROOT

BUILD_OFFS = ROOT / "build-offs"
PAGES = sorted(BUILD_OFFS.glob("[0-9][0-9]-*.html"))
PLAYABLE = sorted(p.parent for p in (BUILD_OFFS / "play").glob("*/index.html"))


def local_targets(page):
    """Files that a page's href and src attributes point at on this site."""
    for link in re.findall(r'(?:href|src)="([^"]+)"', page.read_text()):
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        yield link, (page.parent / unquote(parsed.path)).resolve()


class BuildOffTests(unittest.TestCase):
    def test_index_lists_every_build_off(self):
        self.assertTrue(PAGES)
        index = (ROOT / "build-offs.html").read_text()
        self.assertEqual(re.findall(r'<a class="report-row" href="(build-offs/[^"]+)"', index), [f"build-offs/{p.name}" for p in reversed(PAGES)])

    def test_home_links_the_newest_build_off(self):
        self.assertIn(f'<a class="report-row" href="build-offs/{PAGES[-1].name}"', (ROOT / "index.html").read_text())

    def test_local_links_resolve(self):
        for page in [ROOT / "build-offs.html", *PAGES, *(d / "index.html" for d in PLAYABLE)]:
            for link, target in local_targets(page):
                self.assertTrue(target.is_file(), f"{page.relative_to(ROOT)}: {link}")

    def test_pages_say_what_a_build_off_is_not(self):
        for page in PAGES:
            text = page.read_text()
            self.assertIn("not a benchmark", text, page)
            self.assertIn("How each entry was made", text, page)
            self.assertIn(f'<link rel="canonical" href="https://vulcanbench.com/build-offs/{page.name}">', text, page)

    def test_every_playable_build_is_linked_and_licensed(self):
        self.assertTrue(PLAYABLE)
        pages = "".join(p.read_text() for p in PAGES)
        notice = (BUILD_OFFS / "play" / "THIRD_PARTY_LICENSES.txt").read_text()
        for entry in PLAYABLE:
            self.assertIn(f'href="play/{entry.name}/index.html"', pages)
            self.assertIn(f"{entry.name}/", notice)


if __name__ == "__main__":
    unittest.main()
