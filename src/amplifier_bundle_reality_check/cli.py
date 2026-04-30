# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Amplifier Reality Check CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import acceptance_tests, report


@click.group()
@click.version_option(package_name="amplifier-bundle-reality-check")
def main() -> None:
    """Amplifier Reality Check: verify built software matches user intent."""


# ---------------------------------------------------------------------------
# Acceptance test commands
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def validate_acceptance_tests(path: Path) -> None:
    """Validate the structure of acceptance tests at PATH.

    PATH may be a single ``.yaml`` file or a directory containing one or
    more YAML files (recursively discovered). Each file is checked
    independently against the acceptance-tests schema.

    As a side effect, any test missing an ``id`` is assigned a fresh
    8-char lowercase hex ID and the source YAML is rewritten in place.
    The output JSON reports ``ids_added`` and ``modified_files``.
    On stderr, a short human-readable note is emitted when IDs were
    assigned so pipelines (and humans) can see the mutation.

    Exit codes:
      0 - all files valid
      1 - one or more files invalid
      2 - unexpected error during validation
    """
    try:
        result = acceptance_tests.validate_path(path)
        click.echo(result.model_dump_json(indent=2))
        if result.ids_added:
            click.echo(
                f"Added {result.ids_added} test ID(s) across "
                f"{len(result.modified_files)} file(s).",
                err=True,
            )
        sys.exit(0 if result.valid else 1)
    except SystemExit:
        raise
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}), err=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Report commands
# ---------------------------------------------------------------------------


@main.command()
@click.argument("report_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--acceptance-tests",
    "acceptance_tests_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to acceptance tests (file or directory) used to expand the report.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Where to write the expanded report YAML. Defaults to "
        "<report-dir>/report.expanded.yaml."
    ),
)
@click.option(
    "--html-output",
    "html_output_path",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Where to write the visual HTML report. Defaults to a sibling of "
        "the expanded YAML (<--output parent>/report.html). Pass an empty "
        "string to skip HTML emission."
    ),
)
@click.option(
    "--screenshots-dir",
    "screenshots_dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help=(
        "Base directory for resolving relative screenshot paths in the raw "
        "report. Defaults to the report's parent directory. Absolute paths "
        "in the raw report are used as-is regardless of this flag."
    ),
)
@click.option(
    "--dtu-details-file",
    "dtu_details_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help=(
        "Optional path to a text file whose contents are rendered in the "
        "HTML report's environment-access footer (e.g. DTU URL + exec hint)."
    ),
)
def validate_report(
    report_path: Path,
    acceptance_tests_path: Path,
    output_path: Path | None,
    html_output_path: Path | None,
    screenshots_dir: Path | None,
    dtu_details_file: Path | None,
) -> None:
    """Validate a raw report YAML and emit an expanded report.

    REPORT_PATH is the YAML file produced by the report agent. It must
    contain a top-level ``results`` list of entries with ``id``, ``status``
    (pass | fail), ``evidence``, and optional ``screenshots``.

    The expanded report merges in test descriptions, source files, and
    validator types from the acceptance tests, then organizes the results
    into ``passed``, ``failures``, and ``missing`` buckets with summary
    statistics. Tests without a valid raw entry land in ``missing``;
    raw entries with unknown ids are dropped silently and counted in
    ``dropped_raw_entries``.

    On success, writes the expanded report to ``--output`` and the visual
    HTML report to ``--html-output``, then echoes the validation result
    envelope as JSON to stdout.

    Exit codes:
      0 - validation succeeded; expanded report written
      1 - structural error in either the raw report or acceptance tests
      2 - unexpected error during validation
    """
    try:
        # Default output: <report-dir>/report.expanded.yaml
        if output_path is None:
            output_path = report_path.parent / "report.expanded.yaml"

        # Default HTML output: derived from the *expanded YAML* path so the
        # canonical sibling artifacts land together (and so the default
        # never writes next to a read-only raw report -- e.g. a fixture).
        # Treat an explicit empty string as "skip HTML" so callers can opt
        # out without removing the flag plumbing.
        if html_output_path is None:
            html_output_path = output_path.parent / "report.html"
        elif not str(html_output_path):
            html_output_path = None

        # Default screenshots root: directory containing the raw report.
        # Most validators write screenshots next to (or beside) the raw
        # report; the recipe layer can override via --screenshots-dir.
        screenshots_root = (
            screenshots_dir if screenshots_dir is not None else report_path.parent
        )

        # Load DTU details from file if provided. Fail fast on read errors --
        # if the recipe asked us to surface them, we should know if we can't.
        dtu_details: str | None = None
        if dtu_details_file is not None:
            dtu_details = dtu_details_file.read_text(encoding="utf-8")

        result = report.validate_report(
            raw_path=report_path,
            acceptance_path=acceptance_tests_path,
            output_path=output_path if output_path.name else None,
            html_output_path=html_output_path,
            screenshots_root=screenshots_root,
            dtu_details=dtu_details,
        )
        click.echo(result.model_dump_json(indent=2))

        if result.valid and result.output_path is not None:
            click.echo(f"Wrote expanded report to {result.output_path}.", err=True)
        if result.valid and result.html_output_path is not None:
            click.echo(f"Wrote HTML report to {result.html_output_path}.", err=True)
        if result.expanded_report and result.expanded_report.dropped_raw_entries:
            click.echo(
                f"Dropped {result.expanded_report.dropped_raw_entries} raw "
                f"entr{'y' if result.expanded_report.dropped_raw_entries == 1 else 'ies'} "
                f"(bad shape, bad status, or unknown id).",
                err=True,
            )

        sys.exit(0 if result.valid else 1)
    except SystemExit:
        raise
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}), err=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Schema command
# ---------------------------------------------------------------------------


_SCHEMA_TYPES = {
    "acceptance-tests": acceptance_tests.AcceptanceTestsSuite,
    "report": report.RawReport,
}


@main.command()
@click.option(
    "--type",
    "schema_type",
    type=click.Choice(list(_SCHEMA_TYPES.keys())),
    default="acceptance-tests",
    show_default=True,
    help="Which schema to print.",
)
def schema(schema_type: str) -> None:
    """Print the JSON Schema for an input file.

    Use ``--type acceptance-tests`` (default) for the acceptance-tests YAML
    schema. Use ``--type report`` for the raw report YAML schema -- the
    minimal shape the report agent must produce.
    """
    try:
        model = _SCHEMA_TYPES[schema_type]
        click.echo(json.dumps(model.model_json_schema(), indent=2))
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}), err=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
