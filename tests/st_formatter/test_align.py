import unittest

from tools.st_formatter.align import apply


class TestAlign(unittest.TestCase):
    def test_assign_run_aligned_to_longest_name(self):
        text = "a := 1;\r\nbb := 2;\r\nccc := 3;\r\n"
        out = apply(text)
        lines = out.splitlines()
        col = lines[2].index(":=")
        self.assertEqual(lines[0].index(":="), col)
        self.assertEqual(lines[1].index(":="), col)

    def test_run_breaks_on_blank_line(self):
        text = "a := 1;\r\n\r\nbb := 2;\r\n"
        out = apply(text)
        lines = out.splitlines()
        # each is its own run of one -> single space before :=, not aligned
        # to the other line's longer name
        self.assertEqual(lines[0], "a := 1;")
        self.assertEqual(lines[2], "bb := 2;")

    def test_run_breaks_on_comment_only_line(self):
        text = "a := 1;\r\n(* section *)\r\nbb := 2;\r\n"
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "a := 1;")
        self.assertEqual(lines[2], "bb := 2;")

    def test_run_breaks_on_indent_change(self):
        text = "a := 1;\r\n  bb := 2;\r\n"
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "a := 1;")
        self.assertEqual(lines[1], "  bb := 2;")

    def test_arrow_and_assign_aligned_independently(self):
        text = "Foo(\r\n  a := 1,\r\n  bb => 2\r\n);\r\n"
        out = apply(text)
        lines = out.splitlines()
        self.assertIn(":=", lines[1])
        self.assertIn("=>", lines[2])

    def test_trailing_comment_run_aligned(self):
        text = "a := 1; (* one *)\r\nbb := 2; (* two *)\r\n"
        out = apply(text)
        lines = out.splitlines()
        col0 = lines[0].index("(*")
        col1 = lines[1].index("(*")
        self.assertEqual(col0, col1)

    def test_comment_text_never_modified(self):
        text = "a  := 1;   (*   spaced   out   *)\r\n"
        out = apply(text)
        self.assertIn("(*   spaced   out   *)", out)

    def test_protected_lines_not_realigned(self):
        text = "(* @PATH := 'x' *)\r\na := 1;\r\n"
        out = apply(text)
        self.assertIn("(* @PATH := 'x' *)\r\n", out)


if __name__ == "__main__":
    unittest.main()
