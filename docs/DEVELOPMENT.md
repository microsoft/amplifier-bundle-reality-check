# Development

Local validation loop for iterating on `reality-check` without shipping
changes through upstream. Stands the bundle up inside an isolated DTU,
runs the `reality-check-pipeline` recipe against the
[playground fixtures](playground.md) (amplifier-chat source + synthetic
spec and conversation), and extracts artifacts back to the host.

## Profile

`.amplifier/digital-twin-universe/profiles/reality-check-in-incus.yaml`

Installs the full reality-check stack inside a single Incus container:
Incus, Docker, Amplifier + the DTU and Gitea CLIs (for DTU-in-DTU),
`agent-browser` + Chromium (for the browser validator), the reality-check
bundle composed as `--app`, and the playground pre-staged at `/root/home/`
via `scripts/setup-e2e-playground.sh`.

Notable profile knobs:

```
--var HOST_PORT=<n>    # host port forwarded to the inner Chat UI
                       # (default 8410 via the wrapper script)
--var GITEA_URL=...    # optional: redirect reality-check clones through
--var GITEA_TOKEN=...  # a local Gitea for testing uncommitted changes
```

## Wrapper script

`scripts/run-reality-check-validation.sh` automates the full loop. Writes
its artifacts to a timestamped dir under `$PWD`.

```bash
cd any/working/dir
/path/to/scripts/run-reality-check-validation.sh [flags]
```

Flags:

```
--profile PATH        profile YAML (default: the sibling file above)
--host-port PORT      default 8410; change for concurrent runs
--name NAME           friendly DTU name
--prompt TEXT         override the default recipe-run prompt
--destroy-on-finish   tear the DTU down after extraction (default: keep)
--help                full usage
```

What it does:

1. `amplifier-digital-twin launch` the profile.
2. Poll `check-readiness` until all checks pass.
3. `exec --stream` `amplifier run "<prompt>"` inside the DTU. Live output
   streams to the terminal and to `run.log`.
4. On completion (or failure), `file-pull` `/root/home/` and
   `/root/.amplifier/projects/` back to the host. Runs in an EXIT trap so
   partial artifacts are recovered even when the run errors.
5. Leaves the DTU running so you can `amplifier-digital-twin exec` in for
   a closer look; pass `--destroy-on-finish` to clean up.

## Testing local bundle changes

The DTU clones `reality-check` fresh from GitHub `main` by default. To
exercise uncommitted local changes, mirror your working copy into an
ephemeral Gitea on the host and tell the DTU to clone through it via
the profile's `url_rewrites` block:

```bash
# 1. Stand up a local Gitea and mirror amplifier-bundle-reality-check.
amplifier-gitea create --port 10110
# capture the token from the create output, then:
TOKEN=<token>
amplifier-gitea mirror-from-github <id> \
  --github-repo https://github.com/microsoft/amplifier-bundle-reality-check \
  --github-token "$(gh auth token)"

# 2. Push your local working branch on top of the mirror so it reflects
#    your uncommitted state.
cd /path/to/amplifier-bundle-reality-check
git push "http://admin:${TOKEN}@localhost:10110/admin/amplifier-bundle-reality-check.git" HEAD:main

# 3. Launch with the rewrite vars. The wrapper script doesn't yet
#    forward these, so call the CLI directly for this workflow:
amplifier-digital-twin launch \
  .amplifier/digital-twin-universe/profiles/reality-check-in-incus.yaml \
  --var HOST_PORT=8410 \
  --var GITEA_URL=http://localhost:10110 \
  --var GITEA_TOKEN=${TOKEN}
```

`url_rewrites` in the profile matches only
`github.com/microsoft/amplifier-bundle-reality-check`; transitive deps
(browser-tester, DTU, terminal-tester, foundation, ...) still come from
GitHub. Add more `rules:` entries if you need to iterate on those too.

## Output layout

```
$PWD/reality-check-validation-<UTC-timestamp>/
├── launch-info.json    # raw DTU launch JSON
├── run.log             # full streamed transcript
├── home/               # /root/home from the DTU
│   ├── reality-check-output/{acceptance-tests,report,screenshots}
│   ├── software/       # the artifact under test
│   └── user/           # spec.md, conversation.md fixtures
└── sessions/           # /root/.amplifier/projects — per-session events.jsonl etc.
```

Open `home/reality-check-output/report/report.html` in a browser for the
rendered gap analysis.

## Caveats

- **Provisioning is slow on first run.** `agent-browser install --with-deps`
  pulls Chromium (~300 MB) plus Linux libs. Plan for 10-15 minutes before
  the DTU reaches readiness.
- **Port 8410 by default.** If another DTU (or anything else on the host)
  already holds 8410, use `--host-port 8411` (or any free port) so the
  Incus proxy device can bind.
- **`hooks-notify` warnings in the log are non-fatal.** `amplifier-app-cli`
  injects a `hooks-notify` override for root sessions that doesn't carry
  into recipe sub-sessions; each sub-session logs a "Module not found"
  error at startup and proceeds. The profile sets `notifications: {}` to
  suppress it at the source.
