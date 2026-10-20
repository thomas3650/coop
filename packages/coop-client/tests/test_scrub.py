"""The scrubber: every rule masks the original value, in every spelling it is written.

The fake secrets are assembled at runtime so that no literal in this file has the
shape of a real credential.
"""

import json
from urllib.parse import quote, quote_plus

import pytest
from coop_client.scrub import (
    scrub_form,
    scrub_headers,
    scrub_json,
    scrub_multipart,
    scrub_text,
    scrub_url,
)

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


# The placeholder each key's value becomes, per the redaction list; `<redacted>`
# unless named here.
_PLACEHOLDER_FOR = {"app_installation_id": "<uuid>"}


@pytest.mark.parametrize("key", _MASKED_KEYS)
def test_masks_by_key(key: str) -> None:
    secret = f"v-{key}-s3cr3t"
    out = scrub_json({"outer": [{key: secret, "keep": "visible"}]})
    expected = _PLACEHOLDER_FOR.get(key, "<redacted>")
    assert out == {"outer": [{key: expected, "keep": "visible"}]}
    _assert_absent(json.dumps(out), secret)


def test_app_installation_id_becomes_uuid_in_headers_and_forms() -> None:
    secret = "inst-s3cr3t"
    assert scrub_headers([("App-Installation-Id", secret)]) == [["App-Installation-Id", "<uuid>"]]
    assert scrub_form(f"app_installation_id={secret}") == [["app_installation_id", "<uuid>"]]


def test_list_and_item_names_masked_by_context() -> None:
    value = {
        "member": {"name": "Member Name"},
        "name": "Top Name",
        "lists": [
            {
                "name": "Weekly list",
                "description": "List description",
                "items": [{"name": "Oat milk", "description": "Item note"}],
            }
        ],
        "shoppingList": {"name": "Other list"},
    }
    out = scrub_json(value)
    assert out == {
        "member": "<redacted>",
        "name": "<redacted>",
        "lists": [
            {
                "name": "<list>",
                "description": "<list>",
                "items": [{"name": "<item>", "description": "<item>"}],
            }
        ],
        "shoppingList": {"name": "<list>"},
    }
    flat = json.dumps(out)
    for original in [
        "Member",
        "Top Name",
        "Weekly",
        "List description",
        "Oat",
        "Item note",
        "Other",
    ]:
        assert original not in flat


@pytest.mark.parametrize(
    ("key", "placeholder"),
    [("itemName", "<item>"), ("item_description", "<item>"), ("listName", "<list>")],
)
def test_list_and_item_name_keys(key: str, placeholder: str) -> None:
    assert scrub_json({key: "v-s3cr3t"}) == {key: placeholder}
    assert scrub_form(f"{key}=v-s3cr3t") == [[key, placeholder]]


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
        f"https://login.example.test/connect/authorize?scope=openid&state={quote(secret, safe='')}"
    )
    out = scrub_url(url)
    _assert_absent(out, secret)
    assert out.startswith("https://login.example.test/connect/authorize?")
    assert "scope=openid" in out
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
        "</form>"
    )
    out = scrub_text(html)
    for secret in ["c0de-s3cr3t", "idt-s3cr3t", "ss-s3cr3t"]:
        assert secret not in out


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
        "%3Fresponse_type%3Dcode%26code_challenge%3Dcc-s3cr3t%26state%3Dst-s3cr3t"
        "%26nonce%253Dnn-s3cr3t%26scope%3Dopenid"
    )
    out = scrub_text(url)
    assert "s3cr3t" not in out
    assert "response_type%3Dcode" in out
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
        "Input.Email",
        "phone_number",
        "homeAddress",
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


# Fix round 1: wider key set, more shapes, more carriers.


@pytest.mark.parametrize(
    "key",
    [
        "apikey",
        "api_key",
        "api_key_header",
        "apiKey",
        "clientKey",
        "x-api-key",
        "apimKey",
        "publicKeys",
        "key",
        "X-Unleash-Signature",
        "signatureValue",
        "csrfToken",
    ],
)
def test_masks_api_key_signature_and_token_keys(key: str) -> None:
    secret = "k-s3cr3t"
    assert scrub_json({key: secret}) == {key: "<redacted>"}
    assert scrub_headers([(key, secret)]) == [[key, "<redacted>"]]


def test_key_inside_a_word_is_not_a_key_suffix() -> None:
    assert scrub_json({"keyboard": "visible"}) == {"keyboard": "visible"}


@pytest.mark.parametrize(
    "key",
    [
        "shoppingListId",
        "listItemId",
        "list_item_id",
        "userId",
        "customerId",
        "contactId",
        "customer_ids",
        "sessionId",
        "sessionid",
        "memberId",
        "productIds",
    ],
)
def test_keys_ending_in_id_or_ids_become_id(key: str) -> None:
    out = scrub_json({key: 12345})
    assert out == {key: "<id>"}
    assert scrub_form(f"{key}=12345") == [[key, "<id>"]]


@pytest.mark.parametrize(
    "key",
    [
        "customerNumber",
        "contact_no",
        "userNumber",
        "customer_ids.registered",
        "customer_ids[cookie]",
        "remoteAddress",
        "sub",
    ],
)
def test_masks_member_identifier_keys(key: str) -> None:
    out = scrub_json({key: "m-s3cr3t"})
    assert "m-s3cr3t" not in json.dumps(out)
    assert out[key] in {"<redacted>", "<id>"}  # type: ignore[index]


def test_unleash_context_query_is_masked() -> None:
    url = (
        "https://unleash.example.test/api/frontend?appName=coop&userId=u-s3cr3t"
        "&sessionId=s-s3cr3t&remoteAddress=10.1.2.3&properties%5BcustomerNumber%5D=c-s3cr3t"
    )
    out = scrub_url(url)
    for secret in ["u-s3cr3t", "s-s3cr3t", "10.1.2.3", "c-s3cr3t"]:
        assert secret not in out


@pytest.mark.parametrize(
    "key",
    [
        "navn",
        "Fornavn",
        "efternavn",
        "adresse",
        "vej",
        "vejnavn",
        "postnr",
        "by",
        "postnrBy",
        "post_by",
        "telefon",
        "tlf",
        "mobilNummer",
        "medlemsnummer",
        "medlem",
        "kodeord",
        "nytAdgangskode",
        "fødselsdato",
        "foedselsdato",
        "CPR",
        "cprNr",
    ],
)
def test_masks_danish_personal_data_keys(key: str) -> None:
    assert scrub_json({key: "d-s3cr3t"}) == {key: "<redacted>"}


def test_by_inside_a_word_is_not_the_danish_city_key() -> None:
    assert scrub_json({"sortBy": "x", "standby": "y"}) == {"sortBy": "<redacted>", "standby": "y"}


@pytest.mark.parametrize(
    "key",
    ["cookies", "Proxy-Authorization", "X-Authorization", "oauth_state", "oidc_nonce"],
)
def test_masks_cookie_authorization_state_and_nonce_variants(key: str) -> None:
    assert scrub_headers([(key, "v-s3cr3t")]) == [[key, "<redacted>"]]


def test_masks_a_container_under_a_secret_key_in_json_text() -> None:
    text = '{"address": {"street": "Hidden Way 1", "zip": [1, {"x": "y"}]}, "keep": "ok"}'
    out = scrub_text(text)
    assert "Hidden" not in out
    assert '"keep": "ok"' in out
    assert out == '{"address": "<redacted>", "keep": "ok"}'


def test_masks_a_container_with_brackets_inside_strings() -> None:
    text = '{"member": {"note": "a } tricky ] value", "n": "Hidden"}, "keep": 1}'
    out = scrub_text(text)
    assert "Hidden" not in out
    assert "tricky" not in out
    assert out == '{"member": "<redacted>", "keep": 1}'


def test_recurses_into_stringified_json() -> None:
    inner = json.dumps({"items": [{"name": "Oat milk"}], "listId": 4711})
    out = scrub_json({"payload": inner})
    assert isinstance(out, dict)
    assert json.loads(out["payload"]) == {"items": [{"name": "<item>"}], "listId": "<id>"}


@pytest.mark.parametrize("number", [12345678, 4512345678])
def test_masks_phone_shaped_integers_under_any_key(number: int) -> None:
    assert scrub_json({"count": number}) == {"count": "<redacted>"}


def test_other_integers_survive_under_unknown_keys() -> None:
    assert scrub_json({"count": 3, "ts": 1729425600}) == {"count": 3, "ts": 1729425600}


@pytest.mark.parametrize("number", [3, 1729425600])
def test_masks_any_number_under_a_personal_key(number: int) -> None:
    assert scrub_json({"memberNumber": number}) == {"memberNumber": "<redacted>"}


def test_masks_hex_runs_of_32_or_more() -> None:
    hex_run = "0123456789abcdef" * 2
    out = scrub_text(f"key {hex_run} end")
    assert out == "key <token> end"


def test_masks_base64url_runs_of_32_or_more() -> None:
    run = "Ab9_" * 8
    assert scrub_text(f"x {run} y") == "x <token> y"


def test_masks_apim_key_in_json_and_x_api_key_header() -> None:
    hex_run = "fedcba9876543210" * 2
    assert scrub_json({"apimKey": hex_run}) == {"apimKey": "<redacted>"}
    assert scrub_headers([("x-api-key", hex_run)]) == [["x-api-key", "<redacted>"]]
    assert hex_run not in scrub_text(f"config apim={hex_run};")


@pytest.mark.parametrize("phone", ["4512345678", "12-34-56-78", "12 34 56 78", "+45 1234 5678"])
def test_masks_more_danish_phone_shapes(phone: str) -> None:
    out = scrub_text(f"tel {phone} end")
    assert out == "tel <redacted> end"


@pytest.mark.parametrize("sep", ["%23", "%2F", "%3B", "%2523", "%252F", "%253B"])
def test_masks_keyed_values_after_encoded_separators(sep: str) -> None:
    out = scrub_text(f"https://x.test/cb?r=%2Fa{sep}code%3Dc0de-s3cr3t%26k%3D1")
    assert "c0de-s3cr3t" not in out


def test_masks_unquoted_input_values() -> None:
    html = "<input type=text name=Input.Password value=pw-s3cr3t>"
    assert "pw-s3cr3t" not in scrub_text(html)


@pytest.mark.parametrize("input_type", ["password", "hidden", "PASSWORD"])
def test_masks_value_of_password_and_hidden_inputs_whatever_the_name(input_type: str) -> None:
    html = f'<input type="{input_type}" name="harmless" value="v-s3cr3t" />'
    out = scrub_text(html)
    assert "v-s3cr3t" not in out
    html_unquoted = f"<input type={input_type} name=harmless value=v-s3cr3t>"
    assert "v-s3cr3t" not in scrub_text(html_unquoted)


def test_visible_input_with_harmless_name_keeps_its_value() -> None:
    html = '<input type="text" name="scope" value="openid" />'
    assert scrub_text(html) == html


def test_masks_multipart_parts_by_name() -> None:
    boundary = "XyZb0undary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="Input.Password"\r\n\r\n'
        "pw-s3cr3t\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="scope"\r\n\r\n'
        "openid\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    out = scrub_multipart(body, f"multipart/form-data; boundary={boundary}")
    assert out == [["Input.Password", "<redacted>"], ["scope", "openid"]]


def test_multipart_without_a_boundary_raises() -> None:
    with pytest.raises(ValueError, match="boundary"):
        scrub_multipart(b"garbage", "multipart/form-data")


def test_brackets_in_a_key_do_not_hide_its_suffix() -> None:
    assert scrub_form("listIds[]=4711&listIds%5B%5D=4712") == [
        ["listIds[]", "<id>"],
        ["listIds[]", "<id>"],
    ]


def test_known_secret_matches_a_json_number() -> None:
    assert scrub_json({"count": 1234567, "n": 2}, secrets=["1234567"]) == {
        "count": "<redacted>",
        "n": 2,
    }


def test_multipart_part_that_is_not_utf8_becomes_binary() -> None:
    boundary = "XyZb0undary"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="upload"\r\n\r\n'.encode()
        + b"\xff\xfe\x00raw"
        + f"\r\n--{boundary}--\r\n".encode()
    )
    out = scrub_multipart(body, f"multipart/form-data; boundary={boundary}")
    assert out == [["upload", "<binary>"]]


def test_data_attributes_are_not_the_name_or_type_attribute() -> None:
    html = '<input data-name="code" data-type="hidden" name="scope" type="text" value="openid">'
    assert scrub_text(html) == html


def test_masks_escaped_json_pairs_in_text() -> None:
    text = 'payload={\\"refresh_token\\":\\"rt-s3cr3t\\",\\"keep\\":\\"ok\\"}'
    out = scrub_text(text)
    assert "rt-s3cr3t" not in out
    assert '\\"keep\\":\\"ok\\"' in out


@pytest.mark.parametrize("key", ["kunde", "kundenr", "kundenummer", "kundeNavn"])
def test_masks_danish_customer_keys(key: str) -> None:
    assert scrub_json({key: "k-s3cr3t"}) == {key: "<redacted>"}
