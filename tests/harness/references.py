# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Stored reference images, and the command that regenerates them.

Stored pixels are the exception, not the tool of first resort.
Almost everything worth asserting about a rendering is a comparison *within* one run:
two epochs of the same slide, the same label in two frames, a band that may change
against a background that may not.
Those are unaffected by a glyph rasterisation change in a new typst release,
while a stored image is not.

So a reference is a last resort, and `Reference.check` demands a `reason`
that says why a picture is the only statement that can be made here.
A policy without a regeneration command decays into hand-edited binaries,
so the update path ships with it: `pytest --update-references`.
"""

from pathlib import Path

import attrs
import numpy as np
from PIL import Image

from .raster import assert_identical

__all__ = ("Reference",)


@attrs.frozen
class Reference:
    """The stored reference images of one test module."""

    directory: Path = attrs.field()
    """Where they live: a `references/` directory beside the test module that uses them."""

    update: bool = attrs.field()
    """Whether `--update-references` was given, in which case every reference is rewritten."""

    def path(self, name: str) -> Path:
        """Where the reference with this name is stored."""
        return self.directory / f"{name}.webp"

    def check(self, name: str, image: np.ndarray, reason: str, tol: int = 0):
        """Compare a rendering against its stored reference.

        Parameters
        ----------
        name
            The name of the reference, unique within the test module.
        image
            The rendering, as an RGB array.
        reason
            Why this assertion cannot be made numerically or against a second rendering
            produced in the same run. A stored image has to justify itself;
            this argument is where it does.
        tol
            The tolerance per colour channel.
            Zero is the default, because both sides are rendered by the pinned typst
            and the bundled chromium.
        """
        if not reason:
            raise ValueError("a stored reference image must say why it is stored")
        path = self.path(name)
        if self.update or not path.exists():
            self.write(name, image)
            if not self.update:
                raise AssertionError(
                    f"no reference image {path} yet; "
                    f"it has been written, review it and rerun, "
                    f"or regenerate them all with `pytest --update-references`"
                )
            return
        with Image.open(path) as stored:
            expected = np.asarray(stored.convert("RGB"))
        assert_identical(expected, image, tol, what=f"reference {name} and the rendering")

    def write(self, name: str, image: np.ndarray):
        """Store a rendering as a lossless WebP.

        WebP defaults to lossy, in `Pillow` as in `playwright`'s own `type="webp"`,
        so `lossless=True` is not optional.
        Comparison always happens on decoded arrays, so the storage format
        never enters an assertion.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        Image.fromarray(image, mode="RGB").save(self.path(name), format="WEBP", lossless=True)
