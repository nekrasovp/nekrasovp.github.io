"""Inject the frozen three-entry SITE-005 delta into only the site-wide Atom feed."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pelican import signals

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
MANIFEST = Path(__file__).resolve().parents[1] / "migration/site005/materials.json"


def _entry(record: dict, siteurl: str) -> str:
    feed = record["feed"]
    categories = "".join(
        f"    <category term=\"{html.escape(tag, quote=True)}\" />\n"
        for tag in feed["tags"]
    )
    summary = html.escape(f"<p>{feed['summary']}</p>")
    url = f"{siteurl.rstrip('/')}{record['route']}"
    return (
        "  <entry>\n"
        f"    <title>{html.escape(feed['title'])}</title>\n"
        f"    <link href=\"{html.escape(url, quote=True)}\" rel=\"alternate\" />\n"
        f"    <published>{record['published']}</published>\n"
        f"    <updated>{record['published']}</updated>\n"
        f"    <author><name>{html.escape(record['author'])}</name></author>\n"
        f"    <id>{html.escape(feed['id'])}</id>\n"
        f"    <summary type=\"html\">{summary}</summary>\n"
        f"{categories}"
        "  </entry>\n"
    )


def inject_site005_feed_delta(pelican) -> None:
    """Preserve the generated legacy feed and prepend exactly three summary entries."""

    relative = pelican.settings.get("FEED_ALL_ATOM")
    siteurl = str(pelican.settings.get("SITEURL") or "")
    if not relative or not siteurl.startswith(("https://", "http://")):
        return
    path = Path(pelican.settings["OUTPUT_PATH"]) / str(relative)
    if not path.is_file():
        raise RuntimeError(f"SITE-005 site-wide Atom feed is missing: {path}")
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    essays = [record for record in payload["materials"] if record["role"] == "essay"]
    if len(essays) != 3:
        raise RuntimeError("SITE-005 manifest must declare exactly three feed essays")
    raw = path.read_text(encoding="utf-8")
    root = ET.fromstring(raw)
    namespace = {"atom": ATOM_NAMESPACE}
    existing_ids = {
        node.text for node in root.findall("atom:entry/atom:id", namespace) if node.text
    }
    declared_ids = {record["feed"]["id"] for record in essays}
    if existing_ids & declared_ids:
        raise RuntimeError("SITE-005 essay was already present in the generated feed")
    updated = essays[0]["published"]
    raw, count = re.subn(
        r"(<updated>)[^<]+(</updated>)",
        rf"\g<1>{updated}\g<2>",
        raw,
        count=1,
    )
    if count != 1:
        raise RuntimeError("SITE-005 could not update the site-wide feed timestamp")
    marker = raw.find("<entry>")
    if marker < 0:
        raise RuntimeError("SITE-005 site-wide Atom feed has no legacy entry")
    injected = "".join(_entry(record, siteurl) for record in essays)
    path.write_text(raw[:marker] + injected + raw[marker:], encoding="utf-8")


def register() -> None:
    signals.finalized.connect(inject_site005_feed_delta)
