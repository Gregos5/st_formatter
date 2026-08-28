# st-formatter

A clang-format-style formatter for IEC 61131-3 Structured Text: plain `.st`
source and Bodas/CoDeSys 2.3 `.EXP` exports.

It reindents block nesting, aligns runs of consecutive `:=`, `=>`, and
trailing comments, and never touches anything else. Every formatted file is
checked against the original before being accepted:

- **Token-stream equality** — no code token was added, removed, reordered, or renamed.
- **Nesting-tree equality** — block structure (`IF`/`CASE`/`FOR`/... nesting) is identical.
- **Protected-region identity** — any Bodas/CoDeSys IDE metadata (`(* @PATH := ... *)`,
  `@END_DECLARATION`, `@TEXT_IMPLEMENTATION`, `@OBJECT_END`/`@CONNECTIONS` footers,
  `LIBRARY` manifests) round-trips byte-exact.

A file that fails any check is left untouched and reported as a failure —
formatting never risks changing program meaning.

## Install

**PyPI** (needs Python 3.11+):
```
pip install st-formatter
```

**Standalone executable** (no Python required): download the binary for your
OS from the [Releases page](https://github.com/Gregos5/st_formatter/releases) —
`st-formatter-vX.Y.Z-linux-x86_64`, `-windows-x86_64.exe`, or `-macos-arm64`.

**From source** (development):
```
git clone https://github.com/Gregos5/st_formatter.git
cd st_formatter
pip install -e .
```

## Quick start

```
st-formatter --check path/to/project      # dry run (default) — reports files that would change
st-formatter --write path/to/project      # apply formatting in place
st-formatter --diff path/to/a_file.st     # print a unified diff
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | clean — nothing to format |
| 1 | one or more files would be reformatted (only in dry-run mode) |
| 2 | one or more files failed semantic-equivalence validation (left untouched) |
| 3 | fatal error (bad path, bad config, ...) |

Run `st-formatter --check <path>` in CI to gate a build on formatting.

## Configuration

`st-formatter` looks for a config file the same way `black`/`ruff` do:
starting from the target path(s), it walks upward looking first for a
dedicated `.stformat.toml`, then a `[tool.st_formatter]` table in
`pyproject.toml`, stopping at the first match. CLI flags always override
whatever the config file says. Use `--config PATH` to point at a specific
file instead of auto-discovery.

`.stformat.toml`:
```toml
indent_size = 2
tab_width = 4
indent = true
align = true
extensions = [".st", ".exp"]
exclude = ["**/build/**", "**/_generated/**"]
```

Or inside your project's own `pyproject.toml`:
```toml
[tool.st_formatter]
indent_size = 2
tab_width = 4
indent = true
align = true
extensions = [".st", ".exp"]
exclude = ["**/build/**"]
```

See [examples/.stformat.toml](examples/.stformat.toml) for a copy-pasteable starting point.

| Option | Default | Meaning |
|---|---|---|
| `indent_size` | `2` | Spaces per nesting level |
| `tab_width` | `4` | Width used when normalizing existing tabs |
| `indent` | `true` | Run the reindentation pass |
| `align` | `true` | Run the `:=`/`=>`/comment alignment pass |
| `extensions` | `[".st", ".exp"]` | Extensions treated as ST source when scanning a directory |
| `exclude` | `[]` | Glob patterns (matched against POSIX-style relative paths) to skip when scanning a directory |

Extension filtering only applies when you point `st-formatter` at a
**directory**; a file passed explicitly by path is always processed
regardless of its extension. `exclude` likewise only applies to
directory-discovered files, never to an explicitly named file.

## CI integration

**GitHub Actions** — see [examples/github-actions-consumer.yml](examples/github-actions-consumer.yml):
```yaml
- run: pip install st-formatter
- run: st-formatter --check src/plc
```

**Azure DevOps** — see [examples/azure-pipelines-consumer.yml](examples/azure-pipelines-consumer.yml):
```yaml
- task: UsePythonVersion@0
  inputs: { versionSpec: '3.11' }
- script: pip install st-formatter
- script: st-formatter --check src/plc
```

Both gate the build: `--check` exits non-zero if any file would be reformatted.

## Development

```
pip install -e .
python -m unittest discover -s tests -t . -v
```

(`-t .` matters: it keeps the `tests/st_formatter/` test package from
shadowing the installed `st_formatter` package during discovery.)

Repo layout:

```
src/st_formatter/
  tokenizer.py   — hand-rolled lexer (handles nested (* *) comments, :=/=>, based-literal numbers), lossless round-trip
  regions.py     — detects and protects Bodas/CoDeSys IDE metadata; content-based, so plain .st files with no
                    metadata format normally with zero special-casing
  blocks.py      — block-nesting walker (openers/closers, indent levels)
  indent.py      — reindentation pass driven by blocks.py
  align.py       — aligns consecutive :=, =>, and trailing comments in contiguous runs
  validator.py   — the compile-equivalence stand-in described above
  config.py      — .stformat.toml / pyproject.toml discovery, precedence, and merging
  cli.py         — the st-formatter command
tests/st_formatter/  — unittest suite (run with the command above)
packaging/           — PyInstaller entry point for standalone executable builds
examples/            — copy-pasteable config and CI snippets
```

## License

GPLv3-or-later — see [LICENSE](LICENSE).
