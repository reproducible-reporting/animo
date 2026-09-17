# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 2: the paged outputs, rasterised and compared as arrays.

`typst compile -f png --ppi ..` goes straight to rasters,
so no PDF has to be rendered for an assertion about layout,
and `--input animo=presentation` selects the mode exactly as an ordinary user would.
`pypdfium2` covers the few assertions that are about the PDF writer rather than the layout.

The comparison helpers all report *where* two rasters differ.
A bare boolean makes "identical outside this band" unreadable when it fails,
and that is the shape of the assertion the region design rests on.
"""

import re
from io import BytesIO
from pathlib import Path

import attrs
import numpy as np
import pypdfium2
from PIL import Image

from .typst import TypstRunner, compile_typst

__all__ = (
    "Box",
    "PagedRunner",
    "assert_differs",
    "assert_identical",
    "assert_identical_outside",
    "decode",
    "difference_box",
    "difference_report",
    "load_image",
    "pdf_pages",
)


@attrs.frozen
class Box:
    """A rectangle in pixel coordinates, with `x1` and `y1` just past the last pixel."""

    x0: int = attrs.field()
    y0: int = attrs.field()
    x1: int = attrs.field()
    y1: int = attrs.field()

    def __str__(self) -> str:
        return f"x {self.x0}..{self.x1}, y {self.y0}..{self.y1}"

    def mask(self, shape: tuple[int, ...]) -> np.ndarray:
        """A boolean array covering the first two axes of `shape`, true inside the box."""
        mask = np.zeros(shape[:2], dtype=bool)
        mask[self.y0 : self.y1, self.x0 : self.x1] = True
        return mask


def decode(data: bytes) -> np.ndarray:
    """Decode an encoded image into an RGB array of shape `(height, width, 3)`.

    The storage format never enters an assertion:
    everything is compared on decoded arrays,
    which is what makes a lossless WebP reference and a PNG screenshot interchangeable.

    Transparency is flattened onto white, as a projector shows a slide with no background.
    Typst writes a page without a fill as a transparent PNG, and dropping the alpha channel
    would turn that page black, the colour of text, so no comparison could see the text.
    A slide with a background paints every pixel opaque, which the flattening leaves alone.
    """
    with Image.open(BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return np.asarray(Image.alpha_composite(white, rgba).convert("RGB"))


def load_image(path: Path) -> np.ndarray:
    """Decode an image file into an RGB array."""
    return decode(path.read_bytes())


def _deviation(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """The per-pixel maximum absolute difference over the colour channels."""
    if first.shape != second.shape:
        raise AssertionError(f"raster shapes differ: {first.shape} versus {second.shape}")
    return np.abs(first.astype(np.int16) - second.astype(np.int16)).max(axis=2)


def difference_box(first: np.ndarray, second: np.ndarray, tol: int = 0) -> Box | None:
    """The smallest box containing every pixel that differs by more than `tol`.

    Returns
    -------
    box
        The bounding box of the differences, or `None` when there are none.
    """
    differs = _deviation(first, second) > tol
    if not differs.any():
        return None
    rows = np.flatnonzero(differs.any(axis=1))
    cols = np.flatnonzero(differs.any(axis=0))
    return Box(int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)


def difference_report(first: np.ndarray, second: np.ndarray, tol: int = 0) -> str:
    """Describe how and where two rasters differ, in one sentence.

    This is what a failing comparison says instead of `False`.
    """
    deviation = _deviation(first, second)
    differs = deviation > tol
    height, width = deviation.shape
    if not differs.any():
        return f"identical to within {tol}/255 over {width}x{height} pixels"
    box = difference_box(first, second, tol)
    return (
        f"{int(differs.sum())} of {width * height} pixels differ by more than {tol}/255, "
        f"at most {int(deviation.max())}/255, "
        f"all within {box} of a {width}x{height} raster"
    )


def assert_identical(first: np.ndarray, second: np.ndarray, tol: int = 0, what: str = "rasters"):
    """Assert that two rasters agree everywhere, to within `tol` per channel."""
    if difference_box(first, second, tol) is not None:
        raise AssertionError(f"{what} differ: {difference_report(first, second, tol)}")


def assert_differs(first: np.ndarray, second: np.ndarray, tol: int = 0, what: str = "rasters"):
    """Assert that two rasters disagree somewhere, which is what proves a change happened."""
    if difference_box(first, second, tol) is None:
        raise AssertionError(f"{what} are identical to within {tol}/255, but should differ")


def assert_identical_outside(
    first: np.ndarray,
    second: np.ndarray,
    box: Box,
    tol: int = 0,
    what: str = "rasters",
):
    """Assert that two rasters agree everywhere outside `box`.

    This is the invariant the region design rests on:
    a structural change redraws the whole slide,
    and everything outside the changed region has to come out pixel-identical.
    """
    outside = ~box.mask(first.shape)
    masked_first = np.where(outside[:, :, None], first, 0)
    masked_second = np.where(outside[:, :, None], second, 0)
    if difference_box(masked_first, masked_second, tol) is not None:
        raise AssertionError(
            f"{what} differ outside {box}: {difference_report(masked_first, masked_second, tol)}"
        )


def pdf_pages(path: Path, scale: float = 1.0) -> list[np.ndarray]:
    """Render every page of a PDF with `pypdfium2`, the engine chromium renders PDFs with.

    Only assertions that are about the PDF writer rather than about the layout need this.
    Everything else goes through `PagedRunner.png`, which skips the PDF altogether.
    """
    document = pypdfium2.PdfDocument(path)
    try:
        return [np.asarray(page.render(scale=scale).to_pil().convert("RGB")) for page in document]
    finally:
        document.close()


def _page_number(path: Path) -> int:
    """The page number in a name written from the `page-{p}.png` template.

    The padding of `{0p}` follows the page count, so the order has to be numeric.
    """
    return int(re.fullmatch(r"page-(\d+)", path.stem)[1])


@attrs.frozen
class PagedRunner:
    """Tier 2: render the paged outputs of a document and hand back arrays."""

    typst: TypstRunner = attrs.field()
    """The tier-1 runner, which owns the scratch directory and writes the documents."""

    _count: list[int] = attrs.field(factory=lambda: [0])
    """How many renderings this runner has produced, so that each gets its own directory."""

    def _slot(self) -> Path:
        self._count[0] += 1
        path = self.typst.scratch / f"render{self._count[0]}"
        path.mkdir(exist_ok=True)
        return path

    def png(
        self,
        source: str | Path,
        mode: str | None = None,
        ppi: float = 72.0,
        **kwargs,
    ) -> list[np.ndarray]:
        """Rasterise every page of a document and return them as RGB arrays.

        Parameters
        ----------
        source
            The document, as a body to write or as an existing path.
        mode
            The animo output mode, passed as `--input animo=..` exactly as a user would.
            `None` leaves it out, which selects the handout, animo's default paged output.
        ppi
            The resolution. The default makes one pixel one typst point,
            so a box measured in points is a box of the same numbers in the raster.

        Returns
        -------
        pages
            One array per page, in page order.
        """
        if isinstance(source, str):
            source = self.typst.source(source)
        slot = self._slot()
        # A page number template is mandatory as soon as a document has more than one page,
        # and harmless when it has one, so every rendering goes through the same call.
        sysinp = dict(kwargs.pop("sysinp", None) or {})
        if mode is not None:
            sysinp["animo"] = mode
        template = slot / "page-{p}.png"
        compile_typst(source, template, fmt="png", ppi=ppi, sysinp=sysinp, **kwargs).check()
        pages = sorted(slot.glob("page-*.png"), key=_page_number)
        return [load_image(path) for path in pages]

    def svg(self, source: str | Path, mode: str | None = None, **kwargs) -> list[Path]:
        """Export every page of a document as SVG and return the files, in page order.

        Multi-page SVG export fails without a page number template in the output path,
        which is why an SVG command line differs from the PDF one for the same paged mode.
        """
        if isinstance(source, str):
            source = self.typst.source(source)
        slot = self._slot()
        sysinp = dict(kwargs.pop("sysinp", None) or {})
        if mode is not None:
            sysinp["animo"] = mode
        template = slot / "page-{p}.svg"
        compile_typst(source, template, fmt="svg", sysinp=sysinp, **kwargs).check()
        return sorted(slot.glob("page-*.svg"), key=_page_number)

    def pdf(self, source: str | Path, mode: str | None = None, **kwargs) -> Path:
        """Compile a document to PDF and return the path, for the PDF-writer assertions."""
        if isinstance(source, str):
            source = self.typst.source(source)
        sysinp = dict(kwargs.pop("sysinp", None) or {})
        if mode is not None:
            sysinp["animo"] = mode
        slot = self._slot()
        return compile_typst(source, slot / "out.pdf", sysinp=sysinp, **kwargs).check().output
