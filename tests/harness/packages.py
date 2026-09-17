# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The third-party typst packages a few tests need, and the one place they are pinned.

Some findings are about `data-typst-label` inside a cetz canvas and inside a fletcher node,
and the tag sites of those two packages are a feature of animo,
so the probes and the feature tests import them from here.
Typst downloads them from Universe on first use, which is the only thing in the suite
that reaches the network, so a test that cannot resolve its package skips
with the compiler's own explanation rather than failing.
"""

import pytest

from .typst import TypstRunner

__all__ = ("CETZ", "FLETCHER", "require")


CETZ = "@preview/cetz:0.5.2"
"""The cetz release the suite imports."""

FLETCHER = "@preview/fletcher:0.5.8"
"""The fletcher release the suite imports."""


def require(typst: TypstRunner, package: str) -> str:
    """Skip the test unless the package resolves, and return its import string.

    Skipping here is deliberate.
    A cold package cache without a network connection is an accident of the machine,
    and no claim about typst or about animo is made or refuted by it.
    """
    result = typst.compile(f'#import "{package}"\n')
    if not result.ok:
        pytest.skip(f"{package} does not resolve:\n{result.stderr.strip()}")
    return package
