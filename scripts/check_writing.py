"""Reject forbidden dash characters or entities in new or changed text lines.

Historical report files remain intact. This prevents additions to any tracked
text file, including code, comments and documentation, without rewriting archives.
"""

import argparse
import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def forbidden(text):
    return any(c in html.unescape(text) for c in (chr(0x2013), chr(0x2014)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    subprocess.run(["git", "rev-parse", "--verify", args.base + "^{commit}"], cwd=ROOT, check=True, capture_output=True)
    diff = subprocess.check_output(["git", "diff", "--no-ext-diff", "--unified=0", args.base, "--"], cwd=ROOT).decode("utf-8", errors="replace")
    failures, file = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            file = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and forbidden(line[1:]):
            failures.append(file)
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, untracked):
        raw = (ROOT / name).read_bytes()
        if b"\0" in raw:
            continue
        try:
            if forbidden(raw.decode("utf-8")):
                failures.append(name)
        except UnicodeDecodeError:
            pass
    assert not failures, "Forbidden dash in changed text: " + ", ".join(sorted(set(failures)))
    print("No forbidden dash characters or HTML entities in new text.")


if __name__ == "__main__":
    main()
