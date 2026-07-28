#!/usr/bin/env python3
"""Compose cumulative and OPS-001 gates into the CUT-001 comparison package."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = REPO_ROOT / "migration/production_parity/baseline"
BASELINE_SCRIPTS = REPO_ROOT / "migration/production_parity/scripts"
INTENTIONAL_DIFFERENCES = REPO_ROOT / "migration/cut001/intentional_differences.json"
NOTEBOOK_MANIFEST = REPO_ROOT / "migration/site002v/notebooks.tsv"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BASELINE_SCRIPTS))

from baseline_common import (  # noqa: E402
    load_json,
    parse_atom,
    sitemap_urls,
    tree_file_to_route,
)

from migration.cut001.evidence import build_evidence_manifest  # noqa: E402
from migration.ops001.validate import validate_artifact  # noqa: E402

BASE_COMMIT = "306028c8ab31a21a1297746b4176916315ba6a23"
BASE_TREE = "0cc99d983dc302d08c7330b0451a82d61aa72541"
ACCEPTED_PREVIEW_COMMIT = "95c3f02ad6fc3589798ba73dc19e39045941235e"
ACCEPTED_PREVIEW_TREE = "671f023ce65f661af807edccc6a754d66056ce82"
PRODUCTION_COMMIT = "5c24ba21ec8b442e4b5280a47c85fab61165f8ce"
THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
READER_DISTRIBUTION = "pelican-ipynb-reader"
READER_VERSION = "0.1.0"
READER_SOURCE_COMMIT = "01b298d1a6b714755d7d9170538e4e7994038b8b"
READER_WHEEL_SHA256 = "ec5212c0f5c414743032c3b2880904af898e726e5cb5ab314345634c8bb68153"
READER_SDIST_SHA256 = "c456eb564973d7241eb5ea01aed19662f20fc18c7bef0380d81a5d1b8fc87fa4"
CANONICAL_HOST = "nekrasovp.ru"
THEMELESS_REDIRECTS = {"pages/about.html", "pages/services.html"}
BUILD_INPUT_PATHS = (
    "content",
    "pelicanconf.py",
    "plugins",
    "pyproject.toml",
    "publishconf.py",
    "templates",
    "uv.lock",
)
SITE002_BUILD_INPUT_CHANGES = {"pyproject.toml", "uv.lock"}
HTML_ASSET_ATTRIBUTES = (
    ("img", "src"),
    ("script", "src"),
    ("source", "src"),
    ("video", "poster"),
)


class Cut001ValidationError(RuntimeError):
    """A fail-closed CUT-001 contract violation."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(*arguments: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Cut001ValidationError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _html_routes(root: Path) -> dict[str, str]:
    routes: dict[str, str] = {}
    for path in sorted(root.rglob("*.html")):
        relative = path.relative_to(root).as_posix()
        route = tree_file_to_route(relative)
        if route is None:
            raise Cut001ValidationError(f"cannot derive route for {relative}")
        routes[route] = relative
    return routes


def _check_exact_allowlist(
    *,
    observed: set[str],
    allowlist: dict[str, str],
    label: str,
) -> None:
    allowed = set(allowlist)
    unexplained = sorted(observed - allowed)
    stale = sorted(allowed - observed)
    if unexplained:
        raise Cut001ValidationError(f"unexplained {label}: {unexplained!r}")
    if stale:
        raise Cut001ValidationError(f"stale {label} allowlist: {stale!r}")


def compare_routes(
    preview_root: Path,
    production_root: Path,
    *,
    intentional_added: dict[str, str],
    intentional_missing: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Require exact route-set parity except for an exact reviewed allowlist."""

    preview = _html_routes(preview_root.resolve())
    production = _html_routes(production_root.resolve())
    added = set(preview) - set(production)
    missing = set(production) - set(preview)
    missing_allowlist = intentional_missing or {}
    _check_exact_allowlist(
        observed=added,
        allowlist=intentional_added,
        label="added routes",
    )
    _check_exact_allowlist(
        observed=missing,
        allowlist=missing_allowlist,
        label="missing routes",
    )
    return {
        "added": [
            {"reason": intentional_added[route], "route": route}
            for route in sorted(added)
        ],
        "common": len(set(preview) & set(production)),
        "missing": [
            {"reason": missing_allowlist[route], "route": route}
            for route in sorted(missing)
        ],
        "preview_count": len(preview),
        "production_count": len(production),
    }


def _feed_paths(root: Path) -> dict[str, Path]:
    feed_root = root / "feeds"
    if not feed_root.is_dir():
        return {}
    return {
        f"/feeds/{path.name}": path
        for path in sorted(feed_root.glob("*.xml"))
        if path.is_file()
    }


def compare_feeds(
    preview_root: Path,
    production_root: Path,
    *,
    intentional_added_feeds: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Prove historical IDs and stable entry routing across exact feed trees."""

    preview_paths = _feed_paths(preview_root.resolve())
    production_paths = _feed_paths(production_root.resolve())
    added = set(preview_paths) - set(production_paths)
    missing = set(production_paths) - set(preview_paths)
    allowlist = intentional_added_feeds or {}
    _check_exact_allowlist(
        observed=added,
        allowlist=allowlist,
        label="added feeds",
    )
    if missing:
        raise Cut001ValidationError(f"missing production feeds: {sorted(missing)!r}")

    records: list[dict[str, Any]] = []
    historical_total = 0
    for feed_path in sorted(set(preview_paths) & set(production_paths)):
        preview = parse_atom(preview_paths[feed_path].read_bytes())
        production = parse_atom(production_paths[feed_path].read_bytes())
        preview_by_id = {entry["id"]: entry for entry in preview["entries"]}
        production_by_id = {entry["id"]: entry for entry in production["entries"]}
        production_ids = set(production_by_id)
        preview_ids = set(preview_by_id)
        missing_ids = sorted(production_ids - preview_ids)
        if missing_ids:
            raise Cut001ValidationError(
                f"historical feed IDs missing from {feed_path}: {missing_ids!r}"
            )
        historical_total += len(production_ids)
        routing_differences: list[dict[str, Any]] = []
        presentation_differences: list[dict[str, Any]] = []
        for identifier in sorted(production_ids):
            before = production_by_id[identifier]
            after = preview_by_id[identifier]
            for field in ("url", "published", "updated"):
                if before.get(field) != after.get(field):
                    routing_differences.append(
                        {
                            "after": after.get(field),
                            "before": before.get(field),
                            "field": field,
                            "id": identifier,
                        }
                    )
            for field in ("categories", "title"):
                if before.get(field) != after.get(field):
                    presentation_differences.append(
                        {
                            "after": after.get(field),
                            "before": before.get(field),
                            "field": field,
                            "id": identifier,
                        }
                    )
        if routing_differences:
            raise Cut001ValidationError(
                f"historical feed entry routing changed in {feed_path}: "
                f"{routing_differences!r}"
            )
        records.append(
            {
                "added_ids": sorted(preview_ids - production_ids),
                "feed": feed_path,
                "historical_ids": len(production_ids),
                "presentation_differences": presentation_differences,
                "preview_entries": preview["entry_count"],
                "production_entries": production["entry_count"],
                "routing_differences": [],
            }
        )

    return {
        "added_feeds": [
            {"feed": path, "reason": allowlist[path]} for path in sorted(added)
        ],
        "common_feeds": records,
        "historical_id_occurrences_preserved": historical_total,
        "missing_feeds": [],
    }


def _metadata(path: Path) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    canonical = None
    hreflang: dict[str, str] = {}
    for node in soup.find_all("link", href=True):
        rel = node.get("rel") or []
        tokens = {str(value).casefold() for value in rel}
        if "canonical" in tokens:
            canonical = str(node["href"])
        if "alternate" in tokens and node.get("hreflang"):
            hreflang[str(node["hreflang"])] = str(node["href"])
    html = soup.find("html")
    return {
        "canonical": canonical,
        "hreflang": dict(sorted(hreflang.items())),
        "lang": html.get("lang") if html else None,
    }


def _canonical_equivalent(before: str | None, after: str | None) -> bool:
    if before is None or after is None:
        return before == after
    return before.rstrip("/") == after.rstrip("/")


def compare_canonical_hreflang(
    preview_root: Path,
    production_root: Path,
    *,
    intentional: dict[str, Any],
) -> dict[str, Any]:
    preview = _html_routes(preview_root)
    production = _html_routes(production_root)
    differences: list[dict[str, Any]] = []
    equivalent: list[dict[str, Any]] = []
    for route in sorted(set(preview) & set(production)):
        before = _metadata(production_root / production[route])
        after = _metadata(preview_root / preview[route])
        changed = {
            field: {"after": after[field], "before": before[field]}
            for field in ("canonical", "hreflang", "lang")
            if before[field] != after[field]
        }
        if not changed:
            continue
        only_equivalent_canonical = (
            set(changed) == {"canonical"}
            and _canonical_equivalent(before["canonical"], after["canonical"])
        )
        if only_equivalent_canonical:
            equivalent.append({"changes": changed, "route": route})
            continue
        differences.append({"changes": changed, "route": route})
    payload = (
        json.dumps(
            differences,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    fingerprint = hashlib.sha256(payload).hexdigest()
    if (
        len(differences) != intentional.get("count")
        or fingerprint != intentional.get("sha256")
    ):
        raise Cut001ValidationError(
            "unexplained canonical/hreflang difference fingerprint: "
            f"expected_count={intentional.get('count')!r} "
            f"actual_count={len(differences)} "
            f"expected_sha256={intentional.get('sha256')!r} "
            f"actual_sha256={fingerprint}"
        )
    reason = intentional.get("reason")
    if not isinstance(reason, str) or not reason:
        raise Cut001ValidationError("canonical/hreflang reason is missing")
    return {
        "canonical_equivalent": equivalent,
        "compared_routes": len(set(preview) & set(production)),
        "intentional_differences": [
            {**record, "reason": reason} for record in differences
        ],
        "intentional_differences_fingerprint": {
            "count": len(differences),
            "sha256": fingerprint,
        },
    }


def validate_structured_data(output_root: Path) -> dict[str, Any]:
    documents = 0
    files = 0
    types: Counter[str] = Counter()
    errors: list[str] = []

    def collect_types(value: Any) -> None:
        if isinstance(value, dict):
            candidate = value.get("@type")
            if isinstance(candidate, str):
                types[candidate] += 1
            elif isinstance(candidate, list):
                types.update(item for item in candidate if isinstance(item, str))
            for nested in value.values():
                collect_types(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_types(nested)

    for path in sorted(output_root.resolve().rglob("*.html")):
        files += 1
        relative = path.relative_to(output_root).as_posix()
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        for number, node in enumerate(
            soup.find_all("script", attrs={"type": "application/ld+json"}),
            start=1,
        ):
            documents += 1
            try:
                value = json.loads(node.string or node.get_text())
            except (json.JSONDecodeError, TypeError) as error:
                errors.append(f"{relative}#{number}: {error}")
                continue
            collect_types(value)
    if errors:
        raise Cut001ValidationError(f"invalid JSON-LD: {errors!r}")
    return {
        "documents": documents,
        "files": files,
        "types": dict(sorted(types.items())),
    }


def validate_theme_toggle_markup(output_root: Path) -> dict[str, Any]:
    checked = 0
    exempt: list[str] = []
    errors: list[str] = []
    for path in sorted(output_root.resolve().rglob("*.html")):
        relative = path.relative_to(output_root).as_posix()
        if relative in THEMELESS_REDIRECTS:
            exempt.append(relative)
            continue
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        toggles = soup.select("[data-pet-theme-toggle]")
        scripts = {
            str(node.get("src"))
            for node in soup.find_all("script", src=True)
        }
        if (
            len(toggles) != 1
            or toggles[0].get("aria-pressed") != "false"
            or not any(urlsplit(value).path == "/theme/js/theme.js" for value in scripts)
        ):
            errors.append(relative)
        checked += 1
    if errors:
        raise Cut001ValidationError(
            f"theme toggle contract failed for generated pages: {errors!r}"
        )
    return {"checked": checked, "exempt": exempt}


def _reference_target(
    *,
    source: str,
    url: str,
) -> tuple[str, str] | None:
    parsed = urlsplit(url)
    if parsed.scheme in {"data", "javascript", "mailto", "tel"}:
        return None
    if parsed.hostname and parsed.hostname != CANONICAL_HOST:
        return ("external", url)
    path = unquote(parsed.path)
    if parsed.hostname == CANONICAL_HOST or path.startswith("/"):
        normalized = posixpath.normpath(path or "/")
    else:
        normalized = posixpath.normpath(
            str(PurePosixPath(source).parent / (path or PurePosixPath(source).name))
        )
    if normalized in {".", "/"}:
        target = "index.html"
    else:
        target = normalized.lstrip("/")
        if path.endswith("/"):
            target = f"{target.rstrip('/')}/index.html"
    if target.startswith("../") or target == "..":
        return ("escape", target)
    return ("local", target)


def _srcset(value: str) -> Iterable[str]:
    for part in value.split(","):
        candidate = part.strip().split()
        if candidate:
            yield candidate[0]


def _broken_references(root: Path) -> dict[str, list[dict[str, str]]]:
    broken_links: list[dict[str, str]] = []
    broken_assets: list[dict[str, str]] = []
    external_assets: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.html")):
        source = path.relative_to(root).as_posix()
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        candidates: list[tuple[str, str, str]] = []
        for node in soup.find_all("a", href=True):
            candidates.append(("link", "href", str(node["href"])))
        for tag, attribute in HTML_ASSET_ATTRIBUTES:
            for node in soup.find_all(tag):
                value = node.get(attribute)
                if isinstance(value, str) and value:
                    candidates.append(("asset", attribute, value))
        for node in soup.find_all("link", href=True):
            rel = {str(item).casefold() for item in (node.get("rel") or [])}
            if rel & {"stylesheet", "icon"}:
                candidates.append(("asset", "href", str(node["href"])))
        for node in soup.find_all(["img", "source"], srcset=True):
            for value in _srcset(str(node["srcset"])):
                candidates.append(("asset", "srcset", value))

        for kind, attribute, url in candidates:
            resolved = _reference_target(source=source, url=url)
            if resolved is None:
                continue
            disposition, target = resolved
            record = {
                "attribute": attribute,
                "source": source,
                "target": target,
                "url": url,
            }
            if disposition == "external":
                if kind == "asset":
                    external_assets.append(record)
                continue
            if disposition == "escape" or not (root / target).is_file():
                if kind == "link":
                    broken_links.append(record)
                else:
                    broken_assets.append(record)
    def key(item: dict[str, str]) -> tuple[str, str, str]:
        return item["source"], item["target"], item["url"]

    return {
        "assets": sorted(broken_assets, key=key),
        "external_assets": sorted(external_assets, key=key),
        "links": sorted(broken_links, key=key),
    }


def _reference_key(record: dict[str, str]) -> str:
    return f"{record['source']}|{record['target']}"


def compare_links_and_assets(
    preview_root: Path,
    production_root: Path,
    *,
    intentional_links: dict[str, str],
    intentional_assets: dict[str, str],
) -> dict[str, Any]:
    preview = _broken_references(preview_root.resolve())
    production = _broken_references(production_root.resolve())
    result: dict[str, Any] = {
        "external_preview_assets": preview["external_assets"],
        "external_production_assets": production["external_assets"],
    }
    for label, allowlist in (
        ("links", intentional_links),
        ("assets", intentional_assets),
    ):
        preview_by_key = {_reference_key(item): item for item in preview[label]}
        production_by_key = {
            _reference_key(item): item for item in production[label]
        }
        new = set(preview_by_key) - set(production_by_key)
        _check_exact_allowlist(
            observed=new,
            allowlist=allowlist,
            label=f"broken {label}",
        )
        result[label] = {
            "new": [
                {
                    **preview_by_key[key],
                    "reason": allowlist[key],
                }
                for key in sorted(new)
            ],
            "preview": len(preview_by_key),
            "production": len(production_by_key),
            "resolved": [
                production_by_key[key]
                for key in sorted(set(production_by_key) - set(preview_by_key))
            ],
            "unchanged": len(set(preview_by_key) & set(production_by_key)),
            "unchanged_records": [
                preview_by_key[key]
                for key in sorted(set(preview_by_key) & set(production_by_key))
            ],
        }
    return result


def validate_documents(output_root: Path) -> dict[str, Any]:
    html_files = 0
    xml_files = 0
    for path in sorted(output_root.rglob("*.html")):
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        if soup.find("html") is None:
            raise Cut001ValidationError(
                f"HTML parse failed: {path.relative_to(output_root).as_posix()}"
            )
        html_files += 1
    for path in sorted(output_root.rglob("*.xml")):
        try:
            ET.parse(path)
        except ET.ParseError as error:
            raise Cut001ValidationError(
                f"XML parse failed: {path.relative_to(output_root).as_posix()}: {error}"
            ) from error
        xml_files += 1
    return {"html_files": html_files, "xml_files": xml_files}


def validate_notebooks(output_root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    rows = NOTEBOOK_MANIFEST.read_text(encoding="utf-8").splitlines()
    header = rows[0].split("\t")
    for raw in rows[1:]:
        values = dict(zip(header, raw.split("\t"), strict=True))
        relative = values["route"].lstrip("/")
        path = output_root / relative
        if not path.is_file():
            raise Cut001ValidationError(f"notebook route is missing: {values['route']}")
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        article = soup.select_one("article.pet-notebook-region")
        main = soup.select_one("main#main-content")
        text_length = len(" ".join((article or soup).stripped_strings))
        if article is None or main is None or text_length < 200:
            raise Cut001ValidationError(
                f"notebook is not readable: {values['route']} "
                f"article={article is not None} main={main is not None} "
                f"text_length={text_length}"
            )
        records.append(
            {
                "output": relative,
                "route": values["route"],
                "sha256": _sha256(path),
                "size": path.stat().st_size,
                "source": values["source"],
                "text_length": text_length,
            }
        )
    if len(records) != 11:
        raise Cut001ValidationError(f"expected 11 readable notebooks, got {len(records)}")
    return {"count": len(records), "records": records}


def compare_sitemap(preview_root: Path, production_root: Path) -> dict[str, Any]:
    preview = sitemap_urls((preview_root / "sitemap.xml").read_bytes())
    production = sitemap_urls((production_root / "sitemap.xml").read_bytes())
    missing = sorted(set(production) - set(preview))
    added = sorted(set(preview) - set(production))
    if missing or added:
        raise Cut001ValidationError(
            f"sitemap routes changed: missing={missing!r} added={added!r}"
        )
    return {
        "added": [],
        "missing": [],
        "preview_count": len(preview),
        "production_count": len(production),
    }


def _route_inventory(output_root: Path) -> dict[str, Any]:
    baseline = load_json(BASELINE_ROOT / "routes.json")["routes"]
    by_output: dict[str, list[dict[str, Any]]] = {}
    for record in baseline:
        output = record.get("output_path")
        if output:
            by_output.setdefault(output, []).append(record)
    notebook_routes = {
        line.split("\t")[2]
        for line in NOTEBOOK_MANIFEST.read_text(encoding="utf-8").splitlines()[1:]
    }
    records: list[dict[str, Any]] = []
    for route, relative in sorted(_html_routes(output_root).items()):
        path = output_root / relative
        metadata = _metadata(path)
        records.append(
            {
                "baseline_paths": sorted(
                    item["path"] for item in by_output.get(relative, [])
                ),
                "canonical": metadata["canonical"],
                "hreflang": metadata["hreflang"],
                "lang": metadata["lang"],
                "notebook": route in notebook_routes,
                "output": relative,
                "route": route,
                "sha256": _sha256(path),
                "simulated_status": 200,
                "size": path.stat().st_size,
            }
        )
    return {
        "contract": "nekrasovp-cut001-generated-routes.v1",
        "count": len(records),
        "records": records,
        "status_exceptions": [
            {
                "basis": "GitHub Pages treats CNAME as an artifact-only control file",
                "path": "/CNAME",
                "simulated_status": 404,
            },
            {
                "basis": "GitHub Pages serves the retained 404.html document",
                "path": "/__cut001_missing_probe__",
                "simulated_status": 404,
            },
        ],
    }


def _verify_source_and_dependencies(
    cumulative_report: Path,
    production_root: Path,
) -> dict[str, Any]:
    source_commit = _git("rev-parse", "HEAD")
    source_tree = _git("rev-parse", "HEAD^{tree}")
    if _git("rev-parse", f"{BASE_COMMIT}^{{tree}}") != BASE_TREE:
        raise Cut001ValidationError("CUT-001 base tree no longer matches its contract")
    if (
        _git("rev-parse", f"{ACCEPTED_PREVIEW_COMMIT}^{{tree}}")
        != ACCEPTED_PREVIEW_TREE
    ):
        raise Cut001ValidationError("accepted CUT-001 preview tree no longer matches its contract")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTED_PREVIEW_COMMIT, source_commit],
        cwd=REPO_ROOT,
        check=False,
    )
    if ancestor.returncode:
        raise Cut001ValidationError(
            f"SITE-002 source {source_commit} is not based on accepted preview "
            f"{ACCEPTED_PREVIEW_COMMIT}"
        )
    production_head = _git("-C", str(production_root), "rev-parse", "HEAD")
    if production_head != PRODUCTION_COMMIT:
        raise Cut001ValidationError(
            f"production reference drift: expected={PRODUCTION_COMMIT} "
            f"actual={production_head}"
        )
    changed_build_inputs = _git(
        "diff",
        "--name-only",
        ACCEPTED_PREVIEW_COMMIT,
        source_commit,
        "--",
        *BUILD_INPUT_PATHS,
    ).splitlines()
    if set(changed_build_inputs) != SITE002_BUILD_INPUT_CHANGES:
        raise Cut001ValidationError(
            "SITE-002 build-input delta from the accepted preview is not exactly "
            f"{sorted(SITE002_BUILD_INPUT_CHANGES)!r}: {changed_build_inputs!r}"
        )

    cumulative = load_json(cumulative_report)
    if cumulative.get("repository_head") != source_commit:
        raise Cut001ValidationError(
            "cumulative report was not generated from the exact CUT-001 source commit"
        )
    dependency = cumulative.get("dependency", {})
    theme = cumulative.get("site006v", {}).get("candidate", {})
    lock = dependency.get("lock", {})
    if (
        dependency.get("distribution") != READER_DISTRIBUTION
        or dependency.get("version") != READER_VERSION
        or dependency.get("source_commit") != READER_SOURCE_COMMIT
        or lock.get("wheel", {}).get("sha256") != READER_WHEEL_SHA256
        or lock.get("sdist", {}).get("sha256") != READER_SDIST_SHA256
    ):
        raise Cut001ValidationError("cumulative released-reader identity drift")
    if theme.get("theme_commit") != THEME_COMMIT:
        raise Cut001ValidationError("cumulative theme identity drift")
    return {
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "accepted_preview_commit": ACCEPTED_PREVIEW_COMMIT,
        "accepted_preview_tree": ACCEPTED_PREVIEW_TREE,
        "build_input_diff_from_accepted_preview": changed_build_inputs,
        "production_commit": production_head,
        "reader": dependency,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "theme": theme,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve()
    production_root = args.production_root.resolve()
    evidence_root = args.evidence_root.resolve()
    if not output_root.is_dir() or not production_root.is_dir():
        raise Cut001ValidationError("preview or production artifact is unavailable")
    intents = load_json(args.intentional_differences.resolve())
    if intents.get("production_commit") != PRODUCTION_COMMIT:
        raise Cut001ValidationError("intentional-difference production identity drift")

    source = _verify_source_and_dependencies(
        args.cumulative_report.resolve(),
        production_root,
    )
    ops_errors, ops_evidence = validate_artifact(
        output_root,
        accepted_migration_contracts=True,
    )
    if ops_errors:
        raise Cut001ValidationError(f"OPS-001 validation failed: {ops_errors!r}")

    routes = compare_routes(
        output_root,
        production_root,
        intentional_added=intents["added_routes"],
        intentional_missing=intents["missing_routes"],
    )
    feeds = compare_feeds(
        output_root,
        production_root,
        intentional_added_feeds=intents["added_feeds"],
    )
    canonical = compare_canonical_hreflang(
        output_root,
        production_root,
        intentional=intents["canonical_or_hreflang"],
    )
    references = compare_links_and_assets(
        output_root,
        production_root,
        intentional_links=intents["new_broken_links"],
        intentional_assets=intents["new_broken_assets"],
    )
    references["intentional_production_runtime_external"] = [
        {"reason": reason, "url": url}
        for url, reason in sorted(
            intents["production_runtime_external"].items()
        )
    ]
    route_inventory = _route_inventory(output_root)
    comparison = {
        "artifact": {
            "directory_sha256": ops_evidence["artifact_sha256"],
            "html_files": ops_evidence["html_files"],
            "xml_files": ops_evidence["xml_files"],
        },
        "base001_and_ops001": {
            "base_parity_errors": ops_evidence["base_parity_errors"],
            "global_errors": ops_evidence["global_errors"],
            "reviewed_base_differences": ops_evidence[
                "reviewed_base_differences"
            ],
        },
        "canonical_hreflang": canonical,
        "contract": "nekrasovp-cut001-comparison.v1",
        "documents": validate_documents(output_root),
        "feeds": feeds,
        "notebooks": validate_notebooks(output_root),
        "references": references,
        "rollback": {
            "identifier": f"gh-pages@{PRODUCTION_COMMIT}",
            "instructions": (
                "Discard the preview. Production remains on legacy gh-pages; "
                "re-materialize the exact rollback tree from the recorded commit."
            ),
        },
        "routes": routes,
        "sitemap": compare_sitemap(output_root, production_root),
        "source": source,
        "structured_data": validate_structured_data(output_root),
        "theme_toggle_markup": validate_theme_toggle_markup(output_root),
    }
    evidence_root.mkdir(parents=True, exist_ok=True)
    _write_json(evidence_root / "generated-routes.json", route_inventory)
    _write_json(evidence_root / "feed-diff.json", feeds)
    _write_json(evidence_root / "comparison.json", comparison)
    manifest = build_evidence_manifest(evidence_root, source["source_commit"])
    _write_json(evidence_root / "manifest.json", manifest)
    return comparison


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--production-root", type=Path, required=True)
    result.add_argument("--cumulative-report", type=Path, required=True)
    result.add_argument("--evidence-root", type=Path, required=True)
    result.add_argument(
        "--intentional-differences",
        type=Path,
        default=INTENTIONAL_DIFFERENCES,
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    try:
        report = run(parser().parse_args(argv))
    except Exception as error:
        print(f"CUT-001 validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "CUT-001 machine parity passed: "
        f"{report['routes']['preview_count']} routes, "
        f"{report['notebooks']['count']} notebooks, "
        f"{report['theme_toggle_markup']['checked']} themed HTML documents, "
        f"artifact {report['artifact']['directory_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
