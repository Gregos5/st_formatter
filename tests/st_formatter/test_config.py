import tempfile
import unittest
from pathlib import Path

from st_formatter.config import Config, resolve_config


class TestConfigDiscovery(unittest.TestCase):
    def test_defaults_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")
            config = resolve_config(paths=[str(target)])
            self.assertEqual(config, Config())

    def test_discovers_dedicated_stformat_toml_in_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".stformat.toml").write_text(
                'indent_size = 4\ntab_width = 8\nextensions = [".st"]\n'
            )
            sub = root / "src" / "plc"
            sub.mkdir(parents=True)
            target = sub / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(paths=[str(target)])
            self.assertEqual(config.indent_size, 4)
            self.assertEqual(config.tab_width, 8)
            self.assertEqual(config.extensions, (".st",))

    def test_discovers_tool_table_in_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[tool.st_formatter]\nindent_size = 3\nalign = false\n"
            )
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(paths=[str(target)])
            self.assertEqual(config.indent_size, 3)
            self.assertFalse(config.do_align)

    def test_pyproject_toml_without_tool_table_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text('[project]\nname = "other-tool"\n')
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(paths=[str(target)])
            self.assertEqual(config, Config())

    def test_dedicated_file_wins_over_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".stformat.toml").write_text("indent_size = 4\n")
            (root / "pyproject.toml").write_text(
                "[tool.st_formatter]\nindent_size = 9\n"
            )
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(paths=[str(target)])
            self.assertEqual(config.indent_size, 4)

    def test_explicit_config_path_bypasses_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".stformat.toml").write_text("indent_size = 4\n")
            explicit = root / "other.toml"
            explicit.write_text("indent_size = 7\n")
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(paths=[str(target)], explicit_config=str(explicit))
            self.assertEqual(config.indent_size, 7)

    def test_missing_explicit_config_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")
            with self.assertRaises(FileNotFoundError):
                resolve_config(paths=[str(target)], explicit_config=str(Path(tmp) / "nope.toml"))

    def test_cli_overrides_win_over_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".stformat.toml").write_text("indent_size = 4\n")
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(
                paths=[str(target)], cli_overrides={"indent_size": 10}
            )
            self.assertEqual(config.indent_size, 10)

    def test_cli_override_none_values_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".stformat.toml").write_text("indent_size = 4\n")
            target = root / "a.st"
            target.write_text("PROGRAM Foo\nEND_PROGRAM\n")

            config = resolve_config(
                paths=[str(target)], cli_overrides={"indent_size": None, "tab_width": None}
            )
            self.assertEqual(config.indent_size, 4)
            self.assertEqual(config.tab_width, Config().tab_width)


if __name__ == "__main__":
    unittest.main()
