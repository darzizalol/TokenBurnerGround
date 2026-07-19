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


if __name__ == "__main__":
    unittest.main()
