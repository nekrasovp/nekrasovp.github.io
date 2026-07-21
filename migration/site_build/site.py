"""Single, reproducible command entrypoint for SITE-001 builds."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT = REPO_ROOT / "content"
DEFAULT_OUTPUTS = {
    "markdown": Path("build/markdown"),
    "build": Path("build/production"),
    "serve": Path("build/local"),
}
DEFAULT_CONFIGS = {
    "markdown": Path("migration/site_build/markdownconf.py"),
    "build": Path("publishconf.py"),
    "serve": Path("migration/site_build/markdownconf.py"),
}


def resolve_from_repo(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def validate_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == Path("/") or resolved == REPO_ROOT.resolve():
        raise ValueError(f"refusing unsafe output directory: {resolved}")


def pelican_command(
    mode: str,
    *,
    output: str | Path | None = None,
    config: str | Path | None = None,
    port: int = 8000,
) -> list[str]:
    output_path = resolve_from_repo(output or DEFAULT_OUTPUTS[mode])
    config_path = resolve_from_repo(config or DEFAULT_CONFIGS[mode])
    validate_output(output_path)

    command = [
        sys.executable,
        "-m",
        "pelican",
        str(CONTENT),
        "--output",
        str(output_path),
        "--settings",
        str(config_path),
        "--delete-output-directory",
    ]
    if mode == "markdown":
        command.extend(["--fatal", "warnings"])
    elif mode == "build":
        # Pelican otherwise logs reader failures and exits zero after silently
        # omitting affected articles. Production errors must remain fatal.
        command.extend(["--fatal", "errors"])
    elif mode == "serve":
        command.extend(["--listen", "--autoreload", "--port", str(port)])
    return command


def run(command: Sequence[str]) -> int:
    """Run a child command and preserve its exact exit status."""
    try:
        return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode
    except KeyboardInterrupt:
        return 130


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    for name in ("markdown", "build"):
        command = subparsers.add_parser(name)
        command.add_argument("--output")
        command.add_argument("--config")

    serve = subparsers.add_parser("serve")
    serve.add_argument("--output")
    serve.add_argument("--config")
    serve.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("test")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "test":
        return run([sys.executable, "-m", "pytest"])
    return run(
        pelican_command(
            args.command,
            output=args.output,
            config=args.config,
            port=getattr(args, "port", 8000),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
