"""Hand-rolled lexer for Bodas/CoDeSys 2.3 IEC 61131-3 Structured Text.

Tokenizes with a positional scan (not one big regex) because CoDeSys allows
*nested* block comments -- confirmed by every file's own
`(* @NESTEDCOMMENTS := 'Yes' *)` header line -- which a non-greedy regex
would truncate at the first inner `*)`.

The tokenizer is a total, lossless partition of the input: concatenating
every token's `.text` in order reproduces the original text exactly
(`"".join(t.text for t in tokenize(text)) == text`). That property is what
lets the rest of the formatter treat whitespace as the only thing it is
ever allowed to rewrite.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD = auto()
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    ASSIGN = auto()  # :=
    ARROW = auto()  # =>
    COLON = auto()
    SEMI = auto()
    COMMA = auto()
    DOT = auto()
    DOTDOT = auto()  # ..
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    OPERATOR = auto()
    COMMENT = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    OTHER = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    text: str
    line: int  # 1-based line the token starts on
    col: int  # 0-based column the token starts on, within its start line
    end_line: int  # 1-based line the token ends on (comments may span lines)


KEYWORDS = {
    "PROGRAM", "END_PROGRAM",
    "FUNCTION", "END_FUNCTION",
    "FUNCTION_BLOCK", "END_FUNCTION_BLOCK",
    "ACTION", "END_ACTION",
    "TYPE", "END_TYPE",
    "STRUCT", "END_STRUCT",
    "VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_GLOBAL",
    "CONSTANT", "RETAIN", "END_VAR",
    "IF", "THEN", "ELSIF", "ELSE", "END_IF",
    "CASE", "OF", "END_CASE",
    "FOR", "TO", "BY", "DO", "END_FOR",
    "WHILE", "END_WHILE",
    "REPEAT", "UNTIL", "END_REPEAT",
    "AND", "OR", "XOR", "NOT", "MOD",
    "RETURN", "EXIT", "AT",
}

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BASED_NUMBER_RE = re.compile(r"\d+#[0-9A-Fa-f_]+")
_NUMBER_RE = re.compile(r"\d[\d_]*(\.\d[\d_]*)?([eE][+-]?\d+)?")
_STRING_RE = re.compile(r"'(?:[^'\r\n]|'')*'")
_WS_RE = re.compile(r"[ \t]+")

_MULTI_OPS = (":=", "=>", "<=", ">=", "<>", "..")
_MULTI_OP_TYPES = {
    ":=": TokenType.ASSIGN,
    "=>": TokenType.ARROW,
    "..": TokenType.DOTDOT,
}
_SINGLE_PUNCT = {
    ":": TokenType.COLON,
    ";": TokenType.SEMI,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
}
_OPERATOR_CHARS = set("+-*/=<>^&")


def tokenize(text: str) -> list[Token]:
    """Tokenize the full text of one .EXP file (or a snippet of one).

    `text` should be read with `newline=''` so CRLF line endings are
    preserved verbatim as NEWLINE token text rather than being translated
    by Python's universal-newline handling.
    """
    tokens: list[Token] = []
    i = 0
    n = len(text)
    line = 1
    col = 0

    def advance(count: int) -> None:
        nonlocal i, line, col
        end = i + count
        while i < end:
            if text[i] == "\n":
                line += 1
                col = 0
            else:
                col += 1
            i += 1

    while i < n:
        ch = text[i]
        start_line, start_col = line, col

        if ch == "\r" or ch == "\n":
            nl = text[i:i + 2] if ch == "\r" and i + 1 < n and text[i + 1] == "\n" else ch
            advance(len(nl))
            tokens.append(Token(TokenType.NEWLINE, nl, start_line, start_col, line))
            continue

        m = _WS_RE.match(text, i)
        if m:
            ws = m.group(0)
            advance(len(ws))
            tokens.append(Token(TokenType.WHITESPACE, ws, start_line, start_col, line))
            continue

        if text.startswith("(*", i):
            depth = 0
            j = i
            while j < n:
                if text.startswith("(*", j):
                    depth += 1
                    j += 2
                    continue
                if text.startswith("*)", j):
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                    continue
                j += 1
            comment_text = text[i:j]
            advance(len(comment_text))
            tokens.append(Token(TokenType.COMMENT, comment_text, start_line, start_col, line))
            continue

        m = _STRING_RE.match(text, i)
        if m:
            s = m.group(0)
            advance(len(s))
            tokens.append(Token(TokenType.STRING, s, start_line, start_col, line))
            continue

        m = _BASED_NUMBER_RE.match(text, i)
        if m:
            s = m.group(0)
            advance(len(s))
            tokens.append(Token(TokenType.NUMBER, s, start_line, start_col, line))
            continue

        if ch.isdigit():
            m = _NUMBER_RE.match(text, i)
            s = m.group(0)
            advance(len(s))
            tokens.append(Token(TokenType.NUMBER, s, start_line, start_col, line))
            continue

        matched_op = next((op for op in _MULTI_OPS if text.startswith(op, i)), None)
        if matched_op:
            ttype = _MULTI_OP_TYPES.get(matched_op, TokenType.OPERATOR)
            advance(len(matched_op))
            tokens.append(Token(ttype, matched_op, start_line, start_col, line))
            continue

        m = _IDENT_RE.match(text, i)
        if m:
            s = m.group(0)
            ttype = TokenType.KEYWORD if s.upper() in KEYWORDS else TokenType.IDENT
            advance(len(s))
            tokens.append(Token(ttype, s, start_line, start_col, line))
            continue

        if ch in _SINGLE_PUNCT:
            advance(1)
            tokens.append(Token(_SINGLE_PUNCT[ch], ch, start_line, start_col, line))
            continue

        if ch in _OPERATOR_CHARS:
            advance(1)
            tokens.append(Token(TokenType.OPERATOR, ch, start_line, start_col, line))
            continue

        # Opaque/undecodable byte (e.g. a stray corrupted UTF-8 sequence
        # already baked into the file) -- absorbed verbatim, never "fixed".
        advance(1)
        tokens.append(Token(TokenType.OTHER, ch, start_line, start_col, line))

    tokens.append(Token(TokenType.EOF, "", line, col, line))
    return tokens
