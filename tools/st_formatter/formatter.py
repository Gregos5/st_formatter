"""Orchestrates formatting one file's text: classify -> indent -> align ->
validate. Never touches disk itself -- callers (cli.py) decide that."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import align, indent, validator
from .regions import FileClass, detect


@dataclass
class FormatResult:
    changed: bool
    ok: bool
    formatted_text: str
    failures: list = field(default_factory=list)


def format_text(
    original_text: str,
    indent_size: int = 2,
    tab_width: int = 4,
    do_indent: bool = True,
    do_align: bool = True,
) -> FormatResult:
    regions = detect(original_text)
    if regions.file_class == FileClass.LIBRARY_MANIFEST:
        return FormatResult(changed=False, ok=True, formatted_text=original_text)

    text = original_text
    if do_indent:
        text = indent.apply(text, regions, indent_size=indent_size, tab_width=tab_width)
    if do_align:
        text = align.apply(text)

    result = validator.check(original_text, text)
    if not result.ok:
        return FormatResult(changed=False, ok=False, formatted_text=original_text, failures=result.failures)

    return FormatResult(changed=(text != original_text), ok=True, formatted_text=text)
