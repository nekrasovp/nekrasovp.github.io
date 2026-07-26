"""Run the SITE-004 local browser and accessibility matrix."""

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

THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
SITE004_ROUTES = {
    "home": "index.html",
    "ru": "ru/index.html",
    "work": "work/index.html",
    "writing": "writing/index.html",
    "about": "about/index.html",
    "not_found": "404.html",
}
INHERITED_ROUTES = {
    "code": "ai-native-delivery-contract.html",
    "notebook": "number-sequences.html",
    "wide_table": "stock-data-with-pandas-datareader.html",
}
REDIRECTS = {
    "redirect_about": {
        "path": "pages/about.html",
        "target": "https://nekrasovp.ru/about/",
    },
    "redirect_services": {
        "path": "pages/services.html",
        "target": "https://nekrasovp.ru/work/",
    },
}
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


def _blocked_storage_case(
    browser: Any,
    *,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport)
    context.add_init_script(
        """(() => {
          const fail = () => { throw new DOMException('blocked', 'SecurityError'); };
          Object.defineProperty(Storage.prototype, 'getItem', {value: fail});
          Object.defineProperty(Storage.prototype, 'setItem', {value: fail});
        })()"""
    )
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    initial = page.evaluate(
        """() => ({
          ariaPressed: document.querySelector('[data-pet-theme-toggle]')
            ?.getAttribute('aria-pressed'),
          theme: document.documentElement.dataset.theme || 'light',
          toggleHidden: document.querySelector('[data-pet-theme-toggle]')?.hidden
        })"""
    )
    if initial != {
        "ariaPressed": "false",
        "theme": "light",
        "toggleHidden": False,
    }:
        raise RuntimeError(
            f"{route_name}:{viewport_name} blocked-storage fallback failed: {initial!r}"
        )
    page.locator("[data-pet-theme-toggle]").click()
    after_toggle = page.evaluate(
        """() => ({
          ariaPressed: document.querySelector('[data-pet-theme-toggle]')
            ?.getAttribute('aria-pressed'),
          theme: document.documentElement.dataset.theme || 'light'
        })"""
    )
    if after_toggle != {"ariaPressed": "true", "theme": "dark"}:
        raise RuntimeError(
            f"{route_name}:{viewport_name} blocked-storage toggle failed: "
            f"{after_toggle!r}"
        )
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"blocked-storage network boundary failed: {network!r}")
    return {
        "after_toggle": after_toggle,
        "external_requests": 0,
        "initial": initial,
    }


def _dark_system_first_visit(
    browser: Any,
    *,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport, color_scheme="dark")
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    observation = page.evaluate(
        """() => ({
          background: getComputedStyle(document.body).backgroundColor,
          stored: localStorage.getItem('pelican-engineering-theme'),
          systemDark: matchMedia('(prefers-color-scheme: dark)').matches,
          theme: document.documentElement.dataset.theme || 'light'
        })"""
    )
    if (
        not observation["systemDark"]
        or observation["stored"] is not None
        or observation["theme"] != "light"
        or observation["background"] == "rgb(16, 23, 18)"
    ):
        raise RuntimeError(
            f"{route_name}:{viewport_name} system-dark first visit was not light: "
            f"{observation!r}"
        )
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"system-dark network boundary failed: {network!r}")
    return {**observation, "external_requests": 0}


def _page_semantics_case(
    browser: Any,
    *,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport)
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    observation = page.evaluate(
        """() => ({
          currentLinks: document.querySelectorAll('[aria-current="page"]').length,
          documentWidth: document.documentElement.scrollWidth,
          externalRuntimeSources: [...document.querySelectorAll(
            'script[src], link[rel="stylesheet"], img[src]'
          )].map(node => node.src || node.href)
            .filter(value => new URL(value, location.href).hostname !== location.hostname),
          h1: document.querySelectorAll('main#main-content h1').length,
          lang: document.documentElement.lang,
          main: document.querySelectorAll('main#main-content[tabindex="-1"]').length,
          viewportWidth: innerWidth
        })"""
    )
    expected_lang = "ru" if route_name == "ru" else "en"
    if (
        observation["main"] != 1
        or observation["h1"] != 1
        or observation["lang"] != expected_lang
        or observation["documentWidth"] > observation["viewportWidth"] + 1
        or observation["externalRuntimeSources"]
    ):
        raise RuntimeError(
            f"{route_name}:{viewport_name} SITE-004 page semantics failed: "
            f"{observation!r}"
        )
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"SITE-004 page network boundary failed: {network!r}")
    return {**observation, "external_requests": 0}


def _idle_header_case(
    browser: Any,
    *,
    artifact_root: Path,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport)
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    page.evaluate("scrollTo(0, 0)")
    header = page.locator(".site004-header")
    if not header.is_visible() or page.evaluate("scrollY") != 0:
        raise RuntimeError(f"{route_name}:{viewport_name} idle header is not visible")
    light = shared._screenshot(
        page,
        artifact_root,
        f"{route_name}-{viewport_name}-idle-light",
    )
    page.locator("[data-pet-theme-toggle]").click()
    page.reload(wait_until="networkidle")
    page.evaluate("scrollTo(0, 0)")
    if page.locator("html").get_attribute("data-theme") != "dark":
        raise RuntimeError(
            f"{route_name}:{viewport_name} idle dark persistence failed"
        )
    dark = shared._screenshot(
        page,
        artifact_root,
        f"{route_name}-{viewport_name}-idle-dark",
    )
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"idle-header network boundary failed: {network!r}")
    return {"dark": dark, "external_requests": 0, "light": light}


def _redirect_case(
    browser: Any,
    *,
    output_root: Path,
    route_name: str,
    route_path: str,
    target: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport, java_script_enabled=False)
    shared._install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    page.wait_for_url(target, timeout=5_000)
    final_url = page.url
    context.close()
    if final_url != target:
        raise RuntimeError(
            f"{route_name}:{viewport_name} redirect expected={target!r} "
            f"actual={final_url!r}"
        )
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"redirect network boundary failed: {network!r}")
    return {
        "external_requests": 0,
        "final_url": final_url,
        "java_script_enabled": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Playwright is unavailable in the browser runtime") from error

    output_root = args.output_root.resolve()
    artifact_root = args.artifact_root.resolve()
    axe_script = args.axe_script.resolve()
    routes = {**SITE004_ROUTES, **INHERITED_ROUTES}
    if not output_root.is_dir() or not axe_script.is_file():
        raise RuntimeError("generated output or local axe-core script is unavailable")
    artifact_root.mkdir(parents=True, exist_ok=True)
    for route in routes.values():
        if not (output_root / route).is_file():
            raise RuntimeError(f"browser route is missing: {route}")
    for redirect in REDIRECTS.values():
        if not (output_root / redirect["path"]).is_file():
            raise RuntimeError(f"redirect route is missing: {redirect['path']}")

    theme_cases: dict[str, Any] = {}
    no_javascript: dict[str, Any] = {}
    semantics: dict[str, Any] = {}
    blocked_storage: dict[str, Any] = {}
    dark_system_first_visit: dict[str, Any] = {}
    idle_headers: dict[str, Any] = {}
    redirect_cases: dict[str, Any] = {}
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
                        expect_wide_table=route_name == "wide_table",
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
                    expect_wide_table=route_name == "wide_table",
                )
                if route_name in SITE004_ROUTES:
                    semantics[key] = _page_semantics_case(
                        browser,
                        output_root=output_root,
                        route_name=route_name,
                        route_path=route_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                    blocked_storage[key] = _blocked_storage_case(
                        browser,
                        output_root=output_root,
                        route_name=route_name,
                        route_path=route_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                    dark_system_first_visit[key] = _dark_system_first_visit(
                        browser,
                        output_root=output_root,
                        route_name=route_name,
                        route_path=route_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                    idle_headers[key] = _idle_header_case(
                        browser,
                        artifact_root=artifact_root,
                        output_root=output_root,
                        route_name=route_name,
                        route_path=route_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
            print_cases[route_name] = shared._print_case(
                browser,
                artifact_root=artifact_root,
                output_root=output_root,
                route_name=route_name,
                route_path=route_path,
            )
        for redirect_name, redirect in REDIRECTS.items():
            for viewport_name, viewport in VIEWPORTS.items():
                key = f"{redirect_name}:{viewport_name}"
                redirect_cases[key] = _redirect_case(
                    browser,
                    output_root=output_root,
                    route_name=redirect_name,
                    route_path=redirect["path"],
                    target=redirect["target"],
                    viewport_name=viewport_name,
                    viewport=viewport,
                )
        browser.close()

    screenshots = sorted(artifact_root.glob("*.png"))
    report = {
        "axe_core": re.search(
            r"axe v([0-9.]+)", axe_script.read_text(errors="ignore")
        )[1],
        "blocked_storage": blocked_storage,
        "cases": theme_cases,
        "chromium": browser_version,
        "contract": "nekrasovp-site004-browser.v1",
        "dark_system_first_visit": dark_system_first_visit,
        "idle_headers": idle_headers,
        "no_javascript": no_javascript,
        "page_semantics": semantics,
        "playwright": version("playwright"),
        "print": print_cases,
        "redirects": redirect_cases,
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
        "theme_commit": THEME_COMMIT,
        "totals": {
            "axe_scans": len(theme_cases) * 2,
            "blocked_storage_cases": len(blocked_storage),
            "browser_cases": len(theme_cases),
            "dark_system_first_visit_cases": len(dark_system_first_visit),
            "external_requests": 0,
            "idle_header_cases": len(idle_headers),
            "no_javascript_cases": len(no_javascript),
            "print_cases": len(print_cases),
            "redirect_cases": len(redirect_cases),
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
        print(f"SITE-004 browser validation failed: {error}")
        return 1
    print(
        "SITE-004 browser validation passed: "
        f"{report['totals']['browser_cases']} light/dark/persistence/keyboard cases, "
        f"{report['totals']['no_javascript_cases']} no-JavaScript cases, "
        f"{report['totals']['blocked_storage_cases']} blocked-storage cases, "
        f"{report['totals']['dark_system_first_visit_cases']} system-dark cases, "
        f"{report['totals']['idle_header_cases']} idle-header cases, "
        f"{report['totals']['axe_scans']} axe scans, "
        f"{report['totals']['print_cases']} print cases, "
        f"{report['totals']['redirect_cases']} redirect cases, zero external requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
