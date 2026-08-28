import tempfile
import unittest
from pathlib import Path

from st_formatter import __version__
from st_formatter.cli import EXIT_CLEAN, EXIT_WOULD_CHANGE, _iter_source_files, main

_SIMPLE_PROGRAM = "PROGRAM Foo\r\nVAR\r\n\tx : BOOL;\r\nEND_VAR\r\nEND_PROGRAM\r\n"


class TestIterSourceFiles(unittest.TestCase):
    def test_directory_scan_picks_up_st_and_exp_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.st").write_text(_SIMPLE_PROGRAM)
            (root / "b.EXP").write_text(_SIMPLE_PROGRAM)
            (root / "c.txt").write_text(_SIMPLE_PROGRAM)

            files = _iter_source_files([str(root)], (".st", ".exp"), ())
            names = sorted(f.name for f in files)
            self.assertEqual(names, ["a.st", "b.EXP"])

    def test_exclude_pattern_skips_directory_discovered_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "build"
            build.mkdir()
            (root / "a.st").write_text(_SIMPLE_PROGRAM)
            (build / "b.st").write_text(_SIMPLE_PROGRAM)

            files = _iter_source_files([str(root)], (".st", ".exp"), ("*/build/*",))
            names = sorted(f.name for f in files)
            self.assertEqual(names, ["a.st"])

    def test_explicit_file_arg_bypasses_extension_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "weird.dat"
            target.write_text(_SIMPLE_PROGRAM)

            files = _iter_source_files([str(target)], (".st", ".exp"), ())
            self.assertEqual(files, [target])

    def test_exclude_pattern_does_not_skip_explicit_file_arg(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / "build"
            build.mkdir()
            target = build / "b.st"
            target.write_text(_SIMPLE_PROGRAM)

            files = _iter_source_files([str(target)], (".st", ".exp"), ("*/build/*",))
            self.assertEqual(files, [target])

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            _iter_source_files(["/no/such/path"], (".st", ".exp"), ())


class TestMain(unittest.TestCase):
    def test_version_flag_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_check_mode_reports_would_change_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.st"
            target.write_text("PROGRAM Foo\r\nVAR\r\nx : BOOL;\r\nEND_VAR\r\nEND_PROGRAM\r\n")
            before = target.read_text()

            code = main([str(target)])

            self.assertIn(code, (EXIT_CLEAN, EXIT_WOULD_CHANGE))
            self.assertEqual(target.read_text(), before)

    def test_st_and_exp_directory_are_both_formatted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.st").write_text(_SIMPLE_PROGRAM)
            (root / "b.EXP").write_text(_SIMPLE_PROGRAM)

            code = main(["--write", str(root)])
            self.assertEqual(code, EXIT_CLEAN)


if __name__ == "__main__":
    unittest.main()
