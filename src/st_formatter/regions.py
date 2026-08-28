"""Protected-region detection.

Every source `.EXP` file carries CoDeSys/Bodas IDE metadata disguised as
`(* @KEY := 'value' *)` comments: a header block, an `@END_DECLARATION`/
`@TEXT_IMPLEMENTATION` marker, and a footer `@OBJECT_END`/`@CONNECTIONS`
block. `scripts/export_from_bodas.py` parses the header's `@PATH` and each
file's declaration keyword to rebuild the IDE's folder tree, so these
regions must round-trip byte-exact -- the indent/align passes must never
see or touch them. Some `.EXP` files are pure `LIBRARY` manifests (no ST
code at all) and must be passed through completely untouched.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Mirrors scripts/export_from_bodas.py's KEYWORD_TO_CATEGORY/KEYWORD_RE so
# LIBRARY-manifest detection never drifts from what the export/import
# round-trip tooling already depends on.
_DECLARATION_KEYWORDS = (
    "TYPE", "PROGRAM", "FUNCTION_BLOCK", "FUNCTION", "ACTION",
    "LIBRARY", "VAR_GLOBAL", "RESOURCE", "PLC_CONFIGURATION", "_ALARMCONFIG",
)
_KEYWORD_LINES_TO_SCAN = 60
_DECLARATION_KEYWORD_RE = re.compile(
    r"^\s*(" + "|".join(_DECLARATION_KEYWORDS) + r")\b", re.IGNORECASE
)

# A single-line IDE metadata comment, e.g. `(* @PATH := '\/Bas' *)` or
# `(* @NESTEDCOMMENTS := 'Yes' *)`. Deliberately permissive (no requirement
# that `:=` be present) so an unfamiliar `@KEY` variant is still protected
# rather than silently falling out of the header block.
_HEADER_KEY_LINE_RE = re.compile(r"^\(\*\s*@[A-Za-z_][A-Za-z0-9_]*\b.*\*\)[ \t]*\r?\n?$")
_END_DECLARATION_LINE_RE = re.compile(r"^\(\*\s*@END_DECLARATION\s*:=.*\*\)[ \t]*\r?\n?$")
_TEXT_IMPLEMENTATION_LINE_RE = re.compile(r"^\(\*\s*@TEXT_IMPLEMENTATION\s*:=.*\*\)[ \t]*\r?\n?$")
_OBJECT_END_LINE_RE = re.compile(r"^\(\*\s*@OBJECT_END\s*:=.*\*\)[ \t]*\r?\n?$")


class FileClass:
    ST_SOURCE = "ST_SOURCE"
    LIBRARY_MANIFEST = "LIBRARY_MANIFEST"


@dataclass
class Regions:
    file_class: str
    lines: list[str]  # text.splitlines(keepends=True)
    header_end: int  # 0-based, exclusive: lines[:header_end] is the protected header
    protected: set = field(default_factory=set)  # 0-based indices of standalone protected markers
    footer_start: int | None = None  # 0-based: lines[footer_start:] is the protected footer

    def is_protected(self, idx: int) -> bool:
        if idx < self.header_end:
            return True
        if self.footer_start is not None and idx >= self.footer_start:
            return True
        return idx in self.protected


def detect_declaration_keyword(text: str) -> str | None:
    lines = text.splitlines()[:_KEYWORD_LINES_TO_SCAN]
    for line in lines:
        m = _DECLARATION_KEYWORD_RE.match(line)
        if m:
            return m.group(1).upper()
    return None


def detect(text: str) -> Regions:
    lines = text.splitlines(keepends=True)

    if detect_declaration_keyword(text) == "LIBRARY":
        return Regions(
            file_class=FileClass.LIBRARY_MANIFEST,
            lines=lines,
            header_end=len(lines),
        )

    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    header_end = idx
    while header_end < len(lines) and _HEADER_KEY_LINE_RE.match(lines[header_end]):
        header_end += 1

    protected: set = set()
    footer_start: int | None = None
    for i in range(header_end, len(lines)):
        line = lines[i]
        if _END_DECLARATION_LINE_RE.match(line) or _TEXT_IMPLEMENTATION_LINE_RE.match(line):
            protected.add(i)
        elif footer_start is None and _OBJECT_END_LINE_RE.match(line):
            footer_start = i

    return Regions(
        file_class=FileClass.ST_SOURCE,
        lines=lines,
        header_end=header_end,
        protected=protected,
        footer_start=footer_start,
    )
