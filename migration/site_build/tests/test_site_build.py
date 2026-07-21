from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPOSITORY_ROOT / "migration" / "site_build" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build  # noqa: E402
import compare_route_sets  # noqa: E402


def test_output_path_rejects_checkout_root() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        build.output_path(str(REPOSITORY_ROOT))


def test_output_path_rejects_non_temporary_absolute_path() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        build.output_path(str(REPOSITORY_ROOT.parent / "unsafe-output"))


def test_output_path_accepts_explicit_temporary_child(tmp_path: Path) -> None:
    assert build.output_path(str(tmp_path / "output")) == (tmp_path / "output").resolve()


def test_route_comparison_uses_html_and_xml_only(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        root.mkdir()
        (root / "index.html").write_text("different body", encoding="utf-8")
        (root / "feed.xml").write_text("different feed", encoding="utf-8")
        (root / "asset.css").write_text("ignored", encoding="utf-8")
    assert compare_route_sets.routes(first) == {"index.html", "feed.xml"}
    assert compare_route_sets.routes(first) == compare_route_sets.routes(second)


def test_real_template_failure_is_propagated() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_template_failure.py")],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "template failure propagated" in completed.stdout
