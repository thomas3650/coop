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
