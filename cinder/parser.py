"""Recursive-descent parser: token list -> expression/statement AST.

Precedence, loosest to tightest:
    assignment (=, right-assoc) > or > and > comparisons (== != < <= > >=)
    > + - > * / % > unary (- not)
with parenthesized grouping and call expressions binding tightest of all.

Statement grammar: a program is a list of statements, each one of
`let IDENTIFIER = <expr>;` (LetStmt), `{ <statement>* }` (Block),
`if (<expr>) <statement> [else <statement>]` (IfStmt),
`while (<expr>) <statement>` (WhileStmt), or a bare `<expr>;` (ExprStmt).

A leading `{` is ambiguous between a Block and a statement-level MapLiteral
expression (e.g. `{"a": 1};`). `_brace_statement` disambiguates by attempting
a speculative map-literal parse first; empty `{}` is always an (empty) Block.
"""

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    Call,
    Expr,
    ExprStmt,
    FnDecl,
    Grouping,
    Identifier,
    IfStmt,
    Index,
    IndexAssign,
    LetStmt,
    ListLiteral,
    Literal,
    Logical,
    MapLiteral,
    ReturnStmt,
    Stmt,
    Unary,
    WhileStmt,
)
from cinder.errors import ParseError
from cinder.tokens import Token, TokenType

_COMPARISON = {
    TokenType.EQEQ,
    TokenType.BANGEQ,
    TokenType.LT,
    TokenType.LTEQ,
    TokenType.GT,
    TokenType.GTEQ,
}
_TERM = {TokenType.PLUS, TokenType.MINUS}
_FACTOR = {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}
_UNARY = {TokenType.MINUS, TokenType.NOT}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self._fn_depth = 0

    def parse_expression(self) -> Expr:
        expr = self._assignment()
        if not self._check(TokenType.EOF):
            token = self._peek()
            raise ParseError(
                f"expected end of input, found {self._describe(token)}",
                token.line,
                token.column,
            )
        return expr

    def parse_program(self) -> list:
        statements = []
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
        return statements

    def _statement(self) -> Stmt:
        if self._check(TokenType.LET):
            return self._let_statement()
        if self._check(TokenType.LBRACE):
            return self._brace_statement()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._check(TokenType.WHILE):
            return self._while_statement()
        if self._check(TokenType.FN):
            return self._fn_declaration()
        if self._check(TokenType.RETURN):
            return self._return_statement()
        return self._expr_statement()

    def _let_statement(self) -> Stmt:
        let_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'let'")
        self._consume(TokenType.EQ, "'=' after variable name")
        initializer = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        return LetStmt(name_token.lexeme, initializer, let_token.line, let_token.column)

    def _brace_statement(self) -> Stmt:
        # Empty `{}` is always an empty Block, never a map literal.
        if self._peek_next().type == TokenType.RBRACE:
            return self._block()
        start = self.pos
        try:
            expr = self._map_literal()
        except ParseError:
            expr = None
        if expr is not None and self._check(TokenType.SEMICOLON):
            self._advance()  # consume ';'
            return ExprStmt(expr)
        self.pos = start
        return self._block()

    def _block(self) -> Stmt:
        self._advance()  # consume '{'
        statements = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            statements.append(self._statement())
        self._consume(TokenType.RBRACE, "'}' after block")
        return Block(statements)

    def _if_statement(self) -> Stmt:
        if_token = self._advance()
        self._consume(TokenType.LPAREN, "'(' after 'if'")
        condition = self._assignment()
        self._consume(TokenType.RPAREN, "')' after if condition")
        then_branch = self._statement()
        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            else_branch = self._statement()
        return IfStmt(condition, then_branch, else_branch, if_token.line, if_token.column)

    def _while_statement(self) -> Stmt:
        while_token = self._advance()
        self._consume(TokenType.LPAREN, "'(' after 'while'")
        condition = self._assignment()
        self._consume(TokenType.RPAREN, "')' after while condition")
        body = self._statement()
        return WhileStmt(condition, body, while_token.line, while_token.column)

    def _fn_declaration(self) -> Stmt:
        fn_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "function name after 'fn'")
        self._consume(TokenType.LPAREN, "'(' after function name")
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._consume(TokenType.IDENTIFIER, "parameter name").lexeme)
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self._consume(TokenType.IDENTIFIER, "parameter name").lexeme)
        self._consume(TokenType.RPAREN, "')' after parameters")
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before function body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._fn_depth += 1
        body = self._block()
        self._fn_depth -= 1
        return FnDecl(name_token.lexeme, params, body, fn_token.line, fn_token.column)

    def _return_statement(self) -> Stmt:
        return_token = self._advance()
        if self._fn_depth == 0:
            raise ParseError(
                "'return' outside of a function", return_token.line, return_token.column
            )
        value = None
        if not self._check(TokenType.SEMICOLON):
            value = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after return statement")
        return ReturnStmt(value, return_token.line, return_token.column)

    def _expr_statement(self) -> Stmt:
        expr = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after expression")
        return ExprStmt(expr)

    def _assignment(self) -> Expr:
        expr = self._or()
        if self._check(TokenType.EQ):
            eq_token = self._advance()
            value = self._assignment()
            if isinstance(expr, Identifier):
                return Assign(expr.name, value, eq_token.line, eq_token.column)
            if isinstance(expr, Index):
                return IndexAssign(
                    expr.obj, expr.index, value, eq_token.line, eq_token.column
                )
            raise ParseError(
                "invalid assignment target", eq_token.line, eq_token.column
            )
        return expr

    def _or(self) -> Expr:
        expr = self._and()
        while self._check(TokenType.OR):
            operator = self._advance()
            right = self._and()
            expr = Logical(expr, operator, right)
        return expr

    def _and(self) -> Expr:
        expr = self._comparison()
        while self._check(TokenType.AND):
            operator = self._advance()
            right = self._comparison()
            expr = Logical(expr, operator, right)
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._peek().type in _COMPARISON:
            operator = self._advance()
            right = self._term()
            expr = Binary(expr, operator, right)
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._peek().type in _TERM:
            operator = self._advance()
            right = self._factor()
            expr = Binary(expr, operator, right)
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._peek().type in _FACTOR:
            operator = self._advance()
            right = self._unary()
            expr = Binary(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._peek().type in _UNARY:
            operator = self._advance()
            operand = self._unary()
            return Unary(operator, operand)
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()
        while True:
            if self._check(TokenType.LPAREN):
                self._advance()
                expr = self._finish_call(expr)
            elif self._check(TokenType.LBRACKET):
                expr = self._finish_index(expr)
            else:
                break
        return expr

    def _finish_call(self, callee: Expr) -> Expr:
        paren = self._previous()
        arguments = []
        if not self._check(TokenType.RPAREN):
            arguments.append(self._or())
            while self._check(TokenType.COMMA):
                self._advance()
                arguments.append(self._or())
        self._consume(TokenType.RPAREN, "')' after arguments")
        return Call(callee, arguments, paren.line, paren.column)

    def _finish_index(self, obj: Expr) -> Expr:
        bracket = self._advance()  # consume '['
        index = self._or()
        self._consume(TokenType.RBRACKET, "']' after index")
        return Index(obj, index, bracket.line, bracket.column)

    def _primary(self) -> Expr:
        token = self._peek()

        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column)
        if token.type == TokenType.TRUE:
            self._advance()
            return Literal(True, token.line, token.column)
        if token.type == TokenType.FALSE:
            self._advance()
            return Literal(False, token.line, token.column)
        if token.type == TokenType.NIL:
            self._advance()
            return Literal(None, token.line, token.column)
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(token.lexeme, token.line, token.column)
        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._assignment()
            self._consume(TokenType.RPAREN, "')' after expression")
            return Grouping(expr)
        if token.type == TokenType.LBRACKET:
            return self._list_literal()
        if token.type == TokenType.LBRACE:
            return self._map_literal()

        raise ParseError(
            f"expected an expression, found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _list_literal(self) -> Expr:
        bracket = self._advance()  # consume '['
        elements = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._or())
            while self._check(TokenType.COMMA):
                self._advance()
                elements.append(self._or())
        self._consume(TokenType.RBRACKET, "']' after list literal")
        return ListLiteral(elements, bracket.line, bracket.column)

    def _map_literal(self) -> Expr:
        brace = self._advance()  # consume '{'
        pairs = []
        if not self._check(TokenType.RBRACE):
            pairs.append(self._map_pair())
            while self._check(TokenType.COMMA):
                self._advance()
                pairs.append(self._map_pair())
        self._consume(TokenType.RBRACE, "'}' after map literal")
        return MapLiteral(pairs, brace.line, brace.column)

    def _map_pair(self) -> tuple:
        key = self._or()
        self._consume(TokenType.COLON, "':' after map key")
        value = self._or()
        return (key, value)

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _peek_next(self) -> Token:
        idx = min(self.pos + 1, len(self.tokens) - 1)
        return self.tokens[idx]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def _check(self, type_: TokenType) -> bool:
        return self._peek().type == type_

    def _consume(self, type_: TokenType, expected: str) -> Token:
        if self._check(type_):
            return self._advance()
        token = self._peek()
        raise ParseError(
            f"expected {expected}, found {self._describe(token)}",
            token.line,
            token.column,
        )

    @staticmethod
    def _describe(token: Token) -> str:
        if token.type == TokenType.EOF:
            return "end of input"
        return repr(token.lexeme)


def parse_expression(tokens: list[Token]) -> Expr:
    return Parser(tokens).parse_expression()


def parse_program(tokens: list[Token]) -> list:
    return Parser(tokens).parse_program()
