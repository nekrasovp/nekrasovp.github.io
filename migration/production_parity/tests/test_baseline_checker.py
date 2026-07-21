#!/usr/bin/env python3
"""Positive and required negative tests for the BASE-001 parity checker."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from baseline_common import ATOM_NS, load_json  # noqa: E402
from check_generated_baseline import check_generated  # noqa: E402


def _meta(name: str, value: str | None, *, prop: bool = False) -> str:
    if value is None:
        return ""
    key = "property" if prop else "name"
    return f'<meta {key}="{html.escape(name)}" content="{html.escape(value, quote=True)}">'


def render_html(metadata: dict, redirect: dict | None) -> str:
    ld_document: dict[str, str] = {}
    structured_types = metadata.get("structured_data_types") or []
    if structured_types:
        ld_document["@type"] = structured_types[0]
    if metadata.get("publication_date") and structured_types:
        ld_document["datePublished"] = metadata["publication_date"]
    if metadata.get("modified_date") and structured_types:
        ld_document["dateModified"] = metadata["modified_date"]
    if len(structured_types) > 1:
        ld_payload: object = [ld_document] + [{"@type": value} for value in structured_types[1:]]
    else:
        ld_payload = ld_document
    ld_json = (
        f'<script type="application/ld+json">{json.dumps(ld_payload)}</script>'
        if ld_document
        else ""
    )
    canonical = (
        f'<link rel="canonical" href="{html.escape(metadata["canonical"], quote=True)}">'
        if metadata.get("canonical")
        else ""
    )
    refresh = ""
    if redirect and redirect.get("kind") == "meta_refresh":
        refresh = (
            '<meta http-equiv="refresh" content="0; url='
            f'{html.escape(redirect["target"], quote=True)}">'
        )
    lang = (
        f' lang="{html.escape(metadata["lang"], quote=True)}"'
        if metadata.get("lang")
        else ""
    )
    return "\n".join(
        [
            f"<!doctype html><html{lang}><head>",
            f"<title>{html.escape(metadata.get('title') or '')}</title>",
            _meta("description", metadata.get("description")),
            _meta("og:type", metadata.get("open_graph_type"), prop=True),
            _meta("article:published_time", metadata.get("publication_date"), prop=True),
            _meta("article:modified_time", metadata.get("modified_date"), prop=True),
            canonical,
            refresh,
            ld_json,
            "</head><body></body></html>",
        ]
    )


def write_feed(path: Path, feed: dict) -> None:
    ET.register_namespace("", "http://www.w3.org/2005/Atom")
    root = ET.Element(f"{ATOM_NS}feed")
    for field in ("title", "id", "updated"):
        value = feed.get(field)
        if value is not None:
            ET.SubElement(root, f"{ATOM_NS}{field}").text = value
    for link in feed["links"]:
        ET.SubElement(
            root,
            f"{ATOM_NS}link",
            {"href": link.get("href") or "", "rel": link.get("rel") or "alternate"},
        )
    for expected in feed["entries"]:
        entry = ET.SubElement(root, f"{ATOM_NS}entry")
        for field in ("title", "id", "published", "updated"):
            value = expected.get(field)
            if value is not None:
                ET.SubElement(entry, f"{ATOM_NS}{field}").text = value
        if expected.get("url"):
            ET.SubElement(
                entry,
                f"{ATOM_NS}link",
                {"href": expected["url"], "rel": "alternate"},
            )
        for category in expected.get("categories", []):
            ET.SubElement(entry, f"{ATOM_NS}category", {"term": category})
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def build_fixture(destination: Path, baseline_dir: Path) -> None:
    collection = load_json(baseline_dir / "collection.json")
    routes = load_json(baseline_dir / "routes.json")["routes"]
    metadata = {item["path"]: item for item in load_json(baseline_dir / "metadata.json")["pages"]}
    feeds = load_json(baseline_dir / "feeds.json")["feeds"]
    assets = load_json(baseline_dir / "assets.json")["assets"]

    for route in routes:
        output_path = route.get("output_path")
        if not route.get("check_generated") or not output_path:
            continue
        target = destination / output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if output_path.endswith(".html"):
            target.write_text(
                render_html(metadata[route["path"]], route.get("redirect")),
                encoding="utf-8",
            )

    sitemap_root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    for route in sorted((item for item in routes if item.get("sitemap")), key=lambda item: item["url"]):
        node = ET.SubElement(sitemap_root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = route["url"]
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ET.ElementTree(sitemap_root).write(destination / "sitemap.xml", encoding="utf-8", xml_declaration=True)

    for feed in feeds:
        write_feed(destination / feed["path"].lstrip("/"), feed)
    for asset in assets:
        if asset.get("ownership") == "site" and asset.get("output_path"):
            target = destination / asset["output_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=True)
    (destination / "CNAME").write_text(f"{collection['canonical_host']}\n", encoding="utf-8")
    (destination / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {collection['production_base_url']}/sitemap.xml\n",
        encoding="utf-8",
    )


class BaselineCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline_dir = PACKAGE_ROOT / "baseline"
        cls.temp_root = Path(tempfile.mkdtemp(prefix="base001-checker-tests-"))
        cls.pristine = cls.temp_root / "pristine"
        cls.pristine.mkdir()
        build_fixture(cls.pristine, cls.baseline_dir)
        cls.routes = load_json(cls.baseline_dir / "routes.json")["routes"]
        cls.metadata = load_json(cls.baseline_dir / "metadata.json")["pages"]
        cls.feeds = load_json(cls.baseline_dir / "feeds.json")["feeds"]

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp_root)

    def setUp(self) -> None:
        self.generated = self.temp_root / self._testMethodName
        shutil.copytree(self.pristine, self.generated)

    def errors(self) -> list[str]:
        return check_generated(self.generated, self.baseline_dir)

    def cli_result(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "check_generated_baseline.py"),
                str(self.generated),
                "--baseline-dir",
                str(self.baseline_dir),
            ],
            capture_output=True,
            text=True,
        )

    def test_complete_fixture_passes(self) -> None:
        self.assertEqual([], self.errors())
        self.assertEqual(0, self.cli_result().returncode)

    def test_missing_route_fails(self) -> None:
        route = next(
            item
            for item in self.routes
            if item.get("check_generated")
            and item.get("output_path", "").endswith(".html")
            and not item.get("notebook_article")
        )
        (self.generated / route["output_path"]).unlink()
        self.assertTrue(any("missing route:" in error for error in self.errors()))
        self.assertEqual(1, self.cli_result().returncode)

    def test_missing_notebook_article_fails(self) -> None:
        route = next(item for item in self.routes if item.get("notebook_article"))
        (self.generated / route["output_path"]).unlink()
        self.assertTrue(any("missing notebook article:" in error for error in self.errors()))
        self.assertEqual(1, self.cli_result().returncode)

    def test_missing_feed_entry_fails(self) -> None:
        feed = self.feeds[0]
        feed_path = self.generated / feed["path"].lstrip("/")
        tree = ET.parse(feed_path)
        root = tree.getroot()
        root.remove(root.find(f"{ATOM_NS}entry"))
        tree.write(feed_path, encoding="utf-8", xml_declaration=True)
        self.assertTrue(any("missing feed entry" in error for error in self.errors()))
        self.assertEqual(1, self.cli_result().returncode)

    def test_wrong_canonical_fails(self) -> None:
        page = next(item for item in self.metadata if item.get("canonical"))
        route = next(item for item in self.routes if item["path"] == page["path"] and item.get("output_path"))
        target = self.generated / route["output_path"]
        value = target.read_text(encoding="utf-8").replace(
            page["canonical"], "https://wrong.example.invalid/", 1
        )
        target.write_text(value, encoding="utf-8")
        self.assertTrue(any("canonical" in error for error in self.errors()))
        self.assertEqual(1, self.cli_result().returncode)

    def test_missing_lang_fails(self) -> None:
        page = next(item for item in self.metadata if item.get("lang"))
        route = next(item for item in self.routes if item["path"] == page["path"] and item.get("output_path"))
        target = self.generated / route["output_path"]
        value = re.sub(r"\s+lang=\"[^\"]+\"", "", target.read_text(encoding="utf-8"), count=1)
        target.write_text(value, encoding="utf-8")
        self.assertTrue(any("lang" in error for error in self.errors()))
        self.assertEqual(1, self.cli_result().returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
