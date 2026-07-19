"""Recursive-descent parser: token list -> expression/statement AST.

Precedence, loosest to tightest:
    assignment (=, right-assoc) > or > and > comparisons (== != < <= > >=)
    > + - > * / % > unary (- not)
with parenthesized grouping and call expressions binding tightest of all.

Statement grammar: a program is a list of statements, each one of
`let IDENTIFIER = <expr>;` (LetStmt), `{ <statement>* }` (Block),
`if (<expr>) <statement> [else <statement>]` (IfStmt),
`while (<expr>) <statement>` (WhileStmt), or a bare `<expr>;` (ExprStmt).
"""

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    Call,
    Expr,
    ExprStmt,
    Grouping,
    Identifier,
    IfStmt,
    LetStmt,
    Literal,
    Logical,
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
            return self._block()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._check(TokenType.WHILE):
            return self._while_statement()
        return self._expr_statement()

    def _let_statement(self) -> Stmt:
        let_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'let'")
        self._consume(TokenType.EQ, "'=' after variable name")
        initializer = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        return LetStmt(name_token.lexeme, initializer, let_token.line, let_token.column)

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
        while self._check(TokenType.LPAREN):
            self._advance()
            expr = self._finish_call(expr)
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

        raise ParseError(
            f"expected an expression, found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _peek(self) -> Token:
        return self.tokens[self.pos]

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
