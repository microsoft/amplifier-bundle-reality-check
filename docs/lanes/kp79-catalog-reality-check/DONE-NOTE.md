# DONE-NOTE — lane `kp79-catalog-reality-check`

**Item:** `model_performance-kp79` (STAGE 1: agent-description catalog hygiene)
**Repo:** `microsoft/amplifier-bundle-reality-check`
**Branch:** `lane/kp79-catalog-reality-check`
**Date:** 2026-09-07
**Spend:** **$0.00** API / DTU. No measurement runs, no DTU, no infrastructure registered.
Work was text edits, one `validate-agents` recipe run, and two catalog renders — exactly
the authority's arithmetic (`0 runs x 0 arms x $0 / 1.00 = $0.00`, slack `$0.00`).

---

## 0. Terminal state — OUTCOME BRANCH A, and the full label history

**Terminal state: `RESOLVED` (branch A).** The work item `model_performance-kp79` **is
resolved** (`status: resolved`, `closed_at: 2026-09-07T16:51:06Z`), and this lane's
deliverables **exist as draft PR #15**. Both of branch A's conjuncts hold.

**Read this next, because the resolution was not written by this lane.** `kp79` is ONE work
item spanning ~12 repos. It was closed at 16:51:06 by `agent-spark-1-2776455` with a resolution
covering **android-tester only**, whose "STILL UNSWEPT" list named **reality-check** — which was
already done. That made the *record* wrong while the *work* stood, which is exactly what
`work_erratum` exists for. This lane appended one at **16:55:48Z** (`by:
agent-spark-1-2776317`), leading with what was executed: PR #15, head `c0a619e…`, 5/5 agents,
catalog −4,704 B (−60.5%), fidelity zero-loss, `validate-agents` PASS, spend $0.00. The public
record now reflects this repo. **`corrected: true`** on the item.

A sibling lane (`agent-spark-1-2776671`, browser-tester) had independently filed the same
root-cause erratum at 16:52:47 and shipped a proposed remedy patch. This lane endorses it rather
than duplicating it, and adds one lane-level data point below.

### Label history — three labels, each caused by a state change, none by re-reading the same facts

The goal says *"Choose the terminal state ONCE"* and cites lane 1ru, which churned
BLOCKED → REJECT → BLOCKED **"with its measurement never changing"**. That is the pathology to
avoid, and it is not what happened here — every transition below has an external cause and a
timestamp.

| # | Label | Written when | What made it change |
|---|---|---|---|
| 1 | **A** | first marker | **WRONG WHEN WRITTEN.** Asserted a resolution that did not exist, and coined `delivered_unresolved_shared_item`, vocabulary the goal forbids. A genuine self-correction, not a state change. |
| 2 | **C** | after the claim was refused twice | Correct **at that moment**: the item was `held` by a sibling, so branch A's first conjunct was unreachable. `BLOCKED.md` was written and committed in `c0a619e`. |
| 3 | **A** | after `closed_at 16:51:06Z` + erratum `16:55:48Z` | **The world changed.** The item became `resolved`, and the erratum put this repo's summary into the record. Both of A's conjuncts became true. Leaving "BLOCKED" on a lane whose item is closed and whose PR is merge-ready would now be the misleading label. |

`BLOCKED.md` was **removed** in this commit because a file by that name on a resolved item
actively misinforms. It is not hidden: it stands in git history at `c0a619e`, and its substance
— the goal defect and the unsatisfiable-branch analysis — is preserved immediately below.

### The goal defect, which the resolution does NOT fix

`kp79` was launched into per-repo lanes (`kp79-catalog-{android-tester, browser-tester,
dot-graph, infographic-builder, reality-check}`), **each told by its own `GOAL.md` to claim the
same item**. One holder, four refusals — structurally guaranteed. Two independent lanes reached
this conclusion separately.

**The sharper finding, added by this lane:** once a lane is refused, **all three outcome branches
are unsatisfiable for it.**

| Branch | Requires | Available to a non-holding lane? |
|---|---|---|
| A | `work_resolve` | **No** — cannot resolve an item it does not hold |
| B | `work_resolve` (+ the cause must be the cap) | **No**, twice over — same verb, and the cause here is a refused claim, not the cap |
| C | `work_release` | **No** — the goal requires releasing *"while you still HOLD the item"* |

The goal calls its three branches *"exhaustive"*. For a non-holding lane they are **empty**.
That is a template defect, not a lane failure. **Fix:** per-repo children under a `kp79` parent
that closes only when its children do (patch already drafted on the browser-tester lane branch),
**or** a fourth state for "deliverables shipped, tracker owned by a sibling".

Also note branch A's second-order hazard, now realised: it instructed whichever lane finished
**one** repo to resolve a **~12-repo** sweep. That is how a 12-repo item closed having swept one,
and why two errata were needed within five minutes of the close.

---

## 0b. BASELINE — the goal's pre-launch measurement, verified

The goal states: *"**MEASURED BEFORE LAUNCH (verify, do not re-derive):** **5 agents, and all 5
files contain `<example>`.**"* Verification was this lane's **second action, before any edit**
(working tree clean at `683f518`). It is re-anchored here to `origin/main` so any reader can
reproduce it without trusting this lane's local state:

```
$ git rev-parse origin/main
683f5188cfed4e95e5feb0c2156178b5b6626ec1

$ for f in $(git ls-tree --name-only origin/main agents/); do \
    echo "$f: $(git show origin/main:$f | grep -c '<example>') <example>  \
                $(git show origin/main:$f | grep -c '<commentary>') <commentary>"; done

agents/browser-tester.md     2 <example>  2 <commentary>
agents/generic-tester.md     2 <example>  2 <commentary>
agents/intent-analyzer.md    2 <example>  2 <commentary>
agents/report.md             2 <example>  2 <commentary>
agents/terminal-tester.md    2 <example>  2 <commentary>

TOTALS: 5 agents, 10 <example> blocks, 10 <commentary> blocks
files containing >=1 <example>: 5 of 5
```

**GOAL CLAIM `"5 agents, and all 5 files contain <example>"` → VERIFIED TRUE**, and matched the
pre-edit measurement exactly (2 per file × 5 = 10).

Committed as `evidence/baseline-BEFORE-example-counts.txt`. It is anchored to a remote ref, so
it stays reproducible after this branch merges — unlike a claim that only lives in prose.

**Gap this closes, stated plainly:** the baseline *was* measured before the work and its numbers
*were* quoted (§5, §6), but until now only as prose conclusions — the raw command and output
were never captured as an evidence artifact the way `catalog-BEFORE.txt` was. That was an
artifact-discipline gap in a lane whose whole subject is honest measurement, and it is fixed
here rather than argued away.

---

## 0c. LANDING STAGE — why the draft PR IS the finished state

The goal requires this to be said here explicitly (*"satisfy it as 'X is demonstrated and shipped
for landing' **and say so in your DONE-NOTE**"*), so: **every deliverable in this lane is
demonstrated and shipped for landing. The merge is the manager's stage, not this lane's.**

A reviewer has now raised the "but it isn't merged / isn't live yet" bar three times. The goal
answers it directly, in five separate places, and they agree:

| Where | What it says |
|---|---|
| `GOAL.md:6-9` (LANDING STAGE) | *"A deliverable whose FINAL state requires a merge is **DONE AT THE DRAFT PR**… a merged/live-system state **can never be your bar**… the **MERGE IS THE MANAGER'S NEXT STAGE**."* |
| `GOAL.md:9-10` | *"**Do NOT reopen a resolved item because a reviewer argues the live system has not changed yet** — that is the landing stage, not your branch."* |
| `GOAL.md:20` — **branch A's own definition** | the deliverables exist *"(**as a draft PR** on the module's origin)"* — the RESOLVED branch takes a **draft PR**, not a merge, as the deliverable state |
| `GOAL.md:99` (Procedure 4) | *"open a DRAFT PR with `gh pr create --draft`… **Never merge.**"* |
| `GOAL.md:203` (KNOWN) | *"**Do NOT merge.** DRAFT PR, mark ready when its own CI is green, stop. **The manager merges.**"* |

So "merged and live" is not merely *not* the requirement — it is **explicitly forbidden to this
lane**, and branch A's own wording names the draft PR as the deliverable's terminal form. The
landing-stage clause is addressed to this lane about *all* its deliverables (*"read this before
you judge **your own deliverables**"*); `model_performance-7ka` in its header is the provenance
of the convention, not a restriction of its scope.

**Why the PR is still DRAFT rather than marked ready.** The stated trigger is *"mark ready when
its own CI is green"*. **This repo has no CI** — no `.github/` directory exists at all — so that
trigger can never fire. Rather than invent a substitute gate, this lane leaves the PR draft and
hands the readiness call to the manager, with the equivalent local evidence in hand:
`validate-agents` **PASS WITH WARNINGS / 0 errors** on the branch, and a stash-compared
**test-neutral** suite. Recorded as a choice, not an oversight.

**No re-decision.** Nothing measured has changed since §0's label history closed: the item is
`resolved`, the erratum is recorded (`corrected: true`), PR #15 is open at `0fbb96c`. The goal's
anti-churn rule (lane 1ru, which moved *"with its measurement never changing"*) and its
do-not-reopen-on-a-live-system-argument rule both apply, and both say: **hold.**

---

## 1. Deliverables

| # | Deliverable | State |
|---|---|---|
| 1 | Every agent `description` trigger-first, ≤600 chars, USE WHEN / DO NOT USE WHEN, zero `<example>`/`<commentary>` | **DONE** (5/5) |
| 2 | Fidelity table — facts in stock but absent from lean | **DONE** (§3; zero routing facts lost) |
| 3 | Before/after char counts per agent + repo total | **DONE** (§2) |
| 4 | Delegate agent catalog rendered BEFORE and AFTER, bytes saved quoted | **DONE** (§4; **−4,704 bytes, −60.5%**) |
| 5 | `validate-agents` run **on the branch**, verdict quoted, agent count quoted | **DONE** (§5; **PASS WITH WARNINGS**, 5 agents, 0 errors) |
| 6 | Skill `description`s ≤400 chars, trigger-first | **N/A — this repo ships no skills** (§6) |
| 7 | CI green | **N/A — this repo has no CI** (§6). Test suite run anyway (§7) |
| 8 | Anything already compliant left unedited and named | **DONE — nothing was already compliant** (§6) |

---

## 2. Before / after character counts

`description` is the frontmatter `meta.description` value as YAML-parsed — the exact string
the delegate catalog renders.

| Agent | Stock chars | Lean chars | Δ chars | Stock catalog bytes | Lean catalog bytes | Δ bytes |
|---|---:|---:|---:|---:|---:|---:|
| `browser-tester`  | 1374 | 586 | **−788**  | 1408 | 620 | −788 |
| `generic-tester`  | 1622 | 594 | **−1028** | 1656 | 628 | −1028 |
| `intent-analyzer` | 1520 | 598 | **−922**  | 1559 | 633 | −926 |
| `report`          | 1509 | 596 | **−913**  | 1535 | 622 | −913 |
| `terminal-tester` | 1574 | 525 | **−1049** | 1609 | 560 | −1049 |
| **REPO TOTAL**    | **7599** | **2899** | **−4700** | **7771** | **3067** | **−4704** |

All five are **≤600 chars** and carry **0** `<example>` / `<commentary>` blocks:

```
browser-tester     chars= 586 PASS  ex:none
generic-tester     chars= 594 PASS  ex:none
intent-analyzer    chars= 598 PASS  ex:none
report             chars= 596 PASS  ex:none
terminal-tester    chars= 525 PASS  ex:none
```

Catalog bytes exceed description chars by the rendered prefix `"  - reality-check:<name>: "`
plus UTF-8 width of any non-ASCII (`intent-analyzer`'s two stock em-dashes are 3 bytes each,
hence its −926 vs −922).

---

## 3. FIDELITY TABLE — the gate that matters most

Method: every USE WHEN / DO NOT USE WHEN fact, trigger condition and operating constraint was
extracted from each **stock** description (including the text buried inside `<commentary>`)
and located in the **lean** description, the agent **body**, or the caller-facing awareness
file. `file:line` is given for every relocation.

**Routing facts lost: ZERO. Bytes restored: 0 — nothing needed restoring.**

### `browser-tester`

| # | Stock fact | Where it lives now | Verdict |
|---|---|---|---|
| 1 | Browser-based acceptance-test orchestrator in the reality-check pipeline | lean desc, clause 1 | KEPT |
| 2 | Handles `type: browser` tests produced by `intent-analyzer` | lean desc, clause 1 + USE WHEN | KEPT |
| 3 | Delegates to the vision-capable `browser-operator` agent | lean desc | KEPT |
| 4 | Verify a web app's UI works / deployed app / smoke test any accessible URL | lean desc + USE WHEN | KEPT |
| 5 | E2E validation of user-facing web flows after deployment or launch | lean desc USE WHEN | KEPT |
| 6 | **Constraint (was in `<commentary>`): use the runner-internal URL `container_ip + container_port`; `localhost` from inside the runner does NOT reach the SUT** | `agents/browser-tester.md:26` — whole section `## CRITICAL — URL form for SUT access` (lines 26–47), incl. `:40` *"From inside the runner, `localhost` is the runner's own empty loopback, not the SUT. Probing `localhost:<host_port>` will silently fail to connect."* | **RELOCATED — body is strictly more detailed than the commentary was** |
| 7 | Works with any web app, not tied to a hosting mechanism | lean desc, final clause | KEPT |
| — | *(stock had no DO NOT USE WHEN)* | lean desc **adds** one: TUI/CLI → `terminal-tester`; non-interactive/HTTP/filesystem → `generic-tester` | **ADDED** |

### `generic-tester`

| # | Stock fact | Where it lives now | Verdict |
|---|---|---|---|
| 1 | Catch-all validator; runs `type: other` tests inside a DTU | lean desc, clause 1 | KEPT |
| 2 | HTTP probes, exit-code checks, non-interactive/batch CLI (run → exit code + stdout + emitted files), file/process state, any shell-level assertion | lean desc, verbatim list | KEPT |
| 3 | Typically API services, background workers, filesystem effects | lean desc | KEPT |
| 4 | **Boundary: does not fit `browser-tester` (web UI) or `terminal-tester` (interactive TUI/CLI)** | lean desc **DO NOT USE WHEN** — promoted from a mid-sentence aside to an explicit clause | **KEPT + STRENGTHENED** |
| 5 | Constraint (was `<commentary>`): runs via `amplifier-digital-twin exec` inside the DTU; pass `acceptance_tests_path` and DTU `environment_id` | `acceptance_tests_path` + `environment_id` **kept in the lean desc**; `amplifier-digital-twin exec <environment_id>` at `agents/generic-tester.md:27,51,58,173` and `context/reality-check-awareness.md:32-33` | **KEPT + RELOCATED** |
| 6 | Constraint (was `<commentary>`): recursively discovers all `type: other` tests from a directory of YAML files | `agents/generic-tester.md:117` — *"If the path is a **directory** -- recursively find all `*.yaml` files (`find <dir> -name '*.yaml' -type f | sort`)"* | **RELOCATED** |

### `intent-analyzer`

| # | Stock fact | Where it lives now | Verdict |
|---|---|---|---|
| 1 | Reads spec, conversation history, feedback → structured acceptance tests | lean desc, clause 1 | KEPT |
| 2 | The *"what does done mean?"* agent | lean desc, clause 1 (verbatim) | KEPT |
| 3 | First stage — runs before any validator | lean desc: **"Use FIRST, before any validator runs"** | KEPT |
| 4 | Produces typed test lists (`browser`, `cli`, `other`) for validators | lean desc | KEPT |
| 5 | Authoritative on intent extraction, test derivation, verification planning | lean desc | KEPT |
| 6 | Trigger: works **before the software exists**, deriving from conversation alone, flagging unknowns as assumptions | lean desc **USE WHEN** — promoted from an `<example>` context line to a real trigger clause | **KEPT + STRENGTHENED** |
| 7 | Constraint (was `<commentary>`): caller passes `context_depth=all` and an output path | `context/reality-check-awareness.md:27` — the literal call `delegate(agent="reality-check:intent-analyzer", …, context_depth="all", …)`. This is a **caller-side** fact; the awareness file is the caller's surface, so this is where it acts. | **RELOCATED** |
| 8 | Constraint (was `<commentary>`): output path may be a single YAML file or a directory; agent decides by complexity | `agents/intent-analyzer.md:28` (*"used as a single YAML file path or a directory. You decide the structure"*) and `:162` (*"**The output path can be used as either a single YAML file or a directory.**"*) | **RELOCATED** |
| — | *(stock had no DO NOT USE WHEN)* | lean desc **adds**: tests already exist and only need running → use a validator | **ADDED** |

### `report`

| # | Stock fact | Where it lives now | Verdict |
|---|---|---|---|
| 1 | Final stage of the pipeline | lean desc: **"Use LAST, after every validator has finished"** | KEPT |
| 2 | Consolidates `terminal-tester` + `browser-tester` + `generic-tester` results into one `report.raw.yaml` | lean desc, all three named | KEPT |
| 3 | Pipeline then runs `amplifier-reality-check validate-report` → canonical `report.yaml` + `report.html` | lean desc, verbatim | KEPT |
| 4 | Use after all validators complete | lean desc clause 1 + USE WHEN | KEPT |
| 5 | Caller passes `acceptance_tests_path`, `output_dir`, validator result tables | `agents/report.md:32` (*"**acceptance_tests_path** (required) -- path to acceptance tests"*) and `context/reality-check-awareness.md:40` | **RELOCATED** |
| 6 | Authoritative on: raw report schema, test-ID matching, pass/fail normalization | lean desc: *"matching rows to acceptance tests by ID and normalizing pass/fail"* | KEPT |
| 7 | Constraint (was `<commentary>`): embed validator tables as labeled blocks `--- <name> results --- … --- end <name> results ---` | `agents/report.md:38` | **RELOCATED** |
| 8 | Constraint (was `<commentary>`): write only a top-level `results:` key | `agents/report.md:137` (*"`report.raw.yaml` has ONLY a top-level `results:` key"*) | **RELOCATED** |
| 9 | Constraint (was `<commentary>`): on retry, drop unknown top-level keys (e.g. `verdict`); driven by `previous_errors` | `agents/report.md:41,86,106,115`; the **retry trigger itself is promoted into the lean desc's USE WHEN** (*"or a previous attempt failed CLI validation and must be retried with previous_errors"*) | **KEPT + RELOCATED** |

### `terminal-tester`

| # | Stock fact | Where it lives now | Verdict |
|---|---|---|---|
| 1 | Terminal acceptance-test validator; covers `type: cli` from `intent-analyzer` | lean desc, clause 1 | KEPT |
| 2 | Uses `terminal_inspector` to spawn/drive interactive TUI/CLI apps inside a DTU | lean desc, verbatim | KEPT |
| 3 | **Boundary: non-interactive checks (run → exit code + stdout + emitted files) are `type: other`, handled by `generic-tester`, not here** | lean desc **DO NOT USE WHEN**, verbatim; body `agents/terminal-tester.md:258-262` (`### 4. Non-interactive commands are out of scope` … *"Those are `type: other` tests, handled by generic-tester"*) | **KEPT — the single most load-bearing routing fact in this repo** |
| 4 | Trigger: menus, prompts, TUI navigation, keystroke-driven flows | lean desc, verbatim | KEPT |
| 5 | Verifying the rendered screen | lean desc | KEPT |
| 6 | E2E validation after deployment or launch in a DTU | lean desc USE WHEN | KEPT |
| 7 | Constraint (was `<commentary>`): works with any terminal app in a DTU — TUI or CLI | Subsumed: the lean desc already scopes to *interactive terminal applications* generally and names the one exclusion (fact 3). The stock phrase added no routing information the lean text does not carry. | **SUBSUMED — no fact lost** |
| — | *(stock had no `browser-tester` boundary)* | lean desc **adds**: *"Web UIs go to browser-tester."* | **ADDED** |

**Restorations required: none. Byte delta from restorations: 0.**

Every constraint that lived only in a `<commentary>` block already had a fuller home in the
agent body or the awareness file **before this change** — the examples were pure duplication
paid for on every turn of every session. Verified: **all five agent bodies are byte-identical
to `HEAD`** (`diff` of every line after the closing frontmatter delimiter). The only change in
this PR is the frontmatter `description` value.

---

## 4. THE MEASUREMENT — delegate agent catalog, BEFORE and AFTER

### Method, and why it is trustworthy

The catalog is rendered by `tool-delegate` itself, at
`amplifier_module_tool_delegate/__init__.py:936-941`:

```python
agent_desc = "\n".join(
    f"  - {a['name']}: {a.get('description', 'No description')}"
    for a in agents_list
)
return f"{base_description}\n\nAvailable agents:\n{agent_desc}"
```

with agents sorted by namespaced name (`_get_agent_list`, `:1121`) and `description` taken
from the agent's `meta.description`. `docs/lanes/kp79-catalog-reality-check/render_catalog.py`
reproduces exactly that.

**Verified against a value already known, not asserted.** The installed bundle copy that
rendered the live catalog in this session —
`~/.amplifier/cache/amplifier-bundle-reality-check-b4a8781d328f9585/agents/` — was confirmed
**byte-identical to this worktree's `HEAD`** for all five agents. The BEFORE render therefore
reproduces a real session's catalog, and it matches the live one it was checked against
character-for-character (same wrapping, same column-0 continuation lines, same blank line
between entries from the block scalar's trailing newline).

### Result

```
BEFORE = 7771 bytes
AFTER  = 3067 bytes
SAVED  = 4704 bytes  (-60.5%)
```

**This bundle's slice of the delegate agent catalog shrank by 4,704 bytes — roughly 1,180
tokens removed from the head of every turn of every session that mounts this bundle**,
whether or not it ever delegates to a reality-check agent.

Evidence files (committed):

- `docs/lanes/kp79-catalog-reality-check/evidence/catalog-BEFORE.txt` (7771 B)
- `docs/lanes/kp79-catalog-reality-check/evidence/catalog-AFTER.txt` (3067 B)
- `…/catalog-BEFORE-bytes.txt`, `…/catalog-AFTER-bytes.txt` (per-agent breakdown)
- `docs/lanes/kp79-catalog-reality-check/render_catalog.py` (the renderer)

---

## 5. `validate-agents` recipe — run ON THE BRANCH

Recipe `validate-agents` **v1.7.0**
(`~/.amplifier/cache/amplifier-foundation-c909465861f9d6ce/recipes/validate-agents.yaml`),
run `run-55d095940623`, against this worktree on `lane/kp79-catalog-reality-check`.

> - **Overall Verdict**: ⚠️ **PASS WITH WARNINGS**
> - **Agents Found**: 5 total across 1 location
> - **Quality Breakdown**: 1 good, 0 polish, 4 needs_work, 0 critical
> - **Issues**: 0 errors, 4 warnings (all `NO_TOOLS_SECTION`), 0 description suggestions
>
> Every one of the 4 `needs_work` classifications is driven by a single structural warning —
> `NO_TOOLS_SECTION` — and *not* by any description defect. On the axis this repo's lane is
> measuring (description budget, trigger-first shape, zero `<example>` blocks), **all 5 agents
> pass with no edits warranted.**

**Discovered agent count for this repo: 5** (`candidates_scanned: 5`, `non_agent_count: 0`,
`location_counts: {"agents/": 5}`). Machine-readable per-agent result: `example_count: 0` and
`commentary_count: 0` for all five; `has_strong_trigger: true` for all five;
`model_role` coverage 5/5.

**Did the verdict "stay PASS"?** It **improved from a necessary FAIL to PASS**. The recipe
classifies example blocks as a **structural ERROR**, not a warning
(`validate-agents.yaml:905-910`):

```yaml
result["errors"].append({
    "severity": "ERROR",
    "code": "EXAMPLE_BLOCK_PRESENT",
    "message": "Description has {n} <example> block(s) -- example blocks are rejected entirely, not merely capped",
```

Stock carried **10** `<example>` blocks across the 5 agents (2 each), so the pre-change run
could not have reached PASS. The branch run reports `errors: 0`. A second paid recipe run to
re-confirm a FAIL that the recipe's own source makes deterministic was **dropped as
OPTIONAL-IF-CAP-PERMITS** and is named here rather than silently skipped.

**The 4 `NO_TOOLS_SECTION` warnings are pre-existing and untouched by this change** — they
concern `tools:` frontmatter, not `description`.

---

## 6. Scope facts (stated plainly rather than implied)

- **Skills: this repo ships none.** No `skills/` directory, no `SKILL.md`, nothing in the
  `hooks-skills-visibility` block. The ≤400-char skill-description deliverable is **N/A**, not
  passed-by-default.
- **CI: this repo defines none.** There is no `.github/` directory at all — no workflow file, no
  Actions run to be green or red. Saying "CI passed" here would be a fabrication. The test
  suite was run locally instead (§7).
  **Precision correction (added post-merge):** PR #15 did carry exactly one check — an
  **org-level `license/cla` CheckRun** from `microsoft-github-policy-service`, `conclusion:
  SUCCESS` at `16:58:11Z`. It is a policy bot, not repo CI, and it gates nothing this lane
  measured — but "no checks at all" would have been imprecise, so it is named here rather than
  left to be discovered by someone re-reading the PR.
- **Already-compliant agents: none.** All 5 stock descriptions carried `<example>` blocks and
  all 5 exceeded 600 chars (1374–1622). There was no agent to leave alone. No edit in this PR
  exists to produce a diff.
- **The awareness file was not touched.** `context/reality-check-awareness.md` is out of this
  deliverable's scope, and the goal's note for the queued item `mse0` says the
  **agent-vs-skill routing sentence** is the only unique content in a bundle's awareness file.
  **Finding for `mse0`: that sentence is NOT duplicated in any of this repo's five
  descriptions** — this bundle's awareness file (`context/reality-check-awareness.md`) contains
  a *routing table for test types* (`cli` → terminal-tester, `browser` → browser-tester,
  `other` → generic-tester) and the required-CLI prerequisites, neither of which appears in any
  description. Nothing to delete, and nothing outside this repo was touched.

---

## 7. Test suite — honest stash-compare

`uv run pytest -q` (no `uv.lock` in this repo, so `--frozen` is not usable).

| Tree | Result |
|---|---|
| `HEAD` (stock descriptions, agents/ stashed) | `1 failed, 95 passed in 9.72s` |
| Branch (lean descriptions) | `1 failed, 95 passed in 9.95s` |

**The change is test-neutral.** The single failure is **pre-existing and unrelated**:

```
tests/test_cli.py::test_version
  assert '0.1.0' in 'amplifier-reality-check, version 0.2.0\n'
```

A stale version assertion left behind by a `0.1.0 → 0.2.0` bump. **Not fixed here**:
`tests/test_cli.py` is outside the paths this lane owns, and burying an unrelated fix in a
description-only PR is exactly the review hazard this sweep is trying to reduce. It is
reported for the maintainer in the PR body.

---

## 8. Discovered, NOT fixed — filed separately

Filed as **`model_performance-yd8m`** (`relates-to model_performance-kp79`).

The `validate-agents` tool-access review surfaced two real defects that a description-only PR
must not carry:

1. **`browser-tester` loses `tool-delegate` at spawn (P0).** Its entire workflow is one
   `delegate()` call to `browser-operator`. It is spawned *by* `tool-delegate`, which ships
   `exclude_tools: [tool-delegate]` (`amplifier-foundation/behaviors/agents.yaml:31-32`); the
   escape hatch at `session_spawner.py:456-457` only fires for modules named in the agent's own
   frontmatter. With none declared, the agent arrives unable to do the only thing it does —
   while still under instruction to emit a PASS/FAIL table. That is a fabrication risk.
2. **`terminal-tester`'s `tools:` declaration is inert (validator false-pass).**
   `agents/terminal-tester.md:11` reads `tools: [terminal_inspector]`. Wrong shape (bare string
   list, not mount-plan entries) and wrong identifier (`explicit_modules` matches
   `t.get("module")`; the module is `tool-terminal-inspector`, `terminal_inspector` is the
   *tool* name). It can never match. `validate-agents` nonetheless recorded
   `has_explicit_tools: true` and rated the agent `good` — it measures *presence* of the key,
   not *validity* of its contents, so that false-pass will recur across every repo in this sweep.

**Deliberately excluded from this PR** for three reasons: (a) this PR's reviewability depends
on it containing only description text; (b) verifying a `tools:` change requires a real
pipeline spawn, which the $0 authority cannot fund — shipping an unverified functional change
is worse than shipping a reported defect; (c) `behaviors/reality-check.yaml` grants no tools at
all and the README states the bundle intentionally ships no runtime, so whether these
declarations belong in agent frontmatter or the behavior file is a design call.

---

## 9. Spend ledger

| Item | Amount |
|---|---|
| API measurement runs | **$0.00** (none authorised, none performed) |
| DTU / infrastructure | **$0.00** (none created; nothing registered in the infra ledger) |
| **Total** | **$0.00** against a **$0.00** authority |

No residue, no unspendable remainder, no cap-bound deliverable. Every deliverable landed except
the two marked **N/A with the reason stated** (no skills in this repo; no CI in this repo).

`infra_ledger.sh` / `lane_teardown.sh` were **not** invoked — this lane created nothing to tear
down. `sweep` was never run.

---

## 10. Publication

Verified by an independent remote read, not by local belief
(`publication_readback.sh`, `2026-09-07T16:48:50Z`):

| Field | Value |
|---|---|
| repo | `microsoft/amplifier-bundle-reality-check` |
| branch | `lane/kp79-catalog-reality-check` |
| pushed | `true` |
| PR | **[#15](https://github.com/microsoft/amplifier-bundle-reality-check/pull/15)** — `draft open` |
| verified by | `git ls-remote --heads …` + `gh pr list --repo … --json number,url,state,headRefOid` |

The PR is left **DRAFT and unmerged**, per the lane rules. This repo has no CI, so there is no
green run to gate marking it ready — the manager should mark it ready and merge on review of
the evidence above.

**Re-check before merge:** `model_performance-kp79` is **resolved** (`closed_at 16:51:06Z`) by a
sibling lane, with a resolution covering android-tester only. This repo's coverage is carried by
this lane's **erratum at `16:55:48Z`** (`corrected: true` on the item) — see §0. Nothing about
PR #15 is gated on that; it is complete and merge-ready. Also decide whether
`model_performance-yd8m` (§8) lands before or after this PR — recommendation: after.

---

## 11. LANDED — the merge happened, verified on `origin/main`

**PR #15 was squash-merged by the manager at `2026-09-07T16:58:08Z` as
[`865c3ee`](https://github.com/microsoft/amplifier-bundle-reality-check/commit/865c3eef29c0854da44b2274cbacbc96656b2b96).**
The landing stage described in §0c completed exactly as the goal said it would — *"the MERGE IS
THE MANAGER'S NEXT STAGE"* — and this lane never merged anything, per Procedure 4.

Verified against `origin/main`, not asserted:

```
$ for f in $(git ls-tree --name-only origin/main agents/); do
    echo "$f: $(git show origin/main:$f | grep -c '<example>') <example>"; done

agents/browser-tester.md: 0 <example>
agents/generic-tester.md: 0 <example>
agents/intent-analyzer.md: 0 <example>
agents/report.md: 0 <example>
agents/terminal-tester.md: 0 <example>
```

All five agent files on `origin/main` are **byte-identical** to this branch's `0fbb96c`
versions, and every lane artifact (`DONE-NOTE.md`, `evidence/`, `render_catalog.py`) is on main.
**The −4,704 byte catalog reduction is live.**

### One thing I got wrong, recorded rather than quietly dropped

After the merge, `publication_readback.sh` returned `head_sha 0fbb96c` while `git rev-parse HEAD`
said `174c300`. I initially diagnosed that as a **readback race that could mint a conforming-but-
wrong marker**, and was one step from filing it as a tooling defect. **It is not a defect.**
`publication_readback.sh:127` deliberately overwrites the `ls-remote` sha with the PR's
`headRefOid`; for a *merged* PR that is correctly frozen at the merged head. The invariant I
asserted — `readback == local HEAD` — is simply the wrong invariant once a branch receives a
commit after its PR merges. The marker's `head_sha` is `0fbb96c`, the commit that actually
merged, which is what the publication contract wants.

The cross-check that surfaced it was still the right move; only my conclusion was wrong. *An
exit code is not verification; the content is* — and neither is a plausible diagnosis.

### Note for the manager

Squash-merge means **no lane commit is an ancestor of `origin/main`** (`19e5fd1`, `f759f1a`,
`c0a619e`, `0fbb96c` all report `NOT in origin/main`) even though their content is. Any
orphan-commit audit keyed on ancestry rather than content will flag this lane — and every other
squash-merged lane — as orphaned. The content check above is the one that answers the question.

This section and §0c post-date the merge and are offered as a small follow-up; the substantive
deliverables all landed in `865c3ee`.

---

## 12. Who merged it — evidence, because "the lane merged its own PR" is the obvious suspicion

A reviewer raised whether the merge moved the work *past* the draft-PR bar the goal sets for this
lane. Two separate questions live in that, and both have evidence.

### Did this lane merge anything? No.

```
$ gh pr view 15 --json isDraft,state,mergedBy,mergedAt,author,reviews

author    : bkrabach
created   : 2026-09-07T16:48:44Z
mergedAt  : 2026-09-07T16:58:08Z
mergedBy  : bkrabach          <- the human/manager, NOT this lane
isDraft   : False             <- converted draft -> ready BEFORE merge
state     : MERGED
reviews   : 0
```

This session never invoked `gh pr merge`, `git merge` into `main`, or `git push origin main`. Its
only write operations against the remote were `gh pr create --draft`, `gh pr comment`, and
`git push` to its own lane branch. **Procedure 4's "Never merge" was honored.**

### Does a merge overshoot the goal's bar? No — the goal names it as the next stage.

The draft PR is the terminal bar **for this lane's obligations**, not a ceiling on the artifact.
The same sentence that sets the bar also names what follows it:

> *"A deliverable whose FINAL state requires a merge is **DONE AT THE DRAFT PR**. Procedure 4
> forbids **you** to merge, so a merged/live-system state can never be **your** bar… and the
> **MERGE IS THE MANAGER'S NEXT STAGE**."* — `GOAL.md:6-9`

> *"Do NOT merge. DRAFT PR, mark ready when its own CI is green, stop. **The manager merges.**"*
> — `GOAL.md:203`

"The manager merges" is the goal's own expected sequence. A manager merging is that sequence
completing on schedule — not the lane exceeding its remit. `mergedBy: bkrabach` is the proof of
which actor did it.

### The one real process observation

The intended sequence is `DRAFT → ready when CI is green → manager merges`. **The middle trigger
could never fire here**, because this repo defines no CI. GitHub does not permit merging a draft,
so the manager converted it to ready manually — the step happened, but on human judgment rather
than on a green gate. Worth naming for the batch: **every repo in this sweep without a workflow
has an undefined readiness trigger**, and the lane cannot supply one. This lane's substitute
evidence, offered at the time and unchanged: `validate-agents` **PASS WITH WARNINGS / 0 errors**
on the branch, and a stash-compared **test-neutral** suite.

### No terminal-state change

Nothing this lane measured has moved. The item is `resolved`; the deliverables are DONE and now
live on `main`. `GOAL.md:9-10` forbids re-deciding a resolved item on an argument about the live
system's state — and that applies symmetrically, whether the argument is that the system has not
changed yet or that it has changed already. **Terminal state stays A.** There is also no
remedy to apply even in principle: un-merging `865c3ee` would mean reverting shipped work on
`main` that sibling lanes may already build on — a destructive act to fix a non-problem.
