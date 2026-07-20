"""Golden-output tests: run each examples/*.cin program and diff stdout
against its checked-in examples/*.expected file, so regressions in any
earlier layer (lexer, parser, interpreter, builtins) get caught here too.
"""

import subprocess
import sys
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _example_stems():
    return sorted(p.stem for p in EXAMPLES_DIR.glob("*.cin"))


class TestExamples(unittest.TestCase):
    def test_examples_directory_is_not_empty(self):
        self.assertGreaterEqual(len(_example_stems()), 3)

    def test_every_example_matches_its_golden_output(self):
        for stem in _example_stems():
            with self.subTest(example=stem):
                script = EXAMPLES_DIR / f"{stem}.cin"
                expected_path = EXAMPLES_DIR / f"{stem}.expected"
                self.assertTrue(
                    expected_path.exists(),
                    f"missing golden file for {script}: {expected_path}",
                )
                result = subprocess.run(
                    [sys.executable, "-m", "cinder.cli", "run", str(script)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode, 0, f"{script} exited {result.returncode}: {result.stderr}"
                )
                expected = expected_path.read_text(encoding="utf-8")
                self.assertEqual(result.stdout, expected)


if __name__ == "__main__":
    unittest.main()
