from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from migration.cut001.validate import (  # noqa: E402
    ACCEPTED_PREVIEW_COMMIT,
    Cut001ValidationError,
    compare_feeds,
    compare_routes,
    validate_structured_data,
    validate_theme_toggle_markup,
)

ATOM = "{http://www.w3.org/2005/Atom}"


def test_site002_is_stacked_on_the_exact_accepted_preview() -> None:
    assert ACCEPTED_PREVIEW_COMMIT == "95c3f02ad6fc3589798ba73dc19e39045941235e"


def _page(*, toggle: bool = True, jsonld: object | None = None) -> str:
    toggle_markup = (
        '<button data-pet-theme-toggle aria-pressed="false">Theme</button>'
        if toggle
        else ""
    )
    structured = (
        f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'
        if jsonld is not None
        else ""
    )
    return (
        "<!doctype html><html lang=\"en\"><head>"
        f"{structured}</head><body><main id=\"main-content\">Readable</main>"
        f"{toggle_markup}<script src=\"/theme/js/theme.js\"></script></body></html>"
    )


def _feed(path: Path, identifiers: list[str]) -> None:
    ET.register_namespace("", "http://www.w3.org/2005/Atom")
    root = ET.Element(f"{ATOM}feed")
    ET.SubElement(root, f"{ATOM}id").text = "https://nekrasovp.ru/feeds/all.atom.xml"
    for identifier in identifiers:
        entry = ET.SubElement(root, f"{ATOM}entry")
        ET.SubElement(entry, f"{ATOM}id").text = identifier
        ET.SubElement(
            entry,
            f"{ATOM}link",
            {"href": f"https://nekrasovp.ru/{identifier.rsplit(':', 1)[-1]}.html"},
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def test_unexplained_added_route_is_red(tmp_path: Path) -> None:
    production = tmp_path / "production"
    preview = tmp_path / "preview"
    production.mkdir()
    preview.mkdir()
    (production / "index.html").write_text(_page(), encoding="utf-8")
    (preview / "index.html").write_text(_page(), encoding="utf-8")
    (preview / "unexpected.html").write_text(_page(), encoding="utf-8")

    with pytest.raises(Cut001ValidationError, match="unexplained added routes"):
        compare_routes(preview, production, intentional_added={})


def test_changed_historical_feed_id_is_red(tmp_path: Path) -> None:
    production = tmp_path / "production"
    preview = tmp_path / "preview"
    _feed(production / "feeds/all.atom.xml", ["tag:nekrasovp.ru,2020:/historical"])
    _feed(preview / "feeds/all.atom.xml", ["tag:nekrasovp.ru,2020:/changed"])

    with pytest.raises(Cut001ValidationError, match="historical feed IDs"):
        compare_feeds(preview, production)


def test_invalid_structured_data_is_red(tmp_path: Path) -> None:
    output = tmp_path / "site"
    output.mkdir()
    (output / "index.html").write_text(
        '<html><script type="application/ld+json">{"broken":</script></html>',
        encoding="utf-8",
    )

    with pytest.raises(Cut001ValidationError, match="invalid JSON-LD"):
        validate_structured_data(output)


def test_missing_theme_toggle_on_generated_page_is_red(tmp_path: Path) -> None:
    output = tmp_path / "site"
    output.mkdir()
    (output / "index.html").write_text(_page(toggle=False), encoding="utf-8")

    with pytest.raises(Cut001ValidationError, match="theme toggle contract"):
        validate_theme_toggle_markup(output)


def test_exact_standalone_redirects_are_toggle_exempt(tmp_path: Path) -> None:
    output = tmp_path / "site"
    (output / "pages").mkdir(parents=True)
    (output / "index.html").write_text(_page(), encoding="utf-8")
    for relative in ("pages/about.html", "pages/services.html"):
        (output / relative).write_text(
            "<!doctype html><html lang=\"en\"><head>"
            '<meta http-equiv="refresh" content="0; url=/">'
            "</head><body></body></html>",
            encoding="utf-8",
        )

    evidence = validate_theme_toggle_markup(output)

    assert evidence["checked"] == 1
    assert evidence["exempt"] == ["pages/about.html", "pages/services.html"]
