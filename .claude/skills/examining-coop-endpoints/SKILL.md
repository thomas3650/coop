---
name: examining-coop-endpoints
description: Use when you are unsure how a Coop endpoint behaves, what it returns, whether it changes the shared list, or whether it is part of a login — and before anything that would send a request to Coop.
---

# Examining Coop endpoints

The Coop API is undocumented, and this project runs on **the owner's own Coop
login**. The failure that matters most is Coop locking that account
(`docs/requirements.md` R-ACCOUNT-1). Every question here has a cheap answer and
an expensive one. Take the cheap one first.

## Sources, cheapest first

Work down the list. Stop at the first one that answers the question.

| # | Source | Cost | Where |
|---|---|---|---|
| 1 | This project's API reference | nothing | `docs/api.md` — one entry per endpoint, each claim **measured** or **inferred**, and its **Unknowns** |
| 2 | Captured payloads | nothing | `docs/research/` — dated, scrubbed and trimmed; the offline tests replay them |
| 3 | The decompiled app | nothing | the scratch folder the app version's static-read file in `docs/research/` names; never in the repo. What it shows is **inferred**, never measured |
| 4 | The wire | a Coop session on the owner's login | below — **a fresh ask first** |

Precedence when sources disagree: **code > `docs/research/` >
`docs/requirements.md`.**

## The wire

There are two ways onto it, and both need the owner's yes for that one run
(`CLAUDE.md`, Live requests):

- **A capture** of the app used normally, supervised by the owner
  (`docs/reverse-engineering.md`). It records only what the app does: no
  replayed or stale token, no request crafted by hand, no error provoked on
  purpose.
- **A test marked `live`**, run with `uv run pytest -m live`.

Before either:

1. **Read `docs/api.md` and `docs/research/` again.** Most questions are
   answered there.
2. **Ask the owner.** Say what you would send, how many requests, and which of
   them is part of a login.
3. **One Home Assistant holds the Coop login at a time.** The integration on the
   owner's real Home Assistant is stopped first, on the owner's yes
   (`talking-to-home-assistant` skill).

There is no "probe a variation yourself" here. A question the normal session
does not answer stays in **Unknowns**, and the client handles that case
defensively (the spec under `docs/superpowers/specs/`, "Only what the app does").

## What a call costs

`docs/api-standard.md` holds the three answers: **reads only**, **changes the
shared list**, **part of a login** — or **unmeasured**. Cost, mutation and who
else calls it are three separate questions; a GET is not proof that nothing
changed.

Deleting an item is a call this project does not build (`docs/decisions.md`);
complete-all is not among the calls the spec's client makes. Do not send either.

## Recording what you learn

- An endpoint fact goes in `docs/api.md`, in the shape `docs/api-standard.md`
  sets, marked **measured** or **inferred**, citing the decompiled app as
  "inferred from app 26.12.0" (or the version read) — never by class.
- If it took the wire to learn, it also earns a dated file in `docs/research/`
  and a row in that directory's `README.md`.
- Answered items leave **Unknowns**.

## Common mistakes

| Mistake | Instead |
|---|---|
| Going to the wire for something `docs/api.md` or a payload already shows | Sources 1–3 first, every time |
| Writing a decompiled class name into `docs/api.md` | "inferred from app 26.12.0"; the class names live in the research file |
| Calling a decompiled finding measured | Measured means seen on the wire |
| Replaying a token to see whether refresh tokens rotate | The normal session's answer, or it stays in **Unknowns** |
| Logging in while the owner's real Home Assistant has the integration running | Stop it first, on the owner's yes |
| Writing "this endpoint carries no `X`" after reading a trimmed payload | Read the full capture, or write the narrower claim |
