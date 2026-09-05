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

    def test_list_plus_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('[1, 2] + "a"')
        self.assertIn("unsupported operand types for '+': list and string", str(ctx.exception))

    def test_list_plus_int_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("[1, 2] + 3")
        self.assertIn("unsupported operand types for '+': list and int", str(ctx.exception))

    def test_list_plus_map_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('[1, 2] + {"a": 1}')
        self.assertIn("unsupported operand types for '+': list and map", str(ctx.exception))


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

    def test_unicode_escape_alongside_placeholder(self):
        env = run('let x = 5; let msg = "\\u00e9: ${x}";')
        self.assertEqual(env.get("msg"), chr(0xE9) + ": 5")

    def test_nested_list_result_stringifies_without_extra_flattening(self):
        self.assertEqual(evaluate('"${[[1, 2]]}"'), "[[1, 2]]")

    def test_runtime_error_in_placeholder_reports_placeholder_position(self):
        # Not the string literal's opening-quote position (1, 1).
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('"${1/0}"')
        self.assertEqual((ctx.exception.line, ctx.exception.column), (1, 5))


class TestRawStringLiterals(unittest.TestCase):
    def test_escapes_not_processed(self):
        self.assertEqual(evaluate(r'r"a\nb"'), "a\\nb")

    def test_single_quoted_windows_path(self):
        self.assertEqual(evaluate(r"r'C:\Users\name'"), r"C:\Users\name")

    def test_interpolation_not_processed(self):
        self.assertEqual(evaluate('r"${1 + 2}"'), "${1 + 2}")

    def test_empty_raw_string(self):
        self.assertEqual(evaluate('r""'), "")

    def test_bare_identifier_r_unaffected(self):
        env = run("let r = 5; let result = r + 1;")
        self.assertEqual(env.get("result"), 6)

    def test_ordinary_string_escapes_still_processed(self):
        self.assertEqual(evaluate(r'"a\nb"'), "a\nb")


class TestTripleQuotedStringLiterals(unittest.TestCase):
    def test_embedded_double_quotes_unescaped(self):
        self.assertEqual(
            evaluate('"""she said "hi" to "me" today"""'),
            'she said "hi" to "me" today',
        )

    def test_embedded_mixed_quotes_unescaped(self):
        self.assertEqual(evaluate("'''it's a \"quoted\" word'''"), 'it\'s a "quoted" word')

    def test_interpolation_still_works(self):
        env = run('let x = 5; let msg = """value: ${x}!""";')
        self.assertEqual(env.get("msg"), "value: 5!")

    def test_escapes_still_work(self):
        self.assertEqual(evaluate(r'"""a\tb"""'), "a\tb")

    def test_empty_triple_quoted_string(self):
        self.assertEqual(evaluate('""""""'), "")


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


class TestListConcatenation(unittest.TestCase):
    def test_two_lists(self):
        self.assertEqual(evaluate("[1, 2] + [3, 4]"), [1, 2, 3, 4])

    def test_empty_left(self):
        self.assertEqual(evaluate("[] + [1]"), [1])

    def test_empty_right(self):
        self.assertEqual(evaluate("[1] + []"), [1])

    def test_both_empty(self):
        self.assertEqual(evaluate("[] + []"), [])

    def test_does_not_mutate_inputs(self):
        env = run("let a = [1, 2]; let b = [3, 4]; let c = a + b;")
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("b"), [3, 4])
        self.assertEqual(env.get("c"), [1, 2, 3, 4])

    def test_compound_assignment(self):
        env = run("let xs = [1, 2]; xs += [3, 4];")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])

    def test_left_associative(self):
        env = run("let xs = [1]; xs = xs + [2] + [3];")
        self.assertEqual(env.get("xs"), [1, 2, 3])


class TestMapConcatenation(unittest.TestCase):
    def test_two_maps(self):
        self.assertEqual(evaluate('{"a": 1} + {"b": 2}'), {"a": 1, "b": 2})

    def test_right_wins_on_conflict(self):
        self.assertEqual(evaluate('{"a": 1} + {"a": 2}'), {"a": 2})

    def test_empty_left(self):
        self.assertEqual(evaluate('{} + {"a": 1}'), {"a": 1})

    def test_empty_right(self):
        self.assertEqual(evaluate('{"a": 1} + {}'), {"a": 1})

    def test_key_order_left_then_right_only_keys(self):
        result = evaluate('{"a": 1, "b": 2} + {"b": 3, "c": 4}')
        self.assertEqual(list(result.keys()), ["a", "b", "c"])

    def test_does_not_mutate_inputs(self):
        env = run('let a = {"a": 1}; let b = {"b": 2}; let c = a + b;')
        self.assertEqual(env.get("a"), {"a": 1})
        self.assertEqual(env.get("b"), {"b": 2})
        self.assertEqual(env.get("c"), {"a": 1, "b": 2})

    def test_compound_assignment_on_identifier(self):
        env = run('let m = {"a": 1}; m += {"b": 2};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_compound_assignment_on_index_target(self):
        env = run('let xs = [{"a": 1}]; xs[0] += {"b": 2};')
        self.assertEqual(env.get("xs"), [{"a": 1, "b": 2}])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"m": {"a": 1}}; obj.m += {"b": 2};')
        self.assertEqual(env.get("obj"), {"m": {"a": 1, "b": 2}})

    def test_left_associative(self):
        env = run('let m = {"a": 1} + {"b": 2} + {"c": 3};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2, "c": 3})

    def test_map_plus_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\+': map and list"
        ):
            evaluate('{"a": 1} + [1, 2]')

    def test_map_plus_string_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\+': map and string"
        ):
            evaluate('{"a": 1} + "x"')

    def test_map_plus_number_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\+': map and int"
        ):
            evaluate('{"a": 1} + 1')


class TestMapDifference(unittest.TestCase):
    def test_removes_key_present_in_right(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} - {"a": 1}'), {"b": 2})

    def test_right_value_is_ignored(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} - {"a": 99}'), {"b": 2})

    def test_empty_right_is_noop(self):
        self.assertEqual(evaluate('{"a": 1} - {}'), {"a": 1})

    def test_empty_left(self):
        self.assertEqual(evaluate('{} - {"a": 1}'), {})

    def test_removing_every_key_empties_map(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} - {"a": 1, "b": 2}'), {}
        )

    def test_key_not_present_has_no_effect(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} - {"c": 3}'), {"a": 1, "b": 2}
        )

    def test_does_not_mutate_inputs(self):
        env = run('let a = {"a": 1, "b": 2}; let c = a - {"a": 1};')
        self.assertEqual(env.get("a"), {"a": 1, "b": 2})
        self.assertEqual(env.get("c"), {"b": 2})

    def test_left_associative(self):
        env = run('let m = {"a": 1, "b": 2, "c": 3} - {"a": 1} - {"b": 2};')
        self.assertEqual(env.get("m"), {"c": 3})

    def test_compound_assignment_on_identifier(self):
        env = run('let m = {"a": 1, "b": 2}; m -= {"a": 1};')
        self.assertEqual(env.get("m"), {"b": 2})

    def test_compound_assignment_on_index_target(self):
        env = run('let xs = [{"a": 1, "b": 2}]; xs[0] -= {"a": 1};')
        self.assertEqual(env.get("xs"), [{"b": 2}])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"m": {"a": 1, "b": 2}}; obj.m -= {"a": 1};')
        self.assertEqual(env.get("obj"), {"m": {"b": 2}})

    def test_map_minus_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '-': map and list"
        ):
            evaluate('{"a": 1} - [1, 2]')

    def test_map_minus_string_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '-': map and string"
        ):
            evaluate('{"a": 1} - "x"')

    def test_list_minus_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '-': list and map"
        ):
            evaluate('[1, 2] - {"a": 1}')


class TestListDifference(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(evaluate("[1, 2, 3] - [2]"), [1, 3])

    def test_left_side_is_deduped(self):
        self.assertEqual(evaluate("[1, 2, 2, 3] - [2]"), [1, 3])

    def test_empty_right_is_noop(self):
        self.assertEqual(evaluate("[1, 2, 3] - []"), [1, 2, 3])

    def test_empty_left(self):
        self.assertEqual(evaluate("[] - [1, 2]"), [])

    def test_removing_every_element_empties_list(self):
        self.assertEqual(evaluate("[1, 2] - [1, 2]"), [])

    def test_no_overlap_has_no_effect(self):
        self.assertEqual(evaluate("[1, 2] - [3, 4]"), [1, 2])

    def test_does_not_mutate_inputs(self):
        env = run("let a = [1, 2]; let c = a - [1];")
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("c"), [2])

    def test_left_associative(self):
        env = run("let xs = [1, 2, 3] - [1] - [2];")
        self.assertEqual(env.get("xs"), [3])

    def test_compound_assignment_on_identifier(self):
        env = run("let xs = [1, 2]; xs -= [1];")
        self.assertEqual(env.get("xs"), [2])

    def test_compound_assignment_on_index_target(self):
        env = run("let xs = [[1, 2]]; xs[0] -= [1];")
        self.assertEqual(env.get("xs"), [[2]])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"l": [1, 2]}; obj.l -= [1];')
        self.assertEqual(env.get("obj"), {"l": [2]})

    def test_uses_values_equal_not_native_equality(self):
        self.assertEqual(evaluate("[1, true, 2] - [true]"), [1, 2])

    def test_list_minus_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '-': list and map"
        ):
            evaluate('[1, 2] - {"a": 1}')

    def test_map_minus_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '-': map and list"
        ):
            evaluate('{"a": 1} - [1, 2]')


class TestListIntersection(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(evaluate("[1, 2, 3] & [2, 3, 4]"), [2, 3])

    def test_left_side_is_deduped(self):
        self.assertEqual(evaluate("[1, 2, 2, 3] & [2]"), [2])

    def test_empty_right_empties_result(self):
        self.assertEqual(evaluate("[1, 2, 3] & []"), [])

    def test_empty_left_empties_result(self):
        self.assertEqual(evaluate("[] & [1, 2]"), [])

    def test_full_overlap_keeps_everything_deduped(self):
        self.assertEqual(evaluate("[1, 2] & [1, 2]"), [1, 2])

    def test_no_overlap(self):
        self.assertEqual(evaluate("[1, 2] & [3, 4]"), [])

    def test_does_not_mutate_inputs(self):
        env = run("let a = [1, 2, 3]; let c = a & [2];")
        self.assertEqual(env.get("a"), [1, 2, 3])
        self.assertEqual(env.get("c"), [2])

    def test_left_associative(self):
        env = run("let xs = [1, 2, 3] & [1, 2] & [2];")
        self.assertEqual(env.get("xs"), [2])

    def test_compound_assignment_on_identifier(self):
        env = run("let xs = [1, 2, 3]; xs &= [2, 3];")
        self.assertEqual(env.get("xs"), [2, 3])

    def test_compound_assignment_on_index_target(self):
        env = run("let xs = [[1, 2, 3]]; xs[0] &= [2, 3];")
        self.assertEqual(env.get("xs"), [[2, 3]])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"l": [1, 2, 3]}; obj.l &= [2, 3];')
        self.assertEqual(env.get("obj"), {"l": [2, 3]})

    def test_uses_values_equal_not_native_equality(self):
        self.assertEqual(evaluate("[1, true, 2] & [true]"), [True])

    def test_int_and_int_still_bitwise_and(self):
        self.assertEqual(evaluate("2 & 3"), 2)

    def test_list_and_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': list and int"
        ):
            evaluate("[1, 2] & 3")

    def test_int_and_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': int and list"
        ):
            evaluate("2 & [1, 2]")

    def test_list_and_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': list and map"
        ):
            evaluate('[1, 2] & {"a": 1}')


class TestListUnion(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(evaluate("[1, 2, 3] | [2, 3, 4]"), [1, 2, 3, 4])

    def test_duplicates_on_either_side_deduped(self):
        self.assertEqual(evaluate("[1, 2, 2, 3] | [2]"), [1, 2, 3])

    def test_empty_right_leaves_left_deduped(self):
        self.assertEqual(evaluate("[1, 2, 3] | []"), [1, 2, 3])

    def test_empty_left_leaves_right_deduped(self):
        self.assertEqual(evaluate("[] | [1, 2]"), [1, 2])

    def test_full_overlap_keeps_everything_deduped(self):
        self.assertEqual(evaluate("[1, 2] | [1, 2]"), [1, 2])

    def test_no_overlap_is_concatenation(self):
        self.assertEqual(evaluate("[1, 2] | [3, 4]"), [1, 2, 3, 4])

    def test_does_not_mutate_inputs(self):
        env = run("let a = [1, 2, 3]; let c = a | [4];")
        self.assertEqual(env.get("a"), [1, 2, 3])
        self.assertEqual(env.get("c"), [1, 2, 3, 4])

    def test_left_associative(self):
        env = run("let xs = [1] | [2] | [1, 3];")
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_compound_assignment_on_identifier(self):
        env = run("let xs = [1, 2]; xs |= [2, 3];")
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_compound_assignment_on_index_target(self):
        env = run("let xs = [[1, 2]]; xs[0] |= [2, 3];")
        self.assertEqual(env.get("xs"), [[1, 2, 3]])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"l": [1, 2]}; obj.l |= [2, 3];')
        self.assertEqual(env.get("obj"), {"l": [1, 2, 3]})

    def test_uses_values_equal_not_native_equality(self):
        self.assertEqual(evaluate("[1, true, 2] | [true, 3]"), [1, True, 2, 3])

    def test_int_or_int_still_bitwise_or(self):
        self.assertEqual(evaluate("2 | 3"), 3)

    def test_list_or_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '|': list and int"
        ):
            evaluate("[1, 2] | 3")

    def test_int_or_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '|': int and list"
        ):
            evaluate("2 | [1, 2]")

    def test_list_or_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '|': list and map"
        ):
            evaluate('[1, 2] | {"a": 1}')


class TestListSymmetricDifference(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(evaluate("[1, 2, 3] ^ [2, 3, 4]"), [1, 4])

    def test_duplicates_on_either_side_deduped(self):
        self.assertEqual(evaluate("[1, 1, 2] ^ [2, 2, 3]"), [1, 3])

    def test_empty_right_leaves_left_deduped(self):
        self.assertEqual(evaluate("[1, 2, 3] ^ []"), [1, 2, 3])

    def test_empty_left_leaves_right_deduped(self):
        self.assertEqual(evaluate("[] ^ [1, 2]"), [1, 2])

    def test_full_overlap_empties_result(self):
        self.assertEqual(evaluate("[1, 2] ^ [1, 2]"), [])

    def test_no_overlap_is_concatenation(self):
        self.assertEqual(evaluate("[1, 2] ^ [3, 4]"), [1, 2, 3, 4])

    def test_does_not_mutate_inputs(self):
        env = run("let a = [1, 2, 3]; let c = a ^ [2, 4];")
        self.assertEqual(env.get("a"), [1, 2, 3])
        self.assertEqual(env.get("c"), [1, 3, 4])

    def test_left_associative(self):
        env = run("let xs = [1, 2] ^ [2, 3] ^ [3, 4];")
        self.assertEqual(env.get("xs"), [1, 4])

    def test_compound_assignment_on_identifier(self):
        env = run("let xs = [1, 2]; xs ^= [2, 3];")
        self.assertEqual(env.get("xs"), [1, 3])

    def test_compound_assignment_on_index_target(self):
        env = run("let xs = [[1, 2]]; xs[0] ^= [2, 3];")
        self.assertEqual(env.get("xs"), [[1, 3]])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"l": [1, 2]}; obj.l ^= [2, 3];')
        self.assertEqual(env.get("obj"), {"l": [1, 3]})

    def test_uses_values_equal_not_native_equality(self):
        self.assertEqual(evaluate("[1, true, 2] ^ [true, 3]"), [1, 2, 3])

    def test_int_xor_int_still_bitwise_xor(self):
        self.assertEqual(evaluate("2 ^ 3"), 1)

    def test_list_xor_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': list and int"
        ):
            evaluate("[1, 2] ^ 3")

    def test_int_xor_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': int and list"
        ):
            evaluate("2 ^ [1, 2]")

    def test_list_xor_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': list and map"
        ):
            evaluate('[1, 2] ^ {"a": 1}')


class TestMapIntersection(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} & {"a": 1, "c": 3}'), {"a": 1}
        )

    def test_right_value_is_ignored(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} & {"a": 99}'), {"a": 1})

    def test_empty_right_empties_result(self):
        self.assertEqual(evaluate('{"a": 1} & {}'), {})

    def test_empty_left_empties_result(self):
        self.assertEqual(evaluate('{} & {"a": 1}'), {})

    def test_full_overlap_keeps_everything(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} & {"a": 1, "b": 2}'), {"a": 1, "b": 2}
        )

    def test_no_shared_keys(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} & {"c": 3}'), {})

    def test_does_not_mutate_inputs(self):
        env = run('let m = {"a": 1, "b": 2}; let c = m & {"a": 1};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})
        self.assertEqual(env.get("c"), {"a": 1})

    def test_left_associative(self):
        env = run(
            'let m = {"a": 1, "b": 2, "c": 3} & {"a": 1, "b": 2} & {"b": 2};'
        )
        self.assertEqual(env.get("m"), {"b": 2})

    def test_compound_assignment_on_identifier(self):
        env = run('let m = {"a": 1, "b": 2}; m &= {"a": 1};')
        self.assertEqual(env.get("m"), {"a": 1})

    def test_compound_assignment_on_index_target(self):
        env = run('let xs = [{"a": 1, "b": 2}]; xs[0] &= {"a": 1};')
        self.assertEqual(env.get("xs"), [{"a": 1}])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"m": {"a": 1, "b": 2}}; obj.m &= {"a": 1};')
        self.assertEqual(env.get("obj"), {"m": {"a": 1}})

    def test_int_and_int_still_bitwise_and(self):
        self.assertEqual(evaluate("2 & 3"), 2)

    def test_list_and_list_still_works(self):
        self.assertEqual(evaluate("[1, 2] & [1]"), [1])

    def test_map_and_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': map and int"
        ):
            evaluate('{"a": 1} & 3')

    def test_int_and_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': int and map"
        ):
            evaluate('3 & {"a": 1}')

    def test_map_and_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '&': map and list"
        ):
            evaluate('{"a": 1} & [1, 2]')


class TestMapUnion(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} | {"a": 99, "c": 3}'),
            {"a": 1, "b": 2, "c": 3},
        )

    def test_empty_right_leaves_left_untouched(self):
        self.assertEqual(evaluate('{"a": 1} | {}'), {"a": 1})

    def test_empty_left_leaves_right_untouched(self):
        self.assertEqual(evaluate('{} | {"a": 1}'), {"a": 1})

    def test_full_overlap_keeps_everything(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} | {"a": 1, "b": 2}'), {"a": 1, "b": 2}
        )

    def test_disjoint_keys_combine(self):
        self.assertEqual(evaluate('{"a": 1} | {"b": 2}'), {"a": 1, "b": 2})

    def test_does_not_mutate_inputs(self):
        env = run('let m = {"a": 1}; let c = m | {"a": 2, "b": 3};')
        self.assertEqual(env.get("m"), {"a": 1})
        self.assertEqual(env.get("c"), {"a": 1, "b": 3})

    def test_left_associative(self):
        env = run(
            'let m = {"a": 1} | {"a": 2, "b": 2} | {"a": 3, "c": 3};'
        )
        self.assertEqual(env.get("m"), {"a": 1, "b": 2, "c": 3})

    def test_compound_assignment_on_identifier(self):
        env = run('let m = {"a": 1}; m |= {"a": 2, "b": 2};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_compound_assignment_on_index_target(self):
        env = run('let xs = [{"a": 1}]; xs[0] |= {"a": 2, "b": 2};')
        self.assertEqual(env.get("xs"), [{"a": 1, "b": 2}])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"m": {"a": 1}}; obj.m |= {"a": 2, "b": 2};')
        self.assertEqual(env.get("obj"), {"m": {"a": 1, "b": 2}})

    def test_int_or_int_still_bitwise_or(self):
        self.assertEqual(evaluate("2 | 3"), 3)

    def test_list_or_list_still_works(self):
        self.assertEqual(evaluate("[1, 2] | [2, 3]"), [1, 2, 3])

    def test_map_or_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\|': map and int"
        ):
            evaluate('{"a": 1} | 3')

    def test_int_or_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\|': int and map"
        ):
            evaluate('2 | {"a": 1}')

    def test_map_or_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\|': map and list"
        ):
            evaluate('{"a": 1} | [1, 2]')


class TestMapSymmetricDifference(unittest.TestCase):
    def test_basic_case(self):
        self.assertEqual(
            evaluate('{"a": 1, "b": 2} ^ {"b": 3, "c": 4}'),
            {"a": 1, "c": 4},
        )

    def test_empty_right_leaves_left_untouched(self):
        self.assertEqual(evaluate('{"a": 1} ^ {}'), {"a": 1})

    def test_empty_left_leaves_right_untouched(self):
        self.assertEqual(evaluate('{} ^ {"a": 1}'), {"a": 1})

    def test_full_overlap_leaves_nothing(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} ^ {"a": 1, "b": 2}'), {})

    def test_disjoint_keys_combine(self):
        self.assertEqual(evaluate('{"a": 1} ^ {"b": 2}'), {"a": 1, "b": 2})

    def test_does_not_mutate_inputs(self):
        env = run('let m = {"a": 1}; let c = m ^ {"a": 2, "b": 3};')
        self.assertEqual(env.get("m"), {"a": 1})
        self.assertEqual(env.get("c"), {"b": 3})

    def test_left_associative(self):
        env = run(
            'let m = {"a": 1} ^ {"a": 2, "b": 2} ^ {"b": 3, "c": 3};'
        )
        self.assertEqual(env.get("m"), {"c": 3})

    def test_compound_assignment_on_identifier(self):
        env = run('let m = {"a": 1}; m ^= {"a": 2, "b": 2};')
        self.assertEqual(env.get("m"), {"b": 2})

    def test_compound_assignment_on_index_target(self):
        env = run('let xs = [{"a": 1}]; xs[0] ^= {"a": 2, "b": 2};')
        self.assertEqual(env.get("xs"), [{"b": 2}])

    def test_compound_assignment_on_dot_target(self):
        env = run('let obj = {"m": {"a": 1}}; obj.m ^= {"a": 2, "b": 2};')
        self.assertEqual(env.get("obj"), {"m": {"b": 2}})

    def test_int_xor_int_still_bitwise_xor(self):
        self.assertEqual(evaluate("2 ^ 3"), 1)

    def test_map_xor_int_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': map and int"
        ):
            evaluate('{"a": 1} ^ 3')

    def test_int_xor_map_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': int and map"
        ):
            evaluate('2 ^ {"a": 1}')

    def test_map_xor_list_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "unsupported operand types for '\\^': map and list"
        ):
            evaluate('{"a": 1} ^ [1, 2]')


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

    def test_list_ordering_first_differing_element(self):
        self.assertEqual(evaluate("[1, 2] < [1, 3]"), True)
        self.assertEqual(evaluate("[1, 3] < [1, 2]"), False)

    def test_list_ordering_prefix_is_lesser(self):
        self.assertEqual(evaluate("[1, 2] < [1, 2, 3]"), True)
        self.assertEqual(evaluate("[1, 2, 3] < [1, 2]"), False)

    def test_list_ordering_empty_lists(self):
        self.assertEqual(evaluate("[] < [1]"), True)
        self.assertEqual(evaluate("[] < []"), False)

    def test_list_ordering_inclusive_operators_on_equal_lists(self):
        self.assertEqual(evaluate("[1, 2] <= [1, 2]"), True)
        self.assertEqual(evaluate("[1, 2] >= [1, 2]"), True)

    def test_list_ordering_nested_strings(self):
        self.assertEqual(evaluate('["a", "b"] < ["a", "c"]'), True)

    def test_list_ordering_nested_lists(self):
        self.assertEqual(evaluate("[[1, 2]] < [[1, 3]]"), True)

    def test_list_ordering_mismatched_element_types_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('[1, "a"] < [1, 2]')

    def test_list_vs_number_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("1 < [1, 2]")

    def test_map_ordering_same_key_lesser_value(self):
        self.assertEqual(evaluate('{"a": 1} < {"a": 2}'), True)

    def test_map_ordering_keys_differ_first(self):
        self.assertEqual(evaluate('{"a": 1} < {"b": 0}'), True)

    def test_map_ordering_first_differing_pair_before_length(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} < {"a": 2}'), True)

    def test_map_ordering_empty_map_is_prefix(self):
        self.assertEqual(evaluate('{} < {"a": 1}'), True)

    def test_map_ordering_equal_maps_different_insertion_order(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} <= {"b": 2, "a": 1}'), True)
        self.assertEqual(evaluate('{"a": 1, "b": 2} >= {"b": 2, "a": 1}'), True)
        self.assertEqual(evaluate('{"a": 1, "b": 2} < {"b": 2, "a": 1}'), False)

    def test_map_ordering_incomparable_values_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: map keys or values "
            r"are not comparable",
        ):
            evaluate('{"a": 1} < {"a": "x"}')

    def test_map_ordering_incomparable_keys_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: map keys or values "
            r"are not comparable",
        ):
            evaluate('{1: "a"} < {"b": 2}')

    def test_map_vs_list_still_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: map and list",
        ):
            evaluate('{"a": 1} < [1]')

    def test_map_vs_number_still_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: map and int",
        ):
            evaluate('{"a": 1} < 1')

    def test_list_of_maps_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('[{"a": 1}] < [{"a": 2}]')

    def test_map_ordering_chained_comparison(self):
        self.assertEqual(evaluate('{"a": 1} < {"a": 2} < {"a": 3}'), True)


class TestSpaceshipOperator(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(evaluate("1 <=> 2"), -1)
        self.assertEqual(evaluate("2 <=> 2"), 0)
        self.assertEqual(evaluate("3 <=> 2"), 1)

    def test_strings(self):
        self.assertEqual(evaluate('"a" <=> "b"'), -1)
        self.assertEqual(evaluate('"b" <=> "a"'), 1)
        self.assertEqual(evaluate('"a" <=> "a"'), 0)

    def test_list_lexicographic(self):
        self.assertEqual(evaluate("[1, 2] <=> [1, 3]"), -1)
        self.assertEqual(evaluate("[1, 2] <=> [1, 2]"), 0)

    def test_map_key_sorted_comparison(self):
        self.assertEqual(evaluate('{"a": 1} <=> {"a": 2}'), -1)

    def test_map_equality_is_order_independent(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2} <=> {"b": 2, "a": 1}'), 0)

    def test_cross_int_float_equality(self):
        self.assertEqual(evaluate("1 <=> 1.0"), 0)

    def test_cross_int_float_ordering(self):
        self.assertEqual(evaluate("1.5 <=> 1"), 1)

    def test_incomparable_types_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: int and string",
        ):
            evaluate('1 <=> "a"')

    def test_int_vs_bool_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"unsupported operand types for comparison: int and bool",
        ):
            evaluate("1 <=> true")

    def test_result_composes_with_equality_non_chained(self):
        self.assertEqual(evaluate("(1 <=> 1) == 0"), True)
        self.assertEqual(evaluate("(2 <=> 1) == 1"), True)


class TestChainedComparisons(unittest.TestCase):
    def test_two_operator_chain(self):
        self.assertEqual(evaluate("1 < 2 < 3"), True)

    def test_three_operator_chain(self):
        self.assertEqual(evaluate("1 < 2 < 3 < 4"), True)

    def test_short_circuits_on_first_failing_pair(self):
        self.assertEqual(evaluate("3 < 2 < 100"), False)

    def test_mixed_ordering_operators(self):
        self.assertEqual(evaluate("1 < 2 <= 2 < 3"), True)

    def test_operands_evaluated_exactly_once_and_short_circuit(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let calls = []; '
            'fn track(label, value) { push(calls, label); return value; } '
            'let result = track("a", 5) < track("b", 3) < track("c", 10);',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), False)
        self.assertEqual(env.get("calls"), ["a", "b"])

    def test_type_mismatch_mid_chain_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate('1 < "a" < 3')

    def test_equality_chain_unaffected(self):
        self.assertEqual(evaluate("1 == 1 == 1"), False)

    def test_not_equal_chain_unaffected(self):
        self.assertEqual(evaluate("1 != 2 != 3"), True)

    def test_mixed_ordering_and_equality_unaffected(self):
        self.assertEqual(evaluate("1 < 2 == true"), True)

    def test_list_chained_comparison(self):
        self.assertEqual(evaluate("[1] < [2] < [3]"), True)
        self.assertEqual(evaluate("[3] < [2] < [1]"), False)


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

    def test_bracket_form_computed_key_on_map(self):
        self.assertEqual(evaluate('{"a": 1}?.["a"]'), 1)

    def test_bracket_form_short_circuits_to_nil_on_nil_map(self):
        self.assertIsNone(evaluate('nil?.["a"]'))

    def test_bracket_form_works_on_list(self):
        self.assertEqual(evaluate("[10, 20, 30]?.[1]"), 20)

    def test_bracket_form_short_circuits_to_nil_on_nil_list(self):
        self.assertIsNone(evaluate("nil?.[0]"))

    def test_bracket_form_index_is_arbitrary_expression(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let key = "a"; let m = {"a": 1}; let r = m?.[key];',
            create_global_environment(),
        )
        self.assertEqual(env.get("r"), 1)

    def test_bracket_form_composes_with_nil_coalescing(self):
        self.assertEqual(evaluate('nil?.["a"] ?? "default"'), "default")

    def test_bracket_form_negative_index_normalizes(self):
        self.assertEqual(evaluate("[1, 2, 3]?.[-1]"), 3)

    def test_bracket_form_assignment_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run('let m = {"a": 1}; m?.["a"] = 2;')

    def test_bracket_form_slice_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run('let m = {"a": 1}; m?.[0:1];')

    def test_dot_form_still_works_unaffected(self):
        self.assertEqual(evaluate('{"key": 42}?.key'), 42)


class TestOptionalCallChaining(unittest.TestCase):
    def test_nil_callee_short_circuits_to_nil(self):
        self.assertIsNone(evaluate("nil?.()"))

    def test_non_nil_callee_calls_through_with_arguments(self):
        env = run("fn add(a, b) { return a + b; } let r = add?.(1, 2);")
        self.assertEqual(env.get("r"), 3)

    def test_composes_with_plain_dot_on_callee_side(self):
        env = run(
            'let m = {"greet": fn(name) { return "hi " + name; }}; '
            'let r = m.greet?.("Al");'
        )
        self.assertEqual(env.get("r"), "hi Al")

    def test_chains_after_optional_dot_on_nil_object(self):
        env = run("let m = nil; let r = m?.greet?.(\"Al\");")
        self.assertIsNone(env.get("r"))

    def test_arguments_not_evaluated_when_callee_is_nil(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let calls = []; "
            "fn effect() { push(calls, 1); return 1; } "
            "let f = nil; "
            "f?.(effect()); "
            "let n = len(calls);",
            create_global_environment(),
        )
        self.assertEqual(env.get("n"), 0)

    def test_spread_argument_not_evaluated_when_callee_is_nil(self):
        # must not raise despite the spread argument never being evaluated
        run("let f = nil; let args = [1, 2]; f?.(...args);")

    def test_non_nil_non_callable_still_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("5?.()")

    def test_unterminated_arguments_raises_parse_error(self):
        with self.assertRaises(ParseError):
            evaluate("f?.(")

    def test_plain_call_unaffected_by_shared_helper_extraction(self):
        self.assertEqual(evaluate("(fn(a, b) { return a + b; })(1, 2)"), 3)

    def test_plain_call_with_spread_unaffected(self):
        env = run(
            "fn add(a, b) { return a + b; } let args = [1, 2]; let r = add(...args);"
        )
        self.assertEqual(env.get("r"), 3)

    def test_optional_index_unaffected_by_this_change(self):
        self.assertIsNone(evaluate("nil?.key"))


class TestPipeOperator(unittest.TestCase):
    def test_pipes_value_into_user_defined_function(self):
        from cinder.builtins import create_global_environment

        env = run(
            "fn double(x) { return x * 2; } let r = 5 |> double;",
            create_global_environment(),
        )
        self.assertEqual(env.get("r"), 10)

    def test_chained_pipes_are_left_associative(self):
        from cinder.builtins import create_global_environment

        env = run(
            "fn double(x) { return x * 2; } fn inc(x) { return x + 1; } "
            "let r = 5 |> double |> inc;",
            create_global_environment(),
        )
        self.assertEqual(env.get("r"), 11)

    def test_pipes_into_a_builtin(self):
        from cinder.builtins import create_global_environment

        env = run("let r = -5 |> abs;", create_global_environment())
        self.assertEqual(env.get("r"), 5)

    def test_right_side_evaluated_as_full_expression_before_call(self):
        # `3 |> curry(add, 2)(5)` evaluates `curry(add, 2)(5)` to a
        # one-argument partial application first, then calls it with `3` —
        # not Elixir-style argument insertion.
        from cinder.builtins import create_global_environment

        env = run(
            "fn add(a, b) { return a + b; } let r = 3 |> curry(add, 2)(5);",
            create_global_environment(),
        )
        self.assertEqual(env.get("r"), 8)

    def test_usable_as_let_initializer_without_parens(self):
        from cinder.builtins import create_global_environment

        env = run("let y = 5 |> abs;", create_global_environment())
        self.assertEqual(env.get("y"), 5)

    def test_usable_inside_ternary_branch_without_parens(self):
        from cinder.builtins import create_global_environment

        env = run("let r = true ? 5 |> abs : 0;", create_global_environment())
        self.assertEqual(env.get("r"), 5)

    def test_non_callable_right_side_raises_not_callable(self):
        with self.assertRaisesRegex(CinderRuntimeError, r"int is not callable"):
            evaluate("5 |> 3")

    def test_arity_mismatch_on_implicit_call_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"one\(\) expects 0 argument\(s\), got 1"
        ):
            run("fn one() { return 1; } let r = 5 |> one;")

    def test_missing_right_operand_raises_parse_error(self):
        with self.assertRaises(ParseError):
            evaluate("5 |>")

    def test_pipe_eq_compound_assignment_unaffected(self):
        env = run("let x = 5; x |= 3;")
        self.assertEqual(env.get("x"), 7)

    def test_bitwise_or_unaffected(self):
        self.assertEqual(evaluate("5 | 3"), 7)


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

    def test_unary_plus(self):
        self.assertEqual(evaluate("+5"), 5)
        self.assertEqual(evaluate("+5.5"), 5.5)
        self.assertEqual(evaluate("+0"), 0)

    def test_unary_plus_composes_with_unary_minus(self):
        self.assertEqual(evaluate("-+5"), -5)

    def test_double_unary_plus(self):
        self.assertEqual(evaluate("++5"), 5)

    def test_unary_plus_operand_of_binary_plus(self):
        self.assertEqual(evaluate("2 + +3"), 5)

    def test_unary_plus_on_grouping(self):
        self.assertEqual(evaluate("+(-5)"), -5)

    def test_unary_plus_on_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("+true")
        self.assertEqual(
            ctx.exception.message, "unary '+' requires a number, got bool"
        )

    def test_unary_plus_on_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('+"abc"')
        self.assertEqual(
            ctx.exception.message, "unary '+' requires a number, got string"
        )

    def test_unary_plus_on_nil_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("+nil")
        self.assertEqual(
            ctx.exception.message, "unary '+' requires a number, got nil"
        )

    def test_unary_plus_on_list_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("+[1, 2]")
        self.assertEqual(
            ctx.exception.message, "unary '+' requires a number, got list"
        )

    def test_postfix_increment_decrement_unaffected(self):
        env = run("let x = 5; x++;")
        self.assertEqual(env.get("x"), 6)
        env = run("let x = 5; x--;")
        self.assertEqual(env.get("x"), 4)

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

    def test_let_no_initializer_defaults_to_nil(self):
        env = run("let x;")
        self.assertIsNone(env.get("x"))

    def test_let_no_initializer_is_mutable(self):
        env = run("let x; x = 5;")
        self.assertEqual(env.get("x"), 5)

    def test_let_no_initializer_assigned_conditionally(self):
        env = run("let ran = false; if (true) { let x; x = 1; ran = x == 1; }")
        self.assertTrue(env.get("ran"))

    def test_let_no_initializer_inside_function_body(self):
        env = run("fn f() { let x; return x; } let result = f();")
        self.assertIsNone(env.get("result"))

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

    def test_let_comma_separated_declares_both(self):
        env = run("let a = 1, b = 2;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_let_comma_separated_uninitialized_default_independently(self):
        env = run("let a, b;")
        self.assertIsNone(env.get("a"))
        self.assertIsNone(env.get("b"))

    def test_let_comma_separated_mixed_initialized_and_not(self):
        env = run("let a = 1, b;")
        self.assertEqual(env.get("a"), 1)
        self.assertIsNone(env.get("b"))

    def test_let_comma_separated_later_sees_earlier(self):
        env = run("let a = 1, b = a + 1;")
        self.assertEqual(env.get("b"), 2)

    def test_let_comma_separated_lands_in_same_scope(self):
        env = run("let a = 1, b = 2; a = 3;")
        self.assertEqual(env.get("a"), 3)
        self.assertEqual(env.get("b"), 2)

    def test_let_comma_separated_three_names(self):
        env = run("let a = 1, b = 2, c = 3;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_let_single_declaration_unaffected_by_comma_support(self):
        env = run("let x = 1 + 2;")
        self.assertEqual(env.get("x"), 3)

    def test_let_comma_separated_plain_then_destructure(self):
        env = run("let a = 1, [b, c] = [2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_let_comma_separated_destructure_then_plain(self):
        env = run("let [a, b] = [1, 2], c = 3;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_const_comma_separated_mixed_freezes_destructured_names(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'b'"):
            run("const a = 1, [b, c] = [2, 3]; b = 9;")

    def test_let_comma_separated_destructure_sees_earlier_plain_name(self):
        env = run("let a = 1, [b, c] = [a, a + 1];")
        self.assertEqual(env.get("b"), 1)
        self.assertEqual(env.get("c"), 2)

    def test_let_comma_separated_list_then_map_destructure(self):
        env = run('let [a, b] = [1, 2], {c, d} = {"c": 3, "d": 4};')
        self.assertEqual(env.get("c"), 3)
        self.assertEqual(env.get("d"), 4)


class TestExprStatementCommaSeparated(unittest.TestCase):
    def test_two_assignments_both_take_effect(self):
        env = run("let a; let b; a = 1, b = 2;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_left_to_right_evaluation_order(self):
        env = run("let a = 0, b = 0; a = 1, b = a + 1;")
        self.assertEqual(env.get("b"), 2)

    def test_index_assignment_targets_in_sequence(self):
        env = run("let xs = [0, 0]; xs[0] = 1, xs[1] = 2;")
        self.assertEqual(env.get("xs"), [1, 2])

    def test_single_expression_statement_unaffected_by_comma_support(self):
        env = run("let a; a = 1;")
        self.assertEqual(env.get("a"), 1)

    def test_non_assignment_expression_in_sequence(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let calls = []; push(calls, 1), push(calls, 2);",
            create_global_environment(),
        )
        self.assertEqual(env.get("calls"), [1, 2])

    def test_trailing_comma_still_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run("let a; let b; a = 1, b = 2,;")

    def test_composes_with_if_single_statement_body(self):
        env = run("let a; let b; if (true) a = 1, b = 2;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)


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

    def test_const_comma_separated_declares_both(self):
        env = run("const a = 1, b = 2;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_const_comma_separated_reassignment_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("const a = 1, b = 2; a = 3;")

    def test_const_comma_separated_missing_initializer_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run("const a = 1, b;")


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

    def test_trailing_comma_binds_two_names(self):
        env = run("let [a, b,] = [1, 2];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_single_element_trailing_comma(self):
        env = run("let [a,] = [1];")
        self.assertEqual(env.get("a"), 1)

    def test_rest_element_then_trailing_comma(self):
        env = run("let [a, ...rest,] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), [2, 3])

    def test_real_element_after_rest_still_raises(self):
        with self.assertRaises(ParseError):
            run("let [a, ...rest, b] = [1, 2, 3];")


class TestDestructureListDefaults(unittest.TestCase):
    def test_default_used_when_source_missing_element(self):
        env = run("let [a, b = 5] = [1];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 5)

    def test_default_not_used_when_source_has_element(self):
        env = run("let [a, b = 5] = [1, 2];")
        self.assertEqual(env.get("b"), 2)

    def test_later_default_sees_earlier_bound_name(self):
        env = run("let [a, b = a + 1] = [5];")
        self.assertEqual(env.get("b"), 6)

    def test_plain_assignment_unaffected_by_defaults_support(self):
        env = run("let a = 0; let b = 0; [a, b] = [b, a];")
        self.assertEqual(env.get("a"), 0)
        self.assertEqual(env.get("b"), 0)

    def test_for_loop_element_default(self):
        env = run(
            "let total = 0; "
            "for [a, b = 0] in [[1], [2, 3]] { total = total + a + b; }"
        )
        self.assertEqual(env.get("total"), 6)

    def test_fn_param_element_default(self):
        env = run("fn f([a, b = 10]) { return a + b; } let r = f([1]);")
        self.assertEqual(env.get("r"), 11)

    def test_comprehension_element_default(self):
        env = run(
            "let r = [a + b for [a, b = 100] in [[1], [2, 3]]];"
        )
        self.assertEqual(env.get("r"), [101, 5])

    def test_default_combines_with_trailing_rest(self):
        env = run("let [a = 1, ...rest] = [];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), [])

    def test_too_few_elements_with_required_before_default_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects between 1 and 2 elements, got 0",
        ):
            run("let [a, b = 1] = [];")

    def test_too_many_elements_with_default_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects between 1 and 2 elements, got 3",
        ):
            run("let [a, b = 1] = [1, 2, 3];")

    def test_rest_pattern_too_few_required_elements_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects at least 1 elements, got 0",
        ):
            run("let [a, b = 1, ...rest] = [];")

    def test_no_defaults_message_unchanged(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects 1 elements, got 2",
        ):
            run("let [a] = [1, 2];")


class TestDestructureListHoles(unittest.TestCase):
    def test_interior_hole_discards_middle_position(self):
        env = run("let [a, , c] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)
        with self.assertRaises(KeyError):
            env.get("b")

    def test_leading_hole(self):
        env = run("let [, b] = [1, 2];")
        self.assertEqual(env.get("b"), 2)

    def test_no_holes_behaves_as_before(self):
        env = run("let [a, ...rest] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), [2, 3])

    def test_hole_combines_with_trailing_rest(self):
        env = run("let [a, , ...rest] = [1, 2, 3, 4];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), [3, 4])

    def test_for_loop_hole(self):
        env = run(
            "let total = 0; "
            "for [a, , c] in [[1, 2, 3], [4, 5, 6]] { total = total + a + c; }"
        )
        self.assertEqual(env.get("total"), 14)

    def test_fn_param_hole(self):
        env = run("fn f([a, , c]) { return a + c; } let r = f([1, 2, 3]);")
        self.assertEqual(env.get("r"), 4)

    def test_comprehension_hole(self):
        env = run("let r = [a + c for [a, , c] in [[1, 2, 3]]];")
        self.assertEqual(env.get("r"), [4])

    def test_hole_still_occupies_required_position(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects 3 elements, got 2",
        ):
            run("let [a, , c] = [1, 2];")

    def test_hole_after_default_raises(self):
        with self.assertRaisesRegex(
            ParseError,
            r"element without a default value follows an element with one "
            r"in destructuring pattern",
        ):
            run("let [a = 1, , c] = [9];")

    def test_trailing_comma_now_accepted(self):
        env = run("let [a, b, ] = [1, 2];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_hole_then_trailing_comma_accepted(self):
        # `[a, ,]` has two commas: the break-on-trailing-comma check runs
        # before the next element is parsed, so the first comma's next
        # token is the second comma (not `]`) and falls through to the
        # existing hole logic same as a middle hole would, while the
        # second comma's next token is `]` and triggers the new break.
        env = run("let [a, ,] = [1, 2];")
        self.assertEqual(env.get("a"), 1)

    def test_empty_pattern_unaffected(self):
        with self.assertRaises(ParseError):
            run("let [] = [1];")

    def test_plain_assignment_hole_now_supported(self):
        env = run("let a = 0; let c = 0; [a, , c] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)


class TestDestructureNestedListPattern(unittest.TestCase):
    def test_nested_in_second_position(self):
        env = run("let [a, [b, c]] = [1, [2, 3]];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_nested_in_first_position(self):
        env = run("let [[a, b], c] = [[1, 2], 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_arbitrary_nesting_depth(self):
        env = run("let [a, [b, [c, d]]] = [1, [2, [3, 4]]];")
        self.assertEqual(env.get("d"), 4)

    def test_rest_element_inside_nested_pattern(self):
        env = run("let [a, [b, ...brest]] = [1, [2, 3, 4]];")
        self.assertEqual(env.get("brest"), [3, 4])

    def test_default_value_on_nested_pattern_slot(self):
        env = run("let [a, [b, c] = [0, 0]] = [1];")
        self.assertEqual(env.get("b"), 0)
        self.assertEqual(env.get("c"), 0)

    def test_hole_inside_nested_pattern(self):
        env = run("let [[a, , c]] = [[1, 2, 3]];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)

    def test_non_list_at_nested_position_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"cannot destructure int as a list"
        ):
            run("let [a, [b, c]] = [1, 2];")

    def test_plain_assignment_form(self):
        env = run("let a = 0; let b = 0; let c = 0; [a, [b, c]] = [1, [2, 3]];")
        self.assertEqual(env.get("b"), 2)

    def test_for_loop_form(self):
        env = run(
            "let total = 0; "
            "for [a, [b, c]] in [[1, [2, 3]]] { total = total + b; }"
        )
        self.assertEqual(env.get("total"), 2)

    def test_fn_param_form(self):
        env = run("fn f([a, [b, c]]) { return b + c; } let r = f([1, [2, 3]]);")
        self.assertEqual(env.get("r"), 5)

    def test_comprehension_form(self):
        env = run("let r = [b for [a, [b, c]] in [[1, [2, 3]]]];")
        self.assertEqual(env.get("r"), [2])


class TestDestructureMapPatternNestedInList(unittest.TestCase):
    def test_nested_in_last_position(self):
        env = run('let [a, {b, c}] = [1, {"b": 2, "c": 3}];')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_nested_in_first_position(self):
        env = run('let [{x, y}, a] = [{"x": 1, "y": 2}, 3];')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("y"), 2)
        self.assertEqual(env.get("a"), 3)

    def test_composes_with_nested_list_pattern(self):
        env = run('let [a, [b, {c}]] = [1, [2, {"c": 3}]];')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_rest_element_inside_nested_pattern(self):
        env = run('let [a, {b, ...brest}] = [1, {"b": 2, "c": 3, "d": 4}];')
        self.assertEqual(env.get("brest"), {"c": 3, "d": 4})

    def test_default_value_on_nested_pattern_slot(self):
        env = run('let [a, {b, c = 0}] = [1, {"b": 2}];')
        self.assertEqual(env.get("c"), 0)

    def test_non_map_at_nested_position_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"cannot destructure int as a map"
        ):
            run("let [a, {b}] = [1, 2];")

    def test_missing_key_inside_nested_pattern_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"destructuring pattern expects key 'b', not found in map"
        ):
            run('let [a, {b}] = [1, {}];')

    def test_for_loop_form(self):
        env = run(
            "let total_a = 0; let total_b = 0; "
            'for [a, {b}] in [[1, {"b": 2}], [3, {"b": 4}]] { total_a = total_a + a; total_b = total_b + b; }'
        )
        self.assertEqual(env.get("total_a"), 4)
        self.assertEqual(env.get("total_b"), 6)

    def test_fn_param_form(self):
        env = run('fn f([a, {b}]) { return a + b; } let r = f([1, {"b": 2}]);')
        self.assertEqual(env.get("r"), 3)

    def test_comprehension_form(self):
        env = run(
            'let r = [a + b for [a, {b}] in [[1, {"b": 2}], [3, {"b": 4}]]];'
        )
        self.assertEqual(env.get("r"), [3, 7])

    def test_plain_assignment_form_now_supported(self):
        env = run('let a = 0; let b = 0; [a, {b}] = [1, {"b": 2}];')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)


class TestDestructureNestedMapPattern(unittest.TestCase):
    def test_nested_in_last_position(self):
        env = run('let {a, b: {c, d}} = {"a": 1, "b": {"c": 2, "d": 3}};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 2)
        self.assertEqual(env.get("d"), 3)

    def test_nested_in_first_position(self):
        env = run('let {a: {x, y}, b} = {"a": {"x": 1, "y": 2}, "b": 3};')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("y"), 2)
        self.assertEqual(env.get("b"), 3)

    def test_arbitrary_nesting_depth(self):
        env = run('let {a: {b: {c}}} = {"a": {"b": {"c": 5}}};')
        self.assertEqual(env.get("c"), 5)

    def test_rest_element_inside_nested_pattern(self):
        env = run('let {a: {b, ...brest}} = {"a": {"b": 1, "c": 2, "d": 3}};')
        self.assertEqual(env.get("brest"), {"c": 2, "d": 3})

    def test_rest_element_at_outer_level_with_nested_pattern_elsewhere(self):
        env = run('let {a: {x}, ...rest} = {"a": {"x": 1}, "b": 2, "c": 3};')
        self.assertEqual(env.get("rest"), {"b": 2, "c": 3})

    def test_default_value_on_nested_pattern_slot(self):
        env = run('let {b: {c, d} = {"c": 0, "d": 0}} = {};')
        self.assertEqual(env.get("c"), 0)
        self.assertEqual(env.get("d"), 0)

    def test_non_map_at_nested_position_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"cannot destructure int as a map"
        ):
            run('let {a: {b, c}} = {"a": 1};')

    def test_missing_key_inside_nested_pattern_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"destructuring pattern expects key 'b', not found in map"
        ):
            run('let {a: {b}} = {"a": {}};')

    def test_plain_assignment_form(self):
        env = run(
            "let x = 0; let y = 0; "
            '{outer: {x, y}} = {"outer": {"x": 1, "y": 2}};'
        )
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("y"), 2)

    def test_for_loop_form(self):
        env = run(
            "let total = 0; "
            'for {a: {x}} in [{"a": {"x": 1}}, {"a": {"x": 2}}] { total = total + x; }'
        )
        self.assertEqual(env.get("total"), 3)

    def test_fn_param_form(self):
        env = run(
            "fn f({a: {x, y}}) { return x + y; } "
            'let r = f({"a": {"x": 1, "y": 2}});'
        )
        self.assertEqual(env.get("r"), 3)

    def test_comprehension_form(self):
        env = run(
            'let r = [x for {a: {x}} in [{"a": {"x": 1}}, {"a": {"x": 2}}]];'
        )
        self.assertEqual(env.get("r"), [1, 2])


class TestDestructureListPatternNestedInMap(unittest.TestCase):
    def test_nested_in_last_position(self):
        env = run('let {a, b: [c, d]} = {"a": 1, "b": [2, 3]};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 2)
        self.assertEqual(env.get("d"), 3)

    def test_nested_in_first_position(self):
        env = run('let {x: [y, z], a} = {"x": [1, 2], "a": 3};')
        self.assertEqual(env.get("y"), 1)
        self.assertEqual(env.get("z"), 2)
        self.assertEqual(env.get("a"), 3)

    def test_composes_with_nested_map_pattern(self):
        env = run('let {a, b: {c: [d, e]}} = {"a": 1, "b": {"c": [2, 3]}};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("d"), 2)
        self.assertEqual(env.get("e"), 3)

    def test_rest_element_inside_nested_pattern(self):
        env = run('let {a, b: [c, ...drest]} = {"a": 1, "b": [2, 3, 4]};')
        self.assertEqual(env.get("drest"), [3, 4])

    def test_default_value_on_nested_pattern_slot(self):
        env = run('let {a, b: [c] = [0]} = {"a": 1};')
        self.assertEqual(env.get("c"), 0)

    def test_non_list_at_nested_position_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"cannot destructure int as a list"
        ):
            run('let {a, b: [c]} = {"a": 1, "b": 2};')

    def test_arity_mismatch_inside_nested_pattern_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"destructuring pattern expects 1 elements, got 0"
        ):
            run('let {a, b: [c]} = {"a": 1, "b": []};')

    def test_for_loop_form(self):
        env = run(
            "let total_a = 0; let total_c = 0; "
            'for {a, b: [c]} in [{"a": 1, "b": [2]}, {"a": 3, "b": [4]}] { total_a = total_a + a; total_c = total_c + c; }'
        )
        self.assertEqual(env.get("total_a"), 4)
        self.assertEqual(env.get("total_c"), 6)

    def test_fn_param_form(self):
        env = run('fn f({a, b: [c]}) { return a + c; } let r = f({"a": 1, "b": [2]});')
        self.assertEqual(env.get("r"), 3)

    def test_comprehension_form(self):
        env = run(
            'let r = [a + c for {a, b: [c]} in [{"a": 1, "b": [2]}, {"a": 3, "b": [4]}]];'
        )
        self.assertEqual(env.get("r"), [3, 7])

    def test_plain_assignment_form_still_rejected(self):
        with self.assertRaisesRegex(ParseError, r"expected ';' after expression"):
            run('let a = 0; let c = 0; {a, b: [c]} = {"a": 1, "b": [2]};')


class TestDestructureMapDefaults(unittest.TestCase):
    def test_default_used_when_key_missing(self):
        env = run('let {a, b = 5} = {"a": 1};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 5)

    def test_default_not_used_when_key_present(self):
        env = run('let {a, b = 5} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("b"), 2)

    def test_later_default_sees_earlier_bound_name(self):
        env = run('let {a, b = a + 1} = {"a": 5};')
        self.assertEqual(env.get("b"), 6)

    def test_key_rename_and_default_combine(self):
        env = run('let {a: x = 10} = {};')
        self.assertEqual(env.get("x"), 10)

    def test_defaulted_entry_before_required_no_ordering_restriction(self):
        env = run('let {a: x = 1, b} = {"b": 2};')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_no_defaults_unaffected(self):
        env = run('let {a} = {"a": 1};')
        self.assertEqual(env.get("a"), 1)

    def test_for_loop_entry_default(self):
        env = run(
            'let total = 0; '
            'for {a, b = 0} in [{"a": 1}, {"a": 2, "b": 3}] { total = total + a + b; }'
        )
        self.assertEqual(env.get("total"), 6)

    def test_fn_param_entry_default(self):
        env = run('fn f({a, b = 10}) { return a + b; } let r = f({"a": 1});')
        self.assertEqual(env.get("r"), 11)

    def test_comprehension_entry_default(self):
        env = run(
            'let r = [a + b for {a, b = 100} in [{"a": 1}, {"a": 2, "b": 3}]];'
        )
        self.assertEqual(env.get("r"), [101, 5])

    def test_default_combines_with_trailing_rest(self):
        env = run('let {a = 1, ...rest} = {};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), {})

    def test_plain_assignment_gains_defaults(self):
        env = run('let a = 0; let b = 0; {a, b = 5} = {"a": 1};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 5)

    def test_required_key_still_missing_raises(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"destructuring pattern expects key 'a', not found in map",
        ):
            run('let {a, b = 1} = {};')

    def test_whole_pattern_default_used_when_argument_omitted(self):
        env = run(
            'fn f({a, b} = {"a": 1, "b": 2}) { return a + b; } let r = f();'
        )
        self.assertEqual(env.get("r"), 3)

    def test_whole_pattern_default_unused_when_argument_supplied(self):
        env = run(
            'fn f({a, b} = {"a": 1, "b": 2}) { return a + b; } '
            'let r = f({"a": 9, "b": 1});'
        )
        self.assertEqual(env.get("r"), 10)


class TestDestructureAssign(unittest.TestCase):
    def test_swap_idiom(self):
        env = run("let a = 1; let b = 2; [a, b] = [b, a];")
        self.assertEqual(env.get("a"), 2)
        self.assertEqual(env.get("b"), 1)

    def test_rest_binds_remaining_elements_as_list(self):
        env = run("let a = 0; let b = 0; let rest = []; [a, b, ...rest] = [1, 2, 3, 4];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("rest"), [3, 4])

    def test_hole_skips_element(self):
        env = run("let a = 0; let c = 0; [a, , c] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)

    def test_element_default_used_when_value_missing(self):
        env = run("let a = 0; let b = 0; [a, b = 5] = [1];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 5)

    def test_nested_map_element(self):
        env = run(
            'let a = 0; let b = 0; let c = 0; '
            '[a, {b, c}] = [1, {"b": 2, "c": 3}];'
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_expression_returns_assigned_value(self):
        env = Environment()
        interpreter = Interpreter()
        for statement in parse_program(tokenize("let a = 0; let b = 0;")):
            interpreter.execute(statement, env)
        value = interpreter.evaluate(
            parse_expression(tokenize("[a, b] = [1, 2]")), env
        )
        self.assertEqual(value, [1, 2])

    def test_too_few_elements_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let a = 0; let b = 0; [a, b] = [1];")
        self.assertEqual(
            ctx.exception.message, "destructuring pattern expects 2 elements, got 1"
        )

    def test_non_list_rhs_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let a = 0; [a] = 5;")
        self.assertEqual(ctx.exception.message, "cannot destructure int as a list")

    def test_undefined_name_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("[undefined_a, undefined_b] = [1, 2];")
        self.assertEqual(ctx.exception.message, "undefined name 'undefined_a'")

    def test_const_target_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("const a = 1; let b = 2; [a, b] = [3, 4];")
        self.assertEqual(ctx.exception.message, "cannot assign to const 'a'")

    def test_plain_let_and_for_destructuring_unaffected(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let [a, b] = [1, 2]; for [k, v] in items({"x": 1}) { a = k; b = v; }',
            create_global_environment(),
        )
        self.assertEqual(env.get("a"), "x")
        self.assertEqual(env.get("b"), 1)


class TestBareMultiTargetAssign(unittest.TestCase):
    def test_two_targets(self):
        env = run("let a = 0; let b = 0; a, b = 1, 2;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_swap_idiom(self):
        env = run("let a = 1; let b = 2; a, b = b, a;")
        self.assertEqual(env.get("a"), 2)
        self.assertEqual(env.get("b"), 1)

    def test_three_targets(self):
        env = run("let a = 0; let b = 0; let c = 0; a, b, c = 1, 2, 3;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)
        self.assertEqual(env.get("c"), 3)

    def test_single_rhs_call_unpacks_like_bracketed_form(self):
        env = run(
            "fn pair() { return [1, 2]; } let a = 0; let b = 0; a, b = pair();"
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_too_many_values_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let a = 0; let b = 0; a, b = 1, 2, 3;")
        self.assertEqual(
            ctx.exception.message, "destructuring pattern expects 2 elements, got 3"
        )

    def test_single_target_followed_by_comma_statement_unchanged(self):
        env = run("let a = 0; a = 1, 2;")
        self.assertEqual(env.get("a"), 1)

    def test_bare_comma_identifiers_without_equals_unchanged(self):
        env = run("let a = 1; let b = 2; a, b;")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)


class TestDestructureAssignMap(unittest.TestCase):
    def test_binds_two_names(self):
        env = run('let a = 0; let b = 0; {a, b} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_extra_unnamed_keys_are_ignored(self):
        env = run('let a = 0; {a} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)

    def test_expression_returns_assigned_value(self):
        # `{a, b} = expr` only parses via `_brace_statement`'s statement-level
        # speculation (unlike `[a, b] = expr`, a plain `ListLiteral` that
        # parses fine standalone), so this goes through `parse_program` and
        # pulls the `DestructureAssign` back out of its `ExprStmt` rather
        # than using `parse_expression` directly.
        env = Environment()
        interpreter = Interpreter()
        for statement in parse_program(tokenize("let a = 0; let b = 0;")):
            interpreter.execute(statement, env)
        assign_stmt = parse_program(tokenize('{a, b} = {"a": 1, "b": 2};'))[0]
        value = interpreter.evaluate(assign_stmt.expression, env)
        self.assertEqual(value, {"a": 1, "b": 2})

    def test_missing_named_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('let a = 0; let b = 0; {a, b} = {"a": 1};')
        self.assertEqual(
            ctx.exception.message,
            "destructuring pattern expects key 'b', not found in map",
        )

    def test_non_map_rhs_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let a = 0; {a} = [1, 2];")
        self.assertEqual(ctx.exception.message, "cannot destructure list as a map")

    def test_undefined_name_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('{undefined_a} = {"undefined_a": 1};')
        self.assertEqual(ctx.exception.message, "undefined name 'undefined_a'")

    def test_const_target_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('const a = 1; let b = 2; {a, b} = {"a": 3, "b": 4};')
        self.assertEqual(ctx.exception.message, "cannot assign to const 'a'")

    def test_plain_let_map_destructuring_unaffected(self):
        env = run('let {a, b} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_map_literal_statement_unaffected(self):
        run('{"a": 1};')  # still an ExprStmt(MapLiteral), no destructuring attempted

    def test_rest_binds_remaining_keys_as_map(self):
        env = run('let a = 0; let rest = 0; {a, ...rest} = {"a": 1, "b": 2, "c": 3};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), {"b": 2, "c": 3})

    def test_rest_binds_empty_map_when_nothing_left_over(self):
        env = run('let a = 0; let b = 0; let rest = 0; {a, b, ...rest} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("rest"), {})

    def test_rest_only_pattern_captures_everything(self):
        env = run('let rest = 0; {...rest} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("rest"), {"a": 1, "b": 2})

    def test_no_rest_element_behavior_unchanged(self):
        env = run('let a = 0; {a} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)

    def test_rest_not_last_raises_parse_error(self):
        with self.assertRaises(ParseError):
            run('let a = 0; let rest = 0; {a, ...rest, b} = {"a": 1};')

    def test_key_rename_binds_under_new_name(self):
        env = run('let x = 0; {a: x} = {"a": 5};')
        self.assertEqual(env.get("x"), 5)

    def test_trailing_comma_binds_two_names(self):
        env = run('let a = 0; let b = 0; {a, b,} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)


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

    def test_rest_binds_remaining_keys_as_map(self):
        env = run('let {a, ...rest} = {"a": 1, "b": 2, "c": 3};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), {"b": 2, "c": 3})

    def test_rest_binds_empty_map_when_nothing_left_over(self):
        env = run('let {a, b, ...rest} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("rest"), {})

    def test_rest_only_pattern_captures_everything(self):
        env = run('let {...rest} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("rest"), {"a": 1, "b": 2})

    def test_no_rest_element_behavior_unchanged(self):
        env = run('let {a} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        with self.assertRaises(KeyError):
            env.get("rest")

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

    def test_key_rename_binds_under_new_name(self):
        env = run('let {a: x, b} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("b"), 2)
        with self.assertRaises(KeyError):
            env.get("a")

    def test_key_rename_with_rest_still_collects_by_key(self):
        env = run('let {a: x, ...rest} = {"a": 1, "b": 2, "c": 3};')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("rest"), {"b": 2, "c": 3})

    def test_key_rename_missing_key_error_names_the_key_not_the_binding(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "destructuring pattern expects key 'a', not found in map"
        ):
            run('let {a: x} = {"b": 1};')

    def test_key_renamed_twice_last_binding_wins(self):
        env = run('let {a: x, a: y} = {"a": 1};')
        self.assertEqual(env.get("x"), 1)
        self.assertEqual(env.get("y"), 1)

    def test_trailing_comma_binds_two_names(self):
        env = run('let {a, b,} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_single_entry_trailing_comma(self):
        env = run('let {a,} = {"a": 1};')
        self.assertEqual(env.get("a"), 1)

    def test_rest_entry_then_trailing_comma(self):
        env = run('let {a, ...rest,} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("rest"), {"b": 2})


class TestConstDestructure(unittest.TestCase):
    def test_list_pattern_binds_two_names(self):
        env = run("const [a, b] = [1, 2];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_map_pattern_binds_two_names(self):
        env = run('const {a, b} = {"a": 1, "b": 2};')
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_list_pattern_name_is_frozen(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'a'"):
            run("const [a, b] = [1, 2]; a = 3;")

    def test_map_pattern_name_is_frozen(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'b'"):
            run('const {a, b} = {"a": 1, "b": 2}; b = 3;')

    def test_nested_pattern_name_is_frozen(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'c'"):
            run('const [a, {b, c}] = [1, {"b": 2, "c": 3}]; c = 9;')

    def test_rest_binding_is_frozen(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'rest'"):
            run("const [a, ...rest] = [1, 2, 3]; rest = [];")

    def test_renamed_key_binding_is_frozen(self):
        with self.assertRaisesRegex(CinderRuntimeError, "cannot assign to const 'x'"):
            run('const {a: x} = {"a": 1}; x = 2;')

    def test_list_pattern_default_still_works(self):
        env = run("const [a, b = 5] = [1];")
        self.assertEqual(env.get("b"), 5)

    def test_list_pattern_hole_still_works(self):
        env = run("const [a, , c] = [1, 2, 3];")
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)

    def test_plain_let_destructure_stays_mutable(self):
        env = run("let [a, b] = [1, 2]; a = 3;")
        self.assertEqual(env.get("a"), 3)


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

    def test_plus_and_minus_and_compound_assign_unaffected(self):
        self.assertEqual(evaluate("1 + 2"), 3)
        env = run("let a = 1; a += 1;")
        self.assertEqual(env.get("a"), 2)

    def test_used_as_let_initializer(self):
        env = run("let x = 1; let y = x++;")
        self.assertEqual(env.get("x"), 2)
        self.assertEqual(env.get("y"), 2)

    def test_used_as_chained_assignment_rhs(self):
        env = run("let x = 1; let y = 0; y = x++;")
        self.assertEqual(env.get("x"), 2)
        self.assertEqual(env.get("y"), 2)

    def test_used_inside_parenthesized_subexpression(self):
        env = run("let x = 1; let y = (x++);")
        self.assertEqual(env.get("x"), 2)
        self.assertEqual(env.get("y"), 2)

    def test_minus_minus_used_as_let_initializer(self):
        env = run("let x = 5; let y = x--;")
        self.assertEqual(env.get("x"), 4)
        self.assertEqual(env.get("y"), 4)

    def test_index_target_used_as_let_initializer(self):
        env = run("let xs = [1]; let y = xs[0]++;")
        self.assertEqual(env.get("xs"), [2])
        self.assertEqual(env.get("y"), 2)

    def test_bare_statement_form_unaffected(self):
        env = run("let x = 1; x++;")
        self.assertEqual(env.get("x"), 2)

    def test_for_loop_step_clause_unaffected(self):
        env = run("let total = 0; for (let i = 0; i < 3; i++) { total = total + i; }")
        self.assertEqual(env.get("total"), 3)

    def test_for_loop_non_incdec_step_unaffected(self):
        env = run("let total = 0; for (let i = 0; i < 3; i = i + 1) { total = total + i; }")
        self.assertEqual(env.get("total"), 3)

    def test_precedence_unchanged_negation_then_increment_raises(self):
        with self.assertRaises(ParseError):
            parse_program(tokenize("let x = 1; -x++;"))

    def test_still_unreachable_from_call_argument(self):
        with self.assertRaises(ParseError):
            parse_program(tokenize("let x = 1; print(x++);"))


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

    def test_while_else_runs_on_normal_completion(self):
        env = run(
            "let i = 0; let done = false; "
            "while (i < 3) { i = i + 1; } else { done = true; }"
        )
        self.assertTrue(env.get("done"))

    def test_while_else_skipped_by_break(self):
        env = run("let ran = false; while (true) { break; } else { ran = true; }")
        self.assertFalse(env.get("ran"))

    def test_while_else_runs_on_zero_iterations(self):
        env = run("let ran = false; while (false) { } else { ran = true; }")
        self.assertTrue(env.get("ran"))

    def test_while_else_not_skipped_by_continue(self):
        env = run(
            "let i = 0; let ran = false; "
            "while (i < 3) { i = i + 1; if (i == 1) { continue; } } "
            "else { ran = true; }"
        )
        self.assertTrue(env.get("ran"))

    def test_while_else_skipped_by_labeled_break(self):
        env = run(
            "let ran = false; "
            "outer: while (true) { break outer; } else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_while_else_binds_to_while_not_enclosing_if(self):
        # Dangling-attachment: an unbraced `while` as an `if`'s then-branch
        # now claims a trailing `else` for itself, not the `if`.
        env = run(
            "let attached = false; "
            "if (true) while (false) { } else { attached = true; }"
        )
        self.assertTrue(env.get("attached"))

    def test_while_else_skipped_by_return(self):
        env = run(
            "fn f() { while (true) { return 1; } else { return 2; } } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_while_without_else_still_behaves_as_before(self):
        env = run("let x = 0; while (x < 3) { x = x + 1; }")
        self.assertEqual(env.get("x"), 3)


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


class TestDoWhileElse(unittest.TestCase):
    def test_do_while_else_runs_on_normal_completion(self):
        env = run("let x = 0; let done = false; do { x = 1; } while (false) else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_do_while_else_runs_after_multiple_iterations(self):
        env = run(
            "let i = 0; let done = false; "
            "do { i = i + 1; } while (i < 3) else { done = true; }"
        )
        self.assertTrue(env.get("done"))

    def test_do_while_else_skipped_by_break(self):
        env = run("let ran = false; do { break; } while (true) else { ran = true; }")
        self.assertFalse(env.get("ran"))

    def test_do_while_else_not_skipped_by_continue(self):
        env = run(
            "let i = 0; let ran = false; "
            "do { i = i + 1; if (i == 1) { continue; } } while (i < 2) "
            "else { ran = true; }"
        )
        self.assertTrue(env.get("ran"))

    def test_do_while_else_skipped_by_labeled_break(self):
        env = run(
            "let ran = false; "
            "outer: do { do { break outer; } while (true); } while (true) "
            "else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_do_while_else_skipped_by_return(self):
        env = run(
            "fn f() { do { return 1; } while (false) else { return 2; } } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_do_while_without_else_still_behaves_as_before(self):
        env = run("let x = 0; do { x = 1; } while (false);")
        self.assertEqual(env.get("x"), 1)

    def test_do_while_else_unbraced_single_statement(self):
        env = run("let x = 0; do { } while (false) else x = 1;")
        self.assertEqual(env.get("x"), 1)


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


class TestForElse(unittest.TestCase):
    def test_for_else_runs_on_normal_completion(self):
        env = run(
            "let done = false; "
            "for x in [1, 2, 3] { } else { done = true; }"
        )
        self.assertTrue(env.get("done"))

    def test_for_else_runs_on_zero_iterations(self):
        env = run("let done = false; for x in [] { } else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_for_else_skipped_by_break(self):
        env = run(
            "let ran = false; "
            "for x in [1, 2, 3] { if (x == 2) { break; } } else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_for_else_not_skipped_by_continue(self):
        env = run(
            "let ran = false; "
            "for x in [1, 2, 3] { if (x == 1) { continue; } } else { ran = true; }"
        )
        self.assertTrue(env.get("ran"))

    def test_for_else_skipped_by_labeled_break(self):
        env = run(
            "let ran = false; "
            "outer: for x in [1] { for y in [1] { break outer; } } else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_for_else_skipped_by_return(self):
        env = run(
            "fn f() { for x in [1] { return 1; } else { return 2; } } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_for_else_runs_over_string(self):
        env = run('let done = false; for c in "" { } else { done = true; }')
        self.assertTrue(env.get("done"))

    def test_for_else_runs_over_map(self):
        env = run("let done = false; for k in {} { } else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_for_else_runs_with_list_destructuring(self):
        env = run("let done = false; for [a, b] in [] { } else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_for_else_runs_with_map_destructuring(self):
        env = run("let done = false; for {a} in [] { } else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_for_without_else_still_behaves_as_before(self):
        env = run("let total = 0; for x in [1, 2, 3] { total = total + x; }")
        self.assertEqual(env.get("total"), 6)


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

    def test_map_destructure_multi_name(self):
        env = self._run(
            'let out = []; '
            'for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { push(out, a + b); }'
        )
        self.assertEqual(env.get("out"), [3, 7])

    def test_map_destructure_single_name(self):
        env = self._run('let out = []; for {a} in [{"a": 1}, {"a": 2}] { push(out, a); }')
        self.assertEqual(env.get("out"), [1, 2])

    def test_map_destructure_key_rename(self):
        env = self._run(
            'let out = []; '
            'for {a: x, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { push(out, x + b); }'
        )
        self.assertEqual(env.get("out"), [3, 7])

    def test_map_destructure_non_map_item_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            self._run('for {a} in [{"a": 1}, 5] { }')
        self.assertEqual(ctx.exception.message, "cannot destructure int as a map")

    def test_map_destructure_missing_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            self._run('for {a, b} in [{"a": 1}] { }')
        self.assertEqual(
            ctx.exception.message,
            "destructuring pattern expects key 'b', not found in map",
        )

    def test_map_destructure_with_rest_fresh_per_iteration(self):
        env = self._run(
            'let firsts = []; let rests = []; '
            'for {a, ...rest} in [{"a": 1, "b": 2}, {"a": 3, "c": 4}] { '
            '  push(firsts, a); push(rests, rest); '
            '}'
        )
        self.assertEqual(env.get("firsts"), [1, 3])
        self.assertEqual(env.get("rests"), [{"b": 2}, {"c": 4}])

    def test_map_destructure_labeled_break_targets_outer_loop(self):
        env = self._run(
            'let seen = []; '
            'outer: for {a} in [{"a": 1}] { for x in [1] { break outer; } push(seen, a); }'
        )
        self.assertEqual(env.get("seen"), [])

    def test_list_destructure_trailing_comma(self):
        env = self._run(
            'let ks = []; let vs = []; '
            'for [k, v,] in items({"a": 1}) { push(ks, k); push(vs, v); }'
        )
        self.assertEqual(env.get("ks"), ["a"])
        self.assertEqual(env.get("vs"), [1])

    def test_map_destructure_trailing_comma(self):
        env = self._run(
            'let out = []; '
            'for {a, b,} in [{"a": 1, "b": 2}] { push(out, a + b); }'
        )
        self.assertEqual(env.get("out"), [3])


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

    def test_comma_separated_init_declares_both_loop_variables(self):
        env = self._run(
            "let log = []; "
            "for (let i = 0, j = 3; i < j; i = i + 1) { push(log, i); push(log, j); }"
        )
        self.assertEqual(env.get("log"), [0, 3, 1, 3, 2, 3])

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


class TestForCElse(unittest.TestCase):
    def test_for_c_else_runs_on_normal_completion(self):
        env = run(
            "let x; let done = false; "
            "for (let i = 0; i < 3; i = i + 1) { x = i; } else { done = true; }"
        )
        self.assertTrue(env.get("done"))

    def test_for_c_else_runs_when_condition_false_before_first_iteration(self):
        env = run("let done = false; for (; false;) { } else { done = true; }")
        self.assertTrue(env.get("done"))

    def test_for_c_else_skipped_by_break(self):
        env = run(
            "let i = 0; let ran = false; "
            "for (;; i = i + 1) { if (i == 2) { break; } } else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_for_c_else_not_skipped_by_continue(self):
        env = run(
            "let ran = false; "
            "for (let i = 0; i < 3; i = i + 1) { if (i == 1) { continue; } } "
            "else { ran = true; }"
        )
        self.assertTrue(env.get("ran"))

    def test_for_c_else_skipped_by_labeled_break(self):
        env = run(
            "let ran = false; "
            "outer: for (let i = 0; i < 1; i = i + 1) { "
            "  for (let j = 0; j < 1; j = j + 1) { break outer; } "
            "} else { ran = true; }"
        )
        self.assertFalse(env.get("ran"))

    def test_for_c_else_skipped_by_return(self):
        env = run(
            "fn f() { for (let i = 0; i < 1; i = i + 1) { return 1; } else { return 2; } } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_for_c_without_else_still_behaves_as_before(self):
        env = run("let x; for (let i = 0; i < 2; i = i + 1) { x = i; }")
        self.assertEqual(env.get("x"), 1)

    def test_for_c_else_unbraced_statement_runs(self):
        env = run("let x = 0; for (let i = 0; i < 1; i = i + 1) { } else x = 1;")
        self.assertEqual(env.get("x"), 1)

    def test_for_c_else_sees_final_init_declared_binding(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let fns = []; "
            "for (let i = 0; i < 3; i = i + 1) { } "
            "else { fns = push(fns, fn() { return i; }); } "
            "let result = fns[0]();",
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), 3)


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

    def test_named_function_expression_self_reference_recursion(self):
        env = run(
            "let f = fn fact(n) { return n <= 1 ? 1 : n * fact(n - 1); }; "
            "let result = f(5);"
        )
        self.assertEqual(env.get("result"), 120)

    def test_named_function_expression_self_reference_survives_reassignment(self):
        env = run(
            "let g = fn fact(n) { return n <= 1 ? 1 : n * fact(n - 1); }; "
            "let h = g; g = nil; "
            "let result = h(5);"
        )
        self.assertEqual(env.get("result"), 120)

    def test_named_function_expression_works_as_call_argument(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let result = map([1, 2, 3], fn double(x) { return x * 2; });",
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), [2, 4, 6])

    def test_named_function_expression_parameter_shadows_self_binding(self):
        env = run("let f = fn f(f) { return f + 1; }; let result = f(10);")
        self.assertEqual(env.get("result"), 11)

    def test_fn_declaration_at_statement_position_unaffected(self):
        env = run("fn standalone() { return 1; } let result = standalone();")
        self.assertEqual(env.get("result"), 1)

    def test_named_function_expression_arity_error_uses_given_name(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"fact\(\) expects 1 argument\(s\), got 0"
        ):
            run("let f = fn fact(n) { return n; }; f();")

    def test_anonymous_function_expression_arity_error_still_says_anonymous(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"<anonymous>\(\) expects 1 argument\(s\), got 0"
        ):
            run("let f = fn(n) { return n; }; f();")

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


class TestDestructuringParams(unittest.TestCase):
    def test_list_destructuring_param(self):
        env = run(
            "fn dist([x, y]) { return x * x + y * y; } "
            "let result = dist([3, 4]);"
        )
        self.assertEqual(env.get("result"), 25)

    def test_map_destructuring_param(self):
        from cinder.builtins import create_global_environment

        env = run(
            'fn describe({name, age}) { return name + " is " + str(age); } '
            'let result = describe({"name": "Al", "age": 30});',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), "Al is 30")

    def test_map_destructuring_param_key_rename(self):
        env = run('fn f({a: x}) { return x; } let result = f({"a": 9});')
        self.assertEqual(env.get("result"), 9)

    def test_list_destructuring_param_with_rest_element(self):
        env = run(
            "fn f([a, ...rest]) { return rest; } let result = f([1, 2, 3]);"
        )
        self.assertEqual(env.get("result"), [2, 3])

    def test_map_destructuring_param_with_rest_element(self):
        env = run(
            'fn f({a, ...rest}) { return rest; } '
            'let result = f({"a": 1, "b": 2, "c": 3});'
        )
        self.assertEqual(env.get("result"), {"b": 2, "c": 3})

    def test_list_destructuring_param_combined_with_trailing_rest_param(self):
        env = run(
            "fn f([a, b], ...more) { return [a, b, more]; } "
            "let result = f([1, 2], 3, 4);"
        )
        self.assertEqual(env.get("result"), [1, 2, [3, 4]])

    def test_anonymous_function_with_list_destructuring_param(self):
        env = run(
            "let f = fn([a, b]) { return a + b; }; let result = f([1, 2]);"
        )
        self.assertEqual(env.get("result"), 3)

    def test_arrow_function_with_list_destructuring_param(self):
        env = run("let result = (([a, b]) => a + b)([1, 2]);")
        self.assertEqual(env.get("result"), 3)

    def test_list_destructuring_param_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f([a, b]) { return a; } f(5);")
        self.assertEqual(ctx.exception.message, "cannot destructure int as a list")

    def test_map_destructuring_param_missing_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f({a, b}) { return a; } f({"a": 1});')
        self.assertEqual(
            ctx.exception.message,
            "destructuring pattern expects key 'b', not found in map",
        )

    def test_plain_params_defaults_and_rest_still_work_alongside_destructuring(self):
        env = run(
            "fn f(a, b = 1, ...rest) { return [a, b, rest]; } "
            "let result = f(9);"
        )
        self.assertEqual(env.get("result"), [9, 1, []])

    def test_list_destructuring_param_whole_pattern_default_used_when_omitted(self):
        env = run(
            "fn f([a, b] = [1, 2]) { return a + b; } let result = f();"
        )
        self.assertEqual(env.get("result"), 3)

    def test_list_destructuring_param_whole_pattern_default_unused_when_supplied(self):
        env = run(
            "fn f([a, b] = [1, 2]) { return a + b; } let result = f([5, 6]);"
        )
        self.assertEqual(env.get("result"), 11)

    def test_list_destructuring_param_whole_pattern_default_combines_with_preceding_plain_param(self):
        env = run(
            "fn f(a, [b, c] = [1, 2]) { return [a, b, c]; } "
            "let omitted = f(9); let supplied = f(9, [5, 6]);"
        )
        self.assertEqual(env.get("omitted"), [9, 1, 2])
        self.assertEqual(env.get("supplied"), [9, 5, 6])

    def test_list_destructuring_param_whole_pattern_default_followed_by_defaulted_param(self):
        env = run(
            "fn f([a, b] = [1, 2], c = 3) { return [a, b, c]; } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_list_destructuring_param_trailing_comma(self):
        env = run("fn f([a, b,]) { return a + b; } let result = f([1, 2]);")
        self.assertEqual(env.get("result"), 3)

    def test_map_destructuring_param_trailing_comma(self):
        env = run(
            'fn f({a, b,}) { return a + b; } '
            'let result = f({"a": 1, "b": 2});'
        )
        self.assertEqual(env.get("result"), 3)


class TestArrowFunctions(unittest.TestCase):
    def test_one_param(self):
        env = run("let double = (x) => x * 2; let result = double(21);")
        self.assertEqual(env.get("result"), 42)

    def test_two_params(self):
        env = run("let add = (a, b) => a + b; let result = add(2, 3);")
        self.assertEqual(env.get("result"), 5)

    def test_zero_params(self):
        env = run("let always_42 = () => 42; let result = always_42();")
        self.assertEqual(env.get("result"), 42)

    def test_default_param_used_when_argument_omitted(self):
        env = run("let f = (x, y = 10) => x + y; let result = f(5);")
        self.assertEqual(env.get("result"), 15)

    def test_rest_param(self):
        env = run("let f = (a, ...rest) => rest; let result = f(1, 2, 3);")
        self.assertEqual(env.get("result"), [2, 3])

    def test_ternary_body(self):
        env = run('let f = (x) => x > 0 ? "pos" : "neg"; let result = f(5);')
        self.assertEqual(env.get("result"), "pos")

    def test_ordinary_grouping_unaffected(self):
        env = run("let result = (1 + 2) * 3;")
        self.assertEqual(env.get("result"), 9)

    def test_bare_identifier_in_parens_still_evaluates(self):
        env = run("let x = 5; let result = (x);")
        self.assertEqual(env.get("result"), 5)

    def test_nests_and_closes_over_outer_param(self):
        env = run(
            "let make_adder = (n) => (x) => x + n; "
            "let result = make_adder(10)(5);"
        )
        self.assertEqual(env.get("result"), 15)

    def test_as_callback_to_map_builtin(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let result = map([1, 2, 3], (x) => x * x);",
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), [1, 4, 9])

    def test_bare_identifier_one_param(self):
        env = run("let double = x => x * 2; let result = double(5);")
        self.assertEqual(env.get("result"), 10)

    def test_bare_identifier_as_map_builtin_callback(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let square = n => n * n; let result = map([1, 2, 3], square);",
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), [1, 4, 9])

    def test_bare_identifier_ternary_body(self):
        env = run('let f = x => x > 0 ? "pos" : "neg"; let result = f(-3);')
        self.assertEqual(env.get("result"), "neg")

    def test_bare_identifier_nests_and_closes_over_outer_param(self):
        env = run("let adder = x => (y => x + y); let result = adder(3)(4);")
        self.assertEqual(env.get("result"), 7)

    def test_bare_identifier_without_arrow_still_evaluates_as_identifier(self):
        env = run("let x = 5; let result = x;")
        self.assertEqual(env.get("result"), 5)

    def test_bare_identifier_arrow_block_body_executes(self):
        env = run("let f = x => { let y = x * 2; return y; }; let result = f(5);")
        self.assertEqual(env.get("result"), 10)

    def test_parenthesized_arrow_block_body_executes(self):
        env = run("let f = (x) => { let y = x * 2; return y; }; let result = f(5);")
        self.assertEqual(env.get("result"), 10)

    def test_zero_param_block_body(self):
        env = run("let f = () => { return 42; }; let result = f();")
        self.assertEqual(env.get("result"), 42)

    def test_block_body_multi_statement_control_flow(self):
        env = run(
            "let f = (a, b) => { if (a > b) { return a; } return b; }; "
            "let result = f(3, 7);"
        )
        self.assertEqual(env.get("result"), 7)

    def test_block_body_no_implicit_return(self):
        env = run("let f = (x) => { x * 2; }; let result = f(5);")
        self.assertIsNone(env.get("result"))

    def test_block_body_as_map_builtin_callback(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let result = map([1, 2, 3], x => { return x * x; });",
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), [1, 4, 9])

    def test_block_body_nested_arrows_close_over_outer_param(self):
        env = run(
            "let adder = (x) => { return (y) => { return x + y; }; }; "
            "let result = adder(3)(4);"
        )
        self.assertEqual(env.get("result"), 7)

    def test_block_body_break_continue_resolve_to_own_loop(self):
        env = run(
            "let f = () => { "
            "  let total = 0; "
            "  for i in [1, 2, 3, 4, 5] { "
            "    if (i == 4) { break; } "
            "    if (i == 2) { continue; } "
            "    total = total + i; "
            "  } "
            "  return total; "
            "}; "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 4)

    def test_expression_bodied_arrows_unaffected(self):
        env = run("let f = (x) => x * 2; let result = f(5);")
        self.assertEqual(env.get("result"), 10)
        env2 = run("let g = x => x * 2; let result = g(5);")
        self.assertEqual(env2.get("result"), 10)


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


class TestKeywordCallArguments(unittest.TestCase):
    def test_all_keyword_arguments_order_independent(self):
        env = run(
            "fn greet(name, greeting = \"hi\") { return greeting + \", \" + name; } "
            "let result = greet(name: \"Ada\", greeting: \"yo\");"
        )
        self.assertEqual(env.get("result"), "yo, Ada")

    def test_keyword_arguments_bind_by_declaration_order(self):
        env = run(
            "fn f(a, b) { return a - b; } let result = f(b: 1, a: 5);"
        )
        self.assertEqual(env.get("result"), 4)

    def test_leading_positional_with_trailing_keyword(self):
        env = run(
            "fn f(a, b) { return a - b; } let result = f(5, b: 1);"
        )
        self.assertEqual(env.get("result"), 4)

    def test_keyword_omitted_trailing_parameter_uses_default(self):
        env = run(
            "fn f(a, b = 10) { return a + b; } let result = f(a: 3);"
        )
        self.assertEqual(env.get("result"), 13)

    def test_duplicate_positional_and_keyword_raises_multiple_values(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, b) { return a; } f(1, a: 2);")
        self.assertIn("f() got multiple values for parameter 'a'", str(ctx.exception))

    def test_unexpected_keyword_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a) { return a; } f(a: 1, z: 2);")
        self.assertIn("f() got an unexpected keyword argument 'z'", str(ctx.exception))

    def test_missing_required_argument_via_keyword_call_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, b) { return a; } f(a: 1);")
        self.assertIn("f() missing required argument(s): 'b'", str(ctx.exception))

    def test_destructuring_parameter_has_no_addressable_keyword_name(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f([a, b]) { return a; } f(a: 1);")
        self.assertIn("f() got an unexpected keyword argument 'a'", str(ctx.exception))

    def test_map_destructuring_parameter_has_no_addressable_keyword_name(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f({a, b}) { return a; } f(a: 1);")
        self.assertIn("f() got an unexpected keyword argument 'a'", str(ctx.exception))

    def test_rest_parameter_has_no_addressable_keyword_name(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, ...rest) { return a; } f(a: 1, rest: 2);")
        self.assertIn(
            "f() got an unexpected keyword argument 'rest'", str(ctx.exception)
        )

    def test_duplicate_keyword_argument_in_same_call_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a) { return a; } f(a: 1, a: 2);')
        self.assertIn("duplicate keyword argument 'a' in call", str(ctx.exception))

    def test_existing_purely_positional_calls_unaffected(self):
        env = run("fn f(a, b) { return a + b; } let result = f(1, 2);")
        self.assertEqual(env.get("result"), 3)


class TestKeywordOnlyParameters(unittest.TestCase):
    def test_keyword_only_parameter_supplied_by_name(self):
        env = run(
            'fn greet(name, *, loud) { return loud ? name + "!" : name; } '
            'let result = greet("Ada", loud: true);'
        )
        self.assertEqual(env.get("result"), "Ada!")

    def test_keyword_only_parameter_cannot_be_passed_positionally(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run(
                'fn greet(name, *, loud) { return loud ? name + "!" : name; } '
                'greet("Ada", true);'
            )
        self.assertIn("greet() expects 1 argument(s), got 2", str(ctx.exception))

    def test_keyword_only_parameter_default_applies_when_omitted(self):
        env = run("fn f(a, *, b = 1) { return a + b; } let result = f(1);")
        self.assertEqual(env.get("result"), 2)

    def test_keyword_only_parameter_default_overridden_by_keyword(self):
        env = run("fn f(a, *, b = 1) { return a + b; } let result = f(1, b: 5);")
        self.assertEqual(env.get("result"), 6)

    def test_defaulted_keyword_only_param_may_precede_required_one(self):
        env = run("fn f(a, *, b = 1, c) { return a + c; } let result = f(1, c: 2);")
        self.assertEqual(env.get("result"), 3)

    def test_star_as_first_entry_makes_every_parameter_keyword_only(self):
        env = run("fn f(*, a) { return a; } let result = f(a: 1);")
        self.assertEqual(env.get("result"), 1)

    def test_missing_required_keyword_only_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a, *, b) { return a; } f(1);")
        self.assertIn("f() missing required argument(s): 'b'", str(ctx.exception))

    def test_ordinary_default_parameters_unaffected(self):
        env = run("fn f(a, b = 1) { return a + b; } let result = f(1);")
        self.assertEqual(env.get("result"), 2)

    def test_ordinary_rest_parameter_unaffected(self):
        env = run("fn f(a, ...rest) { return rest; } let result = f(1, 2, 3);")
        self.assertEqual(env.get("result"), [2, 3])


class TestMapSpreadCallArguments(unittest.TestCase):
    def test_map_spread_as_keyword_arguments(self):
        env = run(
            'fn greet(name, greeting) { return greeting + ", " + name; } '
            'let result = greet(...{"name": "Ada", "greeting": "yo"});'
        )
        self.assertEqual(env.get("result"), "yo, Ada")

    def test_map_spread_key_order_independent(self):
        env = run(
            'fn greet(name, greeting) { return greeting + ", " + name; } '
            'let result = greet(...{"greeting": "yo", "name": "Ada"});'
        )
        self.assertEqual(env.get("result"), "yo, Ada")

    def test_map_spread_combines_with_leading_positional(self):
        env = run('fn f(a, b) { return a - b; } let result = f(5, ...{"b": 1});')
        self.assertEqual(env.get("result"), 4)

    def test_map_spread_omitted_trailing_parameter_uses_default(self):
        env = run('fn f(a, b = 10) { return a + b; } let result = f(...{"a": 3});')
        self.assertEqual(env.get("result"), 13)

    def test_map_spread_duplicate_with_positional_raises_multiple_values(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a, b) { return a; } f(1, ...{"a": 2});')
        self.assertIn("f() got multiple values for parameter 'a'", str(ctx.exception))

    def test_map_spread_unexpected_keyword_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a) { return a; } f(...{"a": 1, "z": 2});')
        self.assertIn("f() got an unexpected keyword argument 'z'", str(ctx.exception))

    def test_map_spread_missing_required_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a, b) { return a; } f(...{"a": 1});')
        self.assertIn("f() missing required argument(s): 'b'", str(ctx.exception))

    def test_map_spread_duplicate_with_explicit_keyword_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a) { return a; } f(...{"a": 1}, a: 2);')
        self.assertIn("duplicate keyword argument 'a' in call", str(ctx.exception))

    def test_two_map_spreads_colliding_raises_duplicate(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a) { return a; } f(...{"a": 1}, ...{"a": 2});')
        self.assertIn("duplicate keyword argument 'a' in call", str(ctx.exception))

    def test_map_spread_with_non_string_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f(a) { return a; } f(...{1: "x"});')
        self.assertIn(
            "cannot spread map with non-string key 1 as keyword arguments",
            str(ctx.exception),
        )

    def test_list_spread_regression_unaffected(self):
        env = run(
            "fn f(a, b, c) { return a + b + c; } let result = f(...[1, 2, 3]);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_non_list_non_map_spread_regression_unaffected(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("fn f(a) { return a; } f(...5);")
        self.assertIn("cannot spread int in a function call", str(ctx.exception))

    def test_optional_call_map_spread_shares_call_argument_evaluation(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('fn f() { return 1; } f?.(...{"a": 1});')
        self.assertIn("f() got an unexpected keyword argument 'a'", str(ctx.exception))


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

    def test_map_literal_shorthand_property(self):
        env = run('let a = 1; let b = 2; let m = {a, b};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_map_literal_shorthand_single_entry(self):
        env = run('let a = 1; let m = {a};')
        self.assertEqual(env.get("m"), {"a": 1})

    def test_map_literal_shorthand_with_trailing_comma(self):
        env = run('let a = 1; let m = {a,};')
        self.assertEqual(env.get("m"), {"a": 1})

    def test_map_literal_explicit_key_unaffected_by_shorthand(self):
        env = run('let a = 1; let m = {a: 5};')
        self.assertEqual(env.get("m"), {1: 5})

    def test_map_literal_shorthand_mixed_with_explicit_pairs(self):
        env = run('let a = 1; let b = 2; let m = {a, "c": 3, b};')
        self.assertEqual(env.get("m"), {"a": 1, "c": 3, "b": 2})

    def test_map_literal_shorthand_composes_with_spread(self):
        env = run('let a = 1; let m = {a, ...{"b": 2}};')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_map_literal_shorthand_statement_unaffected(self):
        run('let a = 1; let b = 2; {a, b};')  # ExprStmt(MapLiteral), no destructuring

    def test_map_literal_shorthand_undefined_name_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('{undefined_var};')
        self.assertIn("undefined name", str(ctx.exception))

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


class TestListComprehension(unittest.TestCase):
    def test_basic_transform(self):
        self.assertEqual(evaluate("[x * 2 for x in [1, 2, 3]]"), [2, 4, 6])

    def test_filter_clause(self):
        self.assertEqual(
            evaluate("[x for x in [0,1,2,3,4,5,6,7,8,9] if x % 2 == 0]"),
            [0, 2, 4, 6, 8],
        )

    def test_empty_iterable_gives_empty_result(self):
        self.assertEqual(evaluate("[x for x in []]"), [])

    def test_filter_excludes_everything_gives_empty_result(self):
        self.assertEqual(evaluate("[x for x in [1, 2, 3] if x > 10]"), [])

    def test_string_iterable(self):
        self.assertEqual(evaluate('["-" + c for c in "abc"]'), ["-a", "-b", "-c"])

    def test_map_iterable_yields_keys(self):
        self.assertEqual(evaluate('[k for k in {"a": 1, "b": 2}]'), ["a", "b"])

    def test_closure_captures_its_own_iteration_value(self):
        env = run(
            "let fns = [fn() { return x; } for x in [1, 2, 3]]; "
            "let a = fns[0](); "
            "let c = fns[2]();"
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)

    def test_non_iterable_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("[x for x in 5]")
        self.assertIn(
            "'for'-in loop requires a list, string, or map, got int",
            str(ctx.exception),
        )

    def test_plain_list_literal_unaffected(self):
        self.assertEqual(evaluate("[1, 2, 3]"), [1, 2, 3])
        self.assertEqual(evaluate("[...[1, 2], 3]"), [1, 2, 3])
        self.assertEqual(evaluate("[]"), [])

    def test_destructures_pairs_from_items(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let out = [k + "=" + str(v) for [k, v] in items({"a": 1, "b": 2})];',
            create_global_environment(),
        )
        self.assertEqual(env.get("out"), ["a=1", "b=2"])

    def test_destructures_over_list_of_lists(self):
        self.assertEqual(
            evaluate("[a + b for [a, b] in [[1, 2], [3, 4], [5, 6]]]"), [3, 7, 11]
        )

    def test_destructure_with_rest(self):
        self.assertEqual(
            evaluate("[a for [a, ...rest] in [[1, 2, 3], [4, 5]]]"), [1, 4]
        )
        self.assertEqual(
            evaluate("[rest for [a, ...rest] in [[1, 2, 3], [4, 5]]]"),
            [[2, 3], [5]],
        )

    def test_destructure_non_list_item_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("[x for [a, b] in [[1, 2], 3]]")

    def test_destructure_with_filter(self):
        self.assertEqual(
            evaluate("[a for [a, b] in [[1, 2], [3, 4]] if a > 1]"), [3]
        )

    def test_map_destructures_pairs_from_maps(self):
        self.assertEqual(
            evaluate('[a + b for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}]]'),
            [3, 7],
        )

    def test_map_destructure_with_filter(self):
        self.assertEqual(
            evaluate('[a for {a, b} in [{"a": 1, "b": 2}] if b > 1]'), [1]
        )

    def test_map_destructure_missing_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('[a for {a} in [{"a": 1}, {"b": 2}]]')
        self.assertEqual(
            ctx.exception.message,
            "destructuring pattern expects key 'a', not found in map",
        )

    def test_map_destructure_non_map_item_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("[a for {a} in [1, 2]]")
        self.assertEqual(ctx.exception.message, "cannot destructure int as a map")

    def test_map_destructure_with_rest(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let out = [a + len(rest) for {a, ...rest} in '
            '[{"a": 1, "b": 2}, {"a": 3, "c": 4, "d": 5}]];',
            create_global_environment(),
        )
        self.assertEqual(env.get("out"), [2, 5])

    def test_map_destructure_key_rename(self):
        self.assertEqual(
            evaluate('[x for {a: x} in [{"a": 1}, {"a": 2}]]'), [1, 2]
        )

    def test_list_destructure_trailing_comma(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let out = [k for [k, v,] in items({"a": 1})];',
            create_global_environment(),
        )
        self.assertEqual(env.get("out"), ["a"])

    def test_map_destructure_trailing_comma(self):
        self.assertEqual(
            evaluate('[a for {a, b,} in [{"a": 1, "b": 2}]]'), [1]
        )

    def test_two_for_clauses_cartesian_product(self):
        self.assertEqual(
            evaluate("[x + y for x in [1, 2] for y in [10, 20]]"),
            [11, 21, 12, 22],
        )

    def test_second_clause_filter_uses_own_variable(self):
        self.assertEqual(
            evaluate("[[x, y] for x in [1, 2] for y in [1, 2] if x != y]"),
            [[1, 2], [2, 1]],
        )

    def test_empty_inner_iterable_gives_empty_result(self):
        self.assertEqual(evaluate("[x for x in [1, 2] for y in []]"), [])

    def test_three_for_clauses(self):
        self.assertEqual(
            evaluate("[x + y + z for x in [1] for y in [10] for z in [100]]"),
            [111],
        )

    def test_destructure_pattern_in_non_final_clause(self):
        self.assertEqual(
            evaluate("[a + b for [a] in [[1], [2]] for b in [10, 20]]"),
            [11, 21, 12, 22],
        )

    def test_condition_on_non_final_clause_filters_before_later_clauses_run(self):
        self.assertEqual(
            evaluate("[[x, y] for x in [1, 2, 3] if x > 1 for y in [10, 20]]"),
            [[2, 10], [2, 20], [3, 10], [3, 20]],
        )

    def test_single_clause_form_unchanged(self):
        self.assertEqual(evaluate("[x for x in [1, 2, 3]]"), [1, 2, 3])


class TestMapComprehension(unittest.TestCase):
    def test_basic_transform(self):
        self.assertEqual(
            evaluate("{x: x * x for x in [1, 2, 3]}"), {1: 1, 2: 4, 3: 9}
        )

    def test_filter_clause(self):
        from cinder.builtins import create_global_environment

        env = run(
            "let m = {x: x for x in range(5) if x % 2 == 0};",
            create_global_environment(),
        )
        self.assertEqual(env.get("m"), {0: 0, 2: 2, 4: 4})

    def test_empty_iterable_gives_empty_result(self):
        self.assertEqual(evaluate("{x: x for x in []}"), {})

    def test_key_and_value_are_independent_expressions(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let m = {k: len(k) for k in ["a", "bb", "ccc"]};',
            create_global_environment(),
        )
        self.assertEqual(env.get("m"), {"a": 1, "bb": 2, "ccc": 3})

    def test_colliding_keys_collapse_to_last_write(self):
        self.assertEqual(evaluate("{x: 1 for x in [1, 1, 2]}"), {1: 1, 2: 1})

    def test_closure_captures_its_own_iteration_value(self):
        env = run(
            "let m = {x: fn() { return x; } for x in [1, 2, 3]}; "
            "let a = m[1](); "
            "let c = m[3]();"
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("c"), 3)

    def test_non_iterable_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("{k: v for k in 5}")
        self.assertIn(
            "'for'-in loop requires a list, string, or map, got int",
            str(ctx.exception),
        )

    def test_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("{k: k for k in [[1], [2]]}")
        self.assertIn("list is not a valid map key", str(ctx.exception))

    def test_plain_map_literal_unaffected(self):
        self.assertEqual(evaluate('{"a": 1, "b": 2}'), {"a": 1, "b": 2})
        self.assertEqual(evaluate('{...{"a": 1}, "b": 2}'), {"a": 1, "b": 2})

    def test_destructures_pairs_from_items(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let out = {k: v * 2 for [k, v] in items({"a": 1, "b": 2})};',
            create_global_environment(),
        )
        self.assertEqual(env.get("out"), {"a": 2, "b": 4})

    def test_destructure_non_list_item_raises(self):
        with self.assertRaises(CinderRuntimeError):
            evaluate("{k: v for [k, v] in [[1, 2], 3]}")

    def test_destructure_with_filter(self):
        self.assertEqual(
            evaluate('{k: v for [k, v] in [["a", 1], ["b", 2]] if v > 1}'),
            {"b": 2},
        )
        self.assertEqual(evaluate("{}"), {})

    def test_map_destructures_pairs_from_maps(self):
        self.assertEqual(
            evaluate('{a: b for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}'),
            {1: 2, 3: 4},
        )

    def test_map_destructure_missing_key_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate('{a: a for {a} in [{"a": 1}, {"b": 2}]}')
        self.assertEqual(
            ctx.exception.message,
            "destructuring pattern expects key 'a', not found in map",
        )

    def test_map_destructure_non_map_item_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            evaluate("{a: a for {a} in [1, 2]}")
        self.assertEqual(ctx.exception.message, "cannot destructure int as a map")

    def test_map_destructure_with_rest(self):
        self.assertEqual(
            evaluate(
                '{a: rest for {a, ...rest} in '
                '[{"a": 1, "b": 2}, {"a": 3, "c": 4}]}'
            ),
            {1: {"b": 2}, 3: {"c": 4}},
        )

    def test_map_destructure_key_rename(self):
        self.assertEqual(
            evaluate('{x: x for {a: x} in [{"a": 1}, {"a": 2}]}'),
            {1: 1, 2: 2},
        )

    def test_two_for_clauses_later_combination_overwrites_earlier_on_collision(self):
        self.assertEqual(
            evaluate('{x: y for x in ["a", "b"] for y in [1, 2]}'),
            {"a": 2, "b": 2},
        )

    def test_single_clause_form_unchanged(self):
        self.assertEqual(
            evaluate("{x: x * 2 for x in [1, 2]}"), {1: 2, 2: 4}
        )


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

    def test_slice_assignment_grows_list_when_replacement_is_longer(self):
        env = run("let xs = [1, 2, 3, 4, 5]; xs[1:3] = [9, 9, 9];")
        self.assertEqual(env.get("xs"), [1, 9, 9, 9, 4, 5])

    def test_slice_assignment_with_empty_list_deletes_range(self):
        env = run("let xs = [1, 2, 3, 4, 5]; xs[1:3] = [];")
        self.assertEqual(env.get("xs"), [1, 4, 5])

    def test_slice_assignment_omitted_bounds_spans_whole_list(self):
        env = run("let xs = [1, 2, 3]; xs[:] = [9];")
        self.assertEqual(env.get("xs"), [9])

    def test_slice_assignment_out_of_range_bounds_clamp(self):
        env = run("let xs = [1, 2, 3]; xs[5:10] = [9];")
        self.assertEqual(env.get("xs"), [1, 2, 3, 9])

    def test_slice_assignment_negative_bounds_normalize(self):
        env = run("let xs = [1, 2, 3, 4, 5]; xs[-2:] = [9];")
        self.assertEqual(env.get("xs"), [1, 2, 3, 9])

    def test_slice_assignment_evaluates_to_assigned_value(self):
        env = run("let xs = [1, 2, 3]; let result = (xs[0:1] = [9, 9]);")
        self.assertEqual(env.get("result"), [9, 9])

    def test_slice_assignment_non_list_value_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "slice assignment requires a list value, got int"
        ):
            run("let xs = [1, 2, 3]; xs[0:1] = 5;")

    def test_slice_assignment_on_string_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            "strings are immutable and do not support item assignment",
        ):
            run('let s = "abc"; s[0:1] = "x";')


    def test_extended_slice_assignment_replaces_stepped_positions(self):
        env = run(
            "let xs = [1, 2, 3, 4, 5, 6]; xs[0:6:2] = [9, 9, 9];"
        )
        self.assertEqual(env.get("xs"), [9, 2, 9, 4, 9, 6])

    def test_extended_slice_assignment_negative_step_reverses_target(self):
        env = run("let xs = [1, 2, 3]; xs[::-1] = [7, 8, 9];")
        self.assertEqual(env.get("xs"), [9, 8, 7])

    def test_extended_slice_assignment_length_mismatch_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"attempt to assign sequence of size 1 to extended slice of size 2",
        ):
            run("let xs = [1, 2, 3, 4]; xs[0:4:2] = [1];")

    def test_slice_assignment_explicit_step_one_still_grows(self):
        env = run("let xs = [1, 2, 3]; xs[0:2:1] = [9, 9, 9, 9];")
        self.assertEqual(env.get("xs"), [9, 9, 9, 9, 3])

    def test_extended_slice_assignment_non_list_value_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "slice assignment requires a list value, got str"
        ):
            run('let xs = [1, 2, 3, 4, 5]; xs[0:5:2] = "ab";')

    def test_slice_assignment_non_int_step_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "slice step must be an int, got str"
        ):
            run('let xs = [1, 2, 3]; xs[0:3:"a"] = [1, 2, 3];')

    def test_slice_assignment_zero_step_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, "slice step must not be zero"
        ):
            run("let xs = [1, 2, 3]; xs[0:3:0] = [1, 2, 3];")

    def test_stepped_slice_assignment_on_string_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            "strings are immutable and do not support item assignment",
        ):
            run('let s = "abcdef"; s[0:6:2] = "xyz";')

    def test_slice_compound_assign_still_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            run("[1, 2, 3][0:1] += [9];")

    def test_slice_increment_still_raises_parse_error(self):
        from cinder.errors import ParseError

        with self.assertRaises(ParseError):
            run("[1, 2, 3][0:1]++;")

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

    def test_slice_with_step_assignment_raises_length_mismatch(self):
        with self.assertRaisesRegex(
            CinderRuntimeError,
            r"attempt to assign sequence of size 1 to extended slice of size 2",
        ):
            run("[1, 2, 3][::2] = [9];")


class TestRangeLiteral(unittest.TestCase):
    def test_range_produces_list_matching_range_builtin(self):
        self.assertEqual(evaluate("1..5"), [1, 2, 3, 4])

    def test_range_empty_when_bounds_equal(self):
        self.assertEqual(evaluate("0..0"), [])

    def test_range_descending_bounds_produce_empty_list(self):
        self.assertEqual(evaluate("5..1"), [])

    def test_range_usable_in_for_loop(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run("for i in 1..5 { print(i); }", create_global_environment())
        self.assertEqual(stdout.getvalue(), "1\n2\n3\n4\n")

    def test_range_in_membership_test(self):
        self.assertEqual(evaluate("3 in 1..5"), True)
        self.assertEqual(evaluate("5 in 1..5"), False)

    def test_range_binds_looser_than_arithmetic(self):
        self.assertEqual(evaluate("1 + 1..5 * 2"), [2, 3, 4, 5, 6, 7, 8, 9])

    def test_range_equals_range_builtin(self):
        from cinder.builtins import create_global_environment

        env = run("let result = range(1, 5) == 1..5;", create_global_environment())
        self.assertEqual(env.get("result"), True)

    def test_range_usable_as_comprehension_source(self):
        self.assertEqual(evaluate("[x for x in 1..5]"), [1, 2, 3, 4])

    def test_range_non_int_bound_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"range\(\) requires int arguments, got float"
        ):
            evaluate("1..2.5")

    def test_range_step_does_not_chain(self):
        with self.assertRaises(ParseError):
            run("1..5..10..15;")

    def test_range_with_step_skips_elements(self):
        self.assertEqual(evaluate("1..10..2"), [1, 3, 5, 7, 9])

    def test_range_with_negative_step_counts_down(self):
        self.assertEqual(evaluate("10..0..-2"), [10, 8, 6, 4, 2])

    def test_inclusive_range_with_step_reaches_upper_bound(self):
        self.assertEqual(evaluate("0..=10..2"), [0, 2, 4, 6, 8, 10])

    def test_inclusive_range_with_step_not_landing_on_bound(self):
        self.assertEqual(evaluate("0..=9..2"), [0, 2, 4, 6, 8])

    def test_inclusive_range_with_negative_step_counts_down(self):
        self.assertEqual(evaluate("10..=0..-2"), [10, 8, 6, 4, 2, 0])

    def test_inclusive_range_with_negative_step_landing_on_bound(self):
        self.assertEqual(evaluate("10..=1..-3"), [10, 7, 4, 1])

    def test_range_with_step_usable_in_for_loop(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run("for x in 1..10..2 { print(x); }", create_global_environment())
        self.assertEqual(stdout.getvalue(), "1\n3\n5\n7\n9\n")

    def test_range_with_step_usable_as_comprehension_source(self):
        self.assertEqual(evaluate("[x for x in 0..10..3]"), [0, 3, 6, 9])

    def test_range_step_zero_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"range\(\) step must not be zero"
        ):
            evaluate("1..10..0")

    def test_range_non_int_step_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"range\(\) requires int arguments, got float"
        ):
            evaluate("1..10..1.5")

    def test_range_without_step_unaffected(self):
        self.assertEqual(evaluate("1..10"), [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(evaluate("1..=10"), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_inclusive_range_includes_upper_bound(self):
        self.assertEqual(evaluate("1..=5"), [1, 2, 3, 4, 5])

    def test_exclusive_range_unaffected_by_inclusive_addition(self):
        self.assertEqual(evaluate("1..5"), [1, 2, 3, 4])

    def test_inclusive_range_single_element_when_bounds_equal(self):
        self.assertEqual(evaluate("5..=5"), [5])

    def test_inclusive_range_descending_bounds_produce_empty_list(self):
        self.assertEqual(evaluate("5..=1"), [])

    def test_inclusive_range_in_membership_test(self):
        self.assertEqual(evaluate("3 in 1..=5"), True)

    def test_inclusive_range_non_int_end_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"range\(\) requires int arguments, got string"
        ):
            evaluate('1..="5"')

    def test_inclusive_range_bool_start_raises_cinder_error(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"range\(\) requires int arguments, got bool"
        ):
            evaluate("true..=5")

    def test_inclusive_range_does_not_chain(self):
        with self.assertRaises(ParseError):
            run("1..=5..=10;")


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

    def test_nameless_catch_recovers(self):
        env = run('let ran = 0; try { let x = 1 / 0; } catch { ran = 1; }')
        self.assertEqual(env.get("ran"), 1)

    def test_nameless_catch_with_finally_runs_both(self):
        env = run(
            "let caught = 0; let done = 0; "
            "try { let x = 1 / 0; } catch { caught = 1; } "
            "finally { done = 1; }"
        )
        self.assertEqual(env.get("caught"), 1)
        self.assertEqual(env.get("done"), 1)

    def test_nameless_catch_does_not_run_when_no_error(self):
        env = run("let ran = 0; try { 1; } catch { ran = 1; }")
        self.assertEqual(env.get("ran"), 0)

    def test_nameless_catch_block_does_not_leak_scope(self):
        with self.assertRaises(CinderRuntimeError):
            run('try { let x = 1 / 0; } catch { let y = 1; } y;')

    def test_nameless_catch_binds_no_implicit_name(self):
        with self.assertRaises(CinderRuntimeError):
            run('try { let x = 1 / 0; } catch { e; }')

    def test_return_inside_nameless_catch_returns_from_function(self):
        env = run(
            "fn f() { try { let x = 1 / 0; } catch { return 1; } return 2; } "
            "let result = f();"
        )
        self.assertEqual(env.get("result"), 1)

    def test_catch_list_destructure_binds_elements(self):
        env = run(
            "let a = nil; let b = nil; "
            "try { throw [1, 2]; } catch ([x, y]) { a = x; b = y; }"
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_catch_map_destructure_binds_keys(self):
        env = run(
            'let a = nil; let b = nil; '
            'try { throw {"a": 1, "b": 2}; } catch ({a: x, b: y}) { a = x; b = y; }'
        )
        self.assertEqual(env.get("a"), 1)
        self.assertEqual(env.get("b"), 2)

    def test_catch_list_destructure_rest_capture(self):
        env = run(
            "let r = nil; "
            "try { throw [1, 2, 3]; } catch ([x, ...rest]) { r = rest; }"
        )
        self.assertEqual(env.get("r"), [2, 3])

    def test_catch_map_destructure_default(self):
        env = run(
            'let r = nil; '
            'try { throw {"a": 1}; } catch ({a, b = 5}) { r = b; }'
        )
        self.assertEqual(env.get("r"), 5)

    def test_catch_map_destructure_rename(self):
        env = run(
            'let r = nil; '
            'try { throw {"a": 1}; } catch ({a: x}) { r = x; }'
        )
        self.assertEqual(env.get("r"), 1)

    def test_catch_list_destructure_mismatch_propagates_uncaught(self):
        with self.assertRaisesRegex(
            CinderRuntimeError, r"cannot destructure int as a list"
        ):
            run("try { throw 5; } catch ([a]) { }")

    def test_catch_list_destructure_scope_not_visible_after(self):
        with self.assertRaises(CinderRuntimeError):
            run("try { throw [1]; } catch ([a]) {} a;")


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

    def test_throw_map_is_caught_with_original_value(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                'try { throw {"kind": "MyError", "msg": "oops"}; } '
                "catch (e) { print(e.msg); }",
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "oops\n")

    def test_throw_int_keeps_real_type(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                "try { throw 42; } catch (e) { print(e + 1); }",
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "43\n")

    def test_throw_list_keeps_real_type(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                "try { throw [1, 2, 3]; } catch (e) { print(e[1]); }",
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "2\n")

    def test_throw_nil_is_distinguished_from_unset(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                "try { throw nil; } catch (e) { print(e == nil); }",
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "true\n")

    def test_throw_false_is_not_confused_with_unset(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                "try { throw false; } catch (e) { print(e); }",
                create_global_environment(),
            )
        self.assertEqual(out.getvalue(), "false\n")

    def test_uncaught_throw_int_has_message_and_value(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("throw 42;")
        self.assertEqual(ctx.exception.message, "42")
        self.assertEqual(ctx.exception.value, 42)

    def test_uncaught_throw_map_message_matches_print_format(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('throw {"a": 1};')
        self.assertEqual(ctx.exception.message, '{"a": 1}')

    def test_internal_error_value_still_equals_message(self):
        import io
        from contextlib import redirect_stdout

        from cinder.builtins import create_global_environment

        out = io.StringIO()
        with redirect_stdout(out):
            run(
                'try { 1 + "a"; } catch (e) { print(e); }',
                create_global_environment(),
            )
        self.assertEqual(
            out.getvalue(),
            "unsupported operand types for '+': int and string\n",
        )

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

    def test_range_case_matches_value_inside_range(self):
        env = run(
            'let result = "unset"; '
            'switch (5) { case 1..10: { result = "small"; } '
            'default: { result = "other"; } }'
        )
        self.assertEqual(env.get("result"), "small")

    def test_range_case_end_is_exclusive_by_default(self):
        env = run(
            'let result = "unset"; '
            'switch (10) { case 1..10: { result = "in"; } '
            'default: { result = "out"; } }'
        )
        self.assertEqual(env.get("result"), "out")

    def test_inclusive_range_case_includes_end(self):
        env = run(
            'let result = "unset"; '
            'switch (10) { case 1..=10: { result = "in"; } '
            'default: { result = "out"; } }'
        )
        self.assertEqual(env.get("result"), "in")

    def test_range_case_order_still_short_circuits_on_first_match(self):
        env = run(
            'let result = "unset"; '
            'switch (5) { case 100..200: { result = "no"; } '
            'case 1..10: { result = "yes"; } '
            'default: { result = "neither"; } }'
        )
        self.assertEqual(env.get("result"), "yes")

    def test_range_case_composes_with_plain_values_in_same_case(self):
        env = run(
            'let result = "unset"; '
            'switch (5) { case 1..3, 5: { result = "hit"; } '
            'default: { result = "miss"; } }'
        )
        self.assertEqual(env.get("result"), "hit")

    def test_range_case_falls_through_to_default_for_non_numeric_scrutinee(self):
        env = run(
            'let result = "unset"; '
            'switch ("x") { case 1..10: { result = "no"; } '
            'default: { result = "ok"; } }'
        )
        self.assertEqual(env.get("result"), "ok")


class TestMatchExpression(unittest.TestCase):
    def test_first_matching_arm_wins(self):
        env = run('let result = match (2) { 1 => "one", 2 => "two", _ => "other" };')
        self.assertEqual(env.get("result"), "two")

    def test_no_specific_match_runs_wildcard(self):
        env = run('let result = match (5) { 1 => "one", 2 => "two", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_usable_as_let_initializer(self):
        env = run("let x = match (true) { false => 0, true => 1 };")
        self.assertEqual(env.get("x"), 1)

    def test_string_patterns(self):
        env = run('let result = match ("b") { "a" => 1, "b" => 2, "c" => 3 };')
        self.assertEqual(env.get("result"), 2)

    def test_float_pattern_does_not_spuriously_match_int(self):
        env = run(
            'let result = match (1.5) { 1 => "int one", '
            '1.5 => "float one-half", _ => "other" };'
        )
        self.assertEqual(env.get("result"), "float one-half")

    def test_nil_pattern(self):
        env = run('let result = match (nil) { nil => "nothing", _ => "something" };')
        self.assertEqual(env.get("result"), "nothing")

    def test_no_arm_matched_and_no_wildcard_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('match (3) { 1 => "one", 2 => "two" };')

    def test_arrow_functions_unaffected_by_wildcard_handling(self):
        env = run("let double = x => x * 2; let result = double(5);")
        self.assertEqual(env.get("result"), 10)

    def test_bare_underscore_identifier_still_works(self):
        env = run("let _ = 5;")
        self.assertEqual(env.get("_"), 5)

    def test_subject_evaluated_exactly_once(self):
        env = run(
            "let calls = 0; "
            "fn subject() { calls = calls + 1; return 2; } "
            'let result = match (subject()) { 1 => "one", 2 => "two", _ => "other" };'
        )
        self.assertEqual(env.get("calls"), 1)
        self.assertEqual(env.get("result"), "two")

    def test_bound_identifier_arm_matches_and_binds_value(self):
        env = run('let result = match (5) { 0 => "zero", n => n + 1 };')
        self.assertEqual(env.get("result"), 6)

    def test_earlier_literal_arm_wins_over_later_bound_identifier(self):
        env = run('let result = match (0) { 0 => "zero", n => n + 1 };')
        self.assertEqual(env.get("result"), "zero")

    def test_bound_identifier_does_not_leak_into_enclosing_scope(self):
        env = run("let x = 99; match (5) { n => n }; ")
        self.assertEqual(env.get("x"), 99)
        with self.assertRaises(Exception):
            env.get("n")

    def test_bound_identifier_shadows_outer_variable_inside_arm_only(self):
        env = run("let n = 1; let result = match (5) { n => n * 2 };")
        self.assertEqual(env.get("n"), 1)
        self.assertEqual(env.get("result"), 10)

    def test_wildcard_still_binds_nothing(self):
        env = run('let result = match (5) { _ => "wildcard" };')
        self.assertEqual(env.get("result"), "wildcard")

    def test_bound_identifier_works_for_non_numeric_subject(self):
        env = run("let result = match (true) { flag => flag };")
        self.assertEqual(env.get("result"), True)

    def test_multi_value_arm_matches_either_value(self):
        env = run('let result = match (2) { 1, 2 => "one-or-two", _ => "other" };')
        self.assertEqual(env.get("result"), "one-or-two")

    def test_multi_value_arm_falls_through_when_subject_matches_neither(self):
        env = run('let result = match (5) { 1, 2 => "one-or-two", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_multi_value_arm_with_three_patterns(self):
        env = run('let result = match (3) { 1, 2, 3 => "small", _ => "large" };')
        self.assertEqual(env.get("result"), "small")

    def test_multi_value_arm_mixes_literal_types(self):
        env = run(
            'let a = match (nil) { false, nil => "falsy-ish", true => "truthy" };'
            'let b = match (true) { false, nil => "falsy-ish", true => "truthy" };'
        )
        self.assertEqual(env.get("a"), "falsy-ish")
        self.assertEqual(env.get("b"), "truthy")

    def test_multi_value_arm_no_wildcard_raises_when_unmatched(self):
        with self.assertRaises(CinderRuntimeError):
            run('match (5) { 1, 2 => "a" };')

    def test_multi_value_arm_trailing_comma_after_arm(self):
        env = run('let result = match (1) { 1, 2 => "ok", };')
        self.assertEqual(env.get("result"), "ok")

    def test_list_pattern_binds_each_element(self):
        env = run('let result = match ([1, 2]) { [a, b] => a + b, _ => 0 };')
        self.assertEqual(env.get("result"), 3)

    def test_list_pattern_falls_through_to_matching_length(self):
        env = run('let result = match ([1]) { [a, b] => a + b, [a] => a, _ => 0 };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_falls_through_on_longer_subject(self):
        env = run(
            'let result = match ([1, 2, 3]) { [a, b] => a + b, _ => "no match" };'
        )
        self.assertEqual(env.get("result"), "no match")

    def test_list_pattern_falls_through_on_non_list_subject(self):
        env = run('let result = match (5) { [a, b] => a + b, _ => "not a list" };')
        self.assertEqual(env.get("result"), "not a list")

    def test_list_pattern_underscore_discards_position(self):
        env = run('let result = match ([1, 2]) { [_, b] => b, _ => 0 };')
        self.assertEqual(env.get("result"), 2)

    def test_list_pattern_bare_hole_discards_position(self):
        env = run('let result = match ([1, 2, 3]) { [a, , c] => a + c, _ => 0 };')
        self.assertEqual(env.get("result"), 4)

    def test_list_pattern_leading_bare_hole_discards_position(self):
        env = run('let result = match ([1, 2, 3]) { [, b, c] => b + c, _ => 0 };')
        self.assertEqual(env.get("result"), 5)

    def test_list_pattern_bare_hole_composes_with_rest_capture(self):
        env = run(
            'let result = match ([1, 2, 3, 4]) '
            '{ [a, , ...rest] => rest, _ => 0 };'
        )
        self.assertEqual(env.get("result"), [3, 4])

    def test_nested_list_pattern_bare_hole_discards(self):
        env = run(
            'let result = match ([1, [2, 3]]) { [a, [, c]] => a + c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 4)

    def test_list_pattern_bare_hole_without_default_after_defaulted_raises(self):
        with self.assertRaisesRegex(
            ParseError,
            r"element without a default value follows an element with one "
            r"in list pattern",
        ):
            run('match ([1]) { [a = 1, , c] => 0, _ => -1 };')

    def test_empty_list_pattern_matches_only_empty_list(self):
        env = run('let result = match ([]) { [] => "empty", _ => "nonempty" };')
        self.assertEqual(env.get("result"), "empty")

    def test_list_pattern_repeated_name_later_position_wins(self):
        env = run('let result = match ([1, 2]) { [a, a] => a, _ => "dup" };')
        self.assertEqual(env.get("result"), 2)

    def test_list_pattern_bindings_do_not_leak_into_enclosing_scope(self):
        env = run(
            "let a = 100; match ([1, 2]) { [a, b] => a + b, _ => 0 }; "
        )
        self.assertEqual(env.get("a"), 100)

    def test_list_pattern_leading_literal_element_matches_and_binds_rest(self):
        env = run('let result = match ([1, 2]) { [1, b] => b, _ => 0 };')
        self.assertEqual(env.get("result"), 2)

    def test_list_pattern_leading_literal_element_falls_through_on_mismatch(self):
        env = run('let result = match ([9, 2]) { [1, b] => b, _ => 0 };')
        self.assertEqual(env.get("result"), 0)

    def test_list_pattern_literal_element_in_non_leading_position(self):
        env = run('let result = match ([1, 2]) { [a, 2] => a, _ => 0 };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_string_literal_elements_compare_by_value(self):
        env = run(
            'let result = match (["x", 5]) '
            '{ ["x", "y"] => "no", ["x", n] => n, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 5)

    def test_list_pattern_bool_literal_element_matches(self):
        env = run('let result = match ([true, 1]) { [true, n] => n, _ => 0 };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_all_identifier_form_unaffected(self):
        env = run('let result = match ([1, 2]) { [a, b] => a + b, _ => 0 };')
        self.assertEqual(env.get("result"), 3)

    def test_list_pattern_rest_capture_binds_tail(self):
        env = run(
            'let result = match ([1, 2, 3]) { [a, ...rest] => rest, _ => "no" };'
        )
        self.assertEqual(env.get("result"), [2, 3])

    def test_list_pattern_rest_capture_empty_tail(self):
        env = run('let result = match ([1]) { [a, ...rest] => rest, _ => "no" };')
        self.assertEqual(env.get("result"), [])

    def test_list_pattern_rest_capture_two_element_prefix(self):
        env = run(
            'let a = match ([1, 2]) { [a, b, ...rest] => rest, _ => "no" };'
            'let b = match ([1, 2, 3]) { [a, b, ...rest] => rest, _ => "no" };'
        )
        self.assertEqual(env.get("a"), [])
        self.assertEqual(env.get("b"), [3])

    def test_list_pattern_rest_capture_requires_at_least_prefix_length(self):
        env = run('let result = match ([]) { [a, ...rest] => "yes", _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_list_pattern_rest_capture_discarded_with_underscore(self):
        env = run('let result = match ([1, 2, 3]) { [a, ..._] => a, _ => "no" };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_rest_capture_combines_with_literal_entry(self):
        env = run(
            'let a = match ([1, 2, 3]) { [0, b, ...rest] => rest, _ => "no" };'
            'let b = match ([0, 2, 3]) { [0, b, ...rest] => rest, _ => "no" };'
        )
        self.assertEqual(env.get("a"), "no")
        self.assertEqual(env.get("b"), [3])

    def test_list_pattern_rest_capture_falls_through_on_non_list_subject(self):
        env = run('let result = match ("ab") { [a, ...rest] => "yes", _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_list_pattern_without_rest_unaffected_by_rest_capture_feature(self):
        env = run('let result = match ([1, 2]) { [a, b] => a + b, _ => 0 };')
        self.assertEqual(env.get("result"), 3)

    def test_nested_list_pattern_binds_inner_elements(self):
        env = run(
            'let result = match ([1, [2, 3]]) { [a, [b, c]] => a + b + c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 6)

    def test_nested_list_pattern_falls_through_on_length_mismatch(self):
        env = run(
            'let result = match ([1, [2, 3]]) '
            '{ [a, [b, c, d]] => 0, _ => "no" };'
        )
        self.assertEqual(env.get("result"), "no")

    def test_nested_list_pattern_falls_through_on_non_list_subject(self):
        env = run('let result = match ([1, "x"]) { [a, [b, c]] => "yes", _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_nested_list_pattern_at_every_top_level_position(self):
        env = run(
            'let result = match ([[1, 2], [3, 4]]) '
            '{ [[a, b], [c, d]] => a + b + c + d, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 10)

    def test_nested_list_pattern_two_levels_deep(self):
        env = run(
            'let result = match ([1, [2, [3, 4]]]) '
            '{ [a, [b, [c, d]]] => a + b + c + d, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 10)

    def test_nested_list_pattern_coexists_with_literal_element(self):
        env = run(
            'let result = match ([1, [2, 3]]) { [1, [b, c]] => b + c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 5)

    def test_nested_list_pattern_underscore_discards(self):
        env = run(
            'let result = match ([1, [2, 3]]) { [a, [_, c]] => a + c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 4)

    def test_nested_list_pattern_rest_capture(self):
        env = run(
            'let result = match ([1, [2, 3, 4]]) '
            '{ [a, [b, ...rest]] => rest, _ => [] };'
        )
        self.assertEqual(env.get("result"), [3, 4])

    def test_nested_list_pattern_flat_patterns_still_work(self):
        env = run(
            'let a = match ([1, 2]) { [a, b] => a + b, _ => 0 };'
            'let b = match ([1, 2, 3]) { [a, ...rest] => rest, _ => [] };'
        )
        self.assertEqual(env.get("a"), 3)
        self.assertEqual(env.get("b"), [2, 3])

    def test_list_pattern_default_fires_when_subject_short(self):
        env = run('let result = match ([1]) { [a, b = 0] => a + b, _ => -1 };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_default_not_used_when_subject_supplies_value(self):
        env = run('let result = match ([1, 2]) { [a, b = 0] => a + b, _ => -1 };')
        self.assertEqual(env.get("result"), 3)

    def test_list_pattern_multiple_defaults_all_missing(self):
        env = run('let result = match ([]) { [a = 1, b = 2] => a + b, _ => -1 };')
        self.assertEqual(env.get("result"), 3)

    def test_list_pattern_default_falls_through_on_subject_longer_than_max(self):
        env = run('let result = match ([1, 2, 3]) { [a, b = 0] => a + b, _ => -1 };')
        self.assertEqual(env.get("result"), -1)

    def test_list_pattern_default_expression_sees_earlier_binding(self):
        env = run('let result = match ([1]) { [a, b = a + 1] => b, _ => -1 };')
        self.assertEqual(env.get("result"), 2)

    def test_list_pattern_default_composes_with_rest_capture(self):
        env = run(
            'let result = match ([1]) '
            '{ [a, b = 0, ...rest] => [a, b, rest], _ => "no" };'
        )
        self.assertEqual(env.get("result"), [1, 0, []])

    def test_list_pattern_default_composes_with_nested_list_pattern(self):
        env = run('let result = match ([[1]]) { [[a, b = 0]] => a + b, _ => -1 };')
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_default_falls_through_on_non_list_subject(self):
        env = run('let result = match ({"a": 1}) { [a, b = 0] => a + b, _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_list_pattern_element_without_default_after_defaulted_raises(self):
        with self.assertRaisesRegex(
            ParseError,
            r"element without a default value follows an element with one "
            r"in list pattern",
        ):
            run('match (x) { [a = 1, b] => a, _ => 0 };')

    def test_range_pattern_matches_within_bounds(self):
        env = run('let result = match (5) { 1..10 => "small", _ => "large" };')
        self.assertEqual(env.get("result"), "small")

    def test_range_pattern_upper_bound_exclusive(self):
        env = run('let result = match (15) { 1..10 => "small", _ => "large" };')
        self.assertEqual(env.get("result"), "large")

    def test_range_pattern_inclusive_upper_bound(self):
        env = run('let result = match (10) { 1..=10 => "small", _ => "large" };')
        self.assertEqual(env.get("result"), "small")

    def test_range_pattern_lower_bound_inclusive_both_spellings(self):
        env = run('let a = match (1) { 1..10 => "small", _ => "large" };')
        env2 = run('let a = match (1) { 1..=10 => "small", _ => "large" };')
        self.assertEqual(env.get("a"), "small")
        self.assertEqual(env2.get("a"), "small")

    def test_range_pattern_combines_with_literal_patterns(self):
        env = run(
            'let result = match (6) { 1, 5..10, 20 => "matched", _ => "no" };'
        )
        self.assertEqual(env.get("result"), "matched")

    def test_range_pattern_falls_through_on_non_numeric_subject(self):
        env = run('let result = match ("x") { 1..10 => "n", _ => "s" };')
        self.assertEqual(env.get("result"), "s")

    def test_range_pattern_negative_start_matches(self):
        env = run('let result = match (-5) { -10..0 => "neg", _ => "other" };')
        self.assertEqual(env.get("result"), "neg")

    def test_range_pattern_negative_bounds_excludes_below_start(self):
        env = run('let result = match (5) { -10..0 => "neg", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_range_pattern_negative_bounds_upper_bound_exclusive(self):
        env = run('let result = match (0) { -10..0 => "neg", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_range_pattern_negative_bounds_inclusive_upper_bound(self):
        env = run('let result = match (0) { -10..=0 => "neg", _ => "other" };')
        self.assertEqual(env.get("result"), "neg")

    def test_range_pattern_two_negative_bounds_upper_bound_exclusive(self):
        env = run('let result = match (-1) { -10..-1 => "neg", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_range_pattern_negative_end_bound_empty_range_matches_nothing(self):
        env = run('let result = match (5) { 0..-1 => "empty", _ => "other" };')
        self.assertEqual(env.get("result"), "other")

    def test_negative_literal_pattern_unaffected_by_range_bound_support(self):
        env = run('let result = match (-5) { -5 => "neg", _ => "pos" };')
        self.assertEqual(env.get("result"), "neg")

    def test_list_pattern_still_works_alongside_range_patterns(self):
        env = run('let result = match ([1, 2]) { [a, b] => a + b, _ => 0 };')
        self.assertEqual(env.get("result"), 3)

    def test_negative_literal_pattern_matches_negative_subject(self):
        env = run(
            'let result = match (-5) { -5 => "neg", 5 => "pos", _ => "other" };'
        )
        self.assertEqual(env.get("result"), "neg")

    def test_negative_literal_pattern_does_not_match_positive_subject(self):
        env = run(
            'let result = match (5) { -5 => "neg", 5 => "pos", _ => "other" };'
        )
        self.assertEqual(env.get("result"), "pos")

    def test_negative_float_literal_pattern_matches(self):
        env = run(
            'let result = match (-2.5) { -2.5 => "neg-float", _ => "other" };'
        )
        self.assertEqual(env.get("result"), "neg-float")

    def test_negative_literal_pattern_falls_through_without_raising(self):
        env = run('let result = match (0) { -5 => "neg", _ => "not"};')
        self.assertEqual(env.get("result"), "not")

    def test_negative_literal_pattern_combines_with_other_literals(self):
        env = run(
            'let result = match (-1) { -5, -1, 3 => "matched", _ => "no" };'
        )
        self.assertEqual(env.get("result"), "matched")

    def test_map_pattern_binds_named_keys(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_falls_through_on_missing_key(self):
        env = run(
            'let result = match ({"a": 1}) { {a, b} => a + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 0)

    def test_map_pattern_ignores_extra_keys(self):
        env = run(
            'let result = match ({"a": 1, "b": 2, "c": 3}) '
            '{ {a, b} => a + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_falls_through_on_non_map_subject(self):
        env = run('let result = match ([1, 2]) { {a} => a, _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_single_key(self):
        env = run('let result = match ({"a": 1}) { {a} => a, _ => 0 };')
        self.assertEqual(env.get("result"), 1)

    def test_empty_map_pattern_matches_any_map(self):
        env = run('let result = match ({}) { {} => "empty", _ => "no" };')
        self.assertEqual(env.get("result"), "empty")

    def test_map_pattern_coexists_with_list_pattern_arms(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) '
            '{ [a, b] => "list", {a, b} => a + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_non_identifier_key_raises(self):
        with self.assertRaises(ParseError):
            run('let result = match (x) { {1} => 0 };')

    def test_map_pattern_renamed_keys(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) '
            '{ {a: x, b} => x + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_single_renamed_key(self):
        env = run('let result = match ({"a": 1}) { {a: x} => x, _ => 0 };')
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_renamed_unaffects_unrenamed(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_renamed_falls_through_on_missing_key(self):
        env = run(
            'let result = match ({"a": 1}) { {a: x, b: y} => x + y, _ => -1 };'
        )
        self.assertEqual(env.get("result"), -1)

    def test_map_pattern_renamed_falls_through_on_non_map_subject(self):
        env = run('let result = match ([1, 2]) { {a: x} => x, _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_renamed_ignores_extra_keys(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) { {a: x} => x, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_renamed_binding_scoped_to_arm(self):
        with self.assertRaises(CinderRuntimeError):
            run(
                'let result = match ({"a": 1}) { {a: x} => x, _ => 0 }; '
                'print(x);'
            )

    def test_map_pattern_rename_requires_identifier(self):
        with self.assertRaises(ParseError):
            run('let result = match (x) { {a: 5} => a, _ => 0 };')

    def test_map_pattern_rest_capture_binds_leftover(self):
        env = run(
            'let result = match ({"a": 1, "b": 2, "c": 3}) '
            '{ {a, ...rest} => rest, _ => 0 };'
        )
        self.assertEqual(env.get("result"), {"b": 2, "c": 3})

    def test_map_pattern_rest_capture_empty_when_nothing_left_over(self):
        env = run(
            'let result = match ({"a": 1}) { {a, ...rest} => rest, _ => 0 };'
        )
        self.assertEqual(env.get("result"), {})

    def test_map_pattern_rest_capture_discarded_with_underscore(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) { {a, ..._} => a, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_without_rest_unaffected_by_rest_capture_feature(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) { {a} => a, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_rest_capture_combines_with_rename(self):
        env = run(
            'let result = match ({"a": 1, "b": 2, "c": 3}) '
            '{ {a: x, ...rest} => rest, _ => 0 };'
        )
        self.assertEqual(env.get("result"), {"b": 2, "c": 3})

    def test_map_pattern_rest_capture_falls_through_on_missing_key(self):
        env = run(
            'let result = match ({"a": 1}) { {a, b, ...rest} => rest, _ => "no" };'
        )
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_rest_capture_binding_scoped_to_arm(self):
        with self.assertRaises(CinderRuntimeError):
            run(
                'let result = match ({"a": 1, "b": 2}) '
                '{ {a, ...rest} => a, _ => 0 }; '
                'print(rest);'
            )

    def test_map_pattern_rest_not_last_raises(self):
        with self.assertRaises(ParseError):
            run('let result = match (x) { {a, ...rest, b} => a, _ => 0 };')

    def test_map_pattern_rest_requires_identifier(self):
        with self.assertRaises(ParseError):
            run('let result = match (x) { {a, ...5} => a, _ => 0 };')

    def test_map_pattern_nested_map_value(self):
        env = run(
            'let result = match ({"a": 1, "b": {"c": 2}}) '
            '{ {a, b: {c}} => a + c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_nested_list_value(self):
        env = run(
            'let result = match ({"a": 1, "b": [2, 3]}) '
            '{ {a, b: [x, y]} => a + x + y, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 6)

    def test_map_pattern_nested_map_value_arbitrary_depth(self):
        env = run(
            'let result = match ({"a": {"b": {"c": 1}}}) '
            '{ {a: {b: {c}}} => c, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_nested_map_value_composes_with_rename(self):
        env = run(
            'let result = match ({"a": 1, "b": {"c": 2}}) '
            '{ {a, b: {c: x}} => a + x, _ => 0 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_nested_map_value_composes_with_rest_capture(self):
        env = run(
            'let result = match ({"a": 1, "b": {"c": 2, "d": 3}}) '
            '{ {a, b: {c, ...rest}} => rest, _ => 0 };'
        )
        self.assertEqual(env.get("result"), {"d": 3})

    def test_map_pattern_nested_map_value_falls_through_whole_arm(self):
        env = run(
            'let result = match ({"a": 1, "b": {"c": 2}}) '
            '{ {a, b: {d}} => 0, _ => "no match" };'
        )
        self.assertEqual(env.get("result"), "no match")

    def test_map_pattern_nested_map_value_falls_through_on_non_map_subject(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) '
            '{ {a, b: {c}} => c, _ => "no" };'
        )
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_nested_map_value_falls_through_on_list_subject(self):
        env = run(
            'let result = match ({"a": 1, "b": [1, 2]}) '
            '{ {a, b: {c}} => c, _ => "no" };'
        )
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_nested_bindings_scoped_to_arm(self):
        with self.assertRaises(CinderRuntimeError):
            run(
                'let result = match ({"a": 1, "b": {"c": 2}}) '
                '{ {a, b: {c}} => a, _ => 0 }; '
                'print(c);'
            )

    def test_map_pattern_default_fires_on_missing_key(self):
        env = run(
            'let result = match ({"a": 1}) { {a, b = 0} => a + b, _ => -1 };'
        )
        self.assertEqual(env.get("result"), 1)

    def test_map_pattern_default_unused_when_key_present(self):
        env = run(
            'let result = match ({"a": 1, "b": 2}) '
            '{ {a, b = 0} => a + b, _ => -1 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_multiple_defaults_all_missing(self):
        env = run(
            'let result = match ({}) { {a = 1, b = 2} => a + b, _ => -1 };'
        )
        self.assertEqual(env.get("result"), 3)

    def test_map_pattern_default_references_earlier_binding(self):
        env = run(
            'let result = match ({"a": 1}) { {a, b = a + 1} => b, _ => -1 };'
        )
        self.assertEqual(env.get("result"), 2)

    def test_map_pattern_default_composes_with_rename(self):
        env = run(
            'let result = match ({"b": 2}) { {a: x = 0, b} => x + b, _ => -1 };'
        )
        self.assertEqual(env.get("result"), 2)

    def test_map_pattern_default_composes_with_rest_capture(self):
        env = run(
            'let result = match ({"a": 1, "c": 3}) '
            '{ {a, b = 0, ...rest} => [a, b, rest], _ => "no" };'
        )
        self.assertEqual(env.get("result"), [1, 0, {"c": 3}])

    def test_map_pattern_key_without_default_still_required(self):
        env = run('let result = match ({}) { {a} => a, _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_map_pattern_default_falls_through_on_non_map_subject(self):
        env = run('let result = match ([1]) { {a = 1} => a, _ => "no" };')
        self.assertEqual(env.get("result"), "no")

    def test_list_pattern_whole_binding_holds_original_subject(self):
        env = run(
            'let result = match ([1, 2]) { [a, b] as whole => whole, _ => nil };'
        )
        self.assertEqual(env.get("result"), [1, 2])

    def test_list_pattern_whole_binding_composes_with_destructured_names(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let result = match ([1, 2]) '
            '{ [a, b] as whole => a + b + len(whole), _ => 0 };',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), 5)

    def test_map_pattern_whole_binding(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let result = match ({"a": 1, "b": 2}) '
            '{ {a, b} as whole => len(keys(whole)), _ => 0 };',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), 2)

    def test_list_pattern_whole_binding_composes_with_rest_capture(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let result = match ([1, 2, 3]) '
            '{ [a, ...rest] as whole => len(whole) - len(rest), _ => 0 };',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_whole_binding_composes_with_defaults(self):
        from cinder.builtins import create_global_environment

        env = run(
            'let result = match ([1]) { [a, b = 0] as whole => len(whole), _ => -1 };',
            create_global_environment(),
        )
        self.assertEqual(env.get("result"), 1)

    def test_list_pattern_whole_binding_not_defined_on_non_match(self):
        env = run(
            'let result = match (5) { [a, b] as whole => whole, _ => "no match" };'
        )
        self.assertEqual(env.get("result"), "no match")

    def test_list_pattern_whole_binding_does_not_leak_into_enclosing_scope(self):
        env = run(
            'let whole = 1; '
            'match ([1, 2]) { [a, b] as whole => whole, _ => nil }; '
        )
        self.assertEqual(env.get("whole"), 1)


if __name__ == "__main__":
    unittest.main()
