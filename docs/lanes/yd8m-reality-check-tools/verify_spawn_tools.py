#!/usr/bin/env python3
"""Reproduce the spawn-time tool-filtering computation for this bundle's agents.

This script does NOT simulate. It imports the SAME two functions the Amplifier
CLI uses at spawn time and feeds them the SAME inputs:

  1. ``amplifier_foundation.bundle._dataclass._load_agent_file_metadata``
     -- parses the agent .md frontmatter into the agent config dict.
  2. ``amplifier_app_cli.session_spawner._filter_tools``
     -- applies the parent's ``exclude_tools`` policy, honouring the
        agent's own explicitly-declared tool modules.

The one line that joins them is ``session_spawner.py`` (spawn_sub_session)::

    agent_tool_modules = [t.get("module") for t in agent_config.get("tools", [])]
    merged_config = _filter_tools(merged_config, tool_inheritance, agent_tool_modules)

`tool-delegate` ships ``exclude_tools: [tool-delegate]``
(amplifier-foundation/behaviors/agents.yaml), so every agent it spawns loses
`tool-delegate` unless the agent's OWN frontmatter names that module.

Run:  python docs/lanes/yd8m-reality-check-tools/verify_spawn_tools.py
Exit: 0 if every agent's declaration binds, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

from amplifier_app_cli.session_spawner import _filter_tools
from amplifier_foundation.bundle._dataclass import _load_agent_file_metadata

REPO = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO / "agents"

# The parent (host) session mount plan, in the shape a real session carries.
# Only the entries relevant to these two agents are listed.
PARENT_TOOLS = [
    {"module": "tool-delegate", "source": "git+.../modules/tool-delegate"},
    {"module": "tool-filesystem", "source": "git+..."},
    {"module": "tool-bash", "source": "git+..."},
    {
        "module": "tool-terminal-inspector",
        "source": "../modules/tool-terminal-inspector",
    },
]

# amplifier-foundation/behaviors/agents.yaml -> tool-delegate settings
TOOL_INHERITANCE = {"exclude_tools": ["tool-delegate"]}

# agent name -> tool modules it must still have AFTER the spawn filter runs
REQUIRED = {
    "browser-tester": ["tool-delegate"],
    "terminal-tester": ["tool-terminal-inspector"],
}


def check(agent_name: str, required: list[str]) -> bool:
    path = AGENTS_DIR / f"{agent_name}.md"
    agent_config = _load_agent_file_metadata(path, agent_name)
    declared = agent_config.get("tools", [])

    print(f"\n=== {agent_name}.md ===")
    print(f"frontmatter tools:      {declared!r}")

    # Verbatim from session_spawner.py (spawn_sub_session).
    try:
        agent_tool_modules = [t.get("module") for t in declared]
    except AttributeError as exc:
        print(f"explicit_modules:       *** AttributeError: {exc} ***")
        print("  -> a bare string list has no .get('module'); the declaration")
        print("     cannot participate in the escape hatch at all.")
        return False
    print(f"explicit_modules:       {agent_tool_modules!r}")

    merged = _filter_tools(
        {"tools": list(PARENT_TOOLS)}, TOOL_INHERITANCE, agent_tool_modules
    )
    surviving = [t["module"] for t in merged["tools"]]
    print(f"tools after spawn:      {surviving}")

    ok = True
    for module in required:
        present = module in surviving
        print(f"  {'PASS' if present else 'FAIL'}  {module} survives the spawn filter")
        ok = ok and present
    return ok


def main() -> int:
    all_ok = True
    for agent_name, required in REQUIRED.items():
        all_ok = check(agent_name, required) and all_ok
    print("\n" + ("ALL PASS" if all_ok else "FAILURES PRESENT"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
