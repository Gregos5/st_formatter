"""Project configuration: discovery, precedence, and merging.

Mirrors the black/ruff convention: look for a dedicated `.stformat.toml`
first, then a `[tool.st_formatter]` table in `pyproject.toml`, walking
upward from the target path(s). CLI flags always win over a config file,
and a config file always wins over the built-in defaults.
"""
from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

_DEDICATED_FILENAME = ".stformat.toml"
_PYPROJECT_FILENAME = "pyproject.toml"
_KNOWN_KEYS = {
    "indent_size", "tab_width", "indent", "align",
    "align_conditions", "align_call_args", "extensions", "exclude",
}


@dataclass
class Config:
    indent_size: int = 2
    tab_width: int = 4
    do_indent: bool = True
    do_align: bool = True
    do_align_conditions: bool = True
    do_align_call_args: bool = True
    extensions: tuple = (".st", ".exp")
    exclude: tuple = field(default_factory=tuple)


def _normalize_extensions(values) -> tuple:
    return tuple(v if v.startswith(".") else f".{v}" for v in (e.lower() for e in values))


def _table_to_overrides(table: dict) -> dict:
    unknown = set(table) - _KNOWN_KEYS
    if unknown:
        print(f"warning: ignoring unknown st_formatter config key(s): {', '.join(sorted(unknown))}", file=sys.stderr)

    overrides = {}
    if "indent_size" in table:
        overrides["indent_size"] = int(table["indent_size"])
    if "tab_width" in table:
        overrides["tab_width"] = int(table["tab_width"])
    if "indent" in table:
        overrides["do_indent"] = bool(table["indent"])
    if "align" in table:
        overrides["do_align"] = bool(table["align"])
    if "align_conditions" in table:
        overrides["do_align_conditions"] = bool(table["align_conditions"])
    if "align_call_args" in table:
        overrides["do_align_call_args"] = bool(table["align_call_args"])
    if "extensions" in table:
        overrides["extensions"] = _normalize_extensions(table["extensions"])
    if "exclude" in table:
        overrides["exclude"] = tuple(table["exclude"])
    return overrides


def _load_toml_table(path: Path) -> dict:
    with path.open("rb") as f:
        data = tomllib.load(f)
    if path.name == _PYPROJECT_FILENAME:
        return data.get("tool", {}).get("st_formatter", {})
    return data


def _find_config_file(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    while True:
        dedicated = current / _DEDICATED_FILENAME
        if dedicated.is_file():
            return dedicated
        pyproject = current / _PYPROJECT_FILENAME
        if pyproject.is_file():
            try:
                if _load_toml_table(pyproject):
                    return pyproject
            except tomllib.TOMLDecodeError:
                raise
        if current.parent == current:
            return None
        current = current.parent


def _common_start_dir(paths: list) -> Path:
    resolved = [Path(p).resolve() for p in paths]
    dirs = [p if p.is_dir() else p.parent for p in resolved]
    return Path(os.path.commonpath(dirs))


def resolve_config(paths: list, explicit_config: str = None, cli_overrides: dict = None) -> Config:
    overrides = {}

    if explicit_config:
        config_path = Path(explicit_config)
        if not config_path.is_file():
            raise FileNotFoundError(f"no such config file: {explicit_config}")
        overrides.update(_table_to_overrides(_load_toml_table(config_path)))
    elif paths:
        found = _find_config_file(_common_start_dir(paths))
        if found is not None:
            overrides.update(_table_to_overrides(_load_toml_table(found)))

    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None:
                overrides[key] = value

    known_fields = {f.name for f in fields(Config)}
    overrides = {k: v for k, v in overrides.items() if k in known_fields}
    return Config(**overrides)
