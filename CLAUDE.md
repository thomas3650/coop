# CLAUDE.md — coop

## What this is

A Home Assistant custom integration that shows the owner's shared family
shopping list from the Danish Coop app, built on a Coop API client reverse-engineered
from the app; both live in this one repo. It runs on the owner's own Home Assistant
with the owner's own Coop login. The failure that matters most is **Coop locking
the owner's account**; it ranks above every feature
([spec](docs/superpowers/specs/2026-10-20-coop-shopping-list-design.md#anti-goals)).

## Where the facts live

Read the doc, don't re-derive the fact. Nothing here is restated elsewhere in
this file — one copy of a fact, so a correction lands once.

| Doc | Holds | Cite it as |
|---|---|---|
| `docs/requirements.md` | the target state, as user stories | `R-<AREA>-<n>` |
| `docs/domain-language.md` | the project's vocabulary, and the confusions it guards | the term |
| `docs/superpowers/specs/` | the current design and its deferred work, one spec per phase | the directory and its date |
| `docs/superpowers/plans/` | the task list a phase was built from; a dated record | the directory and its date |
| `docs/decisions.md` | what this project deliberately will not build, and why | the row |
| `docs/research/` | dated snapshots of what a live request or an experiment showed | the file |
| `docs/memory.md` | what the owner has told us that fits no other doc — preferences, standing context | the row |
| `README.md` | status, setup, the commands, and what each runnable script costs | the section |
| `docs/api.md` | the Coop API as observed, one entry per endpoint, and its **Unknowns** | `A-<AREA>-<n>` |
| `docs/api-standard.md` | the shape every `docs/api.md` entry takes, redaction and the checklist | the section |
| `docs/reverse-engineering.md` | how the capture rig differs from the owner's other two repos' | the section |
| `docs/releasing.md` | how a merge releases, and what differs from HA-NortecGo's release rules | the section |

**Precedence when documents disagree: code > `docs/research/` >
`docs/requirements.md`.** Never resolve a contradiction by picking the
convenient side — say so instead.

## Non-negotiable rules

### Secrets

- **Credentials live in `.env`, nowhere else** — never hardcoded, echoed,
  written into a fixture, or put in a commit message. No agent reads `.env`
  directly ([R-ACCOUNT-3](docs/requirements.md#r-account-3)).
- *Scope:* this binds the repo tree. At runtime the integration keeps its
  refresh token in Home Assistant's config entry on the owner's Home Assistant;
  that is not a breach.

### Live requests

They serve [R-ACCOUNT-1](docs/requirements.md#r-account-1) and
[R-ACCOUNT-2](docs/requirements.md#r-account-2). "Coop" here means every host
the Coop app talks to, the remote configuration host included.

- **No request to Coop without a fresh ask** of the owner. The routes to Coop
  are a capture, a `-m live` run, and a dev Home Assistant pointed at the real
  Coop. A yes covers that one run. A step in a plan or an issue is not a yes.
- **One Coop session at a time.** Before a capture, a `-m live` run or a dev
  Home Assistant on the real Coop, the integration on the owner's real Home
  Assistant is stopped if it is running — on the owner's yes — and only one of
  them runs at a time.
- **The capture records only what the app does**: the app used normally, and
  nothing more —
  - no replayed or stale token;
  - no request crafted by hand;
  - no error provoked on purpose.

  A question that leaves open stays in `docs/api.md`'s **Unknowns**. The rig is
  [`docs/reverse-engineering.md`](docs/reverse-engineering.md).

### Docs describe behaviour

- **No doc names this repo's code** — no package, module, function or class
  name, no source path, no pasted code. That lives in the code and its
  docstrings. The exceptions are README commands in fenced blocks,
  `docs/superpowers/` and `docs/research/`
  ([spec](docs/superpowers/specs/2026-10-20-coop-shopping-list-design.md#docs)).
  `tests/test_docs_name_no_code.py` enforces it over `docs/` and `README.md`;
  `CLAUDE.md` and `.claude/` may name scripts
  ([R-REPO-4](docs/requirements.md#r-repo-4)).

## How to work here

### Per-phase workflow

1. **Brainstorm** (`superpowers:brainstorming`) — interrogate scope before a
   plan exists.
2. **Write the plan** (`superpowers:writing-plans`) — decompose into tasks.
3. **Implement test-first** (`superpowers:test-driven-development`) — a failing
   test before the implementation code, for every feature and every bugfix. No
   production code without a red test.
4. **Tick the plan's checkboxes and commit the plan as each task lands** —
   only steps that were actually performed; a verification nobody ran stays
   unticked. Update the current spec's "Not in this phase" list the same way.

### Keeping state

- **Do not use Claude's auto-memory directory.** Anything that must outlive a
  session belongs in this repo: a rule in `CLAUDE.md`, a skill or an agent file, a
  fact in `docs/`, or code — and what fits none of those, a row in
  `docs/memory.md`. An auto-memory file is invisible to the owner and to every
  other agent.
- **Keep a progress file on disk during long work**, with a "RESUME HERE" section
  updated after every step — for a plan, the ledger under `.superpowers/sdd/`.
  Sessions crash and compact; the file and `git log` are what survive.

### Subagents

`.claude/agents/` holds two: **`coop-implementer`** (one scoped task,
test-first) and **`coop-reviewer`** (read-only, findings only). Each carries
this project's rules; a `general-purpose` agent does not.

Documentation is a **skill**, not an agent: invoke `writing-coop-docs` before
editing any doc in this tree. A skill reaches inside a dispatched agent, which is
where most doc edits actually happen.

So when a superpowers template says `Subagent (general-purpose)` — the
implementer, task-reviewer and re-review prompts of
`superpowers:subagent-driven-development` — dispatch the matching agent from
`.claude/agents/` instead, keeping the skill's task brief and review-package
structure. Do not pass a `model` override: each agent pins its own, and an
override silently replaces it.

### Tests

<!-- TODO: how the suite runs, what is mocked, and which test matters most. -->

The suite is **offline**. A test that reaches a real external service is marked
and deselected by default, and never part of a bulk run.

### Domain language

Read `docs/domain-language.md` before naming anything, and use its terms in
code, tests, docstrings and commit messages. A new domain concept gets a row
there — a concept that lives only in code is how the two vocabularies drift apart.

### Comments, docstrings and doc prose

Applies to every word this project writes about itself — comments and
docstrings, commit messages, and the Markdown in `CLAUDE.md`, `README.md` and
`docs/`.

- **State what is true now.** Never narrate a document's own edit history: no
  "this used to say X", no "corrected 2026-09-11", no struck-through sentence
  kept to show what it replaced. `git log` holds that. A date earns its place
  only when it justifies a constraint that binds today.
- **Never restate what another doc says.** Link it. A duplicated fact becomes a
  contradiction the first time one copy is corrected.
- **Never write an absolute you have not walked.** "makes no request", "never
  calls", "carries no `X`" are claims about code and about captured bytes. There
  are exactly two instruments: **walk the call graph** to the leaf that would act,
  or **read the captured payload** in `docs/research/`. A neighbouring docstring
  is not evidence, a trimmed fixture is not evidence, and a green suite is not
  evidence. If you have not walked it, write the narrower thing you established.

## Commands

The gates, all of which must pass before a push. The suite deselects tests
marked `live` (Tests, above):

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv run python scripts/check_doc_links.py
```

`uv run pytest -m live` runs the tests that reach the real Coop with the
owner's credentials: a fresh ask first, every time (Live requests, above).

## Status

[README § Status](README.md#status) holds it.
