"""Tests for cinder.repl: the interactive read-eval-print loop."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from cinder.builtins import create_global_environment
from cinder.interpreter import Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_program
from cinder.repl import _make_completer, _save_history, _try_enable_readline, run_repl


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


class TestLoadCommand(unittest.TestCase):
    def _run(self, lines):
        outputs = []
        run_repl(read_line=_make_read_line(lines), write=outputs.append)
        return outputs

    def _write_temp_cin(self, contents):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = os.path.join(tmpdir.name, "helpers.cin")
        with open(path, "w") as f:
            f.write(contents)
        return path

    def test_load_binds_names_visible_at_next_prompt(self):
        path = self._write_temp_cin(
            'fn double(x) { return x * 2; } let greeting = "hi";'
        )
        outputs = self._run([f":load {path}", "double(21);", "greeting;"])
        self.assertEqual(outputs, ["42", '"hi"'])

    def test_load_nonexistent_file_reports_error_and_continues(self):
        outputs = self._run([":load /no/such/file.cin", "1 + 1;"])
        self.assertEqual(len(outputs), 2)
        self.assertIn("/no/such/file.cin", outputs[0])
        self.assertEqual(outputs[1], "2")

    def test_load_isolates_errors_per_statement(self):
        path = self._write_temp_cin("let a = 1;\nundefined_name;\nlet b = 2;")
        outputs = self._run([f":load {path}", "b;"])
        self.assertEqual(len(outputs), 2)
        self.assertIn(path, outputs[0])
        self.assertIn("undefined name", outputs[0].lower())
        self.assertEqual(outputs[1], "2")

    def test_bare_load_reports_usage_and_does_not_read_a_file(self):
        outputs = self._run([":load", "1 + 1;"])
        self.assertEqual(outputs, ["usage: :load <path>", "2"])

    def test_bare_load_with_trailing_space_reports_usage(self):
        outputs = self._run([":load ", "1 + 1;"])
        self.assertEqual(outputs, ["usage: :load <path>", "2"])

    def test_loaded_names_are_immediately_tab_completable(self):
        path = self._write_temp_cin("let my_loaded_var = 1;")
        outputs = []

        def read_line(prompt):
            outputs.append(None)
            raise EOFError

        # Drive the REPL far enough to load the file, then inspect env
        # directly via the completer, mirroring TestCompleter's approach.
        interpreter = Interpreter()
        env = create_global_environment()
        from cinder.repl import _load_file
        _load_file(path, interpreter, env, lambda *_: None)
        completer = _make_completer(env)
        self.assertEqual(completer("my_loaded", 0), "my_loaded_var")

    def test_load_only_triggers_at_start_of_fresh_statement(self):
        # Mid-continuation (buffered_lines non-empty), a line starting with
        # ":load" is just source text for the open block, not the command.
        with mock.patch("cinder.repl._load_file") as mock_load_file:
            self._run(["if (true) {", ":load x;", "}"])
        mock_load_file.assert_not_called()

        with mock.patch("cinder.repl._load_file") as mock_load_file:
            self._run([":load x"])
        mock_load_file.assert_called_once()


class TestReadlineIntegration(unittest.TestCase):
    def test_try_enable_readline_succeeds_when_available(self):
        self.assertTrue(_try_enable_readline(create_global_environment()))

    def test_try_enable_readline_returns_false_without_raising_when_missing(self):
        with mock.patch.dict(sys.modules, {"readline": None}):
            self.assertFalse(_try_enable_readline(create_global_environment()))

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

        self.assertTrue(_try_enable_readline(create_global_environment()))
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


class TestCompleter(unittest.TestCase):
    def test_unambiguous_prefix_completes_at_state_zero(self):
        completer = _make_completer(create_global_environment())
        self.assertEqual(completer("prin", 0), "print")

    def test_ambiguous_prefix_yields_each_match_in_sorted_order_then_none(self):
        completer = _make_completer(create_global_environment())
        matches = []
        state = 0
        while True:
            match = completer("ma", state)
            if match is None:
                break
            matches.append(match)
            state += 1
        self.assertEqual(matches, sorted(matches))
        for name in ("map", "map_keys", "map_values", "max", "max_by"):
            self.assertIn(name, matches)

    def test_no_match_returns_none_at_state_zero(self):
        completer = _make_completer(create_global_environment())
        self.assertIsNone(completer("zzz", 0))

    def test_session_defined_variable_is_completable(self):
        env = create_global_environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("let my_var = 1;"))
        interpreter.execute(statements[0], env)

        completer = _make_completer(env)
        self.assertEqual(completer("my_v", 0), "my_var")

    def test_variable_in_one_environment_does_not_leak_into_another(self):
        env_with_var = create_global_environment()
        interpreter = Interpreter()
        statements = parse_program(tokenize("let my_var = 1;"))
        interpreter.execute(statements[0], env_with_var)

        other_env = create_global_environment()
        completer = _make_completer(other_env)
        self.assertIsNone(completer("my_v", 0))


if __name__ == "__main__":
    unittest.main()
