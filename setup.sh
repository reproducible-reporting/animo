#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0

# Bootstrap the development environment of a fresh clone.
# Everything it installs lives under `.venv/`, so removing that directory undoes it.

set -euo pipefail

PYTHON_VERSION=3.14

# Bootstrap uv into the virtual environment it is about to create.
mkdir -p .venv/bin/
if [ ! -x .venv/bin/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL=".venv/bin" sh
fi

# Install the interpreter in the same .venv directory.
export UV_PYTHON_INSTALL_DIR=.venv/uv-python
.venv/bin/uv venv --allow-existing --python=$PYTHON_VERSION --managed-python

# Install the development environment.
.venv/bin/uv sync

# The repository-local package directory that makes the working tree resolve
# as `@preview/animo:0.1.0`. It is committed, so this only repairs a lost symlink.
mkdir -p .typst-packages/preview/animo
ln -sfn ../../.. .typst-packages/preview/animo/0.1.0

.venv/bin/uv run pre-commit install
