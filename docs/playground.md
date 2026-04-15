# E2E Playground

A script that creates a self-contained directory for manually testing reality-check against amplifier-chat.

## What it sets up

The script clones amplifier-chat from GitHub into a working directory alongside
synthetic fixture files that simulate the "user asked an agent to build this" scenario:

```
/tmp/reality-check-playground/
├── user/
│   ├── spec.md                # what the user asked for
│   └── conversation.md        # synthetic conversation where an agent built it
└── software/amplifier-chat/   # the built artifact (full source)
```

`user/spec.md` contains realistic user requirements (chat UI, streaming, session
history, pinning, slash commands). `user/conversation.md` is a ~25-turn
back-and-forth covering the key design decisions. Together they give the
intent-analyzer enough signal to derive meaningful acceptance tests.

## Setup

```bash
cd amplifier-bundle-reality-check
./scripts/setup-e2e-playground.sh              # default: /tmp/reality-check-playground
./scripts/setup-e2e-playground.sh /tmp/mytest   # custom target dir
```

The script shallow-clones amplifier-chat from GitHub and strips the `.git`
directory so the result looks like a standalone artifact, not a repo.

## Testing the pipeline

```bash
cd /tmp/reality-check-playground
amplifier   # start a session with the reality-check bundle
```

Then drive the pipeline step by step:

1. **Intent Analyzer** -- derive acceptance tests from the spec and conversation.

   ```
   Read user/spec.md and user/conversation.md, then explore software/amplifier-chat/ to ground the tests in real values. Produce acceptance tests at ./acceptance-tests.yaml.
   ```

2. **DTU** -- generate a profile for the software and launch it.

   ```
   The software at software/amplifier-chat/ is a Python FastAPI web app
   (chat plugin for amplifierd). Generate a DTU profile and launch it.
   It needs an ANTHROPIC_API_KEY passthrough and should expose port 8410.
   ```

3. **Validators** -- run acceptance tests against the live environment.
   The pipeline runs three validators sequentially; each exits immediately
   if no tests of its type exist. For amplifier-chat, only browser tests apply.

   ```
   Run browser tests from ./acceptance-tests.yaml against the chat UI at
   http://127.0.0.1:8410/chat/. Save screenshots to ./screenshots/.
   ```

   (For CLI/TUI software, the terminal-tester step would run instead.
   For API services or libraries, the generic step handles them.)

4. **Report** -- synthesize everything into a gap analysis.

   ```
   Produce the reality check report. Acceptance tests are at
   ./acceptance-tests.yaml. Write report.yaml and report.html to ./report/.
   ```
