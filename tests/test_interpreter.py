"""Tests for cinder.interpreter: expression evaluation, Environment scoping."""

import unittest

from cinder.errors import CinderRuntimeError
from cinder.interpreter import Environment, Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_expression, parse_program


def evaluate(source: str):
    interpreter = Interpreter()
    env = Environment()
    return interpreter.evaluate(parse_expression(tokenize(source)), env)


def run(source: str, env: Environment | None = None) -> Environment:
    interpreter = Interpreter()
    env = env if env is not None else Environment()
    for statement in parse_program(tokenize(source)):
        interpreter.execute(statement, env)
    return env


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


class TestStatements(unittest.TestCase):
    def test_let_declares_and_lookup_works(self):
        env = run("let x = 1 + 2;")
        self.assertEqual(env.get("x"), 3)

    def test_let_can_reference_earlier_let(self):
        env = run("let x = 1 + 2; let y = x * 2;")
        self.assertEqual(env.get("x"), 3)
        self.assertEqual(env.get("y"), 6)

    def test_expr_statement_is_evaluated_and_discarded(self):
        # should not raise, and should not define anything
        env = run("1 + 1;")
        with self.assertRaises(KeyError):
            env.get("anything")

    def test_block_shadows_outer_without_mutating_it(self):
        env = run("let x = 1; { let x = 2; }")
        self.assertEqual(env.get("x"), 1)

    def test_block_can_see_outer_scope(self):
        env = run("let x = 1; { let y = x + 1; }")
        self.assertEqual(env.get("x"), 1)

    def test_nested_block_scoping(self):
        env = run("let x = 1; { let x = 2; { let x = 3; } }")
        self.assertEqual(env.get("x"), 1)

    def test_inner_let_does_not_leak_out(self):
        env = run("{ let x = 1; }")
        with self.assertRaises(KeyError):
            env.get("x")


class TestAssignment(unittest.TestCase):
    def test_assignment_updates_existing_variable(self):
        env = run("let x = 1; x = 2;")
        self.assertEqual(env.get("x"), 2)

    def test_assignment_expression_evaluates_to_assigned_value(self):
        env = run("let x = 1; let y = (x = 5);")
        self.assertEqual(env.get("x"), 5)
        self.assertEqual(env.get("y"), 5)

    def test_assignment_mutates_outer_scope_from_inner_block(self):
        env = run("let x = 1; { x = 2; }")
        self.assertEqual(env.get("x"), 2)

    def test_assignment_to_undefined_name_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("x = 1;")

    def test_invalid_assignment_target_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            parse_program(tokenize("1 = 2;"))


class TestIfStatement(unittest.TestCase):
    def test_if_true_runs_then_branch(self):
        env = run("let x = 0; if (true) { x = 1; }")
        self.assertEqual(env.get("x"), 1)

    def test_if_false_skips_then_branch(self):
        env = run("let x = 0; if (false) { x = 1; }")
        self.assertEqual(env.get("x"), 0)

    def test_if_else_runs_else_branch_when_condition_false(self):
        env = run("let x = 0; if (false) { x = 1; } else { x = 2; }")
        self.assertEqual(env.get("x"), 2)

    def test_if_without_else_and_false_condition_is_noop(self):
        env = run("let x = 0; if (false) { x = 1; }")
        self.assertEqual(env.get("x"), 0)

    def test_nested_if(self):
        env = run(
            "let x = 0; "
            "if (true) { if (true) { x = 1; } else { x = 2; } } else { x = 3; }"
        )
        self.assertEqual(env.get("x"), 1)

    def test_nested_if_inner_false(self):
        env = run(
            "let x = 0; "
            "if (true) { if (false) { x = 1; } else { x = 2; } } else { x = 3; }"
        )
        self.assertEqual(env.get("x"), 2)


class TestWhileStatement(unittest.TestCase):
    def test_while_sums_one_to_ten(self):
        env = run(
            "let i = 1; let total = 0; "
            "while (i <= 10) { total = total + i; i = i + 1; }"
        )
        self.assertEqual(env.get("total"), 55)
        self.assertEqual(env.get("i"), 11)

    def test_while_false_condition_never_runs_body(self):
        env = run("let x = 0; while (false) { x = 1; }")
        self.assertEqual(env.get("x"), 0)


class TestTruthinessRule(unittest.TestCase):
    """Pins the rule: `false`/`nil` are falsy; everything else is truthy."""

    def test_falsy_values_skip_if_branch(self):
        for source in ("false", "nil"):
            env = run(f"let x = 0; if ({source}) {{ x = 1; }}")
            self.assertEqual(env.get("x"), 0, msg=source)

    def test_truthy_values_including_zero_and_empty_string_run_if_branch(self):
        for source in ("true", "0", '""', "1", '"a"'):
            env = run(f"let x = 0; if ({source}) {{ x = 1; }}")
            self.assertEqual(env.get("x"), 1, msg=source)


class TestFunctions(unittest.TestCase):
    def test_recursive_factorial(self):
        env = run(
            "fn factorial(n) { "
            "  if (n <= 1) { return 1; } "
            "  return n * factorial(n - 1); "
            "} "
            "let result = factorial(5);"
        )
        self.assertEqual(env.get("result"), 120)

    def test_recursive_fibonacci(self):
        env = run(
            "fn fib(n) { "
            "  if (n < 2) { return n; } "
            "  return fib(n - 1) + fib(n - 2); "
            "} "
            "let result = fib(10);"
        )
        self.assertEqual(env.get("result"), 55)

    def test_closure_captures_outer_variable_after_outer_returns(self):
        env = run(
            "fn make_adder(x) { "
            "  fn adder(y) { return x + y; } "
            "  return adder; "
            "} "
            "let add5 = make_adder(5); "
            "let result = add5(10);"
        )
        self.assertEqual(env.get("result"), 15)

    def test_function_without_return_yields_nil(self):
        env = run("fn noop() { let x = 1; } let result = noop();")
        self.assertIsNone(env.get("result"))

    def test_return_stops_execution_early(self):
        env = run(
            "fn early() { return 1; return 2; } let result = early();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_wrong_argument_count_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("fn add(a, b) { return a + b; } add(1);")

    def test_calling_non_function_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let x = 1; x();")

    def test_function_is_first_class_value(self):
        env = run("fn double(n) { return n * 2; } let f = double; let result = f(21);")
        self.assertEqual(env.get("result"), 42)


class TestListsAndMaps(unittest.TestCase):
    def test_list_literal(self):
        self.assertEqual(evaluate("[1, 2, 3]"), [1, 2, 3])

    def test_empty_list_literal(self):
        self.assertEqual(evaluate("[]"), [])

    def test_map_literal(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2}'), {"a": 1, "b": 2})

    def test_empty_map_literal(self):
        self.assertEqual(evaluate("{}"), {})

    def test_list_get_index(self):
        self.assertEqual(evaluate("[10, 20, 30][1]"), 20)

    def test_map_get_key(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2}["b"]'), 2)

    def test_list_set_index(self):
        env = run("let xs = [1, 2, 3]; xs[0] = 99;")
        self.assertEqual(env.get("xs"), [99, 2, 3])

    def test_map_set_key(self):
        env = run('let m = {"a": 1}; m["a"] = 99;')
        self.assertEqual(env.get("m"), {"a": 99})

    def test_map_set_new_key_adds_entry(self):
        env = run('let m = {"a": 1}; m["b"] = 2;')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_nested_list_of_maps(self):
        value = evaluate('[{"a": 1}, {"a": 2}][1]["a"]')
        self.assertEqual(value, 2)

    def test_nested_map_of_lists(self):
        value = evaluate('{"xs": [1, 2, 3]}["xs"][2]')
        self.assertEqual(value, 3)

    def test_list_index_via_variable(self):
        env = run("let xs = [1, [2, 3], 4]; let inner = xs[1]; let result = inner[0];")
        self.assertEqual(env.get("result"), 2)

    def test_list_index_out_of_range_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1, 2, 3][5]")

    def test_list_negative_index_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1, 2, 3][-1]")

    def test_map_missing_key_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('{"a": 1}["missing"]')

    def test_list_non_int_index_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('[1, 2, 3]["a"]')

    def test_indexing_non_indexable_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1[0]")

    def test_list_set_out_of_range_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("let xs = [1, 2, 3]; xs[10] = 1;")

    def test_string_get_index(self):
        self.assertEqual(evaluate('"hello"[0]'), "h")
        self.assertEqual(evaluate('"hello"[4]'), "o")

    def test_string_index_out_of_range_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"hello"[5]')

    def test_string_negative_index_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"hello"[-1]')

    def test_string_non_int_index_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"hello"["a"]')

    def test_string_index_assign_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            run('let s = "hi"; s[0] = "y";')


if __name__ == "__main__":
    unittest.main()
