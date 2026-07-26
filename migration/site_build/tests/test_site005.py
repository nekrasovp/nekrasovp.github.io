import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "migration/site005/materials.json"
VALIDATOR = REPO_ROOT / "migration/site005/validate.py"
spec = importlib.util.spec_from_file_location("site005_validate", VALIDATOR)
assert spec and spec.loader
site005 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = site005
spec.loader.exec_module(site005)

UndeclaredSite005Source = site005.UndeclaredSite005Source
Site005RenderedMismatch = site005.Site005RenderedMismatch
validate_collection_absence = site005._validate_collection_absence
validate_feed_membership = site005._validate_feed_membership
load_manifest = site005.load_manifest
validate_inventory = site005.validate_inventory


def test_manifest_declares_exactly_six_frozen_materials() -> None:
    manifest = load_manifest(MANIFEST)
    assert len(manifest.materials) == 6
    assert {item.role for item in manifest.materials} == {"essay", "companion"}
    assert sum(item.role == "essay" for item in manifest.materials) == 3
    assert manifest.site_base_commit == "3acbb7168f55b100cfd8debab2b096baa6ff4919"
    assert manifest.production_commit == "5c24ba21ec8b442e4b5280a47c85fab61165f8ce"
    assert {item.route for item in manifest.materials} == {
        "/ai-native-delivery-contract.html",
        "/ai-native-sdlc-engineering-accountability.html",
        "/logistics-distributed-systems-case-study.html",
        "/logistics-lessons-for-distributed-systems.html",
        "/technical-debt-as-a-portfolio.html",
        "/technical-debt-portfolio-register.html",
    }


def test_inventory_accepts_only_the_declared_composite_sources() -> None:
    evidence = validate_inventory()
    assert evidence["counts"] == {
        "legacy_markdown": 35,
        "legacy_notebooks": 11,
        "site005_hidden_markdown": 6,
    }


def test_undeclared_seventh_source_is_a_hard_error(tmp_path: Path) -> None:
    content_root = tmp_path / "content"
    content_root.mkdir()
    for source in (REPO_ROOT / "content").glob("*"):
        if source.is_file():
            (content_root / source.name).write_bytes(source.read_bytes())
    (content_root / "undeclared-seventh.md").write_text(
        "Title: Undeclared\nStatus: hidden\n\nbody\n",
        encoding="utf-8",
    )
    try:
        validate_inventory(content_root=content_root)
    except UndeclaredSite005Source as error:
        assert "undeclared-seventh.md" in str(error)
    else:
        raise AssertionError("undeclared SITE-005 source did not hard-fail")


def test_manifest_json_is_canonical() -> None:
    parsed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert MANIFEST.read_text(encoding="utf-8") == json.dumps(
        parsed, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"


def test_site004_home_editorial_link_does_not_weaken_collection_guard(
    tmp_path: Path,
) -> None:
    manifest = load_manifest(MANIFEST)
    hidden_route = manifest.materials[0].route
    (tmp_path / "index.html").write_text(
        (
            '<html><body class="site004-home">'
            f'<main><a href="{hidden_route}">Selected essay</a></main>'
            '<ol class="pet-entry-list"><li><a href="/legacy.html">Legacy</a></li></ol>'
            "</body></html>"
        ),
        encoding="utf-8",
    )

    assert validate_collection_absence(tmp_path, manifest) == ["index.html"]

    (tmp_path / "index.html").write_text(
        (
            '<html><body class="site004-home">'
            '<main><a href="/legacy.html">Selected essay</a></main>'
            f'<ol class="pet-entry-list"><li><a href="{hidden_route}">Leak</a></li></ol>'
            "</body></html>"
        ),
        encoding="utf-8",
    )
    with pytest.raises(Site005RenderedMismatch, match="hidden route leaked"):
        validate_collection_absence(tmp_path, manifest)


def test_non_home_collection_still_rejects_hidden_route(tmp_path: Path) -> None:
    manifest = load_manifest(MANIFEST)
    hidden_route = manifest.materials[0].route
    (tmp_path / "archives.html").write_text(
        f'<html><body><a href="{hidden_route}">Leak</a></body></html>',
        encoding="utf-8",
    )

    with pytest.raises(Site005RenderedMismatch, match="hidden route leaked"):
        validate_collection_absence(tmp_path, manifest)


def test_feed_membership_still_rejects_companions_and_wrong_essay_delta() -> None:
    manifest = load_manifest(MANIFEST)
    expected = [
        {"id": item.feed["id"], "link": item.canonical_url}
        for item in manifest.materials
        if item.feed is not None
    ]
    assert len(expected) == 3
    assert validate_feed_membership(expected, expected, manifest) == {
        item["id"] for item in expected
    }

    companion = next(item for item in manifest.materials if item.role == "companion")
    leaked = [*expected, {"id": "companion", "link": companion.canonical_url}]
    with pytest.raises(Site005RenderedMismatch, match="companion entered the feed"):
        validate_feed_membership(leaked, expected, manifest)

    with pytest.raises(
        Site005RenderedMismatch, match="essay feed delta is not exactly three"
    ):
        validate_feed_membership(expected[:2], expected, manifest)
