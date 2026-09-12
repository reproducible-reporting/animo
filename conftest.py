# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The root of the pytest configuration.

The fixtures themselves live in the harness, and are loaded from here as a plugin,
because only a root `conftest.py` may declare `pytest_plugins`
and both `tests/` and `probes/` need them.
"""

pytest_plugins = ("harness.fixtures",)
