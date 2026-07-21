#!/usr/bin/env python3
"""Collect a deterministic production parity snapshot from live and Git state."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from baseline_common import (
    parse_atom,
    parse_html,
    route_to_output_path,
    sitemap_urls,
    tree_file_to_route,
    write_json,
)


SCHEMA_VERSION = 1
SITE_ALIASES = {"nekrasovp.ru", "www.nekrasovp.ru", "nekrasovp.github.io"}
NEW_ROUTES = {
    "/ai-native-delivery-contract.html",
    "/ai-native-sdlc-engineering-accountability.html",
    "/logistics-distributed-systems-case-study.html",
    "/logistics-lessons-for-distributed-systems.html",
    "/technical-debt-as-a-portfolio.html",
    "/technical-debt-portfolio-register.html",
}
SPECIAL_HTML_ROUTES = {
    "/",
    "/404.html",
    "/about/",
    "/archives.html",
    "/authors.html",
    "/categories.html",
    "/pages/about.html",
    "/pages/services.html",
    "/ru/",
    "/tags.html",
    "/work/",
    "/writing/",
}
SPECIAL_FILE_ROUTES = {"/CNAME", "/robots.txt", "/sitemap.xml"}
FEED_ROUTES = {"/feeds/all.atom.xml", "/feeds/blog.atom.xml"}
MISSING_PROBE = "/__base001_expected_missing_route__.html"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    redirect_target: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_text(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def run_json(command: list[str], cwd: Path) -> dict[str, Any]:
    return json.loads(run_text(command, cwd))


def run_bytes(command: list[str], cwd: Path) -> bytes:
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True)
    return result.stdout


def fetch(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 30.0,
    retries: int = 2,
) -> Response:
    opener = build_opener(NoRedirect)
    request = Request(
        url,
        headers={"User-Agent": "nekrasovp-BASE-001-parity-collector/1"},
        method=method,
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                body = response.read()
                headers = {key.lower(): value for key, value in response.headers.items()}
                return Response(
                    url=url,
                    status=response.status,
                    headers=headers,
                    body=body,
                    redirect_target=None,
                )
        except HTTPError as error:
            body = error.read()
            headers = {key.lower(): value for key, value in error.headers.items()}
            location = headers.get("location")
            return Response(
                url=url,
                status=error.code,
                headers=headers,
                body=body,
                redirect_target=urljoin(url, location) if location else None,
            )
        except (TimeoutError, URLError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def fetch_many(urls: Iterable[str], workers: int, *, method: str = "GET") -> dict[str, Response]:
    unique_urls = sorted(set(urls))
    responses: dict[str, Response] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch, url, method=method): url for url in unique_urls}
        for future in as_completed(futures):
            url = futures[future]
            responses[url] = future.result()
    return responses


def canonical_path(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or (parts.hostname or "").lower() not in SITE_ALIASES:
        return None
    path = unquote(parts.path or "/")
    return quote(path, safe="/-._~!$&'()*+,;=:@")


def strip_fragment_and_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))


def verify_live_length(response: Response, body: bytes, label: str) -> None:
    raw_length = response.headers.get("content-length")
    if raw_length and response.status == 200 and int(raw_length) != len(body):
        raise RuntimeError(
            f"live content-length mismatch for {label}: live={raw_length} published_tree={len(body)}"
        )


def load_legacy_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 46:
        raise RuntimeError(f"expected 46 legacy routes, found {len(rows)} in {path}")
    routes = {row["route"]: row for row in rows}
    if len(routes) != 46:
        raise RuntimeError("legacy manifest contains duplicate routes")
    return routes


def classify_route(
    path: str,
    *,
    legacy: dict[str, dict[str, str]],
    sitemap_paths: set[str],
    tree_html_paths: set[str],
    discovered_internal_paths: set[str],
) -> list[str]:
    values: set[str] = set()
    if path in legacy:
        values.add("legacy_article")
    if path in NEW_ROUTES:
        values.add("new_article_or_resource")
    if path in sitemap_paths:
        values.add("sitemap")
    if path in tree_html_paths:
        values.add("published_tree")
    if path == "/index.html":
        values.update({"published_tree_alias", "public_outside_sitemap"})
    if path in discovered_internal_paths:
        values.add("internal_link")
    if path in SPECIAL_HTML_ROUTES:
        values.add("special_page")
    if path in {"/pages/about.html", "/pages/services.html"}:
        values.add("intentional_redirect")
    if path == "/404.html":
        values.add("not_found_document")
    if path in {"/categories.html", "/tags.html", "/authors.html"}:
        values.add("taxonomy_index")
    if path.startswith(("/category/", "/tag/", "/author/")):
        values.add("taxonomy")
    name = Path(path).name
    if name != "404.html" and re.search(r"[A-Za-z-]+[2-9]\.html$", name):
        values.add("pagination")
    if path in FEED_ROUTES:
        values.add("feed")
    if path in SPECIAL_FILE_ROUTES:
        values.add("special_file")
    if path not in sitemap_paths and path in tree_html_paths:
        values.add("public_outside_sitemap")
    return sorted(values)


def collection_settings(repo_root: Path, repository: str) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = run_json(["gh", "api", f"repos/{repository}"], repo_root)
    pages = run_json(["gh", "api", f"repos/{repository}/pages"], repo_root)
    return repo, pages


def collect(args: argparse.Namespace) -> dict[str, Any]:
    started_at = utc_now()
    repo_root = args.repo_root.resolve()
    baseline_dir = args.baseline_dir.resolve()
    legacy = load_legacy_manifest(args.legacy_manifest.resolve())
    production_base = args.production_base.rstrip("/")

    repo_state, pages_state = collection_settings(repo_root, args.repository)
    master_sha = run_text(["git", "rev-parse", args.master_ref], repo_root)
    published_sha = run_text(["git", "rev-parse", args.published_ref], repo_root)
    tree_files = run_text(["git", "ls-tree", "-r", "--name-only", args.published_ref], repo_root).splitlines()
    tree_html_map = {
        route: path
        for path in tree_files
        if (route := tree_file_to_route(path)) is not None
    }
    tree_html_paths = set(tree_html_map)

    sitemap_response = fetch(f"{production_base}/sitemap.xml")
    if sitemap_response.status != 200:
        raise RuntimeError(f"sitemap returned {sitemap_response.status}")
    sitemap_absolute_urls = sitemap_urls(sitemap_response.body)
    if len(sitemap_absolute_urls) != args.expected_sitemap_count:
        raise RuntimeError(
            f"expected {args.expected_sitemap_count} sitemap URLs, found {len(sitemap_absolute_urls)}"
        )
    sitemap_paths = {canonical_path(url) for url in sitemap_absolute_urls}
    sitemap_paths.discard(None)

    feed_responses = fetch_many((f"{production_base}{path}" for path in FEED_ROUTES), args.workers)
    feed_documents: dict[str, dict[str, Any]] = {}
    feed_entry_paths: set[str] = set()
    for url, response in feed_responses.items():
        if response.status != 200:
            raise RuntimeError(f"feed {url} returned {response.status}")
        document = parse_atom(response.body)
        path = canonical_path(url)
        assert path is not None
        feed_documents[path] = document
        for entry in document["entries"]:
            if entry["url"] and (entry_path := canonical_path(entry["url"])):
                feed_entry_paths.add(entry_path)

    seed_paths = (
        set(legacy)
        | NEW_ROUTES
        | SPECIAL_HTML_ROUTES
        | tree_html_paths
        | set(sitemap_paths)
        | feed_entry_paths
    )
    pending = set(seed_paths)
    route_responses: dict[str, Response] = {}
    route_parsers: dict[str, Any] = {}
    discovered_internal_paths: set[str] = set()
    discovered_alias_urls: set[str] = set()

    while pending:
        batch = sorted(pending)
        pending.clear()
        fetched = fetch_many(
            (f"{production_base}{path}" for path in batch),
            args.workers,
            method="HEAD",
        )
        for url, response in fetched.items():
            path = canonical_path(url)
            assert path is not None
            route_responses[path] = response
            content_type = response.headers.get("content-type", "")
            if (
                response.status == 200
                and path in tree_html_map
                and ("html" in content_type or path.endswith(("/", ".html")))
            ):
                body = run_bytes(
                    ["git", "show", f"{args.published_ref}:{tree_html_map[path]}"],
                    repo_root,
                )
                verify_live_length(response, body, path)
                parser = parse_html(body, url)
                route_parsers[path] = parser
                for linked_url in parser.links:
                    normalized_url = strip_fragment_and_query(linked_url)
                    linked_path = canonical_path(normalized_url)
                    if linked_path is None:
                        continue
                    linked_parts = urlsplit(normalized_url)
                    if (linked_parts.hostname or "").lower() == "nekrasovp.github.io":
                        discovered_alias_urls.add(
                            urlunsplit(
                                (
                                    linked_parts.scheme,
                                    linked_parts.netloc,
                                    linked_path,
                                    "",
                                    "",
                                )
                            )
                        )
                    discovered_internal_paths.add(linked_path)
                    if linked_path not in route_responses and linked_path not in pending:
                        pending.add(linked_path)
        if len(route_responses) > 1000:
            raise RuntimeError("internal route discovery exceeded the 1000-route safety limit")

    if "/index.html" in route_responses:
        index_body = run_bytes(["git", "show", f"{args.published_ref}:index.html"], repo_root)
        verify_live_length(route_responses["/index.html"], index_body, "/index.html")
        route_parsers["/index.html"] = parse_html(
            index_body, f"{production_base}/index.html"
        )

    for required_path in legacy:
        if required_path not in route_responses:
            raise RuntimeError(f"legacy route not collected: {required_path}")
    for required_path in NEW_ROUTES:
        if required_path not in route_responses:
            raise RuntimeError(f"new article/resource route not collected: {required_path}")

    special_responses = {
        "/CNAME": fetch(f"{production_base}/CNAME"),
        "/robots.txt": fetch(f"{production_base}/robots.txt"),
        "/sitemap.xml": sitemap_response,
        MISSING_PROBE: fetch(f"{production_base}{MISSING_PROBE}"),
    }
    www_response = fetch("https://www.nekrasovp.ru/")
    alias_responses = fetch_many(discovered_alias_urls, args.workers, method="HEAD")

    routes = []
    metadata = []
    all_local_paths = sorted(set(route_responses) | SPECIAL_FILE_ROUTES | FEED_ROUTES)
    for path in all_local_paths:
        response = route_responses.get(path) or special_responses.get(path) or feed_responses.get(
            f"{production_base}{path}"
        )
        if response is None:
            raise RuntimeError(f"no live response captured for {path}")
        parser = route_parsers.get(path)
        redirect = None
        if response.redirect_target:
            redirect = {"kind": "http", "target": response.redirect_target}
        elif parser and parser.meta_refresh_target:
            redirect = {"kind": "meta_refresh", "target": parser.meta_refresh_target}

        output_path = tree_html_map.get(path)
        if path == "/index.html":
            output_path = "index.html"
        if path in SPECIAL_FILE_ROUTES | FEED_ROUTES:
            output_path = path.lstrip("/")
        check_generated = output_path is not None
        routes.append(
            {
                "check_generated": check_generated,
                "classifications": classify_route(
                    path,
                    legacy=legacy,
                    sitemap_paths=set(sitemap_paths),
                    tree_html_paths=tree_html_paths,
                    discovered_internal_paths=discovered_internal_paths,
                ),
                "expected_status": response.status,
                "legacy_status": legacy.get(path, {}).get("status"),
                "notebook_article": legacy.get(path, {}).get("source", "").lower().endswith(".ipynb"),
                "output_path": output_path,
                "path": path,
                "redirect": redirect,
                "sitemap": path in sitemap_paths,
                "url": f"{production_base}{path}",
            }
        )
        if parser:
            snapshot = parser.snapshot()
            snapshot.update(
                {
                    "archive_status": legacy.get(path, {}).get("status", "current" if path in NEW_ROUTES else None),
                    "path": path,
                    "source_kind": (
                        "notebook"
                        if legacy.get(path, {}).get("source", "").lower().endswith(".ipynb")
                        else "markdown"
                        if path in legacy
                        else "static_or_generated"
                    ),
                }
            )
            metadata.append(snapshot)

    routes.extend(
        [
            {
                "check_generated": False,
                "classifications": ["host_redirect", "live_only"],
                "expected_status": www_response.status,
                "legacy_status": None,
                "notebook_article": False,
                "output_path": None,
                "path": "/",
                "redirect": {"kind": "http", "target": www_response.redirect_target},
                "sitemap": False,
                "url": "https://www.nekrasovp.ru/",
            },
            {
                "check_generated": False,
                "classifications": ["not_found_probe", "live_only"],
                "expected_status": special_responses[MISSING_PROBE].status,
                "legacy_status": None,
                "notebook_article": False,
                "output_path": None,
                "path": MISSING_PROBE,
                "redirect": None,
                "sitemap": False,
                "url": f"{production_base}{MISSING_PROBE}",
            },
        ]
    )
    for url, response in alias_responses.items():
        path = canonical_path(url)
        assert path is not None
        routes.append(
            {
                "check_generated": False,
                "classifications": [
                    "host_redirect",
                    "internal_link_alias",
                    "legacy_github_host",
                    "live_only",
                ],
                "expected_status": response.status,
                "legacy_status": None,
                "notebook_article": False,
                "output_path": None,
                "path": path,
                "redirect": (
                    {"kind": "http", "target": response.redirect_target}
                    if response.redirect_target
                    else None
                ),
                "sitemap": False,
                "url": url,
            }
        )
    routes.sort(key=lambda item: (item["url"], item["path"]))
    metadata.sort(key=lambda item: item["path"])

    asset_groups: dict[str, dict[str, Any]] = {}
    for page_path, parser in route_parsers.items():
        for kind, references in (
            ("image", parser.image_references),
            ("stylesheet", parser.stylesheet_references),
        ):
            for reference in references:
                normalized = strip_fragment_and_query(reference)
                local_path = canonical_path(normalized)
                key = f"site:{local_path}" if local_path else f"external:{normalized}"
                group = asset_groups.setdefault(
                    key,
                    {
                        "kinds": set(),
                        "output_path": local_path.lstrip("/") if local_path else None,
                        "ownership": "site" if local_path else "external",
                        "referenced_by": set(),
                        "referenced_urls": set(),
                    },
                )
                group["kinds"].add(kind)
                group["referenced_by"].add(page_path)
                group["referenced_urls"].add(normalized)

    site_asset_urls = {
        f"{production_base}/{group['output_path']}"
        for group in asset_groups.values()
        if group["ownership"] == "site"
    }
    site_asset_responses = fetch_many(site_asset_urls, args.workers, method="HEAD")
    assets = []
    for key, group in sorted(asset_groups.items()):
        item = {
            "kinds": sorted(group["kinds"]),
            "output_path": group["output_path"],
            "ownership": group["ownership"],
            "referenced_by": sorted(group["referenced_by"]),
            "referenced_urls": sorted(group["referenced_urls"]),
            "sha256": None,
            "status": None,
        }
        if group["ownership"] == "site":
            response = site_asset_responses[f"{production_base}/{group['output_path']}"]
            if group["output_path"] in tree_files:
                body = run_bytes(
                    ["git", "show", f"{args.published_ref}:{group['output_path']}"],
                    repo_root,
                )
                verify_live_length(response, body, group["output_path"])
            else:
                body = fetch(f"{production_base}/{group['output_path']}").body
            item["status"] = response.status
            item["sha256"] = hashlib.sha256(body).hexdigest()
        assets.append(item)

    feeds = []
    for path, document in sorted(feed_documents.items()):
        response = feed_responses[f"{production_base}{path}"]
        feeds.append(
            {
                **document,
                "path": path,
                "sha256": hashlib.sha256(response.body).hexdigest(),
                "status": response.status,
                "url": f"{production_base}{path}",
            }
        )

    finished_at = utc_now()
    collection = {
        "canonical_host": "nekrasovp.ru",
        "collection_finished_at_utc": finished_at,
        "collection_started_at_utc": started_at,
        "default_branch": repo_state["default_branch"],
        "github_pages": {
            "build_type": pages_state.get("build_type"),
            "cname": pages_state.get("cname"),
            "https_enforced": pages_state.get("https_enforced"),
            "protected_domain_state": pages_state.get("protected_domain_state"),
            "source": pages_state.get("source"),
            "status": pages_state.get("status"),
        },
        "production_base_url": production_base,
        "production_content_evidence": {
            "feeds_and_sitemap": "live_get",
            "html_and_site_assets": "published_git_tree_with_live_status_and_content_length",
            "published_ref": args.published_ref,
            "published_sha": published_sha,
        },
        "repository": args.repository,
        "schema_version": SCHEMA_VERSION,
        "source_commits": {
            "default_branch": {"ref": args.master_ref, "sha": master_sha},
            "published_branch": {"ref": args.published_ref, "sha": published_sha},
        },
        "summary_counts": {
            "asset_references": len(assets),
            "feed_entries": {item["path"]: item["entry_count"] for item in feeds},
            "feeds": len(feeds),
            "html_metadata_records": len(metadata),
            "legacy_github_host_redirects": len(alias_responses),
            "legacy_routes": len(legacy),
            "new_article_or_resource_routes": len(NEW_ROUTES),
            "notebook_routes": sum(1 for row in legacy.values() if row["source"].lower().endswith(".ipynb")),
            "public_html_outside_sitemap": sum(
                1 for item in routes if "public_outside_sitemap" in item["classifications"]
            ),
            "route_records": len(routes),
            "sitemap_routes": len(sitemap_paths),
        },
    }

    if collection["default_branch"] != "master":
        raise RuntimeError(f"unexpected default branch: {collection['default_branch']}")
    if collection["github_pages"]["source"] != {"branch": "gh-pages", "path": "/"}:
        raise RuntimeError(f"unexpected Pages source: {collection['github_pages']['source']}")
    if www_response.status not in {301, 302, 307, 308} or www_response.redirect_target != f"{production_base}/":
        raise RuntimeError("www host redirect no longer targets the canonical apex")
    if special_responses[MISSING_PROBE].status != 404:
        raise RuntimeError("the fixed missing-route probe did not return 404")

    write_json(baseline_dir / "collection.json", collection)
    write_json(baseline_dir / "routes.json", {"routes": routes, "schema_version": SCHEMA_VERSION})
    write_json(baseline_dir / "metadata.json", {"pages": metadata, "schema_version": SCHEMA_VERSION})
    write_json(baseline_dir / "feeds.json", {"feeds": feeds, "schema_version": SCHEMA_VERSION})
    write_json(baseline_dir / "assets.json", {"assets": assets, "schema_version": SCHEMA_VERSION})
    return collection


def parse_args() -> argparse.Namespace:
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=package_root.parents[1])
    parser.add_argument("--baseline-dir", type=Path, default=package_root / "baseline")
    parser.add_argument("--legacy-manifest", type=Path, default=package_root / "inputs" / "legacy_routes.tsv")
    parser.add_argument("--repository", default="nekrasovp/nekrasovp.github.io")
    parser.add_argument("--production-base", default="https://nekrasovp.ru")
    parser.add_argument("--master-ref", default="origin/master")
    parser.add_argument("--published-ref", default="origin/gh-pages")
    parser.add_argument("--expected-sitemap-count", type=int, default=58)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        collection = collect(args)
    except Exception as error:  # noqa: BLE001 - CLI must make collection failures explicit
        print(f"BASE-001 collection failed: {error}", file=sys.stderr)
        return 1
    counts = collection["summary_counts"]
    print(
        "BASE-001 collection complete: "
        f"{counts['route_records']} route records, {counts['sitemap_routes']} sitemap routes, "
        f"{counts['legacy_routes']} legacy routes, {counts['feeds']} feeds, "
        f"{counts['asset_references']} asset references"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
