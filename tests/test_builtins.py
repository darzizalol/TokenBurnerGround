"""Tests for cinder.builtins: print, len, type, str, int, float."""

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
