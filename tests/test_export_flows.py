"""The flow export: one scrubbed JSON file per flow, nothing raw, nothing outside out_dir.

The flows are stand-ins with the attributes the export reads from a mitmproxy
`HTTPFlow`, so the suite does not need mitmproxy.
"""

import getpass
import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import export_flows
import pytest

_JWT = "eyJ" + "hbGciOiJSUzI1NiJ9" + "." + "eyJ" + "zdWIiOiJ4In0" + "." + "c2lnbmF0dXJl" * 3


class _Headers:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = pairs

    def items(self, multi: bool = False) -> Iterator[tuple[str, str]]:
        """Like mitmproxy's `Headers.items`: without `multi`, one pair per name."""
        if multi:
            return iter(self._pairs)
        seen: dict[str, tuple[str, str]] = {}
        for name, value in self._pairs:
            seen.setdefault(name.lower(), (name, value))
        return iter(seen.values())


class _Message:
    def __init__(self, headers: list[tuple[str, str]], body: bytes | None) -> None:
        self.headers = _Headers(headers)
        self._body = body

    def get_content(self, strict: bool = True) -> bytes | None:
        assert strict is False
        return self._body


def _flow(
    *,
    url: str = "https://api.example.test/lists",
    method: str = "GET",
    request_headers: list[tuple[str, str]] | None = None,
    request_body: bytes | None = None,
    status: int = 200,
    response_headers: list[tuple[str, str]] | None = None,
    response_body: bytes | None = None,
) -> Any:
    request = _Message(request_headers or [], request_body)
    response = _Message(response_headers or [], response_body)
    return SimpleNamespace(
        request=SimpleNamespace(
            method=method, pretty_url=url, headers=request.headers, get_content=request.get_content
        ),
        response=SimpleNamespace(
            status_code=status, headers=response.headers, get_content=response.get_content
        ),
    )


def _written(out_dir: Path) -> list[str]:
    return sorted(p.name for p in out_dir.iterdir())


def test_writes_one_scrubbed_file_per_flow(tmp_path: Path) -> None:
    flow = _flow(
        method="POST",
        url="https://login.example.test/connect/token",
        request_headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Ocp-Apim-Subscription-Key", "sub-s3cr3t"),
        ],
        request_body=b"grant_type=refresh_token&refresh_token=rt-s3cr3t&scope=openid",
        response_headers=[("Content-Type", "application/json")],
        response_body=json.dumps(
            {"access_token": _JWT, "refresh_token": "rt2-s3cr3t", "token_type": "Bearer"}
        ).encode(),
    )
    count = export_flows.export([flow], tmp_path)
    assert count == 1
    assert _written(tmp_path) == ["0000.json"]
    raw = (tmp_path / "0000.json").read_text()
    assert "s3cr3t" not in raw
    assert _JWT not in raw
    record = json.loads(raw)
    assert record["method"] == "POST"
    assert record["url"] == "https://login.example.test/connect/token"
    assert record["status"] == 200
    assert record["request"]["headers"] == [
        ["Content-Type", "application/x-www-form-urlencoded"],
        ["Ocp-Apim-Subscription-Key", "<redacted>"],
    ]
    assert record["request"]["body"] == [
        ["grant_type", "refresh_token"],
        ["refresh_token", "<redacted>"],
        ["scope", "openid"],
    ]
    assert record["response"]["body"] == {
        "access_token": "<redacted>",
        "refresh_token": "<redacted>",
        "token_type": "Bearer",
    }


def test_scrubs_the_url_query(tmp_path: Path) -> None:
    flow = _flow(url="https://login.example.test/authorize?code_challenge=cc-s3cr3t&x=1")
    export_flows.export([flow], tmp_path)
    raw = (tmp_path / "0000.json").read_text()
    assert "cc-s3cr3t" not in raw
    assert "x=1" in raw


def test_json_body_detected_whatever_the_content_type(tmp_path: Path) -> None:
    flow = _flow(
        response_headers=[("Content-Type", "text/plain")],
        response_body=b'{"email": "a@b.dk", "listId": 4711}',
    )
    export_flows.export([flow], tmp_path)
    record = json.loads((tmp_path / "0000.json").read_text())
    assert record["response"]["body"] == {"email": "<redacted>", "listId": "<id>"}


def test_text_body_goes_through_scrub_text(tmp_path: Path) -> None:
    html = b'<input type="hidden" name="code" value="c0de-s3cr3t" /> Bearer opaque-s3cr3t'
    flow = _flow(response_headers=[("Content-Type", "text/html")], response_body=html)
    export_flows.export([flow], tmp_path)
    raw = (tmp_path / "0000.json").read_text()
    assert "s3cr3t" not in raw


def test_undecodable_body_becomes_a_placeholder(tmp_path: Path) -> None:
    body = gzip.compress(b"refresh_token=rt-s3cr3t") + b"\xff\xfe"
    flow = _flow(response_headers=[("Content-Encoding", "gzip")], response_body=body)
    export_flows.export([flow], tmp_path)
    record = json.loads((tmp_path / "0000.json").read_text())
    assert record["response"]["body"] == "<binary>"


def test_flow_without_response(tmp_path: Path) -> None:
    flow = _flow()
    flow.response = None
    export_flows.export([flow], tmp_path)
    record = json.loads((tmp_path / "0000.json").read_text())
    assert record["status"] is None
    assert record["response"] is None


def test_unparseable_flow_writes_only_a_placeholder(tmp_path: Path) -> None:
    class _Broken:
        @property
        def request(self) -> Any:
            raise ValueError("refresh_token=rt-s3cr3t")

    export_flows.export([_Broken(), SimpleNamespace(type="tcp")], tmp_path)
    assert _written(tmp_path) == ["0000.json", "0001.json"]
    for name in ["0000.json", "0001.json"]:
        raw = (tmp_path / name).read_text()
        assert json.loads(raw) == export_flows.PLACEHOLDER
        assert "s3cr3t" not in raw


def test_a_stream_that_breaks_midway_ends_with_a_placeholder(tmp_path: Path) -> None:
    def stream() -> Iterator[Any]:
        yield _flow()
        raise ValueError("corrupt: refresh_token=rt-s3cr3t")

    export_flows.export(stream(), tmp_path)
    assert _written(tmp_path) == ["0000.json", "0001.json"]
    raw = (tmp_path / "0001.json").read_text()
    assert json.loads(raw) == export_flows.PLACEHOLDER


def test_refuses_to_write_outside_out_dir(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with pytest.raises(export_flows.OutsideOutDirError):
        export_flows.write_record(out_dir, "../escaped.json", {})
    assert not (tmp_path / "escaped.json").exists()


def test_refuses_to_write_through_a_symlink_out_of_out_dir(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (out_dir / "link").symlink_to(elsewhere)
    with pytest.raises(export_flows.OutsideOutDirError):
        export_flows.write_record(out_dir, "link/x.json", {})
    assert list(elsewhere.iterdir()) == []


def _response_body(tmp_path: Path, body: bytes, content_type: str = "text/plain") -> object:
    flow = _flow(response_headers=[("Content-Type", content_type)], response_body=body)
    export_flows.export([flow], tmp_path)
    record = json.loads((tmp_path / "0000.json").read_text())
    return record["response"]["body"]


def test_repeated_headers_are_all_exported(tmp_path: Path) -> None:
    flow = _flow(
        response_headers=[
            ("Set-Cookie", "a=1"),
            ("Set-Cookie", "idsrv.session=c-s3cr3t"),
        ]
    )
    export_flows.export([flow], tmp_path)
    record = json.loads((tmp_path / "0000.json").read_text())
    assert record["response"]["headers"] == [["Set-Cookie", "<redacted>"]] * 2


def test_json_body_with_a_bom(tmp_path: Path) -> None:
    body = "\ufeff".encode() + b'{"refresh_token": "rt-s3cr3t"}'
    assert _response_body(tmp_path, body) == {"refresh_token": "<redacted>"}


def test_ndjson_body_scrubbed_line_by_line(tmp_path: Path) -> None:
    body = b'{"refresh_token": "rt-s3cr3t"}\n{"listId": 4711}\n'
    assert _response_body(tmp_path, body, "application/x-ndjson") == [
        {"refresh_token": "<redacted>"},
        {"listId": "<id>"},
    ]


def test_sse_events_scrubbed_with_their_data_as_json(tmp_path: Path) -> None:
    body = (
        b'event: update\ndata: {"refresh_token":\ndata: "rt-s3cr3t"}\n\nid: 7\ndata: plain c0de=1\n'
    )
    out = _response_body(tmp_path, body, "text/event-stream")
    assert out == [
        {"fields": "event: update", "data": {"refresh_token": "<redacted>"}},
        {"fields": "id: <id>", "data": "plain c0de=1"},
    ]
    assert "rt-s3cr3t" not in json.dumps(out)


def test_a_data_line_outside_an_event_stream_keeps_whole_text_masking(tmp_path: Path) -> None:
    html = (
        b"<p>\ndata: shown in the page\n</p>\n"
        b'<input type="text"\n'
        b'       name="code"\n'
        b'       value="c0de-s3cr3t" />\n'
        b'<pre>{\n  "address": {\n    "street": "Hidden Way 1"\n  }\n}</pre>\n'
    )
    out = _response_body(tmp_path, html, "text/html")
    assert isinstance(out, str)
    assert "c0de-s3cr3t" not in out
    assert "Hidden Way" not in out


def test_multipart_body_scrubbed_by_part_name(tmp_path: Path) -> None:
    boundary = "XyZb0undary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="Input.Password"\r\n\r\n'
        "pw-s3cr3t\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    out = _response_body(tmp_path, body, f"multipart/form-data; boundary={boundary}")
    assert out == [["Input.Password", "<redacted>"]]


def test_unparseable_multipart_becomes_binary(tmp_path: Path) -> None:
    body = b"Input.Password=pw-s3cr3t"
    assert _response_body(tmp_path, body, "multipart/form-data") == "<binary>"


def test_known_secrets_are_masked_in_every_spelling(tmp_path: Path) -> None:
    secret = 'pa"ss w@rd/1'
    flow = _flow(
        url=f"https://x.test/a?q={quote(secret, safe='')}",
        response_body=json.dumps({"note": secret}).encode(),
        response_headers=[("X-Echo", secret)],
    )
    export_flows.export([flow], tmp_path, secrets=[secret])
    raw = (tmp_path / "0000.json").read_text()
    for spelling in [secret, quote(secret, safe=""), json.dumps(secret)[1:-1]]:
        assert spelling not in raw


def test_main_asks_for_each_secret_and_writes_none_of_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secrets = ["first-s3cr3t", "second-s3cr3t"]
    asked: list[str] = []
    answers = iter(secrets)

    def fake_getpass(prompt: str = "") -> str:
        asked.append(prompt)
        return next(answers)

    flow = _flow(
        response_headers=[("X-Echo", secrets[0])],
        response_body=json.dumps({"note": f"{secrets[1]} here"}).encode(),
    )
    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    monkeypatch.setattr(export_flows, "_read_flows", lambda path: iter([flow]))
    out_dir = tmp_path / "out"
    argv = [str(tmp_path / "c.flows"), str(out_dir), "--ask-secret", "--ask-secret"]
    assert export_flows.main(argv) == 0
    assert len(asked) == 2
    assert all("s3cr3t" not in prompt for prompt in asked)
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert [p.name for p in written] == ["0000.json"]
    for path in written:
        content = path.read_bytes()
        for secret in secrets:
            assert secret.encode() not in content


def test_main_refuses_a_non_empty_out_dir_before_asking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []

    def fake_getpass(prompt: str = "") -> str:
        asked.append(prompt)
        return "x"

    (tmp_path / "old.json").write_text("{}")
    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    monkeypatch.setattr(export_flows, "_read_flows", lambda path: iter([_flow()]))
    argv = [str(tmp_path / "c.flows"), str(tmp_path), "--ask-secret"]
    assert export_flows.main(argv) == 2
    assert asked == []
    assert _written(tmp_path) == ["old.json"]


def test_known_secret_held_as_a_json_number_is_masked(tmp_path: Path) -> None:
    flow = _flow(response_body=b'{"kundenr": 1234567, "count": 1234567, "other": 7}')
    export_flows.export([flow], tmp_path, secrets=["1234567"])
    record = json.loads((tmp_path / "0000.json").read_text())
    assert record["response"]["body"] == {
        "kundenr": "<redacted>",
        "count": "<redacted>",
        "other": 7,
    }


def test_refuses_a_non_empty_out_dir(tmp_path: Path) -> None:
    (tmp_path / "old.json").write_text("{}")
    with pytest.raises(export_flows.OutDirNotEmptyError):
        export_flows.export([_flow()], tmp_path)
    assert _written(tmp_path) == ["old.json"]
