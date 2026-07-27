from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from migration.cut001.browser_validate import (  # noqa: E402
    VISUAL_CASES,
    VISUAL_EQUIVALENCES,
    BrowserValidationError,
    _assert_exact_observations,
    _assert_network,
    visual_matrix_contract,
)


def test_visual_matrix_contract_covers_the_authoritative_page_types() -> None:
    contract = visual_matrix_contract()

    assert contract["themes"] == ["dark", "light"]
    assert contract["viewports"] == ["desktop", "mobile"]
    assert contract["page_types"] == {
        "404": {"en", "ru-equivalent"},
        "archive_deprecated": {"en", "ru-equivalent"},
        "home": {"en", "ru"},
        "legacy_markdown": {"en", "ru"},
        "modern_essay": {"en"},
        "notebook": {"en", "ru"},
        "work_about_writing": {"en"},
    }
    assert len({case["route"] for case in VISUAL_CASES.values()}) == len(VISUAL_CASES)
    assert {
        item["virtual_case"] for item in VISUAL_EQUIVALENCES
    } == {"404_ru_acceptable", "archive_deprecated_ru"}
    assert all(
        item["canonical_case"] in VISUAL_CASES for item in VISUAL_EQUIVALENCES
    )


def test_exact_unchanged_missing_asset_is_browser_evidence() -> None:
    _assert_network(
        {
            "blocked_external": [],
            "fulfilled_same_origin": [],
            "missing_same_origin": [
                {
                    "resource_type": "image",
                    "url": "https://nekrasovp.ru/Figure%201.1",
                }
            ],
        },
        allowed_external_urls=set(),
        allowed_missing_same_origin_urls={
            "https://nekrasovp.ru/Figure%201.1",
        },
        label="test",
    )


def test_unreviewed_missing_same_origin_asset_is_red() -> None:
    with pytest.raises(
        BrowserValidationError,
        match="requested missing same-origin files",
    ):
        _assert_network(
            {
                "blocked_external": [],
                "fulfilled_same_origin": [],
                "missing_same_origin": [
                    {
                        "resource_type": "image",
                        "url": "https://nekrasovp.ru/unreviewed.png",
                    }
                ],
            },
            allowed_external_urls=set(),
            allowed_missing_same_origin_urls={
                "https://nekrasovp.ru/Figure%201.1",
            },
            label="test",
        )


def test_stale_unchanged_missing_asset_allowlist_is_red() -> None:
    with pytest.raises(BrowserValidationError, match="observation drift"):
        _assert_exact_observations(
            expected={"https://nekrasovp.ru/Figure%201.1"},
            observed=set(),
            label="test",
        )
