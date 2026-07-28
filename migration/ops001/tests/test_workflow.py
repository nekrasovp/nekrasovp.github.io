from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/ops001.yml"
SHA_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def _load_workflow() -> dict[str, Any]:
    ruby = shutil.which("ruby")
    if ruby is None:
        pytest.fail("Ruby/Psych is required for dependency-free YAML semantic checks")
    script = (
        "require 'json'; require 'yaml'; "
        "puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), aliases: true))"
    )
    result = subprocess.run(
        [ruby, "-e", script, str(WORKFLOW)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(result.stdout)
    assert isinstance(value, dict)
    return value


def _steps_by_name(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {step["name"]: step for step in job["steps"]}


def test_event_permissions_and_concurrency_are_fail_closed() -> None:
    workflow = _load_workflow()

    assert workflow["on"] == {
        "pull_request": None,
        "push": {"branches": ["master"]},
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "ops001-pages-${{ github.ref }}",
        "cancel-in-progress": True,
    }
    assert "workflow_dispatch" not in workflow["on"]


def test_validate_job_has_one_locked_build_and_gate_path() -> None:
    workflow = _load_workflow()
    validate = workflow["jobs"]["validate"]
    steps = _steps_by_name(validate)
    joined_runs = "\n".join(step.get("run", "") for step in validate["steps"])

    assert validate["outputs"] == {
        "validated_commit": "${{ steps.contract.outputs.validated_commit }}",
        "validated_artifact": "${{ steps.contract.outputs.validated_artifact }}",
        "artifact_sha256": "${{ steps.contract.outputs.artifact_sha256 }}",
    }
    assert "./scripts/site validate" in joined_runs
    assert "./scripts/site build --output \"$RUNNER_TEMP/ops001-site\"" in joined_runs
    assert "migration/ops001/validate.py" in joined_runs
    assert "migration/cut001/validate.py" in joined_runs
    assert "migration/cut001/browser_validate.py" in joined_runs
    assert "5c24ba21ec8b442e4b5280a47c85fab61165f8ce" in joined_runs
    assert "027a170ac6c8288347de5353569a089c526afae2" in joined_runs
    assert "./scripts/site test" in joined_runs
    assert "uv sync --locked --all-groups" in joined_runs
    assert "pelican-engineering-theme" in joined_runs
    assert "pelican-ipynb-reader" in joined_runs
    assert "pelican-jupyter" not in joined_runs
    assert steps["Check out the exact site head"]["with"]["fetch-depth"] == 0
    assert steps["Check out the exact site head"]["with"]["persist-credentials"] is False
    evidence_upload = steps["Upload the CUT-001 evidence package"]["with"]
    assert evidence_upload == {
        "name": "cut001-evidence-${{ env.EXPECTED_HEAD }}",
        "path": "${{ runner.temp }}/cut001-evidence",
        "if-no-files-found": "error",
        "include-hidden-files": True,
        "retention-days": 14,
    }


def test_exact_artifact_handoff_and_official_actions_are_sha_pinned() -> None:
    workflow = _load_workflow()
    validate = workflow["jobs"]["validate"]
    deploy = workflow["jobs"]["deploy"]
    validate_steps = _steps_by_name(validate)
    deploy_steps = _steps_by_name(deploy)

    action_uses = [
        step["uses"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]
    assert all(SHA_PIN.fullmatch(value) for value in action_uses)
    assert validate_steps["Upload the exact validated Pages artifact"]["uses"].startswith(
        "actions/upload-pages-artifact@"
    )
    assert validate_steps["Upload the exact validated Pages artifact"]["with"] == {
        "name": "github-pages",
        "path": "${{ runner.temp }}/ops001-site",
        "retention-days": 1,
    }
    assert deploy_steps["Deploy the exact validated Pages artifact"]["uses"].startswith(
        "actions/deploy-pages@"
    )
    assert len(deploy["steps"]) == 1


def test_deploy_is_impossible_without_cut002_and_exact_master_artifact() -> None:
    workflow = _load_workflow()
    deploy = workflow["jobs"]["deploy"]
    condition = deploy["if"]

    assert "github.event_name == 'push'" in condition
    assert "github.ref == 'refs/heads/master'" in condition
    assert "vars.CUT_002_PAGES_DEPLOY_ENABLED == 'true'" in condition
    assert "needs.validate.outputs.validated_commit == github.sha" in condition
    assert "needs.validate.outputs.validated_artifact == 'github-pages'" in condition
    assert deploy["needs"] == ["validate"]
    assert deploy["permissions"] == {
        "pages": "write",
        "id-token": "write",
    }
    assert deploy["outputs"] == {
        "page_url": "${{ steps.deployment.outputs.page_url }}",
        "commit_sha": "${{ needs.validate.outputs.validated_commit }}",
    }
    assert "environment" not in deploy
