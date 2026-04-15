# Reality Check

You have access to the Amplifier Reality Check bundle for verifying that built software actually matches what the user intended, tested in a Digital Twin Universe environment.

## When to Use

- User has built software and wants to verify it works as intended
- User wants end-to-end validation in a realistic isolated environment
- User needs acceptance tests derived from their conversation and spec
- Do NOT use this to validate the amplifier ecosystem. You should use `amplifier-bundle-amplifier-tester`. If it is not installed, tell the user to get that bundle. Only use this bundle if they insist.

## How to Use

**ALWAYS delegate reality check work to the specialized agents.**

Derive acceptance tests from user intent:
```
delegate(agent="reality-check:intent-analyzer", instruction="Analyze user intent and produce acceptance tests. Output path: /tmp/acceptance-tests/. ...", context_depth="all", context_scope="agents")
```

Run validators directly (each discovers acceptance tests and exits immediately if no matching tests):
```
delegate(agent="reality-check:terminal-tester", instruction="Acceptance tests path: /tmp/acceptance-tests/ ...", context_depth="recent", context_scope="agents")
delegate(agent="reality-check:browser-tester", instruction="Acceptance tests path: /tmp/acceptance-tests/ ...", context_depth="recent", context_scope="agents")
```

Test types: `cli` -> terminal-tester, `browser` -> browser-tester, `generic` -> handle directly.

Produce a gap analysis report from validator results:
```
delegate(agent="reality-check:report", instruction="acceptance_tests_path: /tmp/acceptance-tests/ ...", context_depth="recent", context_scope="agents")
```
