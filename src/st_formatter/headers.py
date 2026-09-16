"""Header-separator pass: normalizes the whitespace between an `ACTION`
keyword and its name, e.g. `ACTION Foo:` -> `ACTION\tFoo:`.

Bodas' own re-export of an .EXP file always separates `ACTION` from its
name with a single tab, never a space, so a file round-tripped through
Bodas' design tool shows a diff on every `ACTION` header if this isn't
normalized on our side first. Scoped to bare `ACTION <name>:` header
lines only -- PROGRAM/FUNCTION/TYPE/etc. headers, and any line inside a
protected metadata region, are left untouched.
"""
from __future__ import annotations

from .regions import detect
from .tokenizer import Token, TokenType, tokenize

_SEPARATOR_TEXT = {"space": " ", "tab": "\t"}


def _group_lines(tokens: list[Token]) -> dict[int, list[Token]]:
    by_line: dict[int, list[Token]] = {}
    for t in tokens:
        by_line.setdefault(t.line, []).append(t)
    return by_line


def apply(text: str, separator: str = "space") -> str:
    """Rewrite the whitespace between `ACTION` and its name to exactly one
    space or one tab, per `separator` ("space" or "tab")."""
    sep = _SEPARATOR_TEXT.get(separator)
    if sep is None:
        raise ValueError(f"action_separator must be 'space' or 'tab', got {separator!r}")

    regions = detect(text)
    tokens = tokenize(text)
    by_line = _group_lines(tokens)
    lines = text.splitlines(keepends=True)

    for line_no in range(1, len(lines) + 1):
        line_toks = by_line.get(line_no, [])
        if not line_toks or regions.is_protected(line_no - 1):
            continue

        header = line_toks[0]
        if header.type != TokenType.KEYWORD or header.text.upper() != "ACTION":
            continue
        if len(line_toks) < 2 or line_toks[1].type != TokenType.WHITESPACE:
            continue

        ws = line_toks[1]
        if ws.text == sep:
            continue

        raw = lines[line_no - 1]
        start = ws.col
        end = start + len(ws.text)
        lines[line_no - 1] = raw[:start] + sep + raw[end:]

    return "".join(lines)
