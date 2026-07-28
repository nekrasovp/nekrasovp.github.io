"""Standard-library-only CUT-001 evidence package manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def build_evidence_manifest(
    evidence_root: Path,
    source_commit: str,
) -> dict[str, Any]:
    files = []
    for path in sorted(
        item
        for item in evidence_root.rglob("*")
        if item.is_file() and item.name != "manifest.json"
    ):
        files.append(
            {
                "path": path.relative_to(evidence_root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
        )
    return {
        "contract": "nekrasovp-cut001-evidence-manifest.v1",
        "files": files,
        "source_commit": source_commit,
    }
