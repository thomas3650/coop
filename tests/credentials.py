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


def _parse(text: str) -> dict[str, str]:
    """`KEY=value` lines, skipping blank and `#` lines. Strips a leading `export ` and
    one pair of matching surrounding quotes from the value."""
    parsed: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        parsed[key] = value
    return parsed


def load(*names: str) -> dict[str, str]:
    """Return each named variable's value, from the environment or else `.env`.

    A value already in the environment wins over `.env`. Leaves `os.environ`
    unchanged. Raises `RuntimeError` naming the missing variables, never their values.
    """
    if _pytest_is_running() and os.environ.get(_LIVE_GATE_ENV) != "1":
        raise RuntimeError(
            "credentials.load() called outside `-m live`: reading .env here under a "
            "bare `pytest` run would risk a real Coop request"
        )
    env_file = _env_path()
    from_file = _parse(env_file.read_text()) if env_file.exists() else {}
    loaded = {name: os.environ.get(name) or from_file.get(name, "") for name in names}
    missing = [name for name, value in loaded.items() if not value]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} must be set in .env")
    return loaded
