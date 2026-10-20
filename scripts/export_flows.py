"""Export a mitmproxy capture as one scrubbed JSON file per flow.

    uv run --no-project --with mitmproxy --with-editable ./packages/coop-client python scripts/export_flows.py <flows> <out_dir>

In an environment of its own, from the repo root: the project environment does not
resolve a usable mitmproxy beside Home Assistant's pins. Editable, because uv caches
a built `coop-client` under its unchanged version and would run a stale scrubber.

Each file holds the method, URL, status, and the request's and response's headers
and body, all through the scrubber. A flow that cannot be read as an HTTP exchange
is written as `PLACEHOLDER`, never as its raw bytes. File names come from the flow's
position in the capture, never from its URL. Reads one local file and makes no
network request.

The result is still read by hand before anything derived from it is committed.
"""

import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from coop_client.scrub import scrub_form, scrub_headers, scrub_json, scrub_text, scrub_url

PLACEHOLDER: dict[str, str] = {"unparsed": "<flow could not be exported>"}
BINARY = "<binary>"


class OutsideOutDirError(ValueError):
    """A record's path resolves outside the export's out_dir."""


def _content_type(headers: list[tuple[str, str]]) -> str:
    for name, value in headers:
        if name.lower() == "content-type":
            return value.lower()
    return ""


def scrub_body(body: bytes | None, content_type: str) -> object:
    """A body as scrubbed JSON, scrubbed form pairs, scrubbed text, or `BINARY`."""
    if body is None:
        return None
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return BINARY
    if "application/x-www-form-urlencoded" in content_type:
        return scrub_form(text)
    try:
        parsed = json.loads(text)
    except ValueError:
        return scrub_text(text)
    return scrub_json(parsed)


def _message(message: Any) -> dict[str, object]:
    headers = [(str(k), str(v)) for k, v in message.headers.items(multi=True)]
    # Not strict: a body whose Content-Encoding fails to decode comes back as its
    # raw bytes, which `scrub_body` then reports as `BINARY`.
    body = message.get_content(strict=False)
    return {
        "headers": scrub_headers(headers),
        "body": scrub_body(body, _content_type(headers)),
    }


def record_from_flow(flow: Any) -> dict[str, object]:
    """A scrubbed record of one mitmproxy `HTTPFlow`. Raises `AttributeError` for a
    flow of another kind, which `export` writes as `PLACEHOLDER`."""
    request = flow.request
    response = getattr(flow, "response", None)
    return {
        "method": str(request.method),
        "url": scrub_url(str(request.pretty_url)),
        "status": int(response.status_code) if response is not None else None,
        "request": _message(request),
        "response": _message(response) if response is not None else None,
    }


def write_record(out_dir: Path, name: str, record: object) -> Path:
    """Write `record` as JSON to `out_dir / name`, refusing any path outside `out_dir`."""
    root = out_dir.resolve()
    target = (out_dir / name).resolve()
    if not target.is_relative_to(root) or target == root:
        raise OutsideOutDirError(name)
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def export(flows: Iterable[Any], out_dir: Path) -> int:
    """Write each flow to `out_dir/NNNN.json`; return how many files were written.

    A flow that fails to export, and a stream that fails partway, each leave one
    `PLACEHOLDER` file. The exception's message is not kept: it can quote the flow.
    """
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
            record = record_from_flow(flow)
        except Exception:  # noqa: BLE001 - any parse failure ends in a placeholder
            record = dict(PLACEHOLDER)
        write_record(out_dir, f"{index:04d}.json", record)
        index += 1
    return index


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: export_flows.py <flows> <out_dir>", file=sys.stderr)
        return 2
    # Imported here so the offline suite does not need mitmproxy.
    from mitmproxy.io import FlowReader

    with Path(argv[0]).open("rb") as flows_file:
        count = export(FlowReader(flows_file).stream(), Path(argv[1]))
    print(f"wrote {count} files to {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
