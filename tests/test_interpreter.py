"""Tests for cinder.interpreter: expression evaluation, Environment scoping."""

import unittest

from cinder.errors import CinderRuntimeError
from cinder.interpreter import Environment, Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_expression


def evaluate(source: str):
    interpreter = Interpreter()
    env = Environment()
    return interpreter.evaluate(parse_expression(tokenize(source)), env)


class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(evaluate("1 + 2"), 3)

    def test_precedence(self):
        # multiplication binds tighter than addition
        self.assertEqual(evaluate("1 + 2 * 3"), 7)

    def test_grouping_overrides_precedence(self):
        self.assertEqual(evaluate("(1 + 2) * 3"), 9)

    def test_subtraction_and_division(self):
        self.assertEqual(evaluate("10 - 4 / 2"), 8)

    def test_modulo(self):
        self.assertEqual(evaluate("10 % 3"), 1)

    def test_float_arithmetic(self):
        self.assertEqual(evaluate("1.5 + 2.5"), 4.0)

    def test_division_by_zero_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 / 0")

    def test_modulo_by_zero_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 % 0")

    def test_arithmetic_type_mismatch_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('1 + "x"')

    def test_unary_minus_on_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('-"x"')


class TestStringConcatenation(unittest.TestCase):
    def test_string_plus_string(self):
        self.assertEqual(evaluate('"foo" + "bar"'), "foobar")


class TestComparisons(unittest.TestCase):
    def test_less_than(self):
        self.assertEqual(evaluate("1 < 2"), True)

    def test_greater_than_or_equal(self):
        self.assertEqual(evaluate("2 >= 2"), True)

    def test_equality_numbers(self):
        self.assertEqual(evaluate("1 == 1"), True)

    def test_inequality(self):
        self.assertEqual(evaluate("1 != 2"), True)

    def test_equality_different_types_is_false(self):
        self.assertEqual(evaluate('1 == "1"'), False)

    def test_string_ordering(self):
        self.assertEqual(evaluate('"apple" < "banana"'), True)

    def test_ordering_type_mismatch_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('1 < "x"')


class TestLogical(unittest.TestCase):
    def test_and_short_circuits_on_false(self):
        # right side would error if evaluated; short-circuit must prevent that
        self.assertEqual(evaluate('false and (1 / 0)'), False)

    def test_or_short_circuits_on_true(self):
        self.assertEqual(evaluate('true or (1 / 0)'), True)

    def test_and_evaluates_right_when_left_truthy(self):
        self.assertEqual(evaluate("true and 5"), 5)

    def test_or_evaluates_right_when_left_falsy(self):
        self.assertEqual(evaluate("nil or 5"), 5)


class TestUnaryAndGrouping(unittest.TestCase):
    def test_unary_minus(self):
        self.assertEqual(evaluate("-5"), -5)

    def test_double_unary_minus(self):
        self.assertEqual(evaluate("--5"), 5)

    def test_not_true_is_false(self):
        self.assertEqual(evaluate("not true"), False)

    def test_not_falsy_values(self):
        self.assertEqual(evaluate("not nil"), True)
        self.assertEqual(evaluate("not 0"), False)
        self.assertEqual(evaluate('not ""'), False)

    def test_grouping_passthrough(self):
        self.assertEqual(evaluate("(42)"), 42)


class TestIdentifiers(unittest.TestCase):
    def test_lookup_populated_environment(self):
        interpreter = Interpreter()
        env = Environment()
        env.define("x", 10)
        result = interpreter.evaluate(parse_expression(tokenize("x + 5")), env)
        self.assertEqual(result, 15)

    def test_lookup_in_parent_scope(self):
        interpreter = Interpreter()
        parent = Environment()
        parent.define("x", 7)
        child = Environment(parent)
        result = interpreter.evaluate(parse_expression(tokenize("x")), child)
        self.assertEqual(result, 7)

    def test_undeclared_name_raises_with_line_info(self):
        interpreter = Interpreter()
        env = Environment()
        with self.assertRaises(CinderRuntimeError) as ctx:
            interpreter.evaluate(parse_expression(tokenize("missing")), env)
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)


if __name__ == "__main__":
    unittest.main()
