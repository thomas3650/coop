"""Fail when a Markdown link in this repo points at a file or an anchor that is not there.

Checks every tracked `.md` file outside `docs/superpowers/` and `docs/archive/`, which
are dated records and are not kept up to date. Only `[text](target)` links are read: a
path in backticks may name a file as it was on the day. Makes no network request; an
`http(s)` or `mailto` target is skipped.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKIPPED = ("docs/superpowers/", "docs/archive/")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^(```|~~~).*?^\1\s*$", re.MULTILINE | re.DOTALL)
_ID = re.compile(r'<a\s+id="([^"]+)"')
_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: links and code marks dropped, spaces to dashes."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text).lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(text: str) -> set[str]:
    found = set(_ID.findall(text))
    seen: dict[str, int] = {}
    for heading in _HEADING.findall(_FENCE.sub("", text)):
        slug = _slug(heading)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug if count == 0 else f"{slug}-{count}")
    return found


def broken(root: Path, files: list[str]) -> list[str]:
    problems: list[str] = []
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        for target in _LINK.findall(_FENCE.sub("", text)):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path, _, fragment = target.partition("#")
            dest = (root / name).parent / path if path else root / name
            if not dest.exists():
                problems.append(f"{name}: {target} — no such file")
            elif (
                fragment
                and dest.suffix == ".md"
                and fragment not in anchors(dest.read_text(encoding="utf-8"))
            ):
                problems.append(f"{name}: {target} — no such anchor")
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    listed = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.split()
    files = [f for f in listed if not f.startswith(SKIPPED) and (root / f).exists()]
    problems = broken(root, files)
    for line in problems:
        print(line)
    print(f"{len(files)} files checked, {len(problems)} broken links")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
