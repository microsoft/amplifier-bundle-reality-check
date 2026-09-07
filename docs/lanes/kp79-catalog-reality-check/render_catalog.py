#!/usr/bin/env python3
"""Render this bundle's contribution to the delegate agent catalog.

Reproduces tool-delegate's own rendering, verbatim:

    amplifier_module_tool_delegate/__init__.py:936-941
        agent_desc = "\n".join(
            f"  - {a['name']}: {a.get('description', 'No description')}"
            for a in agents_list
        )

with agents sorted by namespaced name (_get_agent_list, :1121) and the
description taken from the agent's `meta.description` frontmatter value.

Usage: render_catalog.py <bundle-root> [namespace]
"""

import sys
from pathlib import Path

import yaml

NS_DEFAULT = "reality-check"


def load_desc(path: Path) -> tuple[str, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise SystemExit(f"{path}: no frontmatter")
    fm = text.split("---\n", 2)[1]
    meta = yaml.safe_load(fm)["meta"]
    return meta["name"], meta["description"]


def main() -> int:
    root = Path(sys.argv[1])
    ns = sys.argv[2] if len(sys.argv) > 2 else NS_DEFAULT
    entries = []
    for f in sorted((root / "agents").glob("*.md")):
        name, desc = load_desc(f)
        entries.append((f"{ns}:{name}", desc))
    entries.sort(key=lambda e: e[0])
    lines = [f"  - {n}: {d}" for n, d in entries]
    block = "\n".join(lines)
    sys.stdout.write(block)
    total = 0
    print("\n\n===== PER-AGENT CATALOG BYTES =====", file=sys.stderr)
    for n, d in entries:
        b = len(f"  - {n}: {d}".encode())
        total += b
        print(f"{n:42s} desc_chars={len(d):5d}  catalog_bytes={b:5d}", file=sys.stderr)
    print(
        f"{'JOIN newlines (n-1)':42s} {'':19s} catalog_bytes={len(entries) - 1:5d}",
        file=sys.stderr,
    )
    print(
        f"{'TOTAL CATALOG BLOCK':42s} {'':19s} catalog_bytes={len(block.encode()):5d}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
