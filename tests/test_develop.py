"""The dev Home Assistant's config links the integration from the working tree."""

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_develop_setup_only_links_the_integration() -> None:
    subprocess.run([str(_ROOT / "scripts/develop"), "--setup-only"], cwd=_ROOT, check=True)

    link = _ROOT / "config/custom_components/coop_dk"
    assert link.is_symlink()
    assert link.resolve() == (_ROOT / "custom_components/coop_dk").resolve()
    assert (_ROOT / "config/configuration.yaml").read_text().startswith("default_config:")
