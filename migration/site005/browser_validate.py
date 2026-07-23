"""Run the complete local SITE-005 browser matrix against generated output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from migration.site006v import browser_validate as shared  # noqa: E402

MANIFEST = REPO_ROOT / "migration/site005/materials.json"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


def _content_case(
    browser: Any,
    *,
    artifact_root: Path,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
    expected: dict[str, Any],
    java_script_enabled: bool,
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(
        viewport=viewport, java_script_enabled=java_script_enabled
    )
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    observation = page.evaluate(
        """() => {
          const tables = [...document.querySelectorAll('.pet-prose table')];
          const code = [...document.querySelectorAll('.pet-prose pre')];
          const figures = [...document.querySelectorAll('figure.article-diagram')];
          const aside = document.querySelector('aside.article-related a');
          return {
            articleCount: document.querySelectorAll('article.pet-prose').length,
            codeBlocks: code.length,
            codeOverflowModes: code.map(node => getComputedStyle(node).overflowX),
            documentWidth: document.documentElement.scrollWidth,
            externalRuntimeSources: [...document.querySelectorAll(
              'script[src], link[rel="stylesheet"]'
            )]
              .map(node => node.src || node.href)
              .filter(value => new URL(value, location.href).hostname !== location.hostname),
            figureCaptions: figures.map(node => ({
              ariaLabel: node.getAttribute('aria-label'),
              caption: (node.querySelector('figcaption')?.textContent || '').trim()
            })),
            h1: document.querySelectorAll('main#main-content h1').length,
            mermaidRuntime: document.querySelectorAll(
              'script[src*="mermaid"], .mermaid, [data-mermaid]'
            ).length,
            reciprocalHref: aside?.getAttribute('href') || null,
            tableCount: tables.length,
            tableOverflowModes: tables.map(node => getComputedStyle(node).overflowX),
            overflowingTables: tables.filter(
              node => node.scrollWidth > node.clientWidth + 1
            ).length,
            accessibleOverflowingTables: tables.filter(node =>
              node.scrollWidth > node.clientWidth + 1
              && node.getAttribute('role') === 'region'
              && node.getAttribute('tabindex') === '0'
              && node.getAttribute('aria-label')
            ).length,
            viewportWidth: window.innerWidth
          };
        }"""
    )
    expected_tables = len(expected["rendered"]["table_shapes"])
    expected_code = 0 if expected["rendered"]["code_sha256"] == (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    ) else (6 if route_name == "ai-native-delivery-contract" else 1)
    expected_figures = 1 if "figure" in expected else 0
    if observation["articleCount"] != 1 or observation["h1"] != 1:
        raise RuntimeError(f"SITE-005 semantic article shell failed: {observation!r}")
    if (
        observation["tableCount"] != expected_tables
        or observation["codeBlocks"] != expected_code
        or len(observation["figureCaptions"]) != expected_figures
    ):
        raise RuntimeError(f"SITE-005 table/code/figure count failed: {observation!r}")
    if observation["documentWidth"] > observation["viewportWidth"] + 1:
        raise RuntimeError(f"SITE-005 page-level horizontal overflow: {observation!r}")
    if observation["externalRuntimeSources"] or observation["mermaidRuntime"]:
        raise RuntimeError(f"SITE-005 external/Mermaid runtime found: {observation!r}")
    if observation["reciprocalHref"] != expected["companion_route"]:
        raise RuntimeError(f"SITE-005 companion route failed: {observation!r}")
    if any(value not in {"auto", "scroll"} for value in observation["tableOverflowModes"]):
        raise RuntimeError(f"SITE-005 table is not locally scrollable: {observation!r}")
    if any(value not in {"auto", "scroll"} for value in observation["codeOverflowModes"]):
        raise RuntimeError(f"SITE-005 code is not locally scrollable: {observation!r}")
    if java_script_enabled and (
        observation["overflowingTables"]
        != observation["accessibleOverflowingTables"]
    ):
        raise RuntimeError(
            f"SITE-005 overflowing table lacks keyboard semantics: {observation!r}"
        )
    if expected_figures:
        figure = expected["figure"]
        if observation["figureCaptions"] != [
            {
                "ariaLabel": figure["aria_label"],
                "caption": figure["caption"],
            }
        ]:
            raise RuntimeError(f"SITE-005 figure meaning failed: {observation!r}")
    content_target = page.locator(
        "figure.article-diagram, .pet-prose table, .pet-prose pre"
    ).first
    if content_target.count():
        content_target.scroll_into_view_if_needed()
    suffix = "js" if java_script_enabled else "nojs-content"
    screenshot = shared._screenshot(
        page, artifact_root, f"{route_name}-{viewport_name}-{suffix}"
    )
    code_screenshot = None
    if expected_code:
        code_target = page.locator(".pet-prose pre").first
        code_target.scroll_into_view_if_needed()
        code_screenshot = shared._screenshot(
            page,
            artifact_root,
            f"{route_name}-{viewport_name}-{suffix}-code",
        )
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"SITE-005 network boundary failed: {network!r}")
    return {
        "java_script_enabled": java_script_enabled,
        "code_screenshot": code_screenshot,
        "network": {
            "external": [],
            "fulfilled_same_origin": len(network["fulfilled_same_origin"]),
            "missing_same_origin": [],
        },
        "observation": observation,
        "screenshot": screenshot,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Playwright is unavailable in the browser validation runtime") from error

    output_root = args.output_root.resolve()
    artifact_root = args.artifact_root.resolve()
    axe_script = args.axe_script.resolve()
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["source"].removesuffix(".md"): record for record in payload["materials"]}
    routes = {name: record["route"].lstrip("/") for name, record in records.items()}
    if not output_root.is_dir() or not axe_script.is_file():
        raise RuntimeError("generated output or local axe-core script is unavailable")
    artifact_root.mkdir(parents=True, exist_ok=True)
    for route in routes.values():
        if not (output_root / route).is_file():
            raise RuntimeError(f"SITE-005 route is missing: {route}")

    theme_cases: dict[str, Any] = {}
    no_javascript: dict[str, Any] = {}
    content_cases: dict[str, Any] = {}
    content_no_javascript: dict[str, Any] = {}
    print_cases: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_version = browser.version
        for route_name, route_path in routes.items():
            for viewport_name, viewport in VIEWPORTS.items():
                key = f"{route_name}:{viewport_name}"
                try:
                    theme_cases[key] = shared._theme_case(
                        browser,
                        artifact_root=artifact_root,
                        axe_script=axe_script,
                        output_root=output_root,
                        route_name=route_name,
                        route_path=route_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                except RuntimeError as error:
                    raise RuntimeError(f"{key}: {error}") from error
                no_javascript[key] = shared._no_javascript_case(
                    browser,
                    artifact_root=artifact_root,
                    output_root=output_root,
                    route_name=route_name,
                    route_path=route_path,
                    viewport_name=viewport_name,
                    viewport=viewport,
                )
                content_cases[key] = _content_case(
                    browser,
                    artifact_root=artifact_root,
                    output_root=output_root,
                    route_name=route_name,
                    route_path=route_path,
                    viewport_name=viewport_name,
                    viewport=viewport,
                    expected=records[route_name],
                    java_script_enabled=True,
                )
                content_no_javascript[key] = _content_case(
                    browser,
                    artifact_root=artifact_root,
                    output_root=output_root,
                    route_name=route_name,
                    route_path=route_path,
                    viewport_name=viewport_name,
                    viewport=viewport,
                    expected=records[route_name],
                    java_script_enabled=False,
                )
            print_cases[route_name] = shared._print_case(
                browser,
                artifact_root=artifact_root,
                output_root=output_root,
                route_name=route_name,
                route_path=route_path,
            )
        browser.close()

    screenshots = sorted(artifact_root.glob("*.png"))
    report = {
        "axe_core": re.search(
            r"axe v([0-9.]+)", axe_script.read_text(errors="ignore")
        )[1],
        "cases": theme_cases,
        "chromium": browser_version,
        "content_cases": content_cases,
        "content_no_javascript": content_no_javascript,
        "contract": "nekrasovp-site005-browser.v1",
        "no_javascript": no_javascript,
        "playwright": version("playwright"),
        "print": print_cases,
        "routes": routes,
        "screenshots": [
            {
                "path": path.name,
                "sha256": shared._sha256(path),
                "size": path.stat().st_size,
            }
            for path in screenshots
        ],
        "source_head": shared._git("rev-parse", "HEAD"),
        "source_status": shared._git(
            "status", "--porcelain=v1", "--untracked-files=all"
        ),
        "technical_evidence_not_human_acceptance": True,
        "totals": {
            "axe_scans": len(theme_cases) * 2,
            "browser_cases": len(theme_cases),
            "content_cases": len(content_cases),
            "content_no_javascript_cases": len(content_no_javascript),
            "external_requests": 0,
            "no_javascript_cases": len(no_javascript) + len(content_no_javascript),
            "print_cases": len(print_cases),
            "screenshots": len(screenshots),
        },
        "viewports": VIEWPORTS,
    }
    (artifact_root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--artifact-root", type=Path, required=True)
    result.add_argument("--axe-script", type=Path, required=True)
    return result


def main() -> int:
    try:
        report = run(parser().parse_args())
    except Exception as error:
        print(f"SITE-005 browser validation failed: {error}")
        return 1
    print(
        "SITE-005 browser validation passed: "
        f"{report['totals']['browser_cases']} light/dark/keyboard cases, "
        f"{report['totals']['no_javascript_cases']} no-JavaScript cases, "
        f"{report['totals']['axe_scans']} axe scans, "
        f"{report['totals']['print_cases']} print cases, zero external requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
