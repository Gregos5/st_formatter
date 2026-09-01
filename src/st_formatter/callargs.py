"""Call-argument alignment pass: reindents the continuation lines of a
multi-line function/procedure call's argument list.

Two shapes, matched on whether the first argument sits on the opener's own
line or on a new line:

- First argument on a new line: every argument line is indented one level
  deeper than the call statement itself, and a closing paren alone on its
  own line sits back at the call statement's own indent.
- First argument on the same line as `(`: every continuation argument line
  (closing paren included) is aligned to that first argument's column, with
  no space after `(` or before `)`.

Whitespace-only, like indent.py/align.py: only ever rewrites leading
whitespace of continuation lines and the two paren-adjacent gaps. Runs
after indent.py (it needs the call statement's final indent) and before
align.py (so := / => runs can key off the now-uniform indentation).
"""
from __future__ import annotations

from dataclasses import dataclass

from .regions import Regions, detect
from .tokenizer import Token, TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)


@dataclass
class _Call:
    lparen: Token
    rparen: Token
    first_after: Token | None
    last_before: Token | None


def _find_calls(sig: list[Token]) -> list[_Call]:
    calls: list[_Call] = []
    n = len(sig)
    for i, t in enumerate(sig):
        if t.type != TokenType.LPAREN or i == 0:
            continue
        prev = sig[i - 1]
        if prev.type != TokenType.IDENT:
            continue
        if prev.line != t.line or prev.col + len(prev.text) != t.col:
            continue
        depth = 1
        j = i + 1
        while j < n:
            if sig[j].type == TokenType.LPAREN:
                depth += 1
            elif sig[j].type == TokenType.RPAREN:
                depth -= 1
                if depth == 0:
                    first_after = sig[i + 1] if i + 1 < j else None
                    last_before = sig[j - 1] if j - 1 > i else None
                    calls.append(_Call(t, sig[j], first_after, last_before))
                    break
            j += 1
    return calls


def _any_protected(regions: Regions, line_start: int, line_end: int) -> bool:
    return any(regions.is_protected(ln - 1) for ln in range(line_start, line_end + 1))


def _has_multiline_comment(sig: list[Token], line_start: int, line_end: int) -> bool:
    """True if a comment token spanning multiple lines overlaps this range.

    The reindent loops below reset each continuation line's *entire*
    leading run to a fixed width, assuming that run is pure indentation.
    When a multi-line comment's tail actually sits at the start of one of
    those lines, that assumption is wrong and reindenting corrupts the
    comment. Simplest safe fix: leave the whole call untouched.
    """
    return any(
        t.type == TokenType.COMMENT and t.end_line > t.line
        and t.line <= line_end and t.end_line >= line_start
        for t in sig
    )


def _leading_width(raw: str) -> int:
    return len(raw) - len(raw.lstrip(" "))


def _set_leading(raw: str, width: int) -> str:
    return (" " * width) + raw.lstrip(" ")


def _apply_case_new_line(lines: list[str], lparen: Token, rparen: Token, indent_size: int, closer_is_alone: bool) -> None:
    opener_line = lparen.line
    closer_line = rparen.line
    opener_indent = _leading_width(lines[opener_line - 1])
    target_indent = opener_indent + indent_size

    for ln in range(opener_line + 1, closer_line + 1):
        lines[ln - 1] = _set_leading(lines[ln - 1], target_indent)

    if closer_is_alone:
        lines[closer_line - 1] = _set_leading(lines[closer_line - 1], opener_indent)


def _apply_case_same_line(lines: list[str], lparen: Token, rparen: Token) -> None:
    opener_line = lparen.line
    closer_line = rparen.line

    raw_open = lines[opener_line - 1]
    lparen_end = lparen.col + 1
    k = lparen_end
    while k < len(raw_open) and raw_open[k] in (" ", "\t"):
        k += 1
    lines[opener_line - 1] = raw_open[:lparen_end] + raw_open[k:]
    target_col = lparen_end

    orig_leading_close = _leading_width(lines[closer_line - 1])

    for ln in range(opener_line + 1, closer_line + 1):
        lines[ln - 1] = _set_leading(lines[ln - 1], target_col)

    shift = target_col - orig_leading_close
    new_rparen_col = rparen.col + shift
    raw_close = lines[closer_line - 1]
    m = new_rparen_col
    while m > 0 and raw_close[m - 1] in (" ", "\t"):
        m -= 1
    lines[closer_line - 1] = raw_close[:m] + raw_close[new_rparen_col:]


def apply(text: str, indent_size: int = 2) -> str:
    done_lines: set[int] = set()

    while True:
        regions = detect(text)
        sig = [t for t in tokenize(text) if t.type not in _NON_SIG]
        lines = text.splitlines(keepends=True)

        target: _Call | None = None
        for c in _find_calls(sig):
            if c.lparen.line == c.rparen.line or c.first_after is None:
                continue
            if c.lparen.line in done_lines:
                continue
            if _any_protected(regions, c.lparen.line, c.rparen.line):
                done_lines.add(c.lparen.line)
                continue
            if _has_multiline_comment(sig, c.lparen.line, c.rparen.line):
                done_lines.add(c.lparen.line)
                continue
            target = c
            break

        if target is None:
            return text

        if target.first_after.line == target.lparen.line:
            _apply_case_same_line(lines, target.lparen, target.rparen)
        else:
            closer_is_alone = target.last_before is None or target.last_before.line != target.rparen.line
            _apply_case_new_line(lines, target.lparen, target.rparen, indent_size, closer_is_alone)

        done_lines.add(target.lparen.line)
        text = "".join(lines)
