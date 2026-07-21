"""Acceptance fixture for the Markdown warnings-as-errors policy."""

from migration.site_build.markdownconf import *  # noqa: F403

PLUGINS = ["migration.site_build.tests.fixtures.warning_plugin"]
