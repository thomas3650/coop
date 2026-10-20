# Coop API reference

The Coop app's API as this project knows it: the hosts, the
[remote configuration](domain-language.md#dl-remote-configuration), the login and
the shopping-list calls this project uses. Every entry follows
[`api-standard.md`](api-standard.md). It describes Coop's API, which is Coop's to
change.

**Nothing here is measured yet.** Every claim is inferred from app 26.12.0, from
the static read in
[`research/2026-10-20-app-26.12.0-static-read.md`](research/2026-10-20-app-26.12.0-static-read.md);
no response has been captured. The capture turns entries measured
([spec](superpowers/specs/2026-10-20-coop-shopping-list-design.md#2-the-capture--the-gono-go-gate)).

## Hosts and the remote configuration

| Host | What | Status |
|---|---|---|
| `https://api.coopdk.lobyco.net/` | the default base of the remote configuration; the configuration's path is relative to it | inferred from app 26.12.0 |
| the remote configuration's `oidc.configuration` | the login: `issuer`, `authorizationEndpoint`, `tokenEndpoint`, `logoutEndpoint`; the host was not found in the app | inferred from app 26.12.0 |
| the remote configuration's `shoppingListV2.baseUrl` | the shopping-list service; every shopping-list path below is relative to it, as the app writes it (no leading slash); the host was not found in the app | inferred from app 26.12.0 |
| `unleash.coopdk.lobyco.net`, `api.omni.coop.dk` | feature flags and marketing analytics, each with a key built into the app | inferred from app 26.12.0 |

The app fetches the remote configuration first (A-CONFIG-1). Its client id,
redirect URIs, the shopping-list base URL and subscription key were not found in
the app; the app reads them from that configuration.

## Headers on every shopping-list call

| Header | Value | Status |
|---|---|---|
| `Authorization` | `Bearer <token>`, a token for the scopes `shopping-list offline_access` and the service's audiences | inferred from app 26.12.0 |
| `Ocp-Apim-Subscription-Key` | `<redacted>`, the configuration's `shoppingListV2.subscriptionKey`, when set | inferred from app 26.12.0 |
| `Accept-Language` | the device locale | inferred from app 26.12.0 |
| `User-Agent` | the system's `http.agent` | inferred from app 26.12.0 |
| `X-ActionName` | one name per call, in each entry's Notes; whether it reaches the server is unknown | inferred from app 26.12.0 |
| `X-Auth-Compatibility-Mode` | `Platform`, sent when a call's scopes include one from a fixed set; whether the shopping-list scopes are in it is unknown | inferred from app 26.12.0 |

No shopping-list call carries the placeholder header that makes the app add its
request signature, `X-Request-Signature` (inferred from app 26.12.0).

## Errors the app names

Which call answers with which error is not known (inferred from app 26.12.0).

| Area | Names |
|---|---|
| Login and tokens | `access_denied`, `user_blocked`, `invalid_grant`, `token_inactive`; a 403 `insufficient_scope`; `CredentialsPromptRequired` on a 401 or 403, after which the app retries the call |
| Shopping list | too many items, too many lists, too many subscribers, list not found, item not found, operation forbidden, invalid category, sharing link not valid — conditions the app distinguishes; the codes the server sends for them are unknown |

---

## GET appconfig/v1/AppConfiguration

Fetch the remote configuration: the login's endpoints and client, and each service's base URL, key and scopes.

| Auth | Cost | Status |
|---|---|---|
| unknown — the call declares no token scopes | reads only | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| none | | | | |

**Response** — none captured.

**Cost & mutation** — <a id="a-config-1"></a>A-CONFIG-1: a read with no login
(inferred from app 26.12.0); whether it changes anything on the server is not
known. Who-else-calls: the app, at start (inferred from app 26.12.0).

**Errors** — none captured.

**Notes** — `X-ActionName: AppConfiguration`. The response, as the app models it
(inferred from app 26.12.0), is a map keyed by service:

| Key | Holds |
|---|---|
| `oidc` | `configuration` {`issuer`, `authorizationEndpoint`, `tokenEndpoint`, `logoutEndpoint`}, `client` {`clientId`, `redirectUris` (array)} |
| `shoppingListV2` | `baseUrl`, `auth` {`audiences`, `scopes`}, `subscriptionKey`, `readTimeout`, `writeTimeout`, `status` |

## GET {authorizationEndpoint}

Start the login in a web view: the OIDC authorization request with PKCE.

| Auth | Cost | Status |
|---|---|---|
| none | part of a login | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| response_type | query | string | unknown | `code` |
| scope | query | string | unknown | space-joined; `shopping-list offline_access` for the shopping list |
| audience | query | string | unknown | space-joined, the service's audiences; sent when there are any |
| client_id | query | string | unknown | the configuration's `oidc.client.clientId` |
| redirect_uri | query | string | unknown | one of the configuration's `redirectUris`, picked at random |
| state, nonce | query | string | unknown | new per login |
| code_challenge, code_challenge_method | query | string | unknown | PKCE, `S256` |
| hideHeader | query | string | unknown | `true` |
| id_token_hint | query | string | no | sent when the app holds an id token |
| app_installation_id | query | string | no | `<uuid>`; sent when the app has one |
| login_hint | query | string | no | sent when the app has one |

**Response** — none captured.

**Cost & mutation** — <a id="a-auth-1"></a>A-AUTH-1: a login weighs on the
account-lock risk ([R-ACCOUNT-1](requirements.md#r-account-1)). It ends in a
redirect to the `redirect_uri` with a code, which the web view catches (inferred
from app 26.12.0). Who-else-calls: the app, at a login, and when a refresh fails
it reopens the login, apparently silently with `id_token_hint` (inferred from app
26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — the app recognises the paths `/connect/authorize` and
`/connect/authorize/callback`, IdentityServer/Duende paths (inferred from app
26.12.0). The app has MitID handling; what the login page asks for is decided on
the server. The manifest declares the schemes `coop-member` and
`coop-member-app`.

## POST {tokenEndpoint}

Exchange the authorization code for tokens: the end of a login.

| Auth | Cost | Status |
|---|---|---|
| none — no client secret | part of a login | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| grant_type | form | string | unknown | `authorization_code` |
| code | form | string | unknown | `<redacted>`, from the redirect |
| client_id | form | string | unknown | the configuration's client id |
| code_verifier | form | string | unknown | `<redacted>`, the PKCE verifier |
| redirect_uri | form | string | unknown | one of the configuration's `redirectUris`, picked at random again, apart from the authorize request's pick |

**Response** — none captured.

**Cost & mutation** — <a id="a-auth-2"></a>A-AUTH-2: mints a session's tokens;
whether a second session logs the phone out is unknown. Who-else-calls: the app,
at a login (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — the response, as the app models it (inferred from app 26.12.0):
`access_token`, `id_token`, `refresh_token`, `expires_in`. The app keeps one token
per scope and audience set.

## POST {tokenEndpoint}

Refresh: trade the [refresh token](domain-language.md#dl-refresh-token) for a new access token.

| Auth | Cost | Status |
|---|---|---|
| none — no client secret | part of a login | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| grant_type | form | string | unknown | `refresh_token` |
| refresh_token | form | string | unknown | `<token>` |
| client_id | form | string | unknown | the configuration's client id |

No `scope` is sent (inferred from app 26.12.0).

**Response** — none captured.

**Cost & mutation** — <a id="a-auth-3"></a>A-AUTH-3: whether the refresh token
rotates is unknown; [refresh token](domain-language.md#dl-refresh-token) holds how
this project handles that.
Who-else-calls: the app, on a 401 from a service, before retrying the call
(inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — the response is as in A-AUTH-2 (inferred from app 26.12.0).

## GET v1/shopping-lists

List the account's shopping lists.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | reads only | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| none | | | | |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-1"></a>A-LIST-1: a read (inferred from app
26.12.0); whether it changes anything on the server is not known.
Who-else-calls: the app (inferred from app 26.12.0).

**Errors** — none captured.

**Notes** — `X-ActionName: fetchAllShoppingLists`. A list, as the app models it
(inferred from app 26.12.0): `id` (integer), `name`, `description`, `permission`
(`Owner`, `ReadWrite`, `Undefined`), `shareType` (`Private`, `Shared`,
`Undefined`), `itemsCount`, `subscribersCount`, `createdDate`, `modifiedDate`.

## GET v1/shopping-lists/{listId}/items

List a list's items.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | reads only | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | integer | yes | the shared list's id |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-2"></a>A-LIST-2: a read (inferred from app
26.12.0); whether it changes anything on the server is not known.
Who-else-calls: the app (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — `X-ActionName: fetchShoppingListItems`. An item, as the app models it
(inferred from app 26.12.0): `id`, `name`, `description`, `product` {`id`,
`imageUrl`}, `offer` {`offerId`, `chainId`, `offerType`, `startDate`, `endDate`,
`details`}, `state` (`Normal`, `Completed`), `quantity` (number), `amount`
(integer), `unit` {`name`, `fullName`, `order`}, `createdDate`, `modifiedDate`,
`categoryId`. That the response holds the open items and Indkøbte varer together
is inferred, not seen.

## POST v1/shopping-lists/{listId}/items/bulk

Add one or more items to a list.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | changes the shared list | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | integer | yes | the shared list's id |
| (body) | body | array | yes | of new items, below |
| name | body item | string | unknown | the item's text |
| amount, unitName, quantity, categoryId, suggestionId, productId, offer | body item | — | unknown | free text is inferred to need only `name` |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-3"></a>A-LIST-3: adds items to the
list (inferred from app 26.12.0).
Who-else-calls: the app, when someone adds an item (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — `X-ActionName: addItemsBulk`. The app reads the response as a list of
items, shaped as in A-LIST-2 (inferred from app 26.12.0).

## PUT v1/shopping-lists/{listId}/items/{itemId}/complete

[Mark an item as shopped](domain-language.md#dl-mark-as-shopped): move it to Indkøbte varer.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | changes the shared list | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | integer | yes | the shared list's id |
| itemId | path | integer | yes | the item's id |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-4"></a>A-LIST-4: sets the item's `state` to
`Completed` (inferred from app 26.12.0). Who-else-calls: the app, when someone
ticks an item (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — `X-ActionName: markItemAsChecked`. No body. The app reads the response
as one item, shaped as in A-LIST-2 (inferred from app 26.12.0).

## PUT v1/shopping-lists/{listId}/items/{itemId}/uncomplete

[Put an item back](domain-language.md#dl-put-back) from Indkøbte varer.

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | changes the shared list | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | integer | yes | the shared list's id |
| itemId | path | integer | yes | the item's id |
| restoreItemOrder | query | boolean | unknown | the value the app sends is unknown |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-5"></a>A-LIST-5: sets the item's `state` to
`Normal` (inferred from app 26.12.0). Who-else-calls: the app, when someone
unticks an item (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — `X-ActionName: markItemAsUnchecked`. No body. The app reads the
response as one item, shaped as in A-LIST-2 (inferred from app 26.12.0).

## DELETE v1/shopping-lists/{listId}/items/{itemId}

Delete an item. See [decisions](decisions.md) and [R-LIST-6](requirements.md#r-list-6).

| Auth | Cost | Status |
|---|---|---|
| `Bearer` + subscription key | changes the shared list | inferred from app 26.12.0 |

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| listId | path | integer | yes | the shared list's id |
| itemId | path | integer | yes | the item's id |

**Response** — none captured.

**Cost & mutation** — <a id="a-list-6"></a>A-LIST-6: removes the item from the
list (inferred from app 26.12.0). Who-else-calls: the
app, when someone deletes an item (inferred from app 26.12.0).

**Errors** — none captured; the app's own error names are under [Errors the app names](#errors-the-app-names).

**Notes** — `X-ActionName: deleteItem`.

---

## Other calls in the app

The app's other shopping-list calls — rename, delete a list, set an amount,
complete-all, undo, share, suggestions, categories and units — are listed in the
static read's
[shopping-list calls](research/2026-10-20-app-26.12.0-static-read.md#shopping-list-calls).

---

## Unknowns

Each is open until the capture answers it; an answered item is deleted.

1. What the login page asks for: email and password, MitID, or a code.
2. Which redirect URI the configuration serves, and whether it is a custom scheme.
3. How many redirect URIs the configuration serves; the app picks one at random
   for the authorize request and again for the code exchange.
4. Whether one refresh token covers the `shopping-list` scope, or that scope needs
   its own authorization.
5. Whether refresh tokens rotate, as the normal session shows it (what a reused
   old one does is not tested).
6. Whether a second session logs the phone out.
7. The real shape of the list and item payloads, of the add, complete and
   uncomplete requests, and of the errors.
8. The client id, the identity-provider host and the shopping-list base URL — the
   remote configuration's values.
9. Token lifetimes.
10. Where `app_installation_id` comes from.
11. Whether `X-ActionName` reaches the server, and whether shopping-list calls
    carry `X-Auth-Compatibility-Mode`.
12. What the remote configuration request carries, and whether it needs a key.
13. The `restoreItemOrder` value the app sends on uncomplete.
14. Whether the items call returns the open items and Indkøbte varer together.
15. Which calls the app's widget makes when it polls, and how often.
16. Whether a new login triggers device binding, and whether binding a second
    device affects the phone.
