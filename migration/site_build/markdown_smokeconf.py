"""Production-shaped configuration for SITE-001 Markdown-only smoke builds."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from publishconf import *  # noqa: F403,E402


# SITE-001 intentionally excludes the archived notebook reader. The normal
# production configuration remains unchanged and therefore still exposes the
# notebook incompatibility owned by PLUGIN-002/SITE-002.
MARKUP = ("md",)
PLUGINS = ["i18n_subsites", "related_posts", "tag_cloud"]
PLUGIN_PATHS = [str(REPOSITORY_ROOT / "plugins")]
THEME = str(REPOSITORY_ROOT / "theme")
DELETE_OUTPUT_DIRECTORY = True
