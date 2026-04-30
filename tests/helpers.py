# Copyright (c) Microsoft. All rights reserved.

"""Test helpers for subprocess-level CLI invocation.

Mirrors the pattern used in amplifier-bundle-gitea: invoke the CLI via
``uv run --no-sync`` so tests behave exactly like a real user. Run
``uv sync`` once before running tests.
"""

import json
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run amplifier-reality-check via uv, exactly as a user would."""
    return subprocess.run(
        [
            "uv",
            "run",
            "--no-sync",
            "--project",
            str(PROJECT_DIR),
            "amplifier-reality-check",
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_cli_json(
    *args: str, **kwargs
) -> tuple[dict, subprocess.CompletedProcess[str]]:
    """Run a command, assert success, parse JSON from stdout."""
    result = run_cli(*args, **kwargs)
    assert result.returncode == 0, (
        f"Command failed (exit {result.returncode}):\n"
        f"  stdout: {result.stdout}\n"
        f"  stderr: {result.stderr}"
    )
    return json.loads(result.stdout), result
