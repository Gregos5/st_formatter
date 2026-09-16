import unittest

from st_formatter.blanklines import apply


class TestBlankLines(unittest.TestCase):
    def test_trailing_blank_before_end_action_removed(self):
        text = "ACTION Foo:\r\n  ;\r\n\r\n\r\nEND_ACTION\r\n"
        out = apply(text)
        self.assertEqual(out, "ACTION Foo:\r\n  ;\r\nEND_ACTION\r\n")

    def test_trailing_blank_before_end_program_removed(self):
        text = "PROGRAM Foo\r\n  ;\r\n\r\nEND_PROGRAM\r\n"
        out = apply(text)
        self.assertEqual(out, "PROGRAM Foo\r\n  ;\r\nEND_PROGRAM\r\n")

    def test_whitespace_only_blank_line_also_removed(self):
        text = "ACTION Foo:\r\n  ;\r\n\t \r\nEND_ACTION\r\n"
        out = apply(text)
        self.assertEqual(out, "ACTION Foo:\r\n  ;\r\nEND_ACTION\r\n")

    def test_no_blank_line_is_a_no_op(self):
        text = "ACTION Foo:\r\n  ;\r\nEND_ACTION\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_blank_lines_inside_body_untouched(self):
        text = "ACTION Foo:\r\n  a := 1;\r\n\r\n  b := 2;\r\nEND_ACTION\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_non_pou_closer_untouched(self):
        text = "IF x THEN\r\n  ;\r\n\r\nEND_IF\r\n"
        out = apply(text)
        self.assertEqual(out, text)


if __name__ == "__main__":
    unittest.main()
