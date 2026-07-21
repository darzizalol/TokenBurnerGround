"""Standard library builtins injected into every Cinder program's global scope.

`create_global_environment` returns a fresh `Environment` with `print`,
`len`, `type`, `str`, `int`, `float`, `push`, `pop`, `keys`, `values`,
`upper`, `lower`, `trim`, `split`, `join`, `find`, `starts_with`, `ends_with`,
`replace`, `abs`, `min`, `max`, `round`, `contains`, `reverse`, `sort`,
`range`, `map`, `filter`, `reduce`, `slice`, `concat`, and `assert` already
defined.
CLI entrypoints and the REPL should build their global scope with this
instead of a bare `Environment()` so `.cin` scripts can actually produce
output.
"""

from cinder.errors import CinderRuntimeError
from cinder.interpreter import (
    Builtin,
    CinderFunction,
    Environment,
    call_value,
    is_truthy,
    type_name,
)

_NUMERIC = (int, float)


def _is_numeric(value: object) -> bool:
    return isinstance(value, _NUMERIC) and not isinstance(value, bool)


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


def _upper(arguments: list, line: int, column: int) -> object:
    _require_arity("upper", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"upper() requires a string, got {type_name(value)}", line, column
        )
    return value.upper()


def _lower(arguments: list, line: int, column: int) -> object:
    _require_arity("lower", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"lower() requires a string, got {type_name(value)}", line, column
        )
    return value.lower()


def _trim(arguments: list, line: int, column: int) -> object:
    _require_arity("trim", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"trim() requires a string, got {type_name(value)}", line, column
        )
    return value.strip()


def _split(arguments: list, line: int, column: int) -> object:
    _require_arity("split", arguments, 2, line, column)
    value, sep = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"split() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(sep, str):
        raise CinderRuntimeError(
            f"split() requires a string separator, got {type_name(sep)}", line, column
        )
    if sep == "":
        raise CinderRuntimeError("split() separator must not be empty", line, column)
    return value.split(sep)


def _join(arguments: list, line: int, column: int) -> object:
    _require_arity("join", arguments, 2, line, column)
    items, sep = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"join() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not isinstance(sep, str):
        raise CinderRuntimeError(
            f"join() requires a string separator, got {type_name(sep)}", line, column
        )
    for item in items:
        if not isinstance(item, str):
            raise CinderRuntimeError(
                f"join() requires a list of strings, got {type_name(item)}", line, column
            )
    return sep.join(items)


def _find(arguments: list, line: int, column: int) -> object:
    _require_arity("find", arguments, 2, line, column)
    value, sub = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"find() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(sub, str):
        raise CinderRuntimeError(
            f"find() requires a string to search for, got {type_name(sub)}", line, column
        )
    return value.find(sub)


def _starts_with(arguments: list, line: int, column: int) -> object:
    _require_arity("starts_with", arguments, 2, line, column)
    value, prefix = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"starts_with() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(prefix, str):
        raise CinderRuntimeError(
            f"starts_with() requires a string prefix, got {type_name(prefix)}", line, column
        )
    return value.startswith(prefix)


def _ends_with(arguments: list, line: int, column: int) -> object:
    _require_arity("ends_with", arguments, 2, line, column)
    value, suffix = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"ends_with() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(suffix, str):
        raise CinderRuntimeError(
            f"ends_with() requires a string suffix, got {type_name(suffix)}", line, column
        )
    return value.endswith(suffix)


def _replace(arguments: list, line: int, column: int) -> object:
    _require_arity("replace", arguments, 3, line, column)
    value, old, new = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"replace() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(old, str):
        raise CinderRuntimeError(
            f"replace() requires a string to search for, got {type_name(old)}", line, column
        )
    if not isinstance(new, str):
        raise CinderRuntimeError(
            f"replace() requires a string replacement, got {type_name(new)}", line, column
        )
    return value.replace(old, new)


def _abs(arguments: list, line: int, column: int) -> object:
    _require_arity("abs", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"abs() requires a number, got {type_name(value)}", line, column
        )
    return abs(value)


def _min(arguments: list, line: int, column: int) -> object:
    if not arguments:
        raise CinderRuntimeError("min() expects at least 1 argument, got 0", line, column)
    for value in arguments:
        if not _is_numeric(value):
            raise CinderRuntimeError(
                f"min() requires numbers, got {type_name(value)}", line, column
            )
    return min(arguments)


def _max(arguments: list, line: int, column: int) -> object:
    if not arguments:
        raise CinderRuntimeError("max() expects at least 1 argument, got 0", line, column)
    for value in arguments:
        if not _is_numeric(value):
            raise CinderRuntimeError(
                f"max() requires numbers, got {type_name(value)}", line, column
            )
    return max(arguments)


def _round(arguments: list, line: int, column: int) -> object:
    _require_arity("round", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"round() requires a number, got {type_name(value)}", line, column
        )
    return round(value)


def _contains(arguments: list, line: int, column: int) -> object:
    _require_arity("contains", arguments, 2, line, column)
    collection, item = arguments
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
                f"contains() on a string requires a string to search for, got {type_name(item)}",
                line, column,
            )
        return item in collection
    raise CinderRuntimeError(
        f"contains() requires a list, map, or string, got {type_name(collection)}", line, column
    )


def _reverse(arguments: list, line: int, column: int) -> object:
    _require_arity("reverse", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"reverse() requires a list, got {type_name(value)}", line, column
        )
    return list(reversed(value))


def _range(arguments: list, line: int, column: int) -> object:
    if len(arguments) == 1:
        start, stop = 0, arguments[0]
    elif len(arguments) == 2:
        start, stop = arguments
    else:
        raise CinderRuntimeError(
            f"range() expects 1 or 2 argument(s), got {len(arguments)}", line, column
        )
    for value in (start, stop):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"range() requires int arguments, got {type_name(value)}", line, column
            )
    return list(range(start, stop))


def _sort(arguments: list, line: int, column: int) -> object:
    _require_arity("sort", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"sort() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        return []
    if all(_is_numeric(element) for element in value):
        return sorted(value)
    if all(isinstance(element, str) for element in value):
        return sorted(value)
    raise CinderRuntimeError(
        "sort() requires a list of all numbers or all strings", line, column
    )


def _normalize_slice_bound(value: int, length: int) -> int:
    if value < 0:
        value += length
    return max(0, min(value, length))


def _slice(arguments: list, line: int, column: int) -> object:
    _require_arity("slice", arguments, 3, line, column)
    value, start, end = arguments
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"slice() requires a list as its first argument, got {type_name(value)}",
            line, column,
        )
    for bound in (start, end):
        if not isinstance(bound, int) or isinstance(bound, bool):
            raise CinderRuntimeError(
                f"slice() requires int bounds, got {type_name(bound)}", line, column
            )
    length = len(value)
    start = _normalize_slice_bound(start, length)
    end = _normalize_slice_bound(end, length)
    return value[start:end]


def _concat(arguments: list, line: int, column: int) -> object:
    _require_arity("concat", arguments, 2, line, column)
    list1, list2 = arguments
    if not isinstance(list1, list):
        raise CinderRuntimeError(
            f"concat() requires a list as its first argument, got {type_name(list1)}",
            line, column,
        )
    if not isinstance(list2, list):
        raise CinderRuntimeError(
            f"concat() requires a list as its second argument, got {type_name(list2)}",
            line, column,
        )
    return list1 + list2


def _assert(arguments: list, line: int, column: int) -> object:
    _require_arity("assert", arguments, 2, line, column)
    condition, message = arguments
    if not isinstance(message, str):
        raise CinderRuntimeError(
            f"assert() requires a string message, got {type_name(message)}", line, column
        )
    if not is_truthy(condition):
        raise CinderRuntimeError(message, line, column)
    return None


def _is_callable(value: object) -> bool:
    return isinstance(value, (CinderFunction, Builtin))


def _map(arguments: list, line: int, column: int) -> object:
    _require_arity("map", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"map() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"map() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    return [call_value(fn, [item], line, column) for item in items]


def _filter(arguments: list, line: int, column: int) -> object:
    _require_arity("filter", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"filter() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"filter() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    return [item for item in items if is_truthy(call_value(fn, [item], line, column))]


def _reduce(arguments: list, line: int, column: int) -> object:
    _require_arity("reduce", arguments, 3, line, column)
    items, fn, initial = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"reduce() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"reduce() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    acc = initial
    for item in items:
        acc = call_value(fn, [acc, item], line, column)
    return acc


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
    "upper": _upper,
    "lower": _lower,
    "trim": _trim,
    "split": _split,
    "join": _join,
    "find": _find,
    "starts_with": _starts_with,
    "ends_with": _ends_with,
    "replace": _replace,
    "abs": _abs,
    "min": _min,
    "max": _max,
    "round": _round,
    "contains": _contains,
    "reverse": _reverse,
    "sort": _sort,
    "range": _range,
    "map": _map,
    "filter": _filter,
    "reduce": _reduce,
    "slice": _slice,
    "concat": _concat,
    "assert": _assert,
}


def create_global_environment() -> Environment:
    env = Environment()
    for name, fn in _BUILTINS.items():
        env.define(name, Builtin(name, fn))
    return env
