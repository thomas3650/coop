# Domain language

The vocabulary this project uses for itself. Where a word here means something
different from its everyday sense, that's deliberate — use the project's meaning
everywhere: code, tests, docs, commit messages and conversation.

What the Coop app does is inferred from app 26.12.0 until a capture measures it
([`docs/research/`](research/README.md)).

## Coop

| Term | Danish | Definition | Not to be confused with |
|---|---|---|---|
| <a id="dl-owner"></a>**The owner** | — | The account holder whose Coop login the integration uses, and who owns this repo and its Home Assistant. | Not a family member at home, who uses the dashboard and has a Coop login of their own that this project does not use. |
| <a id="dl-shared-list"></a>**The shared list** | indkøbsliste | The one shopping list the owner's family shares between their own Coop logins; the only list Home Assistant shows. | Not every list on the account — any other list is ignored. Not Indkøbte varer. |
| <a id="dl-item"></a>**Item** | vare | One line on the shared list: a name, an amount, and a state of `Normal` or `Completed`. An **open item** is one in state `Normal`. | Not a product from Coop's catalogue — an item added from Home Assistant is free text. |
| <a id="dl-indkobte-varer"></a>**Indkøbte varer** | Indkøbte varer | The items of the shared list in state `Completed` — where an item goes when it is ticked in the store. | Not a separate list; not something Home Assistant ever clears. |
| <a id="dl-mark-as-shopped"></a>**Mark as shopped** | — | Ticking an item, which moves it to Indkøbte varer. The API calls it **complete**. | Not delete: the item stays on the list, in Indkøbte varer. |
| <a id="dl-put-back"></a>**Put back** | — | Unticking an item in Indkøbte varer, which returns it to the open items. The API calls it **uncomplete**. | Not adding the item again. |
| <a id="dl-remote-configuration"></a>**Remote configuration** | — | What the app fetches first: the login's endpoints and client id, the shopping-list service's base URL, its subscription key and its audiences. | Not a value in the app's code — none of these was found there. |
| <a id="dl-one-time-browser-login"></a>**One-time browser login** | — | The owner's single Coop login in their own browser during setup, which gives Home Assistant its first refresh token. After it, Home Assistant only refreshes. | Not a login Home Assistant repeats on its own: a refused refresh ends in Home Assistant's re-authenticate flow, which the owner starts. |
| <a id="dl-refresh-token"></a>**Refresh token** | — | The long-lived token Home Assistant keeps in its config entry and trades for a new access token. Treated as use-once: a rotated one is stored before the next request. | Not the owner's password, which Home Assistant never holds. Not the access token, which a request carries. |
| <a id="dl-account-lock"></a>**Account lock** | — | Coop refusing the owner's login, for whatever reason Coop has. The failure that ranks above every feature ([R-ACCOUNT-1](requirements.md#r-account-1)). | Not a refused refresh, which only means the owner logs in again. |

## This project

| Term | Danish | Definition | Not to be confused with |
|---|---|---|---|
| <a id="dl-real-ha"></a>**The owner's real Home Assistant** | — | The Home Assistant the owner's family uses at home. Reached from here through the Home Assistant MCP tools only. | Not the **dev Home Assistant**, a disposable one on the Mac at `http://localhost:8123`. One of the two holds the Coop login at a time. |
| <a id="dl-capture"></a>**The capture** | — | A supervised session recording the Coop app's own traffic on an emulator, used normally ([`reverse-engineering.md`](reverse-engineering.md)). | Not a probe: nothing in it is sent by hand. |
| <a id="dl-scrubber"></a>**The scrubber** | — | What every capture goes through before anything derived from it is committed; it masks what [the redaction list](api-standard.md#redaction) names. | Not proof of safety on its own — the result is still read by hand. |
| <a id="dl-live-marker"></a>**`live` marker** | — | The pytest marker on a test that reaches the real Coop with the owner's credentials. A plain `uv run pytest` deselects it; a `-m live` run needs a fresh ask. | Not "slow" or "integration": the marker means a real request to Coop. |
| <a id="dl-live-guard"></a>**Live guard** | — | What stops an unmarked test reaching the owner's credentials: collection fails when a test not marked `live` sits in a module that can reach the credentials loader, and the loader refuses to read `.env` during a test run unless that run's marker expression is exactly `live`. | Not the `live` marker itself, which only deselects. |
