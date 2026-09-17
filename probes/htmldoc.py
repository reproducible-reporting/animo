# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Build the typst documents the browser probes load.

Every one of them is a style element and one or more `html.frame`s,
which is the shape of the HTML output animo will emit.
None of them import animo: a probe reports on typst and on chromium, never on the package.
"""

import textwrap

__all__ = ("STACK_CSS", "document", "stacked")


STACK_CSS = """\
/* The epoch frames of one slide, stacked in a single grid cell. */
.stack { display: grid; isolation: isolate; }
.stack > * { grid-row: 1; grid-column: 1; isolation: isolate; }
body { margin: 0; background: #ffffff; }
"""
"""The stacking that *Architecture* prescribes, and that several findings were measured on.

The frame isolates as well as the stack, because a blend on a group inside an inline SVG
reaches the page behind an isolating HTML ancestor in playwright's webkit 26.5.
A probe that measures where a blend stops overrides this. See *Findings*.
"""


def document(body: str, css: str = "") -> str:
    """A typst document that emits a `<style>` element followed by `body`.

    The stylesheet goes through a raw block, so that no CSS character needs escaping.
    """
    if not css:
        return body
    block = textwrap.indent(css.rstrip(), "  ")
    return f'#html.elem("style", ```\n{block}\n```.text)\n{body}\n'


def stacked(frames: list[str], css: str = "") -> str:
    """A document whose frames are stacked in one grid cell, as epoch frames are.

    Parameters
    ----------
    frames
        The body of each `html.frame`, in document order.
    css
        Extra rules, appended after the stacking rules.
    """
    inner = "\n".join(f"  #html.frame[{frame}]" for frame in frames)
    body = f'#html.elem("div", attrs: (class: "stack"))[\n{inner}\n]'
    return document(body, STACK_CSS + css)
