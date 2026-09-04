# Copyright (c) Microsoft. All rights reserved.

"""Lint: every shipped recipe with an ``agent:`` reference is schema v2.

A recipe that references an agent but declares no ``schema_version: 2``
dependency manifest is *caller-bound*: its ``agent:`` names resolve from
whatever agent map the calling session happens to have. Run it from a
bundle that does not ship those agents and it fails at the first agent
step with "not found in configuration".

Declaring ``schema_version: 2`` plus a ``dependencies`` block makes the
recipe portable -- agents resolve only from the declared closure.

This test enforces that property for every ``recipes/**/*.yaml`` in the
repo, so a newly added recipe cannot regress it silently.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipes"

#: Recipes deliberately left legacy, each with the reason it cannot be
#: made schema-v2 safe. Keep this empty unless there is a real blocker --
#: e.g. a recipe using ``agent: self``, which has no declarable source
#: (the engine cannot resolve a caller-defined agent from a closure).
#:
#: Maps a repo-relative POSIX path to the reason.
LEGACY_EXEMPT: dict[str, str] = {}


def _recipe_files() -> list[Path]:
    return sorted(RECIPES_DIR.rglob("*.yaml"))


def _references_an_agent(doc: object) -> bool:
    """True if any step anywhere in the document carries an ``agent:`` key."""
    if isinstance(doc, dict):
        if "agent" in doc:
            return True
        return any(_references_an_agent(v) for v in doc.values())
    if isinstance(doc, list):
        return any(_references_an_agent(v) for v in doc)
    return False


def test_recipes_dir_is_not_empty() -> None:
    """Guard: the lint below is vacuous if the glob finds nothing."""
    assert _recipe_files(), f"no recipe YAML found under {RECIPES_DIR}"


@pytest.mark.parametrize("path", _recipe_files(), ids=lambda p: p.name)
def test_agent_referencing_recipe_declares_schema_v2(path: Path) -> None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not _references_an_agent(doc):
        pytest.skip(f"{rel} references no agents; schema v2 not required")

    if rel in LEGACY_EXEMPT:
        assert doc.get("schema_version") is None, (
            f"{rel} is listed in LEGACY_EXEMPT but declares a schema_version. "
            "Remove the exemption."
        )
        return

    assert doc.get("schema_version") == 2, (
        f"{rel} references an agent but does not declare `schema_version: 2`. "
        "Without a dependency manifest its `agent:` names resolve from the "
        "calling session's agent map, so it cannot run from a bundle that "
        "does not already ship them. Add `schema_version: 2` and a "
        "`dependencies:` block, or add the file to LEGACY_EXEMPT with a "
        "reason."
    )

    deps = doc.get("dependencies")
    assert isinstance(deps, list) and deps, (
        f"{rel} declares `schema_version: 2` but no non-empty `dependencies:` "
        "list. A schema-2 recipe resolves agents ONLY from its declared "
        "closure, so an empty closure can supply nothing."
    )
    for entry in deps:
        assert isinstance(entry, dict), (
            f"{rel}: dependency entry is not a mapping: {entry!r}"
        )
        assert entry.get("source"), (
            f"{rel}: dependency entry has no `source`: {entry!r}"
        )
        assert entry.get("kind") in {"bundle", "behavior"}, (
            f"{rel}: dependency `kind` must be 'bundle' or 'behavior', got {entry.get('kind')!r}"
        )


@pytest.mark.parametrize("path", _recipe_files(), ids=lambda p: p.name)
def test_recipe_declares_no_step_agent_config(path: Path) -> None:
    """Schema 2 REJECTS the historical step-level ``agent_config`` field.

    It is never silently retained inert, so a schema-2 recipe carrying one
    fails at parse. Catch it here instead of at run time.
    """
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if doc.get("schema_version") != 2:
        pytest.skip("not a schema-2 recipe")

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            assert "agent_config" not in node, (
                f"{path.relative_to(REPO_ROOT).as_posix()}: step-level "
                "`agent_config` is rejected under schema_version 2."
            )
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(doc)
