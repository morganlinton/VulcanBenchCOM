"""Build sitemap.xml from the pages on disk, dating each entry by its last git change.

    python3 scripts/build_sitemap.py            # write sitemap.xml
    python3 scripts/build_sitemap.py --check    # exit 1 if sitemap.xml is stale

A page with uncommitted changes is dated today. Priorities: the homepage 1.0,
the benchmarks index, methodology and SWE v4 reports 0.9, archive reports and
the leaderboard 0.8, everything else 0.7. 404.html is never listed.
"""

import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://vulcanbench.com/"


def lastmod(path):
    if subprocess.run(["git", "status", "--porcelain", "--", str(path)], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        return datetime.date.today().isoformat()
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return out or datetime.date.today().isoformat()


def priority(rel):
    if rel == "index.html":
        return "1.0"
    if rel in ("benchmarks.html", "methodology.html") or rel.startswith("benchmarks/swe-v4"):
        return "0.9"
    if rel.startswith("benchmarks/") or rel == "leaderboard.html":
        return "0.8"
    return "0.7"


def order(rel):
    groups = ("index.html", "benchmarks.html", "leaderboard.html", "methodology.html", "methodology-notes.html", "benchmark-your-stack.html",
              "benchmark-your-model.html", "support.html", "blog.html")
    if rel in groups:
        return (0, groups.index(rel), rel)
    if rel.startswith("benchmarks/swe-v4"):
        return (1, 0, rel)
    if rel.startswith("benchmarks/"):
        return (2, 0, rel)
    if rel.startswith("blog/"):
        return (3, 0, rel)
    return (4, 0, rel)


def build():
    pages = sorted((p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.html") if ".git" not in p.parts and p.name != "404.html"), key=order)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in pages:
        loc = SITE if rel == "index.html" else SITE + rel
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod(ROOT / rel)}</lastmod><priority>{priority(rel)}</priority></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    text = build()
    target = ROOT / "sitemap.xml"
    if "--check" in sys.argv:
        if target.read_text() != text:
            print("sitemap.xml is stale; run python3 scripts/build_sitemap.py")
            sys.exit(1)
        print("sitemap.xml is current")
        return
    target.write_text(text)
    print(f"wrote {target.name} with {text.count('<url>')} entries")


if __name__ == "__main__":
    main()
