"""Tests for the release zip HACS downloads."""

import json
import stat
import zipfile
from pathlib import Path

from build_zip import build_zip

_ROOT = Path(__file__).resolve().parents[1]


def _entries(archive: Path) -> dict[str, zipfile.ZipInfo]:
    with zipfile.ZipFile(archive) as zf:
        return {info.filename: info for info in zf.infolist()}


def test_release_zip_contains_client_source(tmp_path: Path) -> None:
    """The zip holds the integration and the client's source as regular files, not links.

    HACS extracts the zip into the integration's own directory, so the entries sit at the
    zip's root.
    """
    archive = build_zip(tmp_path / "coop_dk.zip")

    entries = _entries(archive)
    for name in ("manifest.json", "__init__.py", "coop_client/__init__.py"):
        assert name in entries, sorted(entries)
        mode = entries[name].external_attr >> 16
        assert not stat.S_ISLNK(mode), name
    assert not any(".." in name.split("/") for name in entries)
    assert not any(name.startswith("/") for name in entries)
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in entries)


def test_release_zip_client_matches_the_package(tmp_path: Path) -> None:
    """Each client source file is in the zip with the package's bytes."""
    archive = build_zip(tmp_path / "coop_dk.zip")
    package = _ROOT / "packages" / "coop-client" / "src" / "coop_client"

    with zipfile.ZipFile(archive) as zf:
        for path in package.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                name = f"coop_client/{path.relative_to(package).as_posix()}"
                assert zf.read(name) == path.read_bytes(), name


def test_release_zip_name_is_the_one_hacs_looks_for() -> None:
    """hacs.json names the asset the release uploads."""
    hacs = json.loads((_ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["zip_release"] is True
    assert hacs["filename"] == "coop_dk.zip"
    release = (_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "coop_dk.zip" in release


def test_release_zip_follows_a_linked_directory_and_skips_bytecode(tmp_path: Path) -> None:
    """A linked directory's files go in under the link's name; bytecode stays out."""
    target = tmp_path / "client"
    (target / "__pycache__").mkdir(parents=True)
    (target / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    (target / "__pycache__" / "__init__.cpython-314.pyc").write_bytes(b"\0")
    source = tmp_path / "integration"
    source.mkdir()
    (source / "manifest.json").write_text("{}\n", encoding="utf-8")
    (source / "stray.pyc").write_bytes(b"\0")
    (source / "linked").symlink_to(Path("..") / "client")

    entries = _entries(build_zip(tmp_path / "out.zip", source=source))

    assert sorted(entries) == ["linked/__init__.py", "manifest.json"]
