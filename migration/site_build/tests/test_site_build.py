from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SITE_SCRIPT = REPO_ROOT / "migration/site_build/site.py"
EXPECTED_NOTEBOOKS = 11


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


def test_production_keeps_every_notebook_and_legacy_reader() -> None:
    notebooks = list((REPO_ROOT / "content").glob("*.ipynb"))
    metadata = list((REPO_ROOT / "content").glob("*.nbdata"))
    assert len(notebooks) == EXPECTED_NOTEBOOKS
    assert len(metadata) == EXPECTED_NOTEBOOKS

    config = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    assert "'ipynb.markup'" in config
    assert "MARKUP = ('md', 'ipynb')" in config


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


def test_full_build_fails_on_legacy_notebook_reader(tmp_path: Path) -> None:
    result = run_site("build", "--output", str(tmp_path / "production"))
    assert result.returncode != 0
    assert "TemplateNotFound" in result.stdout
    assert "basic" in result.stdout
