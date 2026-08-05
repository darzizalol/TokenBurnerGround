"""Tests for cinder.interpreter: expression evaluation, Environment scoping."""

import unittest

from cinder.errors import CinderRuntimeError, ParseError
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


class TestFloorDivision(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(evaluate("7 // 2"), 3)

    def test_exact_no_remainder(self):
        self.assertEqual(evaluate("6 // 2"), 3)

    def test_floors_toward_negative_infinity(self):
        # -7 // 2 is -4 (floored), not -3 (truncated toward zero) — this
        # would catch an accidental int(a / b) implementation.
        self.assertEqual(evaluate("-7 // 2"), -4)

    def test_float_operand_returns_float(self):
        self.assertEqual(evaluate("7.5 // 2"), 3.0)

    def test_same_precedence_tier_as_mul_div_mod(self):
        # Evaluated left-to-right when mixed with */ /%.
        self.assertEqual(evaluate("8 // 2 * 2"), 8)

    def test_looser_than_exponent(self):
        self.assertEqual(evaluate("2 ** 3 // 2"), 4)

    def test_division_by_zero_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("7 // 0")
        self.assertIn("division by zero in '//'", str(ctx.exception))

    def test_non_number_operand_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('"a" // 2')
        self.assertIn("'//'", str(ctx.exception))


class TestExponentiation(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(evaluate("2 ** 10"), 1024)

    def test_right_associative(self):
        # 2 ** (3 ** 2) == 2 ** 9 == 512, not (2 ** 3) ** 2 == 64.
        self.assertEqual(evaluate("2 ** 3 ** 2"), 512)

    def test_unary_minus_binds_tighter_than_exponent(self):
        # Deliberately diverges from Python: here unary minus binds tighter,
        # so both forms are (-2) ** 2 == 4, never -(2 ** 2) == -4.
        self.assertEqual(evaluate("(-2) ** 2"), 4)
        self.assertEqual(evaluate("-2 ** 2"), 4)

    def test_negative_exponent(self):
        self.assertEqual(evaluate("2 ** -1"), 0.5)

    def test_float_base(self):
        self.assertEqual(evaluate("2.5 ** 2"), 6.25)

    def test_zero_exponent_and_zero_base(self):
        self.assertEqual(evaluate("2 ** 0"), 1)
        self.assertEqual(evaluate("0 ** 0"), 1)

    def test_string_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"a" ** 2')
        with self.assertRaises(CinderRuntimeError):
            evaluate('2 ** "a"')

    def test_zero_to_negative_power_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("0 ** -1")
        with self.assertRaises(CinderRuntimeError):
            evaluate("0.0 ** -1")

    def test_overflow_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("2.0 ** 100000")

    def test_complex_result_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("(-8) ** 0.5")

    def test_binds_tighter_than_multiplication(self):
        self.assertEqual(evaluate("2 ** 3 * 4"), 32)
        self.assertEqual(evaluate("2 * 3 ** 2"), 18)


class TestPrefixedIntLiterals(unittest.TestCase):
    def test_hex_literal_value(self):
        self.assertEqual(evaluate("0xFF"), 255)

    def test_binary_literal_value(self):
        self.assertEqual(evaluate("0b1010"), 10)

    def test_octal_literal_value(self):
        self.assertEqual(evaluate("0o17"), 15)

    def test_hex_arithmetic(self):
        self.assertEqual(evaluate("0xFF + 1"), 256)

    def test_hex_comparison(self):
        self.assertEqual(evaluate("0x10 > 15"), True)

    def test_hex_as_list_index(self):
        self.assertEqual(evaluate("[10, 20, 30][0x1]"), 20)

    def test_hex_as_function_argument(self):
        env = run("fn double(x) { return x * 2; } let result = double(0x10);")
        self.assertEqual(env.get("result"), 32)


class TestBitwise(unittest.TestCase):
    def test_and_or_xor(self):
        self.assertEqual(evaluate("5 & 3"), 1)
        self.assertEqual(evaluate("5 | 2"), 7)
        self.assertEqual(evaluate("5 ^ 1"), 4)

    def test_not(self):
        self.assertEqual(evaluate("~5"), -6)

    def test_shifts(self):
        self.assertEqual(evaluate("1 << 3"), 8)
        self.assertEqual(evaluate("16 >> 2"), 4)

    def test_shift_binds_looser_than_addition(self):
        self.assertEqual(evaluate("2 + 3 << 1"), 10)

    def test_float_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("5.0 & 3")

    def test_string_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"a" | 1')

    def test_unary_not_on_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('~"a"')

    def test_unary_not_on_float_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("~5.0")

    def test_unary_not_on_bool_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("~true")

    def test_bool_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("true & 1")

    def test_negative_left_shift_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 << -1")

    def test_negative_right_shift_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 >> -1")


class TestStringConcatenation(unittest.TestCase):
    def test_string_plus_string(self):
        self.assertEqual(evaluate('"foo" + "bar"'), "foobar")


class TestStringInterpolation(unittest.TestCase):
    def test_identifier_placeholder(self):
        env = run('let name = "world"; let msg = "hello, ${name}!";')
        self.assertEqual(env.get("msg"), "hello, world!")

    def test_arbitrary_expression_placeholder(self):
        self.assertEqual(evaluate('"${1 + 2}"'), "3")

    def test_non_list_result_stringifies_unquoted_like_print(self):
        self.assertEqual(evaluate('"${[1, 2, 3]}"'), "[1, 2, 3]")
        self.assertEqual(evaluate('"${ {"a": 1} }"'), '{"a": 1}')

    def test_multiple_placeholders(self):
        self.assertEqual(evaluate('"a${1}b${2}c"'), "a1b2c")

    def test_plain_string_with_no_placeholders_is_unchanged(self):
        self.assertEqual(evaluate('"no placeholders here"'), "no placeholders here")

    def test_nested_list_result_stringifies_without_extra_flattening(self):
        self.assertEqual(evaluate('"${[[1, 2]]}"'), "[[1, 2]]")

    def test_runtime_error_in_placeholder_reports_placeholder_position(self):
        # Not the string literal's opening-quote position (1, 1).
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('"${1/0}"')
        self.assertEqual((ctx.exception.line, ctx.exception.column), (1, 5))


class TestRepetition(unittest.TestCase):
    def test_string_times_int(self):
        self.assertEqual(evaluate('"ab" * 3'), "ababab")

    def test_int_times_string(self):
        self.assertEqual(evaluate('3 * "ab"'), "ababab")

    def test_list_times_int(self):
        self.assertEqual(evaluate("[1, 2] * 2"), [1, 2, 1, 2])

    def test_int_times_list(self):
        self.assertEqual(evaluate("2 * [1, 2]"), [1, 2, 1, 2])

    def test_string_times_zero(self):
        self.assertEqual(evaluate('"x" * 0'), "")

    def test_list_times_negative(self):
        self.assertEqual(evaluate("[1] * -1"), [])

    def test_list_times_float_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1] * 1.5")

    def test_string_times_float_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"a" * 1.5')

    def test_list_repetition_does_not_mutate_input(self):
        env = run("let original = [1, 2]; let repeated = original * 2;")
        self.assertEqual(env.get("original"), [1, 2])
        self.assertEqual(env.get("repeated"), [1, 2, 1, 2])

    def test_numeric_multiplication_unchanged(self):
        self.assertEqual(evaluate("3 * 4"), 12)
        self.assertEqual(evaluate("2.5 * 2"), 5.0)


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


class TestNullishCoalescing(unittest.TestCase):
    def test_nil_left_falls_through_to_right(self):
        self.assertEqual(evaluate("nil ?? 5"), 5)

    def test_non_nil_left_short_circuits(self):
        self.assertEqual(evaluate("1 ?? 5"), 1)

    def test_zero_is_not_nil(self):
        self.assertEqual(evaluate("0 ?? 5"), 0)

    def test_empty_string_is_not_nil(self):
        self.assertEqual(evaluate('"" ?? "x"'), "")

    def test_false_is_not_nil(self):
        # unlike `or`, `??` only falls through on `nil`, not general falsiness
        self.assertEqual(evaluate("false ?? 5"), False)

    def test_right_not_evaluated_when_left_non_nil(self):
        # division by zero on the right must not raise since the left short-circuits
        self.assertEqual(evaluate("1 ?? (1 / 0)"), 1)

    def test_right_associative_chaining(self):
        self.assertEqual(evaluate("nil ?? nil ?? 3"), 3)


class TestOptionalChaining(unittest.TestCase):
    def test_nil_short_circuits_to_nil(self):
        self.assertIsNone(evaluate("nil?.key"))

    def test_non_nil_map_behaves_like_plain_dot(self):
        self.assertEqual(evaluate('{"key": 42}?.key'), 42)

    def test_composes_with_nil_coalescing(self):
        self.assertEqual(evaluate('nil?.key ?? "default"'), "default")

    def test_missing_key_on_non_nil_map_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("{}?.missing")

    def test_non_nil_non_map_still_raises_not_indexable(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("5?.key")

    def test_single_level_short_circuit_only(self):
        # `?.a` yields nil, then the plain `.b` on that nil still raises —
        # this is the documented, deliberate divergence from JS-style
        # full-chain optional chaining.
        with self.assertRaises(CinderRuntimeError):
            evaluate("nil?.a.b")

    def test_base_expression_evaluated_exactly_once(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let calls = []; "
            "fn m() { push(calls, 1); return nil; } "
            "m()?.key; "
            "let n = len(calls);",
            create_global_environment(),
        )
        self.assertEqual(env.get("n"), 1)

    def test_optional_dot_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run("let m = nil; m?.key = 5;")

    def test_optional_dot_compound_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run("let m = nil; m?.key += 1;")


class TestTernary(unittest.TestCase):
    def test_true_condition_takes_then_branch(self):
        self.assertEqual(evaluate("true ? 1 : 2"), 1)

    def test_false_condition_takes_else_branch(self):
        self.assertEqual(evaluate("false ? 1 : 2"), 2)

    def test_zero_is_truthy_regression(self):
        # Cinder's `0` is truthy (unlike Python), so the then-branch is taken.
        self.assertEqual(evaluate('0 ? "a" : "b"'), "a")

    def test_else_branch_not_evaluated_when_condition_true(self):
        # division by zero in the untaken else-branch must not raise
        env = run("let x = true ? 1 : (1 / 0);")
        self.assertEqual(env.get("x"), 1)

    def test_then_branch_not_evaluated_when_condition_false(self):
        # division by zero in the untaken then-branch must not raise
        env = run("let x = false ? (1 / 0) : 2;")
        self.assertEqual(env.get("x"), 2)

    def test_nested_ternary_right_associative(self):
        self.assertEqual(evaluate("true ? false ? 1 : 2 : 3"), 2)

    def test_map_literal_statement_still_parses_with_ternary(self):
        env = run('{"a": 1} ? 1 : 2;')
        self.assertIsInstance(env, Environment)

    def test_ternary_as_call_argument(self):
        # len(...) forces evaluation of a ternary passed as a call argument.
        from cinder.builtins import create_global_environment

        interpreter = Interpreter()
        result = interpreter.evaluate(
            parse_expression(tokenize('len(true ? "abc" : "de")')),
            create_global_environment(),
        )
        self.assertEqual(result, 3)

    def test_ternary_as_list_element(self):
        self.assertEqual(evaluate("[1, true ? 2 : 3, 4]"), [1, 2, 4])

    def test_ternary_as_map_value(self):
        self.assertEqual(evaluate('{"k": true ? 1 : 2}'), {"k": 1})

    def test_ternary_as_index(self):
        self.assertEqual(evaluate("[10, 20][true ? 0 : 1]"), 10)


class TestMembership(unittest.TestCase):
    def test_in_list_true(self):
        self.assertEqual(evaluate("2 in [1, 2, 3]"), True)

    def test_in_list_false(self):
        self.assertEqual(evaluate("5 in [1, 2, 3]"), False)

    def test_in_list_does_not_conflate_bool_with_int(self):
        self.assertEqual(evaluate("true in [1, 2, 3]"), False)

    def test_in_map_checks_keys_not_values(self):
        self.assertEqual(evaluate('"a" in {"a": 1}'), True)
        self.assertEqual(evaluate('"z" in {"a": 1}'), False)

    def test_in_string_substring(self):
        self.assertEqual(evaluate('"ll" in "hello"'), True)
        self.assertEqual(evaluate('"z" in "hello"'), False)

    def test_in_non_collection_right_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 in 5")

    def test_in_precedence_with_and(self):
        # regression: `in` must bind tighter than `and` on both sides
        self.assertEqual(evaluate("1 in [1] and 2 in [2]"), True)
        self.assertEqual(evaluate("1 in [1] and 9 in [2]"), False)

    def test_for_in_loop_still_parses_and_runs(self):
        # regression: adding `in` as a binary operator must not affect
        # the `for`-loop grammar's own use of the `in` keyword.
        env = run("let total = 0; for x in [1, 2, 3] { total = total + x; }")
        self.assertEqual(env.get("total"), 6)

    def test_not_in_list(self):
        self.assertEqual(evaluate("2 not in [1, 2, 3]"), False)
        self.assertEqual(evaluate("4 not in [1, 2, 3]"), True)

    def test_not_in_string_substring(self):
        self.assertEqual(evaluate('"a" not in "abc"'), False)
        self.assertEqual(evaluate('"z" not in "abc"'), True)

    def test_not_in_map_checks_keys(self):
        self.assertEqual(evaluate('"x" not in {"x": 1}'), False)
        self.assertEqual(evaluate('"y" not in {"x": 1}'), True)

    def test_not_in_precedence_with_and(self):
        self.assertEqual(evaluate("1 not in [2] and 2 not in [1]"), True)

    def test_comparison_binds_tighter_than_not_in(self):
        # `1 < 2` is `true`; `true not in [true]` is `false`.
        self.assertEqual(evaluate("1 < 2 not in [true]"), False)

    def test_not_in_agrees_with_parenthesized_not_in(self):
        self.assertEqual(
            evaluate("not (2 in [1, 2, 3])"), evaluate("2 not in [1, 2, 3]")
        )
        self.assertEqual(
            evaluate("not (4 in [1, 2, 3])"), evaluate("4 not in [1, 2, 3]")
        )

    def test_not_in_non_collection_right_operand_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("5 not in 5")


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

    def test_all_names_includes_parent_chain(self):
        parent = Environment()
        parent.define("x", 1)
        child = Environment(parent)
        child.define("y", 2)
        self.assertEqual(child.all_names(), {"x", "y"})


class TestUndefinedNameSuggestions(unittest.TestCase):
    def test_identifier_lookup_suggests_close_match(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let cost = 1; costt;")
        self.assertEqual(
            ctx.exception.message, "undefined name 'costt' (did you mean 'cost'?)"
        )

    def test_assignment_suggests_close_match(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let cost = 1; costt = 2;")
        self.assertEqual(
            ctx.exception.message, "undefined name 'costt' (did you mean 'cost'?)"
        )

    def test_no_close_match_leaves_message_unchanged(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("zzzzzzz_no_match;")
        self.assertEqual(ctx.exception.message, "undefined name 'zzzzzzz_no_match'")

    def test_builtin_typo_suggests_builtin(self):
        from cinder.builtins import create_global_environment

        with self.assertRaises(CinderRuntimeError) as ctx:
            run("pritn(1);", create_global_environment())
        self.assertEqual(
            ctx.exception.message, "undefined name 'pritn' (did you mean 'print'?)"
        )

    def test_suggestion_does_not_change_line_or_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let cost = 1;\ncostt;")
        self.assertEqual(ctx.exception.line, 2)
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

    def test_let_redeclare_same_scope_overwrites(self):
        # Regression: `Environment.define` just overwrites the dict entry,
        # so a second `let` for the same name in the same scope silently
        # rebinds rather than erroring. Pinning this rather than adding new
        # redeclaration-checking behavior.
        env = run("let x = 1; let x = 2;")
        self.assertEqual(env.get("x"), 2)


class TestConst(unittest.TestCase):
    def test_const_declares_and_lookup_works(self):
        env = run("const x = 5;")
        self.assertEqual(env.get("x"), 5)

    def test_const_reassignment_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("const x = 5; x = 6;")

    def test_const_reassignment_leaves_value_unchanged(self):
        env = Environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("const x = 5; x = 6;"))
        with self.assertRaises(CinderRuntimeError):
            for statement in statements:
                interpreter.execute(statement, env)
        self.assertEqual(env.get("x"), 5)

    def test_const_reassignment_error_carries_assignment_location(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("const x = 5;\nx = 6;")
        self.assertEqual(ctx.exception.line, 2)

    def test_const_compound_assignment_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("const x = 5; x += 1;")

    def test_const_compound_assignment_leaves_value_unchanged(self):
        env = Environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("const x = 5; x += 1;"))
        with self.assertRaises(CinderRuntimeError):
            for statement in statements:
                interpreter.execute(statement, env)
        self.assertEqual(env.get("x"), 5)

    def test_const_index_assignment_unaffected(self):
        env = run("const xs = [1, 2]; xs[0] = 9;")
        self.assertEqual(env.get("xs"), [9, 2])

    def test_const_inner_block_shadows_outer_let(self):
        # A `const` shadowing an outer `let` in an inner block is a fresh,
        # independent binding; the outer `let` can still be reassigned once
        # the inner block exits.
        env = run("let x = 1; { const x = 2; } x = 3;")
        self.assertEqual(env.get("x"), 3)

    def test_const_inner_block_does_not_leak_out(self):
        env = run("{ const x = 1; }")
        with self.assertRaises(KeyError):
            env.get("x")

    def test_const_increment_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("const x = 5; x++;")

    def test_let_then_const_redeclare_same_scope_freezes(self):
        # `let` followed by `const` for the same name in the same scope:
        # define_const freshly freezes the name, so it takes effect even
        # though a plain `let` bound it moments earlier.
        with self.assertRaises(CinderRuntimeError):
            run("let x = 1; const x = 2; x = 3;")

    def test_const_then_let_redeclare_same_scope_unfreezes(self):
        # `const` followed by `let` for the same name in the same scope:
        # `define` discards the stale `_frozen` entry, so the name is
        # mutable again rather than still raising from the earlier const.
        env = run("const x = 1; let x = 2; x = 3;")
        self.assertEqual(env.get("x"), 3)

    def test_const_redeclare_same_scope_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("const x = 1; const x = 2; x = 3;")


class TestDestructureLet(unittest.TestCase):
    def test_binds_two_names(self):
        env = run("let [a, b] = [1, 2];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_binds_three_names_in_order(self):
        env = run("let [a, b, c] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_rest_binds_remaining_elements_as_list(self):
        env = run("let [a, b, ...rest] = [1, 2, 3, 4];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("rest"), [3, 4])

    def test_rest_binds_empty_list_when_nothing_left_over(self):
        env = run("let [a, ...rest] = [1];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), [])

    def test_rest_only_pattern_captures_everything(self):
        env = run("let [...rest] = [1, 2, 3];")
        self.assertEqual(env.get("rest"), [1, 2, 3])

    def test_rest_does_not_relax_minimum_length(self):
        with self.assertRaises(CinderRuntimeError):
            run("let [a, b, ...rest] = [1];")

    def test_initializer_fully_evaluated_before_binding(self):
        # RHS is evaluated in full against the outer `x` before any name is
        # bound, matching scalar `let`'s evaluate-then-bind order — neither
        # element sees the new `x` mid-destructure.
        env = run("let x = 5; let [x, y] = [x + 1, x];")
        self.assertEqual(env.get("x"), 6)
        self.assertEqual(env.get("y"), 5)

    def test_too_many_elements_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let [a, b] = [1, 2, 3];")

    def test_too_few_elements_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let [a, b, c] = [1, 2];")

    def test_non_list_rhs_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let [a, b] = 5;")

    def test_error_carries_line_and_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let [a, b] = 5;")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_bindings_are_ordinary_mutable_variables(self):
        env = run("let [a, b] = [1, 2]; a = 99;")
        self.assertEqual(env.get("a"), 99)
        self.assertEqual(env.get("b"), 2)

    def test_does_not_leak_out_of_block(self):
        env = run("{ let [a, b] = [1, 2]; }")
        with self.assertRaises(KeyError):
            env.get("a")


class TestDestructureLetMap(unittest.TestCase):
    def test_binds_two_names(self):
        env = run('let {a, b} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_extra_unnamed_keys_are_ignored(self):
        env = run('let {a} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        with self.assertRaises(KeyError):
            env.get("b")

    def test_missing_named_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('let {a, b} = {"a": 1};')

    def test_missing_named_key_error_carries_line_and_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('let {a, b} = {"a": 1};')
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_non_map_rhs_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let {a} = [1, 2];")

    def test_non_map_rhs_scalar_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let {a} = 5;")

    def test_non_map_rhs_error_carries_line_and_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let {a} = 5;")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_bindings_are_ordinary_mutable_variables(self):
        env = run('let {a, b} = {"a": 1, "b": 2}; a = 99;')
        self.assertEqual(env.get("a"), 99)
        self.assertEqual(env.get("b"), 2)

    def test_does_not_leak_out_of_block(self):
        env = run('{ let {a, b} = {"a": 1, "b": 2}; }')
        with self.assertRaises(KeyError):
            env.get("a")

    def test_list_destructuring_unaffected(self):
        env = run("let [a, b] = [1, 2];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_plain_let_unaffected(self):
        env = run("let x = 1;")
        self.assertEqual(env.get("x"), 1)


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


class TestCompoundAssignment(unittest.TestCase):
    def test_plus_eq(self):
        env = run("let x = 5; x += 3;")
        self.assertEqual(env.get("x"), 8)

    def test_minus_eq(self):
        env = run("let x = 5; x -= 2;")
        self.assertEqual(env.get("x"), 3)

    def test_star_eq(self):
        env = run("let x = 5; x *= 4;")
        self.assertEqual(env.get("x"), 20)

    def test_slash_eq(self):
        env = run("let x = 6; x /= 2;")
        self.assertEqual(env.get("x"), 3)

    def test_percent_eq(self):
        env = run("let x = 5; x %= 3;")
        self.assertEqual(env.get("x"), 2)

    def test_starstar_eq(self):
        env = run("let x = 2; x **= 10; x;")
        self.assertEqual(env.get("x"), 1024)

    def test_starstar_eq_negative_exponent(self):
        env = run("let x = 2; x **= -1; x;")
        self.assertEqual(env.get("x"), 0.5)

    def test_starstar_eq_on_index_target(self):
        env = run("let xs = [2]; xs[0] **= 3; xs[0];")
        self.assertEqual(env.get("xs"), [8])

    def test_starstar_eq_on_dot_access_target(self):
        env = run('let m = {"a": 2}; m.a **= 3; m.a;')
        self.assertEqual(env.get("m"), {"a": 8})

    def test_starstar_eq_type_error_matches_binary(self):
        with self.assertRaises(CinderRuntimeError):
            run('let x = "a"; x **= 2;')

    def test_const_starstar_eq_raises_and_leaves_value_unchanged(self):
        env = Environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("const x = 2; x **= 2;"))
        with self.assertRaises(CinderRuntimeError):
            for statement in statements:
                interpreter.execute(statement, env)
        self.assertEqual(env.get("x"), 2)

    def test_slashslash_eq(self):
        env = run("let x = 7; x //= 2; x;")
        self.assertEqual(env.get("x"), 3)

    def test_slashslash_eq_floors_toward_negative_infinity(self):
        env = run("let x = -7; x //= 2; x;")
        self.assertEqual(env.get("x"), -4)

    def test_slashslash_eq_on_index_target(self):
        env = run("let xs = [7]; xs[0] //= 2; xs[0];")
        self.assertEqual(env.get("xs"), [3])

    def test_slashslash_eq_on_dot_access_target(self):
        env = run('let m = {"a": 7}; m.a //= 2; m.a;')
        self.assertEqual(env.get("m"), {"a": 3})

    def test_const_slashslash_eq_raises_and_leaves_value_unchanged(self):
        env = Environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("const x = 7; x //= 2;"))
        with self.assertRaises(CinderRuntimeError):
            for statement in statements:
                interpreter.execute(statement, env)
        self.assertEqual(env.get("x"), 7)

    def test_slashslash_eq_division_by_zero(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let x = 7; x //= 0;")
        self.assertIn("division by zero in '//'", str(ctx.exception))

    def test_slash_eq_still_works_alongside_slashslash_eq(self):
        # A plain "/=" must still parse and behave as before — confirms the
        # new SLASHSLASHEQ token doesn't shadow or interfere with "/=".
        env = run("let x = 7; x /= 2; x;")
        self.assertEqual(env.get("x"), 3.5)

    def test_compound_assignment_to_undefined_variable_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("x += 1;")

    def test_compound_assignment_type_error_matches_binary(self):
        with self.assertRaises(CinderRuntimeError):
            run('let s = "a"; s -= 1;')

    def test_arithmetic_compound_assign_on_index_target(self):
        env = run("let xs = [1, 2, 3]; xs[0] += 5;")
        self.assertEqual(env.get("xs"), [6, 2, 3])
        env = run("let xs = [1, 2, 3]; xs[0] -= 1;")
        self.assertEqual(env.get("xs"), [0, 2, 3])
        env = run("let xs = [1, 2, 3]; xs[0] *= 2;")
        self.assertEqual(env.get("xs"), [2, 2, 3])
        env = run("let xs = [1, 2, 3]; xs[0] /= 2;")
        self.assertEqual(env.get("xs"), [0.5, 2, 3])
        env = run("let xs = [1, 2, 3]; xs[0] %= 2;")
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_arithmetic_compound_assign_on_dot_access_target(self):
        # `m.key` desugars to the same Index node as `m["key"]`, so it gets
        # the same IndexCompoundAssign treatment for free.
        env = run('let m = {"count": 1}; m.count += 1;')
        self.assertEqual(env.get("m"), {"count": 2})

    def test_arithmetic_compound_assign_evaluates_index_expression_once(self):
        # Regression: xs[idx()] += 1 must call idx() exactly once, not once
        # for the read and again for the write.
        env = run(
            """
            let calls = 0;
            let idx = fn() { calls = calls + 1; return 0; };
            let xs = [5];
            xs[idx()] += 3;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("xs"), [8])

    def test_arithmetic_compound_assign_evaluates_object_expression_once(self):
        env = run(
            """
            let calls = 0;
            let get_list = fn() { calls = calls + 1; return xs; };
            let xs = [5];
            get_list()[0] += 3;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("xs"), [8])

    def test_invalid_arithmetic_compound_assign_target_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            parse_program(tokenize("1 + 1 += 1;"))

    def test_amp_eq_and_pipe_eq_and_caret_eq(self):
        env = run("let a = 0b1010; a &= 0b0110;")
        self.assertEqual(env.get("a"), 2)
        env = run("let a = 2; a |= 0b0001;")
        self.assertEqual(env.get("a"), 3)
        env = run("let a = 3; a ^= 0b0011;")
        self.assertEqual(env.get("a"), 0)

    def test_lshift_eq_and_rshift_eq(self):
        env = run("let b = 1; b <<= 3;")
        self.assertEqual(env.get("b"), 8)
        env = run("let b = 8; b >>= 2;")
        self.assertEqual(env.get("b"), 2)

    def test_bitwise_compound_assign_on_index_target(self):
        env = run("let xs = [5]; xs[0] &= 3;")
        self.assertEqual(env.get("xs"), [1])
        env = run("let xs = [8]; xs[0] >>= 2;")
        self.assertEqual(env.get("xs"), [2])

    def test_bitwise_compound_assign_evaluates_index_expression_once(self):
        # Regression: xs[idx()] &= 3 must call idx() exactly once, not once
        # for the read and again for the write.
        env = run(
            """
            let calls = 0;
            let idx = fn() { calls = calls + 1; return 0; };
            let xs = [5];
            xs[idx()] &= 3;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("xs"), [1])

    def test_bitwise_compound_assign_evaluates_object_expression_once(self):
        env = run(
            """
            let calls = 0;
            let get_list = fn() { calls = calls + 1; return xs; };
            let xs = [5];
            get_list()[0] &= 3;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("xs"), [1])

    def test_bitwise_compound_assign_type_error_matches_binary(self):
        with self.assertRaises(CinderRuntimeError):
            run("let a = 1.5; a &= 1;")

    def test_shift_compound_assign_negative_count_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("let b = 1; b <<= -1;")
        with self.assertRaises(CinderRuntimeError):
            run("let b = 1; b >>= -1;")


class TestNilCoalescingCompoundAssignment(unittest.TestCase):
    def test_nil_target_is_replaced(self):
        env = run("let x = nil; x ??= 5;")
        self.assertEqual(env.get("x"), 5)

    def test_non_nil_target_is_left_untouched(self):
        env = run("let x = 1; x ??= 5;")
        self.assertEqual(env.get("x"), 1)

    def test_false_is_not_nil(self):
        # unlike `x ||= 5`-style truthiness (which this language doesn't
        # have), `??=` only replaces on `nil`, not general falsiness.
        env = run("let x = false; x ??= 5;")
        self.assertEqual(env.get("x"), False)

    def test_right_not_evaluated_when_target_non_nil(self):
        env = run(
            """
            let calls = 0;
            fn bump() { calls = calls + 1; return 99; }
            let x = 1;
            x ??= bump();
            """
        )
        self.assertEqual(env.get("calls"), 0)
        self.assertEqual(env.get("x"), 1)

    def test_right_evaluated_once_when_target_nil(self):
        env = run(
            """
            let calls = 0;
            fn bump() { calls = calls + 1; return 99; }
            let x = nil;
            x ??= bump();
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("x"), 99)

    def test_index_target_nil_is_replaced(self):
        env = run('let m = {"a": nil}; m["a"] ??= 5;')
        self.assertEqual(env.get("m"), {"a": 5})

    def test_list_index_target_nil_is_replaced(self):
        env = run("let xs = [nil]; xs[0] ??= 1;")
        self.assertEqual(env.get("xs"), [1])

    def test_list_index_target_non_nil_is_left_untouched(self):
        env = run("let xs = [7]; xs[0] ??= 1;")
        self.assertEqual(env.get("xs"), [7])

    def test_index_target_non_nil_is_left_untouched(self):
        env = run('let m = {"a": 1}; m["a"] ??= 5;')
        self.assertEqual(env.get("m"), {"a": 1})

    def test_dot_access_target_nil_is_replaced(self):
        # `m.key` desugars to the same Index node as `m["key"]`, so it gets
        # the same IndexNilCoalesceAssign treatment for free.
        env = run("let m = {}; m.key ??= 5;")
        self.assertEqual(env.get("m"), {"key": 5})

    def test_index_target_evaluates_object_and_index_exactly_once_when_nil(self):
        env = run(
            """
            let calls = 0;
            let counter = fn() { calls = calls + 1; return calls; };
            let m = {1: nil};
            m[counter()] ??= 99;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("m"), {1: 99})

    def test_index_target_evaluates_object_and_index_exactly_once_when_non_nil(self):
        env = run(
            """
            let calls = 0;
            let counter = fn() { calls = calls + 1; return calls; };
            let m = {1: 1};
            m[counter()] ??= 99;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("m"), {1: 1})

    def test_index_target_right_not_evaluated_when_current_non_nil(self):
        env = run(
            """
            let m = {"a": 1};
            let calls = [];
            fn side() { push(calls, 1); return 99; }
            m["a"] ??= side();
            """
        )
        self.assertEqual(env.get("calls"), [])
        self.assertEqual(env.get("m"), {"a": 1})

    def test_invalid_qq_eq_target_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_program(tokenize("1 + 1 ??= 1;"))


class TestIncrementDecrement(unittest.TestCase):
    def test_plus_plus(self):
        env = run("let a = 5; a++;")
        self.assertEqual(env.get("a"), 6)

    def test_minus_minus(self):
        env = run("let a = 5; a--;")
        self.assertEqual(env.get("a"), 4)

    def test_plus_plus_then_minus_minus_round_trips(self):
        env = run("let a = 5; a++; a--;")
        self.assertEqual(env.get("a"), 5)

    def test_plus_plus_on_index_target(self):
        env = run("let xs = [1]; xs[0]++;")
        self.assertEqual(env.get("xs"), [2])

    def test_minus_minus_on_index_target(self):
        env = run("let xs = [1]; xs[0]--;")
        self.assertEqual(env.get("xs"), [0])

    def test_increment_evaluates_index_expression_once(self):
        # Same double-evaluation hazard as bitwise compound-assign on an
        # index target: idx() must be called exactly once.
        env = run(
            """
            let calls = 0;
            let idx = fn() { calls = calls + 1; return 0; };
            let xs = [1];
            xs[idx()]++;
            """
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("xs"), [2])

    def test_increment_to_undefined_variable_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("a++;")

    def test_increment_type_error_matches_binary(self):
        with self.assertRaises(CinderRuntimeError):
            run('let s = "a"; s++;')

    def test_increment_on_non_lvalue_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_program(tokenize("5++;"))

    def test_used_as_expression_value_is_unparseable(self):
        with self.assertRaises(ParseError):
            parse_program(tokenize("let b = a++;"))

    def test_plus_and_minus_and_compound_assign_unaffected(self):
        self.assertEqual(evaluate("1 + 2"), 3)
        env = run("let a = 1; a += 1;")
        self.assertEqual(env.get("a"), 2)


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


class TestDoWhileStatement(unittest.TestCase):
    def _run(self, source: str) -> Environment:
        from cinder.builtins import create_global_environment

        return run(source, create_global_environment())

    def test_do_while_runs_body_while_condition_holds(self):
        env = self._run(
            "let i = 0; let log = []; "
            "do { push(log, i); i = i + 1; } while (i < 3); "
        )
        self.assertEqual(env.get("log"), [0, 1, 2])

    def test_do_while_runs_body_once_even_if_condition_starts_false(self):
        env = self._run("let i = 5; let log = []; do { push(log, i); } while (i < 0);")
        self.assertEqual(env.get("log"), [5])

    def test_break_exits_do_while_without_rechecking_condition(self):
        env = self._run(
            "let i = 0; let log = []; "
            "do { push(log, i); i = i + 1; break; } while (true); "
        )
        self.assertEqual(env.get("log"), [0])

    def test_continue_goes_to_condition_check_not_top_of_body(self):
        # If `continue` re-ran the body from the top without checking `cond`
        # first, this would infinite-loop instead of terminating.
        env = self._run(
            "let i = 0; let log = []; "
            "do { i = i + 1; if (i < 3) { continue; } push(log, i); } while (i < 3); "
        )
        self.assertEqual(env.get("log"), [3])
        self.assertEqual(env.get("i"), 3)


class TestForStatement(unittest.TestCase):
    def test_for_in_sums_list(self):
        env = run("let total = 0; for x in [1, 2, 3] { total = total + x; }")
        self.assertEqual(env.get("total"), 6)

    def test_for_in_empty_list_never_runs_body(self):
        env = run("let x = 0; for item in [] { x = 1; }")
        self.assertEqual(env.get("x"), 0)

    def test_for_in_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("for x in 5 { }")

    def test_for_in_evaluates_iterable_once(self):
        env = run(
            "let calls = 0; "
            "fn make_list() { calls = calls + 1; return [1, 2, 3]; } "
            "let total = 0; "
            "for x in make_list() { total = total + x; }"
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("total"), 6)

    def test_closure_inside_for_body_captures_its_own_iteration_value(self):
        # Regression test: each iteration must get a fresh binding of the
        # loop variable, so closures made in different iterations don't all
        # end up sharing the final value (a classic per-iteration-scoping bug).
        env = run(
            "let fns = [nil, nil, nil]; "
            "let i = 0; "
            "for x in [1, 2, 3] { "
            "  fn make() { return x; } "
            "  fns[i] = make; "
            "  i = i + 1; "
            "} "
            "let a = fns[0](); "
            "let b = fns[1](); "
            "let c = fns[2]();"
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_for_loop_variable_does_not_leak_after_loop(self):
        with self.assertRaises(KeyError):
            run("for x in [1, 2, 3] { }").get("x")

    def test_for_in_string_iterates_characters(self):
        env = run(
            'let chars = [nil, nil, nil]; let i = 0; '
            'for c in "abc" { chars[i] = c; i = i + 1; }'
        )
        self.assertEqual(env.get("chars"), ["a", "b", "c"])

    def test_for_in_empty_string_never_runs_body(self):
        env = run('let x = 0; for c in "" { x = 1; }')
        self.assertEqual(env.get("x"), 0)

    def test_for_in_map_iterates_keys(self):
        env = run(
            'let ks = [nil, nil]; let i = 0; '
            'for k in {"a": 1, "b": 2} { ks[i] = k; i = i + 1; }'
        )
        self.assertEqual(env.get("ks"), ["a", "b"])

    def test_for_in_empty_map_never_runs_body(self):
        env = run("let x = 0; for k in {} { x = 1; }")
        self.assertEqual(env.get("x"), 0)


class TestForDestructuring(unittest.TestCase):
    def _run(self, source: str) -> Environment:
        from cinder.builtins import create_global_environment

        return run(source, create_global_environment())

    def test_destructures_pairs_from_items(self):
        env = self._run(
            'let ks = []; let vs = []; '
            'for [k, v] in items({"a": 1, "b": 2}) { push(ks, k); push(vs, v); }'
        )
        self.assertEqual(env.get("ks"), ["a", "b"])
        self.assertEqual(env.get("vs"), [1, 2])

    def test_binds_first_and_rest_each_iteration(self):
        env = self._run(
            "let firsts = []; let rests = []; "
            "for [first, ...rest] in [[1, 2, 3], [4, 5, 6]] { "
            "  push(firsts, first); push(rests, rest); "
            "}"
        )
        self.assertEqual(env.get("firsts"), [1, 4])
        self.assertEqual(env.get("rests"), [[2, 3], [5, 6]])

    def test_two_element_lists_bind_a_and_b(self):
        env = self._run("let a = nil; let b = nil; for [x, y] in [[1, 2]] { a = x; b = y; }")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_non_list_item_raises_cinder_runtime_error(self):
        with self.assertRaises(CinderRuntimeError):
            self._run("for [a, b] in [1, 2, 3] { }")

    def test_wrong_length_item_with_no_rest_raises(self):
        with self.assertRaises(CinderRuntimeError):
            self._run("for [a, b] in [[1, 2, 3]] { }")

    def test_error_carries_loop_line_and_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            self._run("for [a, b] in [1, 2, 3] { }")
        self.assertEqual(ctx.exception.line, 1)

    def test_labeled_break_still_works_on_destructuring_loop(self):
        env = self._run(
            'let seen = []; '
            'outer: for [k, v] in items({"a": 1, "b": 2}) { '
            '  if (k == "b") { break outer; } '
            '  push(seen, k); '
            '}'
        )
        self.assertEqual(env.get("seen"), ["a"])

    def test_let_destructuring_unaffected_by_shared_helper(self):
        env = run("let [a, b, ...rest] = [1, 2, 3, 4];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("rest"), [3, 4])


class TestForCStatement(unittest.TestCase):
    def _run(self, source: str) -> Environment:
        from cinder.builtins import create_global_environment

        return run(source, create_global_environment())

    def test_full_three_clause_for(self):
        env = self._run("let log = []; for (let i = 0; i < 3; i = i + 1) { push(log, i); }")
        self.assertEqual(env.get("log"), [0, 1, 2])

    def test_increment_step(self):
        env = self._run("let log = []; for (let i = 0; i < 3; i++) { push(log, i); }")
        self.assertEqual(env.get("log"), [0, 1, 2])

    def test_empty_init_reuses_outer_variable(self):
        env = self._run("let i = 0; let log = []; for (; i < 3; i++) { push(log, i); }")
        self.assertEqual(env.get("log"), [0, 1, 2])

    def test_break_stops_before_step_reruns(self):
        env = self._run(
            "let log = []; "
            "for (let i = 0; i < 5; i++) { if (i == 2) { break; } push(log, i); }"
        )
        self.assertEqual(env.get("log"), [0, 1])

    def test_continue_skips_to_step_not_body_top(self):
        env = self._run(
            "let log = []; "
            "for (let i = 0; i < 5; i++) { if (i == 2) { continue; } push(log, i); }"
        )
        self.assertEqual(env.get("log"), [0, 1, 3, 4])

    def test_infinite_loop_with_immediate_break(self):
        env = run("let ran = false; for (;;) { ran = true; break; }")
        self.assertEqual(env.get("ran"), True)

    def test_init_let_scoped_to_loop_only(self):
        with self.assertRaises(CinderRuntimeError):
            run("for (let i = 0; i < 3; i++) { } i;")

    def test_foreach_unaffected_regression(self):
        env = run("let total = 0; for x in [1, 2, 3] { total = total + x; }")
        self.assertEqual(env.get("total"), 6)

    def test_closure_inside_for_c_body_captures_its_own_iteration_value(self):
        # Regression test: each iteration must get a fresh binding of the
        # init-declared loop variable, so closures made in different
        # iterations don't all end up sharing the final post-loop value
        # (mirrors test_closure_inside_for_body_captures_its_own_iteration_value
        # for the foreach form).
        env = self._run(
            "let fns = [nil, nil, nil]; "
            "for (let i = 0; i < 3; i = i + 1) { fn make() { return i; } fns[i] = make; } "
            "let a = fns[0](); "
            "let b = fns[1](); "
            "let c = fns[2]();"
        )
        self.assertEqual(env.get("a"), 0)
        self.assertEqual(env.get("b"), 1)
        self.assertEqual(env.get("c"), 2)


class TestBreakContinue(unittest.TestCase):
    def test_break_exits_while_loop_immediately(self):
        env = run(
            "let i = 0; let total = 0; "
            "while (i < 10) { "
            "  i = i + 1; "
            "  if (i == 3) { break; } "
            "  total = total + i; "
            "}"
        )
        self.assertEqual(env.get("total"), 3)  # only 1 + 2 ran before break
        self.assertEqual(env.get("i"), 3)

    def test_continue_skips_rest_of_while_iteration(self):
        env = run(
            "let i = 0; let total = 0; "
            "while (i < 5) { "
            "  i = i + 1; "
            "  if (i == 3) { continue; } "
            "  total = total + i; "
            "}"
        )
        self.assertEqual(env.get("total"), 12)  # 1 + 2 + 4 + 5, 3 skipped
        self.assertEqual(env.get("i"), 5)

    def test_break_exits_for_loop_immediately(self):
        env = run(
            "let total = 0; "
            "for x in [1, 2, 3, 4, 5] { "
            "  if (x == 3) { break; } "
            "  total = total + x; "
            "}"
        )
        self.assertEqual(env.get("total"), 3)  # only 1 + 2 ran before break

    def test_continue_skips_rest_of_for_iteration(self):
        env = run(
            "let total = 0; "
            "for x in [1, 2, 3, 4, 5] { "
            "  if (x == 3) { continue; } "
            "  total = total + x; "
            "}"
        )
        self.assertEqual(env.get("total"), 12)  # 1 + 2 + 4 + 5, 3 skipped

    def test_break_inside_nested_function_does_not_escape_outer_loop(self):
        # Regression test: return already threads through nested calls via
        # `_ReturnSignal`; break/continue must not accidentally do the same
        # and unwind past a function-call boundary. A break inside a
        # function's own loop must only stop that loop, even when the
        # function is declared and called from inside another loop.
        env = run(
            "let outer_iterations = 0; "
            "let inner_sum = 0; "
            "for i in [1, 2, 3] { "
            "  fn inner_loop() { "
            "    let sum = 0; "
            "    for j in [1, 2, 3] { "
            "      if (j == 2) { break; } "
            "      sum = sum + j; "
            "    } "
            "    return sum; "
            "  } "
            "  inner_sum = inner_sum + inner_loop(); "
            "  outer_iterations = outer_iterations + 1; "
            "}"
        )
        self.assertEqual(env.get("outer_iterations"), 3)
        self.assertEqual(env.get("inner_sum"), 3)  # 1 (before break) x 3 calls


class TestLabeledBreakContinue(unittest.TestCase):
    def _run_with_builtins(self, source: str) -> Environment:
        from cinder.builtins import create_global_environment

        return run(source, create_global_environment())

    def test_continue_outer_skips_rest_of_outer_iteration(self):
        env = self._run_with_builtins(
            "let log = []; "
            "outer: for (let i = 0; i < 3; i++) { "
            "  for (let j = 0; j < 3; j++) { "
            "    if (j == 1) { continue outer; } "
            "    push(log, [i, j]); "
            "  } "
            "}"
        )
        self.assertEqual(env.get("log"), [[0, 0], [1, 0], [2, 0]])

    def test_break_outer_stops_the_entire_nested_structure(self):
        env = self._run_with_builtins(
            "let log = []; "
            "outer: for (let i = 0; i < 3; i++) { "
            "  for (let j = 0; j < 3; j++) { "
            "    if (j == 1) { break outer; } "
            "    push(log, [i, j]); "
            "  } "
            "}"
        )
        self.assertEqual(env.get("log"), [[0, 0]])

    def test_unlabeled_break_continue_inside_labeled_loop_still_target_innermost(self):
        # Regression: a label on the outer loop must not change the default
        # target of a bare, unlabeled break/continue in the inner loop.
        env = self._run_with_builtins(
            "let log = []; "
            "outer: for (let i = 0; i < 2; i++) { "
            "  for (let j = 0; j < 3; j++) { "
            "    if (j == 1) { break; } "
            "    push(log, [i, j]); "
            "  } "
            "}"
        )
        self.assertEqual(env.get("log"), [[0, 0], [1, 0]])

    def test_labeled_break_on_while_loop(self):
        env = self._run_with_builtins(
            "let log = []; let i = 0; "
            "lbl: while (i < 5) { "
            "  i = i + 1; "
            "  if (i == 3) { break lbl; } "
            "  push(log, i); "
            "}"
        )
        self.assertEqual(env.get("log"), [1, 2])

    def test_labeled_break_on_do_while_loop(self):
        env = self._run_with_builtins(
            "let log = []; let i = 0; "
            "lbl: do { "
            "  i = i + 1; "
            "  if (i == 3) { break lbl; } "
            "  push(log, i); "
            "} while (i < 5);"
        )
        self.assertEqual(env.get("log"), [1, 2])

    def test_labeled_break_on_foreach_for_loop(self):
        env = self._run_with_builtins(
            "let log = []; "
            "lbl: for x in [1, 2, 3, 4] { "
            "  if (x == 3) { break lbl; } "
            "  push(log, x); "
            "}"
        )
        self.assertEqual(env.get("log"), [1, 2])

    def test_labeled_break_on_c_style_for_loop(self):
        env = self._run_with_builtins(
            "let log = []; "
            "lbl: for (let i = 0; i < 5; i++) { "
            "  if (i == 2) { break lbl; } "
            "  push(log, i); "
            "}"
        )
        self.assertEqual(env.get("log"), [0, 1])

    def test_break_nonexistent_label_is_a_parse_error(self):
        with self.assertRaises(ParseError):
            run("while (true) { break nonexistent; }")

    def test_break_and_continue_outside_loop_still_raise_parse_error(self):
        # Regression: labels must not weaken the existing "outside any loop"
        # check for plain, unlabeled break/continue.
        with self.assertRaises(ParseError):
            run("break;")
        with self.assertRaises(ParseError):
            run("continue;")


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

    def test_anonymous_function_bound_with_let(self):
        env = run("let double = fn(n) { return n * 2; }; let result = double(21);")
        self.assertEqual(env.get("result"), 42)

    def test_anonymous_function_called_immediately(self):
        env = run("let result = fn(n) { return n + 1; }(41);")
        self.assertEqual(env.get("result"), 42)

    def test_anonymous_function_closes_over_outer_variable(self):
        env = run(
            "fn make_adder(x) { return fn(y) { return x + y; }; } "
            "let add5 = make_adder(5); "
            "let result = add5(10);"
        )
        self.assertEqual(env.get("result"), 15)

    def test_direct_runtime_error_has_empty_frames(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('1 + "a";')
        self.assertEqual(ctx.exception.frames, [])

    def test_single_call_frame_records_function_name(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f() { return 1 + "a"; } f();')
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["f"])

    def test_two_level_call_frames_innermost_first(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                "fn a() { b(); } "
                'fn b() { return 1 + "a"; } '
                "a();"
            )
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["b", "a"])

    def test_recursive_call_frames_one_per_active_call(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                "fn rec(n) { "
                '  if (n <= 0) { return 1 + "a"; } '
                "  return rec(n - 1); "
                "} "
                "rec(3);"
            )
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["rec", "rec", "rec", "rec"])

    def test_error_inside_builtin_callback_records_frame(self):
        from cinder.builtins import create_global_environment

        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                'fn bad(x) { return x + "a"; } '
                "map([1, 2], bad);",
                create_global_environment(),
            )
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["bad"])


class TestDefaultParameters(unittest.TestCase):
    def test_default_used_when_argument_omitted(self):
        env = run(
            'fn greet(name, greeting = "hi") { return greeting + " " + name; } '
            'let result = greet("Bo");'
        )
        self.assertEqual(env.get("result"), "hi Bo")

    def test_default_overridden_when_argument_supplied(self):
        env = run(
            'fn greet(name, greeting = "hi") { return greeting + " " + name; } '
            'let result = greet("Bo", "hey");'
        )
        self.assertEqual(env.get("result"), "hey Bo")

    def test_later_default_sees_earlier_bound_parameter(self):
        env = run(
            "fn f(a, b = a + 1) { return b; } let result = f(5);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_too_few_arguments_raises_with_range_message(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a, b = 1) { return a; } f();')
        self.assertIn("expects at least 1 argument(s), got 0", str(ctx.exception))

    def test_too_many_arguments_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('fn f(a, b = 1) { return a; } f(1, 2, 3);')

    def test_non_default_param_after_default_is_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            run("fn f(a = 1, b) { }")

    def test_default_expression_reevaluated_each_call_not_cached(self):
        env = run(
            "let counter = 0; "
            "fn f(a = counter) { counter += 1; return a; } "
            "let first = f(); "
            "let second = f();"
        )
        self.assertEqual(env.get("first"), 0)
        self.assertEqual(env.get("second"), 1)

    def test_anonymous_function_supports_default_params(self):
        env = run(
            "let f = fn(a, b = 2) { return a + b; }; "
            "let result = f(1);"
        )
        self.assertEqual(env.get("result"), 3)

    def test_anonymous_function_default_overridden(self):
        env = run(
            "let f = fn(a, b = 2) { return a + b; }; "
            "let result = f(1, 10);"
        )
        self.assertEqual(env.get("result"), 11)

    def test_error_in_default_expression_records_calling_frame(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                "fn g() { return 1 + \"a\"; } "
                "fn f(a = g()) { return a; } "
                "f();"
            )
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["g", "f"])


class TestRestParameters(unittest.TestCase):
    def test_rest_param_collects_extra_arguments(self):
        env = run(
            "fn f(a, ...rest) { return rest; } let result = f(1, 2, 3);"
        )
        self.assertEqual(env.get("result"), [2, 3])

    def test_rest_param_empty_when_no_extra_arguments(self):
        env = run("fn f(a, ...rest) { return rest; } let result = f(1);")
        self.assertEqual(env.get("result"), [])

    def test_rest_param_with_no_named_params(self):
        env = run("fn f(...rest) { return rest; } let result = f(1, 2, 3);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_rest_param_combined_with_default_one_argument(self):
        env = run(
            "fn f(a, b = 1, ...rest) { return [a, b, rest]; } "
            "let result = f(10);"
        )
        self.assertEqual(env.get("result"), [10, 1, []])

    def test_rest_param_combined_with_default_two_arguments(self):
        env = run(
            "fn f(a, b = 1, ...rest) { return [a, b, rest]; } "
            "let result = f(10, 20);"
        )
        self.assertEqual(env.get("result"), [10, 20, []])

    def test_rest_param_combined_with_default_four_arguments(self):
        env = run(
            "fn f(a, b = 1, ...rest) { return [a, b, rest]; } "
            "let result = f(10, 20, 30, 40);"
        )
        self.assertEqual(env.get("result"), [10, 20, [30, 40]])

    def test_rest_param_works_for_anonymous_functions(self):
        env = run(
            "let f = fn(a, ...rest) { return rest; }; "
            "let result = f(1, 2, 3);"
        )
        self.assertEqual(env.get("result"), [2, 3])

    def test_missing_required_argument_still_raises_with_rest_param(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, ...rest) { return rest; } f();")
        self.assertIn("expects at least 1 argument(s), got 0", str(ctx.exception))


class TestSpreadCallArguments(unittest.TestCase):
    def test_spread_all_arguments(self):
        env = run(
            "fn f(a, b, c) { return a + b + c; } "
            "let result = f(...[1, 2, 3]);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_spread_last(self):
        env = run(
            "fn f(a, b, c) { return a + b + c; } "
            "let result = f(1, ...[2, 3]);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_spread_first(self):
        env = run(
            "fn f(a, b, c) { return a + b + c; } "
            "let result = f(...[1, 2], 3);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_multiple_spreads_with_rest_param(self):
        env = run(
            "fn g(...all) { return all; } "
            "let result = g(...[1, 2], ...[3, 4]);"
        )
        self.assertEqual(env.get("result"), [1, 2, 3, 4])

    def test_spreading_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a) { return a; } f(...5);")
        self.assertEqual(ctx.exception.line, 1)
        self.assertIn("cannot spread", str(ctx.exception))
        self.assertIn("a function call", str(ctx.exception))

    def test_spread_wrong_argument_count_hits_arity_check(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, b, c) { return a + b + c; } f(...[1]);")
        self.assertIn("expects 3 argument(s), got 1", str(ctx.exception))


class TestListsAndMaps(unittest.TestCase):
    def test_list_literal(self):
        self.assertEqual(evaluate("[1, 2, 3]"), [1, 2, 3])

    def test_empty_list_literal(self):
        self.assertEqual(evaluate("[]"), [])

    def test_list_literal_with_spread(self):
        self.assertEqual(evaluate("[...[1, 2], 3]"), [1, 2, 3])

    def test_list_literal_multiple_spreads(self):
        self.assertEqual(evaluate("[0, ...[1, 2], 3, ...[4, 5]]"), [0, 1, 2, 3, 4, 5])

    def test_spread_of_empty_list(self):
        self.assertEqual(evaluate("[...[]]"), [])

    def test_spreading_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("[...5]")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 2)

    def test_map_literal(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2}'), {"a": 1, "b": 2})

    def test_empty_map_literal(self):
        self.assertEqual(evaluate("{}"), {})

    def test_map_literal_with_spread(self):
        self.assertEqual(evaluate('{"a": 1, ...{"b": 2}}'), {"a": 1, "b": 2})

    def test_map_literal_spread_then_explicit_key_overrides(self):
        self.assertEqual(evaluate('{...{"a": 1}, "a": 2}'), {"a": 2})

    def test_map_literal_later_spread_overrides_earlier_key_by_key(self):
        self.assertEqual(
            evaluate('{...{"a": 1}, ...{"a": 2, "b": 3}}'), {"a": 2, "b": 3}
        )

    def test_map_literal_spread_of_empty_map(self):
        self.assertEqual(evaluate("{...{}}"), {})

    def test_map_literal_spreading_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("{...[1, 2]}")
        self.assertIn("cannot spread", str(ctx.exception))
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 2)

    def test_map_literal_spreading_number_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("{...5}")
        self.assertIn("cannot spread", str(ctx.exception))

    def test_map_literal_mixed_spreads_and_keys_strict_last_write_wins(self):
        self.assertEqual(
            evaluate('{"x": 0, ...{"a": 1}, "y": 2, ...{"a": 3}}'),
            {"x": 0, "a": 3, "y": 2},
        )

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

    def test_list_negative_index(self):
        self.assertEqual(evaluate("[1, 2, 3][-1]"), 3)
        self.assertEqual(evaluate("[1, 2, 3][-3]"), 1)

    def test_list_negative_index_out_of_range_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1, 2, 3][-4]")

    def test_list_negative_index_assign(self):
        env = run("let xs = [1, 2, 3]; xs[-1] = 9;")
        self.assertEqual(env.get("xs"), [1, 2, 9])

    def test_map_missing_key_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('{"a": 1}["missing"]')

    def test_dot_access_get(self):
        self.assertEqual(evaluate('{"a": 1}.a'), 1)

    def test_dot_access_chained_nested_maps(self):
        self.assertEqual(evaluate('{"nested": {"b": 2}}.nested.b'), 2)

    def test_dot_access_assignment(self):
        env = run('let m = {"a": 1}; m.a = 5;')
        self.assertEqual(env.get("m"), {"a": 5})

    def test_dot_access_bitwise_compound_assign(self):
        env = run("let m = {\"x\": 6}; m.x &= 3;")
        self.assertEqual(env.get("m"), {"x": 2})

    def test_dot_access_increment(self):
        env = run('let m = {"x": 1}; m.x++;')
        self.assertEqual(env.get("m"), {"x": 2})

    def test_dot_access_arithmetic_compound_assign(self):
        env = run('let m = {"a": 1}; m.a += 1;')
        self.assertEqual(env.get("m"), {"a": 2})

    def test_dot_access_missing_key_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('{"a": 1}.b')

    def test_dot_access_on_list_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1, 2, 3].foo")

    def test_dot_access_calls_map_value(self):
        self.assertEqual(
            evaluate('{"greet": fn(name) { return "hi " + name; }}.greet("Ada")'),
            "hi Ada",
        )

    def test_dot_access_before_keyword_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run('let m = {"if": 1}; m.if;')

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

    def test_string_negative_index(self):
        self.assertEqual(evaluate('"hello"[-1]'), "o")
        self.assertEqual(evaluate('"hello"[-5]'), "h")

    def test_string_negative_index_out_of_range_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"hello"[-6]')

    def test_string_non_int_index_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('"hello"["a"]')

    def test_string_index_assign_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            run('let s = "hi"; s[0] = "y";')


class TestSlicing(unittest.TestCase):
    def test_list_slice_both_bounds(self):
        self.assertEqual(evaluate("[1, 2, 3, 4, 5][1:3]"), [2, 3])

    def test_string_slice_both_bounds(self):
        self.assertEqual(evaluate('"hello"[1:3]'), "el")

    def test_slice_missing_start(self):
        self.assertEqual(evaluate("[1, 2, 3][:2]"), [1, 2])

    def test_slice_missing_end(self):
        self.assertEqual(evaluate("[1, 2, 3][1:]"), [2, 3])

    def test_slice_missing_both_returns_new_list(self):
        env = run("let xs = [1, 2, 3]; let ys = xs[:];")
        xs, ys = env.get("xs"), env.get("ys")
        self.assertEqual(ys, [1, 2, 3])
        self.assertIsNot(xs, ys)

    def test_slice_negative_start_normalizes(self):
        self.assertEqual(evaluate("[1, 2, 3][-2:]"), [2, 3])

    def test_slice_out_of_range_end_clamps(self):
        self.assertEqual(evaluate("[1, 2, 3][0:100]"), [1, 2, 3])

    def test_plain_index_still_returns_element(self):
        self.assertEqual(evaluate("[1, 2, 3][1]"), 2)

    def test_slicing_map_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('{"a": 1}[0:1]')

    def test_slice_non_int_bound_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('[1, 2, 3]["a":2]')

    def test_slice_assignment_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            run("[1, 2, 3][1:2] = [9];")

    def test_slice_step_skips_elements(self):
        self.assertEqual(evaluate("[1, 2, 3, 4, 5][::2]"), [1, 3, 5])

    def test_slice_negative_step_reverses_list(self):
        self.assertEqual(evaluate("[1, 2, 3, 4, 5][::-1]"), [5, 4, 3, 2, 1])

    def test_slice_all_three_parts(self):
        self.assertEqual(evaluate("[1, 2, 3, 4, 5][1:4:2]"), [2, 4])

    def test_slice_step_on_string(self):
        self.assertEqual(evaluate('"abcdef"[::2]'), "ace")

    def test_slice_negative_step_reverses_string(self):
        self.assertEqual(evaluate('"abcdef"[::-1]'), "fedcba")

    def test_slice_explicit_default_step_matches_omitted(self):
        self.assertEqual(
            evaluate("[1, 2, 3, 4, 5][::1]"), evaluate("[1, 2, 3, 4, 5][:]")
        )

    def test_slice_omitted_step_two_colon_form_unaffected(self):
        self.assertEqual(evaluate("[1, 2, 3][1:3]"), [2, 3])

    def test_slice_zero_step_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[1, 2, 3][::0]")

    def test_slice_non_int_step_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('[1, 2, 3][::"a"]')

    def test_slice_step_on_non_sliceable_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("5[::2]")

    def test_slice_with_step_assignment_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            run("[1, 2, 3][::2] = [9];")


class TestTryCatch(unittest.TestCase):
    def test_catch_binds_error_message_and_recovers(self):
        env = run("let msg = nil; try { let x = 1 / 0; } catch (e) { msg = e; }")
        self.assertIsInstance(env.get("msg"), str)
        self.assertIn("division by zero", env.get("msg"))

    def test_execution_continues_after_caught_error(self):
        env = run(
            "let after = 0; "
            "try { let x = 1 / 0; } catch (e) {} "
            "after = 1;"
        )
        self.assertEqual(env.get("after"), 1)

    def test_catch_block_does_not_run_when_no_error(self):
        env = run("let ran = 0; try { 1; } catch (e) { ran = 1; }")
        self.assertEqual(env.get("ran"), 0)

    def test_catch_name_not_visible_after_try_catch(self):
        with self.assertRaises(CinderRuntimeError):
            run("try { let x = 1 / 0; } catch (e) {} e;")

    def test_break_inside_try_inside_for_loop_exits_loop(self):
        env = run(
            "let ran = 0; "
            "for x in [1] { try { break; } catch (e) {} ran = 1; }"
        )
        self.assertEqual(env.get("ran"), 0)

    def test_return_inside_try_inside_function_returns_from_function(self):
        env = run(
            "fn f() { try { return 1; } catch (e) { return 2; } return 3; } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_error_raised_inside_catch_block_is_not_re_caught(self):
        with self.assertRaises(CinderRuntimeError):
            run("try { let x = 1 / 0; } catch (e) { let y = 1 / 0; }")

    def test_no_error_when_try_body_succeeds(self):
        env = run("let x = 0; try { x = 1; } catch (e) { x = 2; }")
        self.assertEqual(env.get("x"), 1)

    def test_nested_try_catch(self):
        env = run(
            "let outer = nil; let inner = nil; "
            "try { "
            "  try { let x = 1 / 0; } catch (e) { inner = e; let y = 1 / 0; } "
            "} catch (e) { outer = e; }"
        )
        self.assertIsInstance(env.get("inner"), str)
        self.assertIsInstance(env.get("outer"), str)


class TestTryFinally(unittest.TestCase):
    def _run(self, source: str) -> Environment:
        from cinder.builtins import create_global_environment

        return run(source, create_global_environment())

    def test_finally_runs_after_clean_try(self):
        env = self._run("let log = []; try { push(log, 1); } finally { push(log, 2); } ")
        self.assertEqual(env.get("log"), [1, 2])

    def test_finally_runs_after_catch_handles_error(self):
        env = self._run(
            "let log = []; "
            'try { push(log, 1); assert(false, "x"); } '
            "catch (e) { push(log, 2); } "
            "finally { push(log, 3); }"
        )
        self.assertEqual(env.get("log"), [1, 2, 3])

    def test_finally_runs_before_function_return(self):
        env = self._run(
            "let log = []; "
            "fn f() { try { return 1; } finally { push(log, 1); } } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)
        self.assertEqual(env.get("log"), [1])

    def test_finally_runs_before_loop_break(self):
        env = self._run(
            "let log = []; "
            "for x in [1, 2] { try { break; } finally { push(log, 1); } } "
        )
        self.assertEqual(env.get("log"), [1])

    def test_finally_runs_before_loop_continue(self):
        env = self._run(
            "let log = []; "
            "for x in [1, 2] { try { continue; } finally { push(log, x); } } "
        )
        self.assertEqual(env.get("log"), [1, 2])

    def test_finally_only_no_catch_clause_is_valid(self):
        env = self._run("let log = []; try { push(log, 1); } finally { push(log, 2); }")
        self.assertEqual(env.get("log"), [1, 2])

    def test_finally_only_still_propagates_uncaught_error(self):
        with self.assertRaises(CinderRuntimeError):
            self._run("let log = []; try { let x = 1 / 0; } finally { push(log, 1); }")

    def test_omitting_finally_behaves_as_before(self):
        env = run("let msg = nil; try { let x = 1 / 0; } catch (e) { msg = e; }")
        self.assertIsInstance(env.get("msg"), str)
        self.assertIn("division by zero", env.get("msg"))


class TestThrowStatement(unittest.TestCase):
    def test_thrown_string_is_caught_and_bound(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                'try { throw "boom"; } catch (e) { print(e); }',
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "boom\n")

    def test_uncaught_throw_raises_with_own_line_and_column(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('throw "boom";')
        self.assertEqual(ctx.exception.message, "boom")
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_throw_non_string_raises_type_error(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("throw 42;")
        self.assertEqual(
            ctx.exception.message, "throw requires a string message, got int"
        )
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_throw_inside_nested_call_reports_call_stack(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                "fn a() { b(); } "
                'fn b() { throw "boom"; } '
                "a();"
            )
        names = [frame[0] for frame in ctx.exception.frames]
        self.assertEqual(names, ["b", "a"])

    def test_finally_runs_before_throw_propagates_uncaught(self):
        from cinder.builtins import create_global_environment

        env = create_global_environment()
        with self.assertRaises(CinderRuntimeError):
            run(
                'let log = []; try { throw "x"; } finally { push(log, 1); }',
                env,
            )
        self.assertEqual(env.get("log"), [1])

    def test_throw_without_expression_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run("throw;")


class TestSwitchStatement(unittest.TestCase):
    def test_first_match_wins_no_fallthrough(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run(
                'switch (2) { case 1: { print("one"); } '
                'case 2: { print("two"); } '
                'default: { print("other"); } }',
                create_global_environment(),
            )
        self.assertEqual(stdout.getvalue(), "two\n")

    def test_no_match_runs_default(self):
        env = run(
            'let result = "unset"; '
            'switch (99) { case 1: { result = "one"; } default: { result = "other"; } }'
        )
        self.assertEqual(env.get("result"), "other")

    def test_no_match_no_default_is_noop(self):
        env = run('let result = "unset"; switch (99) { case 1: { result = "one"; } }')
        self.assertEqual(env.get("result"), "unset")

    def test_case_values_compare_via_values_equal_bool_vs_int(self):
        env = run(
            'let result = "unset"; '
            "switch (true) { case 1: { result = \"int\"; } case true: { result = \"bool\"; } }"
        )
        self.assertEqual(env.get("result"), "bool")

    def test_case_int_does_not_match_bool_scrutinee(self):
        env = run(
            'let result = "unset"; '
            "switch (1) { case true: { result = \"bool\"; } case 1: { result = \"int\"; } }"
        )
        self.assertEqual(env.get("result"), "int")

    def test_let_inside_case_does_not_leak_outside(self):
        with self.assertRaises(KeyError):
            run("switch (1) { case 1: { let a = 1; } }").get("a")

    def test_let_inside_one_case_not_visible_in_another_case(self):
        with self.assertRaises(CinderRuntimeError):
            run(
                "switch (2) { case 1: { let a = 1; } "
                "case 2: { a = 2; } }"
            )

    def test_break_inside_switch_inside_while_still_breaks_loop(self):
        env = run(
            "let i = 0; let ran_after = 0; "
            "while (i < 3) { "
            "  i = i + 1; "
            "  switch (i) { case 2: { break; } } "
            "  ran_after = i; "
            "}"
        )
        self.assertEqual(env.get("i"), 2)
        self.assertEqual(env.get("ran_after"), 1)

    def test_scrutinee_evaluated_exactly_once(self):
        env = run(
            "let calls = 0; "
            "fn scrutinee() { calls = calls + 1; return 2; } "
            'let result = "unset"; '
            'switch (scrutinee()) { case 1: { result = "one"; } case 2: { result = "two"; } }'
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("result"), "two")

    def test_case_values_after_match_are_not_evaluated(self):
        env = run(
            "let calls = 0; "
            "fn side_effect() { calls = calls + 1; return 99; } "
            "switch (1) { case 1: { } case side_effect(): { } }"
        )
        self.assertEqual(env.get("calls"), 0)

    def test_multi_value_case_matches_any_listed_value(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run(
                'switch (2) { case 1, 2, 3: { print("small"); } '
                'default: { print("big"); } }',
                create_global_environment(),
            )
        self.assertEqual(stdout.getvalue(), "small\n")

    def test_multi_value_case_falls_through_to_default_on_no_match(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run(
                'switch (5) { case 1, 2, 3: { print("small"); } '
                'default: { print("big"); } }',
                create_global_environment(),
            )
        self.assertEqual(stdout.getvalue(), "big\n")

    def test_multi_value_case_short_circuits_on_first_match(self):
        env = run(
            "let g_calls = 0; "
            "fn f() { return 1; } "
            "fn g() { g_calls = g_calls + 1; return 2; } "
            "switch (1) { case f(), g(): { } }"
        )
        self.assertEqual(env.get("g_calls"), 0)

    def test_multi_value_case_values_can_mix_literal_and_computed(self):
        env = run(
            "let x = 2; let result = \"unset\"; "
            'switch (3) { case 1, x + 1, "three": { result = "matched"; } }'
        )
        self.assertEqual(env.get("result"), "matched")

    def test_single_value_case_with_shared_body_runs_on_either_value(self):
        results = []
        for scrutinee in (1, 2):
            env = run(
                f'let result = "unset"; '
                f'switch ({scrutinee}) {{ case 1, 2: {{ result = "matched"; }} }}'
            )
            results.append(env.get("result"))
        self.assertEqual(results, ["matched", "matched"])


if __name__ == "__main__":
    unittest.main()
