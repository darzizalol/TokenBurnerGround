"""Interactive read-eval-print loop for Cinder.

Reads statements from stdin (or an injected `read_line` source, for tests),
accumulates lines until parens/braces/brackets balance, then lexes, parses,
and executes the buffered source against an `Environment` that persists
across inputs. Bare expression statements echo their value; `CinderError`s
are caught and reported per statement without killing the loop.
"""

from pathlib import Path
from typing import Callable, Optional

from cinder.ast_nodes import ExprStmt
from cinder.builtins import create_global_environment, stringify
from cinder.errors import CinderError, LexError
from cinder.interpreter import Environment, Interpreter
from cinder.lexer import tokenize
from cinder.parser import parse_program
from cinder.tokens import KEYWORDS, TokenType

PRIMARY_PROMPT = ">>> "
CONTINUATION_PROMPT = "... "
REPL_SOURCE_NAME = "<repl>"
EXIT_COMMAND = "exit"
LOAD_COMMAND_PREFIX = ":load "
LOAD_COMMAND_BARE = ":load"

# Lives inside the project directory, never the user's home or a dotfile
# outside the repo.
HISTORY_FILE = str(Path(__file__).resolve().parent.parent / ".cinder_history")

_OPENERS = {TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET}
_CLOSERS = {TokenType.RPAREN, TokenType.RBRACE, TokenType.RBRACKET}


def _make_completer(env: Environment) -> Callable[[str, int], Optional[str]]:
    """Build a `readline`-shaped completer over `env`'s bindings (which
    already include every builtin, since `create_global_environment` defines
    them straight into the environment) plus the language's keywords.

    Re-reads `env` on every call, so names defined later in the session (via
    `let`/`const`/`fn`) become completable immediately."""
    def completer(text: str, state: int) -> Optional[str]:
        candidates = sorted(n for n in KEYWORDS.keys() | env.all_names() if n.startswith(text))
        if state < len(candidates):
            return candidates[state]
        return None
    return completer


def _try_enable_readline(env: Environment) -> bool:
    """Import `readline` so `input()` gets history/in-line editing for free,
    load any history persisted from a previous session, and wire up Tab
    completion over `env`'s names.

    Not available on every platform (e.g. stock Windows Python), so the REPL
    must keep working without it."""
    try:
        import readline  # noqa: F401
    except ImportError:
        return False
    try:
        readline.read_history_file(HISTORY_FILE)
    except OSError:
        pass  # no history file yet, or it's unreadable — start fresh
    readline.set_completer(_make_completer(env))
    readline.parse_and_bind("tab: complete")
    return True


def _save_history() -> None:
    """Persist in-session command history to `HISTORY_FILE`, best-effort."""
    import readline
    try:
        readline.write_history_file(HISTORY_FILE)
    except OSError:
        pass  # e.g. read-only filesystem — don't let this crash the REPL


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


def _run_statements(
    statements: list,
    interpreter: Interpreter,
    env: Environment,
    write: Callable[[str], None],
    source_name: str,
) -> None:
    """Execute `statements` one at a time against `env`, catching each
    `CinderError` per-statement so one bad statement doesn't stop the rest
    from running. `source_name` labels diagnostics (`<repl>` for prompt
    input, a loaded file's path for `:load`)."""
    for statement in statements:
        try:
            if isinstance(statement, ExprStmt):
                value = interpreter.evaluate(statement.expression, env)
                if value is not None:
                    write(stringify(value, quoted=True))
            else:
                interpreter.execute(statement, env)
        except CinderError as e:
            write(f"{source_name}:{e.line}:{e.column}: {e.message}")


def _load_file(
    path: str,
    interpreter: Interpreter,
    env: Environment,
    write: Callable[[str], None],
) -> None:
    """Handle a `:load <path>` REPL command: read and run `path`'s
    statements against the session's persistent `env`, so later prompt
    input sees any names it binds."""
    if not path:
        write("usage: :load <path>")
        return
    try:
        source = Path(path).read_text()
    except OSError as exc:
        write(f"could not read {path}: {exc}")
        return
    try:
        statements = parse_program(tokenize(source))
    except CinderError as e:
        write(f"{path}:{e.line}:{e.column}: {e.message}")
        return
    _run_statements(statements, interpreter, env, write, path)


def run_repl(
    read_line: Callable[[str], str] = input,
    write: Optional[Callable[[str], None]] = None,
) -> None:
    if write is None:
        write = print

    interpreter = Interpreter()
    env = create_global_environment()
    has_readline = _try_enable_readline(env)
    buffered_lines: list[str] = []

    try:
        while True:
            prompt = CONTINUATION_PROMPT if buffered_lines else PRIMARY_PROMPT
            try:
                line = read_line(prompt)
            except EOFError:
                return

            if not buffered_lines and line.strip() == EXIT_COMMAND:
                return

            if not buffered_lines and (
                line.strip().startswith(LOAD_COMMAND_PREFIX)
                or line.strip() == LOAD_COMMAND_BARE
            ):
                path = line.strip()[len(LOAD_COMMAND_PREFIX):].strip()
                _load_file(path, interpreter, env, write)
                continue

            buffered_lines.append(line)
            source = "\n".join(buffered_lines)
            if _needs_more_input(source):
                continue
            buffered_lines = []

            try:
                statements = parse_program(tokenize(source))
            except CinderError as e:
                write(f"{REPL_SOURCE_NAME}:{e.line}:{e.column}: {e.message}")
                continue
            _run_statements(statements, interpreter, env, write, REPL_SOURCE_NAME)
    finally:
        if has_readline:
            _save_history()
