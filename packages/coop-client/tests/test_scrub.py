"""The scrubber: every rule masks the original value, in every spelling it is written.

The fake secrets are assembled at runtime so that no literal in this file has the
shape of a real credential.
"""

import json
from urllib.parse import quote, quote_plus

import pytest
from coop_client.scrub import scrub_form, scrub_headers, scrub_json, scrub_text, scrub_url

_JWT = "eyJ" + "hbGciOiJSUzI1NiJ9" + "." + "eyJ" + "zdWIiOiJ4In0" + "." + "c2lnbmF0dXJl" * 3
_LONG = ("Ab9_" * 10) + "-x"


def _assert_absent(output: str, secret: str) -> None:
    for spelling in {secret, quote(secret, safe=""), quote(secret), quote_plus(secret)}:
        assert spelling not in output


_MASKED_KEYS = [
    "access_token",
    "refresh_token",
    "id_token",
    "code",
    "code_verifier",
    "code_challenge",
    "state",
    "nonce",
    "Authorization",
    "Ocp-Apim-Subscription-Key",
    "subscriptionKey",
    "app_installation_id",
    "name",
    "description",
    "email",
    "phone",
    "memberNumber",
    "address",
]


@pytest.mark.parametrize("key", _MASKED_KEYS)
def test_masks_by_key(key: str) -> None:
    secret = f"v-{key}-s3cr3t"
    out = scrub_json({"outer": [{key: secret, "keep": "visible"}]})
    assert out == {"outer": [{key: "<redacted>", "keep": "visible"}]}
    _assert_absent(json.dumps(out), secret)


@pytest.mark.parametrize("key", ["ACCESS_TOKEN", "accessToken", "Refresh-Token"])
def test_masks_by_key_in_any_case_and_separator(key: str) -> None:
    out = scrub_json({key: "v-s3cr3t"})
    assert out == {key: "<redacted>"}


def test_masks_a_keyed_container_whole() -> None:
    out = scrub_json({"address": {"street": "Hidden Way 1", "city": "Town"}})
    assert out == {"address": "<redacted>"}
    assert "Hidden Way" not in json.dumps(out)


def test_masks_jwt() -> None:
    out = scrub_text(f"token is {_JWT} here")
    assert out == "token is <JWT> here"
    _assert_absent(out, _JWT)


def test_masks_jwt_under_an_unknown_json_key() -> None:
    out = scrub_json({"whatever": {"nested": [f"x {_JWT}"]}})
    assert out == {"whatever": {"nested": ["x <JWT>"]}}


def test_masks_email_and_danish_phone() -> None:
    email = "some.one+tag@example.dk"
    for phone in ["12345678", "+4512345678", "+45 12 34 56 78", "12 34 56 78"]:
        out = scrub_text(f"mail {email} call {phone}.")
        _assert_absent(out, email)
        _assert_absent(out, phone)
        assert "12" not in out.replace("<redacted>", "")


def test_phone_rule_leaves_longer_digit_runs() -> None:
    assert scrub_text("ts 1729425600 ean 5701234567890") == "ts 1729425600 ean 5701234567890"


def test_masks_known_secret_anywhere() -> None:
    secret = "pa ss/w@rd+1"
    for url in [
        f"https://example.test/cb?x={quote(secret, safe='')}&y=1",
        f"https://example.test/cb?x={quote_plus(secret)}&y=1",
        f"https://example.test/cb?x={secret}&y=1",
    ]:
        out = scrub_text(url, secrets=[secret])
        _assert_absent(out, secret)
        assert out.endswith("&y=1")


def test_unknown_long_token_is_masked() -> None:
    out = scrub_text(f"opaque {_LONG} end")
    assert out == "opaque <token> end"


def test_short_slugs_survive_the_long_token_rule() -> None:
    assert scrub_text("shopping-list-v2") == "shopping-list-v2"


@pytest.mark.parametrize("key", ["id", "listId", "itemId"])
def test_list_and_item_ids_masked(key: str) -> None:
    out = scrub_json({"items": [{key: 4711, "ok": True}]})
    assert out == {"items": [{key: "<id>", "ok": True}]}
    assert "4711" not in json.dumps(out)


@pytest.mark.parametrize(
    "key",
    ["password", "Password", "pwd", "otp", "one_time_code", "newPassword", "otpCode"],
)
def test_masks_password_and_one_time_code_keys(key: str) -> None:
    out = scrub_json({key: "hunter2-s3cr3t"})
    assert out == {key: "<redacted>"}


@pytest.mark.parametrize(
    "key",
    [
        "Cookie",
        "Set-Cookie",
        "client_secret",
        "session",
        "sessionid",
        "session_state",
        "__RequestVerificationToken",
    ],
)
def test_masks_cookie_secret_and_session_keys(key: str) -> None:
    out = scrub_json({key: "v-s3cr3t"})
    assert out == {key: "<redacted>"}


def test_masks_request_signature_header() -> None:
    out = scrub_headers([("X-Request-Signature", "sig-s3cr3t"), ("Accept", "*/*")])
    assert out == [["X-Request-Signature", "<redacted>"], ["Accept", "*/*"]]


def test_masks_every_set_cookie_header() -> None:
    headers = [
        ("Set-Cookie", "idsrv.session=abc123s3cr3t; path=/; secure"),
        ("set-cookie", ".AspNetCore.Identity.Application=def456s3cr3t; path=/"),
        ("Content-Type", "text/html"),
    ]
    out = scrub_headers(headers)
    assert out == [
        ["Set-Cookie", "<redacted>"],
        ["set-cookie", "<redacted>"],
        ["Content-Type", "text/html"],
    ]


def test_masks_idsrv_and_aspnetcore_cookie_values_in_text() -> None:
    text = "idsrv.session=abc123s3cr3t; .AspNetCore.Antiforgery.x1=def456s3cr3t; keep=1"
    out = scrub_text(text)
    assert "abc123s3cr3t" not in out
    assert "def456s3cr3t" not in out
    assert "keep=1" in out


def test_masks_bearer_value() -> None:
    out = scrub_text("Authorization: Bearer opaque.s3cr3t-value")
    assert out == "Authorization: Bearer <token>"


def test_masks_bearer_value_inside_json_text() -> None:
    out = scrub_text('{"h": "Bearer abc.s3cr3t", "k": 1}')
    assert out == '{"h": "Bearer <token>", "k": 1}'


def test_masks_form_body_by_key() -> None:
    secret_code = "c0de/s3cr3t+@"
    secret_pw = "pw s3cr3t@"
    body = (
        f"grant_type=authorization_code&code={quote_plus(secret_code)}"
        f"&Password={quote_plus(secret_pw)}&redirect_uri=coop%3A%2F%2Fcb"
    )
    out = scrub_form(body)
    assert out == [
        ["grant_type", "authorization_code"],
        ["code", "<redacted>"],
        ["Password", "<redacted>"],
        ["redirect_uri", "coop://cb"],
    ]
    _assert_absent(json.dumps(out), secret_code)
    _assert_absent(json.dumps(out), secret_pw)


def test_masks_url_query_by_key() -> None:
    secret = "st@te/s3cr3t"
    url = (
        f"https://login.example.test/connect/authorize?client_id=app&state={quote(secret, safe='')}"
    )
    out = scrub_url(url)
    _assert_absent(out, secret)
    assert out.startswith("https://login.example.test/connect/authorize?")
    assert "client_id=app" in out
    assert "state=" in out


def test_masks_url_fragment_by_key() -> None:
    secret = "c0de-s3cr3t"
    out = scrub_url(f"coop://callback#code={secret}&session_state=xyz-s3cr3t")
    _assert_absent(out, secret)
    assert "xyz-s3cr3t" not in out
    assert out.startswith("coop://callback#")


def test_masks_location_and_referer_header_queries() -> None:
    secret = "c0de-s3cr3t"
    out = scrub_headers(
        [
            ("Location", f"coop://callback?code={secret}&state=st-s3cr3t"),
            ("Referer", f"https://login.example.test/x?code={secret}"),
        ]
    )
    flat = json.dumps(out)
    _assert_absent(flat, secret)
    assert "st-s3cr3t" not in flat
    assert out[0][0] == "Location"


def test_masks_form_post_hidden_inputs_in_html() -> None:
    html = (
        '<form method="post" action="coop://cb">'
        '<input type="hidden" name="code" value="c0de-s3cr3t" />'
        "<input type='hidden' name='id_token' value='idt-s3cr3t'/>"
        '<input type="hidden" value="ss-s3cr3t" name="session_state" />'
        '<input type="hidden" name="scope" value="openid" />'
        "</form>"
    )
    out = scrub_text(html)
    for secret in ["c0de-s3cr3t", "idt-s3cr3t", "ss-s3cr3t"]:
        assert secret not in out
    assert 'value="openid"' in out


def test_masks_keyed_values_in_json_text_and_form_text() -> None:
    text = '{"refresh_token": "rt s3cr3t", "x": 1} and password=pw-s3cr3t&ok=1'
    out = scrub_text(text)
    assert "rt s3cr3t" not in out
    assert "s3cr3t" not in out
    assert "ok=1" in out


def test_masks_uuid() -> None:
    uuid = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
    out = scrub_text(f"/installations/{uuid}/x")
    assert out == "/installations/<uuid>/x"


def test_masks_keyed_values_inside_a_percent_encoded_return_url() -> None:
    url = (
        "https://login.example.test/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize"
        "%3Fclient_id%3Dapp%26code_challenge%3Dcc-s3cr3t%26state%3Dst-s3cr3t"
        "%26nonce%253Dnn-s3cr3t%26scope%3Dopenid"
    )
    out = scrub_text(url)
    assert "s3cr3t" not in out
    assert "client_id%3Dapp" in out
    assert "scope%3Dopenid" in out


@pytest.mark.parametrize(
    "key", ["Input.Code", "TwoFactorCode", "RecoveryCode", "VerificationCode", "postalCode"]
)
def test_masks_keys_ending_in_code(key: str) -> None:
    out = scrub_form(f"{key}=135790&keep=1")
    assert out == [[key, "<redacted>"], ["keep", "1"]]


def test_code_challenge_method_stays_visible() -> None:
    assert scrub_json({"code_challenge_method": "S256"}) == {"code_challenge_method": "S256"}


@pytest.mark.parametrize(
    "key",
    [
        "given_name",
        "family_name",
        "itemName",
        "Input.Email",
        "phone_number",
        "homeAddress",
        "memberId",
        "member",
    ],
)
def test_masks_keys_containing_personal_data_parts(key: str) -> None:
    out = scrub_json({key: "v-s3cr3t"})
    assert out == {key: "<redacted>"}


def test_masks_subject_claim() -> None:
    assert scrub_json({"sub": "v-s3cr3t"}) == {"sub": "<redacted>"}


def test_masks_numeric_path_segments_as_ids() -> None:
    out = scrub_url("https://api.example.test/lists/12345678/items/42?x=1")
    assert out == "https://api.example.test/lists/<id>/items/<id>?x=1"


def test_masks_numeric_path_segments_in_location_header() -> None:
    out = scrub_headers([("Location", "/lists/4711/items/12")])
    assert out == [["Location", "/lists/<id>/items/<id>"]]
