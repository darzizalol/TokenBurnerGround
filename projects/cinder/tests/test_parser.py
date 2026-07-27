"""Tests for cinder.parser: expression precedence, grouping, calls, errors."""

import unittest

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    BreakStmt,
    Call,
    ContinueStmt,
    DestructureLetStmt,
    ExprStmt,
    FnDecl,
    FnExpr,
    ForStmt,
    Grouping,
    Identifier,
    Index,
    IndexAssign,
    IndexCompoundAssign,
    InterpString,
    LetStmt,
    ListLiteral,
    Literal,
    Logical,
    MapLiteral,
    ReturnStmt,
    SliceExpr,
    Spread,
    SwitchStmt,
    Ternary,
    TryStmt,
    Unary,
)
from cinder.errors import LexError, ParseError
from cinder.lexer import tokenize
from cinder.parser import parse_expression, parse_program
from cinder.tokens import TokenType


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
    if isinstance(node, Spread):
        return ("Spread", shape(node.expression))
    if isinstance(node, ListLiteral):
        return ("ListLiteral", [shape(e) for e in node.elements])
    if isinstance(node, MapLiteral):
        return ("MapLiteral", [(shape(k), shape(v)) for k, v in node.pairs])
    if isinstance(node, Index):
        return ("Index", shape(node.obj), shape(node.index))
    if isinstance(node, SliceExpr):
        return (
            "SliceExpr",
            shape(node.obj),
            shape(node.start) if node.start is not None else None,
            shape(node.end) if node.end is not None else None,
        )
    if isinstance(node, IndexAssign):
        return (
            "IndexAssign",
            shape(node.obj),
            shape(node.index),
            shape(node.value),
        )
    if isinstance(node, IndexCompoundAssign):
        return (
            "IndexCompoundAssign",
            shape(node.obj),
            shape(node.index),
            node.operator.type,
            shape(node.value),
        )
    if isinstance(node, Assign):
        return ("Assign", node.name, shape(node.value))
    if isinstance(node, Ternary):
        return (
            "Ternary",
            shape(node.condition),
            shape(node.then_expr),
            shape(node.else_expr),
        )
    if isinstance(node, FnExpr):
        return ("FnExpr", params_shape(node.params), node.rest_param, stmt_shape(node.body))
    if isinstance(node, InterpString):
        return (
            "InterpString",
            [part if isinstance(part, str) else shape(part) for part in node.parts],
        )
    raise TypeError(f"unhandled node type: {type(node)!r}")


def params_shape(params):
    """Structural view of an `FnDecl`/`FnExpr` params list."""
    return [
        (name, shape(default) if default is not None else None)
        for name, default in params
    ]


def parse(source: str):
    return parse_expression(tokenize(source))


def parse_stmts(source: str):
    return parse_program(tokenize(source))


def stmt_shape(node):
    """Structural view of a statement AST node, ignoring line/column noise."""
    if isinstance(node, LetStmt):
        return ("LetStmt", node.name, shape(node.initializer))
    if isinstance(node, DestructureLetStmt):
        return ("DestructureLetStmt", node.names, shape(node.initializer), node.is_map)
    if isinstance(node, ExprStmt):
        return ("ExprStmt", shape(node.expression))
    if isinstance(node, Block):
        return ("Block", [stmt_shape(s) for s in node.statements])
    if isinstance(node, FnDecl):
        return (
            "FnDecl",
            node.name,
            params_shape(node.params),
            node.rest_param,
            stmt_shape(node.body),
        )
    if isinstance(node, ReturnStmt):
        return ("ReturnStmt", shape(node.value) if node.value is not None else None)
    if isinstance(node, ForStmt):
        return (
            "ForStmt",
            node.var_name,
            shape(node.iterable),
            stmt_shape(node.body),
        )
    if isinstance(node, BreakStmt):
        return ("BreakStmt",)
    if isinstance(node, ContinueStmt):
        return ("ContinueStmt",)
    if isinstance(node, TryStmt):
        return (
            "TryStmt",
            stmt_shape(node.try_block),
            node.catch_name,
            stmt_shape(node.catch_block),
        )
    if isinstance(node, SwitchStmt):
        return (
            "SwitchStmt",
            shape(node.scrutinee),
            [(shape(case.value), stmt_shape(case.body)) for case in node.cases],
            stmt_shape(node.default) if node.default is not None else None,
        )
    raise TypeError(f"unhandled statement type: {type(node)!r}")


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

    def test_in_is_binary_op(self):
        self.assertEqual(
            shape(parse("2 in [1, 2, 3]")),
            (
                "Binary",
                ("Literal", 2),
                TokenType.IN,
                ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
            ),
        )

    def test_in_binds_tighter_than_and(self):
        self.assertEqual(
            shape(parse("1 in [1] and 2 in [2]")),
            (
                "Logical",
                ("Binary", ("Literal", 1), TokenType.IN, ("ListLiteral", [("Literal", 1)])),
                TokenType.AND,
                ("Binary", ("Literal", 2), TokenType.IN, ("ListLiteral", [("Literal", 2)])),
            ),
        )

    def test_comparison_binds_tighter_than_in(self):
        self.assertEqual(
            shape(parse("1 < 2 in [true]")),
            (
                "Binary",
                ("Binary", ("Literal", 1), TokenType.LT, ("Literal", 2)),
                TokenType.IN,
                ("ListLiteral", [("Literal", True)]),
            ),
        )

    def test_bitwise_or_binds_looser_than_comparison(self):
        # `1 | 2 == 3` parses as `1 | (2 == 3)` or `(1 | 2) == 3`; this repo
        # picks the latter, since bitwise ops bind tighter than comparisons.
        self.assertEqual(
            shape(parse("1 | 2 == 3")),
            (
                "Binary",
                ("Binary", ("Literal", 1), TokenType.PIPE, ("Literal", 2)),
                TokenType.EQEQ,
                ("Literal", 3),
            ),
        )

    def test_shift_binds_looser_than_addition(self):
        # `2 + 3 << 1` is `(2 + 3) << 1`, not `2 + (3 << 1)`.
        self.assertEqual(
            shape(parse("2 + 3 << 1")),
            (
                "Binary",
                ("Binary", ("Literal", 2), TokenType.PLUS, ("Literal", 3)),
                TokenType.LSHIFT,
                ("Literal", 1),
            ),
        )

    def test_bitwise_precedence_or_xor_and_shift(self):
        # `|` loosest, then `^`, then `&`, then `<<`/`>>` tightest.
        self.assertEqual(
            shape(parse("1 | 2 ^ 3 & 4 << 5")),
            (
                "Binary",
                ("Literal", 1),
                TokenType.PIPE,
                (
                    "Binary",
                    ("Literal", 2),
                    TokenType.CARET,
                    (
                        "Binary",
                        ("Literal", 3),
                        TokenType.AMP,
                        ("Binary", ("Literal", 4), TokenType.LSHIFT, ("Literal", 5)),
                    ),
                ),
            ),
        )

    def test_bitwise_not_binds_tighter_than_shift(self):
        self.assertEqual(
            shape(parse("~1 << 2")),
            (
                "Binary",
                ("Unary", TokenType.TILDE, ("Literal", 1)),
                TokenType.LSHIFT,
                ("Literal", 2),
            ),
        )

    def test_nullish_binds_looser_than_or(self):
        # `a or b ?? c` parses as `(a or b) ?? c`.
        self.assertEqual(
            shape(parse("true or false ?? 1")),
            (
                "Logical",
                ("Logical", ("Literal", True), TokenType.OR, ("Literal", False)),
                TokenType.QUESTION_QUESTION,
                ("Literal", 1),
            ),
        )

    def test_for_in_loop_parsing_unaffected_by_in_operator(self):
        self.assertEqual(
            stmt_shape(parse_stmts("for x in [1, 2, 3] { }")[0]),
            (
                "ForStmt",
                "x",
                ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
                ("Block", []),
            ),
        )


class TestTernary(unittest.TestCase):
    def test_basic_ternary(self):
        self.assertEqual(
            shape(parse("true ? 1 : 2")),
            ("Ternary", ("Literal", True), ("Literal", 1), ("Literal", 2)),
        )

    def test_ternary_right_associative_in_else_branch(self):
        # `a ? b : c ? d : e` parses as `a ? b : (c ? d : e)`.
        self.assertEqual(
            shape(parse("true ? 1 : false ? 2 : 3")),
            (
                "Ternary",
                ("Literal", True),
                ("Literal", 1),
                ("Ternary", ("Literal", False), ("Literal", 2), ("Literal", 3)),
            ),
        )

    def test_nested_ternary_in_then_branch(self):
        self.assertEqual(
            shape(parse("true ? false ? 1 : 2 : 3")),
            (
                "Ternary",
                ("Literal", True),
                ("Ternary", ("Literal", False), ("Literal", 1), ("Literal", 2)),
                ("Literal", 3),
            ),
        )

    def test_ternary_condition_binds_looser_than_or(self):
        self.assertEqual(
            shape(parse("true or false ? 1 : 2")),
            (
                "Ternary",
                ("Logical", ("Literal", True), TokenType.OR, ("Literal", False)),
                ("Literal", 1),
                ("Literal", 2),
            ),
        )

    def test_map_literal_statement_with_ternary(self):
        # A leading `{` map literal statement must still parse correctly
        # when followed by a ternary operator.
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1} ? 1 : 2;')],
            [
                (
                    "ExprStmt",
                    (
                        "Ternary",
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                        ("Literal", 1),
                        ("Literal", 2),
                    ),
                )
            ],
        )

    def test_ternary_missing_colon_raises(self):
        with self.assertRaises(ParseError):
            parse("true ? 1 2")

    def test_ternary_as_call_argument(self):
        self.assertEqual(
            shape(parse("f(true ? 1 : 2)")),
            (
                "Call",
                ("Identifier", "f"),
                [("Ternary", ("Literal", True), ("Literal", 1), ("Literal", 2))],
            ),
        )

    def test_ternary_as_list_element(self):
        self.assertEqual(
            shape(parse("[1, true ? 2 : 3, 4]")),
            (
                "ListLiteral",
                [
                    ("Literal", 1),
                    ("Ternary", ("Literal", True), ("Literal", 2), ("Literal", 3)),
                    ("Literal", 4),
                ],
            ),
        )

    def test_ternary_as_map_value(self):
        self.assertEqual(
            shape(parse('{"k": true ? 1 : 2}')),
            (
                "MapLiteral",
                [
                    (
                        ("Literal", "k"),
                        ("Ternary", ("Literal", True), ("Literal", 1), ("Literal", 2)),
                    )
                ],
            ),
        )

    def test_ternary_as_index(self):
        self.assertEqual(
            shape(parse("xs[true ? 0 : 1]")),
            (
                "Index",
                ("Identifier", "xs"),
                ("Ternary", ("Literal", True), ("Literal", 0), ("Literal", 1)),
            ),
        )


class TestNullishCoalescing(unittest.TestCase):
    def test_basic_nullish(self):
        self.assertEqual(
            shape(parse("a ?? b")),
            ("Logical", ("Identifier", "a"), TokenType.QUESTION_QUESTION, ("Identifier", "b")),
        )

    def test_nullish_right_associative(self):
        # `a ?? b ?? c` parses as `a ?? (b ?? c)`.
        self.assertEqual(
            shape(parse("a ?? b ?? c")),
            (
                "Logical",
                ("Identifier", "a"),
                TokenType.QUESTION_QUESTION,
                ("Logical", ("Identifier", "b"), TokenType.QUESTION_QUESTION, ("Identifier", "c")),
            ),
        )

    def test_nullish_binds_tighter_than_ternary(self):
        # `a ?? b ? c : d` parses as `(a ?? b) ? c : d`.
        self.assertEqual(
            shape(parse("a ?? b ? c : d")),
            (
                "Ternary",
                ("Logical", ("Identifier", "a"), TokenType.QUESTION_QUESTION, ("Identifier", "b")),
                ("Identifier", "c"),
                ("Identifier", "d"),
            ),
        )


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

    def test_call_with_spread_argument(self):
        self.assertEqual(
            shape(parse("f(...args)")),
            ("Call", ("Identifier", "f"), [("Spread", ("Identifier", "args"))]),
        )

    def test_call_with_mixed_spread_and_plain_arguments(self):
        self.assertEqual(
            shape(parse("f(1, ...xs, 2)")),
            (
                "Call",
                ("Identifier", "f"),
                [
                    ("Literal", 1),
                    ("Spread", ("Identifier", "xs")),
                    ("Literal", 2),
                ],
            ),
        )

    def test_call_with_multiple_spread_arguments(self):
        self.assertEqual(
            shape(parse("f(...xs, ...ys)")),
            (
                "Call",
                ("Identifier", "f"),
                [
                    ("Spread", ("Identifier", "xs")),
                    ("Spread", ("Identifier", "ys")),
                ],
            ),
        )


class TestListsAndMaps(unittest.TestCase):
    def test_list_literal(self):
        self.assertEqual(
            shape(parse("[1, 2, 3]")),
            ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
        )

    def test_empty_list_literal(self):
        self.assertEqual(shape(parse("[]")), ("ListLiteral", []))

    def test_list_literal_with_spread(self):
        self.assertEqual(
            shape(parse("[...[1, 2], 3]")),
            (
                "ListLiteral",
                [
                    ("Spread", ("ListLiteral", [("Literal", 1), ("Literal", 2)])),
                    ("Literal", 3),
                ],
            ),
        )

    def test_list_literal_multiple_spreads(self):
        self.assertEqual(
            shape(parse("[0, ...[1, 2], 3, ...[4, 5]]")),
            (
                "ListLiteral",
                [
                    ("Literal", 0),
                    ("Spread", ("ListLiteral", [("Literal", 1), ("Literal", 2)])),
                    ("Literal", 3),
                    ("Spread", ("ListLiteral", [("Literal", 4), ("Literal", 5)])),
                ],
            ),
        )

    def test_bare_spread_in_map_literal_raises(self):
        with self.assertRaises(ParseError):
            parse("{...m}")

    def test_map_literal(self):
        self.assertEqual(
            shape(parse('{"a": 1, "b": 2}')),
            (
                "MapLiteral",
                [
                    (("Literal", "a"), ("Literal", 1)),
                    (("Literal", "b"), ("Literal", 2)),
                ],
            ),
        )

    def test_empty_map_literal(self):
        self.assertEqual(shape(parse("{}")), ("MapLiteral", []))

    def test_index_get(self):
        self.assertEqual(
            shape(parse("xs[0]")),
            ("Index", ("Identifier", "xs"), ("Literal", 0)),
        )

    def test_chained_index(self):
        self.assertEqual(
            shape(parse("xs[0][1]")),
            ("Index", ("Index", ("Identifier", "xs"), ("Literal", 0)), ("Literal", 1)),
        )

    def test_index_assignment(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("xs[0] = 5;")],
            [
                (
                    "ExprStmt",
                    ("IndexAssign", ("Identifier", "xs"), ("Literal", 0), ("Literal", 5)),
                )
            ],
        )

    def test_map_literal_missing_colon_raises(self):
        with self.assertRaises(ParseError):
            parse('{"a" 1}')

    def test_unclosed_list_literal_raises(self):
        with self.assertRaises(ParseError):
            parse("[1, 2")

    def test_slice_both_bounds(self):
        self.assertEqual(
            shape(parse("xs[1:3]")),
            ("SliceExpr", ("Identifier", "xs"), ("Literal", 1), ("Literal", 3)),
        )

    def test_slice_missing_start(self):
        self.assertEqual(
            shape(parse("xs[:3]")),
            ("SliceExpr", ("Identifier", "xs"), None, ("Literal", 3)),
        )

    def test_slice_missing_end(self):
        self.assertEqual(
            shape(parse("xs[1:]")),
            ("SliceExpr", ("Identifier", "xs"), ("Literal", 1), None),
        )

    def test_slice_both_missing(self):
        self.assertEqual(
            shape(parse("xs[:]")),
            ("SliceExpr", ("Identifier", "xs"), None, None),
        )

    def test_plain_index_unaffected_by_slice_grammar(self):
        self.assertEqual(
            shape(parse("xs[1]")),
            ("Index", ("Identifier", "xs"), ("Literal", 1)),
        )

    def test_slice_assignment_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("xs[1:2] = [9];")


class TestStringInterpolation(unittest.TestCase):
    def test_plain_string_stays_a_literal(self):
        self.assertEqual(shape(parse('"plain"')), ("Literal", "plain"))

    def test_identifier_placeholder(self):
        self.assertEqual(
            shape(parse('"hello, ${name}!"')),
            ("InterpString", ["hello, ", ("Identifier", "name"), "!"]),
        )

    def test_arbitrary_expression_placeholder(self):
        self.assertEqual(
            shape(parse('"${1 + 2}"')),
            (
                "InterpString",
                [("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2))],
            ),
        )

    def test_multiple_placeholders(self):
        self.assertEqual(
            shape(parse('"a${1}b${2}c"')),
            ("InterpString", ["a", ("Literal", 1), "b", ("Literal", 2), "c"]),
        )

    def test_leading_and_trailing_placeholders_drop_empty_literals(self):
        self.assertEqual(
            shape(parse('"${1}${2}"')),
            ("InterpString", [("Literal", 1), ("Literal", 2)]),
        )

    def test_nested_braces_in_placeholder_not_truncated(self):
        self.assertEqual(
            shape(parse('"${ {"a": 1}["a"] }"')),
            (
                "InterpString",
                [
                    (
                        "Index",
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                        ("Literal", "a"),
                    )
                ],
            ),
        )

    def test_list_placeholder(self):
        self.assertEqual(
            shape(parse('"${[1, 2, 3]}"')),
            (
                "InterpString",
                [("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)])],
            ),
        )

    def test_placeholder_expression_position_matches_source(self):
        # The `/` in the placeholder is at line 1, column 5 (after `"`, `$`,
        # `{`, `1`) — not the string literal's opening-quote position.
        node = parse('"${1/0}"')
        placeholder = node.parts[0]
        self.assertEqual(
            (placeholder.operator.line, placeholder.operator.column), (1, 5)
        )

    def test_unterminated_placeholder_raises_lex_error(self):
        with self.assertRaises(LexError):
            parse('"unterminated ${1 + 1"')

    def test_malformed_placeholder_expression_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse('"${)}"')


class TestCompoundAssignment(unittest.TestCase):
    def test_plus_eq_desugars_to_binary_plus(self):
        self.assertEqual(
            shape(parse("x += 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.PLUS, ("Literal", 1))),
        )

    def test_minus_eq_desugars_to_binary_minus(self):
        self.assertEqual(
            shape(parse("x -= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.MINUS, ("Literal", 1))),
        )

    def test_star_eq_desugars_to_binary_star(self):
        self.assertEqual(
            shape(parse("x *= 2")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.STAR, ("Literal", 2))),
        )

    def test_slash_eq_desugars_to_binary_slash(self):
        self.assertEqual(
            shape(parse("x /= 2")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.SLASH, ("Literal", 2))),
        )

    def test_percent_eq_desugars_to_binary_percent(self):
        self.assertEqual(
            shape(parse("x %= 3")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.PERCENT, ("Literal", 3))),
        )

    def test_index_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("xs[0] += 1;")

    def test_amp_eq_desugars_to_binary_amp(self):
        self.assertEqual(
            shape(parse("x &= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.AMP, ("Literal", 1))),
        )

    def test_pipe_eq_desugars_to_binary_pipe(self):
        self.assertEqual(
            shape(parse("x |= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.PIPE, ("Literal", 1))),
        )

    def test_caret_eq_desugars_to_binary_caret(self):
        self.assertEqual(
            shape(parse("x ^= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.CARET, ("Literal", 1))),
        )

    def test_lshift_eq_desugars_to_binary_lshift(self):
        self.assertEqual(
            shape(parse("x <<= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.LSHIFT, ("Literal", 1))),
        )

    def test_rshift_eq_desugars_to_binary_rshift(self):
        self.assertEqual(
            shape(parse("x >>= 1")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.RSHIFT, ("Literal", 1))),
        )

    def test_bitwise_compound_assign_allows_index_target(self):
        # Unlike the arithmetic set, the bitwise/shift ops accept an
        # index-expression target too, desugaring into IndexCompoundAssign
        # (not IndexAssign wrapping a Binary over the same Index node, which
        # would evaluate obj/index twice at runtime).
        stmts = parse_stmts("xs[0] &= 1;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.AMP,
                    ("Literal", 1),
                ),
            ),
        )

    def test_plain_lshift_and_rshift_unaffected(self):
        # Regression: plain (non-assignment) `<<`/`>>` still parse as before.
        self.assertEqual(
            shape(parse("1 << 2")),
            ("Binary", ("Literal", 1), TokenType.LSHIFT, ("Literal", 2)),
        )
        self.assertEqual(
            shape(parse("1 >> 2")),
            ("Binary", ("Literal", 1), TokenType.RSHIFT, ("Literal", 2)),
        )


class TestStatements(unittest.TestCase):
    def test_let_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let x = 1 + 2;")],
            [("LetStmt", "x", ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2)))],
        )

    def test_expr_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("1 + 2;")],
            [("ExprStmt", ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2)))],
        )

    def test_multiple_statements(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let x = 1; let y = 2;")],
            [
                ("LetStmt", "x", ("Literal", 1)),
                ("LetStmt", "y", ("Literal", 2)),
            ],
        )

    def test_block_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("{ let x = 1; x; }")],
            [("Block", [("LetStmt", "x", ("Literal", 1)), ("ExprStmt", ("Identifier", "x"))])],
        )

    def test_empty_block(self):
        self.assertEqual([stmt_shape(s) for s in parse_stmts("{}")], [("Block", [])])

    def test_nested_block(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("{ { let x = 1; } }")],
            [("Block", [("Block", [("LetStmt", "x", ("Literal", 1))])])],
        )

    def test_let_missing_equals_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let x 1;")

    def test_let_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let x = 1")

    def test_destructure_let_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [a, b] = [1, 2];")],
            [
                (
                    "DestructureLetStmt",
                    ["a", "b"],
                    ("ListLiteral", [("Literal", 1), ("Literal", 2)]),
                    False,
                )
            ],
        )

    def test_destructure_let_statement_single_name(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [a] = [1];")],
            [("DestructureLetStmt", ["a"], ("ListLiteral", [("Literal", 1)]), False)],
        )

    def test_destructure_let_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [1, b] = [1, 2];")

    def test_destructure_let_missing_equals_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [a, b] [1, 2];")

    def test_destructure_let_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [a, b] = [1, 2]")

    def test_destructure_let_unclosed_bracket_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [a, b = [1, 2];")

    def test_destructure_let_map_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('let {a, b} = {"a": 1, "b": 2};')],
            [
                (
                    "DestructureLetStmt",
                    ["a", "b"],
                    (
                        "MapLiteral",
                        [
                            (("Literal", "a"), ("Literal", 1)),
                            (("Literal", "b"), ("Literal", 2)),
                        ],
                    ),
                    True,
                )
            ],
        )

    def test_destructure_let_map_statement_single_name(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('let {a} = {"a": 1};')],
            [
                (
                    "DestructureLetStmt",
                    ["a"],
                    ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                    True,
                )
            ],
        )

    def test_destructure_let_map_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('let {1, b} = {"a": 1, "b": 2};')

    def test_destructure_let_map_missing_equals_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('let {a, b} {"a": 1, "b": 2};')

    def test_destructure_let_map_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('let {a, b} = {"a": 1, "b": 2}')

    def test_destructure_let_map_unclosed_brace_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('let {a, b = {"a": 1, "b": 2};')

    def test_unclosed_block_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("{ let x = 1; ")

    def test_map_literal_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1};')],
            [("ExprStmt", ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]))],
        )

    def test_map_literal_statement_multiple_pairs(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1, "b": 2};')],
            [
                (
                    "ExprStmt",
                    (
                        "MapLiteral",
                        [
                            (("Literal", "a"), ("Literal", 1)),
                            (("Literal", "b"), ("Literal", 2)),
                        ],
                    ),
                )
            ],
        )

    def test_map_literal_statement_inside_block(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{ {"a": 1}; }')],
            [("Block", [("ExprStmt", ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]))])],
        )

    def test_map_literal_statement_with_index(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1}["a"];')],
            [
                (
                    "ExprStmt",
                    (
                        "Index",
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                        ("Literal", "a"),
                    ),
                )
            ],
        )

    def test_map_literal_statement_with_call(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1}();')],
            [
                (
                    "ExprStmt",
                    ("Call", ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]), []),
                )
            ],
        )

    def test_map_literal_statement_with_binary_op(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1} == {"a": 1};')],
            [
                (
                    "ExprStmt",
                    (
                        "Binary",
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                        TokenType.EQEQ,
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                    ),
                )
            ],
        )

    def test_block_still_parses_as_block(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("{ let x = 1; print(x); }")],
            [
                (
                    "Block",
                    [
                        ("LetStmt", "x", ("Literal", 1)),
                        ("ExprStmt", ("Call", ("Identifier", "print"), [("Identifier", "x")])),
                    ],
                )
            ],
        )


class TestFunctions(unittest.TestCase):
    def test_fn_declaration_no_params(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f() { return 1; }")],
            [("FnDecl", "f", [], None, ("Block", [("ReturnStmt", ("Literal", 1))]))],
        )

    def test_fn_declaration_with_params(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn add(a, b) { return a + b; }")],
            [
                (
                    "FnDecl",
                    "add",
                    [("a", None), ("b", None)],
                    None,
                    (
                        "Block",
                        [
                            (
                                "ReturnStmt",
                                ("Binary", ("Identifier", "a"), TokenType.PLUS, ("Identifier", "b")),
                            )
                        ],
                    ),
                )
            ],
        )

    def test_return_without_value(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f() { return; }")],
            [("FnDecl", "f", [], None, ("Block", [("ReturnStmt", None)]))],
        )

    def test_call_expression_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("f(1, 2);")],
            [("ExprStmt", ("Call", ("Identifier", "f"), [("Literal", 1), ("Literal", 2)]))],
        )

    def test_fn_missing_body_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f()")

    def test_return_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f() { return 1 }")

    def test_fn_expression_no_params(self):
        self.assertEqual(
            shape(parse("fn() { return 1; }")),
            ("FnExpr", [], None, ("Block", [("ReturnStmt", ("Literal", 1))])),
        )

    def test_fn_expression_with_params(self):
        self.assertEqual(
            shape(parse("fn(x) { return x * 2; }")),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            ("Binary", ("Identifier", "x"), TokenType.STAR, ("Literal", 2)),
                        )
                    ],
                ),
            ),
        )

    def test_fn_expression_as_call_argument(self):
        self.assertEqual(
            shape(parse("map([1], fn(x) { return x; })")),
            (
                "Call",
                ("Identifier", "map"),
                [
                    ("ListLiteral", [("Literal", 1)]),
                    (
                        "FnExpr",
                        [("x", None)],
                        None,
                        ("Block", [("ReturnStmt", ("Identifier", "x"))]),
                    ),
                ],
            ),
        )

    def test_fn_expression_missing_body_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let f = fn();")

    def test_fn_declaration_with_default_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('fn greet(name, greeting = "hi") { return greeting; }')],
            [
                (
                    "FnDecl",
                    "greet",
                    [("name", None), ("greeting", ("Literal", "hi"))],
                    None,
                    ("Block", [("ReturnStmt", ("Identifier", "greeting"))]),
                )
            ],
        )

    def test_fn_declaration_default_referencing_earlier_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f(a, b = a + 1) { return b; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [
                        ("a", None),
                        (
                            "b",
                            ("Binary", ("Identifier", "a"), TokenType.PLUS, ("Literal", 1)),
                        ),
                    ],
                    None,
                    ("Block", [("ReturnStmt", ("Identifier", "b"))]),
                )
            ],
        )

    def test_fn_expression_with_default_param(self):
        self.assertEqual(
            shape(parse("fn(a, b = 2) { return a + b; }")),
            (
                "FnExpr",
                [("a", None), ("b", ("Literal", 2))],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            ("Binary", ("Identifier", "a"), TokenType.PLUS, ("Identifier", "b")),
                        )
                    ],
                ),
            ),
        )

    def test_fn_non_default_param_after_default_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f(a = 1, b) { }")

    def test_fn_declaration_with_rest_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f(a, ...rest) { return rest; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [("a", None)],
                    "rest",
                    ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
                )
            ],
        )

    def test_fn_declaration_with_only_rest_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f(...rest) { return rest; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [],
                    "rest",
                    ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
                )
            ],
        )

    def test_fn_expression_with_rest_param(self):
        self.assertEqual(
            shape(parse("fn(a, ...rest) { return rest; }")),
            (
                "FnExpr",
                [("a", None)],
                "rest",
                ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
            ),
        )

    def test_fn_rest_param_after_default_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f(a, b = 1, ...rest) { return rest; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [("a", None), ("b", ("Literal", 1))],
                    "rest",
                    ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
                )
            ],
        )

    def test_fn_rest_param_not_last_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f(...rest, a) { }")

    def test_fn_multiple_rest_params_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f(...a, ...b) { }")

    def test_fn_rest_param_missing_name_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f(...) { }")

    def test_return_at_top_level_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("return 5;")

    def test_return_inside_top_level_if_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("if (true) { return 5; }")

    def test_return_inside_top_level_while_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { return 5; }")

    def test_return_after_fn_body_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f() { return 1; } return 2;")


class TestForStatement(unittest.TestCase):
    def test_for_in_list_literal(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("for x in [1, 2, 3] { print(x); }")],
            [
                (
                    "ForStmt",
                    "x",
                    ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
                    (
                        "Block",
                        [
                            (
                                "ExprStmt",
                                ("Call", ("Identifier", "print"), [("Identifier", "x")]),
                            )
                        ],
                    ),
                )
            ],
        )

    def test_for_in_identifier(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("for x in xs { }")],
            [("ForStmt", "x", ("Identifier", "xs"), ("Block", []))],
        )

    def test_missing_in_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for x [1, 2, 3] { }")

    def test_missing_loop_variable_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for in [1, 2, 3] { }")

    def test_non_block_body_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for x in [1, 2, 3] print(x);")

    def test_return_inside_top_level_for_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for x in [1] { return 5; }")


class TestBreakContinue(unittest.TestCase):
    def test_break_and_continue_inside_while_body(self):
        # WhileStmt has no `stmt_shape` case (not needed elsewhere in this
        # suite); shape its body directly instead of the statement itself.
        stmts = parse_stmts("while (true) { break; continue; }")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(
            stmt_shape(stmts[0].body),
            ("Block", [("BreakStmt",), ("ContinueStmt",)]),
        )

    def test_break_and_continue_inside_for_body(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("for x in [1] { break; continue; }")
            ],
            [
                (
                    "ForStmt",
                    "x",
                    ("ListLiteral", [("Literal", 1)]),
                    ("Block", [("BreakStmt",), ("ContinueStmt",)]),
                )
            ],
        )

    def test_break_outside_loop_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("break;")

    def test_continue_outside_loop_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("continue;")

    def test_break_inside_if_outside_loop_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("if (true) { break; }")

    def test_break_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { break }")

    def test_continue_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { continue }")

    def test_break_inside_function_nested_in_loop_without_own_loop_raises(self):
        # A function body resets loop-nesting the same way it resets return's
        # function-nesting: break/continue must refer to a loop inside the
        # nearest enclosing function, not one merely lexically outside it.
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { fn f() { break; } }")

    def test_break_inside_function_with_own_loop_is_valid(self):
        stmts = parse_stmts("while (true) { fn f() { while (true) { break; } } }")
        self.assertEqual(len(stmts), 1)


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


class TestTryCatch(unittest.TestCase):
    def test_try_catch_shape(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("try { let x = 1; } catch (e) { print(e); }")
            ],
            [
                (
                    "TryStmt",
                    ("Block", [("LetStmt", "x", ("Literal", 1))]),
                    "e",
                    (
                        "Block",
                        [
                            (
                                "ExprStmt",
                                ("Call", ("Identifier", "print"), [("Identifier", "e")]),
                            )
                        ],
                    ),
                )
            ],
        )

    def test_try_catch_empty_bodies(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("try {} catch (e) {}")],
            [("TryStmt", ("Block", []), "e", ("Block", []))],
        )

    def test_missing_catch_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("try { 1; }")

    def test_bare_catch_without_name_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("try { 1; } catch { }")

    def test_try_body_must_be_block(self):
        with self.assertRaises(ParseError):
            parse_stmts("try 1; catch (e) { }")

    def test_catch_body_must_be_block(self):
        with self.assertRaises(ParseError):
            parse_stmts("try { } catch (e) 1;")

    def test_missing_catch_parens_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("try { } catch e { }")

    def test_break_inside_try_inside_loop_is_valid(self):
        stmts = parse_stmts("while (true) { try { break; } catch (e) {} }")
        self.assertEqual(len(stmts), 1)


class TestSwitchStatement(unittest.TestCase):
    def test_switch_shape(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts(
                    "switch (x) { case 1: { let a = 1; } "
                    "case 2: { let a = 2; } default: { let a = 3; } }"
                )
            ],
            [
                (
                    "SwitchStmt",
                    ("Identifier", "x"),
                    [
                        (
                            ("Literal", 1),
                            ("Block", [("LetStmt", "a", ("Literal", 1))]),
                        ),
                        (
                            ("Literal", 2),
                            ("Block", [("LetStmt", "a", ("Literal", 2))]),
                        ),
                    ],
                    ("Block", [("LetStmt", "a", ("Literal", 3))]),
                )
            ],
        )

    def test_switch_without_default(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("switch (x) { case 1: { } }")
            ],
            [("SwitchStmt", ("Identifier", "x"), [(("Literal", 1), ("Block", []))], None)],
        )

    def test_switch_empty_body(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("switch (x) { }")],
            [("SwitchStmt", ("Identifier", "x"), [], None)],
        )

    def test_switch_without_paren_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch x { case 1: { } }")

    def test_case_missing_colon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch (x) { case 1 { } }")

    def test_case_missing_block_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch (x) { case 1: print(1); }")

    def test_default_missing_colon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch (x) { default { } }")

    def test_default_missing_block_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch (x) { default: print(1); }")

    def test_duplicate_default_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("switch (x) { default: { } default: { } }")

    def test_break_inside_switch_inside_loop_is_valid(self):
        stmts = parse_stmts("while (true) { switch (1) { case 1: { break; } } }")
        self.assertEqual(len(stmts), 1)


if __name__ == "__main__":
    unittest.main()
