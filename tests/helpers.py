# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Compile typst documents in a subprocess.

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

__all__ = ("ROOT", "TypstResult", "compile_typst", "manifest", "write_typst")


ROOT = Path(__file__).resolve().parent.parent
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

    @property
    def ok(self) -> bool:
        """Whether the document compiled."""
        return self.returncode == 0

    def check(self) -> "TypstResult":
        """Raise `AssertionError` with the compiler's own explanation when it failed."""
        if not self.ok:
            raise AssertionError(f"typst compile failed with {self.returncode}:\n{self.stderr}")
        return self


def manifest() -> dict:
    """The `package` table of `typst.toml`."""
    with open(ROOT / "typst.toml", "rb") as fh:
        return tomllib.load(fh)["package"]


def compile_typst(
    source: Path,
    output: Path | None = None,
    fmt: str | None = None,
    sysinp: dict[str, str] | None = None,
    features: Iterable[str] = (),
) -> TypstResult:
    """Compile a typst document and return the outcome instead of raising on failure.

    Parameters
    ----------
    source
        The document to compile.
    output
        Where the compiler writes its result.
        Defaults to the source with a suffix that matches `fmt`.
    fmt
        The output format, passed as `--format`.
        Defaults to typst's own choice, which follows the suffix of `output`.
    sysinp
        Key-value pairs passed as `--input`, which is how the output mode is selected.
    features
        Unstable features to enable, passed as `--features`.

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
    args += [str(source), str(output)]

    # The package directory is exported here rather than left to `direnv`,
    # so that the suite is green for a contributor who does not use it.
    env = dict(os.environ)
    env["TYPST_PACKAGE_PATH"] = str(ROOT / ".typst-packages")
    proc = subprocess.run(args, capture_output=True, text=True, check=False, env=env)
    return TypstResult(proc.returncode, proc.stderr, output if proc.returncode == 0 else None)


def write_typst(scratch: Path, body: str, name: str = "doc.typ") -> Path:
    """Write a typst document in a scratch directory and return its path.

    The directory has to lie inside the repository,
    because typst refuses a source file outside its project root.
    """
    path = scratch / name
    path.write_text(body)
    return path
