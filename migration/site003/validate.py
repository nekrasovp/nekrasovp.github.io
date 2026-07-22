"""Validate the authoritative SITE-003 source and rendered metadata contracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"
MANIFEST = REPO_ROOT / "migration/production_parity/inputs/legacy_routes.tsv"
SITE003_BASE_COMMIT = "8e80e4d6ada80f9ad06896674bbcaab8f98a7bfe"
SITEURL = "https://nekrasovp.ru"
SITENAME = "Data driven"
EXPECTED_ARTICLES = 46
EXPECTED_MARKDOWN = 35
EXPECTED_NOTEBOOKS = 11
EXPECTED_STATUS_COUNTS = {
    "archive": 16,
    "deprecated": 8,
    "keep": 13,
    "refresh": 9,
}
EXPECTED_LANGUAGE_COUNTS = {"en": 42, "ru": 4}
LANGUAGE_LABELS = {"en": "English", "ru": "Русский"}
MANIFEST_FIELDS = ("route", "published_at", "language", "status", "source", "title")
EDITABLE_METADATA = {
    "canonical",
    "lang",
    "legacy_source",
    "modified",
    "status",
    "title",
}
MANUAL_REVIEW_SOURCES = (
    "technical-debt-examples.md",  # refresh, ru
    "update-django-user-password.md",  # keep, en
    "mkrf-spb-geo-data.ipynb",  # archive, ru
    "fixing-caching-sha2-password.md",  # deprecated, en
)


@dataclass(frozen=True)
class ManifestRow:
    route: str
    published_at: str
    language: str
    status: str
    source: str
    title: str

    @property
    def is_notebook(self) -> bool:
        return self.source.casefold().endswith(".ipynb")


class Site003ValidationError(RuntimeError):
    """A stable, source-aware SITE-003 contract failure."""

    error_code = "validation_error"
    stage = "inventory_validation"

    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        super().__init__(
            "SITE-003 pre-Pelican validation failed: "
            f"source={source!r} stage={self.stage} error_code={self.error_code} "
            f"error_type={type(self).__name__} {message}"
        )


class InvalidManifest(Site003ValidationError):
    error_code = "invalid_manifest"


class DuplicateManifestMapping(Site003ValidationError):
    error_code = "duplicate_manifest_mapping"


class MissingExpectedSource(Site003ValidationError):
    error_code = "missing_expected_source"


class UnexpectedLegacySource(Site003ValidationError):
    error_code = "unexpected_legacy_source"


class MissingMetadataField(Site003ValidationError):
    error_code = "missing_metadata_field"


class DuplicateMetadataField(Site003ValidationError):
    error_code = "duplicate_metadata_field"


class UnknownStatus(Site003ValidationError):
    error_code = "unknown_status"


class InvalidLanguage(Site003ValidationError):
    error_code = "invalid_language"


class MetadataMismatch(Site003ValidationError):
    error_code = "metadata_mismatch"


class SourcePreservationMismatch(Site003ValidationError):
    error_code = "source_preservation_mismatch"


class RenderedContractMismatch(Site003ValidationError):
    error_code = "rendered_contract_mismatch"
    stage = "rendered_validation"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _aggregate_sha256(records: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for source, value in sorted(records):
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(value).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest(path: Path) -> list[ManifestRow]:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if tuple(reader.fieldnames or ()) != MANIFEST_FIELDS:
                raise InvalidManifest(
                    path.as_posix(), f"expected exact columns {MANIFEST_FIELDS!r}"
                )
            rows = [
                ManifestRow(**{field: row[field] for field in MANIFEST_FIELDS})
                for row in reader
            ]
    except Site003ValidationError:
        raise
    except Exception as error:
        raise InvalidManifest(path.as_posix(), str(error)) from error

    if len(rows) != EXPECTED_ARTICLES:
        raise InvalidManifest(path.as_posix(), f"expected 46 rows, observed {len(rows)}")
    sources = [row.source for row in rows]
    routes = [row.route for row in rows]
    if len(sources) != len(set(sources)) or len(routes) != len(set(routes)):
        raise DuplicateManifestMapping(path.as_posix(), "sources and routes must be one-to-one")

    for row in rows:
        source = PurePosixPath(row.source)
        if source.is_absolute() or ".." in source.parts or source.name != row.source:
            raise InvalidManifest(row.source, "source must be one safe content-root filename")
        if not row.route.startswith("/") or not row.route.endswith(".html"):
            raise InvalidManifest(row.source, f"invalid route {row.route!r}")
        if row.status not in EXPECTED_STATUS_COUNTS:
            raise UnknownStatus(row.source, f"manifest status={row.status!r}")
        if row.language not in EXPECTED_LANGUAGE_COUNTS:
            raise InvalidLanguage(row.source, f"manifest language={row.language!r}")

    status_counts = Counter(row.status for row in rows)
    language_counts = Counter(row.language for row in rows)
    if dict(sorted(status_counts.items())) != dict(sorted(EXPECTED_STATUS_COUNTS.items())):
        raise InvalidManifest(path.as_posix(), f"unexpected status counts {dict(status_counts)!r}")
    if dict(sorted(language_counts.items())) != dict(sorted(EXPECTED_LANGUAGE_COUNTS.items())):
        raise InvalidManifest(
            path.as_posix(), f"unexpected language counts {dict(language_counts)!r}"
        )
    return rows


def _split_metadata(source: str, raw: bytes) -> tuple[bytes, bytes | None]:
    if not source.casefold().endswith(".md"):
        return raw, None
    candidates = []
    for delimiter in (b"\r\n\r\n", b"\n\n"):
        position = raw.find(delimiter)
        if position >= 0:
            candidates.append((position, len(delimiter)))
    if not candidates:
        raise MissingMetadataField(source, "Markdown metadata has no terminating blank line")
    position, length = min(candidates)
    return raw[:position], raw[position + length :]


def _parse_metadata(source: str, raw: bytes) -> dict[str, str]:
    header, _body = _split_metadata(source, raw)
    try:
        text = header.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise MetadataMismatch(source, f"metadata is not UTF-8: {error}") from error
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).casefold()
        if key in result:
            raise DuplicateMetadataField(source, f"field={key!r}")
        result[key] = match.group(2).strip()
    return result


def _git_blob(base_commit: str, repository_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{base_commit}:{repository_path}"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SourcePreservationMismatch(repository_path, f"base object unavailable: {detail}")
    return result.stdout


def _expected_route(source: str, metadata: Mapping[str, str]) -> str:
    save_as = metadata.get("save_as")
    if save_as:
        return "/" + save_as.lstrip("/")
    slug = metadata.get("slug")
    if not slug:
        raise MissingMetadataField(source, "field='slug'")
    return f"/{slug}.html"


def _require_metadata(row: ManifestRow, metadata: Mapping[str, str]) -> None:
    for field in ("title", "date", "slug", "lang", "status"):
        if not metadata.get(field):
            raise MissingMetadataField(row.source, f"field={field!r}")
    status = metadata["status"]
    language = metadata["lang"]
    if status not in EXPECTED_STATUS_COUNTS:
        raise UnknownStatus(row.source, f"source status={status!r}")
    if language not in EXPECTED_LANGUAGE_COUNTS:
        raise InvalidLanguage(row.source, f"source language={language!r}")

    expected = {
        "date": row.published_at,
        "language": row.language,
        "route": row.route,
        "status": row.status,
        "title": row.title,
    }
    actual = {
        "date": metadata["date"][:10],
        "language": language,
        "route": _expected_route(row.source, metadata),
        "status": status,
        "title": metadata["title"],
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            raise MetadataMismatch(
                row.source,
                f"field={field!r} expected={expected_value!r} actual={actual[field]!r}",
            )
    if "modified" in metadata:
        raise MetadataMismatch(row.source, "modified is not supported without factual evidence")


def _stable_metadata(metadata: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in metadata.items() if key not in EDITABLE_METADATA}


def validate_inventory(
    *,
    content_root: Path = CONTENT_ROOT,
    manifest_path: Path = MANIFEST,
    base_commit: str = SITE003_BASE_COMMIT,
) -> dict[str, Any]:
    """Validate all 46 source records before Pelican reads any article."""

    rows = _load_manifest(manifest_path)
    manifest_sources = {row.source for row in rows}
    actual_sources = {
        path.name
        for pattern in ("*.md", "*.ipynb")
        for path in content_root.glob(pattern)
        if path.is_file()
    }
    missing = sorted(manifest_sources - actual_sources)
    unexpected = sorted(actual_sources - manifest_sources)
    if missing:
        raise MissingExpectedSource(missing[0], f"missing sources={missing!r}")
    if unexpected:
        raise UnexpectedLegacySource(unexpected[0], f"unexpected sources={unexpected!r}")

    expected_nbdata = {
        Path(row.source).with_suffix(".nbdata").name for row in rows if row.is_notebook
    }
    actual_nbdata = {path.name for path in content_root.glob("*.nbdata") if path.is_file()}
    if expected_nbdata != actual_nbdata:
        missing_metadata = sorted(expected_nbdata - actual_nbdata)
        unexpected_metadata = sorted(actual_nbdata - expected_nbdata)
        source = (missing_metadata or unexpected_metadata)[0]
        raise MissingExpectedSource(
            source,
            f"nbdata missing={missing_metadata!r} unexpected={unexpected_metadata!r}",
        )

    markdown_bodies: list[tuple[str, bytes]] = []
    notebook_bytes: list[tuple[str, bytes]] = []
    metadata_records = 0
    for row in rows:
        source_path = content_root / row.source
        source_raw = source_path.read_bytes()
        metadata_path = (
            source_path.with_suffix(".nbdata") if row.is_notebook else source_path
        )
        metadata_raw = metadata_path.read_bytes()
        metadata = _parse_metadata(row.source, metadata_raw)
        _require_metadata(row, metadata)
        metadata_records += 1

        base_source_raw = _git_blob(base_commit, f"content/{row.source}")
        if row.is_notebook:
            if source_raw != base_source_raw:
                raise SourcePreservationMismatch(row.source, "notebook bytes differ from base")
            notebook_bytes.append((row.source, source_raw))
            metadata_name = Path(row.source).with_suffix(".nbdata").name
            base_metadata_raw = _git_blob(base_commit, f"content/{metadata_name}")
            base_metadata = _parse_metadata(row.source, base_metadata_raw)
        else:
            _current_header, current_body = _split_metadata(row.source, source_raw)
            _base_header, base_body = _split_metadata(row.source, base_source_raw)
            if current_body != base_body:
                raise SourcePreservationMismatch(row.source, "Markdown body bytes differ from base")
            assert current_body is not None
            markdown_bodies.append((row.source, current_body))
            base_metadata = _parse_metadata(row.source, base_source_raw)

        if _stable_metadata(metadata) != _stable_metadata(base_metadata):
            raise SourcePreservationMismatch(
                row.source, "non-SITE-003 metadata fields differ from base"
            )

    markdown_count = sum(not row.is_notebook for row in rows)
    notebook_count = sum(row.is_notebook for row in rows)
    if (markdown_count, notebook_count) != (EXPECTED_MARKDOWN, EXPECTED_NOTEBOOKS):
        raise InvalidManifest(
            manifest_path.as_posix(),
            f"expected 35 Markdown + 11 notebooks, observed {markdown_count} + {notebook_count}",
        )

    return {
        "canonical_contract": f"{SITEURL}<manifest route>",
        "counts": {
            "articles": len(rows),
            "languages": dict(sorted(Counter(row.language for row in rows).items())),
            "markdown": markdown_count,
            "notebooks": notebook_count,
            "statuses": dict(sorted(Counter(row.status for row in rows).items())),
        },
        "manifest_sha256": _sha256(manifest_path),
        "metadata_records_validated": metadata_records,
        "source_preservation": {
            "base_commit": base_commit,
            "dates_preserved": len(rows),
            "markdown_bodies_preserved": markdown_count,
            "markdown_body_aggregate_sha256": _aggregate_sha256(markdown_bodies),
            "notebook_bytes_preserved": notebook_count,
            "notebook_source_aggregate_sha256": _aggregate_sha256(notebook_bytes),
            "routes_preserved": len(rows),
            "stable_metadata_preserved": len(rows),
        },
    }


def _canonical_link(soup: BeautifulSoup) -> str | None:
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        tokens = rel if isinstance(rel, list) else str(rel).split()
        if "canonical" in {token.casefold() for token in tokens}:
            href = link.get("href")
            return str(href) if href is not None else None
    return None


def validate_output(
    *,
    output_root: Path,
    manifest_path: Path = MANIFEST,
) -> dict[str, Any]:
    """Validate the 46 generated routes, notices, languages, and canonicals."""

    rows = _load_manifest(manifest_path)
    notice_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    manual: dict[str, Any] = {}
    for row in rows:
        route_path = output_root / row.route.lstrip("/")
        if not route_path.is_file():
            raise RenderedContractMismatch(row.source, f"missing route {row.route!r}")
        soup = BeautifulSoup(route_path.read_text(encoding="utf-8"), "html.parser")
        html = soup.find("html")
        html_lang = html.get("lang") if html else None
        if html_lang != row.language:
            raise RenderedContractMismatch(
                row.source,
                f"html lang expected={row.language!r} actual={html_lang!r}",
            )
        expected_title = f"{row.title} - {SITENAME}"
        rendered_title = soup.title.get_text(strip=True) if soup.title else None
        if rendered_title != expected_title:
            raise RenderedContractMismatch(
                row.source,
                f"title expected={expected_title!r} actual={rendered_title!r}",
            )
        canonical = _canonical_link(soup)
        expected_canonical = f"{SITEURL}{row.route}"
        if canonical != expected_canonical:
            raise RenderedContractMismatch(
                row.source,
                f"canonical expected={expected_canonical!r} actual={canonical!r}",
            )

        article = soup.find("article", attrs={"data-content-status": True})
        rendered_status = article.get("data-content-status") if article else None
        if rendered_status != row.status:
            raise RenderedContractMismatch(
                row.source,
                f"status expected={row.status!r} actual={rendered_status!r}",
            )

        labels = soup.select(".article-language[data-language-code]")
        expected_label = LANGUAGE_LABELS[row.language]
        if len(labels) != 1 or labels[0].get("data-language-code") != row.language:
            raise RenderedContractMismatch(row.source, "expected exactly one language label")
        label_text = " ".join(labels[0].get_text(" ", strip=True).split())
        if label_text != expected_label:
            raise RenderedContractMismatch(
                row.source,
                f"language label expected={expected_label!r} actual={label_text!r}",
            )
        label_counts[row.language] += 1

        notices = soup.select(".content-notice[data-content-status]")
        if row.status in {"archive", "deprecated"}:
            if len(notices) != 1 or notices[0].get("data-content-status") != row.status:
                raise RenderedContractMismatch(row.source, "expected one status-specific notice")
            notice_counts[row.status] += 1
            notice_text = " ".join(notices[0].get_text(" ", strip=True).split())
        else:
            if notices:
                raise RenderedContractMismatch(
                    row.source, f"misleading notice rendered for {row.status!r}"
                )
            notice_text = None

        for robots in soup.find_all("meta", attrs={"name": re.compile(r"^robots$", re.I)}):
            if "noindex" in str(robots.get("content") or "").casefold():
                raise RenderedContractMismatch(
                    row.source, "lifecycle status silently introduced noindex"
                )

        if row.source in MANUAL_REVIEW_SOURCES:
            manual[row.source] = {
                "canonical": canonical,
                "html_language": html_lang,
                "language_label": label_text,
                "notice_text": notice_text,
                "route": row.route,
                "status": row.status,
                "title": rendered_title,
            }

    expected_notices = {"archive": 16, "deprecated": 8}
    if dict(sorted(notice_counts.items())) != expected_notices:
        raise RenderedContractMismatch(
            manifest_path.as_posix(), f"unexpected notice counts {dict(notice_counts)!r}"
        )
    if dict(sorted(label_counts.items())) != EXPECTED_LANGUAGE_COUNTS:
        raise RenderedContractMismatch(
            manifest_path.as_posix(), f"unexpected language-label counts {dict(label_counts)!r}"
        )
    if set(manual) != set(MANUAL_REVIEW_SOURCES):
        raise RenderedContractMismatch(
            manifest_path.as_posix(), f"manual review examples incomplete: {sorted(manual)!r}"
        )

    return {
        "canonical_routes": len(rows),
        "language_labels": dict(sorted(label_counts.items())),
        "manual_source_and_render_inspection": manual,
        "noindex_from_status": 0,
        "notices": {**expected_notices, "keep": 0, "refresh": 0},
        "routes": len(rows),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--content-root", type=Path, default=CONTENT_ROOT)
    result.add_argument("--manifest", type=Path, default=MANIFEST)
    result.add_argument("--base-commit", default=SITE003_BASE_COMMIT)
    result.add_argument("--output-root", type=Path)
    result.add_argument("--evidence-out", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        evidence = {
            "contract": "nekrasovp-site003-metadata.v1",
            "inventory": validate_inventory(
                content_root=args.content_root.resolve(),
                manifest_path=args.manifest.resolve(),
                base_commit=args.base_commit,
            ),
        }
        if args.output_root:
            evidence["rendered"] = validate_output(
                output_root=args.output_root.resolve(),
                manifest_path=args.manifest.resolve(),
            )
        if args.evidence_out:
            args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
            args.evidence_out.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except Site003ValidationError as error:
        print(error, file=sys.stderr)
        return 1
    counts = evidence["inventory"]["counts"]
    message = (
        "SITE-003 pre-Pelican validation passed: "
        f"{counts['markdown']} Markdown + {counts['notebooks']} notebooks = "
        f"{counts['articles']} sources"
    )
    if "rendered" in evidence:
        message += "; 46 rendered route/status/language/notice contracts passed"
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
