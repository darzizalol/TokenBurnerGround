"""Tests for cinder.cli's `run` subcommand catching CinderError and printing
a `file:line:column: message` diagnostic to stderr with a non-zero exit code."""

import subprocess
import sys
import tempfile
import unittest


def _run_script(source: str):
    with tempfile.NamedTemporaryFile("w", suffix=".cin", delete=False) as f:
        f.write(source)
        path = f.name
    result = subprocess.run(
        [sys.executable, "-m", "cinder.cli", "run", path],
        capture_output=True,
        text=True,
    )
    return path, result


class TestCliErrorDiagnostics(unittest.TestCase):
    def test_lex_error_prints_diagnostic(self):
        path, result = _run_script('let x = "unterminated;\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), f"{path}:1:9: unterminated string")

    def test_parse_error_prints_diagnostic(self):
        path, result = _run_script("let x = 1\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr.strip(),
            f"{path}:2:1: expected ';' after variable declaration, found end of input",
        )

    def test_runtime_error_prints_diagnostic(self):
        path, result = _run_script("print(undefined_var);\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr.strip(),
            f"{path}:1:7: undefined name 'undefined_var'",
        )

    def test_clean_script_exits_zero_with_no_stderr(self):
        path, result = _run_script("let x = 1 + 2;\nprint(x);\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_single_call_prints_one_at_line(self):
        path, result = _run_script(
            'fn f() { return 1 + "a"; }\n'
            "f();\n"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr.strip(),
            f"{path}:1:19: unsupported operand types for '+': int and string\n"
            "  at f (2:2)",
        )

    def test_two_level_chain_prints_innermost_call_first(self):
        path, result = _run_script(
            "fn a() { b(); }\n"
            'fn b() { return 1 + "a"; }\n'
            "a();\n"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr.strip(),
            f"{path}:2:19: unsupported operand types for '+': int and string\n"
            "  at b (1:11)\n"
            "  at a (3:2)",
        )

    def test_recursive_error_prints_one_at_line_per_active_call(self):
        path, result = _run_script(
            "fn rec(n) {\n"
            "  if (n <= 0) { return 1 + \"a\"; }\n"
            "  return rec(n - 1);\n"
            "}\n"
            "rec(3);\n"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr.strip(),
            f"{path}:2:26: unsupported operand types for '+': int and string\n"
            "  at rec (3:13)\n"
            "  at rec (3:13)\n"
            "  at rec (3:13)\n"
            "  at rec (5:4)",
        )


if __name__ == "__main__":
    unittest.main()
