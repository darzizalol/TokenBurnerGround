"""Tests for cinder.repl: the interactive read-eval-print loop."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from cinder.repl import _save_history, _try_enable_readline, run_repl


def _make_read_line(lines):
    it = iter(lines)

    def read_line(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return read_line


class TestRepl(unittest.TestCase):
    def _run(self, lines):
        outputs = []
        run_repl(read_line=_make_read_line(lines), write=outputs.append)
        return outputs

    def test_let_then_reference_next_line(self):
        outputs = self._run(["let x = 1 + 2;", "x;"])
        self.assertEqual(outputs, ["3"])

    def test_let_statement_produces_no_output(self):
        outputs = self._run(["let a = 1;"])
        self.assertEqual(outputs, [])

    def test_bare_expression_echoes_value(self):
        outputs = self._run(['"hello";'])
        self.assertEqual(outputs, ['"hello"'])

    def test_cinder_error_prints_diagnostic_and_continues(self):
        outputs = self._run(["y;", "let z = 5;", "z;"])
        self.assertEqual(len(outputs), 2)
        self.assertIn("<repl>", outputs[0])
        self.assertIn("undefined name", outputs[0].lower())
        self.assertEqual(outputs[1], "5")

    def test_illegal_character_reports_immediately_and_does_not_wedge(self):
        outputs = self._run(["@;", "let z = 5;", "z;"])
        self.assertEqual(len(outputs), 2)
        self.assertIn("<repl>", outputs[0])
        self.assertIn("unrecognized character", outputs[0].lower())
        self.assertEqual(outputs[1], "5")

    def test_clean_exit_on_eof(self):
        outputs = self._run([])
        self.assertEqual(outputs, [])

    def test_exit_command_stops_loop(self):
        outputs = self._run(["exit", "let a = 1;", "a;"])
        self.assertEqual(outputs, [])

    def test_multiline_block_accumulates_until_balanced(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            outputs = self._run(["if (true) {", 'print("in if");', "}"])
        self.assertEqual(outputs, [])
        self.assertEqual(stdout.getvalue().strip(), "in if")

    def test_environment_persists_across_function_call(self):
        outputs = self._run([
            "fn add(a, b) {",
            "  return a + b;",
            "}",
            "add(2, 3);",
        ])
        self.assertEqual(outputs, ["5"])


class TestReadlineIntegration(unittest.TestCase):
    def test_try_enable_readline_succeeds_when_available(self):
        self.assertTrue(_try_enable_readline())

    def test_try_enable_readline_returns_false_without_raising_when_missing(self):
        with mock.patch.dict(sys.modules, {"readline": None}):
            self.assertFalse(_try_enable_readline())

    def test_repl_still_works_when_readline_is_unavailable(self):
        with mock.patch.dict(sys.modules, {"readline": None}):
            outputs = []
            run_repl(read_line=_make_read_line(["let x = 1 + 2;", "x;"]), write=outputs.append)
        self.assertEqual(outputs, ["3"])


class TestHistoryPersistence(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._history_file = os.path.join(self._tmpdir.name, ".cinder_history")
        self._patcher = mock.patch("cinder.repl.HISTORY_FILE", self._history_file)
        self._patcher.start()
        import readline
        readline.clear_history()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()
        import readline
        readline.clear_history()

    def test_history_saved_on_exit_and_loaded_next_session(self):
        import readline
        readline.add_history("let x = 1;")
        readline.add_history("x;")

        run_repl(read_line=_make_read_line([]), write=lambda *_: None)
        self.assertTrue(os.path.exists(self._history_file))

        readline.clear_history()
        self.assertEqual(readline.get_current_history_length(), 0)

        self.assertTrue(_try_enable_readline())
        self.assertEqual(readline.get_current_history_length(), 2)
        self.assertEqual(readline.get_history_item(1), "let x = 1;")
        self.assertEqual(readline.get_history_item(2), "x;")

    def test_first_run_with_no_history_file_starts_and_exits_cleanly(self):
        self.assertFalse(os.path.exists(self._history_file))
        outputs = self._run_helper([])
        self.assertEqual(outputs, [])
        self.assertTrue(os.path.exists(self._history_file))

    def test_readline_unavailable_repl_still_exits_cleanly(self):
        with mock.patch.dict(sys.modules, {"readline": None}):
            outputs = self._run_helper(["let x = 1;"])
        self.assertEqual(outputs, [])
        self.assertFalse(os.path.exists(self._history_file))

    def test_write_history_file_oserror_does_not_raise(self):
        import readline
        with mock.patch.object(readline, "write_history_file", side_effect=OSError):
            outputs = self._run_helper(["let x = 1;"])
        self.assertEqual(outputs, [])

    def test_save_history_oserror_is_swallowed(self):
        import readline
        with mock.patch.object(readline, "write_history_file", side_effect=OSError):
            _save_history()  # must not raise

    def _run_helper(self, lines):
        outputs = []
        run_repl(read_line=_make_read_line(lines), write=outputs.append)
        return outputs


if __name__ == "__main__":
    unittest.main()
