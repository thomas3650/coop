"""The scrubber: masks secrets and personal data in a capture before it is committed.

It masks the redaction list in `docs/api-standard.md` by key wherever a key is
visible (JSON, headers, form bodies, URL queries and fragments, hidden form inputs,
`key=value` text) and by shape everywhere else. Personal data and list content are
masked as `<redacted>`, not as `<list>` or `<item>`. A value under a key outside
its key set (an item's text under `text`, say) is masked only if its shape is
recognised, so the result is still read by hand.
"""

import json
import re
from collections.abc import Callable, Iterable
from urllib.parse import quote, quote_plus, unquote_plus, urlsplit, urlunsplit

REDACTED = "<redacted>"
ID = "<id>"

# Keys masked whole, compared after `_normalise`.
_SECRET_KEYS = frozenset(
    {
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "code",
        "codeverifier",
        "codechallenge",
        "state",
        "nonce",
        "authorization",
        "ocpapimsubscriptionkey",
        "subscriptionkey",
        "appinstallationid",
        "name",
        "description",
        "email",
        "phone",
        "membernumber",
        "address",
        "pwd",
        "onetimecode",
        "cookie",
        "setcookie",
        "xrequestsignature",
        "sub",
    }
)
# A key containing any of these is masked whole, so `newPassword`, `otpCode`,
# `client_secret`, `session_state`, `__RequestVerificationToken`, `given_name`,
# `itemName` and `memberId` are caught without a row each.
_SECRET_KEY_PARTS = (
    "password",
    "otp",
    "session",
    "secret",
    "token",
    "name",
    "email",
    "phone",
    "address",
    "member",
)
# A key ending in this is masked whole: the login form's `Input.Code` and
# `TwoFactorCode`. `code_challenge_method` does not end in it, and stays visible.
_SECRET_KEY_SUFFIX = "code"
# `token_type` holds the scheme name, not a token.
_NOT_SECRET_KEYS = frozenset({"tokentype"})
_ID_KEYS = frozenset({"id", "listid", "itemid"})


def _normalise(key: str) -> str:
    return re.sub(r"[-_.\s]", "", unquote_plus(key)).lower()


def is_id_key(key: str) -> bool:
    """True if `key` names a list or item id."""
    return _normalise(key) in _ID_KEYS


def is_secret_key(key: str) -> bool:
    """True if the value under `key` is masked whole, in any case or separator style."""
    n = _normalise(key)
    if n in _NOT_SECRET_KEYS:
        return False
    return (
        n in _SECRET_KEYS
        or n.endswith(_SECRET_KEY_SUFFIX)
        or any(part in n for part in _SECRET_KEY_PARTS)
    )


def _mask_for(key: str) -> str | None:
    if is_id_key(key):
        return ID
    if is_secret_key(key):
        return REDACTED
    return None


def _spellings(secret: str) -> set[str]:
    """`secret` raw, percent-encoded, form-encoded and as written inside a JSON string."""
    return {
        secret,
        quote(secret, safe=""),
        quote(secret),
        quote_plus(secret),
        json.dumps(secret)[1:-1],
        json.dumps(secret, ensure_ascii=False)[1:-1],
    }


# A JWT or JWE: a base64url header starting `eyJ`, then dot-separated segments, any
# of which may be empty. Without a dot, only when no base64url character precedes
# it, since `eyJ` also occurs inside ordinary words.
_JWT = re.compile(
    r"eyJ[A-Za-z0-9_-]{5,}(?:\.[A-Za-z0-9_-]*)+|(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}"
)
_BEARER = re.compile(r"\b(Bearer)\s+[^\s\"',;&]+", re.IGNORECASE)
_SESSION_COOKIE = re.compile(r"((?:idsrv|\.AspNetCore\.)[^=;\s]*=)[^;\s\"']+", re.IGNORECASE)
_INPUT_TAG = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_ATTR_NAME = re.compile(r"\bname\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
_ATTR_VALUE = re.compile(r"(\bvalue\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)
# `"key": value` in JSON text: a string (escapes included) or a bare scalar.
_JSON_PAIR = re.compile(
    r"([\"'])([^\"'\\]{1,100})\1(\s*:\s*)(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|[^,}\]\s]+)"
)
# `key%3Dvalue` inside a percent-encoded URL (an IdentityServer `ReturnUrl`), single
# or double encoded. The key starts after an encoded `?` or `&`, or after no key
# character; the value stops at the encoded `&`.
_ENCODED_PAIR = re.compile(
    r"(?:(?<=%3F)|(?<=%26)|(?<=%253F)|(?<=%2526)|(?<![A-Za-z0-9_.%-]))"
    r"([A-Za-z0-9_.-]+)(%3D|%253D)((?:(?!%26|%2526)[^&\s\"'<>#])+)",
    re.IGNORECASE,
)
# `key=value` in a query, a fragment, a form body or a cookie.
_PLAIN_PAIR = re.compile(r"(?<![A-Za-z0-9_.%-])([A-Za-z0-9_.-]+)(=)([^&\s;\"'<>#]+)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+(?:@|%40)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_LONG_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}=*")
# A Danish phone number: eight digits, run together or in pairs, with or without the
# country code. Not inside a longer digit run, so timestamps and EANs survive.
_PHONE = re.compile(r"(?<![\d+])(?:(?:\+|00)45\s?)?(?:\d{8}|\d{2}(?: \d{2}){3})(?!\d)")


def _mask_input_tag(match: re.Match[str]) -> str:
    tag = match.group(0)
    name = _ATTR_NAME.search(tag)
    if name is None or _mask_for(name.group(2)) is None:
        return tag
    return _ATTR_VALUE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}{m.group(2)}", tag)


def _mask_json_pair(match: re.Match[str]) -> str:
    quote_char, key, colon, _value = match.groups()
    mask = _mask_for(key)
    if mask is None:
        return match.group(0)
    return f'{quote_char}{key}{quote_char}{colon}"{mask}"'


def _pair_masker(match: re.Match[str]) -> str:
    key, sep, _value = match.groups()
    mask = _mask_for(key)
    if mask is None:
        return match.group(0)
    return f"{key}{sep}{mask}"


_RULES: list[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]] = [
    (_JWT, "<JWT>"),
    (_BEARER, r"\1 <token>"),
    (_SESSION_COOKIE, r"\1" + REDACTED),
    (_INPUT_TAG, _mask_input_tag),
    (_JSON_PAIR, _mask_json_pair),
    (_ENCODED_PAIR, _pair_masker),
    (_PLAIN_PAIR, _pair_masker),
    (_EMAIL, REDACTED),
    (_UUID, "<uuid>"),
    # After the JWT and UUID rules, so a JWT reads `<JWT>`, not three `<token>`s.
    (_LONG_TOKEN, "<token>"),
    # After the long-token rule, so digits inside a token do not split it.
    (_PHONE, REDACTED),
]


def scrub_text(text: str, secrets: Iterable[str] = ()) -> str:
    """Mask every known secret in `text` in each of its spellings, then every shape
    and keyed value the rules recognise."""
    spellings = {s for secret in secrets if secret for s in _spellings(secret)}
    # Longest first, so a secret that contains another is masked whole.
    for spelling in sorted(spellings, key=len, reverse=True):
        text = text.replace(spelling, REDACTED)
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text


def scrub_json(value: object, *, secrets: Iterable[str] = ()) -> object:
    """Mask a parsed JSON value: by key, recursively, and every other string by
    `scrub_text`. A masked key's value is replaced whole, container or not."""
    secrets = tuple(secrets)
    if isinstance(value, dict):
        out: dict[object, object] = {}
        for key, item in value.items():
            mask = _mask_for(key) if isinstance(key, str) else None
            scrubbed_key = scrub_text(key, secrets) if isinstance(key, str) else key
            out[scrubbed_key] = mask if mask is not None else scrub_json(item, secrets=secrets)
        return out
    if isinstance(value, list):
        return [scrub_json(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        return scrub_text(value, secrets)
    return value


def _scrub_pairs(encoded: str, secrets: tuple[str, ...]) -> str:
    """Mask a `k=v&k=v` string by key, keeping the encoding of what survives."""
    parts = []
    for part in encoded.split("&"):
        key, sep, value = part.partition("=")
        mask = _mask_for(key)
        if mask is not None:
            parts.append(f"{key}{sep}{mask}" if sep else key)
        else:
            parts.append(f"{scrub_text(key, secrets)}{sep}{scrub_text(value, secrets)}")
    return "&".join(parts)


def _mask_path_ids(path: str) -> str:
    """A path with every all-digit segment, a list or item id, as `<id>`."""
    return "/".join(ID if segment.isdigit() else segment for segment in path.split("/"))


def scrub_url(url: str, secrets: Iterable[str] = ()) -> str:
    """Mask a URL: all-digit path segments as `<id>`, its query and fragment by key,
    and all of it by `scrub_text`."""
    secrets = tuple(secrets)
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            scrub_text(parts.netloc, secrets),
            scrub_text(_mask_path_ids(parts.path), secrets),
            _scrub_pairs(parts.query, secrets) if parts.query else "",
            _scrub_pairs(parts.fragment, secrets) if parts.fragment else "",
        )
    )


def scrub_form(body: str, secrets: Iterable[str] = ()) -> list[list[str]]:
    """Decode an `application/x-www-form-urlencoded` body into `[key, value]` pairs,
    masked by key and by `scrub_text`."""
    secrets = tuple(secrets)
    pairs: list[list[str]] = []
    for part in body.split("&"):
        if not part:
            continue
        raw_key, _, raw_value = part.partition("=")
        key, value = unquote_plus(raw_key), unquote_plus(raw_value)
        mask = _mask_for(key)
        pairs.append(
            [
                scrub_text(key, secrets),
                mask if mask is not None else scrub_text(value, secrets),
            ]
        )
    return pairs


def scrub_headers(
    headers: Iterable[tuple[str, str]], secrets: Iterable[str] = ()
) -> list[list[str]]:
    """Mask headers as `[name, value]` pairs, keeping repeats such as `Set-Cookie`.

    A header named in the key set is masked whole. A value holding a URL (`Location`,
    `Referer`) is masked as a URL, so an authorization code in its query is caught.
    """
    secrets = tuple(secrets)
    out: list[list[str]] = []
    for name, value in headers:
        if _mask_for(name) is not None:
            out.append([name, REDACTED])
        elif "://" in value or value.startswith("/"):
            out.append([name, scrub_url(value, secrets)])
        else:
            out.append([name, scrub_text(value, secrets)])
    return out
