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
class Assign:
    name: str
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class ListLiteral:
    elements: list
    line: int
    column: int


@dataclass(frozen=True)
class MapLiteral:
    pairs: list  # list[tuple[Expr, Expr]] of (key, value) expressions
    line: int
    column: int


@dataclass(frozen=True)
class Index:
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


Expr = Union[
    Literal,
    Identifier,
    Unary,
    Binary,
    Logical,
    Grouping,
    Call,
    Assign,
    ListLiteral,
    MapLiteral,
    Index,
    IndexAssign,
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


@dataclass(frozen=True)
class ForStmt:
    var_name: str
    iterable: "Expr"
    body: "Block"
    line: int
    column: int


@dataclass(frozen=True)
class FnDecl:
    name: str
    params: list
    body: "Block"
    line: int
    column: int


@dataclass(frozen=True)
class ReturnStmt:
    value: "Expr | None"
    line: int
    column: int


Stmt = Union[
    ExprStmt, LetStmt, Block, IfStmt, WhileStmt, ForStmt, FnDecl, ReturnStmt
]
