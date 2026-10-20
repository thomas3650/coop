# Capturing the Coop app's traffic

How to decrypt and read the Coop app's own HTTPS, so `docs/api.md` can turn its
inferred entries into measured ones. A how-to; what a given run showed is a dated
file in [`research/`](research/README.md).

## The recipe is the owner's other two repos'; the deltas are here

The emulator rig — a rooted Android 14 emulator, mitmproxy in WireGuard mode, the
mitmproxy CA as a system certificate, the WireGuard client config — is
`docs/reverse-engineering.md` in the owner's `nortecgo` repo, and the Chrome trap
below is from the same file in `nota_music_provider`. Read those for the one-time
install and the mechanics. What follows is only what Coop does differently.

| # | Delta | Detail |
|---|---|---|
| 1 | **Its own emulator** | A new Android 14 emulator named `coop`, from the same `google_apis` arm64 image as `nortec`. The `nortec` emulator stays untouched. |
| 2 | **A split bundle, from the owner's phone** | Four APK files pulled from the owner's phone, installed with `adb install-multiple`. Their version and SHA-256 go in the run's research file. The APKs and the decompiled source never enter the repo; `.gitignore` covers them. |
| 3 | **No Frida to start with** | The decompiled app shows no certificate pinning, no custom trust manager, no network security config and no attestation call (inferred from app 26.12.0). The system CA should be enough; Frida is added only if the capture comes back blank. |
| 4 | **The Chrome trap is expected** | In nota, the system-CA mount broke the Chrome renderer its login page ran in. Coop's login also runs in a web view. If it renders blank, log in with the mount off, then mount it and relaunch the app on its stored login. |
| 5 | **The captures stay out of git** | `mitmdump` writes to `.captures/`, which is git-ignored. Every flow is scrubbed ([redaction](api-standard.md#redaction)) and read by hand before anything derived from it is committed. |

## Only what the app does

The owner's decision, and a rule in [`CLAUDE.md`](../CLAUDE.md) (Live requests).
The capture records the app used normally and nothing more:

- no replayed or stale token;
- no request crafted by hand;
- no error provoked on purpose.

A question the normal session does not answer stays open in `docs/api.md`'s
**Unknowns**; the questions the capture must answer are in the
[spec](superpowers/specs/2026-10-20-coop-shopping-list-design.md#2-the-capture--the-gono-go-gate).

## The session is supervised

| Step | Who |
|---|---|
| Stop the integration on the owner's real Home Assistant, if it is running, so the emulator's is the only Coop session this project holds | the owner, or the agent on the owner's yes |
| Type the Coop login on the emulator; nothing automates it | the owner |
| Add one item of the owner's own, mark it as shopped, put it back — nothing else | the owner |
| Check that the phone is still logged in | the owner |
