"""Tree-walking evaluator for Cinder expressions and statements.

`Interpreter.evaluate` walks the expression AST produced by `cinder.parser`
and returns a plain Python value (int, float, str, bool, None), or a Python
`list`/`dict` backing a Cinder list/map literal.
`Interpreter.execute` walks statements (`LetStmt`, `ExprStmt`, `Block`,
`IfStmt`, `WhileStmt`, `ForStmt`), mutating an `Environment` rather than
returning a value. `ForStmt` binds its loop variable in a fresh child
`Environment` per iteration, so a closure created inside the loop body
captures that iteration's value rather than the final one.

`Call` nodes invoke a `CinderFunction`: a new child `Environment` of the
function's closure is pushed, parameters are bound there, and the body runs.
`return` unwinds via `_ReturnSignal`, a Python exception internal to this
module (never exposed as a `CinderError`), caught at the call boundary.
`break`/`continue` unwind similarly via `_BreakSignal`/`_ContinueSignal`,
caught by the nearest enclosing `WhileStmt`/`ForStmt`'s own execution (the
parser guarantees they never appear outside a loop, or outside a loop within
the nearest enclosing function, so no other boundary needs to catch them).

A `CinderFunction` wraps either a named `FnDecl` (statement position) or an
anonymous `FnExpr` (expression position, e.g. a callback literal passed
straight to `map`/`filter`) — both carry `params`/`body`, so `call_value`
(the shared entry point for invoking any callable Cinder value, used by both
`_evaluate_call` and stdlib higher-order builtins) doesn't need to
distinguish them.
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
    Stmt,
    Ternary,
    Unary,
    WhileStmt,
)
from cinder.errors import CinderRuntimeError
from cinder.tokens import TokenType

_NUMERIC = (int, float)


class _ReturnSignal(Exception):
    """Internal control-flow signal for `return`; never surfaced to users."""

    def __init__(self, value: object):
        self.value = value


class _BreakSignal(Exception):
    """Internal control-flow signal for `break`; never surfaced to users."""


class _ContinueSignal(Exception):
    """Internal control-flow signal for `continue`; never surfaced to users."""


class CinderFunction:
    """A first-class function value: an `FnDecl`/`FnExpr` plus the `Environment`
    it closed over. `FnExpr` (anonymous functions) have no `name`."""

    def __init__(self, decl: "FnDecl | FnExpr", closure: "Environment"):
        self.decl = decl
        self.closure = closure

    @property
    def name(self) -> str:
        return getattr(self.decl, "name", "<anonymous>")

    @property
    def arity(self) -> int:
        return len(self.decl.params)


class Builtin:
    """A native Python function exposed as a callable Cinder value.

    `fn` receives the already-evaluated argument list plus the call site's
    line/column (for error reporting) and returns the Cinder result.
    """

    def __init__(self, name: str, fn):
        self.name = name
        self._fn = fn

    def call(self, arguments: list, line: int, column: int) -> object:
        return self._fn(arguments, line, column)


class Environment:
    """Maps names to values with a parent pointer for lexical scoping."""

    def __init__(self, parent: "Environment | None" = None):
        self.parent = parent
        self._values: dict[str, object] = {}

    def define(self, name: str, value: object) -> None:
        self._values[name] = value

    def get(self, name: str) -> object:
        env: Environment | None = self
        while env is not None:
            if name in env._values:
                return env._values[name]
            env = env.parent
        raise KeyError(name)

    def assign(self, name: str, value: object) -> None:
        env: Environment | None = self
        while env is not None:
            if name in env._values:
                env._values[name] = value
                return
            env = env.parent
        raise KeyError(name)


def is_truthy(value: object) -> bool:
    """`false` and `nil` are falsy; everything else, including 0 and "", is truthy."""
    return value is not False and value is not None


class Interpreter:
    def evaluate(self, expr: Expr, env: Environment) -> object:
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, Identifier):
            return self._evaluate_identifier(expr, env)
        if isinstance(expr, Grouping):
            return self.evaluate(expr.expression, env)
        if isinstance(expr, Unary):
            return self._evaluate_unary(expr, env)
        if isinstance(expr, Logical):
            return self._evaluate_logical(expr, env)
        if isinstance(expr, Ternary):
            return self._evaluate_ternary(expr, env)
        if isinstance(expr, Binary):
            return self._evaluate_binary(expr, env)
        if isinstance(expr, Assign):
            return self._evaluate_assign(expr, env)
        if isinstance(expr, Call):
            return self._evaluate_call(expr, env)
        if isinstance(expr, ListLiteral):
            return [self.evaluate(element, env) for element in expr.elements]
        if isinstance(expr, MapLiteral):
            return self._evaluate_map_literal(expr, env)
        if isinstance(expr, Index):
            return self._evaluate_index(expr, env)
        if isinstance(expr, IndexAssign):
            return self._evaluate_index_assign(expr, env)
        if isinstance(expr, FnExpr):
            return CinderFunction(expr, env)
        raise TypeError(f"unhandled expression type: {type(expr)!r}")

    def execute(self, stmt: Stmt, env: Environment) -> None:
        if isinstance(stmt, LetStmt):
            env.define(stmt.name, self.evaluate(stmt.initializer, env))
            return
        if isinstance(stmt, ExprStmt):
            self.evaluate(stmt.expression, env)
            return
        if isinstance(stmt, Block):
            block_env = Environment(env)
            for inner in stmt.statements:
                self.execute(inner, block_env)
            return
        if isinstance(stmt, IfStmt):
            if is_truthy(self.evaluate(stmt.condition, env)):
                self.execute(stmt.then_branch, env)
            elif stmt.else_branch is not None:
                self.execute(stmt.else_branch, env)
            return
        if isinstance(stmt, WhileStmt):
            while is_truthy(self.evaluate(stmt.condition, env)):
                try:
                    self.execute(stmt.body, env)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
            return
        if isinstance(stmt, ForStmt):
            self._execute_for(stmt, env)
            return
        if isinstance(stmt, FnDecl):
            env.define(stmt.name, CinderFunction(stmt, env))
            return
        if isinstance(stmt, ReturnStmt):
            value = self.evaluate(stmt.value, env) if stmt.value is not None else None
            raise _ReturnSignal(value)
        if isinstance(stmt, BreakStmt):
            raise _BreakSignal()
        if isinstance(stmt, ContinueStmt):
            raise _ContinueSignal()
        raise TypeError(f"unhandled statement type: {type(stmt)!r}")

    def _execute_for(self, stmt: ForStmt, env: Environment) -> None:
        iterable = self.evaluate(stmt.iterable, env)
        if isinstance(iterable, dict):
            items = list(iterable.keys())
        elif isinstance(iterable, (list, str)):
            items = list(iterable)
        else:
            raise CinderRuntimeError(
                f"'for'-in loop requires a list, string, or map, got {type_name(iterable)}",
                stmt.line,
                stmt.column,
            )
        for item in items:
            iter_env = Environment(env)
            iter_env.define(stmt.var_name, item)
            try:
                self.execute(stmt.body, iter_env)
            except _BreakSignal:
                break
            except _ContinueSignal:
                continue

    def _evaluate_call(self, expr: Call, env: Environment) -> object:
        callee = self.evaluate(expr.callee, env)
        arguments = [self.evaluate(arg, env) for arg in expr.arguments]
        return call_value(callee, arguments, expr.line, expr.column)

    def _evaluate_map_literal(self, expr: MapLiteral, env: Environment) -> object:
        result: dict = {}
        for key_expr, value_expr in expr.pairs:
            key = self.evaluate(key_expr, env)
            if not _is_valid_key(key):
                raise CinderRuntimeError(
                    f"{type_name(key)} is not a valid map key",
                    expr.line,
                    expr.column,
                )
            result[key] = self.evaluate(value_expr, env)
        return result

    def _evaluate_index(self, expr: Index, env: Environment) -> object:
        obj = self.evaluate(expr.obj, env)
        index = self.evaluate(expr.index, env)
        if isinstance(obj, list):
            if not isinstance(index, int) or isinstance(index, bool):
                raise CinderRuntimeError(
                    f"list index must be an int, got {type_name(index)}",
                    expr.line,
                    expr.column,
                )
            normalized = index + len(obj) if index < 0 else index
            if normalized < 0 or normalized >= len(obj):
                raise CinderRuntimeError(
                    f"list index {index} out of range (length {len(obj)})",
                    expr.line,
                    expr.column,
                )
            return obj[normalized]
        if isinstance(obj, dict):
            if not _is_valid_key(index):
                raise CinderRuntimeError(
                    f"{type_name(index)} is not a valid map key",
                    expr.line,
                    expr.column,
                )
            if index not in obj:
                raise CinderRuntimeError(
                    f"missing map key {index!r}", expr.line, expr.column
                )
            return obj[index]
        if isinstance(obj, str):
            if not isinstance(index, int) or isinstance(index, bool):
                raise CinderRuntimeError(
                    f"string index must be an int, got {type_name(index)}",
                    expr.line,
                    expr.column,
                )
            normalized = index + len(obj) if index < 0 else index
            if normalized < 0 or normalized >= len(obj):
                raise CinderRuntimeError(
                    f"string index {index} out of range (length {len(obj)})",
                    expr.line,
                    expr.column,
                )
            return obj[normalized]
        raise CinderRuntimeError(
            f"{type_name(obj)} is not indexable", expr.line, expr.column
        )

    def _evaluate_index_assign(self, expr: IndexAssign, env: Environment) -> object:
        obj = self.evaluate(expr.obj, env)
        index = self.evaluate(expr.index, env)
        value = self.evaluate(expr.value, env)
        if isinstance(obj, list):
            if not isinstance(index, int) or isinstance(index, bool):
                raise CinderRuntimeError(
                    f"list index must be an int, got {type_name(index)}",
                    expr.line,
                    expr.column,
                )
            normalized = index + len(obj) if index < 0 else index
            if normalized < 0 or normalized >= len(obj):
                raise CinderRuntimeError(
                    f"list index {index} out of range (length {len(obj)})",
                    expr.line,
                    expr.column,
                )
            obj[normalized] = value
            return value
        if isinstance(obj, dict):
            if not _is_valid_key(index):
                raise CinderRuntimeError(
                    f"{type_name(index)} is not a valid map key",
                    expr.line,
                    expr.column,
                )
            obj[index] = value
            return value
        if isinstance(obj, str):
            raise CinderRuntimeError(
                "strings are immutable and do not support item assignment",
                expr.line,
                expr.column,
            )
        raise CinderRuntimeError(
            f"{type_name(obj)} does not support item assignment",
            expr.line,
            expr.column,
        )

    def _evaluate_identifier(self, expr: Identifier, env: Environment) -> object:
        try:
            return env.get(expr.name)
        except KeyError:
            raise CinderRuntimeError(
                f"undefined name {expr.name!r}", expr.line, expr.column
            ) from None

    def _evaluate_assign(self, expr: Assign, env: Environment) -> object:
        value = self.evaluate(expr.value, env)
        try:
            env.assign(expr.name, value)
        except KeyError:
            raise CinderRuntimeError(
                f"undefined name {expr.name!r}", expr.line, expr.column
            ) from None
        return value

    def _evaluate_unary(self, expr: Unary, env: Environment) -> object:
        operand = self.evaluate(expr.operand, env)
        if expr.operator.type == TokenType.MINUS:
            if not isinstance(operand, _NUMERIC) or isinstance(operand, bool):
                raise CinderRuntimeError(
                    f"unary '-' requires a number, got {type_name(operand)}",
                    expr.operator.line,
                    expr.operator.column,
                )
            return -operand
        if expr.operator.type == TokenType.NOT:
            return not is_truthy(operand)
        raise TypeError(f"unhandled unary operator: {expr.operator.type!r}")

    def _evaluate_logical(self, expr: Logical, env: Environment) -> object:
        left = self.evaluate(expr.left, env)
        if expr.operator.type == TokenType.OR:
            if is_truthy(left):
                return left
            return self.evaluate(expr.right, env)
        if expr.operator.type == TokenType.AND:
            if not is_truthy(left):
                return left
            return self.evaluate(expr.right, env)
        raise TypeError(f"unhandled logical operator: {expr.operator.type!r}")

    def _evaluate_ternary(self, expr: Ternary, env: Environment) -> object:
        condition = self.evaluate(expr.condition, env)
        if is_truthy(condition):
            return self.evaluate(expr.then_expr, env)
        return self.evaluate(expr.else_expr, env)

    def _evaluate_binary(self, expr: Binary, env: Environment) -> object:
        left = self.evaluate(expr.left, env)
        right = self.evaluate(expr.right, env)
        op = expr.operator.type

        if op == TokenType.PLUS:
            if _is_number(left) and _is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise CinderRuntimeError(
                f"unsupported operand types for '+': {type_name(left)} and {type_name(right)}",
                expr.operator.line,
                expr.operator.column,
            )
        if op == TokenType.MINUS:
            return self._numeric_op(expr, left, right, lambda a, b: a - b)
        if op == TokenType.STAR:
            repeated = self._repeat_op(left, right)
            if repeated is not None:
                return repeated
            return self._numeric_op(expr, left, right, lambda a, b: a * b)
        if op == TokenType.SLASH:
            return self._divide_op(expr, left, right, lambda a, b: a / b)
        if op == TokenType.PERCENT:
            return self._divide_op(expr, left, right, lambda a, b: a % b)

        if op == TokenType.EQEQ:
            return _values_equal(left, right)
        if op == TokenType.BANGEQ:
            return not _values_equal(left, right)
        if op in (TokenType.LT, TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):
            return self._compare(expr, left, right, op)
        if op == TokenType.IN:
            return contains_value(right, left, expr.operator.line, expr.operator.column)

        raise TypeError(f"unhandled binary operator: {op!r}")

    def _repeat_op(self, left, right):
        """str/list * int repetition (either operand order); None if not applicable."""
        if isinstance(left, (str, list)) and _is_int(right):
            return left * right
        if isinstance(right, (str, list)) and _is_int(left):
            return right * left
        return None

    def _numeric_op(self, expr: Binary, left, right, fn):
        if not (_is_number(left) and _is_number(right)):
            raise CinderRuntimeError(
                f"unsupported operand types for {expr.operator.lexeme!r}: "
                f"{type_name(left)} and {type_name(right)}",
                expr.operator.line,
                expr.operator.column,
            )
        return fn(left, right)

    def _divide_op(self, expr: Binary, left, right, fn):
        if not (_is_number(left) and _is_number(right)):
            return self._numeric_op(expr, left, right, fn)
        if right == 0:
            raise CinderRuntimeError(
                f"division by zero in {expr.operator.lexeme!r}",
                expr.operator.line,
                expr.operator.column,
            )
        return fn(left, right)

    def _compare(self, expr: Binary, left, right, op: TokenType) -> bool:
        comparable = (_is_number(left) and _is_number(right)) or (
            isinstance(left, str) and isinstance(right, str)
        )
        if not comparable:
            raise CinderRuntimeError(
                f"unsupported operand types for comparison: "
                f"{type_name(left)} and {type_name(right)}",
                expr.operator.line,
                expr.operator.column,
            )
        if op == TokenType.LT:
            return left < right
        if op == TokenType.LTEQ:
            return left <= right
        if op == TokenType.GT:
            return left > right
        return left >= right


def call_value(callee: object, arguments: list, line: int, column: int) -> object:
    """Invoke a callable Cinder value (`Builtin` or `CinderFunction`) with already-evaluated arguments.

    Shared by `Interpreter._evaluate_call` and any builtin (e.g. `map`/`filter`)
    that needs to invoke a Cinder function value passed to it.
    """
    if isinstance(callee, Builtin):
        return callee.call(arguments, line, column)
    if not isinstance(callee, CinderFunction):
        raise CinderRuntimeError(f"{type_name(callee)} is not callable", line, column)
    if len(arguments) != callee.arity:
        raise CinderRuntimeError(
            f"{callee.name}() expects {callee.arity} argument(s), got {len(arguments)}",
            line,
            column,
        )
    call_env = Environment(callee.closure)
    for param, value in zip(callee.decl.params, arguments):
        call_env.define(param, value)
    try:
        Interpreter().execute(callee.decl.body, call_env)
    except _ReturnSignal as signal:
        return signal.value
    except CinderRuntimeError as error:
        error.frames.append((callee.name, line, column))
        raise
    return None


def _is_number(value: object) -> bool:
    return isinstance(value, _NUMERIC) and not isinstance(value, bool)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_valid_key(value: object) -> bool:
    """Map keys must be an immutable, hashable Cinder value."""
    return value is None or isinstance(value, (int, float, str, bool))


def contains_value(collection: object, item: object, line: int, column: int) -> bool:
    """Membership-test semantics shared by the `in` operator and `contains()`:
    list `==` membership, map key check, string substring check."""
    if isinstance(collection, list):
        return any(item == element for element in collection)
    if isinstance(collection, dict):
        try:
            return item in collection
        except TypeError:
            return False
    if isinstance(collection, str):
        if not isinstance(item, str):
            raise CinderRuntimeError(
                f"membership test on a string requires a string, got {type_name(item)}",
                line,
                column,
            )
        return item in collection
    raise CinderRuntimeError(
        f"membership test requires a list, map, or string, got {type_name(collection)}",
        line,
        column,
    )


def _values_equal(left: object, right: object) -> bool:
    if _is_number(left) and _is_number(right):
        return left == right
    if type(left) is not type(right):
        return False
    return left == right


def type_name(value: object) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "map"
    if isinstance(value, (CinderFunction, Builtin)):
        return "function"
    return type(value).__name__
