#!/usr/bin/env python3
"""Compare two collections while excluding their collection timestamps."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FILES = ("assets.json", "collection.json", "feeds.json", "metadata.json", "routes.json")
TIMESTAMP_FIELDS = {"collection_started_at_utc", "collection_finished_at_utc"}


def normalized(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    value = copy.deepcopy(value)
    if path.name == "collection.json":
        for field in TIMESTAMP_FIELDS:
            value.pop(field, None)
    return value


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare(first: Path, second: Path) -> list[str]:
    errors = []
    for name in FILES:
        first_value = normalized(first / name)
        second_value = normalized(second / name)
        if first_value != second_value:
            errors.append(
                f"{name} differs: first={digest(first_value)} second={digest(second_value)}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    errors = compare(args.first.resolve(), args.second.resolve())
    if errors:
        print("BASE-001 collections are not deterministic:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BASE-001 collections are deterministic after excluding collection timestamps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
