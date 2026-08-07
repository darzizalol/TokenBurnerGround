"""Tests for cinder.builtins: print, len, is_empty, type, str, int, float, ord, chr, push, pop,
insert, remove_at, keys, values, items, get, get_in, remove, merge, upper, lower, trim, trim_start, trim_end, split, lines, words, join,
find, starts_with, ends_with, replace, pad_start, pad_end, abs, min, max, round, to_fixed, floor, ceil,
pow, sqrt, sum, any, all, contains, index_of, last_index_of, find_index, find_last_index, copy, unique, reverse, rotate, sort, sort_by, min_by, max_by, range, map,
filter, reduce, slice, take, drop, concat, flatten, flatten_deep, zip, enumerate, assert, format, is_list, is_map,
is_string, is_number, is_bool, is_nil, is_function, random_int, random_choice."""

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


class TestIsEmpty(unittest.TestCase):
    def test_is_empty_string_true(self):
        self.assertEqual(run('let result = is_empty("");').get("result"), True)

    def test_is_empty_string_false(self):
        self.assertEqual(run('let result = is_empty("x");').get("result"), False)

    def test_is_empty_list_true(self):
        self.assertEqual(run("let result = is_empty([]);").get("result"), True)

    def test_is_empty_list_false(self):
        self.assertEqual(run("let result = is_empty([1]);").get("result"), False)

    def test_is_empty_map_true(self):
        self.assertEqual(run("let result = is_empty({});").get("result"), True)

    def test_is_empty_map_false(self):
        self.assertEqual(run('let result = is_empty({"a": 1});').get("result"), False)

    def test_is_empty_of_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_empty(5);")

    def test_is_empty_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('is_empty("a", "b");')


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


class TestOrd(unittest.TestCase):
    def test_ord_of_letter(self):
        self.assertEqual(run('let result = ord("A");').get("result"), 65)

    def test_ord_round_trips_with_chr(self):
        self.assertEqual(run('let result = ord(chr(97));').get("result"), 97)

    def test_ord_of_empty_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('ord("");')

    def test_ord_of_multi_character_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('ord("ab");')

    def test_ord_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("ord(5);")

    def test_ord_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('ord("a", "b");')


class TestChr(unittest.TestCase):
    def test_chr_of_code_point(self):
        self.assertEqual(run("let result = chr(65);").get("result"), "A")

    def test_chr_round_trips_with_ord(self):
        self.assertEqual(run('let result = chr(ord("z"));').get("result"), "z")

    def test_chr_of_negative_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chr(-1);")

    def test_chr_of_out_of_range_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chr(1114112);")

    def test_chr_of_non_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('chr("65");')

    def test_chr_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chr();")


class TestToHex(unittest.TestCase):
    def test_to_hex_of_positive_int(self):
        self.assertEqual(run("let result = to_hex(255);").get("result"), "ff")

    def test_to_hex_of_zero(self):
        self.assertEqual(run("let result = to_hex(0);").get("result"), "0")

    def test_to_hex_of_negative_int(self):
        self.assertEqual(run("let result = to_hex(-255);").get("result"), "-ff")

    def test_to_hex_of_non_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_hex(1.5);")

    def test_to_hex_of_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('to_hex("255");')

    def test_to_hex_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_hex();")


class TestToBin(unittest.TestCase):
    def test_to_bin_of_positive_int(self):
        self.assertEqual(run("let result = to_bin(5);").get("result"), "101")

    def test_to_bin_of_zero(self):
        self.assertEqual(run("let result = to_bin(0);").get("result"), "0")

    def test_to_bin_of_negative_int(self):
        self.assertEqual(run("let result = to_bin(-5);").get("result"), "-101")

    def test_to_bin_of_non_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_bin(1.5);")

    def test_to_bin_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_bin();")


class TestToOct(unittest.TestCase):
    def test_to_oct_of_positive_int(self):
        self.assertEqual(run("let result = to_oct(8);").get("result"), "10")

    def test_to_oct_of_zero(self):
        self.assertEqual(run("let result = to_oct(0);").get("result"), "0")

    def test_to_oct_of_negative_int(self):
        self.assertEqual(run("let result = to_oct(-8);").get("result"), "-10")

    def test_to_oct_of_non_int_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_oct(1.5);")

    def test_to_oct_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_oct();")


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


class TestInsert(unittest.TestCase):
    def test_insert_in_middle(self):
        env = run("let l = [1, 2, 3]; insert(l, 1, 99);")
        self.assertEqual(env.get("l"), [1, 99, 2, 3])

    def test_insert_at_front(self):
        env = run("let l = [1, 2, 3]; insert(l, 0, 99);")
        self.assertEqual(env.get("l"), [99, 1, 2, 3])

    def test_insert_at_length_appends(self):
        env = run("let l = [1, 2, 3]; insert(l, 3, 99);")
        self.assertEqual(env.get("l"), [1, 2, 3, 99])

    def test_insert_negative_index(self):
        env = run("let l = [1, 2, 3]; insert(l, -1, 99);")
        self.assertEqual(env.get("l"), [1, 2, 99, 3])

    def test_insert_returns_nil(self):
        env = run("let l = [1, 2]; let result = insert(l, 0, 9);")
        self.assertIsNone(env.get("result"))

    def test_insert_out_of_range_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("insert([1, 2], 5, 0);")

    def test_insert_non_int_index_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('insert([1, 2], "0", 9);')

    def test_insert_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("insert(5, 0, 9);")

    def test_insert_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("insert([1, 2], 0);")


class TestRemoveAt(unittest.TestCase):
    def test_remove_at_returns_removed_element(self):
        env = run("let l = [1, 2, 3]; let result = remove_at(l, 1);")
        self.assertEqual(env.get("result"), 2)
        self.assertEqual(env.get("l"), [1, 3])

    def test_remove_at_negative_index(self):
        env = run("let l = [1, 2, 3]; let result = remove_at(l, -1);")
        self.assertEqual(env.get("result"), 3)
        self.assertEqual(env.get("l"), [1, 2])

    def test_remove_at_on_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("remove_at([], 0);")

    def test_remove_at_non_int_index_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove_at([1, 2], "0");')

    def test_remove_at_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("remove_at(5, 0);")

    def test_remove_at_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("remove_at([1, 2]);")


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


class TestItems(unittest.TestCase):
    def test_items_returns_key_value_pairs_in_insertion_order(self):
        env = run('let result = items({"a": 1, "b": 2});')
        self.assertEqual(env.get("result"), [["a", 1], ["b", 2]])

    def test_items_of_empty_map_is_empty_list(self):
        env = run("let result = items({});")
        self.assertEqual(env.get("result"), [])

    def test_items_matches_zipped_keys_and_values(self):
        env = run(
            'let m = {"x": 10, "y": 20, "z": 30};'
            "let its = items(m);"
            "let ks = keys(m);"
            "let vs = values(m);"
        )
        its, ks, vs = env.get("its"), env.get("ks"), env.get("vs")
        self.assertEqual(len(its), len(ks))
        for i in range(len(its)):
            self.assertEqual(its[i], [ks[i], vs[i]])

    def test_items_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("items(5);")
        with self.assertRaises(CinderRuntimeError):
            run("items([1, 2]);")

    def test_items_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('items({"a": 1}, 2);')


class TestFromEntries(unittest.TestCase):
    def test_from_entries_builds_map_from_pairs(self):
        env = run('let result = from_entries([["a", 1], ["b", 2]]);')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_from_entries_later_entry_wins_on_duplicate_key(self):
        env = run('let result = from_entries([["a", 1], ["a", 2]]);')
        self.assertEqual(env.get("result"), {"a": 2})

    def test_from_entries_of_empty_list_is_empty_map(self):
        env = run("let result = from_entries([]);")
        self.assertEqual(env.get("result"), {})

    def test_from_entries_round_trips_with_items(self):
        env = run(
            'let m = {"x": 1, "y": 2};'
            "let result = from_entries(items(m));"
        )
        self.assertEqual(env.get("result"), {"x": 1, "y": 2})

    def test_from_entries_wrong_length_pair_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('from_entries([["a", 1, "extra"]]);')
        with self.assertRaises(CinderRuntimeError):
            run('from_entries([["a"]]);')

    def test_from_entries_non_list_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("from_entries([5]);")

    def test_from_entries_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('from_entries([[[1, 2], "value"]]);')

    def test_from_entries_on_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("from_entries(5);")

    def test_from_entries_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("from_entries();")
        with self.assertRaises(CinderRuntimeError):
            run('from_entries([["a", 1]], "extra");')


class TestZipObject(unittest.TestCase):
    def test_zip_object_builds_map_from_parallel_lists(self):
        env = run('let result = zip_object(["a", "b", "c"], [1, 2, 3]);')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2, "c": 3})

    def test_zip_object_truncates_to_shorter_values_list(self):
        env = run('let result = zip_object(["a", "b"], [1, 2, 3]);')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_zip_object_truncates_to_shorter_keys_list(self):
        env = run('let result = zip_object(["a", "b", "c"], [1, 2]);')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_zip_object_of_empty_lists_is_empty_map(self):
        env = run("let result = zip_object([], []);")
        self.assertEqual(env.get("result"), {})

    def test_zip_object_later_entry_wins_on_duplicate_key(self):
        env = run('let result = zip_object(["a", "a", "b"], [1, 2, 3]);')
        self.assertEqual(env.get("result"), {"a": 2, "b": 3})

    def test_zip_object_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_object([[1, 2]], [1]);")

    def test_zip_object_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_object(5, [1]);")

    def test_zip_object_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('zip_object(["a"], 5);')

    def test_zip_object_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_object();")
        with self.assertRaises(CinderRuntimeError):
            run('zip_object(["a"], [1], "extra");')


class TestGet(unittest.TestCase):
    def test_get_returns_value_for_present_key(self):
        env = run('let result = get({"a": 1}, "a", 0);')
        self.assertEqual(env.get("result"), 1)

    def test_get_returns_default_for_missing_key(self):
        env = run('let result = get({"a": 1}, "z", 0);')
        self.assertEqual(env.get("result"), 0)

    def test_get_returns_default_on_empty_map(self):
        env = run('let result = get({}, "a", "default");')
        self.assertEqual(env.get("result"), "default")

    def test_get_does_not_always_return_default(self):
        env = run('let result = get({"a": 1}, "a", 0);')
        self.assertNotEqual(env.get("result"), 0)

    def test_get_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('get(5, "a", 0);')

    def test_get_with_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('get({"a": 1}, [1, 2], 0);')

    def test_get_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('get({"a": 1}, "a");')
        with self.assertRaises(CinderRuntimeError):
            run('get({"a": 1}, "a", 0, 1);')


class TestGetIn(unittest.TestCase):
    def test_get_in_walks_nested_maps(self):
        env = run('let result = get_in({"a": {"b": {"c": 1}}}, ["a", "b", "c"], nil);')
        self.assertEqual(env.get("result"), 1)

    def test_get_in_missing_key_partway_returns_default(self):
        env = run('let result = get_in({"a": {"b": 1}}, ["a", "x"], "missing");')
        self.assertEqual(env.get("result"), "missing")

    def test_get_in_mixes_map_keys_and_list_indices(self):
        env = run('let result = get_in({"a": [1, 2, 3]}, ["a", 1], nil);')
        self.assertEqual(env.get("result"), 2)

    def test_get_in_out_of_range_list_index_returns_default(self):
        env = run('let result = get_in({"a": [1, 2, 3]}, ["a", 99], "oob");')
        self.assertEqual(env.get("result"), "oob")

    def test_get_in_negative_list_index_normalizes(self):
        env = run('let result = get_in({"a": [1, 2, 3]}, ["a", -1], nil);')
        self.assertEqual(env.get("result"), 3)

    def test_get_in_descends_into_non_container_returns_default(self):
        env = run('let result = get_in({"a": 5}, ["a", "b"], "nope");')
        self.assertEqual(env.get("result"), "nope")

    def test_get_in_empty_path_returns_container(self):
        env = run('let result = get_in({"a": 1}, [], "unused");')
        self.assertEqual(env.get("result"), {"a": 1})

    def test_get_in_starts_from_top_level_list(self):
        env = run('let result = get_in([1, [2, 3]], [1, 0], nil);')
        self.assertEqual(env.get("result"), 2)

    def test_get_in_non_list_path_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('get_in({"a": 1}, "a", nil);')

    def test_get_in_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('get_in({"a": 1}, ["a"]);')
        with self.assertRaises(CinderRuntimeError):
            run('get_in({"a": 1}, ["a"], nil, 1);')

    def test_get_in_does_not_mutate_container(self):
        env = run(
            'let original = {"a": {"b": {"c": 1}}}; '
            'get_in(original, ["a", "b", "c"], nil);'
        )
        self.assertEqual(env.get("original"), {"a": {"b": {"c": 1}}})


class TestPluck(unittest.TestCase):
    def test_pluck_extracts_field_from_each_map(self):
        env = run(
            'let result = pluck([{"name": "a", "age": 1}, {"name": "b", "age": 2}], "name");'
        )
        self.assertEqual(env.get("result"), ["a", "b"])

    def test_pluck_on_empty_list_returns_empty_list(self):
        env = run('let result = pluck([], "x");')
        self.assertEqual(env.get("result"), [])

    def test_pluck_missing_key_on_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pluck([{"name": "a"}, {"age": 2}], "name");')

    def test_pluck_non_map_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pluck([{"name": "a"}, 5], "name");')

    def test_pluck_with_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pluck([{"name": "a"}], [1, 2]);')

    def test_pluck_on_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pluck(5, "name");')

    def test_pluck_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pluck([{"name": "a"}]);')
        with self.assertRaises(CinderRuntimeError):
            run('pluck([{"name": "a"}], "name", "extra");')


class TestRemove(unittest.TestCase):
    def test_remove_mutates_original_map_in_place(self):
        env = run('let m = {"a": 1, "b": 2}; remove(m, "a");')
        self.assertEqual(env.get("m"), {"b": 2})

    def test_remove_returns_removed_value(self):
        env = run('let result = remove({"a": 1}, "a");')
        self.assertEqual(env.get("result"), 1)

    def test_remove_missing_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove({"a": 1}, "z");')

    def test_remove_on_non_list_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove(5, "a");')

    def test_remove_with_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove({"a": 1}, [1, 2]);')

    def test_remove_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('remove({"a": 1}, "a", 1);')

    def test_remove_on_list_mutates_in_place(self):
        env = run('let l = [1, 2, 3]; remove(l, 2);')
        self.assertEqual(env.get("l"), [1, 3])

    def test_remove_on_list_returns_removed_value(self):
        env = run('let result = remove([1, 2, 3], 2);')
        self.assertEqual(env.get("result"), 2)

    def test_remove_on_list_removes_only_first_match(self):
        env = run('let l = [1, 2, 1]; remove(l, 1);')
        self.assertEqual(env.get("l"), [2, 1])

    def test_remove_on_list_missing_value_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('remove([1, 2], 5);')

    def test_remove_on_list_bool_vs_int_distinguished_by_values_equal(self):
        # 1 and true are distinct under Cinder's `==`/values_equal (unlike
        # Python's native equality), so `true` doesn't match the int `1`.
        with self.assertRaises(CinderRuntimeError):
            run('remove([1, 2, 3], true);')


class TestMerge(unittest.TestCase):
    def test_merge_combines_disjoint_keys(self):
        env = run('let result = merge({"a": 1}, {"b": 2});')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_merge_map2_wins_on_conflict(self):
        env = run('let result = merge({"a": 1}, {"a": 2});')
        self.assertEqual(env.get("result"), {"a": 2})

    def test_merge_with_empty_map(self):
        self.assertEqual(run('let result = merge({}, {"a": 1});').get("result"), {"a": 1})
        self.assertEqual(run('let result = merge({"a": 1}, {});').get("result"), {"a": 1})

    def test_merge_key_order_map1_then_map2_only_keys(self):
        env = run('let result = merge({"a": 1, "b": 2}, {"b": 3, "c": 4});')
        self.assertEqual(list(env.get("result").keys()), ["a", "b", "c"])

    def test_merge_does_not_mutate_inputs(self):
        env = run(
            'let m1 = {"a": 1};'
            'let m2 = {"b": 2};'
            "let result = merge(m1, m2);"
        )
        self.assertEqual(env.get("m1"), {"a": 1})
        self.assertEqual(env.get("m2"), {"b": 2})

    def test_merge_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("merge(5, {});")
        with self.assertRaises(CinderRuntimeError):
            run("merge({}, 5);")

    def test_merge_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('merge({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('merge({"a": 1}, {}, {});')


class TestDeepMerge(unittest.TestCase):
    def test_deep_merge_combines_disjoint_keys(self):
        env = run('let result = deep_merge({"a": 1}, {"b": 2});')
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_deep_merge_recurses_into_nested_maps(self):
        env = run('let result = deep_merge({"a": {"x": 1}}, {"a": {"y": 2}});')
        self.assertEqual(env.get("result"), {"a": {"x": 1, "y": 2}})

    def test_deep_merge_map2_wins_on_leaf_conflict(self):
        env = run('let result = deep_merge({"a": {"x": 1}}, {"a": {"x": 2}});')
        self.assertEqual(env.get("result"), {"a": {"x": 2}})

    def test_deep_merge_overwrites_lists_wholesale(self):
        env = run('let result = deep_merge({"a": [1, 2]}, {"a": [3]});')
        self.assertEqual(env.get("result"), {"a": [3]})

    def test_deep_merge_non_map_value_wins_outright(self):
        env = run('let result = deep_merge({"a": {"x": 1}}, {"a": 5});')
        self.assertEqual(env.get("result"), {"a": 5})

    def test_deep_merge_three_levels_of_nesting(self):
        env = run(
            'let result = deep_merge({"a": {"b": {"c": 1}}}, '
            '{"a": {"b": {"d": 2}}});'
        )
        self.assertEqual(env.get("result"), {"a": {"b": {"c": 1, "d": 2}}})

    def test_deep_merge_does_not_mutate_inputs(self):
        env = run(
            'let m1 = {"a": {"x": 1}};'
            'let m2 = {"a": {"y": 2}};'
            "let result = deep_merge(m1, m2);"
        )
        self.assertEqual(env.get("m1"), {"a": {"x": 1}})
        self.assertEqual(env.get("m2"), {"a": {"y": 2}})

    def test_deep_merge_result_mutation_does_not_leak_into_inputs(self):
        env = run(
            'let m1 = {"a": {"x": 1}};'
            'let m2 = {"b": 2};'
            "let result = deep_merge(m1, m2);"
            'result["a"]["z"] = 999;'
        )
        self.assertEqual(env.get("m1"), {"a": {"x": 1}})
        self.assertEqual(env.get("result"), {"a": {"x": 1, "z": 999}, "b": 2})

    def test_deep_merge_result_list_mutation_does_not_leak_into_inputs(self):
        env = run(
            'let m1 = {"a": [1, 2]};'
            'let m2 = {"b": 3};'
            "let result = deep_merge(m1, m2);"
            'result["a"][0] = 999;'
        )
        self.assertEqual(env.get("m1"), {"a": [1, 2]})
        self.assertEqual(env.get("result"), {"a": [999, 2], "b": 3})

    def test_deep_merge_with_empty_maps(self):
        self.assertEqual(run("let result = deep_merge({}, {});").get("result"), {})

    def test_deep_merge_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("deep_merge(5, {});")
        with self.assertRaises(CinderRuntimeError):
            run("deep_merge({}, 5);")

    def test_deep_merge_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('deep_merge({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('deep_merge({"a": 1}, {}, {});')


class TestDeepEqual(unittest.TestCase):
    def test_equal_nested_lists(self):
        env = run("let result = deep_equal([1, [2, 3]], [1, [2, 3]]);")
        self.assertTrue(env.get("result"))

    def test_unequal_nested_lists(self):
        env = run("let result = deep_equal([1, [2, 3]], [1, [2, 4]]);")
        self.assertFalse(env.get("result"))

    def test_equal_maps_regardless_of_key_order(self):
        env = run(
            'let result = deep_equal({"a": 1, "b": {"c": 2}}, '
            '{"b": {"c": 2}, "a": 1});'
        )
        self.assertTrue(env.get("result"))

    def test_maps_with_different_key_sets_are_unequal(self):
        env = run('let result = deep_equal({"a": 1}, {"a": 1, "b": 2});')
        self.assertFalse(env.get("result"))

    def test_numeric_equality_ignores_int_float_distinction(self):
        env = run("let result = deep_equal(1, 1.0);")
        self.assertTrue(env.get("result"))

    def test_bool_never_equal_to_number(self):
        env = run("let result = deep_equal(true, 1);")
        self.assertFalse(env.get("result"))

    def test_different_length_lists_are_unequal(self):
        env = run("let result = deep_equal([1, 2], [1, 2, 3]);")
        self.assertFalse(env.get("result"))

    def test_equal_strings_and_nils(self):
        self.assertTrue(run('let result = deep_equal("x", "x");').get("result"))
        self.assertTrue(run("let result = deep_equal(nil, nil);").get("result"))

    def test_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("deep_equal(1);")
        with self.assertRaises(CinderRuntimeError):
            run("deep_equal(1, 2, 3);")


class TestInvert(unittest.TestCase):
    def test_invert_swaps_keys_and_values(self):
        env = run('let result = invert({"a": 1, "b": 2});')
        self.assertEqual(env.get("result"), {1: "a", 2: "b"})

    def test_invert_collision_later_entry_wins(self):
        env = run('let result = invert({"a": 1, "b": 1});')
        self.assertEqual(env.get("result"), {1: "b"})

    def test_invert_of_empty_map(self):
        self.assertEqual(run("let result = invert({});").get("result"), {})

    def test_invert_does_not_mutate_input(self):
        env = run('let m = {"a": 1}; let result = invert(m);')
        self.assertEqual(env.get("m"), {"a": 1})

    def test_invert_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("invert(5);")

    def test_invert_with_invalid_value_as_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('invert({"a": [1]});')

    def test_invert_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("invert();")
        with self.assertRaises(CinderRuntimeError):
            run('invert({"a": 1}, {"b": 2});')


class TestPick(unittest.TestCase):
    def test_pick_selects_subset(self):
        env = run('let result = pick({"a": 1, "b": 2, "c": 3}, ["a", "c"]);')
        self.assertEqual(env.get("result"), {"a": 1, "c": 3})

    def test_pick_result_order_follows_keys_argument(self):
        env = run('let result = pick({"a": 1, "b": 2, "c": 3}, ["c", "a"]);')
        self.assertEqual(list(env.get("result").keys()), ["c", "a"])

    def test_pick_skips_key_not_in_map(self):
        env = run('let result = pick({"a": 1}, ["a", "missing"]);')
        self.assertEqual(env.get("result"), {"a": 1})

    def test_pick_with_empty_keys_is_empty_map(self):
        env = run('let result = pick({"a": 1}, []);')
        self.assertEqual(env.get("result"), {})

    def test_pick_does_not_mutate_input(self):
        env = run('let m = {"a": 1, "b": 2}; let result = pick(m, ["a"]);')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_pick_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pick(5, ["a"]);')

    def test_pick_with_non_list_keys_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pick({"a": 1}, "a");')

    def test_pick_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pick({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('pick({"a": 1}, ["a"], 1);')


class TestOmit(unittest.TestCase):
    def test_omit_removes_given_keys(self):
        env = run('let result = omit({"a": 1, "b": 2, "c": 3}, ["b"]);')
        self.assertEqual(env.get("result"), {"a": 1, "c": 3})

    def test_omit_preserves_source_key_order(self):
        env = run('let result = omit({"a": 1, "b": 2, "c": 3}, ["b"]);')
        self.assertEqual(list(env.get("result").keys()), ["a", "c"])

    def test_omit_skips_key_not_in_map(self):
        env = run('let result = omit({"a": 1}, ["missing"]);')
        self.assertEqual(env.get("result"), {"a": 1})

    def test_omit_with_empty_keys_is_copy_of_map(self):
        env = run('let m = {"a": 1}; let result = omit(m, []);')
        self.assertEqual(env.get("result"), {"a": 1})

    def test_omit_does_not_mutate_input(self):
        env = run('let m = {"a": 1, "b": 2}; let result = omit(m, ["a"]);')
        self.assertEqual(env.get("m"), {"a": 1, "b": 2})

    def test_omit_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('omit(5, ["a"]);')

    def test_omit_with_non_list_keys_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('omit({"a": 1}, "a");')

    def test_omit_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('omit({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('omit({"a": 1}, ["a"], 1);')


class TestPickBy(unittest.TestCase):
    def test_pick_by_keeps_entries_matching_predicate(self):
        env = run(
            'let result = pick_by({"a": 1, "b": 2, "c": 3}, fn(k, v) { return v > 1; });'
        )
        self.assertEqual(env.get("result"), {"b": 2, "c": 3})

    def test_pick_by_predicate_can_inspect_key(self):
        env = run(
            'let result = pick_by({"a": 1, "bb": 2, "ccc": 3}, '
            "fn(k, v) { return len(k) == 1; });"
        )
        self.assertEqual(env.get("result"), {"a": 1})

    def test_pick_by_of_empty_map_is_empty(self):
        env = run("let result = pick_by({}, fn(k, v) { return true; });")
        self.assertEqual(env.get("result"), {})

    def test_pick_by_always_false_predicate_is_empty(self):
        env = run(
            'let result = pick_by({"a": 1, "b": 2}, fn(k, v) { return false; });'
        )
        self.assertEqual(env.get("result"), {})

    def test_pick_by_preserves_source_key_order(self):
        env = run(
            'let result = keys(pick_by({"z": 1, "a": 2}, fn(k, v) { return true; }));'
        )
        self.assertEqual(env.get("result"), ["z", "a"])

    def test_pick_by_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pick_by([1, 2, 3], fn(k, v) { return true; });")

    def test_pick_by_with_non_callable_predicate_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pick_by({"a": 1}, "not a function");')

    def test_pick_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pick_by({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('pick_by({"a": 1}, fn(k, v) { return true; }, 1);')


class TestOmitBy(unittest.TestCase):
    def test_omit_by_drops_entries_matching_predicate(self):
        env = run(
            'let result = omit_by({"a": 1, "b": 2, "c": 3}, fn(k, v) { return v > 1; });'
        )
        self.assertEqual(env.get("result"), {"a": 1})

    def test_omit_by_always_false_predicate_is_identity(self):
        env = run(
            'let result = omit_by({"a": 1, "b": 2}, fn(k, v) { return false; });'
        )
        self.assertEqual(env.get("result"), {"a": 1, "b": 2})

    def test_omit_by_of_empty_map_is_empty(self):
        env = run("let result = omit_by({}, fn(k, v) { return true; });")
        self.assertEqual(env.get("result"), {})

    def test_omit_by_on_non_map_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("omit_by([1, 2, 3], fn(k, v) { return true; });")

    def test_omit_by_with_non_callable_predicate_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('omit_by({"a": 1}, "not a function");')

    def test_omit_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('omit_by({"a": 1});')
        with self.assertRaises(CinderRuntimeError):
            run('omit_by({"a": 1}, fn(k, v) { return true; }, 1);')


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


class TestCapitalize(unittest.TestCase):
    def test_capitalize_lowercase_word(self):
        self.assertEqual(
            run('let result = capitalize("hello");').get("result"), "Hello"
        )

    def test_capitalize_already_capitalized(self):
        self.assertEqual(
            run('let result = capitalize("Hello");').get("result"), "Hello"
        )

    def test_capitalize_only_touches_first_character(self):
        # Deliberately not Python's str.capitalize(), which would also
        # lowercase the remainder.
        self.assertEqual(
            run('let result = capitalize("hELLO");').get("result"), "HELLO"
        )

    def test_capitalize_empty_string(self):
        self.assertEqual(run('let result = capitalize("");').get("result"), "")

    def test_capitalize_non_alphabetic_first_character(self):
        self.assertEqual(
            run('let result = capitalize("1abc");').get("result"), "1abc"
        )

    def test_capitalize_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("capitalize(1);")

    def test_capitalize_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("capitalize();")
        with self.assertRaises(CinderRuntimeError):
            run('capitalize("a", "b");')


class TestTitle(unittest.TestCase):
    def test_title_single_word(self):
        self.assertEqual(run('let result = title("hello");').get("result"), "Hello")

    def test_title_multiple_words(self):
        self.assertEqual(
            run('let result = title("hello world");').get("result"), "Hello World"
        )

    def test_title_preserves_internal_whitespace_runs(self):
        self.assertEqual(
            run('let result = title("hello   world");').get("result"),
            "Hello   World",
        )

    def test_title_preserves_leading_and_trailing_whitespace(self):
        self.assertEqual(
            run('let result = title("  hello world  ");').get("result"),
            "  Hello World  ",
        )

    def test_title_only_touches_first_letter_of_each_word(self):
        # Deliberately not Python's str.title(), which also lowercases the
        # rest of each word and mishandles apostrophes.
        self.assertEqual(
            run('let result = title("won\'t stop");').get("result"), "Won't Stop"
        )

    def test_title_empty_string(self):
        self.assertEqual(run('let result = title("");').get("result"), "")

    def test_title_word_with_leading_non_alphabetic_character(self):
        self.assertEqual(
            run('let result = title("1abc test");').get("result"), "1Abc Test"
        )

    def test_title_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("title(1);")

    def test_title_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("title();")
        with self.assertRaises(CinderRuntimeError):
            run('title("a", "b");')


class TestSwapCase(unittest.TestCase):
    def test_swap_case_mixed(self):
        self.assertEqual(
            run('let result = swap_case("Hello World");').get("result"),
            "hELLO wORLD",
        )

    def test_swap_case_empty_string(self):
        self.assertEqual(run('let result = swap_case("");').get("result"), "")

    def test_swap_case_leaves_non_alphabetic_untouched(self):
        self.assertEqual(
            run('let result = swap_case("123 abc XYZ");').get("result"),
            "123 ABC xyz",
        )

    def test_swap_case_all_uppercase(self):
        self.assertEqual(run('let result = swap_case("ABC");').get("result"), "abc")

    def test_swap_case_all_lowercase(self):
        self.assertEqual(run('let result = swap_case("abc");').get("result"), "ABC")

    def test_swap_case_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("swap_case(5);")

    def test_swap_case_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("swap_case();")
        with self.assertRaises(CinderRuntimeError):
            run('swap_case("a", "b");')


class TestTrim(unittest.TestCase):
    def test_trim_strips_leading_and_trailing_whitespace(self):
        self.assertEqual(run('let result = trim("  hi  ");').get("result"), "hi")

    def test_trim_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("trim(1);")

    def test_trim_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('trim("a", "b");')


class TestTrimStart(unittest.TestCase):
    def test_trim_start_strips_leading_whitespace_only(self):
        self.assertEqual(
            run('let result = trim_start("  hi  ");').get("result"), "hi  "
        )

    def test_trim_start_no_whitespace_is_noop(self):
        self.assertEqual(run('let result = trim_start("hi");').get("result"), "hi")

    def test_trim_start_empty_string(self):
        self.assertEqual(run('let result = trim_start("");').get("result"), "")

    def test_trim_start_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("trim_start(1);")

    def test_trim_start_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('trim_start("a", "b");')


class TestTrimEnd(unittest.TestCase):
    def test_trim_end_strips_trailing_whitespace_only(self):
        self.assertEqual(
            run('let result = trim_end("  hi  ");').get("result"), "  hi"
        )

    def test_trim_end_no_whitespace_is_noop(self):
        self.assertEqual(run('let result = trim_end("hi");').get("result"), "hi")

    def test_trim_end_empty_string(self):
        self.assertEqual(run('let result = trim_end("");').get("result"), "")

    def test_trim_end_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("trim_end(1);")

    def test_trim_end_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('trim_end("a", "b");')


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


class TestLines(unittest.TestCase):
    def test_lines_splits_on_newline(self):
        env = run('let result = lines("a\\nb\\nc");')
        self.assertEqual(env.get("result"), ["a", "b", "c"])

    def test_lines_preserves_empty_line(self):
        env = run('let result = lines("a\\n\\nb");')
        self.assertEqual(env.get("result"), ["a", "", "b"])

    def test_lines_of_empty_string_is_single_empty_string(self):
        env = run('let result = lines("");')
        self.assertEqual(env.get("result"), [""])

    def test_lines_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("lines(1);")

    def test_lines_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('lines("a", "b");')


class TestWords(unittest.TestCase):
    def test_words_splits_on_whitespace_runs(self):
        env = run('let result = words("  a   b\\tc\\n");')
        self.assertEqual(env.get("result"), ["a", "b", "c"])

    def test_words_of_empty_string_is_empty_list(self):
        env = run('let result = words("");')
        self.assertEqual(env.get("result"), [])

    def test_words_of_all_whitespace_is_empty_list(self):
        env = run('let result = words("   ");')
        self.assertEqual(env.get("result"), [])

    def test_words_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("words(1);")

    def test_words_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('words("a", "b");')


class TestChars(unittest.TestCase):
    def test_chars_splits_into_characters(self):
        env = run('let result = chars("abc");')
        self.assertEqual(env.get("result"), ["a", "b", "c"])

    def test_chars_of_empty_string_is_empty_list(self):
        env = run('let result = chars("");')
        self.assertEqual(env.get("result"), [])

    def test_chars_of_single_character(self):
        env = run('let result = chars("a");')
        self.assertEqual(env.get("result"), ["a"])

    def test_chars_keeps_whitespace(self):
        env = run('let result = chars(" a ");')
        self.assertEqual(env.get("result"), [" ", "a", " "])

    def test_chars_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chars(5);")

    def test_chars_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('chars("a", "b");')


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


class TestFindLast(unittest.TestCase):
    def test_find_last_returns_index_of_last_match(self):
        self.assertEqual(run('let result = find_last("abcabc", "a");').get("result"), 3)

    def test_find_last_contrasts_with_find_on_same_input(self):
        env = run(
            'let last = find_last("abcabc", "a"); '
            'let first = find("abcabc", "a");'
        )
        self.assertEqual(env.get("last"), 3)
        self.assertEqual(env.get("first"), 0)

    def test_find_last_returns_negative_one_when_not_found(self):
        self.assertEqual(run('let result = find_last("abcabc", "z");').get("result"), -1)

    def test_find_last_on_empty_needle_returns_haystack_length(self):
        self.assertEqual(run('let result = find_last("hello", "");').get("result"), 5)

    def test_find_last_on_both_empty_returns_zero(self):
        self.assertEqual(run('let result = find_last("", "");').get("result"), 0)

    def test_find_last_returns_last_of_overlapping_matches(self):
        self.assertEqual(run('let result = find_last("aaa", "a");').get("result"), 2)

    def test_find_last_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('find_last(5, "a");')
        self.assertIn("find_last", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_find_last_on_non_string_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('find_last("abc", 5);')
        self.assertIn("find_last", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_find_last_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('find_last("hello");')


class TestIndexOf(unittest.TestCase):
    def test_index_of_returns_index_of_first_match(self):
        self.assertEqual(run('let result = index_of([1, 2, 3], 2);').get("result"), 1)

    def test_index_of_returns_negative_one_when_not_found(self):
        self.assertEqual(run('let result = index_of([1, 2, 3], 9);').get("result"), -1)

    def test_index_of_on_empty_list_returns_negative_one(self):
        self.assertEqual(run('let result = index_of([], 1);').get("result"), -1)

    def test_index_of_returns_first_match_not_last(self):
        self.assertEqual(
            run('let result = index_of(["a", "b", "a"], "a");').get("result"), 0
        )

    def test_index_of_uses_value_equality_for_nested_lists(self):
        self.assertEqual(
            run('let result = index_of([[1, 2], [3, 4]], [3, 4]);').get("result"), 1
        )

    def test_index_of_does_not_conflate_bool_with_int(self):
        self.assertEqual(
            run('let result = index_of([1, 2, 3], true);').get("result"), -1
        )
        self.assertEqual(
            run('let result = index_of([true, false], true);').get("result"), 0
        )

    def test_index_of_on_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('index_of(5, 1);')

    def test_index_of_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('index_of([1]);')
        with self.assertRaises(CinderRuntimeError):
            run('index_of([1], 2, 3);')


class TestLastIndexOf(unittest.TestCase):
    def test_last_index_of_returns_index_of_last_match(self):
        self.assertEqual(
            run('let result = last_index_of([1, 2, 3, 2, 1], 2);').get("result"), 3
        )

    def test_last_index_of_returns_negative_one_when_not_found(self):
        self.assertEqual(
            run('let result = last_index_of([1, 2, 3], 9);').get("result"), -1
        )

    def test_last_index_of_on_empty_list_returns_negative_one(self):
        self.assertEqual(run('let result = last_index_of([], 1);').get("result"), -1)

    def test_last_index_of_does_not_conflate_bool_with_int(self):
        self.assertEqual(
            run('let result = last_index_of([1, true, 0, false], true);').get("result"),
            1,
        )
        self.assertEqual(
            run('let result = last_index_of([1, true, 0, false], false);').get("result"),
            3,
        )

    def test_last_index_of_on_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('last_index_of(5, 1);')

    def test_last_index_of_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('last_index_of([1]);')
        with self.assertRaises(CinderRuntimeError):
            run('last_index_of([1], 2, 3);')


class TestFindIndex(unittest.TestCase):
    def test_find_index_returns_index_of_first_match(self):
        env = run("let result = find_index([1, 2, 3, 4], fn(n) { return n > 2; });")
        self.assertEqual(env.get("result"), 2)

    def test_find_index_returns_negative_one_when_not_found(self):
        env = run("let result = find_index([1, 2, 3], fn(n) { return n > 10; });")
        self.assertEqual(env.get("result"), -1)

    def test_find_index_on_empty_list_returns_negative_one_and_never_calls_fn(self):
        env = run(
            "let calls = []; "
            "let result = find_index([], fn(n) { push(calls, n); return n; });"
        )
        self.assertEqual(env.get("result"), -1)
        self.assertEqual(env.get("calls"), [])

    def test_find_index_short_circuits_after_first_match(self):
        env = run(
            "let calls = []; "
            "let result = find_index([1, 2, 3, 4], fn(n) { push(calls, n); return n > 2; });"
        )
        self.assertEqual(env.get("result"), 2)
        self.assertEqual(env.get("calls"), [1, 2, 3])

    def test_find_index_on_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("find_index(5, fn(n) { return n; });")
        self.assertEqual(ctx.exception.line, 1)

    def test_find_index_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("find_index([1, 2], 5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_find_index_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("find_index([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("find_index([1], fn(n) { return n; }, 3);")


class TestFindLastIndex(unittest.TestCase):
    def test_find_last_index_returns_index_of_last_match(self):
        env = run("let result = find_last_index([1, 2, 3, 4], fn(n) { return n > 2; });")
        self.assertEqual(env.get("result"), 3)

    def test_find_last_index_contrasts_with_find_index_on_same_input(self):
        env = run(
            "let last = find_last_index([1, 2, 3, 4], fn(n) { return n > 2; }); "
            "let first = find_index([1, 2, 3, 4], fn(n) { return n > 2; });"
        )
        self.assertEqual(env.get("last"), 3)
        self.assertEqual(env.get("first"), 2)

    def test_find_last_index_returns_negative_one_when_not_found(self):
        env = run("let result = find_last_index([1, 2, 3], fn(n) { return n > 10; });")
        self.assertEqual(env.get("result"), -1)

    def test_find_last_index_on_empty_list_returns_negative_one_and_never_calls_fn(self):
        env = run(
            "let calls = []; "
            "let result = find_last_index([], fn(n) { push(calls, n); return n; });"
        )
        self.assertEqual(env.get("result"), -1)
        self.assertEqual(env.get("calls"), [])

    def test_find_last_index_returns_later_of_two_matching_indices(self):
        env = run("let result = find_last_index([1, 2, 2, 3], fn(n) { return n == 2; });")
        self.assertEqual(env.get("result"), 2)

    def test_find_last_index_on_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("find_last_index(5, fn(n) { return n; });")
        self.assertEqual(ctx.exception.line, 1)
        self.assertIn("find_last_index", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_find_last_index_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("find_last_index([1, 2], 5);")
        self.assertEqual(ctx.exception.line, 1)
        self.assertIn("find_last_index", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_find_last_index_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("find_last_index([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("find_last_index([1], fn(n) { return n; }, 3);")


class TestCount(unittest.TestCase):
    def test_count_returns_number_of_matches(self):
        self.assertEqual(
            run('let result = count([1, 2, 1, 3, 1], 1);').get("result"), 3
        )

    def test_count_returns_zero_when_not_found(self):
        self.assertEqual(run('let result = count([1, 2, 3], 9);').get("result"), 0)

    def test_count_on_empty_list_returns_zero(self):
        self.assertEqual(run('let result = count([], 1);').get("result"), 0)

    def test_count_counts_all_matches_for_strings(self):
        self.assertEqual(
            run('let result = count(["a", "b", "a"], "a");').get("result"), 2
        )

    def test_count_uses_value_equality_for_nested_lists(self):
        self.assertEqual(
            run('let result = count([[1, 2], [1, 2], [3]], [1, 2]);').get("result"),
            2,
        )

    def test_count_does_not_conflate_bool_with_int(self):
        self.assertEqual(
            run('let result = count([1, 2, 3], true);').get("result"), 0
        )
        self.assertEqual(
            run('let result = count([true, false, true], true);').get("result"), 2
        )

    def test_count_on_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('count(5, 1);')

    def test_count_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('count([1]);')
        with self.assertRaises(CinderRuntimeError):
            run('count([1], 2, 3);')


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


class TestStripPrefix(unittest.TestCase):
    def test_strip_prefix_match(self):
        self.assertEqual(
            run('let result = strip_prefix("hello_world", "hello_");').get("result"),
            "world",
        )

    def test_strip_prefix_no_match_unchanged(self):
        self.assertEqual(
            run('let result = strip_prefix("hello", "xyz");').get("result"), "hello"
        )

    def test_strip_prefix_empty_prefix_unchanged(self):
        self.assertEqual(
            run('let result = strip_prefix("hello", "");').get("result"), "hello"
        )

    def test_strip_prefix_on_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_prefix(1, "h");')

    def test_strip_prefix_non_string_prefix_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_prefix("hello", 1);')

    def test_strip_prefix_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_prefix("hello");')


class TestStripSuffix(unittest.TestCase):
    def test_strip_suffix_match(self):
        self.assertEqual(
            run('let result = strip_suffix("file.txt", ".txt");').get("result"), "file"
        )

    def test_strip_suffix_no_match_unchanged(self):
        self.assertEqual(
            run('let result = strip_suffix("file", ".txt");').get("result"), "file"
        )

    def test_strip_suffix_empty_suffix_unchanged(self):
        self.assertEqual(
            run('let result = strip_suffix("file", "");').get("result"), "file"
        )

    def test_strip_suffix_on_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_suffix(1, ".txt");')

    def test_strip_suffix_non_string_suffix_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_suffix("file", 1);')

    def test_strip_suffix_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('strip_suffix("file");')


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


class TestReplaceFirst(unittest.TestCase):
    def test_replace_first_only_changes_leftmost_occurrence(self):
        self.assertEqual(run('let result = replace_first("a-a-a", "a", "b");').get("result"), "b-a-a")

    def test_replace_contrasts_by_replacing_all_occurrences(self):
        self.assertEqual(run('let result = replace("a-a-a", "a", "b");').get("result"), "b-b-b")

    def test_replace_first_replaces_first_of_multiple_matches(self):
        self.assertEqual(run('let result = replace_first("hello", "l", "L");').get("result"), "heLlo")

    def test_replace_first_no_match_returns_unchanged(self):
        self.assertEqual(run('let result = replace_first("hello", "xyz", "L");').get("result"), "hello")

    def test_replace_first_empty_old_matches_at_start(self):
        self.assertEqual(run('let result = replace_first("hello", "", "X");').get("result"), "Xhello")

    def test_replace_first_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('replace_first(5, "a", "b");')
        self.assertIn("replace_first", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_replace_first_on_non_string_old_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('replace_first("a", 5, "b");')
        self.assertIn("replace_first", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_replace_first_on_non_string_new_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('replace_first("a", "a", 5);')
        self.assertIn("replace_first", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_replace_first_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('replace_first("a", "a");')


class TestPadStart(unittest.TestCase):
    def test_pad_start_pads_on_the_left(self):
        self.assertEqual(run('let result = pad_start("7", 3, "0");').get("result"), "007")

    def test_pad_start_already_at_width_unchanged(self):
        self.assertEqual(run('let result = pad_start("hello", 3, " ");').get("result"), "hello")

    def test_pad_start_empty_string(self):
        self.assertEqual(run('let result = pad_start("", 3, "x");').get("result"), "xxx")

    def test_pad_start_exactly_at_width_unchanged(self):
        self.assertEqual(run('let result = pad_start("ab", 2, "0");').get("result"), "ab")

    def test_pad_start_multi_character_fill_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_start("7", 3, "ab");')

    def test_pad_start_negative_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_start("7", -1, "0");')

    def test_pad_start_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_start(5, 3, "0");')

    def test_pad_start_on_non_int_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_start("7", "3", "0");')

    def test_pad_start_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_start("7", 3);')


class TestPadEnd(unittest.TestCase):
    def test_pad_end_pads_on_the_right(self):
        self.assertEqual(run('let result = pad_end("7", 3, "0");').get("result"), "700")

    def test_pad_end_already_at_width_unchanged(self):
        self.assertEqual(run('let result = pad_end("hello", 3, " ");').get("result"), "hello")

    def test_pad_end_empty_string(self):
        self.assertEqual(run('let result = pad_end("", 3, "x");').get("result"), "xxx")

    def test_pad_end_exactly_at_width_unchanged(self):
        self.assertEqual(run('let result = pad_end("ab", 2, "0");').get("result"), "ab")

    def test_pad_end_multi_character_fill_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_end("7", 3, "ab");')

    def test_pad_end_negative_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_end("7", -1, "0");')

    def test_pad_end_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_end(5, 3, "0");')

    def test_pad_end_on_non_int_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_end("7", "3", "0");')

    def test_pad_end_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_end("7", 3);')


class TestPadCenter(unittest.TestCase):
    def test_pad_center_odd_padding_favors_left(self):
        self.assertEqual(run('let result = pad_center("ab", 5, "*");').get("result"), "**ab*")

    def test_pad_center_even_padding_splits_evenly(self):
        self.assertEqual(run('let result = pad_center("ab", 6, "*");').get("result"), "**ab**")

    def test_pad_center_width_smaller_than_string_unchanged(self):
        self.assertEqual(run('let result = pad_center("hello", 3, "*");').get("result"), "hello")

    def test_pad_center_exactly_at_width_unchanged(self):
        self.assertEqual(run('let result = pad_center("hello", 5, "*");').get("result"), "hello")

    def test_pad_center_empty_string(self):
        self.assertEqual(run('let result = pad_center("", 3, "*");').get("result"), "***")

    def test_pad_center_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_center(5, 3, "*");')

    def test_pad_center_on_non_int_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_center("ab", "3", "*");')

    def test_pad_center_negative_width_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_center("ab", -1, "*");')

    def test_pad_center_multi_character_fill_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_center("ab", 5, "**");')

    def test_pad_center_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pad_center("ab", 5);')


class TestTruncate(unittest.TestCase):
    def test_truncate_cuts_and_appends_suffix(self):
        self.assertEqual(run('let result = truncate("hello world", 8, "...");').get("result"), "hello...")

    def test_truncate_short_max_length(self):
        self.assertEqual(run('let result = truncate("hello world", 5, "...");').get("result"), "he...")

    def test_truncate_shorter_than_max_length_unchanged(self):
        self.assertEqual(run('let result = truncate("hello", 10, "...");').get("result"), "hello")

    def test_truncate_exactly_at_max_length_unchanged(self):
        self.assertEqual(run('let result = truncate("hello", 5, "...");').get("result"), "hello")

    def test_truncate_max_length_smaller_than_suffix(self):
        self.assertEqual(run('let result = truncate("hello world", 1, "...");').get("result"), "...")

    def test_truncate_empty_suffix_is_hard_cut(self):
        self.assertEqual(run('let result = truncate("hello", 3, "");').get("result"), "hel")

    def test_truncate_on_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('truncate(5, 3, "...");')
        self.assertIn("truncate", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_truncate_on_non_int_max_length_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('truncate("hello", "3", "...");')
        self.assertIn("truncate", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_truncate_negative_max_length_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('truncate("hello", -1, "...");')
        self.assertIn("truncate", ctx.exception.message)
        self.assertIn("-1", ctx.exception.message)

    def test_truncate_on_non_string_suffix_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('truncate("hello", 3, 5);')
        self.assertIn("truncate", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_truncate_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('truncate("hello", 3);')


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


class TestSign(unittest.TestCase):
    def test_sign_of_positive_int(self):
        self.assertEqual(run("let result = sign(5);").get("result"), 1)

    def test_sign_of_negative_int(self):
        self.assertEqual(run("let result = sign(-5);").get("result"), -1)

    def test_sign_of_zero_int(self):
        self.assertEqual(run("let result = sign(0);").get("result"), 0)

    def test_sign_of_positive_float(self):
        self.assertEqual(run("let result = sign(3.5);").get("result"), 1)

    def test_sign_of_negative_float(self):
        self.assertEqual(run("let result = sign(-3.5);").get("result"), -1)

    def test_sign_of_zero_float(self):
        self.assertEqual(run("let result = sign(0.0);").get("result"), 0)

    def test_sign_result_type_is_always_int(self):
        self.assertEqual(run("let result = type(sign(3.5));").get("result"), "int")
        self.assertEqual(run("let result = type(sign(-3.5));").get("result"), "int")
        self.assertEqual(run("let result = type(sign(0.0));").get("result"), "int")

    def test_sign_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sign("x");')

    def test_sign_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sign(1, 2);")


class TestIsPositive(unittest.TestCase):
    def test_is_positive_of_positive_int(self):
        self.assertEqual(run("let result = is_positive(5);").get("result"), True)

    def test_is_positive_of_positive_float(self):
        self.assertEqual(run("let result = is_positive(1.5);").get("result"), True)

    def test_is_positive_of_negative_int(self):
        self.assertEqual(run("let result = is_positive(-5);").get("result"), False)

    def test_is_positive_of_zero(self):
        self.assertEqual(run("let result = is_positive(0);").get("result"), False)

    def test_is_positive_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_positive("5");')
        self.assertIn("is_positive", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_positive_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_positive(true);")
        self.assertIn("is_positive", ctx.exception.message)

    def test_is_positive_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_positive(1, 2);")


class TestIsNegative(unittest.TestCase):
    def test_is_negative_of_negative_int(self):
        self.assertEqual(run("let result = is_negative(-5);").get("result"), True)

    def test_is_negative_of_negative_float(self):
        self.assertEqual(run("let result = is_negative(-1.5);").get("result"), True)

    def test_is_negative_of_positive_int(self):
        self.assertEqual(run("let result = is_negative(5);").get("result"), False)

    def test_is_negative_of_zero(self):
        self.assertEqual(run("let result = is_negative(0);").get("result"), False)

    def test_is_negative_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_negative("5");')
        self.assertIn("is_negative", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_negative_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_negative(true);")
        self.assertIn("is_negative", ctx.exception.message)

    def test_is_negative_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_negative(1, 2);")


class TestIsZero(unittest.TestCase):
    def test_is_zero_of_zero_int(self):
        self.assertEqual(run("let result = is_zero(0);").get("result"), True)

    def test_is_zero_of_zero_float(self):
        self.assertEqual(run("let result = is_zero(0.0);").get("result"), True)

    def test_is_zero_of_positive_int(self):
        self.assertEqual(run("let result = is_zero(5);").get("result"), False)

    def test_is_zero_of_negative_int(self):
        self.assertEqual(run("let result = is_zero(-5);").get("result"), False)

    def test_is_zero_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_zero("5");')
        self.assertIn("is_zero", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_zero_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_zero(true);")
        self.assertIn("is_zero", ctx.exception.message)

    def test_is_zero_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_zero(1, 2);")

    def test_is_zero_mutual_exclusivity(self):
        for value in (-5, -1.5, 0, 0.0, 5, 1.5):
            source = (
                f"let a = is_positive({value}); "
                f"let b = is_negative({value}); "
                f"let c = is_zero({value});"
            )
            result = run(source)
            self.assertEqual(
                sum([result.get("a"), result.get("b"), result.get("c")]), 1
            )


class TestIsEven(unittest.TestCase):
    def test_is_even_of_even_int(self):
        self.assertEqual(run("let result = is_even(4);").get("result"), True)

    def test_is_even_of_odd_int(self):
        self.assertEqual(run("let result = is_even(3);").get("result"), False)

    def test_is_even_of_zero(self):
        self.assertEqual(run("let result = is_even(0);").get("result"), True)

    def test_is_even_of_negative_even_int(self):
        self.assertEqual(run("let result = is_even(-4);").get("result"), True)

    def test_is_even_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_even(4.0);")
        self.assertIn("is_even", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_even_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_even("4");')
        self.assertIn("is_even", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_even_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_even();")


class TestIsOdd(unittest.TestCase):
    def test_is_odd_of_odd_int(self):
        self.assertEqual(run("let result = is_odd(3);").get("result"), True)

    def test_is_odd_of_even_int(self):
        self.assertEqual(run("let result = is_odd(4);").get("result"), False)

    def test_is_odd_of_negative_odd_int(self):
        self.assertEqual(run("let result = is_odd(-3);").get("result"), True)

    def test_is_odd_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_odd(4.0);")
        self.assertIn("is_odd", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_odd_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_odd("4");')
        self.assertIn("is_odd", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_odd_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_odd(1, 2);")


class TestIsDivisible(unittest.TestCase):
    def test_is_divisible_true(self):
        self.assertEqual(run("let result = is_divisible(10, 5);").get("result"), True)

    def test_is_divisible_false(self):
        self.assertEqual(run("let result = is_divisible(10, 3);").get("result"), False)

    def test_is_divisible_zero_dividend(self):
        self.assertEqual(run("let result = is_divisible(0, 5);").get("result"), True)

    def test_is_divisible_negative_dividend(self):
        self.assertEqual(run("let result = is_divisible(-10, 5);").get("result"), True)

    def test_is_divisible_negative_divisor(self):
        self.assertEqual(run("let result = is_divisible(10, -5);").get("result"), True)

    def test_is_divisible_agrees_with_is_even(self):
        for x in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
            expected = run(f"let result = is_even({x});").get("result")
            actual = run(f"let result = is_divisible({x}, 2);").get("result")
            self.assertEqual(actual, expected)

    def test_is_divisible_agrees_with_is_odd(self):
        for x in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
            expected = run(f"let result = is_odd({x});").get("result")
            actual = run(f"let result = not is_divisible({x}, 2);").get("result")
            self.assertEqual(actual, expected)

    def test_is_divisible_by_zero_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_divisible(10, 0);")
        self.assertIn("is_divisible() divisor must not be zero", ctx.exception.message)

    def test_is_divisible_non_int_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_divisible(1.5, 2);")
        self.assertIn("is_divisible", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_divisible_non_int_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_divisible(10, 1.5);")
        self.assertIn("is_divisible", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_divisible_bool_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_divisible(true, 2);")
        self.assertIn("is_divisible", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_is_divisible_bool_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_divisible(10, true);")
        self.assertIn("is_divisible", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_is_divisible_string_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_divisible("10", 2);')
        self.assertIn("is_divisible", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_divisible_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_divisible(10);")


class TestIsPrime(unittest.TestCase):
    def test_is_prime_of_two(self):
        self.assertEqual(run("let result = is_prime(2);").get("result"), True)

    def test_is_prime_of_larger_primes(self):
        self.assertEqual(run("let result = is_prime(17);").get("result"), True)
        self.assertEqual(run("let result = is_prime(97);").get("result"), True)

    def test_is_prime_of_one_is_false(self):
        self.assertEqual(run("let result = is_prime(1);").get("result"), False)

    def test_is_prime_of_zero_is_false(self):
        self.assertEqual(run("let result = is_prime(0);").get("result"), False)

    def test_is_prime_of_negative_is_false(self):
        self.assertEqual(run("let result = is_prime(-7);").get("result"), False)

    def test_is_prime_of_composites_is_false(self):
        self.assertEqual(run("let result = is_prime(4);").get("result"), False)
        self.assertEqual(run("let result = is_prime(9);").get("result"), False)
        self.assertEqual(run("let result = is_prime(100);").get("result"), False)

    def test_is_prime_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_prime(4.0);")
        self.assertIn("is_prime", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_prime_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_prime(true);")
        self.assertIn("is_prime", ctx.exception.message)

    def test_is_prime_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_prime("4");')
        self.assertIn("is_prime", ctx.exception.message)
        self.assertIn("string", ctx.exception.message)

    def test_is_prime_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_prime();")


class TestDigitSum(unittest.TestCase):
    def test_digit_sum_of_zero(self):
        self.assertEqual(run("let result = digit_sum(0);").get("result"), 0)

    def test_digit_sum_of_single_digit(self):
        self.assertEqual(run("let result = digit_sum(5);").get("result"), 5)

    def test_digit_sum_of_multiple_digits(self):
        self.assertEqual(run("let result = digit_sum(123);").get("result"), 6)

    def test_digit_sum_of_repeated_digits(self):
        self.assertEqual(run("let result = digit_sum(999);").get("result"), 27)

    def test_digit_sum_of_negative_ignores_sign(self):
        self.assertEqual(run("let result = digit_sum(-123);").get("result"), 6)

    def test_digit_sum_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("digit_sum(3.0);")
        self.assertIn("digit_sum", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_digit_sum_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("digit_sum(true);")
        self.assertIn("digit_sum", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_digit_sum_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("digit_sum();")


class TestReverseInt(unittest.TestCase):
    def test_reverse_int_of_zero(self):
        self.assertEqual(run("let result = reverse_int(0);").get("result"), 0)

    def test_reverse_int_of_single_digit(self):
        self.assertEqual(run("let result = reverse_int(5);").get("result"), 5)

    def test_reverse_int_of_multiple_digits(self):
        self.assertEqual(run("let result = reverse_int(123);").get("result"), 321)

    def test_reverse_int_of_negative_preserves_sign(self):
        self.assertEqual(run("let result = reverse_int(-123);").get("result"), -321)

    def test_reverse_int_of_trailing_zero(self):
        self.assertEqual(run("let result = reverse_int(120);").get("result"), 21)

    def test_reverse_int_of_repeated_trailing_zeros(self):
        self.assertEqual(run("let result = reverse_int(100);").get("result"), 1)

    def test_reverse_int_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("reverse_int(3.0);")
        self.assertIn("reverse_int", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_reverse_int_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("reverse_int(true);")
        self.assertIn("reverse_int", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_reverse_int_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reverse_int();")


class TestIsPerfectSquare(unittest.TestCase):
    def test_is_perfect_square_of_zero(self):
        self.assertEqual(run("let result = is_perfect_square(0);").get("result"), True)

    def test_is_perfect_square_of_one(self):
        self.assertEqual(run("let result = is_perfect_square(1);").get("result"), True)

    def test_is_perfect_square_of_four(self):
        self.assertEqual(run("let result = is_perfect_square(4);").get("result"), True)

    def test_is_perfect_square_of_sixteen(self):
        self.assertEqual(run("let result = is_perfect_square(16);").get("result"), True)

    def test_is_perfect_square_of_non_square_is_false(self):
        self.assertEqual(run("let result = is_perfect_square(15);").get("result"), False)

    def test_is_perfect_square_of_two_is_false(self):
        self.assertEqual(run("let result = is_perfect_square(2);").get("result"), False)

    def test_is_perfect_square_of_negative_is_false(self):
        self.assertEqual(run("let result = is_perfect_square(-4);").get("result"), False)

    def test_is_perfect_square_of_large_bignum(self):
        self.assertEqual(
            run(
                "let result = is_perfect_square("
                "999999999999999999999999 * 999999999999999999999999);"
            ).get("result"),
            True,
        )

    def test_is_perfect_square_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_perfect_square(3.0);")
        self.assertIn("is_perfect_square", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_perfect_square_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_perfect_square(true);")
        self.assertIn("is_perfect_square", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_is_perfect_square_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_perfect_square();")


class TestIsArmstrong(unittest.TestCase):
    def test_is_armstrong_of_zero(self):
        self.assertEqual(run("let result = is_armstrong(0);").get("result"), True)

    def test_is_armstrong_of_single_digit(self):
        self.assertEqual(run("let result = is_armstrong(5);").get("result"), True)

    def test_is_armstrong_of_nine(self):
        self.assertEqual(run("let result = is_armstrong(9);").get("result"), True)

    def test_is_armstrong_of_153(self):
        self.assertEqual(run("let result = is_armstrong(153);").get("result"), True)

    def test_is_armstrong_of_9474(self):
        self.assertEqual(run("let result = is_armstrong(9474);").get("result"), True)

    def test_is_armstrong_of_ten_is_false(self):
        self.assertEqual(run("let result = is_armstrong(10);").get("result"), False)

    def test_is_armstrong_of_123_is_false(self):
        self.assertEqual(run("let result = is_armstrong(123);").get("result"), False)

    def test_is_armstrong_of_negative_is_false(self):
        self.assertEqual(run("let result = is_armstrong(-153);").get("result"), False)

    def test_is_armstrong_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_armstrong(3.0);")
        self.assertIn("is_armstrong", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_armstrong_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_armstrong(true);")
        self.assertIn("is_armstrong", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_is_armstrong_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_armstrong();")


class TestIsLeapYear(unittest.TestCase):
    def test_is_leap_year_of_2000(self):
        self.assertEqual(run("let result = is_leap_year(2000);").get("result"), True)

    def test_is_leap_year_of_1900(self):
        self.assertEqual(run("let result = is_leap_year(1900);").get("result"), False)

    def test_is_leap_year_of_2024(self):
        self.assertEqual(run("let result = is_leap_year(2024);").get("result"), True)

    def test_is_leap_year_of_2023(self):
        self.assertEqual(run("let result = is_leap_year(2023);").get("result"), False)

    def test_is_leap_year_of_zero(self):
        self.assertEqual(run("let result = is_leap_year(0);").get("result"), True)

    def test_is_leap_year_of_negative_2000(self):
        self.assertEqual(run("let result = is_leap_year(-2000);").get("result"), True)

    def test_is_leap_year_of_negative_1900(self):
        self.assertEqual(run("let result = is_leap_year(-1900);").get("result"), False)

    def test_is_leap_year_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_leap_year(4.0);")
        self.assertIn("is_leap_year", ctx.exception.message)
        self.assertIn("float", ctx.exception.message)

    def test_is_leap_year_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_leap_year(true);")
        self.assertIn("is_leap_year", ctx.exception.message)
        self.assertIn("bool", ctx.exception.message)

    def test_is_leap_year_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_leap_year();")


class TestIsPerfectNumber(unittest.TestCase):
    def test_is_perfect_number_of_6(self):
        self.assertEqual(run("let result = is_perfect_number(6);").get("result"), True)

    def test_is_perfect_number_of_28(self):
        self.assertEqual(run("let result = is_perfect_number(28);").get("result"), True)

    def test_is_perfect_number_of_496(self):
        self.assertEqual(run("let result = is_perfect_number(496);").get("result"), True)

    def test_is_perfect_number_of_12_is_false(self):
        self.assertEqual(run("let result = is_perfect_number(12);").get("result"), False)

    def test_is_perfect_number_of_1_is_false(self):
        self.assertEqual(run("let result = is_perfect_number(1);").get("result"), False)

    def test_is_perfect_number_of_zero_is_false(self):
        self.assertEqual(run("let result = is_perfect_number(0);").get("result"), False)

    def test_is_perfect_number_of_negative_is_false(self):
        self.assertEqual(run("let result = is_perfect_number(-6);").get("result"), False)

    def test_is_perfect_number_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_perfect_number(3.0);")
        self.assertIn("is_perfect_number", ctx.exception.message)

    def test_is_perfect_number_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_perfect_number(true);")
        self.assertIn("is_perfect_number", ctx.exception.message)

    def test_is_perfect_number_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_perfect_number();")


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

    def test_max_with_spread_call_argument(self):
        self.assertEqual(run("let result = max(...[3, 1, 2]);").get("result"), 3)


class TestClamp(unittest.TestCase):
    def test_clamp_already_in_range(self):
        self.assertEqual(run("let result = clamp(5, 0, 10);").get("result"), 5)

    def test_clamp_below_range(self):
        self.assertEqual(run("let result = clamp(-5, 0, 10);").get("result"), 0)

    def test_clamp_above_range(self):
        self.assertEqual(run("let result = clamp(15, 0, 10);").get("result"), 10)

    def test_clamp_mixed_int_and_float(self):
        self.assertEqual(run("let result = clamp(2.5, 0, 2);").get("result"), 2)

    def test_clamp_lo_greater_than_hi_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("clamp(5, 10, 0);")

    def test_clamp_non_numeric_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('clamp("x", 0, 10);')

    def test_clamp_non_numeric_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('clamp(5, "x", 10);')

    def test_clamp_non_numeric_third_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('clamp(5, 0, "x");')

    def test_clamp_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("clamp(5, 0);")


class TestRound(unittest.TestCase):
    def test_round_ties_to_even(self):
        self.assertEqual(run("let result = round(2.5);").get("result"), 2)
        self.assertEqual(run("let result = round(3.5);").get("result"), 4)

    def test_round_one_arg_unchanged(self):
        self.assertEqual(run("let result = round(3.456);").get("result"), 3)

    def test_round_with_digits(self):
        self.assertEqual(run("let result = round(3.456, 2);").get("result"), 3.46)

    def test_round_with_zero_digits_returns_float(self):
        self.assertEqual(run("let result = round(3.456, 0);").get("result"), 3.0)
        self.assertIsInstance(run("let result = round(3.456, 0);").get("result"), float)

    def test_round_with_digits_ties_to_even(self):
        self.assertEqual(run("let result = round(2.5, 0);").get("result"), 2.0)

    def test_round_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('round("x");')

    def test_round_of_non_numeric_with_digits_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('round("x", 2);')

    def test_round_non_int_digits_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("round(3.456, 1.5);")
        with self.assertRaises(CinderRuntimeError):
            run('round(3.456, "2");')

    def test_round_negative_digits_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("round(3.456, -1);")

    def test_round_zero_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("round();")

    def test_round_too_many_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("round(1.5, 2, 3);")


class TestToFixed(unittest.TestCase):
    def test_to_fixed_truncates_and_rounds(self):
        self.assertEqual(run("let result = to_fixed(3.14159, 2);").get("result"), "3.14")

    def test_to_fixed_zero_pads_int_input(self):
        self.assertEqual(run("let result = to_fixed(3, 2);").get("result"), "3.00")

    def test_to_fixed_rounds_half_away_via_float_format(self):
        self.assertEqual(run("let result = to_fixed(3.145, 2);").get("result"), "3.15")

    def test_to_fixed_zero_digits_preserves_sign_no_dot(self):
        self.assertEqual(run("let result = to_fixed(-1.5, 0);").get("result"), "-2")

    def test_to_fixed_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('to_fixed("x", 2);')

    def test_to_fixed_non_int_digits_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_fixed(3.456, 1.5);")
        with self.assertRaises(CinderRuntimeError):
            run('to_fixed(3.456, "2");')

    def test_to_fixed_negative_digits_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_fixed(3.456, -1);")

    def test_to_fixed_zero_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_fixed();")

    def test_to_fixed_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("to_fixed(1.5);")
        with self.assertRaises(CinderRuntimeError):
            run("to_fixed(1.5, 2, 3);")


class TestFloor(unittest.TestCase):
    def test_floor_of_positive_float(self):
        self.assertEqual(run("let result = floor(1.5);").get("result"), 1)

    def test_floor_of_negative_float(self):
        self.assertEqual(run("let result = floor(-1.5);").get("result"), -2)

    def test_floor_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('floor("a");')

    def test_floor_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("floor();")


class TestCeil(unittest.TestCase):
    def test_ceil_of_positive_float(self):
        self.assertEqual(run("let result = ceil(1.1);").get("result"), 2)

    def test_ceil_of_negative_float(self):
        self.assertEqual(run("let result = ceil(-1.1);").get("result"), -1)

    def test_ceil_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("ceil(nil);")

    def test_ceil_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("ceil();")


class TestPow(unittest.TestCase):
    def test_pow_of_two_ints_is_int(self):
        result = run("let result = pow(2, 10);").get("result")
        self.assertEqual(result, 1024)
        self.assertIsInstance(result, int)

    def test_pow_with_fractional_exponent_is_float(self):
        result = run("let result = pow(2, 0.5);").get("result")
        self.assertAlmostEqual(result, 1.4142135623730951)
        self.assertIsInstance(result, float)

    def test_pow_with_negative_exponent_is_float(self):
        self.assertEqual(run("let result = pow(2, -1);").get("result"), 0.5)

    def test_pow_of_non_numeric_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pow("a", 2);')

    def test_pow_of_non_numeric_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('pow(2, "a");')

    def test_pow_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pow(2);")

    def test_pow_of_negative_base_with_fractional_exponent_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pow(-8, 0.5);")

    def test_pow_of_zero_base_with_negative_exponent_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pow(0, -1);")

    def test_pow_overflow_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pow(10.0, 400);")


class TestSqrt(unittest.TestCase):
    def test_sqrt_of_perfect_square_is_float(self):
        result = run("let result = sqrt(9);").get("result")
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_sqrt_of_non_perfect_square(self):
        self.assertAlmostEqual(run("let result = sqrt(2);").get("result"), 1.4142135623730951)

    def test_sqrt_of_negative_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sqrt(-1);")

    def test_sqrt_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sqrt("a");')

    def test_sqrt_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sqrt();")


class TestSin(unittest.TestCase):
    def test_sin_of_zero(self):
        result = run("let result = sin(0);").get("result")
        self.assertEqual(result, 0.0)
        self.assertIsInstance(result, float)

    def test_sin_of_int_and_float(self):
        self.assertAlmostEqual(run("let result = sin(1);").get("result"), 0.8414709848078965)
        self.assertAlmostEqual(run("let result = sin(1.0);").get("result"), 0.8414709848078965)

    def test_sin_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sin("a");')

    def test_sin_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sin();")


class TestCos(unittest.TestCase):
    def test_cos_of_zero(self):
        result = run("let result = cos(0);").get("result")
        self.assertEqual(result, 1.0)
        self.assertIsInstance(result, float)

    def test_cos_of_int_and_float(self):
        self.assertAlmostEqual(run("let result = cos(1);").get("result"), 0.5403023058681398)
        self.assertAlmostEqual(run("let result = cos(1.0);").get("result"), 0.5403023058681398)

    def test_cos_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('cos("a");')

    def test_cos_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("cos();")


class TestTan(unittest.TestCase):
    def test_tan_of_zero(self):
        result = run("let result = tan(0);").get("result")
        self.assertEqual(result, 0.0)
        self.assertIsInstance(result, float)

    def test_tan_of_int_and_float(self):
        self.assertAlmostEqual(run("let result = tan(1);").get("result"), 1.5574077246549023)
        self.assertAlmostEqual(run("let result = tan(1.0);").get("result"), 1.5574077246549023)

    def test_tan_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('tan("a");')

    def test_tan_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("tan();")


class TestLog(unittest.TestCase):
    def test_log_of_one(self):
        result = run("let result = log(1);").get("result")
        self.assertEqual(result, 0.0)
        self.assertIsInstance(result, float)

    def test_log_of_e(self):
        self.assertAlmostEqual(run("let result = log(2.718281828459045);").get("result"), 1.0)

    def test_log_of_zero_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("log(0);")

    def test_log_of_negative_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("log(-1);")

    def test_log_of_non_numeric_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('log("a");')

    def test_log_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("log();")


class TestGcd(unittest.TestCase):
    def test_gcd_of_two_positive_ints(self):
        self.assertEqual(run("let result = gcd(12, 18);").get("result"), 6)

    def test_gcd_with_zero_and_nonzero(self):
        self.assertEqual(run("let result = gcd(0, 5);").get("result"), 5)

    def test_gcd_of_two_zeros(self):
        self.assertEqual(run("let result = gcd(0, 0);").get("result"), 0)

    def test_gcd_ignores_sign(self):
        self.assertEqual(run("let result = gcd(-12, 18);").get("result"), 6)

    def test_gcd_of_float_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("gcd(12.0, 18);")

    def test_gcd_of_float_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("gcd(12, 18.0);")

    def test_gcd_of_non_numeric_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('gcd("a", 18);')

    def test_gcd_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("gcd(12);")


class TestLcm(unittest.TestCase):
    def test_lcm_of_two_positive_ints(self):
        self.assertEqual(run("let result = lcm(4, 6);").get("result"), 12)

    def test_lcm_with_zero_and_nonzero(self):
        self.assertEqual(run("let result = lcm(0, 5);").get("result"), 0)

    def test_lcm_ignores_sign(self):
        self.assertEqual(run("let result = lcm(-4, 6);").get("result"), 12)

    def test_lcm_of_float_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("lcm(4.0, 6);")

    def test_lcm_of_float_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("lcm(4, 6.0);")

    def test_lcm_of_non_numeric_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('lcm(4, "a");')

    def test_lcm_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("lcm(4);")


class TestFactorial(unittest.TestCase):
    def test_factorial_of_zero(self):
        self.assertEqual(run("let result = factorial(0);").get("result"), 1)

    def test_factorial_of_one(self):
        self.assertEqual(run("let result = factorial(1);").get("result"), 1)

    def test_factorial_of_five(self):
        self.assertEqual(run("let result = factorial(5);").get("result"), 120)

    def test_factorial_of_ten(self):
        self.assertEqual(run("let result = factorial(10);").get("result"), 3628800)

    def test_factorial_of_twenty_has_no_precision_loss(self):
        self.assertEqual(
            run("let result = factorial(20);").get("result"), 2432902008176640000
        )

    def test_factorial_of_negative_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("factorial(-1);")

    def test_factorial_of_float_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("factorial(3.0);")

    def test_factorial_of_bool_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("factorial(true);")

    def test_factorial_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("factorial(5, 6);")


class TestSum(unittest.TestCase):
    def test_sum_of_ints_is_int(self):
        result = run("let result = sum([1, 2, 3]);").get("result")
        self.assertEqual(result, 6)
        self.assertIsInstance(result, int)

    def test_sum_with_a_float_is_float(self):
        result = run("let result = sum([1, 2.5]);").get("result")
        self.assertEqual(result, 3.5)
        self.assertIsInstance(result, float)

    def test_sum_of_empty_list_is_zero(self):
        result = run("let result = sum([]);").get("result")
        self.assertEqual(result, 0)
        self.assertIsInstance(result, int)

    def test_sum_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sum(["a"]);')

    def test_sum_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("sum(5);")
        self.assertEqual(ctx.exception.line, 1)


class TestSumBy(unittest.TestCase):
    def test_sum_by_doubles_and_sums(self):
        result = run("let result = sum_by([1, 2, 3], fn(n) { return n * 2; });").get("result")
        self.assertEqual(result, 12)

    def test_sum_by_empty_list_is_zero_and_fn_not_called(self):
        calls = run(
            "let calls = 0; "
            "let result = sum_by([], fn(n) { calls = calls + 1; return n; });"
        )
        self.assertEqual(calls.get("result"), 0)
        self.assertEqual(calls.get("calls"), 0)

    def test_sum_by_sums_function_result_not_element(self):
        result = run(
            'let result = sum_by(["a", "bb", "ccc"], fn(s) { return len(s); });'
        ).get("result")
        self.assertEqual(result, 6)

    def test_sum_by_non_numeric_result_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('sum_by([1, 2], fn(n) { return "x"; });')
        self.assertIn("sum_by", str(ctx.exception))
        self.assertIn("string", str(ctx.exception))

    def test_sum_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("sum_by(5, fn(n) { return n; });")
        self.assertIn("sum_by", str(ctx.exception))
        self.assertIn("int", str(ctx.exception))

    def test_sum_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("sum_by([1, 2], 5);")
        self.assertIn("sum_by", str(ctx.exception))
        self.assertIn("int", str(ctx.exception))

    def test_sum_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("sum_by([1]);")
        self.assertEqual(ctx.exception.line, 1)


class TestProduct(unittest.TestCase):
    def test_product_of_ints(self):
        result = run("let result = product([1, 2, 3, 4]);").get("result")
        self.assertEqual(result, 24)

    def test_product_of_single_element_list(self):
        result = run("let result = product([5]);").get("result")
        self.assertEqual(result, 5)

    def test_product_of_empty_list_is_one(self):
        result = run("let result = product([]);").get("result")
        self.assertEqual(result, 1)
        self.assertIsInstance(result, int)

    def test_product_with_a_zero_element_is_zero(self):
        result = run("let result = product([2, 0, 3]);").get("result")
        self.assertEqual(result, 0)

    def test_product_with_a_float_is_float(self):
        result = run("let result = product([1, 2.5, 2]);").get("result")
        self.assertEqual(result, 5)
        self.assertIsInstance(result, float)

    def test_product_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('product([1, "two", 3]);')

    def test_product_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("product(5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_product_of_string_argument_raises_naming_string(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('product("abc");')
        self.assertIn("product", str(ctx.exception))
        self.assertIn("string", str(ctx.exception))


class TestMean(unittest.TestCase):
    def test_mean_of_ints_is_float(self):
        result = run("let result = mean([1, 2, 3]);").get("result")
        self.assertEqual(result, 2.0)
        self.assertIsInstance(result, float)

    def test_mean_of_two_ints_is_float(self):
        result = run("let result = mean([1, 2]);").get("result")
        self.assertEqual(result, 1.5)
        self.assertIsInstance(result, float)

    def test_mean_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("mean([]);")

    def test_mean_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('mean(["a"]);')

    def test_mean_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("mean(5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_mean_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("mean();")


class TestMedian(unittest.TestCase):
    def test_median_of_odd_length_list(self):
        result = run("let result = median([1, 3, 2]);").get("result")
        self.assertEqual(result, 2)

    def test_median_of_even_length_list_is_float(self):
        result = run("let result = median([1, 2, 3, 4]);").get("result")
        self.assertEqual(result, 2.5)
        self.assertIsInstance(result, float)

    def test_median_of_single_element_list(self):
        result = run("let result = median([5]);").get("result")
        self.assertEqual(result, 5)

    def test_median_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("median([]);")

    def test_median_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('median(["a"]);')

    def test_median_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("median(5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_median_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("median();")


class TestVariance(unittest.TestCase):
    def test_variance_of_textbook_example(self):
        result = run("let result = variance([2, 4, 4, 4, 5, 5, 7, 9]);").get("result")
        self.assertEqual(result, 4)

    def test_variance_of_single_element_list_is_zero(self):
        result = run("let result = variance([5]);").get("result")
        self.assertEqual(result, 0)

    def test_variance_of_identical_elements_is_zero(self):
        result = run("let result = variance([3, 3, 3]);").get("result")
        self.assertEqual(result, 0)

    def test_variance_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("variance([]);")

    def test_variance_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('variance([1, "two", 3]);')

    def test_variance_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('variance("abc");')
        self.assertEqual(ctx.exception.line, 1)

    def test_variance_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("variance();")


class TestStdDev(unittest.TestCase):
    def test_std_dev_of_textbook_example(self):
        result = run("let result = std_dev([2, 4, 4, 4, 5, 5, 7, 9]);").get("result")
        self.assertEqual(result, 2)

    def test_std_dev_of_single_element_list_is_zero(self):
        result = run("let result = std_dev([5]);").get("result")
        self.assertEqual(result, 0)

    def test_std_dev_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("std_dev([]);")

    def test_std_dev_of_non_numeric_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('std_dev([1, "two", 3]);')

    def test_std_dev_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('std_dev("abc");')
        self.assertEqual(ctx.exception.line, 1)

    def test_std_dev_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("std_dev();")


class TestMode(unittest.TestCase):
    def test_mode_of_clear_winner(self):
        result = run("let result = mode([1, 2, 2, 3]);").get("result")
        self.assertEqual(result, 2)

    def test_mode_tie_resolves_to_first_appearance(self):
        result = run("let result = mode([1, 1, 2, 2]);").get("result")
        self.assertEqual(result, 1)

    def test_mode_of_single_element_list(self):
        result = run("let result = mode([5]);").get("result")
        self.assertEqual(result, 5)

    def test_mode_works_on_strings(self):
        result = run('let result = mode(["a", "b", "b", "c"]);').get("result")
        self.assertEqual(result, "b")

    def test_mode_splits_bools_from_ints(self):
        result = run("let result = mode([true, false, true]);").get("result")
        self.assertIs(result, True)

        result = run("let result = mode([1, true, 1]);").get("result")
        self.assertEqual(result, 1)
        self.assertNotIsInstance(result, bool)

    def test_mode_of_lists_of_lists_uses_values_equal_fallback(self):
        result = run("let result = mode([[1], [1], [2]]);").get("result")
        self.assertEqual(result, [1])

    def test_mode_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("mode([]);")

    def test_mode_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('mode("abc");')
        self.assertIn("mode", str(ctx.exception))
        self.assertIn("string", str(ctx.exception))

    def test_mode_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("mode();")


class TestAny(unittest.TestCase):
    def test_any_true_when_an_element_is_truthy(self):
        self.assertIs(run("let result = any([false, nil, 1]);").get("result"), True)

    def test_any_false_when_all_elements_falsy(self):
        self.assertIs(run("let result = any([false, nil]);").get("result"), False)

    def test_any_of_empty_list_is_false(self):
        self.assertIs(run("let result = any([]);").get("result"), False)

    def test_any_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("any(5);")
        self.assertEqual(ctx.exception.line, 1)


class TestAll(unittest.TestCase):
    def test_all_true_when_every_element_truthy(self):
        self.assertIs(run('let result = all([1, "a", true]);').get("result"), True)

    def test_all_false_when_an_element_falsy(self):
        self.assertIs(run("let result = all([1, false]);").get("result"), False)

    def test_all_of_empty_list_is_true(self):
        self.assertIs(run("let result = all([]);").get("result"), True)

    def test_all_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("all(5);")
        self.assertEqual(ctx.exception.line, 1)


class TestNone(unittest.TestCase):
    def test_none_true_when_no_element_truthy(self):
        self.assertIs(
            run("let result = none([false, nil, false]);").get("result"), True
        )

    def test_none_false_when_an_element_truthy(self):
        self.assertIs(run("let result = none([false, 1, nil]);").get("result"), False)

    def test_none_of_empty_list_is_true(self):
        self.assertIs(run("let result = none([]);").get("result"), True)

    def test_none_uses_cinder_falsy_set_not_python_falsy_set(self):
        self.assertIs(
            run('let result = none([0, "", nil, false]);').get("result"), False
        )

    def test_none_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("none(5);")
        self.assertIn("none", str(ctx.exception))
        self.assertIn("int", str(ctx.exception))

    def test_none_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("none();")


class TestContains(unittest.TestCase):
    def test_contains_in_list(self):
        self.assertIs(run("let result = contains([1, 2, 3], 2);").get("result"), True)
        self.assertIs(run("let result = contains([1, 2, 3], 9);").get("result"), False)

    def test_contains_does_not_conflate_bool_with_int(self):
        self.assertIs(
            run("let result = contains([1, 2, 3], true);").get("result"), False
        )
        self.assertIs(
            run("let result = contains([0, false], 0);").get("result"), True
        )
        self.assertIs(
            run("let result = contains([0, false], false);").get("result"), True
        )

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

    def test_contains_matches_in_operator(self):
        cases = [
            ("[1, 2], 1", "1 in [1, 2]"),
            ("[1, 2], 9", "9 in [1, 2]"),
            ('{"a": 1}, "a"', '"a" in {"a": 1}'),
            ('{"a": 1}, "b"', '"b" in {"a": 1}'),
            ('"hello", "ell"', '"ell" in "hello"'),
            ('"hello", "xyz"', '"xyz" in "hello"'),
        ]
        for contains_args, in_expr in cases:
            self.assertIs(
                run(f"let result = contains({contains_args});").get("result"),
                run(f"let result = {in_expr};").get("result"),
            )


class TestCopy(unittest.TestCase):
    def test_copy_list_breaks_aliasing(self):
        env = run("let a = [1, 2]; let b = copy(a); push(b, 3);")
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("b"), [1, 2, 3])

    def test_copy_map_breaks_aliasing(self):
        env = run('let a = {"x": 1}; let b = copy(a); b["y"] = 2;')
        self.assertEqual(env.get("a"), {"x": 1})
        self.assertEqual(env.get("b"), {"x": 1, "y": 2})

    def test_copy_is_shallow(self):
        env = run(
            "let a = [1, [2, 3]]; let b = copy(a); push(b[1], 4);"
        )
        self.assertEqual(env.get("a"), [1, [2, 3, 4]])
        self.assertEqual(env.get("b"), [1, [2, 3, 4]])

    def test_copy_on_unsupported_type_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("copy(5);")
        with self.assertRaises(CinderRuntimeError):
            run('copy("a");')

    def test_copy_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("copy([1], [2]);")


class TestDeepCopy(unittest.TestCase):
    def test_deep_copy_breaks_aliasing_at_nested_list_depth(self):
        env = run(
            "let a = [[1, 2], [3]]; let b = deep_copy(a); push(b[0], 99);"
        )
        self.assertEqual(env.get("a"), [[1, 2], [3]])
        self.assertEqual(env.get("b"), [[1, 2, 99], [3]])

    def test_deep_copy_breaks_aliasing_for_nested_list_in_map(self):
        env = run(
            'let a = {"x": [1, 2]}; let b = deep_copy(a); push(b["x"], 3);'
        )
        self.assertEqual(env.get("a"), {"x": [1, 2]})
        self.assertEqual(env.get("b"), {"x": [1, 2, 3]})

    def test_deep_copy_passes_through_non_container_elements(self):
        env = run("let result = deep_copy([1, \"a\", true, nil]);")
        self.assertEqual(env.get("result"), [1, "a", True, None])

    def test_deep_copy_handles_mixed_nesting(self):
        env = run(
            'let a = {"a": [{"b": 1}]}; let b = deep_copy(a); b["a"][0]["b"] = 99;'
        )
        self.assertEqual(env.get("a"), {"a": [{"b": 1}]})
        self.assertEqual(env.get("b"), {"a": [{"b": 99}]})

    def test_deep_copy_on_unsupported_type_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("deep_copy(5);")

    def test_deep_copy_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("deep_copy([1], [2]);")


class TestUnique(unittest.TestCase):
    def test_unique_keeps_first_occurrence_preserving_order(self):
        self.assertEqual(
            run("let result = unique([1, 2, 2, 3, 1]);").get("result"), [1, 2, 3]
        )

    def test_unique_of_empty_list(self):
        self.assertEqual(run("let result = unique([]);").get("result"), [])

    def test_unique_of_strings(self):
        self.assertEqual(
            run('let result = unique(["a", "a", "b"]);').get("result"), ["a", "b"]
        )

    def test_unique_uses_value_equality_for_nested_lists(self):
        self.assertEqual(
            run("let result = unique([[1], [1], [2]]);").get("result"), [[1], [2]]
        )

    def test_unique_does_not_conflate_bool_and_int(self):
        self.assertEqual(
            run("let result = unique([1, true, 0, false]);").get("result"),
            [1, True, 0, False],
        )

    def test_unique_does_not_conflate_bool_and_int_alongside_unhashable_elements(self):
        self.assertEqual(
            run("let result = unique([1, true, [1], [1]]);").get("result"),
            [1, True, [1]],
        )

    def test_unique_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = unique(xs);")
        env.get("result").append(4)
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_unique_returns_new_list_not_same_object(self):
        env = run("let xs = [1, 2, 3]; let result = unique(xs);")
        self.assertIsNot(env.get("result"), env.get("xs"))

    def test_unique_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("unique(5);")

    def test_unique_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("unique([1], 2);")
        with self.assertRaises(CinderRuntimeError):
            run("unique();")


class TestUnionIntersectionDifference(unittest.TestCase):
    def test_union_combines_and_dedupes(self):
        self.assertEqual(
            run("let result = union([1, 2, 3], [2, 3, 4]);").get("result"),
            [1, 2, 3, 4],
        )

    def test_intersection_keeps_common_elements(self):
        self.assertEqual(
            run("let result = intersection([1, 2, 3], [2, 3, 4]);").get("result"),
            [2, 3],
        )

    def test_difference_keeps_elements_not_in_second_list(self):
        self.assertEqual(
            run("let result = difference([1, 2, 3], [2, 3, 4]);").get("result"),
            [1],
        )

    def test_union_does_not_conflate_bool_and_int(self):
        self.assertEqual(
            run("let result = union([1, true], [1, false]);").get("result"),
            [1, True, False],
        )

    def test_union_collapses_duplicates_within_a_single_input(self):
        self.assertEqual(
            run("let result = union([1, 1, 2], [2]);").get("result"), [1, 2]
        )

    def test_union_with_empty_list(self):
        self.assertEqual(run("let result = union([], [1]);").get("result"), [1])

    def test_intersection_with_empty_list(self):
        self.assertEqual(
            run("let result = intersection([], [1]);").get("result"), []
        )

    def test_difference_with_empty_second_list(self):
        self.assertEqual(
            run("let result = difference([], [1]);").get("result"), []
        )

    def test_difference_with_empty_first_list(self):
        self.assertEqual(
            run("let result = difference([1], []);").get("result"), [1]
        )

    def test_union_uses_value_equality_for_nested_lists(self):
        self.assertEqual(
            run("let result = union([[1], [2]], [[1], [3]]);").get("result"),
            [[1], [2], [3]],
        )

    def test_intersection_preserves_first_list_order(self):
        self.assertEqual(
            run("let result = intersection([3, 1, 2], [1, 2, 3]);").get("result"),
            [3, 1, 2],
        )

    def test_union_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("union(5, [1]);")

    def test_union_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("union([1], 5);")

    def test_intersection_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("intersection(5, [1]);")
        with self.assertRaises(CinderRuntimeError):
            run("intersection([1], 5);")

    def test_difference_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("difference(5, [1]);")
        with self.assertRaises(CinderRuntimeError):
            run("difference([1], 5);")

    def test_union_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("union([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("union([1], [2], [3]);")

    def test_intersection_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("intersection([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("intersection([1], [2], [3]);")

    def test_difference_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("difference([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("difference([1], [2], [3]);")


class TestSymmetricDifference(unittest.TestCase):
    def test_symmetric_difference_keeps_elements_unique_to_either_side(self):
        self.assertEqual(
            run(
                "let result = symmetric_difference([1, 2, 3], [2, 3, 4]);"
            ).get("result"),
            [1, 4],
        )

    def test_symmetric_difference_of_identical_lists_is_empty(self):
        self.assertEqual(
            run("let result = symmetric_difference([1, 2], [1, 2]);").get("result"),
            [],
        )

    def test_symmetric_difference_with_empty_second_list(self):
        self.assertEqual(
            run("let result = symmetric_difference([1, 2], []);").get("result"),
            [1, 2],
        )

    def test_symmetric_difference_with_empty_first_list(self):
        self.assertEqual(
            run("let result = symmetric_difference([], [1, 2]);").get("result"),
            [1, 2],
        )

    def test_symmetric_difference_of_two_empty_lists_is_empty(self):
        self.assertEqual(
            run("let result = symmetric_difference([], []);").get("result"), []
        )

    def test_symmetric_difference_dedupes_within_each_input(self):
        self.assertEqual(
            run(
                "let result = symmetric_difference([1, 1, 2], [2, 3]);"
            ).get("result"),
            [1, 3],
        )

    def test_symmetric_difference_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("symmetric_difference(5, [1]);")

    def test_symmetric_difference_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("symmetric_difference([1], 5);")

    def test_symmetric_difference_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("symmetric_difference([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("symmetric_difference([1], [2], [3]);")


class TestIsSubsetIsSuperset(unittest.TestCase):
    def test_is_subset_true_when_all_elements_found(self):
        self.assertIs(
            run("let result = is_subset([1, 2], [1, 2, 3]);").get("result"), True
        )

    def test_is_subset_false_when_element_missing(self):
        self.assertIs(
            run("let result = is_subset([1, 2, 3], [1, 2]);").get("result"), False
        )

    def test_is_subset_empty_first_list_is_true(self):
        self.assertIs(
            run("let result = is_subset([], [1, 2, 3]);").get("result"), True
        )
        self.assertIs(run("let result = is_subset([], []);").get("result"), True)

    def test_is_subset_empty_second_list_is_false(self):
        self.assertIs(
            run("let result = is_subset([1, 2, 3], []);").get("result"), False
        )

    def test_is_subset_duplicates_in_first_list_do_not_require_duplicates(self):
        self.assertIs(
            run("let result = is_subset([1, 1, 2], [1, 2]);").get("result"), True
        )

    def test_is_subset_uses_deep_equality(self):
        self.assertIs(
            run(
                "let result = is_subset([[1, 2]], [[1, 2], [3, 4]]);"
            ).get("result"),
            True,
        )

    def test_is_subset_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_subset(5, [1, 2]);")
        self.assertIn("is_subset", ctx.exception.message)
        self.assertIn("first", ctx.exception.message)

    def test_is_subset_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_subset([1, 2], 5);")
        self.assertIn("is_subset", ctx.exception.message)
        self.assertIn("second", ctx.exception.message)

    def test_is_subset_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_subset([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("is_subset([1], [2], [3]);")

    def test_is_superset_true_when_first_contains_all_of_second(self):
        self.assertIs(
            run("let result = is_superset([1, 2, 3], [1, 2]);").get("result"), True
        )

    def test_is_superset_false_when_second_has_extra_element(self):
        self.assertIs(
            run("let result = is_superset([1, 2], [1, 2, 3]);").get("result"), False
        )

    def test_is_superset_is_flipped_is_subset(self):
        self.assertEqual(
            run(
                "let a = [1, 2]; let b = [1, 2, 3];"
                "let result = [is_subset(a, b), is_superset(b, a)];"
            ).get("result"),
            [True, True],
        )

    def test_is_superset_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_superset(5, [1, 2]);")
        self.assertIn("is_superset", ctx.exception.message)
        self.assertIn("first", ctx.exception.message)

    def test_is_superset_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_superset([1, 2], 5);")
        self.assertIn("is_superset", ctx.exception.message)
        self.assertIn("second", ctx.exception.message)

    def test_is_superset_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_superset([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("is_superset([1], [2], [3]);")

    def test_is_disjoint_true_when_no_shared_elements(self):
        self.assertIs(
            run("let result = is_disjoint([1, 2], [3, 4]);").get("result"), True
        )

    def test_is_disjoint_false_when_element_shared(self):
        self.assertIs(
            run("let result = is_disjoint([1, 2], [2, 3]);").get("result"), False
        )

    def test_is_disjoint_empty_first_list_is_true(self):
        self.assertIs(
            run("let result = is_disjoint([], [1, 2, 3]);").get("result"), True
        )

    def test_is_disjoint_both_empty_is_true(self):
        self.assertIs(run("let result = is_disjoint([], []);").get("result"), True)

    def test_is_disjoint_matches_empty_intersection(self):
        self.assertEqual(
            run(
                "let a = [1, 2, 3]; let b = [3, 4, 5];"
                "let result = [is_disjoint(a, b), len(intersection(a, b)) == 0];"
            ).get("result"),
            [False, False],
        )
        self.assertEqual(
            run(
                "let a = [1, 2]; let b = [3, 4];"
                "let result = [is_disjoint(a, b), len(intersection(a, b)) == 0];"
            ).get("result"),
            [True, True],
        )

    def test_is_disjoint_uses_deep_equality(self):
        self.assertIs(
            run(
                "let result = is_disjoint([[1, 2]], [[1, 2]]);"
            ).get("result"),
            False,
        )

    def test_is_disjoint_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_disjoint(5, [1, 2]);")
        self.assertIn("is_disjoint", ctx.exception.message)
        self.assertIn("first", ctx.exception.message)

    def test_is_disjoint_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_disjoint([1, 2], 5);")
        self.assertIn("is_disjoint", ctx.exception.message)
        self.assertIn("second", ctx.exception.message)

    def test_is_disjoint_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_disjoint([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("is_disjoint([1], [2], [3]);")


class TestInterleave(unittest.TestCase):
    def test_interleave_equal_length_lists(self):
        self.assertEqual(
            run("let result = interleave([1, 3, 5], [2, 4, 6]);").get("result"),
            [1, 2, 3, 4, 5, 6],
        )

    def test_interleave_appends_remaining_elements_of_longer_list(self):
        self.assertEqual(
            run("let result = interleave([1, 2], [10, 20, 30, 40]);").get("result"),
            [1, 10, 2, 20, 30, 40],
        )

    def test_interleave_first_list_longer(self):
        self.assertEqual(
            run("let result = interleave([1, 2, 3, 4], [10, 20]);").get("result"),
            [1, 10, 2, 20, 3, 4],
        )

    def test_interleave_first_list_empty(self):
        self.assertEqual(
            run("let result = interleave([], [1, 2]);").get("result"), [1, 2]
        )

    def test_interleave_second_list_empty(self):
        self.assertEqual(
            run("let result = interleave([1, 2], []);").get("result"), [1, 2]
        )

    def test_interleave_both_empty(self):
        self.assertEqual(run("let result = interleave([], []);").get("result"), [])

    def test_interleave_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("interleave(5, [1]);")

    def test_interleave_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("interleave([1], 5);")

    def test_interleave_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("interleave([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("interleave([1], [2], [3]);")


class TestInterpose(unittest.TestCase):
    def test_interpose_basic(self):
        self.assertEqual(
            run("let result = interpose([1, 2, 3], 0);").get("result"),
            [1, 0, 2, 0, 3],
        )

    def test_interpose_single_element(self):
        self.assertEqual(run("let result = interpose([1], 0);").get("result"), [1])

    def test_interpose_empty_list(self):
        self.assertEqual(run("let result = interpose([], 0);").get("result"), [])

    def test_interpose_separator_type_need_not_match(self):
        self.assertEqual(
            run('let result = interpose([1, 2], "x");').get("result"), [1, "x", 2]
        )

    def test_interpose_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("interpose(5, 0);")

    def test_interpose_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("interpose([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("interpose([1], 0, 0);")


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


class TestRotate(unittest.TestCase):
    def test_rotate_left_by_positive_n(self):
        self.assertEqual(
            run("let result = rotate([1, 2, 3, 4, 5], 2);").get("result"),
            [3, 4, 5, 1, 2],
        )

    def test_rotate_right_by_negative_n(self):
        self.assertEqual(
            run("let result = rotate([1, 2, 3, 4, 5], -1);").get("result"),
            [5, 1, 2, 3, 4],
        )

    def test_rotate_by_zero_is_no_op(self):
        self.assertEqual(run("let result = rotate([1, 2, 3], 0);").get("result"), [1, 2, 3])

    def test_rotate_by_length_is_no_op(self):
        self.assertEqual(run("let result = rotate([1, 2, 3], 3);").get("result"), [1, 2, 3])

    def test_rotate_by_more_than_length_wraps_via_modulo(self):
        self.assertEqual(run("let result = rotate([1, 2, 3], 4);").get("result"), [2, 3, 1])

    def test_rotate_empty_list_is_always_a_no_op(self):
        self.assertEqual(run("let result = rotate([], 5);").get("result"), [])

    def test_rotate_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = rotate(xs, 1);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [2, 3, 1])

    def test_rotate_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('rotate("hi", 1);')

    def test_rotate_of_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('rotate([1, 2, 3], "1");')

    def test_rotate_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("rotate([1, 2, 3]);")


class TestFirst(unittest.TestCase):
    def test_first_of_multi_element_list(self):
        self.assertEqual(run("let result = first([1, 2, 3]);").get("result"), 1)

    def test_first_of_single_element_list(self):
        self.assertEqual(run("let result = first([42]);").get("result"), 42)

    def test_first_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("first([]);")

    def test_first_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("first(5);")

    def test_first_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("first([1], 2);")


class TestLast(unittest.TestCase):
    def test_last_of_multi_element_list(self):
        self.assertEqual(run("let result = last([1, 2, 3]);").get("result"), 3)

    def test_last_of_single_element_list(self):
        self.assertEqual(run("let result = last([42]);").get("result"), 42)

    def test_last_of_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("last([]);")

    def test_last_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("last(5);")

    def test_last_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("last([1], 2);")


class TestRandomInt(unittest.TestCase):
    def test_degenerate_range_is_exact(self):
        for _ in range(10):
            self.assertEqual(run("let result = random_int(1, 1);").get("result"), 1)

    def test_result_is_int_within_bounds(self):
        for _ in range(200):
            result = run("let result = random_int(1, 10);").get("result")
            self.assertIsInstance(result, int)
            self.assertGreaterEqual(result, 1)
            self.assertLessEqual(result, 10)

    def test_min_greater_than_max_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("random_int(5, 1);")

    def test_non_int_min_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('random_int("1", 5);')

    def test_non_int_max_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('random_int(1, "5");')

    def test_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("random_int(1);")


class TestRandomChoice(unittest.TestCase):
    def test_result_is_member_of_list(self):
        for _ in range(50):
            result = run("let result = random_choice([1, 2, 3]);").get("result")
            self.assertIn(result, [1, 2, 3])

    def test_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("random_choice([]);")

    def test_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('random_choice("hi");')

    def test_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("random_choice([1], 2);")


class TestShuffle(unittest.TestCase):
    def test_shuffle_contains_same_elements(self):
        result = run("let result = shuffle([1, 2, 3]);").get("result")
        self.assertEqual(sorted(result), [1, 2, 3])

    def test_shuffle_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = shuffle(xs);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(sorted(env.get("result")), [1, 2, 3])

    def test_shuffle_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('shuffle("hi");')

    def test_shuffle_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("shuffle([1], 2);")


class TestSample(unittest.TestCase):
    def test_sample_returns_n_elements_from_source(self):
        result = run("let result = sample([1, 2, 3, 4], 2);").get("result")
        self.assertEqual(len(result), 2)
        for element in result:
            self.assertIn(element, [1, 2, 3, 4])

    def test_sample_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3, 4]; let result = sample(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])

    def test_sample_n_equal_to_length_is_full_shuffle(self):
        result = run("let result = sample([1, 2, 3], 3);").get("result")
        self.assertEqual(sorted(result), [1, 2, 3])

    def test_sample_n_zero_returns_empty_list(self):
        self.assertEqual(run("let result = sample([1, 2, 3], 0);").get("result"), [])

    def test_sample_n_greater_than_length_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sample([1, 2, 3], 4);")

    def test_sample_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sample([1, 2, 3], -1);")

    def test_sample_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sample([1, 2, 3], "2");')

    def test_sample_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sample("hi", 2);')

    def test_sample_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sample([1, 2, 3]);")


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


class TestSortBy(unittest.TestCase):
    def test_sort_by_identity_key_matches_plain_sort(self):
        env = run("let result = sort_by([3, 1, 2], fn(x) { return x; });")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_sort_by_string_length(self):
        env = run('let result = sort_by(["bb", "a", "ccc"], fn(x) { return len(x); });')
        self.assertEqual(env.get("result"), ["a", "bb", "ccc"])

    def test_sort_by_empty_list_never_calls_fn(self):
        env = run("let result = sort_by([], fn(x) { return x / 0; });")
        self.assertEqual(env.get("result"), [])

    def test_sort_by_is_stable(self):
        env = run(
            "let result = sort_by([[1, \"a\"], [1, \"b\"]], fn(x) { return x[0]; });"
        )
        self.assertEqual(env.get("result"), [[1, "a"], [1, "b"]])

    def test_sort_by_does_not_mutate_input(self):
        env = run("let xs = [3, 1, 2]; let result = sort_by(xs, fn(x) { return x; });")
        self.assertEqual(env.get("xs"), [3, 1, 2])
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_sort_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sort_by(5, fn(x) { return x; });")

    def test_sort_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sort_by([1, 2], 5);")

    def test_sort_by_mixed_type_keys_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sort_by([1, "a"], fn(x) { return x; });')

    def test_sort_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sort_by([1]);")


class TestMinByMaxBy(unittest.TestCase):
    def test_min_by_picks_smallest_key(self):
        env = run("let result = min_by([3, 1, 2], fn(n) { return n; });")
        self.assertEqual(env.get("result"), 1)

    def test_max_by_picks_largest_key(self):
        env = run("let result = max_by([3, 1, 2], fn(n) { return n; });")
        self.assertEqual(env.get("result"), 3)

    def test_min_by_string_length(self):
        env = run('let result = min_by(["ccc", "a", "bb"], fn(s) { return len(s); });')
        self.assertEqual(env.get("result"), "a")

    def test_min_by_tie_keeps_first_match(self):
        env = run(
            'let result = min_by([[1, "a"], [1, "b"]], fn(x) { return x[0]; });'
        )
        self.assertEqual(env.get("result"), [1, "a"])

    def test_max_by_tie_keeps_first_match(self):
        env = run(
            'let result = max_by([[1, "a"], [1, "b"]], fn(x) { return x[0]; });'
        )
        self.assertEqual(env.get("result"), [1, "a"])

    def test_min_by_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("min_by([], fn(n) { return n; });")

    def test_max_by_empty_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("max_by([], fn(n) { return n; });")

    def test_min_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("min_by(5, fn(n) { return n; });")

    def test_max_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("max_by(5, fn(n) { return n; });")

    def test_min_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("min_by([1, 2], 5);")

    def test_max_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("max_by([1, 2], 5);")

    def test_min_by_mixed_type_keys_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('min_by([1, "a"], fn(x) { return x; });')

    def test_max_by_mixed_type_keys_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('max_by([1, "a"], fn(x) { return x; });')

    def test_min_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("min_by([1]);")

    def test_max_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("max_by([1]);")


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


class TestRepeat(unittest.TestCase):
    def test_repeat_returns_n_copies(self):
        self.assertEqual(run('let result = repeat("x", 3);').get("result"), ["x", "x", "x"])

    def test_repeat_zero_returns_empty_list(self):
        self.assertEqual(run("let result = repeat(0, 0);").get("result"), [])

    def test_repeat_aliases_list_elements(self):
        env = run("let result = repeat([1], 2); push(result[0], 2);")
        self.assertEqual(env.get("result"), [[1, 2], [1, 2]])

    def test_repeat_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('repeat("x", -1);')

    def test_repeat_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('repeat("x", "3");')

    def test_repeat_bool_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('repeat("x", true);')

    def test_repeat_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('repeat("x");')
        with self.assertRaises(CinderRuntimeError):
            run('repeat("x", 1, 2);')


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


class TestMapValues(unittest.TestCase):
    def test_map_values_with_closure(self):
        env = run('let result = map_values({"a": 1, "b": 2}, fn(v) { return v * 10; });')
        self.assertEqual(env.get("result"), {"a": 10, "b": 20})

    def test_map_values_preserves_key_order(self):
        env = run('let result = map_values({"b": 1, "a": 2}, fn(v) { return v; });')
        self.assertEqual(list(env.get("result").keys()), ["b", "a"])

    def test_map_values_of_empty_map(self):
        env = run("let result = map_values({}, fn(v) { return v; });")
        self.assertEqual(env.get("result"), {})

    def test_map_values_does_not_mutate_input(self):
        env = run(
            'let m = {"a": 1}; let result = map_values(m, fn(v) { return v * 10; });'
        )
        self.assertEqual(env.get("m"), {"a": 1})
        self.assertEqual(env.get("result"), {"a": 10})

    def test_map_values_non_map_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("map_values(5, fn(v) { return v; });")

    def test_map_values_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_values({"a": 1}, 5);')

    def test_map_values_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_values({"a": 1});')

    def test_map_values_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_values({"a": 1}, fn(x, y) { return x; });')


class TestMapKeys(unittest.TestCase):
    def test_map_keys_with_closure(self):
        env = run('let result = map_keys({"a": 1, "b": 2}, fn(k) { return upper(k); });')
        self.assertEqual(env.get("result"), {"A": 1, "B": 2})

    def test_map_keys_collision_later_entry_wins(self):
        env = run('let result = map_keys({"cat": 1, "car": 2}, fn(k) { return k[0]; });')
        self.assertEqual(env.get("result"), {"c": 2})

    def test_map_keys_of_empty_map(self):
        env = run("let result = map_keys({}, fn(k) { return k; });")
        self.assertEqual(env.get("result"), {})

    def test_map_keys_does_not_mutate_input(self):
        env = run(
            'let m = {"a": 1}; let result = map_keys(m, fn(k) { return upper(k); });'
        )
        self.assertEqual(env.get("m"), {"a": 1})
        self.assertEqual(env.get("result"), {"A": 1})

    def test_map_keys_with_invalid_result_as_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_keys({"a": 1}, fn(k) { return [k]; });')

    def test_map_keys_non_map_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("map_keys(5, fn(k) { return k; });")

    def test_map_keys_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_keys({"a": 1}, 5);')

    def test_map_keys_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_keys({"a": 1});')

    def test_map_keys_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run('map_keys({"a": 1}, fn(x, y) { return x; });')


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


class TestReject(unittest.TestCase):
    def test_reject_with_closure(self):
        env = run(
            "let result = reject([1, 2, 3, 4], fn(n) { return n % 2 == 0; });"
        )
        self.assertEqual(env.get("result"), [1, 3])

    def test_reject_contrasts_with_filter(self):
        env = run(
            "let rejected = reject([1, 2, 3, 4], fn(n) { return n % 2 == 0; }); "
            "let filtered = filter([1, 2, 3, 4], fn(n) { return n % 2 == 0; });"
        )
        self.assertEqual(env.get("rejected"), [1, 3])
        self.assertEqual(env.get("filtered"), [2, 4])

    def test_reject_of_empty_list_never_calls_fn(self):
        env = run("let result = reject([], fn(n) { return true; });")
        self.assertEqual(env.get("result"), [])

    def test_reject_always_falsy_predicate_keeps_everything(self):
        env = run("let result = reject([1, 2, 3], fn(n) { return false; });")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_reject_always_truthy_predicate_keeps_nothing(self):
        env = run("let result = reject([1, 2, 3], fn(n) { return true; });")
        self.assertEqual(env.get("result"), [])

    def test_reject_only_removes_predicate_truthy_elements(self):
        env = run(
            "let result = reject([0, 1, nil, 2, false], fn(n) { return n == 1; });"
        )
        self.assertEqual(env.get("result"), [0, None, 2, False])

    def test_reject_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3, 4]; "
            "let result = reject(xs, fn(n) { return n % 2 == 0; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [1, 3])

    def test_reject_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reject(5, fn(n) { return true; });")

    def test_reject_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reject([1, 2], 5);")

    def test_reject_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("reject([1, 2]);")

    def test_reject_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("reject([1], fn(x, y) { return x; });")


class TestCompact(unittest.TestCase):
    def test_compact_drops_nil_and_false(self):
        result = run("let result = compact([1, nil, 2, false, 3]);").get("result")
        self.assertEqual(result, [1, 2, 3])

    def test_compact_keeps_python_falsy_but_cinder_truthy_values(self):
        result = run('let result = compact([0, 0.0, "", nil, false, 1]);').get(
            "result"
        )
        self.assertEqual(result, [0, 0.0, "", 1])

    def test_compact_of_empty_list(self):
        result = run("let result = compact([]);").get("result")
        self.assertEqual(result, [])

    def test_compact_with_nothing_falsy_returns_equal_new_list(self):
        env = run("let xs = [1, 2, 3]; let result = compact(xs);")
        self.assertEqual(env.get("result"), [1, 2, 3])
        self.assertIsNot(env.get("result"), env.get("xs"))

    def test_compact_non_list_argument_raises_naming_compact_and_type(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('compact("abc");')
        self.assertIn("compact", str(ctx.exception))
        self.assertIn("string", str(ctx.exception))

    def test_compact_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("compact();")
        with self.assertRaises(CinderRuntimeError):
            run("compact([1], [2]);")


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


class TestPipe(unittest.TestCase):
    def test_pipe_applies_left_to_right(self):
        env = run(
            "let result = pipe(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5);"
        )
        self.assertEqual(env.get("result"), 12)

    def test_pipe_of_zero_functions_is_identity(self):
        env = run("let result = pipe()(5);")
        self.assertEqual(env.get("result"), 5)

    def test_pipe_of_single_function_is_passthrough(self):
        env = run("let result = pipe(fn(x) { return x; })(5);")
        self.assertEqual(env.get("result"), 5)

    def test_pipe_of_three_functions(self):
        env = run(
            "let result = pipe("
            "fn(x) { return x + 1; }, "
            "fn(x) { return x * 2; }, "
            "fn(x) { return x - 3; }"
            ")(5);"
        )
        self.assertEqual(env.get("result"), 9)

    def test_pipe_result_is_first_class_function_value(self):
        env = run(
            "let piped = pipe(fn(x) { return x + 1; }); "
            "let result_type = type(piped); "
            "let mapped = map([1, 2, 3], piped);"
        )
        self.assertEqual(env.get("result_type"), "function")
        self.assertEqual(env.get("mapped"), [2, 3, 4])

    def test_pipe_non_function_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pipe(1, fn(x) { return x; });")

    def test_pipe_result_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("pipe(fn(x) { return x; })();")
        with self.assertRaises(CinderRuntimeError):
            run("pipe(fn(x) { return x; })(1, 2);")


class TestCompose(unittest.TestCase):
    def test_compose_applies_right_to_left(self):
        env = run(
            "let result = compose(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5);"
        )
        self.assertEqual(env.get("result"), 11)

    def test_compose_differs_from_pipe_on_same_functions(self):
        env = run(
            "let piped = pipe(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5); "
            "let composed = compose(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5);"
        )
        self.assertNotEqual(env.get("piped"), env.get("composed"))

    def test_compose_of_zero_functions_is_identity(self):
        env = run("let result = compose()(5);")
        self.assertEqual(env.get("result"), 5)

    def test_compose_of_three_functions(self):
        env = run(
            "let result = compose("
            "fn(x) { return x + 1; }, "
            "fn(x) { return x * 2; }, "
            "fn(x) { return x - 3; }"
            ")(5);"
        )
        self.assertEqual(env.get("result"), 5)

    def test_compose_result_is_first_class_function_value(self):
        env = run(
            "let composed = compose(fn(x) { return x + 1; }); "
            "let result_type = type(composed);"
        )
        self.assertEqual(env.get("result_type"), "function")

    def test_compose_non_function_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("compose(1, fn(x) { return x; });")

    def test_compose_result_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("compose(fn(x) { return x; })();")
        with self.assertRaises(CinderRuntimeError):
            run("compose(fn(x) { return x; })(1, 2);")


class TestCurry(unittest.TestCase):
    def test_curry_two_step(self):
        env = run(
            "let result = curry(fn(a, b) { return a + b; }, 2)(1)(2);"
        )
        self.assertEqual(env.get("result"), 3)

    def test_curry_three_step(self):
        env = run(
            "let result = curry(fn(a, b, c) { return a + b + c; }, 3)(1)(2)(3);"
        )
        self.assertEqual(env.get("result"), 6)

    def test_curry_partial_application_is_reusable(self):
        env = run(
            "let add5 = curry(fn(a, b) { return a + b; }, 2)(5); "
            "let r1 = add5(1); "
            "let r2 = add5(10);"
        )
        self.assertEqual(env.get("r1"), 6)
        self.assertEqual(env.get("r2"), 15)

    def test_curry_step_is_independent_across_calls(self):
        env = run(
            "let step1 = curry(fn(a, b, c) { return a + b + c; }, 3)(1); "
            "let r1 = step1(2)(3); "
            "let r2 = step1(3)(3);"
        )
        self.assertEqual(env.get("r1"), 6)
        self.assertEqual(env.get("r2"), 7)

    def test_curry_result_is_first_class_function_value(self):
        env = run(
            "let step = curry(fn(a, b) { return a + b; }, 2)(1); "
            "let result_type = type(step); "
            "let mapped = map([1, 2, 3], curry(fn(a, b) { return a + b; }, 2)(10));"
        )
        self.assertEqual(env.get("result_type"), "function")
        self.assertEqual(env.get("mapped"), [11, 12, 13])

    def test_curry_non_function_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("curry(1, 2);")

    def test_curry_arity_below_one_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a) { return a; }, 0);")
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a) { return a; }, -1);")

    def test_curry_non_int_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('curry(fn(a) { return a; }, "2");')

    def test_curry_step_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a, b) { return a + b; }, 2)();")
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a, b) { return a + b; }, 2)(1, 2);")
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a, b) { return a + b; }, 2)(1)();")
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a, b) { return a + b; }, 2)(1)(2, 3);")

    def test_curry_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("curry(fn(a) { return a; });")


class TestMemoize(unittest.TestCase):
    def test_memoize_caches_repeated_single_argument_calls(self):
        env = run(
            "let calls = 0; "
            "fn f(x) { calls = calls + 1; return x * 2; } "
            "let memoized = memoize(f); "
            "memoized(5); memoized(5); memoized(3);"
        )
        self.assertEqual(env.get("calls"), 2)

    def test_memoize_caches_by_full_argument_list(self):
        env = run(
            "let calls = 0; "
            "fn f(a, b) { calls = calls + 1; return a + b; } "
            "let memoized = memoize(f); "
            "memoized(1, 2); memoized(1, 2); memoized(2, 1);"
        )
        self.assertEqual(env.get("calls"), 2)

    def test_memoize_calls_do_not_share_cache(self):
        env = run(
            "let calls = 0; "
            "fn f(x) { calls = calls + 1; return x; } "
            "let m1 = memoize(f); let m2 = memoize(f); "
            "m1(1); m2(1);"
        )
        self.assertEqual(env.get("calls"), 2)

    def test_memoize_distinguishes_number_and_bool_keys(self):
        env = run(
            "let calls = 0; "
            "fn f(x) { calls = calls + 1; return x; } "
            "let memoized = memoize(f); "
            "memoized(1); memoized(true);"
        )
        self.assertEqual(env.get("calls"), 2)

    def test_memoize_result_is_first_class_function_value(self):
        env = run(
            "let memoized = memoize(fn(x) { return x; }); "
            "let result_type = type(memoized); "
            "let mapped = map([1, 2, 3], memoize(fn(x) { return x * 2; }));"
        )
        self.assertEqual(env.get("result_type"), "function")
        self.assertEqual(env.get("mapped"), [2, 4, 6])

    def test_memoize_non_function_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("memoize(1);")

    def test_memoize_list_argument_raises_at_call_site(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("let memoized = memoize(fn(x) { return x; }); memoized([1, 2]);")
        self.assertIn("list", str(ctx.exception))

    def test_memoize_map_argument_raises_at_call_site(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('let memoized = memoize(fn(m) { return m; }); memoized({"a": 1});')
        self.assertIn("map", str(ctx.exception))

    def test_memoize_arity_mismatch_on_wrapped_function_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run(
                "let memoized = memoize(fn(a, b) { return a + b; }); "
                "memoized(1);"
            )

    def test_memoize_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("memoize();")
        with self.assertRaises(CinderRuntimeError):
            run("memoize(fn(x) { return x; }, fn(y) { return y; });")


class TestGroupBy(unittest.TestCase):
    def test_group_by_parity(self):
        env = run(
            "let result = group_by([1, 2, 3, 4, 5, 6], fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("result"), {1: [1, 3, 5], 0: [2, 4, 6]})

    def test_group_by_empty_list_never_calls_fn(self):
        env = run("let result = group_by([], fn(n) { return n / 0; });")
        self.assertEqual(env.get("result"), {})

    def test_group_by_string_first_letter(self):
        env = run(
            'let result = group_by(["apple", "avocado", "banana"], '
            "fn(s) { return s[0]; });"
        )
        self.assertEqual(
            env.get("result"), {"a": ["apple", "avocado"], "b": ["banana"]}
        )

    def test_group_by_preserves_element_order_within_group(self):
        env = run(
            "let result = group_by([3, 1, 4, 1, 5], fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("result"), {1: [3, 1, 1, 5], 0: [4]})

    def test_group_by_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = group_by(xs, fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_group_by_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_by([1, 2], fn(n) { return [n]; });")

    def test_group_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_by(5, fn(n) { return n; });")

    def test_group_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_by([1, 2], 5);")

    def test_group_by_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_by([1], fn(x, y) { return x; });")

    def test_group_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_by([1]);")


class TestKeyBy(unittest.TestCase):
    def test_key_by_indexes_maps_by_computed_key(self):
        env = run(
            'let result = key_by([{"id": 1, "n": "a"}, {"id": 2, "n": "b"}], '
            'fn(x) { return x["id"]; });'
        )
        self.assertEqual(
            env.get("result"),
            {1: {"id": 1, "n": "a"}, 2: {"id": 2, "n": "b"}},
        )

    def test_key_by_duplicate_keys_later_item_wins(self):
        env = run(
            'let result = key_by([{"id": 1, "n": "a"}, {"id": 1, "n": "b"}], '
            'fn(x) { return x["id"]; });'
        )
        self.assertEqual(env.get("result"), {1: {"id": 1, "n": "b"}})

    def test_key_by_empty_list(self):
        env = run("let result = key_by([], fn(x) { return x; });")
        self.assertEqual(env.get("result"), {})

    def test_key_by_does_not_mutate_input(self):
        env = run(
            'let xs = [{"id": 1}]; '
            'let result = key_by(xs, fn(x) { return x["id"]; });'
        )
        self.assertEqual(env.get("xs"), [{"id": 1}])

    def test_key_by_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("key_by([1, 2], fn(n) { return [n]; });")

    def test_key_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("key_by(5, fn(n) { return n; });")

    def test_key_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("key_by([1, 2], 5);")

    def test_key_by_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("key_by([1], fn(x, y) { return x; });")

    def test_key_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("key_by([1]);")


class TestCountBy(unittest.TestCase):
    def test_count_by_parity(self):
        env = run(
            "let result = count_by([1, 2, 3, 4], fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("result"), {1: 2, 0: 2})

    def test_count_by_string_length(self):
        env = run(
            'let result = count_by(["a", "bb", "cc", "d"], '
            "fn(s) { return len(s); });"
        )
        self.assertEqual(env.get("result"), {1: 2, 2: 2})

    def test_count_by_empty_list_never_calls_fn(self):
        env = run("let result = count_by([], fn(n) { return n / 0; });")
        self.assertEqual(env.get("result"), {})

    def test_count_by_key_order_matches_first_occurrence(self):
        env = run(
            "let result = count_by([3, 1, 4, 1, 5], fn(n) { return n % 2; });"
        )
        self.assertEqual(list(env.get("result").keys()), [1, 0])

    def test_count_by_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = count_by(xs, fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_count_by_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("count_by([1, 2], fn(n) { return [n]; });")

    def test_count_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("count_by(5, fn(n) { return n; });")

    def test_count_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("count_by([1], 5);")

    def test_count_by_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("count_by([1], fn(x, y) { return x; });")

    def test_count_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("count_by([1]);")


class TestFrequencies(unittest.TestCase):
    def test_frequencies_basic(self):
        env = run("let result = frequencies([1, 2, 2, 3, 3, 3]);")
        self.assertEqual(env.get("result"), {1: 1, 2: 2, 3: 3})

    def test_frequencies_strings(self):
        env = run('let result = frequencies(["a", "b", "a"]);')
        self.assertEqual(env.get("result"), {"a": 2, "b": 1})

    def test_frequencies_empty_list(self):
        env = run("let result = frequencies([]);")
        self.assertEqual(env.get("result"), {})

    def test_frequencies_key_order_matches_first_occurrence(self):
        env = run("let result = keys(frequencies([3, 1, 3, 2]));")
        self.assertEqual(env.get("result"), [3, 1, 2])

    def test_frequencies_bools(self):
        env = run("let result = frequencies([true, false, true]);")
        self.assertEqual(env.get("result"), {True: 2, False: 1})

    def test_frequencies_unhashable_element_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("frequencies([[1, 2], [1, 2]]);")

    def test_frequencies_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('frequencies("abc");')

    def test_frequencies_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("frequencies([1], [2]);")


class TestDistinctBy(unittest.TestCase):
    def test_distinct_by_parity_keeps_first_of_each_key(self):
        env = run(
            "let result = distinct_by([1, 2, 3, 4], fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("result"), [1, 2])

    def test_distinct_by_string_length(self):
        env = run(
            'let result = distinct_by(["a", "bb", "c", "dd"], '
            "fn(s) { return len(s); });"
        )
        self.assertEqual(env.get("result"), ["a", "bb"])

    def test_distinct_by_empty_list_never_calls_fn(self):
        env = run("let result = distinct_by([], fn(n) { return n / 0; });")
        self.assertEqual(env.get("result"), [])

    def test_distinct_by_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = distinct_by(xs, fn(n) { return n % 2; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_distinct_by_unhashable_key_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("distinct_by([1, 2], fn(n) { return [n]; });")

    def test_distinct_by_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("distinct_by(5, fn(n) { return n; });")

    def test_distinct_by_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("distinct_by([1], 5);")

    def test_distinct_by_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("distinct_by([1], fn(x, y) { return x; });")

    def test_distinct_by_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("distinct_by([1]);")


class TestPartition(unittest.TestCase):
    def test_partition_splits_matching_and_non_matching(self):
        env = run(
            "let result = partition([1, 2, 3, 4, 5, 6], "
            "fn(n) { return n % 2 == 0; });"
        )
        self.assertEqual(env.get("result"), [[2, 4, 6], [1, 3, 5]])

    def test_partition_of_empty_list_never_calls_fn(self):
        env = run("let result = partition([], fn(n) { return n / 0; });")
        self.assertEqual(env.get("result"), [[], []])

    def test_partition_all_matching(self):
        env = run("let result = partition([1, 2, 3], fn(n) { return true; });")
        self.assertEqual(env.get("result"), [[1, 2, 3], []])

    def test_partition_none_matching(self):
        env = run("let result = partition([1, 2, 3], fn(n) { return false; });")
        self.assertEqual(env.get("result"), [[], [1, 2, 3]])

    def test_partition_uses_cinder_truthiness(self):
        env = run(
            'let result = partition([0, "", 1, "a"], fn(x) { return x; });'
        )
        self.assertEqual(env.get("result"), [[0, "", 1, "a"], []])

    def test_partition_preserves_relative_order(self):
        env = run(
            "let result = partition([3, 1, 4, 1, 5], fn(n) { return n % 2 == 1; });"
        )
        self.assertEqual(env.get("result"), [[3, 1, 1, 5], [4]])

    def test_partition_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = partition(xs, fn(n) { return n % 2 == 0; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])

    def test_partition_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("partition(5, fn(n) { return n; });")

    def test_partition_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("partition([1, 2], 5);")

    def test_partition_propagates_callback_arity_error(self):
        with self.assertRaises(CinderRuntimeError):
            run("partition([1], fn(x, y) { return x; });")

    def test_partition_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("partition([1]);")


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


class TestSplitAt(unittest.TestCase):
    def test_split_at_basic(self):
        env = run("let result = split_at([1, 2, 3, 4, 5], 2);")
        self.assertEqual(env.get("result"), [[1, 2], [3, 4, 5]])

    def test_split_at_zero(self):
        env = run("let result = split_at([1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [[], [1, 2, 3]])

    def test_split_at_full_length(self):
        env = run("let result = split_at([1, 2, 3], 3);")
        self.assertEqual(env.get("result"), [[1, 2, 3], []])

    def test_split_at_negative_index(self):
        env = run("let result = split_at([1, 2, 3], -1);")
        self.assertEqual(env.get("result"), [[1, 2], [3]])

    def test_split_at_index_exceeds_length_clamps(self):
        env = run("let result = split_at([1, 2, 3], 10);")
        self.assertEqual(env.get("result"), [[1, 2, 3], []])

    def test_split_at_negative_index_exceeds_length_clamps(self):
        env = run("let result = split_at([1, 2, 3], -10);")
        self.assertEqual(env.get("result"), [[], [1, 2, 3]])

    def test_split_at_empty_list(self):
        env = run("let result = split_at([], 0);")
        self.assertEqual(env.get("result"), [[], []])

    def test_split_at_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3, 4]; let result = split_at(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [[1, 2], [3, 4]])

    def test_split_at_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("split_at(5, 1);")

    def test_split_at_non_int_index_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('split_at([1, 2], "1");')

    def test_split_at_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("split_at([1, 2]);")


class TestTake(unittest.TestCase):
    def test_take_basic(self):
        env = run("let result = take([1, 2, 3, 4], 2);")
        self.assertEqual(env.get("result"), [1, 2])

    def test_take_n_exceeds_length_clamps(self):
        env = run("let result = take([1, 2], 10);")
        self.assertEqual(env.get("result"), [1, 2])

    def test_take_zero(self):
        env = run("let result = take([1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [])

    def test_take_empty_list(self):
        env = run("let result = take([], 3);")
        self.assertEqual(env.get("result"), [])

    def test_take_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3, 4]; let result = take(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [1, 2])

    def test_take_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take([1, 2], -1);")

    def test_take_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take(5, 1);")

    def test_take_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('take([1, 2], "1");')

    def test_take_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take([1, 2]);")


class TestDrop(unittest.TestCase):
    def test_drop_basic(self):
        env = run("let result = drop([1, 2, 3, 4], 2);")
        self.assertEqual(env.get("result"), [3, 4])

    def test_drop_n_exceeds_length_clamps(self):
        env = run("let result = drop([1, 2], 10);")
        self.assertEqual(env.get("result"), [])

    def test_drop_zero(self):
        env = run("let result = drop([1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_drop_empty_list(self):
        env = run("let result = drop([], 3);")
        self.assertEqual(env.get("result"), [])

    def test_drop_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3, 4]; let result = drop(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3, 4])
        self.assertEqual(env.get("result"), [3, 4])

    def test_drop_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop([1, 2], -1);")

    def test_drop_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop(5, 1);")

    def test_drop_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('drop([1, 2], "1");')

    def test_drop_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop([1, 2]);")


class TestTakeRight(unittest.TestCase):
    def test_take_right_basic(self):
        env = run("let result = take_right([1, 2, 3, 4, 5], 2);")
        self.assertEqual(env.get("result"), [4, 5])

    def test_take_right_n_exceeds_length_clamps(self):
        env = run("let result = take_right([1, 2, 3], 10);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_take_right_zero(self):
        env = run("let result = take_right([1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [])

    def test_take_right_empty_list(self):
        env = run("let result = take_right([], 3);")
        self.assertEqual(env.get("result"), [])

    def test_take_right_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; take_right(xs, 1); let result = xs;")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_take_right_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take_right([1, 2, 3], -1);")

    def test_take_right_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('take_right("abc", 2);')

    def test_take_right_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('take_right([1, 2], "1");')

    def test_take_right_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take_right([1, 2]);")


class TestDropRight(unittest.TestCase):
    def test_drop_right_basic(self):
        env = run("let result = drop_right([1, 2, 3, 4, 5], 2);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_drop_right_n_exceeds_length_clamps(self):
        env = run("let result = drop_right([1, 2, 3], 10);")
        self.assertEqual(env.get("result"), [])

    def test_drop_right_zero(self):
        env = run("let result = drop_right([1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_drop_right_empty_list(self):
        env = run("let result = drop_right([], 3);")
        self.assertEqual(env.get("result"), [])

    def test_drop_right_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; drop_right(xs, 1); let result = xs;")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_drop_right_negative_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop_right([1, 2, 3], -1);")

    def test_drop_right_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('drop_right("abc", 2);')

    def test_drop_right_non_int_n_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('drop_right([1, 2], "1");')

    def test_drop_right_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop_right([1, 2]);")


class TestTakeWhile(unittest.TestCase):
    def test_take_while_stops_at_first_falsy(self):
        env = run(
            "let result = take_while([1, 2, 3, 4, 1], fn(n) { return n < 3; });"
        )
        self.assertEqual(env.get("result"), [1, 2])

    def test_take_while_none_matching_returns_empty(self):
        env = run("let result = take_while([1, 2], fn(n) { return n > 10; });")
        self.assertEqual(env.get("result"), [])

    def test_take_while_all_matching_returns_copy(self):
        env = run("let result = take_while([1, 2, 3], fn(n) { return n > 0; });")
        self.assertEqual(env.get("result"), [1, 2, 3])

    def test_take_while_empty_list(self):
        env = run("let result = take_while([], fn(n) { return n; });")
        self.assertEqual(env.get("result"), [])

    def test_take_while_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = take_while(xs, fn(n) { return n < 3; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [1, 2])

    def test_take_while_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take_while(5, fn(n) { return n; });")

    def test_take_while_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take_while([1], 5);")

    def test_take_while_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("take_while([1]);")


class TestDropWhile(unittest.TestCase):
    def test_drop_while_keeps_from_first_falsy(self):
        env = run(
            "let result = drop_while([1, 2, 3, 4, 1], fn(n) { return n < 3; });"
        )
        self.assertEqual(env.get("result"), [3, 4, 1])

    def test_drop_while_none_matching_returns_full_list(self):
        env = run("let result = drop_while([1, 2], fn(n) { return n > 10; });")
        self.assertEqual(env.get("result"), [1, 2])

    def test_drop_while_all_matching_returns_empty(self):
        env = run("let result = drop_while([1, 2, 3], fn(n) { return n > 0; });")
        self.assertEqual(env.get("result"), [])

    def test_drop_while_empty_list(self):
        env = run("let result = drop_while([], fn(n) { return n; });")
        self.assertEqual(env.get("result"), [])

    def test_drop_while_does_not_mutate_input(self):
        env = run(
            "let xs = [1, 2, 3]; "
            "let result = drop_while(xs, fn(n) { return n < 3; });"
        )
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [3])

    def test_drop_while_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop_while(5, fn(n) { return n; });")

    def test_drop_while_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop_while([1], 5);")

    def test_drop_while_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("drop_while([1]);")


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


class TestChunk(unittest.TestCase):
    def test_chunk_uneven_remainder_gets_shorter_sublist(self):
        env = run("let result = chunk([1, 2, 3, 4, 5], 2);")
        self.assertEqual(env.get("result"), [[1, 2], [3, 4], [5]])

    def test_chunk_evenly_divides(self):
        env = run("let result = chunk([1, 2, 3, 4], 2);")
        self.assertEqual(env.get("result"), [[1, 2], [3, 4]])

    def test_chunk_size_one(self):
        env = run("let result = chunk([1, 2, 3], 1);")
        self.assertEqual(env.get("result"), [[1], [2], [3]])

    def test_chunk_empty_list(self):
        env = run("let result = chunk([], 3);")
        self.assertEqual(env.get("result"), [])

    def test_chunk_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = chunk(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [[1, 2], [3]])

    def test_chunk_zero_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chunk([1, 2, 3], 0);")

    def test_chunk_negative_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chunk([1, 2, 3], -1);")

    def test_chunk_zero_size_raises_even_for_empty_list(self):
        with self.assertRaises(CinderRuntimeError):
            run("chunk([], 0);")

    def test_chunk_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chunk(5, 2);")

    def test_chunk_non_int_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('chunk([1, 2, 3], "2");')

    def test_chunk_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("chunk([1, 2, 3]);")
        with self.assertRaises(CinderRuntimeError):
            run("chunk([1, 2, 3], 2, 3);")


class TestSlidingWindow(unittest.TestCase):
    def test_sliding_window_size_two(self):
        env = run("let result = sliding_window([1, 2, 3, 4], 2);")
        self.assertEqual(env.get("result"), [[1, 2], [2, 3], [3, 4]])

    def test_sliding_window_size_three(self):
        env = run("let result = sliding_window([1, 2, 3, 4], 3);")
        self.assertEqual(env.get("result"), [[1, 2, 3], [2, 3, 4]])

    def test_sliding_window_size_one(self):
        env = run("let result = sliding_window([1, 2, 3], 1);")
        self.assertEqual(env.get("result"), [[1], [2], [3]])

    def test_sliding_window_size_larger_than_list_returns_empty(self):
        env = run("let result = sliding_window([1, 2], 5);")
        self.assertEqual(env.get("result"), [])

    def test_sliding_window_empty_list(self):
        env = run("let result = sliding_window([], 1);")
        self.assertEqual(env.get("result"), [])

    def test_sliding_window_does_not_mutate_input(self):
        env = run("let xs = [1, 2, 3]; let result = sliding_window(xs, 2);")
        self.assertEqual(env.get("xs"), [1, 2, 3])
        self.assertEqual(env.get("result"), [[1, 2], [2, 3]])

    def test_sliding_window_zero_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window([1, 2, 3], 0);")

    def test_sliding_window_negative_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window([1, 2, 3], -1);")

    def test_sliding_window_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window(5, 2);")

    def test_sliding_window_non_int_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('sliding_window([1, 2, 3], "2");')

    def test_sliding_window_bool_size_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window([1, 2, 3], true);")

    def test_sliding_window_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window([1, 2, 3]);")
        with self.assertRaises(CinderRuntimeError):
            run("sliding_window([1, 2, 3], 2, 3);")


class TestGroupConsecutive(unittest.TestCase):
    def test_group_consecutive_trailing_singleton_stays_separate(self):
        env = run("let result = group_consecutive([1, 1, 2, 2, 2, 1]);")
        self.assertEqual(env.get("result"), [[1, 1], [2, 2, 2], [1]])

    def test_group_consecutive_no_adjacent_duplicates(self):
        env = run("let result = group_consecutive([1, 2, 3]);")
        self.assertEqual(env.get("result"), [[1], [2], [3]])

    def test_group_consecutive_empty_list(self):
        env = run("let result = group_consecutive([]);")
        self.assertEqual(env.get("result"), [])

    def test_group_consecutive_single_run_covers_whole_list(self):
        env = run('let result = group_consecutive(["a", "a", "a"]);')
        self.assertEqual(env.get("result"), [["a", "a", "a"]])

    def test_group_consecutive_structural_equality_for_list_elements(self):
        env = run("let result = group_consecutive([[1, 2], [1, 2], [3]]);")
        self.assertEqual(env.get("result"), [[[1, 2], [1, 2]], [[3]]])

    def test_group_consecutive_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_consecutive(5);")

    def test_group_consecutive_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("group_consecutive();")
        with self.assertRaises(CinderRuntimeError):
            run("group_consecutive([1, 2], 3);")


class TestFlatten(unittest.TestCase):
    def test_flatten_one_level_of_nesting(self):
        env = run("let result = flatten([[1, 2], [3, 4]]);")
        self.assertEqual(env.get("result"), [1, 2, 3, 4])

    def test_flatten_only_goes_one_level_deep(self):
        env = run("let result = flatten([[1], [2, [3, 4]]]);")
        self.assertEqual(env.get("result"), [1, 2, [3, 4]])

    def test_flatten_passes_through_non_list_elements(self):
        env = run("let result = flatten([1, [2, 3], 4]);")
        self.assertEqual(env.get("result"), [1, 2, 3, 4])

    def test_flatten_of_empty_lists(self):
        self.assertEqual(run("let result = flatten([]);").get("result"), [])
        self.assertEqual(run("let result = flatten([[], []]);").get("result"), [])

    def test_flatten_with_no_nesting_returns_new_list(self):
        env = run("let a = [1, 2, 3]; let result = flatten(a);")
        self.assertEqual(env.get("result"), [1, 2, 3])
        self.assertIsNot(env.get("result"), env.get("a"))

    def test_flatten_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("flatten(5);")

    def test_flatten_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("flatten();")
        with self.assertRaises(CinderRuntimeError):
            run("flatten([1], [2]);")


class TestFlattenDeep(unittest.TestCase):
    def test_flatten_deep_flattens_multiple_levels(self):
        env = run("let result = flatten_deep([1, [2, 3], [4, [5, 6]]]);")
        self.assertEqual(env.get("result"), [1, 2, 3, 4, 5, 6])

    def test_flatten_deep_flattens_arbitrary_depth(self):
        env = run("let result = flatten_deep([[[1]], [[2]]]);")
        self.assertEqual(env.get("result"), [1, 2])

    def test_flatten_deep_with_no_nesting_returns_new_list(self):
        env = run("let a = [1, 2, 3]; let result = flatten_deep(a);")
        self.assertEqual(env.get("result"), [1, 2, 3])
        self.assertIsNot(env.get("result"), env.get("a"))

    def test_flatten_deep_empty_nested_lists_contribute_nothing(self):
        env = run("let result = flatten_deep([[], 1, []]);")
        self.assertEqual(env.get("result"), [1])

    def test_flatten_deep_of_empty_list(self):
        self.assertEqual(run("let result = flatten_deep([]);").get("result"), [])

    def test_flatten_deep_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("flatten_deep(5);")

    def test_flatten_deep_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("flatten_deep();")
        with self.assertRaises(CinderRuntimeError):
            run("flatten_deep([1], [2]);")


class TestFlatMap(unittest.TestCase):
    def test_flat_map_splices_list_results(self):
        env = run("let result = flat_map([1, 2, 3], fn(n) { return [n, n]; });")
        self.assertEqual(env.get("result"), [1, 1, 2, 2, 3, 3])

    def test_flat_map_passes_through_non_list_results(self):
        env = run("let result = flat_map([1, 2, 3], fn(n) { return n * 2; });")
        self.assertEqual(env.get("result"), [2, 4, 6])

    def test_flat_map_of_empty_list_never_calls_fn(self):
        env = run(
            "let calls = 0;"
            "let counter = fn(n) { calls = calls + 1; return n; };"
            "let result = flat_map([], counter);"
        )
        self.assertEqual(env.get("result"), [])
        self.assertEqual(env.get("calls"), 0)

    def test_flat_map_only_flattens_one_level(self):
        env = run("let result = flat_map([[1, 2]], fn(x) { return x; });")
        self.assertEqual(env.get("result"), [1, 2])

    def test_flat_map_does_not_mutate_input(self):
        env = run("let xs = [1, 2]; let result = flat_map(xs, fn(x) { return [x]; });")
        self.assertEqual(env.get("xs"), [1, 2])
        self.assertEqual(env.get("result"), [1, 2])

    def test_flat_map_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("flat_map(5, fn(n) { return n; });")
        self.assertEqual(ctx.exception.line, 1)

    def test_flat_map_non_callable_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("flat_map([1, 2], 5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_flat_map_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("flat_map([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("flat_map([1], fn(x) { return x; }, 2);")


class TestZip(unittest.TestCase):
    def test_zip_pairs_elements(self):
        env = run('let result = zip([1, 2, 3], ["a", "b", "c"]);')
        self.assertEqual(env.get("result"), [[1, "a"], [2, "b"], [3, "c"]])

    def test_zip_truncates_to_shorter_list(self):
        env = run("let result = zip([1, 2], [1]);")
        self.assertEqual(env.get("result"), [[1, 1]])

    def test_zip_with_empty_list(self):
        env = run("let result = zip([], [1, 2]);")
        self.assertEqual(env.get("result"), [])

    def test_zip_does_not_mutate_inputs(self):
        env = run("let a = [1, 2]; let b = [3, 4]; let result = zip(a, b);")
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("b"), [3, 4])
        self.assertEqual(env.get("result"), [[1, 3], [2, 4]])

    def test_zip_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("zip(5, [1]);")
        self.assertEqual(ctx.exception.line, 1)
        with self.assertRaises(CinderRuntimeError):
            run("zip([1], 5);")


class TestZipLongest(unittest.TestCase):
    def test_zip_longest_pads_shorter_second_list(self):
        env = run('let result = zip_longest([1, 2, 3], ["a", "b"], nil);')
        self.assertEqual(env.get("result"), [[1, "a"], [2, "b"], [3, None]])

    def test_zip_longest_pads_shorter_first_list(self):
        env = run("let result = zip_longest([1], [1, 2, 3], 0);")
        self.assertEqual(env.get("result"), [[1, 1], [0, 2], [0, 3]])

    def test_zip_longest_equal_length_lists_ignore_fill(self):
        env = run('let result = zip_longest([1, 2], [1, 2], "x");')
        self.assertEqual(env.get("result"), [[1, 1], [2, 2]])

    def test_zip_longest_both_empty(self):
        env = run("let result = zip_longest([], [], 0);")
        self.assertEqual(env.get("result"), [])

    def test_zip_longest_first_empty(self):
        env = run("let result = zip_longest([], [1, 2], 0);")
        self.assertEqual(env.get("result"), [[0, 1], [0, 2]])

    def test_zip_longest_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("zip_longest(5, [1], 0);")
        self.assertEqual(ctx.exception.line, 1)
        with self.assertRaises(CinderRuntimeError):
            run("zip_longest([1], 5, 0);")

    def test_zip_longest_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_longest([1], [2]);")
        with self.assertRaises(CinderRuntimeError):
            run("zip_longest([1], [2], 0, 0);")


class TestUnzip(unittest.TestCase):
    def test_unzip_splits_pairs(self):
        env = run(
            'let result = unzip([[1, "a"], [2, "b"], [3, "c"]]);'
        )
        self.assertEqual(env.get("result"), [[1, 2, 3], ["a", "b", "c"]])

    def test_unzip_empty_list(self):
        env = run("let result = unzip([]);")
        self.assertEqual(env.get("result"), [[], []])

    def test_unzip_single_pair(self):
        env = run("let result = unzip([[1, 2]]);")
        self.assertEqual(env.get("result"), [[1], [2]])

    def test_unzip_round_trips_with_zip(self):
        env = run(
            'let pairs = [[1, "a"], [2, "b"], [3, "c"]];'
            "let u = unzip(pairs);"
            "let result = zip(u[0], u[1]);"
        )
        self.assertEqual(
            env.get("result"), [[1, "a"], [2, "b"], [3, "c"]]
        )

    def test_unzip_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("unzip(5);")
        self.assertEqual(ctx.exception.line, 1)

    def test_unzip_element_not_a_list_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("unzip([1, 2]);")

    def test_unzip_element_wrong_length_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("unzip([[1]]);")
        with self.assertRaises(CinderRuntimeError):
            run("unzip([[1, 2, 3]]);")
        with self.assertRaises(CinderRuntimeError):
            run("unzip([[]]);")

    def test_unzip_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("unzip();")
        with self.assertRaises(CinderRuntimeError):
            run("unzip([[1, 2]], [[3, 4]]);")


class TestZipWith(unittest.TestCase):
    def test_zip_with_combines_elementwise(self):
        env = run(
            "let result = zip_with([1, 2, 3], [10, 20, 30], fn(a, b) { return a + b; });"
        )
        self.assertEqual(env.get("result"), [11, 22, 33])

    def test_zip_with_truncates_to_shorter_list(self):
        env = run(
            "let result = zip_with([1, 2], [1, 2, 3], fn(a, b) { return a + b; });"
        )
        self.assertEqual(env.get("result"), [2, 4])

    def test_zip_with_of_empty_list(self):
        env = run("let result = zip_with([], [1, 2], fn(a, b) { return a + b; });")
        self.assertEqual(env.get("result"), [])

    def test_zip_with_does_not_mutate_inputs(self):
        env = run(
            "let a = [1, 2]; let b = [3, 4];"
            "let result = zip_with(a, b, fn(x, y) { return x + y; });"
        )
        self.assertEqual(env.get("a"), [1, 2])
        self.assertEqual(env.get("b"), [3, 4])
        self.assertEqual(env.get("result"), [4, 6])

    def test_zip_with_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("zip_with(5, [1], fn(a, b) { return a; });")
        self.assertEqual(ctx.exception.line, 1)

    def test_zip_with_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_with([1], 5, fn(a, b) { return a; });")

    def test_zip_with_non_callable_third_argument_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_with([1], [2], 5);")

    def test_zip_with_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("zip_with([1], [2]);")


class TestEnumerate(unittest.TestCase):
    def test_enumerate_pairs_index_and_value(self):
        env = run('let result = enumerate(["a", "b", "c"]);')
        self.assertEqual(env.get("result"), [[0, "a"], [1, "b"], [2, "c"]])

    def test_enumerate_of_empty_list_is_empty_list(self):
        env = run("let result = enumerate([]);")
        self.assertEqual(env.get("result"), [])

    def test_enumerate_matches_zip_of_range_and_list(self):
        env = run(
            'let l = ["x", "y", "z"];'
            "let en = enumerate(l);"
            "let zr = zip(range(len(l)), l);"
        )
        en, zr = env.get("en"), env.get("zr")
        self.assertEqual(en, zr)

    def test_enumerate_does_not_mutate_input(self):
        env = run('let a = ["a", "b"]; let result = enumerate(a);')
        self.assertEqual(env.get("a"), ["a", "b"])
        self.assertEqual(env.get("result"), [[0, "a"], [1, "b"]])

    def test_enumerate_non_list_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("enumerate(5);")
        self.assertEqual(ctx.exception.line, 1)
        with self.assertRaises(CinderRuntimeError):
            run('enumerate({"a": 1});')

    def test_enumerate_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('enumerate(["a"], 2);')


class TestAssert(unittest.TestCase):
    def test_assert_true_does_not_raise_and_returns_nil(self):
        env = run('let result = assert(true, "should not fire");')
        self.assertIsNone(env.get("result"))

    def test_assert_false_condition_raises_with_message_and_location(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('assert(1 == 2, "math is broken");')
        self.assertIn("math is broken", ctx.exception.message)
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 7)

    def test_assert_zero_is_truthy_and_does_not_raise(self):
        run('assert(0, "zero is falsy? no");')

    def test_assert_non_str_message_raises_regardless_of_condition(self):
        with self.assertRaises(CinderRuntimeError):
            run("assert(false, 42);")

    def test_assert_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("assert(true);")
        with self.assertRaises(CinderRuntimeError):
            run('assert(true, "x", "y");')


class TestIsList(unittest.TestCase):
    def test_is_list_true_for_list(self):
        self.assertIs(run("let result = is_list([1]);").get("result"), True)

    def test_is_list_false_for_map(self):
        self.assertIs(run('let result = is_list({"a": 1});').get("result"), False)

    def test_is_list_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_list();")
        with self.assertRaises(CinderRuntimeError):
            run("is_list([1], [2]);")


class TestIsMap(unittest.TestCase):
    def test_is_map_true_for_map(self):
        self.assertIs(run('let result = is_map({"a": 1});').get("result"), True)

    def test_is_map_false_for_list(self):
        self.assertIs(run("let result = is_map([1]);").get("result"), False)

    def test_is_map_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_map();")
        with self.assertRaises(CinderRuntimeError):
            run('is_map({"a": 1}, {"b": 2});')


class TestIsString(unittest.TestCase):
    def test_is_string_true_for_string(self):
        self.assertIs(run('let result = is_string("a");').get("result"), True)

    def test_is_string_false_for_number(self):
        self.assertIs(run("let result = is_string(1);").get("result"), False)

    def test_is_string_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_string();")
        with self.assertRaises(CinderRuntimeError):
            run('is_string("a", "b");')


class TestIsPalindrome(unittest.TestCase):
    def test_is_palindrome_odd_length_true(self):
        self.assertIs(run('let result = is_palindrome("racecar");').get("result"), True)

    def test_is_palindrome_even_length_true(self):
        self.assertIs(run('let result = is_palindrome("noon");').get("result"), True)

    def test_is_palindrome_false(self):
        self.assertIs(run('let result = is_palindrome("hello");').get("result"), False)

    def test_is_palindrome_empty_string_true(self):
        self.assertIs(run('let result = is_palindrome("");').get("result"), True)

    def test_is_palindrome_single_character_true(self):
        self.assertIs(run('let result = is_palindrome("a");').get("result"), True)

    def test_is_palindrome_no_case_folding(self):
        self.assertIs(
            run('let result = is_palindrome("Racecar");').get("result"), False
        )

    def test_is_palindrome_no_whitespace_stripping(self):
        self.assertIs(
            run('let result = is_palindrome("a man a");').get("result"), False
        )

    def test_is_palindrome_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_palindrome(5);")
        self.assertIn("is_palindrome", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_palindrome_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_palindrome();")
        with self.assertRaises(CinderRuntimeError):
            run('is_palindrome("a", "b");')


class TestIsAnagram(unittest.TestCase):
    def test_is_anagram_true(self):
        self.assertIs(
            run('let result = is_anagram("listen", "silent");').get("result"), True
        )

    def test_is_anagram_false(self):
        self.assertIs(
            run('let result = is_anagram("hello", "world");').get("result"), False
        )

    def test_is_anagram_both_empty_true(self):
        self.assertIs(run('let result = is_anagram("", "");').get("result"), True)

    def test_is_anagram_different_lengths_false(self):
        self.assertIs(run('let result = is_anagram("a", "");').get("result"), False)

    def test_is_anagram_order_independent_true(self):
        self.assertIs(
            run('let result = is_anagram("aabb", "abab");').get("result"), True
        )

    def test_is_anagram_case_sensitive_false(self):
        self.assertIs(
            run('let result = is_anagram("Listen", "Silent");').get("result"), False
        )

    def test_is_anagram_no_whitespace_stripping(self):
        self.assertIs(
            run('let result = is_anagram("dormitory", "dirty room");').get("result"),
            False,
        )

    def test_is_anagram_of_non_string_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_anagram(5, "abc");')
        self.assertIn("is_anagram", ctx.exception.message)
        self.assertIn("first", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_anagram_of_non_string_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_anagram("abc", 5);')
        self.assertIn("is_anagram", ctx.exception.message)
        self.assertIn("second", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_anagram_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('is_anagram("a");')
        with self.assertRaises(CinderRuntimeError):
            run('is_anagram("a", "b", "c");')


class TestIsPermutation(unittest.TestCase):
    def test_is_permutation_reordered_true(self):
        self.assertIs(
            run("let result = is_permutation([1, 2, 3], [3, 2, 1]);").get("result"),
            True,
        )

    def test_is_permutation_different_counts_false(self):
        self.assertIs(
            run("let result = is_permutation([1, 2, 2], [1, 1, 2]);").get("result"),
            False,
        )

    def test_is_permutation_both_empty_true(self):
        self.assertIs(run("let result = is_permutation([], []);").get("result"), True)

    def test_is_permutation_different_lengths_false(self):
        self.assertIs(
            run("let result = is_permutation([1], [1, 2]);").get("result"), False
        )

    def test_is_permutation_uses_deep_equality(self):
        self.assertIs(
            run("let result = is_permutation([[1, 2]], [[1, 2]]);").get("result"),
            True,
        )

    def test_is_permutation_distinguishes_int_and_string(self):
        self.assertIs(
            run('let result = is_permutation([1, "1"], ["1", 1]);').get("result"),
            True,
        )

    def test_is_permutation_non_list_first_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_permutation(5, [1, 2]);")
        self.assertIn("is_permutation", ctx.exception.message)
        self.assertIn("first", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_permutation_non_list_second_argument_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_permutation([1, 2], 5);")
        self.assertIn("is_permutation", ctx.exception.message)
        self.assertIn("second", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_permutation_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_permutation([1]);")
        with self.assertRaises(CinderRuntimeError):
            run("is_permutation([1], [2], [3]);")


class TestIsPangram(unittest.TestCase):
    def test_is_pangram_canonical_true(self):
        self.assertIs(
            run(
                'let result = is_pangram("The quick brown fox jumps over the lazy dog");'
            ).get("result"),
            True,
        )

    def test_is_pangram_second_canonical_true(self):
        self.assertIs(
            run(
                'let result = is_pangram("Pack my box with five dozen liquor jugs");'
            ).get("result"),
            True,
        )

    def test_is_pangram_missing_letters_false(self):
        self.assertIs(run('let result = is_pangram("hello world");').get("result"), False)

    def test_is_pangram_empty_string_false(self):
        self.assertIs(run('let result = is_pangram("");').get("result"), False)

    def test_is_pangram_all_uppercase_true(self):
        self.assertIs(
            run(
                'let result = is_pangram("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG");'
            ).get("result"),
            True,
        )

    def test_is_pangram_exact_alphabet_true(self):
        self.assertIs(
            run('let result = is_pangram("abcdefghijklmnopqrstuvwxyz");').get("result"),
            True,
        )

    def test_is_pangram_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_pangram(5);")
        self.assertIn("is_pangram", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_pangram_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_pangram();")
        with self.assertRaises(CinderRuntimeError):
            run('is_pangram("a", "b");')


class TestIsUpper(unittest.TestCase):
    def test_is_upper_all_upper_true(self):
        self.assertIs(run('let result = is_upper("ABC");').get("result"), True)

    def test_is_upper_all_lower_false(self):
        self.assertIs(run('let result = is_upper("abc");').get("result"), False)

    def test_is_upper_mixed_case_false(self):
        self.assertIs(run('let result = is_upper("Abc");').get("result"), False)

    def test_is_upper_with_digits_true(self):
        self.assertIs(run('let result = is_upper("ABC123");').get("result"), True)

    def test_is_upper_digits_only_false(self):
        self.assertIs(run('let result = is_upper("123");').get("result"), False)

    def test_is_upper_empty_string_false(self):
        self.assertIs(run('let result = is_upper("");').get("result"), False)

    def test_is_upper_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_upper(5);")
        self.assertIn("is_upper", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_upper_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_upper();")
        with self.assertRaises(CinderRuntimeError):
            run('is_upper("a", "b");')


class TestIsLower(unittest.TestCase):
    def test_is_lower_all_lower_true(self):
        self.assertIs(run('let result = is_lower("abc");').get("result"), True)

    def test_is_lower_all_upper_false(self):
        self.assertIs(run('let result = is_lower("ABC");').get("result"), False)

    def test_is_lower_mixed_case_false(self):
        self.assertIs(run('let result = is_lower("Abc");').get("result"), False)

    def test_is_lower_with_digits_true(self):
        self.assertIs(run('let result = is_lower("abc123");').get("result"), True)

    def test_is_lower_digits_only_false(self):
        self.assertIs(run('let result = is_lower("123");').get("result"), False)

    def test_is_lower_empty_string_false(self):
        self.assertIs(run('let result = is_lower("");').get("result"), False)

    def test_is_lower_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_lower(5);")
        self.assertIn("is_lower", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_lower_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_lower();")
        with self.assertRaises(CinderRuntimeError):
            run('is_lower("a", "b");')


class TestIsAlpha(unittest.TestCase):
    def test_is_alpha_all_alpha_true(self):
        self.assertIs(run('let result = is_alpha("abc");').get("result"), True)

    def test_is_alpha_with_digits_false(self):
        self.assertIs(run('let result = is_alpha("abc123");').get("result"), False)

    def test_is_alpha_empty_string_false(self):
        self.assertIs(run('let result = is_alpha("");').get("result"), False)

    def test_is_alpha_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_alpha(5);")
        self.assertIn("is_alpha", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_alpha_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_alpha();")
        with self.assertRaises(CinderRuntimeError):
            run('is_alpha("a", "b");')


class TestIsDigit(unittest.TestCase):
    def test_is_digit_all_digits_true(self):
        self.assertIs(run('let result = is_digit("123");').get("result"), True)

    def test_is_digit_with_decimal_point_false(self):
        self.assertIs(run('let result = is_digit("12.3");').get("result"), False)

    def test_is_digit_empty_string_false(self):
        self.assertIs(run('let result = is_digit("");').get("result"), False)

    def test_is_digit_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_digit(5);")
        self.assertIn("is_digit", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_digit_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_digit();")
        with self.assertRaises(CinderRuntimeError):
            run('is_digit("1", "2");')


class TestIsAlnum(unittest.TestCase):
    def test_is_alnum_letters_and_digits_true(self):
        self.assertIs(run('let result = is_alnum("abc123");').get("result"), True)

    def test_is_alnum_with_space_false(self):
        self.assertIs(run('let result = is_alnum("abc 123");').get("result"), False)

    def test_is_alnum_empty_string_false(self):
        self.assertIs(run('let result = is_alnum("");').get("result"), False)

    def test_is_alnum_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_alnum(5);")
        self.assertIn("is_alnum", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_alnum_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_alnum();")
        with self.assertRaises(CinderRuntimeError):
            run('is_alnum("a", "b");')


class TestIsSpace(unittest.TestCase):
    def test_is_space_all_spaces_true(self):
        self.assertIs(run('let result = is_space("   ");').get("result"), True)

    def test_is_space_with_non_space_false(self):
        self.assertIs(run('let result = is_space(" a ");').get("result"), False)

    def test_is_space_empty_string_false(self):
        self.assertIs(run('let result = is_space("");').get("result"), False)

    def test_is_space_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_space(5);")
        self.assertIn("is_space", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_space_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_space();")
        with self.assertRaises(CinderRuntimeError):
            run('is_space(" ", " ");')


class TestIsBlank(unittest.TestCase):
    def test_is_blank_empty_string_true(self):
        self.assertIs(run('let result = is_blank("");').get("result"), True)

    def test_is_blank_spaces_only_true(self):
        self.assertIs(run('let result = is_blank("   ");').get("result"), True)

    def test_is_blank_other_whitespace_true(self):
        self.assertIs(run('let result = is_blank("\\t\\n");').get("result"), True)

    def test_is_blank_non_whitespace_false(self):
        self.assertIs(run('let result = is_blank("a");').get("result"), False)

    def test_is_blank_padded_non_whitespace_false(self):
        self.assertIs(run('let result = is_blank(" a ");').get("result"), False)

    def test_is_blank_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_blank(5);")
        self.assertIn("is_blank", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_blank_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_blank();")
        with self.assertRaises(CinderRuntimeError):
            run('is_blank(" ", " ");')


class TestIsAscii(unittest.TestCase):
    def test_is_ascii_letters_and_digits_true(self):
        self.assertIs(run('let result = is_ascii("hello");').get("result"), True)

    def test_is_ascii_letters_digits_and_punctuation_true(self):
        self.assertIs(
            run('let result = is_ascii("Hello123 !");').get("result"), True
        )

    def test_is_ascii_with_accented_char_false(self):
        self.assertIs(run('let result = is_ascii("héllo");').get("result"), False)

    def test_is_ascii_with_non_ascii_script_false(self):
        self.assertIs(run('let result = is_ascii("日本語");').get("result"), False)

    def test_is_ascii_empty_string_true(self):
        self.assertIs(run('let result = is_ascii("");').get("result"), True)

    def test_is_ascii_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_ascii(5);")
        self.assertIn("is_ascii", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_ascii_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_ascii();")
        with self.assertRaises(CinderRuntimeError):
            run('is_ascii("a", "b");')


class TestIsNumeric(unittest.TestCase):
    def test_is_numeric_plain_digits_true(self):
        self.assertIs(run('let result = is_numeric("123");').get("result"), True)

    def test_is_numeric_with_letter_false(self):
        self.assertIs(run('let result = is_numeric("12a3");').get("result"), False)

    def test_is_numeric_empty_string_false(self):
        self.assertIs(run('let result = is_numeric("");').get("result"), False)

    def test_is_numeric_minus_sign_false(self):
        self.assertIs(run('let result = is_numeric("-5");').get("result"), False)

    def test_is_numeric_fraction_char_true_but_is_digit_false(self):
        self.assertIs(run('let result = is_numeric("½");').get("result"), True)
        self.assertIs(run('let result = is_digit("½");').get("result"), False)

    def test_is_numeric_of_non_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_numeric(5);")
        self.assertIn("is_numeric", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_numeric_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_numeric();")
        with self.assertRaises(CinderRuntimeError):
            run('is_numeric("1", "2");')


class TestIsSorted(unittest.TestCase):
    def test_is_sorted_ascending_numbers_true(self):
        self.assertIs(run("let result = is_sorted([1, 2, 3]);").get("result"), True)

    def test_is_sorted_descending_numbers_false(self):
        self.assertIs(run("let result = is_sorted([3, 2, 1]);").get("result"), False)

    def test_is_sorted_equal_adjacent_elements_true(self):
        self.assertIs(run("let result = is_sorted([1, 1, 2]);").get("result"), True)

    def test_is_sorted_ascending_strings_true(self):
        self.assertIs(
            run('let result = is_sorted(["a", "b", "c"]);').get("result"), True
        )

    def test_is_sorted_descending_strings_false(self):
        self.assertIs(
            run('let result = is_sorted(["c", "a"]);').get("result"), False
        )

    def test_is_sorted_empty_list_true(self):
        self.assertIs(run("let result = is_sorted([]);").get("result"), True)

    def test_is_sorted_single_element_true(self):
        self.assertIs(run("let result = is_sorted([5]);").get("result"), True)

    def test_is_sorted_mixed_numeric_and_string_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run('is_sorted([1, "a"]);')
        self.assertIn("is_sorted", ctx.exception.message)

    def test_is_sorted_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_sorted(5);")
        self.assertIn("is_sorted", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_sorted_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_sorted();")
        with self.assertRaises(CinderRuntimeError):
            run("is_sorted([1], [2]);")


class TestIsUnique(unittest.TestCase):
    def test_is_unique_all_distinct_true(self):
        self.assertIs(run("let result = is_unique([1, 2, 3]);").get("result"), True)

    def test_is_unique_with_duplicate_false(self):
        self.assertIs(run("let result = is_unique([1, 2, 2]);").get("result"), False)

    def test_is_unique_empty_list_true(self):
        self.assertIs(run("let result = is_unique([]);").get("result"), True)

    def test_is_unique_single_element_true(self):
        self.assertIs(run("let result = is_unique([5]);").get("result"), True)

    def test_is_unique_duplicate_strings_false(self):
        self.assertIs(
            run('let result = is_unique(["a", "b", "a"]);').get("result"), False
        )

    def test_is_unique_deep_equality_nested_lists_false(self):
        self.assertIs(
            run("let result = is_unique([[1, 2], [1, 2]]);").get("result"), False
        )

    def test_is_unique_of_non_list_raises(self):
        with self.assertRaises(CinderRuntimeError) as ctx:
            run("is_unique(5);")
        self.assertIn("is_unique", ctx.exception.message)
        self.assertIn("int", ctx.exception.message)

    def test_is_unique_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_unique();")
        with self.assertRaises(CinderRuntimeError):
            run("is_unique([1], [2]);")


class TestIsNumber(unittest.TestCase):
    def test_is_number_true_for_int(self):
        self.assertIs(run("let result = is_number(1);").get("result"), True)

    def test_is_number_true_for_float(self):
        self.assertIs(run("let result = is_number(1.5);").get("result"), True)

    def test_is_number_false_for_string(self):
        self.assertIs(run('let result = is_number("1");').get("result"), False)

    def test_is_number_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_number();")
        with self.assertRaises(CinderRuntimeError):
            run("is_number(1, 2);")


class TestIsInt(unittest.TestCase):
    def test_is_int_true_for_int(self):
        self.assertIs(run("let result = is_int(4);").get("result"), True)

    def test_is_int_true_for_negative_int(self):
        self.assertIs(run("let result = is_int(-3);").get("result"), True)

    def test_is_int_false_for_float(self):
        self.assertIs(run("let result = is_int(4.0);").get("result"), False)

    def test_is_int_false_for_bool(self):
        self.assertIs(run("let result = is_int(true);").get("result"), False)

    def test_is_int_false_for_non_numeric_string(self):
        self.assertIs(run('let result = is_int("4");').get("result"), False)

    def test_is_int_false_for_nil(self):
        self.assertIs(run("let result = is_int(nil);").get("result"), False)

    def test_is_int_false_for_list(self):
        self.assertIs(run("let result = is_int([1, 2]);").get("result"), False)

    def test_is_int_false_for_map(self):
        self.assertIs(run("let result = is_int({});").get("result"), False)

    def test_is_int_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_int();")
        with self.assertRaises(CinderRuntimeError):
            run("is_int(1, 2);")


class TestIsFloat(unittest.TestCase):
    def test_is_float_true_for_float(self):
        self.assertIs(run("let result = is_float(4.0);").get("result"), True)

    def test_is_float_true_for_negative_float(self):
        self.assertIs(run("let result = is_float(-3.5);").get("result"), True)

    def test_is_float_false_for_int(self):
        self.assertIs(run("let result = is_float(4);").get("result"), False)

    def test_is_float_false_for_bool(self):
        self.assertIs(run("let result = is_float(true);").get("result"), False)

    def test_is_float_false_for_non_numeric_string(self):
        self.assertIs(run('let result = is_float("4");').get("result"), False)

    def test_is_float_false_for_nil(self):
        self.assertIs(run("let result = is_float(nil);").get("result"), False)

    def test_is_float_false_for_list(self):
        self.assertIs(run("let result = is_float([1, 2]);").get("result"), False)

    def test_is_float_false_for_map(self):
        self.assertIs(run("let result = is_float({});").get("result"), False)

    def test_is_float_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_float();")
        with self.assertRaises(CinderRuntimeError):
            run("is_float(1, 2);")

    def test_is_number_implies_exactly_one_of_is_int_is_float(self):
        result = run(
            "let a = is_int(4) or is_float(4.0);"
            "let b = is_int(4) and is_float(4);"
            "let c = is_int(4.0) and is_float(4.0);"
        )
        self.assertIs(result.get("a"), True)
        self.assertIs(result.get("b"), False)
        self.assertIs(result.get("c"), False)


class TestIsBool(unittest.TestCase):
    def test_is_bool_true_for_bool(self):
        self.assertIs(run("let result = is_bool(true);").get("result"), True)

    def test_is_bool_false_for_int(self):
        self.assertIs(run("let result = is_bool(0);").get("result"), False)

    def test_is_bool_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_bool();")
        with self.assertRaises(CinderRuntimeError):
            run("is_bool(true, false);")


class TestIsNil(unittest.TestCase):
    def test_is_nil_true_for_nil(self):
        self.assertIs(run("let result = is_nil(nil);").get("result"), True)

    def test_is_nil_false_for_false(self):
        self.assertIs(run("let result = is_nil(false);").get("result"), False)

    def test_is_nil_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_nil();")
        with self.assertRaises(CinderRuntimeError):
            run("is_nil(nil, nil);")


class TestIsFunction(unittest.TestCase):
    def test_is_function_true_for_named_fn(self):
        env = run("fn f(x) { return x; } let result = is_function(f);")
        self.assertIs(env.get("result"), True)

    def test_is_function_true_for_anonymous_fn(self):
        env = run("let result = is_function(fn(x) { return x; });")
        self.assertIs(env.get("result"), True)

    def test_is_function_true_for_builtin_by_name(self):
        env = run("let result = is_function(len);")
        self.assertIs(env.get("result"), True)

    def test_is_function_false_for_non_function(self):
        env = run("let result = is_function(1);")
        self.assertIs(env.get("result"), False)

    def test_is_function_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("is_function();")
        with self.assertRaises(CinderRuntimeError):
            run("is_function(len, len);")


class TestFormat(unittest.TestCase):
    def test_format_substitutes_placeholders_in_order(self):
        env = run('let result = format("{} + {} = {}", 1, 2, 3);')
        self.assertEqual(env.get("result"), "1 + 2 = 3")

    def test_format_with_no_placeholders_and_no_args(self):
        env = run('let result = format("no placeholders");')
        self.assertEqual(env.get("result"), "no placeholders")

    def test_format_uses_stringify_not_python_str(self):
        env = run('let result = format("{}", [1, 2]);')
        self.assertEqual(env.get("result"), "[1, 2]")

    def test_format_renders_string_argument_unquoted(self):
        env = run('let result = format("{}", "hi");')
        self.assertEqual(env.get("result"), "hi")

    def test_format_too_few_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('format("{} {}", 1);')

    def test_format_too_many_arguments_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('format("{}", 1, 2);')

    def test_format_invalid_brace_pair_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run('format("{ }", 1);')

    def test_format_non_string_template_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("format(5, 1);")

    def test_format_wrong_arity_raises(self):
        with self.assertRaises(CinderRuntimeError):
            run("format();")


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
