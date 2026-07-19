"""Standard library builtins injected into every Cinder program's global scope.

`create_global_environment` returns a fresh `Environment` with `print`,
`len`, `type`, `str`, `int`, and `float` already defined. CLI entrypoints and
the REPL should build their global scope with this instead of a bare
`Environment()` so `.cin` scripts can actually produce output.
"""

from cinder.errors import CinderRuntimeError
from cinder.interpreter import Builtin, Environment, type_name

_NUMERIC = (int, float)


def stringify(value: object, *, quoted: bool = False) -> str:
    """Render a Cinder value as text, matching `print`/`str()` output."""
    if isinstance(value, str):
        return f'"{value}"' if quoted else value
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(stringify(v, quoted=True) for v in value) + "]"
    if isinstance(value, dict):
        pairs = (f"{stringify(k, quoted=True)}: {stringify(v, quoted=True)}" for k, v in value.items())
        return "{" + ", ".join(pairs) + "}"
    return str(value)


def _arity_error(name: str, expected: int, got: int, line: int, column: int) -> CinderRuntimeError:
    return CinderRuntimeError(
        f"{name}() expects {expected} argument(s), got {got}", line, column
    )


def _require_arity(name: str, arguments: list, expected: int, line: int, column: int) -> None:
    if len(arguments) != expected:
        raise _arity_error(name, expected, len(arguments), line, column)


def _print(arguments: list, line: int, column: int) -> object:
    print(" ".join(stringify(arg) for arg in arguments))
    return None


def _len(arguments: list, line: int, column: int) -> object:
    _require_arity("len", arguments, 1, line, column)
    value = arguments[0]
    if isinstance(value, (str, list, dict)):
        return len(value)
    raise CinderRuntimeError(
        f"len() requires a string, list, or map, got {type_name(value)}", line, column
    )


def _type(arguments: list, line: int, column: int) -> object:
    _require_arity("type", arguments, 1, line, column)
    return type_name(arguments[0])


def _str(arguments: list, line: int, column: int) -> object:
    _require_arity("str", arguments, 1, line, column)
    return stringify(arguments[0])


def _int(arguments: list, line: int, column: int) -> object:
    _require_arity("int", arguments, 1, line, column)
    value = arguments[0]
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, _NUMERIC):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise CinderRuntimeError(
                f"int() could not convert string {value!r}", line, column
            ) from None
    raise CinderRuntimeError(
        f"int() requires a number or string, got {type_name(value)}", line, column
    )


def _float(arguments: list, line: int, column: int) -> object:
    _require_arity("float", arguments, 1, line, column)
    value = arguments[0]
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, _NUMERIC):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise CinderRuntimeError(
                f"float() could not convert string {value!r}", line, column
            ) from None
    raise CinderRuntimeError(
        f"float() requires a number or string, got {type_name(value)}", line, column
    )


def _push(arguments: list, line: int, column: int) -> object:
    _require_arity("push", arguments, 2, line, column)
    target, value = arguments
    if not isinstance(target, list):
        raise CinderRuntimeError(
            f"push() requires a list as its first argument, got {type_name(target)}", line, column
        )
    target.append(value)
    return target


def _pop(arguments: list, line: int, column: int) -> object:
    _require_arity("pop", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, list):
        raise CinderRuntimeError(
            f"pop() requires a list, got {type_name(target)}", line, column
        )
    if not target:
        raise CinderRuntimeError("pop() called on an empty list", line, column)
    return target.pop()


def _keys(arguments: list, line: int, column: int) -> object:
    _require_arity("keys", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"keys() requires a map, got {type_name(target)}", line, column
        )
    return list(target.keys())


def _values(arguments: list, line: int, column: int) -> object:
    _require_arity("values", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"values() requires a map, got {type_name(target)}", line, column
        )
    return list(target.values())


_BUILTINS = {
    "print": _print,
    "len": _len,
    "type": _type,
    "str": _str,
    "int": _int,
    "float": _float,
    "push": _push,
    "pop": _pop,
    "keys": _keys,
    "values": _values,
}


def create_global_environment() -> Environment:
    env = Environment()
    for name, fn in _BUILTINS.items():
        env.define(name, Builtin(name, fn))
    return env
