"""Expose SITE-003 lifecycle metadata while preserving SITE-005 hidden Articles."""

from pelican import signals
from pelican.contents import Article

LIFECYCLE_STATUSES = {"archive", "deprecated", "keep", "refresh"}
ARCHIVE_NOTICES = {
    "en": "This article is preserved as a historical record and may not reflect current practices.",
    "ru": (
        "Статья сохранена как исторический материал и может не отражать "
        "современные практики."
    ),
}
DEPRECATED_WARNING = (
    "This article is deprecated and may contain outdated or unsafe guidance. "
    "Verify current documentation before use."
)


def normalize_article_status(content):
    """Keep lifecycle status for templates while publishing every legacy article."""

    if not isinstance(content, Article) or "status" not in content.metadata:
        return
    if str(content.metadata.get("site005_material", "")).casefold() == "true":
        publication_status = str(content.metadata["status"]).casefold()
        if publication_status != "hidden":
            raise ValueError(
                f"SITE-005 material must use hidden status for {content.source_path}"
            )
        role = str(content.metadata.get("site005_role", "")).casefold()
        if role not in {"essay", "companion"}:
            raise ValueError(f"unknown SITE-005 role {role!r} for {content.source_path}")
        content.site005_material = True
        content.site005_role = role
        content.status = "hidden"
        return
    lifecycle_status = str(content.metadata["status"]).casefold()
    if lifecycle_status not in LIFECYCLE_STATUSES:
        raise ValueError(
            f"unknown SITE-003 lifecycle status {lifecycle_status!r} "
            f"for {content.source_path}"
        )
    content.lifecycle_status = lifecycle_status
    language = str(getattr(content, "lang", "en")).casefold()
    if lifecycle_status == "archive":
        content.archive_notice = ARCHIVE_NOTICES.get(language, ARCHIVE_NOTICES["en"])
    elif lifecycle_status == "deprecated":
        content.deprecated_warning = DEPRECATED_WARNING
    content.status = "published"


def register():
    signals.content_object_init.connect(normalize_article_status)
