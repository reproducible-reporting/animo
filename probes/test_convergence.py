# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A panic that depends on `query` can be swallowed*.

Animo reads the document back with `query` in several places, and a value read that way is
read once per introspection pass. A check on such a value is therefore not a check on the
document but a check on one pass, and if it fails the pass, the failure may never be
reported: typst runs the document again, the next pass sees a different document because
the failed one produced nothing, and the two alternate until the iteration limit.

What surfaces is a convergence warning about an element count, pointing at the `query`,
with nothing about the panic that caused it. So a diagnostic that depends on `query` has
to be a value animo resolves, never a panic.
"""

from harness import TypstRunner

STABLE = """\
#set page(width: 10cm, height: 5cm)
#context {
  if query(<m>).len() >= 2 {
    panic("this pass saw both markers")
  }
}

#[#metadata(1)<m>]
#[#metadata(2)<m>]
"""

OSCILLATING = """\
#set page(width: 10cm, height: 5cm)
#context {
  // The marker this pass emits is the one the next pass panics on, and the pass that
  // panics emits nothing, so the pass after that emits it again.
  if query(<m>).len() == 0 [#metadata(1)<m>] else {
    panic("this pass saw the marker")
  }
}
"""


def test_a_panic_in_the_final_pass_is_reported(typst: TypstRunner):
    """The control. A document that converges reports the panic of its last pass.

    Without this, the probe below would be about panics rather than about convergence.
    """
    typst.fails(STABLE, "this pass saw both markers")


def test_a_panic_in_an_earlier_pass_is_swallowed(typst: TypstRunner):
    """The finding. The compilation succeeds, and the panic is nowhere in the output.

    The document is one whose own panic changes what the next pass sees,
    which is what any query-driven check on a document animo also emits amounts to.
    """
    result = typst.warns(OSCILLATING, "did not converge within five attempts")
    assert "this pass saw the marker" not in result.stderr, (
        "the panic of an earlier pass reached the diagnostics after all, "
        "so a check on a queried value can be a panic again"
    )
