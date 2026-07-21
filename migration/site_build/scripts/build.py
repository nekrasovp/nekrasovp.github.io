#!/usr/bin/env python3
"""Run explicit, failure-propagating Pelican builds for SITE-001."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTENT_PATH = REPOSITORY_ROOT / "content"
SYSTEM_TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
TEMP_ROOTS = {SYSTEM_TEMP_ROOT, Path("/tmp").resolve(), Path("/var/tmp").resolve()}
SETTINGS = {
    "local": REPOSITORY_ROOT / "pelicanconf.py",
    "markdown-smoke": REPOSITORY_ROOT / "migration" / "site_build" / "markdown_smokeconf.py",
    "production": REPOSITORY_ROOT / "publishconf.py",
}
PROTECTED_OUTPUTS = {
    Path("/"),
    Path.home().resolve(),
    *TEMP_ROOTS,
    REPOSITORY_ROOT,
    (REPOSITORY_ROOT / ".git").resolve(),
    CONTENT_PATH.resolve(),
    (REPOSITORY_ROOT / "migration").resolve(),
    (REPOSITORY_ROOT / "plugins").resolve(),
    (REPOSITORY_ROOT / "theme").resolve(),
}


def resolved_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPOSITORY_ROOT / path
    return path.resolve()


def output_path(value: str) -> Path:
    path = resolved_path(value)
    if path in PROTECTED_OUTPUTS:
        raise argparse.ArgumentTypeError(f"unsafe output path: {path}")
    if REPOSITORY_ROOT in path.parents:
        allowed_roots = {
            (REPOSITORY_ROOT / ".tmp").resolve(),
            (REPOSITORY_ROOT / "output").resolve(),
        }
        if path not in allowed_roots and not any(root in path.parents for root in allowed_roots):
            raise argparse.ArgumentTypeError(
                "output inside the checkout must be under .tmp/ or output/"
            )
    elif not any(root in path.parents for root in TEMP_ROOTS):
        raise argparse.ArgumentTypeError(
            "absolute output outside the checkout must be under a system temporary directory"
        )
    return path


def settings_path(value: str) -> Path:
    path = resolved_path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"settings file does not exist: {path}")
    return path


def pelican_command(args: argparse.Namespace) -> list[str]:
    settings = args.settings or SETTINGS[args.mode]
    command = [
        sys.executable,
        "-m",
        "pelican",
        str(CONTENT_PATH),
        "--output",
        str(args.output),
        "--settings",
        str(settings),
        "--delete-output-directory",
    ]
    fatal_level = "warnings" if args.mode == "markdown-smoke" else "errors"
    command.extend(["--fatal", fatal_level])
    return command


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="run one clean Pelican build")
    build.add_argument("mode", choices=tuple(SETTINGS))
    build.add_argument("--output", required=True, type=output_path)
    build.add_argument("--settings", type=settings_path, help=argparse.SUPPRESS)

    serve = subparsers.add_parser("serve", help="build and serve locally")
    serve.add_argument("mode", choices=("local", "markdown-smoke"), default="local", nargs="?")
    serve.add_argument("--output", required=True, type=output_path)
    serve.add_argument("--settings", type=settings_path, help=argparse.SUPPRESS)
    serve.add_argument("--bind", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    return result


def main() -> int:
    args = parser().parse_args()
    completed = subprocess.run(pelican_command(args), cwd=REPOSITORY_ROOT, check=False)
    if completed.returncode or args.command == "build":
        return completed.returncode
    server = [
        sys.executable,
        "-m",
        "http.server",
        str(args.port),
        "--bind",
        args.bind,
        "--directory",
        str(args.output),
    ]
    try:
        return subprocess.run(server, cwd=REPOSITORY_ROOT, check=False).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
