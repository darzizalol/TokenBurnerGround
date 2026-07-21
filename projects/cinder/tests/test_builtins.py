"""Tests for cinder.builtins: print, len, type, str, int, float, push, pop,
keys, values, upper, lower, trim, split, join, find, starts_with, ends_with,
replace, abs, min, max, round, contains, reverse, sort, range, map, filter,
reduce, slice, concat."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from cinder.builtins import create_global_environment
from cinder.errors import CinderRuntimeError
from cinder.interpreter import Environment, Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_program


def run(source: str) -> Environment:
    interpreter = Interpreter()
    env = create_global_environment()
    for statement in parse_program(tokenize(source)):
        interpreter.execute(statement, env)
    return env


class TestPrint(unittest.TestCase):
    def test_prints_space_joined_values_with_trailing_newline(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run('print(1, "two", 3.0, true, nil);')
        self.assertEqual(stdout.getvalue(), "1 two 3.0 true nil\n")

    def test_print_returns_nil(self):
        env = run("let result = print();")
        self.assertIsNone(env.get("result"))

    def test_print_renders_list_and_map(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run('print([1, "a"], {"k": 1});')
        self.assertEqual(stdout.getvalue(), '[1, "a"] {"k": 1}\n')


class TestLen(unittest.TestCase):
    def test_len_of_string(self):
        self.assertEqual(run('let result = len("hello");').get("result"), 5)

    def test_len_of_list(self):
        self.assertEqual(run("let result = len([1, 2, 3]);").get("result"), 3)

    def test_len_of_map(self):
        self.assertEqual(run('let result = len({"a": 1, "b": 2});').get("result"), 2)

    def test_len_of_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("len(42);")

    def test_len_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('len("a", "b");')


class TestType(unittest.TestCase):
    def test_type_names(self):
        cases = {
            "1": "int",
            "1.5": "float",
            '"s"': "string",
            "true": "bool",
            "nil": "nil",
            "[1]": "list",
            '{"a": 1}': "map",
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                env = run(f"let result = type({expr});")
                self.assertEqual(env.get("result"), expected)

    def test_type_of_function(self):
        env = run("fn f() {} let result = type(f);")
        self.assertEqual(env.get("result"), "function")

    def test_type_of_builtin_is_function(self):
        env = run("let result = type(print);")
        self.assertEqual(env.get("result"), "function")


class TestStr(unittest.TestCase):
    def test_str_of_int(self):
        self.assertEqual(run("let result = str(42);").get("result"), "42")

    def test_str_of_string_is_identity(self):
        self.assertEqual(run('let result = str("hi");').get("result"), "hi")

    def test_str_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("str();")


class TestInt(unittest.TestCase):
    def test_int_of_float_truncates(self):
        self.assertEqual(run("let result = int(3.9);").get("result"), 3)

    def test_int_of_numeric_string(self):
        self.assertEqual(run('let result = int("42");').get("result"), 42)

    def test_int_of_non_numeric_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('int("abc");')


class TestFloat(unittest.TestCase):
    def test_float_of_int(self):
        self.assertEqual(run("let result = float(3);").get("result"), 3.0)

    def test_float_of_numeric_string(self):
        self.assertEqual(run('let result = float("1.5");').get("result"), 1.5)

    def test_float_of_non_numeric_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('float("abc");')


class TestPush(unittest.TestCase):
    def test_push_appends_and_returns_the_list(self):
        env = run("let xs = [1, 2]; let result = push(xs, 3);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_push_on_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('push("a", 1);')

    def test_push_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("push([1]);")


class TestPop(unittest.TestCase):
    def test_pop_removes_and_returns_last_element(self):
        env = run("let xs = [1, 2, 3]; let result = pop(xs);")
        self.assertEqual(env.get("result"), 3)
        self.assertEqual(env.get("xs"), [1, 2])

    def test_pop_on_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pop("a");')

    def test_pop_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pop([1], 2);")

    def test_pop_on_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pop([]);")


class TestKeys(unittest.TestCase):
    def test_keys_returns_insertion_order(self):
        env = run('let result = keys({"b": 1, "a": 2});')
        self.assertEqual(env.get("result"), ["b", "a"])

    def test_keys_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("keys([1]);")

    def test_keys_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('keys({"a": 1}, 2);')


class TestValues(unittest.TestCase):
    def test_values_returns_insertion_order(self):
        env = run('let result = values({"b": 1, "a": 2});')
        self.assertEqual(env.get("result"), [1, 2])

    def test_values_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("values([1]);")

    def test_values_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('values({"a": 1}, 2);')


class TestUpper(unittest.TestCase):
    def test_upper_of_string(self):
        self.assertEqual(run('let result = upper("hello");').get("result"), "HELLO")

    def test_upper_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("upper(1);")

    def test_upper_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('upper("a", "b");')


class TestLower(unittest.TestCase):
    def test_lower_of_string(self):
        self.assertEqual(run('let result = lower("HELLO");').get("result"), "hello")

    def test_lower_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("lower(1);")

    def test_lower_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('lower("a", "b");')


class TestTrim(unittest.TestCase):
    def test_trim_strips_leading_and_trailing_whitespace(self):
        self.assertEqual(run('let result = trim("  hi  ");').get("result"), "hi")

    def test_trim_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("trim(1);")

    def test_trim_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('trim("a", "b");')


class TestSplit(unittest.TestCase):
    def test_split_on_literal_separator(self):
        env = run('let result = split("a,b,c", ",");')
        self.assertEqual(env.get("result"), ["a", "b", "c"])

    def test_split_on_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('split(1, ",");')

    def test_split_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('split("a,b");')

    def test_split_on_empty_separator_raises_cinder_error(self):
        with self.assertRaises(CinderRuntimeError):
            run('split("a,b,c", "");')


class TestJoin(unittest.TestCase):
    def test_join_concatenates_with_separator(self):
        env = run('let result = join(["a", "b", "c"], ",");')
        self.assertEqual(env.get("result"), "a,b,c")

    def test_join_on_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('join("a", ",");')

    def test_join_on_list_with_non_string_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('join(["a", 1], ",");')

    def test_join_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('join(["a"]);')

    def test_split_join_round_trip(self):
        env = run('let result = join(split("a,b,c", ","), ",");')
        self.assertEqual(env.get("result"), "a,b,c")


class TestFind(unittest.TestCase):
    def test_find_returns_index_of_first_match(self):
        self.assertEqual(run('let result = find("hello", "ll");').get("result"), 2)

    def test_find_returns_negative_one_when_not_found(self):
        self.assertEqual(run('let result = find("hello", "z");').get("result"), -1)

    def test_find_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('find(1, "l");')

    def test_find_on_non_string_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('find("hello", 1);')

    def test_find_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('find("hello");')


class TestStartsWith(unittest.TestCase):
    def test_starts_with_true(self):
        self.assertIs(run('let result = starts_with("hello", "he");').get("result"), True)

    def test_starts_with_false(self):
        self.assertIs(run('let result = starts_with("hello", "x");').get("result"), False)

    def test_starts_with_on_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('starts_with(1, "h");')

    def test_starts_with_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('starts_with("hello");')


class TestEndsWith(unittest.TestCase):
    def test_ends_with_true(self):
        self.assertIs(run('let result = ends_with("hello", "lo");').get("result"), True)

    def test_ends_with_false(self):
        self.assertIs(run('let result = ends_with("hello", "x");').get("result"), False)

    def test_ends_with_on_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('ends_with(1, "o");')

    def test_ends_with_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('ends_with("hello");')


class TestReplace(unittest.TestCase):
    def test_replace_all_occurrences(self):
        self.assertEqual(run('let result = replace("aaa", "a", "b");').get("result"), "bbb")

    def test_replace_no_match_returns_unchanged(self):
        self.assertEqual(run('let result = replace("hello", "z", "x");').get("result"), "hello")

    def test_replace_empty_old_matches_python_semantics(self):
        self.assertEqual(run('let result = replace("ab", "", "-");').get("result"), "-a-b-")

    def test_replace_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('replace(1, "a", "b");')

    def test_replace_on_non_string_old_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('replace("a", 1, "b");')

    def test_replace_on_non_string_new_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('replace("a", "a", 1);')

    def test_replace_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('replace("a", "a");')


class TestAbs(unittest.TestCase):
    def test_abs_of_negative_int(self):
        self.assertEqual(run("let result = abs(-3);").get("result"), 3)

    def test_abs_of_negative_float(self):
        self.assertEqual(run("let result = abs(-3.5);").get("result"), 3.5)

    def test_abs_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('abs("x");')

    def test_abs_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("abs(1, 2);")


class TestMin(unittest.TestCase):
    def test_min_of_several_arguments(self):
        self.assertEqual(run("let result = min(3, 1, 2);").get("result"), 1)

    def test_min_of_single_argument(self):
        self.assertEqual(run("let result = min(5);").get("result"), 5)

    def test_min_of_zero_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("min();")

    def test_min_of_non_numeric_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('min(1, "x");')


class TestMax(unittest.TestCase):
    def test_max_of_several_arguments(self):
        self.assertEqual(run("let result = max(3, 1, 2);").get("result"), 3)

    def test_max_of_single_argument(self):
        self.assertEqual(run("let result = max(5);").get("result"), 5)

    def test_max_of_zero_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("max();")

    def test_max_of_non_numeric_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('max(1, "x");')


class TestRound(unittest.TestCase):
    def test_round_ties_to_even(self):
        self.assertEqual(run("let result = round(2.5);").get("result"), 2)
        self.assertEqual(run("let result = round(3.5);").get("result"), 4)

    def test_round_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('round("x");')

    def test_round_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("round(1.5, 2);")


class TestContains(unittest.TestCase):
    def test_contains_in_list(self):
        self.assertIs(run("let result = contains([1, 2, 3], 2);").get("result"), True)
        self.assertIs(run("let result = contains([1, 2, 3], 9);").get("result"), False)

    def test_contains_checks_map_keys_not_values(self):
        self.assertIs(run('let result = contains({"a": 1}, "a");').get("result"), True)
        self.assertIs(run('let result = contains({"a": 1}, "b");').get("result"), False)
        self.assertIs(run('let result = contains({"a": 1}, 1);').get("result"), False)

    def test_contains_substring(self):
        self.assertIs(run('let result = contains("hello", "ell");').get("result"), True)
        self.assertIs(run('let result = contains("hello", "xyz");').get("result"), False)

    def test_contains_on_unsupported_collection_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("contains(5, 1);")

    def test_contains_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("contains([1]);")


class TestReverse(unittest.TestCase):
    def test_reverse_returns_new_reversed_list(self):
        self.assertEqual(run("let result = reverse([1, 2, 3]);").get("result"), [3, 2, 1])

    def test_reverse_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = reverse(xs);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [3, 2, 1])

    def test_reverse_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('reverse("hi");')

    def test_reverse_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reverse([1], 2);")


class TestSort(unittest.TestCase):
    def test_sort_of_ints(self):
        self.assertEqual(run("let result = sort([3, 1, 2]);").get("result"), [1, 2, 3])

    def test_sort_of_floats(self):
        self.assertEqual(run("let result = sort([2.5, 1.1]);").get("result"), [1.1, 2.5])

    def test_sort_of_strings(self):
        self.assertEqual(run('let result = sort(["b", "a"]);').get("result"), ["a", "b"])

    def test_sort_of_empty_list(self):
        self.assertEqual(run("let result = sort([]);").get("result"), [])

    def test_sort_of_mixed_numeric_and_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sort([1, "a"]);')

    def test_sort_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sort(5);")

    def test_sort_does_not_mutate_input(self):
        env = run("let xs = [3, 1, 2]; let result = sort(xs);")
        self.assertEqual(env.get("xs"), [3, 1, 2])
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_sort_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sort([1], 2);")


class TestRange(unittest.TestCase):
    def test_range_one_argument(self):
        self.assertEqual(run("let result = range(5);").get("result"), [0, 1, 2, 3, 4])

    def test_range_two_arguments(self):
        self.assertEqual(run("let result = range(2, 5);").get("result"), [2, 3, 4])

    def test_range_zero_returns_empty(self):
        self.assertEqual(run("let result = range(0);").get("result"), [])

    def test_range_equal_bounds_returns_empty(self):
        self.assertEqual(run("let result = range(3, 3);").get("result"), [])

    def test_range_descending_bounds_returns_empty(self):
        self.assertEqual(run("let result = range(5, 2);").get("result"), [])

    def test_range_non_int_stop_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('range("x");')

    def test_range_non_int_start_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('range(1, "x");')

    def test_range_float_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("range(1.5);")

    def test_range_zero_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("range();")

    def test_range_too_many_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("range(1, 2, 3);")

    def test_for_in_range_prints_each_value(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            run("for i in range(3) { print(i); }")
        self.assertEqual(stdout.getvalue(), "0\n1\n2\n")


class TestMap(unittest.TestCase):
    def test_map_with_closure(self):
        env = run("let result = map([1, 2, 3], fn(x) { return x * 2; });")
        self.assertEqual(env.get("result"), [2, 4, 6])

    def test_map_with_builtin_by_name(self):
        env = run("let result = map([1, -2, 3], abs);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_map_of_empty_list(self):
        env = run("let result = map([], fn(x) { return x; });")
        self.assertEqual(env.get("result"), [])

    def test_map_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = map(xs, fn(x) { return x * 2; });")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [2, 4, 6])

    def test_map_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("map(5, fn(x) { return x; });")

    def test_map_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("map([1, 2], 5);")

    def test_map_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("map([1], fn(x, y) { return x; });")


class TestFilter(unittest.TestCase):
    def test_filter_with_closure(self):
        env = run("let result = filter([1, 2, 3, 4], fn(x) { return x > 2; });")
        self.assertEqual(env.get("result"), [3, 4])

    def test_filter_of_empty_list(self):
        env = run("let result = filter([], fn(x) { return true; });")
        self.assertEqual(env.get("result"), [])

    def test_filter_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3, 4]; "
            "let result = filter(xs, fn(x) { return x > 2; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [3, 4])

    def test_filter_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("filter(5, fn(x) { return x; });")

    def test_filter_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("filter([1, 2], 5);")

    def test_filter_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("filter([1], fn(x, y) { return x; });")


class TestReduce(unittest.TestCase):
    def test_reduce_sums_list(self):
        env = run("let result = reduce([1, 2, 3], fn(acc, x) { return acc + x; }, 0);")
        self.assertEqual(env.get("result"), 6)

    def test_reduce_products_list(self):
        env = run(
            "let result = reduce([1, 2, 3, 4], fn(acc, x) { return acc * x; }, 1);"
        )
        self.assertEqual(env.get("result"), 24)

    def test_reduce_of_empty_list_returns_initial_without_calling_fn(self):
        env = run(
            "let touched = []; "
            "let result = reduce([], fn(acc, x) { push(touched, x); return acc + x; }, 0); "
        )
        self.assertEqual(env.get("result"), 0)
        self.assertEqual(env.get("touched"), [])

    def test_reduce_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reduce(5, fn(acc, x) { return acc; }, 0);")

    def test_reduce_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reduce([1, 2], 5, 0);")

    def test_reduce_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("reduce([1], fn(x) { return x; }, 0);")

    def test_reduce_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = reduce(xs, fn(acc, x) { return acc + x; }, 0);"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), 6)


class TestSlice(unittest.TestCase):
    def test_slice_basic_range(self):
        env = run("let result = slice([1, 2, 3, 4], 1, 3);")
        self.assertEqual(env.get("result"), [2, 3])

    def test_slice_negative_bounds(self):
        env = run("let result = slice([1, 2, 3], -2, -1);")
        self.assertEqual(env.get("result"), [2])

    def test_slice_out_of_range_end_clamps(self):
        env = run("let result = slice([1, 2, 3], 0, 100);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_slice_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3, 4]; let result = slice(xs, 1, 3);")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [2, 3])

    def test_slice_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("slice(5, 0, 1);")

    def test_slice_non_int_bound_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("slice([1, 2], 0.5, 1);")


class TestConcat(unittest.TestCase):
    def test_concat_joins_lists(self):
        env = run("let result = concat([1, 2], [3, 4]);")
        self.assertEqual(env.get("result"), [1, 2, 3, 4])

    def test_concat_with_empty_list(self):
        env = run("let result = concat([], [1]);")
        self.assertEqual(env.get("result"), [1])

    def test_concat_does_not_mutate_inputs(self):
        env = run("let a = [1, 2]; let b = [3, 4]; let result = concat(a, b);")
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("b"), [3, 4])
        self.assertEqual(env.get("result"), [1, 2, 3, 4])

    def test_concat_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("concat(5, [1]);")
        with self.assertRaises(CinderRuntimeError):
            run("concat([1], 5);")


class TestEndToEndViaCli(unittest.TestCase):
    def test_run_script_prints_expected_output(self):
        with tempfile.NamedTemporaryFile("w", suffix=".cin", delete=False) as f:
            f.write(
                'fn greet(name) { return "hello, " + name; }\n'
                'print(greet("cinder"));\n'
                "print(len([1, 2, 3]));\n"
            )
            path = f.name
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "run", path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "hello, cinder\n3\n")


if __name__ == "__main__":
    unittest.main()
