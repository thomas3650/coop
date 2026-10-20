---
name: writing-coop-docs
description: Use when writing or updating any documentation in this repo — a decision row, a dated research finding, a requirement, a domain term, a memory row — and when deciding which doc a new fact belongs in.
---

# Writing coop docs

The job is to keep a fact findable, not to add prose. **The default size of a
change here is one table row.**

## Where a fact goes

| Doc | Holds | Shape |
|---|---|---|
| `docs/decisions.md` | what this project deliberately will **not** build, and why | one row: decision + why, with a link to the spec when a design exists |
| `docs/superpowers/specs/` | the current design and its deferred work, one spec per phase | while a phase is underway, the only edit is its "Not in this phase" list |
| `docs/superpowers/plans/` | the task list a phase was built from | tick checkboxes as tasks land; leave it alone once the phase is merged |
| `docs/requirements.md` | what the owner wants, as user stories | one story, with an `R-<AREA>-<n>` anchor |
| `docs/domain-language.md` | the project's vocabulary | one term + its definition + what it is not |
| `docs/memory.md` | what the owner told us that fits no other doc | one row: item + why; delete the row when it stops being true |
| `docs/research/` | a dated snapshot of something a live request or an experiment showed | a new dated file, plus its row in `docs/research/README.md`; not kept up to date |
| `CLAUDE.md` | the rules an agent must not break | a rule, only when it binds behaviour |

Precedence when documents disagree: **code > `docs/research/` >
`docs/requirements.md`.**

## Rules

- **Never create a new top-level doc.** Ask; the answer is nearly always a row in
  an existing one.
- **Never restate what another doc says.** Link it. A duplicated fact becomes a
  contradiction the first time one copy is corrected.
- Tables and one-line sentences over paragraphs. Cut every sentence that does not
  change what a reader does.
- **State what is true now.** Never narrate the document's own edit history.
  Correct the claim and stop; `git log` holds the rest. A date earns its place
  only when it justifies a constraint that binds today.
- **Never write an absolute you have not walked.** Walk the call graph to the
  leaf, or read the payload in `docs/research/`. If you have not, write the
  narrower thing you established.
- Use the terms in `docs/domain-language.md`.
- Never write a credential, a token, a real name or an email into a doc.
- After editing, run `uv run python scripts/check_doc_links.py` (or `python3`
  without uv); a broken link or anchor fails it.
