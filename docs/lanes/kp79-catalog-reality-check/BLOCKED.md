# BLOCKED — lane `kp79-catalog-reality-check`

## READ THIS FIRST, BEFORE THE WORD "BLOCKED" MISLEADS YOU

**The deliverables are COMPLETE and shipped in draft PR
[#15](https://github.com/microsoft/amplifier-bundle-reality-check/pull/15). Merge it.**

What is blocked is **one thing only**: this lane cannot `work_resolve`
`model_performance-kp79`, because it never held it and cannot hold it. Nothing about the
engineering work is blocked, incomplete, or unverified.

| | State |
|---|---|
| Agent-description hygiene (5/5) | **DONE** |
| Catalog measurement (−4,704 B, −60.5%) | **DONE** |
| Fidelity audit (zero facts lost) | **DONE** |
| `validate-agents` on branch | **DONE — PASS WITH WARNINGS, 5 agents, 0 errors** |
| Tests (stash-compared) | **DONE — test-neutral** |
| Draft PR pushed + readback-verified | **DONE — PR #15, `f759f1a…`** |
| `work_resolve(model_performance-kp79)` | **BLOCKED — see below** |

---

## Why this file exists, and why branch C is the honest label

OUTCOME branch A requires **two** conjuncts: *"Work item `model_performance-kp79` … is
resolved with a user-readable summary **AND** the deliverables below exist (as a draft PR on
the module's origin)."*

- Second conjunct: **satisfied** — PR #15.
- First conjunct: **unreachable by this lane**, for a reason that is not the cap.

The goal names this exact reason under branch C: *"The outcome is unreachable for a reason
other than the cap — a missing prerequisite, **a refused claim**, a broken dependency, a defect
in another component."*

So the outcome **as the goal defines it** was not fully reached, and the reason is a refused
claim. **Branch C.** An earlier draft of this lane's marker labelled it branch A and coined the
terminal state `delivered_unresolved_shared_item`. That was wrong twice over: it asserted a
resolution that does not exist, and it invented vocabulary the goal explicitly forbids
(*"Do not invent a vocabulary word for it"*). Corrected here, once, to the goal's own word.

## The refusal, verbatim

```
work_claim(project="model_performance", item_id="model_performance-kp79")

  claim model_performance-kp79 as 'agent-spark-1-2776317' failed:
    Error claiming model_performance-kp79: issue already claimed by agent-spark-1-2776455
```

Attempted **twice** — once as the lane's first action, once after all deliverables landed.
Refused identically both times. `work_list` confirms `status: held`,
`holder: agent-spark-1-2776455`.

## Root cause: this is a DEFECT IN THE GOAL, not a lane failure

`model_performance-kp79` is **one work item spanning ~12 repos**, and the batch launched
**four sibling lanes against it simultaneously**:

```
lanes/kp79-catalog-android-tester
lanes/kp79-catalog-browser-tester
lanes/kp79-catalog-dot-graph
lanes/kp79-catalog-reality-check   <- this lane
```

One item, four claimants. **Three of the four are guaranteed to be refused.** The goal's
Procedure step 1 and its three outcome branches were written for a single-repo lane, so they
make 3-of-4 lanes look blocked when all four are doing fine.

**Fix before the next multi-repo sweep:** either give each repo its own work item, or state in
the goal that only the holding lane resolves and siblings report through their `DONE.json`.

## Branch C's own procedure is likewise not fully executable — stated, not hidden

Branch C prescribes `BLOCKED.md` **and** `work_release(id="model_performance-kp79")`, with the
goal adding: *"Release while you still HOLD the item."*

| C's conjunct | State |
|---|---|
| `BLOCKED.md` names the reason | **DONE** — this file |
| `BLOCKED.md` is committed | **DONE** — committed to `lane/kp79-catalog-reality-check` |
| item released via `work_release` | **IMPOSSIBLE** — a lane cannot release an item it never held; `work_release` refuses, mutating nothing |

Neither branch A nor branch C is *cleanly* satisfiable from this state. That is the defect
itself. Branch C is chosen because it is the only branch that does not require this lane to
assert something false about the tracker, and because the goal explicitly lists a refused claim
as a C reason. The one C conjunct that cannot be met is named above rather than quietly skipped.

## What the manager must do

1. **Merge PR #15.** It is complete, evidence-backed, and independently readback-verified. Do
   **not** read "BLOCKED" as "no work landed" — see the table at the top of this file.
2. **Resolve `model_performance-kp79` exactly once**, via whichever lane holds it, with a
   resolution covering all four repos. This lane's contribution is PR #15.
3. **Triage `model_performance-yd8m`** (filed by this lane): `browser-tester` loses
   `tool-delegate` at spawn; `terminal-tester`'s `tools:` declaration is inert. Recommended to
   land after PR #15.
4. **Fix the goal template** per the root-cause section above.

Full evidence, fidelity table and measurements: `DONE-NOTE.md` in this directory.
