<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Configuration for Snipwise

`typst.toml` is the single source of the version of the package and of the typst release
it is compiled with.
Snipwise copies both into every file that repeats them,
so that bumping a release is an edit of the manifest followed by `pre-commit run --all-files`.
The keyword list is metadata of three release descriptions,
which Snipwise writes in the syntax each of them uses.

```toml
# The Animo tagline is repeated in several places.
# `README.md` shows it as it is written, links and all,
# and `docs/index.md` is a symlink to it, so both paths name the same bytes.
# Everywhere else it is metadata, so the markup is stripped and the sentence is put on one line.
# The blank lines around the paragraph are what `mdformat` writes between an HTML comment
# and a paragraph, and rendering them here stops the two hooks from undoing each other.
[[targets]]
patterns = ["README.md", "docs/index.md"]
snippets = ["tagline"]
render = "\n{{ content }}\n"

# The summary of the Python package metadata, which is a single-line TOML string.
[[targets]]
patterns = ["pyproject.toml"]
scanner = "regex"
regex = '(?m)^description = "(?P<content>[^"]*)"$'
snippets = ["tagline"]
render = "{{ content | plain | unwrap }}"

# The description of the package manifest, which Typst Universe shows next to the package name.
[[targets]]
patterns = ["typst.toml"]
scanner = "regex"
regex = '(?m)^description = "(?P<content>[^"]*)"$'
snippets = ["tagline"]
render = "{{ content | plain | unwrap }}"

# The meta description that every page of the documentation site carries.
[[targets]]
patterns = ["zensical.toml"]
scanner = "regex"
regex = '(?m)^site_description = "(?P<content>[^"]*)"$'
snippets = ["tagline"]
render = "{{ content | plain | unwrap }}"

# The abstract of the citation metadata, which is a folded YAML block scalar.
# The template terminates the last line, because the region includes its newline.
[[targets]]
patterns = ["CITATION.cff"]
scanner = "regex"
regex = '(?m)^abstract: >-\n(?P<content>(?:^  .*\n)+)'
snippets = ["tagline"]
render = "{{ content | plain | unwrap | prefix('  ') }}\n"

# The Zenodo metadata, which is JSON and therefore carries no markers.
[[targets]]
patterns = [".zenodo.json"]
scanner = "json"
insert = [{ snippet = "tagline", pointer = "/description" }]
render = "{{ content | plain | unwrap }}"

# The keywords of the citation metadata, which is a YAML sequence.
[[targets]]
patterns = ["CITATION.cff"]
snippets = ["keywords"]
render = "{{ content | prefix('- ') }}"

# The keywords of the package manifest, which Typst Universe uses to find the package.
[[targets]]
patterns = ["typst.toml"]
snippets = ["keywords"]
render = '''{{ content | prefix('"') | suffix('",') }}'''

# The keywords of the Zenodo metadata, which is an array of strings and carries no markers.
[[targets]]
patterns = [".zenodo.json"]
scanner = "json"
insert = [{ snippet = "keywords", pointer = "/keywords", shape = "lines" }]

# Version sources
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

# The Python side declares a version because `uv` wants one.
# Nothing is ever built from it, but a stale number there is still confusing.
[[targets]]
patterns = ["pyproject.toml"]
scanner = "regex"
regex = '(?m)^version = "(?P<content>[^"]*)"'
snippets = ["version"]
render = "{{ content | unwrap }}"

# The citation metadata, which names the version of the release it describes.
# `CITATION.cff` is YAML, so the field is specific enough to anchor an expression on;
# `.zenodo.json` supports no comment, so its value is addressed by pointer.
[[targets]]
patterns = ["CITATION.cff"]
scanner = "regex"
regex = '(?m)^version: (?P<content>[0-9]+\.[0-9]+\.[0-9]+)$'
snippets = ["version"]
render = "{{ content | unwrap }}"

[[targets]]
patterns = [".zenodo.json"]
scanner = "json"
insert = [{ snippet = "version", pointer = "/version" }]
render = "{{ content | unwrap }}"

# The package version is repeated in two shapes, and both are matched rather than marked.
# A link from `README.md` into the repository names the tag of the release it documents,
# because the Universe package checker asks a README to link to a resource
# that matches the version of the package.
# An import string names the release a reader fetches from Typst Universe,
# and the repository-local package directory gives that same release a path.
# The two shapes are anchored in one rule rather than two,
# because two narrowed rules holding the same snippet in the same file are refused,
# and `README.md` carries both.
# A placeholder such as `@preview/animo:X.Y.Z` has no digits, so neither anchor matches it.
[[targets]]
patterns = [
  "*.md",
  ".envrc",
  "benchmarks/*.typ",
  "docs/**/*.md",
  "examples/*.typ",
  "planning/*.md",
  "setup.sh",
  "tests/*.py",
  "tests/documents/*.typ",
  "tools/*.py",
]
scanner = "regex"
regex = '(?:animo/blob/v|preview/animo[:/])(?P<content>[0-9]+\.[0-9]+\.[0-9]+)'
snippets = ["version"]
render = "{{ content | unwrap }}"

# The typst release, which is a bare version number wherever it is repeated,
# so in prose it is marked rather than matched: there is no expression that tells
# the pinned release apart from a mention of some other release.
# The `codeblock` filter writes the fences, so the marker comments stay outside the block
# instead of being shown as text by the documentation site.
# The blank lines around the block are what `mdformat` writes between an HTML comment
# and a fence, and rendering them here stops the two hooks from undoing each other.
[[targets]]
patterns = ["docs/**/*.md"]
snippets = ["typst-version"]
render = "\n{{ content | codeblock }}\n\n"

# In `README.md` the same release appears twice in the badge row,
# as the message of a shields.io badge and as the release tag that badge links to.
# Both are anchored on their surrounding URL, in one rule rather than two,
# because two narrowed rules holding the same snippet in the same file are refused.
# Neither anchor is the one the package version uses, so the two rules do not overlap.
[[targets]]
patterns = ["README.md"]
scanner = "regex"
regex = '(?:img\.shields\.io/badge/typst-|typst/releases/tag/v)(?P<content>[0-9]+\.[0-9]+\.[0-9]+)'
snippets = ["typst-version"]
render = "{{ content | unwrap }}"

# In the workflows the same release is an argument of `setup-typst`,
# which is specific enough to anchor an expression on
# and leaves the file readable as ordinary YAML.
[[targets]]
patterns = [".github/workflows/*.yml"]
scanner = "regex"
regex = 'typst-version: "(?P<content>[0-9]+\.[0-9]+\.[0-9]+)"'
snippets = ["typst-version"]
render = "{{ content | unwrap }}"

# The documentation site declares the release as a macro variable,
# so that a page can name it as a placeholder instead of a literal.
# The field name is specific enough to anchor an expression on,
# and it does not overlap with the `site_description` anchor the tagline uses.
[[targets]]
patterns = ["zensical.toml"]
scanner = "regex"
regex = '(?m)^typst_version = "(?P<content>[0-9]+\.[0-9]+\.[0-9]+)"$'
snippets = ["typst-version"]
render = "{{ content | unwrap }}"
```

## `tagline`

```markdown
Animo powers both dynamic HTML and static PDF presentations.
```

## `keywords`

```text
animation
beamer
handout
HTML
presentation
reproducibility
reproducible research
slide
slides
slipshow
talk
typst
```

## `version`

The version of the package, as the `version` field of `typst.toml` declares it.

## `typst-version`

The typst release the package is compiled and tested with,
as the `compiler` field of `typst.toml` declares it.
