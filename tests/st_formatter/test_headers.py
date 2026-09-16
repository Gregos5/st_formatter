import unittest

from st_formatter.headers import apply


class TestHeaders(unittest.TestCase):
    def test_space_normalized_to_tab(self):
        text = "ACTION Foo:\r\n  ;\r\nEND_ACTION\r\n"
        out = apply(text, separator="tab")
        self.assertTrue(out.startswith("ACTION\tFoo:\r\n"))

    def test_already_tab_left_unchanged(self):
        text = "ACTION\tFoo:\r\n  ;\r\nEND_ACTION\r\n"
        out = apply(text, separator="tab")
        self.assertEqual(out, text)

    def test_tab_normalized_to_space(self):
        text = "ACTION\tFoo:\r\n  ;\r\nEND_ACTION\r\n"
        out = apply(text, separator="space")
        self.assertTrue(out.startswith("ACTION Foo:\r\n"))

    def test_multiple_spaces_collapsed_to_one(self):
        text = "ACTION   Foo:\r\n  ;\r\nEND_ACTION\r\n"
        out = apply(text, separator="space")
        self.assertTrue(out.startswith("ACTION Foo:\r\n"))

    def test_other_pou_headers_untouched(self):
        text = "PROGRAM Foo\r\nEND_PROGRAM\r\n"
        out = apply(text, separator="tab")
        self.assertEqual(out, text)

    def test_protected_header_lines_untouched(self):
        text = "(* @PATH := 'x' *)\r\nACTION Foo:\r\nEND_ACTION\r\n"
        out = apply(text, separator="tab")
        self.assertIn("(* @PATH := 'x' *)\r\n", out)
        self.assertIn("ACTION\tFoo:", out)

    def test_invalid_separator_raises(self):
        with self.assertRaises(ValueError):
            apply("ACTION Foo:\r\nEND_ACTION\r\n", separator="bogus")


if __name__ == "__main__":
    unittest.main()
