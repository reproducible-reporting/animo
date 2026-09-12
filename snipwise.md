<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Configuration for Snipwise

`typst.toml` is the single source of the version of the package and of the typst release
it is compiled with.
Snipwise copies both into every file that repeats them,
so that bumping a release is an edit of the manifest followed by `pre-commit run --all-files`.

```toml
[[sources]]
patterns = ["typst.toml"]
scanner = "regex"
regex = '(?m)^version = "(?P<content>[^"]*)"'
snippets = ["version"]

[[sources]]
patterns = ["typst.toml"]
scanner = "regex"
regex = '(?m)^compiler = "(?P<content>[^"]*)"'
snippets = ["typst-version"]

# Every place where the version appears as text:
# the import string that every example, snippet and test shows,
# and the last directory of the repository-local package tree, which is named after it.
# The expression is anchored on the package name and matches a version number only,
# so a reader can copy any of these files and compile it without an edit.
# One rule covers both forms, because two narrowed rules holding the same snippet
# in the same file are refused as a conflict.
# A pattern that matches no file is refused as well,
# so `examples/`, `probes/` and `benchmarks/` join this list when they exist.
[[targets]]
patterns = [
  "*.md",
  "*.sh",
  "plan.py",
  "docs/**/*.md",
  "planning/**/*.md",
  "tests/**/*.typ",
]
scanner = "regex"
regex = '(?:@preview/animo:|\.typst-packages/preview/animo/)(?P<content>[0-9]+\.[0-9]+\.[0-9]+)'
snippets = ["version"]
render = "{{ content | unwrap }}"

# The Python side declares a version because `uv` wants one.
# Nothing is ever built from it, but a stale number there is still confusing.
[[targets]]
patterns = ["pyproject.toml"]
scanner = "regex"
regex = '(?m)^version = "(?P<content>[^"]*)"'
snippets = ["version"]
render = "{{ content | unwrap }}"

# The typst release, which is a bare version number wherever it is repeated,
# so it is marked rather than matched: there is no expression that tells
# the pinned release apart from a mention of some other release.
# The workflows join this list when they exist.
[[targets]]
patterns = ["docs/**/*.md"]
```

## `version`

The version of the package, as the `version` field of `typst.toml` declares it.

## `typst-version`

The typst release the package is compiled and tested with,
as the `compiler` field of `typst.toml` declares it.
