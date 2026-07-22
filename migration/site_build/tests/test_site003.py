from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = REPO_ROOT / "migration/site003/validate.py"
spec = importlib.util.spec_from_file_location("site003_validate", VALIDATOR)
assert spec and spec.loader
site003 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = site003
spec.loader.exec_module(site003)

EXPECTED_LANGUAGE_COUNTS = site003.EXPECTED_LANGUAGE_COUNTS
EXPECTED_STATUS_COUNTS = site003.EXPECTED_STATUS_COUNTS
InvalidLanguage = site003.InvalidLanguage
ManifestRow = site003.ManifestRow
UnknownStatus = site003.UnknownStatus
_require_metadata = site003._require_metadata
validate_inventory = site003.validate_inventory


def test_authoritative_inventory_matches_all_46_sources() -> None:
    evidence = validate_inventory()

    assert evidence["counts"] == {
        "articles": 46,
        "languages": EXPECTED_LANGUAGE_COUNTS,
        "markdown": 35,
        "notebooks": 11,
        "statuses": EXPECTED_STATUS_COUNTS,
    }
    assert evidence["source_preservation"]["markdown_bodies_preserved"] == 35
    assert evidence["source_preservation"]["notebook_bytes_preserved"] == 11
    assert evidence["source_preservation"]["dates_preserved"] == 46
    assert evidence["source_preservation"]["routes_preserved"] == 46


def _row() -> ManifestRow:
    return ManifestRow(
        route="/example.html",
        published_at="2020-01-01",
        language="en",
        status="keep",
        source="example.md",
        title="Example",
    )


def _metadata() -> dict[str, str]:
    return {
        "date": "2020-01-01 15:00",
        "lang": "en",
        "slug": "example",
        "status": "keep",
        "title": "Example",
    }


def test_unknown_status_is_typed_and_source_aware() -> None:
    metadata = _metadata()
    metadata["status"] = "unknown"

    with pytest.raises(UnknownStatus, match=r"source='example\.md'.*unknown_status"):
        _require_metadata(_row(), metadata)


def test_invalid_language_is_typed_and_source_aware() -> None:
    metadata = _metadata()
    metadata["lang"] = "xx"

    with pytest.raises(InvalidLanguage, match=r"source='example\.md'.*invalid_language"):
        _require_metadata(_row(), metadata)


def test_validator_is_the_pre_pelican_entrypoint() -> None:
    site_script = (REPO_ROOT / "migration/site_build/site.py").read_text(encoding="utf-8")

    assert "run_site003_preflight()" in site_script
    assert "if preflight:" in site_script
    assert site_script.index("if preflight:") < site_script.index("pelican_command(", 3000)
