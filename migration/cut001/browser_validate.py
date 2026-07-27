#!/usr/bin/env python3
"""Run the CUT-001 browser, accessibility, and visual comparison matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any, Sequence
from urllib.parse import quote, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from migration.cut001.evidence import build_evidence_manifest  # noqa: E402

THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
ACCEPTED_READER_COMMIT = "137e1eb0ea620f1b15fff0ba81725eea23de1b7a"
READER_RELEASE = "pelican-ipynb-reader==0.1.0"
THEMELESS_REDIRECTS = {"pages/about.html", "pages/services.html"}
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}
VISUAL_CASES: dict[str, dict[str, str]] = {
    "home_en": {"language": "en", "page_type": "home", "route": "index.html"},
    "home_ru": {"language": "ru", "page_type": "home", "route": "ru/index.html"},
    "work": {
        "language": "en",
        "page_type": "work_about_writing",
        "route": "work/index.html",
    },
    "about": {
        "language": "en",
        "page_type": "work_about_writing",
        "route": "about/index.html",
    },
    "writing": {
        "language": "en",
        "page_type": "work_about_writing",
        "route": "writing/index.html",
    },
    "modern_essay": {
        "language": "en",
        "page_type": "modern_essay",
        "route": "ai-native-sdlc-engineering-accountability.html",
    },
    "legacy_markdown_en": {
        "language": "en",
        "page_type": "legacy_markdown",
        "route": "python-gil.html",
    },
    "legacy_markdown_ru": {
        "language": "ru",
        "page_type": "legacy_markdown",
        "route": "technical-debt-examples.html",
    },
    "notebook_en": {
        "language": "en",
        "page_type": "notebook",
        "route": "number-sequences.html",
    },
    "notebook_ru": {
        "language": "ru",
        "page_type": "notebook",
        "route": "mkrf-spb-geo-data.html",
    },
    "archive_en": {
        "language": "en",
        "page_type": "archive_deprecated",
        "route": "arbitrage.html",
    },
    "deprecated_en": {
        "language": "en",
        "page_type": "archive_deprecated",
        "route": "fixing-caching-sha2-password.html",
    },
    "not_found_en": {
        "language": "en",
        "page_type": "404",
        "route": "404.html",
    },
}
VISUAL_EQUIVALENCES = [
    {
        "canonical_case": "notebook_ru",
        "reason": (
            "The Russian notebook is also the only Russian archived notebook "
            "case; duplicate pixels are referenced instead of fabricated."
        ),
        "virtual_case": "archive_deprecated_ru",
    },
    {
        "canonical_case": "not_found_en",
        "reason": (
            "The static 404 document is language-neutral enough for the "
            "plan's Russian acceptable case; duplicate pixels are referenced."
        ),
        "virtual_case": "404_ru_acceptable",
    },
]


class BrowserValidationError(RuntimeError):
    """A fail-closed browser or visual evidence violation."""


def visual_matrix_contract() -> dict[str, Any]:
    page_types: dict[str, set[str]] = {}
    for case in VISUAL_CASES.values():
        page_types.setdefault(case["page_type"], set()).add(case["language"])
    page_types["archive_deprecated"].add("ru-equivalent")
    page_types["404"].add("ru-equivalent")
    return {
        "page_types": page_types,
        "themes": sorted(("light", "dark")),
        "viewports": sorted(VIEWPORTS),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise BrowserValidationError(result.stderr.strip())
    return result.stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_output_file(output_root: Path, url_path: str) -> Path | None:
    decoded = unquote(url_path)
    relative = PurePosixPath(decoded.lstrip("/") or "index.html")
    if relative.is_absolute() or ".." in relative.parts:
        return None
    if decoded.endswith("/"):
        relative = relative / "index.html"
    candidate = output_root.joinpath(*relative.parts)
    return candidate if candidate.is_file() else None


def _install_routes(
    context: Any,
    output_root: Path,
    network: dict[str, list[dict[str, str]]],
    *,
    local_hosts: set[str],
) -> None:
    def handle(route: Any) -> None:
        request = route.request
        parsed = urlparse(request.url)
        if parsed.hostname not in local_hosts:
            network["blocked_external"].append(
                {"resource_type": request.resource_type, "url": request.url}
            )
            route.abort()
            return
        candidate = _safe_output_file(output_root, parsed.path)
        if candidate is None:
            network["missing_same_origin"].append(
                {"resource_type": request.resource_type, "url": request.url}
            )
            route.abort()
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        network["fulfilled_same_origin"].append(
            {"resource_type": request.resource_type, "url": request.url}
        )
        route.fulfill(
            status=200,
            body=candidate.read_bytes(),
            content_type=content_type,
        )

    context.route("**/*", handle)


def _network() -> dict[str, list[dict[str, str]]]:
    return {
        "blocked_external": [],
        "fulfilled_same_origin": [],
        "missing_same_origin": [],
    }


def _assert_network(
    network: dict[str, list[dict[str, str]]],
    *,
    allowed_external_urls: set[str],
    allowed_missing_same_origin_urls: set[str],
    label: str,
) -> None:
    unexpected_missing = [
        item
        for item in network["missing_same_origin"]
        if item["url"] not in allowed_missing_same_origin_urls
    ]
    if unexpected_missing:
        raise BrowserValidationError(
            f"{label} requested missing same-origin files: "
            f"{unexpected_missing!r}"
        )
    unexpected = sorted(
        {
            item["url"]
            for item in network["blocked_external"]
            if item["url"] not in allowed_external_urls
        }
    )
    if unexpected:
        raise BrowserValidationError(
            f"{label} requested unreviewed external resources: {unexpected!r}"
        )


def _assert_exact_observations(
    *, expected: set[str], observed: set[str], label: str
) -> None:
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    if missing or unexpected:
        raise BrowserValidationError(
            f"{label} observation drift: missing={missing!r}, "
            f"unexpected={unexpected!r}"
        )


def _layout(page: Any, *, expected_language: str) -> dict[str, Any]:
    observation = page.evaluate(
        """expectedLanguage => {
          const toggle = document.querySelector('[data-pet-theme-toggle]');
          return {
            ariaPressed: toggle?.getAttribute('aria-pressed') || null,
            documentWidth: document.documentElement.scrollWidth,
            language: document.documentElement.lang,
            mainCount: document.querySelectorAll('main#main-content').length,
            theme: document.documentElement.dataset.theme || 'light',
            toggleCount: document.querySelectorAll('[data-pet-theme-toggle]').length,
            toggleHidden: toggle?.hidden ?? null,
            viewportWidth: window.innerWidth,
            expectedLanguage
          };
        }""",
        expected_language,
    )
    if (
        observation["language"] != expected_language
        or observation["mainCount"] != 1
        or observation["toggleCount"] != 1
        or observation["toggleHidden"] is not False
        or observation["documentWidth"] > observation["viewportWidth"] + 1
    ):
        raise BrowserValidationError(f"visual layout contract failed: {observation!r}")
    return observation


def _axe(page: Any, axe_script: Path) -> dict[str, Any]:
    page.add_script_tag(path=str(axe_script))
    result = page.evaluate(
        """async () => {
          const report = await axe.run(document, {
            resultTypes: ['violations', 'incomplete']
          });
          const slim = item => ({
            id: item.id,
            impact: item.impact,
            nodes: item.nodes.length
          });
          return {
            incomplete: report.incomplete.map(slim),
            passes: report.passes.length,
            violations: report.violations.map(slim)
          };
        }"""
    )
    if result["violations"]:
        raise BrowserValidationError(f"axe violations found: {result['violations']!r}")
    return result


def _screenshot(page: Any, artifact_root: Path, name: str) -> dict[str, Any]:
    path = artifact_root / "screenshots" / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=False)
    return {
        "path": path.relative_to(artifact_root).as_posix(),
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _preview_case(
    browser: Any,
    *,
    artifact_root: Path,
    axe_script: Path,
    case_name: str,
    case: dict[str, str],
    output_root: Path,
    viewport_name: str,
    viewport: dict[str, int],
    allowed_external_urls: set[str],
    allowed_missing_same_origin_urls: set[str],
) -> dict[str, Any]:
    network = _network()
    context = browser.new_context(viewport=viewport)
    _install_routes(
        context,
        output_root,
        network,
        local_hosts={"nekrasovp.ru"},
    )
    page = context.new_page()
    page.goto(
        f"https://nekrasovp.ru/{case['route']}",
        wait_until="networkidle",
    )
    light = _layout(page, expected_language=case["language"])
    if light["theme"] != "light" or light["ariaPressed"] != "false":
        raise BrowserValidationError(
            f"{case_name}:{viewport_name} did not start light: {light!r}"
        )
    axe_light = _axe(page, axe_script)
    light_screenshot = _screenshot(
        page,
        artifact_root,
        f"{case_name}-{viewport_name}-preview-light",
    )
    page.locator("[data-pet-theme-toggle]").click()
    dark = page.evaluate(
        """() => {
          const toggle = document.querySelector('[data-pet-theme-toggle]');
          return {
            ariaPressed: toggle?.getAttribute('aria-pressed') || null,
            stored: localStorage.getItem('pelican-engineering-theme'),
            theme: document.documentElement.dataset.theme || 'light'
          };
        }"""
    )
    if dark != {"ariaPressed": "true", "stored": "dark", "theme": "dark"}:
        raise BrowserValidationError(
            f"{case_name}:{viewport_name} dark toggle failed: {dark!r}"
        )
    axe_dark = _axe(page, axe_script)
    dark_screenshot = _screenshot(
        page,
        artifact_root,
        f"{case_name}-{viewport_name}-preview-dark",
    )
    context.close()
    _assert_network(
        network,
        allowed_external_urls=allowed_external_urls,
        allowed_missing_same_origin_urls=allowed_missing_same_origin_urls,
        label=f"{case_name}:{viewport_name}:preview",
    )
    return {
        "accessibility": {"dark": axe_dark, "light": axe_light},
        "dark": dark,
        "language": case["language"],
        "light": light,
        "network": {
            "blocked_external": network["blocked_external"],
            "fulfilled_same_origin": len(network["fulfilled_same_origin"]),
            "missing_same_origin": network["missing_same_origin"],
            "outbound_requests": 0,
        },
        "page_type": case["page_type"],
        "route": case["route"],
        "screenshots": {"dark": dark_screenshot, "light": light_screenshot},
        "viewport": viewport,
    }


def _production_reference(
    browser: Any,
    *,
    artifact_root: Path,
    case_name: str,
    case: dict[str, str],
    production_root: Path,
    viewport_name: str,
    viewport: dict[str, int],
    allowed_external_urls: set[str],
    allowed_missing_same_origin_urls: set[str],
) -> dict[str, Any]:
    network = _network()
    context = browser.new_context(viewport=viewport)
    _install_routes(
        context,
        production_root,
        network,
        local_hosts={"nekrasovp.github.io", "nekrasovp.ru"},
    )
    page = context.new_page()
    page.goto(
        f"https://nekrasovp.ru/{case['route']}",
        wait_until="networkidle",
    )
    observation = page.evaluate(
        """() => ({
          documentWidth: document.documentElement.scrollWidth,
          language: document.documentElement.lang || null,
          viewportWidth: window.innerWidth
        })"""
    )
    screenshot = _screenshot(
        page,
        artifact_root,
        f"{case_name}-{viewport_name}-production",
    )
    context.close()
    _assert_network(
        network,
        allowed_external_urls=allowed_external_urls,
        allowed_missing_same_origin_urls=allowed_missing_same_origin_urls,
        label=f"{case_name}:{viewport_name}:production",
    )
    return {
        "network": {
            "blocked_external": network["blocked_external"],
            "fulfilled_same_origin": len(network["fulfilled_same_origin"]),
            "missing_same_origin": network["missing_same_origin"],
            "outbound_requests": 0,
        },
        "observation": observation,
        "screenshot": screenshot,
        "viewport": viewport,
    }


def _all_page_toggle(
    browser: Any,
    *,
    output_root: Path,
    allowed_external_urls: set[str],
    allowed_missing_same_origin_urls: set[str],
) -> dict[str, Any]:
    network = _network()
    context = browser.new_context(viewport=VIEWPORTS["desktop"])
    _install_routes(
        context,
        output_root,
        network,
        local_hosts={"nekrasovp.ru"},
    )
    page = context.new_page()
    records: list[dict[str, Any]] = []
    for path in sorted(output_root.rglob("*.html")):
        relative = path.relative_to(output_root).as_posix()
        if relative in THEMELESS_REDIRECTS:
            continue
        page.goto(f"https://nekrasovp.ru/{relative}", wait_until="domcontentloaded")
        page.evaluate("localStorage.removeItem('pelican-engineering-theme')")
        page.reload(wait_until="domcontentloaded")
        before = page.evaluate(
            """() => {
              const toggle = document.querySelector('[data-pet-theme-toggle]');
              return {
                ariaPressed: toggle?.getAttribute('aria-pressed') || null,
                theme: document.documentElement.dataset.theme || 'light',
                toggleCount: document.querySelectorAll(
                  '[data-pet-theme-toggle]'
                ).length,
                toggleHidden: toggle?.hidden ?? null
              };
            }"""
        )
        if before != {
            "ariaPressed": "false",
            "theme": "light",
            "toggleCount": 1,
            "toggleHidden": False,
        }:
            raise BrowserValidationError(
                f"all-page first-visit toggle failed for {relative}: {before!r}"
            )
        page.locator("[data-pet-theme-toggle]").click()
        after = page.evaluate(
            """() => ({
              ariaPressed: document.querySelector(
                '[data-pet-theme-toggle]'
              )?.getAttribute('aria-pressed') || null,
              stored: localStorage.getItem('pelican-engineering-theme'),
              theme: document.documentElement.dataset.theme || 'light'
            })"""
        )
        if after != {"ariaPressed": "true", "stored": "dark", "theme": "dark"}:
            raise BrowserValidationError(
                f"all-page dark toggle failed for {relative}: {after!r}"
            )
        records.append({"after": after, "before": before, "output": relative})
    context.close()
    _assert_network(
        network,
        allowed_external_urls=allowed_external_urls,
        allowed_missing_same_origin_urls=allowed_missing_same_origin_urls,
        label="all-page-toggle",
    )
    if len(records) != 147:
        raise BrowserValidationError(
            f"expected 147 themed pages in the runtime toggle gate, got {len(records)}"
        )
    return {
        "blocked_external": network["blocked_external"],
        "count": len(records),
        "missing_same_origin": network["missing_same_origin"],
        "outbound_requests": 0,
        "records": records,
        "standalone_redirect_exemptions": sorted(THEMELESS_REDIRECTS),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise BrowserValidationError(
            "use the exact locked theme development environment"
        ) from error

    output_root = args.output_root.resolve()
    production_root = args.production_root.resolve()
    artifact_root = args.artifact_root.resolve()
    axe_script = args.axe_script.resolve()
    comparison = json.loads(args.comparison_report.read_text(encoding="utf-8"))
    allowed_external_urls = {
        record["url"]
        for field in (
            "external_preview_assets",
            "external_production_assets",
            "intentional_production_runtime_external",
        )
        for record in comparison["references"][field]
    }
    expected_runtime_external = {
        record["url"]
        for record in comparison["references"][
            "intentional_production_runtime_external"
        ]
    }
    allowed_missing_same_origin_urls = {
        "https://nekrasovp.ru/"
        + quote(record["target"], safe="/")
        for record in comparison["references"]["assets"]["unchanged_records"]
    }
    if (
        not output_root.is_dir()
        or not production_root.is_dir()
        or not axe_script.is_file()
    ):
        raise BrowserValidationError(
            "preview, production, or exact axe-core source is unavailable"
        )
    artifact_root.mkdir(parents=True, exist_ok=True)
    for case in VISUAL_CASES.values():
        if not (output_root / case["route"]).is_file():
            raise BrowserValidationError(
                f"preview matrix route is missing: {case['route']}"
            )
        if not (production_root / case["route"]).is_file():
            raise BrowserValidationError(
                f"production matrix route is missing: {case['route']}"
            )

    preview_cases: dict[str, Any] = {}
    production_cases: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_version = browser.version
        for case_name, case in VISUAL_CASES.items():
            for viewport_name, viewport in VIEWPORTS.items():
                key = f"{case_name}:{viewport_name}"
                preview_cases[key] = _preview_case(
                    browser,
                    artifact_root=artifact_root,
                    axe_script=axe_script,
                    case_name=case_name,
                    case=case,
                    output_root=output_root,
                    viewport_name=viewport_name,
                    viewport=viewport,
                    allowed_external_urls=allowed_external_urls,
                    allowed_missing_same_origin_urls=(
                        allowed_missing_same_origin_urls
                    ),
                )
                production_cases[key] = _production_reference(
                    browser,
                    artifact_root=artifact_root,
                    case_name=case_name,
                    case=case,
                    production_root=production_root,
                    viewport_name=viewport_name,
                    viewport=viewport,
                    allowed_external_urls=allowed_external_urls,
                    allowed_missing_same_origin_urls=(
                        allowed_missing_same_origin_urls
                    ),
                )
        all_page_toggle = _all_page_toggle(
            browser,
            output_root=output_root,
            allowed_external_urls=allowed_external_urls,
            allowed_missing_same_origin_urls=allowed_missing_same_origin_urls,
        )
        browser.close()

    accessibility_cases = {
        key: value["accessibility"] for key, value in preview_cases.items()
    }
    incomplete = sum(
        len(theme["incomplete"])
        for case in accessibility_cases.values()
        for theme in case.values()
    )
    screenshot_matrix = {
        key: {
            "dark": value["screenshots"]["dark"],
            "light": value["screenshots"]["light"],
            "production": production_cases[key]["screenshot"],
        }
        for key, value in preview_cases.items()
    }
    for equivalence in VISUAL_EQUIVALENCES:
        canonical = equivalence["canonical_case"]
        screenshot_matrix[equivalence["virtual_case"]] = {
            "canonical_case": canonical,
            "reason": equivalence["reason"],
            "screenshots": {
                viewport: screenshot_matrix[f"{canonical}:{viewport}"]
                for viewport in VIEWPORTS
            },
            "visual_equivalence": True,
        }
    observed_runtime_external = {
        item["url"]
        for case in production_cases.values()
        for item in case["network"]["blocked_external"]
    }
    _assert_exact_observations(
        expected=expected_runtime_external,
        observed=observed_runtime_external & expected_runtime_external,
        label="production runtime external allowlist",
    )
    observed_missing_same_origin = {
        item["url"]
        for case in (*preview_cases.values(), *production_cases.values())
        for item in case["network"]["missing_same_origin"]
    } | {
        item["url"] for item in all_page_toggle["missing_same_origin"]
    }
    _assert_exact_observations(
        expected=allowed_missing_same_origin_urls,
        observed=observed_missing_same_origin,
        label="unchanged missing same-origin asset allowlist",
    )

    accessibility = {
        "axe_core": re.search(
            r"axe v([0-9.]+)",
            axe_script.read_text(encoding="utf-8", errors="ignore"),
        )[1],
        "cases": accessibility_cases,
        "contract": "nekrasovp-cut001-accessibility.v1",
        "incomplete_groups": incomplete,
        "scans": len(accessibility_cases) * 2,
        "violations": 0,
    }
    matrix = {
        "cases": screenshot_matrix,
        "contract": "nekrasovp-cut001-screenshot-matrix.v1",
        "equivalences": VISUAL_EQUIVALENCES,
        "owner_visual_acceptance": "not_performed",
        "production_reference_commit": (
            "5c24ba21ec8b442e4b5280a47c85fab61165f8ce"
        ),
        "technical_evidence_not_human_acceptance": True,
        "visual_cases": VISUAL_CASES,
    }
    report = {
        "accessibility": accessibility,
        "all_generated_pages_theme_toggle": all_page_toggle,
        "chromium": browser_version,
        "contract": "nekrasovp-cut001-browser.v1",
        "playwright": version("playwright"),
        "preview_cases": preview_cases,
        "production_cases": production_cases,
        "production_runtime_external": {
            "expected": sorted(expected_runtime_external),
            "observed": sorted(observed_runtime_external),
        },
        "unchanged_missing_same_origin_assets": {
            "expected": sorted(allowed_missing_same_origin_urls),
            "observed": sorted(observed_missing_same_origin),
        },
        "accepted_reader_commit": ACCEPTED_READER_COMMIT,
        "reader_release": READER_RELEASE,
        "source_head": _git("rev-parse", "HEAD"),
        "source_status": _git(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
        "technical_evidence_not_human_acceptance": True,
        "theme_commit": THEME_COMMIT,
        "totals": {
            "accessibility_scans": accessibility["scans"],
            "all_page_toggle_cases": all_page_toggle["count"],
            "external_outbound_requests": 0,
            "production_reference_screenshots": len(production_cases),
            "screenshots": len(list((artifact_root / "screenshots").glob("*.png"))),
            "visual_preview_cases": len(preview_cases),
        },
        "visual_equivalences": VISUAL_EQUIVALENCES,
    }
    _write_json(artifact_root / "accessibility.json", accessibility)
    _write_json(artifact_root / "screenshot-matrix.json", matrix)
    _write_json(artifact_root / "browser-report.json", report)
    _write_json(
        artifact_root / "manifest.json",
        build_evidence_manifest(artifact_root, report["source_head"]),
    )
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--production-root", type=Path, required=True)
    result.add_argument("--artifact-root", type=Path, required=True)
    result.add_argument("--axe-script", type=Path, required=True)
    result.add_argument("--comparison-report", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    try:
        report = run(parser().parse_args(argv))
    except Exception as error:
        print(f"CUT-001 browser validation failed: {error}", file=sys.stderr)
        return 1
    totals = report["totals"]
    print(
        "CUT-001 browser validation passed: "
        f"{totals['visual_preview_cases']} preview cases, "
        f"{totals['production_reference_screenshots']} production references, "
        f"{totals['accessibility_scans']} axe scans, "
        f"{totals['all_page_toggle_cases']} generated-page toggle cases, "
        f"{totals['external_outbound_requests']} outbound requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
