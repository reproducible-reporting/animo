# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The third-party typst packages a few probes need, and the one place they are pinned.

Two findings are about `data-typst-label` inside a cetz canvas and inside a fletcher node,
so probing them means importing those packages.
Typst downloads them from Universe on first use, which is the only thing in the suite
that reaches the network, so a probe that cannot resolve its package skips
with the compiler's own explanation rather than failing.
"""

import pytest
from harness import TypstRunner

__all__ = ("CETZ", "FLETCHER", "require")


CETZ = "@preview/cetz:0.5.2"
"""The cetz release the probes import."""

FLETCHER = "@preview/fletcher:0.5.8"
"""The fletcher release the probes import."""


def require(typst: TypstRunner, package: str) -> str:
    """Skip the test unless the package resolves, and return its import string.

    Skipping here is deliberate.
    A cold package cache without a network connection is an accident of the machine,
    not a behaviour of typst, and a probe only ever reports on the latter.
    """
    result = typst.compile(f'#import "{package}"\n')
    if not result.ok:
        pytest.skip(f"{package} does not resolve:\n{result.stderr.strip()}")
    return package
