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
    ":": TokenType.COLON,
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

_PREFIXED_INT_BASES = {
    "x": (16, "0123456789abcdef"),
    "b": (2, "01"),
    "o": (8, "01234567"),
}


class Lexer:
    def __init__(self, source: str, start_line: int = 1, start_column: int = 1):
        """`start_line`/`start_column` let a `${expr}` placeholder's raw source
        be re-lexed by a fresh `Lexer` whose positions still match the
        original file, so errors inside the placeholder report the right
        line/column instead of restarting at 1:1 (see `Parser._build_interp_string`)."""
        self.source = source
        self.pos = 0
        self.line = start_line
        self.column = start_column
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
            elif char == ".":
                self._dot(start_line, start_col)
            elif char == "?":
                self._question(start_line, start_col)
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
            elif char == "/" and self._peek_next() == "*":
                self._block_comment()
            else:
                break

    def _block_comment(self):
        start_line, start_col = self.line, self.column
        self._advance()  # consume '/'
        self._advance()  # consume '*'
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated block comment",
                    start_line,
                    start_col,
                    unterminated=True,
                )
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()  # consume '*'
                self._advance()  # consume '/'
                break
            self._advance()

    def _string(self, start_line: int, start_col: int):
        start_pos = self.pos - 1  # position of the opening quote
        parts: list = []  # str segments and ("expr", raw, line, col) placeholders
        chars = []
        has_interp = False
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            if self._peek() == '"':
                self._advance()
                break
            if self._peek() == "$" and self._peek_next() == "{":
                has_interp = True
                parts.append("".join(chars))
                chars = []
                self._advance()  # consume '$'
                self._advance()  # consume '{'
                parts.append(self._interp_placeholder(start_line, start_col))
                continue
            char = self._advance()
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
        parts.append("".join(chars))
        lexeme = self.source[start_pos : self.pos]
        if not has_interp:
            self.tokens.append(
                Token(TokenType.STRING, lexeme, parts[0], start_line, start_col)
            )
        else:
            self.tokens.append(
                Token(TokenType.INTERP_STRING, lexeme, parts, start_line, start_col)
            )

    def _interp_placeholder(self, str_start_line: int, str_start_col: int) -> tuple:
        """Scan a `${...}` placeholder's raw expression text, tracking brace
        depth so a nested `{}` (e.g. a map literal) doesn't end it early.
        Quotes inside the expression aren't tracked specially — they're just
        ordinary characters here, so a nested string containing `{`/`}` would
        misparse, but that's not part of this grammar (only brace nesting is)."""
        expr_start_line, expr_start_col = self.line, self.column
        expr_start_pos = self.pos
        depth = 1
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string",
                    str_start_line,
                    str_start_col,
                    unterminated=True,
                )
            char = self._peek()
            if char == "{":
                depth += 1
                self._advance()
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
                self._advance()
            else:
                self._advance()
        expr_text = self.source[expr_start_pos : self.pos]
        self._advance()  # consume closing '}'
        return ("expr", expr_text, expr_start_line, expr_start_col)

    def _number(self, first: str, start_line: int, start_col: int):
        if first == "0" and self._peek().lower() in _PREFIXED_INT_BASES:
            self._prefixed_int(start_line, start_col)
            return

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

    def _prefixed_int(self, start_line: int, start_col: int):
        prefix = self._advance()  # consume 'x'/'b'/'o' (any case)
        base, alphabet = _PREFIXED_INT_BASES[prefix.lower()]
        digits = []
        while self._peek().isalnum():
            char = self._advance()
            if char.lower() not in alphabet:
                raise LexError(
                    f"invalid digit {char!r} in base-{base} literal",
                    start_line,
                    start_col,
                )
            digits.append(char)
        if not digits:
            raise LexError(
                f"expected digits after '0{prefix}'", start_line, start_col
            )
        lexeme = f"0{prefix}{''.join(digits)}"
        value = int("".join(digits), base)
        self.tokens.append(Token(TokenType.INT, lexeme, value, start_line, start_col))

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

    def _dot(self, start_line: int, start_col: int):
        if self._peek() == "." and self._peek_next() == ".":
            self._advance()
            self._advance()
            self.tokens.append(
                Token(TokenType.DOT_DOT_DOT, "...", None, start_line, start_col)
            )
        else:
            self.tokens.append(Token(TokenType.DOT, ".", None, start_line, start_col))

    def _question(self, start_line: int, start_col: int):
        if self._match("?"):
            self.tokens.append(
                Token(TokenType.QUESTION_QUESTION, "??", None, start_line, start_col)
            )
        else:
            self.tokens.append(Token(TokenType.QUESTION, "?", None, start_line, start_col))

    def _gt(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(Token(TokenType.GTEQ, ">=", None, start_line, start_col))
        elif self._match(">"):
            self.tokens.append(Token(TokenType.RSHIFT, ">>", None, start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.GT, ">", None, start_line, start_col))


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
