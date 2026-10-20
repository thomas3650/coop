"""Run the flow export end to end on a capture written by mitmproxy itself.

    uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows_selfcheck.py

Builds flows with mitmproxy's test helpers, with secrets planted where a login puts
them: a bearer JWT, a form-posted password, an `idsrv` session cookie, and a refresh
token in a JSON response. Writes them with mitmproxy's `FlowWriter` into a temporary
folder, runs the export on that file, and fails if a planted value appears in any
exported file. Makes no network request. Not part of the offline suite, which does
not have mitmproxy.
"""

import json
import sys
import tempfile
from pathlib import Path

import export_flows


def _planted() -> dict[str, str]:
    """Fake secrets, assembled at runtime so no literal has a credential's shape."""
    return {
        "jwt": "eyJ" + "hbGciOiJSUzI1NiJ9" + "." + "eyJ" + "zdWIiOiJ4In0" + "." + "c2ln" * 9,
        "password": "pw-" + "selfcheck" + "-planted",
        "cookie": "idsrv-" + "selfcheck" + "-planted",
        "refresh_token": "rt-" + "selfcheck" + "-planted",
    }


def main() -> int:
    from mitmproxy.io import FlowWriter
    from mitmproxy.test import tflow

    planted = _planted()

    login = tflow.tflow(resp=True)
    login.request.method = "POST"
    login.request.url = "https://login.example.test/Account/Login"
    login.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
    login.request.content = f"Input.Username=u&Input.Password={planted['password']}".encode()
    login.response.headers["Set-Cookie"] = f"idsrv.session={planted['cookie']}; path=/; secure"

    api = tflow.tflow(resp=True)
    api.request.url = "https://api.example.test/lists/4711"
    api.request.headers["Authorization"] = f"Bearer {planted['jwt']}"
    api.response.headers["Content-Type"] = "application/json"
    api.response.content = json.dumps(
        {"refresh_token": planted["refresh_token"], "token_type": "Bearer"}
    ).encode()

    with tempfile.TemporaryDirectory() as tmp:
        flows_path = Path(tmp) / "capture.flows"
        with flows_path.open("wb") as flows_file:
            writer = FlowWriter(flows_file)
            writer.add(login)
            writer.add(api)
        out_dir = Path(tmp) / "out"
        export_flows.main([str(flows_path), str(out_dir)])

        exported = sorted(out_dir.iterdir())
        leaks = [
            f"{path.name}: {label}"
            for path in exported
            for label, value in planted.items()
            if value in path.read_text(encoding="utf-8")
        ]
        for path in exported:
            print(f"--- {path.name}")
            print(path.read_text(encoding="utf-8"))
    if len(exported) != 2 or leaks:
        print(f"FAIL: {len(exported)} files, leaks: {leaks}", file=sys.stderr)
        return 1
    print(f"OK: none of {sorted(planted)} appears in the {len(exported)} exported files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
