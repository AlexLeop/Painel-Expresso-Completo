"""Run the one-shot backend release tasks in a fixed, fail-fast order.

This entrypoint intentionally avoids a shell command chain so deployment
platforms do not need to preserve quoting around ``&&`` expressions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


APP_ROOT = Path(__file__).resolve().parents[1]


def deployment_commands(python_executable: str = sys.executable) -> tuple[tuple[str, ...], ...]:
    return (
        (python_executable, "scripts/apply_schema.py"),
        (
            python_executable,
            "manage.py",
            "migrate",
            "--settings=config.settings_migrate",
            "--noinput",
        ),
        (
            python_executable,
            "manage.py",
            "warmup_denylist",
            "--settings=config.settings_migrate",
        ),
        (
            python_executable,
            "manage.py",
            "collectstatic",
            "--settings=config.settings_migrate",
            "--noinput",
        ),
    )


def run(commands: Sequence[Sequence[str]]) -> None:
    for command in commands:
        print(f"[deploy] Running: {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=APP_ROOT, check=True)


def main() -> int:
    try:
        run(deployment_commands())
    except subprocess.CalledProcessError as exc:
        print(
            f"[deploy] Failed with exit code {exc.returncode}: {' '.join(exc.cmd)}",
            file=sys.stderr,
        )
        return exc.returncode or 1

    print("[deploy] Release tasks completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
