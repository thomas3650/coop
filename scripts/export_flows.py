"""Export a mitmproxy capture as one scrubbed JSON file per flow.

    uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows.py <flows> <out_dir> [--ask-secret ...]

In an environment of its own, from the repo root: the project environment does not
resolve a usable mitmproxy beside Home Assistant's pins. Editable, because uv caches
a built `coop-client` under its unchanged version and would run a stale scrubber.

Point both paths at the gitignored `.captures/`. The out_dir must be empty. Each
`--ask-secret` prompts, without echo, for one value known to be secret (the
password, say); it is masked in every spelling the scrubber knows and is not
written anywhere.

Each file holds the method, URL, status, and the request's and response's headers
and body, all through the scrubber. A flow that cannot be read as an HTTP exchange
is written as `PLACEHOLDER`, never as its raw bytes. File names come from the flow's
position in the capture, never from its URL. Reads one local file and makes no
network request.

The result is still read by hand before anything derived from it is committed.
"""

import argparse
import getpass
import json
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from coop_client.scrub import (
    BINARY,
    scrub_form,
    scrub_headers,
    scrub_json,
    scrub_multipart,
    scrub_text,
    scrub_url,
)

PLACEHOLDER: dict[str, str] = {"unparsed": "<flow could not be exported>"}
_BOM = "\ufeff"


class OutsideOutDirError(ValueError):
    """A record's path resolves outside the export's out_dir."""


class OutDirNotEmptyError(ValueError):
    """The export's out_dir is a file, or a folder that already holds files."""


def _content_type(headers: list[tuple[str, str]]) -> str:
    for name, value in headers:
        if name.lower() == "content-type":
            return value
    return ""


def _json_lines(text: str, secrets: tuple[str, ...]) -> list[object] | None:
    """NDJSON scrubbed line by line, or None if a line is not JSON."""
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    try:
        return [scrub_json(json.loads(line), secrets=secrets) for line in lines]
    except ValueError:
        return None


def _event_stream(text: str, secrets: tuple[str, ...]) -> list[dict[str, object]]:
    """Server-sent events, one `{"fields", "data"}` record per event.

    An event's `data:` lines are joined, as the event-stream format joins them, and
    the result is scrubbed as JSON when it parses, else by `scrub_text`. Its other
    lines (`event:`, comments) are scrubbed together by `scrub_text`, with an `id:`
    line's value as `<id>`.
    """
    events: list[dict[str, object]] = []
    for block in re.split(r"\r?\n\r?\n", text):
        lines = block.splitlines()
        if not lines:
            continue
        data = [line[5:].removeprefix(" ") for line in lines if line.startswith("data:")]
        fields = "\n".join(
            "id: <id>" if line.startswith("id:") else line
            for line in lines
            if not line.startswith("data:")
        )
        joined = "\n".join(data)
        try:
            scrubbed: object = scrub_json(json.loads(joined), secrets=secrets)
        except ValueError:
            scrubbed = scrub_text(joined, secrets)
        events.append({"fields": scrub_text(fields, secrets), "data": scrubbed if data else None})
    return events


def scrub_body(body: bytes | None, content_type: str, secrets: Iterable[str] = ()) -> object:
    """A body as scrubbed JSON, NDJSON or server-sent events, scrubbed form or
    multipart pairs, scrubbed text, or `BINARY`."""
    secrets = tuple(secrets)
    if body is None:
        return None
    kind = content_type.lower()
    if "multipart/" in kind:
        try:
            return scrub_multipart(body, content_type, secrets)
        except ValueError:
            return BINARY
    try:
        text = body.decode("utf-8").removeprefix(_BOM)
    except UnicodeDecodeError:
        return BINARY
    if "application/x-www-form-urlencoded" in kind:
        return scrub_form(text, secrets)
    try:
        return scrub_json(json.loads(text), secrets=secrets)
    except ValueError:
        pass
    lines = _json_lines(text, secrets)
    if lines is not None:
        return lines
    if "text/event-stream" in kind:
        return _event_stream(text, secrets)
    return scrub_text(text, secrets)


def _message(message: Any, secrets: tuple[str, ...]) -> dict[str, object]:
    headers = [(str(k), str(v)) for k, v in message.headers.items(multi=True)]
    # Not strict: mitmproxy then returns a body whose Content-Encoding fails to
    # decode as its raw bytes instead of raising; `scrub_body` treats those like any
    # other body, so bytes that are not UTF-8 become `BINARY`.
    body = message.get_content(strict=False)
    return {
        "headers": scrub_headers(headers, secrets),
        "body": scrub_body(body, _content_type(headers), secrets),
    }


def record_from_flow(flow: Any, secrets: Iterable[str] = ()) -> dict[str, object]:
    """A scrubbed record of one mitmproxy `HTTPFlow`. Raises `AttributeError` for a
    flow of another kind, which `export` writes as `PLACEHOLDER`."""
    secrets = tuple(secrets)
    request = flow.request
    response = getattr(flow, "response", None)
    return {
        "method": str(request.method),
        "url": scrub_url(str(request.pretty_url), secrets),
        "status": int(response.status_code) if response is not None else None,
        "request": _message(request, secrets),
        "response": _message(response, secrets) if response is not None else None,
    }


def write_record(out_dir: Path, name: str, record: object) -> Path:
    """Write `record` as JSON to `out_dir / name`, refusing any path outside `out_dir`."""
    root = out_dir.resolve()
    target = (out_dir / name).resolve()
    if not target.is_relative_to(root) or target == root:
        raise OutsideOutDirError(name)
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def _not_empty(out_dir: Path) -> bool:
    """True unless `out_dir` is missing or an empty folder."""
    if not out_dir.exists():
        return False
    return not out_dir.is_dir() or any(out_dir.iterdir())


def export(flows: Iterable[Any], out_dir: Path, secrets: Iterable[str] = ()) -> int:
    """Write each flow to `out_dir/NNNN.json`; return how many files were written.

    Refuses an `out_dir` that is a file or already holds files. Each of `secrets` is masked in
    every spelling the scrubber knows. A flow that fails to export, and a stream
    that fails partway, each leave one `PLACEHOLDER` file. The exception's message
    is not kept: it can quote the flow.
    """
    secrets = tuple(secrets)
    if _not_empty(out_dir):
        raise OutDirNotEmptyError(str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    index = 0
    iterator: Iterator[Any] = iter(flows)
    while True:
        try:
            flow = next(iterator)
        except StopIteration:
            break
        except Exception:  # noqa: BLE001 - any read failure ends in a placeholder
            write_record(out_dir, f"{index:04d}.json", PLACEHOLDER)
            index += 1
            break
        try:
            record = record_from_flow(flow, secrets)
        except Exception:  # noqa: BLE001 - any parse failure ends in a placeholder
            record = dict(PLACEHOLDER)
        write_record(out_dir, f"{index:04d}.json", record)
        index += 1
    return index


def _read_flows(path: Path) -> Iterator[Any]:
    # Imported here so the offline suite does not need mitmproxy.
    from mitmproxy.io import FlowReader

    with path.open("rb") as flows_file:
        yield from FlowReader(flows_file).stream()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Export a capture, scrubbed.")
    parser.add_argument("flows", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--ask-secret",
        action="count",
        default=0,
        help="prompt, without echo, for one known secret to mask; repeat for more",
    )
    args = parser.parse_args(argv)
    # Before the prompts, so a refused export never asks for a secret.
    if _not_empty(args.out_dir):
        print(f"refusing: {args.out_dir} is not an empty directory", file=sys.stderr)
        return 2
    secrets = [
        getpass.getpass(f"Secret {number} to mask: ") for number in range(1, args.ask_secret + 1)
    ]
    try:
        count = export(_read_flows(args.flows), args.out_dir, secrets=secrets)
    except OutDirNotEmptyError:
        print(f"refusing: {args.out_dir} is not an empty directory", file=sys.stderr)
        return 2
    print(f"wrote {count} files to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
