"""Tests for cinder.parser: expression precedence, grouping, calls, errors."""

import unittest

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    BreakStmt,
    Call,
    ConstStmt,
    ContinueStmt,
    DestructureAssign,
    DestructureLetStmt,
    DoWhileStmt,
    ExprStmt,
    FnDecl,
    FnExpr,
    ForCStmt,
    ForStmt,
    Grouping,
    Identifier,
    Index,
    IndexAssign,
    IndexCompoundAssign,
    IndexNilCoalesceAssign,
    InterpString,
    LetStmt,
    ListComprehension,
    ListLiteral,
    Literal,
    Logical,
    MapComprehension,
    MapLiteral,
    OptionalIndex,
    ReturnStmt,
    SliceExpr,
    Spread,
    SwitchStmt,
    Ternary,
    ThrowStmt,
    TryStmt,
    Unary,
    WhileStmt,
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
    if isinstance(node, ListComprehension):
        return (
            "ListComprehension",
            shape(node.element),
            node.var_name,
            shape(node.iterable),
            shape(node.condition) if node.condition is not None else None,
        )
    if isinstance(node, MapLiteral):
        return (
            "MapLiteral",
            [
                shape(entry)
                if isinstance(entry, Spread)
                else (shape(entry[0]), shape(entry[1]))
                for entry in node.pairs
            ],
        )
    if isinstance(node, MapComprehension):
        return (
            "MapComprehension",
            shape(node.key),
            shape(node.value),
            node.var_name,
            shape(node.iterable),
            shape(node.condition) if node.condition is not None else None,
        )
    if isinstance(node, Index):
        return ("Index", shape(node.obj), shape(node.index))
    if isinstance(node, OptionalIndex):
        return ("OptionalIndex", shape(node.obj), shape(node.index))
    if isinstance(node, SliceExpr):
        return (
            "SliceExpr",
            shape(node.obj),
            shape(node.start) if node.start is not None else None,
            shape(node.end) if node.end is not None else None,
            shape(node.step) if node.step is not None else None,
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
    if isinstance(node, IndexNilCoalesceAssign):
        return (
            "IndexNilCoalesceAssign",
            shape(node.obj),
            shape(node.index),
            shape(node.value),
        )
    if isinstance(node, Assign):
        return ("Assign", node.name, shape(node.value))
    if isinstance(node, DestructureAssign):
        return ("DestructureAssign", node.names, node.rest, shape(node.value), node.is_map)
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
    """Structural view of an `FnDecl`/`FnExpr` params list. A plain
    identifier parameter renders as `(name, default_shape)`, same as before
    `Param` existed; a destructuring parameter renders as
    `("Param", names, rest, is_map)`."""
    return [param_shape(param) for param in params]


def param_shape(param):
    if param.names is not None:
        return ("Param", param.names, param.rest, param.is_map)
    return (param.name, shape(param.default) if param.default is not None else None)


def parse(source: str):
    return parse_expression(tokenize(source))


def parse_stmts(source: str):
    return parse_program(tokenize(source))


def stmt_shape(node):
    """Structural view of a statement AST node, ignoring line/column noise."""
    if isinstance(node, LetStmt):
        return ("LetStmt", node.name, shape(node.initializer))
    if isinstance(node, ConstStmt):
        return ("ConstStmt", node.name, shape(node.initializer))
    if isinstance(node, DestructureLetStmt):
        return ("DestructureLetStmt", node.names, shape(node.initializer), node.is_map, node.rest)
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
    if isinstance(node, ThrowStmt):
        return ("ThrowStmt", shape(node.expression))
    if isinstance(node, ForStmt):
        return (
            "ForStmt",
            node.var_name,
            shape(node.iterable),
            stmt_shape(node.body),
        )
    if isinstance(node, ForCStmt):
        return (
            "ForCStmt",
            stmt_shape(node.init) if node.init is not None else None,
            shape(node.condition) if node.condition is not None else None,
            stmt_shape(node.step) if node.step is not None else None,
            stmt_shape(node.body),
        )
    if isinstance(node, DoWhileStmt):
        return ("DoWhileStmt", shape(node.condition), stmt_shape(node.body))
    if isinstance(node, BreakStmt):
        return ("BreakStmt",)
    if isinstance(node, ContinueStmt):
        return ("ContinueStmt",)
    if isinstance(node, TryStmt):
        return (
            "TryStmt",
            stmt_shape(node.try_block),
            node.catch_name,
            stmt_shape(node.catch_block) if node.catch_block is not None else None,
            stmt_shape(node.finally_block) if node.finally_block is not None else None,
        )
    if isinstance(node, SwitchStmt):
        return (
            "SwitchStmt",
            shape(node.scrutinee),
            [
                ([shape(v) for v in case.values], stmt_shape(case.body))
                for case in node.cases
            ],
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

    def test_exponent_binds_tighter_than_multiplication(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("2 * 3 ** 2")),
            (
                "Binary",
                ("Literal", 2),
                TokenType.STAR,
                ("Binary", ("Literal", 3), TokenType.STARSTAR, ("Literal", 2)),
            ),
        )

    def test_exponent_is_right_associative(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("2 ** 3 ** 2")),
            (
                "Binary",
                ("Literal", 2),
                TokenType.STARSTAR,
                ("Binary", ("Literal", 3), TokenType.STARSTAR, ("Literal", 2)),
            ),
        )

    def test_unary_minus_binds_tighter_than_exponent(self):
        # `-2 ** 2` parses as `(-2) ** 2`, not Python's `-(2 ** 2)`.
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("-2 ** 2")),
            (
                "Binary",
                ("Unary", TokenType.MINUS, ("Literal", 2)),
                TokenType.STARSTAR,
                ("Literal", 2),
            ),
        )

    def test_floor_div_left_associative_same_tier_as_mul_div_mod(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("8 // 2 * 2")),
            (
                "Binary",
                ("Binary", ("Literal", 8), TokenType.SLASHSLASH, ("Literal", 2)),
                TokenType.STAR,
                ("Literal", 2),
            ),
        )

    def test_exponent_binds_tighter_than_floor_division(self):
        from cinder.tokens import TokenType

        self.assertEqual(
            shape(parse("2 ** 3 // 2")),
            (
                "Binary",
                ("Binary", ("Literal", 2), TokenType.STARSTAR, ("Literal", 3)),
                TokenType.SLASHSLASH,
                ("Literal", 2),
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

    def test_not_in_is_binary_op(self):
        self.assertEqual(
            shape(parse("2 not in [1, 2, 3]")),
            (
                "Binary",
                ("Literal", 2),
                TokenType.NOT_IN,
                ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
            ),
        )

    def test_not_in_binds_tighter_than_and(self):
        self.assertEqual(
            shape(parse("1 not in [1] and 2 not in [2]")),
            (
                "Logical",
                ("Binary", ("Literal", 1), TokenType.NOT_IN, ("ListLiteral", [("Literal", 1)])),
                TokenType.AND,
                ("Binary", ("Literal", 2), TokenType.NOT_IN, ("ListLiteral", [("Literal", 2)])),
            ),
        )

    def test_comparison_binds_tighter_than_not_in(self):
        self.assertEqual(
            shape(parse("1 < 2 not in [true]")),
            (
                "Binary",
                ("Binary", ("Literal", 1), TokenType.LT, ("Literal", 2)),
                TokenType.NOT_IN,
                ("ListLiteral", [("Literal", True)]),
            ),
        )

    def test_not_followed_by_non_in_is_unary(self):
        # `not x in y` (no adjacent `in` right after `not`) stays unary `not`
        # applied first, i.e. `(not x) in y` — unchanged existing behavior.
        self.assertEqual(
            shape(parse("not x in y")),
            (
                "Binary",
                ("Unary", TokenType.NOT, ("Identifier", "x")),
                TokenType.IN,
                ("Identifier", "y"),
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

    def test_list_comprehension(self):
        self.assertEqual(
            shape(parse("[x * 2 for x in xs]")),
            (
                "ListComprehension",
                ("Binary", ("Identifier", "x"), TokenType.STAR, ("Literal", 2)),
                "x",
                ("Identifier", "xs"),
                None,
            ),
        )

    def test_list_comprehension_with_filter(self):
        self.assertEqual(
            shape(parse("[x for x in xs if x > 0]")),
            (
                "ListComprehension",
                ("Identifier", "x"),
                "x",
                ("Identifier", "xs"),
                ("Binary", ("Identifier", "x"), TokenType.GT, ("Literal", 0)),
            ),
        )

    def test_list_comprehension_spread_head_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse("[...[1, 2] for x in [1, 2]]")

    def test_list_comprehension_destructure_two_names(self):
        node = parse("[k for [k, v] in items(m)]")
        self.assertIsInstance(node, ListComprehension)
        self.assertIsNone(node.var_name)
        self.assertEqual(node.names, ["k", "v"])
        self.assertIsNone(node.rest)

    def test_list_comprehension_destructure_single_name(self):
        node = parse("[a for [a] in xs]")
        self.assertEqual(node.names, ["a"])
        self.assertIsNone(node.rest)

    def test_list_comprehension_destructure_with_rest(self):
        node = parse("[a for [a, ...rest] in xs]")
        self.assertEqual(node.names, ["a"])
        self.assertEqual(node.rest, "rest")

    def test_list_comprehension_destructure_with_filter(self):
        node = parse("[a for [a, b] in xs if a > 1]")
        self.assertEqual(node.names, ["a", "b"])
        self.assertEqual(
            shape(node.condition),
            ("Binary", ("Identifier", "a"), TokenType.GT, ("Literal", 1)),
        )

    def test_list_comprehension_destructure_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse("[x for [1, b] in xs]")

    def test_plain_list_literal_still_parses_after_comprehension_added(self):
        self.assertEqual(
            shape(parse("[1, 2, 3]")),
            ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
        )

    def test_map_literal_with_spread(self):
        self.assertEqual(
            shape(parse('{...m, "b": 2}')),
            (
                "MapLiteral",
                [
                    ("Spread", ("Identifier", "m")),
                    (("Literal", "b"), ("Literal", 2)),
                ],
            ),
        )

    def test_map_literal_multiple_spreads(self):
        self.assertEqual(
            shape(parse('{"x": 0, ...m1, "y": 2, ...m2}')),
            (
                "MapLiteral",
                [
                    (("Literal", "x"), ("Literal", 0)),
                    ("Spread", ("Identifier", "m1")),
                    (("Literal", "y"), ("Literal", 2)),
                    ("Spread", ("Identifier", "m2")),
                ],
            ),
        )

    def test_bare_spread_map_literal(self):
        self.assertEqual(
            shape(parse("{...m}")),
            ("MapLiteral", [("Spread", ("Identifier", "m"))]),
        )

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

    def test_map_comprehension(self):
        self.assertEqual(
            shape(parse("{x: x * x for x in xs}")),
            (
                "MapComprehension",
                ("Identifier", "x"),
                ("Binary", ("Identifier", "x"), TokenType.STAR, ("Identifier", "x")),
                "x",
                ("Identifier", "xs"),
                None,
            ),
        )

    def test_map_comprehension_with_filter(self):
        self.assertEqual(
            shape(parse("{x: x for x in xs if x > 0}")),
            (
                "MapComprehension",
                ("Identifier", "x"),
                ("Identifier", "x"),
                "x",
                ("Identifier", "xs"),
                ("Binary", ("Identifier", "x"), TokenType.GT, ("Literal", 0)),
            ),
        )

    def test_map_comprehension_spread_head_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse("{...m for x in [1, 2]}")

    def test_map_comprehension_destructure_two_names(self):
        node = parse("{k: v for [k, v] in items(m)}")
        self.assertIsInstance(node, MapComprehension)
        self.assertIsNone(node.var_name)
        self.assertEqual(node.names, ["k", "v"])
        self.assertIsNone(node.rest)

    def test_map_comprehension_destructure_with_rest(self):
        node = parse("{a: rest for [a, ...rest] in xs}")
        self.assertEqual(node.names, ["a"])
        self.assertEqual(node.rest, "rest")

    def test_map_comprehension_destructure_with_filter(self):
        node = parse("{k: v for [k, v] in items(m) if v > 0}")
        self.assertEqual(node.names, ["k", "v"])
        self.assertEqual(
            shape(node.condition),
            ("Binary", ("Identifier", "v"), TokenType.GT, ("Literal", 0)),
        )

    def test_map_comprehension_destructure_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse("{x: x for [1, b] in xs}")

    def test_plain_map_literal_still_parses_after_comprehension_added(self):
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

    def test_list_destructure_assignment(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("[a, b] = [b, a];")],
            [
                (
                    "ExprStmt",
                    (
                        "DestructureAssign",
                        ["a", "b"],
                        None,
                        ("ListLiteral", [("Identifier", "b"), ("Identifier", "a")]),
                        False,
                    ),
                )
            ],
        )

    def test_list_destructure_assignment_with_rest(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("[a, b, ...rest] = [1, 2, 3, 4];")],
            [
                (
                    "ExprStmt",
                    (
                        "DestructureAssign",
                        ["a", "b"],
                        "rest",
                        (
                            "ListLiteral",
                            [
                                ("Literal", 1),
                                ("Literal", 2),
                                ("Literal", 3),
                                ("Literal", 4),
                            ],
                        ),
                        False,
                    ),
                )
            ],
        )

    def test_list_destructure_assignment_literal_element_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[1, 2] = [3, 4];")

    def test_list_destructure_assignment_nested_pattern_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[[a, b], c] = [[1, 2], 3];")

    def test_list_destructure_assignment_rest_not_last_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[a, ...rest, b] = [1, 2, 3];")

    def test_list_destructure_assignment_empty_pattern_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[] = [1];")

    def test_list_destructure_compound_assign_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[a, b] += [1, 2];")

    def test_list_destructure_qq_assign_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("[a, b] ??= [1, 2];")

    def test_map_destructure_assignment(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{a, b} = {"a": 1, "b": 2};')],
            [
                (
                    "ExprStmt",
                    (
                        "DestructureAssign",
                        ["a", "b"],
                        None,
                        (
                            "MapLiteral",
                            [
                                (("Literal", "a"), ("Literal", 1)),
                                (("Literal", "b"), ("Literal", 2)),
                            ],
                        ),
                        True,
                    ),
                )
            ],
        )

    def test_map_destructure_assignment_single_name(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{a} = {"a": 1};')],
            [
                (
                    "ExprStmt",
                    (
                        "DestructureAssign",
                        ["a"],
                        None,
                        ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]),
                        True,
                    ),
                )
            ],
        )

    def test_map_destructure_assignment_literal_pattern_element_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("{1, 2} = {};")

    def test_map_literal_statement_unaffected(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('{"a": 1};')],
            [("ExprStmt", ("MapLiteral", [(("Literal", "a"), ("Literal", 1))]))],
        )

    def test_empty_braces_still_empty_block(self):
        self.assertEqual([stmt_shape(s) for s in parse_stmts("{}")], [("Block", [])])

    def test_let_map_destructure_unaffected_by_assign_form(self):
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
                    None,
                )
            ],
        )

    def test_dot_access_desugars_to_index(self):
        self.assertEqual(
            shape(parse("m.a")),
            ("Index", ("Identifier", "m"), ("Literal", "a")),
        )

    def test_chained_dot_access(self):
        self.assertEqual(
            shape(parse("m.nested.b")),
            (
                "Index",
                ("Index", ("Identifier", "m"), ("Literal", "nested")),
                ("Literal", "b"),
            ),
        )

    def test_dot_access_assignment(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("m.a = 5;")],
            [
                (
                    "ExprStmt",
                    ("IndexAssign", ("Identifier", "m"), ("Literal", "a"), ("Literal", 5)),
                )
            ],
        )

    def test_dot_access_after_keyword_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse("m.if")

    def test_dot_access_missing_identifier_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse("m.")

    def test_optional_dot_access_desugars_to_optional_index(self):
        self.assertEqual(
            shape(parse("m?.a")),
            ("OptionalIndex", ("Identifier", "m"), ("Literal", "a")),
        )

    def test_optional_dot_access_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("m?.a = 5;")

    def test_optional_dot_access_compound_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("m?.a += 1;")

    def test_optional_bracket_access_desugars_to_optional_index(self):
        self.assertEqual(
            shape(parse('m?.["a"]')),
            ("OptionalIndex", ("Identifier", "m"), ("Literal", "a")),
        )

    def test_optional_bracket_access_accepts_arbitrary_expression(self):
        self.assertEqual(
            shape(parse("m?.[key]")),
            ("OptionalIndex", ("Identifier", "m"), ("Identifier", "key")),
        )

    def test_optional_bracket_access_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts('m?.["a"] = 5;')

    def test_optional_bracket_access_slice_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse('m?.[0:1]')

    def test_map_literal_missing_colon_raises(self):
        with self.assertRaises(ParseError):
            parse('{"a" 1}')

    def test_unclosed_list_literal_raises(self):
        with self.assertRaises(ParseError):
            parse("[1, 2")

    def test_slice_both_bounds(self):
        self.assertEqual(
            shape(parse("xs[1:3]")),
            (
                "SliceExpr",
                ("Identifier", "xs"),
                ("Literal", 1),
                ("Literal", 3),
                None,
            ),
        )

    def test_slice_missing_start(self):
        self.assertEqual(
            shape(parse("xs[:3]")),
            ("SliceExpr", ("Identifier", "xs"), None, ("Literal", 3), None),
        )

    def test_slice_missing_end(self):
        self.assertEqual(
            shape(parse("xs[1:]")),
            ("SliceExpr", ("Identifier", "xs"), ("Literal", 1), None, None),
        )

    def test_slice_both_missing(self):
        self.assertEqual(
            shape(parse("xs[:]")),
            ("SliceExpr", ("Identifier", "xs"), None, None, None),
        )

    def test_slice_step_only(self):
        self.assertEqual(
            shape(parse("xs[::2]")),
            ("SliceExpr", ("Identifier", "xs"), None, None, ("Literal", 2)),
        )

    def test_slice_start_and_step(self):
        self.assertEqual(
            shape(parse("xs[1::2]")),
            (
                "SliceExpr",
                ("Identifier", "xs"),
                ("Literal", 1),
                None,
                ("Literal", 2),
            ),
        )

    def test_slice_end_and_step(self):
        self.assertEqual(
            shape(parse("xs[:5:2]")),
            (
                "SliceExpr",
                ("Identifier", "xs"),
                None,
                ("Literal", 5),
                ("Literal", 2),
            ),
        )

    def test_slice_all_three(self):
        self.assertEqual(
            shape(parse("xs[1:4:2]")),
            (
                "SliceExpr",
                ("Identifier", "xs"),
                ("Literal", 1),
                ("Literal", 4),
                ("Literal", 2),
            ),
        )

    def test_slice_negative_step_reverses(self):
        self.assertEqual(
            shape(parse("xs[::-1]")),
            (
                "SliceExpr",
                ("Identifier", "xs"),
                None,
                None,
                ("Unary", TokenType.MINUS, ("Literal", 1)),
            ),
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

    def test_starstar_eq_desugars_to_binary_starstar(self):
        self.assertEqual(
            shape(parse("x **= 2")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.STARSTAR, ("Literal", 2))),
        )

    def test_starstar_eq_allows_index_target(self):
        stmts = parse_stmts("xs[0] **= 3;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.STARSTAR,
                    ("Literal", 3),
                ),
            ),
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

    def test_slashslash_eq_desugars_to_binary_slashslash(self):
        self.assertEqual(
            shape(parse("x //= 2")),
            ("Assign", "x", ("Binary", ("Identifier", "x"), TokenType.SLASHSLASH, ("Literal", 2))),
        )

    def test_slashslash_eq_allows_index_target(self):
        stmts = parse_stmts("xs[0] //= 3;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.SLASHSLASH,
                    ("Literal", 3),
                ),
            ),
        )

    def test_plus_eq_allows_index_target(self):
        # The arithmetic set now accepts an index-expression target too,
        # desugaring into IndexCompoundAssign (not IndexAssign wrapping a
        # Binary over the same Index node, which would evaluate obj/index
        # twice at runtime) — same treatment the bitwise/shift set already
        # has.
        stmts = parse_stmts("xs[0] += 1;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.PLUS,
                    ("Literal", 1),
                ),
            ),
        )

    def test_invalid_arithmetic_compound_assign_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("1 + 1 += 1;")

    def test_qq_eq_desugars_to_assign_of_logical_question_question(self):
        # Unlike the arithmetic compound-assign ops, `??=` desugars into a
        # Logical node (not Binary) so the right-hand side short-circuits
        # exactly like plain `??`, rather than evaluating eagerly.
        self.assertEqual(
            shape(parse("x ??= 1")),
            (
                "Assign",
                "x",
                ("Logical", ("Identifier", "x"), TokenType.QUESTION_QUESTION, ("Literal", 1)),
            ),
        )

    def test_qq_eq_allows_index_target(self):
        # Unlike plain identifiers (desugared via Logical/Assign above),
        # an Index target desugars into a dedicated IndexNilCoalesceAssign
        # node so obj/index are each evaluated exactly once and the RHS
        # short-circuits, mirroring how the bitwise/shift set desugars into
        # IndexCompoundAssign for an Index target.
        stmts = parse_stmts("xs[0] ??= 1;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexNilCoalesceAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    ("Literal", 1),
                ),
            ),
        )

    def test_qq_eq_invalid_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("1 + 1 ??= 1;")

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


class TestIncrementDecrement(unittest.TestCase):
    def test_plus_plus_desugars_to_assign_of_binary_plus_one(self):
        stmts = parse_stmts("a++;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                ("Assign", "a", ("Binary", ("Identifier", "a"), TokenType.PLUS, ("Literal", 1))),
            ),
        )

    def test_minus_minus_desugars_to_assign_of_binary_minus_one(self):
        stmts = parse_stmts("a--;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                ("Assign", "a", ("Binary", ("Identifier", "a"), TokenType.MINUS, ("Literal", 1))),
            ),
        )

    def test_plus_plus_allows_index_target(self):
        # Like the bitwise compound-assign ops, ++/-- accept an index target,
        # desugaring into IndexCompoundAssign so obj/index are each evaluated
        # once rather than twice.
        stmts = parse_stmts("xs[0]++;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.PLUS,
                    ("Literal", 1),
                ),
            ),
        )

    def test_minus_minus_allows_index_target(self):
        stmts = parse_stmts("xs[0]--;")
        self.assertEqual(
            stmt_shape(stmts[0]),
            (
                "ExprStmt",
                (
                    "IndexCompoundAssign",
                    ("Identifier", "xs"),
                    ("Literal", 0),
                    TokenType.MINUS,
                    ("Literal", 1),
                ),
            ),
        )

    def test_non_lvalue_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_stmts("5++;")
        with self.assertRaises(ParseError):
            parse_stmts("(1 + 2)--;")

    def test_used_as_value_is_unparseable(self):
        # `++`/`--` is statement-only sugar, not an expression: using it as a
        # value is rejected (whether by an explicit lvalue check or simply
        # because the grammar never reaches it inside an expression).
        with self.assertRaises(ParseError):
            parse_stmts("let b = a++;")

    def test_plus_and_minus_and_compound_assign_unaffected(self):
        # Regression: plain `+`/`-` and `+=`/`-=` still parse exactly as
        # before the doubled-character lookahead was added.
        self.assertEqual(
            shape(parse("1 + 2")),
            ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2)),
        )
        self.assertEqual(
            shape(parse("a += 1")),
            ("Assign", "a", ("Binary", ("Identifier", "a"), TokenType.PLUS, ("Literal", 1))),
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

    def test_const_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("const x = 1 + 2;")],
            [("ConstStmt", "x", ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2)))],
        )

    def test_const_missing_initializer_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("const x;")

    def test_const_missing_equals_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("const x 1;")

    def test_const_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("const x = 1")

    def test_destructure_let_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [a, b] = [1, 2];")],
            [
                (
                    "DestructureLetStmt",
                    ["a", "b"],
                    ("ListLiteral", [("Literal", 1), ("Literal", 2)]),
                    False,
                    None,
                )
            ],
        )

    def test_destructure_let_statement_single_name(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [a] = [1];")],
            [("DestructureLetStmt", ["a"], ("ListLiteral", [("Literal", 1)]), False, None)],
        )

    def test_destructure_let_list_rest(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [a, b, ...rest] = [1, 2, 3, 4];")],
            [
                (
                    "DestructureLetStmt",
                    ["a", "b"],
                    (
                        "ListLiteral",
                        [("Literal", 1), ("Literal", 2), ("Literal", 3), ("Literal", 4)],
                    ),
                    False,
                    "rest",
                )
            ],
        )

    def test_destructure_let_list_rest_only(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("let [...rest] = [1, 2, 3];")],
            [
                (
                    "DestructureLetStmt",
                    [],
                    ("ListLiteral", [("Literal", 1), ("Literal", 2), ("Literal", 3)]),
                    False,
                    "rest",
                )
            ],
        )

    def test_destructure_let_list_rest_not_last_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [a, ...rest, b] = [1, 2, 3];")

    def test_destructure_let_list_rest_missing_name_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("let [a, ...] = [1, 2];")

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
                    None,
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
                    None,
                )
            ],
        )

    def test_destructure_let_map_rest_token_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('let {...rest} = {"a": 1};')

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

    def test_throw_statement(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts('throw "boom";')],
            [("ThrowStmt", ("Literal", "boom"))],
        )

    def test_throw_without_expression_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("throw;")

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

    def test_fn_declaration_with_list_destructuring_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn dist([x, y]) { return x; }")],
            [
                (
                    "FnDecl",
                    "dist",
                    [("Param", ["x", "y"], None, False)],
                    None,
                    ("Block", [("ReturnStmt", ("Identifier", "x"))]),
                )
            ],
        )

    def test_fn_declaration_with_map_destructuring_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn describe({name, age}) { return name; }")],
            [
                (
                    "FnDecl",
                    "describe",
                    [("Param", ["name", "age"], None, True)],
                    None,
                    ("Block", [("ReturnStmt", ("Identifier", "name"))]),
                )
            ],
        )

    def test_fn_declaration_with_list_destructuring_param_and_rest_element(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f([a, ...rest]) { return rest; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [("Param", ["a"], "rest", False)],
                    None,
                    ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
                )
            ],
        )

    def test_fn_declaration_with_destructuring_param_and_trailing_rest_param(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("fn f([a, b], ...more) { return more; }")],
            [
                (
                    "FnDecl",
                    "f",
                    [("Param", ["a", "b"], None, False)],
                    "more",
                    ("Block", [("ReturnStmt", ("Identifier", "more"))]),
                )
            ],
        )

    def test_fn_expression_with_list_destructuring_param(self):
        self.assertEqual(
            shape(parse("fn([a, b]) { return a; }")),
            (
                "FnExpr",
                [("Param", ["a", "b"], None, False)],
                None,
                ("Block", [("ReturnStmt", ("Identifier", "a"))]),
            ),
        )

    def test_arrow_function_with_list_destructuring_param(self):
        self.assertEqual(
            shape(parse("([a, b]) => a + b")),
            (
                "FnExpr",
                [("Param", ["a", "b"], None, False)],
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

    def test_list_destructuring_param_with_default_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("fn f([a, b] = [1, 2]) { return a; }")

    def test_map_destructuring_param_with_default_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts('fn f({a, b} = {"a": 1, "b": 2}) { return a; }')

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


class TestArrowFunctions(unittest.TestCase):
    def test_arrow_no_params(self):
        self.assertEqual(
            shape(parse("() => 42")),
            ("FnExpr", [], None, ("Block", [("ReturnStmt", ("Literal", 42))])),
        )

    def test_arrow_one_param(self):
        self.assertEqual(
            shape(parse("(x) => x * 2")),
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

    def test_arrow_two_params(self):
        self.assertEqual(
            shape(parse("(a, b) => a + b")),
            (
                "FnExpr",
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
            ),
        )

    def test_arrow_with_default_param(self):
        self.assertEqual(
            shape(parse("(x, y = 10) => x + y")),
            (
                "FnExpr",
                [("x", None), ("y", ("Literal", 10))],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            ("Binary", ("Identifier", "x"), TokenType.PLUS, ("Identifier", "y")),
                        )
                    ],
                ),
            ),
        )

    def test_arrow_with_rest_param(self):
        self.assertEqual(
            shape(parse("(a, ...rest) => rest")),
            (
                "FnExpr",
                [("a", None)],
                "rest",
                ("Block", [("ReturnStmt", ("Identifier", "rest"))]),
            ),
        )

    def test_arrow_body_is_ternary(self):
        self.assertEqual(
            shape(parse('(x) => x > 0 ? "pos" : "neg"')),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            (
                                "Ternary",
                                ("Binary", ("Identifier", "x"), TokenType.GT, ("Literal", 0)),
                                ("Literal", "pos"),
                                ("Literal", "neg"),
                            ),
                        )
                    ],
                ),
            ),
        )

    def test_arrow_as_call_argument(self):
        self.assertEqual(
            shape(parse("map([1], (x) => x)")),
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

    def test_arrow_nests_and_closes_over_outer_param(self):
        self.assertEqual(
            shape(parse("(n) => (x) => x + n")),
            (
                "FnExpr",
                [("n", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            (
                                "FnExpr",
                                [("x", None)],
                                None,
                                (
                                    "Block",
                                    [
                                        (
                                            "ReturnStmt",
                                            (
                                                "Binary",
                                                ("Identifier", "x"),
                                                TokenType.PLUS,
                                                ("Identifier", "n"),
                                            ),
                                        )
                                    ],
                                ),
                            ),
                        )
                    ],
                ),
            ),
        )

    def test_ordinary_grouping_still_works(self):
        self.assertEqual(
            shape(parse("(1 + 2) * 3")),
            (
                "Binary",
                ("Grouping", ("Binary", ("Literal", 1), TokenType.PLUS, ("Literal", 2))),
                TokenType.STAR,
                ("Literal", 3),
            ),
        )

    def test_bare_identifier_in_parens_without_arrow_is_grouping(self):
        # One parameter-shaped token inside the parens but no `=>` after the
        # `)` — the speculative arrow-parse must fail and hand control back
        # to plain grouping, not error.
        self.assertEqual(shape(parse("(x)")), ("Grouping", ("Identifier", "x")))

    def test_malformed_arrow_param_list_raises(self):
        # Trailing comma with no parameter after it: falls back to the
        # grouping-expression path (per `_try_arrow_function`'s unconditional
        # backtrack), which itself fails to find a `)` immediately after the
        # bare `x` — this documents whichever error actually surfaces rather
        # than asserting the `fn`-side parameter error in advance.
        with self.assertRaises(ParseError) as ctx:
            parse_stmts("let result = (x, ) => x;")
        self.assertIn("')'", str(ctx.exception))

    def test_arrow_block_body_parses(self):
        self.assertEqual(
            shape(parse("(x) => { let y = x * 2; return y; }")),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "LetStmt",
                            "y",
                            ("Binary", ("Identifier", "x"), TokenType.STAR, ("Literal", 2)),
                        ),
                        ("ReturnStmt", ("Identifier", "y")),
                    ],
                ),
            ),
        )

    def test_arrow_block_body_no_implicit_return(self):
        # A block body does not implicitly return its last expression — it
        # parses as a plain `ExprStmt`, not wrapped in a synthetic `ReturnStmt`.
        self.assertEqual(
            shape(parse("(x) => { x * 2; }")),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ExprStmt",
                            ("Binary", ("Identifier", "x"), TokenType.STAR, ("Literal", 2)),
                        )
                    ],
                ),
            ),
        )

    def test_arrow_block_body_break_without_own_loop_raises(self):
        # A block-bodied arrow resets loop-nesting the same way an ordinary
        # `fn` body does — `break` inside it must refer to a loop inside the
        # arrow's own body, not one merely lexically outside it.
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { let f = () => { break; }; }")

    def test_arrow_block_body_break_with_own_loop_is_valid(self):
        stmts = parse_stmts("while (true) { let f = () => { while (true) { break; } }; }")
        self.assertEqual(len(stmts), 1)

    def test_bare_identifier_arrow_one_param(self):
        self.assertEqual(
            shape(parse("x => x * 2")),
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

    def test_bare_identifier_arrow_body_is_ternary(self):
        self.assertEqual(
            shape(parse('x => x > 0 ? "pos" : "neg"')),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            (
                                "Ternary",
                                ("Binary", ("Identifier", "x"), TokenType.GT, ("Literal", 0)),
                                ("Literal", "pos"),
                                ("Literal", "neg"),
                            ),
                        )
                    ],
                ),
            ),
        )

    def test_bare_identifier_arrow_nests_and_closes_over_outer_param(self):
        self.assertEqual(
            shape(parse("x => (y => x + y)")),
            (
                "FnExpr",
                [("x", None)],
                None,
                (
                    "Block",
                    [
                        (
                            "ReturnStmt",
                            (
                                "Grouping",
                                (
                                    "FnExpr",
                                    [("y", None)],
                                    None,
                                    (
                                        "Block",
                                        [
                                            (
                                                "ReturnStmt",
                                                (
                                                    "Binary",
                                                    ("Identifier", "x"),
                                                    TokenType.PLUS,
                                                    ("Identifier", "y"),
                                                ),
                                            )
                                        ],
                                    ),
                                ),
                            ),
                        )
                    ],
                ),
            ),
        )

    def test_bare_identifier_without_arrow_is_plain_identifier(self):
        self.assertEqual(shape(parse("x")), ("Identifier", "x"))

    def test_bare_identifier_arrow_block_body_parses(self):
        self.assertEqual(
            shape(parse("x => { return x; }")),
            (
                "FnExpr",
                [("x", None)],
                None,
                ("Block", [("ReturnStmt", ("Identifier", "x"))]),
            ),
        )


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


class TestForDestructuring(unittest.TestCase):
    def test_for_list_destructure_two_names(self):
        stmt = parse_stmts("for [k, v] in items(m) { }")[0]
        self.assertIsInstance(stmt, ForStmt)
        self.assertIsNone(stmt.var_name)
        self.assertEqual(stmt.names, ["k", "v"])
        self.assertIsNone(stmt.rest)
        self.assertEqual(
            shape(stmt.iterable),
            ("Call", ("Identifier", "items"), [("Identifier", "m")]),
        )

    def test_for_list_destructure_single_name(self):
        stmt = parse_stmts("for [a] in xs { }")[0]
        self.assertEqual(stmt.names, ["a"])
        self.assertIsNone(stmt.rest)

    def test_for_list_destructure_with_rest(self):
        stmt = parse_stmts("for [first, ...rest] in xs { }")[0]
        self.assertEqual(stmt.names, ["first"])
        self.assertEqual(stmt.rest, "rest")

    def test_for_list_destructure_rest_not_last_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for [a, ...rest, b] in xs { }")

    def test_for_list_destructure_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for [1, b] in xs { }")

    def test_for_list_destructure_unclosed_bracket_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for [a, b in xs { }")

    def test_for_list_destructure_missing_in_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for [a, b] xs { }")

    def test_for_list_destructure_carries_its_label(self):
        stmt = parse_stmts("outer: for [k, v] in items(m) { break outer; }")[0]
        self.assertEqual(stmt.label, "outer")
        self.assertEqual(stmt.names, ["k", "v"])

    def test_for_list_destructure_body_parses(self):
        self.assertEqual(
            stmt_shape(parse_stmts("for [k, v] in xs { print(k); }")[0].body),
            ("Block", [("ExprStmt", ("Call", ("Identifier", "print"), [("Identifier", "k")]))]),
        )

    def test_for_map_destructure_two_names(self):
        stmt = parse_stmts("for {a, b} in maps { }")[0]
        self.assertIsInstance(stmt, ForStmt)
        self.assertIsNone(stmt.var_name)
        self.assertEqual(stmt.names, ["a", "b"])
        self.assertIsNone(stmt.rest)
        self.assertTrue(stmt.is_map)
        self.assertEqual(shape(stmt.iterable), ("Identifier", "maps"))

    def test_for_map_destructure_single_name(self):
        stmt = parse_stmts("for {a} in maps { }")[0]
        self.assertEqual(stmt.names, ["a"])
        self.assertTrue(stmt.is_map)

    def test_for_map_destructure_rejects_rest(self):
        with self.assertRaises(ParseError):
            parse_stmts("for {a, ...rest} in maps { }")

    def test_for_map_destructure_non_identifier_pattern_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for {1, b} in maps { }")

    def test_for_map_destructure_unclosed_brace_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for {a, b in maps { }")

    def test_for_map_destructure_missing_in_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for {a, b} maps { }")

    def test_for_map_destructure_carries_its_label(self):
        stmt = parse_stmts("outer: for {a} in maps { break outer; }")[0]
        self.assertEqual(stmt.label, "outer")
        self.assertEqual(stmt.names, ["a"])
        self.assertTrue(stmt.is_map)

    def test_for_map_destructure_body_parses(self):
        self.assertEqual(
            stmt_shape(parse_stmts("for {a} in maps { print(a); }")[0].body),
            ("Block", [("ExprStmt", ("Call", ("Identifier", "print"), [("Identifier", "a")]))]),
        )

    def test_for_list_destructure_is_map_false(self):
        stmt = parse_stmts("for [k, v] in items(m) { }")[0]
        self.assertFalse(stmt.is_map)


class TestForCStatement(unittest.TestCase):
    def test_full_three_clause_for(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("for (let i = 0; i < 3; i = i + 1) { }")],
            [
                (
                    "ForCStmt",
                    ("LetStmt", "i", ("Literal", 0)),
                    ("Binary", ("Identifier", "i"), TokenType.LT, ("Literal", 3)),
                    (
                        "ExprStmt",
                        ("Assign", "i", ("Binary", ("Identifier", "i"), TokenType.PLUS, ("Literal", 1))),
                    ),
                    ("Block", []),
                )
            ],
        )

    def test_increment_step_desugars_to_plusplus(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("for (let i = 0; i < 3; i++) { }")][0][3],
            ("ExprStmt", ("Assign", "i", ("Binary", ("Identifier", "i"), TokenType.PLUS, ("Literal", 1)))),
        )

    def test_empty_init_clause(self):
        shapes = [stmt_shape(s) for s in parse_stmts("for (; i < 3; i++) { }")]
        self.assertIsNone(shapes[0][1])

    def test_empty_condition_clause(self):
        shapes = [stmt_shape(s) for s in parse_stmts("for (;;) { break; }")]
        self.assertIsNone(shapes[0][1])
        self.assertIsNone(shapes[0][2])
        self.assertIsNone(shapes[0][3])

    def test_non_block_body_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("for (;;) break;")

    def test_break_and_continue_allowed_inside_c_for(self):
        # Regression: _loop_depth must be tracked for the C-style form too.
        parse_stmts("for (let i = 0; i < 3; i++) { if (i == 1) { break; } continue; }")

    def test_foreach_still_parses_unaffected(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("for x in xs { }")],
            [("ForStmt", "x", ("Identifier", "xs"), ("Block", []))],
        )


class TestDoWhileStatement(unittest.TestCase):
    def test_do_while_shape(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("do { print(1); } while (x < 3);")
            ],
            [
                (
                    "DoWhileStmt",
                    (
                        "Binary",
                        ("Identifier", "x"),
                        TokenType.LT,
                        ("Literal", 3),
                    ),
                    (
                        "Block",
                        [("ExprStmt", ("Call", ("Identifier", "print"), [("Literal", 1)]))],
                    ),
                )
            ],
        )

    def test_plain_while_still_parses_unaffected(self):
        # WhileStmt has no `stmt_shape` case (see TestBreakContinue below);
        # shape its body directly instead of the statement itself.
        stmts = parse_stmts("while (x < 3) { print(1); }")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(
            shape(stmts[0].condition),
            ("Binary", ("Identifier", "x"), TokenType.LT, ("Literal", 3)),
        )
        self.assertEqual(
            stmt_shape(stmts[0].body),
            ("Block", [("ExprStmt", ("Call", ("Identifier", "print"), [("Literal", 1)]))]),
        )

    def test_missing_trailing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("do { print(1); } while (x < 3)")

    def test_missing_while_keyword_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("do { print(1); } (x < 3);")


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

    def test_break_and_continue_inside_do_while_body(self):
        stmts = parse_stmts("do { break; continue; } while (true);")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(
            stmt_shape(stmts[0].body),
            ("Block", [("BreakStmt",), ("ContinueStmt",)]),
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


class TestLabeledLoops(unittest.TestCase):
    def test_while_carries_its_label(self):
        stmt = parse_stmts("outer: while (true) { break outer; }")[0]
        self.assertIsInstance(stmt, WhileStmt)
        self.assertEqual(stmt.label, "outer")
        self.assertEqual(stmt.body.statements[0].label, "outer")

    def test_do_while_carries_its_label(self):
        stmt = parse_stmts("outer: do { break outer; } while (true);")[0]
        self.assertIsInstance(stmt, DoWhileStmt)
        self.assertEqual(stmt.label, "outer")

    def test_foreach_for_carries_its_label(self):
        stmt = parse_stmts("outer: for x in [1] { break outer; }")[0]
        self.assertIsInstance(stmt, ForStmt)
        self.assertEqual(stmt.label, "outer")

    def test_c_style_for_carries_its_label(self):
        stmt = parse_stmts("outer: for (let i = 0; i < 1; i++) { break outer; }")[0]
        self.assertIsInstance(stmt, ForCStmt)
        self.assertEqual(stmt.label, "outer")

    def test_unlabeled_loops_default_label_to_none(self):
        # Regression: a plain, unlabeled loop must still parse with `label`
        # defaulting to None, not require the new syntax.
        stmt = parse_stmts("while (true) { break; }")[0]
        self.assertIsNone(stmt.label)
        self.assertIsNone(stmt.body.statements[0].label)

    def test_break_and_continue_without_a_name_still_default_to_none(self):
        stmts = parse_stmts("outer: while (true) { break; continue; }")
        body_stmts = stmts[0].body.statements
        self.assertIsNone(body_stmts[0].label)
        self.assertIsNone(body_stmts[1].label)

    def test_nested_loops_break_and_continue_can_name_the_outer_label(self):
        stmts = parse_stmts(
            "outer: for (let i = 0; i < 3; i++) {"
            "  for (let j = 0; j < 3; j++) {"
            "    continue outer;"
            "    break outer;"
            "  }"
            "}"
        )
        inner_body = stmts[0].body.statements[0].body.statements
        self.assertEqual(inner_body[0].label, "outer")
        self.assertEqual(inner_body[1].label, "outer")

    def test_break_naming_nonexistent_label_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { break nonexistent; }")

    def test_continue_naming_nonexistent_label_raises(self):
        with self.assertRaises(ParseError):
            parse_stmts("while (true) { continue nonexistent; }")

    def test_break_naming_label_only_valid_in_sibling_loop_raises(self):
        # `a` and `b` are siblings, not nested — `a`'s label isn't in scope
        # inside `b`'s body.
        with self.assertRaises(ParseError):
            parse_stmts(
                "a: while (true) { break; } b: while (true) { break a; }"
            )

    def test_labeled_break_outside_any_loop_raises(self):
        # Same guard as unlabeled break/continue outside a loop — a label
        # doesn't create a loop out of nothing.
        with self.assertRaises(ParseError):
            parse_stmts("break outer;")

    def test_bare_empty_map_literal_still_parses_as_expression_statement(self):
        # Regression: the new "IDENTIFIER ':' loop-keyword" lookahead in
        # `_statement` must not affect the unrelated leading-`{` disambiguation
        # between a Block and a map-literal expression statement.
        stmts = parse_stmts('{"a": 1};')
        self.assertEqual(stmt_shape(stmts[0]), ("ExprStmt", ("MapLiteral", [(("Literal", "a"), ("Literal", 1))])))


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
                    None,
                )
            ],
        )

    def test_try_catch_empty_bodies(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("try {} catch (e) {}")],
            [("TryStmt", ("Block", []), "e", ("Block", []), None)],
        )

    def test_try_catch_finally_shape(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("try { 1; } catch (e) { 2; } finally { 3; }")
            ],
            [
                (
                    "TryStmt",
                    ("Block", [("ExprStmt", ("Literal", 1))]),
                    "e",
                    ("Block", [("ExprStmt", ("Literal", 2))]),
                    ("Block", [("ExprStmt", ("Literal", 3))]),
                )
            ],
        )

    def test_try_finally_without_catch_shape(self):
        self.assertEqual(
            [stmt_shape(s) for s in parse_stmts("try { 1; } finally { 2; }")],
            [
                (
                    "TryStmt",
                    ("Block", [("ExprStmt", ("Literal", 1))]),
                    None,
                    None,
                    ("Block", [("ExprStmt", ("Literal", 2))]),
                )
            ],
        )

    def test_finally_body_must_be_block(self):
        with self.assertRaises(ParseError):
            parse_stmts("try { 1; } finally 2;")

    def test_missing_catch_and_finally_raises(self):
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
                            [("Literal", 1)],
                            ("Block", [("LetStmt", "a", ("Literal", 1))]),
                        ),
                        (
                            [("Literal", 2)],
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
            [("SwitchStmt", ("Identifier", "x"), [([("Literal", 1)], ("Block", []))], None)],
        )

    def test_switch_multi_value_case_shape(self):
        self.assertEqual(
            [
                stmt_shape(s)
                for s in parse_stmts("switch (x) { case 1, 2, 3: { } }")
            ],
            [
                (
                    "SwitchStmt",
                    ("Identifier", "x"),
                    [
                        (
                            [("Literal", 1), ("Literal", 2), ("Literal", 3)],
                            ("Block", []),
                        )
                    ],
                    None,
                )
            ],
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
