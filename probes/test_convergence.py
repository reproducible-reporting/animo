# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A panic that depends on `query` can be swallowed*.

Animo reads the document back with `query` in several places, and a value read that way is
read once per introspection pass. A check on such a value is therefore not a check on the
document but a check on one pass, and if it fails the pass, the failure may never be
reported: typst runs the document again, the next pass sees a different document because
the failed one produced nothing, and the two alternate until the iteration limit.

What surfaces is a convergence warning about an element count, pointing at the `query`,
with nothing about the panic that caused it.

What makes the next pass pass is that the panic empties the block it is raised in.
A check in a block of its own, which emits nothing the check reads, does not change the
document by failing, and typst keeps only the errors of the pass it ends on:
a value that is missing in an early pass is forgotten, and one that is missing for good
is reported. So a diagnostic that depends on `query` is either a value animo resolves,
or a panic raised in a block that emits nothing it reads.
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


APART = """\
#set page(width: 10cm, height: 5cm)
#metadata(none)<seed>
// The checked value, which appears only in the second pass: the first sees no seed.
#context if query(<seed>).len() > 0 [#metadata(EMITTED)<m>]
// The check, in a block of its own that emits nothing, so failing changes nothing it reads.
#context if 2 not in query(<m>).map(it => it.value) {
  panic("the checked value is missing")
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


def test_a_check_apart_from_what_it_checks_reports_a_value_missing_for_good(
    typst: TypstRunner,
):
    """The way out. Failing empties only the check, so every pass fails it, the last included.

    The document converges on the error, which is reported with no convergence warning.
    """
    result = typst.fails(APART.replace("EMITTED", "1"), "the checked value is missing")
    assert "did not converge" not in result.stderr, result.stderr


def test_a_check_apart_from_what_it_checks_forgets_a_value_that_arrives_late(
    typst: TypstRunner,
):
    """The control. The check fails in the first two passes and not in the last.

    Only the errors of the pass typst ends on are kept, which is what lets a check tolerate
    content that a nested tag reports one pass after the slide around it.
    """
    result = typst.ok(APART.replace("EMITTED", "2"))
    assert "did not converge" not in result.stderr, result.stderr
