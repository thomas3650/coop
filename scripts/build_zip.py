"""Build the release zip HACS downloads: the integration directory, client included.

HACS extracts the zip into the integration's own directory, so its entries sit at the zip's root.
The client directory is a symlink in the tree; the walk follows it, so the zip holds the client's
source as regular files. Stdlib only.
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path

INTEGRATION = Path(__file__).resolve().parent.parent / "custom_components" / "coop_dk"


def build_zip(out: Path, *, source: Path = INTEGRATION) -> Path:
    """Write the files under `source` to the zip at `out`, following symlinks, and return `out`."""
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for directory, dirs, files in os.walk(source, followlinks=True):
            dirs.sort()
            here = Path(directory)
            for name in sorted(files):
                if name.endswith(".pyc"):
                    continue
                path = here / name
                archive.write(path, path.relative_to(source).as_posix())
    return out


def main(argv: list[str] | None = None) -> int:
    """Build the zip at the given path."""
    parser = argparse.ArgumentParser(description="Build the release zip.")
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    print(build_zip(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
