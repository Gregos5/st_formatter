# st_formatter
Structured text formatter module (IEC 61131-3 Structured Text)

## Files 
Built (tools/st_formatter/, plus tools/format_st.py/tools/format_st.bat, tests/st_formatter/):

tokenizer.py — hand-rolled lexer (handles nested (* *) comments, :=/=>, based-literal numbers), lossless (every byte round-trips).
regions.py — detects and protects Bodas/CoDeSys IDE metadata (header block, @END_DECLARATION, @TEXT_IMPLEMENTATION, @OBJECT_END/@CONNECTIONS footer) and passes LIBRARY manifest files through untouched.
blocks.py / indent.py — block-nesting reindent (2-space, no tabs), confirmed against real files: PROGRAM/ACTION/TYPE bodies stay flush-left, VAR*/STRUCT/IF/CASE/FOR/WHILE genuinely indent.
align.py — aligns consecutive :=, =>, and trailing comments in contiguous runs.
validator.py — the compile-equivalence stand-in: token-stream equality, nesting-tree equality, and protected-region byte-identity; a failing file is discarded and left untouched.
cli.py — python -m tools.st_formatter <paths> [--write|--check] [--diff] [--report ...], safe dry-run default, never touches git.