"""Run the local SITE-006V browser matrix against generated static output."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
ROUTES = {
    "archive": "archives.html",
    "article": "python-gil.html",
    "index": "index.html",
    "notebook": "number-sequences.html",
    "page": "pages/about.html",
}
WIDE_TABLE_ROUTE = "stock-data-with-pandas-datareader.html"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}
AXE_CONTENT_LEDGER = {
    "notebook:mobile:dark": {"incomplete": {"color-contrast": 3}, "violations": {}},
    "notebook:mobile:light": {"incomplete": {"color-contrast": 3}, "violations": {}},
    "page:desktop:dark": {"incomplete": {}, "violations": {"heading-order": 1}},
    "page:desktop:light": {"incomplete": {}, "violations": {"heading-order": 1}},
    "page:mobile:dark": {"incomplete": {}, "violations": {"heading-order": 1}},
    "page:mobile:light": {"incomplete": {}, "violations": {"heading-order": 1}},
    "wide_table:desktop:light": {
        "incomplete": {"color-contrast": 6},
        "violations": {},
    },
    "wide_table:mobile:light": {
        "incomplete": {"color-contrast": 99},
        "violations": {},
    },
}
ZERO_AXE_FINDINGS = {"incomplete": {}, "violations": {}}


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
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _safe_output_file(output_root: Path, url_path: str) -> Path | None:
    decoded = unquote(url_path)
    relative = PurePosixPath(decoded.lstrip("/") or "index.html")
    if relative.is_absolute() or ".." in relative.parts:
        return None
    if decoded.endswith("/"):
        relative = relative / "index.html"
    candidate = output_root.joinpath(*relative.parts)
    return candidate if candidate.is_file() else None


def _install_local_routes(context: Any, output_root: Path, network: dict[str, Any]) -> None:
    def handle(route: Any) -> None:
        url = route.request.url
        parsed = urlparse(url)
        if parsed.hostname != "nekrasovp.ru":
            network["external"].append(url)
            route.abort()
            return
        candidate = _safe_output_file(output_root, parsed.path)
        if candidate is None:
            network["missing_same_origin"].append(url)
            route.abort()
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        network["fulfilled_same_origin"].append(url)
        route.fulfill(
            status=200,
            body=candidate.read_bytes(),
            content_type=content_type,
        )

    context.route("**/*", handle)


def _assert_layout(page: Any, *, notebook_mobile: bool) -> dict[str, Any]:
    layout = page.evaluate(
        """() => ({
          documentWidth: document.documentElement.scrollWidth,
          mainCount: document.querySelectorAll('main#main-content[tabindex="-1"]').length,
          viewportWidth: window.innerWidth,
          overflowingOutputs: [...document.querySelectorAll('.output_html')]
            .filter(element => element.scrollWidth > element.clientWidth + 1).length,
          wideTableScrollers: document.querySelectorAll(
            '[data-pet-table-scroller="true"][role="region"][tabindex="0"]'
          ).length
        })"""
    )
    if layout["mainCount"] != 1:
        raise RuntimeError(f"browser lost the one semantic main target: {layout!r}")
    if layout["documentWidth"] > layout["viewportWidth"] + 1:
        raise RuntimeError(f"page-level horizontal overflow: {layout!r}")
    if notebook_mobile and (
        layout["wideTableScrollers"] < 1 or layout["overflowingOutputs"] < 1
    ):
        raise RuntimeError(f"mobile notebook has no accessible wide-table scroller: {layout!r}")
    return layout


def _keyboard_case(page: Any) -> dict[str, Any]:
    page.evaluate("document.activeElement.blur()")
    page.keyboard.press("Tab")
    first = page.evaluate(
        """() => ({
          className: document.activeElement.className,
          tagName: document.activeElement.tagName
        })"""
    )
    if "pet-skip-link" not in str(first["className"]):
        raise RuntimeError(f"skip link is not the first keyboard target: {first!r}")
    focus_order = []
    for _ in range(20):
        page.keyboard.press("Tab")
        current = page.evaluate(
            """() => ({
              ariaLabel: document.activeElement.getAttribute('aria-label'),
              className: document.activeElement.className,
              tagName: document.activeElement.tagName,
              text: (document.activeElement.textContent || '').trim().slice(0, 80)
            })"""
        )
        focus_order.append(current)
        if "pet-theme-toggle" in str(current["className"]):
            break
    if not any("pet-theme-toggle" in str(item["className"]) for item in focus_order):
        raise RuntimeError("theme toggle is not keyboard reachable")

    page.locator(".pet-skip-link").focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(50)
    skip_target = page.evaluate("document.activeElement.id")
    if skip_target != "main-content":
        raise RuntimeError(f"skip link did not focus main-content: {skip_target!r}")
    return {"first": first, "focus_order": focus_order, "skip_target": skip_target}


def _axe(
    page: Any,
    axe_script: Path,
    *,
    expected: dict[str, dict[str, int]],
) -> dict[str, Any]:
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
    observed = {
        category: {item["id"]: item["nodes"] for item in result[category]}
        for category in ("incomplete", "violations")
    }
    if observed != expected:
        raise RuntimeError(
            f"axe finding ledger mismatch: expected={expected!r} observed={observed!r}"
        )
    result["content_owned_findings"] = observed
    return result


def _screenshot(page: Any, artifact_root: Path, name: str) -> dict[str, Any]:
    path = artifact_root / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return {
        "path": path.name,
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _theme_case(
    browser: Any,
    *,
    artifact_root: Path,
    axe_script: Path,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
    expect_wide_table: bool = False,
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport)
    _install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    light = page.evaluate(
        """() => {
          const toggle = document.querySelector('[data-pet-theme-toggle]');
          return {
            ariaPressed: toggle.getAttribute('aria-pressed'),
            stored: localStorage.getItem('pelican-engineering-theme'),
            theme: document.documentElement.dataset.theme || 'light',
            toggleHidden: toggle.hidden
          };
        }"""
    )
    if light != {
        "ariaPressed": "false",
        "stored": None,
        "theme": "light",
        "toggleHidden": False,
    }:
        raise RuntimeError(f"first-visit light contract failed: {light!r}")
    layout_light = _assert_layout(
        page,
        notebook_mobile=expect_wide_table and viewport_name == "mobile",
    )
    keyboard = _keyboard_case(page)
    axe_light = _axe(
        page,
        axe_script,
        expected=AXE_CONTENT_LEDGER.get(
            f"{route_name}:{viewport_name}:light", ZERO_AXE_FINDINGS
        ),
    )
    light_shot = _screenshot(
        page, artifact_root, f"{route_name}-{viewport_name}-light"
    )

    page.locator("[data-pet-theme-toggle]").click()
    page.reload(wait_until="networkidle")
    dark = page.evaluate(
        """() => {
          const toggle = document.querySelector('[data-pet-theme-toggle]');
          return {
            ariaPressed: toggle.getAttribute('aria-pressed'),
            earlyMark: performance.getEntriesByName('pet-theme-applied').length,
            stored: localStorage.getItem('pelican-engineering-theme'),
            theme: document.documentElement.dataset.theme || 'light'
          };
        }"""
    )
    if (
        dark["ariaPressed"] != "true"
        or dark["stored"] != "dark"
        or dark["theme"] != "dark"
        or dark["earlyMark"] < 1
    ):
        raise RuntimeError(f"persisted dark contract failed: {dark!r}")
    layout_dark = _assert_layout(
        page,
        notebook_mobile=expect_wide_table and viewport_name == "mobile",
    )
    axe_dark = _axe(
        page,
        axe_script,
        expected=AXE_CONTENT_LEDGER.get(
            f"{route_name}:{viewport_name}:dark", ZERO_AXE_FINDINGS
        ),
    )
    dark_shot = _screenshot(page, artifact_root, f"{route_name}-{viewport_name}-dark")
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"network boundary failed: {network!r}")
    return {
        "axe_dark": axe_dark,
        "axe_light": axe_light,
        "dark": dark,
        "keyboard": keyboard,
        "layout_dark": layout_dark,
        "layout_light": layout_light,
        "light": light,
        "network": {
            "external": [],
            "fulfilled_same_origin": len(network["fulfilled_same_origin"]),
            "missing_same_origin": [],
        },
        "screenshots": [light_shot, dark_shot],
    }


def _no_javascript_case(
    browser: Any,
    *,
    artifact_root: Path,
    output_root: Path,
    route_name: str,
    route_path: str,
    viewport_name: str,
    viewport: dict[str, int],
    expect_wide_table: bool = False,
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=viewport, java_script_enabled=False)
    _install_local_routes(context, output_root, network)
    page = context.new_page()
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    fallback = page.locator("html").get_attribute("data-theme")
    if fallback is not None or page.locator("[data-pet-theme-toggle]").is_visible():
        raise RuntimeError("no-JavaScript page did not retain the light hidden-toggle fallback")
    layout = _assert_layout(page, notebook_mobile=False)
    if (
        expect_wide_table
        and viewport_name == "mobile"
        and layout["overflowingOutputs"] < 1
    ):
        raise RuntimeError(f"no-JavaScript wide table is not locally scrollable: {layout!r}")
    page.keyboard.press("Tab")
    if "pet-skip-link" not in str(page.locator(":focus").get_attribute("class")):
        raise RuntimeError("no-JavaScript skip link is not keyboard reachable")
    screenshot = _screenshot(page, artifact_root, f"{route_name}-{viewport_name}-nojs")
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"no-JavaScript network boundary failed: {network!r}")
    return {
        "layout": layout,
        "light_fallback": True,
        "network": {
            "external": [],
            "fulfilled_same_origin": len(network["fulfilled_same_origin"]),
            "missing_same_origin": [],
        },
        "screenshot": screenshot,
        "skip_link_keyboard_reachable": True,
        "theme_toggle_hidden": True,
    }


def _print_case(
    browser: Any,
    *,
    artifact_root: Path,
    output_root: Path,
    route_name: str,
    route_path: str,
) -> dict[str, Any]:
    network = {"external": [], "fulfilled_same_origin": [], "missing_same_origin": []}
    context = browser.new_context(viewport=VIEWPORTS["desktop"])
    context.add_init_script(
        "localStorage.setItem('pelican-engineering-theme', 'dark')"
    )
    _install_local_routes(context, output_root, network)
    page = context.new_page()
    page.emulate_media(media="print")
    page.goto(f"https://nekrasovp.ru/{route_path}", wait_until="networkidle")
    colors = page.evaluate(
        """() => ({
          background: getComputedStyle(document.body).backgroundColor,
          color: getComputedStyle(document.body).color,
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: window.innerWidth
        })"""
    )
    if colors["background"] == "rgb(16, 23, 18)":
        raise RuntimeError(f"print retained the dark background: {colors!r}")
    if colors["documentWidth"] > colors["viewportWidth"] + 1:
        raise RuntimeError(f"print surface overflows the viewport: {colors!r}")
    screenshot = _screenshot(page, artifact_root, f"{route_name}-desktop-print")
    context.close()
    if network["external"] or network["missing_same_origin"]:
        raise RuntimeError(f"print network boundary failed: {network!r}")
    return {"computed": colors, "light_print": True, "screenshot": screenshot}


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("install the locked theme development environment") from error

    output_root = args.output_root.resolve()
    artifact_root = args.artifact_root.resolve()
    axe_script = args.axe_script.resolve()
    if not output_root.is_dir() or not axe_script.is_file():
        raise RuntimeError("generated output or local axe-core script is unavailable")
    artifact_root.mkdir(parents=True, exist_ok=True)
    for route in ROUTES.values():
        if not (output_root / route).is_file():
            raise RuntimeError(f"representative route is missing: {route}")
    if not (output_root / WIDE_TABLE_ROUTE).is_file():
        raise RuntimeError(f"wide-table route is missing: {WIDE_TABLE_ROUTE}")

    cases: dict[str, Any] = {}
    no_javascript: dict[str, Any] = {}
    wide_table: dict[str, Any] = {}
    wide_table_no_javascript: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_version = browser.version
        for route_name, route_path in ROUTES.items():
            for viewport_name, viewport in VIEWPORTS.items():
                key = f"{route_name}:{viewport_name}"
                cases[key] = _theme_case(
                    browser,
                    artifact_root=artifact_root,
                    axe_script=axe_script,
                    output_root=output_root,
                    route_name=route_name,
                    route_path=route_path,
                    viewport_name=viewport_name,
                    viewport=viewport,
                )
                no_javascript[key] = _no_javascript_case(
                    browser,
                    artifact_root=artifact_root,
                    output_root=output_root,
                    route_name=route_name,
                    route_path=route_path,
                    viewport_name=viewport_name,
                    viewport=viewport,
                )
        for viewport_name, viewport in VIEWPORTS.items():
            wide_table[viewport_name] = _theme_case(
                browser,
                artifact_root=artifact_root,
                axe_script=axe_script,
                output_root=output_root,
                route_name="wide_table",
                route_path=WIDE_TABLE_ROUTE,
                viewport_name=viewport_name,
                viewport=viewport,
                expect_wide_table=True,
            )
            wide_table_no_javascript[viewport_name] = _no_javascript_case(
                browser,
                artifact_root=artifact_root,
                output_root=output_root,
                route_name="wide_table",
                route_path=WIDE_TABLE_ROUTE,
                viewport_name=viewport_name,
                viewport=viewport,
                expect_wide_table=True,
            )
        print_cases = {
            name: _print_case(
                browser,
                artifact_root=artifact_root,
                output_root=output_root,
                route_name=name,
                route_path=ROUTES[name],
            )
            for name in ("article", "notebook")
        }
        print_cases["wide_table"] = _print_case(
            browser,
            artifact_root=artifact_root,
            output_root=output_root,
            route_name="wide_table",
            route_path=WIDE_TABLE_ROUTE,
        )
        browser.close()

    screenshots = sorted(artifact_root.glob("*.png"))
    report = {
        "axe_core": re.search(r"axe v([0-9.]+)", axe_script.read_text(errors="ignore"))[1],
        "axe_content_ledger": AXE_CONTENT_LEDGER,
        "cases": cases,
        "chromium": browser_version,
        "contract": "nekrasovp-site006v-browser.v1",
        "no_javascript": no_javascript,
        "playwright": version("playwright"),
        "print": print_cases,
        "routes": ROUTES,
        "screenshots": [
            {
                "path": path.name,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
            for path in screenshots
        ],
        "source_head": _git("rev-parse", "HEAD"),
        "source_status": _git("status", "--porcelain=v1", "--untracked-files=all"),
        "technical_evidence_not_human_acceptance": True,
        "theme_commit": THEME_COMMIT,
        "totals": {
            "axe_scans": (len(cases) + len(wide_table)) * 2,
            "browser_cases": len(cases) + len(wide_table),
            "external_requests": 0,
            "no_javascript_cases": len(no_javascript) + len(wide_table_no_javascript),
            "print_cases": len(print_cases),
            "screenshots": len(screenshots),
        },
        "wide_table": {
            "cases": wide_table,
            "no_javascript": wide_table_no_javascript,
            "route": WIDE_TABLE_ROUTE,
        },
    }
    report_path = artifact_root / "report.json"
    report_path.write_text(
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
        print(f"SITE-006V browser validation failed: {error}")
        return 1
    print(
        "SITE-006V browser validation passed: "
        f"{report['totals']['browser_cases']} light/dark/persistence/keyboard cases, "
        f"{report['totals']['no_javascript_cases']} no-JavaScript cases, "
        f"{report['totals']['axe_scans']} axe scans, "
        f"{report['totals']['print_cases']} print cases, zero external requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
