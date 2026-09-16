"""Blank-line pass: trims blank lines immediately before a POU-level
block closer, e.g. a run of blank lines right before `END_ACTION` is
removed entirely.

Scoped to the closers that pair with a POU-level opener (ACTION, PROGRAM,
FUNCTION, FUNCTION_BLOCK) -- VAR/IF/CASE/... blocks are left alone, since
this is only ever observed at POU body boundaries in Bodas' own
re-export.
"""
from __future__ import annotations

from .regions import detect
from .tokenizer import Token, TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)
_POU_CLOSERS = {"END_ACTION", "END_PROGRAM", "END_FUNCTION", "END_FUNCTION_BLOCK"}


def _group_lines(tokens: list[Token]) -> dict[int, list[Token]]:
    by_line: dict[int, list[Token]] = {}
    for t in tokens:
        by_line.setdefault(t.line, []).append(t)
    return by_line


def apply(text: str) -> str:
    regions = detect(text)
    tokens = tokenize(text)
    by_line = _group_lines(tokens)
    lines = text.splitlines(keepends=True)

    to_remove: set = set()
    for line_no in range(1, len(lines) + 1):
        line_toks = by_line.get(line_no, [])
        sig = [t for t in line_toks if t.type not in _NON_SIG]
        if not sig or sig[0].type != TokenType.KEYWORD or sig[0].text.upper() not in _POU_CLOSERS:
            continue

        j = line_no - 2  # 0-based index of the line immediately above this closer
        while j >= 0 and lines[j].strip() == "" and not regions.is_protected(j):
            to_remove.add(j)
            j -= 1

    if not to_remove:
        return text
    return "".join(line for idx, line in enumerate(lines) if idx not in to_remove)
