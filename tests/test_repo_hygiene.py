"""The private paths a capture or a dev Home Assistant leaves in the tree are gitignored."""

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".captures/x.flows",
        "config/configuration.yaml",
        "base.apk",
        "x.xapk",
        "decompiled/x.java",
    ],
)
def test_gitignore_covers_private_paths(path: str) -> None:
    result = subprocess.run(["git", "check-ignore", "-q", path], cwd=_ROOT, check=False)

    assert result.returncode == 0, f"{path} is not gitignored"
