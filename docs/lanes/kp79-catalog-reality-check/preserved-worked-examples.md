# Preserved worked examples — the 10 `<example>` blocks removed from the descriptions

**Why this file exists.** The lean rewrite (PR #15, merged as `865c3ee`) verified that every
USE WHEN / DO NOT USE WHEN **fact**, trigger and constraint survived — but the worked
**illustrations** themselves were deleted rather than relocated. `#341`'s own remediation says
where they belong:

> *"Delete all `<example>` blocks… **If a worked example is genuinely useful for human authors,
> put it in a body doc, not the description field**."*
> — `validate-agents.yaml:909`

"A body **doc**" — a documentation file. **Not** the agent body: everything below an agent's
frontmatter *"is sent to the model as system instruction"* (`validate-agents.yaml:915-916`), so
parking 3,943 bytes of illustration there would be paid on every spawn of those agents and would
put documentation where the validator says only instruction belongs.

So they live here: recovered verbatim from `683f518` (pre-change `main`), costing **zero** bytes
in the delegate catalog and **zero** bytes per spawn.

**Maintainer note:** if these are useful beyond this lane's record, promote this file to
`docs/`. This lane kept it inside its own artifact root rather than editing a path it does not
own.

---

## `browser-tester`

```
<example>
Context: User wants to verify a web app works
user: 'Verify the UI at http://10.119.176.42:8080 works'
assistant: 'I'll delegate to browser-tester to open the app and verify the web UI with a real browser.'
<commentary>
Use the runner-internal URL (container_ip + container_port) -- localhost
from inside the runner does NOT reach the SUT.
</commentary>
</example>
<example>
Context: User wants to test a form flow
user: 'Test the login form on our staging site'
assistant: 'I'll use browser-tester to navigate to the login form, fill credentials, submit, and verify the result.'
<commentary>
Works with any web app -- not tied to a specific hosting mechanism.
</commentary>
</example>
```

## `generic-tester`

```
<example>
Context: Validating an HTTP API inside a DTU
user: 'Verify the /api/version endpoint returns a version string'
assistant: 'I'll delegate to generic-tester to run the HTTP probe inside the DTU and verify the response.'
<commentary>
Runs type: other tests via amplifier-digital-twin exec inside the DTU.
Pass acceptance_tests_path and DTU environment_id in the instruction.
</commentary>
</example>
<example>
Context: Mixed test suite, only `other`-type tests remain
user: 'Run the generic verification pass against the DTU'
assistant: 'I'll use generic-tester to cover the type: other tests in the acceptance suite against the DTU.'
<commentary>
Recursively discovers all type: other tests from a directory of YAML files.
</commentary>
</example>
```

## `intent-analyzer`

```
<example>
Context: A resolver built a web app and needs to verify it
user: 'Analyze what the user wanted and produce acceptance tests'
assistant: 'I'll delegate to intent-analyzer to derive structured acceptance tests from the conversation history.'
<commentary>
Pass context_depth=all and an output path. The agent decides single-file
or directory output based on complexity.
</commentary>
</example>
<example>
Context: Called early, before software exists
user: 'What should we verify once this is built?'
assistant: 'I'll use intent-analyzer to derive acceptance tests from the conversation, flagging unknowns as assumptions.'
<commentary>
No file paths needed — derives tests purely from conversation history.
</commentary>
</example>
```

## `report`

```
<example>
Context: All validators completed; first attempt at the report.
user: 'Produce the reality check report'
assistant: 'I'll delegate to the report agent to consolidate validator results into report.raw.yaml.'
<commentary>
Embed validator result tables in the instruction as labeled blocks
(--- name results --- ... --- end name results ---). The agent matches
rows to acceptance tests by ID and writes only a top-level results: key.
</commentary>
</example>
<example>
Context: Retry; previous attempt failed CLI validation.
user: 'Retry the report'
assistant: 'I'll re-run the report agent with previous_errors populated so it can fix the structural issue.'
<commentary>
Drop unknown top-level keys (e.g. verdict) from report.raw.yaml on retry.
</commentary>
</example>
```

## `terminal-tester`

```
<example>
Context: User wants to verify a CLI tool works in a DTU
user: 'Verify the codex CLI works inside the DTU'
assistant: 'I'll delegate to terminal-tester to spawn the CLI inside the DTU and verify its output.'
<commentary>
Terminal verification against any DTU environment.
</commentary>
</example>
<example>
Context: User wants to test a TUI application flow
user: 'Test the interactive menu in my app inside the DTU'
assistant: 'I'll use terminal-tester to launch the TUI via DTU exec, interact with it, and verify the results.'
<commentary>
Works with any terminal app inside a DTU -- TUI or CLI.
</commentary>
</example>
```

