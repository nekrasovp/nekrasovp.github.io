import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "migration/site004/pages.json"
VALIDATOR = REPO_ROOT / "migration/site004/validate.py"
spec = importlib.util.spec_from_file_location("site004_validate", VALIDATOR)
assert spec and spec.loader
site004 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = site004
spec.loader.exec_module(site004)

DuplicateSite004Writer = site004.DuplicateSite004Writer
OutputRecord = site004.OutputRecord
Site004MetadataMismatch = site004.Site004MetadataMismatch
Site004RenderedMismatch = site004.Site004RenderedMismatch
Site004UnresolvedLink = site004.Site004UnresolvedLink
load_manifest = site004.load_manifest
validate_internal_links = site004.validate_internal_links
validate_inventory = site004.validate_inventory
validate_rendered = site004.validate_rendered
validate_rendered_record = site004.validate_rendered_record


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _synthetic_record(*, kind: str = "page") -> OutputRecord:
    text = "Approved copy Destination"
    return OutputRecord(
        {
            "canonical": "https://nekrasovp.ru/example/",
            "content_hrefs": ["/destination.html"],
            "content_text_sha256": _sha(text),
            "description": "Description",
            "footer_hrefs": [],
            "headings": ["Approved copy"],
            "hreflang": {},
            "jsonld": [
                {
                    "@context": "https://schema.org",
                    "@type": "Person",
                    "name": "Pavel Nekrasov",
                }
            ],
            "kind": kind,
            "lang": "en",
            "navigation_hrefs": [],
            "og": {
                "og:title": "Example",
                "og:type": "website",
                "og:url": "https://nekrasovp.ru/example/",
            },
            "output": "example/index.html",
            "owner": "content/pages/Example.md",
            "robots": None,
            "route": "/example/",
            "title": "Example",
            "twitter": {"twitter:card": "summary"},
        }
    )


def _synthetic_html() -> str:
    return """<!doctype html>
<html lang="en"><head>
<title>Example</title>
<meta name="description" content="Description">
<link rel="canonical" href="https://nekrasovp.ru/example/">
<meta property="og:type" content="website">
<meta property="og:title" content="Example">
<meta property="og:url" content="https://nekrasovp.ru/example/">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","name":"Pavel Nekrasov"}
</script>
</head><body><main><h1>Approved copy</h1>
<a href="/destination.html">Destination</a></main></body></html>
"""


def test_manifest_enumerates_exactly_eight_outputs_and_required_routes() -> None:
    manifest = load_manifest(MANIFEST)
    assert len(manifest.outputs) == 8
    assert {record.output for record in manifest.outputs} == site004.EXPECTED_OUTPUTS
    assert len(manifest.required_generated_routes) == 8


def test_current_inventory_has_one_explicit_writer_per_output() -> None:
    evidence = validate_inventory()
    assert evidence["outputs"] == 8
    assert evidence["page_sources"] == 4
    assert all(len(owners) == 1 for owners in evidence["writers"].values())


def test_duplicate_output_writer_is_a_hard_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "content/pages").mkdir(parents=True)
    (repo / "templates/site004").mkdir(parents=True)
    (repo / "migration/site004").mkdir(parents=True)
    (repo / "migration/site004/pages.json").write_bytes(MANIFEST.read_bytes())
    (repo / "content/pages/About.md").write_text(
        "Title: About\n\nOld body\n", encoding="utf-8"
    )
    (repo / "pelicanconf.py").write_text(
        "TEMPLATE_PAGES = {'site004/redirect-about.html': 'pages/about.html'}\n",
        encoding="utf-8",
    )
    (repo / "templates/site004/redirect-about.html").write_text(
        "<!doctype html>", encoding="utf-8"
    )
    with pytest.raises(DuplicateSite004Writer):
        validate_inventory(repo_root=repo)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('lang="en"', 'lang="ru"'),
        ("https://nekrasovp.ru/example/", "https://nekrasovp.ru/wrong/"),
        ("Approved copy", "Missing approved copy"),
        ('content="Description"', 'content="Wrong"'),
        ('"name":"Pavel Nekrasov"', '"name":"Wrong"'),
    ],
)
def test_rendered_validator_rejects_wrong_semantics(
    tmp_path: Path, old: str, new: str
) -> None:
    output = tmp_path / "example/index.html"
    output.parent.mkdir(parents=True)
    output.write_text(_synthetic_html().replace(old, new, 1), encoding="utf-8")
    with pytest.raises(Site004RenderedMismatch):
        validate_rendered_record(_synthetic_record(), output)


def test_redirect_intent_is_exact(tmp_path: Path) -> None:
    text = "Moved Destination"
    record = OutputRecord(
        {
            "canonical": "https://nekrasovp.ru/destination/",
            "content_hrefs": ["/destination/"],
            "content_text_sha256": _sha(text),
            "description": None,
            "footer_hrefs": [],
            "headings": [],
            "hreflang": {},
            "jsonld": [],
            "kind": "redirect",
            "lang": "en",
            "navigation_hrefs": [],
            "og": {},
            "output": "legacy.html",
            "owner": "templates/site004/redirect.html",
            "redirect_target": "/destination/",
            "robots": "noindex, follow",
            "route": "/legacy.html",
            "title": "Moved",
            "twitter": {},
        }
    )
    output = tmp_path / "legacy.html"
    output.write_text(
        """<!doctype html><html lang="en"><head><title>Moved</title>
<meta http-equiv="refresh" content="0; url=/wrong/">
<link rel="canonical" href="https://nekrasovp.ru/destination/">
<meta name="robots" content="noindex, follow"></head>
<body><p>Moved <a href="/destination/">Destination</a></p></body></html>""",
        encoding="utf-8",
    )
    with pytest.raises(Site004RenderedMismatch):
        validate_rendered_record(record, output)


def test_missing_route_and_unresolved_internal_link_are_hard_errors(
    tmp_path: Path,
) -> None:
    with pytest.raises(Site004RenderedMismatch):
        validate_rendered(tmp_path)

    output = tmp_path / "example/index.html"
    output.parent.mkdir(parents=True)
    output.write_text(_synthetic_html(), encoding="utf-8")
    with pytest.raises(Site004UnresolvedLink):
        site004._resolve_anchor(
            output_root=tmp_path,
            source_output="example/index.html",
            href="/destination.html",
        )


def test_manifest_json_is_valid() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["contract"] == "nekrasovp-site004-pages.v1"
