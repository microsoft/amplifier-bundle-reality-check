#!/usr/bin/env python3
"""Cheap structural check for this bundle: does its YAML actually parse?

Run it exactly the same way CI does::

    uv run --no-project --with pyyaml python .github/scripts/check_bundle_structure.py

What it checks, and nothing more:

1. ``bundle.md`` has a ``---`` fenced YAML frontmatter block that parses, and
   declares ``bundle.name`` and ``bundle.version``.
2. Every path in the frontmatter's ``includes:`` list resolves to a file that
   exists on disk. Entries take the ``<bundle-name>:<relative/path>`` form and
   MAY omit the extension (``reality-check:behaviors/reality-check`` resolves
   to ``behaviors/reality-check.yaml``), so both spellings are accepted.
3. Every ``behaviors/*.yaml`` parses as YAML and is a non-empty mapping.

What it deliberately does NOT check:

* ``recipes/**/*.yaml`` -- already parsed, and schema-linted harder, by
  ``tests/test_recipe_schema_lint.py`` in the test job. Duplicating it here
  would give two places to update and one of them would rot.
* Anything semantic. This is a syntax gate, not a validator.

Deliberate design notes:

* An EMPTY glob is a FAILURE, not a pass. A check that silently reports
  "0 problems found in 0 files" is indistinguishable from a working one.
* Paths are resolved relative to this file's own location, never interpolated
  into source text, and are reported with ``as_posix()`` so the output reads
  the same on every OS.
* No network, no API keys, no LLM. Runs in about a second.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

problems: list[str] = []
checked: list[str] = []


def rel(path: Path) -> str:
    """Repo-relative, forward-slash path -- identical output on every OS."""
    return path.relative_to(REPO_ROOT).as_posix()


def parse_frontmatter(text: str) -> dict | None:
    """Return the parsed YAML frontmatter of a bundle.md, or None if malformed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        return None
    block = "\n".join(lines[1:end])
    loaded = yaml.safe_load(block)
    return loaded if isinstance(loaded, dict) else None


def resolve_include(entry: str) -> Path | None:
    """Resolve an ``includes:`` entry to an existing file, or None.

    Accepts ``<bundle>:<path>`` and bare ``<path>``, with or without a YAML
    extension -- the bundle loader appends one, so a manifest that omits it is
    correct and must not be reported as a broken link.
    """
    _, _, relative = entry.partition(":")
    candidate = relative or entry
    for suffix in ("", ".yaml", ".yml"):
        target = REPO_ROOT / f"{candidate}{suffix}"
        if target.is_file():
            return target
    return None


# --- 1 + 2: bundle.md frontmatter -------------------------------------------

bundle_md = REPO_ROOT / "bundle.md"

if not bundle_md.is_file():
    problems.append("bundle.md is missing from the repository root")
else:
    try:
        parsed = parse_frontmatter(bundle_md.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        parsed = None
        problems.append(f"{rel(bundle_md)}: frontmatter is not valid YAML: {exc}")

    if parsed is None:
        problems.append(
            f"{rel(bundle_md)}: no parseable '---' fenced YAML frontmatter mapping"
        )
    else:
        checked.append(rel(bundle_md))
        bundle_block = parsed.get("bundle")
        if not isinstance(bundle_block, dict):
            problems.append(f"{rel(bundle_md)}: frontmatter has no 'bundle:' mapping")
        else:
            for key in ("name", "version"):
                if not bundle_block.get(key):
                    problems.append(
                        f"{rel(bundle_md)}: frontmatter is missing 'bundle.{key}'"
                    )

        includes = parsed.get("includes") or []
        if not isinstance(includes, list):
            problems.append(
                f"{rel(bundle_md)}: 'includes:' must be a list, got {type(includes).__name__}"
            )
            includes = []
        if not includes:
            problems.append(
                f"{rel(bundle_md)}: 'includes:' is empty -- nothing was actually checked"
            )
        for entry in includes:
            if not isinstance(entry, str) and not isinstance(entry, dict):
                problems.append(
                    f"{rel(bundle_md)}: includes entry is not a string or mapping: {entry!r}"
                )
                continue
            # Entries are either a bare string or a single-key mapping such as
            # `- bundle: reality-check:behaviors/reality-check`.
            if isinstance(entry, dict):
                values = [v for v in entry.values() if isinstance(v, str)]
                if len(values) != 1:
                    problems.append(
                        f"{rel(bundle_md)}: includes entry is not a single string value: {entry!r}"
                    )
                    continue
                target_spec = values[0]
            else:
                target_spec = entry
            # Remote includes (git+https://..., @bundle refs) are not on disk.
            if target_spec.startswith(("git+", "http://", "https://")):
                continue
            if resolve_include(target_spec) is None:
                problems.append(
                    f"{rel(bundle_md)}: includes '{target_spec}' -> no such file in this repo"
                )


# --- 3: every behaviour file the bundle ships -------------------------------


def parse_all(directory: str, pattern: str) -> int:
    """Parse every match as a YAML mapping; return how many files matched."""
    root = REPO_ROOT / directory
    if not root.is_dir():
        problems.append(f"{directory}/ directory is missing")
        return 0

    matches = sorted(root.glob(pattern))
    if not matches:
        # An empty glob is a failure. See the module docstring.
        problems.append(
            f"{directory}/{pattern} matched NO files -- nothing was actually checked"
        )
        return 0

    for path in matches:
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{rel(path)}: not valid YAML: {exc}")
            continue
        if not isinstance(loaded, dict):
            problems.append(
                f"{rel(path)}: expected a YAML mapping, got {type(loaded).__name__}"
            )
            continue
        checked.append(rel(path))
    return len(matches)


behaviors_count = parse_all("behaviors", "*.yaml")


# --- report ------------------------------------------------------------------

print(f"bundle.md frontmatter : {'ok' if bundle_md.is_file() else 'MISSING'}")
print(f"behaviors/*.yaml      : {behaviors_count} file(s)")
print(f"parsed cleanly        : {len(checked)} file(s)")

if problems:
    print(f"\nFAIL -- {len(problems)} problem(s):", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    sys.exit(1)

print("\nOK -- bundle structure checks passed")
