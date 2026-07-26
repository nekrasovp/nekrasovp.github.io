#!/usr/bin/env python3
"""Create deterministic sitemap, robots, and the referenced SITE-005 category feed."""

from __future__ import annotations

import argparse
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROUTES = REPO_ROOT / "migration/production_parity/baseline/routes.json"
BASELINE_FEEDS = REPO_ROOT / "migration/production_parity/baseline/feeds.json"
SITE005_MANIFEST = REPO_ROOT / "migration/site005/materials.json"
ORIGIN = "https://nekrasovp.ru"
ATOM = "{http://www.w3.org/2005/Atom}"
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain an object")
    return value


def _write_sitemap(output_root: Path) -> int:
    routes = _load(BASELINE_ROUTES)["routes"]
    records = [record for record in routes if record.get("sitemap")]
    if len(records) != 58:
        raise RuntimeError(f"expected 58 baseline sitemap records, got {len(records)}")
    missing = sorted(
        record["output_path"]
        for record in records
        if not (output_root / record["output_path"]).is_file()
    )
    if missing:
        raise RuntimeError(f"cannot publish sitemap with missing outputs: {missing!r}")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root = ET.Element(f"{SITEMAP}urlset")
    for record in sorted(records, key=lambda item: item["url"]):
        url = ET.SubElement(root, f"{SITEMAP}url")
        ET.SubElement(url, f"{SITEMAP}loc").text = record["url"]
    ET.ElementTree(root).write(
        output_root / "sitemap.xml",
        encoding="utf-8",
        xml_declaration=True,
    )
    return len(records)


def _write_misc_feed(output_root: Path) -> int:
    source = output_root / "feeds/all.atom.xml"
    target = output_root / "feeds/misc.atom.xml"
    materials = _load(SITE005_MANIFEST)["materials"]
    expected = {
        record["feed"]["id"]
        for record in materials
        if isinstance(record.get("feed"), dict)
    }
    if len(expected) != 3:
        raise RuntimeError(f"expected three SITE-005 feed IDs, got {len(expected)}")
    tree = ET.parse(source)
    root = tree.getroot()
    retained = []
    for entry in list(root.findall(f"{ATOM}entry")):
        identifier = entry.findtext(f"{ATOM}id")
        if identifier not in expected:
            root.remove(entry)
        else:
            retained.append(entry)
    actual = {entry.findtext(f"{ATOM}id") for entry in retained}
    if actual != expected:
        raise RuntimeError(f"SITE-005 feed IDs differ: expected={expected!r} actual={actual!r}")
    for link in root.findall(f"{ATOM}link"):
        if link.get("rel") == "self":
            link.set("href", f"{ORIGIN}/feeds/misc.atom.xml")
    feed_id = root.find(f"{ATOM}id")
    if feed_id is not None:
        feed_id.text = f"{ORIGIN}/feeds/misc.atom.xml"
    title = root.find(f"{ATOM}title")
    if title is not None:
        title.text = "Pavel Nekrasov — Misc"
    updated = root.find(f"{ATOM}updated")
    entry_updates = [
        value
        for entry in retained
        if (value := entry.findtext(f"{ATOM}updated")) is not None
    ]
    if updated is not None and entry_updates:
        updated.text = max(entry_updates)
    target.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", "http://www.w3.org/2005/Atom")
    ET.ElementTree(copy.deepcopy(root)).write(
        target,
        encoding="utf-8",
        xml_declaration=True,
    )
    return len(retained)


def _normalize_historical_feed_ids(output_root: Path) -> int:
    baseline_feeds = {
        record["path"].lstrip("/"): record
        for record in _load(BASELINE_FEEDS)["feeds"]
    }
    site005_entries = {
        record["canonical_url"]: record["feed"]["id"]
        for record in _load(SITE005_MANIFEST)["materials"]
        if isinstance(record.get("feed"), dict)
    }
    normalized = 0
    for relative in ("feeds/all.atom.xml", "feeds/blog.atom.xml"):
        expected = {
            entry["url"]: entry["id"]
            for entry in baseline_feeds[relative]["entries"]
        }
        path = output_root / relative
        tree = ET.parse(path)
        root = tree.getroot()
        for entry in root.findall(f"{ATOM}entry"):
            link = entry.find(f"{ATOM}link[@rel='alternate']")
            identifier = entry.find(f"{ATOM}id")
            if link is None or identifier is None:
                raise RuntimeError(f"{relative} entry is missing alternate link or id")
            url = link.get("href")
            if url not in expected:
                if site005_entries.get(url) == identifier.text:
                    continue
                raise RuntimeError(
                    f"{relative} has an unreviewed entry pair: "
                    f"url={url!r} id={identifier.text!r}"
                )
            if identifier.text != expected[url]:
                identifier.text = expected[url]
                normalized += 1
        tree.write(path, encoding="utf-8", xml_declaration=True)
    if normalized not in {0, 92}:
        raise RuntimeError(
            "historical feed IDs must be wholly raw or wholly normalized: "
            f"observed_normalizations={normalized}"
        )
    return normalized


def finalize(output_root: Path) -> dict[str, int]:
    root = output_root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"output directory is missing: {root}")
    sitemap_urls = _write_sitemap(root)
    (root / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n",
        encoding="utf-8",
    )
    normalized_ids = _normalize_historical_feed_ids(root)
    misc_entries = _write_misc_feed(root)
    return {
        "historical_feed_ids_normalized": normalized_ids,
        "misc_feed_entries": misc_entries,
        "sitemap_urls": sitemap_urls,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(finalize(args.output_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
