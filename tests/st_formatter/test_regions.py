import unittest

from tools.st_formatter.regions import FileClass, detect


class TestRegions(unittest.TestCase):
    def test_program_header_and_end_declaration(self):
        text = (
            "(* @NESTEDCOMMENTS := 'Yes' *)\r\n"
            "(* @PATH := '\\/Task_MAIN' *)\r\n"
            "PROGRAM Foo\r\n"
            "VAR\r\n"
            "\tx : BOOL;\r\n"
            "END_VAR\r\n"
            "(* @END_DECLARATION := '0' *)\r\n"
            "x := TRUE;\r\n"
            "END_PROGRAM\r\n"
        )
        regions = detect(text)
        self.assertEqual(regions.file_class, FileClass.ST_SOURCE)
        self.assertTrue(regions.is_protected(0))
        self.assertTrue(regions.is_protected(1))
        self.assertFalse(regions.is_protected(2))  # PROGRAM line
        end_decl_idx = text.splitlines(keepends=True).index("(* @END_DECLARATION := '0' *)\r\n")
        self.assertTrue(regions.is_protected(end_decl_idx))
        self.assertFalse(regions.is_protected(end_decl_idx + 1))  # x := TRUE; is real code

    def test_action_text_implementation_marker(self):
        text = (
            "ACTION Foo:\r\n"
            "(* @TEXT_IMPLEMENTATION := 'ST' *)\r\n"
            "x := 1;\r\n"
            "END_ACTION\r\n"
        )
        regions = detect(text)
        lines = text.splitlines(keepends=True)
        marker_idx = lines.index("(* @TEXT_IMPLEMENTATION := 'ST' *)\r\n")
        self.assertTrue(regions.is_protected(marker_idx))
        self.assertFalse(regions.is_protected(marker_idx + 1))

    def test_gvl_footer_block_protected(self):
        text = (
            "(* @NESTEDCOMMENTS := 'Yes' *)\r\n"
            "(* @GLOBAL_VARIABLE_LIST := 'HardwareMapping' *)\r\n"
            "VAR_GLOBAL CONSTANT\r\n"
            "\tx : BOOL := TRUE;\r\n"
            "END_VAR\r\n"
            "(* @OBJECT_END := 'HardwareMapping' *)\r\n"
            "(* @CONNECTIONS := HardwareMapping\r\n"
            "FILENAME : ''\r\n"
            "FILETIME : 0\r\n"
            "*)\r\n"
        )
        regions = detect(text)
        lines = text.splitlines(keepends=True)
        footer_idx = lines.index("(* @OBJECT_END := 'HardwareMapping' *)\r\n")
        self.assertEqual(regions.footer_start, footer_idx)
        for i in range(footer_idx, len(lines)):
            self.assertTrue(regions.is_protected(i))
        self.assertFalse(regions.is_protected(footer_idx - 1))  # END_VAR is real code

    def test_library_manifest_is_full_pass_through(self):
        text = (
            "LIBRARY\r\n"
            "Basics_13_RC30.lib 6.8.26 08:09:34\r\n"
            "(* @LIBRARYSYMFILEINFO := '0' *)\r\n"
            "NumOfPOUs: 22\r\n"
        )
        regions = detect(text)
        self.assertEqual(regions.file_class, FileClass.LIBRARY_MANIFEST)
        for i in range(len(regions.lines)):
            self.assertTrue(regions.is_protected(i))


if __name__ == "__main__":
    unittest.main()
