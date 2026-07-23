import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "migration/site005/materials.json"
VALIDATOR = REPO_ROOT / "migration/site005/validate.py"
spec = importlib.util.spec_from_file_location("site005_validate", VALIDATOR)
assert spec and spec.loader
site005 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = site005
spec.loader.exec_module(site005)

UndeclaredSite005Source = site005.UndeclaredSite005Source
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
