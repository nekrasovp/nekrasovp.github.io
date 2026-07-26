#!/usr/bin/env python3
"""Compose BASE-001 parity with global artifact integrity checks for OPS-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Sequence
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = REPO_ROOT / "migration/production_parity/baseline"
BASELINE_SCRIPTS = REPO_ROOT / "migration/production_parity/scripts"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BASELINE_SCRIPTS))

from check_generated_baseline import check_generated  # noqa: E402

CANONICAL_HOST = "nekrasovp.ru"
FORBIDDEN_LINK_HOSTS = {"localhost", "127.0.0.1", "nekrasovp.github.io"}
URL_ATTRIBUTES = (("link", "href"), ("script", "src"), ("img", "src"))
REVIEWED_BASE_DIFFERENCES_COUNT = 269
REVIEWED_BASE_DIFFERENCES_SHA256 = (
    "01d9fe59419bdbe96bf02288d683a5ff18001067b1e9aba8f81b5892fac68067"
)
RETIRED_BASE_ASSET_ERRORS = {
    "missing referenced asset: assets/site.css",
    "missing referenced asset: theme/css/bootstrap.flatly.min.css",
    "missing referenced asset: theme/css/font-awesome.min.css",
    "missing referenced asset: theme/css/pygments/friendly.css",
    "missing referenced asset: theme/css/style.css",
}
CANONICAL_DIFFERENCE = re.compile(
    r"^metadata mismatch for (?P<path>/[^:]*): canonical "
    r"expected=.* actual='(?P<actual>https://nekrasovp\.ru[^']*)'$"
)


def _local_target(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme in {"data", "javascript", "mailto", "tel"}:
        return None
    if parsed.hostname and parsed.hostname != CANONICAL_HOST:
        return None
    path = unquote(parsed.path)
    if not path or path == "/":
        return "index.html"
    target = PurePosixPath(path.removeprefix("/"))
    if path.endswith("/"):
        target /= "index.html"
    return target.as_posix()


def _check_url(
    *,
    output_root: Path,
    source: str,
    url: str,
    check_target: bool,
) -> list[str]:
    errors: list[str] = []
    parsed = urlsplit(url)
    if parsed.hostname in FORBIDDEN_LINK_HOSTS:
        errors.append(f"forbidden production host in {source}: {url}")
    if parsed.scheme in {"http", "https"} and parsed.hostname not in {
        None,
        CANONICAL_HOST,
    }:
        return errors
    if check_target:
        target = _local_target(url)
        if target is not None and not (output_root / target).exists():
            errors.append(f"missing internal link target in {source}: {url} -> {target}")
    return errors


def _check_html(output_root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    files = 0
    links = 0
    for path in sorted(output_root.rglob("*.html")):
        files += 1
        relative = path.relative_to(output_root).as_posix()
        try:
            soup = BeautifulSoup(path.read_bytes(), "html.parser")
        except Exception as error:
            errors.append(f"invalid HTML {relative}: {error}")
            continue
        if soup.find("html") is None:
            errors.append(f"invalid HTML {relative}: missing html element")
        nodes: list[tuple[Any, str]] = []
        for tag, attribute in URL_ATTRIBUTES:
            for node in soup.find_all(tag):
                nodes.append((node, attribute))
        for node in soup.find_all(
            "meta",
            attrs={"property": lambda value: value in {"og:url", "twitter:url"}},
        ):
            nodes.append((node, "content"))
        for node in soup.find_all("a", href=True):
            if node.find_parent("article", class_="pet-prose") is None:
                nodes.append((node, "href"))
        for node, attribute in nodes:
            value = node.get(attribute)
            if not isinstance(value, str) or value.startswith("#"):
                continue
            links += 1
            errors.extend(
                _check_url(
                    output_root=output_root,
                    source=relative,
                    url=value,
                    check_target=(
                        not (
                            urlsplit(value).scheme == ""
                            and any(character.isspace() for character in value)
                        )
                        and (
                            node.name != "a"
                            or value.startswith("/")
                            or urlsplit(value).hostname == CANONICAL_HOST
                        )
                    ),
                )
            )
    return errors, {"html_files": files, "html_links": links}


def _check_xml(output_root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    files = 0
    urls = 0
    for path in sorted(output_root.rglob("*.xml")):
        files += 1
        relative = path.relative_to(output_root).as_posix()
        try:
            root = ET.parse(path).getroot()
        except Exception as error:
            errors.append(f"invalid XML {relative}: {error}")
            continue
        for node in root.iter():
            candidates = [node.attrib.get("href")]
            local_name = node.tag.rsplit("}", 1)[-1]
            if local_name in {"link", "loc", "uri"}:
                candidates.append(node.text)
            for value in candidates:
                if not isinstance(value, str) or "://" not in value:
                    continue
                urls += 1
                errors.extend(
                    _check_url(
                        output_root=output_root,
                        source=relative,
                        url=value,
                        check_target=False,
                    )
                )
    return errors, {"xml_files": files, "xml_urls": urls}


def _artifact_sha256(output_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        relative = path.relative_to(output_root).as_posix().encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _accepted_migration_evidence(output_root: Path) -> dict[str, Any]:
    from migration.site003 import validate as site003
    from migration.site004 import validate as site004
    from migration.site006v import validate as site006v

    site006v_output = site006v.output_evidence(output_root)
    committed = json.loads(
        (REPO_ROOT / "migration/site004/evidence/validation.json").read_text(
            encoding="utf-8"
        )
    )["site006v"]["output"]
    for field in ("metadata", "routes"):
        if site006v_output[field]["sha256"] != committed[field]["sha256"]:
            raise RuntimeError(
                f"SITE-006V {field} fingerprint changed: "
                f"expected={committed[field]['sha256']} "
                f"actual={site006v_output[field]['sha256']}"
            )
    return {
        "site003": site003.validate_output(output_root=output_root),
        "site004": site004.validate_rendered(output_root),
        "site006v": site006v_output,
    }


def _is_reviewed_parity_candidate(error: str) -> bool:
    if error.startswith("metadata mismatch") and (
        ": publication_date " in error or ": title " in error
    ):
        return True
    canonical = CANONICAL_DIFFERENCE.fullmatch(error)
    if canonical:
        path = canonical.group("path")
        actual = canonical.group("actual").rstrip("/")
        expected = f"https://nekrasovp.ru{path}".rstrip("/")
        return actual == expected
    return error in RETIRED_BASE_ASSET_ERRORS


def _reviewed_parity_fingerprint(errors: list[str]) -> tuple[int, str]:
    candidates = sorted(error for error in errors if _is_reviewed_parity_candidate(error))
    payload = ("\n".join(candidates) + "\n").encode()
    return len(candidates), hashlib.sha256(payload).hexdigest()


def validate_artifact(
    output_root: Path,
    *,
    baseline_root: Path = BASELINE_ROOT,
    accepted_migration_contracts: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    root = output_root.resolve()
    if not root.is_dir():
        return [f"missing artifact directory: {root}"], {}
    parity_errors = check_generated(root, baseline_root.resolve())
    accepted_evidence: dict[str, Any] | None = None
    accepted_contract_error: str | None = None
    reviewed_differences: list[str] = []
    if accepted_migration_contracts:
        try:
            accepted_evidence = _accepted_migration_evidence(root)
        except Exception as error:  # existing validators expose their typed reasons
            accepted_contract_error = str(error)
        else:
            count, fingerprint = _reviewed_parity_fingerprint(parity_errors)
            if (
                count == REVIEWED_BASE_DIFFERENCES_COUNT
                and fingerprint == REVIEWED_BASE_DIFFERENCES_SHA256
            ):
                reviewed_differences = [
                    error
                    for error in parity_errors
                    if _is_reviewed_parity_candidate(error)
                ]
                parity_errors = [
                    error for error in parity_errors if error not in reviewed_differences
                ]
            else:
                accepted_contract_error = (
                    "reviewed BASE difference fingerprint mismatch: "
                    f"expected_count={REVIEWED_BASE_DIFFERENCES_COUNT} "
                    f"actual_count={count} "
                    f"expected_sha256={REVIEWED_BASE_DIFFERENCES_SHA256} "
                    f"actual_sha256={fingerprint}"
                )
    html_errors, html_evidence = _check_html(root)
    xml_errors, xml_evidence = _check_xml(root)
    contract_errors = (
        [f"accepted migration contract failed: {accepted_contract_error}"]
        if accepted_contract_error
        else []
    )
    errors = sorted(
        set([*parity_errors, *html_errors, *xml_errors, *contract_errors])
    )
    evidence = {
        "artifact_sha256": _artifact_sha256(root),
        "accepted_migration_contracts": accepted_evidence,
        "accepted_migration_contract_error": accepted_contract_error,
        "base_parity_errors": len(parity_errors),
        "global_errors": len(set([*html_errors, *xml_errors])),
        "reviewed_base_differences": len(reviewed_differences),
        **html_evidence,
        **xml_evidence,
    }
    return errors, evidence


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("output_root", type=Path)
    result.add_argument("--baseline-dir", type=Path, default=BASELINE_ROOT)
    result.add_argument("--accepted-migration-contracts", action="store_true")
    result.add_argument("--report-out", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    errors, evidence = validate_artifact(
        args.output_root,
        baseline_root=args.baseline_dir,
        accepted_migration_contracts=args.accepted_migration_contracts,
    )
    report = {
        "contract": "nekrasovp-ops001-validation.v1",
        "errors": errors,
        "evidence": evidence,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
