"""Run the flow export end to end on a capture written by mitmproxy itself.

    uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows_selfcheck.py

Builds flows with mitmproxy's test helpers, with secrets planted where a login puts
them: a bearer JWT, a form-posted password, an `idsrv` session cookie, and a refresh
token in JSON responses compressed with gzip, br and zstd (those this mitmproxy can
write), plus a body whose Content-Encoding does not decode. Writes them with mitmproxy's `FlowWriter` into a temporary
folder, runs the export on that file, and fails if a planted value appears in any
exported file, if a compressed body is not exported as scrubbed JSON, or if the
undecodable body is not exported as `<binary>`. Makes no network request. Not part of the offline suite, which does
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

    # One response per Content-Encoding mitmproxy can write here. Setting `content`
    # after the header makes mitmproxy compress the body, so the capture holds the
    # encoded bytes and the export has to decode them.
    problems: list[str] = []
    encoded = []
    for encoding in _encodings():
        flow = tflow.tflow(resp=True)
        flow.request.url = f"https://api.example.test/token?enc={encoding}"
        flow.response.headers["Content-Type"] = "application/json"
        flow.response.headers["Content-Encoding"] = encoding
        flow.response.content = json.dumps(
            {"refresh_token": planted["refresh_token"], "token_type": "Bearer"}
        ).encode()
        if flow.response.raw_content == flow.response.content:
            problems.append(f"{encoding}: mitmproxy did not compress the body")
        encoded.append((encoding, flow))

    # A body whose Content-Encoding is a lie: `get_content(strict=False)` hands back
    # the raw bytes, which are not UTF-8, so the export writes `<binary>`.
    broken = tflow.tflow(resp=True)
    broken.response.headers["Content-Encoding"] = "gzip"
    broken.response.raw_content = b"\xff\xfe not gzip " + planted["refresh_token"].encode()

    flows = [login, api, *(flow for _, flow in encoded), broken]
    with tempfile.TemporaryDirectory() as tmp:
        flows_path = Path(tmp) / "capture.flows"
        with flows_path.open("wb") as flows_file:
            writer = FlowWriter(flows_file)
            for flow in flows:
                writer.add(flow)
        out_dir = Path(tmp) / "out"
        export_flows.main([str(flows_path), str(out_dir)])

        exported = sorted(out_dir.iterdir())
        texts = {path.name: path.read_text(encoding="utf-8") for path in exported}
        for name, text in texts.items():
            print(f"--- {name}")
            print(text)
    problems += [
        f"{name}: {label} leaked"
        for name, text in texts.items()
        for label, value in planted.items()
        if value in text
    ]
    expected_names = [f"{index:04d}.json" for index in range(len(flows))]
    missing = [name for name in expected_names if name not in texts]
    if missing or len(texts) != len(flows):
        problems.append(f"{len(texts)} files for {len(flows)} flows; missing {missing}")
    for index, (encoding, _) in enumerate(encoded, start=2):
        name = f"{index:04d}.json"
        if name in texts:
            body = _response_body(texts[name])
            if body != {"refresh_token": "<redacted>", "token_type": "Bearer"}:
                problems.append(f"{encoding} body exported as {body!r}")
    broken_name = expected_names[-1]
    if broken_name in texts:
        broken_body = _response_body(texts[broken_name])
        if broken_body != "<binary>":
            problems.append(f"undecodable body exported as {broken_body!r}")
    if problems:
        print(f"FAIL: {problems}", file=sys.stderr)
        return 1
    encodings = [encoding for encoding, _ in encoded]
    print(
        f"OK: {len(flows)} flows; none of {sorted(planted)} appears; "
        f"{encodings} bodies exported as scrubbed JSON; the undecodable body as <binary>"
    )
    return 0


def _response_body(text: str) -> object:
    """The exported response body, or the whole record if it has none (a placeholder)."""
    record = json.loads(text)
    response = record.get("response") if isinstance(record, dict) else None
    return response.get("body") if isinstance(response, dict) else record


def _encodings() -> list[str]:
    """gzip, br and zstd, those of them this mitmproxy can encode."""
    from mitmproxy.net import encoding

    usable = []
    for name in ["gzip", "br", "zstd"]:
        try:
            encoding.encode(b"x", name)
        except ValueError:
            continue
        usable.append(name)
    return usable


if __name__ == "__main__":
    sys.exit(main())
