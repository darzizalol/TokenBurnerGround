"""Tests for cinder.parser: expression precedence, grouping, calls, errors."""

import unittest

from cinder.ast_nodes import Binary, Call, Grouping, Identifier, Literal, Logical, Unary
from cinder.errors import ParseError
from cinder.lexer import tokenize
from cinder.parser import parse_expression


def shape(node):
    """Structural view of an AST node, ignoring line/column noise."""
    if isinstance(node, Literal):
        return ("Literal", node.value)
    if isinstance(node, Identifier):
        return ("Identifier", node.name)
    if isinstance(node, Unary):
        return ("Unary", node.operator.type, shape(node.operand))
    if isinstance(node, Binary):
        return ("Binary", shape(node.left), node.operator.type, shape(node.right))
    if isinstance(node, Logical):
        return ("Logical", shape(node.left), node.operator.type, shape(node.right))
    if isinstance(node, Grouping):
        return ("Grouping", shape(node.expression))
    if isinstance(node, Call):
        return ("Call", shape(node.callee), [shape(a) for a in node.arguments])
    raise TypeError(f"unhandled node type: {type(node)!r}")


def parse(source: str):
    return parse_expression(tokenize(source))


class TestPrecedence(unittest.TestCase):
    def test_addition_and_multiplication(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("1 + 2 * 3")),
            (
                "Binary",
                ("Literal", 1),
                TokenType.PLUS,
                ("Binary", ("Literal", 2), TokenType.STAR, ("Literal", 3)),
            ),
        )

    def test_grouping_overrides_precedence(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("(1 + 2) * 3")),
            (
                "Binary",
                ("Grouping", ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2))),
                TokenType.STAR,
                ("Literal", 3),
            ),
        )

    def test_not_binds_tighter_than_and(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("not true and false")),
            (
                "Logical",
                ("Unary", TokenType.NOT, ("Literal", True)),
                TokenType.AND,
                ("Literal", False),
            ),
        )

    def test_unary_minus_binds_tighter_than_plus(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("-1 + 2")),
            (
                "Binary",
                ("Unary", TokenType.MINUS, ("Literal", 1)),
                TokenType.PLUS,
                ("Literal", 2),
            ),
        )

    def test_comparison_binds_tighter_than_and(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("1 < 2 and 3 > 4")),
            (
                "Logical",
                ("Binary", ("Literal", 1), TokenType.LT, ("Literal", 2)),
                TokenType.AND,
                ("Binary", ("Literal", 3), TokenType.GT, ("Literal", 4)),
            ),
        )

    def test_and_binds_tighter_than_or(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("true or false and true")),
            (
                "Logical",
                ("Literal", True),
                TokenType.OR,
                ("Logical", ("Literal", False), TokenType.AND, ("Literal", True)),
            ),
        )

    def test_left_associative_subtraction(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("10 - 2 - 3")),
            (
                "Binary",
                ("Binary", ("Literal", 10), TokenType.MINUS, ("Literal", 2)),
                TokenType.MINUS,
                ("Literal", 3),
            ),
        )

    def test_identifier_and_string(self):
        self.assertEqual(shape(parse("x")), ("Identifier", "x"))
        self.assertEqual(shape(parse('"hi"')), ("Literal", "hi"))
        self.assertEqual(shape(parse("nil")), ("Literal", None))


class TestCalls(unittest.TestCase):
    def test_call_with_arguments(self):
        self.assertEqual(
            shape(parse("f(1, 2)")),
            ("Call", ("Identifier", "f"), [("Literal", 1), ("Literal", 2)]),
        )

    def test_call_no_arguments(self):
        self.assertEqual(shape(parse("f()")), ("Call", ("Identifier", "f"), []))

    def test_chained_calls(self):
        self.assertEqual(
            shape(parse("f()()")),
            ("Call", ("Call", ("Identifier", "f"), []), []),
        )


class TestErrors(unittest.TestCase):
    def test_unclosed_grouping(self):
        with self.assertRaises(ParseError) as ctx:
            parse("(1 + 2")
        self.assertEqual(ctx.exception.line, 1)

    def test_missing_operand(self):
        with self.assertRaises(ParseError) as ctx:
            parse("1 +")
        self.assertEqual(ctx.exception.line, 1)

    def test_trailing_garbage(self):
        with self.assertRaises(ParseError) as ctx:
            parse("1 + 2 3")
        self.assertEqual(ctx.exception.line, 1)

    def test_error_reports_correct_line(self):
        with self.assertRaises(ParseError) as ctx:
            parse("1 +\n2 +\n")
        self.assertEqual(ctx.exception.line, 3)


if __name__ == "__main__":
    unittest.main()
