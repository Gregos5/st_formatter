"""CLI entry point for the ST formatter.

    st-formatter <paths...> [options]
    python -m st_formatter <paths...> [options]

There is no implicit default path: callers must name the directory/files
to format explicitly (e.g. `code`), so the tool stays safe to point at a
small test-fixtures directory too. The tool never invokes git itself.
"""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import sys
from pathlib import Path

from . import __version__
from .config import resolve_config
from .formatter import format_text

EXIT_CLEAN = 0
EXIT_WOULD_CHANGE = 1
EXIT_VALIDATION_FAILED = 2
EXIT_FATAL = 3


def _is_excluded(path: Path, exclude_patterns: tuple) -> bool:
    posix = path.as_posix()
    return any(fnmatch.fnmatch(posix, pat) for pat in exclude_patterns)


def _iter_source_files(paths: list, extensions: tuple, exclude_patterns: tuple, verbose: bool = False) -> list:
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if not f.is_file() or f.suffix.lower() not in extensions:
                    continue
                if _is_excluded(f, exclude_patterns):
                    continue
                files.append(f)
        elif p.is_file():
            if verbose and p.suffix.lower() not in extensions:
                print(f"note: {p} has an unrecognized extension, formatting it anyway (explicit file argument)")
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
        description="clang-format-style formatter for IEC 61131-3 Structured "
                     "Text (.st) and Bodas/CoDeSys 2.3 .EXP exports."
    )
    parser.add_argument("paths", nargs="+", help="Files and/or directories to format (.st and .EXP by default)")
    parser.add_argument("--write", action="store_true", help="Apply changes in place (default: dry run)")
    parser.add_argument("--check", action="store_true", help="Explicit dry-run alias (default behavior)")
    parser.add_argument("--diff", action="store_true", help="Print a unified diff for each file that would change")
    parser.add_argument("--config", metavar="PATH", help="Use this config file instead of auto-discovery")
    parser.add_argument("--extensions", metavar="EXT,...", help="Comma-separated extensions to treat as ST source, "
                                                                  "e.g. .st,.exp (default: .st,.exp)")
    parser.add_argument("--indent-size", type=int, default=None)
    parser.add_argument("--tab-width", type=int, default=None)
    parser.add_argument("--no-align", action="store_true", default=None,
                         help="Skip the := / => / comment alignment pass")
    parser.add_argument("--no-indent", action="store_true", default=None, help="Skip the reindentation pass")
    parser.add_argument("--no-align-conditions", action="store_true", default=None,
                         help="Skip the IF/ELSIF/WHILE/UNTIL condition alignment pass")
    parser.add_argument("--no-align-call-args", action="store_true", default=None,
                         help="Skip the call-argument-list alignment pass")
    parser.add_argument("--report", metavar="PATH", help="Write the full summary/diff/failure log to this file")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"st-formatter {__version__}")
    args = parser.parse_args(argv)

    try:
        config = resolve_config(
            paths=args.paths,
            explicit_config=args.config,
            cli_overrides={
                "indent_size": args.indent_size,
                "tab_width": args.tab_width,
                "do_indent": None if args.no_indent is None else not args.no_indent,
                "do_align": None if args.no_align is None else not args.no_align,
                "do_align_conditions": None if args.no_align_conditions is None else not args.no_align_conditions,
                "do_align_call_args": None if args.no_align_call_args is None else not args.no_align_call_args,
                "extensions": tuple(e.strip() for e in args.extensions.split(",")) if args.extensions else None,
            },
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: invalid config: {exc}", file=sys.stderr)
        return EXIT_FATAL

    try:
        files = _iter_source_files(args.paths, config.extensions, config.exclude, verbose=args.verbose)
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
            indent_size=config.indent_size,
            tab_width=config.tab_width,
            do_indent=config.do_indent,
            do_align=config.do_align,
            do_align_conditions=config.do_align_conditions,
            do_align_call_args=config.do_align_call_args,
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
