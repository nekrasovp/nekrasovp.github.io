from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
THEME_COMMIT = "027a170ac6c8288347de5353569a089c526afae2"
THEME_REPOSITORY = "https://github.com/nekrasovp/pelican-engineering-theme.git"
THEME_REQUIREMENT = (
    "pelican-engineering-theme @ "
    f"git+{THEME_REPOSITORY}@{THEME_COMMIT}"
)
PUBLIC_BLOCKS = {
    "body_class",
    "body_end",
    "body_start",
    "canonical",
    "content",
    "content_footer",
    "content_header",
    "head_meta",
    "head_styles",
    "hero",
    "html_head",
    "page_class",
    "scripts",
    "site_footer",
    "site_header",
    "site_navigation",
    "structured_data",
    "title",
}


def test_theme_dependency_is_an_exact_vcs_pin() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"].count(THEME_REQUIREMENT) == 1

    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = [
        package
        for package in lock["package"]
        if package["name"] == "pelican-engineering-theme"
    ]
    assert len(packages) == 1
    source = packages[0]["source"]["git"]
    assert f"rev={THEME_COMMIT}" in source
    assert source.endswith(f"#{THEME_COMMIT}")


def test_settings_use_only_the_installed_theme_public_api() -> None:
    production = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    markdown = (REPO_ROOT / "migration/site_build/markdownconf.py").read_text(
        encoding="utf-8"
    )

    assert "from pelican_engineering_theme import get_theme_path" in production
    assert "THEME = str(get_theme_path())" in production
    assert "THEME_TEMPLATES_OVERRIDES" in production
    assert 'THEME = \'theme\'' not in production
    assert 'REPO_ROOT / "theme"' not in markdown


def test_site_owned_templates_extend_only_the_18_public_blocks() -> None:
    templates = REPO_ROOT / "templates"
    assert templates.is_dir()
    observed_blocks: set[str] = set()
    for template in templates.glob("*.html"):
        source = template.read_text(encoding="utf-8")
        assert re.search(r'{%\s+extends\s+"!theme/[a-z_]+\.html"\s+%}', source)
        observed_blocks.update(re.findall(r"{%\s+block\s+([a-z_]+)", source))

    assert observed_blocks
    assert observed_blocks <= PUBLIC_BLOCKS
    assert len(PUBLIC_BLOCKS) == 18


def test_vendored_theme_is_preserved_but_not_active() -> None:
    assert (REPO_ROOT / "theme/templates/base.html").is_file()
    assert (REPO_ROOT / "theme/static/js/jquery.min.js").is_file()
    settings = "\n".join(
        (
            (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "migration/site_build/markdownconf.py").read_text(
                encoding="utf-8"
            ),
        )
    )
    assert 'THEME = "theme"' not in settings
    assert "REPO_ROOT / \"theme\"" not in settings


def test_browser_matrix_keeps_the_wide_table_case_and_single_focus_label() -> None:
    browser_validator = (
        REPO_ROOT / "migration/site006v/browser_validate.py"
    ).read_text(encoding="utf-8")

    assert browser_validator.count("WIDE_TABLE_ROUTE") >= 6
    assert browser_validator.count("ariaLabel:") == 1
