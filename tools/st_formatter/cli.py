"""CLI entry point for the ST formatter.

    python -m tools.st_formatter <paths...> [options]

There is no implicit default path: callers must name the directory/files
to format explicitly (e.g. `code`), so the tool stays safe to point at a
small test-fixtures directory too. The tool never invokes git itself.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from .formatter import format_text

EXIT_CLEAN = 0
EXIT_WOULD_CHANGE = 1
EXIT_VALIDATION_FAILED = 2
EXIT_FATAL = 3


def _iter_exp_files(paths: list) -> list:
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() == ".exp"))
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError(f"no such file or directory: {raw}")
    return files


def _read(path: Path) -> str:
    with path.open("r", encoding="latin-1", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="latin-1", newline="") as f:
        f.write(text)


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Basic clang-format-style formatter for IEC 61131-3 "
                     "Structured Text .EXP files (Bodas/CoDeSys 2.3)."
    )
    parser.add_argument("paths", nargs="+", help="Files and/or directories to format (.EXP files only)")
    parser.add_argument("--write", action="store_true", help="Apply changes in place (default: dry run)")
    parser.add_argument("--check", action="store_true", help="Explicit dry-run alias (default behavior)")
    parser.add_argument("--diff", action="store_true", help="Print a unified diff for each file that would change")
    parser.add_argument("--indent-size", type=int, default=2)
    parser.add_argument("--tab-width", type=int, default=4)
    parser.add_argument("--no-align", action="store_true", help="Skip the := / => / comment alignment pass")
    parser.add_argument("--no-indent", action="store_true", help="Skip the reindentation pass")
    parser.add_argument("--report", metavar="PATH", help="Write the full summary/diff/failure log to this file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        files = _iter_exp_files(args.paths)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FATAL

    unchanged = reformatted = failed = 0
    report_lines: list = []

    for path in files:
        try:
            original = _read(path)
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            failed += 1
            continue

        result = format_text(
            original,
            indent_size=args.indent_size,
            tab_width=args.tab_width,
            do_indent=not args.no_indent,
            do_align=not args.no_align,
        )

        if not result.ok:
            failed += 1
            msg = f"FAILED VALIDATION: {path}"
            print(msg, file=sys.stderr)
            report_lines.append(msg)
            for f in result.failures:
                print(f"    {f}", file=sys.stderr)
                report_lines.append(f"    {f}")
            continue

        if not result.changed:
            unchanged += 1
            if args.verbose:
                print(f"unchanged: {path}")
            continue

        reformatted += 1
        if args.verbose:
            print(f"reformatted: {path}" if args.write else f"would reformat: {path}")

        if args.diff:
            diff = "".join(difflib.unified_diff(
                original.splitlines(keepends=True),
                result.formatted_text.splitlines(keepends=True),
                fromfile=str(path), tofile=str(path),
            ))
            print(diff)
            report_lines.append(diff)

        if args.write:
            try:
                _write(path, result.formatted_text)
            except OSError as exc:
                print(f"error: cannot write {path}: {exc}", file=sys.stderr)
                failed += 1

    verb = "reformatted" if args.write else "would be reformatted"
    summary = (
        f"{len(files)} files: {unchanged} unchanged, {reformatted} {verb}, "
        f"{failed} FAILED VALIDATION (skipped, left untouched)"
    )
    print(summary)
    report_lines.append(summary)

    if args.report:
        Path(args.report).write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    if failed:
        return EXIT_VALIDATION_FAILED
    if reformatted and not args.write:
        return EXIT_WOULD_CHANGE
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
