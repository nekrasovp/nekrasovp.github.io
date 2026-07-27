from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OPS_VALIDATOR = REPO_ROOT / "migration/ops001/validate.py"
OPS_WORKFLOW = REPO_ROOT / ".github/workflows/ops001.yml"
LEGACY_WORKFLOW = REPO_ROOT / ".github/workflows/site002v.yml"


def test_ops001_has_one_authoritative_ci_entrypoint() -> None:
    assert OPS_VALIDATOR.is_file()
    assert OPS_WORKFLOW.is_file()
    assert not LEGACY_WORKFLOW.exists()


def test_required_baseline_negative_gates_run_in_the_default_suite() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["pytest"]["ini_options"]["testpaths"] == [
        "migration/site_build/tests",
        "migration/production_parity/tests",
        "migration/ops001/tests",
    ]
