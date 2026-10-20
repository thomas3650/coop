# Requirements

The target state — how the system is meant to work, not a description of today's
code. Where the code differs, the requirement stands; what is deferred and why is
the "Not in this phase" section of the current spec under `docs/superpowers/specs/`.
What will not be built lives in [`decisions.md`](decisions.md).

Each requirement is a short user story with an anchor:
`- <a id="r-area-1"></a>**R-AREA-1** As a <persona>, I <get what>, so <why>.`

**Personas:** [the owner](domain-language.md#dl-owner) holds the Coop login the
integration uses and sets it up; a **family member at home** uses the shopping
list on the Home Assistant dashboard.

The detail behind each story is the phase 1 spec's
[Goals](superpowers/specs/2026-10-20-coop-shopping-list-design.md#goals); not
restated here.

## The list

- <a id="r-list-1"></a>**R-LIST-1** As the owner, Home Assistant shows the one [shared list](domain-language.md#dl-shared-list) and ignores any other list on the account, so the dashboard is the family's list and nothing else.
- <a id="r-list-2"></a>**R-LIST-2** As a family member at home, I see the open items and the items in [Indkøbte varer](domain-language.md#dl-indkobte-varer), so I know what is still to buy without picking up a phone.
- <a id="r-list-3"></a>**R-LIST-3** As a family member at home, I add an item as free text, and it lands on the list with quantity 1, so I can note what we are out of the moment I see it.
- <a id="r-list-4"></a>**R-LIST-4** As a family member at home, ticking an item [marks it as shopped](domain-language.md#dl-mark-as-shopped): it moves to Indkøbte varer exactly as ticking it in the app does, so the app and the dashboard agree.
- <a id="r-list-5"></a>**R-LIST-5** As a family member at home, unticking an item in Indkøbte varer [puts it back](domain-language.md#dl-put-back) on the list, so a tick by mistake costs nothing.
- <a id="r-list-6"></a>**R-LIST-6** As the owner, Home Assistant never deletes an item — not even one added by mistake — and never clears Indkøbte varer; marking as shopped is the only way an item leaves the list from Home Assistant, so nothing the family wrote is lost from the dashboard.
- <a id="r-list-7"></a>**R-LIST-7** As a family member at home, the list is re-read once an hour and when I press the refresh button on the dashboard, so what I see is recent without anyone opening the app.

## Setup

- <a id="r-setup-1"></a>**R-SETUP-1** As the owner, the integration uses my own Coop login, set up through a [one-time browser login](domain-language.md#dl-one-time-browser-login), so setup asks nothing of my phone and Home Assistant does not log in again on its own.
- <a id="r-setup-2"></a>**R-SETUP-2** As the owner, I install the integration as a HACS custom repository on my Home Assistant, so it updates the way my other custom integrations do.

## The account

- <a id="r-account-1"></a>**R-ACCOUNT-1** As the owner, nothing this project builds or runs gives Coop a reason to lock my account ([anti-goals](superpowers/specs/2026-10-20-coop-shopping-list-design.md#anti-goals)).
- <a id="r-account-2"></a>**R-ACCOUNT-2** As the owner, one Home Assistant holds my Coop login at a time, so a dev Home Assistant and my real one never fight over it.
- <a id="r-account-3"></a>**R-ACCOUNT-3** As the owner, no token, password, member number, name, address or list content ever reaches a commit, so the public repo carries nothing of mine.

## The repo

- <a id="r-repo-1"></a>**R-REPO-1** As the owner, the Coop API client and the integration live in one public GitHub repo from the first commit, the client bundled inside the integration at release, with dependency updates and a release pipeline HACS can see, so one place holds the whole thing.
- <a id="r-repo-2"></a>**R-REPO-2** As the owner, each feature is tried in a local Home Assistant through the Chrome browser before it is called done, so "done" means seen working, as in my other two repos.
- <a id="r-repo-3"></a>**R-REPO-3** As the owner, the Coop API is documented in a reference of its own, every entry following [the entry standard](api-standard.md), so what the API does is read, not re-derived.
- <a id="r-repo-4"></a>**R-REPO-4** As the owner, the docs describe how things behave and never name this repo's code, so a doc stays true when the code is reorganised.
