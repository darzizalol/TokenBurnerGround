"""Tests for cinder.lexer: literals, identifiers, operators, comments, errors."""

import unittest

from cinder.errors import LexError
from cinder.lexer import tokenize
from cinder.tokens import TokenType


def types(tokens):
    return [t.type for t in tokens]


class TestLiterals(unittest.TestCase):
    def test_integer(self):
        tokens = tokenize("42")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 42)
        self.assertEqual(tokens[0].lexeme, "42")

    def test_float(self):
        tokens = tokenize("3.14")
        self.assertEqual(types(tokens), [TokenType.FLOAT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 3.14)

    def test_float_requires_digit_after_dot(self):
        # "1." followed by non-digit should lex as INT then DOT, not FLOAT.
        tokens = tokenize("1.foo")
        self.assertEqual(
            types(tokens),
            [TokenType.INT, TokenType.DOT, TokenType.IDENTIFIER, TokenType.EOF],
        )

    def test_string_basic(self):
        tokens = tokenize('"hello"')
        self.assertEqual(types(tokens), [TokenType.STRING, TokenType.EOF])
        self.assertEqual(tokens[0].literal, "hello")

    def test_string_escapes(self):
        tokens = tokenize(r'"a\nb\tc\\d\"e"')
        self.assertEqual(tokens[0].literal, "a\nb\tc\\d\"e")

    def test_identifier(self):
        tokens = tokenize("foo_bar1")
        self.assertEqual(types(tokens), [TokenType.IDENTIFIER, TokenType.EOF])
        self.assertEqual(tokens[0].lexeme, "foo_bar1")


class TestKeywords(unittest.TestCase):
    def test_all_keywords(self):
        keywords = {
            "let": TokenType.LET,
            "if": TokenType.IF,
            "else": TokenType.ELSE,
            "while": TokenType.WHILE,
            "fn": TokenType.FN,
            "return": TokenType.RETURN,
            "true": TokenType.TRUE,
            "false": TokenType.FALSE,
            "nil": TokenType.NIL,
            "and": TokenType.AND,
            "or": TokenType.OR,
            "not": TokenType.NOT,
        }
        for word, expected_type in keywords.items():
            with self.subTest(word=word):
                tokens = tokenize(word)
                self.assertEqual(types(tokens), [expected_type, TokenType.EOF])


class TestOperators(unittest.TestCase):
    def test_all_operators_and_punctuation(self):
        source = "+ - * / % == != < <= > >= = ( ) { } [ ] , ; . : ?"
        expected = [
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.PERCENT,
            TokenType.EQEQ,
            TokenType.BANGEQ,
            TokenType.LT,
            TokenType.LTEQ,
            TokenType.GT,
            TokenType.GTEQ,
            TokenType.EQ,
            TokenType.LPAREN,
            TokenType.RPAREN,
            TokenType.LBRACE,
            TokenType.RBRACE,
            TokenType.LBRACKET,
            TokenType.RBRACKET,
            TokenType.COMMA,
            TokenType.SEMICOLON,
            TokenType.DOT,
            TokenType.COLON,
            TokenType.QUESTION,
            TokenType.EOF,
        ]
        self.assertEqual(types(tokenize(source)), expected)

    def test_compound_assignment_operators(self):
        source = "+= -= *= /= %="
        expected = [
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
            TokenType.PERCENTEQ,
            TokenType.EOF,
        ]
        self.assertEqual(types(tokenize(source)), expected)

    def test_compound_assignment_lexes_as_single_token(self):
        # `+=` must lex as one PLUSEQ token, not PLUS then EQ.
        tokens = tokenize("x += 1")
        self.assertEqual(
            types(tokens),
            [TokenType.IDENTIFIER, TokenType.PLUSEQ, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, "+=")


class TestComments(unittest.TestCase):
    def test_comment_stripped(self):
        tokens = tokenize("let x = 1; # this is a comment\nlet y = 2;")
        self.assertNotIn("#", [t.lexeme for t in tokens])
        let_count = sum(1 for t in tokens if t.type == TokenType.LET)
        self.assertEqual(let_count, 2)

    def test_comment_to_end_of_file(self):
        tokens = tokenize("42 # trailing comment with no newline")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])


class TestLineColumn(unittest.TestCase):
    def test_multiline_line_and_column(self):
        source = "let x = 1;\nlet y = 2;"
        tokens = tokenize(source)
        # First token on line 1.
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[0].column, 1)
        # Find the second `let`, which starts line 2 column 1.
        lets = [t for t in tokens if t.type == TokenType.LET]
        self.assertEqual(lets[1].line, 2)
        self.assertEqual(lets[1].column, 1)
        # `y` identifier on line 2 is after "let ", so column 5.
        idents = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        y_token = idents[1]
        self.assertEqual(y_token.line, 2)
        self.assertEqual(y_token.column, 5)


class TestErrors(unittest.TestCase):
    def test_unterminated_string(self):
        with self.assertRaises(LexError) as ctx:
            tokenize('"unterminated')
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_unterminated_string_multiline(self):
        with self.assertRaises(LexError) as ctx:
            tokenize('let x = 1;\n"unterminated')
        self.assertEqual(ctx.exception.line, 2)
        self.assertEqual(ctx.exception.column, 1)

    def test_unrecognized_character(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("let x = 1; @")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 12)


if __name__ == "__main__":
    unittest.main()
