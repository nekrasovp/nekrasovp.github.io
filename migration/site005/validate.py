"""Validate the six frozen SITE-005 sources and their rendered contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"
MANIFEST_PATH = REPO_ROOT / "migration/site005/materials.json"
LEGACY_MANIFEST = REPO_ROOT / "migration/production_parity/inputs/legacy_routes.tsv"
SITEURL = "https://nekrasovp.ru"
SOCIAL_IMAGE = f"{SITEURL}/images/social-preview.png"
SOCIAL_IMAGE_ALT = "Pavel Nekrasov — Tech Lead and Backend/Platform Engineer"
EXPECTED_SITE005 = 6
EXPECTED_ESSAYS = 3
EXPECTED_COMPANIONS = 3
EXPECTED_ALL_FEED_ENTRIES = 49
EXPECTED_LEGACY_ENTRIES = 46
SITE_BASE_COMMIT = "3acbb7168f55b100cfd8debab2b096baa6ff4919"
PRODUCTION_COMMIT = "5c24ba21ec8b442e4b5280a47c85fab61165f8ce"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
INSTALL_NOISE = "Installed 2 packages in 11ms"


class Site005ValidationError(RuntimeError):
    """Stable SITE-005 failure with source and stage context."""

    error_code = "validation_error"
    stage = "inventory_validation"

    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        super().__init__(
            "SITE-005 validation failed: "
            f"source={source!r} stage={self.stage} error_code={self.error_code} "
            f"error_type={type(self).__name__} {message}"
        )


class InvalidSite005Manifest(Site005ValidationError):
    error_code = "invalid_manifest"


class MissingSite005Source(Site005ValidationError):
    error_code = "missing_site005_source"


class UndeclaredSite005Source(Site005ValidationError):
    error_code = "undeclared_site005_source"


class Site005MetadataMismatch(Site005ValidationError):
    error_code = "metadata_mismatch"


class Site005AssetMismatch(Site005ValidationError):
    error_code = "asset_mismatch"


class Site005RenderedMismatch(Site005ValidationError):
    error_code = "rendered_mismatch"
    stage = "rendered_validation"


@dataclass(frozen=True)
class Material:
    source: str
    route: str
    role: str
    title: str
    description: str
    author: str
    language: str
    published: str
    canonical_url: str
    companion_route: str
    payload: Mapping[str, Any]

    @property
    def slug(self) -> str:
        return self.route.removeprefix("/").removesuffix(".html")

    @property
    def feed(self) -> Mapping[str, Any] | None:
        value = self.payload.get("feed")
        return value if isinstance(value, Mapping) else None

    @property
    def figure(self) -> Mapping[str, Any] | None:
        value = self.payload.get("figure")
        return value if isinstance(value, Mapping) else None

    @property
    def rendered(self) -> Mapping[str, Any]:
        value = self.payload.get("rendered")
        return value if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class Manifest:
    site_base_commit: str
    production_commit: str
    asset: Mapping[str, Any]
    materials: tuple[Material, ...]
    feed_baseline: Mapping[str, Any]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def load_manifest(path: Path = MANIFEST_PATH) -> Manifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise InvalidSite005Manifest(path.as_posix(), str(error)) from error
    if payload.get("contract") != "nekrasovp-site005-materials.v1":
        raise InvalidSite005Manifest(path.as_posix(), "unknown contract")
    provenance = payload.get("frozen_provenance")
    asset = payload.get("asset")
    records = payload.get("materials")
    if not isinstance(provenance, dict) or not isinstance(asset, dict):
        raise InvalidSite005Manifest(path.as_posix(), "provenance or asset is not an object")
    expected_provenance = {
        "production_commit": PRODUCTION_COMMIT,
        "site_base_commit": SITE_BASE_COMMIT,
    }
    if provenance != expected_provenance:
        raise InvalidSite005Manifest(
            path.as_posix(),
            f"frozen provenance expected={expected_provenance!r} actual={provenance!r}",
        )
    expected_asset_identity = {
        "canonical_url": SOCIAL_IMAGE,
        "path": "content/images/social-preview.png",
        "production_path": "images/social-preview.png",
    }
    for key, expected_value in expected_asset_identity.items():
        if asset.get(key) != expected_value:
            raise InvalidSite005Manifest(
                path.as_posix(),
                f"asset field={key!r} expected={expected_value!r} actual={asset.get(key)!r}",
            )
    if not isinstance(records, list) or len(records) != EXPECTED_SITE005:
        raise InvalidSite005Manifest(path.as_posix(), "expected exactly six materials")
    materials: list[Material] = []
    for record in records:
        if not isinstance(record, dict):
            raise InvalidSite005Manifest(path.as_posix(), "material is not an object")
        try:
            item = Material(
                source=record["source"],
                route=record["route"],
                role=record["role"],
                title=record["title"],
                description=record["description"],
                author=record["author"],
                language=record["language"],
                published=record["published"],
                canonical_url=record["canonical_url"],
                companion_route=record["companion_route"],
                payload=record,
            )
        except KeyError as error:
            raise InvalidSite005Manifest(
                path.as_posix(), f"material missing field {error.args[0]!r}"
            ) from error
        materials.append(item)
    sources = [item.source for item in materials]
    routes = [item.route for item in materials]
    if len(set(sources)) != EXPECTED_SITE005 or len(set(routes)) != EXPECTED_SITE005:
        raise InvalidSite005Manifest(path.as_posix(), "sources and routes must be unique")
    if sum(item.role == "essay" for item in materials) != EXPECTED_ESSAYS:
        raise InvalidSite005Manifest(path.as_posix(), "expected exactly three essays")
    if sum(item.role == "companion" for item in materials) != EXPECTED_COMPANIONS:
        raise InvalidSite005Manifest(path.as_posix(), "expected exactly three companions")
    route_set = set(routes)
    for item in materials:
        if item.role not in {"essay", "companion"}:
            raise InvalidSite005Manifest(item.source, f"invalid role {item.role!r}")
        if (
            not item.route.startswith("/")
            or not item.route.endswith(".html")
            or item.canonical_url != f"{SITEURL}{item.route}"
        ):
            raise InvalidSite005Manifest(item.source, "invalid route/canonical mapping")
        if item.companion_route not in route_set or item.companion_route == item.route:
            raise InvalidSite005Manifest(item.source, "invalid companion route")
        if item.role == "essay" and item.feed is None:
            raise InvalidSite005Manifest(item.source, "essay feed record is missing")
        if item.role == "companion" and item.feed is not None:
            raise InvalidSite005Manifest(item.source, "companion must not have a feed record")
    return Manifest(
        site_base_commit=str(provenance.get("site_base_commit", "")),
        production_commit=str(provenance.get("production_commit", "")),
        asset=asset,
        materials=tuple(materials),
        feed_baseline=payload.get("feed_baseline", {}),
    )


def _legacy_sources() -> set[str]:
    lines = LEGACY_MANIFEST.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    source_index = header.index("source")
    return {line.split("\t")[source_index] for line in lines[1:] if line}


def _parse_metadata(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    try:
        header, body = re.split(r"\r?\n\r?\n", raw, maxsplit=1)
    except ValueError as error:
        raise Site005MetadataMismatch(
            path.name, "metadata has no terminating blank line"
        ) from error
    metadata: dict[str, str] = {}
    for line in header.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            raise Site005MetadataMismatch(path.name, f"invalid metadata line {line!r}")
        key = match.group(1).casefold()
        if key in metadata:
            raise Site005MetadataMismatch(path.name, f"duplicate metadata {key!r}")
        metadata[key] = match.group(2).strip()
    return metadata, body


def _validate_source(item: Material, content_root: Path) -> dict[str, Any]:
    source_path = content_root / item.source
    if not source_path.is_file():
        raise MissingSite005Source(item.source, "declared source is absent")
    metadata, body = _parse_metadata(source_path)
    companion = item.payload.get("companion", {})
    expected = {
        "author": item.author,
        "canonical": item.canonical_url,
        "date": item.published.replace("T", " "),
        "lang": item.language,
        "save_as": item.route.lstrip("/"),
        "site005_companion_description": str(companion.get("description", "")),
        "site005_companion_route": item.companion_route,
        "site005_companion_title": str(companion.get("title", "")),
        "site005_material": "true",
        "site005_role": item.role,
        "slug": item.slug,
        "status": "hidden",
        "summary": item.description,
        "title": item.title,
        "url": item.route.lstrip("/"),
    }
    for key, expected_value in expected.items():
        if metadata.get(key) != expected_value:
            raise Site005MetadataMismatch(
                item.source,
                f"field={key!r} expected={expected_value!r} actual={metadata.get(key)!r}",
            )
    if INSTALL_NOISE in body:
        raise Site005MetadataMismatch(item.source, "install-noise literal is present")
    if "~~~mermaid" in body or "```mermaid" in body:
        raise Site005MetadataMismatch(item.source, "Mermaid runtime source remains")
    if (
        "ai_native_delivery_contract_template.md" in body
        or "logistics_distributed_systems_case_study.md" in body
    ):
        raise Site005MetadataMismatch(item.source, "source filename link remains")
    figure_count = body.count('<figure class="article-diagram"')
    if figure_count != (1 if item.figure else 0):
        raise Site005MetadataMismatch(
            item.source, f"expected {1 if item.figure else 0} static figure(s)"
        )
    if item.figure:
        for value in (item.figure["aria_label"], item.figure["caption"]):
            if str(value) not in body:
                raise Site005MetadataMismatch(item.source, "static figure semantics differ")
    if item.slug == "ai-native-delivery-contract":
        if (
            "<problem statement>" not in body
            or "&lt;explicitly excluded outcome or scope&gt;" not in body
        ):
            raise Site005MetadataMismatch(item.source, "visible placeholders are not escaped")
    expected_source_sha = item.payload.get("source_sha256")
    if expected_source_sha and _sha256(source_path) != expected_source_sha:
        raise Site005MetadataMismatch(item.source, "transformed source hash differs")
    return {
        "body_sha256": _sha256_bytes(body.encode("utf-8")),
        "figure_count": figure_count,
        "metadata_fields": len(metadata),
        "source_sha256": _sha256(source_path),
    }


def _validate_asset(manifest: Manifest, content_root: Path) -> dict[str, Any]:
    asset = manifest.asset
    path = REPO_ROOT / str(asset.get("path", ""))
    if content_root != CONTENT_ROOT:
        path = content_root / Path(str(asset.get("path", ""))).relative_to("content")
    if not path.is_file():
        raise Site005AssetMismatch(path.as_posix(), "social asset is missing")
    actual = {
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    expected = {key: asset.get(key) for key in ("bytes", "sha256")}
    if actual != expected:
        raise Site005AssetMismatch(path.as_posix(), f"expected={expected!r} actual={actual!r}")
    with Image.open(path) as image:
        size = image.size
    if size != (1200, 630):
        raise Site005AssetMismatch(path.as_posix(), f"expected 1200x630, observed {size!r}")
    return {**actual, "dimensions": [1200, 630]}


def validate_inventory(
    *,
    content_root: Path = CONTENT_ROOT,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    """Require the exact 46-source legacy corpus plus six declared hidden sources."""

    manifest = load_manifest(manifest_path)
    legacy = _legacy_sources()
    declared = {item.source for item in manifest.materials}
    actual = {
        path.name
        for pattern in ("*.md", "*.ipynb")
        for path in content_root.glob(pattern)
        if path.is_file()
    }
    missing = sorted((legacy | declared) - actual)
    unexpected = sorted(actual - legacy - declared)
    if missing:
        raise MissingSite005Source(missing[0], f"missing sources={missing!r}")
    if unexpected:
        raise UndeclaredSite005Source(unexpected[0], f"unexpected sources={unexpected!r}")
    sources = {
        item.source: _validate_source(item, content_root) for item in manifest.materials
    }
    return {
        "asset": _validate_asset(manifest, content_root),
        "counts": {
            "legacy_markdown": 35,
            "legacy_notebooks": 11,
            "site005_hidden_markdown": 6,
        },
        "materials": sources,
        "production_commit": manifest.production_commit,
        "site_base_commit": manifest.site_base_commit,
    }


def _normalized_text(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def semantic_snapshot(soup: BeautifulSoup) -> dict[str, Any]:
    """Theme-independent semantic groups used by the frozen rendered contract."""

    main = soup.find("main") or soup.body
    if main is None:
        return {}
    paragraphs = []
    for paragraph in main.find_all("p"):
        classes = set(paragraph.get("class") or ())
        if classes & {"eyebrow", "lede", "site-content-language"}:
            continue
        paragraphs.append(_normalized_text(paragraph))
    code = [
        "\n".join(line.strip() for line in block.get_text().strip().splitlines())
        for block in main.select("pre code")
    ]
    tables = []
    for table in main.find_all("table"):
        rows = table.find_all("tr")
        tables.append(
            [
                len(rows),
                max((len(row.find_all(["th", "td"])) for row in rows), default=0),
            ]
        )
    return {
        "code_sha256": _canonical_hash(code),
        "headings_sha256": _canonical_hash(
            [[tag.name, _normalized_text(tag)] for tag in main.find_all(["h1", "h2", "h3"])]
        ),
        "paragraphs_sha256": _canonical_hash(paragraphs),
        "table_shapes": tables,
        "visible_placeholders": sorted(
            set(re.findall(r"<[^<>\n]+>", main.get_text("\n", strip=True)))
        ),
    }


def _meta(soup: BeautifulSoup, *, name: str | None = None, prop: str | None = None) -> str | None:
    attrs = {"name": name} if name else {"property": prop}
    tag = soup.find("meta", attrs=attrs)
    return str(tag.get("content")) if tag and tag.get("content") is not None else None


def _canonical(soup: BeautifulSoup) -> str | None:
    tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    return str(tag.get("href")) if tag and tag.get("href") is not None else None


def _validate_metadata(item: Material, soup: BeautifulSoup) -> dict[str, Any]:
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    expected_title = f"{item.title} — Pavel Nekrasov"
    expected = {
        "canonical": item.canonical_url,
        "description": item.description,
        "og:description": item.description,
        "og:image": SOCIAL_IMAGE,
        "og:image:alt": SOCIAL_IMAGE_ALT,
        "og:title": item.title,
        "og:type": "article",
        "og:url": item.canonical_url,
        "title": expected_title,
        "twitter:card": "summary_large_image",
        "twitter:image": SOCIAL_IMAGE,
    }
    actual = {
        "canonical": _canonical(soup),
        "description": _meta(soup, name="description"),
        "og:description": _meta(soup, prop="og:description"),
        "og:image": _meta(soup, prop="og:image"),
        "og:image:alt": _meta(soup, prop="og:image:alt"),
        "og:title": _meta(soup, prop="og:title"),
        "og:type": _meta(soup, prop="og:type"),
        "og:url": _meta(soup, prop="og:url"),
        "title": title,
        "twitter:card": _meta(soup, name="twitter:card"),
        "twitter:image": _meta(soup, name="twitter:image"),
    }
    if actual != expected:
        raise Site005RenderedMismatch(
            item.source, f"head metadata expected={expected!r} actual={actual!r}"
        )
    expected_selectors = {
        "link[rel='canonical']": 1,
        "meta[name='description']": 1,
        "meta[name='twitter:card']": 1,
        "meta[name='twitter:image']": 1,
        "meta[property='og:description']": 1,
        "meta[property='og:image']": 1,
        "meta[property='og:image:alt']": 1,
        "meta[property='og:title']": 1,
        "meta[property='og:type']": 1,
        "meta[property='og:url']": 1,
    }
    observed_counts = {
        selector: len(soup.select(selector)) for selector in expected_selectors
    }
    if observed_counts != expected_selectors:
        raise Site005RenderedMismatch(
            item.source,
            f"head tag counts expected={expected_selectors!r} actual={observed_counts!r}",
        )
    forbidden_selectors = (
        "meta[name='twitter:description']",
        "meta[name='twitter:title']",
        "meta[property='article:published_time']",
        "meta[property='article:section']",
        "meta[property='article:tag']",
    )
    forbidden = [selector for selector in forbidden_selectors if soup.select(selector)]
    if forbidden:
        raise Site005RenderedMismatch(
            item.source, f"unexpected frozen-head tags are present: {forbidden!r}"
        )
    scripts = soup.find_all("script", type="application/ld+json")
    if len(scripts) != 1:
        raise Site005RenderedMismatch(item.source, "expected exactly one JSON-LD object")
    try:
        schema = json.loads(scripts[0].string or "")
    except json.JSONDecodeError as error:
        raise Site005RenderedMismatch(item.source, f"invalid JSON-LD: {error}") from error
    expected_schema = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "author": {
            "@type": "Person",
            "name": "Pavel Nekrasov",
            "url": f"{SITEURL}/",
        },
        "datePublished": "2026-07-15",
        "description": item.description,
        "headline": item.title,
        "image": SOCIAL_IMAGE,
        "inLanguage": "en",
        "mainEntityOfPage": item.canonical_url,
    }
    if schema != expected_schema:
        raise Site005RenderedMismatch(
            item.source, f"JSON-LD expected={expected_schema!r} actual={schema!r}"
        )
    return {"head": actual, "json_ld_sha256": _canonical_hash(schema)}


def _entry_snapshot(entry: ET.Element) -> dict[str, Any]:
    def text(name: str) -> str | None:
        element = entry.find(f"atom:{name}", ATOM_NS)
        return element.text if element is not None else None

    author = entry.find("atom:author/atom:name", ATOM_NS)
    link = entry.find("atom:link[@rel='alternate']", ATOM_NS)
    summary = entry.find("atom:summary", ATOM_NS)
    return {
        "author": author.text if author is not None else None,
        "categories": [node.get("term") for node in entry.findall("atom:category", ATOM_NS)],
        "content_present": entry.find("atom:content", ATOM_NS) is not None,
        "id": text("id"),
        "link": link.get("href") if link is not None else None,
        "published": text("published"),
        "summary": summary.text if summary is not None else None,
        "summary_type": summary.get("type") if summary is not None else None,
        "title": text("title"),
        "updated": text("updated"),
    }


def feed_snapshot(path: Path) -> list[dict[str, Any]]:
    root = ET.fromstring(path.read_bytes())
    return [_entry_snapshot(entry) for entry in root.findall("atom:entry", ATOM_NS)]


def _validate_feeds(output_root: Path, manifest: Manifest) -> dict[str, Any]:
    all_path = output_root / "feeds/all.atom.xml"
    blog_path = output_root / "feeds/blog.atom.xml"
    if not all_path.is_file() or not blog_path.is_file():
        raise Site005RenderedMismatch("feeds", "required Atom feed is missing")
    entries = feed_snapshot(all_path)
    if len(entries) != EXPECTED_ALL_FEED_ENTRIES:
        raise Site005RenderedMismatch(
            "feeds/all.atom.xml",
            f"expected {EXPECTED_ALL_FEED_ENTRIES} total entries, observed {len(entries)}",
        )
    expected = []
    for item in manifest.materials:
        if item.feed is None:
            continue
        expected.append(
            {
                "author": "Pavel Nekrasov",
                "categories": list(item.feed["tags"]),
                "content_present": False,
                "id": item.feed["id"],
                "link": item.canonical_url,
                "published": item.published,
                "summary": f"<p>{item.feed['summary']}</p>",
                "summary_type": "html",
                "title": item.feed["title"],
                "updated": item.published,
            }
        )
    if entries[:3] != expected:
        raise Site005RenderedMismatch(
            "feeds/all.atom.xml", f"essay feed entries differ: {entries[:3]!r}"
        )
    declared_ids = {entry["id"] for entry in expected}
    companion_routes = {
        item.canonical_url for item in manifest.materials if item.role == "companion"
    }
    if any(entry["link"] in companion_routes for entry in entries):
        raise Site005RenderedMismatch("feeds/all.atom.xml", "companion entered the feed")
    if sum(entry["id"] in declared_ids for entry in entries) != EXPECTED_ESSAYS:
        raise Site005RenderedMismatch("feeds/all.atom.xml", "essay feed delta is not exactly three")
    baseline = manifest.feed_baseline
    legacy_hash = _canonical_hash(
        [entry for entry in entries if entry["id"] not in declared_ids]
    )
    if len(entries) - len(declared_ids) != EXPECTED_LEGACY_ENTRIES:
        raise Site005RenderedMismatch(
            "feeds/all.atom.xml", "legacy feed cardinality changed"
        )
    if baseline and legacy_hash != baseline.get("all_atom_legacy_entries_sha256"):
        raise Site005RenderedMismatch("feeds/all.atom.xml", "legacy feed entries changed")
    blog_entries = feed_snapshot(blog_path)
    if len(blog_entries) != EXPECTED_LEGACY_ENTRIES:
        raise Site005RenderedMismatch(
            "feeds/blog.atom.xml", "blog feed cardinality changed"
        )
    blog_sha = _canonical_hash(blog_entries)
    if baseline and blog_sha != baseline.get("blog_entries_sha256"):
        raise Site005RenderedMismatch("feeds/blog.atom.xml", "blog feed records changed")
    return {
        "all_entries": len(entries),
        "blog_entries_sha256": blog_sha,
        "essay_delta": len(declared_ids),
        "legacy_entries_sha256": legacy_hash,
    }


def _require_resolved_internal_links(output_root: Path, soup: BeautifulSoup, source: str) -> None:
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if not href.startswith("/") or href.startswith("//"):
            continue
        target = href.split("#", 1)[0].split("?", 1)[0]
        if not target or target == "/":
            continue
        path = output_root / target.lstrip("/")
        if target.endswith("/"):
            path /= "index.html"
        if not path.is_file():
            raise Site005RenderedMismatch(source, f"unresolved internal link {href!r}")


def _validate_legacy_notices(output_root: Path) -> dict[str, dict[str, Any]]:
    expected = {
        "what-is-technical-debt.html": {
            "links": [
                "/technical-debt-as-a-portfolio.html",
                "/technical-debt-portfolio-register.html",
            ],
            "text": (
                "Обновление, июль 2026. Продолжение темы: англоязычная статья "
                "Technical Debt as a Portfolio, Not a Backlog и практический "
                "реестр технического долга ."
            ),
        },
        "technical-debt-examples.html": {
            "links": [
                "/technical-debt-as-a-portfolio.html",
                "/technical-debt-portfolio-register.html",
            ],
            "text": (
                "Обновление, июль 2026. Новая англоязычная статья "
                "Technical Debt as a Portfolio, Not a Backlog показывает, как "
                "превратить такие примеры в управляемый портфель рисков; рядом "
                "доступен готовый шаблон реестра ."
            ),
        },
    }
    for route, record in expected.items():
        soup = BeautifulSoup((output_root / route).read_text(encoding="utf-8"), "html.parser")
        notice = soup.find(class_="site005-update-notice")
        if notice is None:
            raise Site005RenderedMismatch(route, "technical-debt update notice is missing")
        actual_text = _normalized_text(notice)
        actual_links = [str(link["href"]) for link in notice.find_all("a", href=True)]
        if actual_text != record["text"] or actual_links != record["links"]:
            raise Site005RenderedMismatch(
                route,
                f"notice expected={record!r} "
                f"actual={{'text': {actual_text!r}, 'links': {actual_links!r}}}",
            )
    return expected


def _validate_collection_absence(output_root: Path, manifest: Manifest) -> list[str]:
    candidates = {
        output_root / "index.html",
        output_root / "archives.html",
        output_root / "authors.html",
        output_root / "categories.html",
        output_root / "tags.html",
    }
    for directory in ("author", "category", "tag"):
        candidates.update((output_root / directory).glob("*.html"))
    routes = {item.route for item in manifest.materials}
    checked = []
    for path in sorted(candidates):
        if not path.is_file():
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        links = {str(link.get("href")) for link in soup.find_all("a", href=True)}
        leaked = sorted(routes & links)
        if leaked:
            raise Site005RenderedMismatch(path.name, f"hidden route leaked: {leaked!r}")
        checked.append(path.relative_to(output_root).as_posix())
    return checked


def validate_output(
    *,
    output_root: Path,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    """Validate all six hidden routes, feed delta, graph, and legacy notices."""

    manifest = load_manifest(manifest_path)
    output_asset = output_root / str(manifest.asset["production_path"])
    if not output_asset.is_file():
        raise Site005AssetMismatch(
            output_asset.as_posix(), "generated social asset is missing"
        )
    output_asset_evidence = {
        "bytes": output_asset.stat().st_size,
        "sha256": _sha256(output_asset),
    }
    expected_asset_evidence = {
        key: manifest.asset[key] for key in ("bytes", "sha256")
    }
    if output_asset_evidence != expected_asset_evidence:
        raise Site005AssetMismatch(
            output_asset.as_posix(),
            f"expected={expected_asset_evidence!r} actual={output_asset_evidence!r}",
        )
    with Image.open(output_asset) as image:
        if image.size != (1200, 630):
            raise Site005AssetMismatch(
                output_asset.as_posix(),
                f"expected 1200x630, observed {image.size!r}",
            )
    materials: dict[str, Any] = {}
    for item in manifest.materials:
        path = output_root / item.route.lstrip("/")
        if not path.is_file():
            raise Site005RenderedMismatch(item.source, f"missing route {item.route!r}")
        raw = path.read_text(encoding="utf-8")
        if INSTALL_NOISE in raw:
            raise Site005RenderedMismatch(item.source, "install-noise literal is rendered")
        if re.search(r"https?://(?:cdn\\.|unpkg|jsdelivr|mermaid)", raw, re.I):
            raise Site005RenderedMismatch(item.source, "external runtime dependency is rendered")
        soup = BeautifulSoup(raw, "html.parser")
        html = soup.find("html")
        if html is None or html.get("lang") != item.language:
            raise Site005RenderedMismatch(item.source, "document language differs")
        metadata = _validate_metadata(item, soup)
        snapshot = semantic_snapshot(soup)
        expected_snapshot = item.rendered
        for key in (
            "code_sha256",
            "headings_sha256",
            "paragraphs_sha256",
            "table_shapes",
            "visible_placeholders",
        ):
            if expected_snapshot and snapshot.get(key) != expected_snapshot.get(key):
                raise Site005RenderedMismatch(
                    item.source,
                    f"semantic group {key!r} expected={expected_snapshot.get(key)!r} "
                    f"actual={snapshot.get(key)!r}",
                )
        figures = soup.find_all("figure", class_="article-diagram")
        if len(figures) != (1 if item.figure else 0):
            raise Site005RenderedMismatch(item.source, "static figure count differs")
        if item.figure:
            figure = figures[0]
            caption = figure.find("figcaption")
            if (
                figure.get("aria-label") != item.figure["aria_label"]
                or caption is None
                or _normalized_text(caption) != item.figure["caption"]
            ):
                raise Site005RenderedMismatch(item.source, "static figure meaning differs")
        aside = soup.find("aside", class_="article-related")
        companion = item.payload.get("companion", {})
        if aside is None:
            raise Site005RenderedMismatch(item.source, "companion aside is missing")
        aside_link = aside.find("a")
        aside_paragraphs = aside.find_all("p")
        if (
            aside_link is None
            or aside_link.get("href") != item.companion_route
            or _normalized_text(aside_link) != companion.get("title")
            or not aside_paragraphs
            or _normalized_text(aside_paragraphs[-1]) != companion.get("description")
        ):
            raise Site005RenderedMismatch(item.source, "companion aside differs")
        _require_resolved_internal_links(output_root, soup, item.source)
        materials[item.route] = {**metadata, "semantic": snapshot}
    graph = {item.route: item.companion_route for item in manifest.materials}
    for source, target in graph.items():
        if graph.get(target) != source:
            raise Site005RenderedMismatch(source, "companion graph is not reciprocal")
    return {
        "asset": {**output_asset_evidence, "dimensions": [1200, 630]},
        "collection_pages_checked": _validate_collection_absence(output_root, manifest),
        "feeds": _validate_feeds(output_root, manifest),
        "legacy_notices": _validate_legacy_notices(output_root),
        "materials": materials,
        "reciprocal_companion_graph": graph,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--content-root", type=Path, default=CONTENT_ROOT)
    result.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    result.add_argument("--output-root", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        inventory = validate_inventory(
            content_root=args.content_root.resolve(),
            manifest_path=args.manifest.resolve(),
        )
        if args.output_root:
            output = validate_output(
                output_root=args.output_root.resolve(),
                manifest_path=args.manifest.resolve(),
            )
            print(
                "SITE-005 validation passed: "
                f"{len(output['materials'])} hidden materials, "
                f"{output['feeds']['essay_delta']} essay feed entries"
            )
        else:
            print(
                "SITE-005 pre-Pelican validation passed: "
                f"{inventory['counts']['site005_hidden_markdown']} declared hidden sources"
            )
        return 0
    except Site005ValidationError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
