# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Render an :class:`ExpandedReport` as a self-contained HTML document.

The CLI calls :func:`render_html` after ``validate_report`` has produced an
``ExpandedReport`` and writes the result next to ``report.yaml``. The model
no longer produces HTML directly -- the agent only writes ``report.raw.yaml``.

Templating uses python-liquid (``Environment(autoescape=True)``) so all
string interpolation is HTML-escaped by default. Screenshot images are
resolved against an optional base directory and embedded as ``data:`` URIs;
missing files or non-image suffixes (e.g. ``.txt``) degrade gracefully to a
caption-only placeholder.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from liquid import Environment

from .report import ExpandedReport, ExpandedResult

# ---------------------------------------------------------------------------
# Liquid template
# ---------------------------------------------------------------------------

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Reality Check Report</title>
<style>
  :root {
    --green: #2e7d32;
    --amber: #f57f17;
    --red: #c62828;
    --grey: #6b7280;
    --bg: #ffffff;
    --fg: #111827;
    --muted: #6b7280;
    --border: #e5e7eb;
    --row-alt: #f9fafb;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Oxygen, Ubuntu, Cantarell, sans-serif;
    color: var(--fg);
    background: var(--bg);
    line-height: 1.5;
  }
  .container { max-width: 1100px; margin: 0 auto; padding: 24px; }
  .banner {
    border-radius: 8px;
    padding: 24px 32px;
    color: #ffffff;
    margin-bottom: 24px;
  }
  .banner h1 { margin: 0 0 8px 0; font-size: 22px; font-weight: 600; }
  .banner .pass-rate { font-size: 32px; font-weight: 700; letter-spacing: -0.01em; }
  .banner.green { background: var(--green); }
  .banner.amber { background: var(--amber); }
  .banner.red { background: var(--red); }
  section { margin-bottom: 32px; }
  section h2 {
    font-size: 16px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin: 0 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }
  .summary p { margin: 0 0 8px 0; }
  .summary .meta { color: var(--muted); font-size: 14px; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }
  th, td {
    text-align: left;
    padding: 10px 12px;
    vertical-align: top;
    border-bottom: 1px solid var(--border);
  }
  th { font-weight: 600; color: var(--muted); }
  tr:nth-child(even) td { background: var(--row-alt); }
  .id-cell {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
    white-space: nowrap;
  }
  .evidence {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #ffffff;
  }
  .pill.pass { background: var(--green); }
  .pill.fail { background: var(--red); }
  .pill.missing { background: var(--grey); }
  .screenshot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
  }
  .screenshot-card {
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    background: var(--row-alt);
  }
  .screenshot-card .caption {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 8px;
    word-break: break-all;
  }
  .screenshot-card img {
    display: block;
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    cursor: zoom-in;
  }
  .screenshot-card .placeholder {
    font-size: 12px;
    color: var(--muted);
    font-style: italic;
    padding: 16px;
    text-align: center;
    background: #ffffff;
    border: 1px dashed var(--border);
    border-radius: 4px;
  }
  ul.assumptions { margin: 0; padding-left: 20px; }
  ul.assumptions li { margin-bottom: 4px; }
  .dropped {
    font-size: 13px;
    color: var(--muted);
    background: var(--row-alt);
    padding: 12px 16px;
    border-radius: 6px;
    border-left: 3px solid var(--amber);
  }
  .dtu-details {
    background: #0b1021;
    color: #e6e6e6;
    padding: 16px 20px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-word;
  }
  footer { color: var(--muted); font-size: 12px; text-align: center; margin-top: 32px; }
</style>
</head>
<body>
<div class="container">

  <div class="banner {{ banner_class }}">
    <h1>Reality Check Report</h1>
    <div class="pass-rate">{{ stats.pass_rate }} passed</div>
  </div>

  <section class="summary">
    <h2>Summary</h2>
    {% if summary %}<p>{{ summary }}</p>{% endif %}
    <p class="meta">
      Generated {{ timestamp }}
      &middot; {{ stats.total }} test{% if stats.total != 1 %}s{% endif %}
      ({{ stats.passed }} passed, {{ stats.failed }} failed, {{ stats.missing }} missing)
    </p>
  </section>

  {% if passed.size > 0 %}
  <section>
    <h2>Passed ({{ passed.size }})</h2>
    <table>
      <thead>
        <tr><th style="width:14%">ID</th><th style="width:8%">Status</th><th style="width:14%">Validator</th><th style="width:28%">Test</th><th>Evidence</th></tr>
      </thead>
      <tbody>
        {% for r in passed %}
        <tr>
          <td class="id-cell">{{ r.id }}</td>
          <td><span class="pill pass">pass</span></td>
          <td>{{ r.validator }}</td>
          <td>{{ r.test }}</td>
          <td class="evidence">{{ r.evidence }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if failures.size > 0 %}
  <section>
    <h2>Failures ({{ failures.size }})</h2>
    <table>
      <thead>
        <tr><th style="width:14%">ID</th><th style="width:8%">Status</th><th style="width:14%">Validator</th><th style="width:28%">Test</th><th>Evidence</th></tr>
      </thead>
      <tbody>
        {% for r in failures %}
        <tr>
          <td class="id-cell">{{ r.id }}</td>
          <td><span class="pill fail">fail</span></td>
          <td>{{ r.validator }}</td>
          <td>{{ r.test }}</td>
          <td class="evidence">{{ r.evidence }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if screenshots.size > 0 %}
  <section>
    <h2>Screenshots ({{ screenshots.size }})</h2>
    <div class="screenshot-grid">
      {% for shot in screenshots %}
      <div class="screenshot-card">
        <div class="caption">
          <span class="id-cell">{{ shot.test_id }}</span> &middot; {{ shot.filename }}
        </div>
        {% if shot.data_uri %}
          <a href="{{ shot.data_uri }}" target="_blank" rel="noopener">
            <img src="{{ shot.data_uri }}" alt="{{ shot.filename }}">
          </a>
        {% else %}
          <div class="placeholder">{{ shot.placeholder_note }}</div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </section>
  {% endif %}

  {% if missing.size > 0 %}
  <section>
    <h2>Missing ({{ missing.size }})</h2>
    <table>
      <thead>
        <tr><th style="width:14%">ID</th><th style="width:8%">Status</th><th style="width:14%">Validator</th><th style="width:28%">Test</th><th>Reason</th></tr>
      </thead>
      <tbody>
        {% for r in missing %}
        <tr>
          <td class="id-cell">{{ r.id }}</td>
          <td><span class="pill missing">missing</span></td>
          <td>{{ r.validator }}</td>
          <td>{{ r.test }}</td>
          <td>{{ r.reason }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if dropped_count > 0 %}
  <section>
    <h2>Dropped Validator Output</h2>
    <div class="dropped">
      {{ dropped_count }} raw entr{% if dropped_count == 1 %}y{% else %}ies{% endif %}
      from validators were dropped (bad shape, bad status, or unknown id) and
      do not appear above. They were excluded from the canonical report so the
      pass-rate reflects only matched acceptance tests.
    </div>
  </section>
  {% endif %}

  {% if assumptions.size > 0 %}
  <section>
    <h2>Assumptions</h2>
    <ul class="assumptions">
      {% for a in assumptions %}
      <li>{{ a }}</li>
      {% endfor %}
    </ul>
  </section>
  {% endif %}

  {% if dtu_details %}
  <section>
    <h2>Environment Access</h2>
    <pre class="dtu-details">{{ dtu_details }}</pre>
  </section>
  {% endif %}

  <footer>
    Generated by amplifier-reality-check &middot; raw report:
    <span class="id-cell">{{ raw_report_source }}</span>
  </footer>

</div>
</body>
</html>
"""

# Single Liquid environment per process; templates are pure -- no IO at render time.
_ENV = Environment(autoescape=True)
_COMPILED = _ENV.from_string(_TEMPLATE)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Suffixes treated as embeddable images. Anything else (notably ``.txt``,
# which validators sometimes use to dump CLI evidence) renders as a
# caption-only placeholder so the HTML doesn't try to inline arbitrary files.
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def render_html(
    report: ExpandedReport,
    *,
    screenshots_root: Path | None = None,
    dtu_details: str | None = None,
) -> str:
    """Render ``report`` as a complete, self-contained HTML page.

    Args:
        report: The expanded report produced by ``report.validate_report``.
        screenshots_root: Optional base directory used to resolve relative
            screenshot paths. Absolute paths in ``report`` are used as-is.
            When ``None``, only absolute paths can be embedded; relative paths
            fall back to the placeholder.
        dtu_details: Optional free-form text rendered in a footer section
            (typically the access details handed back by the DTU profile
            builder). Empty/None hides the section entirely.

    Returns:
        A single self-contained HTML document. No external CSS, no JS, no
        network references. Screenshots are embedded as ``data:`` URIs.
    """
    context = _build_context(
        report,
        screenshots_root=screenshots_root,
        dtu_details=dtu_details,
    )
    return _COMPILED.render(**context)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _banner_class(stats_total: int, stats_passed: int) -> str:
    """Return ``green`` / ``amber`` / ``red`` per the pass-rate rule.

    * All passing -> green (including the 0/0 edge case, which signals "no
      tests ran but nothing failed either" and shouldn't be alarming).
    * Some passing -> amber.
    * Zero passing with non-zero total -> red.
    """
    if stats_total == 0 or stats_passed == stats_total:
        return "green"
    if stats_passed == 0:
        return "red"
    return "amber"


def _img_to_data_uri(path: Path) -> str | None:
    """Return a ``data:`` URI for an image file, or ``None`` if not embeddable.

    Returns ``None`` for: missing files, directories, unsupported suffixes,
    and read errors. Caller is expected to render a placeholder instead.
    """
    suffix = path.suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        return None
    try:
        data = path.read_bytes()
    except (OSError, FileNotFoundError):
        return None
    mime_suffix = "svg+xml" if suffix == ".svg" else suffix.lstrip(".")
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/{mime_suffix};base64,{b64}"


def _resolve_screenshot(
    raw_path: str,
    screenshots_root: Path | None,
) -> Path | None:
    """Resolve ``raw_path`` to a concrete file path.

    Order:
      1. Absolute path -> use as-is.
      2. With ``screenshots_root`` -> ``screenshots_root / raw_path``.
      3. Bare relative path with no root -> ``None`` (caller renders a placeholder).

    The function does NOT verify the file exists; the caller does that via
    :func:`_img_to_data_uri` so missing files and non-image suffixes share
    the same fallback path.
    """
    if not raw_path:
        return None
    p = Path(raw_path)
    if p.is_absolute():
        return p
    if screenshots_root is not None:
        return screenshots_root / p
    return None


def _build_screenshot_entries(
    rows: list[ExpandedResult],
    screenshots_root: Path | None,
) -> list[dict[str, Any]]:
    """Flatten screenshot references across ``rows`` into template-ready dicts.

    Order matches the order screenshots appear within each row. Each entry:

        {
          "test_id": "<id>",
          "filename": "<basename or raw path>",
          "data_uri": "data:image/...;base64,..." | None,
          "placeholder_note": "<human reason>" | "",
        }
    """
    entries: list[dict[str, Any]] = []
    for row in rows:
        for raw in row.screenshots:
            resolved = _resolve_screenshot(raw, screenshots_root)
            data_uri: str | None = None
            note = ""
            if resolved is None:
                note = "Relative path with no screenshots-dir configured."
            elif not resolved.exists():
                note = f"File not found: {resolved}"
            elif resolved.suffix.lower() not in _IMAGE_SUFFIXES:
                note = f"Non-image evidence ({resolved.suffix or 'no suffix'})"
            else:
                data_uri = _img_to_data_uri(resolved)
                if data_uri is None:
                    note = f"Failed to read: {resolved}"

            entries.append(
                {
                    "test_id": row.id,
                    "filename": Path(raw).name or raw,
                    "data_uri": data_uri,
                    "placeholder_note": note,
                }
            )
    return entries


def _result_to_dict(r: ExpandedResult) -> dict[str, Any]:
    """Project an ``ExpandedResult`` into the shape the template expects."""
    return {
        "id": r.id,
        "test": r.test,
        "validator": r.validator,
        "status": r.status,
        "evidence": r.evidence or "",
        "reason": r.reason or "",
    }


def _build_context(
    report: ExpandedReport,
    *,
    screenshots_root: Path | None,
    dtu_details: str | None,
) -> dict[str, Any]:
    """Assemble the Liquid render context from an ``ExpandedReport``."""
    stats = report.statistics
    # Screenshots: only passed + failures contribute (missing entries have
    # no validator output, so no screenshots).
    screenshots = _build_screenshot_entries(
        list(report.passed) + list(report.failures),
        screenshots_root,
    )
    return {
        "summary": report.summary,
        "timestamp": report.timestamp,
        "raw_report_source": report.raw_report_source,
        "acceptance_tests_source": report.acceptance_tests_source,
        "stats": {
            "total": stats.total,
            "passed": stats.passed,
            "failed": stats.failed,
            "missing": stats.missing,
            "pass_rate": stats.pass_rate,
        },
        "banner_class": _banner_class(stats.total, stats.passed),
        "passed": [_result_to_dict(r) for r in report.passed],
        "failures": [_result_to_dict(r) for r in report.failures],
        "missing": [_result_to_dict(r) for r in report.missing],
        "screenshots": screenshots,
        "assumptions": list(report.assumptions),
        "dropped_count": report.dropped_raw_entries,
        "dtu_details": (dtu_details or "").strip() or None,
    }


__all__ = ["render_html"]
