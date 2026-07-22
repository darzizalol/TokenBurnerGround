"""Lexer: source text -> list[Token]."""

from cinder.errors import LexError
from cinder.tokens import KEYWORDS, Token, TokenType

_SIMPLE_TOKENS = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    ".": TokenType.DOT,
    ":": TokenType.COLON,
    "?": TokenType.QUESTION,
    "&": TokenType.AMP,
    "|": TokenType.PIPE,
    "^": TokenType.CARET,
    "~": TokenType.TILDE,
}

_COMPOUND_ASSIGN_TOKENS = {
    "+": (TokenType.PLUS, TokenType.PLUSEQ),
    "-": (TokenType.MINUS, TokenType.MINUSEQ),
    "*": (TokenType.STAR, TokenType.STAREQ),
    "/": (TokenType.SLASH, TokenType.SLASHEQ),
    "%": (TokenType.PERCENT, TokenType.PERCENTEQ),
}

_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "\\": "\\",
    '"': '"',
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end():
            self._skip_whitespace_and_comments()
            if self._at_end():
                break
            start_line, start_col = self.line, self.column
            char = self._advance()

            if char == '"':
                self._string(start_line, start_col)
            elif char.isdigit():
                self._number(char, start_line, start_col)
            elif char.isalpha() or char == "_":
                self._identifier(char, start_line, start_col)
            elif char in _SIMPLE_TOKENS:
                self.tokens.append(
                    Token(_SIMPLE_TOKENS[char], char, None, start_line, start_col)
                )
            elif char in _COMPOUND_ASSIGN_TOKENS:
                self._op_or_compound_assign(char, start_line, start_col)
            elif char == "=":
                self._equals_or(start_line, start_col)
            elif char == "!":
                self._bang(start_line, start_col)
            elif char == "<":
                self._lt(start_line, start_col)
            elif char == ">":
                self._gt(start_line, start_col)
            else:
                raise LexError(
                    f"unrecognized character {char!r}", start_line, start_col
                )

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.source[self.pos]

    def _peek_next(self) -> str:
        if self.pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.pos + 1]

    def _advance(self) -> str:
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._peek() != expected:
            return False
        self._advance()
        return True

    def _skip_whitespace_and_comments(self):
        while not self._at_end():
            char = self._peek()
            if char in " \t\r\n":
                self._advance()
            elif char == "#":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            else:
                break

    def _string(self, start_line: int, start_col: int):
        start_pos = self.pos - 1  # position of the opening quote
        chars = []
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            char = self._advance()
            if char == '"':
                break
            if char == "\\":
                if self._at_end():
                    raise LexError(
                        "unterminated string",
                        start_line,
                        start_col,
                        unterminated=True,
                    )
                escape = self._advance()
                if escape not in _ESCAPES:
                    raise LexError(
                        f"invalid escape sequence '\\{escape}'", start_line, start_col
                    )
                chars.append(_ESCAPES[escape])
            else:
                chars.append(char)
        lexeme = self.source[start_pos : self.pos]
        self.tokens.append(
            Token(TokenType.STRING, lexeme, "".join(chars), start_line, start_col)
        )

    def _number(self, first: str, start_line: int, start_col: int):
        digits = [first]
        while self._peek().isdigit():
            digits.append(self._advance())

        is_float = False
        if self._peek() == "." and self._peek_next().isdigit():
            is_float = True
            digits.append(self._advance())  # consume '.'
            while self._peek().isdigit():
                digits.append(self._advance())

        lexeme = "".join(digits)
        if is_float:
            self.tokens.append(
                Token(TokenType.FLOAT, lexeme, float(lexeme), start_line, start_col)
            )
        else:
            self.tokens.append(
                Token(TokenType.INT, lexeme, int(lexeme), start_line, start_col)
            )

    def _identifier(self, first: str, start_line: int, start_col: int):
        chars = [first]
        while self._peek().isalnum() or self._peek() == "_":
            chars.append(self._advance())
        lexeme = "".join(chars)
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, lexeme, None, start_line, start_col))

    def _op_or_compound_assign(self, char: str, start_line: int, start_col: int):
        simple_type, compound_type = _COMPOUND_ASSIGN_TOKENS[char]
        if self._match("="):
            lexeme = char + "="
            self.tokens.append(Token(compound_type, lexeme, None, start_line, start_col))
        else:
            self.tokens.append(Token(simple_type, char, None, start_line, start_col))

    def _equals_or(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(Token(TokenType.EQEQ, "==", None, start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.EQ, "=", None, start_line, start_col))

    def _bang(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(
                Token(TokenType.BANGEQ, "!=", None, start_line, start_col)
            )
        else:
            raise LexError("unrecognized character '!'", start_line, start_col)

    def _lt(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(Token(TokenType.LTEQ, "<=", None, start_line, start_col))
        elif self._match("<"):
            self.tokens.append(Token(TokenType.LSHIFT, "<<", None, start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.LT, "<", None, start_line, start_col))

    def _gt(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(Token(TokenType.GTEQ, ">=", None, start_line, start_col))
        elif self._match(">"):
            self.tokens.append(Token(TokenType.RSHIFT, ">>", None, start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.GT, ">", None, start_line, start_col))


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
