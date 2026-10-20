# Decisions

A log of things this project deliberately will not build, and why. When a new one
comes up, add a row and point it at a spec if there's a design behind it; a
one-line "no" needs none.

| Decision | Why |
|---|---|
| Home Assistant never deletes an item and never clears Indkøbte varer | Nothing the family wrote may be lost from the dashboard; marking as shopped is the only way out ([R-LIST-6](requirements.md#r-list-6)) |
| No product search when adding an item, no quantity editing, no renaming, and one list only, in phase 1 | The owner's [Goals](superpowers/specs/2026-10-20-coop-shopping-list-design.md#goals): free text, quantity 1, the one shared list |
| One repo for the client and the integration, not a public client and a private integration | One public repo from the first commit, the client bundled into the integration at release ([R-REPO-1](requirements.md#r-repo-1)) |
| No listing in HACS's default store, and no support for other Coop members | Phase 1 is for the owner's own Home Assistant ([spec](superpowers/specs/2026-10-20-coop-shopping-list-design.md#not-in-this-phase)) |
