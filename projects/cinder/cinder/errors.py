"""Structured error hierarchy for Cinder.

All Cinder-raised errors carry line/column so the CLI (and tests) can point
at exactly where things went wrong, instead of a bare Python traceback.
"""


class CinderError(Exception):
    """Base class for all errors raised by Cinder tooling."""

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{line}:{column}: {message}")


class LexError(CinderError):
    """Raised by the lexer on unterminated strings or unrecognized characters.

    `unterminated` marks the "ran off the end looking for a closing quote"
    case: the REPL uses it to tell "might be completed by more input" apart
    from "this line is just wrong," which it must report immediately.
    """

    def __init__(
        self, message: str, line: int, column: int, unterminated: bool = False
    ):
        super().__init__(message, line, column)
        self.unterminated = unterminated


class ParseError(CinderError):
    """Raised by the parser on malformed token sequences."""


_UNSET = object()


class CinderRuntimeError(CinderError):
    """Raised by the interpreter for errors detected during evaluation.

    `frames` records the call chain the error passed through on its way out,
    one `(function_name, call_line, call_column)` tuple per call-site,
    innermost call first. Empty for an error raised directly at top level.

    `value` is the original Cinder value a `catch (e)` clause binds `e`
    to. It defaults to `message` itself (every internal engine error is,
    in effect, a string-valued exception) unless explicitly overridden —
    `ThrowStmt` handling is the only caller that does, passing the
    literal value the user threw.
    """

    def __init__(
        self, message: str, line: int, column: int, value: object = _UNSET
    ):
        super().__init__(message, line, column)
        self.frames: list[tuple[str, int, int]] = []
        self.value = message if value is _UNSET else value
