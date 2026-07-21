"""Markdown-only smoke configuration for SITE-001."""

from pathlib import Path

from pelicanconf import *  # noqa: F403

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keep all working site plugins in the smoke build. The legacy notebook reader
# is excluded only here so modern dependencies can validate the Markdown route.
MARKUP = ("md",)
THEME = str(REPO_ROOT / "theme")
PLUGIN_PATHS = [str(REPO_ROOT / "plugins")]
PLUGINS = ["i18n_subsites", "related_posts", "tag_cloud"]
