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
class KeywordArg:
    """A `name: expr` argument inside a call's argument list; `Call.arguments`/
    `OptionalCall.arguments` mix these with plain `Expr`s and `Spread`s."""

    name: str
    value: "Expr"
    line: int
    column: int


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
class ComprehensionClause:
    var_name: "str | None"
    iterable: "Expr"
    condition: "Expr | None"
    line: int
    column: int
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False


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
    extra_clauses: "list[ComprehensionClause] | None" = None


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
    extra_clauses: "list[ComprehensionClause] | None" = None


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
    step: "Expr | None"
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class RangeExpr:
    start: "Expr"
    end: "Expr"
    line: int
    column: int
    inclusive: bool = False
    step: "Expr | None" = None


@dataclass(frozen=True)
class Ternary:
    condition: "Expr"
    then_expr: "Expr"
    else_expr: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class MatchArm:
    """`pattern` is `None` for an unconditional arm — either the `_`
    wildcard (`binding` also `None`) or a bound-identifier pattern
    (`binding` holds the name), both of which match unconditionally
    and are otherwise compared via `values_equal`, the same helper
    `SwitchStmt` case-matching already uses, when `pattern` is not
    `None`. A bound-identifier arm's `binding` name is defined, holding
    the match subject's value, in a fresh child scope that only
    `body`'s evaluation sees — it does not leak into the enclosing
    scope, mirroring `TryStmt`'s own `catch_name` binding
    (`cinder/interpreter.py`'s `_execute_try`). `list_pattern` is a
    third, mutually exclusive pattern kind: a flat list of `(name,
    default)` pairs (`name` is `None` for `_`, `default` is `None` when
    the element has no default) tested against the subject's shape
    rather than compared with `values_equal`; a trailing run of
    defaulted elements lets a shorter-than-the-pattern subject still
    match, falling back to each default (evaluated in the arm's own
    environment, left to right, so an earlier element is visible to a
    later default) — mirroring `let`/`for`/destructuring list patterns'
    own trailing-default support. `pattern` and `binding` stay `None`
    for a list-pattern arm. `range_pattern` is a fourth pattern kind: a
    membership test against an int range, combinable with literal
    patterns (but not with the wildcard/bound-identifier kind) in a
    multi-value arm; `pattern` and `binding` stay `None` for a
    range-pattern entry. `list_rest` accompanies `list_pattern`: `None`
    when the list pattern has no rest capture, the bound name when it
    does (kept as the literal name `"_"` when the rest is discarded, so
    the interpreter can tell "no rest capture" apart from "rest
    capture, discarded"). `map_pattern` is a fifth, mutually exclusive
    pattern kind: a flat list of `(key, binding, default)` triples,
    tested for presence against the subject's keys (a map/dict), unless
    `default` is set, in which case a missing key falls back to
    `default` (evaluated in the arm's own environment, left to right,
    so an earlier binding is visible to a later default) rather than
    failing the match — mirroring `list_pattern`'s own trailing-default
    support, except a map pattern's defaults may appear in any position
    since each entry is looked up by key, not position. `binding` is
    either a plain name (equal to `key` when unrenamed, binding the
    key's value directly), a nested list pattern as an `(entries, rest,
    True)` triple, or a nested map pattern as an `(entries, rest)` pair
    — the trailing `True` tag on the triple is what lets the
    interpreter tell a nested list pattern apart from a nested map
    pattern, since both would otherwise reduce to the same 2-tuple
    shape. A nested pattern is matched recursively against the key's
    value rather than bound directly, mirroring `list_pattern`'s own
    nested-element support, and its own `default` stays `None` — only a
    plain-name binding may carry a default. `pattern` and `binding` stay
    `None` for a map-pattern arm. `map_rest` accompanies `map_pattern`,
    mirroring `list_rest`: `None` when the map pattern has no rest
    capture, the bound name when it does (kept as the literal name
    `"_"` when the rest is discarded, so the interpreter can tell "no
    rest capture" apart from "rest capture, discarded")."""

    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
    list_pattern: "list | None" = None
    range_pattern: "RangeExpr | None" = None
    list_rest: "str | None" = None
    map_pattern: "list[tuple[str, object, Expr | None]] | None" = None
    map_rest: "str | None" = None


@dataclass(frozen=True)
class MatchExpr:
    """`match (subject) { pattern => body, ..., _ => body }`. `subject` is
    evaluated exactly once; `arms` are tried in source order via
    `values_equal` and the first match's `body` is evaluated and returned
    (no fallthrough, short-circuits on first match same as `SwitchStmt`).
    An arm may also be unconditional: the `_` wildcard or a
    bound-identifier pattern (any other identifier, which binds the
    subject's value for the arm's body). If no arm matches (including no
    unconditional arm present), raises `CinderRuntimeError` — unlike
    `switch`'s `default`, there is no silent no-op: `match` is an
    expression and must produce a value or fail."""

    subject: "Expr"
    arms: list
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
    the function has none — see `fn f(a, ...rest) { ... }`.

    `name` is the function's own self-reference name for `fn name(...) {
    ... }`, or `None` for the plain anonymous `fn(...) { ... }` form —
    see `_fn_expression` in `parser.py` and `CinderFunction.name` in
    `interpreter.py`."""

    params: list
    rest_param: "str | None"
    body: "Block"
    line: int
    column: int
    name: "str | None" = None


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
    RangeExpr,
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
class DeclSeq:
    declarations: list
    line: int
    column: int


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
