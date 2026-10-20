"""Tests for the repo-root `conftest.py` guard against an unmarked live test.

`credentials.load()` (`tests/credentials.py`) is the only door to the owner's
credentials inside the test suite. The guard in the repo-root `conftest.py`
aborts collection when a test module can reach that loader without carrying
`@pytest.mark.live`; otherwise nothing deselects it, and a bare `uv run pytest`
would send a real Coop request.

Runs the guard inside pytest's own `pytester` fixture: an isolated subprocess
pytest project, so these tests never read the real `.env`. Every case uses
`runpytest_subprocess()`, never the in-process `runpytest()`: once a live test
module exists, a bare `uv run pytest` imports it at collection time (marker
deselection happens after import), which puts the real `credentials` module into
this process's `sys.modules`, and an in-process pytester run would resolve
`credentials` against that cached module instead of the project's own stub.

Four holes are known and not closed by the collection-time check: a fixture that
reaches the loader indirectly, a function-local import, `importlib`, and
import-time execution that runs before collection's marker check.
`credentials.load()` gates itself against those; the last four tests here
exercise that gate with the real `credentials.py`.
"""

import pathlib

import pytest

pytest_plugins = ["pytester"]

# tests/test_live_guard.py -> the repo root is one level up.
_ROOT_CONFTEST = pathlib.Path(__file__).resolve().parents[1] / "conftest.py"
_CREDENTIALS_PATH = pathlib.Path(__file__).resolve().parent / "credentials.py"

# A fixture defined in a conftest, not in the test module: the collection-time
# check never sees it, so only `load()`'s own gate stands between it and `.env`.
_INDIRECT_FIXTURE_CONFTEST = """

import pytest

import credentials


@pytest.fixture
def creds():
    return credentials.load("COOP_SENTINEL_TOKEN")
"""


def _run(pytester: pytest.Pytester, *args: str) -> pytest.RunResult:
    """Run the pytester project in a subprocess without the Home Assistant plugin.

    The plugin autoloads from its entry point, and its autouse async fixture errors
    in a project that does not set `asyncio_mode = "auto"`. These tests exercise the
    guard, not Home Assistant.
    """
    return pytester.runpytest_subprocess("-p", "no:homeassistant", *args)


def test_unmarked_import_credentials_fails_collection(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(_ROOT_CONFTEST.read_text())
    pytester.makepyfile(credentials="")
    pytester.makepyfile(
        test_offender="""
        import credentials


        def test_it():
            pass
        """
    )

    result = _run(pytester)

    assert result.ret != 0
    result.stderr.fnmatch_lines(["*can reach the owner's Coop credentials*"])


def test_marked_import_credentials_collects(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(_ROOT_CONFTEST.read_text())
    pytester.makepyfile(credentials="")
    pytester.makepyfile(
        test_offender="""
        import pytest

        import credentials


        @pytest.mark.live
        def test_it():
            pass
        """
    )

    result = _run(pytester, "-m", "live")

    result.assert_outcomes(passed=1)


def test_unmarked_from_credentials_import_load_fails_collection(
    pytester: pytest.Pytester,
) -> None:
    """`from credentials import load` binds `load`, not `credentials`, in the test
    module's namespace, so a check for the literal name alone misses it."""
    pytester.makeconftest(_ROOT_CONFTEST.read_text())
    pytester.makepyfile(credentials="def load():\n    ...\n")
    pytester.makepyfile(
        test_offender="""
        from credentials import load


        def test_it():
            load()
        """
    )

    result = _run(pytester)

    assert result.ret != 0
    result.stderr.fnmatch_lines(["*can reach the owner's Coop credentials*"])


def test_marked_from_credentials_import_load_collects(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(_ROOT_CONFTEST.read_text())
    pytester.makepyfile(credentials="def load():\n    ...\n")
    pytester.makepyfile(
        test_offender="""
        import pytest

        from credentials import load


        @pytest.mark.live
        def test_it():
            load()
        """
    )

    result = _run(pytester, "-m", "live")

    result.assert_outcomes(passed=1)


def test_indirect_fixture_unmarked_is_blocked_by_loads_own_gate(
    pytester: pytest.Pytester,
) -> None:
    """Nothing here points `load()` at any `.env`: the gate must fire before a file
    is opened. Were the gate gone, `load()` would raise its missing-variable error
    instead, a different message from the one asserted, so a weakened gate turns
    this red rather than passing for the wrong reason."""
    pytester.makeconftest(_ROOT_CONFTEST.read_text() + _INDIRECT_FIXTURE_CONFTEST)
    pytester.makepyfile(credentials=_CREDENTIALS_PATH.read_text())
    pytester.makepyfile(
        test_offender="""
        def test_it(creds):
            pass
        """
    )

    result = _run(pytester)

    assert result.ret != 0
    # Matched against the "E " exception summary line, not the traceback's printed
    # source of `load()`, which shows the raise statement whether or not it ran.
    result.stdout.fnmatch_lines(["*E*RuntimeError: credentials.load() called outside*"])


def test_preexisting_gate_env_var_without_live_is_still_refused(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gate flag left exported by an earlier `-m live` run must not open the door
    for a run that did not itself ask for live. The pytester subprocess inherits
    this process's environment, so setting the flag here reproduces that shape."""
    monkeypatch.setenv("COOP_LIVE_GATE_OPEN", "1")
    pytester.makeconftest(_ROOT_CONFTEST.read_text() + _INDIRECT_FIXTURE_CONFTEST)
    pytester.makepyfile(credentials=_CREDENTIALS_PATH.read_text())
    pytester.makepyfile(
        test_offender="""
        def test_it(creds):
            pass
        """
    )

    result = _run(pytester)

    assert result.ret != 0
    result.stdout.fnmatch_lines(["*E*RuntimeError: credentials.load() called outside*"])


def test_unrelated_marker_expression_does_not_open_the_gate(
    pytester: pytest.Pytester,
) -> None:
    """The gate opens for the exact marker expression `live` only; a run narrowed by
    some other expression stays closed."""
    pytester.makeconftest(_ROOT_CONFTEST.read_text() + _INDIRECT_FIXTURE_CONFTEST)
    pytester.makepyfile(credentials=_CREDENTIALS_PATH.read_text())
    pytester.makepyfile(
        test_offender="""
        def test_it(creds):
            pass
        """
    )

    result = _run(pytester, "-m", "not slow")

    assert result.ret != 0
    result.stdout.fnmatch_lines(["*E*RuntimeError: credentials.load() called outside*"])


def test_indirect_fixture_marked_live_reads_the_pointed_env_file(
    pytester: pytest.Pytester, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The legitimate case under `-m live` is not blocked. `load()` is pointed at a
    throwaway `.env` holding a made-up sentinel, never the owner's real one.

    Any value of the sentinel inherited from the shell (direnv, `uv run --env-file
    .env`) is cleared first, since `load()` lets the environment beat the file. The
    assertion shows only a boolean on failure: comparing the value directly would
    let pytest's assertion rewriting print it.
    """
    monkeypatch.delenv("COOP_SENTINEL_TOKEN", raising=False)
    env_file = tmp_path / "fake.env"
    env_file.write_text("COOP_SENTINEL_TOKEN=sentinel-token\n")
    pytester.makeconftest(_ROOT_CONFTEST.read_text() + _INDIRECT_FIXTURE_CONFTEST)
    pytester.makepyfile(credentials=_CREDENTIALS_PATH.read_text())
    pytester.makepyfile(
        test_offender=f"""
        import os

        import pytest

        os.environ["_COOP_CREDENTIALS_ENV_FILE"] = {str(env_file)!r}


        @pytest.mark.live
        def test_it(creds):
            token_matches = creds == {{"COOP_SENTINEL_TOKEN": "sentinel-token"}}
            assert token_matches, "loaded value did not match the sentinel"
        """
    )

    result = _run(pytester, "-m", "live")

    result.assert_outcomes(passed=1)
    output = result.stdout.str() + result.stderr.str()
    assert "sentinel-token" not in output
