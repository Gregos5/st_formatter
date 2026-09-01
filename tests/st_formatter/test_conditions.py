import unittest

from st_formatter.conditions import apply


class TestConditions(unittest.TestCase):
    def test_multiline_if_and_or_aligned_and_spaced(self):
        text = (
            "    IF flgErrorSet_b  = TRUE  OR\r\n"
            "      flgRcvdOnce_b = FALSE  OR\r\n"
            "      flgRcvdSafe_b =  TRUE\r\n"
            "      THEN\r\n"
        )
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "    IF flgErrorSet_b = TRUE OR")
        self.assertEqual(lines[1], "       flgRcvdOnce_b = FALSE OR")
        self.assertEqual(lines[2], "       flgRcvdSafe_b = TRUE")
        # THEN alone on its own line is untouched
        self.assertEqual(lines[3], "      THEN")

    def test_single_line_if_untouched(self):
        text = "IF a  =  TRUE THEN\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_condition_without_logical_operator_untouched(self):
        text = "IF a  =\r\n  TRUE THEN\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_while_condition_aligned(self):
        text = (
            "WHILE flgA = TRUE AND\r\n"
            "  flgB = FALSE\r\n"
            "DO\r\n"
        )
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "WHILE flgA = TRUE AND")
        self.assertEqual(lines[1], "      flgB = FALSE")
        self.assertEqual(lines[2], "DO")

    def test_until_condition_aligned(self):
        text = (
            "REPEAT\r\n"
            "UNTIL flgA = TRUE AND\r\n"
            "  flgB = FALSE\r\n"
            ";\r\n"
            "END_REPEAT\r\n"
        )
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[1], "UNTIL flgA = TRUE AND")
        self.assertEqual(lines[2], "      flgB = FALSE")

    def test_terminator_sharing_last_condition_line_is_realigned(self):
        text = (
            "IF flgA = TRUE OR\r\n"
            "  flgB = FALSE THEN\r\n"
        )
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[1], "   flgB = FALSE THEN")

    def test_protected_condition_left_untouched(self):
        # A condition inside the footer region (after @OBJECT_END) must
        # never be realigned -- the whole footer round-trips byte-exact.
        text = (
            "x := 1;\r\n"
            "(* @OBJECT_END := 'x' *)\r\n"
            "IF flgA = TRUE OR\r\n"
            "  flgB = FALSE\r\n"
            "  THEN\r\n"
        )
        out = apply(text)
        self.assertEqual(out, text)

    def test_comment_bearing_line_left_alone(self):
        text = (
            "IF flgA = TRUE  OR (* keep spacing *)\r\n"
            "  flgB = FALSE\r\n"
            "  THEN\r\n"
        )
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "IF flgA = TRUE  OR (* keep spacing *)")


if __name__ == "__main__":
    unittest.main()
