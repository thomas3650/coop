# Coop shopping list in Home Assistant — phase 1 design

## Intent

The owner's family keeps one shared shopping list in the Danish Coop app
("Coop – Scan & Pay, App offers", also called *medlem*, package
`dk.coop.coopplus`). Each family member uses their own Coop login and the list
is shared between them. In the store the owner ticks items off in the app as
they go into the basket; a ticked item moves to **Indkøbte varer**.

The owner wants that list on a Home Assistant dashboard, so anyone at home can
add an item or mark one as shopped without picking up a phone. The app stays
the tool in the store.

There is no public Coop API. This project reverse-engineers the app's own API
and builds two things on it: a Coop API client and a Home Assistant custom
integration that uses it.

Phase 1 is for the owner's own Home Assistant only.

## Goals

The owner decided each of these.

| Goal | Detail |
|---|---|
| One list | HA shows the one shared family list. Any other list on the account is ignored. |
| Read | HA shows the open items and the items in Indkøbte varer. |
| Add | Free text only. Every item HA adds has quantity 1. |
| Mark as shopped | Ticking an item in HA moves it to Indkøbte varer, exactly as ticking in the app does. |
| Put back | Unticking an item in Indkøbte varer puts it back on the list. |
| Never delete | HA never deletes an item, not even one added by mistake, and never clears Indkøbte varer. Marking as shopped is the only way an item leaves the list from HA. |
| Freshness | HA re-reads the list once an hour, and on a refresh button on the dashboard. A refresh button is enough; no re-read on events such as arriving home. |
| Login | The owner's own Coop login. A one-time login in a browser during setup is acceptable. |
| Install | A HACS custom repository on the owner's HA. |
| Repo | One public GitHub repo from the first commit, holding both the client and the integration. The client is bundled inside the integration at release. Renovate keeps dependencies up to date; a release pipeline publishes versions HACS can see. |
| Verification | Each feature is tried in a local Home Assistant through the Chrome browser before it is called done, as in the owner's other two repos. |
| API docs | A `docs/api.md` API reference and a `docs/api-standard.md` entry standard, after the pattern of `nota_music_provider`. |
| Docs describe behaviour | No doc names this repo's code. See [Docs](#docs). |

## Anti-goals

**Coop locking the owner's account** is the failure that matters most. It
ranks above freshness and above every feature. Everything below about login,
polling and live requests follows from it.

Also a failure even if it technically works:

- a token, password, member number, name, address or list content in a commit;
- HA deleting something from the family list;
- a dev Home Assistant and the owner's real one fighting over the same login.

## What the app showed

The source is a static read of the decompiled app, version 26.12.0, pulled
from the owner's phone. Nothing has touched Coop's servers yet, so each point
below is **inferred**, none is measured. The findings go into a dated
`docs/research/` file as the project's first evidence (a phase 1 task).

- **Bootstrap.** The app first fetches a remote configuration from
  `api.coopdk.lobyco.net`. That configuration holds:
  - the OIDC issuer and its endpoints;
  - the client id and redirect URIs;
  - the shopping-list service's base URL, its Azure API Management
    subscription key and its audiences.

  None of these values was found in the app's code.
- **Login.** OIDC authorization code with PKCE, shown in a WebView, with no
  client secret. The paths look like IdentityServer/Duende. Whether the login
  page asks for email and password, MitID or a one-time code is decided on the
  server and was not visible in the code.
- **Tokens.**
  - The app holds one token per scope set. The shopping list uses the scopes
    `shopping-list offline_access`.
  - A refresh is a form post with `grant_type=refresh_token`, `refresh_token`
    and `client_id`.
  - Request signing with a device key was found on payment and subscription
    calls, not on shopping-list calls.
- **Shopping list.** A REST API under `v1/shopping-lists`:
  - list the lists, list a list's items;
  - add items (bulk);
  - edit an item, set its amount;
  - complete, uncomplete, complete-all;
  - delete an item.

  An item carries a `state` of `Normal` or `Completed`. Indkøbte varer is
  inferred to be the items in state `Completed`, not a separate list.
- **Sync.** No realtime channel was found; the app's widget polls.
- **Network security.** None found in the decompiled 26.12.0 code:
  - no certificate pinning;
  - no custom trust manager;
  - no network security config;
  - no Play Integrity, SafetyNet or attestation call;
  - no root or emulator check that blocks the app.

  That is what a static read found, not a walked fact. The capture confirms or
  refutes it.

## Phase 1, in order

### 1. Repo foundation

- **Docs and skills.** Fill the empty docs and skills. See [Docs](#docs).
- **Tooling.** A uv workspace with two members, the client package and the
  integration. Ruff, mypy strict on the client, pytest with the live marker
  deselected by default (`CLAUDE.md`, Tests).
- **CI.** Offline only: static checks and the suite, on every pull request.
- **CI checks**, after the pattern of the owner's `HA-NortecGo` repo:
  - lint and tests;
  - `hassfest` and HACS validation;
  - a secret scan (gitleaks).
- **Renovate.** Configuration for Python dependencies and GitHub Actions.
- **Release pipeline**, the owner's decision: a release is a workflow that runs
  after a merge to `main`, never a hand-pushed tag. The pattern is
  `HA-NortecGo`'s auto-release and version-check workflows, and its
  `docs/releasing.md`.
  - **PR titles.** Every PR title is `type(scope)!: text`, checked on every PR.
    - `fix` and `perf` release a patch.
    - `feat` releases a minor version.
    - `docs`, `chore`, `ci`, `test` and `refactor` release nothing.
  - **On release.** When the checks on `main` pass after a releasing merge,
    the workflow:
    1. copies the client into the integration folder;
    2. tags the version;
    3. publishes a GitHub release with the integration zip HACS installs.
  - **How the version is bumped** is the builder's to settle. `HA-NortecGo`
    bumps it on the PR branch; a bump decided after the merge is equally
    acceptable.
  - **Autonomy.** No release needs a separate ask: merging a releasing PR is
    what releases it. The agent merges when ready, as the owner set out.
- **GitHub.** The repo itself, secret scanning and push protection. Creating
  the public GitHub repo is outward-facing, so it waits for the owner's yes
  after this spec is approved. The plan's tasks are then filed as GitHub issues
  on it, which the owner asked for.

### 2. The capture — the go/no-go gate

Nothing that logs in to Coop is built before the capture has answered the
questions below.

**Rig** (the builder's call, recommended):

- A new Android 14 emulator named `coop`, from the same `google_apis`
  arm64 image as the existing `nortec` emulator. The `nortec` emulator stays
  untouched.
- The four APK files pulled from the owner's phone, installed with
  `adb install-multiple`. Their version and SHA-256 are recorded in the
  research file.
- The mitmproxy CA mounted as a system certificate.
- `mitmdump` in WireGuard mode writing to a git-ignored `.captures/`.
- The nortecgo and nota `docs/reverse-engineering.md` files hold the recipe.
  The coop version records only what differs.
- Frida is added only if the capture comes back blank.

**Known trap.** In nota, the certificate mount broke the Chrome renderer the
login page ran in. Coop's login also runs in a web view. If it renders blank,
log in with the mount off, then mount it and relaunch the app on its stored
login.

**The session is supervised.**

- The owner types their Coop login on the emulator; nothing automates it.
- The capture tests with one item of the owner's own, added, completed and
  uncompleted, nothing else.
- Afterwards the owner checks whether their phone is still logged in.

**Only what the app does**, the owner's decision. The capture records the app
being used normally and nothing more:

- no replayed or stale token;
- no request crafted by hand;
- no error provoked on purpose.

A question the normal session does not answer stays open in `docs/api.md`'s
**Unknowns**. The client then handles that case defensively:

- every refresh token is treated as use-once, and the new one is stored
  before the next request;
- an unrecognised error is treated as a temporary failure, never as a reason
  to log in again.

**It must answer:**

| Question | Why it matters |
|---|---|
| What the login page asks for: email and password, MitID, or a code | Decides what the HA setup screen asks for |
| Which redirect URI the configuration actually serves, and whether it is a custom scheme (the manifest declares `coop-member` and `coop-member-app`) | Decides whether "log in in a browser, copy the address back" works from a desktop browser |
| Whether one refresh token covers the `shopping-list` scope, or that scope needs its own authorization | Decides the token handling in the client |
| Whether refresh tokens rotate, as the normal session shows it (what a reused old one does is not tested) | A server in the IdentityServer style may revoke the whole token family on reuse, which is a lock risk |
| Whether a second session logs the phone out | If it does, HA moves to a separate Coop account invited to the shared list |
| The real shape of the list and item payloads, the add, complete and uncomplete requests, and the errors | The client is written against measured payloads, not guesses |

Every answer goes into `docs/api.md` as a measured entry, plus a dated
research file with scrubbed, trimmed payloads, which the offline tests replay.
**When the work stops for the owner.** The phase stops and the owner decides
if the capture shows:

- the login needs the phone;
- a second session logs the phone out (the fallback, a separate Coop account,
  is one the owner would have to create);
- any other answer that breaks the plan.

**Two plans** (the builder's call):

- **Plan 1, written now:** the repo foundation and the capture.
- **Plan 2, written after the capture:** the client, the integration and the
  local checks.

Nothing is built on payloads that were only inferred. Plan 1's tasks are filed
as issues once the repo exists; plan 2's are filed when that plan is written.

### 3. The Coop client

An async Python library that speaks Coop's API and nothing else. It:

- fetches the remote configuration first, and takes the base URL,
  subscription key, audiences and OIDC endpoints from it;
- builds the authorization URL for the one-time login, with PKCE, and
  exchanges the code;
- refreshes the access token and reports every rotated refresh token to its
  caller at once, so the caller can store it before using it;
- reads the lists and the chosen list's items;
- adds a free-text item with quantity 1, completes an item, uncompletes an
  item.

It has no call that deletes an item or clears a list.

Its errors tell the caller three things apart:

- a refused refresh, after which the owner must log in again;
- a temporary failure, after which the caller backs off;
- a list or item that no longer exists.

**Looking like the app** (the builder's call):

- It fetches the remote configuration once when it starts, as the app does at
  launch, not before every request.
- It sends the headers the capture shows the app sending.
- Where the app sends an installation id, the client uses one of its own,
  generated once and stored. It never uses the phone's.

Tested offline against a fake that serves the captured payloads.

### 4. The Home Assistant integration

**Setup.**

- A config flow shows the authorization link. The owner logs in in their
  browser and pastes the address the browser ends on.
- The exact mechanism depends on the capture's redirect-URI answer; that is
  the builder's to settle then.
- The refresh token is stored in the config entry. A rotated one is written
  back at once.

**Which list** (the builder's call):

- If the account has one list, setup uses it.
- If it has several, setup asks the owner to pick one.
- The list's id is stored in the config entry.
- If that list later disappears, HA raises a repair issue. It never picks
  another list on its own.

**Entities.**

- **A to-do entity for the shared list.**
  - It advertises create and update support, and **not** delete support. HA
    then never offers "remove completed items", and the integration has no
    path to the delete endpoint.
  - An open item is `needs_action`; an item in Indkøbte varer is `completed`.
  - Setting `completed` calls complete; setting it back calls uncomplete.
  - A new item is created with its summary as the name and quantity 1.
  - **Rename** (the builder's call): renaming an item is not in this phase.
    The integration refuses it with an HA error rather than silently ignoring
    it.
  - **Quantity** (the builder's call): an item whose quantity is above 1 shows
    it read-only in the item's description, as `Antal: N`.
- **A refresh button entity.** HA's to-do card has no refresh control of its
  own. Pressing the button re-reads the list straight away.

**Polling.**

- A data coordinator re-reads the list once an hour.
- **The interval is a setting** in the integration's options (the builder's
  call).
- After each write HA makes, it re-reads the list (the builder's call), so
  the card is right at once.

**Gentle by construction:**

- **One login only.** HA logs in once in the setup flow. After that, only
  refreshes.
- **A refused refresh stops it.** HA stops and raises HA's re-authenticate
  flow. It never retries a login on its own.
- **Back off.** On a temporary failure or rate limiting, the next attempt
  waits longer each time instead of hammering.
- **No extra calls.** No request the app does not make.

**HTTP** (the builder's call): through HA's shared aiohttp session, so the
integration adds no HTTP library of its own.

### 5. Local Home Assistant and Chrome checks

**Dev HA.**

- A dev Home Assistant Core runs on the Mac from its own Python environment,
  at `http://localhost:8123`. Docker is not installed, and nota runs its dev
  Music Assistant the same way.
- Its config folder is git-ignored inside the repo.
- A script links the integration, with the client, into its
  `custom_components`.

**Chrome check.**

- When a feature is built, an agent opens the dev HA in Chrome through the
  Chrome tools and does it:
  - adds the integration;
  - opens the list card;
  - adds an item, ticks it, unticks it;
  - presses refresh.
- The result is written up as a dated research file.
- A feature is not called done before that has happened.

**Which Coop the dev HA talks to** (the builder's call):

- Because the client takes its base URL from the remote configuration, the
  dev HA can be pointed at a local fake that replays the scrubbed captures.
  Routine Chrome checks run against that fake.
- A dev HA run against the real Coop is reserved for milestones, each one
  asked for first.
- **One Home Assistant holds the Coop login at a time.** The dev HA logs in to
  the real Coop only while the owner's real HA does not have the integration
  running, and only after the owner says yes.

**The owner's real HA** is touched only through the Home Assistant MCP tools:

- reads are free;
- each change is asked for, one at a time.

The owner's real dashboard is not edited from this repo; adding the card to it
is the owner's.

## Docs

The rule the owner set: **docs describe how things behave, never this repo's
code.**

**What no doc may carry:**

- names of this repo's packages, modules, functions or classes;
- source paths;
- pasted code.

That lives in the code and its docstrings.

**Allowed exceptions:**

- **README commands**, which a person types.
- **`docs/superpowers/`**, whose specs and plans are dated records that name
  files.
- **Research files** may name the decompiled app's classes. A research file is
  a dated snapshot.

`docs/api.md` cites the decompiled app as "inferred from app 26.12.0", never
by class, because the obfuscated names change every version.

**Enforcement.** A test fails when a doc outside `docs/superpowers/` and
`docs/research/` names the repo's package or module names or a source path.
`CLAUDE.md` and the `writing-coop-docs` skill state the rule.

**To fill in phase 1:**

| Where | What |
|---|---|
| `CLAUDE.md` | "What this is"; Commands; the docs-describe-behaviour rule; the live-request and one-login rules from this spec; two rows for the API docs in "Where the facts live" |
| `README.md` | What it is, status, setup, commands, and what each runnable script costs |
| `docs/requirements.md` | Personas (the account holder, a family member at home); one story per goal above |
| `docs/domain-language.md` | `indkøbsliste` / the shared list; Indkøbte varer; mark as shopped, which the API calls complete; put back, which is uncomplete; refresh token; one-time browser login |
| `docs/decisions.md` | HA never deletes; no product search, quantity editing or multiple lists in phase 1; one repo, not a public/private split; no HACS default listing |
| `docs/memory.md` | The owner's way of working: they approve the spec; the agent asks before the plan is approved; the agent merges when ready; implementation goes to subagents by default and small tasks are done natively |
| `docs/api-standard.md` | nota's standard adapted: the loan cost becomes **reads only** / **changes the shared list** / **part of a login**, and those three questions stay separate; measured and inferred markers; `A-<AREA>-<n>` anchors; redaction; checklist |
| `docs/api.md` | The Coop API reference: seeded from the static read with every entry inferred, plus an **Unknowns** list; the capture turns entries measured |
| `docs/research/` | The static read of app 26.12.0; the capture; each Chrome check |
| `docs/reverse-engineering.md` | The rig's differences from nortecgo and nota |
| `.claude/skills/` | `examining-coop-endpoints`: which source to check, cheapest first, and ask before any live request. `talking-to-home-assistant`: the real HA is reached through MCP only, read freely, and each change asked for |
| `.claude/agents/` | Fill each TODO row from the rules above |

## Secrets and redaction

- Credentials and tokens live in `.env` and in HA's config entry, nowhere else
  (`CLAUDE.md`, Secrets).
- **Scrubbing.** Every capture goes through a scrubber before anything
  derived from it is committed. The scrubber masks:
  - access, refresh and id tokens; the PKCE verifier and code;
  - the APIM subscription key, and the Unleash and Bloomreach keys;
  - `app_installation_id`;
  - member number, name, email, phone, address;
  - list and item names and ids.
- **Never in the repo:**
  - `.captures/`;
  - the APK files;
  - the decompiled source, which stays in a scratch folder;
  - the dev HA's config folder.
- `.gitignore` covers each of these before the first capture is written.

## Not in this phase

- Product search when adding an item
- Editing an item's quantity, or renaming an item
- Deleting items or clearing Indkøbte varer
- More than one list
- Listing in HACS's default store, or support for other Coop members
- Adding the card to the owner's real dashboard (the owner does it)
- Re-reading the list on events other than the refresh button and the hourly
  poll
