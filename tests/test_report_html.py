# Copyright (c) Microsoft. All rights reserved.

"""Unit tests for the HTML renderer in ``report_html``.

These tests exercise the pure ``render_html`` function in-process; no
subprocess, no CLI. The CLI side is covered by ``test_report.py``.

Things we assert:
* Banner color rule (green / amber / red) per pass-rate.
* Sections are conditionally rendered (passed / failures / missing /
  screenshots / dropped / assumptions / DTU details).
* Liquid autoescape: any HTML special characters in user-supplied data
  appear escaped in the output.
* Screenshot embedding: real image files become ``data:`` URIs;
  missing files and non-image suffixes degrade to a placeholder caption
  without crashing.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from amplifier_bundle_reality_check.report import (
    ExpandedReport,
    ExpandedResult,
    Statistics,
)
from amplifier_bundle_reality_check.report_html import render_html

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Smallest valid 1x1 PNG, base64-encoded. Used to write tiny image fixtures
# without depending on Pillow at test time.
_PNG_1X1_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAAWgmWQ0A"
    "AAAASUVORK5CYII="
)


def _png_bytes() -> bytes:
    return base64.b64decode(_PNG_1X1_B64)


def _make_report(
    *,
    passed: list[ExpandedResult] | None = None,
    failures: list[ExpandedResult] | None = None,
    missing: list[ExpandedResult] | None = None,
    summary: str = "Test summary",
    assumptions: list[str] | None = None,
    dropped: int = 0,
) -> ExpandedReport:
    """Build an ``ExpandedReport`` with sensible defaults and computed stats."""
    passed = passed or []
    failures = failures or []
    missing = missing or []
    total = len(passed) + len(failures) + len(missing)
    return ExpandedReport(
        summary=summary,
        timestamp="2026-04-30T12:00:00Z",
        acceptance_tests_source="/tmp/acceptance.yaml",
        raw_report_source="/tmp/report.raw.yaml",
        statistics=Statistics(
            total=total,
            passed=len(passed),
            failed=len(failures),
            missing=len(missing),
            pass_rate=f"{len(passed)}/{total}" if total else "0/0",
        ),
        passed=passed,
        failures=failures,
        missing=missing,
        assumptions=assumptions or [],
        dropped_raw_entries=dropped,
    )


def _result(
    id_: str,
    *,
    test: str = "A test",
    status: str = "pass",
    evidence: str | None = "ok",
    screenshots: list[str] | None = None,
    reason: str | None = None,
    validator: str = "browser",
) -> ExpandedResult:
    return ExpandedResult(
        id=id_,
        test=test,
        source_file="suite.yaml",
        validator=validator,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        evidence=evidence,
        screenshots=screenshots or [],
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Banner color rule
# ---------------------------------------------------------------------------


def test_banner_green_when_all_pass():
    report = _make_report(passed=[_result("aaaaaaaa")])
    html = render_html(report)
    assert 'class="banner green"' in html
    assert "1/1 passed" in html


def test_banner_amber_when_partial_pass():
    report = _make_report(
        passed=[_result("aaaaaaaa")],
        failures=[_result("bbbbbbbb", status="fail", evidence="boom")],
    )
    html = render_html(report)
    assert 'class="banner amber"' in html
    assert "1/2 passed" in html


def test_banner_red_when_no_pass():
    report = _make_report(
        failures=[_result("aaaaaaaa", status="fail", evidence="boom")],
    )
    html = render_html(report)
    assert 'class="banner red"' in html
    assert "0/1 passed" in html


def test_banner_green_when_zero_tests():
    """Edge case: 0/0 rendered as green ("nothing failed") rather than red."""
    report = _make_report()
    html = render_html(report)
    assert 'class="banner green"' in html
    assert "0/0 passed" in html


# ---------------------------------------------------------------------------
# Conditional sections
# ---------------------------------------------------------------------------


def test_passed_section_present_only_when_non_empty():
    report = _make_report()  # zero tests -> no passed section
    html = render_html(report)
    assert "Passed (" not in html


def test_failures_and_missing_render_with_correct_counts():
    report = _make_report(
        passed=[_result("aaaaaaaa", test="login works")],
        failures=[
            _result("bbbbbbbb", status="fail", test="dash shows", evidence="timeout")
        ],
        missing=[
            _result("cccccccc", status="missing", test="health", reason="no result")
        ],
    )
    html = render_html(report)
    assert "Passed (1)" in html
    assert "Failures (1)" in html
    assert "Missing (1)" in html
    assert "login works" in html
    assert "dash shows" in html
    assert "timeout" in html
    assert "no result" in html
    # Status pills present in correct flavors.
    assert 'class="pill pass"' in html
    assert 'class="pill fail"' in html
    assert 'class="pill missing"' in html


def test_dropped_section_omitted_when_zero():
    report = _make_report(passed=[_result("aaaaaaaa")], dropped=0)
    html = render_html(report)
    assert "Dropped Validator Output" not in html


def test_dropped_section_renders_with_correct_pluralization():
    one = render_html(_make_report(passed=[_result("aaaaaaaa")], dropped=1))
    many = render_html(_make_report(passed=[_result("aaaaaaaa")], dropped=3))
    assert "Dropped Validator Output" in one
    assert "1 raw entry" in one
    assert "Dropped Validator Output" in many
    assert "3 raw entries" in many


def test_assumptions_rendered_when_present():
    report = _make_report(
        passed=[_result("aaaaaaaa")],
        assumptions=["dev server on 8080", "demo user exists"],
    )
    html = render_html(report)
    assert "<h2>Assumptions</h2>" in html
    assert "dev server on 8080" in html
    assert "demo user exists" in html


def test_assumptions_section_omitted_when_empty():
    html = render_html(_make_report(passed=[_result("aaaaaaaa")]))
    assert "<h2>Assumptions</h2>" not in html


def test_dtu_details_rendered_when_provided():
    report = _make_report(passed=[_result("aaaaaaaa")])
    html = render_html(report, dtu_details="URL: http://localhost:8410/chat/")
    assert "Environment Access" in html
    assert "http://localhost:8410/chat/" in html


def test_dtu_details_section_omitted_when_blank():
    report = _make_report(passed=[_result("aaaaaaaa")])
    # Empty string and whitespace-only -> no DTU section.
    assert "Environment Access" not in render_html(report)
    assert "Environment Access" not in render_html(report, dtu_details="")
    assert "Environment Access" not in render_html(report, dtu_details="   \n  ")


# ---------------------------------------------------------------------------
# Autoescape
# ---------------------------------------------------------------------------


def test_html_autoescaped_in_user_fields():
    """Every user-controlled string is HTML-escaped via Liquid autoescape."""
    nasty = '<script>alert("xss")</script>'
    report = _make_report(
        summary=nasty,
        passed=[_result("aaaaaaaa", test=nasty, evidence=nasty)],
        assumptions=[nasty],
    )
    html = render_html(report, dtu_details=nasty)
    # The literal string must NOT appear unescaped.
    assert "<script>alert" not in html
    # It SHOULD appear escaped.
    assert "&lt;script&gt;alert(" in html


# ---------------------------------------------------------------------------
# Screenshot embedding
# ---------------------------------------------------------------------------


def test_screenshot_embedded_as_data_uri(tmp_path: Path):
    img = tmp_path / "01-login.png"
    img.write_bytes(_png_bytes())
    report = _make_report(
        passed=[_result("aaaaaaaa", screenshots=["01-login.png"])],
    )
    html = render_html(report, screenshots_root=tmp_path)
    assert "Screenshots (1)" in html
    assert "data:image/png;base64," in html
    # Filename surfaces in the caption regardless.
    assert "01-login.png" in html


def test_screenshot_missing_file_renders_placeholder(tmp_path: Path):
    report = _make_report(
        passed=[_result("aaaaaaaa", screenshots=["does-not-exist.png"])],
    )
    html = render_html(report, screenshots_root=tmp_path)
    assert "Screenshots (1)" in html
    assert "data:image/png;base64," not in html
    assert "File not found" in html
    assert "does-not-exist.png" in html


def test_screenshot_non_image_suffix_renders_placeholder(tmp_path: Path):
    """Screenshots referencing .txt evidence dumps degrade to a caption."""
    txt = tmp_path / "evidence.txt"
    txt.write_text("CLI output...")
    report = _make_report(
        passed=[_result("aaaaaaaa", screenshots=["evidence.txt"])],
    )
    html = render_html(report, screenshots_root=tmp_path)
    assert "Non-image evidence" in html
    assert "evidence.txt" in html
    assert "data:image/" not in html


def test_screenshot_relative_path_with_no_root_renders_placeholder():
    report = _make_report(
        passed=[_result("aaaaaaaa", screenshots=["01-login.png"])],
    )
    html = render_html(report, screenshots_root=None)
    assert "no screenshots-dir configured" in html


def test_screenshot_absolute_path_used_as_is(tmp_path: Path):
    """Absolute paths in the raw report ignore ``screenshots_root``."""
    img = tmp_path / "absolute.png"
    img.write_bytes(_png_bytes())
    other_root = tmp_path / "wrong"
    other_root.mkdir()
    report = _make_report(
        passed=[_result("aaaaaaaa", screenshots=[str(img)])],
    )
    html = render_html(report, screenshots_root=other_root)
    assert "data:image/png;base64," in html


def test_no_screenshots_section_when_none(tmp_path: Path):
    report = _make_report(passed=[_result("aaaaaaaa")])
    html = render_html(report, screenshots_root=tmp_path)
    assert "Screenshots (" not in html


# ---------------------------------------------------------------------------
# Portability: HTML survives source images being moved/deleted
# ---------------------------------------------------------------------------


def test_html_is_fully_portable_after_source_images_deleted(tmp_path: Path):
    """The rendered HTML carries every screenshot inline as a data URI.

    Concretely: render with screenshots in dir A, write the HTML to a
    completely separate dir B, delete dir A entirely, and confirm that
    the HTML still contains every image's bytes inline. No ``<img src>``
    or ``<a href>`` in the screenshots gallery should reference a
    filesystem path -- only ``data:`` URIs are allowed for portability.
    """
    import re
    import shutil

    # Source images live in a dedicated subtree so we can nuke it later.
    src_dir = tmp_path / "src" / "screenshots"
    src_dir.mkdir(parents=True)
    (src_dir / "01-login.png").write_bytes(_png_bytes())
    (src_dir / "02-error.png").write_bytes(_png_bytes() * 2)  # different bytes
    (src_dir / "03-success.png").write_bytes(_png_bytes() * 3)

    # The destination for the HTML lives in a sibling subtree -- distinct
    # parent from the screenshots, so nothing happens to "leak" via shared
    # ancestors when the sources are removed.
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    html_path = dest_dir / "report.html"

    report = _make_report(
        passed=[
            _result("aaaaaaaa", screenshots=["01-login.png"]),
            _result(
                "bbbbbbbb",
                test="failure flow",
                screenshots=["02-error.png", "03-success.png"],
            ),
        ],
    )
    html = render_html(report, screenshots_root=src_dir)
    html_path.write_text(html, encoding="utf-8")

    # Pull the rug: delete the source images entirely.
    shutil.rmtree(src_dir)
    assert not src_dir.exists()

    # Re-read from disk (not from the in-memory string) so we verify the
    # written file -- the artifact a user would actually open.
    rendered = html_path.read_text(encoding="utf-8")

    # Every <img src="..."> in the document MUST be a data: URI. No file
    # paths, no relative references, no file:// schemes -- those would
    # break the moment the report is moved or shared.
    img_srcs = re.findall(r'<img[^>]*\bsrc="([^"]*)"', rendered)
    assert img_srcs, "expected at least one <img> in the rendered output"
    for src in img_srcs:
        assert src.startswith("data:image/"), (
            f"non-portable <img src={src!r}> -- only data: URIs are allowed"
        )

    # Every <a href="..."> in the screenshots gallery wraps an image and
    # MUST also be a data: URI. (Other anchors in the document, if any,
    # may use #fragment links; we accept those too.) Nothing should ever
    # be a file:// or filesystem path.
    a_hrefs = re.findall(r'<a[^>]*\bhref="([^"]*)"', rendered)
    for href in a_hrefs:
        assert href.startswith("data:") or href.startswith("#"), (
            f"non-portable <a href={href!r}> -- only data:/# URIs are allowed"
        )

    # A file:// scheme would let a browser load the image from the source
    # path -- defeating portability. Forbid it outright.
    assert "file://" not in rendered

    # All three images embedded -- distinct payloads encode to distinct
    # base64 strings, so each should appear as its own data URI.
    assert len(img_srcs) == 3
    assert len(set(img_srcs)) == 3, "expected three distinct data URIs"


# ---------------------------------------------------------------------------
# Misc structural checks
# ---------------------------------------------------------------------------


def test_html_is_self_contained():
    """No external network references; CSS is inline in <style>."""
    report = _make_report(passed=[_result("aaaaaaaa")])
    html = render_html(report)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "<style>" in html
    # No CDN, no external sheet, no remote font.
    for marker in ("http://", "https://"):
        assert marker not in html, (
            f"unexpected external reference {marker!r} in HTML output"
        )


@pytest.mark.parametrize(
    "count,expected_word", [(0, "0 tests"), (1, "1 test"), (5, "5 tests")]
)
def test_summary_meta_pluralization(count: int, expected_word: str):
    passed = [_result(f"{i:08x}") for i in range(count)]
    report = _make_report(passed=passed)
    html = render_html(report)
    assert expected_word in html
