"""Command-line entrypoint for Cinder: `run <file>` and `repl` subcommands.

`run` lexes, parses, and executes a `.cin` file end to end against a global
scope pre-populated with the standard library builtins (`print`, `len`,
`type`, `str`, `int`, `float`).
"""

import argparse
import sys

from cinder.builtins import create_global_environment
from cinder.interpreter import Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_program


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cinder", description="The Cinder scripting language.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a Cinder script")
    run_parser.add_argument("file", help="Path to a .cin script")

    subparsers.add_parser("repl", help="Start an interactive Cinder REPL")

    return parser


def run_file(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    statements = parse_program(tokenize(source))
    interpreter = Interpreter()
    env = create_global_environment()
    for statement in statements:
        interpreter.execute(statement, env)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        run_file(args.file)
        return 0
    if args.command == "repl":
        print("repl: not implemented yet")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
