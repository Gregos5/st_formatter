"""Column-alignment passes: consecutive `:=`, consecutive `=>`, and
consecutive trailing `(* ... *)` comments.

Runs after indent.py, so leading indentation is already final. Each pass
re-tokenizes the current text (cheap at this file scale) and works purely
by splicing whitespace between two token boundaries on a line -- it never
touches the operator token, the comment token, or anything else.
"""
from __future__ import annotations

from .blocks import NestingWalker, is_case_label_line
from .regions import Regions, detect
from .tokenizer import Token, TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.EOF)

# Block kinds whose body lines are `name : type` declarations -- the only
# place a bare `:` gets its spacing normalized to exactly one space on
# each side. Everything else that ever carries a bare `:` (CASE labels,
# ACTION/TYPE/FUNCTION headers) is left exactly as written.
_DECL_COLON_CONTEXTS = {"VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_GLOBAL", "STRUCT"}

LineInfo = tuple[int, list[Token], int, bool, int]  # (line_no, sig_tokens, leading_width, protected, depth_before)


def _group_lines(tokens: list[Token]) -> dict[int, list[Token]]:
    by_line: dict[int, list[Token]] = {}
    for t in tokens:
        by_line.setdefault(t.line, []).append(t)
    return by_line


def _build_lines_info(text: str) -> tuple[list[str], list[LineInfo], Regions]:
    regions = detect(text)
    tokens = tokenize(text)
    by_line = _group_lines(tokens)
    lines = text.splitlines(keepends=True)

    info: list[LineInfo] = []
    depth = 0
    for line_no in range(1, len(lines) + 1):
        line_toks = by_line.get(line_no, [])
        sig = [t for t in line_toks if t.type not in _NON_SIG]
        width = len(line_toks[0].text) if line_toks and line_toks[0].type == TokenType.WHITESPACE else 0
        protected = regions.is_protected(line_no - 1)
        depth_before = depth
        for t in sig:
            if t.type == TokenType.LPAREN:
                depth += 1
            elif t.type == TokenType.RPAREN:
                depth -= 1
        info.append((line_no, sig, width, protected, depth_before))
    return lines, info, regions


def _deepest_op(sig: list[Token], depth_before: int, wanted: TokenType) -> Token | None:
    """Pick the `:=`/`=>` token that sits at the deepest paren nesting on
    the line -- e.g. on `Result := Foo(Arg := 1)` this returns the inner
    `Arg :=`, the one relevant to call-argument alignment, not the outer
    statement assign.
    """
    depth = depth_before
    best: Token | None = None
    best_depth = -1
    for t in sig:
        if t.type == TokenType.LPAREN:
            depth += 1
        elif t.type == TokenType.RPAREN:
            depth -= 1
        elif t.type in (TokenType.ASSIGN, TokenType.ARROW) and t.type == wanted:
            if depth >= best_depth:
                best = t
                best_depth = depth
    return best


def _get_assign_op(sig: list[Token], depth_before: int = 0) -> Token | None:
    if not sig or (len(sig) == 1 and sig[0].type == TokenType.COMMENT):
        return None
    return _deepest_op(sig, depth_before, TokenType.ASSIGN)


def _get_arrow_op(sig: list[Token], depth_before: int = 0) -> Token | None:
    if not sig or (len(sig) == 1 and sig[0].type == TokenType.COMMENT):
        return None
    return _deepest_op(sig, depth_before, TokenType.ARROW)


def _get_trailing_comment_op(sig: list[Token], depth_before: int = 0) -> Token | None:
    if len(sig) < 2 or sig[-1].type != TokenType.COMMENT:
        return None
    return sig[-1]


def _get_decl_colon(sig: list[Token]) -> Token | None:
    for idx, t in enumerate(sig):
        if t.type != TokenType.COLON or idx == 0:
            continue
        nxt = sig[idx + 1] if idx + 1 < len(sig) else None
        if nxt is not None and nxt.type == TokenType.COLON:
            continue
        return t
    return None


def _run_decl_colon_pass(text: str) -> str:
    """Collapse the whitespace around a `name : type` declaration colon to
    exactly one space on each side. Scoped to VAR*/STRUCT block bodies via
    a NestingWalker so CASE labels and POU-header colons are never touched.
    """
    regions = detect(text)
    tokens = tokenize(text)
    by_line = _group_lines(tokens)
    lines = text.splitlines(keepends=True)
    walker = NestingWalker()

    for line_no in range(1, len(lines) + 1):
        line_toks = by_line.get(line_no, [])
        sig = [t for t in line_toks if t.type not in _NON_SIG]
        protected = regions.is_protected(line_no - 1)
        if not sig or protected:
            continue

        in_case = bool(walker.stack) and walker.stack[-1].kind == "CASE"
        context = walker.stack[-1].kind if walker.stack else None
        walker.visit_line(sig)

        if context not in _DECL_COLON_CONTEXTS or is_case_label_line(sig, in_case):
            continue

        colon = _get_decl_colon(sig)
        if colon is None:
            continue

        idx = sig.index(colon)
        prev = sig[idx - 1]
        nxt = sig[idx + 1] if idx + 1 < len(sig) else None
        raw = lines[line_no - 1]
        prev_end = prev.col + len(prev.text)
        if nxt is not None:
            lines[line_no - 1] = raw[:prev_end] + " : " + raw[nxt.col:]
        else:
            lines[line_no - 1] = raw[:prev_end] + " :" + raw[colon.col + 1:]

    return "".join(lines)


def _run_align(lines: list[str], lines_info: list[LineInfo], get_op) -> None:
    i = 0
    n = len(lines_info)
    while i < n:
        line_no, sig, width, protected, depth_before = lines_info[i]
        op = None if protected else get_op(sig, depth_before)
        if op is None:
            i += 1
            continue

        run = [i]
        j = i + 1
        while j < n:
            _, sig2, width2, prot2, depth2 = lines_info[j]
            # A line reached while still inside an open call (depth2 > 0)
            # continues the run regardless of leading width -- the call's
            # own opener line naturally sits at a shallower indent than
            # its continuation-argument lines.
            if prot2 or get_op(sig2, depth2) is None:
                break
            if depth2 == 0 and width2 != width:
                break
            run.append(j)
            j += 1

        target = 0
        for k in run:
            sig_k, depth_k = lines_info[k][1], lines_info[k][4]
            op_k = get_op(sig_k, depth_k)
            idx = sig_k.index(op_k)
            before_end = (sig_k[idx - 1].col + len(sig_k[idx - 1].text)) if idx > 0 else 0
            target = max(target, before_end + 1)

        for k in run:
            line_no_k, sig_k, _, _, depth_k = lines_info[k]
            op_k = get_op(sig_k, depth_k)
            idx = sig_k.index(op_k)
            before_end = (sig_k[idx - 1].col + len(sig_k[idx - 1].text)) if idx > 0 else 0
            pad = max(1, target - before_end)
            raw = lines[line_no_k - 1]
            lines[line_no_k - 1] = raw[:before_end] + (" " * pad) + raw[op_k.col:]

        i = j if j > i else i + 1


def _run_pass(text: str, get_op) -> str:
    lines, info, _ = _build_lines_info(text)
    _run_align(lines, info, get_op)
    return "".join(lines)


def apply(text: str) -> str:
    text = _run_decl_colon_pass(text)
    text = _run_pass(text, _get_assign_op)
    text = _run_pass(text, _get_arrow_op)
    text = _run_pass(text, _get_trailing_comment_op)
    return text
