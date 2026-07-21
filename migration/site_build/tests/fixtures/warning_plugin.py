"""Plugin fixture that emits one deterministic Pelican warning."""

import logging

from pelican import signals

LOGGER = logging.getLogger(__name__)


def emit_warning(_pelican) -> None:
    LOGGER.warning("SITE-001 deterministic warning fixture")


def register() -> None:
    signals.initialized.connect(emit_warning)
