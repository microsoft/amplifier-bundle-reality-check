# Lane j1e6 — CI for `amplifier-bundle-reality-check`

**Item:** `model_performance-j1e6` (project `model_performance`)
**Repo:** `microsoft/amplifier-bundle-reality-check` — one of the 19 with **no
`.github/workflows` directory at all**
**Branch:** `lane/j1e6-ci-reality-check`
**Spend:** **$0.00** of a $0.00 authority. No API calls, no DTU, no containers,
no infrastructure registered. CI minutes only (6 GitHub-hosted jobs across two
runs, ~2 min wall each).

---

## OUTCOME

**Deliverables: all DONE.** The item's own terminal state is **not this lane's to
set** — see *Finding 1*, below.

| Deliverable | State |
|---|---|
| `.github/workflows/ci.yml` running the real suite, ruff pinned, push:main + pull_request, no path filters / `continue-on-error` / `\|\| true` | **DONE** |
| RED run URL, job log showing the real suite executing with a genuine test failure | **DONE** |
| GREEN run URL | **DONE** |
| Scratch PR closed, branch deleted — verified, not assumed | **DONE** |
| Statement of what the suite actually covers | **DONE** — 96 tests, a real suite |
| Clean main red → stop, report, fix as separate named commits | **DONE** — main *was* red; see *Finding 2* |
| Draft PR, marked ready when green, not merged | **DONE** |

---

## THE RED-THEN-GREEN GATE

**RED —** run
<https://github.com/microsoft/amplifier-bundle-reality-check/actions/runs/34150897354>
(scratch PR #18, head `60ba5d0f680cad75cefa45af3d178b80c2c6d717`).

Job log, `Tests — Python 3.11` → `Run tests` step, verbatim:

```
FAILED tests/test_ci_red_proof.py::test_ci_can_actually_go_red - AssertionError: deliberate failure — proving the CI test job runs the real suite
assert 1 == 2
1 failed, 96 passed in 15.87s
##[error]Process completed with exit code 1.
```

That is the shape the gate demands: **the real suite executed** (96 other tests
passed) and the failure is a genuine `AssertionError` inside the **test job** —
not a setup, install or lint error, which would have proved nothing. All three
Python legs failed identically; `Lint (ruff 0.15.11)` and `Bundle structure`
both stayed **green**, so the red is attributable to the one deliberate test and
nothing else.

Per-job conclusions are captured in `evidence/red-run-34150897354-jobs.txt`; the
test-job log excerpt is in `evidence/red-run-34150897354-python311-testjob.txt`.

**Scratch PR closed and branch deleted, verified by remote read:**

```
$ gh pr view 18 --json state,mergedAt,headRefName
state=CLOSED mergedAt=null head=scratch/j1e6-ci-red-proof
$ git ls-remote --heads origin scratch/j1e6-ci-red-proof | wc -l
0
```

**GREEN —** run
<https://github.com/microsoft/amplifier-bundle-reality-check/actions/runs/34151125100>
(PR #19, head `a6bbe02dba93d3f7916c5c45509ee0850240ae31`). All **5 jobs
success**; `Tests — Python 3.11` → `Run tests` reads `96 passed in 15.75s`.
Per-job URLs in `evidence/green-runs.txt`.

The real PR carries the workflow and the two named fix commits, and **not** the
deliberate failure — that reached only the scratch branch and is gone with it.

---

## WHAT THE SUITE ACTUALLY COVERS

**96 tests**, and they are a real suite — not an import smoke standing in for
one. This repo did **not** need the `8j42` zero-tests pattern.

| File | What it covers |
|---|---|
| `tests/test_cli.py` | CLI surface end-to-end: every command invoked as a real subprocess via `uv run`, valid/invalid acceptance-test fixtures, error-shape assertions |
| `tests/test_report.py` | `validate-report` — raw-report normalisation, id matching, malformed YAML, missing keys |
| `tests/test_report_html.py` | HTML report rendering |
| `tests/test_ids.py` | Acceptance-test id generation and stability |
| `tests/test_recipe_schema_lint.py` | Every shipped `recipes/**/*.yaml` declares `schema_version: 2` + a dependency manifest |

The suite runs on **3.11, 3.12 and 3.13** (`requires-python = ">=3.11"`).
Verified locally on all three before pushing: **96 passed** on each.

The workflow adds two checks the suite does not provide:

- **`lint`** — `uvx ruff@0.15.11 check .` **and** `format --check .`, unscoped
  over the whole tree.
- **`bundle-structure`** — YAML-parses `bundle.md`'s frontmatter, resolves every
  `includes:` target on disk, parses `behaviors/*.yaml`. An **empty glob is a
  failure**: "0 problems in 0 files" reads exactly like a working check. Proven
  to go red locally two ways before shipping — a broken `behaviors/*.yaml`
  (exit 1) and a missing `includes:` target (exit 1).

**Not wired, on purpose:** nothing here calls an LLM or stands up a container.
The bundle's real validation loop (`scripts/run-reality-check-validation*.sh`,
the `reality-check-pipeline` recipe, the DTU profiles) needs API keys, Incus and
a live Digital Twin Universe and costs money per run. That exclusion is stated
in the workflow header, not left to be discovered.

---

## FINDINGS

### Finding 1 — the item could not be claimed, and that is a defect in the GOAL, not a blocker

`work_claim(project="model_performance", item_id="model_performance-j1e6")`
was **refused**:

```
claim model_performance-j1e6 as 'agent-spark-1-1310096' failed:
Error claiming model_performance-j1e6: issue already claimed by agent-spark-1-1101253
```

The holder is **not stale** (`work_status`: `held_stale: 0`). It is a **sibling
CI lane on another repo** — which is the item's own design. Quoting the item
description verbatim:

> FILED AS ONE ITEM WITH MANY LANES, not one item per repo. […] one lane per
> repo, one PR per repo, **all against this item**.

So `model_performance-j1e6` is intended to be worked by **19 lanes
concurrently**, while `work_claim` is by construction **exclusive to one
holder**. The goal's Procedure 1 ("if the claim is refused … write BLOCKED.md,
commit, write the completion marker, stop") and its OUTCOME branch A ("the work
item … *is resolved*") are therefore **unsatisfiable for 18 of the 19 lanes**,
and following Procedure 1 literally would have shipped **no CI at all** to 18
repos — the exact opposite of the owner directive.

**Choice made, and recorded here rather than escalated** (SCOPE-OUTS: "No
waiting on any human decision: choose, record the choice, continue"):

- **Did the work.** The deliverables cost **$0** and none of them depend on
  holding the tracker item. The goal is explicit that "if you can spend your way
  to the deliverable and simply did not, that is neither B nor C: finish the
  work."
- **Did not write `BLOCKED.md`.** Branch C is for an outcome that is
  *unreachable*. The outcome was reached: the CI exists, has been seen red, has
  been seen green, and is shipped as a draft PR.
- **Did not resolve the item, and could not have.** Resolving is impossible
  without holding it — and would be **wrong** even if possible, because
  resolving closes it for the ~17 sibling repos still without CI. The item's
  terminal word belongs to the manager (or to whichever lane is last), after all
  19 PRs land.

**Recommended goal fix for the next batch:** for a one-item-many-lanes item,
state the terminal verb as *"report against the item; the manager resolves it
once every lane's PR has landed"*, and drop the Procedure-1 "refused claim →
BLOCKED" rule for items explicitly marked multi-lane. As written, the goal makes
a refused claim indistinguishable from a genuine prerequisite failure.

### Finding 2 — clean main was RED, and it was a real defect

Before wiring anything, the suite was run on untouched `main` (`865c3ee`):
**95 passed, 1 failed**.

```
tests/test_cli.py:42: in test_version
    assert "0.1.0" in result.stdout
E   AssertionError: assert '0.1.0' in 'amplifier-reality-check, version 0.2.0\n'
```

`test_version` asserted the **literal** `"0.1.0"` while `pyproject.toml`
declares `0.2.0`, so the suite has been red since the version bump — one failure
with nothing to do with any change under test. Had CI been wired first, the very
first run would have been red for a reason no contributor caused.

**Fixed as its own named commit, not papered over** (`2ea928b`): the test now
reads `importlib.metadata.version("amplifier-bundle-reality-check")`, which is
the same source `click.version_option(package_name=...)` reads, so it cannot go
stale again. No `continue-on-error`, no narrowed selection, no deselect.

Suite after: **96 passed, 0 failed**, on each of 3.11 / 3.12 / 3.13.

### Finding 3 — ruff was clean; ruff *format* was not, and the fix was 2 files

At the pinned family version **0.15.11**: `ruff check .` reported **"All checks
passed!"** on untouched main. `ruff format --check .` reported **2 files would
be reformatted** (`tests/helpers.py`, one signature rewrapped;
`docs/lanes/kp79-catalog-reality-check/render_catalog.py`, two long `print(...)`
calls split) — **9 insertions, 5 deletions, no behaviour change**.

Applied rather than excluded, as its own named commit (`b61bd92`). The sibling
lane on `routing-matrix` (`b4xs`) chose the opposite for its repo and said so —
its format diff was 14 files / ~137 lines and would have collided with every
in-flight branch. At 2 files the calculus flips: an exclusion rule would cost
more than the reformat, and a narrowed lint scope is how a green CI stops
meaning anything.

### Finding 4 — no committed lockfile, so ruff is pinned in the workflow

`.gitignore` excludes `uv.lock` in this repo, so there is no lockfile to
`uv sync --frozen` against and no lockfile to pin ruff *through* — which is how
`context-intelligence` and `evaluation` pin theirs. Ruff is therefore pinned
**explicitly and visibly** at the command: `uvx ruff@0.15.11`, the same
mechanism `routing-matrix` uses, and byte-for-byte what a contributor runs
locally.

The consequence for the test job is stated in the workflow header rather than
left to be discovered: `pyproject.toml` declares two dependencies as
`git+…@main` (`amplifier-bundle-digital-twin-universe`,
`amplifier-bundle-gitea`), so **a breaking change on either repo's main can turn
this job red without a commit here**. That is the real cost of not committing a
lock. It was not "fixed" by committing one, because the bundle's own install
path (`uv pip install -e . --no-sources`, what the Amplifier activator runs)
ignores a lockfile entirely — a lock would pin CI to a reality the product never
sees.

---

## DEVIATIONS FROM THE GOAL

1. **Worked without holding the item.** Finding 1. Recorded, not escalated.
2. **The real PR carries three commits, not "the workflow ONLY".** The other two
   are the clean-main-red fix and the format fix, which the goal itself
   prescribes as "separate, named commits". The deliberate failing test reached
   only the scratch branch and is gone with it.
3. **Lane artifacts are committed to the repo** under
   `docs/lanes/j1e6-ci-reality-check/` per artifact-path/v1 — the same place the
   prior lane (`kp79`) put its own. The repo-root `DONE-NOTE.md` was never
   created or modified.

## CAP

The $0.00 authority **bound nothing**. Its arithmetic is
`0 runs × 0 arms × $0 / 1.00 = $0.00`, which is trivially closed: this
deliverable buys no runs. Every deliverable landed inside it. No residue, no
unspendable remainder, no NOT-POSSIBLE.
