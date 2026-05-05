# Amplifier Bundle Reality Check

AI-generated software is typically verified in the same environment and context it was built in.
This leads to agents claiming "done" when the work doesn't actually meet the user's intent,
hasn't been tested in a real environment, or only passes in the narrow conditions of the dev session.

Amplifier Reality Check closes that gap: it captures what the user actually wanted,
derives verifiable criteria, and tests the result in a
[Digital Twin Universe](https://github.com/microsoft/amplifier-bundle-digital-twin-universe)
environment so that "done" means done.

![Architecture](docs/reality-check-architecture.svg)


## Prerequisites

This bundle depends on the Digital Twin Universe bundle (which itself depends on
[amplifier-bundle-gitea](https://github.com/microsoft/amplifier-bundle-gitea)).
See their READMEs for prerequisite setup:

- [Digital Twin Universe prerequisites](https://github.com/microsoft/amplifier-bundle-digital-twin-universe#prerequisites)
- [Gitea prerequisites](https://github.com/microsoft/amplifier-bundle-gitea#prerequisites)
- [Terminal Tester prerequisites](https://github.com/microsoft/amplifier-bundle-terminal-tester#prerequisites) (for CLI/TUI validation)

For the CLI:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager and runner)


## Installation

This repo is an Amplifier bundle. The bundle provides a `reality-check` skill, agents, and recipes.

Install as an app bundle:

```bash
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-reality-check@main --app
```

To compose into a custom bundle, reference the behavior:

```bash
amplifier bundle add "git+https://github.com/microsoft/amplifier-bundle-reality-check@main#subdirectory=behaviors/reality-check.yaml" --app
```

`--app` composes the bundle onto every Amplifier session. Remove it to only register the bundle for later activation with `amplifier bundle use`.

This bundle doesn't ship a runtime (no provider, orchestrator, or tools) — it must be composed onto a bundle that does, like `amplifier-foundation`.

The bundle ships an `amplifier-reality-check` CLI used by the recipe pipeline to validate acceptance tests and reports. Install it on PATH:

```bash
uv tool install git+https://github.com/microsoft/amplifier-bundle-reality-check@main
```

The DTU profiles install the CLI automatically inside the test container; install on the host as above for local validation outside the pipeline.


## Agents

- **[Intent Analyzer](agents/intent-analyzer.md)** -- reads user interactions (spec, conversation history, feedback) and produces structured acceptance tests. The "what does done mean?" agent.
- **[Browser Tester](agents/browser-tester.md)** -- drives a real browser against web UIs to verify they actually work end-to-end.
- **[Terminal Tester](agents/terminal-tester.md)** -- drives terminal applications inside DTU environments to verify CLI/TUI apps work end-to-end. Uses the DTU exec bridge pattern with `terminal_inspector`.
- **[Generic Tester](agents/generic-tester.md)** -- the catch-all validator. Handles acceptance tests with `type: other` -- anything that doesn't fit the specialized `browser` or `cli` validators (HTTP probes, file checks, process inspection, library imports, etc.). Uses the DTU exec bridge pattern with `bash`.
- **[Report](agents/report.md)** -- consumes acceptance tests and validator results, produces a slim `report.raw.yaml`. The CLI (`amplifier-reality-check validate-report`) then expands it into the canonical `report.yaml` and self-contained `report.html`.


## CLI

The `amplifier-reality-check` CLI provides three subcommands:

```bash
# Validate the structure of acceptance tests. Auto-injects 8-char hex IDs
# for any tests missing one (rewrites the YAML in place).
amplifier-reality-check validate-acceptance-tests <PATH>

# Validate a raw report YAML produced by the report agent and emit the
# canonical expanded report.yaml + the self-contained report.html.
amplifier-reality-check validate-report <RAW> --acceptance-tests <PATH>

# Print the JSON Schema for an input file (acceptance-tests | report).
amplifier-reality-check schema --type acceptance-tests
```

Acceptance tests follow a strict schema: each test requires a unique `id` (8-char lowercase hex, auto-injected on first validate), a `software_type` (`web_app` | `cli_tool` | `api_service` | `library`), and a `type` (`browser` | `cli` | `other`). The recipe pipeline calls `validate-acceptance-tests` and `validate-report` as convergence gates; running the CLI manually is useful when authoring tests or debugging a failing pipeline.


## Recipes

- **[reality-check-pipeline](recipes/reality-check-pipeline.yaml)** -- runs the full pipeline end-to-end: derives acceptance tests from user intent (CLI-validated convergence loop, capped at 3 attempts), deploys the software in a Digital Twin Universe environment, runs validators sequentially (terminal-tester for `type: cli`, browser-tester for `type: browser`, generic-tester for `type: other` -- each exits immediately if no matching tests exist), and produces a gap analysis report (CLI-validated convergence loop, capped at 3 attempts). Outputs `acceptance-tests.yaml`, `report.raw.yaml`, `report.yaml`, and `report.html`. The DTU environment is left running so the user can interact with the deployed software.
  - Sample prompt: 
  ```
  Run the reality-check-pipeline recipe against the software at ./my-app with spec at ./spec.md and conversation at ./conversation.json
  ```

Two internal sub-recipes drive the convergence loops; they aren't meant to be invoked directly:

- **[intent-iteration](recipes/intent-iteration.yaml)** -- one pass of intent-analyzer + `validate-acceptance-tests`.
- **[report-iteration](recipes/report-iteration.yaml)** -- one pass of the report agent + `validate-report` (which emits the canonical YAML and HTML).

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
