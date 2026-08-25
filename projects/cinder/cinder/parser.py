"""Recursive-descent parser: token list -> expression/statement AST.

Precedence, loosest to tightest:
    assignment (=, +=, -=, *=, /=, %=, &=, |=, ^=, <<=, >>=, right-assoc)
    > ternary (?:, right-assoc)
    > ?? (nullish-coalescing, right-assoc) > or > and > in / not in
    > comparisons (== != < <= > >=) > | > ^ > & > << >> >
    + - > * / % > unary (- + not ~)
with parenthesized grouping and call expressions binding tightest of all.

`??` reuses the `Logical` AST node (like `and`/`or`) since it also
short-circuits: `a ?? b` evaluates `b` only when `a` is `nil`, never for any
other falsy value (`0`, `""`, `false`).

Compound assignment (`x += 1`) is desugared at parse time into `x = x + 1`
(reusing the `Binary`/`Assign` AST nodes) rather than adding dedicated
interpreter support. Both the arithmetic set (`+=` `-=` `*=` `/=` `%=`) and
the bitwise/shift set (`&=` `|=` `^=` `<<=` `>>=`) accept an `Identifier`
target or an `Index` target (which includes dot access, e.g. `m.key`,
since it desugars into the same `Index` node as `m["key"]`); an `Index`
target desugars into a dedicated `IndexCompoundAssign` node (not
`IndexAssign` wrapping a `Binary` over the same `Index` node — that would
evaluate the object/index sub-expressions twice) so `obj`/`index` are each
evaluated exactly once at runtime and their values reused for both the
read and the write.

`x++`/`x--` desugar into `x += 1`/`x -= 1` (evaluating to the new,
post-increment value, like every other compound-assign operator) and are
recognized directly in `_assignment`, so they're reachable from any
expression context an ordinary assignment is: a `let` initializer, the RHS
of a chained assignment, or a parenthesized sub-expression — while still
staying at assignment-level precedence and reachability, e.g. `print(x++)`
is still a `ParseError`, matching `print(x = 5)`. Like the bitwise/shift
compound-assign set, both an `Identifier` and an `Index` target are
accepted, the latter via `IndexCompoundAssign` for the same
single-evaluation reason. The lexer's doubled-`-` lookahead means
`--5` (prefix double negation, no space) now lexes as one `MINUSMINUS`
token instead of two `MINUS`; `_unary` re-splits it back into nested
`Unary(MINUS, ...)` nodes since a leading `--` can never be a postfix
decrement (there's nothing before it to decrement). `++5` gets the
identical treatment via `PLUSPLUS`, re-split into nested
`Unary(PLUS, ...)` nodes, for the same reason.

Statement grammar: a program is a list of statements, each one of
`let IDENTIFIER = <expr>;` (LetStmt), `let [IDENTIFIER, ...] = <expr>;` or
`let {IDENTIFIER, ...} = <expr>;` (DestructureLetStmt, a flat positional
list pattern or a flat shorthand map pattern — `is_map` distinguishes the
two), `{ <statement>* }` (Block),
`if (<expr>) <statement> [else <statement>]` (IfStmt),
`while (<expr>) <statement>` (WhileStmt), `for IDENTIFIER in <expr> { ... }`
(ForStmt, body always a block), `for (init; cond; step) { ... }` (ForCStmt,
disambiguated from the foreach form by peeking for `(` right after `for`;
`init`/`cond`/`step` are each independently optional), `break;`/`continue;`
(BreakStmt/ContinueStmt,
only valid inside a loop), `try { <statement>* } catch (IDENTIFIER)
{ <statement>* }` (TryStmt, both bodies always blocks, the parenthesized
catch name is required), `switch (<expr>) { case <expr>: { ... } ...
[default: { ... }] }` (SwitchStmt, each case/default body always a block; at
most one `default`, checked at parse time), or a bare `<expr>;` (ExprStmt).

`fn` at statement position (`fn NAME(params) { body }`) is a named `FnDecl`;
`fn` anywhere else in the expression grammar (`_primary`) is an anonymous
`FnExpr` function literal usable as a value, e.g. passed straight to a
callback-taking builtin like `map`/`filter` or bound with `let`. Both share
parameter/body parsing via `_fn_params_and_body`.

A parameter may carry a default value (`fn f(a, b = 1) { ... }`), parsed by
`_fn_param` at ternary precedence (the same tier `_map_pair`'s value and
`_list_literal`'s elements use — a bare `,` at that precedence still ends the
parameter, so parsing the full comma-containing assignment grammar here would
be ambiguous with the next parameter). Once one parameter has a default,
every parameter after it must too; `_fn_param` raises `ParseError` at the
first offending parameter otherwise.

A function may also declare a single trailing rest parameter
(`fn f(a, ...rest) { ... }`), reusing the spread operator's `DOT_DOT_DOT`
token from `cinder/tokens.py`. `_fn_params_and_body` parses it as
`rest_param` (a bare `str | None`, separate from `params`) and requires it
to be the last parameter — a `,` after it (another parameter or a second
`...rest`) raises `ParseError`. It may follow default parameters.

A leading `{` is ambiguous between a Block and a statement-level expression
rooted in a MapLiteral (e.g. `{"a": 1};`, `{"a": 1}["a"];`). `_brace_statement`
disambiguates by attempting a speculative full-expression parse first (so
postfix indexing/calls and binary operators on the leading map literal are
captured too); empty `{}` is always an (empty) Block.

`_loop_labels` tracks loop nesting the same way `_fn_depth` tracks function
nesting for `return`: `break`/`continue` outside any loop is a `ParseError`.
It's a `list[str | None]` rather than a plain counter — one entry per
enclosing loop, `None` for an unlabeled loop or the loop's label string —
so a labeled `break`/`continue` can be validated against the full set of
enclosing labels, not just a depth count. Entering a function body resets
`_loop_labels` to `[]` (saved/restored around the body) so a bare
`break`/`continue` inside a function nested in a loop is still rejected
unless that function has its own enclosing loop — mirroring how `return`
is scoped to the nearest function, not any outer one.

A label (`outer: while (...) { ... }`) is a plain `IDENTIFIER` followed by
`:` immediately before one of `while`/`do`/`for` at statement position — no
new token type needed. `_statement`'s dispatcher peeks two tokens ahead for
this shape before falling into the normal statement dispatch (an
identifier followed by `:` never starts a valid expression statement today,
so there's no ambiguity to resolve). `break`/`continue` optionally consume
a trailing `IDENTIFIER` naming the loop to target; a name that doesn't
match any label currently on `_loop_labels` is a `ParseError` at the name's
own position.
"""

from cinder.ast_nodes import (
    Assign,
    Binary,
    Block,
    BreakStmt,
    Call,
    ChainedComparison,
    ComprehensionClause,
    ConstStmt,
    ContinueStmt,
    DeclSeq,
    DestructureAssign,
    DestructureLetStmt,
    DoWhileStmt,
    Expr,
    ExprStmt,
    FnDecl,
    FnExpr,
    ForCStmt,
    ForStmt,
    Grouping,
    Identifier,
    IfStmt,
    Index,
    IndexAssign,
    IndexCompoundAssign,
    IndexNilCoalesceAssign,
    InterpString,
    KeywordArg,
    LetStmt,
    ListComprehension,
    ListLiteral,
    Literal,
    Logical,
    MapComprehension,
    MapLiteral,
    MatchArm,
    MatchExpr,
    OptionalCall,
    OptionalIndex,
    Param,
    RangeExpr,
    ReturnStmt,
    SliceAssign,
    SliceExpr,
    Spread,
    Stmt,
    SwitchCase,
    SwitchStmt,
    Ternary,
    ThrowStmt,
    TryStmt,
    Unary,
    WhileStmt,
)
from cinder.errors import ParseError
from cinder.lexer import Lexer
from cinder.tokens import Token, TokenType

_COMPARISON = {
    TokenType.EQEQ,
    TokenType.BANGEQ,
    TokenType.LT,
    TokenType.LTEQ,
    TokenType.GT,
    TokenType.GTEQ,
}
_ORDERING = {
    TokenType.LT,
    TokenType.LTEQ,
    TokenType.GT,
    TokenType.GTEQ,
}
_TERM = {TokenType.PLUS, TokenType.MINUS}
_FACTOR = {TokenType.STAR, TokenType.SLASH, TokenType.SLASHSLASH, TokenType.PERCENT}
_UNARY = {TokenType.MINUS, TokenType.PLUS, TokenType.NOT, TokenType.TILDE}
_BITSHIFT = {TokenType.LSHIFT, TokenType.RSHIFT}
_COMPOUND_ASSIGN_OPS = {
    TokenType.PLUSEQ: TokenType.PLUS,
    TokenType.MINUSEQ: TokenType.MINUS,
    TokenType.STAREQ: TokenType.STAR,
    TokenType.STARSTAREQ: TokenType.STARSTAR,
    TokenType.SLASHEQ: TokenType.SLASH,
    TokenType.SLASHSLASHEQ: TokenType.SLASHSLASH,
    TokenType.PERCENTEQ: TokenType.PERCENT,
    TokenType.AMPEQ: TokenType.AMP,
    TokenType.PIPEEQ: TokenType.PIPE,
    TokenType.CARETEQ: TokenType.CARET,
    TokenType.LSHIFTEQ: TokenType.LSHIFT,
    TokenType.RSHIFTEQ: TokenType.RSHIFT,
}
# Both the arithmetic and bitwise/shift compound-assign ops accept an
# index-expression target (which includes dot access, since `m.key`
# desugars into `Index(obj, Literal("key"))` at parse time) in addition to
# a plain identifier target.
_INDEX_TARGET_COMPOUND_ASSIGN_OPS = {
    TokenType.PLUSEQ,
    TokenType.MINUSEQ,
    TokenType.STAREQ,
    TokenType.STARSTAREQ,
    TokenType.SLASHEQ,
    TokenType.SLASHSLASHEQ,
    TokenType.PERCENTEQ,
    TokenType.AMPEQ,
    TokenType.PIPEEQ,
    TokenType.CARETEQ,
    TokenType.LSHIFTEQ,
    TokenType.RSHIFTEQ,
}
# `x++`/`x--` desugar into `x += 1`/`x -= 1`: unlike the
# arithmetic compound-assign ops above, these accept both `Identifier` and
# `Index` targets (an `Index` target desugars into `IndexCompoundAssign`,
# same as the bitwise/shift compound-assign ops, to evaluate `obj`/`index`
# only once).
_INCREMENT_DECREMENT_OPS = {
    TokenType.PLUSPLUS: TokenType.PLUS,
    TokenType.MINUSMINUS: TokenType.MINUS,
}
_LOOP_KEYWORDS = {TokenType.WHILE, TokenType.DO, TokenType.FOR}


class _RestNotLast(Exception):
    """Internal marker: a `...rest` wasn't the last element of a
    speculatively-parsed map-destructuring assignment pattern. Deliberately
    not a `ParseError` subclass so it can't be caught by the shape-mismatch
    `except ParseError` in `Parser._try_map_destructure_assign_statement`."""

    def __init__(self, token: Token):
        self.token = token


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self._fn_depth = 0
        self._loop_labels: list = []

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
        if (
            self._check(TokenType.IDENTIFIER)
            and self._peek_next().type == TokenType.COLON
            and self._peek_at(2).type in _LOOP_KEYWORDS
        ):
            return self._labeled_loop_statement()
        if self._check(TokenType.LET):
            return self._let_statement()
        if self._check(TokenType.CONST):
            return self._const_statement()
        if self._check(TokenType.LBRACE):
            return self._brace_statement()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._check(TokenType.WHILE):
            return self._while_statement()
        if self._check(TokenType.DO):
            return self._do_while_statement()
        if self._check(TokenType.FOR):
            return self._for_statement()
        if self._check(TokenType.FN):
            return self._fn_declaration()
        if self._check(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.THROW):
            return self._throw_statement()
        if self._check(TokenType.BREAK):
            return self._break_statement()
        if self._check(TokenType.CONTINUE):
            return self._continue_statement()
        if self._check(TokenType.TRY):
            return self._try_statement()
        if self._check(TokenType.SWITCH):
            return self._switch_statement()
        return self._expr_statement()

    def _let_statement(self) -> Stmt:
        let_token = self._advance()
        if self._check(TokenType.LBRACKET):
            return self._destructure_let_statement(let_token, is_map=False)
        if self._check(TokenType.LBRACE):
            return self._destructure_let_statement(let_token, is_map=True)
        declarations = [self._one_let_declaration(let_token)]
        while self._check(TokenType.COMMA):
            self._advance()
            declarations.append(self._one_let_declaration(let_token))
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        if len(declarations) == 1:
            return declarations[0]
        return DeclSeq(declarations, let_token.line, let_token.column)

    def _one_let_declaration(self, let_token: Token) -> LetStmt:
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'let'")
        if self._check(TokenType.SEMICOLON) or self._check(TokenType.COMMA):
            initializer: Expr = Literal(None, name_token.line, name_token.column)
        else:
            self._consume(TokenType.EQ, "'=' after variable name")
            initializer = self._assignment()
        return LetStmt(name_token.lexeme, initializer, name_token.line, name_token.column)

    def _const_statement(self) -> Stmt:
        const_token = self._advance()
        declarations = [self._one_const_declaration(const_token)]
        while self._check(TokenType.COMMA):
            self._advance()
            declarations.append(self._one_const_declaration(const_token))
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        if len(declarations) == 1:
            return declarations[0]
        return DeclSeq(declarations, const_token.line, const_token.column)

    def _one_const_declaration(self, const_token: Token) -> ConstStmt:
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'const'")
        self._consume(TokenType.EQ, "'=' after variable name")
        initializer = self._assignment()
        return ConstStmt(name_token.lexeme, initializer, name_token.line, name_token.column)

    def _destructure_let_statement(self, let_token: Token, is_map: bool) -> Stmt:
        if is_map:
            names, rest = self._destructure_map_pattern()
        else:
            names, rest = self._destructure_list_pattern()
        self._consume(TokenType.EQ, "'=' after destructuring pattern")
        initializer = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        return DestructureLetStmt(names, initializer, let_token.line, let_token.column, is_map=is_map, rest=rest)

    def _destructure_map_pattern_entry(self) -> "tuple[str, object, Expr | None]":
        key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
        if self._check(TokenType.COLON):
            self._advance()
            if self._check(TokenType.LBRACE):
                nested_names, nested_rest = self._destructure_map_pattern()
                binding = (nested_names, nested_rest)
            elif self._check(TokenType.LBRACKET):
                nested_names, nested_rest = self._destructure_list_pattern()
                binding = (nested_names, nested_rest, True)
            else:
                binding = self._consume(
                    TokenType.IDENTIFIER, "identifier in destructuring pattern"
                ).lexeme
        else:
            binding = key
        default = None
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
        return key, binding, default

    def _destructure_map_pattern(self) -> "tuple[list, str | None]":
        self._advance()  # consume '{'
        names = []
        rest = None
        if self._check(TokenType.DOT_DOT_DOT):
            rest = self._destructure_rest_name()
        else:
            names.append(self._destructure_map_pattern_entry())
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACE):
                break
            if rest is not None:
                token = self._peek()
                raise ParseError(
                    f"rest element must be last in destructuring pattern, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._destructure_rest_name()
            else:
                names.append(self._destructure_map_pattern_entry())
        self._consume(TokenType.RBRACE, "'}' after destructuring pattern")
        return names, rest

    def _destructure_list_pattern_entry(self, seen_default: bool) -> "tuple[str | None, Expr | None]":
        if self._check(TokenType.COMMA):
            if seen_default:
                token = self._peek()
                raise ParseError(
                    "element without a default value follows an element with one "
                    "in destructuring pattern",
                    token.line,
                    token.column,
                )
            return None, None
        if self._check(TokenType.LBRACKET):
            nested_names, nested_rest = self._destructure_list_pattern()
            pattern = (nested_names, nested_rest)
            if self._check(TokenType.EQ):
                self._advance()
                default = self._ternary()
                return pattern, default
            if seen_default:
                token = self._peek()
                raise ParseError(
                    "element without a default value follows an element with one "
                    "in destructuring pattern",
                    token.line,
                    token.column,
                )
            return pattern, None
        if self._check(TokenType.LBRACE):
            nested_names, nested_rest = self._destructure_map_pattern()
            pattern = (nested_names, nested_rest, True)
            if self._check(TokenType.EQ):
                self._advance()
                default = self._ternary()
                return pattern, default
            if seen_default:
                token = self._peek()
                raise ParseError(
                    "element without a default value follows an element with one "
                    "in destructuring pattern",
                    token.line,
                    token.column,
                )
            return pattern, None
        name_token = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern")
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
            return name_token.lexeme, default
        if seen_default:
            raise ParseError(
                "element without a default value follows an element with one "
                "in destructuring pattern",
                name_token.line,
                name_token.column,
            )
        return name_token.lexeme, None

    def _destructure_list_pattern(self) -> "tuple[list, str | None]":
        self._advance()  # consume '['
        names = []
        rest = None
        seen_default = False
        if self._check(TokenType.DOT_DOT_DOT):
            rest = self._destructure_rest_name()
        else:
            names.append(self._destructure_list_pattern_entry(seen_default))
            seen_default = names[-1][1] is not None
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACKET):
                break
            if rest is not None:
                token = self._peek()
                raise ParseError(
                    f"rest element must be last in destructuring pattern, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._destructure_rest_name()
            else:
                names.append(self._destructure_list_pattern_entry(seen_default))
                seen_default = seen_default or names[-1][1] is not None
        self._consume(TokenType.RBRACKET, "']' after destructuring pattern")
        return names, rest

    def _destructure_assign_pattern(
        self, list_literal: ListLiteral, eq_token: Token
    ) -> "tuple[list, str | None]":
        """Validate a `ListLiteral` already parsed on the LHS of `=` as a flat
        assignment-destructuring pattern (same shape `_destructure_list_pattern`
        enforces for `let`: plain identifiers, optionally a trailing
        `...identifier` rest). Any other shape is the existing invalid
        assignment target error, reported at the `=` token like every other
        invalid target."""

        elements = list_literal.elements
        if not elements:
            raise ParseError(
                "invalid assignment target", eq_token.line, eq_token.column
            )
        names = []
        rest = None
        for index, element in enumerate(elements):
            is_last = index == len(elements) - 1
            if isinstance(element, Spread):
                if not is_last or not isinstance(element.expression, Identifier):
                    raise ParseError(
                        "invalid assignment target", eq_token.line, eq_token.column
                    )
                rest = element.expression.name
            elif isinstance(element, Identifier):
                names.append((element.name, None))
            elif isinstance(element, ListLiteral):
                nested_names, nested_rest = self._destructure_assign_pattern(element, eq_token)
                names.append(((nested_names, nested_rest), None))
            else:
                raise ParseError(
                    "invalid assignment target", eq_token.line, eq_token.column
                )
        return names, rest

    def _destructure_rest_name(self) -> str:
        self._advance()  # DOT_DOT_DOT
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after '...' in destructuring pattern")
        return name_token.lexeme

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
        destructure_assign = self._try_map_destructure_assign_statement()
        if destructure_assign is not None:
            return destructure_assign
        self.pos = start
        return self._block()

    def _try_map_destructure_assign_statement(self) -> "Stmt | None":
        """Speculatively parses `{a, b} = expr;` (optionally with a trailing
        `...rest`) as a map-pattern assignment-destructure, tried after the
        map-literal-expression attempt in `_brace_statement` fails (or isn't
        followed by `;`) and before falling back to `_block()`. Returns
        `None` — leaving `self.pos` untouched for the caller to reset — on
        any shape mismatch (a non-identifier pattern element, or no `=`
        after the closing `}`), so `{1, 2};` and the like keep failing
        exactly as before via the `_block()` fallback.

        A rest element that isn't last is a real syntax error, not a shape
        mismatch: it's raised eagerly, as soon as the second element after
        `rest` is seen, via a marker exception distinct from `ParseError` so
        this function's own catch-all can't swallow it — the same failure
        mode the deferred-raise version of this code had, where a
        non-identifier token following the misplaced rest (e.g. `5`) raised
        `ParseError` from the nested `_consume(IDENTIFIER, ...)` before the
        deferred check ever ran, and fell through to `_block()`'s unrelated
        error instead."""

        start = self.pos
        try:
            self._advance()  # consume '{'
            names = []
            rest = None
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._destructure_rest_name()
            else:
                names.append(self._destructure_map_pattern_entry())
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACE):
                    break
                if rest is not None:
                    raise _RestNotLast(self._peek())
                if self._check(TokenType.DOT_DOT_DOT):
                    rest = self._destructure_rest_name()
                else:
                    names.append(self._destructure_map_pattern_entry())
            for _, binding, _ in names:
                if isinstance(binding, tuple) and len(binding) == 3:
                    # A list pattern nested inside a map pattern has no
                    # plain-assignment reading (only `let`/`for`/fn params/
                    # comprehensions support it) — fall through to `_block()`
                    # exactly as before this shape existed.
                    raise ParseError(
                        "invalid assignment target", self._peek().line, self._peek().column
                    )
            self._consume(TokenType.RBRACE, "'}' after destructuring pattern")
            eq_token = self._consume(TokenType.EQ, "'=' after destructuring pattern")
        except _RestNotLast as violation:
            token = violation.token
            raise ParseError(
                f"rest element must be last in destructuring pattern, found {self._describe(token)}",
                token.line,
                token.column,
            ) from None
        except ParseError:
            self.pos = start
            return None
        value = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after destructuring assignment")
        return ExprStmt(
            DestructureAssign(names, rest, value, eq_token.line, eq_token.column, is_map=True)
        )

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

    def _labeled_loop_statement(self) -> Stmt:
        label_token = self._advance()  # IDENTIFIER
        self._advance()  # ':'
        if self._check(TokenType.WHILE):
            return self._while_statement(label_token.lexeme)
        if self._check(TokenType.DO):
            return self._do_while_statement(label_token.lexeme)
        return self._for_statement(label_token.lexeme)

    def _while_statement(self, label: "str | None" = None) -> Stmt:
        while_token = self._advance()
        self._consume(TokenType.LPAREN, "'(' after 'while'")
        condition = self._assignment()
        self._consume(TokenType.RPAREN, "')' after while condition")
        self._loop_labels.append(label)
        body = self._statement()
        self._loop_labels.pop()
        return WhileStmt(condition, body, while_token.line, while_token.column, label)

    def _do_while_statement(self, label: "str | None" = None) -> Stmt:
        do_token = self._advance()
        self._loop_labels.append(label)
        body = self._statement()
        self._loop_labels.pop()
        self._consume(TokenType.WHILE, "'while' after 'do' body")
        self._consume(TokenType.LPAREN, "'(' after 'while'")
        condition = self._assignment()
        self._consume(TokenType.RPAREN, "')' after while condition")
        self._consume(TokenType.SEMICOLON, "';' after 'do ... while (...)'")
        return DoWhileStmt(condition, body, do_token.line, do_token.column, label)

    def _for_statement(self, label: "str | None" = None) -> Stmt:
        for_token = self._advance()
        if self._check(TokenType.LPAREN):
            return self._for_c_statement(for_token, label)
        var_name = None
        names = None
        rest = None
        is_map = False
        if self._check(TokenType.LBRACKET):
            names, rest = self._destructure_list_pattern()
        elif self._check(TokenType.LBRACE):
            names, rest = self._destructure_map_pattern()
            is_map = True
        else:
            var_name = self._consume(TokenType.IDENTIFIER, "identifier after 'for'").lexeme
        self._consume(TokenType.IN, "'in' after for-loop variable")
        iterable = self._assignment()
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before for-loop body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._loop_labels.append(label)
        body = self._block()
        self._loop_labels.pop()
        return ForStmt(
            var_name,
            iterable,
            body,
            for_token.line,
            for_token.column,
            label,
            names=names,
            rest=rest,
            is_map=is_map,
        )

    def _for_c_statement(self, for_token: Token, label: "str | None" = None) -> Stmt:
        self._advance()  # LPAREN
        if self._check(TokenType.SEMICOLON):
            self._advance()
            init = None
        elif self._check(TokenType.LET):
            init = self._let_statement()  # consumes its own trailing ';'
        else:
            init = ExprStmt(self._assignment())
            self._consume(TokenType.SEMICOLON, "';' after for-loop init")
        if self._check(TokenType.SEMICOLON):
            condition = None
        else:
            condition = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after for-loop condition")
        if self._check(TokenType.RPAREN):
            step = None
        else:
            step = ExprStmt(self._assignment())
        self._consume(TokenType.RPAREN, "')' after for-loop clauses")
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before for-loop body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._loop_labels.append(label)
        body = self._block()
        self._loop_labels.pop()
        return ForCStmt(
            init, condition, step, body, for_token.line, for_token.column, label
        )

    def _fn_declaration(self) -> Stmt:
        fn_token = self._advance()
        name_token = self._consume(TokenType.IDENTIFIER, "function name after 'fn'")
        params, rest_param, body = self._fn_params_and_body()
        return FnDecl(
            name_token.lexeme, params, rest_param, body, fn_token.line, fn_token.column
        )

    def _fn_expression(self) -> Expr:
        fn_token = self._advance()
        name = None
        if self._check(TokenType.IDENTIFIER):
            name = self._advance().lexeme
        params, rest_param, body = self._fn_params_and_body()
        return FnExpr(params, rest_param, body, fn_token.line, fn_token.column, name)

    def _try_arrow_function(self) -> "FnExpr | None":
        """Speculatively parses `(params) => expr` or `(params) => { ... }`
        at expression position, tried before `_primary`'s existing `(`
        grouping-expression parse — the two share an opening `(` and look
        identical until either a valid parameter-list shape isn't found or
        no `=>` follows the closing `)`. Desugars to a plain `FnExpr`, so
        the interpreter needs no changes at all. Returns `None` on any
        shape mismatch, leaving `self.pos` restored to before the `(` for
        the caller's grouping fallback — matching the backtracking pattern
        `_brace_statement` uses for its own `{`-disambiguation problem."""
        start = self.pos
        try:
            lparen = self._advance()  # consume '('
            params, rest_param = self._fn_param_list()
            self._consume(TokenType.RPAREN, "')' after parameters")
            self._consume(TokenType.FAT_ARROW, "'=>' after arrow function parameters")
        except ParseError:
            self.pos = start
            return None
        body = self._arrow_body(lparen.line, lparen.column)
        return FnExpr(params, rest_param, body, lparen.line, lparen.column)

    def _arrow_body(self, line: int, column: int) -> "Block":
        """Parses an arrow function's body, shared by both the
        parenthesized (`_try_arrow_function`) and bare single-identifier
        (`_primary`'s `IDENTIFIER` branch) forms: a block body `{ ... }`,
        parsed exactly like an ordinary `fn` body via `_fn_params_and_body`
        (same `_fn_depth`/`_loop_labels` bookkeeping, no implicit return),
        or — when no `{` follows `=>` — a bare expression body wrapped in a
        synthetic `return`, unchanged from before block bodies existed."""
        if self._check(TokenType.LBRACE):
            self._fn_depth += 1
            outer_loop_labels = self._loop_labels
            self._loop_labels = []
            body = self._block()
            self._loop_labels = outer_loop_labels
            self._fn_depth -= 1
            return body
        body_expr = self._assignment()
        return Block([ReturnStmt(body_expr, line, column)])

    def _fn_params_and_body(self) -> tuple:
        self._consume(TokenType.LPAREN, "'(' after 'fn'")
        params, rest_param = self._fn_param_list()
        self._consume(TokenType.RPAREN, "')' after parameters")
        if not self._check(TokenType.LBRACE):
            token = self._peek()
            raise ParseError(
                f"expected '{{' before function body, found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._fn_depth += 1
        outer_loop_labels = self._loop_labels
        self._loop_labels = []
        body = self._block()
        self._loop_labels = outer_loop_labels
        self._fn_depth -= 1
        return params, rest_param, body

    def _fn_param_list(self) -> tuple:
        """Parses a comma-separated parameter list — default values and a
        single trailing rest parameter, via `_fn_param`/`_fn_rest_param` —
        assuming the caller has already consumed the opening `(` and will
        consume the closing `)` itself. Shared by `fn` expressions/
        declarations and arrow-function parameter lists."""
        params = []
        rest_param = None
        seen_default = False
        if not self._check(TokenType.RPAREN):
            if self._check(TokenType.DOT_DOT_DOT):
                rest_param = self._fn_rest_param()
            else:
                params.append(self._fn_param(seen_default))
                seen_default = seen_default or params[-1].default is not None
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                if rest_param is not None:
                    token = self._peek()
                    raise ParseError(
                        "rest parameter must be the last parameter",
                        token.line,
                        token.column,
                    )
                if self._check(TokenType.DOT_DOT_DOT):
                    rest_param = self._fn_rest_param()
                else:
                    params.append(self._fn_param(seen_default))
                    seen_default = seen_default or params[-1].default is not None
        return params, rest_param

    def _fn_rest_param(self) -> str:
        self._advance()  # DOT_DOT_DOT
        name_token = self._consume(TokenType.IDENTIFIER, "parameter name after '...'")
        return name_token.lexeme

    def _fn_param(self, seen_default: bool) -> Param:
        if self._check(TokenType.LBRACKET):
            bracket_token = self._peek()
            if seen_default:
                raise ParseError(
                    "destructuring parameter without a default value "
                    "follows a parameter with one",
                    bracket_token.line,
                    bracket_token.column,
                )
            names, rest = self._destructure_list_pattern()
            if self._check(TokenType.EQ):
                raise ParseError(
                    "destructuring parameter cannot have a default value",
                    bracket_token.line,
                    bracket_token.column,
                )
            return Param(name=None, names=names, rest=rest)
        if self._check(TokenType.LBRACE):
            brace_token = self._peek()
            if seen_default:
                raise ParseError(
                    "destructuring parameter without a default value "
                    "follows a parameter with one",
                    brace_token.line,
                    brace_token.column,
                )
            names, rest = self._destructure_map_pattern()
            if self._check(TokenType.EQ):
                raise ParseError(
                    "destructuring parameter cannot have a default value",
                    brace_token.line,
                    brace_token.column,
                )
            return Param(name=None, names=names, rest=rest, is_map=True)
        name_token = self._consume(TokenType.IDENTIFIER, "parameter name")
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
        elif seen_default:
            raise ParseError(
                f"parameter '{name_token.lexeme}' without a default value "
                "follows a parameter with one",
                name_token.line,
                name_token.column,
            )
        else:
            default = None
        return Param(name=name_token.lexeme, default=default)

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

    def _throw_statement(self) -> Stmt:
        throw_token = self._advance()
        if self._check(TokenType.SEMICOLON):
            raise ParseError(
                "expected expression after 'throw'", throw_token.line, throw_token.column
            )
        expression = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after throw statement")
        return ThrowStmt(expression, throw_token.line, throw_token.column)

    def _break_statement(self) -> Stmt:
        break_token = self._advance()
        if not self._loop_labels:
            raise ParseError(
                "'break' outside of a loop", break_token.line, break_token.column
            )
        label = self._consume_loop_label("break")
        self._consume(TokenType.SEMICOLON, "';' after 'break'")
        return BreakStmt(break_token.line, break_token.column, label)

    def _continue_statement(self) -> Stmt:
        continue_token = self._advance()
        if not self._loop_labels:
            raise ParseError(
                "'continue' outside of a loop", continue_token.line, continue_token.column
            )
        label = self._consume_loop_label("continue")
        self._consume(TokenType.SEMICOLON, "';' after 'continue'")
        return ContinueStmt(continue_token.line, continue_token.column, label)

    def _consume_loop_label(self, keyword: str) -> "str | None":
        """Optionally consumes a trailing `IDENTIFIER` naming the loop a
        `break`/`continue` targets, validating it against `_loop_labels` —
        the labels of loops currently open in the parser. Absent entirely
        (next token isn't an identifier) it targets the innermost loop, same
        as today."""
        if not self._check(TokenType.IDENTIFIER):
            return None
        label_token = self._advance()
        if label_token.lexeme not in self._loop_labels:
            raise ParseError(
                f"'{keyword} {label_token.lexeme}' does not match any enclosing loop label",
                label_token.line,
                label_token.column,
            )
        return label_token.lexeme

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
        catch_name = None
        catch_block = None
        if self._check(TokenType.CATCH):
            self._advance()
            if self._check(TokenType.LPAREN):
                self._advance()
                name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'catch ('")
                self._consume(TokenType.RPAREN, "')' after catch name")
                catch_name = name_token.lexeme
            if not self._check(TokenType.LBRACE):
                token = self._peek()
                raise ParseError(
                    f"expected '{{' before catch body, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            catch_block = self._block()
        finally_block = None
        if self._check(TokenType.FINALLY):
            self._advance()
            if not self._check(TokenType.LBRACE):
                token = self._peek()
                raise ParseError(
                    f"expected '{{' before finally body, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            finally_block = self._block()
        if catch_block is None and finally_block is None:
            token = self._peek()
            raise ParseError(
                f"expected 'catch' or 'finally' after try block, found {self._describe(token)}",
                token.line,
                token.column,
            )
        return TryStmt(
            try_block,
            catch_name,
            catch_block,
            finally_block,
            try_token.line,
            try_token.column,
        )

    def _switch_statement(self) -> Stmt:
        switch_token = self._advance()
        self._consume(TokenType.LPAREN, "'(' after 'switch'")
        scrutinee = self._assignment()
        self._consume(TokenType.RPAREN, "')' after switch expression")
        self._consume(TokenType.LBRACE, "'{' after switch expression")
        cases = []
        default = None
        while self._check(TokenType.CASE) or self._check(TokenType.DEFAULT):
            if self._check(TokenType.CASE):
                self._advance()
                values = [self._ternary()]
                while self._check(TokenType.COMMA):
                    self._advance()
                    values.append(self._ternary())
                self._consume(TokenType.COLON, "':' after case value")
                if not self._check(TokenType.LBRACE):
                    token = self._peek()
                    raise ParseError(
                        f"expected '{{' before case body, found {self._describe(token)}",
                        token.line,
                        token.column,
                    )
                cases.append(SwitchCase(values, self._block()))
            else:
                default_token = self._advance()
                if default is not None:
                    raise ParseError(
                        "duplicate 'default' in switch statement",
                        default_token.line,
                        default_token.column,
                    )
                self._consume(TokenType.COLON, "':' after 'default'")
                if not self._check(TokenType.LBRACE):
                    token = self._peek()
                    raise ParseError(
                        f"expected '{{' before default body, found {self._describe(token)}",
                        token.line,
                        token.column,
                    )
                default = self._block()
        self._consume(TokenType.RBRACE, "'}' after switch body")
        return SwitchStmt(scrutinee, cases, default, switch_token.line, switch_token.column)

    def _match_expr(self) -> Expr:
        match_token = self._advance()  # consume 'match'
        self._consume(TokenType.LPAREN, "'(' after 'match'")
        subject = self._assignment()
        self._consume(TokenType.RPAREN, "')' after match subject")
        self._consume(TokenType.LBRACE, "'{' after match subject")
        arms = list(self._match_arm())
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACE):
                break
            arms.extend(self._match_arm())
        self._consume(TokenType.RBRACE, "'}' after match arms")
        return MatchExpr(subject, arms, match_token.line, match_token.column)

    def _match_arm(self) -> "list[MatchArm]":
        if self._check(TokenType.LBRACKET):
            list_pattern = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, list_pattern)]
        first_token = self._peek()
        entries = [self._match_pattern()]
        while self._check(TokenType.COMMA):
            self._advance()
            entries.append(self._match_pattern())
        if len(entries) > 1 and any(pattern is None for pattern, _ in entries):
            raise ParseError(
                "'_' or a bound identifier cannot be combined with other "
                "patterns in a match arm",
                first_token.line,
                first_token.column,
            )
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return [MatchArm(pattern, body, binding) for pattern, binding in entries]

    def _match_list_pattern(self) -> "list[str | None]":
        self._advance()  # consume '['
        names: "list[str | None]" = []
        if not self._check(TokenType.RBRACKET):
            names.append(self._match_list_pattern_name())
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._match_list_pattern_name())
        self._consume(TokenType.RBRACKET, "']' after list pattern")
        return names

    def _match_list_pattern_name(self) -> "str | None":
        token = self._peek()
        if token.type != TokenType.IDENTIFIER:
            raise ParseError(
                f"expected an identifier or '_' inside list pattern, "
                f"found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._advance()
        return None if token.lexeme == "_" else token.lexeme

    def _match_pattern(self) -> "tuple[Expr | None, str | None]":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.lexeme == "_":
                return None, None
            return None, token.lexeme
        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column), None
        if token.type == TokenType.TRUE:
            self._advance()
            return Literal(True, token.line, token.column), None
        if token.type == TokenType.FALSE:
            self._advance()
            return Literal(False, token.line, token.column), None
        if token.type == TokenType.NIL:
            self._advance()
            return Literal(None, token.line, token.column), None
        raise ParseError(
            f"expected a literal, identifier, or '_' in match pattern, "
            f"found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _expr_statement(self) -> Stmt:
        multi_assign = self._try_multi_assign_statement()
        if multi_assign is not None:
            return multi_assign
        first = self._assignment()
        statements = [ExprStmt(first)]
        while self._check(TokenType.COMMA):
            self._advance()
            statements.append(ExprStmt(self._assignment()))
        self._consume(TokenType.SEMICOLON, "';' after expression")
        if len(statements) == 1:
            return statements[0]
        return DeclSeq(statements, first.line, first.column)

    def _try_multi_assign_statement(self) -> "Stmt | None":
        """Speculatively parses bare comma-separated multi-target
        assignment `a, b = 1, 2;` (including the swap idiom
        `a, b = b, a;`), tried before `_expr_statement`'s existing
        single-target/comma-separated-statements parse. Desugars to the
        same `DestructureAssign` node the bracketed form `[a, b] = expr;`
        already produces (`_assignment`'s `isinstance(expr, ListLiteral)`
        branch), reusing its runtime semantics for free: RHS evaluated
        once, length-checked, assigned left to right — so the RHS is
        evaluated in full (both `b` and `a` in the swap case) before any
        target is written, which is what makes the swap idiom correct.
        Returns `None` on any shape mismatch — fewer than two
        comma-separated identifiers, or no top-level `=` following them —
        leaving `self.pos` untouched so the caller's own `_assignment()`-
        based parse runs unchanged; this keeps `a = 1, 2;` (single target,
        PR #289's DeclSeq form) and `a, b;` (two independent identifier
        statements) parsing exactly as before, since both fail this
        speculative parse (too few names, or no top-level `=`)."""
        start = self.pos
        try:
            names = [self._consume(TokenType.IDENTIFIER, "identifier")]
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._consume(TokenType.IDENTIFIER, "identifier"))
            if len(names) < 2 or not self._check(TokenType.EQ):
                self.pos = start
                return None
            eq_token = self._advance()
            values = [self._assignment()]
            while self._check(TokenType.COMMA):
                self._advance()
                values.append(self._assignment())
        except ParseError:
            self.pos = start
            return None
        self._consume(TokenType.SEMICOLON, "';' after multi-target assignment")
        pattern_names = [(name.lexeme, None) for name in names]
        value = values[0] if len(values) == 1 else ListLiteral(
            values, eq_token.line, eq_token.column
        )
        return ExprStmt(
            DestructureAssign(
                pattern_names, None, value, eq_token.line, eq_token.column, is_map=False
            )
        )

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
            if isinstance(expr, SliceExpr):
                return SliceAssign(
                    expr.obj, expr.start, expr.end, expr.step, value,
                    eq_token.line, eq_token.column,
                )
            if isinstance(expr, ListLiteral):
                names, rest = self._destructure_assign_pattern(expr, eq_token)
                return DestructureAssign(
                    names, rest, value, eq_token.line, eq_token.column
                )
            raise ParseError(
                "invalid assignment target", eq_token.line, eq_token.column
            )
        if self._check(TokenType.QQEQ):
            op_token = self._advance()
            value = self._assignment()
            if isinstance(expr, Identifier):
                qq_operator = Token(
                    TokenType.QUESTION_QUESTION, "??", None, op_token.line, op_token.column
                )
                logical = Logical(expr, qq_operator, value)
                return Assign(expr.name, logical, op_token.line, op_token.column)
            if isinstance(expr, Index):
                return IndexNilCoalesceAssign(
                    expr.obj, expr.index, value, op_token.line, op_token.column
                )
            raise ParseError(
                "invalid assignment target", op_token.line, op_token.column
            )
        if self._peek().type in _COMPOUND_ASSIGN_OPS:
            op_token = self._advance()
            value = self._assignment()
            binary_operator = Token(
                _COMPOUND_ASSIGN_OPS[op_token.type],
                op_token.lexeme[:-1],
                None,
                op_token.line,
                op_token.column,
            )
            if isinstance(expr, Identifier):
                binary = Binary(expr, binary_operator, value)
                return Assign(expr.name, binary, op_token.line, op_token.column)
            if (
                isinstance(expr, Index)
                and op_token.type in _INDEX_TARGET_COMPOUND_ASSIGN_OPS
            ):
                # Not desugared into IndexAssign(obj, index, Binary(Index(obj,
                # index), op, value)): that would embed `expr` (the Index node)
                # both directly and inside the Binary's left, so the interpreter
                # would evaluate `obj`/`index` twice — once for the read, once
                # walking the nested Index again. IndexCompoundAssign instead
                # carries obj/index once, evaluated a single time at runtime.
                return IndexCompoundAssign(
                    expr.obj,
                    expr.index,
                    binary_operator,
                    value,
                    op_token.line,
                    op_token.column,
                )
            raise ParseError(
                "invalid assignment target", op_token.line, op_token.column
            )
        if self._peek().type in _INCREMENT_DECREMENT_OPS:
            op_token = self._advance()
            binary_operator = Token(
                _INCREMENT_DECREMENT_OPS[op_token.type],
                op_token.lexeme[0],
                None,
                op_token.line,
                op_token.column,
            )
            one = Literal(1, op_token.line, op_token.column)
            if isinstance(expr, Identifier):
                return Assign(
                    expr.name,
                    Binary(expr, binary_operator, one),
                    op_token.line,
                    op_token.column,
                )
            if isinstance(expr, Index):
                return IndexCompoundAssign(
                    expr.obj,
                    expr.index,
                    binary_operator,
                    one,
                    op_token.line,
                    op_token.column,
                )
            raise ParseError(
                "invalid assignment target", op_token.line, op_token.column
            )
        return expr

    def _ternary(self) -> Expr:
        expr = self._pipe()
        if self._check(TokenType.QUESTION):
            question_token = self._advance()
            then_expr = self._ternary()
            self._consume(TokenType.COLON, "':' in ternary expression")
            else_expr = self._ternary()
            return Ternary(
                expr, then_expr, else_expr, question_token.line, question_token.column
            )
        return expr

    def _pipe(self) -> Expr:
        expr = self._nullish()
        while self._check(TokenType.PIPE_ARROW):
            operator = self._advance()
            right = self._nullish()
            expr = Binary(expr, operator, right)
        return expr

    def _nullish(self) -> Expr:
        expr = self._or()
        if self._check(TokenType.QUESTION_QUESTION):
            operator = self._advance()
            right = self._nullish()  # right-recursive: right-associative chaining
            return Logical(expr, operator, right)
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
        while True:
            if self._check(TokenType.IN):
                operator = self._advance()
                right = self._comparison()
                expr = Binary(expr, operator, right)
            elif (
                self._check(TokenType.NOT)
                and self._peek_next().type == TokenType.IN
            ):
                not_token = self._advance()
                self._advance()  # consume IN
                operator = Token(
                    TokenType.NOT_IN, "not in", None, not_token.line, not_token.column
                )
                right = self._comparison()
                expr = Binary(expr, operator, right)
            else:
                break
        return expr

    def _comparison(self) -> Expr:
        operands = [self._range_expr()]
        operators = []
        while self._peek().type in _COMPARISON:
            operators.append(self._advance())
            operands.append(self._range_expr())
        if not operators:
            return operands[0]
        if len(operators) >= 2 and all(op.type in _ORDERING for op in operators):
            return ChainedComparison(
                operands, operators, operators[0].line, operators[0].column
            )
        result = operands[0]
        for operator, right in zip(operators, operands[1:]):
            result = Binary(result, operator, right)
        return result

    def _range_expr(self) -> Expr:
        expr = self._bitor()
        if self._check(TokenType.DOT_DOT) or self._check(TokenType.DOT_DOT_EQ):
            dots = self._advance()
            end = self._bitor()
            inclusive = dots.type is TokenType.DOT_DOT_EQ
            step = None
            if self._check(TokenType.DOT_DOT):
                self._advance()
                step = self._bitor()
            return RangeExpr(expr, end, dots.line, dots.column, inclusive, step)
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
        expr = self._power()
        while self._peek().type in _FACTOR:
            operator = self._advance()
            right = self._power()
            expr = Binary(expr, operator, right)
        return expr

    def _power(self) -> Expr:
        expr = self._unary()
        if self._check(TokenType.STARSTAR):
            operator = self._advance()
            right = self._power()  # right-associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
            expr = Binary(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._check(TokenType.MINUSMINUS):
            # `--5`/`--x` in prefix position has no postfix meaning (there's
            # nothing before it to decrement) — it's the same doubled unary
            # minus `- -5` lexes as with a space, just written without one.
            # Re-split the merged token into two MINUS operators rather than
            # rejecting what used to parse fine before `--` became a token.
            token = self._advance()
            minus = Token(TokenType.MINUS, "-", None, token.line, token.column)
            return Unary(minus, Unary(minus, self._unary()))
        if self._check(TokenType.PLUSPLUS):
            # Same re-split as MINUSMINUS above: a leading `++` in
            # expression position can never be a postfix increment (there's
            # nothing before it to increment), so it unambiguously means
            # doubled unary plus.
            token = self._advance()
            plus = Token(TokenType.PLUS, "+", None, token.line, token.column)
            return Unary(plus, Unary(plus, self._unary()))
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
            elif self._check(TokenType.DOT):
                expr = self._finish_dot(expr)
            elif self._check(TokenType.QUESTION_DOT):
                expr = self._finish_optional_dot(expr)
            else:
                break
        return expr

    def _finish_call(self, callee: Expr) -> Expr:
        paren = self._previous()
        arguments = []
        seen_keyword = False
        if not self._check(TokenType.RPAREN):
            arguments.append(self._call_argument())
            seen_keyword = isinstance(arguments[-1], KeywordArg)
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                argument = self._call_argument()
                if seen_keyword and not isinstance(argument, KeywordArg):
                    raise ParseError(
                        "positional argument follows keyword argument",
                        paren.line,
                        paren.column,
                    )
                seen_keyword = seen_keyword or isinstance(argument, KeywordArg)
                arguments.append(argument)
        self._consume(TokenType.RPAREN, "')' after arguments")
        return Call(callee, arguments, paren.line, paren.column)

    def _call_argument(self) -> Expr:
        if self._check(TokenType.DOT_DOT_DOT):
            dots = self._advance()
            return Spread(self._ternary(), dots.line, dots.column)
        if (
            self._check(TokenType.IDENTIFIER)
            and self._peek_next().type == TokenType.COLON
        ):
            name_token = self._advance()
            self._advance()  # consume ':'
            return KeywordArg(
                name_token.lexeme, self._ternary(), name_token.line, name_token.column
            )
        return self._ternary()

    def _finish_index(self, obj: Expr) -> Expr:
        bracket = self._advance()  # consume '['
        start = None
        if not self._check(TokenType.COLON):
            start = self._ternary()
        if self._check(TokenType.COLON):
            self._advance()
            end = None
            if not self._check(TokenType.RBRACKET) and not self._check(TokenType.COLON):
                end = self._ternary()
            step = None
            if self._check(TokenType.COLON):
                self._advance()
                if not self._check(TokenType.RBRACKET):
                    step = self._ternary()
            self._consume(TokenType.RBRACKET, "']' after slice")
            return SliceExpr(obj, start, end, step, bracket.line, bracket.column)
        self._consume(TokenType.RBRACKET, "']' after index")
        return Index(obj, start, bracket.line, bracket.column)

    def _finish_dot(self, obj: Expr) -> Expr:
        dot = self._advance()  # consume '.'
        name_token = self._consume(TokenType.IDENTIFIER, "a property name after '.'")
        key = Literal(name_token.lexeme, name_token.line, name_token.column)
        return Index(obj, key, dot.line, dot.column)

    def _finish_optional_dot(self, obj: Expr) -> Expr:
        dot = self._advance()  # consume '?.'
        if self._check(TokenType.LPAREN):
            return self._finish_optional_call(obj)
        if self._check(TokenType.LBRACKET):
            self._advance()  # consume '['
            index = self._ternary()
            self._consume(TokenType.RBRACKET, "']' after index")
            return OptionalIndex(obj, index, dot.line, dot.column)
        name_token = self._consume(TokenType.IDENTIFIER, "a property name after '?.'")
        key = Literal(name_token.lexeme, name_token.line, name_token.column)
        return OptionalIndex(obj, key, dot.line, dot.column)

    def _finish_optional_call(self, callee: Expr) -> Expr:
        self._advance()  # consume '('
        paren = self._previous()
        arguments = []
        seen_keyword = False
        if not self._check(TokenType.RPAREN):
            arguments.append(self._call_argument())
            seen_keyword = isinstance(arguments[-1], KeywordArg)
            while self._check(TokenType.COMMA):
                self._advance()
                argument = self._call_argument()
                if seen_keyword and not isinstance(argument, KeywordArg):
                    raise ParseError(
                        "positional argument follows keyword argument",
                        paren.line,
                        paren.column,
                    )
                seen_keyword = seen_keyword or isinstance(argument, KeywordArg)
                arguments.append(argument)
        self._consume(TokenType.RPAREN, "')' after arguments")
        return OptionalCall(callee, arguments, paren.line, paren.column)

    def _primary(self) -> Expr:
        token = self._peek()

        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column)
        if token.type == TokenType.INTERP_STRING:
            self._advance()
            return self._build_interp_string(token)
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
            if self._peek_next().type == TokenType.FAT_ARROW:
                self._advance()  # consume the identifier
                self._consume(TokenType.FAT_ARROW, "'=>' after arrow function parameter")
                body = self._arrow_body(token.line, token.column)
                return FnExpr(
                    [Param(name=token.lexeme)], None, body, token.line, token.column
                )
            self._advance()
            return Identifier(token.lexeme, token.line, token.column)
        if token.type == TokenType.LPAREN:
            arrow = self._try_arrow_function()
            if arrow is not None:
                return arrow
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
        if token.type == TokenType.MATCH:
            return self._match_expr()

        raise ParseError(
            f"expected an expression, found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _list_literal(self) -> Expr:
        bracket = self._advance()  # consume '['
        elements = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._list_element())
            if self._check(TokenType.FOR):
                if isinstance(elements[0], Spread):
                    raise ParseError(
                        "spread not allowed in list comprehension",
                        bracket.line,
                        bracket.column,
                    )
                return self._list_comprehension(bracket, elements[0])
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._list_element())
        self._consume(TokenType.RBRACKET, "']' after list literal")
        return ListLiteral(elements, bracket.line, bracket.column)

    def _comprehension_clause(self) -> ComprehensionClause:
        var_name = None
        names = None
        rest = None
        is_map = False
        if self._check(TokenType.LBRACKET):
            names, rest = self._destructure_list_pattern()
        elif self._check(TokenType.LBRACE):
            names, rest = self._destructure_map_pattern()
            is_map = True
        else:
            var_name = self._consume(TokenType.IDENTIFIER, "loop variable after 'for'").lexeme
        self._consume(TokenType.IN, "'in' after loop variable")
        iterable = self._ternary()
        condition = None
        if self._check(TokenType.IF):
            self._advance()
            condition = self._ternary()
        return ComprehensionClause(
            var_name, iterable, condition, self._previous().line, self._previous().column,
            names=names, rest=rest, is_map=is_map,
        )

    def _list_comprehension(self, bracket: Token, element: Expr) -> Expr:
        self._advance()  # consume 'for'
        clause = self._comprehension_clause()
        extra_clauses = []
        while self._check(TokenType.FOR):
            self._advance()  # consume 'for'
            extra_clauses.append(self._comprehension_clause())
        self._consume(TokenType.RBRACKET, "']' after list comprehension")
        return ListComprehension(
            element,
            clause.var_name,
            clause.iterable,
            clause.condition,
            bracket.line,
            bracket.column,
            names=clause.names,
            rest=clause.rest,
            is_map=clause.is_map,
            extra_clauses=extra_clauses or None,
        )

    def _list_element(self) -> Expr:
        if self._check(TokenType.DOT_DOT_DOT):
            dots = self._advance()
            return Spread(self._ternary(), dots.line, dots.column)
        return self._ternary()

    def _map_literal(self) -> Expr:
        brace = self._advance()  # consume '{'
        pairs = []
        if not self._check(TokenType.RBRACE):
            entry = self._map_entry()
            if self._check(TokenType.FOR):
                if isinstance(entry, Spread):
                    raise ParseError(
                        "spread not allowed in map comprehension",
                        brace.line,
                        brace.column,
                    )
                return self._map_comprehension(brace, entry)
            pairs.append(entry)
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACE):
                    break
                pairs.append(self._map_entry())
        self._consume(TokenType.RBRACE, "'}' after map literal")
        return MapLiteral(pairs, brace.line, brace.column)

    def _map_comprehension(self, brace: Token, entry: tuple) -> Expr:
        key, value = entry
        self._advance()  # consume 'for'
        clause = self._comprehension_clause()
        extra_clauses = []
        while self._check(TokenType.FOR):
            self._advance()  # consume 'for'
            extra_clauses.append(self._comprehension_clause())
        self._consume(TokenType.RBRACE, "'}' after map comprehension")
        return MapComprehension(
            key,
            value,
            clause.var_name,
            clause.iterable,
            clause.condition,
            brace.line,
            brace.column,
            names=clause.names,
            rest=clause.rest,
            is_map=clause.is_map,
            extra_clauses=extra_clauses or None,
        )

    def _map_entry(self):
        if self._check(TokenType.DOT_DOT_DOT):
            dots = self._advance()
            return Spread(self._ternary(), dots.line, dots.column)
        if self._check(TokenType.IDENTIFIER) and self._peek_next().type in (
            TokenType.COMMA,
            TokenType.RBRACE,
        ):
            name = self._advance()
            key = Literal(name.lexeme, name.line, name.column)
            value = Identifier(name.lexeme, name.line, name.column)
            return (key, value)
        return self._map_pair()

    def _map_pair(self) -> tuple:
        key = self._or()
        self._consume(TokenType.COLON, "':' after map key")
        value = self._ternary()
        return (key, value)

    def _build_interp_string(self, token: Token) -> Expr:
        """Each `("expr", raw, line, col)` placeholder from the lexer is
        re-lexed/parsed as a standalone expression on the spot, seeding the
        sub-`Lexer` with the placeholder's own source position so any
        Lex/ParseError it raises still points at the right place in the
        original file rather than restarting at 1:1."""
        parts = []
        for part in token.literal:
            if isinstance(part, str):
                if part:
                    parts.append(part)
                continue
            _, raw_source, expr_line, expr_col = part
            sub_tokens = Lexer(raw_source, expr_line, expr_col).tokenize()
            parts.append(Parser(sub_tokens).parse_expression())
        return InterpString(parts, token.line, token.column)

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _peek_next(self) -> Token:
        idx = min(self.pos + 1, len(self.tokens) - 1)
        return self.tokens[idx]

    def _peek_at(self, offset: int) -> Token:
        idx = min(self.pos + offset, len(self.tokens) - 1)
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
