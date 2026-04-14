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
delegate(agent="reality-check:intent-analyzer", instruction="<what to analyze>", context_depth="all", context_scope="agents")
```

Verify a web UI works via browser testing:
```
delegate(agent="reality-check:browser-tester", instruction="<what to verify>", context_depth="recent", context_scope="agents")
```

Produce a gap analysis report from validator results:
```
delegate(agent="reality-check:report", instruction="<acceptance tests path and validator results>", context_depth="recent", context_scope="agents")
```
