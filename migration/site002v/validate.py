"""Run the complete immutable-reader SITE-002V acceptance gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from migration.site003 import validate as site003_validation  # noqa: E402
from migration.site006v import validate as site006v_validation  # noqa: E402

CONTENT_ROOT = REPO_ROOT / "content"
FULL_MANIFEST = REPO_ROOT / "migration/production_parity/inputs/legacy_routes.tsv"
NOTEBOOK_MANIFEST = REPO_ROOT / "migration/site002v/notebooks.tsv"
BASELINE_METADATA = REPO_ROOT / "migration/production_parity/baseline/metadata.json"
REPRESENTATIVE_NOTEBOOK = REPO_ROOT / "migration/site002v/fixtures/representative-outputs.ipynb"
REPRESENTATIVE_METADATA = REPO_ROOT / "migration/site002v/fixtures/representative-outputs.nbdata"
SITE_BASE_COMMIT = "cac7d59b7a691ebdedea17f5978ce24693830bf8"
PLUGIN_COMMIT = "137e1eb0ea620f1b15fff0ba81725eea23de1b7a"
PLUGIN_REPOSITORY = "https://github.com/nekrasovp/pelican-jupyter.git"
PLUGIN_REQUIREMENT = f"pelican-jupyter @ git+{PLUGIN_REPOSITORY}@{PLUGIN_COMMIT}"
EXPECTED_ARTICLES = 46
EXPECTED_MARKDOWN = 35
EXPECTED_NOTEBOOKS = 11
EXPECTED_MISSING_ALT = 57
EXPECTED_EMPTY_ALT = 2
EXPECTED_TITLE_GAPS = 0
EXPECTED_READER_LANGUAGE_ABSENT = 0
EXPECTED_RENDERED_LANGUAGE_GAPS = 0
EXPECTED_TITLE_OVERRIDES = 46
REQUIRED_CORPUS_OUTPUT_MODES = {"code", "image", "markdown", "png", "svg", "table"}


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode:
        output = result.stdout + result.stderr
        raise RuntimeError(f"{label} failed with exit {result.returncode}:\n{output}")


def _resolve_python(executable: str) -> str:
    path = Path(executable)
    if not path.is_absolute():
        path = Path.cwd() / path
    absolute = Path(os.path.abspath(path))
    if not absolute.is_file():
        raise RuntimeError(f"Python executable is unavailable: {executable}")
    return str(absolute)


def _safe_work_root(path: Path) -> Path:
    resolved = Path(os.path.abspath(path))
    forbidden = {Path("/"), REPO_ROOT.resolve(), Path.home().resolve()}
    if resolved in forbidden or "site002v" not in resolved.name.casefold():
        raise RuntimeError(f"refusing unsafe SITE-002V work root: {resolved}")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        path.relative_to(CONTENT_ROOT).as_posix(): _sha256(path)
        for path in sorted(CONTENT_ROOT.rglob("*"))
        if path.is_file()
    }


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *arguments], cwd=REPO_ROOT)


def _git_status() -> str:
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    _require_success(status, "git status")
    return status.stdout


def _verify_site_base() -> None:
    commit = _git("cat-file", "-e", f"{SITE_BASE_COMMIT}^{{commit}}")
    _require_success(commit, "SITE-002V base object check")
    ancestor = _git("merge-base", "--is-ancestor", SITE_BASE_COMMIT, "HEAD")
    if ancestor.returncode:
        raise RuntimeError(f"HEAD is not based on required site commit {SITE_BASE_COMMIT}")


def _load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream, delimiter="\t")]


def _validate_manifests() -> list[dict[str, str]]:
    full = _load_tsv(FULL_MANIFEST)
    notebooks = _load_tsv(NOTEBOOK_MANIFEST)
    required = {"source", "metadata", "route"}
    with NOTEBOOK_MANIFEST.open(encoding="utf-8", newline="") as stream:
        fieldnames = csv.DictReader(stream, delimiter="\t").fieldnames
    if not fieldnames or set(fieldnames) != required:
        raise RuntimeError("notebook manifest must contain source, metadata, and route")

    full_notebooks = [row for row in full if row["source"].casefold().endswith(".ipynb")]
    full_markdown = [row for row in full if row["source"].casefold().endswith(".md")]
    if (len(full), len(full_markdown), len(full_notebooks)) != (
        EXPECTED_ARTICLES,
        EXPECTED_MARKDOWN,
        EXPECTED_NOTEBOOKS,
    ):
        raise RuntimeError("legacy article manifest is not exactly 35 Markdown + 11 notebooks")
    if len(notebooks) != EXPECTED_NOTEBOOKS:
        raise RuntimeError("SITE-002V notebook manifest does not contain exactly 11 rows")

    keys = [(row["source"], row["metadata"], row["route"]) for row in notebooks]
    if len(keys) != len(set(keys)):
        raise RuntimeError("SITE-002V notebook manifest contains duplicate mappings")
    expected_pairs = {(row["source"], row["route"]) for row in full_notebooks}
    actual_pairs = {(row["source"], row["route"]) for row in notebooks}
    if actual_pairs != expected_pairs:
        raise RuntimeError("SITE-002V notebook mappings differ from the BASE-001 manifest")
    for row in notebooks:
        source = Path(row["source"])
        metadata = Path(row["metadata"])
        if source.is_absolute() or metadata.is_absolute() or ".." in source.parts + metadata.parts:
            raise RuntimeError(f"unsafe notebook manifest path: {row!r}")
        if source.suffix.casefold() != ".ipynb" or metadata != source.with_suffix(".nbdata"):
            raise RuntimeError(f"notebook and metadata names do not form a pair: {row!r}")
        if not row["route"].startswith("/") or not row["route"].endswith(".html"):
            raise RuntimeError(f"invalid notebook route: {row!r}")
        if not (CONTENT_ROOT / source).is_file() or not (CONTENT_ROOT / metadata).is_file():
            raise RuntimeError(f"notebook manifest input is missing: {row!r}")
    return notebooks


def _lock_source() -> str:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    matches = [package for package in lock["package"] if package["name"] == "pelican-jupyter"]
    if len(matches) != 1:
        raise RuntimeError("uv.lock must contain exactly one pelican-jupyter package")
    source = matches[0].get("source", {}).get("git")
    if not isinstance(source, str):
        raise RuntimeError("pelican-jupyter lock source is not Git")
    if f"rev={PLUGIN_COMMIT}" not in source or not source.endswith(f"#{PLUGIN_COMMIT}"):
        raise RuntimeError("pelican-jupyter lock source does not resolve the exact commit")
    return source


def _verify_dependency_input() -> str:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    if dependencies.count(PLUGIN_REQUIREMENT) != 1:
        raise RuntimeError("pyproject.toml does not contain the one exact plugin requirement")
    config = (REPO_ROOT / "pelicanconf.py").read_text(encoding="utf-8")
    if "pelican.plugins.ipynb_reader" not in config or "ipynb.markup" in config:
        raise RuntimeError(
            "production-intent configuration does not exclusively select the new reader"
        )
    if (REPO_ROOT / "plugins/ipynb").exists():
        raise RuntimeError("the vendored reader remains under the active plugins root")
    return _lock_source()


def _create_locked_environment(work_root: Path, python: str) -> Path:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required for SITE-002V validation")
    environment_root = work_root / "locked-environment"
    created = _run(
        [uv, "venv", "--python", python, str(environment_root)],
        cwd=work_root,
    )
    _require_success(created, "external virtual environment creation")
    environment = {**os.environ, "VIRTUAL_ENV": str(environment_root)}
    synced = _run(
        [uv, "sync", "--project", str(REPO_ROOT), "--locked", "--all-groups", "--active"],
        cwd=work_root,
        environment=environment,
    )
    _require_success(synced, "external locked environment sync")
    executable = environment_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        raise RuntimeError("external locked Python executable was not created")
    return executable


def _installed_provenance(python: Path) -> dict[str, Any]:
    probe_code = r'''
import importlib.metadata as metadata
import json
from pathlib import Path
import pelican.plugins.ipynb_reader as reader

distribution = metadata.distribution("pelican-jupyter")
direct_url = json.loads(distribution.read_text("direct_url.json"))
print(json.dumps({
    "direct_url": direct_url,
    "module_file": str(Path(reader.__file__).resolve()),
    "version": distribution.version,
}, sort_keys=True))
'''
    probe = _run([str(python), "-I", "-c", probe_code], cwd=python.parent)
    _require_success(probe, "installed reader provenance probe")
    payload = json.loads(probe.stdout)
    module_path = Path(payload["module_file"])
    if module_path.is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"reader imported from the site checkout: {module_path}")
    direct_url = payload["direct_url"]
    vcs = direct_url.get("vcs_info", {})
    if vcs.get("vcs") != "git" or vcs.get("commit_id") != PLUGIN_COMMIT:
        raise RuntimeError(f"installed reader commit provenance is invalid: {direct_url!r}")
    if vcs.get("requested_revision") != PLUGIN_COMMIT:
        raise RuntimeError(f"installed reader requested revision is not exact: {direct_url!r}")
    if direct_url.get("url", "").removeprefix("git+") != PLUGIN_REPOSITORY:
        raise RuntimeError(f"installed reader repository is invalid: {direct_url!r}")
    marker = "/site-packages/"
    normalized = module_path.as_posix()
    if marker not in normalized:
        raise RuntimeError(f"reader did not import from site-packages: {module_path}")
    return {
        "commit_id": vcs["commit_id"],
        "import_path": f"site-packages/{normalized.split(marker, 1)[1]}",
        "outside_source_checkouts": True,
        "repository": direct_url["url"].removeprefix("git+"),
        "requested_revision": vcs["requested_revision"],
        "version": payload["version"],
    }


def _write_instrumentation(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "sitecustomize.py").write_text(
        '''"""Process-local SITE-002V no-execution instrumentation."""
import atexit
import json
import os
import socket
from pathlib import Path

from jupyter_client import KernelManager
from nbclient import NotebookClient

observations = {"client_executes": 0, "kernel_starts": 0, "network_connects": 0}

def blocked_kernel(*args, **kwargs):
    observations["kernel_starts"] += 1
    raise AssertionError("SITE-002V build attempted to start a kernel")

def blocked_execute(*args, **kwargs):
    observations["client_executes"] += 1
    raise AssertionError("SITE-002V build attempted to execute a notebook")

original_connect = socket.socket.connect
def observed_connect(instance, address):
    if instance.family in (socket.AF_INET, socket.AF_INET6):
        observations["network_connects"] += 1
        raise AssertionError("SITE-002V build attempted a network connection")
    return original_connect(instance, address)

KernelManager.start_kernel = blocked_kernel
NotebookClient.execute = blocked_execute
socket.socket.connect = observed_connect

@atexit.register
def record():
    Path(os.environ["SITE002V_OBSERVATIONS"]).write_text(
        json.dumps(observations, sort_keys=True) + "\\n", encoding="utf-8"
    )
''',
        encoding="utf-8",
    )


def _representative_fixture(
    python: Path, work_root: Path, instrumentation: Path, marker: Path
) -> tuple[dict[str, Any], dict[str, int]]:
    if not REPRESENTATIVE_NOTEBOOK.is_file() or not REPRESENTATIVE_METADATA.is_file():
        raise RuntimeError("the committed representative output fixture is incomplete")
    code = r'''
import json
import sys
from html.parser import HTMLParser
from pelican.plugins.ipynb_reader import IPYNBReader
from pelican.settings import read_settings

class Facts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.classes = set()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.casefold())
        for name, value in attrs:
            if name.casefold() == "class" and value:
                self.classes.update(value.split())

source, content_root, output_root = sys.argv[1:]
settings = read_settings(override={
    "OUTPUT_PATH": output_root,
    "PATH": content_root,
    "TIMEZONE": "Europe/Moscow",
})
fragment, metadata = IPYNBReader(settings).read(source)
facts = Facts()
facts.feed(fragment)
facts.close()
required = {"cell", "input_area", "output_error", "output_html", "representative-rich-output"}
missing = sorted(required - facts.classes)
if missing:
    raise RuntimeError(f"representative fragment tokens are missing: {missing!r}")
if "html" in facts.tags or "body" in facts.tags:
    raise RuntimeError("representative fragment contains a nested document")
print(json.dumps({
    "html_contract": metadata["notebook_html_contract"],
    "nested_document": False,
    "required_class_tokens": sorted(required),
    "title": str(metadata["title"]),
}, sort_keys=True))
'''
    observation_path = work_root / "representative-observations.json"
    environment = {
        **os.environ,
        "PELICAN_IPYNB_SENTINEL_MARKER": str(marker),
        "PYTHONPATH": str(instrumentation),
        "SITE002V_OBSERVATIONS": str(observation_path),
    }
    probe = _run(
        [
            str(python),
            "-c",
            code,
            str(REPRESENTATIVE_NOTEBOOK),
            str(REPRESENTATIVE_NOTEBOOK.parent),
            str(work_root / "representative-output"),
        ],
        cwd=work_root,
        environment=environment,
    )
    _require_success(probe, "representative committed-output fixture")
    if not observation_path.is_file():
        raise RuntimeError("representative no-execution observation was not written")
    observed = json.loads(observation_path.read_text(encoding="utf-8"))
    if any(observed.values()) or marker.exists():
        raise RuntimeError(f"representative no-execution observation is not zero: {observed!r}")
    result = json.loads(probe.stdout)
    result.update(
        {
            "metadata_sha256": _sha256(REPRESENTATIVE_METADATA),
            "notebook_sha256": _sha256(REPRESENTATIVE_NOTEBOOK),
        }
    )
    return result, observed


def _validate_build_log(log: str) -> dict[str, int]:
    processed = re.search(r"Done: Processed (\d+) articles", log)
    if not processed or int(processed.group(1)) != EXPECTED_ARTICLES:
        raise RuntimeError(f"Pelican did not report exactly {EXPECTED_ARTICLES} articles")
    missing_alt = [
        int(value)
        for value in re.findall(r"WARNING\s+Alternative text is missing on (\d+) image\(s\)\.", log)
    ]
    empty_alt = len(re.findall(r"WARNING\s+Empty alt attribute for image", log))
    warning_tokens = len(re.findall(r"\bWARNING\b", log))
    if warning_tokens != len(missing_alt) + empty_alt:
        raise RuntimeError("Pelican emitted a warning outside the exact SITE-002V alt ledger")
    ledger = {
        "empty_alt": empty_alt,
        "nbconvert_missing_alt": sum(missing_alt),
        "warning_records": warning_tokens,
    }
    return ledger


def _build_command(python: Path, output: Path) -> list[str]:
    return [
        str(python),
        "-m",
        "pelican",
        str(CONTENT_ROOT),
        "--output",
        str(output),
        "--settings",
        str(REPO_ROOT / "publishconf.py"),
        "--delete-output-directory",
        "--fatal",
        "errors",
    ]


def _gate_command(
    python: Path,
    *,
    baseline_metadata: Path,
    content_root: Path,
    output_root: Path,
    evidence_out: Path,
) -> list[str]:
    return [
        str(python),
        "-m",
        "pelican.plugins.ipynb_reader.publication",
        "--expected-manifest",
        str(FULL_MANIFEST),
        "--baseline-metadata",
        str(baseline_metadata),
        "--content-root",
        str(content_root),
        "--output-root",
        str(output_root),
        "--external-commit",
        PLUGIN_COMMIT,
        "--expected-articles",
        str(EXPECTED_ARTICLES),
        "--expected-notebooks",
        str(EXPECTED_NOTEBOOKS),
        "--expected-missing-alt",
        str(EXPECTED_MISSING_ALT),
        "--expected-empty-alt",
        str(EXPECTED_EMPTY_ALT),
        "--timezone",
        "Europe/Moscow",
        "--evidence-out",
        str(evidence_out),
    ]


def _write_site003_baseline_overlay(path: Path) -> dict[str, Any]:
    payload = json.loads(BASELINE_METADATA.read_text(encoding="utf-8"))
    pages = {page["path"]: page for page in payload["pages"]}
    changed: list[dict[str, str]] = []
    for row in _load_tsv(FULL_MANIFEST):
        page = pages[row["route"]]
        expected_title = f"{row['title']} — {site003_validation.SITENAME}"
        if page["title"] != expected_title:
            changed.append(
                {
                    "after": expected_title,
                    "before": page["title"],
                    "route": row["route"],
                    "source": row["source"],
                }
            )
            page["title"] = expected_title
    if len(changed) != EXPECTED_TITLE_OVERRIDES:
        raise RuntimeError(
            f"SITE-003 title overlay expected {EXPECTED_TITLE_OVERRIDES} changes, "
            f"observed {len(changed)}"
        )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "frozen_baseline_sha256": _sha256(BASELINE_METADATA),
        "overlay_sha256": _sha256(path),
        "title_overrides": changed,
    }


def _metadata_observations(evidence: dict[str, Any]) -> dict[str, Any]:
    notebooks = [
        record for record in evidence["records"] if record["source_kind"] == "notebook"
    ]
    result = {
        "inventory_reader_title_mismatches": sorted(
            record["source"]
            for record in notebooks
            if record["publisher_target"]["route_inventory_title"]
            != record["metadata"]["title"]
        ),
        "owner": "SITE-003",
        "reader_language_absent": sorted(
            record["source"]
            for record in notebooks
            if record["metadata"]["language"] is None
        ),
        "rendered_language_target_mismatches": sorted(
            record["source"]
            for record in notebooks
            if record["rendered_observation"]["html_lang"]
            != record["publisher_target"]["language"]
        ),
    }
    expected = {
        "inventory_reader_title_mismatches": EXPECTED_TITLE_GAPS,
        "reader_language_absent": EXPECTED_READER_LANGUAGE_ABSENT,
        "rendered_language_target_mismatches": EXPECTED_RENDERED_LANGUAGE_GAPS,
    }
    for field, count in expected.items():
        if len(result[field]) != count:
            raise RuntimeError(
                f"metadata deviation {field} expected {count}, "
                f"observed {len(result[field])}"
            )
    return result


def _assert_typed_failure(
    result: subprocess.CompletedProcess[str],
    *,
    label: str,
    source: str,
    tokens: tuple[str, ...],
) -> dict[str, Any]:
    log = result.stdout + result.stderr
    required = (source, *tokens)
    if result.returncode == 0 or not all(token in log for token in required):
        raise RuntimeError(f"{label} did not fail with source-aware tokens {required!r}:\n{log}")
    return {
        "exit_code": result.returncode,
        "isolated_fixture": True,
        "source": source,
        "tokens": list(tokens),
    }


def _reader_failure(
    python: Path, source: Path, content_root: Path, output: Path
) -> subprocess.CompletedProcess[str]:
    code = r'''
import sys
from pelican.plugins.ipynb_reader import IPYNBReader
from pelican.settings import read_settings

source, content_root, output_root = sys.argv[1:]
settings = read_settings(override={
    "OUTPUT_PATH": output_root,
    "PATH": content_root,
    "TIMEZONE": "Europe/Moscow",
})
IPYNBReader(settings).read(source)
'''
    return _run(
        [str(python), "-I", "-c", code, str(source), str(content_root), str(output)],
        cwd=output.parent,
    )


def _negative_gates(
    python: Path,
    work_root: Path,
    notebooks: list[dict[str, str]],
    positive_output: Path,
    baseline_metadata: Path,
) -> dict[str, Any]:
    selected = notebooks[0]
    source_name = selected["source"]
    metadata_name = selected["metadata"]
    route = selected["route"]
    fixtures = work_root / "negative-fixtures"
    fixtures.mkdir()
    results: dict[str, Any] = {}

    missing_source_content = fixtures / "missing-source/content"
    shutil.copytree(CONTENT_ROOT, missing_source_content)
    (missing_source_content / source_name).unlink()
    missing_source = _run(
        _gate_command(
            python,
            baseline_metadata=baseline_metadata,
            content_root=missing_source_content,
            output_root=positive_output,
            evidence_out=fixtures / "missing-source/evidence.json",
        ),
        cwd=fixtures / "missing-source",
    )
    results["missing_source"] = _assert_typed_failure(
        missing_source,
        label="missing source gate",
        source=source_name,
        tokens=("publication_verification", "missing_expected_source", "MissingExpectedSource"),
    )

    missing_route_output = fixtures / "missing-route/output"
    shutil.copytree(positive_output, missing_route_output)
    (missing_route_output / route.lstrip("/")).unlink()
    missing_route = _run(
        _gate_command(
            python,
            baseline_metadata=baseline_metadata,
            content_root=CONTENT_ROOT,
            output_root=missing_route_output,
            evidence_out=fixtures / "missing-route/evidence.json",
        ),
        cwd=fixtures / "missing-route",
    )
    results["missing_route"] = _assert_typed_failure(
        missing_route,
        label="missing route gate",
        source=source_name,
        tokens=("publication_verification", "missing_expected_route", "MissingExpectedRoute"),
    )

    reader_root = fixtures / "reader-inputs"
    reader_root.mkdir()
    source_fixture = reader_root / source_name
    metadata_fixture = reader_root / metadata_name
    shutil.copy2(CONTENT_ROOT / source_name, source_fixture)
    shutil.copy2(CONTENT_ROOT / metadata_name, metadata_fixture)

    missing_metadata_root = fixtures / "missing-metadata/content"
    shutil.copytree(reader_root, missing_metadata_root)
    (missing_metadata_root / metadata_name).unlink()
    missing_metadata = _reader_failure(
        python,
        missing_metadata_root / source_name,
        missing_metadata_root,
        fixtures / "missing-metadata/output",
    )
    results["missing_metadata"] = _assert_typed_failure(
        missing_metadata,
        label="missing metadata gate",
        source=source_name,
        tokens=("metadata_discovery", "missing_metadata", "MissingMetadata"),
    )

    missing_title_root = fixtures / "missing-title/content"
    shutil.copytree(reader_root, missing_title_root)
    title_path = missing_title_root / metadata_name
    original = title_path.read_text(encoding="utf-8")
    without_title = "".join(
        line
        for line in original.splitlines(keepends=True)
        if not line.casefold().startswith("title:")
    )
    title_path.write_text(without_title, encoding="utf-8")
    missing_title = _reader_failure(
        python,
        missing_title_root / source_name,
        missing_title_root,
        fixtures / "missing-title/output",
    )
    results["missing_required_title"] = _assert_typed_failure(
        missing_title,
        label="missing required title gate",
        source=source_name,
        tokens=("validation", "missing_title", "MissingTitle"),
    )

    malformed_root = fixtures / "malformed-notebook/content"
    shutil.copytree(reader_root, malformed_root)
    (malformed_root / source_name).write_text("{not valid notebook json\n", encoding="utf-8")
    malformed = _reader_failure(
        python,
        malformed_root / source_name,
        malformed_root,
        fixtures / "malformed-notebook/output",
    )
    results["malformed_notebook"] = _assert_typed_failure(
        malformed,
        label="malformed notebook gate",
        source=source_name,
        tokens=("notebook_parsing", "malformed_notebook"),
    )

    metadata_source = next(
        row["source"]
        for row in _load_tsv(FULL_MANIFEST)
        if row["source"].casefold().endswith(".md")
    )
    invalid_metadata_root = fixtures / "invalid-metadata/content"
    shutil.copytree(CONTENT_ROOT, invalid_metadata_root)
    metadata_path = invalid_metadata_root / metadata_source
    original_metadata = metadata_path.read_bytes()
    cases = {
        "invalid_language": (b"Lang", b"xx", ("invalid_language", "InvalidLanguage")),
        "unknown_status": (b"Status", b"unknown", ("unknown_status", "UnknownStatus")),
    }
    for label, (field, value, tokens) in cases.items():
        mutated, replacements = re.subn(
            rb"(?im)^" + field + rb":[^\r\n]*",
            field + b": " + value,
            original_metadata,
            count=1,
        )
        if replacements != 1:
            raise RuntimeError(f"could not create {label} SITE-003 fixture")
        metadata_path.write_bytes(mutated)
        failure = _run(
            [
                str(python),
                str(REPO_ROOT / "migration/site003/validate.py"),
                "--content-root",
                str(invalid_metadata_root),
                "--manifest",
                str(FULL_MANIFEST),
                "--base-commit",
                site003_validation.SITE003_BASE_COMMIT,
            ],
            cwd=fixtures / "invalid-metadata",
        )
        results[label] = _assert_typed_failure(
            failure,
            label=f"{label} gate",
            source=metadata_source,
            tokens=("inventory_validation", *tokens),
        )
    metadata_path.write_bytes(original_metadata)
    return results


def run(args: argparse.Namespace) -> dict[str, Any]:
    python = _resolve_python(args.python)
    work_root = _safe_work_root(args.work_root)
    report_out = Path(os.path.abspath(args.report_out or work_root / "report.json"))
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)

    _verify_site_base()
    notebooks = _validate_manifests()
    inventory = site003_validation.validate_inventory()
    baseline_overlay = work_root / "site003-baseline-overlay.json"
    overlay_evidence = _write_site003_baseline_overlay(baseline_overlay)
    lock_source = _verify_dependency_input()
    theme_input = site006v_validation.verify_dependency_input()
    status_before = _git_status()
    sources_before = _source_hashes()
    external_python = _create_locked_environment(work_root, python)
    provenance = _installed_provenance(external_python)
    theme_provenance = site006v_validation.installed_provenance(external_python)

    instrumentation = work_root / "instrumentation"
    _write_instrumentation(instrumentation)
    marker = work_root / "executed.marker"
    representative, representative_observation = _representative_fixture(
        external_python, work_root, instrumentation, marker
    )
    evidence_paths: list[Path] = []
    warning_ledgers: list[dict[str, int]] = []
    observations: list[dict[str, int]] = []
    rendered_contracts: list[dict[str, Any]] = []
    theme_outputs: list[dict[str, Any]] = []

    for number in (1, 2):
        output = work_root / f"output-{number}"
        observation_path = work_root / f"observations-{number}.json"
        environment = {
            **os.environ,
            "PELICAN_IPYNB_SENTINEL_MARKER": str(marker),
            "PYTHONPATH": str(instrumentation),
            "SITE002V_OBSERVATIONS": str(observation_path),
        }
        build = _run(
            _build_command(external_python, output),
            cwd=REPO_ROOT,
            environment=environment,
        )
        log = build.stdout + build.stderr
        if build.returncode:
            raise RuntimeError(f"clean Pelican build {number} failed:\n{log}")
        warning_ledgers.append(_validate_build_log(log))
        if not observation_path.is_file():
            raise RuntimeError(f"no-execution observation {number} was not written")
        observed = json.loads(observation_path.read_text(encoding="utf-8"))
        if any(observed.values()):
            raise RuntimeError(f"no-execution observation {number} is non-zero: {observed!r}")
        observations.append(observed)

        evidence = work_root / f"publication-evidence-{number}.json"
        gate = _run(
            _gate_command(
                external_python,
                baseline_metadata=baseline_overlay,
                content_root=CONTENT_ROOT,
                output_root=output,
                evidence_out=evidence,
            ),
            cwd=work_root,
        )
        _require_success(gate, f"publication completeness gate {number}")
        evidence_paths.append(evidence)
        rendered_contracts.append(
            site003_validation.validate_output(
                output_root=output,
                manifest_path=FULL_MANIFEST,
            )
        )
        theme_outputs.append(site006v_validation.output_evidence(output))

    if evidence_paths[0].read_bytes() != evidence_paths[1].read_bytes():
        raise RuntimeError("the two normalized publication evidence files differ")
    if warning_ledgers[0] != warning_ledgers[1]:
        raise RuntimeError("the two warning ledgers differ")
    if rendered_contracts[0] != rendered_contracts[1]:
        raise RuntimeError("the two SITE-003 rendered contract reports differ")
    if theme_outputs[0] != theme_outputs[1]:
        raise RuntimeError("the two normalized SITE-006V output reports differ")
    if marker.exists():
        raise RuntimeError("the build created the execution marker")
    if _source_hashes() != sources_before:
        raise RuntimeError("content source bytes changed during validation")
    if _git_status() != status_before:
        raise RuntimeError("Git status changed during validation")

    publication = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
    if publication["counts"] != {
        "articles": EXPECTED_ARTICLES,
        "markdown": EXPECTED_MARKDOWN,
        "notebooks": EXPECTED_NOTEBOOKS,
    }:
        raise RuntimeError(f"unexpected publication counts: {publication['counts']!r}")
    observed_modes = set(publication["output_modes"])
    missing_modes = sorted(REQUIRED_CORPUS_OUTPUT_MODES - observed_modes)
    if missing_modes:
        raise RuntimeError(f"representative committed output modes are missing: {missing_modes!r}")

    negative = _negative_gates(
        external_python,
        work_root,
        notebooks,
        work_root / "output-1",
        baseline_overlay,
    )
    if _source_hashes() != sources_before or _git_status() != status_before:
        raise RuntimeError("isolated negative fixtures changed repository sources or status")

    result = {
        "contract": "nekrasovp-site002v-site003-site006v-validation.v3",
        "counts": publication["counts"],
        "dependency": {
            "direct_requirement": PLUGIN_REQUIREMENT,
            "installed": provenance,
            "lock_source": lock_source,
            "plugin_commit": PLUGIN_COMMIT,
        },
        "determinism": {
            "normalized_asset_evidence_identical": True,
            "normalized_metadata_evidence_identical": True,
            "normalized_publication_evidence_sha256": _sha256(evidence_paths[0]),
            "publication_evidence_identical": True,
            "route_evidence_identical": True,
            "theme_identity_evidence_identical": True,
            "warning_ledgers_identical": True,
        },
        "emitted_build_warning_ledger": warning_ledgers[0],
        "metadata_observations": _metadata_observations(publication),
        "negative_gates": negative,
        "no_execution": {
            "committed_fixture_observation": representative_observation,
            "marker_created": False,
            "observations": observations,
            "repository_status_unchanged": True,
            "source_bytes_unchanged": True,
        },
        "notebook_manifest": [
            {key: row[key] for key in ("source", "metadata", "route")} for row in notebooks
        ],
        "output_modes": publication["output_modes"],
        "publication_records": publication["records"],
        "representative_committed_output_fixture": representative,
        "site_base_commit": SITE_BASE_COMMIT,
        "site003": {
            "baseline_overlay": overlay_evidence,
            "inventory": inventory,
            "rendered": rendered_contracts[0],
        },
        "site006v": {
            "candidate": {
                **theme_input,
                "installed": theme_provenance,
                "theme_commit": site006v_validation.THEME_COMMIT,
            },
            "output": theme_outputs[0],
            "presentation_changes": {
                "approved_title_separator": " — ",
                "baseline_title_overrides": EXPECTED_TITLE_OVERRIDES,
                "legacy_presentation_selectors_required": False,
            },
        },
        "warning_ledger": publication["warning_ledger"],
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--python", default=sys.executable)
    result.add_argument(
        "--work-root",
        type=Path,
        default=Path(tempfile.gettempdir()) / "nekrasovp-site002v-validation",
    )
    result.add_argument("--report-out", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        evidence = run(args)
    except Exception as error:
        print(f"SITE-002V validation failed: {error}", file=sys.stderr)
        return 1
    counts = evidence["counts"]
    print(
        "SITE-006V validation passed twice: "
        f"{counts['markdown']} Markdown + {counts['notebooks']} notebooks = "
        f"{counts['articles']} articles; {len(evidence['negative_gates'])} negative gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
