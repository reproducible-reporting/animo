# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Compile typst documents in a subprocess, and the tier-1 runner built on it.

Every tier of the test suite goes through `compile_typst`,
so that the compiler is invoked the same way everywhere:
the repository as the typst root, the repository-local package directory on
`TYPST_PACKAGE_PATH`, and `--ignore-system-fonts`,
which is what keeps a rendering identical between a contributor's machine and CI.
"""

import os
import subprocess
import tomllib
from collections.abc import Iterable
from pathlib import Path

import attrs

__all__ = (
    "ROOT",
    "TypstResult",
    "TypstRunner",
    "compile_typst",
    "manifest",
    "write_typst",
)


ROOT = Path(__file__).resolve().parent.parent.parent
"""The repository root, which is also the typst root of every compilation."""


@attrs.frozen
class TypstResult:
    """The outcome of one `typst compile` subprocess."""

    returncode: int = attrs.field()
    """The exit status of the compiler, zero when the document compiled."""

    stderr: str = attrs.field()
    """Everything the compiler wrote to standard error, warnings included."""

    output: Path | None = attrs.field()
    """The file the compiler was asked to write, or `None` when it did not run to completion."""

    source: Path | None = attrs.field(default=None)
    """The document that was compiled, so that a failure can quote it."""

    @property
    def ok(self) -> bool:
        """Whether the document compiled."""
        return self.returncode == 0

    def check(self) -> TypstResult:
        """Raise `AssertionError` with the compiler's own explanation when it failed."""
        if not self.ok:
            raise AssertionError(f"typst compile failed with {self.returncode}:\n{self.report()}")
        return self

    def report(self) -> str:
        """The compiler's diagnostics, with the numbered source underneath."""
        parts = [self.stderr.rstrip()]
        if self.source is not None and self.source.is_file():
            lines = self.source.read_text().splitlines()
            width = len(str(len(lines)))
            listing = "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(lines, 1))
            parts.append(f"--- {self.source.name} ---\n{listing}")
        return "\n".join(parts)


def manifest() -> dict:
    """The `package` table of `typst.toml`."""
    with open(ROOT / "typst.toml", "rb") as fh:
        return tomllib.load(fh)["package"]


def compile_typst(
    source: Path,
    output: Path | str | None = None,
    fmt: str | None = None,
    sysinp: dict[str, str] | None = None,
    features: Iterable[str] = (),
    ppi: float | None = None,
) -> TypstResult:
    """Compile a typst document and return the outcome instead of raising on failure.

    Parameters
    ----------
    source
        The document to compile.
    output
        Where the compiler writes its result.
        Defaults to the source with a suffix that matches `fmt`.
        The literal `-` sends the result to standard output, where it is discarded,
        which is how a document that only has to compile is compiled.
    fmt
        The output format, passed as `--format`.
        Defaults to typst's own choice, which follows the suffix of `output`.
    sysinp
        Key-value pairs passed as `--input`, which is how the output mode is selected.
    features
        Unstable features to enable, passed as `--features`.
    ppi
        The resolution of a PNG export, passed as `--ppi`.

    Returns
    -------
    result
        The exit status, the standard error and the output path.
    """
    suffix = {"html": ".html", "png": ".png", "svg": ".svg"}.get(fmt or "", ".pdf")
    if output is None:
        output = source.with_suffix(suffix)
    args = ["typst", "compile", "--root", str(ROOT), "--ignore-system-fonts"]
    if fmt is not None:
        args += ["--format", fmt]
    for feature in features:
        args += ["--features", feature]
    for key, value in (sysinp or {}).items():
        args += ["--input", f"{key}={value}"]
    if ppi is not None:
        args += ["--ppi", str(ppi)]
    args += [str(source), str(output)]

    # The package directory is exported here rather than left to `direnv`,
    # so that the suite is green for a contributor who does not use it.
    env = dict(os.environ)
    env["TYPST_PACKAGE_PATH"] = str(ROOT / ".typst-packages")
    # The result may be a PDF on standard output, so only standard error is decoded.
    proc = subprocess.run(args, capture_output=True, check=False, env=env)
    stderr = proc.stderr.decode(errors="replace")
    written = None if proc.returncode != 0 or output == "-" else Path(output)
    return TypstResult(proc.returncode, stderr, written, source)


def write_typst(scratch: Path, body: str, name: str = "doc.typ") -> Path:
    """Write a typst document in a scratch directory and return its path.

    The directory has to lie inside the repository,
    because typst refuses a source file outside its project root.
    """
    path = scratch / name
    path.write_text(body)
    return path


@attrs.frozen
class TypstRunner:
    """Tier 1: compile a document and assert that it did or did not compile.

    The document is exported nowhere.
    Everything it has to say, it says with `#assert`,
    so a passing test is a document that the compiler accepted.
    """

    scratch: Path = attrs.field()
    """The directory the documents are written in, inside the repository."""

    _count: list[int] = attrs.field(factory=lambda: [0])
    """How many documents this runner has written, so that each gets its own name."""

    def source(self, body: str, name: str | None = None) -> Path:
        """Write `body` as a document and return its path."""
        if name is None:
            self._count[0] += 1
            name = f"doc{self._count[0]}.typ"
        return write_typst(self.scratch, body, name)

    def compile(self, source: str | Path, html: bool = False, **kwargs) -> TypstResult:
        """Compile a document without exporting anything, and return the outcome.

        Parameters
        ----------
        source
            The document, as a body to write or as an existing path.
        html
            Compile for the HTML target instead of the paged one.
            Several behaviours differ between the two, and a probe that is about one of them
            has to be able to ask for either.
        """
        if isinstance(source, str):
            source = self.source(source)
        if html:
            kwargs.setdefault("features", ["html"])
        return compile_typst(source, output="-", fmt="html" if html else "pdf", **kwargs)

    def ok(self, source: str | Path, **kwargs) -> TypstResult:
        """Assert that a document compiles, and return the outcome for its warnings."""
        return self.compile(source, **kwargs).check()

    def fails(self, source: str | Path, message: str | None = None, **kwargs) -> TypstResult:
        """Assert that a document does not compile, and that the compiler said why.

        Parameters
        ----------
        source
            The document, as a body to write or as an existing path.
        message
            A substring the compiler's diagnostics must contain.
            This is the assertion that matters:
            a document may fail for a reason that has nothing to do with the claim.
        """
        result = self.compile(source, **kwargs)
        if result.ok:
            raise AssertionError(f"document compiled but should not have:\n{result.report()}")
        if message is not None and message not in result.stderr:
            raise AssertionError(
                f"expected {message!r} in the compiler's diagnostics, got:\n{result.report()}"
            )
        return result

    def warns(self, source: str | Path, message: str, **kwargs) -> TypstResult:
        """Assert that a document compiles and that the compiler warned about something."""
        result = self.ok(source, **kwargs)
        if message not in result.stderr:
            raise AssertionError(
                f"expected the warning {message!r}, got:\n{result.stderr.rstrip() or '(nothing)'}"
            )
        return result

    def svg(self, source: str | Path, name: str = "out.svg", **kwargs) -> str:
        """Compile a single-page document to SVG and return the markup.

        SVG is the cheapest way to look at what typst emits for a labelled box,
        and it is the same printing code the HTML target runs.
        """
        if isinstance(source, str):
            source = self.source(source)
        result = compile_typst(source, self.scratch / name, fmt="svg", **kwargs).check()
        return result.output.read_text()

    def html(self, source: str | Path, name: str = "out.html", **kwargs) -> Path:
        """Compile a document to HTML and return the path of the written file."""
        if isinstance(source, str):
            source = self.source(source)
        kwargs.setdefault("features", ["html"])
        result = compile_typst(source, self.scratch / name, fmt="html", **kwargs).check()
        return result.output
