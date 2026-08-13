"""Expression AST node definitions for Cinder.

Binary/Unary/Logical nodes carry the full operator Token (not just the
lexeme) so later stages (the interpreter's runtime errors) have line/column
available without threading it through separately.
"""

from dataclasses import dataclass
from typing import Any, Union

from cinder.tokens import Token


@dataclass(frozen=True)
class Literal:
    value: Any
    line: int
    column: int


@dataclass(frozen=True)
class Identifier:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class Unary:
    operator: Token
    operand: "Expr"


@dataclass(frozen=True)
class Binary:
    left: "Expr"
    operator: Token
    right: "Expr"


@dataclass(frozen=True)
class ChainedComparison:
    """`a < b < c` (and longer/mixed-ordering-operator chains).

    `operands` holds the N+1 sub-expressions and `operators` the N ordering
    Tokens between them (drawn purely from `<`/`<=`/`>`/`>=` — a chain mixing
    in `==`/`!=` stays a left-folded `Binary` chain instead, unchanged from
    before this node existed). Evaluates as `operands[0] operators[0]
    operands[1] and operands[1] operators[1] operands[2] and ...`, each
    operand evaluated exactly once and the whole chain short-circuiting on
    the first `false` pairwise comparison."""

    operands: list
    operators: list
    line: int
    column: int


@dataclass(frozen=True)
class Logical:
    left: "Expr"
    operator: Token
    right: "Expr"


@dataclass(frozen=True)
class Grouping:
    expression: "Expr"


@dataclass(frozen=True)
class Call:
    callee: "Expr"
    arguments: list
    line: int
    column: int


@dataclass(frozen=True)
class OptionalCall:
    callee: "Expr"
    arguments: list
    line: int
    column: int


@dataclass(frozen=True)
class Assign:
    name: str
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class DestructureAssign:
    """`[a, b] = expr;` (and the rest-element form `[a, ...rest] = expr;`), or
    with `is_map=True` the map-pattern form `{a, b} = expr;` (and its own
    rest-element form `{a, ...rest} = expr;`) — the
    assignment counterpart to `DestructureLetStmt`: `names`/`rest` must
    already be bound (via `env.assign`, not `env.define`). Flat patterns
    only, mirroring `DestructureLetStmt`'s own "no nesting" rule; unlike that
    statement node this has no leading keyword to disambiguate at statement
    level, so it is an `Expr` and slots into `_assignment`/`_brace_statement`
    instead."""

    names: list
    rest: "str | None"
    value: "Expr"
    line: int
    column: int
    is_map: bool = False


@dataclass(frozen=True)
class Spread:
    """A `...expr` element inside a list literal; `ListLiteral.elements` mixes
    these with plain `Expr`s."""

    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class ListLiteral:
    elements: list
    line: int
    column: int


@dataclass(frozen=True)
class ListComprehension:
    element: "Expr"
    var_name: "str | None"
    iterable: "Expr"
    condition: "Expr | None"
    line: int
    column: int
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False


@dataclass(frozen=True)
class MapLiteral:
    pairs: list  # list of (key, value) Expr tuples mixed with Spread entries
    line: int
    column: int


@dataclass(frozen=True)
class MapComprehension:
    key: "Expr"
    value: "Expr"
    var_name: "str | None"
    iterable: "Expr"
    condition: "Expr | None"
    line: int
    column: int
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False


@dataclass(frozen=True)
class Index:
    obj: "Expr"
    index: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class OptionalIndex:
    obj: "Expr"
    index: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class IndexAssign:
    obj: "Expr"
    index: "Expr"
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class IndexCompoundAssign:
    """`xs[i] &= v` and friends: unlike `IndexAssign`, `obj`/`index` are each
    evaluated exactly once (their values are reused for both the read and
    the write) rather than desugaring into an `IndexAssign` around a
    `Binary` that re-walks an embedded `Index` sub-expression."""

    obj: "Expr"
    index: "Expr"
    operator: Token
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class IndexNilCoalesceAssign:
    """`xs[i] ??= v` and `m.key ??= v`: like `IndexCompoundAssign`, `obj`/
    `index` are each evaluated exactly once, but unlike the arithmetic/
    bitwise/shift compound-assign family, `value` is only evaluated (and
    written back) when the current value is `nil` — the short-circuit
    contract already guaranteed for the identifier case via `Logical`.
    No `operator` field: the operation is always `??`."""

    obj: "Expr"
    index: "Expr"
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class SliceExpr:
    obj: "Expr"
    start: "Expr | None"
    end: "Expr | None"
    step: "Expr | None"
    line: int
    column: int


@dataclass(frozen=True)
class SliceAssign:
    obj: "Expr"
    start: "Expr | None"
    end: "Expr | None"
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class Ternary:
    condition: "Expr"
    then_expr: "Expr"
    else_expr: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class InterpString:
    """`"...${expr}..."` — `parts` interleaves literal `str` segments with
    parsed sub-expressions in source order (an all-`str` list never occurs;
    a plain string with no `${` lexes as a regular `Literal` instead)."""

    parts: list
    line: int
    column: int


@dataclass(frozen=True)
class Param:
    """One function parameter. A plain identifier parameter sets only
    `name`/`default` (`names=None`); a list-destructuring parameter sets
    `name=None, names=names, rest=rest`; a map-destructuring parameter sets
    `name=None, names=names, is_map=True`. Same field shape `ForStmt` uses
    for its own pattern flexibility."""

    name: "str | None"
    default: "Expr | None" = None
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False


@dataclass(frozen=True)
class FnExpr:
    """An anonymous `fn(params) { body }` function literal, usable as a value
    (e.g. passed directly to `map`/`filter`, or bound with `let`) — unlike
    `FnDecl`, which only appears at statement position and requires a name.

    `params` is a `list[Param]` — see `Param`'s docstring for its shape.

    `rest_param` is the name of a trailing `...name` parameter, or `None` if
    the function has none — see `fn f(a, ...rest) { ... }`."""

    params: list
    rest_param: "str | None"
    body: "Block"
    line: int
    column: int


Expr = Union[
    Literal,
    Identifier,
    Unary,
    Binary,
    ChainedComparison,
    Logical,
    Grouping,
    Call,
    Assign,
    DestructureAssign,
    ListLiteral,
    MapLiteral,
    Index,
    IndexAssign,
    SliceExpr,
    SliceAssign,
    Ternary,
    FnExpr,
    InterpString,
]


@dataclass(frozen=True)
class ExprStmt:
    expression: "Expr"


@dataclass(frozen=True)
class LetStmt:
    name: str
    initializer: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class ConstStmt:
    name: str
    initializer: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class DestructureLetStmt:
    names: list
    initializer: "Expr"
    line: int
    column: int
    is_map: bool = False
    rest: "str | None" = None


@dataclass(frozen=True)
class Block:
    statements: list


@dataclass(frozen=True)
class IfStmt:
    condition: "Expr"
    then_branch: "Stmt"
    else_branch: "Stmt | None"
    line: int
    column: int


@dataclass(frozen=True)
class WhileStmt:
    condition: "Expr"
    body: "Stmt"
    line: int
    column: int
    label: "str | None" = None


@dataclass(frozen=True)
class DoWhileStmt:
    condition: "Expr"
    body: "Stmt"
    line: int
    column: int
    label: "str | None" = None


@dataclass(frozen=True)
class ForStmt:
    var_name: "str | None"
    iterable: "Expr"
    body: "Block"
    line: int
    column: int
    label: "str | None" = None
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False


@dataclass(frozen=True)
class ForCStmt:
    """Classic three-clause `for (init; cond; step) { ... }`, distinct from
    the foreach `ForStmt` above. `init`/`step` are `None` when their clause
    is empty (`for (;;) { ... }` is a valid infinite loop); `condition` is
    `None` when omitted, treated as always-true at execution time."""

    init: "Stmt | None"
    condition: "Expr | None"
    step: "Stmt | None"
    body: "Block"
    line: int
    column: int
    label: "str | None" = None


@dataclass(frozen=True)
class FnDecl:
    """`params` and `rest_param` are the same shape as `FnExpr`'s — see its
    docstring and `Param`'s."""

    name: str
    params: list
    rest_param: "str | None"
    body: "Block"
    line: int
    column: int


@dataclass(frozen=True)
class ReturnStmt:
    value: "Expr | None"
    line: int
    column: int


@dataclass(frozen=True)
class ThrowStmt:
    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class BreakStmt:
    line: int
    column: int
    label: "str | None" = None


@dataclass(frozen=True)
class ContinueStmt:
    line: int
    column: int
    label: "str | None" = None


@dataclass(frozen=True)
class TryStmt:
    try_block: "Block"
    catch_name: "str | None"
    catch_block: "Block | None"
    finally_block: "Block | None"
    line: int
    column: int


@dataclass(frozen=True)
class SwitchCase:
    values: list
    body: "Block"


@dataclass(frozen=True)
class SwitchStmt:
    """`switch (scrutinee) { case v1: { ... } case v2: { ... } default: { ... } }`.

    `scrutinee` is evaluated exactly once; `cases` are tried in source order
    via `values_equal` and the first match's block runs (no fallthrough). A
    case may list several values (`case v1, v2, v3: { ... }`) — its `values`
    is evaluated left to right and the block runs on the first match, so a
    later value expression's side effects don't happen once an earlier one
    already matched. `default` (or `None`) runs only if no case matched. Not
    a loop: `break`/`continue` inside a case body still target an enclosing
    loop, if any."""

    scrutinee: "Expr"
    cases: list
    default: "Block | None"
    line: int
    column: int


Stmt = Union[
    ExprStmt,
    LetStmt,
    ConstStmt,
    DestructureLetStmt,
    Block,
    IfStmt,
    WhileStmt,
    DoWhileStmt,
    ForStmt,
    ForCStmt,
    FnDecl,
    ReturnStmt,
    ThrowStmt,
    BreakStmt,
    ContinueStmt,
    TryStmt,
    SwitchStmt,
]
