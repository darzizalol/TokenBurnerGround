"""Recursive-descent parser: token list -> expression/statement AST.

Precedence, loosest to tightest:
    assignment (=, +=, -=, *=, /=, %=, right-assoc) > ternary (?:, right-assoc)
    > or > and > in > comparisons (== != < <= > >=) > | > ^ > & > << >> >
    + - > * / % > unary (- not ~)
with parenthesized grouping and call expressions binding tightest of all.

Compound assignment (`x += 1`) is desugared at parse time into `x = x + 1`
(reusing the `Binary`/`Assign` AST nodes, restricted to `Identifier` targets
like plain `=`) rather than adding dedicated interpreter support.

Statement grammar: a program is a list of statements, each one of
`let IDENTIFIER = <expr>;` (LetStmt), `{ <statement>* }` (Block),
`if (<expr>) <statement> [else <statement>]` (IfStmt),
`while (<expr>) <statement>` (WhileStmt), `for IDENTIFIER in <expr> { ... }`
(ForStmt, body always a block), `break;`/`continue;` (BreakStmt/ContinueStmt,
only valid inside a loop), `try { <statement>* } catch (IDENTIFIER)
{ <statement>* }` (TryStmt, both bodies always blocks, the parenthesized
catch name is required), or a bare `<expr>;` (ExprStmt).

`fn` at statement position (`fn NAME(params) { body }`) is a named `FnDecl`;
`fn` anywhere else in the expression grammar (`_primary`) is an anonymous
`FnExpr` function literal usable as a value, e.g. passed straight to a
callback-taking builtin like `map`/`filter` or bound with `let`. Both share
parameter/body parsing via `_fn_params_and_body`.

A leading `{` is ambiguous between a Block and a statement-level expression
rooted in a MapLiteral (e.g. `{"a": 1};`, `{"a": 1}["a"];`). `_brace_statement`
disambiguates by attempting a speculative full-expression parse first (so
postfix indexing/calls and binary operators on the leading map literal are
captured too); empty `{}` is always an (empty) Block.

`_loop_depth` tracks loop nesting the same way `_fn_depth` tracks function
nesting for `return`: `break`/`continue` outside any loop is a `ParseError`.
Entering a function body resets `_loop_depth` to 0 (saved/restored around the
body) so a bare `break`/`continue` inside a function nested in a loop is
still rejected unless that function has its own enclosing loop — mirroring
how `return` is scoped to the nearest function, not any outer one.
"""

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    BreakStmt,
    Call,
    ContinueStmt,
    Expr,
    ExprStmt,
    FnDecl,
    FnExpr,
    ForStmt,
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
    SliceExpr,
    Stmt,
    Ternary,
    TryStmt,
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
_UNARY = {TokenType.MINUS, TokenType.NOT, TokenType.TILDE}
_BITSHIFT = {TokenType.LSHIFT, TokenType.RSHIFT}
_COMPOUND_ASSIGN_OPS = {
    TokenType.PLUSEQ: TokenType.PLUS,
    TokenType.MINUSEQ: TokenType.MINUS,
    TokenType.STAREQ: TokenType.STAR,
    TokenType.SLASHEQ: TokenType.SLASH,
    TokenType.PERCENTEQ: TokenType.PERCENT,
}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self._fn_depth = 0
        self._loop_depth = 0

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
        if self._check(TokenType.FOR):
            return self._for_statement()
        if self._check(TokenType.FN):
            return self._fn_declaration()
        if self._check(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.BREAK):
            return self._break_statement()
        if self._check(TokenType.CONTINUE):
            return self._continue_statement()
        if self._check(TokenType.TRY):
            return self._try_statement()
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
            expr = self._assignment()
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
        self._loop_depth += 1
        body = self._statement()
        self._loop_depth -= 1
        return WhileStmt(condition, body, while_token.line, while_token.column)

    def _for_statement(self) -> Stmt:
        for_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'for'")
        self._consume(TokenType.IN, "'in' after for-loop variable")
        iterable = self._assignment()
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before for-loop body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._loop_depth += 1
        body = self._block()
        self._loop_depth -= 1
        return ForStmt(
            name_token.lexeme, iterable, body, for_token.line, for_token.column
        )

    def _fn_declaration(self) -> Stmt:
        fn_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "function name after 'fn'")
        params, body = self._fn_params_and_body()
        return FnDecl(name_token.lexeme, params, body, fn_token.line, fn_token.column)

    def _fn_expression(self) -> Expr:
        fn_token = self._advance()
        params, body = self._fn_params_and_body()
        return FnExpr(params, body, fn_token.line, fn_token.column)

    def _fn_params_and_body(self) -> tuple:
        self._consume(TokenType.LPAREN, "'(' after 'fn'")
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
        outer_loop_depth = self._loop_depth
        self._loop_depth = 0
        body = self._block()
        self._loop_depth = outer_loop_depth
        self._fn_depth -= 1
        return params, body

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

    def _break_statement(self) -> Stmt:
        break_token = self._advance()
        if self._loop_depth == 0:
            raise ParseError(
                "'break' outside of a loop", break_token.line, break_token.column
            )
        self._consume(TokenType.SEMICOLON, "';' after 'break'")
        return BreakStmt(break_token.line, break_token.column)

    def _continue_statement(self) -> Stmt:
        continue_token = self._advance()
        if self._loop_depth == 0:
            raise ParseError(
                "'continue' outside of a loop", continue_token.line, continue_token.column
            )
        self._consume(TokenType.SEMICOLON, "';' after 'continue'")
        return ContinueStmt(continue_token.line, continue_token.column)

    def _try_statement(self) -> Stmt:
        try_token = self._advance()
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before try body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        try_block = self._block()
        self._consume(TokenType.CATCH, "'catch' after try block")
        self._consume(TokenType.LPAREN, "'(' after 'catch'")
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'catch ('")
        self._consume(TokenType.RPAREN, "')' after catch name")
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before catch body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        catch_block = self._block()
        return TryStmt(
            try_block, name_token.lexeme, catch_block, try_token.line, try_token.column
        )

    def _expr_statement(self) -> Stmt:
        expr = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after expression")
        return ExprStmt(expr)

    def _assignment(self) -> Expr:
        expr = self._ternary()
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
        if self._peek().type in _COMPOUND_ASSIGN_OPS:
            op_token = self._advance()
            value = self._assignment()
            if not isinstance(expr, Identifier):
                raise ParseError(
                    "invalid assignment target", op_token.line, op_token.column
                )
            binary_operator = Token(
                _COMPOUND_ASSIGN_OPS[op_token.type],
                op_token.lexeme[0],
                None,
                op_token.line,
                op_token.column,
            )
            binary = Binary(expr, binary_operator, value)
            return Assign(expr.name, binary, op_token.line, op_token.column)
        return expr

    def _ternary(self) -> Expr:
        expr = self._or()
        if self._check(TokenType.QUESTION):
            question_token = self._advance()
            then_expr = self._ternary()
            self._consume(TokenType.COLON, "':' in ternary expression")
            else_expr = self._ternary()
            return Ternary(
                expr, then_expr, else_expr, question_token.line, question_token.column
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
        expr = self._membership()
        while self._check(TokenType.AND):
            operator = self._advance()
            right = self._membership()
            expr = Logical(expr, operator, right)
        return expr

    def _membership(self) -> Expr:
        expr = self._comparison()
        while self._check(TokenType.IN):
            operator = self._advance()
            right = self._comparison()
            expr = Binary(expr, operator, right)
        return expr

    def _comparison(self) -> Expr:
        expr = self._bitor()
        while self._peek().type in _COMPARISON:
            operator = self._advance()
            right = self._bitor()
            expr = Binary(expr, operator, right)
        return expr

    def _bitor(self) -> Expr:
        expr = self._bitxor()
        while self._check(TokenType.PIPE):
            operator = self._advance()
            right = self._bitxor()
            expr = Binary(expr, operator, right)
        return expr

    def _bitxor(self) -> Expr:
        expr = self._bitand()
        while self._check(TokenType.CARET):
            operator = self._advance()
            right = self._bitand()
            expr = Binary(expr, operator, right)
        return expr

    def _bitand(self) -> Expr:
        expr = self._bitshift()
        while self._check(TokenType.AMP):
            operator = self._advance()
            right = self._bitshift()
            expr = Binary(expr, operator, right)
        return expr

    def _bitshift(self) -> Expr:
        expr = self._term()
        while self._peek().type in _BITSHIFT:
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
            arguments.append(self._ternary())
            while self._check(TokenType.COMMA):
                self._advance()
                arguments.append(self._ternary())
        self._consume(TokenType.RPAREN, "')' after arguments")
        return Call(callee, arguments, paren.line, paren.column)

    def _finish_index(self, obj: Expr) -> Expr:
        bracket = self._advance()  # consume '['
        start = None
        if not self._check(TokenType.COLON):
            start = self._ternary()
        if self._check(TokenType.COLON):
            self._advance()
            end = None
            if not self._check(TokenType.RBRACKET):
                end = self._ternary()
            self._consume(TokenType.RBRACKET, "']' after slice")
            return SliceExpr(obj, start, end, bracket.line, bracket.column)
        self._consume(TokenType.RBRACKET, "']' after index")
        return Index(obj, start, bracket.line, bracket.column)

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
        if token.type == TokenType.FN:
            return self._fn_expression()

        raise ParseError(
            f"expected an expression, found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _list_literal(self) -> Expr:
        bracket = self._advance()  # consume '['
        elements = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._ternary())
            while self._check(TokenType.COMMA):
                self._advance()
                elements.append(self._ternary())
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
        value = self._ternary()
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
