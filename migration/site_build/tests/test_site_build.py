from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SITE_SCRIPT = REPO_ROOT / "migration/site_build/site.py"
SITE002V_VALIDATOR = REPO_ROOT / "migration/site002v/validate.py"
OPS001_WORKFLOW = REPO_ROOT / ".github/workflows/ops001.yml"
EXPECTED_NOTEBOOKS = 11
READER_DISTRIBUTION = "pelican-ipynb-reader"
READER_VERSION = "0.1.0"
READER_WHEEL_SHA256 = "ec5212c0f5c414743032c3b2880904af898e726e5cb5ab314345634c8bb68153"
READER_SDIST_SHA256 = "c456eb564973d7241eb5ea01aed19662f20fc18c7bef0380d81a5d1b8fc87fa4"
SITE_BASE_COMMIT = "cac7d59b7a691ebdedea17f5978ce24693830bf8"


def load_site_module():
    spec = importlib.util.spec_from_file_location("site_build_entrypoint", SITE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_site(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SITE_SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def html_routes(output: Path) -> set[str]:
    return {path.relative_to(output).as_posix() for path in output.rglob("*.html")}


def test_runtime_is_python_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_default_outputs_are_explicit_and_repo_relative() -> None:
    site = load_site_module()
    for mode, relative_output in site.DEFAULT_OUTPUTS.items():
        command = site.pelican_command(mode)
        output = Path(command[command.index("--output") + 1])
        assert output == REPO_ROOT / relative_output
        assert output != Path("/output")


def test_production_keeps_every_notebook_and_uses_immutable_reader() -> None:
    notebooks = list((REPO_ROOT / "content").glob("*.ipynb"))
    metadata = list((REPO_ROOT / "content").glob("*.nbdata"))
    assert len(notebooks) == EXPECTED_NOTEBOOKS
    assert len(metadata) == EXPECTED_NOTEBOOKS

    config = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    assert "pelican.plugins.ipynb_reader" in config
    assert "ipynb.markup" not in config
    assert "MARKUP = ('md', 'ipynb')" in config
    assert not (REPO_ROOT / "plugins/ipynb").exists()


def test_notebook_manifest_has_exact_source_metadata_route_pairs() -> None:
    manifest = REPO_ROOT / "migration/site002v/notebooks.tsv"
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert len(rows) == EXPECTED_NOTEBOOKS
    assert len({(row["source"], row["metadata"], row["route"]) for row in rows}) == len(rows)
    for row in rows:
        source = Path(row["source"])
        assert row["metadata"] == source.with_suffix(".nbdata").as_posix()
        assert (REPO_ROOT / "content" / source).is_file()
        assert (REPO_ROOT / "content" / row["metadata"]).is_file()
        assert row["route"].startswith("/") and row["route"].endswith(".html")


def test_lock_resolves_exact_public_reader_release() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected = f"{READER_DISTRIBUTION}=={READER_VERSION}"
    assert project["project"]["dependencies"].count(expected) == 1

    lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    lock = tomllib.loads(lock_text)
    packages = [
        package for package in lock["package"] if package["name"] == READER_DISTRIBUTION
    ]
    assert len(packages) == 1
    package = packages[0]
    assert package["version"] == READER_VERSION
    assert package["source"] == {"registry": "https://pypi.org/simple"}
    assert package["sdist"]["hash"] == f"sha256:{READER_SDIST_SHA256}"
    assert [wheel["hash"] for wheel in package["wheels"]] == [
        f"sha256:{READER_WHEEL_SHA256}"
    ]
    assert "pelican-jupyter" not in lock_text
    assert "git+https://github.com/nekrasovp/pelican-jupyter" not in lock_text


def test_ci_keeps_history_required_by_permanent_site_base_gate() -> None:
    workflow = OPS001_WORKFLOW.read_text(encoding="utf-8")
    checkout = re.search(
        r"uses: actions/checkout@[0-9a-f]{40}\n(?P<with>(?:\s{8,}.+\n)+)",
        workflow,
    )
    assert checkout
    checkout_config = checkout.group("with")
    assert "ref: ${{ env.EXPECTED_HEAD }}" in checkout_config
    assert re.search(r"^\s+fetch-depth: 0$", checkout_config, flags=re.MULTILINE)

    validator = SITE002V_VALIDATOR.read_text(encoding="utf-8")
    assert f'SITE_BASE_COMMIT = "{SITE_BASE_COMMIT}"' in validator
    assert '_git("cat-file", "-e", f"{SITE_BASE_COMMIT}^{{commit}}")' in validator
    assert '_git("merge-base", "--is-ancestor", SITE_BASE_COMMIT, "HEAD")' in validator


def test_two_clean_markdown_builds_have_the_same_routes(tmp_path: Path) -> None:
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first = run_site("markdown", "--output", str(first_output))
    second = run_site("markdown", "--output", str(second_output))

    assert first.returncode == 0, first.stdout
    assert second.returncode == 0, second.stdout
    first_routes = html_routes(first_output)
    assert first_routes
    assert first_routes == html_routes(second_output)


def test_markdown_warning_is_fatal(tmp_path: Path) -> None:
    result = run_site(
        "markdown",
        "--config",
        "migration/site_build/tests/fixtures/warningconf.py",
        "--output",
        str(tmp_path / "warning"),
    )
    assert result.returncode != 0
    assert "SITE-001 deterministic warning fixture" in result.stdout


def test_template_failure_is_nonzero(tmp_path: Path) -> None:
    result = run_site(
        "markdown",
        "--config",
        "migration/site_build/tests/fixtures/broken_templateconf.py",
        "--output",
        str(tmp_path / "broken-template"),
    )
    assert result.returncode != 0
    assert "Could not find the theme" in result.stdout


def test_legacy_reader_archive_is_removed_after_released_artifact_parity() -> None:
    archive = REPO_ROOT / "migration/site002v/archive/legacy-ipynb-reader"
    assert not archive.exists()
    active_plugins = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    markdown_plugins = (REPO_ROOT / "migration/site_build/markdownconf.py").read_text(
        encoding="utf-8"
    )
    assert "legacy-ipynb-reader" not in active_plugins
    assert "legacy-ipynb-reader" not in markdown_plugins


def test_site002_evidence_binds_the_stacked_release_and_equivalence() -> None:
    path = REPO_ROOT / "migration/site002/evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path.read_text(encoding="utf-8") == json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    assert payload["branch_strategy"]["base_head"] == (
        "95c3f02ad6fc3589798ba73dc19e39045941235e"
    )
    assert payload["release"]["version"] == READER_VERSION
    assert payload["release"]["wheel"]["sha256"] == READER_WHEEL_SHA256
    assert payload["release"]["sdist"]["sha256"] == READER_SDIST_SHA256
    assert payload["artifact_comparison"]["classification"] == "rendered_equivalent"
    assert payload["artifact_comparison"]["unexplained_differences"] == []
