import unittest

from st_formatter.callargs import apply


class TestCallArgs(unittest.TestCase):
    def test_case_new_line_reindented_one_level_deeper(self):
        text = (
            "  InitSafout_POL_HS_Single(\r\n"
            "OutChannel_HS_u32 := 1,\r\n"
            "        FrequencySelect_u16 := 2\r\n"
            "  );\r\n"
        )
        out = apply(text, indent_size=2)
        lines = out.splitlines()
        self.assertEqual(lines[1], "    OutChannel_HS_u32 := 1,")
        self.assertEqual(lines[2], "    FrequencySelect_u16 := 2")
        self.assertEqual(lines[3], "  );")

    def test_case_new_line_closer_sharing_last_arg_line_not_forced_to_opener_indent(self):
        text = (
            "  Foo(\r\n"
            "a := 1);\r\n"
        )
        out = apply(text, indent_size=2)
        lines = out.splitlines()
        self.assertEqual(lines[1], "    a := 1);")

    def test_case_same_line_aligned_to_first_arg_column_no_paren_padding(self):
        text = (
            "  InitSafout_POL_LS(HwOutpChnl_s.CHNL,\r\n"
            "prm_s.FreqSlct_u16,\r\n"
            "        prm_s.ClosedLoop_Kp_u16,\r\n"
            "  flgSafoutCurrDevChk_b := FALSE);\r\n"
        )
        out = apply(text, indent_size=2)
        lines = out.splitlines()
        first_arg_col = lines[0].index("HwOutpChnl_s")
        self.assertEqual(lines[1].index("prm_s.FreqSlct_u16"), first_arg_col)
        self.assertEqual(lines[2].index("prm_s.ClosedLoop_Kp_u16"), first_arg_col)
        self.assertEqual(lines[3].index("flgSafoutCurrDevChk_b"), first_arg_col)
        self.assertTrue(lines[3].endswith("FALSE);"))

    def test_case_same_line_space_after_open_paren_collapsed(self):
        text = "Foo( a,\r\n     b);\r\n"
        out = apply(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "Foo(a,")

    def test_single_line_call_untouched(self):
        text = "Foo(a, b, c);\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_empty_call_untouched(self):
        text = "Foo(\r\n);\r\n"
        out = apply(text)
        self.assertEqual(out, text)

    def test_nested_call_argument_list_also_reindented(self):
        text = (
            "  Outer(\r\n"
            "    Inner(\r\n"
            "x := 1\r\n"
            "    ),\r\n"
            "    b\r\n"
            "  );\r\n"
        )
        out = apply(text, indent_size=2)
        lines = out.splitlines()
        # Inner( is itself an argument line of Outer, at 4-space indent;
        # its own argument list should be indented one level deeper still.
        self.assertEqual(lines[2], "      x := 1")
        self.assertEqual(lines[3], "    ),")

    def test_call_with_multiline_comment_argument_left_untouched(self):
        # A comment token that spans multiple lines has no real leading
        # whitespace of its own on its continuation line -- reindenting
        # that line (as pure indentation) corrupts the comment's text.
        text = (
            "func_pf(\r\n"
            "  ptr,\r\n"
            "  lenMax_u32,\r\n"
            "  buf_p (* comment line one\r\n"
            "\t\t\t\tcomment line two *)\r\n"
            "  ) := 1;\r\n"
        )
        out = apply(text, indent_size=2)
        self.assertEqual(out, text)

    def test_protected_call_left_untouched(self):
        # A call inside the footer region (after @OBJECT_END) must never be
        # reindented -- the whole footer round-trips byte-exact.
        text = (
            "x := 1;\r\n"
            "(* @OBJECT_END := 'x' *)\r\n"
            "Foo(\r\n"
            "a := 1\r\n"
            ");\r\n"
        )
        out = apply(text)
        self.assertEqual(out, text)


if __name__ == "__main__":
    unittest.main()
