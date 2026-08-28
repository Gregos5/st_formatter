"""Equivalence checking: formatting must never change program semantics.

Three independent checks compare the original and formatted text; a
formatted file is only accepted if all three pass. There is no accessible
headless Bodas/CoDeSys 2.3 compiler in this environment, so this is a
self-contained stand-in: it proves no code token was added, removed,
reordered, or renamed, that block nesting is structurally identical, and
that every IDE metadata region round-tripped byte-exact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .blocks import nesting_events
from .regions import detect
from .tokenizer import TokenType, tokenize

_NON_SIG = (TokenType.WHITESPACE, TokenType.NEWLINE)


@dataclass
class ValidationResult:
    ok: bool
    failures: list = field(default_factory=list)


def _structural_tokens(text: str):
    return [(t.type, t.text) for t in tokenize(text) if t.type not in _NON_SIG]


def _first_divergence(a: list, b: list) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def check(original_text: str, formatted_text: str) -> ValidationResult:
    failures: list = []

    orig_struct = _structural_tokens(original_text)
    fmt_struct = _structural_tokens(formatted_text)
    if orig_struct != fmt_struct:
        idx = _first_divergence(orig_struct, fmt_struct)
        failures.append(
            f"Check A (token-stream equality) failed at token #{idx}: "
            f"original={orig_struct[max(0, idx - 2):idx + 3]!r} "
            f"formatted={fmt_struct[max(0, idx - 2):idx + 3]!r}"
        )

    orig_events = nesting_events(tokenize(original_text))
    fmt_events = nesting_events(tokenize(formatted_text))
    if orig_events != fmt_events:
        idx = _first_divergence(orig_events, fmt_events)
        failures.append(
            f"Check B (nesting-tree equality) failed at event #{idx}: "
            f"original={orig_events[max(0, idx - 2):idx + 3]} "
            f"formatted={fmt_events[max(0, idx - 2):idx + 3]}"
        )

    orig_regions = detect(original_text)
    fmt_regions = detect(formatted_text)
    if orig_regions.file_class != fmt_regions.file_class:
        failures.append(
            "Check C (protected-region identity) failed: file class changed "
            f"from {orig_regions.file_class} to {fmt_regions.file_class}"
        )
    else:
        orig_header = "".join(orig_regions.lines[:orig_regions.header_end])
        fmt_header = "".join(fmt_regions.lines[:fmt_regions.header_end])
        if orig_header != fmt_header:
            failures.append("Check C (protected-region identity) failed: header block changed")

        orig_marked = "".join(orig_regions.lines[i] for i in sorted(orig_regions.protected))
        fmt_marked = "".join(fmt_regions.lines[i] for i in sorted(fmt_regions.protected))
        if orig_marked != fmt_marked:
            failures.append(
                "Check C (protected-region identity) failed: "
                "@END_DECLARATION/@TEXT_IMPLEMENTATION marker(s) changed"
            )

        orig_footer = (
            "".join(orig_regions.lines[orig_regions.footer_start:])
            if orig_regions.footer_start is not None else ""
        )
        fmt_footer = (
            "".join(fmt_regions.lines[fmt_regions.footer_start:])
            if fmt_regions.footer_start is not None else ""
        )
        if orig_footer != fmt_footer:
            failures.append("Check C (protected-region identity) failed: footer block changed")

    return ValidationResult(ok=not failures, failures=failures)
