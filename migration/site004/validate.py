"""Validate SITE-004 source ownership and rendered semantic parity."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"
TEMPLATES_ROOT = REPO_ROOT / "templates"
CONFIG_PATH = REPO_ROOT / "pelicanconf.py"
MANIFEST_PATH = REPO_ROOT / "migration/site004/pages.json"
SITEURL = "https://nekrasovp.ru"
SITE_BASE_COMMIT = "2f91ab0fe347e8c7bc26fa08943d068397ca83a7"
PRODUCTION_COMMIT = "5c24ba21ec8b442e4b5280a47c85fab61165f8ce"
THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
EXPECTED_OUTPUTS = {
    "index.html",
    "ru/index.html",
    "work/index.html",
    "writing/index.html",
    "about/index.html",
    "404.html",
    "pages/about.html",
    "pages/services.html",
}
EXPECTED_PAGE_SOURCES = {
    "content/pages/Ru.md",
    "content/pages/Work.md",
    "content/pages/Writing.md",
    "content/pages/About.md",
}


class Site004ValidationError(RuntimeError):
    """Stable SITE-004 failure with source and stage context."""

    error_code = "validation_error"
    stage = "source_validation"

    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        super().__init__(
            "SITE-004 validation failed: "
            f"source={source!r} stage={self.stage} error_code={self.error_code} "
            f"error_type={type(self).__name__} {message}"
        )


class InvalidSite004Manifest(Site004ValidationError):
    error_code = "invalid_manifest"


class MissingSite004Owner(Site004ValidationError):
    error_code = "missing_owner"


class DuplicateSite004Writer(Site004ValidationError):
    error_code = "duplicate_writer"


class Site004MetadataMismatch(Site004ValidationError):
    error_code = "metadata_mismatch"


class Site004RenderedMismatch(Site004ValidationError):
    error_code = "rendered_mismatch"
    stage = "rendered_validation"


class Site004UnresolvedLink(Site004ValidationError):
    error_code = "unresolved_internal_link"
    stage = "link_validation"


@dataclass(frozen=True)
class OutputRecord:
    payload: Mapping[str, Any]

    @property
    def output(self) -> str:
        return str(self.payload["output"])

    @property
    def route(self) -> str:
        return str(self.payload["route"])

    @property
    def owner(self) -> str:
        return str(self.payload["owner"])

    @property
    def kind(self) -> str:
        return str(self.payload["kind"])


@dataclass(frozen=True)
class Manifest:
    outputs: tuple[OutputRecord, ...]
    required_generated_routes: tuple[str, ...]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_manifest(path: Path = MANIFEST_PATH) -> Manifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise InvalidSite004Manifest(path.as_posix(), str(error)) from error
    if payload.get("contract") != "nekrasovp-site004-pages.v1":
        raise InvalidSite004Manifest(path.as_posix(), "unknown contract")
    expected_provenance = {
        "production_commit": PRODUCTION_COMMIT,
        "site_base_commit": SITE_BASE_COMMIT,
        "theme_commit": THEME_COMMIT,
    }
    if payload.get("frozen_provenance") != expected_provenance:
        raise InvalidSite004Manifest(
            path.as_posix(),
            f"frozen provenance expected={expected_provenance!r} "
            f"actual={payload.get('frozen_provenance')!r}",
        )
    records = payload.get("outputs")
    if not isinstance(records, list) or len(records) != 8:
        raise InvalidSite004Manifest(path.as_posix(), "expected exactly eight outputs")
    outputs = tuple(OutputRecord(record) for record in records if isinstance(record, dict))
    if len(outputs) != 8 or {record.output for record in outputs} != EXPECTED_OUTPUTS:
        raise InvalidSite004Manifest(path.as_posix(), "output set differs")
    if len({record.route for record in outputs}) != 8:
        raise InvalidSite004Manifest(path.as_posix(), "routes must be unique")
    if [record.kind for record in outputs].count("redirect") != 2:
        raise InvalidSite004Manifest(path.as_posix(), "expected exactly two redirects")
    required = payload.get("required_generated_routes")
    if not isinstance(required, list) or len(required) != 8:
        raise InvalidSite004Manifest(
            path.as_posix(), "expected six SITE-005 and two legacy required routes"
        )
    return Manifest(outputs=outputs, required_generated_routes=tuple(map(str, required)))


def _parse_metadata(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    try:
        header, body = re.split(r"\r?\n\r?\n", raw, maxsplit=1)
    except ValueError as error:
        raise Site004MetadataMismatch(
            path.as_posix(), "metadata has no terminating blank line"
        ) from error
    metadata: dict[str, str] = {}
    for line in header.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            raise Site004MetadataMismatch(
                path.as_posix(), f"invalid metadata line {line!r}"
            )
        key = match.group(1).casefold()
        if key in metadata:
            raise Site004MetadataMismatch(path.as_posix(), f"duplicate metadata {key!r}")
        metadata[key] = match.group(2).strip()
    return metadata, body


def _slugify_filename(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.casefold()).strip("-")


def _page_output(path: Path, metadata: Mapping[str, str]) -> str:
    save_as = metadata.get("save_as")
    if save_as:
        return save_as.lstrip("/")
    slug = metadata.get("slug") or _slugify_filename(path)
    return f"pages/{slug}.html"


def _literal_assignment(path: Path, name: str) -> Any:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    matches = [
        node.value
        for node in module.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )
        if isinstance(target, ast.Name) and target.id == name
    ]
    if not matches:
        return None
    try:
        return ast.literal_eval(matches[-1])
    except Exception as error:
        raise Site004MetadataMismatch(
            path.as_posix(), f"{name} must be a literal assignment"
        ) from error


def _collect_writers(
    *,
    content_root: Path,
    templates_root: Path,
    config_path: Path,
) -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    writers: dict[str, list[str]] = {}
    page_metadata: dict[str, dict[str, str]] = {}
    pages_root = content_root / "pages"
    for page_path in sorted(pages_root.glob("*.md")) if pages_root.is_dir() else ():
        metadata, _body = _parse_metadata(page_path)
        output = _page_output(page_path, metadata)
        relative = page_path.relative_to(content_root.parent).as_posix()
        writers.setdefault(output, []).append(relative)
        page_metadata[relative] = metadata

    index_path = templates_root / "index.html"
    if index_path.is_file():
        writers.setdefault("index.html", []).append(
            index_path.relative_to(templates_root.parent).as_posix()
        )
    else:
        writers.setdefault("index.html", []).append("!theme/index.html")

    template_pages = _literal_assignment(config_path, "TEMPLATE_PAGES")
    if template_pages is None:
        template_pages = {}
    if not isinstance(template_pages, dict):
        raise Site004MetadataMismatch(
            config_path.as_posix(), "TEMPLATE_PAGES must be a literal dict"
        )
    for template_name, output in template_pages.items():
        if not isinstance(template_name, str) or not isinstance(output, str):
            raise Site004MetadataMismatch(
                config_path.as_posix(), "TEMPLATE_PAGES keys and values must be strings"
            )
        owner = (templates_root / template_name).relative_to(
            templates_root.parent
        ).as_posix()
        writers.setdefault(output.lstrip("/"), []).append(owner)
    return writers, page_metadata


def _require_theme_extension(path: Path, target: str) -> None:
    if not path.is_file():
        raise MissingSite004Owner(path.as_posix(), "declared template is absent")
    first_nonempty = next(
        (line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()),
        "",
    )
    if first_nonempty != f'{{% extends "!theme/{target}" %}}':
        raise Site004MetadataMismatch(
            path.as_posix(), f"must extend !theme/{target} through the public block contract"
        )


def validate_inventory(
    *,
    repo_root: Path = REPO_ROOT,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path or repo_root / "migration/site004/pages.json")
    content_root = repo_root / "content"
    templates_root = repo_root / "templates"
    config_path = repo_root / "pelicanconf.py"
    writers, page_metadata = _collect_writers(
        content_root=content_root,
        templates_root=templates_root,
        config_path=config_path,
    )
    for output, owners in writers.items():
        if output in EXPECTED_OUTPUTS and len(owners) != 1:
            raise DuplicateSite004Writer(
                output, f"expected one writer, found {owners!r}"
            )
    for record in manifest.outputs:
        owners = writers.get(record.output, [])
        if owners != [record.owner]:
            error_type = DuplicateSite004Writer if len(owners) > 1 else MissingSite004Owner
            raise error_type(
                record.output,
                f"expected owner={record.owner!r} actual={owners!r}",
            )
        source_metadata = record.payload.get("source_metadata")
        if isinstance(source_metadata, dict):
            actual = page_metadata.get(record.owner)
            if actual is None:
                raise MissingSite004Owner(record.owner, "declared Page source is absent")
            for key, expected in source_metadata.items():
                if actual.get(key) != expected:
                    raise Site004MetadataMismatch(
                        record.owner,
                        f"field={key!r} expected={expected!r} actual={actual.get(key)!r}",
                    )

    page_sources = set(page_metadata)
    if page_sources != EXPECTED_PAGE_SOURCES:
        raise Site004MetadataMismatch(
            "content/pages",
            f"expected explicit Page sources={sorted(EXPECTED_PAGE_SOURCES)!r} "
            f"actual={sorted(page_sources)!r}",
        )
    _require_theme_extension(templates_root / "index.html", "index.html")
    _require_theme_extension(templates_root / "site004_page.html", "page.html")
    _require_theme_extension(templates_root / "site004/404.html", "base.html")
    for redirect in (
        templates_root / "site004/redirect-about.html",
        templates_root / "site004/redirect-services.html",
    ):
        if not redirect.is_file():
            raise MissingSite004Owner(redirect.as_posix(), "redirect template is absent")
        text = redirect.read_text(encoding="utf-8")
        if "{% extends" in text or "data-pet-theme-loader" in text:
            raise Site004MetadataMismatch(
                redirect.as_posix(), "redirect must remain a minimal standalone document"
            )
    return {
        "outputs": len(manifest.outputs),
        "page_sources": len(page_sources),
        "writers": {
            key: value
            for key, value in sorted(writers.items())
            if key in EXPECTED_OUTPUTS
        },
    }


def _meta_map(soup: BeautifulSoup, attribute: str, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = tag.get(attribute)
        if not isinstance(key, str) or not key.startswith(prefix):
            continue
        content = tag.get("content")
        if key in result or not isinstance(content, str):
            raise Site004RenderedMismatch(key, "duplicate or invalid metadata")
        result[key] = content
    return result


def _canonical(soup: BeautifulSoup) -> str | None:
    links = soup.find_all("link", rel=lambda value: value and "canonical" in value)
    if len(links) > 1:
        raise Site004RenderedMismatch("canonical", "multiple canonical links")
    return str(links[0].get("href")) if links else None


def _hreflang(soup: BeautifulSoup) -> dict[str, str]:
    result: dict[str, str] = {}
    for link in soup.find_all("link", rel=lambda value: value and "alternate" in value):
        language = link.get("hreflang")
        href = link.get("href")
        if isinstance(language, str) and isinstance(href, str):
            if language in result:
                raise Site004RenderedMismatch("hreflang", f"duplicate {language!r}")
            result[language] = href
    return result


def _jsonld(soup: BeautifulSoup) -> list[Any]:
    values: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            values.append(json.loads(script.get_text()))
        except Exception as error:
            raise Site004RenderedMismatch("jsonld", str(error)) from error
    return values


def _content_node(soup: BeautifulSoup, kind: str) -> Tag:
    node = soup.body if kind == "redirect" else soup.main
    if not isinstance(node, Tag):
        raise Site004RenderedMismatch(kind, "content root is missing")
    return node


def _hrefs(node: Tag) -> list[str]:
    return sorted({str(tag["href"]) for tag in node.find_all("a", href=True)})


def validate_rendered_record(record: OutputRecord, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Site004RenderedMismatch(record.output, "expected output is missing")
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    html = soup.html
    if not isinstance(html, Tag) or html.get("lang") != record.payload["lang"]:
        raise Site004RenderedMismatch(
            record.output,
            f"html lang expected={record.payload['lang']!r} "
            f"actual={html.get('lang') if isinstance(html, Tag) else None!r}",
        )
    title = soup.title.get_text(strip=True) if soup.title else None
    if title != record.payload["title"]:
        raise Site004RenderedMismatch(
            record.output, f"title expected={record.payload['title']!r} actual={title!r}"
        )
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content") if description_tag else None
    if description != record.payload.get("description"):
        raise Site004RenderedMismatch(
            record.output,
            f"description expected={record.payload.get('description')!r} "
            f"actual={description!r}",
        )
    canonical = _canonical(soup)
    if canonical != record.payload.get("canonical"):
        raise Site004RenderedMismatch(
            record.output,
            f"canonical expected={record.payload.get('canonical')!r} actual={canonical!r}",
        )
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots = robots_tag.get("content") if robots_tag else None
    if robots != record.payload.get("robots"):
        raise Site004RenderedMismatch(
            record.output,
            f"robots expected={record.payload.get('robots')!r} actual={robots!r}",
        )
    actual_og = _meta_map(soup, "property", "og:")
    actual_twitter = _meta_map(soup, "name", "twitter:")
    if actual_og != record.payload["og"]:
        raise Site004RenderedMismatch(
            record.output, f"Open Graph expected={record.payload['og']!r} actual={actual_og!r}"
        )
    if actual_twitter != record.payload["twitter"]:
        raise Site004RenderedMismatch(
            record.output,
            f"Twitter expected={record.payload['twitter']!r} actual={actual_twitter!r}",
        )
    if _hreflang(soup) != record.payload["hreflang"]:
        raise Site004RenderedMismatch(record.output, "hreflang group differs")
    if _jsonld(soup) != record.payload["jsonld"]:
        raise Site004RenderedMismatch(record.output, "structured data differs")

    node = _content_node(soup, record.kind)
    text = " ".join(node.stripped_strings)
    if _sha256_text(text) != record.payload["content_text_sha256"]:
        raise Site004RenderedMismatch(record.output, "approved normalized copy differs")
    headings = [
        heading.get_text(" ", strip=True) for heading in node.find_all(("h1", "h2", "h3"))
    ]
    if headings != record.payload["headings"]:
        raise Site004RenderedMismatch(record.output, "heading sequence differs")
    if _hrefs(node) != record.payload["content_hrefs"]:
        raise Site004RenderedMismatch(record.output, "content href set differs")

    if record.kind == "redirect":
        refresh = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
        expected_refresh = f"0; url={record.payload['redirect_target']}"
        if not refresh or refresh.get("content") != expected_refresh:
            raise Site004RenderedMismatch(
                record.output,
                f"redirect expected={expected_refresh!r} "
                f"actual={refresh.get('content') if refresh else None!r}",
            )
    header = soup.find("header")
    footer = soup.find("footer")
    navigation = _hrefs(header) if isinstance(header, Tag) else []
    footer_hrefs = _hrefs(footer) if isinstance(footer, Tag) else []
    if navigation != record.payload["navigation_hrefs"]:
        raise Site004RenderedMismatch(record.output, "navigation href set differs")
    if footer_hrefs != record.payload["footer_hrefs"]:
        raise Site004RenderedMismatch(record.output, "footer href set differs")
    return {
        "content_text_sha256": _sha256_text(text),
        "headings": len(headings),
        "hrefs": len(_hrefs(node)),
        "jsonld": len(record.payload["jsonld"]),
        "output": record.output,
    }


def _route_to_output(path: str) -> str:
    decoded = unquote(path)
    if decoded == "/":
        return "index.html"
    if decoded.endswith("/"):
        return decoded.lstrip("/") + "index.html"
    return decoded.lstrip("/")


def _resolve_anchor(
    *,
    output_root: Path,
    source_output: str,
    href: str,
    check_fragment: bool = True,
) -> None:
    split = urlsplit(href)
    if split.scheme in {"mailto", "tel"}:
        return
    if split.scheme in {"http", "https"}:
        if split.netloc not in {"nekrasovp.ru", "www.nekrasovp.ru"}:
            return
        path = split.path
    elif split.scheme or split.netloc:
        return
    else:
        path = split.path
    if not path:
        target_output = source_output
    elif path.startswith("/"):
        target_output = _route_to_output(path)
    else:
        base = Path(source_output).parent
        target_output = (base / unquote(path)).as_posix()
        if target_output.endswith("/"):
            target_output += "index.html"
    target = output_root / target_output
    if not target.is_file():
        raise Site004UnresolvedLink(
            source_output, f"href={href!r} expected_output={target_output!r}"
        )
    if check_fragment and split.fragment and target.suffix == ".html":
        soup = BeautifulSoup(target.read_bytes(), "html.parser")
        if soup.find(id=unquote(split.fragment)) is None:
            raise Site004UnresolvedLink(
                source_output, f"href={href!r} fragment target is absent"
            )


def validate_internal_links(
    *,
    output_root: Path,
    manifest: Manifest,
) -> dict[str, Any]:
    required_outputs = {
        _route_to_output(route) for route in manifest.required_generated_routes
    }
    missing_required = sorted(
        output for output in required_outputs if not (output_root / output).is_file()
    )
    if missing_required:
        raise Site004UnresolvedLink(
            "required_generated_routes", f"missing={missing_required!r}"
        )
    checked_documents = {record.output for record in manifest.outputs} | required_outputs
    site004_outputs = {record.output for record in manifest.outputs}
    checked_links = 0
    for source_output in sorted(checked_documents):
        source = output_root / source_output
        if not source.is_file() or source.suffix != ".html":
            continue
        soup = BeautifulSoup(source.read_bytes(), "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            _resolve_anchor(
                output_root=output_root,
                source_output=source_output,
                href=href,
                check_fragment=source_output in site004_outputs,
            )
            checked_links += 1
    return {
        "checked_documents": len(checked_documents),
        "checked_links": checked_links,
        "required_generated_routes": len(required_outputs),
    }


def validate_rendered(
    output_root: Path,
    *,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    records = [
        validate_rendered_record(record, output_root / record.output)
        for record in manifest.outputs
    ]
    return {
        "links": validate_internal_links(output_root=output_root, manifest=manifest),
        "outputs": records,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        inventory = validate_inventory()
        if args.output_root is None:
            print(
                "SITE-004 pre-Pelican validation passed: "
                f"{inventory['outputs']} outputs with one writer each"
            )
            return 0
        rendered = validate_rendered(args.output_root.resolve())
    except Site004ValidationError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(
        "SITE-004 rendered validation passed: "
        f"{len(rendered['outputs'])} outputs, "
        f"{rendered['links']['checked_documents']} linked documents, "
        f"{rendered['links']['checked_links']} links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
