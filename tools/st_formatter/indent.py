"""Reindentation pass: recomputes each content line's leading indentation
from block-keyword nesting (blocks.py).

This is a line-based, non-reflowing transform: it never merges/splits
lines or reorders tokens. It only ever rewrites WHITESPACE token text (or
inserts a new leading-whitespace token where a line previously had none) --
every other token (keyword/identifier/number/string/comment/operator/
newline) is always re-emitted verbatim. That invariant is what makes the
validator's Check A (structural token-stream equality) hold by
construction.
"""
from __future__ import annotations

from .blocks import NestingWalker, significant
from .regions import Regions
from .tokenizer import Token, TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)


def _group_lines(tokens: list[Token]) -> dict[int, list[Token]]:
    by_line: dict[int, list[Token]] = {}
    for t in tokens:
        by_line.setdefault(t.line, []).append(t)
    return by_line


def _paren_depth_at_line_start(tokens: list[Token]) -> dict[int, int]:
    depth_at_start: dict[int, int] = {}
    depth = 0
    seen_line = 0
    for t in tokens:
        if t.line != seen_line:
            depth_at_start[t.line] = depth
            seen_line = t.line
        if t.type == TokenType.LPAREN:
            depth += 1
        elif t.type == TokenType.RPAREN:
            depth = max(0, depth - 1)
    return depth_at_start


def _reindent_tokens(tokens: list[Token], regions: Regions, indent_size: int, tab_width: int) -> list[Token]:
    by_line = _group_lines(tokens)
    if not by_line:
        return tokens
    depth_at_start = _paren_depth_at_line_start(tokens)
    walker = NestingWalker()

    out: list[Token] = []
    for line_no in range(1, max(by_line) + 1):
        line_toks = by_line.get(line_no)
        if not line_toks:
            continue

        sig = significant(line_toks)
        protected = regions.is_protected(line_no - 1)
        continuation = depth_at_start.get(line_no, 0) > 0

        if not sig or protected:
            out.extend(line_toks)
            continue

        level = None if continuation else walker.visit_line(sig)

        has_leading_ws = line_toks[0].type == TokenType.WHITESPACE
        if has_leading_ws:
            lead = line_toks[0]
            new_text = (" " * (level * indent_size)) if level is not None else lead.text.expandtabs(tab_width)
            out.append(Token(TokenType.WHITESPACE, new_text, lead.line, 0, lead.line))
            rest = line_toks[1:]
        else:
            if level is not None and level > 0:
                out.append(Token(TokenType.WHITESPACE, " " * (level * indent_size), line_no, 0, line_no))
            rest = line_toks

        for t in rest:
            if t.type == TokenType.WHITESPACE and "\t" in t.text:
                out.append(Token(TokenType.WHITESPACE, t.text.replace("\t", " "), t.line, t.col, t.end_line))
            else:
                out.append(t)

    return out


def apply(text: str, regions: Regions, indent_size: int = 2, tab_width: int = 4) -> str:
    tokens = tokenize(text)
    new_tokens = _reindent_tokens(tokens, regions, indent_size, tab_width)
    return "".join(t.text for t in new_tokens)
