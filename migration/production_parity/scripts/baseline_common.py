#!/usr/bin/env python3
"""Shared parsers and path helpers for the production parity baseline."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit


ATOM_NS = "{http://www.w3.org/2005/Atom}"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def route_to_output_path(route: str) -> str:
    path = urlsplit(route).path
    if path == "/":
        return "index.html"
    if path.endswith("/"):
        return f"{path.lstrip('/')}index.html"
    return path.lstrip("/")


def tree_file_to_route(path: str) -> str | None:
    if not path.endswith(".html"):
        return None
    if path == "index.html":
        return "/"
    if path.endswith("/index.html"):
        return f"/{path[:-len('index.html')]}"
    return f"/{path}"


def sitemap_urls(data: bytes) -> list[str]:
    root = ET.fromstring(data)
    return sorted(
        item.text.strip()
        for item in root.findall(f".//{SITEMAP_NS}loc")
        if item.text and item.text.strip()
    )


def _text(element: ET.Element, child: str) -> str | None:
    node = element.find(f"{ATOM_NS}{child}")
    if node is None or node.text is None:
        return None
    return node.text.strip()


def parse_atom(data: bytes) -> dict[str, Any]:
    root = ET.fromstring(data)
    links = []
    for link in root.findall(f"{ATOM_NS}link"):
        links.append(
            {
                "href": link.attrib.get("href"),
                "rel": link.attrib.get("rel", "alternate"),
            }
        )

    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        alternate = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.attrib.get("rel", "alternate") == "alternate":
                alternate = link.attrib.get("href")
                break
        entries.append(
            {
                "categories": sorted(
                    category.attrib.get("term", "")
                    for category in entry.findall(f"{ATOM_NS}category")
                ),
                "id": _text(entry, "id"),
                "published": _text(entry, "published"),
                "title": _text(entry, "title"),
                "updated": _text(entry, "updated"),
                "url": alternate,
            }
        )

    entries.sort(key=lambda item: (item["id"] or "", item["url"] or ""))
    links.sort(key=lambda item: (item["rel"] or "", item["href"] or ""))
    return {
        "entry_count": len(entries),
        "entries": entries,
        "id": _text(root, "id"),
        "links": links,
        "title": _text(root, "title"),
        "updated": _text(root, "updated"),
    }


def _json_ld_values(value: Any, key: str) -> list[str]:
    results: list[str] = []
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, str):
            results.append(candidate)
        elif isinstance(candidate, list):
            results.extend(item for item in candidate if isinstance(item, str))
        for nested in value.values():
            results.extend(_json_ld_values(nested, key))
    elif isinstance(value, list):
        for nested in value:
            results.extend(_json_ld_values(nested, key))
    return results


def _srcset_urls(value: str) -> list[str]:
    return [part.strip().split()[0] for part in value.split(",") if part.strip()]


class HTMLSnapshotParser(HTMLParser):
    """Extract the parity-relevant metadata and references from one HTML page."""

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.lang: str | None = None
        self.title_parts: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []
        self.json_ld_documents: list[Any] = []
        self.meta: dict[str, list[str]] = {}
        self.canonical: str | None = None
        self.links: set[str] = set()
        self.image_references: set[str] = set()
        self.stylesheet_references: set[str] = set()
        self.feed_references: set[str] = set()
        self.time_values: list[str] = []
        self.meta_refresh_target: str | None = None

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = self._attrs(attrs)
        tag = tag.lower()

        if tag == "html":
            self.lang = values.get("lang") or None
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (values.get("name") or values.get("property") or values.get("itemprop") or "").lower()
            content = values.get("content", "").strip()
            if key and content:
                self.meta.setdefault(key, []).append(content)
            if values.get("http-equiv", "").lower() == "refresh" and content:
                match = re.search(r"(?:^|;)\s*url\s*=\s*['\"]?([^'\"]+)", content, re.IGNORECASE)
                if match:
                    self.meta_refresh_target = urljoin(self.page_url, match.group(1).strip())
        elif tag == "link":
            href = values.get("href", "").strip()
            rel = {item.lower() for item in values.get("rel", "").split()}
            if href and "canonical" in rel:
                self.canonical = urljoin(self.page_url, href)
            if href and "stylesheet" in rel:
                self.stylesheet_references.add(urljoin(self.page_url, href))
            if href and "alternate" in rel and "atom" in values.get("type", "").lower():
                self.feed_references.add(urljoin(self.page_url, href))
        elif tag == "a":
            href = values.get("href", "").strip()
            if href:
                self.links.add(urljoin(self.page_url, href))
        elif tag == "img":
            src = values.get("src", "").strip()
            if src and not src.startswith("data:"):
                self.image_references.add(urljoin(self.page_url, src))
            for item in _srcset_urls(values.get("srcset", "")):
                if not item.startswith("data:"):
                    self.image_references.add(urljoin(self.page_url, item))
        elif tag == "source":
            src = values.get("src", "").strip()
            if src and not src.startswith("data:"):
                self.image_references.add(urljoin(self.page_url, src))
            for item in _srcset_urls(values.get("srcset", "")):
                if not item.startswith("data:"):
                    self.image_references.add(urljoin(self.page_url, item))
        elif tag == "time":
            datetime_value = values.get("datetime", "").strip()
            if datetime_value:
                self.time_values.append(datetime_value)
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            raw = "".join(self._json_ld_parts).strip()
            if raw:
                try:
                    self.json_ld_documents.append(json.loads(raw))
                except json.JSONDecodeError:
                    self.json_ld_documents.append({"_invalid_json_ld": raw})
            self._in_json_ld = False
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._json_ld_parts.append(data)

    def snapshot(self) -> dict[str, Any]:
        structured_types: list[str] = []
        published: list[str] = []
        modified: list[str] = []
        for document in self.json_ld_documents:
            structured_types.extend(_json_ld_values(document, "@type"))
            published.extend(_json_ld_values(document, "datePublished"))
            modified.extend(_json_ld_values(document, "dateModified"))

        open_graph_type = (self.meta.get("og:type") or [None])[0]
        is_article = open_graph_type == "article" or any(
            value.lower().endswith("article") for value in structured_types
        )
        publication_date = (self.meta.get("article:published_time") or published or [None])[0]
        if not publication_date and is_article and self.time_values:
            publication_date = self.time_values[0]

        return {
            "canonical": self.canonical,
            "description": (self.meta.get("description") or [None])[0],
            "lang": self.lang,
            "modified_date": (self.meta.get("article:modified_time") or modified or [None])[0],
            "open_graph_type": open_graph_type,
            "publication_date": publication_date,
            "structured_data_types": sorted(set(structured_types)),
            "title": " ".join("".join(self.title_parts).split()) or None,
        }


def parse_html(data: bytes, page_url: str) -> HTMLSnapshotParser:
    parser = HTMLSnapshotParser(page_url)
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()
    return parser
