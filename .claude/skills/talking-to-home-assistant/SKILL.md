---
name: talking-to-home-assistant
description: Use when anything in this repo needs the owner's real Home Assistant — reading an integration's state, version or log, checking the Coop list's to-do entity, installing, reloading, enabling or disabling the integration — or when a `mcp__home-assistant__*` call fails and curl, the REST API, the websocket API or SSH looks like a way round it. Not for the dev Home Assistant on localhost.
---

# Talking to Home Assistant

The owner's real Home Assistant is their **live home**: the family uses its
dashboard every day. This repo's business with it is the Coop integration and
the shared list's to-do entity, nothing else.

**The `mcp__home-assistant__*` tools are the only way in. Reading is allowed;
every change needs the owner's yes for that one action.**

The dev Home Assistant at `http://localhost:8123` is a different thing: it is
this repo's, and it is driven through Chrome (`docs/requirements.md` R-REPO-2).

## Rules

| Rule | Detail |
|---|---|
| **MCP only** | No `curl`, `WebFetch`, REST or websocket call, and no SSH, to the owner's real Home Assistant to get round a tool, and no command handed to the owner to run instead. A blocked call is a blocked task: report the error and stop. |
| **No tools at all** | The server is registered in Claude Code's user config (`claude mcp get home-assistant`). A session started without the `mcp__home-assistant__*` tools says so and does not improvise. |
| **Reads need no ask** | The "Read" rows below. |
| **Every change is asked for, one at a time** | The "Change" rows below. A yes covers that action only; a step in a plan or an issue is not a yes. |
| **Never delete from the Coop list** | `ha_remove_todo_item`, and "remove completed items", on the Coop list's entity: not from here, whatever the reason (R-LIST-6). Adding or ticking an item with `ha_set_todo_item` changes the family's real list: ask for each one. |
| **One Home Assistant holds the Coop login** | Before a dev Home Assistant logs in to the real Coop, or a capture runs, the integration here is disabled — on the owner's yes — and enabled again afterwards, also on a yes (`CLAUDE.md`, Live requests). |
| **The dashboard is the owner's** | Adding the list card to the real dashboard is the owner's job. Dashboards, automations, areas, labels and other integrations are not this repo's; do not touch them from here. |
| **The token stays out of this repo** | It lives in Claude Code's user config; there is no `.mcp.json` in this repo. Never print it, copy it into a file, a doc or a commit. |
| **A log is scrubbed before it leaves the session** | A Home Assistant log holds more than this integration's lines. Scrub it, then take only the lines the question needs into a doc, an issue or a PR. List content is personal data ([redaction](../../../docs/api-standard.md#redaction)). |

## Which tool

| Task | Tool | Kind |
|---|---|---|
| The integration's config entry and its state | `ha_get_integration` | Read |
| An entity's state, e.g. the Coop list's to-do entity | `ha_get_state`, `ha_get_entity` | Read |
| The items of a to-do entity | `ha_get_todo` | Read |
| Home Assistant's log | `ha_get_logs` | Read |
| Versions and health | `ha_get_system_health`, `ha_get_overview` | Read |
| HACS: installed repositories and versions | `ha_get_hacs_info` | Read |
| Install or update the integration through HACS | `ha_manage_hacs` | **Change** |
| Add, reload, enable or disable the integration | `ha_set_integration` | **Change** |
| Add or tick an item | `ha_set_todo_item` | **Change** |
| Press the refresh button | `ha_call_service` | **Change** — it sends a request to Coop |
| Restart Home Assistant | `ha_restart` | **Change** |

Each tool describes its own parameters. After a change with an unknown outcome
(a timeout, a dropped connection), read the state back before anything else.
Never replay a change.

## Mistakes this skill exists for

| Thought | Instead |
|---|---|
| "The tool timed out; the REST API is the same thing" | Report the error and stop. |
| "The plan says disable the integration, so I may" | The plan is not a yes. Ask for that action. |
| "A test item proves it works" | It lands on the family's real list. Ask first, or use the dev Home Assistant. |
| "This completed item is clutter; I'll remove it" | Never delete from the Coop list. |
| "The card would look better on the main dashboard" | The dashboard is the owner's. |
