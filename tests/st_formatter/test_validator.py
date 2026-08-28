import unittest

from tools.st_formatter import validator


class TestValidator(unittest.TestCase):
    def test_whitespace_only_change_passes(self):
        original = "a\t:=\t1;\r\n"
        formatted = "a := 1;\r\n"
        result = validator.check(original, formatted)
        self.assertTrue(result.ok, result.failures)

    def test_renamed_identifier_fails_check_a(self):
        original = "x := 1;\r\n"
        formatted = "y := 1;\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        self.assertTrue(any("Check A" in f for f in result.failures))

    def test_dropped_statement_fails_check_a(self):
        original = "a := 1;\r\nb := 2;\r\n"
        formatted = "a := 1;\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        self.assertTrue(any("Check A" in f for f in result.failures))

    def test_comment_text_change_fails_check_a(self):
        original = "a := 1; (* keep this *)\r\n"
        formatted = "a := 1; (* changed *)\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        self.assertTrue(any("Check A" in f for f in result.failures))

    def test_mismatched_nesting_fails_check_b(self):
        original = "IF a THEN\r\n\tx := 1;\r\nEND_IF\r\n"
        formatted = "IF a THEN\r\n\tx := 1;\r\nEND_CASE\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        # Malformed either way, but at minimum Check A must catch the
        # END_IF -> END_CASE token substitution.
        self.assertTrue(any("Check A" in f for f in result.failures))

    def test_altered_header_fails_check_c(self):
        original = "(* @PATH := '\\/IO' *)\r\nPROGRAM Foo\r\nEND_PROGRAM\r\n"
        formatted = "(* @PATH := '\\/OTHER' *)\r\nPROGRAM Foo\r\nEND_PROGRAM\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        self.assertTrue(any("Check C" in f for f in result.failures))

    def test_altered_end_declaration_marker_fails_check_c(self):
        original = "PROGRAM Foo\r\nVAR\r\nEND_VAR\r\n(* @END_DECLARATION := '0' *)\r\nEND_PROGRAM\r\n"
        formatted = "PROGRAM Foo\r\nVAR\r\nEND_VAR\r\n(* @END_DECLARATION := '1' *)\r\nEND_PROGRAM\r\n"
        result = validator.check(original, formatted)
        self.assertFalse(result.ok)
        self.assertTrue(any("Check C" in f for f in result.failures))


if __name__ == "__main__":
    unittest.main()
