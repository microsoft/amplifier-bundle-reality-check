# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Reality-check report schema, validation, and expansion.

The report pipeline has two layers:

1. **Raw report** (model output): the report agent produces the bare minimum --
   for each acceptance test it ran, an ``id`` (matching the acceptance test),
   a ``status`` (``pass`` or ``fail``), an ``evidence`` string, and an optional
   list of screenshot paths. Nothing else.

2. **Expanded report** (computed): ``validate_report`` cross-references the raw
   report against the acceptance tests file/directory and produces a fully
   merged report with the test description, source file, validator type, and
   summary statistics. Tests that the model didn't cover, or whose ids don't
   line up, land in the ``missing`` bucket.

Per-entry tolerances: a raw entry with a malformed id, a bad status, or a
nonexistent acceptance-test id is dropped silently (counted in
``dropped_raw_entries``). Validation only fails on top-level structural
problems (YAML parse error, IO error, missing/wrong-type ``results`` key).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field

from . import acceptance_tests
from .acceptance_tests import (
    AcceptanceTestsSuite,
    NonEmptyStr,
    TestId,
    discover_yaml_files,
    validate_file,
)

# ---------------------------------------------------------------------------
# Raw report (what the model produces)
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    """Base for raw schema models: forbid unknown keys, no type coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


RawStatus = Literal["pass", "fail"]


class RawResultEntry(_Strict):
    """One result row from a validator agent.

    The model is responsible for ``id``, ``status``, ``evidence`` (and any
    ``screenshots`` produced by the validator). All human-readable context
    (test description, source file, validator type) is merged in from the
    acceptance tests by id lookup -- the model doesn't restate it.
    """

    id: TestId
    status: RawStatus
    evidence: NonEmptyStr
    screenshots: list[NonEmptyStr] = Field(default_factory=list)


class RawReport(_Strict):
    """Top-level container the model writes to disk."""

    results: list[RawResultEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Expanded report (what the CLI computes and writes)
# ---------------------------------------------------------------------------


# Mirrors acceptance_tests.Test.type so the report's validator column always
# tracks the test type vocabulary.
ValidatorType = Literal["browser", "cli", "other"]
ExpandedStatus = Literal["pass", "fail", "missing"]


class ExpandedResult(BaseModel):
    """One row in the expanded report -- one per acceptance test."""

    id: TestId
    test: NonEmptyStr
    source_file: str
    validator: ValidatorType
    status: ExpandedStatus
    evidence: str | None = None
    screenshots: list[str] = Field(default_factory=list)
    reason: str | None = None  # populated when status == "missing"


class Statistics(BaseModel):
    total: int
    passed: int
    failed: int
    missing: int
    pass_rate: str  # e.g. "3/5"


class ExpandedReport(BaseModel):
    """Fully merged report. This is the format the CLI writes to disk."""

    summary: str
    timestamp: str
    acceptance_tests_source: str
    raw_report_source: str
    statistics: Statistics
    passed: list[ExpandedResult] = Field(default_factory=list)
    failures: list[ExpandedResult] = Field(default_factory=list)
    missing: list[ExpandedResult] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    dropped_raw_entries: int = 0


# ---------------------------------------------------------------------------
# Validation result envelope
# ---------------------------------------------------------------------------


class ReportValidationResult(BaseModel):
    """Top-level result envelope returned by ``validate_report``.

    Mirrors the shape of ``acceptance_tests.ValidationReport`` for callers
    that already understand that format. ``valid`` is True only when there
    were no structural errors with either input. Per-entry tolerances do
    not affect ``valid``.
    """

    raw_report_path: Path
    acceptance_tests_path: Path
    raw_errors: list[dict[str, Any]] = Field(default_factory=list)
    acceptance_errors: list[dict[str, Any]] = Field(default_factory=list)
    expanded_report: ExpandedReport | None = None
    output_path: Path | None = None
    html_output_path: Path | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid(self) -> bool:
        return not self.raw_errors and not self.acceptance_errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    """Parse a YAML file. Return (data, errors). Errors are pydantic-shaped."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), []
    except yaml.YAMLError as exc:
        return None, [{"type": "yaml_parse_error", "loc": [], "msg": str(exc)}]
    except OSError as exc:
        return None, [{"type": "io_error", "loc": [], "msg": str(exc)}]


def _validate_raw_envelope(
    data: Any,
) -> tuple[list[dict[str, Any]], int, dict[str, RawResultEntry]]:
    """Validate the top-level shape of a raw report.

    Returns ``(errors, dropped_count, by_id)``:
      * ``errors``: structural errors (non-empty -> fail validation)
      * ``dropped_count``: raw entries we couldn't accept (bad id, bad
        status, missing field, duplicate id, etc.)
      * ``by_id``: surviving entries keyed by id (id is unique here -- on
        duplicates, first wins)

    Per-entry validation is tolerant: a malformed entry is dropped, not
    fatal. The envelope itself (must be a dict, must have ``results`` as a
    list) IS fatal.
    """
    errors: list[dict[str, Any]] = []
    dropped = 0
    by_id: dict[str, RawResultEntry] = {}

    if data is None:
        errors.append(
            {
                "type": "empty_report",
                "loc": [],
                "msg": "raw report is empty (no top-level mapping)",
            }
        )
        return errors, 0, {}

    if not isinstance(data, dict):
        errors.append(
            {
                "type": "model_type",
                "loc": [],
                "msg": "raw report root must be a mapping",
                "input": type(data).__name__,
            }
        )
        return errors, 0, {}

    # Reject unknown top-level keys, mirroring AcceptanceTestsSuite (extra=forbid)
    for key in data:
        if key not in {"results"}:
            errors.append(
                {
                    "type": "extra_forbidden",
                    "loc": [key],
                    "msg": f"unknown top-level key: {key!r}",
                    "input": key,
                }
            )

    if "results" not in data:
        errors.append(
            {
                "type": "missing",
                "loc": ["results"],
                "msg": "raw report must include a 'results' list",
            }
        )
        return errors, 0, {}

    results = data["results"]
    if not isinstance(results, list):
        errors.append(
            {
                "type": "list_type",
                "loc": ["results"],
                "msg": "'results' must be a list",
                "input": type(results).__name__,
            }
        )
        return errors, 0, {}

    if errors:
        # Top-level shape is bad enough that we don't bother with per-entry
        # processing -- the model needs to fix its envelope first.
        return errors, 0, {}

    # Per-entry: tolerant. Bad entries get dropped + counted.
    for entry in results:
        if not isinstance(entry, dict):
            dropped += 1
            continue
        try:
            parsed = RawResultEntry.model_validate(entry)
        except ValidationError:
            dropped += 1
            continue
        if parsed.id in by_id:
            # Duplicate id: first wins, rest dropped.
            dropped += 1
            continue
        by_id[parsed.id] = parsed

    return errors, dropped, by_id


def _load_acceptance(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    Path,
    list[tuple[Path, AcceptanceTestsSuite]],
]:
    """Load + validate an acceptance-tests path (file or directory).

    Returns ``(errors, root, suites)``:
      * ``errors``: structural errors collected across files
      * ``root``: the directory that ``source_file`` paths are relative to
        -- the parent dir for a single file, the path itself for a dir.
      * ``suites``: validated suites, paired with their source paths
    """
    errors: list[dict[str, Any]] = []

    if path.is_file():
        root = path.parent
    else:
        root = path

    files = discover_yaml_files(path)
    if not files:
        errors.append(
            {
                "type": "no_files_found",
                "loc": [],
                "msg": f"no .yaml or .yml files found at {path}",
            }
        )
        return errors, root, []

    suites: list[tuple[Path, AcceptanceTestsSuite]] = []
    for f in files:
        result = validate_file(f)
        if not result.valid:
            for e in result.errors:
                errors.append(
                    {
                        **e,
                        # Tag with file so the caller can tell which file failed.
                        "file": str(f),
                    }
                )
            continue
        # validate_file only confirmed validity; reload+parse to get the model.
        with open(f, encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        try:
            suite = AcceptanceTestsSuite.model_validate(data)
        except ValidationError as exc:  # pragma: no cover - validate_file caught it
            for e in exc.errors(include_url=False):
                errors.append({**e, "file": str(f)})
            continue
        suites.append((f, suite))

    return errors, root, suites


def _relative_path(file: Path, root: Path) -> str:
    """Return ``file`` relative to ``root``, falling back to absolute path."""
    try:
        return str(file.relative_to(root))
    except ValueError:
        return str(file)


# ---------------------------------------------------------------------------
# Expansion
# ---------------------------------------------------------------------------


def expand_report(
    raw_by_id: dict[str, RawResultEntry],
    suites: list[tuple[Path, AcceptanceTestsSuite]],
    acceptance_root: Path,
    raw_path: Path,
    acceptance_path: Path,
    dropped_raw_entries: int = 0,
) -> ExpandedReport:
    """Merge the raw report with the acceptance tests into an expanded report.

    Matching is by ``id``. Raw entries whose id doesn't appear in any suite
    are dropped silently and counted in ``dropped_raw_entries``. Acceptance
    tests with no surviving raw entry land in the ``missing`` bucket.
    """
    # Build acceptance index keyed by id.
    accept_by_id: dict[str, tuple[AcceptanceTestsSuite, Any, Path]] = {}
    summaries: list[str] = []
    assumptions: list[str] = []
    for source_file, suite in suites:
        summaries.append(suite.summary)
        assumptions.extend(suite.assumptions)
        for test in suite.tests:
            # Duplicate ids across files are caught upstream by
            # acceptance_tests._check_unique_ids -- if we still see one here,
            # first-seen wins.
            accept_by_id.setdefault(test.id, (suite, test, source_file))

    passed: list[ExpandedResult] = []
    failures: list[ExpandedResult] = []
    missing: list[ExpandedResult] = []

    # Drop raw entries whose id isn't in acceptance.
    matched_ids: set[str] = set()
    for rid, raw in raw_by_id.items():
        if rid not in accept_by_id:
            dropped_raw_entries += 1
            continue
        matched_ids.add(rid)
        _suite, test, source_file = accept_by_id[rid]
        result = ExpandedResult(
            id=rid,
            test=test.description,
            source_file=_relative_path(source_file, acceptance_root),
            validator=test.type,
            status=raw.status,
            evidence=raw.evidence,
            screenshots=list(raw.screenshots),
        )
        if raw.status == "pass":
            passed.append(result)
        else:
            failures.append(result)

    # Acceptance tests not covered by a valid raw entry -> missing.
    for tid, (_suite, test, source_file) in accept_by_id.items():
        if tid in matched_ids:
            continue
        missing.append(
            ExpandedResult(
                id=tid,
                test=test.description,
                source_file=_relative_path(source_file, acceptance_root),
                validator=test.type,
                status="missing",
                evidence=None,
                screenshots=[],
                reason="no validator result for this test id",
            )
        )

    # Stable ordering: by id within each bucket so output is reproducible.
    passed.sort(key=lambda r: r.id)
    failures.sort(key=lambda r: r.id)
    missing.sort(key=lambda r: r.id)

    total = len(passed) + len(failures) + len(missing)
    stats = Statistics(
        total=total,
        passed=len(passed),
        failed=len(failures),
        missing=len(missing),
        pass_rate=f"{len(passed)}/{total}" if total else "0/0",
    )

    # Carry summary forward. If we loaded a directory of suites, concatenate
    # their summaries with " | " so all of them survive in the artifact.
    summary = " | ".join(s for s in summaries if s) or ""

    # De-dupe assumptions while preserving order.
    seen: set[str] = set()
    deduped_assumptions: list[str] = []
    for a in assumptions:
        if a not in seen:
            seen.add(a)
            deduped_assumptions.append(a)

    return ExpandedReport(
        summary=summary,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        acceptance_tests_source=str(acceptance_path),
        raw_report_source=str(raw_path),
        statistics=stats,
        passed=passed,
        failures=failures,
        missing=missing,
        assumptions=deduped_assumptions,
        dropped_raw_entries=dropped_raw_entries,
    )


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def validate_report(
    raw_path: Path,
    acceptance_path: Path,
    output_path: Path | None = None,
    *,
    html_output_path: Path | None = None,
    screenshots_root: Path | None = None,
    dtu_details: str | None = None,
) -> ReportValidationResult:
    """Validate a raw report and emit an expanded report (+ optional HTML).

    Side effects:
      * When validation succeeds and ``output_path`` is provided, writes the
        expanded report to disk as YAML.
      * When validation succeeds and ``html_output_path`` is provided, renders
        and writes the visual HTML artifact via :mod:`report_html`.

    Both writes are independent: callers can request just the YAML, just the
    HTML, neither, or both. ``screenshots_root`` and ``dtu_details`` are only
    consulted by the HTML renderer; passing them without
    ``html_output_path`` is a no-op.

    Validation succeeds when both the raw report has a well-formed envelope
    and every acceptance-tests file is structurally valid. Per-entry
    tolerances do NOT make validation fail; they bump
    ``dropped_raw_entries`` instead.
    """
    raw_data, raw_load_errors = _load_yaml(raw_path)
    if raw_load_errors:
        return ReportValidationResult(
            raw_report_path=raw_path,
            acceptance_tests_path=acceptance_path,
            raw_errors=raw_load_errors,
        )

    raw_envelope_errors, dropped, by_id = _validate_raw_envelope(raw_data)
    accept_errors, accept_root, suites = _load_acceptance(acceptance_path)

    # Don't proceed with expansion if structure is broken.
    if raw_envelope_errors or accept_errors:
        return ReportValidationResult(
            raw_report_path=raw_path,
            acceptance_tests_path=acceptance_path,
            raw_errors=raw_envelope_errors,
            acceptance_errors=accept_errors,
        )

    expanded = expand_report(
        raw_by_id=by_id,
        suites=suites,
        acceptance_root=accept_root,
        raw_path=raw_path,
        acceptance_path=acceptance_path,
        dropped_raw_entries=dropped,
    )

    written_path: Path | None = None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fp:
            yaml.safe_dump(
                expanded.model_dump(mode="json"),
                fp,
                sort_keys=False,
                allow_unicode=True,
            )
        written_path = output_path

    written_html_path: Path | None = None
    if html_output_path is not None:
        # Local import: keeps the (cheap) liquid dependency out of the
        # import path for callers that only want YAML expansion.
        from . import report_html

        html_output_path.parent.mkdir(parents=True, exist_ok=True)
        html = report_html.render_html(
            expanded,
            screenshots_root=screenshots_root,
            dtu_details=dtu_details,
        )
        html_output_path.write_text(html, encoding="utf-8")
        written_html_path = html_output_path

    return ReportValidationResult(
        raw_report_path=raw_path,
        acceptance_tests_path=acceptance_path,
        expanded_report=expanded,
        output_path=written_path,
        html_output_path=written_html_path,
    )


# Expose a stable name so cli.py can reference the schema source-of-truth.
RawReportSchema = RawReport

__all__ = [
    "RawResultEntry",
    "RawReport",
    "RawReportSchema",
    "ExpandedResult",
    "Statistics",
    "ExpandedReport",
    "ReportValidationResult",
    "expand_report",
    "validate_report",
    "acceptance_tests",
]
