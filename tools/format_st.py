#!/usr/bin/env python3
"""Thin wrapper so the formatter can be run as `python tools/format_st.py ...`
without needing `python -m tools.st_formatter` from the repo root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.st_formatter.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
