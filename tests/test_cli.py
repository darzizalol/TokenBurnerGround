"""Tests for cinder.cli: the argparse entrypoint scaffolding."""

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

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
    def test_run_not_implemented_exits_zero(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(["run", "examples/does_not_exist_yet.cin"])
        self.assertEqual(exit_code, 0)
        self.assertIn("not implemented", stdout.getvalue().lower())

    def test_repl_not_implemented_exits_zero(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(["repl"])
        self.assertEqual(exit_code, 0)
        self.assertIn("not implemented", stdout.getvalue().lower())

    def test_missing_command_requires_subcommand(self):
        with self.assertRaises(SystemExit):
            cli.main([])


if __name__ == "__main__":
    unittest.main()
