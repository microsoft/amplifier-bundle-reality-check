# Copyright (c) Microsoft. All rights reserved.

"""Guards the shape of every agent's ``tools:`` frontmatter declaration.

An agent spawned by ``tool-delegate`` inherits the parent session's tools
MINUS the parent's ``exclude_tools`` list, PLUS whatever tool modules the
agent's OWN frontmatter declares. amplifier-foundation ships
``exclude_tools: [tool-delegate]`` (behaviors/agents.yaml), so an agent whose
job is to delegate keeps ``delegate`` only by naming ``tool-delegate`` itself.

The escape hatch reads that declaration as a MOUNT PLAN::

    agent_tool_modules = [t.get("module") for t in agent_config.get("tools", [])]

Two ways to get it wrong, and neither is caught by "the key is present":

* Wrong SHAPE -- a bare string list (``tools: [terminal_inspector]``) has no
  ``.get``. That line raises ``AttributeError`` and the spawn fails outright.
* Wrong IDENTIFIER -- ``terminal_inspector`` is the TOOL name;
  ``tool-terminal-inspector`` is the MODULE name, and the module name is what
  is matched. A tool name can never match, so the declaration is inert.

This test asserts both, per agent, from the files themselves.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

# Agents that MUST declare a tool module, and which one.
#
# browser-tester: its entire documented workflow is one delegate() call to
#   browser-tester:browser-operator, and it is spawned BY tool-delegate.
# terminal-tester: drives terminal_inspector, whose module is
#   tool-terminal-inspector (amplifier-bundle-terminal-tester).
REQUIRED_MODULES = {
    "browser-tester": "tool-delegate",
    "terminal-tester": "tool-terminal-inspector",
}


def _frontmatter(path: Path) -> dict:
    """Parse the ``---`` fenced YAML frontmatter block of an agent .md file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no frontmatter fence"
    _, block, _ = text.split("---\n", 2)
    parsed = yaml.safe_load(block)
    assert isinstance(parsed, dict), f"{path.name}: frontmatter is not a mapping"
    return parsed


def _agent_files() -> list[Path]:
    files = sorted(AGENTS_DIR.glob("*.md"))
    # An empty glob would make every parametrised check vacuously pass.
    assert files, f"no agent .md files found under {AGENTS_DIR}"
    return files


@pytest.mark.parametrize("path", _agent_files(), ids=lambda p: p.name)
def test_tools_declaration_is_mount_plan_shape(path: Path) -> None:
    """``tools:``, when present, is a list of ``{module: ...}`` entries."""
    tools = _frontmatter(path).get("tools")
    if tools is None:
        return

    assert isinstance(tools, list), (
        f"{path.name}: `tools:` must be a list of mount-plan entries, "
        f"got {type(tools).__name__}"
    )
    for entry in tools:
        assert isinstance(entry, dict), (
            f"{path.name}: `tools:` entry {entry!r} is a bare {type(entry).__name__}. "
            "Use mount-plan shape (`- module: tool-x`) -- the spawn-time filter "
            "calls .get('module') on each entry and a bare string raises "
            "AttributeError, failing the spawn."
        )
        assert "module" in entry, (
            f"{path.name}: `tools:` entry {entry!r} has no `module:` key; "
            "the spawn-time filter matches on the module name."
        )
        assert isinstance(entry["module"], str) and entry["module"], (
            f"{path.name}: `tools:` entry {entry!r} has an empty/non-string module name"
        )


@pytest.mark.parametrize(
    ("agent", "module"), sorted(REQUIRED_MODULES.items()), ids=lambda v: str(v)
)
def test_required_tool_module_is_declared(agent: str, module: str) -> None:
    """The agents that depend on a specific module name it in frontmatter."""
    path = AGENTS_DIR / f"{agent}.md"
    assert path.exists(), f"missing agent file: {path}"

    tools = _frontmatter(path).get("tools") or []
    declared = [t.get("module") for t in tools if isinstance(t, dict)]
    assert module in declared, (
        f"{agent}.md must declare `- module: {module}` under `tools:` "
        f"(declared: {declared}). Without it the module is filtered out at "
        "spawn time by the parent's exclude_tools policy."
    )
