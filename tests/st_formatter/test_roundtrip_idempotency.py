import unittest

from st_formatter.formatter import format_text

FIXTURES = {
    "program_if_case": (
        "(* @NESTEDCOMMENTS := 'Yes' *)\r\n"
        "(* @PATH := '\\/Task_MAIN' *)\r\n"
        "PROGRAM Foo\r\n"
        "VAR_INPUT\r\n"
        "\tx\t\t: BOOL;  \t(* comment *)\r\n"
        "\tCmd_s: BOOL;\r\n"
        "END_VAR\r\n"
        "VAR\r\n"
        "\ty : INT := 0;\r\n"
        "END_VAR\r\n"
        "(* @END_DECLARATION := '0' *)\r\n"
        "IF x = TRUE\r\n"
        "\tTHEN DoA();\r\n"
        "\tELSE ;\r\n"
        "END_IF\r\n"
        "CASE y OF\r\n"
        "0: Foo();\r\n"
        "1: ;\r\n"
        "END_CASE\r\n"
        "END_PROGRAM\r\n"
        "ACTION Bar:\r\n"
        "(* @TEXT_IMPLEMENTATION := 'ST' *)\r\n"
        "a := 1;\r\n"
        "bb := 2;\r\n"
        "END_ACTION\r\n"
    ),
    "dut": (
        "(* @NESTEDCOMMENTS := 'Yes' *)\r\n"
        "(* @PATH := '\\/IO' *)\r\n"
        "TYPE Foo_ts :\r\n"
        "STRUCT\r\n"
        "\tx\t: DWORD;  (* a *)\r\n"
        "\tyy\t: UINT;   (* b *)\r\n"
        "END_STRUCT\r\n"
        "END_TYPE\r\n"
        "(* @END_DECLARATION := '0' *)\r\n"
    ),
    "gvl_with_footer": (
        "(* @NESTEDCOMMENTS := 'Yes' *)\r\n"
        "(* @GLOBAL_VARIABLE_LIST := 'Bar' *)\r\n"
        "VAR_GLOBAL CONSTANT\r\n"
        "\tX_U32 := (a := 1, (* comment *) b := 2);\r\n"
        "END_VAR\r\n"
        "(* @OBJECT_END := 'Bar' *)\r\n"
        "(* @CONNECTIONS := Bar\r\n"
        "FILENAME : ''\r\n"
        "FILETIME : 0\r\n"
        "*)\r\n"
    ),
    "library_manifest": (
        "LIBRARY\r\n"
        "Basics_13_RC30.lib 6.8.26 08:09:34\r\n"
        "(* @LIBRARYSYMFILEINFO := '0' *)\r\n"
        "NumOfPOUs: 22\r\n"
    ),
}


class TestRoundtripIdempotency(unittest.TestCase):
    def test_all_fixtures_validate_and_are_idempotent(self):
        for name, text in FIXTURES.items():
            with self.subTest(fixture=name):
                first = format_text(text)
                self.assertTrue(first.ok, first.failures)

                second = format_text(first.formatted_text)
                self.assertTrue(second.ok, second.failures)
                self.assertEqual(
                    second.formatted_text, first.formatted_text,
                    "formatting an already-formatted file must be a no-op",
                )
                self.assertFalse(second.changed)

    def test_library_manifest_is_untouched(self):
        text = FIXTURES["library_manifest"]
        result = format_text(text)
        self.assertTrue(result.ok)
        self.assertFalse(result.changed)
        self.assertEqual(result.formatted_text, text)


if __name__ == "__main__":
    unittest.main()
