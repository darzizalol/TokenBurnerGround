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
    "~": TokenType.TILDE,
}

_COMPOUND_ASSIGN_TOKENS = {
    "+": (TokenType.PLUS, TokenType.PLUSEQ),
    "-": (TokenType.MINUS, TokenType.MINUSEQ),
    "*": (TokenType.STAR, TokenType.STAREQ),
    "/": (TokenType.SLASH, TokenType.SLASHEQ),
    "%": (TokenType.PERCENT, TokenType.PERCENTEQ),
    "&": (TokenType.AMP, TokenType.AMPEQ),
    "|": (TokenType.PIPE, TokenType.PIPEEQ),
    "^": (TokenType.CARET, TokenType.CARETEQ),
}

# Only `+`/`-` get a doubled-character form (`++`/`--`); the other operators
# in `_COMPOUND_ASSIGN_TOKENS` above have no such statement-sugar counterpart.
_INCREMENT_DECREMENT_TOKENS = {
    "+": TokenType.PLUSPLUS,
    "-": TokenType.MINUSMINUS,
}

_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "0": "\0",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "\\": "\\",
    '"': '"',
    "'": "'",
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

            if char == '"' or char == "'":
                if self._peek() == char and self._peek_next() == char:
                    self._advance()
                    self._advance()
                    self._string(start_line, start_col, quote=char, triple=True)
                else:
                    self._string(start_line, start_col, quote=char)
            elif char == "r" and self._peek() in ('"', "'"):
                quote = self._advance()
                self._raw_string(start_line, start_col, quote=quote)
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

    def _string(self, start_line: int, start_col: int, quote: str, triple: bool = False):
        start_pos = self.pos - (3 if triple else 1)  # position of the opening quote(s)
        delimiter = quote * 3 if triple else quote
        parts: list = []  # str segments and ("expr", raw, line, col) placeholders
        chars = []
        has_interp = False
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            if self.source[self.pos : self.pos + len(delimiter)] == delimiter:
                for _ in delimiter:
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
                if escape == "u":
                    chars.append(self._unicode_escape(start_line, start_col))
                elif escape not in _ESCAPES:
                    raise LexError(
                        f"invalid escape sequence '\\{escape}'", start_line, start_col
                    )
                else:
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

    def _unicode_escape(self, start_line: int, start_col: int) -> str:
        digits = []
        for _ in range(4):
            if self._at_end() or self._peek() not in "0123456789abcdefABCDEF":
                raise LexError(
                    "invalid unicode escape sequence, expected 4 hex digits after '\\u'",
                    start_line,
                    start_col,
                )
            digits.append(self._advance())
        return chr(int("".join(digits), 16))

    def _raw_string(self, start_line: int, start_col: int, quote: str):
        start_pos = self.pos - 2  # position of the 'r' prefix
        chars = []
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            if self._peek() == quote:
                self._advance()
                break
            chars.append(self._advance())
        lexeme = self.source[start_pos : self.pos]
        self.tokens.append(
            Token(TokenType.STRING, lexeme, "".join(chars), start_line, start_col)
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
        while self._peek().isdigit() or (
            self._peek() == "_"
            and digits[-1].isdigit()
            and self._peek_next().isdigit()
        ):
            digits.append(self._advance())

        is_float = False
        if self._peek() == "." and self._peek_next().isdigit():
            is_float = True
            digits.append(self._advance())  # consume '.'
            while self._peek().isdigit() or (
                self._peek() == "_"
                and digits[-1].isdigit()
                and self._peek_next().isdigit()
            ):
                digits.append(self._advance())

        if self._peek().lower() == "e" and (
            self._peek_next().isdigit() or self._peek_next() in "+-"
        ):
            is_float = True
            digits.append(self._advance())  # consume 'e'/'E'
            if self._peek() in "+-":
                digits.append(self._advance())  # consume sign
            exponent_start = len(digits)
            while self._peek().isdigit() or (
                self._peek() == "_"
                and digits[-1].isdigit()
                and self._peek_next().isdigit()
            ):
                digits.append(self._advance())
            if len(digits) == exponent_start:
                raise LexError(
                    "expected digits after exponent", start_line, start_col
                )

        lexeme = "".join(digits)
        value_str = "".join(c for c in digits if c != "_")
        if is_float:
            self.tokens.append(
                Token(TokenType.FLOAT, lexeme, float(value_str), start_line, start_col)
            )
        else:
            self.tokens.append(
                Token(TokenType.INT, lexeme, int(value_str), start_line, start_col)
            )

    def _prefixed_int(self, start_line: int, start_col: int):
        prefix = self._advance()  # consume 'x'/'b'/'o' (any case)
        base, alphabet = _PREFIXED_INT_BASES[prefix.lower()]
        digits = []
        while self._peek().isalnum() or (
            self._peek() == "_"
            and digits
            and digits[-1].lower() in alphabet
            and self._peek_next().isalnum()
        ):
            char = self._advance()
            if char == "_":
                digits.append(char)
                continue
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
        value = int("".join(c for c in digits if c != "_"), base)
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
        if char == "*" and self._match("*"):
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.STARSTAREQ, "**=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.STARSTAR, "**", None, start_line, start_col)
                )
            return
        if char == "/" and self._match("/"):
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.SLASHSLASHEQ, "//=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.SLASHSLASH, "//", None, start_line, start_col)
                )
            return
        if char == "|" and self._match(">"):
            self.tokens.append(Token(TokenType.PIPE_ARROW, "|>", None, start_line, start_col))
            return
        if char in _INCREMENT_DECREMENT_TOKENS and self._match(char):
            doubled_type = _INCREMENT_DECREMENT_TOKENS[char]
            self.tokens.append(
                Token(doubled_type, char + char, None, start_line, start_col)
            )
        elif self._match("="):
            lexeme = char + "="
            self.tokens.append(Token(compound_type, lexeme, None, start_line, start_col))
        else:
            self.tokens.append(Token(simple_type, char, None, start_line, start_col))

    def _equals_or(self, start_line: int, start_col: int):
        if self._match(">"):
            self.tokens.append(Token(TokenType.FAT_ARROW, "=>", None, start_line, start_col))
        elif self._match("="):
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
            if self._match(">"):
                self.tokens.append(
                    Token(TokenType.SPACESHIP, "<=>", None, start_line, start_col)
                )
            else:
                self.tokens.append(Token(TokenType.LTEQ, "<=", None, start_line, start_col))
        elif self._match("<"):
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.LSHIFTEQ, "<<=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.LSHIFT, "<<", None, start_line, start_col)
                )
        else:
            self.tokens.append(Token(TokenType.LT, "<", None, start_line, start_col))

    def _dot(self, start_line: int, start_col: int):
        if self._peek() == "." and self._peek_next() == ".":
            self._advance()
            self._advance()
            self.tokens.append(
                Token(TokenType.DOT_DOT_DOT, "...", None, start_line, start_col)
            )
        elif self._peek() == ".":
            self._advance()
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.DOT_DOT_EQ, "..=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.DOT_DOT, "..", None, start_line, start_col)
                )
        else:
            self.tokens.append(Token(TokenType.DOT, ".", None, start_line, start_col))

    def _question(self, start_line: int, start_col: int):
        if self._match("?"):
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.QQEQ, "??=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.QUESTION_QUESTION, "??", None, start_line, start_col)
                )
        elif self._match("."):
            self.tokens.append(
                Token(TokenType.QUESTION_DOT, "?.", None, start_line, start_col)
            )
        else:
            self.tokens.append(Token(TokenType.QUESTION, "?", None, start_line, start_col))

    def _gt(self, start_line: int, start_col: int):
        if self._match("="):
            self.tokens.append(Token(TokenType.GTEQ, ">=", None, start_line, start_col))
        elif self._match(">"):
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.RSHIFTEQ, ">>=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.RSHIFT, ">>", None, start_line, start_col)
                )
        else:
            self.tokens.append(Token(TokenType.GT, ">", None, start_line, start_col))


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
