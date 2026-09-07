# yd8m — reality-check agent tool declarations

Work item `model_performance-yd8m`. Two defects found (not fixed) by the earlier
`kp79` catalog-hygiene lane, fixed and demonstrated here. Branch cut from, and
rebased onto, `origin/main` at `0a9b4c0`.

---

## The mechanism, in one paragraph

An agent spawned by `tool-delegate` gets
`final_tools = (inherited − exclude_tools) + explicit`. `exclude_tools` comes from
the parent: amplifier-foundation ships `exclude_tools: [tool-delegate]`
(`behaviors/agents.yaml:31-32`), so no agent it spawns may delegate further. The
`+ explicit` term — the escape hatch — is computed in
`amplifier_app_cli/session_spawner.py` (`spawn_sub_session`):

```python
agent_tool_modules = [t.get("module") for t in agent_config.get("tools", [])]
merged_config = _filter_tools(merged_config, tool_inheritance, agent_tool_modules)
```

Two consequences that a "the key is present" check cannot see:

* It reads the agent's **raw** frontmatter, not the normalised mount plan. A bare
  string has no `.get`, so a bare-string list raises `AttributeError` **and the
  spawn fails outright**.
* It matches on the **module** name. `terminal_inspector` is the TOOL name;
  `tool-terminal-inspector` is the module name. A tool name can never match.

---

## DEFECT 1 — browser-tester arrived unable to delegate · **DONE**

`agents/browser-tester.md` declared no `tools:` at all. Its entire documented
workflow is one `delegate(agent="browser-tester:browser-operator", …)` call, and
it is spawned **by** `tool-delegate` — so `delegate` was filtered out of it every
time, while the agent was still under instruction to emit a PASS/FAIL table. That
is a fabrication risk, not a silent no-op.

**Fix:** `agents/browser-tester.md` frontmatter now declares

```yaml
tools:
  - module: tool-delegate
```

### Evidence — REAL spawns, not frontmatter inspection

The cached bundle the CLI actually mounts
(`~/.amplifier/cache/amplifier-bundle-reality-check-b4a8781d328f9585`) was verified
**byte-identical to `origin/main`** before the fail-before runs, and restored to
`origin/main` afterwards.

| | fail-before (`origin/main`) | pass-after (fixed file installed) |
|---|---|---|
| child mount plan, tool modules | **20**, `tool-delegate` **absent** | **21**, `tool-delegate` **present** |
| agent's own answer to "is `delegate` in your tool list?" | **NO** | **YES** |
| child session id | `0000000000000000-3b26d397595c40d8_reality-check-browser-tester` | `0000000000000000-baaa124fef61491a_reality-check-browser-tester` |

The mount-plan row is read from each child session's own recorded config event
(`events.jsonl` line 0, `data.raw.tools[*].module`) — the session's account of
itself, not a reconstruction.

### Evidence — a real end-to-end delegation to browser-operator

```
root  →  delegate(reality-check:browser-tester)          session 0000000000000000-14ae67e383b54574_reality-check-browser-tester
             (mount plan: 21 tool modules, tool-delegate present)
      →  delegate(browser-tester:browser-operator)       session 14ae67e383b54574-7667decea1bb4823_browser-tester-browser-operator
      →  verbatim reply: PONG
```

Both session directories exist on disk under
`~/.amplifier/projects/-tmp-yd8m-passafter/sessions/`. The nested session id is
prefixed with the parent's id, which is how the chain is checkable after the fact.

**One disclosed variation on that run.** The two-hop chain first failed three
times for a reason unrelated to this fix: routing sent the middle hop to a Gemini
model, and Gemini rejected the nested call with
`400 INVALID_ARGUMENT — Function call is missing a thought_signature in
functionCall parts … function call 'default_api:delegate', position 3`. That error
naming `delegate` is itself proof the tool was present and invoked — before the
fix the agent could not have emitted that call at all. To route the middle hop off
Gemini, `model_role: [vision, general]` was removed from the **cache copy only**
for that one run, so the agent's own `provider_preferences` (anthropic
`claude-opus-*`) won. The `tools:` block under test was unchanged, and the
repository file is unchanged. Three attempts to pin the provider without touching
the file (`provider_preferences` and `model_role` on the delegate call, `-p
anthropic` on the root) were all overridden by role routing; unsetting
`GOOGLE_API_KEY` fails loud by design rather than falling back.

That Gemini failure is an upstream provider-adapter bug, listed in "Filed
elsewhere" below. It is not caused by, and does not affect, this change.

---

## DEFECT 2 — terminal-tester could not be spawned at all · **DONE**

`agents/terminal-tester.md:11` read `tools: [terminal_inspector]` — wrong shape
(bare string list, not mount-plan entries) and wrong identifier (tool name, not
module name).

The work item recorded this as an inert declaration. It is worse than that: the
bare string list makes `[t.get("module") for t in …]` raise, so **every delegation
to `reality-check:terminal-tester` failed outright**, taking the pipeline's entire
`type: cli` lane with it.

**Fail-before, real spawn, verbatim:**

```
Agent delegation failed (AttributeError): 'str' object has no attribute 'get'
```

**Fix:**

```yaml
tools:
  - module: tool-terminal-inspector
```

**Pass-after, real spawn:** the agent spawns (session
`0000000000000000-eddbab79cba64b6b_reality-check-terminal-tester`, 20 tool
modules), reports `terminal_inspector` present **YES**, and — correctly — `delegate`
**NO**, since it does not declare that module and does not need it.

`explicit_modules` now genuinely matches: `['tool-terminal-inspector']`, against a
parent entry of the same module name.

---

## The open design question, answered · **frontmatter, not the behavior file**

`behaviors/reality-check.yaml` grants no tools at all, and the README says the
bundle intentionally ships no runtime. So: do these declarations belong in agent
frontmatter (as done here) or in the behavior file?

**Answer: agent frontmatter. The behavior file cannot express this at all.**

1. **The escape hatch only reads frontmatter.** `_filter_tools`'s `explicit`
   term is built from `agent_config["tools"]` — the agent's own file. A module
   listed in a behavior file is part of the *inherited* set, which is exactly the
   set `exclude_tools` filters. Moving `tool-delegate` into
   `behaviors/reality-check.yaml` would not restore it to browser-tester; it would
   be excluded on the way in, same as before. **There is no behavior-file spelling
   of this fix.**
2. **The declaration is a per-agent fact, not a bundle-wide one.** browser-tester
   needs `delegate`; terminal-tester must NOT have it. A behavior file is
   bundle-scoped and cannot draw that line.
3. **It does not contradict "ships no runtime".** Neither entry carries a
   `source:`, so neither mounts anything new. A source-less entry merges into the
   parent session's existing entry for that module and inherits its pin — it says
   *"do not take this away from me"*, not *"install this"*. The bundle still
   provides no runtime of its own; `behaviors/reality-check.yaml` is unchanged.
4. **Why no `source:`, given the ecosystem precedent both ways.**
   amplifier-bundle-context-intelligence pins
   `tool-delegate` + `source: git+…amplifier-foundation@main#subdirectory=modules/tool-delegate`;
   amplifier-bundle-converge declares source-less `- module: tool-filesystem`. A
   source here would *override* the parent's own pin (child wins on `source:` in
   `merge_module_items`), which would silently defeat a local foundation checkout
   or a pinned ref. Both modules are guaranteed present anyway — browser-tester is
   by construction spawned by `tool-delegate`, and `tool-terminal-inspector` is
   mounted by this bundle's own `behaviors/reality-check.yaml` (via the included
   terminal-tester behavior). The source-less form is both safer and the smaller
   change. **Cost of being wrong:** an agent spawned from a parent that lacks the
   module would carry a source-less, unresolvable entry; adding a `source:` later
   is a one-line change if that ever appears.

---

## Regression guard

`tests/test_agent_frontmatter_tools.py` — parses every `agents/*.md` frontmatter
and asserts (a) any `tools:` is a list of `{module: …}` mappings, and (b) the two
agents that depend on a specific module name it.

* On `origin/main`: **3 failed, 4 passed** — it catches both defects.
* With the fix: **7 passed**; full suite **103 passed**.
* An empty `agents/*.md` glob is a hard failure, so the parametrised checks cannot
  pass vacuously.

`docs/lanes/yd8m-reality-check-tools/verify_spawn_tools.py` reproduces the spawn
computation end-to-end by importing the CLI's own `_load_agent_file_metadata` and
`_filter_tools`. It is a lane artifact, not part of the suite: it imports
`amplifier_app_cli`, which this bundle does not depend on and CI does not install.

```
$ python docs/lanes/yd8m-reality-check-tools/verify_spawn_tools.py

=== browser-tester.md ===
frontmatter tools:      [{'module': 'tool-delegate'}]
explicit_modules:       ['tool-delegate']
tools after spawn:      ['tool-delegate', 'tool-filesystem', 'tool-bash', 'tool-terminal-inspector']
  PASS  tool-delegate survives the spawn filter

=== terminal-tester.md ===
frontmatter tools:      [{'module': 'tool-terminal-inspector'}]
explicit_modules:       ['tool-terminal-inspector']
tools after spawn:      ['tool-filesystem', 'tool-bash', 'tool-terminal-inspector']
  PASS  tool-terminal-inspector survives the spawn filter

ALL PASS
```

On `origin/main` the same script prints `FAIL` for browser-tester and
`*** AttributeError: 'str' object has no attribute 'get' ***` for terminal-tester.

---

## CI

This repo gained CI in `0a9b4c0` (after this lane's branch point; the branch was
rebased onto it). All three jobs were run locally against this change:

| job | result |
|---|---|
| `uvx ruff@0.15.11 check .` | All checks passed! |
| `uvx ruff@0.15.11 format --check .` | 16 files already formatted |
| `pytest tests/ -q` | 103 passed |
| `check_bundle_structure.py` | OK |

---

## Filed elsewhere — not fixed here

1. **`validate-agents` false pass.** It recorded `has_explicit_tools: true` and
   rated `tools: [terminal_inspector]` "good". The structural check measures
   PRESENCE of the key, not VALIDITY of its contents, so it will keep minting
   clean verdicts for declarations that crash the spawn. Out of this lane's scope
   by instruction.
2. **`session_spawner.py` reads raw frontmatter.** `merge_module_lists` already
   normalises bare strings to `{module: …}` (its docstring names
   `terminal_inspector` explicitly), but the escape-hatch line does not use it —
   it reads `agent_config["tools"]` directly and raises. A malformed declaration
   should be reported as malformed, not surface as a bare `AttributeError` from a
   delegation.
3. **Gemini + nested delegate.** A Gemini-routed sub-agent that itself calls
   `delegate` fails with `400 … missing a thought_signature in functionCall parts`.
   Reproduced 3/3 in this lane; the same chain succeeds on anthropic.
