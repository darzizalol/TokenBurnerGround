"""Tests for cinder.cli: the argparse entrypoint scaffolding."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from cinder import cli


class TestCliHelp(unittest.TestCase):
    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())

    def test_module_has_main(self):
        self.assertTrue(hasattr(cli, "main"))


class TestCliSubcommands(unittest.TestCase):
    def test_run_let_script_exits_zero(self):
        with tempfile.NamedTemporaryFile("w", suffix=".cin", delete=False) as f:
            f.write("let x = 1 + 2;\nlet y = x * 2;\n")
            path = f.name
        exit_code = cli.main(["run", path])
        self.assertEqual(exit_code, 0)

    def test_run_executes_via_subprocess(self):
        with tempfile.NamedTemporaryFile("w", suffix=".cin", delete=False) as f:
            f.write("let x = 1 + 2;\n")
            path = f.name
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "run", path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

    def test_repl_on_empty_stdin_exits_zero(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch("sys.stdin", io.StringIO("")):
            exit_code = cli.main(["repl"])
        self.assertEqual(exit_code, 0)

    def test_missing_command_requires_subcommand(self):
        with self.assertRaises(SystemExit):
            cli.main([])

    def test_run_nonexistent_path_reports_diagnostic_not_traceback(self):
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "run", "/no/such/file.cin"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("/no/such/file.cin", result.stderr)


class TestCliEval(unittest.TestCase):
    def test_eval_prints_expression_result(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(["eval", "print(1 + 2);"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "3\n")

    def test_eval_multi_statement_snippet(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(["eval", "let x = 1; x = 2; print(x);"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "2\n")

    def test_eval_runtime_error_reports_eval_prefixed_diagnostic(self):
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "eval", "print(undefined_name);"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(
            "<eval>:1:7: undefined name 'undefined_name'", result.stderr
        )

    def test_eval_parse_error_reports_eval_prefixed_diagnostic(self):
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "eval", "let x = ;"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(result.stderr.startswith("<eval>:"))

    def test_run_file_behavior_unchanged_after_refactor(self):
        with tempfile.NamedTemporaryFile("w", suffix=".cin", delete=False) as f:
            f.write("print(1 + 2);\n")
            path = f.name
        result = subprocess.run(
            [sys.executable, "-m", "cinder.cli", "run", path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "3\n")


if __name__ == "__main__":
    unittest.main()
