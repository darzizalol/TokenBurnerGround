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
    """Raised by the lexer on unterminated strings or unrecognized characters."""


class ParseError(CinderError):
    """Raised by the parser on malformed token sequences."""
