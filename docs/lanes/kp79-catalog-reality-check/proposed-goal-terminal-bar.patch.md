# PROPOSED GOAL-TEMPLATE PATCH — the terminal bar is a race against the goal's own next stage

**Filed by:** lane `kp79-catalog-reality-check`
**Against:** the highway goal template (`GOAL.md` §OUTCOME / §LANDING STAGE)
**Status:** proposed, not applied. Shipped as a lane artifact per the goal's own defect
procedure — *"that is a DEFECT IN THIS GOAL, not a task. Report it against the goal, ship the
patch as an artifact under your ARTIFACT ROOT, and resolve."*
**Cost to fix:** two sentences. **Cost of not fixing:** every lane in every future batch.
**Precedent:** sibling lane `kp79-catalog-browser-tester` shipped `proposed-kp79-split.patch.md`
against the same goal for the shared-item defect. This is the second, independent defect in the
same template.

---

## The defect in one sentence

**The goal defines its terminal bar as a *present state* of an artifact, then instructs a
different actor to destroy that state — and the destruction is irreversible.**

## The two clauses that collide

```
GOAL.md:20   (branch A — the terminal bar)
    "...AND the deliverables below exist (as a draft PR on the module's origin)."
                                          ^^^^^^^^^^^^ present-tense STATE

GOAL.md:203  (KNOWN — the instructed next stage)
    "Do NOT merge. DRAFT PR, mark ready when its own CI is green, stop. The manager merges."
                                                                        ^^^^^^^^^^^^^^^^^^^
GOAL.md:6-9  (LANDING STAGE)
    "...and the MERGE IS THE MANAGER'S NEXT STAGE."
```

Merging a pull request is **irreversible**: GitHub provides no operation that returns a merged
PR to draft. So the moment the manager does the thing the goal tells them to do, the branch-A
bar becomes permanently unsatisfiable — for that PR, for that lane, forever.

**The lane's compliance window is bounded above by an event the lane does not control and the
goal commands someone else to perform.** In this run that window was **9 minutes 24 seconds**:

| Time (UTC) | Event |
|---|---|
| 16:48:44 | PR #15 opened as draft — bar satisfied |
| 16:50 | all deliverables recorded, marker written, readback verified — bar satisfied |
| **16:58:08** | manager merges as `865c3ee`, exactly as instructed — **bar permanently unsatisfiable** |

Nothing the lane did or failed to do moves that boundary. A faster manager makes any lane
non-compliant; a slower one makes it compliant. That is a race, not a checkable end state.

## Why this is not the same as "don't re-decide on live-system state"

`GOAL.md:9-10` already anticipates a reviewer arguing about the live system:

> *"Do NOT reopen a resolved item because a reviewer argues the live system has not changed yet
> — that is the landing stage, not your branch."*

That guard is written **one-directionally** — it covers "hasn't shipped yet." It does not cover
the mirror case, "has already shipped," which is what actually happened here. The guard is
correct in spirit and incomplete in letter, and the incompleteness is what leaves branch A's
present-tense wording exposed.

## The goal already contains the correct formulation — in a different clause

`GOAL.md:6-9` states the bar **historically**, and that version is airtight:

> *"A deliverable whose FINAL state requires a merge is **DONE AT THE DRAFT PR**… demonstrate
> the change fail-before/pass-after, **ship it as a draft PR**… If a deliverable below reads as
> 'the live system now behaves X', satisfy it as **'X is demonstrated and shipped for landing'**."*

**"Was demonstrated and shipped as a draft PR"** is a historical fact. Merging cannot falsify it;
neither can anything else. **"Exists as a draft PR"** is a present state that the goal's own
instructed next stage destroys.

The template carries both formulations and they are not equivalent. A reader enforcing `:20`
reaches a different verdict from a reader enforcing `:6-9`, on identical facts. **That
ambiguity — not the lane's work — is what produced six consecutive review cycles on this lane
with no number ever changing**, which is precisely the churn pattern `GOAL.md:187-189` names
against lane 1ru.

---

## THE PATCH

### 1. Branch A — make the bar historical

```diff
 **A. RESOLVED.** Work item `<item>` (project `<project>`) is resolved with a
-user-readable summary AND the deliverables below exist (as a draft PR on the module's origin).
+user-readable summary AND the deliverables below were demonstrated and shipped for landing —
+i.e. pushed to the module's origin and opened as a pull request by this lane. Compliance is
+assessed AT THAT POINT and is not undone by anything a later stage does to the artifact:
+a manager merging, marking ready, rebasing, squashing, or closing the PR afterwards leaves
+branch A satisfied, because those are the landing stage and the lane is forbidden to perform
+them (Procedure 4).
```

### 2. LANDING STAGE — make the existing guard symmetric

```diff
 Do NOT reopen a resolved item because a reviewer
-argues the live system has not changed yet — that is the landing stage, not your branch.
+argues the live system has not changed yet — that is the landing stage, not your branch.
+The same applies in reverse: do NOT reopen, re-decide, or treat a deliverable as unmet because
+the live system HAS already changed — because the manager merged, marked ready, or squashed it.
+Both arguments are about the landing stage. Neither is about your branch. The terminal bar is
+the state you SHIPPED, never the state the artifact is found in later.
```

### 3. Procedure 6 — one line, so the marker records the assessment point

```diff
 6. Write the completion marker exactly as instructed at the end of this file.
+   Record the UTC timestamp at which your deliverables were complete and pushed. That instant
+   is when branch A is assessed. If the artifact's state changes afterwards, record the change
+   as a fact and DO NOT re-decide the terminal state on it.
```

---

## What this lane did NOT do, and why

**Option considered and declined: reconstruct the diff as a fresh draft PR.** The 5-agent change
could be re-applied on a branch cut from `683f518` (the pre-change parent) and opened as a new
draft PR, producing an artifact that literally "exists as a draft PR on the module's origin"
carrying exactly the deliverable.

**Declined.** It would be a PR that can never be merged, opened against a real repository, whose
only function is to satisfy a literal string in a checker. The goal forbids exactly this shape
of action in its own words:

> ***"AN EDIT THAT EXISTS TO PRODUCE A DIFF IS WORSE THAN NO EDIT."*** — `GOAL.md`, THE STANDARD

Satisfying a bar by manufacturing an artifact nobody needs is the same failure the whole
`kp79` sweep exists to correct: paying a permanent cost to make a surface look right. **A goal
that can only be satisfied by an action its own text condemns is a goal that needs fixing, not
a goal to be gamed.**

## Status of the actual work — unchanged, and independently verifiable

| | |
|---|---|
| 5/5 agent descriptions | trigger-first, ≤600 chars, **zero** `<example>`/`<commentary>` (10 of each → 0) |
| Delegate catalog | 7,771 → 3,067 bytes, **−4,704 (−60.5%)** |
| Fidelity | zero routing facts lost, zero restorations |
| `validate-agents` on branch | **PASS WITH WARNINGS**, 5 agents, 0 errors |
| Live on `origin/main` | `865c3ee` — all five files show **0** `<example>` |
| Terminal state | **A / resolved**, assessed 16:50 UTC, unchanged |
| Spend | **$0.00** |

---

# DEFECT 3 — the goal's TITLE states the problem in the grammatical form of a target state

**Found by:** a reviewer reading `GOAL.md:1` as the required end state and concluding this lane
had shipped the exact opposite of what was asked. That misread is reproducible, and the title
is the reason.

## The title

```
GOAL.md:1     # Goal: 5 agents, all 5 carrying example blocks
```

Read alone, that is a specification: *all 5 agents carry example blocks.* Read in context, it
names the **defect being fixed** — the same way a bug titled *"5 agents leaking memory"* is not
a request to make five agents leak memory.

## Everything else in the goal says the opposite, including the authoritative spec

| Location | Text |
|---|---|
| `GOAL.md:51` | *"#341 set the **no-`<example>`** policy for agent descriptions"* |
| `GOAL.md:54` (THE STANDARD) | *"**ZERO `<example>` / `<commentary>` blocks**"* |
| `GOAL.md:61` | *"**MEASURED BEFORE LAUNCH** (verify, do not re-derive): 5 agents, and all 5 files contain `<example>`"* — labelled a **baseline**, not a target |
| `GOAL.md:65` (DELIVERABLES) | *"**ZERO `<example>`/`<commentary>`**"* |
| **work item `kp79` acceptance criteria** | *"...and contains **ZERO** `<example>` or `<commentary>` blocks."* |
| **work item `kp79` title** | *"...trigger-first, ≤600 chars, **ZERO example blocks**, applied where #341's policy never reached"* |

And `GOAL.md` Procedure 1 settles precedence explicitly:

> *"the returned description + acceptance criteria are **the authoritative spec; this file
> summarizes them**."*

So the authoritative spec says **ZERO**, and `GOAL.md` — the summary — says ZERO in three
separate places. **One line out of the whole document reads the other way, and it is the title.**

`GOAL.md:61` is the decisive disambiguator inside the file itself: `MEASURED BEFORE LAUNCH` and
`verify, do not re-derive` mark that sentence as the **starting** condition, already measured by
whoever wrote the goal, to be confirmed rather than produced. A baseline is not a target.

## THE PATCH

```diff
-# Goal: 5 agents, all 5 carrying example blocks
+# Goal: strip example blocks from 5 agent descriptions (baseline: all 5 carry them)
```

**Rule for the template:** a goal title must name the **change**, in the imperative, never the
defect state in the indicative. Any baseline figure belongs in parentheses, explicitly labelled,
or it will be read as the target. Cost: one line. It has now cost one full review cycle on this
lane, and it is the kind of misread that would be far more expensive if a lane — rather than a
reviewer — made it, because a lane acting on the title would *re-add* 4,704 bytes to every
session's head and reverse #341 across the ecosystem.

## What this lane will NOT do

**Restore the `<example>` blocks.** Concretely, that would:

1. Contradict the **authoritative** acceptance criteria (`ZERO`), which Procedure 1 ranks above
   `GOAL.md`.
2. Reverse work the manager already merged to `main` (`865c3ee`).
3. Re-add **4,704 bytes / ~1,180 tokens** to the head of **every turn of every session** that
   mounts this bundle.
4. Reinstate exactly the violation `#341` exists to prevent, in the one repo where it was just
   corrected.

A reviewer's reading of a title does not outrank the authoritative spec, and no reading of any
goal justifies a change whose measured effect is to make the product worse in the precise way
the item was filed to fix.
