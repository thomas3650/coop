# Plan 1 — Repo foundation and the capture: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Dispatch `coop-implementer` / `coop-reviewer` from `.claude/agents/`, never `general-purpose` (`CLAUDE.md`, Subagents).

**Goal:** A public repo with working CI, Renovate and an auto-release pipeline, the project docs and skills filled in, a capture scrubber, and a supervised capture of the Coop app that answers the spec's go/no-go questions.

**Architecture:**
- **Layout.** A uv workspace with the client at `packages/coop-client/src/coop_client/`. The HACS integration lives at `custom_components/coop_dk/` in the repo root.
- **How the integration gets the client.** A committed relative symlink, `custom_components/coop_dk/coop_client`, points at the client package. Integration code imports it relatively, as `from .coop_client import …`.
  - In development and tests, the symlink resolves to the package.
  - At release, the workflow zips the integration with symlinks dereferenced, so HACS installs a self-contained folder.
- **Releases.** They follow `HA-NortecGo`: PR-title-driven, and published after a merge to `main` once the checks pass.

**Tech Stack:** Python 3.14, uv, ruff, mypy (strict), pytest + pytest-asyncio, pytest-homeassistant-custom-component, GitHub Actions, Renovate, mitmproxy, Android emulator + adb, jadx.

**Spec:** [`docs/superpowers/specs/2026-10-20-coop-shopping-list-design.md`](../specs/2026-10-20-coop-shopping-list-design.md)

**Reference repos on disk:**
- `~/Documents/Sourcecode/HA-NortecGo`: CI, release, Renovate, dev HA script.
- `~/Documents/Sourcecode/nota_music_provider`: uv workspace, live guard, the api docs, skills.
- `~/Documents/Sourcecode/nortecgo`: the reverse-engineering rig and its `tools/`.

Read from these repos; never copy a value specific to them (domain, ids, version pins) without checking it.

## Global Constraints

- **Coop locking the owner's account is the failure that matters most.** It ranks above every feature.
- **No live Coop request in this plan except Task 9's supervised capture.** That capture records the app used normally: no replayed or stale token, no hand-crafted request, no error provoked on purpose.
- **Never committed:** a token, password, member number, name, email, phone, address, or list or item content. Credentials live in `.env` only (`CLAUDE.md`, Secrets).
- **Never in the repo:**
  - `.captures/`;
  - any `*.apk` or `*.xapk`;
  - the decompiled source;
  - the dev HA's `config/`.
- **Docs describe behaviour.** No doc outside `docs/superpowers/` and `docs/research/` names this repo's packages, modules, functions, classes or source paths. README commands are the exception.
- **Names.**
  - Integration domain: `coop_dk`, display name `Coop`.
  - Client distribution `coop-client`, import name `coop_client`.
  - `codeowners`: `["@thomas3650"]`.
  - `iot_class`: `cloud_polling`.
  - Python `>=3.14`.
  - License: Apache-2.0, as in `HA-NortecGo`.
- **Commits** use the GitHub noreply address (set in local git config). End each one with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Git flow.** Each task is done on a branch and opened as a PR. The PR title is `type(scope): text`; this plan's PRs are `chore`, `ci`, `docs` or `test` and release nothing. The agent merges when the checks are green.
- **Before editing any doc**, invoke `writing-coop-docs`.
- **Progress ledger.** `.superpowers/sdd/plan-1-ledger.md` has a "RESUME HERE" section, updated after every task.

## Review Focus

1. **A capture artefact leaking through the scrubber.** A token or key shape the scrubber does not list must still be masked. Task 7 pins this with the generic long-token rule and a test, `test_unknown_long_token_is_masked`.
2. **A dev `config/`, APK or `.captures/` file staged by accident.** Task 1 pins `test_gitignore_covers_private_paths`, which runs `git check-ignore` on each path.
3. **The release zip shipping a dangling symlink instead of the client.** Task 5 pins `test_release_zip_contains_client_source`, which builds the zip and asserts that `coop_dk/coop_client/__init__.py` is a regular file.
4. **A PR title that releases by mistake, or a releasing title that does not.** Task 5's `release_check` tests cover each type in the table, including `!` on a non-releasing type.
5. **A doc naming code after a rename.** Task 2's `test_docs_name_no_code` derives the forbidden names from the actual package and module tree, not from a fixed list.

---

### Task 0: Unblock the first push

GitHub refused the first push for email privacy: the local commits carry the owner's personal address. Local config now uses the noreply address. The permission guard refused re-authoring the existing commits in place.

The fix leaves the existing commits as they are:

1. Make a new orphan branch `publish`, holding the current tree as one commit authored with the noreply address.
2. Push it as `main`.
3. The old local `main` stays, renamed `local-history`.

- [x] **Step 1:** Run:
  ```
  git branch -m main local-history
  git checkout --orphan main
  git commit
  git push -u origin main
  ```
- [x] **Step 2:** Check that `git log --format='%ae' origin/main | sort -u` prints only the noreply address.

### Task 1: Workspace, tooling and the live guard

**Files:**
- Create:
  - `pyproject.toml`;
  - `packages/coop-client/pyproject.toml`, `packages/coop-client/src/coop_client/__init__.py`, `packages/coop-client/src/coop_client/py.typed`;
  - `conftest.py`;
  - `tests/test_repo_hygiene.py`;
  - `LICENSE`;
  - `.python-version` (`3.14`).
- Modify: `.gitignore`

**Interfaces:**
- Produces:
  - **pytest config.** `-m "not live"` is in `addopts`, with `--strict-markers`. The `live` marker is defined. `asyncio_mode = "auto"`. `testpaths = ["tests", "packages/coop-client/tests"]`.
  - **The live guard.** The root `conftest.py` fails collection if a test module that is not marked `live` imports `tests/credentials.py`, the same as nota's guard.

- [x] **Step 1: Write the failing test** `tests/test_repo_hygiene.py::test_gitignore_covers_private_paths`. It is parametrised over `.env`, `.captures/x.flows`, `config/configuration.yaml`, `base.apk`, `x.xapk` and `decompiled/x.java`, and asserts that `git check-ignore -q <path>` exits 0 for each.
- [x] **Step 2:** Run `uv run pytest tests/test_repo_hygiene.py -v`. Expected: FAIL on `.captures/x.flows`, `config/…`, `*.apk`, `*.xapk` and `decompiled/…`.
- [x] **Step 3:** Add `.captures/`, `/config/`, `*.apk`, `*.xapk` and `decompiled/` to `.gitignore`. Write the root `pyproject.toml`:
  - a uv workspace with `packages/coop-client`;
  - a dev group with `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-homeassistant-custom-component` (latest), `actionlint-py`, `zizmor` and `coop-client` (workspace);
  - a `capture` group with `mitmproxy`;
  - ruff with line-length 100;
  - mypy strict over `packages/coop-client/src`, `custom_components` and `scripts`.

  Then `uv sync`.
- [x] **Step 4:** Run `uv run pytest -v`. Expected: PASS. Then run `uv run ruff check && uv run ruff format --check && uv run mypy`. Expected: clean.
- [x] **Step 5:** Port nota's live guard and its pytester test into `conftest.py` and `tests/test_live_guard.py`. See it go red with the guard removed, then restore it.
- [x] **Step 6:** Commit on branch `chore/workspace`. Open a PR titled `chore: uv workspace, tooling and the live guard`.

### Task 2: The docs-describe-behaviour test and the doc gates

**Files:**
- Create: `tests/test_docs_name_no_code.py`
- Modify: `scripts/check_doc_links.py`, only if the test needs a shared helper.

**Interfaces:**
- Consumes: the package tree from Task 1.
- Produces: `uv run pytest tests/test_docs_name_no_code.py` and `uv run python scripts/check_doc_links.py`, both as CI gates (Task 4).

- [x] **Step 1: Write the failing tests.**
  - `test_docs_name_no_code`: walks every tracked `.md` file except those under `docs/superpowers/` and `docs/research/`. Builds the forbidden set from the repo itself:
    - the names `coop_client` and `coop_dk`;
    - every module stem under `packages/coop-client/src/coop_client/` and `custom_components/coop_dk/` (excluding `__init__`);
    - any path starting `packages/`, `custom_components/` or `scripts/`.

    Fails, naming the file and line, when one appears. Text inside fenced code blocks in `README.md` is allowed.
  - `test_docs_name_no_code_catches_a_module_name`: writes a temp doc containing `coop_client` and asserts the checker reports it.
- [x] **Step 2:** Run it. Expected: the second test FAILS, because no checker function exists yet.
- [x] **Step 3:** Implement `find_code_names(root: Path) -> list[tuple[Path, int, str]]` inside the test module, with the test asserting the list is empty.
- [x] **Step 4:** Run `uv run pytest tests/test_docs_name_no_code.py -v`. Expected: PASS.
- [x] **Step 5:** Commit and open a PR titled `test: docs name no code`.

### Task 3: Fill the docs, the skills and the agents

Invoke `writing-coop-docs` first. Content comes from the spec's [Docs](../specs/2026-10-20-coop-shopping-list-design.md#docs) table; this task does not restate it.

**Files:**
- Modify:
  - `CLAUDE.md`, filling "What this is" and Commands, and adding these rules:
    - docs describe behaviour;
    - no live Coop request without a fresh ask;
    - one Home Assistant holds the Coop login at a time;
    - the capture records only what the app does.

    Also add rows for `docs/api.md`, `docs/api-standard.md` and `docs/reverse-engineering.md` to "Where the facts live".
  - `README.md`, `docs/requirements.md`, `docs/domain-language.md`, `docs/decisions.md`, `docs/memory.md`;
  - `.claude/agents/coop-implementer.md`, filling the invariants rows and the gate commands;
  - `.claude/agents/coop-reviewer.md`, putting "a change that raises the account-lock risk" first;
  - `.claude/skills/writing-coop-docs/SKILL.md`, adding rows for the three new docs.
- Create:
  - `docs/api-standard.md`, adapted from nota's. The cost line is `reads only` / `changes the shared list` / `part of a login`. It keeps the measured/inferred markers, `A-<AREA>-<n>` anchors, the redaction list from the spec's "Secrets and redaction" section, and a secret-scan checklist line.
  - `docs/reverse-engineering.md`: only the deltas from nortecgo's and nota's recipe, plus the "only what the app does" rule.
  - `.claude/skills/examining-coop-endpoints/SKILL.md`: the sources to check, cheapest first: `docs/api.md`, `docs/research/` payloads, the decompiled app, then the wire. The wire needs a fresh ask.
  - `.claude/skills/talking-to-home-assistant/SKILL.md`: adapted from nota's. Real HA through `mcp__home-assistant__*` only; reads are free; each change is asked for; the dashboard is not this repo's; one HA holds the Coop login.

- [x] **Step 1:** Write the docs.
- [x] **Step 2:** Run `uv run python scripts/check_doc_links.py` and `uv run pytest tests/test_docs_name_no_code.py`. Expected: 0 broken links; PASS.
- [ ] **Step 3:** Commit and open a PR titled `docs: fill the project docs, skills and agents`.

### Task 4: CI checks

**Files:**
- Create:
  - `.github/workflows/lint.yml`: `uv sync --locked`, ruff check, ruff format --check, mypy, actionlint, zizmor.
  - `.github/workflows/tests.yml`: pytest, plus `scripts/check_doc_links.py`.
  - `.github/workflows/gitleaks.yml`;
  - `.github/pull_request_template.md`: what and why, `Closes #`, and a checklist of gates, title type, no private data, docs updated.
  - `.github/ISSUE_TEMPLATE/task.yml`.

Pin every action by SHA with a version comment, as `HA-NortecGo` does, and set `permissions: contents: read` and `persist-credentials: false`. Copy the SHAs from `HA-NortecGo/.github/workflows/`.

- [ ] **Step 1:** Write the workflows.
- [ ] **Step 2:** Run `uv run actionlint && uv run zizmor --offline .github/workflows`. Expected: clean.
- [ ] **Step 3:** Push the branch and open a PR titled `ci: lint, tests and gitleaks`. Expected: all three checks green on the PR (`gh pr checks`).
- [ ] **Step 4:** After the merge, set branch protection on `main` with `gh api`: require a PR, require the `lint`, `tests` and `gitleaks` checks, no force pushes. Record the settings in the ledger.

### Task 5: Integration skeleton, HACS files and the release pipeline

**Files:**
- Create:
  - **The integration skeleton:**
    - `custom_components/coop_dk/manifest.json`, with domain, name, codeowners, `"config_flow": false`, `iot_class`, `integration_type: "service"`, `requirements: []`, the documentation and issue_tracker URLs, and `"version": "0.0.0"`;
    - `custom_components/coop_dk/__init__.py`, holding only `DOMAIN = "coop_dk"` and an `async_setup` that returns `True`;
    - `custom_components/coop_dk/coop_client`, the symlink to `../../packages/coop-client/src/coop_client`.
  - **HACS:** `hacs.json`: `{"name": "Coop", "zip_release": true, "filename": "coop_dk.zip", "homeassistant": "<the HA version pytest-homeassistant-custom-component pins>"}`.
  - **Release:**
    - `CHANGELOG.md`, with `## [Unreleased]`;
    - `scripts/release_check.py`, ported from `HA-NortecGo`, with the manifest path changed;
    - `scripts/build_zip.py`, holding `build_zip(out: Path) -> Path` that zips `custom_components/coop_dk/` with symlinks followed;
    - `tests/test_release_check.py`, ported from HA-NortecGo's tests for it;
    - `tests/test_build_zip.py`;
    - `.github/workflows/version-check.yml`, `.github/workflows/auto-release.yml`, `.github/workflows/release.yml`, `.github/workflows/hassfest.yml`, `.github/workflows/hacs.yml`.
  - **Docs:** `docs/releasing.md`. It links HA-NortecGo's rules and states only what differs.

**Interfaces:**
- Produces:
  - `uv run python scripts/release_check.py release-pr --title='<title>'`, the bump step;
  - `release.yml`, which uploads `coop_dk.zip` built by `build_zip.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_release_zip_contains_client_source`: `build_zip` into `tmp_path`. Asserts that `coop_dk/manifest.json` and `coop_dk/coop_client/__init__.py` are entries whose zip info is not a symlink (external attr), and that no entry path contains `..`.
  - The ported `release_check` tests: each title type maps to its release level from `HA-NortecGo/docs/releasing.md`, and `docs!:` is rejected.
- [ ] **Step 2:** Run `uv run pytest tests/test_build_zip.py tests/test_release_check.py -v`. Expected: FAIL (modules missing).
- [ ] **Step 3:** Implement `build_zip` and port `release_check.py`. Then add the workflows. `release.yml` runs `build_zip.py` and attaches the zip to the GitHub release; the rest follows HA-NortecGo.
- [ ] **Step 4:** Run `uv run pytest -v && uv run mypy && uv run actionlint && uv run zizmor --offline .github/workflows`. Expected: PASS and clean.
- [ ] **Step 5:** Open a PR titled `ci: integration skeleton and auto-release`. Expected: hassfest and hacs green on the PR, and `version-check` green for the `ci:` title. After the merge, no release is published, because `ci` releases nothing. Add `hassfest`, `hacs` and `version-check` to the required checks.

### Task 6: Renovate and the dev Home Assistant

**Files:**
- Create:
  - `renovate.json`: managers `pep621`, `homeassistant-manifest` and `github-actions`; semantic commits `chore(deps)`; GitHub Actions pinned to digests.
  - `scripts/develop`, adapted from HA-NortecGo's. It creates `config/` with `default_config:`, symlinks `custom_components/coop_dk` into `config/custom_components/`, and runs `uv run hass -c config --debug`.
- Modify: `README.md`, adding the Commands section: `scripts/develop`, with its cost "no Coop request until the integration is set up".

- [ ] **Step 1:** Run `scripts/develop` in the background and wait for `http://localhost:8123` to answer.
- [ ] **Step 2: Chrome check.** Use the Chrome tools to:
  - open `localhost:8123`;
  - complete onboarding with a throwaway local user;
  - confirm the log shows `coop_dk` loaded with no error.

  Stop HA afterwards.
- [ ] **Step 3: Install the Renovate GitHub App** on `thomas3650/coop`, through the Chrome tools on github.com. If it needs the owner's own sign-in, ask the owner to click it. Expected: Renovate opens its onboarding PR or reads `renovate.json`.
- [ ] **Step 4:** Commit and open a PR titled `chore: renovate and the dev Home Assistant`.

### Task 7: The capture scrubber and flow export

**Files:**
- Create:
  - `packages/coop-client/src/coop_client/scrub.py`;
  - `packages/coop-client/tests/test_scrub.py`;
  - `scripts/export_flows.py`.

**Interfaces:**
- Produces:
  - `scrub_text(text: str, secrets: Iterable[str] = ()) -> str`
  - `scrub_json(value: object) -> object`, which masks by key, recursively.
  - `uv run --group capture python scripts/export_flows.py <flows> <out_dir>`: writes one scrubbed JSON file per flow, holding method, URL, request headers and body, status, and response headers and body.

- [ ] **Step 1: Write the failing tests**, one per rule, each asserting the original value is absent from the output:
  - `test_masks_by_key`: these keys become `<redacted>`:
    - `access_token`, `refresh_token`, `id_token`, `code`, `code_verifier`, `code_challenge`, `state`, `nonce`;
    - `Authorization`, `Ocp-Apim-Subscription-Key`, `subscriptionKey`, `app_installation_id`;
    - `name`, `description`, `email`, `phone`, `memberNumber`, `address`.
  - `test_masks_jwt`: an `eyJ…` JWT becomes `<JWT>`.
  - `test_masks_email_and_danish_phone`: an email and an 8-digit phone number.
  - `test_masks_known_secret_anywhere`: a value passed in `secrets` is masked inside a URL query.
  - `test_unknown_long_token_is_masked`: a 40-character base64url run becomes `<token>`.
  - `test_list_and_item_ids_masked`: integer `id` and `listId` become `<id>`.
- [ ] **Step 2:** Run `uv run pytest packages/coop-client/tests/test_scrub.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `scrub.py` with regexes and the key set above. `export_flows.py` reads with `mitmproxy.io.FlowReader` and applies `scrub_json` to JSON bodies and headers, and `scrub_text` to everything else.
- [ ] **Step 4:** Run `uv run pytest -v && uv run mypy`. Expected: PASS.
- [ ] **Step 5:** Commit and open a PR titled `chore(client): capture scrubber`. Not `feat`, because nothing a user sees changes and `feat` would release.

### Task 8: The static read, as research and as `docs/api.md`

Invoke `writing-coop-docs` and `examining-coop-endpoints`.

**Files:**
- Create:
  - `docs/research/2026-10-20-app-26.12.0-static-read.md`. It records:
    - the app version, `versionCode` 7569545, and the SHA-256 of each of the four APK files;
    - how the APK was pulled and decompiled;
    - the findings listed in the spec's "What the app showed" section, with the decompiled class names for that version.

    Hardcoded keys are noted as present, never quoted.
  - `docs/api.md`. It opens with the hosts and the bootstrap. It has one entry per endpoint the spec names:
    - the AppConfiguration bootstrap;
    - authorize, token (code exchange) and token (refresh);
    - list lists, list items, add items (bulk), complete, uncomplete, delete item.

    Each entry follows `docs/api-standard.md`, every claim is marked "inferred from app 26.12.0", and no class names appear. It ends with **Unknowns**: one item per row of the spec's capture question table.
- Modify: `docs/research/README.md`, adding a row.

- [ ] **Step 1:** Write both docs.
- [ ] **Step 2:** Run the secret scan line from `api-standard.md`, then `scripts/check_doc_links.py`, then `tests/test_docs_name_no_code.py`. Expected: nothing printed; 0 broken; PASS.
- [ ] **Step 3:** Commit and open a PR titled `docs: Coop API reference from the static read of app 26.12.0`.

### Task 9: The capture rig and the supervised capture (with the owner)

Done natively by the controller, not a subagent: it needs the owner at the emulator.

- [ ] **Step 1: Rig.**
  1. Create the AVD `coop` from `system-images;android-34;google_apis;arm64-v8a`, using the emulator at `/opt/homebrew/share/android-commandlinetools/emulator/emulator`, and boot it.
  2. Run `adb root`.
  3. Install the four files from `~/Downloads/coop-apk/` with `adb install-multiple`.
  4. Mount the mitmproxy CA as a system cert with nortecgo's `tools/install_system_ca.sh`, and check the count is 1.
  5. Start `mitmdump --mode wireguard -w .captures/coop-2026-10-xx.flows` and connect the emulator with nortecgo's `tools/make_wg_config.sh`.
  6. Run `git check-ignore .captures/` first.
- [ ] **Step 2: Ask the owner before starting.** The ask names exactly what happens:
  - one login typed by the owner;
  - open the shopping list;
  - add one test item, tick it, untick it;
  - close the app.
- [ ] **Step 3:** The owner logs in on the emulator. If the login page renders blank, unmount the CA, log in, remount, and relaunch the app on its stored login (the spec's known trap). Record which happened.
- [ ] **Step 4:** The owner does the list steps on the emulator, then checks whether their phone is still logged in and tells the controller.
- [ ] **Step 5:** Stop mitmdump. Run `scripts/export_flows.py` into `.captures/export/`. Read every exported file for an unscrubbed value before anything leaves `.captures/`.
- [ ] **Step 6: Write it up.**
  - Write `docs/research/2026-10-xx-first-capture.md`, which answers each capture question or leaves it open. Committed, trimmed payloads go under `docs/research/payloads/2026-10-xx-capture/`.
  - In `docs/api.md`, mark the measured entries measured, and delete each Unknown the capture answered.
  - Give a **go / no-go verdict** against the spec's "When the work stops for the owner" list.
- [ ] **Step 7:** Run the secret scan, the doc link check and the docs test. Expected: clean. Commit and open a PR titled `docs: first capture of the Coop app`.
- [ ] **Step 8:** Report the verdict to the owner. On a go, plan 2 (client, integration, local checks) is written next. On a no-go, stop.

## Not in this plan

Everything that logs in to Coop from code, which is the client's auth, the list calls and the integration's entities and config flow, is plan 2. It is written after Task 9 against measured payloads.
