import unittest

from st_formatter.tokenizer import TokenType, tokenize


class TestTokenizer(unittest.TestCase):
    def test_lossless_roundtrip(self):
        text = (
            "(* @PATH := '\\/IO' *)\r\n"
            "TYPE Foo :\r\n"
            "STRUCT\r\n"
            "\tx\t: INT := 16#01; (* comment *)\r\n"
            "END_STRUCT\r\n"
            "END_TYPE\r\n"
        )
        tokens = tokenize(text)
        self.assertEqual("".join(t.text for t in tokens), text)

    def test_nested_block_comment(self):
        text = "(* outer (* inner *) still-outer *)"
        tokens = tokenize(text)
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].text, text)

    def test_header_comment_captured_as_one_token(self):
        text = "(* @PATH := '\\/Task_MAIN\\/3_Task_MAIN_OUTPUT' *)\r\n"
        tokens = tokenize(text)
        self.assertEqual(tokens[0].type, TokenType.COMMENT)
        self.assertEqual(tokens[0].text, text.split("\r\n")[0])

    def test_assign_vs_arrow_vs_colon(self):
        tokens = tokenize("a := b => c : d")
        types = [t.type for t in tokens if t.type not in (TokenType.WHITESPACE, TokenType.EOF)]
        self.assertIn(TokenType.ASSIGN, types)
        self.assertIn(TokenType.ARROW, types)
        self.assertIn(TokenType.COLON, types)

    def test_based_literal_number(self):
        tokens = tokenize("16#01")
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].text, "16#01")

    def test_crlf_preserved_as_single_newline_token(self):
        tokens = tokenize("a\r\nb")
        nl = [t for t in tokens if t.type == TokenType.NEWLINE]
        self.assertEqual(len(nl), 1)
        self.assertEqual(nl[0].text, "\r\n")

    def test_keyword_case_preserved(self):
        tokens = tokenize("if x then end_if")
        kw = [t for t in tokens if t.type == TokenType.KEYWORD]
        self.assertEqual([t.text for t in kw], ["if", "then", "end_if"])

    def test_stray_byte_absorbed_without_crash(self):
        text = "(* Light \xfd 01 *)"
        tokens = tokenize(text)
        self.assertEqual("".join(t.text for t in tokens), text)


if __name__ == "__main__":
    unittest.main()
