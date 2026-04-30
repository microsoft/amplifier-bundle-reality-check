# Development

Local validation loop for iterating on `reality-check` without shipping
changes through upstream. Stands the bundle up inside an isolated DTU,
runs the `reality-check-pipeline` recipe, and extracts artifacts back
to the host.

## Profiles

Two profiles are shipped under `.amplifier/digital-twin-universe/profiles/`:

- **`reality-check-in-incus.yaml`** -- the heavy profile. Installs the full
  reality-check stack inside a single Incus container: Incus, Docker,
  Amplifier + the DTU and Gitea CLIs (for DTU-in-DTU), `agent-browser` +
  Chromium (for the browser validator), the reality-check bundle composed
  as `--app`, and the [playground fixtures](playground.md) (amplifier-chat
  source + synthetic spec and conversation) pre-staged at `/root/home/`
  via `scripts/setup-e2e-playground.sh`. Use this for browser-based
  validation against amplifier-chat.

- **`reality-check-in-incus-simple.yaml`** -- the smoke-test profile.
  Same outer DTU stack, but no Chromium / `agent-browser` overhead and an
  inline "add two numbers" CLI playground instead of amplifier-chat. Use
  this for fast iteration on the pipeline plumbing (CLI-validated
  convergence loops, recipe wiring, the report agent) where you don't
  need a real browser.

Notable profile knobs (both profiles):

```
--var HOST_PORT=<n>    # host port forwarded to the inner Chat UI
                       # (default 8410 via the wrapper script)
--var GITEA_URL=...    # optional: redirect reality-check clones through
--var GITEA_TOKEN=...  # a local Gitea for testing uncommitted changes
```

## Wrapper scripts

Two wrappers are shipped under `scripts/`:

- **`run-reality-check-validation.sh`** -- the inner script. Launches the
  given profile, polls for readiness, runs `amplifier run "<prompt>"`
  inside the DTU with streamed output, then extracts artifacts on exit.
  Output goes to a timestamped dir under `/tmp/reality-check-runs/` so
  the repo working tree is never polluted regardless of invocation CWD.

- **`run-reality-check-validation-simple.sh`** -- the outer wrapper for
  testing local bundle changes. Spins up an `amplifier-gitea` instance
  (or reuses the first running one), mirrors
  `amplifier-bundle-reality-check` from GitHub, snapshots the local
  working tree (committed + staged + untracked) via `git commit-tree`
  against a temp index, force-pushes that snapshot to Gitea's `main`,
  then calls the inner script with `GITEA_URL` and `GITEA_TOKEN` set so
  the DTU clones your local tree instead of GitHub. Pinned to the simple
  profile and a 1h exec timeout.

### Running

```bash
# Smoke-test the pipeline against your local working tree (recommended
# for iterating on recipes / agents / CLI):
./scripts/run-reality-check-validation-simple.sh

# Run the inner script directly against the heavy profile (browser tests
# against amplifier-chat):
./scripts/run-reality-check-validation.sh [flags]
```

Inner-script flags:

```
--profile PATH        profile YAML (default: reality-check-in-incus.yaml)
--name NAME           friendly DTU name
--prompt TEXT         override the default recipe-run prompt
--out-dir PATH        full output directory (default:
                      /tmp/reality-check-runs/reality-check-validation-<TS>)
--host-port PORT      default 8410; change for concurrent runs
--var KEY=VALUE       extra --var entry forwarded to launch (repeatable)
--exec-timeout SEC    timeout for the inner `amplifier run` exec call
                      (default: 1800 = 30 min; pass 'none' to disable)
--destroy-on-finish   tear the DTU down after extraction (default: keep)
--help                full usage
```

What the inner script does:

1. `amplifier-digital-twin launch` the profile.
2. Poll `check-readiness` until all checks pass.
3. `exec --stream` `amplifier run "<prompt>"` inside the DTU. Live output
   streams to the terminal and to `run.log`.
4. On completion (or failure), `file-pull` `/root/home/` and
   `/root/.amplifier/projects/` back to the host. Runs in an EXIT trap so
   partial artifacts are recovered even when the run errors.
5. Leaves the DTU running so you can `amplifier-digital-twin exec` in for
   a closer look; pass `--destroy-on-finish` to clean up.

The simple wrapper additionally copies the extracted `home/` directory
to a flat `/tmp/reality-check-home-<TS>/` for easy file-browser access.

## Output layout

```
/tmp/reality-check-runs/reality-check-validation-<UTC-timestamp>/
├── launch-info.json    # raw DTU launch JSON
├── run.log             # full streamed transcript
├── home/               # /root/home from the DTU
│   ├── reality-check-output/{acceptance-tests,report,screenshots}
│   ├── software/       # the artifact under test
│   └── user/           # spec.md, conversation.md fixtures
└── sessions/           # /root/.amplifier/projects -- per-session events.jsonl etc.
```

Open `home/reality-check-output/report/report.html` in a browser for the
rendered gap analysis.

## Working on the Python CLI

The bundle ships an `amplifier-reality-check` CLI under
`src/amplifier_bundle_reality_check/`. To hack on it:

```bash
# Install in editable mode + dev deps
uv sync

# Run the CLI from the working tree
uv run amplifier-reality-check --help
uv run amplifier-reality-check validate-acceptance-tests path/to/tests.yaml
uv run amplifier-reality-check validate-report path/to/raw.yaml \
    --acceptance-tests path/to/tests.yaml
uv run amplifier-reality-check schema --type acceptance-tests

# Test suite
uv run pytest

# Lint and type-check
uv run ruff check src/ tests/
uv run pyright src/
```

When iterating on the CLI alongside the recipe pipeline, the simple
wrapper script (`run-reality-check-validation-simple.sh`) is the primary
loop -- it pushes your local tree (including untracked CLI changes) to
Gitea, and the DTU profile installs the CLI from there.

## Caveats

- **Provisioning is slow on first run.** The heavy profile pulls
  `agent-browser install --with-deps` (Chromium ~300 MB plus Linux libs).
  Plan for 10-15 minutes before the DTU reaches readiness. The simple
  profile is faster (no Chromium).
- **Port 8410 by default.** If another DTU (or anything else on the host)
  already holds 8410, use `--host-port 8411` (or any free port) so the
  Incus proxy device can bind.
- **`hooks-notify` warnings in the log are non-fatal.** `amplifier-app-cli`
  injects a `hooks-notify` override for root sessions that doesn't carry
  into recipe sub-sessions; each sub-session logs a "Module not found"
  error at startup and proceeds. The profile sets `notifications: {}` to
  suppress it at the source.
