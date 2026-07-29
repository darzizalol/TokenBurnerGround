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

    def test_hex_integer(self):
        tokens = tokenize("0x1F")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 31)
        self.assertEqual(tokens[0].lexeme, "0x1F")

    def test_hex_integer_lowercase(self):
        tokens = tokenize("0xff")
        self.assertEqual(tokens[0].literal, 255)

    def test_hex_integer_uppercase_prefix(self):
        tokens = tokenize("0X1f")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 31)

    def test_binary_integer(self):
        tokens = tokenize("0b1010")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 10)

    def test_octal_integer(self):
        tokens = tokenize("0o17")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 15)

    def test_bare_zero_still_decimal(self):
        tokens = tokenize("0")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 0)

    def test_leading_zero_decimal_unaffected(self):
        # No octal-by-leading-zero in Cinder: "007" is decimal 7.
        tokens = tokenize("007")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])
        self.assertEqual(tokens[0].literal, 7)

    def test_hex_literal_in_arithmetic(self):
        tokens = tokenize("0xFF + 1")
        self.assertEqual(
            types(tokens), [TokenType.INT, TokenType.PLUS, TokenType.INT, TokenType.EOF]
        )
        self.assertEqual(tokens[0].literal, 255)

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

    def test_question_question_is_one_token(self):
        # "??" must lex as one QUESTION_QUESTION token, not two QUESTIONs.
        tokens = tokenize("a ?? b")
        self.assertEqual(
            types(tokens),
            [
                TokenType.IDENTIFIER,
                TokenType.QUESTION_QUESTION,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_question_question_does_not_collide_with_ternary_question(self):
        tokens = tokenize("a ? b : c")
        self.assertEqual(
            types(tokens),
            [
                TokenType.IDENTIFIER,
                TokenType.QUESTION,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_bitwise_operators(self):
        source = "& | ^ ~ << >>"
        expected = [
            TokenType.AMP,
            TokenType.PIPE,
            TokenType.CARET,
            TokenType.TILDE,
            TokenType.LSHIFT,
            TokenType.RSHIFT,
            TokenType.EOF,
        ]
        self.assertEqual(types(tokenize(source)), expected)

    def test_lshift_does_not_collide_with_lteq_or_lt(self):
        # "<<" must lex as one LSHIFT token, not two LT tokens.
        tokens = tokenize("1 << 2")
        self.assertEqual(
            types(tokens),
            [TokenType.INT, TokenType.LSHIFT, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, "<<")
        # "<=" still lexes as LTEQ, not LT then EQ.
        self.assertEqual(types(tokenize("1 <= 2")), [TokenType.INT, TokenType.LTEQ, TokenType.INT, TokenType.EOF])
        # A lone "<" still lexes as LT.
        self.assertEqual(types(tokenize("1 < 2")), [TokenType.INT, TokenType.LT, TokenType.INT, TokenType.EOF])

    def test_rshift_does_not_collide_with_gteq_or_gt(self):
        tokens = tokenize("1 >> 2")
        self.assertEqual(
            types(tokens),
            [TokenType.INT, TokenType.RSHIFT, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, ">>")
        self.assertEqual(types(tokenize("1 >= 2")), [TokenType.INT, TokenType.GTEQ, TokenType.INT, TokenType.EOF])
        self.assertEqual(types(tokenize("1 > 2")), [TokenType.INT, TokenType.GT, TokenType.INT, TokenType.EOF])

    def test_dot_dot_dot_does_not_collide_with_dot(self):
        # "..." must lex as one DOT_DOT_DOT token, not three DOT tokens.
        tokens = tokenize("...")
        self.assertEqual(types(tokens), [TokenType.DOT_DOT_DOT, TokenType.EOF])
        self.assertEqual(tokens[0].lexeme, "...")
        # A lone "." still lexes as DOT.
        self.assertEqual(types(tokenize(".")), [TokenType.DOT, TokenType.EOF])

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

    def test_bitwise_compound_assignment_operators(self):
        source = "&= |= ^="
        expected = [
            TokenType.AMPEQ,
            TokenType.PIPEEQ,
            TokenType.CARETEQ,
            TokenType.EOF,
        ]
        self.assertEqual(types(tokenize(source)), expected)

    def test_bitwise_compound_assignment_lexes_as_single_token(self):
        tokens = tokenize("a &= 1")
        self.assertEqual(
            types(tokens),
            [TokenType.IDENTIFIER, TokenType.AMPEQ, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, "&=")
        # A lone `&` still lexes as AMP, not AMPEQ.
        self.assertEqual(types(tokenize("a & 1")), [TokenType.IDENTIFIER, TokenType.AMP, TokenType.INT, TokenType.EOF])

    def test_shift_compound_assignment_operators(self):
        tokens = tokenize("a <<= 1; b >>= 2;")
        self.assertEqual(
            types(tokens),
            [
                TokenType.IDENTIFIER,
                TokenType.LSHIFTEQ,
                TokenType.INT,
                TokenType.SEMICOLON,
                TokenType.IDENTIFIER,
                TokenType.RSHIFTEQ,
                TokenType.INT,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[1].lexeme, "<<=")
        self.assertEqual(tokens[5].lexeme, ">>=")

    def test_shift_compound_assignment_does_not_collide_with_shift_or_comparisons(self):
        # Plain `<<`/`>>` (no trailing `=`) still lex as before.
        self.assertEqual(
            types(tokenize("1 << 2")),
            [TokenType.INT, TokenType.LSHIFT, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(
            types(tokenize("1 >> 2")),
            [TokenType.INT, TokenType.RSHIFT, TokenType.INT, TokenType.EOF],
        )
        # `<=`/`>=` are unaffected by the new lookahead.
        self.assertEqual(
            types(tokenize("1 <= 2")),
            [TokenType.INT, TokenType.LTEQ, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(
            types(tokenize("1 >= 2")),
            [TokenType.INT, TokenType.GTEQ, TokenType.INT, TokenType.EOF],
        )

    def test_increment_decrement_operators(self):
        tokens = tokenize("a++; b--;")
        self.assertEqual(
            types(tokens),
            [
                TokenType.IDENTIFIER,
                TokenType.PLUSPLUS,
                TokenType.SEMICOLON,
                TokenType.IDENTIFIER,
                TokenType.MINUSMINUS,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[1].lexeme, "++")
        self.assertEqual(tokens[4].lexeme, "--")

    def test_increment_decrement_does_not_collide_with_plus_minus_or_compound_assign(self):
        # Plain `+`/`-` and `+=`/`-=` still lex as before.
        self.assertEqual(
            types(tokenize("1 + 2")),
            [TokenType.INT, TokenType.PLUS, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(
            types(tokenize("1 - 2")),
            [TokenType.INT, TokenType.MINUS, TokenType.INT, TokenType.EOF],
        )
        tokens = tokenize("a += 1")
        self.assertEqual(
            types(tokens),
            [TokenType.IDENTIFIER, TokenType.PLUSEQ, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, "+=")
        tokens = tokenize("a -= 1")
        self.assertEqual(
            types(tokens),
            [TokenType.IDENTIFIER, TokenType.MINUSEQ, TokenType.INT, TokenType.EOF],
        )
        self.assertEqual(tokens[1].lexeme, "-=")


class TestComments(unittest.TestCase):
    def test_comment_stripped(self):
        tokens = tokenize("let x = 1; # this is a comment\nlet y = 2;")
        self.assertNotIn("#", [t.lexeme for t in tokens])
        let_count = sum(1 for t in tokens if t.type == TokenType.LET)
        self.assertEqual(let_count, 2)

    def test_comment_to_end_of_file(self):
        tokens = tokenize("42 # trailing comment with no newline")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])

    def test_block_comment_leading(self):
        tokens = tokenize("/* comment */ 1")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])

    def test_block_comment_trailing(self):
        tokens = tokenize("1 /* trailing */")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])

    def test_block_comment_between_tokens_acts_as_whitespace(self):
        tokens = tokenize("1 /* comment */ + 2")
        self.assertEqual(
            types(tokens),
            [TokenType.INT, TokenType.PLUS, TokenType.INT, TokenType.EOF],
        )

    def test_block_comment_does_not_nest(self):
        # The first `*/` closes the comment, so the trailing `*/` lexes as
        # normal tokens (STAR then SLASH), matching C/Java/JS semantics.
        tokens = tokenize("/* outer /* inner */ 1 */")
        self.assertEqual(
            types(tokens),
            [
                TokenType.INT,
                TokenType.STAR,
                TokenType.SLASH,
                TokenType.EOF,
            ],
        )

    def test_line_comment_containing_block_comment_markers(self):
        tokens = tokenize("# /* not a block comment */\n1")
        self.assertEqual(types(tokens), [TokenType.INT, TokenType.EOF])

    def test_division_still_lexes(self):
        tokens = tokenize("10 / 2")
        self.assertEqual(
            types(tokens),
            [TokenType.INT, TokenType.SLASH, TokenType.INT, TokenType.EOF],
        )

    def test_compound_divide_assign_still_lexes(self):
        tokens = tokenize("x /= 2")
        self.assertEqual(
            types(tokens),
            [TokenType.IDENTIFIER, TokenType.SLASHEQ, TokenType.INT, TokenType.EOF],
        )

    def test_multiline_block_comment_preserves_line_numbers(self):
        source = "1;\n/* line 2\nline 3\nline 4 */\n@"
        with self.assertRaises(LexError) as ctx:
            tokenize(source)
        self.assertEqual(ctx.exception.line, 5)
        self.assertEqual(ctx.exception.column, 1)


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


class TestStringInterpolation(unittest.TestCase):
    def test_plain_string_has_no_interpolation(self):
        tokens = tokenize('"plain"')
        self.assertEqual(types(tokens), [TokenType.STRING, TokenType.EOF])
        self.assertEqual(tokens[0].literal, "plain")

    def test_single_placeholder(self):
        tokens = tokenize('"hello, ${name}!"')
        self.assertEqual(types(tokens), [TokenType.INTERP_STRING, TokenType.EOF])
        self.assertEqual(
            tokens[0].literal, ["hello, ", ("expr", "name", 1, 11), "!"]
        )

    def test_multiple_placeholders(self):
        tokens = tokenize('"a${1}b${2}c"')
        self.assertEqual(
            tokens[0].literal,
            ["a", ("expr", "1", 1, 5), "b", ("expr", "2", 1, 10), "c"],
        )

    def test_leading_and_trailing_placeholders_keep_empty_literal_segments(self):
        # The lexer itself doesn't drop empty literal segments — the parser
        # does, when building the `InterpString` AST node.
        tokens = tokenize('"${1}${2}"')
        parts = tokens[0].literal
        self.assertEqual([p for p in parts if isinstance(p, str)], ["", "", ""])

    def test_nested_braces_not_truncated(self):
        tokens = tokenize('"${ {"a": 1} }"')
        self.assertEqual(types(tokens), [TokenType.INTERP_STRING, TokenType.EOF])
        self.assertEqual(tokens[0].literal, ["", ("expr", ' {"a": 1} ', 1, 4), ""])

    def test_escapes_still_work_alongside_interpolation(self):
        tokens = tokenize(r'"a\nb${1}"')
        self.assertEqual(tokens[0].literal[0], "a\nb")

    def test_placeholder_raw_source_and_position(self):
        # Position is of the first character *inside* the placeholder (after
        # the opening quote, `$`, and `{`), not the string's opening quote.
        tokens = tokenize('"${1/0}"')
        _, raw, line, col = tokens[0].literal[1]
        self.assertEqual(raw, "1/0")
        self.assertEqual((line, col), (1, 4))


class TestErrors(unittest.TestCase):
    def test_unterminated_string(self):
        with self.assertRaises(LexError) as ctx:
            tokenize('"unterminated')
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_unterminated_placeholder(self):
        with self.assertRaises(LexError) as ctx:
            tokenize('"unterminated ${1 + 1"')
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)
        self.assertTrue(ctx.exception.unterminated)

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

    def test_unterminated_block_comment(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("1 /* unterminated")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 3)
        self.assertTrue(ctx.exception.unterminated)

    def test_unterminated_block_comment_multiline(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("1;\n/* opened here\nstill open")
        self.assertEqual(ctx.exception.line, 2)
        self.assertEqual(ctx.exception.column, 1)
        self.assertTrue(ctx.exception.unterminated)

    def test_hex_prefix_without_digits(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("0x")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_binary_prefix_without_digits(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("0b")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_hex_invalid_digit(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("0x1G")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_binary_invalid_digit(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("0b12")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_octal_invalid_digit(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("0o8")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)


if __name__ == "__main__":
    unittest.main()
