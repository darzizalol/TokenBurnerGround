"""Interactive read-eval-print loop for Cinder.

Reads statements from stdin (or an injected `read_line` source, for tests),
accumulates lines until parens/braces/brackets balance, then lexes, parses,
and executes the buffered source against an `Environment` that persists
across inputs. Bare expression statements echo their value; `CinderError`s
are caught and reported per statement without killing the loop.
"""

from typing import Callable, Optional

from cinder.ast_nodes import ExprStmt
from cinder.builtins import create_global_environment, stringify
from cinder.errors import CinderError, LexError
from cinder.interpreter import Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_program
from cinder.tokens import TokenType

PRIMARY_PROMPT = ">>> "
CONTINUATION_PROMPT = "... "
REPL_SOURCE_NAME = "<repl>"
EXIT_COMMAND = "exit"

_OPENERS = {TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET}
_CLOSERS = {TokenType.RPAREN, TokenType.RBRACE, TokenType.RBRACKET}


def _try_enable_readline() -> bool:
    """Import `readline` so `input()` gets history/in-line editing for free.

    Not available on every platform (e.g. stock Windows Python), so the REPL
    must keep working without it."""
    try:
        import readline  # noqa: F401
    except ImportError:
        return False
    return True


def _needs_more_input(source: str) -> bool:
    """True while `source` is an incomplete statement: unbalanced brackets
    or an unterminated string, either of which more lines might complete."""
    try:
        tokens = tokenize(source)
    except LexError as e:
        return e.unterminated
    depth = 0
    for token in tokens:
        if token.type in _OPENERS:
            depth += 1
        elif token.type in _CLOSERS:
            depth -= 1
    return depth > 0


def run_repl(
    read_line: Callable[[str], str] = input,
    write: Optional[Callable[[str], None]] = None,
) -> None:
    if write is None:
        write = print

    _try_enable_readline()

    interpreter = Interpreter()
    env = create_global_environment()
    buffered_lines: list[str] = []

    while True:
        prompt = CONTINUATION_PROMPT if buffered_lines else PRIMARY_PROMPT
        try:
            line = read_line(prompt)
        except EOFError:
            return

        if not buffered_lines and line.strip() == EXIT_COMMAND:
            return

        buffered_lines.append(line)
        source = "\n".join(buffered_lines)
        if _needs_more_input(source):
            continue
        buffered_lines = []

        try:
            statements = parse_program(tokenize(source))
            for statement in statements:
                if isinstance(statement, ExprStmt):
                    value = interpreter.evaluate(statement.expression, env)
                    if value is not None:
                        write(stringify(value, quoted=True))
                else:
                    interpreter.execute(statement, env)
        except CinderError as e:
            write(f"{REPL_SOURCE_NAME}:{e.line}:{e.column}: {e.message}")
