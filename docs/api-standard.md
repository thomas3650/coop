# API documentation standard

How every endpoint entry in `docs/api.md` must look, so it reads as an API spec:
the template, the rules per section, redaction and the checklist. Which doc a fact
belongs in, and the prose rules, are the `writing-coop-docs` skill. The shape is
adapted from the owner's `nota_music_provider` repo, with its loan cost replaced by
this project's three cost answers.

An entry describes the Coop API **as observed** — never the code in this repo that
calls it ([`CLAUDE.md`](../CLAUDE.md), Docs describe behaviour). Every section of
the template is present; write `none` where one does not apply, so an omission is
always visible. Keep each code span on one line.

## Template

````markdown
## METHOD /path

One-line purpose.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` / subscription key / none | reads only / changes the shared list / part of a login / unmeasured | measured 2026-10-21 (app 26.12.0) · or inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | string | yes | the shared list's id |

**200** (real, scrubbed, trimmed):

```jsonc
{ "field": "value" }   // meaning of a non-obvious field
```

**Cost & mutation** — <a id="a-area-n"></a>A-AREA-n: what it costs, what it
changes, and who else calls it on its own (the Coop app, its widget — never this
repo's code) — three separate claims, each **measured** or **inferred**.

**Errors** — endpoint-specific status and body, or `none`.

**Notes** — caveats, extra headers the app sends, open points, or `none`.
````

## Rules per section

| Section | Rule |
|---|---|
| Heading | `METHOD /path`, without the query string; query parameters go in the parameter table. |
| Auth | The credential the request carries, not the login that minted it. |
| Cost | One of **reads only**, **changes the shared list**, **part of a login**, or **unmeasured** — never "free", "safe" or a guess. `part of a login` covers every step of the OIDC login and every token refresh: each one weighs on the account-lock risk ([spec](superpowers/specs/2026-10-20-coop-shopping-list-design.md#anti-goals)). |
| Status | `measured <date> (app <version>)` or `inferred from app 26.12.0`. A fact keeps its own date when a neighbour is remeasured. |
| Parameters | Every path, query and body parameter seen. `Required` is `yes`, `no` (seen sent without it) or `unknown` (the app always sends it). Headers every call carries are stated once at the top of `docs/api.md`, not per entry. |
| Response | **Real captured JSON**, scrubbed, long arrays trimmed to one or two items with the real shape stated. Never written from memory, from the decompiled app or from a fixture; an entry with no capture says `none captured`. |
| Cost & mutation | Carries the `A-<AREA>-<n>` anchor so other docs can cite it. Cost, mutation and who-else-calls are **three separate questions**: a GET is not proof that nothing changed, and a call that reads only can still be part of a pattern that looks unlike the app. |
| Errors | Endpoint-specific statuses and bodies, as the normal session showed them; none is provoked on purpose ([`CLAUDE.md`](../CLAUDE.md), Live requests). |
| Notes | Caveats, extra headers, open points. When an entry answers an item in `docs/api.md`'s **Unknowns**, delete that item. |

The decompiled app is cited as `inferred from app 26.12.0` (or the version read),
never by class or method: the obfuscated names change with every version. The
class names live in that version's `docs/research/` file.

## Status markers

Every claim is one of two, never blurred:

- **measured** — seen on the wire in a capture of the app, with a date and the app
  version (`measured 2026-10-21 (app 26.12.0)`).
- **inferred** — never seen on the wire: read from the decompiled app or reasoned
  from a measured sibling. Name the source (`inferred from app 26.12.0`,
  `inferred from GET /v1/shopping-lists`).

Precedence when sources disagree: **code > `docs/research/` >
`docs/requirements.md`.**

## Redaction

`docs/api.md` is committed. Every capture goes through the project's scrubber
first; then read the result for a secret in a shape it does not mask, and redact
that by hand. Scrub first, then trim.

| What | Becomes |
|---|---|
| Access, refresh and id tokens; the PKCE verifier and the authorization code | `<token>` / `<JWT>` / `<redacted>` |
| The API Management subscription key, the Unleash key and the Bloomreach key | `<redacted>` |
| `app_installation_id` | `<uuid>` |
| Member number, name, email, phone, address | `<redacted>` |
| List and item names, and list and item ids | `<list>` / `<item>` / `<id>` |

No counts of the account's live data (how many items, how many lists) — state the
shape, never the number.

## Checklist

1. Heading is `METHOD /path` with a one-line purpose.
2. The Auth / Cost / Status table is filled; `unmeasured` is allowed.
3. Parameters are listed, or `none`.
4. Response is real, scrubbed, hand-checked and trimmed, with its status — or
   `none captured`.
5. Cost & mutation, Errors and Notes are present (or `none`), with an
   `A-<AREA>-<n>` anchor; who-else-calls names callers outside this repo only.
6. Every claim is marked **measured** or **inferred**; no decompiled class name
   appears.
7. Answered items are removed from **Unknowns**.
8. The secret scan over the API reference prints nothing:
   `grep -nEi 'eyJ[A-Za-z0-9_-]{8,}|[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-|@[a-z0-9.-]+\.[a-z]{2,}'`
