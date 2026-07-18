"""Command-line entrypoint for Cinder: `run <file>` and `repl` subcommands."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cinder", description="The Cinder scripting language.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a Cinder script")
    run_parser.add_argument("file", help="Path to a .cin script")

    subparsers.add_parser("repl", help="Start an interactive Cinder REPL")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        print("run: not implemented yet")
        return 0
    if args.command == "repl":
        print("repl: not implemented yet")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
