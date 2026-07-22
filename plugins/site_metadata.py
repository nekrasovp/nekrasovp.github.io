"""Expose SITE-003 lifecycle metadata without consuming Pelican publication status."""

from pelican import signals
from pelican.contents import Article

LIFECYCLE_STATUSES = {"archive", "deprecated", "keep", "refresh"}


def normalize_article_status(content):
    """Keep lifecycle status for templates while publishing every legacy article."""

    if not isinstance(content, Article) or "status" not in content.metadata:
        return
    lifecycle_status = str(content.metadata["status"]).casefold()
    if lifecycle_status not in LIFECYCLE_STATUSES:
        raise ValueError(
            f"unknown SITE-003 lifecycle status {lifecycle_status!r} "
            f"for {content.source_path}"
        )
    content.lifecycle_status = lifecycle_status
    content.status = "published"


def register():
    signals.content_object_init.connect(normalize_article_status)
