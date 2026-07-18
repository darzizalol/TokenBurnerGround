"""Token and TokenType definitions for the Cinder lexer.

This is a stub: only enough exists here to be importable by the CLI
scaffolding. The lexer task fleshes out the full set of token kinds.
"""

from enum import Enum, auto


class TokenType(Enum):
    EOF = auto()
