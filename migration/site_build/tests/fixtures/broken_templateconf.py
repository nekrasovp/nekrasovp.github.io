"""Acceptance fixture: configure a theme path that cannot contain templates."""

from migration.site_build.markdownconf import *  # noqa: F403

THEME = "migration/site_build/tests/fixtures/missing-theme"
