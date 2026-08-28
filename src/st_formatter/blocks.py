"""Block-nesting analysis, shared by indent.py (reindentation) and
validator.py (Check B: nesting-tree equality).

Confirmed against real usage in the repo: PROGRAM/ACTION/TYPE/FUNCTION
bodies sit flush with their header (they are POU-level wrappers spanning
almost the whole file), while VAR*/STRUCT/IF/CASE/FOR/WHILE/REPEAT bodies
are genuinely indented one level relative to their header.
"""
from __future__ import annotations

from dataclasses import dataclass

from .tokenizer import Token, TokenType

# Opener keyword -> its closer keyword. VAR_INPUT/VAR_OUTPUT/VAR_IN_OUT/
# VAR_GLOBAL all close on END_VAR, matching real usage.
OPENER_TO_CLOSER = {
    "PROGRAM": "END_PROGRAM",
    "FUNCTION": "END_FUNCTION",
    "FUNCTION_BLOCK": "END_FUNCTION_BLOCK",
    "ACTION": "END_ACTION",
    "TYPE": "END_TYPE",
    "STRUCT": "END_STRUCT",
    "VAR": "END_VAR",
    "VAR_INPUT": "END_VAR",
    "VAR_OUTPUT": "END_VAR",
    "VAR_IN_OUT": "END_VAR",
    "VAR_GLOBAL": "END_VAR",
    "IF": "END_IF",
    "CASE": "END_CASE",
    "FOR": "END_FOR",
    "WHILE": "END_WHILE",
    "REPEAT": "END_REPEAT",
}
OPENER_KEYWORDS = set(OPENER_TO_CLOSER)
CLOSER_KEYWORDS = set(OPENER_TO_CLOSER.values())

# Openers whose own body is NOT indented relative to their header line.
FLAT_OPENERS = {"PROGRAM", "FUNCTION", "FUNCTION_BLOCK", "ACTION", "TYPE"}

MID_KEYWORDS = {"THEN", "ELSE", "ELSIF", "UNTIL"}

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)


@dataclass
class Frame:
    kind: str
    closer: str
    header_level: int
    body_level: int
    content_level: int


def significant(tokens: list[Token]) -> list[Token]:
    return [t for t in tokens if t.type not in _NON_SIG]


def is_case_label_line(sig: list[Token], in_case: bool) -> bool:
    """A CASE label line: a comma/`..`-separated list of idents/numbers
    followed by a bare `:` (not `:=`), as the first thing on the line."""
    if not in_case or not sig:
        return False
    saw_value = False
    for t in sig:
        if t.type in (TokenType.IDENT, TokenType.NUMBER):
            saw_value = True
        elif t.type in (TokenType.DOTDOT, TokenType.COMMA):
            continue
        elif t.type == TokenType.COLON:
            return saw_value
        else:
            return False
    return False


class NestingWalker:
    """Walks a file's content lines in order, maintaining the block-frame
    stack, and returns the indentation level for each line visited."""

    def __init__(self) -> None:
        self.stack: list[Frame] = []

    def current_level(self) -> int:
        return self.stack[-1].content_level if self.stack else 0

    def visit_line(self, sig: list[Token]) -> int:
        if not sig:
            return self.current_level()

        tok0 = sig[0]
        kw0 = tok0.text.upper() if tok0.type == TokenType.KEYWORD else None

        if kw0 in OPENER_KEYWORDS:
            level = self.current_level()
            body_level = level if kw0 in FLAT_OPENERS else level + 1
            self.stack.append(Frame(
                kind=kw0, closer=OPENER_TO_CLOSER[kw0],
                header_level=level, body_level=body_level,
                content_level=body_level,
            ))
            return level

        if kw0 in CLOSER_KEYWORDS:
            if self.stack and self.stack[-1].closer == kw0:
                return self.stack.pop().header_level
            # Malformed/mismatched nesting: best-effort, never crash.
            return self.current_level()

        in_case = bool(self.stack) and self.stack[-1].kind == "CASE"
        if kw0 in MID_KEYWORDS or is_case_label_line(sig, in_case):
            if self.stack:
                level = self.stack[-1].body_level
                self.stack[-1].content_level = self.stack[-1].body_level + 1
            else:
                level = 0
            return level

        return self.current_level()


def nesting_events(tokens: list[Token]) -> list[str]:
    """Flat OPEN/CLOSE event sequence from a token stream's KEYWORD
    tokens alone -- independent of line/indentation, used by the
    validator to assert nesting is unchanged by formatting."""
    events: list[str] = []
    for t in tokens:
        if t.type != TokenType.KEYWORD:
            continue
        kw = t.text.upper()
        if kw in OPENER_KEYWORDS:
            events.append(f"OPEN:{kw}")
        elif kw in CLOSER_KEYWORDS:
            events.append(f"CLOSE:{kw}")
    return events
