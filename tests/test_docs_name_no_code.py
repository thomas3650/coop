"""The docs describe how things behave; they never name this repo's code.

Covers every tracked `.md` file under `docs/` and `README.md`. `docs/superpowers/` and
`docs/research/` are dated records and may name files. `CLAUDE.md` and `.claude/` are agent
instructions, which must name scripts. A command in a fenced block of `README.md` is
allowed: a person types it.
"""

import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGES = ("coop_client", "coop_dk")
_MODULE_DIRS = (
    Path("packages/coop-client/src/coop_client"),
    Path("custom_components/coop_dk"),
)
_PATH_PREFIXES = ("packages/", "custom_components/", "scripts/")
_SKIPPED = ("docs/superpowers/", "docs/research/")
_FENCE = re.compile(r"^(```|~~~)")


def _forbidden(root: Path) -> re.Pattern[str]:
    """Package names and source-path prefixes anywhere; module stems only as code."""
    stems = sorted(
        path.stem
        for module_dir in _MODULE_DIRS
        if (root / module_dir).is_dir()
        for path in (root / module_dir).rglob("*.py")
        if path.stem != "__init__"
    )
    names = [re.escape(name) for name in _PACKAGES]
    prefixes = [re.escape(prefix) for prefix in _PATH_PREFIXES]
    modules = [rf"{re.escape(stem)}\.py" for stem in stems]
    dotted = [rf"(?:{'|'.join(names)})\.{re.escape(stem)}" for stem in stems]
    alternatives = [*dotted, *modules, *names]
    return re.compile(
        rf"(?<![\w/])(?:{'|'.join(alternatives)})\b|(?<![\w/.-])(?:{'|'.join(prefixes)})"
    )


def _docs(root: Path) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [
        root / name
        for name in listed
        if (name == "README.md" or name.startswith("docs/")) and not name.startswith(_SKIPPED)
    ]


def find_code_names(root: Path) -> list[tuple[Path, int, str]]:
    """Every line of a covered doc that names this repo's code, as (file, line number, match)."""
    pattern = _forbidden(root)
    hits: list[tuple[Path, int, str]] = []
    for doc in _docs(root):
        in_fence = False
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            if _FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            if in_fence and doc.name == "README.md" and doc.parent == root:
                continue
            hits.extend((doc, number, match.group(0)) for match in pattern.finditer(line))
    return hits


def test_docs_name_no_code() -> None:
    hits = find_code_names(_ROOT)

    assert hits == [], "\n".join(
        f"{doc.relative_to(_ROOT)}:{number}: names code ({name})" for doc, number, name in hits
    )


def _repo(tmp_path: Path, doc: str, text: str) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "packages/coop-client/src/coop_client").mkdir(parents=True)
    (tmp_path / "packages/coop-client/src/coop_client/scrub.py").write_text("")
    (tmp_path / doc).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / doc).write_text(text, encoding="utf-8")
    return tmp_path


def test_docs_name_no_code_catches_a_module_name(tmp_path: Path) -> None:
    root = _repo(tmp_path, "docs/api.md", "The refresh lives in coop_client.\n")

    assert [(number, name) for _, number, name in find_code_names(root)] == [(1, "coop_client")]


def test_docs_name_no_code_catches_a_module_file_and_a_source_path(tmp_path: Path) -> None:
    root = _repo(tmp_path, "docs/api.md", "See scrub.py.\nAnd packages/coop-client/x.\n")

    assert [(number, name) for _, number, name in find_code_names(root)] == [
        (1, "scrub.py"),
        (2, "packages/"),
    ]


def test_docs_name_no_code_allows_ordinary_words_and_readme_commands(tmp_path: Path) -> None:
    root = _repo(tmp_path, "README.md", "Captures are scrubbed.\n\n```\nscripts/develop\n```\n")

    assert find_code_names(root) == []


def test_docs_name_no_code_skips_dated_records(tmp_path: Path) -> None:
    root = _repo(tmp_path, "docs/superpowers/plans/p.md", "Create coop_client/scrub.py.\n")

    assert find_code_names(root) == []
