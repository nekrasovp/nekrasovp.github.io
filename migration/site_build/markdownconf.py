"""Markdown-only smoke configuration for SITE-001."""

from pathlib import Path

from pelicanconf import *  # noqa: F403

REPO_ROOT = Path(__file__).resolve().parents[2]

# Installed namespace plugins are auto-discovered by Pelican, so the explicit
# ignore is what makes this command an intentionally Markdown-only smoke build.
MARKUP = ("md",)
IGNORE_FILES = [*IGNORE_FILES, "*.ipynb"]  # noqa: F405
THEME = str(REPO_ROOT / "theme")
PLUGIN_PATHS = [str(REPO_ROOT / "plugins")]
PLUGINS = ["i18n_subsites", "related_posts", "tag_cloud"]
