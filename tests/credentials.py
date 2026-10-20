"""Read the owner's Coop credentials from the repo-root `.env`. Test use only.

The only module in the test suite that reads `.env`. Not in `coop_client`: a library
must not walk up the filesystem looking for a dotfile.

Gated, not just named. The repo-root `conftest.py` fails collection when a test
module that is not marked `live` imports this module, but it cannot see a fixture
defined in another conftest, a function-local import, `importlib.import_module`, or
import-time execution. So `load()` refuses to read `.env` while pytest is running
unless `conftest.py` opened `_LIVE_GATE_ENV`, which it does only when the run's own
`-m` value is exactly `live`.
"""

import os
import sys
from pathlib import Path

# Set by the repo-root conftest.py's `pytest_configure`, only for a `-m live` run.
_LIVE_GATE_ENV = "COOP_LIVE_GATE_OPEN"


def _pytest_is_running() -> bool:
    """True once something has imported `pytest` into this process."""
    return "pytest" in sys.modules


def _env_path() -> Path:
    """The repo-root `.env`, or the file `_COOP_CREDENTIALS_ENV_FILE` points at.

    The override exists so the gate's own pytester tests (`test_live_guard.py`) can
    point `load()` at a throwaway file holding made-up values, never the real `.env`.
    """
    override = os.environ.get("_COOP_CREDENTIALS_ENV_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / ".env"


def load(*names: str) -> dict[str, str]:
    """Return each named variable's value, from the environment or `.env`.

    A value already in the environment wins over `.env`. Raises `RuntimeError` naming
    the missing variables, never their values.
    """
    if _pytest_is_running() and os.environ.get(_LIVE_GATE_ENV) != "1":
        raise RuntimeError(
            "credentials.load() called outside `-m live`: reading .env here under a "
            "bare `pytest` run would risk a real Coop request"
        )
    env_file = _env_path()
    if env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} must be set in .env")
    return {name: os.environ[name] for name in names}
