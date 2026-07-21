#!/usr/bin/env python3
"""Check a generated site directory against the frozen production baseline."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from baseline_common import load_json, parse_atom, parse_html, sitemap_urls


METADATA_FIELDS = (
    "canonical",
    "description",
    "lang",
    "modified_date",
    "open_graph_type",
    "publication_date",
    "structured_data_types",
    "title",
)


def _site_url(collection: dict[str, Any], path: str) -> str:
    return f"{collection['production_base_url'].rstrip('/')}{path}"


def _compare_metadata(
    generated_dir: Path,
    collection: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
    routes: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for route in routes:
        path = route["path"]
        output_path = route.get("output_path")
        if not route.get("check_generated") or not output_path:
            continue
        file_path = generated_dir / output_path
        if not file_path.exists():
            label = "missing notebook article" if route.get("notebook_article") else "missing route"
            errors.append(f"{label}: {path} ({output_path})")
            continue
        if not output_path.endswith(".html"):
            continue
        expected = metadata.get(path)
        if expected is None:
            errors.append(f"missing metadata baseline record: {path}")
            continue
        parser = parse_html(file_path.read_bytes(), _site_url(collection, path))
        actual = parser.snapshot()
        for field in METADATA_FIELDS:
            if actual.get(field) != expected.get(field):
                errors.append(
                    f"metadata mismatch for {path}: {field} expected={expected.get(field)!r} "
                    f"actual={actual.get(field)!r}"
                )
        expected_redirect = route.get("redirect")
        if expected_redirect and expected_redirect.get("kind") == "meta_refresh":
            if parser.meta_refresh_target != expected_redirect.get("target"):
                errors.append(
                    f"redirect mismatch for {path}: expected={expected_redirect.get('target')!r} "
                    f"actual={parser.meta_refresh_target!r}"
                )
    return errors


def _check_sitemap(generated_dir: Path, routes: list[dict[str, Any]]) -> list[str]:
    sitemap_path = generated_dir / "sitemap.xml"
    if not sitemap_path.exists():
        return ["missing route: /sitemap.xml (sitemap.xml)"]
    expected = sorted(route["url"] for route in routes if route.get("sitemap"))
    try:
        actual = sitemap_urls(sitemap_path.read_bytes())
    except Exception as error:  # noqa: BLE001
        return [f"invalid sitemap.xml: {error}"]
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        return [f"sitemap mismatch: missing={missing!r} unexpected={unexpected!r}"]
    return []


def _check_feeds(generated_dir: Path, feeds: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for expected in feeds:
        file_path = generated_dir / expected["path"].lstrip("/")
        if not file_path.exists():
            errors.append(f"missing feed: {expected['path']}")
            continue
        try:
            actual = parse_atom(file_path.read_bytes())
        except Exception as error:  # noqa: BLE001
            errors.append(f"invalid feed {expected['path']}: {error}")
            continue
        expected_ids = {entry["id"] for entry in expected["entries"]}
        actual_ids = {entry["id"] for entry in actual["entries"]}
        missing_ids = sorted(expected_ids - actual_ids)
        if missing_ids:
            errors.append(f"missing feed entry in {expected['path']}: {missing_ids!r}")
        unexpected_ids = sorted(actual_ids - expected_ids)
        if unexpected_ids:
            errors.append(f"unexpected feed entry in {expected['path']}: {unexpected_ids!r}")
        if actual["entry_count"] != expected["entry_count"]:
            errors.append(
                f"feed count mismatch for {expected['path']}: "
                f"expected={expected['entry_count']} actual={actual['entry_count']}"
            )
        expected_by_id = {entry["id"]: entry for entry in expected["entries"]}
        actual_by_id = {entry["id"]: entry for entry in actual["entries"]}
        for entry_id in sorted(expected_ids & actual_ids):
            for field in ("url", "published", "updated"):
                if actual_by_id[entry_id].get(field) != expected_by_id[entry_id].get(field):
                    errors.append(
                        f"feed entry mismatch in {expected['path']} for {entry_id}: {field} "
                        f"expected={expected_by_id[entry_id].get(field)!r} "
                        f"actual={actual_by_id[entry_id].get(field)!r}"
                    )
    return errors


def _check_assets(
    generated_dir: Path, assets: list[dict[str, Any]], *, verify_hashes: bool
) -> list[str]:
    errors: list[str] = []
    for asset in assets:
        output_path = asset.get("output_path")
        if (
            asset.get("ownership") != "site"
            or asset.get("status") != 200
            or not output_path
        ):
            continue
        file_path = generated_dir / output_path
        if not file_path.exists():
            errors.append(f"missing referenced asset: {output_path}")
            continue
        if verify_hashes:
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual != asset.get("sha256"):
                errors.append(
                    f"asset hash mismatch for {output_path}: "
                    f"expected={asset.get('sha256')} actual={actual}"
                )
    return errors


def check_generated(
    generated_dir: Path,
    baseline_dir: Path,
    *,
    verify_asset_hashes: bool = False,
) -> list[str]:
    collection = load_json(baseline_dir / "collection.json")
    route_records = load_json(baseline_dir / "routes.json")["routes"]
    metadata_records = {
        item["path"]: item for item in load_json(baseline_dir / "metadata.json")["pages"]
    }
    feed_records = load_json(baseline_dir / "feeds.json")["feeds"]
    asset_records = load_json(baseline_dir / "assets.json")["assets"]

    errors = _compare_metadata(
        generated_dir, collection, metadata_records, route_records
    )
    errors.extend(_check_sitemap(generated_dir, route_records))
    errors.extend(_check_feeds(generated_dir, feed_records))
    errors.extend(
        _check_assets(generated_dir, asset_records, verify_hashes=verify_asset_hashes)
    )

    cname = generated_dir / "CNAME"
    if cname.exists() and cname.read_text(encoding="utf-8").strip() != collection["canonical_host"]:
        errors.append(
            f"CNAME mismatch: expected={collection['canonical_host']!r} "
            f"actual={cname.read_text(encoding='utf-8').strip()!r}"
        )
    robots = generated_dir / "robots.txt"
    expected_sitemap_line = f"Sitemap: {collection['production_base_url']}/sitemap.xml"
    if robots.exists() and expected_sitemap_line not in robots.read_text(encoding="utf-8"):
        errors.append(f"robots.txt missing canonical sitemap declaration: {expected_sitemap_line}")
    return sorted(set(errors))


def parse_args() -> argparse.Namespace:
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated_dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path, default=package_root / "baseline")
    parser.add_argument("--verify-asset-hashes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = check_generated(
        args.generated_dir.resolve(),
        args.baseline_dir.resolve(),
        verify_asset_hashes=args.verify_asset_hashes,
    )
    if errors:
        print(f"BASE-001 parity check failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BASE-001 parity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
