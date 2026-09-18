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

# The typst release the manifest pins, installed under `.venv/` like everything else here,
# so that it shadows any other typst on PATH once the environment is activated.
# The test suite asserts that `typst --version` agrees with the `compiler` field of
# `typst.toml`, because the rendered pixels a test compares are the pixels of one release.
# Snipwise copies the number from that field, so it is never edited here by hand.
TYPST_VERSION="0.15.0"

case "$(uname -s)/$(uname -m)" in
Linux/x86_64) typst_target="x86_64-unknown-linux-musl" ;;
Linux/aarch64 | Linux/arm64) typst_target="aarch64-unknown-linux-musl" ;;
Darwin/x86_64) typst_target="x86_64-apple-darwin" ;;
Darwin/arm64) typst_target="aarch64-apple-darwin" ;;
*)
  echo "typst ${TYPST_VERSION} has no build for $(uname -s)/$(uname -m)." >&2
  echo "Install it by hand and put it on PATH ahead of .venv/bin." >&2
  exit 1
  ;;
esac

# A second run downloads nothing, because the binary already there is the pinned release.
if [ "$(.venv/bin/typst --version 2>/dev/null | cut -d' ' -f2)" != "${TYPST_VERSION}" ]; then
  echo "Downloading typst ${TYPST_VERSION} for ${typst_target}."
  typst_unpacked=".venv/typst-download"
  rm -rf "${typst_unpacked}"
  mkdir -p "${typst_unpacked}"
  typst_release="https://github.com/typst/typst/releases/download/v${TYPST_VERSION}"
  curl -LsSf "${typst_release}/typst-${typst_target}.tar.xz" |
    tar -xJ -C "${typst_unpacked}"
  mv "${typst_unpacked}/typst-${typst_target}/typst" .venv/bin/typst
  rm -rf "${typst_unpacked}"
fi

# The browsers the browser tier of the test suite drives.
# Three rendering engines, because a deck that only works in one of them is not a
# presentation format.
# `PLAYWRIGHT_BROWSERS_PATH` keeps them under `.venv/`, like everything else this script
# installs, and `.envrc` exports the same value so that `pytest` finds them.
export PLAYWRIGHT_BROWSERS_PATH="${PWD}/.venv/playwright"

# Chromium and firefox run wherever playwright runs, so the browser tier requires them.
engines=(chromium firefox)

# Playwright builds one webkit for linux, against the libraries debian and ubuntu carry,
# and it is a 300 MB download that can never launch anywhere else.
# So it is fetched only where it has a chance: any non-linux platform, where playwright
# supports webkit natively, and the debian family.
# Elsewhere the browser tier skips webkit and says so, and continuous integration, which
# runs on ubuntu and names every engine on the command line, covers it.
if [ "$(uname -s)" != "Linux" ] || { [ -r /etc/os-release ] &&
  grep -Eq '^(ID|ID_LIKE)=.*(debian|ubuntu)' /etc/os-release; }; then
  engines+=(webkit)
fi

.venv/bin/uv run playwright install "${engines[@]}"

# Which engines actually launch, as a sentence at bootstrap rather than as a surprise at
# the first test run. An engine may be installed and still not start, on a debian that is
# missing the system libraries `playwright install-deps webkit` would add.
echo
for engine in chromium firefox webkit; do
  if [[ " ${engines[*]} " != *" ${engine} "* ]]; then
    echo "  ${engine}: no build for this platform, so the test suite will skip it"
  elif .venv/bin/uv run python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    getattr(p, '${engine}').launch().close()
" >/dev/null 2>&1; then
    echo "  ${engine}: runs here"
  else
    echo "  ${engine}: installed but will not start, so the test suite will skip it"
  fi
done
echo

# The repository-local package directory that makes the working tree resolve
# as `@preview/animo:0.1.1`. It is committed, so this only repairs a lost symlink.
mkdir -p .typst-packages/preview/animo
ln -sfn ../../.. .typst-packages/preview/animo/0.1.1

.venv/bin/uv run pre-commit install
