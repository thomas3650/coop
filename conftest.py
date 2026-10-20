"""Repo-root conftest: a test that can reach the owner's Coop credentials must be
marked `live`.

`addopts` deselects `live` tests, so the gate keys on that marker, and a test that
forgets it would be deselected by nothing. At the root, not in a nested conftest,
because pytest loads conftests rootdir-down: a nested placement would gate a full
`uv run pytest` but not a run pointed at a sibling test directory.

Keyed on the module that reads `.env` inside the test suite (`tests/credentials.py`),
not on a fixture name. The check runs in `pytest_collection_modifyitems` rather than
in a fixture: a session-scoped fixture's `request.node` is the Session, so the test's
own markers are not visible from there. At collection time both the test module's
namespace and its markers are.
"""

import os
from typing import Any

import pytest

_CREDENTIALS_MODULE = "credentials"

# Read by `credentials.load()`. The collection-time check below sees only a test
# module's own namespace; it cannot see a fixture defined in another conftest, a
# function-local import, `importlib.import_module`, or import-time execution that
# runs before this hook fires. So `load()` also refuses to read `.env` unless this
# flag is open.
_LIVE_GATE_ENV = "COOP_LIVE_GATE_OPEN"


def _reaches_the_credentials_loader(module_dict: dict[str, Any]) -> bool:
    """True if a test module's namespace holds `credentials` itself, or any object
    defined in a module whose last dotted segment is `credentials`.

    `import credentials` binds a module object, which has no `__module__`, so the
    name check catches it. `from credentials import load` binds `load`, so the
    `__module__` check catches it. Matching the last segment keeps the check live if
    the loader moves into a package.
    """
    if _CREDENTIALS_MODULE in module_dict:
        return True
    for value in module_dict.values():
        origin = getattr(value, "__module__", None)
        if isinstance(origin, str) and origin.rsplit(".", 1)[-1] == _CREDENTIALS_MODULE:
            return True
    return False


def _live_requested(markexpr: str) -> bool:
    """True iff this run's own `-m` value is exactly `live`.

    An allowlist: `-m "not slow"` or any other expression stays closed. pytest's `-m`
    is a store option, so a command-line `-m live` replaces `addopts`'s `-m not live`
    and `config.option.markexpr` holds the whole expression.
    """
    return markexpr.strip() == "live"


def pytest_configure(config: pytest.Config) -> None:
    """Open the gate only for a run that asked for `live`, and pop a flag left in the
    environment by an earlier run, so a stray export cannot open it."""
    if _live_requested(config.getoption("markexpr", default="")):
        os.environ[_LIVE_GATE_ENV] = "1"
    else:
        os.environ.pop(_LIVE_GATE_ENV, None)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    offenders = [
        item.nodeid
        for item in items
        if _reaches_the_credentials_loader(getattr(getattr(item, "module", None), "__dict__", {}))
        and item.get_closest_marker("live") is None
    ]
    if offenders:
        raise pytest.UsageError(
            "these tests can reach the owner's Coop credentials but are not marked `live`:\n  "
            + "\n  ".join(offenders)
            + "\n\nMark them @pytest.mark.live; a live test sends real requests to Coop."
        )
