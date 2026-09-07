# Copyright (c) Microsoft. All rights reserved.

"""TEMPORARY — a deliberate failure, to prove this repo's CI can go RED.

This file exists only on the scratch branch `scratch/j1e6-ci-red-proof`, whose
whole purpose is to make the `test` job fail with a genuine TEST failure
("N passed, 1 failed") rather than a setup or lint error. A red caused by a
broken install proves nothing about whether the suite runs at all.

The scratch PR is closed and this branch deleted as soon as that run is
observed. Nothing here reaches the real PR.
"""


def test_ci_can_actually_go_red():
    observed = 1
    expected = 2
    assert observed == expected, (
        "deliberate failure — proving the CI test job runs the real suite"
    )
