from __future__ import annotations

import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PARITY_ROOT = REPO_ROOT / "migration/production_parity"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PARITY_ROOT / "scripts"))

from baseline_common import ATOM_NS, load_json  # noqa: E402

from migration.ops001.finalize import finalize  # noqa: E402
from migration.ops001.validate import validate_artifact  # noqa: E402
from migration.production_parity.tests.test_baseline_checker import (  # noqa: E402
    build_fixture,
)


@pytest.fixture
def baseline_artifact(tmp_path: Path) -> tuple[Path, Path]:
    baseline = PARITY_ROOT / "baseline"
    output = tmp_path / "site"
    output.mkdir()
    build_fixture(output, baseline)
    return output, baseline


@pytest.fixture(scope="module")
def real_artifact(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("ops001-real") / "site"
    subprocess.run(
        [str(REPO_ROOT / "scripts/site"), "build", "--output", str(output)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return output


def _copy_real_artifact(real_artifact: Path, tmp_path: Path) -> Path:
    output = tmp_path / "site"
    shutil.copytree(real_artifact, output)
    return output


def _replace_canonical(path: Path, replacement: str) -> None:
    payload = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(<link\s+rel="canonical"\s+href=")[^"]+',
        rf"\g<1>{replacement}",
        payload,
        count=1,
    )
    assert count == 1
    path.write_text(updated, encoding="utf-8")


def test_positive_composed_gate(baseline_artifact: tuple[Path, Path]) -> None:
    output, baseline = baseline_artifact

    errors, evidence = validate_artifact(output, baseline_root=baseline)

    assert errors == []
    assert evidence["base_parity_errors"] == 0
    assert evidence["global_errors"] == 0
    assert evidence["html_files"] > 0
    assert evidence["xml_files"] == 3
    assert len(evidence["artifact_sha256"]) == 64


def test_notebook_removal_reuses_exact_base_reason(
    baseline_artifact: tuple[Path, Path],
) -> None:
    output, baseline = baseline_artifact
    routes = load_json(baseline / "routes.json")["routes"]
    route = next(item for item in routes if item.get("notebook_article"))
    (output / route["output_path"]).unlink()

    errors, _ = validate_artifact(output, baseline_root=baseline)

    assert f"missing notebook article: {route['path']} ({route['output_path']})" in errors


def test_canonical_break_reuses_exact_base_reason(
    baseline_artifact: tuple[Path, Path],
) -> None:
    output, baseline = baseline_artifact
    pages = load_json(baseline / "metadata.json")["pages"]
    page = next(item for item in pages if item.get("canonical"))
    routes = load_json(baseline / "routes.json")["routes"]
    route = next(
        item
        for item in routes
        if item["path"] == page["path"] and item.get("output_path")
    )
    target = output / route["output_path"]
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            page["canonical"],
            "https://wrong.example.invalid/",
            1,
        ),
        encoding="utf-8",
    )

    errors, _ = validate_artifact(output, baseline_root=baseline)

    assert any(
        error.startswith(f"metadata mismatch for {page['path']}: canonical ")
        for error in errors
    )


def test_feed_entry_removal_reuses_exact_base_reason(
    baseline_artifact: tuple[Path, Path],
) -> None:
    output, baseline = baseline_artifact
    feed = load_json(baseline / "feeds.json")["feeds"][0]
    path = output / feed["path"].lstrip("/")
    root = ET.parse(path).getroot()
    entry = root.find(f"{ATOM_NS}entry")
    assert entry is not None
    identifier = entry.findtext(f"{ATOM_NS}id")
    root.remove(entry)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

    errors, _ = validate_artifact(output, baseline_root=baseline)

    assert any(
        error.startswith(f"missing feed entry in {feed['path']}:")
        and identifier in error
        for error in errors
    )


def test_missing_internal_asset_is_global_red(
    baseline_artifact: tuple[Path, Path],
) -> None:
    output, baseline = baseline_artifact
    target = output / "index.html"
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "</head>",
            '<link rel="stylesheet" href="/missing.css"></head>',
        ),
        encoding="utf-8",
    )

    errors, _ = validate_artifact(output, baseline_root=baseline)

    assert "missing internal link target in index.html: /missing.css -> missing.css" in errors


def test_finalize_writes_exact_sitemap_robots_and_misc_feed(
    baseline_artifact: tuple[Path, Path],
) -> None:
    output, _ = baseline_artifact

    evidence = finalize(output)

    assert evidence == {
        "historical_feed_ids_normalized": 0,
        "misc_feed_entries": 3,
        "sitemap_urls": 58,
    }
    assert (
        output / "robots.txt"
    ).read_text(encoding="utf-8") == (
        "User-agent: *\nAllow: /\n\n"
        "Sitemap: https://nekrasovp.ru/sitemap.xml\n"
    )
    feed = ET.parse(output / "feeds/misc.atom.xml").getroot()
    assert len(feed.findall(f"{ATOM_NS}entry")) == 3


def test_real_artifact_passes_accepted_migration_contracts(
    real_artifact: Path,
) -> None:
    errors, evidence = validate_artifact(
        real_artifact,
        accepted_migration_contracts=True,
    )

    assert errors == []
    assert evidence["base_parity_errors"] == 0
    assert evidence["global_errors"] == 0
    assert evidence["reviewed_base_differences"] == 269


def test_accepted_mode_notebook_removal_stays_exact_red(
    real_artifact: Path,
    tmp_path: Path,
) -> None:
    output = _copy_real_artifact(real_artifact, tmp_path)
    routes = load_json(PARITY_ROOT / "baseline/routes.json")["routes"]
    route = next(item for item in routes if item.get("notebook_article"))
    (output / route["output_path"]).unlink()

    errors, _ = validate_artifact(output, accepted_migration_contracts=True)

    assert f"missing notebook article: {route['path']} ({route['output_path']})" in errors


def test_accepted_mode_canonical_break_stays_exact_red(
    real_artifact: Path,
    tmp_path: Path,
) -> None:
    output = _copy_real_artifact(real_artifact, tmp_path)
    routes = load_json(PARITY_ROOT / "baseline/routes.json")["routes"]
    route = next(item for item in routes if item.get("notebook_article"))
    target = output / route["output_path"]
    _replace_canonical(target, "https://wrong.example.invalid/")

    errors, _ = validate_artifact(output, accepted_migration_contracts=True)

    assert any(
        error.startswith(f"metadata mismatch for {route['path']}: canonical ")
        and "wrong.example.invalid" in error
        for error in errors
    )


def test_accepted_mode_feed_removal_stays_exact_red(
    real_artifact: Path,
    tmp_path: Path,
) -> None:
    output = _copy_real_artifact(real_artifact, tmp_path)
    materials = load_json(REPO_ROOT / "migration/site005/materials.json")["materials"]
    identifier = next(record["feed"]["id"] for record in materials if record.get("feed"))
    path = output / "feeds/all.atom.xml"
    root = ET.parse(path).getroot()
    entry = next(
        item
        for item in root.findall(f"{ATOM_NS}entry")
        if item.findtext(f"{ATOM_NS}id") == identifier
    )
    root.remove(entry)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

    errors, _ = validate_artifact(output, accepted_migration_contracts=True)

    assert any(
        error.startswith("missing feed entry in /feeds/all.atom.xml:")
        and identifier in error
        for error in errors
    )


def test_unreviewed_neighbor_canonical_diff_breaks_allowlist_fingerprint(
    real_artifact: Path,
    tmp_path: Path,
) -> None:
    output = _copy_real_artifact(real_artifact, tmp_path)
    target = output / "archives.html"
    _replace_canonical(target, "https://nekrasovp.ru/unreviewed-neighbor.html")

    errors, _ = validate_artifact(output, accepted_migration_contracts=True)

    assert any(
        error.startswith("metadata mismatch for /archives.html: canonical ")
        and "unreviewed-neighbor" in error
        for error in errors
    )
    assert any(
        "accepted migration contract failed: SITE-006V metadata fingerprint changed"
        in error
        for error in errors
    )
