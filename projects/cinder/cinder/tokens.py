"""Token and TokenType definitions for the Cinder lexer."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    # `"...${expr}..."`; `literal` is a list of `str` (literal segments) and
    # `("expr", raw_source, line, column)` tuples (one per placeholder),
    # interleaved in source order — see `Lexer._string`/`Parser._build_interp_string`.
    INTERP_STRING = auto()
    IDENTIFIER = auto()

    # Keywords
    LET = auto()
    CONST = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    FOR = auto()
    IN = auto()
    AS = auto()
    # Never produced by the lexer/KEYWORDS; synthesized by the parser from
    # adjacent `not`/`in` tokens, mirroring how compound-assign tokens
    # synthesize e.g. `TokenType.PLUS`.
    NOT_IN = auto()
    FN = auto()
    RETURN = auto()
    THROW = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    SWITCH = auto()
    MATCH = auto()
    CASE = auto()
    DEFAULT = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    PLUSPLUS = auto()
    MINUSMINUS = auto()
    STAR = auto()
    STARSTAR = auto()
    STARSTAREQ = auto()
    SLASH = auto()
    SLASHSLASH = auto()
    SLASHSLASHEQ = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    BANGEQ = auto()
    LT = auto()
    LTEQ = auto()
    GT = auto()
    GTEQ = auto()
    SPACESHIP = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    PERCENTEQ = auto()
    AMP = auto()
    PIPE = auto()
    PIPE_ARROW = auto()
    CARET = auto()
    TILDE = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    AMPEQ = auto()
    PIPEEQ = auto()
    CARETEQ = auto()
    LSHIFTEQ = auto()
    RSHIFTEQ = auto()

    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()
    DOT = auto()
    DOT_DOT = auto()
    DOT_DOT_EQ = auto()
    DOT_DOT_DOT = auto()
    COLON = auto()
    QUESTION = auto()
    QUESTION_QUESTION = auto()
    QQEQ = auto()
    QUESTION_DOT = auto()
    FAT_ARROW = auto()

    EOF = auto()


KEYWORDS = {
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "do": TokenType.DO,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "as": TokenType.AS,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "throw": TokenType.THROW,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "switch": TokenType.SWITCH,
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "nil": TokenType.NIL,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int
