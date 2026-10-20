# Memory

What the owner has told us that must outlive a session but is not a rule
(`CLAUDE.md`), a requirement, a term or a design decision. One row per item;
delete a row when it stops being true.

| Item | Why |
|---|---|
| The agent handles GitHub — the repo, its settings, issues, PRs and merging when ready — without asking each time | The owner said so on 2026-10-20 |
| The owner's first concern is Coop locking their account | The owner said so; it ranks above freshness and every feature ([R-ACCOUNT-1](requirements.md#r-account-1)) |
| The owner approves each spec | The owner's way of working |
| The agent asks the owner to approve each plan before it is executed | The owner's way of working |
| Implementation goes to subagents by default; a small task is done natively | The owner's way of working |
| Each feature is verified in a local Home Assistant through Chrome before it is called done | The owner's way of working, as in their other two repos ([R-REPO-2](requirements.md#r-repo-2)) |
