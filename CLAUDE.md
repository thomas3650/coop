# CLAUDE.md — coop

## What this is

<!-- TODO: one paragraph — what coop is, who uses it, and the boundary that must not
be crossed (an external service, a package split, a privacy scope). -->

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

**Precedence when documents disagree: code > `docs/research/` >
`docs/requirements.md`.** Never resolve a contradiction by picking the
convenient side — say so instead.

## Non-negotiable rules

<!-- TODO: the rules an agent can break without noticing, grouped by risk
(cost, secrets, external systems). Each one cites the requirement it serves. -->

### Secrets

- **Credentials live in `.env`, nowhere else** — never hardcoded, echoed,
  written into a fixture, or put in a commit message. No agent reads `.env`
  directly.

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

<!-- TODO: language, tooling, and the gate commands. The static checks include
`scripts/check_doc_links.py`. -->

## Status

[README § Status](README.md#status) holds it.
