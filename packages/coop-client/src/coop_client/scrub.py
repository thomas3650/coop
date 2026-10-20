"""The scrubber: masks secrets and personal data in a capture before it is committed.

By key, where a key is visible: parsed JSON (and JSON held in a string), headers,
`application/x-www-form-urlencoded` and `multipart/form-data` bodies, URL queries
and fragments, `key%3Dvalue` pairs inside an encoded URL, `"key": value` and
`key=value` in text, and `<input>` values. By shape only, everywhere else: a JWT, a
bearer value, `idsrv*` and `.AspNetCore.*` cookie values, an email address, a
Danish phone number, a UUID, a run of 32 or more base64url characters, and any
secret the caller passes in. A value under a key outside the key set, in a shape
none of these match, comes through unmasked; the result is still read by hand.
"""

import json
import re
from collections.abc import Callable, Iterable
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from urllib.parse import quote, quote_plus, unquote_plus, urlsplit, urlunsplit

REDACTED = "<redacted>"
ID = "<id>"
UUID = "<uuid>"
LIST = "<list>"
ITEM = "<item>"
BINARY = "<binary>"

# Keys masked whole, compared after `_normalise`; the parts and suffixes below
# catch the rest of the redaction list.
_SECRET_KEYS = frozenset({"codeverifier", "codechallenge", "description", "pwd", "sub"})
# A key containing any of these is masked whole, so `newPassword`, `otpCode`,
# `client_secret`, `session_state`, `csrfToken`, `X-Unleash-Signature`, `api_key`,
# `Proxy-Authorization`, `cookies`, `given_name`, `fornavn` and `cprNr` are caught
# without a row each.
_SECRET_KEY_PARTS = (
    "password",
    "otp",
    "session",
    "secret",
    "token",
    "signature",
    "apikey",
    "authorization",
    "cookie",
    "name",
    "email",
    "phone",
    "address",
    "member",
    # Danish: name, address, street, postcode, phone, mobile, member, password,
    # date of birth, civil registration number, customer.
    "navn",
    "adresse",
    "vej",
    "postnr",
    "telefon",
    "tlf",
    "mobil",
    "medlem",
    "kodeord",
    "adgangskode",
    "fødselsdato",
    "foedselsdato",
    "cpr",
    "kunde",
)
# A key ending in any of these is masked whole: the login form's `Input.Code` and
# `TwoFactorCode`, `apiKey`, `clientKey`, `oauth_state`, `oidc_nonce`.
# `code_challenge_method` and `keyboard` do not end in one, and stay visible.
_SECRET_KEY_SUFFIXES = ("code", "key", "keys", "state", "nonce")
# A key with one of these as a whole word is masked: `by` (Danish: town) in `by`,
# `postnrBy` and `post_by`, not inside `standby`.
_SECRET_KEY_WORDS = frozenset({"by"})
# A key with one of the first parts and one of the second is a member identifier:
# `customerNumber`, `contact_no`, `customer_ids.registered`.
_MEMBER_PARTS = ("customer", "contact", "user")
_MEMBER_ID_PARTS = ("id", "number", "no")
# `token_type` holds the scheme name, not a token.
_NOT_SECRET_KEYS = frozenset({"tokentype"})
# A key ending in one of these holds an id: `listId`, `shoppingListId`, `customer_ids`.
_ID_SUFFIXES = ("id", "ids")


def _normalise(key: str) -> str:
    return re.sub(r"[-_.\s\[\]]", "", unquote_plus(key)).lower()


def _words(key: str) -> list[str]:
    """`key` split at separators and at a lower-to-upper case change, lower-cased."""
    spaced = re.sub(r"(?<=[a-zæøå0-9])(?=[A-ZÆØÅ])", " ", unquote_plus(key))
    return [w.lower() for w in re.split(r"[^A-Za-z0-9æøåÆØÅ]+", spaced) if w]


def is_id_key(key: str) -> bool:
    """True if `key` names an id: it ends in `id` or `ids`."""
    return _normalise(key).endswith(_ID_SUFFIXES)


def is_secret_key(key: str) -> bool:
    """True if the value under `key` is masked whole, in any case or separator style."""
    n = _normalise(key)
    if n in _NOT_SECRET_KEYS:
        return False
    return (
        n in _SECRET_KEYS
        or n.endswith(_SECRET_KEY_SUFFIXES)
        or any(part in n for part in _SECRET_KEY_PARTS)
        or not _SECRET_KEY_WORDS.isdisjoint(_words(key))
        or (
            any(part in n for part in _MEMBER_PARTS) and any(part in n for part in _MEMBER_ID_PARTS)
        )
    )


def _context_of(key: str) -> str | None:
    """`ITEM` or `LIST` if `key` names items or lists (`items`, `shoppingList`)."""
    n = _normalise(key)
    if "item" in n:
        return ITEM
    if "list" in n:
        return LIST
    return None


def _mask_for(key: str, context: str | None = None) -> str | None:
    """The placeholder for the value under `key`, or None to keep it.

    `context` is `ITEM` or `LIST` when the key sits inside an item or a list, so a
    bare `name` or `description` there is list content, not the member's.
    """
    n = _normalise(key)
    if n == "appinstallationid":
        return UUID
    if n.endswith(("name", "description")):
        own = _context_of(key)
        if own is not None:
            return own
        if n in {"name", "description"} and context is not None:
            return context
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


def _attribute(name: str) -> re.Pattern[str]:
    """An HTML attribute, its value double-quoted, single-quoted or bare. Not the
    tail of a longer attribute name such as `data-{name}`."""
    return re.compile(
        rf"((?<![\w-]){name}\s*=\s*)(?:\"([^\"]*)\"|'([^']*)'|([^\s>\"']+))", re.IGNORECASE
    )


_ATTR_NAME = _attribute("name")
_ATTR_TYPE = _attribute("type")
_ATTR_VALUE = _attribute("value")
# An input whose value is masked whatever its name.
_MASKED_INPUT_TYPES = frozenset({"password", "hidden"})
# `"key": value` in JSON text: a string (escapes included) or a bare scalar.
# `\"key\": value` in JSON that is itself inside a JSON string.
_ESCAPED_JSON_PAIR = re.compile(r'(\\")([^"\\]{1,100})\\"(\s*:\s*)(\\".*?\\"|[^,}\]\s\\]+)')
_JSON_PAIR = re.compile(
    r"([\"'])([^\"'\\]{1,100})\1(\s*:\s*)(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|[^,}\]\s]+)"
)
# `key%3Dvalue` inside a percent-encoded URL (an IdentityServer `ReturnUrl`), single
# or double encoded. The key starts after an encoded `?`, `&`, `#`, `/` or `;`, or after no key
# character; the value stops at the encoded `&`.
_ENCODED_PAIR = re.compile(
    r"(?:(?<=%3F)|(?<=%26)|(?<=%23)|(?<=%2F)|(?<=%3B)"
    r"|(?<=%253F)|(?<=%2526)|(?<=%2523)|(?<=%252F)|(?<=%253B)|(?<![A-Za-z0-9_.%-]))"
    r"([A-Za-z0-9_.-]+)(%3D|%253D)((?:(?!%26|%2526)[^&\s\"'<>#])+)",
    re.IGNORECASE,
)
# `key=value` in a query, a fragment, a form body or a cookie.
_PLAIN_PAIR = re.compile(r"(?<![A-Za-z0-9_.%-])([A-Za-z0-9_.-]+)(=)([^&\s;\"'<>#]+)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+(?:@|%40)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
# A long hex or base64url run: an API key, an opaque token, a session id.
_LONG_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}=*")
# A Danish phone number: eight digits, run together, in pairs split by spaces or
# hyphens, or in fours; with or without `+45`, `0045` or `45`. Not inside a longer
# digit run, so timestamps and EANs survive.
_PHONE = re.compile(
    r"(?<![\d+])(?:(?:\+|00)?45[ -]?)?(?:\d{8}|\d{2}(?:[ -]\d{2}){3}|\d{4} \d{4})(?!\d)"
)
_PHONE_NUMBER = re.compile(r"(?:45)?\d{8}")
_CONTAINER_KEY = re.compile(r"([\"'])([^\"'\\]{1,100})\1(\s*:\s*)(?=[{\[])")


def _attribute_value(pattern: re.Pattern[str], tag: str) -> str | None:
    found = pattern.search(tag)
    if found is None:
        return None
    return next(g for g in found.groups()[1:] if g is not None)


def _mask_input_tag(match: re.Match[str]) -> str:
    tag = match.group(0)
    name = _attribute_value(_ATTR_NAME, tag)
    input_type = (_attribute_value(_ATTR_TYPE, tag) or "").lower()
    mask = _mask_for(name) if name is not None else None
    if mask is None and input_type in _MASKED_INPUT_TYPES:
        mask = REDACTED
    if mask is None:
        return tag
    return _ATTR_VALUE.sub(lambda m: f'{m.group(1)}"{mask}"', tag)


def _container_end(text: str, start: int) -> int:
    """The index after the JSON object or array opening at `start`, or the end of
    `text` if it never closes."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth == 0:
                return index + 1
    return len(text)


def _mask_keyed_containers(text: str) -> str:
    """Mask an object or array under a masked key in JSON text, balanced to its end."""
    out: list[str] = []
    position = 0
    while (found := _CONTAINER_KEY.search(text, position)) is not None:
        mask = _mask_for(found.group(2))
        if mask is None:
            out.append(text[position : found.end()])
            position = found.end()
            continue
        out.append(text[position : found.end()] + f'"{mask}"')
        position = _container_end(text, found.end())
    out.append(text[position:])
    return "".join(out)


def _mask_json_pair(match: re.Match[str]) -> str:
    quote_char, key, colon, _value = match.groups()
    mask = _mask_for(key)
    if mask is None:
        return match.group(0)
    return f'{quote_char}{key}{quote_char}{colon}"{mask}"'


def _mask_escaped_json_pair(match: re.Match[str]) -> str:
    escaped_quote, key, colon, _value = match.groups()
    mask = _mask_for(key)
    if mask is None:
        return match.group(0)
    return f"{escaped_quote}{key}{escaped_quote}{colon}{escaped_quote}{mask}{escaped_quote}"


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
    (_ESCAPED_JSON_PAIR, _mask_escaped_json_pair),
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
    text = _mask_keyed_containers(text)
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text


def scrub_json(value: object, *, secrets: Iterable[str] = ()) -> object:
    """Mask a parsed JSON value: by key, recursively, and every other string by
    `scrub_text`. A masked key's value is replaced whole, container or not."""
    return _scrub_json(value, tuple(secrets), None)


def _scrub_json(value: object, secrets: tuple[str, ...], context: str | None) -> object:
    if isinstance(value, dict):
        out: dict[object, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                out[key] = _scrub_json(item, secrets, context)
                continue
            mask = _mask_for(key, context)
            inner = _context_of(key) or context
            out[scrub_text(key, secrets)] = (
                mask if mask is not None else _scrub_json(item, secrets, inner)
            )
        return out
    if isinstance(value, list):
        return [_scrub_json(item, secrets, context) for item in value]
    if isinstance(value, str):
        return _scrub_string(value, secrets, context)
    if isinstance(value, int | float) and not isinstance(value, bool):
        # A known secret held as a number: a member number, say.
        if str(value) in secrets:
            return REDACTED
        if isinstance(value, int) and _PHONE_NUMBER.fullmatch(str(value)):
            return REDACTED
    return value


def _scrub_string(value: str, secrets: tuple[str, ...], context: str | None) -> str:
    """A string scrubbed as text, or, if it holds a JSON object or array, as JSON."""
    if value.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(value)
        except ValueError:
            pass
        else:
            scrubbed = _scrub_json(parsed, secrets, context)
            return json.dumps(scrubbed, ensure_ascii=False)
    return scrub_text(value, secrets)


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

    A header named in the key set is masked whole, with its key's placeholder. A value holding a URL (`Location`,
    `Referer`) is masked as a URL, so an authorization code in its query is caught.
    """
    secrets = tuple(secrets)
    out: list[list[str]] = []
    for name, value in headers:
        mask = _mask_for(name)
        if mask is not None:
            out.append([name, mask])
        elif "://" in value or value.startswith("/"):
            out.append([name, scrub_url(value, secrets)])
        else:
            out.append([name, scrub_text(value, secrets)])
    return out


def scrub_multipart(body: bytes, content_type: str, secrets: Iterable[str] = ()) -> list[list[str]]:
    """Parse a `multipart/form-data` body into `[name, value]` pairs, masked by name
    and by `scrub_text`. A part that is not UTF-8 becomes `BINARY`.

    Raises `ValueError` for a body that does not parse as named parts.
    """
    secrets = tuple(secrets)
    if "boundary=" not in content_type.lower():
        raise ValueError("multipart body without a boundary")
    header = b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n"
    message = BytesParser(policy=policy.HTTP).parsebytes(header + body)
    if not isinstance(message, EmailMessage) or not message.is_multipart():
        raise ValueError("not a multipart body")
    pairs: list[list[str]] = []
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str):
            raise ValueError("multipart part without a name")  # noqa: TRY004 - a malformed body, as documented
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            raise ValueError("multipart part without a body")  # noqa: TRY004 - a malformed body, as documented
        mask = _mask_for(name)
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            text = BINARY
        pairs.append([scrub_text(name, secrets), mask or scrub_text(text, secrets)])
    if not pairs:
        raise ValueError("multipart body without parts")
    return pairs
