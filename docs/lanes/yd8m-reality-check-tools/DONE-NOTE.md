# DONE-NOTE — lane yd8m-reality-check-tools

**Outcome: A. RESOLVED at the LANDING STAGE.** Both deliverables are DONE. The final
state requires a merge this lane may not perform, so the work ships as a **draft
PR** with fail-before/pass-after demonstrated. **The merge is the manager's next
stage.**

- PR (draft): <https://github.com/microsoft/amplifier-bundle-reality-check/pull/20>
- Branch: `lane/yd8m-reality-check-tools`, rebased onto `origin/main` @ `0a9b4c0`
- CI: **6/6 green** (ruff check, ruff format, pytest 3.11/3.12/3.13, bundle
  structure, CLA). The repo gained CI in `0a9b4c0`, after this lane's branch point;
  the branch was rebased onto it so CI actually runs.
- Spend: **$0.00** against the $0 authority — text/config edits, local test runs,
  and a real spawn demonstration; no paid measurement beyond ordinary session use.

## Deliverables

| deliverable | status |
|---|---|
| `browser-tester.md` declares the module needed for `tool-delegate` to survive `exclude_tools`; demonstrated by a REAL spawn plus a successful delegation to browser-operator | **DONE** |
| `terminal-tester.md`'s `tools:` corrected to real mount-plan shape + real module name; `explicit_modules` demonstrably matches | **DONE** |
| frontmatter-vs-behavior-file design question answered explicitly with reasoning | **DONE** — answered *frontmatter*, four reasons, in `FINDINGS.md` and the PR body |
| CI green where the repo has CI | **DONE** — 6/6 |

## What was proven

Fail-before ran against a cached bundle verified **byte-identical to
`origin/main`**; the cache was restored afterwards.

- **browser-tester, before:** child mount plan 20 tool modules, `tool-delegate`
  absent; agent answers "is `delegate` present? **NO**".
- **browser-tester, after:** 21 modules, `tool-delegate` present; agent answers
  **YES**; a two-hop delegation returns **PONG** from
  `browser-tester:browser-operator`
  (`0000000000000000-14ae67e383b54574_…` → `14ae67e383b54574-7667decea1bb4823_…`).
- **terminal-tester, before:** delegation **failed outright** —
  `AttributeError: 'str' object has no attribute 'get'`. The work item recorded
  this as an inert declaration; it was worse than inert, and it took the
  pipeline's entire `type: cli` lane with it.
- **terminal-tester, after:** spawns cleanly; `terminal_inspector` present **YES**,
  `delegate` correctly **NO**.
- **Regression test:** 3 failed / 4 passed on `origin/main`; 7 passed here; full
  suite 103 passed.

Detail, session ids and the design reasoning: `FINDINGS.md` beside this file.

## Disclosed variation (one run)

The two-hop delegation failed 3/3 while routing sent the middle hop to Gemini,
which rejects a nested `delegate` with `400 … missing a thought_signature in
functionCall parts`. That error naming `delegate` is itself proof the tool was
present and invoked. To route the hop off Gemini, `model_role` was removed from the
**cache copy only** for that one run; the `tools:` block under test and the
repository file are unchanged. Three attempts to pin the provider without touching
the file were overridden by role routing. Global routing was deliberately **not**
switched, to avoid perturbing sibling lanes.

## Filed elsewhere, not fixed here

1. `validate-agents` false pass (`has_explicit_tools: true` for a declaration that
   crashes the spawn) — out of scope by instruction.
2. `session_spawner.spawn_sub_session` reads raw frontmatter and raises
   `AttributeError` instead of reporting a malformed declaration, even though
   `merge_module_lists` already normalises bare strings.
3. Gemini + nested `delegate` → `400 … missing a thought_signature`; the same chain
   succeeds on anthropic.

No other repo was touched. Nothing was merged.
