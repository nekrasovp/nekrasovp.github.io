#!/usr/bin/env python3
"""Prove that the SITE-001 wrapper propagates a real Jinja template error."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BUILD_WRAPPER = Path(__file__).with_name("build.py")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="site001-template-failure-") as temporary:
        root = Path(temporary)
        broken_theme = root / "theme"
        shutil.copytree(REPOSITORY_ROOT / "theme", broken_theme)
        (broken_theme / "templates" / "base.html").write_text(
            "{% this_tag_does_not_exist %}\n", encoding="utf-8"
        )
        settings = root / "brokenconf.py"
        settings.write_text(
            "from migration.site_build.markdown_smokeconf import *\n"
            f"THEME = {str(broken_theme)!r}\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(BUILD_WRAPPER),
                "build",
                "markdown-smoke",
                "--output",
                str(root / "output"),
                "--settings",
                str(settings),
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    combined = completed.stdout + completed.stderr
    if completed.returncode == 0:
        print("wrapper incorrectly returned zero for a broken template", file=sys.stderr)
        return 1
    if "this_tag_does_not_exist" not in combined and "TemplateSyntaxError" not in combined:
        print("build failed, but not with the forced template error", file=sys.stderr)
        print(combined, file=sys.stderr)
        return 1
    print(f"template failure propagated: child_exit={completed.returncode} verifier_exit=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
