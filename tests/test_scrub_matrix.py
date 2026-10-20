"""The scrubber and the flow export, generated: every secret key, in every carrier, with
every awkward value, comes out masked.

Each case plants a distinct value under one secret key, writes it into one carrier
with the encoder that carrier really uses, and runs it through three paths:

- `export`: the flow export, with the carrier's own content type;
- `mislabelled`: the flow export, with the body sent as `text/plain`, so it reaches
  `scrub_text` the way a body with a wrong content type does;
- `text`: `scrub_text` on the carrier's raw text.

Neither the value, in any of its spellings, nor the fragments before and after its
awkward characters may appear in the output. A neighbouring value under `keep`
survives, so masking everything does not pass. The shape cases plant a value under
a key outside the key set and expect the shape rule's placeholder.

The values are assembled at runtime so that no literal in this file has the shape of
a real credential.
"""

import html
import json
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote, quote_plus, urlencode

import export_flows
import pytest
from coop_client.scrub import scrub_text

KEYS = [
    "password",
    "refresh_token",
    "code",
    "Ocp-Apim-Subscription-Key",
    "idsrv.session",
    "adgangskode",
]
KEEP = "kpvisible"


@dataclass(frozen=True)
class Kind:
    """An awkward value, and how a JSON writer spells it."""

    special: str
    ascii_only: bool = True
    slash_escaped: bool = False
    trailing: bool = False


KINDS = {
    "ascii": Kind("Qz7"),
    "space": Kind("a b"),
    "quote": Kind('a"b'),
    "backslash": Kind("a\\b"),
    "trailing_backslash": Kind("\\", trailing=True),
    "newline": Kind("a\nb"),
    "danish": Kind("æøå", ascii_only=False),
    "danish_escaped": Kind("æøå"),
    "slash": Kind("a/b"),
    "slash_escaped": Kind("a/b", slash_escaped=True),
}


@dataclass(frozen=True)
class Planted:
    key: str
    value: str
    fragments: tuple[str, ...]
    kind: Kind


def _planted(key: str, kind_name: str) -> Planted:
    """A value unique to `key` and `kind_name`, with short alphanumeric fragments that
    no shape rule masks, around the awkward characters."""
    k = KEYS.index(key)
    v = list(KINDS).index(kind_name)
    kind = KINDS[kind_name]
    head, tail = f"hd{k}k{v}h", f"tl{k}k{v}t"
    value = head + tail + kind.special if kind.trailing else head + kind.special + tail
    return Planted(key, value, (head, tail), kind)


def _spellings(value: str) -> set[str]:
    return {
        value,
        json.dumps(value)[1:-1],
        json.dumps(value, ensure_ascii=False)[1:-1],
        quote(value, safe=""),
        quote(value),
        quote_plus(value),
        html.escape(value),
    }


def _dumps(obj: object, kind: Kind, indent: int | None = None) -> str:
    text = json.dumps(obj, ensure_ascii=kind.ascii_only, indent=indent)
    return text.replace("/", "\\/") if kind.slash_escaped else text


def _js_single(value: str) -> str:
    """`value` as a JavaScript single-quoted string literal."""
    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{escaped}'"


# A JSON payload holding the planted value under its key: as a string, inside an
# object, inside an array, and after a neighbour.
PAYLOADS: dict[str, Callable[[str, object], dict[str, object]]] = {
    "pair": lambda key, value: {key: value, "keep": KEEP},
    "pair_last": lambda key, value: {"keep": KEEP, key: value},
    "object": lambda key, value: {key: {"v": value}, "keep": KEEP},
    "array": lambda key, value: {key: [value], "keep": KEEP},
}


def _in_string(
    depth: int, prefix: str, indent: int | None = None
) -> Callable[[dict[str, object], Kind], str]:
    """A payload's JSON text held inside a JSON string, `depth` levels down, each level
    written as `{"payload": "<prefix><inner>"}`."""

    def carry(payload: dict[str, object], kind: Kind) -> str:
        text = _dumps(payload, kind, indent)
        for _ in range(depth):
            text = _dumps({"payload": prefix + text}, kind)
        return text

    return carry


# JSON carriers: (content type, how the payload's JSON text is carried).
JSON_CARRIERS: dict[str, tuple[str, Callable[[dict[str, object], Kind], str]]] = {
    "json": ("application/json", _in_string(0, "")),
    "json_pretty": ("application/json", _in_string(0, "", indent=2)),
    "json_truncated": ("application/json", lambda p, k: _dumps(p, k)[:-1]),
    **{f"json_in_json_d{d}": ("application/json", _in_string(d, "")) for d in (1, 2, 3)},
    **{f"json_in_text_d{d}": ("application/json", _in_string(d, "req ")) for d in (1, 2, 3)},
    "json_pretty_in_text_d1": ("application/json", _in_string(1, "req ", indent=2)),
    "json_in_script": (
        "text/html",
        lambda p, k: f"<script>var cfg = {_dumps(p, k)};</script>",
    ),
    "sse": ("text/event-stream", lambda p, k: f"event: token\ndata: {_dumps(p, k)}\n\n"),
    "sse_pretty": (
        "text/event-stream",
        lambda p, k: (
            "event: token\n"
            + "".join(f"data: {line}\n" for line in _dumps(p, k, indent=2).splitlines())
            + "\n"
        ),
    ),
}


def _html_inputs(p: Planted) -> dict[str, str]:
    """`<input>` carriers, the value escaped as HTML escapes an attribute."""
    key, esc = p.key, html.escape(p.value)
    keep = f'<input type="text" name="keep" value="{KEEP}">'
    inputs = {
        "html_hidden": f'<input type="hidden" name="{key}" value="{esc}" />',
        "html_password_single": f"<input type='password' name='{key}' value='{esc}'>",
        "html_text_named": f'<input type="text" name="{key}" value="{esc}">',
        "html_value_first": f'<input value="{esc}" name="{key}" type="text">',
        "html_multiline": f'<input\n  type="text"\n  name="{key}"\n  value="{esc}"\n/>',
        "html_data_value": f'<input type="text" name="{key}" data-value="{esc}">',
        "html_decoy_attribute": f'<input type="text" name="{key}" title="x value=" value="{esc}">',
        "html_gt_in_value": f'<input type="text" name="{key}" value="a>{esc}">',
        "html_hidden_neutral_name": f'<input type="hidden" name="field" value="{esc}">',
        "html_password_neutral_name": f'<input type="PASSWORD" name="field" value="{esc}">',
    }
    if not any(c in p.value for c in " \n"):
        inputs["html_unquoted"] = f"<input type=text name={key} value={esc}>"
    return {name: f"<form>{tag}{keep}</form>" for name, tag in inputs.items()}


def _multipart(p: Planted) -> str:
    """A `multipart/form-data` body as a browser writes it."""
    return (
        f'--bnd\r\nContent-Disposition: form-data; name="{p.key}"\r\n\r\n{p.value}\r\n'
        f'--bnd\r\nContent-Disposition: form-data; name="keep"\r\n\r\n{KEEP}\r\n'
        "--bnd--\r\n"
    )


def _body_carriers(p: Planted) -> dict[str, tuple[str, str]]:
    """Every body carrier for `p`: name -> (content type, body text)."""
    carriers: dict[str, tuple[str, str]] = {}
    for payload_name, payload in PAYLOADS.items():
        for name, (content_type, carry) in JSON_CARRIERS.items():
            carriers[f"{name}/{payload_name}"] = (
                content_type,
                carry(payload(p.key, p.value), p.kind),
            )
    carriers["js_single_quoted"] = (
        "application/javascript",
        f"var cfg = {{'{p.key}': {_js_single(p.value)}, 'keep': '{KEEP}'}};",
    )
    form = urlencode({p.key: p.value, "keep": KEEP})
    carriers["form"] = ("application/x-www-form-urlencoded", form)
    carriers["multipart"] = ("multipart/form-data; boundary=bnd", _multipart(p))
    carriers.update({name: ("text/html", text) for name, text in _html_inputs(p).items()})
    return carriers


def _url_carriers(p: Planted) -> dict[str, str]:
    pairs = urlencode({p.key: p.value, "keep": KEEP})
    inner = f"/connect/authorize/callback?{pairs}"
    return {
        "query": f"https://login.example.test/connect/authorize?{pairs}",
        "fragment": f"https://app.example.test/cb#{pairs}",
        "return_url": f"https://login.example.test/Account/Login?ReturnUrl={quote(inner, safe='')}",
        "return_url_double": (
            "https://login.example.test/Account/Login?ReturnUrl="
            + quote(quote(inner, safe=""), safe="")
        ),
    }


class _Headers:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = pairs

    def items(self, multi: bool = False) -> list[tuple[str, str]]:
        return self._pairs


def _message(headers: list[tuple[str, str]], body: bytes | None) -> SimpleNamespace:
    return SimpleNamespace(headers=_Headers(headers), get_content=lambda strict=True: body)


def _export(
    *,
    url: str = "https://api.example.test/x",
    request_headers: list[tuple[str, str]] | None = None,
    body: bytes | None = None,
    response_headers: list[tuple[str, str]] | None = None,
) -> str:
    """The flow export's record of one flow, as the JSON file it writes."""
    request = _message(request_headers or [], body)
    request.method, request.pretty_url = "POST", url
    flow: Any = SimpleNamespace(
        request=request,
        response=SimpleNamespace(status_code=200, **vars(_message(response_headers or [], None))),
    )
    return json.dumps(export_flows.record_from_flow(flow), indent=2, ensure_ascii=False)


def _outputs_for_body(content_type: str, text: str) -> dict[str, str]:
    body = text.encode()
    return {
        "export": _export(request_headers=[("Content-Type", content_type)], body=body),
        "mislabelled": _export(request_headers=[("Content-Type", "text/plain")], body=body),
        "text": scrub_text(text),
    }


def _outputs_for_url(url: str) -> dict[str, str]:
    return {
        "export": _export(url=url),
        "location": _export(response_headers=[("Location", url)]),
        "text": scrub_text(url),
    }


def _leaks(output: str, p: Planted) -> list[str]:
    found = [s for s in sorted(_spellings(p.value)) if s in output]
    found += [f for f in p.fragments if f in output]
    if KEEP not in output:
        found.append(f"<{KEEP} lost>")
    return found


def _cases(p: Planted) -> dict[str, dict[str, str]]:
    cases = {name: _outputs_for_body(*carrier) for name, carrier in _body_carriers(p).items()}
    cases.update({name: _outputs_for_url(url) for name, url in _url_carriers(p).items()})
    if "\n" not in p.value:
        cookie = f"{p.key}={quote(p.value, safe='')}; keep={KEEP}"
        cases["header"] = {
            "export": _export(request_headers=[(p.key, p.value), ("X-Keep", KEEP)]),
            "cookie": _export(request_headers=[("Cookie", cookie), ("X-Keep", KEEP)]),
            "set_cookie": _export(
                response_headers=[("Set-Cookie", f"{cookie}; path=/"), ("X-Keep", KEEP)]
            ),
            "cookie_as_text": scrub_text(cookie),
        }
    return cases


@pytest.mark.parametrize("kind_name", list(KINDS))
@pytest.mark.parametrize("key", KEYS)
def test_secret_key_masked_in_every_carrier(key: str, kind_name: str) -> None:
    p = _planted(key, kind_name)
    failures = {
        f"{carrier} via {path}": leaked
        for carrier, outputs in _cases(p).items()
        for path, output in outputs.items()
        if (leaked := _leaks(output, p))
    }
    assert failures == {}


@dataclass(frozen=True)
class Shape:
    """A value masked by its shape; `secret` is the part that must not survive, and
    none of `fragments` either."""

    value: str
    placeholder: str
    secret: str = ""
    fragments: tuple[str, ...] = ()


def _jwt() -> str:
    return "eyJ" + "hbGciOiJSUzI1NiJ9" + "." + "eyJ" + "zdWIiOiJ4In0" + "." + "c2ln" * 9


SHAPES = {
    "jwt": Shape(_jwt(), "<JWT>"),
    "bearer": Shape("Bearer " + "br7+tok/x=", "Bearer <token>", "br7+tok/x=", ("br7", "tok/x")),
    "idsrv_cookie": Shape("idsrv=" + "ck7val", "<redacted>", "ck7val"),
    "aspnetcore_cookie": Shape(
        ".AspNetCore.Identity.Application=" + "ck8val",
        "<redacted>",
        "ck8val",
    ),
    "email": Shape("some.one" + "@example.test", "<redacted>"),
    "uuid": Shape("123e4567-e89b-12d3-a456-" + "426614174000", "<uuid>"),
    "long_token": Shape("Ab9_" * 10 + "-x", "<token>"),
    "phone": Shape("12 34 " + "56 78", "<redacted>"),
}


@pytest.mark.parametrize("shape_name", list(SHAPES))
def test_shape_masked_under_an_unknown_key_in_every_carrier(shape_name: str) -> None:
    shape = SHAPES[shape_name]
    secret = shape.secret or shape.value
    kind = KINDS["ascii"]
    payload: dict[str, object] = {"note": shape.value, "keep": KEEP}
    bodies = {
        name: (content_type, carry(payload, kind))
        for name, (content_type, carry) in JSON_CARRIERS.items()
    }
    bodies["form"] = ("application/x-www-form-urlencoded", urlencode(payload))
    bodies["text"] = ("text/plain", f"note: {shape.value}\nkeep: {KEEP}\n")
    bodies["html_text_input"] = (
        "text/html",
        (
            f'<input type="text" name="note" value="{html.escape(shape.value)}">'
            f'<input type="text" name="keep" value="{KEEP}">'
        ),
    )
    cases = {name: _outputs_for_body(*carrier) for name, carrier in bodies.items()}
    cases["query"] = _outputs_for_url(f"https://api.example.test/x?{urlencode(payload)}")
    failures = {
        f"{carrier} via {path}": output
        for carrier, outputs in cases.items()
        for path, output in outputs.items()
        if any(s in output for s in {*_spellings(secret), *shape.fragments}) or KEEP not in output
    }
    assert sorted(failures) == []
    missing_placeholder = sorted(
        f"{carrier} via {path}"
        for carrier, outputs in cases.items()
        for path, output in outputs.items()
        if shape.placeholder not in output
    )
    assert missing_placeholder == []


@pytest.mark.parametrize("number", [12345678, 4512345678])
def test_phone_number_held_as_a_json_number_masked(number: int) -> None:
    body = json.dumps({"note": number, "keep": KEEP})
    out = _export(request_headers=[("Content-Type", "application/json")], body=body.encode())
    assert str(number) not in out
    assert KEEP in out
