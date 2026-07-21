#!/usr/bin/env python3
"""Compare route-bearing generated files from two Pelican builds."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROUTE_SUFFIXES = {".html", ".xml"}


def routes(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in ROUTE_SUFFIXES
    }


def digest(values: set[str]) -> str:
    payload = "\n".join(sorted(values)).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()

    first = routes(args.first.resolve())
    second = routes(args.second.resolve())
    if first != second:
        print("route sets differ", file=sys.stderr)
        for route in sorted(first - second):
            print(f"- only first: {route}", file=sys.stderr)
        for route in sorted(second - first):
            print(f"- only second: {route}", file=sys.stderr)
        return 1
    print(f"route sets match: count={len(first)} sha256={digest(first)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
