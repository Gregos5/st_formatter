"""Condition alignment pass: aligns multi-line IF/ELSIF/WHILE/UNTIL
conditions joined by AND/OR/XOR to the column of the first condition
token, and collapses inter-token spacing inside the condition to exactly
one space.

Whitespace-only, like indent.py/align.py: never adds, removes, reorders,
or renames a token. Runs after indent.py (it needs the opener keyword's
final column) and before align.py.
"""
from __future__ import annotations

from .regions import Regions, detect
from .tokenizer import Token, TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)
_OPENER_TERMINATOR = {"IF": "THEN", "ELSIF": "THEN", "WHILE": "DO"}
_LOGICAL = {"AND", "OR", "XOR"}


def _find_condition_spans(sig: list[Token]) -> list[tuple[int, int]]:
    """Return (start, end) index pairs into `sig`: sig[start:end] is one
    condition's own tokens (opener keyword and terminator excluded)."""
    spans: list[tuple[int, int]] = []
    n = len(sig)
    i = 0
    while i < n:
        t = sig[i]
        if t.type == TokenType.KEYWORD:
            kw = t.text.upper()
            if kw in _OPENER_TERMINATOR or kw == "UNTIL":
                terminator_kw = _OPENER_TERMINATOR.get(kw)
                start = i + 1
                depth = 0
                j = start
                while j < n:
                    tj = sig[j]
                    if tj.type == TokenType.LPAREN:
                        depth += 1
                    elif tj.type == TokenType.RPAREN:
                        depth = max(0, depth - 1)
                    elif depth == 0 and (
                        (terminator_kw and tj.type == TokenType.KEYWORD and tj.text.upper() == terminator_kw)
                        or (terminator_kw is None and tj.type == TokenType.SEMI)
                    ):
                        spans.append((start, j))
                        i = j
                        break
                    j += 1
        i += 1
    return spans


def _has_top_level_logical(cond: list[Token]) -> bool:
    depth = 0
    for t in cond:
        if t.type == TokenType.LPAREN:
            depth += 1
        elif t.type == TokenType.RPAREN:
            depth = max(0, depth - 1)
        elif depth == 0 and t.type == TokenType.KEYWORD and t.text.upper() in _LOGICAL:
            return True
    return False


def _any_protected(regions: Regions, line_start: int, line_end: int) -> bool:
    return any(regions.is_protected(ln - 1) for ln in range(line_start, line_end + 1))


def _rewrite_condition(lines: list[str], opener: Token, cond: list[Token], terminator: Token | None) -> None:
    target_col = opener.col + len(opener.text) + 1

    include_terminator = terminator is not None and terminator.line == cond[-1].line
    relevant = [opener] + cond + ([terminator] if include_terminator else [])

    by_line: dict[int, list[Token]] = {}
    for t in relevant:
        by_line.setdefault(t.line, []).append(t)

    for line_no, toks in by_line.items():
        if any(t.type == TokenType.COMMENT for t in toks):
            continue
        raw = lines[line_no - 1]
        prefix = raw[:toks[0].col] if line_no == opener.line else " " * target_col
        body = " ".join(t.text for t in toks)
        last = toks[-1]
        suffix = raw[last.col + len(last.text):]
        lines[line_no - 1] = prefix + body + suffix


def apply(text: str) -> str:
    regions = detect(text)
    sig = [t for t in tokenize(text) if t.type not in _NON_SIG]
    lines = text.splitlines(keepends=True)

    for start, end in _find_condition_spans(sig):
        opener = sig[start - 1]
        cond = sig[start:end]
        if not cond or opener.line == cond[-1].line:
            continue
        if not _has_top_level_logical(cond):
            continue
        terminator = sig[end] if end < len(sig) else None
        last_line = terminator.line if (terminator is not None and terminator.line == cond[-1].line) else cond[-1].line
        if _any_protected(regions, opener.line, last_line):
            continue
        _rewrite_condition(lines, opener, cond, terminator)

    return "".join(lines)
