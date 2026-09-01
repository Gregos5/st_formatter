import unittest

from st_formatter.indent import apply
from st_formatter.regions import detect


def _fmt(text: str, indent_size: int = 2, tab_width: int = 4) -> str:
    return apply(text, detect(text), indent_size=indent_size, tab_width=tab_width)


class TestIndent(unittest.TestCase):
    def test_program_body_indents_var_flat_vs_var_members_indenting(self):
        # PROGRAM/END_PROGRAM sit flush left, but the body between them (and
        # the VAR_INPUT *members*) is indented one level. VAR_INPUT/END_VAR
        # themselves stay flush with the body around them.
        text = (
            "PROGRAM Foo\r\n"
            "VAR_INPUT\r\n"
            "\tx : BOOL;\r\n"
            "END_VAR\r\n"
            "x := TRUE;\r\n"
            "END_PROGRAM\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "PROGRAM Foo")
        self.assertEqual(lines[1], "  VAR_INPUT")
        self.assertEqual(lines[2], "    x : BOOL;")
        self.assertEqual(lines[3], "  END_VAR")
        self.assertEqual(lines[4], "  x := TRUE;")
        self.assertEqual(lines[5], "END_PROGRAM")

    def test_action_body_is_indented(self):
        text = (
            "ACTION Foo:\r\n"
            "x := TRUE;\r\n"
            "END_ACTION\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "ACTION Foo:")
        self.assertEqual(lines[1], "  x := TRUE;")
        self.assertEqual(lines[2], "END_ACTION")

    def test_if_then_else_inline_idiom(self):
        text = (
            "IF cond = TRUE\r\n"
            "\tTHEN DoThing();\r\n"
            "\tELSE ;\r\n"
            "END_IF\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "IF cond = TRUE")
        self.assertEqual(lines[1], "  THEN DoThing();")
        self.assertEqual(lines[2], "ELSE ;")
        self.assertEqual(lines[3], "END_IF")

    def test_if_else_block_not_indented_relative_to_if(self):
        # ELSE/ELSIF are part of the IF/END_IF structure and sit at the same
        # level as IF and END_IF; only the branch bodies indent.
        text = (
            "IF stStartRelease_b THEN\r\n"
            "\t(* Normal operational mode *)\r\n"
            "\t_RUN();\r\n"
            "\tELSE\r\n"
            "\t\t(* Wait for start release *)\r\n"
            "\t\t_STARTLOCK();\r\n"
            "END_IF\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "IF stStartRelease_b THEN")
        self.assertEqual(lines[1], "  (* Normal operational mode *)")
        self.assertEqual(lines[2], "  _RUN();")
        self.assertEqual(lines[3], "ELSE")
        self.assertEqual(lines[4], "  (* Wait for start release *)")
        self.assertEqual(lines[5], "  _STARTLOCK();")
        self.assertEqual(lines[6], "END_IF")

    def test_if_then_alone_with_indented_body(self):
        text = (
            "IF cond\r\n"
            "\tTHEN\r\n"
            "\t\tA();\r\n"
            "\t\tB();\r\n"
            "END_IF\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "IF cond")
        self.assertEqual(lines[1], "  THEN")
        self.assertEqual(lines[2], "    A();")
        self.assertEqual(lines[3], "    B();")
        self.assertEqual(lines[4], "END_IF")

    def test_case_labels_normalized_one_level_under_case(self):
        # Real-world inconsistency: some CASE blocks in the repo put labels
        # flush with CASE/END_CASE instead of one level under. The formatter
        # normalizes to one canonical convention.
        text = (
            "CASE x OF\r\n"
            "0: Foo();\r\n"
            "1: ;\r\n"
            "END_CASE\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[1], "  0: Foo();")
        self.assertEqual(lines[2], "  1: ;")

    def test_case_label_with_separate_body_lines(self):
        text = (
            "CASE x OF\r\n"
            "\t0:\r\n"
            "\t\tFoo();\r\n"
            "\t\tBar();\r\n"
            "END_CASE\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[1], "  0:")
        self.assertEqual(lines[2], "    Foo();")
        self.assertEqual(lines[3], "    Bar();")

    def test_type_struct_nesting(self):
        text = (
            "TYPE Foo_ts :\r\n"
            "STRUCT\r\n"
            "\tx : INT;\r\n"
            "END_STRUCT\r\n"
            "END_TYPE\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "TYPE Foo_ts :")
        self.assertEqual(lines[1], "STRUCT")
        self.assertEqual(lines[2], "  x : INT;")
        self.assertEqual(lines[3], "END_STRUCT")
        self.assertEqual(lines[4], "END_TYPE")

    def test_no_tabs_in_output(self):
        text = "PROGRAM Foo\r\nVAR\r\n\tx\t\t: INT;\r\nEND_VAR\r\nEND_PROGRAM\r\n"
        out = _fmt(text)
        self.assertNotIn("\t", out)

    def test_continuation_line_not_reindented(self):
        text = (
            "PROGRAM Foo\r\n"
            "DoCall(\r\n"
            "\t\tflgA := TRUE,\r\n"
            "\t\tflgB := FALSE\r\n"
            ");\r\n"
            "END_PROGRAM\r\n"
        )
        out = _fmt(text)
        lines = out.splitlines()
        # leading indent of continuation lines is tab-expanded, not
        # recomputed from nesting depth
        self.assertIn("flgA", lines[2])
        self.assertNotIn("\t", lines[2])

    def test_protected_lines_untouched(self):
        text = (
            "(* @PATH := '\\/IO' *)\r\n"
            "PROGRAM Foo\r\n"
            "END_PROGRAM\r\n"
            "(* @OBJECT_END := 'Foo' *)\r\n"
        )
        out = _fmt(text)
        self.assertIn("(* @PATH := '\\/IO' *)\r\n", out)
        self.assertIn("(* @OBJECT_END := 'Foo' *)\r\n", out)


if __name__ == "__main__":
    unittest.main()
