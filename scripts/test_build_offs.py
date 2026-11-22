"""Regression checks for the build-off pages and the playable builds they host."""

import json
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

    def test_vote_boxes_match_the_vote_function(self):
        # api/build-off-vote.js only accepts the build-offs and choices it lists; a page must offer exactly those.
        function = (ROOT / "api" / "build-off-vote.js").read_text()
        listed = {slug: re.findall(r'"([^"]+)"', choices) for slug, choices in re.findall(r'^  "([^"]+)": \[([^\]]*)\],$', function, re.M)}
        self.assertTrue(listed)
        voting = {}
        for page in PAGES:
            text = page.read_text()
            boxes = re.findall(r'<div class="bo-vote" data-build-off="([^"]+)">', text)
            if not boxes:
                continue
            self.assertEqual(boxes, [page.stem], page)
            voting[page.stem] = re.findall(r'<button class="btn" type="button" data-choice="([^"]+)"', text)
            self.assertEqual(re.findall(r'<div class="bo-vote-row" data-choice="([^"]+)"', text), voting[page.stem], page)
            self.assertIn('<script src="../build-off-vote.js?v=', text, page)
            self.assertIn('<link rel="stylesheet" href="../build-offs.css?v=', text, page)
            self.assertIn("reader poll", text, page)
        self.assertEqual(voting, listed)

    def test_vote_function_keeps_previews_and_addresses_out_of_the_tally(self):
        function = (ROOT / "api" / "build-off-vote.js").read_text()
        self.assertIn('process.env.VERCEL_ENV === "production" ? "build-off-votes" : "build-off-votes-preview"', function)
        self.assertIn('createHmac("sha256", key)', function)
        self.assertIn('access: "private"', function)
        self.assertNotIn("address:", function)  # a stored record never carries the address
        self.assertIn(".build-off-votes-local.json", (ROOT / ".gitignore").read_text())

    def test_renamed_playable_build_redirects(self):
        # Fall Line became Tahoe Ski Adventures; links to the old address must keep working.
        self.assertFalse((BUILD_OFFS / "play" / "fall-line").exists())
        redirects = {r["source"]: r["destination"] for r in json.loads((ROOT / "vercel.json").read_text())["redirects"]}
        self.assertEqual(redirects["/build-offs/play/fall-line/:path*"], "/build-offs/play/tahoe-ski-adventures/:path*")
        for bare in ("/build-offs/play/fall-line", "/build-offs/play/fall-line/"):  # ":path*" misses the bare folder
            self.assertEqual(redirects[bare], "/build-offs/play/tahoe-ski-adventures/index.html")
        self.assertTrue((BUILD_OFFS / "play" / "tahoe-ski-adventures" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
