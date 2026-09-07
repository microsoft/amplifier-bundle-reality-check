#!/usr/bin/env python3
"""goal_lint.py -- catch a goal that contradicts itself, BEFORE a lane is launched against it.

WHY THIS EXISTS
    Lane kp79-catalog-reality-check spent six review cycles on a goal whose TITLE asserted
    the state its own DELIVERABLES forbade:

        GOAL.md:1   "# Goal: 5 agents, all 5 carrying example blocks"
        GOAL.md:54  "...and ZERO <example> / <commentary> blocks."
        GOAL.md:65  "...ZERO <example>/<commentary>."

    Those two conditions are MUTUALLY EXCLUSIVE. No artifact satisfies both. A lane must
    pick one, and every reviewer who picks the other reads the lane as having shipped the
    opposite of what was asked -- which is exactly what happened, repeatedly.

    The contradiction is statically detectable in the goal text. Nothing checked it, because
    no check existed. This is that check.

    It is deliberately NARROW. It reports only contradictions it can point at with two line
    numbers and a shared token. It does not grade goals, score clarity, or guess at intent --
    an over-eager linter on goal prose would be noise, and noise is how a real finding gets
    ignored.

USAGE
    goal_lint.py GOAL.md [GOAL.md ...]

EXIT CODES
    0  no contradiction found
    1  at least one contradiction found
    2  usage / unreadable file
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Tokens worth cross-checking. Each is something a goal can both assert the presence of
# and forbid -- which is precisely when a title and a deliverable can silently disagree.
TRACKED_TOKENS = ("<example>", "<commentary>")

# "the doc forbids this token" -- deliberately conservative wording set.
_FORBID = re.compile(r"\b(ZERO|NO|NONE|WITHOUT|MUST NOT|STRIP|REMOVE|DELETE)\b", re.I)

# "the doc asserts this token is present" -- indicative, stative verbs.
_ASSERT_PRESENT = re.compile(r"\b(carry|carrying|carries|contain|contains|containing|with|all)\b", re.I)

# A baseline is not a target. These markers exempt a line from the "asserts present" reading.
_BASELINE_MARKER = re.compile(
    r"\b(MEASURED BEFORE LAUNCH|BASELINE|BEFORE\b.*\bAFTER|verify, do not re-derive|stock|was measured)\b",
    re.I,
)


@dataclass
class Finding:
    code: str
    detail: str
    lines: tuple[int, ...]

    def render(self) -> str:
        where = ", ".join(f"line {n}" for n in self.lines)
        return f"[{self.code}] {where}\n    {self.detail}"


def _normalise(line: str) -> str:
    """Strip markdown emphasis and backticks so token matching sees the plain text."""
    return line.replace("**", "").replace("`", "").replace("*", "")


def lint_goal(text: str) -> list[Finding]:
    """Return every self-contradiction found in one goal document.

    The library entry point. The CLI below is a thin wrapper over exactly this.
    """
    raw = text.splitlines()
    lines = [_normalise(ln) for ln in raw]
    findings: list[Finding] = []

    title_idx = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)

    for token in TRACKED_TOKENS:
        forbidding = [
            i for i, ln in enumerate(lines)
            if token in ln and _FORBID.search(ln) and not ln.startswith("# ")
        ]
        if not forbidding:
            continue

        # CHECK 1 -- the title asserts the very state the deliverables forbid.
        if title_idx is not None:
            title = lines[title_idx]
            token_word = token.strip("<>")
            title_mentions = token in title or token_word in title.lower()
            if title_mentions and _ASSERT_PRESENT.search(title) and not _FORBID.search(title):
                findings.append(Finding(
                    "TITLE_ASSERTS_FORBIDDEN_STATE",
                    f"The title states {token!r} is present, but the document forbids it "
                    f"(first at line {forbidding[0] + 1}). These cannot both hold; a reviewer "
                    f"enforcing the title will read the lane as having shipped the opposite of "
                    f"the deliverable. Name the CHANGE in the title, imperative -- put any "
                    f"baseline in a labelled parenthetical.",
                    (title_idx + 1, forbidding[0] + 1),
                ))

        # CHECK 2 -- a non-title, non-baseline line asserts the forbidden state is required.
        for i, ln in enumerate(lines):
            if i == title_idx or token not in ln:
                continue
            if _FORBID.search(ln) or _BASELINE_MARKER.search(ln):
                continue  # forbidding, or explicitly a baseline -- both fine
            if _ASSERT_PRESENT.search(ln) and re.search(r"\b(require|must|shall|final state)\b", ln, re.I):
                findings.append(Finding(
                    "BODY_ASSERTS_FORBIDDEN_STATE",
                    f"This line requires {token!r} to be present while line "
                    f"{forbidding[0] + 1} forbids it. If it is a starting measurement, label "
                    f"it (e.g. 'MEASURED BEFORE LAUNCH') so it cannot be read as a target.",
                    (i + 1, forbidding[0] + 1),
                ))

    # CHECK 3 -- terminal bar stated as a present state the goal tells another actor to destroy.
    bar = [i for i, ln in enumerate(lines) if re.search(r"exist.{0,40}as a draft PR", ln, re.I)]
    merge = [i for i, ln in enumerate(lines) if re.search(r"the manager merges|MERGE IS THE MANAGER", ln, re.I)]
    if bar and merge:
        findings.append(Finding(
            "TERMINAL_BAR_IS_A_RACE",
            "The terminal bar is a PRESENT STATE ('deliverables exist as a draft PR') while "
            f"line {merge[0] + 1} instructs another actor to merge. Merging is irreversible, so "
            "the instructed next stage permanently falsifies the bar and the lane's compliance "
            "window is bounded by an event it does not control. State the bar historically: "
            "'were demonstrated and shipped for landing'.",
            (bar[0] + 1, merge[0] + 1),
        ))

    # CHECK 4 -- the goal requires a FINAL REPOSITORY STATE while forbidding the lane to merge.
    # Only a merge changes repository state. If the document both demands an end state of the
    # repo and prohibits the lane from merging, the condition is unreachable by any permitted
    # action -- not merely hard, FORBIDDEN. This is the mirror of TERMINAL_BAR_IS_A_RACE:
    # both arise from stating the bar as REPOSITORY STATE instead of LANE ACTION.
    forbids_merge = [
        i for i, ln in enumerate(lines)
        if re.search(r"\b(never merge|do not merge|don't merge)\b", ln, re.I)
    ]
    demands_repo_state = [
        i for i, ln in enumerate(lines)
        if re.search(r"\b(final state|end state|the live system|state of the repo)\b", ln, re.I)
        and not re.search(r"\b(demonstrated|shipped for landing|DONE AT THE DRAFT PR)\b", ln, re.I)
    ]
    if forbids_merge and demands_repo_state:
        findings.append(Finding(
            "FINAL_STATE_REQUIRES_A_FORBIDDEN_MERGE",
            f"Line {demands_repo_state[0] + 1} makes the bar a FINAL REPOSITORY STATE while line "
            f"{forbids_merge[0] + 1} forbids the lane to merge. Only a merge changes repository "
            "state, so the condition is unreachable by any action the lane is permitted to take. "
            "Either state the bar as a lane ACTION ('demonstrated and shipped for landing'), or "
            "name the actor who performs the merge as part of the condition.",
            (demands_repo_state[0] + 1, forbids_merge[0] + 1),
        ))

    return findings


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]]
    if not paths:
        sys.stderr.write(f"usage: {Path(argv[0]).name} GOAL.md [GOAL.md ...]\n")
        return 2

    total = 0
    for p in paths:
        try:
            text = p.read_text()
        except OSError as exc:
            sys.stderr.write(f"error: cannot read {p}: {exc}\n")
            return 2
        found = lint_goal(text)
        total += len(found)
        status = "CONTRADICTIONS" if found else "clean"
        print(f"\n=== {p} -- {status} ({len(found)}) ===")
        for f in found:
            print(f.render())

    print(f"\nGOAL LINT  files={len(paths)}  findings={total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
