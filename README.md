# coop

A Home Assistant custom integration that puts the shared family shopping list from
the Danish Coop app on a Home Assistant dashboard: anyone at home can see it, add an
item, and mark one as shopped without picking up a phone. There is no public Coop
API, so this repo also holds a Coop API client built on the app's own API, as the
app is seen to use it. For the owner's own Home Assistant, with the owner's own
Coop login; not for other Coop members ([decisions](docs/decisions.md)).

What it is for: [requirements](docs/requirements.md). The design:
`docs/superpowers/specs/`. The rules every change follows: [`CLAUDE.md`](CLAUDE.md).

## Status

Phase 1, plan 1 (the repo foundation and the capture) is under way. Nothing that
talks to Coop exists yet.

## Setup

Python at the floor `pyproject.toml` sets, and `uv`:

```bash
uv sync
```

Where credentials live: [`CLAUDE.md`](CLAUDE.md), Secrets. `.gitignore` covers
`.env`.

## Commands

The gates. None sends a request to Coop: the suite deselects tests marked `live`.

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv run python scripts/check_doc_links.py
```

| Runnable | What it costs |
|---|---|
| `uv run pytest -m live` | Real requests to Coop with the owner's login. **Ask the owner first, every time.** No test is marked `live` yet. |
| The doc link check (the last gate above) | Reads the repo's Markdown files; no network request. |

The bump step for a releasing PR ([releasing](docs/releasing.md)), with the PR's title in single
quotes, and the release zip as the release workflow builds it:

```bash
uv run python scripts/release_check.py release-pr --title='fix: …'
uv run python scripts/build_zip.py /tmp/coop_dk.zip
```

| Runnable | What it costs |
|---|---|
| The bump step | Fetches `main` from GitHub; edits the manifest's version and the changelog, and commits nothing. |
| The zip build | Writes one zip file; no network request. |

A recorded capture, as one file per request through [the scrubber](docs/domain-language.md#dl-scrubber), in an environment of its own:

```bash
uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows.py <flows> <out_dir>
uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows_selfcheck.py
```

| Runnable | What it costs |
|---|---|
| The flow export | Reads one capture file and writes into the folder it is given; no request to Coop. uv fetches mitmproxy from PyPI when its cache lacks it. The output is still read by hand before anything from it is committed. |
| The export self-check | Writes a made-up capture into a temporary folder, exports it and fails if a planted secret survives; no request to Coop. |

The dev Home Assistant at `http://localhost:8123`, with the integration linked from the working
tree; its config folder is gitignored:

```bash
scripts/develop
```

| Runnable | What it costs |
|---|---|
| The dev Home Assistant | No request to Coop until the integration is set up and can log in; that needs the owner's yes, and the owner's real Home Assistant must not hold the Coop login at the same time. |
