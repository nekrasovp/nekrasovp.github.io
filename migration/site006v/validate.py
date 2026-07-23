"""Validate the immutable installed-theme and generated-output boundaries."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
THEME_REPOSITORY = "https://github.com/nekrasovp/pelican-engineering-theme.git"
THEME_REQUIREMENT = (
    "pelican-engineering-theme @ "
    f"git+{THEME_REPOSITORY}@{THEME_COMMIT}"
)
PUBLIC_BLOCKS = {
    "body_class",
    "body_end",
    "body_start",
    "canonical",
    "content",
    "content_footer",
    "content_header",
    "head_meta",
    "head_styles",
    "hero",
    "html_head",
    "page_class",
    "scripts",
    "site_footer",
    "site_header",
    "site_navigation",
    "structured_data",
    "title",
}
LEGACY_ASSET_TOKENS = (
    "addthis",
    "bootstrap",
    "disqus",
    "font-awesome",
    "fontawesome",
    "jquery",
    "shariff",
    "tipuesearch",
)
REQUIRED_THEME_ASSETS = {
    "theme/css/scaffold.css",
    "theme/js/theme.js",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode:
        raise RuntimeError(
            f"{label} failed with exit {result.returncode}:\n"
            f"{result.stdout}{result.stderr}"
        )


def _lock_source() -> str:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    matches = [
        package
        for package in lock["package"]
        if package["name"] == "pelican-engineering-theme"
    ]
    if len(matches) != 1:
        raise RuntimeError("uv.lock must contain exactly one pelican-engineering-theme")
    source = matches[0].get("source", {}).get("git")
    if not isinstance(source, str):
        raise RuntimeError("pelican-engineering-theme lock source is not Git")
    if f"rev={THEME_COMMIT}" not in source or not source.endswith(f"#{THEME_COMMIT}"):
        raise RuntimeError("theme lock source does not resolve the exact full commit")
    if "branch=" in source or "tag=" in source:
        raise RuntimeError("theme lock source contains a floating branch or tag")
    return source


def _template_boundary() -> dict[str, Any]:
    templates = REPO_ROOT / "templates"
    if not templates.is_dir():
        raise RuntimeError("site-owned theme override directory is missing")
    records = []
    for template in sorted(templates.glob("*.html")):
        source = template.read_text(encoding="utf-8")
        parent = re.search(r'{%\s+extends\s+"(!theme/[a-z_]+\.html)"\s+%}', source)
        if not parent:
            raise RuntimeError(f"{template.name} does not extend the !theme namespace")
        blocks = sorted(set(re.findall(r"{%\s+block\s+([a-z_]+)", source)))
        unsupported = sorted(set(blocks) - PUBLIC_BLOCKS)
        if not blocks or unsupported:
            raise RuntimeError(
                f"{template.name} has invalid public blocks: unsupported={unsupported!r}"
            )
        records.append(
            {
                "blocks": blocks,
                "path": template.relative_to(REPO_ROOT).as_posix(),
                "theme_parent": parent.group(1),
            }
        )
    if not records:
        raise RuntimeError("site-owned override boundary contains no HTML templates")
    return {
        "documented_public_blocks": sorted(PUBLIC_BLOCKS),
        "public_block_count": len(PUBLIC_BLOCKS),
        "templates": records,
    }


def verify_dependency_input() -> dict[str, Any]:
    """Reject local, copied, PyPI, tag, branch, or relative theme inputs."""

    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    if dependencies.count(THEME_REQUIREMENT) != 1:
        raise RuntimeError("pyproject.toml does not contain the one exact theme requirement")
    config = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    markdown = (REPO_ROOT / "migration/site_build/markdownconf.py").read_text(
        encoding="utf-8"
    )
    if "from pelican_engineering_theme import get_theme_path" not in config:
        raise RuntimeError("Pelican configuration does not import the public theme API")
    if "THEME = str(get_theme_path())" not in config:
        raise RuntimeError("Pelican THEME is not obtained through get_theme_path()")
    if "THEME_TEMPLATES_OVERRIDES" not in config:
        raise RuntimeError("site-owned theme override boundary is not configured")
    if 'THEME = \'theme\'' in config or 'REPO_ROOT / "theme"' in markdown:
        raise RuntimeError("the vendored theme remains configured as active")
    vendored = REPO_ROOT / "theme"
    if not (vendored / "templates/base.html").is_file():
        raise RuntimeError("rollback-only vendored theme was unexpectedly deleted")
    return {
        "direct_requirement": THEME_REQUIREMENT,
        "lock_source": _lock_source(),
        "override_boundary": _template_boundary(),
        "vendored_theme_present": True,
        "vendored_theme_configured": False,
    }


def installed_provenance(python: Path) -> dict[str, Any]:
    """Prove that the active theme is the exact installed VCS distribution."""

    probe_code = r'''
import importlib.metadata as metadata
import json
import runpy
import sys
from pathlib import Path

import pelican_engineering_theme
from pelican_engineering_theme import get_theme_path

distribution = metadata.distribution("pelican-engineering-theme")
direct_url_text = distribution.read_text("direct_url.json")
if direct_url_text is None:
    raise RuntimeError("installed distribution has no direct_url.json")
settings = runpy.run_path(sys.argv[1])
print(json.dumps({
    "active_theme": settings["THEME"],
    "direct_url": json.loads(direct_url_text),
    "distribution_root": str(distribution.locate_file("")),
    "module_file": str(Path(pelican_engineering_theme.__file__).resolve()),
    "override_paths": settings["THEME_TEMPLATES_OVERRIDES"],
    "theme_path": str(get_theme_path()),
    "version": distribution.version,
}, sort_keys=True))
'''
    probe = _run(
        [str(python), "-I", "-c", probe_code, str(REPO_ROOT / "publishconf.py")],
        cwd=REPO_ROOT,
    )
    _require_success(probe, "installed theme provenance probe")
    payload = json.loads(probe.stdout)
    direct_url = payload["direct_url"]
    vcs = direct_url.get("vcs_info", {})
    if vcs.get("vcs") != "git" or vcs.get("commit_id") != THEME_COMMIT:
        raise RuntimeError(f"installed theme commit provenance is invalid: {direct_url!r}")
    if vcs.get("requested_revision") != THEME_COMMIT:
        raise RuntimeError(f"installed theme requested revision is not exact: {direct_url!r}")
    if direct_url.get("url", "").removeprefix("git+") != THEME_REPOSITORY:
        raise RuntimeError(f"installed theme repository is invalid: {direct_url!r}")
    if direct_url.get("dir_info") or direct_url.get("archive_info"):
        raise RuntimeError(f"installed theme came from a local or archive source: {direct_url!r}")

    theme_path = Path(payload["theme_path"])
    active_theme = Path(payload["active_theme"])
    module_file = Path(payload["module_file"])
    if not theme_path.is_absolute() or not theme_path.is_dir():
        raise RuntimeError(f"get_theme_path() did not return an absolute directory: {theme_path}")
    if theme_path != active_theme:
        raise RuntimeError(f"active THEME differs from get_theme_path(): {active_theme}")
    if theme_path.is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"theme resolved inside the site checkout: {theme_path}")
    normalized_theme = theme_path.as_posix()
    normalized_module = module_file.as_posix()
    marker = "/site-packages/"
    if marker not in normalized_theme or marker not in normalized_module:
        raise RuntimeError("theme module and resources must resolve under site-packages")
    expected_overrides = [str((REPO_ROOT / "templates").resolve())]
    observed_overrides = [str(Path(path).resolve()) for path in payload["override_paths"]]
    if observed_overrides != expected_overrides:
        raise RuntimeError(
            f"unexpected THEME_TEMPLATES_OVERRIDES: {observed_overrides!r}"
        )
    return {
        "active_theme_matches_public_api": True,
        "commit_id": vcs["commit_id"],
        "direct_url": direct_url,
        "distribution_root": (
            "site-packages/" + payload["distribution_root"].split(marker, 1)[-1]
            if marker in payload["distribution_root"]
            else "site-packages"
        ),
        "get_theme_path": "site-packages/" + normalized_theme.split(marker, 1)[1],
        "import_path": "site-packages/" + normalized_module.split(marker, 1)[1],
        "outside_source_checkouts": True,
        "override_path": "site/templates",
        "requested_revision": vcs["requested_revision"],
        "version": payload["version"],
    }


def _canonical(soup: BeautifulSoup) -> str | None:
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        tokens = rel if isinstance(rel, list) else str(rel).split()
        if "canonical" in {str(token).casefold() for token in tokens}:
            href = link.get("href")
            return str(href) if href is not None else None
    return None


def _urls_for(
    soup: BeautifulSoup, selectors: tuple[tuple[str, str], ...]
) -> list[str]:
    values: list[str] = []
    for selector, attribute in selectors:
        for element in soup.select(selector):
            value = element.get(attribute)
            if value:
                values.append(str(value))
    return values


def output_evidence(output_root: Path) -> dict[str, Any]:
    """Collect deterministic routes, metadata, assets, and inactive-theme proof."""

    html_files = sorted(output_root.rglob("*.html"))
    if not html_files:
        raise RuntimeError("generated output contains no HTML")
    metadata: list[dict[str, Any]] = []
    active_urls: set[str] = set()
    content_media_urls: set[str] = set()
    external_runtime: set[str] = set()
    legacy_references: set[str] = set()
    for path in html_files:
        route = path.relative_to(output_root).as_posix()
        text = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(text, "html.parser")
        if not soup.select_one("script[data-pet-theme-loader]"):
            raise RuntimeError(f"{route} does not use the packaged theme loader")
        body = soup.find("body")
        if not body or "pet-shell" not in (body.get("class") or []):
            raise RuntimeError(f"{route} does not use the packaged theme shell")
        if len(soup.select('main#main-content[tabindex="-1"]')) != 1:
            raise RuntimeError(f"{route} lost the one focusable main target")
        html = soup.find("html")
        metadata.append(
            {
                "canonical": _canonical(soup),
                "language": html.get("lang") if html else None,
                "route": route,
                "title": soup.title.get_text(strip=True) if soup.title else None,
            }
        )
        runtime_urls = _urls_for(
            soup,
            (
                ("script[src]", "src"),
                ('link[rel~="stylesheet"][href]', "href"),
                ("iframe[src]", "src"),
            ),
        )
        media_urls = _urls_for(
            soup,
            (
                ("img[src]", "src"),
                ("source[src]", "src"),
                ("video[src]", "src"),
                ("audio[src]", "src"),
            ),
        )
        for value in runtime_urls:
            active_urls.add(value)
            lowered = value.casefold()
            if any(token in lowered for token in LEGACY_ASSET_TOKENS):
                legacy_references.add(value)
            parsed = urlparse(value if not value.startswith("//") else "https:" + value)
            if parsed.scheme in {"http", "https"} and parsed.netloc != "nekrasovp.ru":
                external_runtime.add(value)
        for value in media_urls:
            lowered = value.casefold()
            if any(token in lowered for token in LEGACY_ASSET_TOKENS):
                legacy_references.add(value)
            parsed = urlparse(value if not value.startswith("//") else "https:" + value)
            if parsed.scheme in {"http", "https"} and parsed.netloc != "nekrasovp.ru":
                content_media_urls.add(value)

    if external_runtime:
        raise RuntimeError(
            f"generated HTML has external active runtime URLs: {sorted(external_runtime)!r}"
        )
    if legacy_references:
        raise RuntimeError(
            f"generated HTML references inactive legacy assets: {sorted(legacy_references)!r}"
        )

    assets = []
    legacy_asset_files = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() in {".html", ".xml"}:
            continue
        relative = path.relative_to(output_root).as_posix()
        lowered = relative.casefold()
        if any(token in lowered for token in LEGACY_ASSET_TOKENS):
            legacy_asset_files.append(relative)
        assets.append(
            {
                "path": relative,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
        )
    if legacy_asset_files:
        raise RuntimeError(f"inactive vendored assets were copied: {legacy_asset_files!r}")
    asset_paths = {record["path"] for record in assets}
    if not REQUIRED_THEME_ASSETS <= asset_paths:
        raise RuntimeError(
            f"packaged theme assets missing: {sorted(REQUIRED_THEME_ASSETS - asset_paths)!r}"
        )

    route_payload = "\n".join(record["route"] for record in metadata).encode()
    metadata_payload = json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode()
    asset_payload = json.dumps(assets, sort_keys=True, ensure_ascii=False).encode()
    return {
        "assets": {
            "count": len(assets),
            "records": assets,
            "sha256": hashlib.sha256(asset_payload).hexdigest(),
        },
        "inactive_legacy_theme": {
            "active_references": [],
            "copied_assets": [],
            "vendored_sources_preserved": True,
        },
        "metadata": {
            "records": metadata,
            "sha256": hashlib.sha256(metadata_payload).hexdigest(),
        },
        "runtime": {
            "active_urls": sorted(active_urls),
            "external_content_media": sorted(content_media_urls),
            "external_requests": [],
        },
        "routes": {
            "count": len(metadata),
            "paths": [record["route"] for record in metadata],
            "sha256": hashlib.sha256(route_payload).hexdigest(),
        },
        "theme_assets": sorted(REQUIRED_THEME_ASSETS),
    }
