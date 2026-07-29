"""Standard library builtins injected into every Cinder program's global scope.

`create_global_environment` returns a fresh `Environment` with `print`,
`len`, `is_empty`, `type`, `str`, `int`, `float`, `ord`, `chr`, `push`, `pop`, `insert`, `remove_at`,
`keys`, `values`, `items`, `get`, `remove`, `merge`, `upper`, `lower`, `trim`, `split`, `lines`, `words`, `join`, `find`,
`starts_with`, `ends_with`, `replace`, `abs`, `min`, `max`, `round`, `floor`,
`ceil`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `log`, `gcd`, `lcm`, `sum`, `mean`, `median`,
`any`, `all`, `contains`, `copy`, `unique`, `reverse`, `sort`, `sort_by`, `range`, `map`,
`filter`, `reduce`, `slice`, `concat`, `flatten`, `zip`, `assert`, `format`, `is_list`, `is_map`,
`is_string`, `is_number`, `is_bool`, `is_nil`, and `is_function` already
defined. CLI entrypoints and the REPL should build their global scope with
this instead of a bare `Environment()` so `.cin` scripts can actually produce
output.
"""

import math
import random

from cinder.errors import CinderRuntimeError
from cinder.interpreter import (
    Builtin,
    CinderFunction,
    Environment,
    _is_valid_key,
    _normalize_slice_bound,
    call_value,
    contains_value,
    is_truthy,
    normalize_index,
    stringify,
    type_name,
    values_equal,
)

_NUMERIC = (int, float)


def _is_numeric(value: object) -> bool:
    return isinstance(value, _NUMERIC) and not isinstance(value, bool)


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


def _is_empty(arguments: list, line: int, column: int) -> object:
    _require_arity("is_empty", arguments, 1, line, column)
    value = arguments[0]
    if isinstance(value, (str, list, dict)):
        return len(value) == 0
    raise CinderRuntimeError(
        f"is_empty() requires a string, list, or map, got {type_name(value)}", line, column
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


def _ord(arguments: list, line: int, column: int) -> object:
    _require_arity("ord", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"ord() requires a string, got {type_name(value)}", line, column
        )
    if len(value) != 1:
        raise CinderRuntimeError(
            f"ord() requires a string of length 1, got length {len(value)}", line, column
        )
    return ord(value)


def _chr(arguments: list, line: int, column: int) -> object:
    _require_arity("chr", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, int) or isinstance(value, bool):
        raise CinderRuntimeError(
            f"chr() requires an int, got {type_name(value)}", line, column
        )
    try:
        return chr(value)
    except ValueError:
        raise CinderRuntimeError(
            f"chr() requires a code point between 0 and 0x10FFFF, got {value}", line, column
        ) from None


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


def _insert(arguments: list, line: int, column: int) -> object:
    _require_arity("insert", arguments, 3, line, column)
    target, index, value = arguments
    if not isinstance(target, list):
        raise CinderRuntimeError(
            f"insert() requires a list as its first argument, got {type_name(target)}",
            line, column,
        )
    if not isinstance(index, int) or isinstance(index, bool):
        raise CinderRuntimeError(
            f"insert() requires an int index, got {type_name(index)}", line, column
        )
    length = len(target)
    normalized = normalize_index(index, length)
    if normalized < 0 or normalized > length:
        raise CinderRuntimeError(
            f"insert() index {index} out of range (length {length})", line, column
        )
    target.insert(normalized, value)
    return None


def _remove_at(arguments: list, line: int, column: int) -> object:
    _require_arity("remove_at", arguments, 2, line, column)
    target, index = arguments
    if not isinstance(target, list):
        raise CinderRuntimeError(
            f"remove_at() requires a list, got {type_name(target)}", line, column
        )
    if not isinstance(index, int) or isinstance(index, bool):
        raise CinderRuntimeError(
            f"remove_at() requires an int index, got {type_name(index)}", line, column
        )
    length = len(target)
    normalized = normalize_index(index, length)
    if normalized < 0 or normalized >= length:
        raise CinderRuntimeError(
            f"remove_at() index {index} out of range (length {length})", line, column
        )
    return target.pop(normalized)


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


def _items(arguments: list, line: int, column: int) -> object:
    _require_arity("items", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"items() requires a map, got {type_name(target)}", line, column
        )
    return [[key, value] for key, value in target.items()]


def _get(arguments: list, line: int, column: int) -> object:
    _require_arity("get", arguments, 3, line, column)
    target, key, default = arguments
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"get() requires a map, got {type_name(target)}", line, column
        )
    if not _is_valid_key(key):
        raise CinderRuntimeError(
            f"{type_name(key)} is not a valid map key", line, column
        )
    if key not in target:
        return default
    return target[key]


def _pluck(arguments: list, line: int, column: int) -> object:
    _require_arity("pluck", arguments, 2, line, column)
    items, key = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"pluck() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_valid_key(key):
        raise CinderRuntimeError(
            f"{type_name(key)} is not a valid map key", line, column
        )
    result: list = []
    for item in items:
        if not isinstance(item, dict):
            raise CinderRuntimeError(
                f"pluck() requires a list of maps, got {type_name(item)}",
                line, column,
            )
        if key not in item:
            raise CinderRuntimeError(f"missing map key {key!r}", line, column)
        result.append(item[key])
    return result


def _remove(arguments: list, line: int, column: int) -> object:
    _require_arity("remove", arguments, 2, line, column)
    target, key = arguments
    if isinstance(target, list):
        for index, element in enumerate(target):
            if values_equal(element, key):
                return target.pop(index)
        raise CinderRuntimeError(f"value not found in list: {key!r}", line, column)
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"remove() requires a list or map, got {type_name(target)}", line, column
        )
    if not _is_valid_key(key):
        raise CinderRuntimeError(
            f"{type_name(key)} is not a valid map key", line, column
        )
    if key not in target:
        raise CinderRuntimeError(f"missing map key {key!r}", line, column)
    return target.pop(key)


def _merge(arguments: list, line: int, column: int) -> object:
    _require_arity("merge", arguments, 2, line, column)
    map1, map2 = arguments
    if not isinstance(map1, dict):
        raise CinderRuntimeError(
            f"merge() requires a map, got {type_name(map1)}", line, column
        )
    if not isinstance(map2, dict):
        raise CinderRuntimeError(
            f"merge() requires a map, got {type_name(map2)}", line, column
        )
    result = dict(map1)
    result.update(map2)
    return result


def _invert(arguments: list, line: int, column: int) -> object:
    _require_arity("invert", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"invert() requires a map, got {type_name(target)}", line, column
        )
    result: dict = {}
    for key, value in target.items():
        if not _is_valid_key(value):
            raise CinderRuntimeError(
                f"{type_name(value)} is not a valid map key", line, column
            )
        result[value] = key
    return result


def _pick(arguments: list, line: int, column: int) -> object:
    _require_arity("pick", arguments, 2, line, column)
    target, keys = arguments
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"pick() requires a map, got {type_name(target)}", line, column
        )
    if not isinstance(keys, list):
        raise CinderRuntimeError(
            f"pick() requires a list of keys, got {type_name(keys)}", line, column
        )
    result: dict = {}
    for key in keys:
        if _is_valid_key(key) and key in target:
            result[key] = target[key]
    return result


def _omit(arguments: list, line: int, column: int) -> object:
    _require_arity("omit", arguments, 2, line, column)
    target, keys = arguments
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"omit() requires a map, got {type_name(target)}", line, column
        )
    if not isinstance(keys, list):
        raise CinderRuntimeError(
            f"omit() requires a list of keys, got {type_name(keys)}", line, column
        )
    return {key: value for key, value in target.items() if key not in keys}


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


def _capitalize(arguments: list, line: int, column: int) -> object:
    _require_arity("capitalize", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"capitalize() requires a string, got {type_name(value)}", line, column
        )
    if not value:
        return value
    return value[0].upper() + value[1:]


def _title(arguments: list, line: int, column: int) -> object:
    _require_arity("title", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"title() requires a string, got {type_name(value)}", line, column
        )
    result = []
    at_word_start = True
    for ch in value:
        if ch.isspace():
            at_word_start = True
            result.append(ch)
        elif at_word_start and ch.isalpha():
            result.append(ch.upper())
            at_word_start = False
        else:
            result.append(ch)
    return "".join(result)


def _trim(arguments: list, line: int, column: int) -> object:
    _require_arity("trim", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"trim() requires a string, got {type_name(value)}", line, column
        )
    return value.strip()


def _trim_start(arguments: list, line: int, column: int) -> object:
    _require_arity("trim_start", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"trim_start() requires a string, got {type_name(value)}", line, column
        )
    return value.lstrip()


def _trim_end(arguments: list, line: int, column: int) -> object:
    _require_arity("trim_end", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"trim_end() requires a string, got {type_name(value)}", line, column
        )
    return value.rstrip()


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


def _lines(arguments: list, line: int, column: int) -> object:
    _require_arity("lines", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"lines() requires a string, got {type_name(value)}", line, column
        )
    return value.split("\n")


def _words(arguments: list, line: int, column: int) -> object:
    _require_arity("words", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"words() requires a string, got {type_name(value)}", line, column
        )
    return value.split()


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


def _strip_prefix(arguments: list, line: int, column: int) -> object:
    _require_arity("strip_prefix", arguments, 2, line, column)
    value, prefix = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"strip_prefix() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(prefix, str):
        raise CinderRuntimeError(
            f"strip_prefix() requires a string prefix, got {type_name(prefix)}", line, column
        )
    return value.removeprefix(prefix)


def _strip_suffix(arguments: list, line: int, column: int) -> object:
    _require_arity("strip_suffix", arguments, 2, line, column)
    value, suffix = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"strip_suffix() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(suffix, str):
        raise CinderRuntimeError(
            f"strip_suffix() requires a string suffix, got {type_name(suffix)}", line, column
        )
    return value.removesuffix(suffix)


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


def _check_pad_arguments(name: str, value: object, width: object, fill: object, line: int, column: int) -> None:
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"{name}() requires a string as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(width, int) or isinstance(width, bool):
        raise CinderRuntimeError(
            f"{name}() requires an int width, got {type_name(width)}", line, column
        )
    if width < 0:
        raise CinderRuntimeError(f"{name}() width must not be negative, got {width}", line, column)
    if not isinstance(fill, str) or len(fill) != 1:
        raise CinderRuntimeError(
            f"{name}() requires a single-character fill string, got {fill!r}", line, column
        )


def _pad_start(arguments: list, line: int, column: int) -> object:
    _require_arity("pad_start", arguments, 3, line, column)
    value, width, fill = arguments
    _check_pad_arguments("pad_start", value, width, fill, line, column)
    if len(value) >= width:
        return value
    return fill * (width - len(value)) + value


def _pad_end(arguments: list, line: int, column: int) -> object:
    _require_arity("pad_end", arguments, 3, line, column)
    value, width, fill = arguments
    _check_pad_arguments("pad_end", value, width, fill, line, column)
    if len(value) >= width:
        return value
    return value + fill * (width - len(value))


def _abs(arguments: list, line: int, column: int) -> object:
    _require_arity("abs", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"abs() requires a number, got {type_name(value)}", line, column
        )
    return abs(value)


def _sign(arguments: list, line: int, column: int) -> object:
    _require_arity("sign", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"sign() requires a number, got {type_name(value)}", line, column
        )
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


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


def _clamp(arguments: list, line: int, column: int) -> object:
    _require_arity("clamp", arguments, 3, line, column)
    n, lo, hi = arguments
    for position, value in (("first", n), ("second", lo), ("third", hi)):
        if not _is_numeric(value):
            raise CinderRuntimeError(
                f"clamp() requires a number as its {position} argument, got {type_name(value)}",
                line, column,
            )
    if lo > hi:
        raise CinderRuntimeError(
            f"clamp() requires lo <= hi, got lo={lo}, hi={hi}", line, column
        )
    if n < lo:
        return lo
    if n > hi:
        return hi
    return n


def _round(arguments: list, line: int, column: int) -> object:
    if len(arguments) == 0:
        raise _arity_error("round", 1, 0, line, column)
    if len(arguments) > 2:
        raise _arity_error("round", 2, len(arguments), line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"round() requires a number, got {type_name(value)}", line, column
        )
    if len(arguments) == 1:
        return round(value)
    digits = arguments[1]
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise CinderRuntimeError(
            f"round() requires an int digits argument, got {type_name(digits)}",
            line, column,
        )
    if digits < 0:
        raise CinderRuntimeError(
            f"round() requires digits >= 0, got {digits}", line, column
        )
    return round(value, digits)


def _floor(arguments: list, line: int, column: int) -> object:
    _require_arity("floor", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"floor() requires a number, got {type_name(value)}", line, column
        )
    return math.floor(value)


def _ceil(arguments: list, line: int, column: int) -> object:
    _require_arity("ceil", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"ceil() requires a number, got {type_name(value)}", line, column
        )
    return math.ceil(value)


def _pow(arguments: list, line: int, column: int) -> object:
    _require_arity("pow", arguments, 2, line, column)
    base, exp = arguments
    if not _is_numeric(base):
        raise CinderRuntimeError(
            f"pow() requires a number as its first argument, got {type_name(base)}",
            line, column,
        )
    if not _is_numeric(exp):
        raise CinderRuntimeError(
            f"pow() requires a number as its second argument, got {type_name(exp)}",
            line, column,
        )
    try:
        result = base ** exp
    except ZeroDivisionError:
        raise CinderRuntimeError(
            "pow() cannot raise zero to a negative power", line, column
        ) from None
    except OverflowError:
        raise CinderRuntimeError("pow() result is too large", line, column) from None
    if isinstance(result, complex):
        raise CinderRuntimeError(
            "pow() requires a non-negative base for fractional exponents, "
            "no complex numbers",
            line, column,
        )
    return result


def _sqrt(arguments: list, line: int, column: int) -> object:
    _require_arity("sqrt", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"sqrt() requires a number, got {type_name(value)}", line, column
        )
    if value < 0:
        raise CinderRuntimeError(
            "sqrt() requires a non-negative number, no complex numbers", line, column
        )
    return math.sqrt(value)


def _sin(arguments: list, line: int, column: int) -> object:
    _require_arity("sin", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"sin() requires a number, got {type_name(value)}", line, column
        )
    return math.sin(value)


def _cos(arguments: list, line: int, column: int) -> object:
    _require_arity("cos", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"cos() requires a number, got {type_name(value)}", line, column
        )
    return math.cos(value)


def _tan(arguments: list, line: int, column: int) -> object:
    _require_arity("tan", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"tan() requires a number, got {type_name(value)}", line, column
        )
    return math.tan(value)


def _log(arguments: list, line: int, column: int) -> object:
    _require_arity("log", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"log() requires a number, got {type_name(value)}", line, column
        )
    if value <= 0:
        raise CinderRuntimeError(
            "log() requires a positive number, domain error", line, column
        )
    return math.log(value)


def _gcd(arguments: list, line: int, column: int) -> object:
    _require_arity("gcd", arguments, 2, line, column)
    a, b = arguments
    for position, value in (("first", a), ("second", b)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"gcd() requires an int as its {position} argument, got {type_name(value)}",
                line, column,
            )
    return math.gcd(a, b)


def _lcm(arguments: list, line: int, column: int) -> object:
    _require_arity("lcm", arguments, 2, line, column)
    a, b = arguments
    for position, value in (("first", a), ("second", b)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"lcm() requires an int as its {position} argument, got {type_name(value)}",
                line, column,
            )
    return math.lcm(a, b)


def _sum(arguments: list, line: int, column: int) -> object:
    _require_arity("sum", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"sum() requires a list, got {type_name(value)}", line, column
        )
    total = 0
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"sum() requires a list of numbers, got {type_name(element)}", line, column
            )
        total = total + element
    return total


def _mean(arguments: list, line: int, column: int) -> object:
    _require_arity("mean", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"mean() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("mean() requires a non-empty list", line, column)
    total = 0
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"mean() requires a list of numbers, got {type_name(element)}", line, column
            )
        total = total + element
    return total / len(value)


def _median(arguments: list, line: int, column: int) -> object:
    _require_arity("median", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"median() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("median() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"median() requires a list of numbers, got {type_name(element)}", line, column
            )
    ordered = sorted(value)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _any(arguments: list, line: int, column: int) -> object:
    _require_arity("any", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"any() requires a list, got {type_name(value)}", line, column
        )
    return any(is_truthy(element) for element in value)


def _all(arguments: list, line: int, column: int) -> object:
    _require_arity("all", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"all() requires a list, got {type_name(value)}", line, column
        )
    return all(is_truthy(element) for element in value)


def _contains(arguments: list, line: int, column: int) -> object:
    _require_arity("contains", arguments, 2, line, column)
    collection, item = arguments
    return contains_value(collection, item, line, column)


def _index_of(arguments: list, line: int, column: int) -> object:
    _require_arity("index_of", arguments, 2, line, column)
    collection, item = arguments
    if not isinstance(collection, list):
        raise CinderRuntimeError(
            f"index_of() requires a list, got {type_name(collection)}", line, column
        )
    for index, element in enumerate(collection):
        if values_equal(element, item):
            return index
    return -1


def _last_index_of(arguments: list, line: int, column: int) -> object:
    _require_arity("last_index_of", arguments, 2, line, column)
    collection, item = arguments
    if not isinstance(collection, list):
        raise CinderRuntimeError(
            f"last_index_of() requires a list, got {type_name(collection)}", line, column
        )
    for index in range(len(collection) - 1, -1, -1):
        if values_equal(collection[index], item):
            return index
    return -1


def _find_index(arguments: list, line: int, column: int) -> object:
    _require_arity("find_index", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"find_index() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"find_index() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    for index, item in enumerate(items):
        if is_truthy(call_value(fn, [item], line, column)):
            return index
    return -1


def _count(arguments: list, line: int, column: int) -> object:
    _require_arity("count", arguments, 2, line, column)
    collection, item = arguments
    if not isinstance(collection, list):
        raise CinderRuntimeError(
            f"count() requires a list, got {type_name(collection)}", line, column
        )
    return sum(1 for element in collection if values_equal(element, item))


def _dedupe(value: list) -> list:
    if all(_is_valid_key(element) for element in value):
        # Key on (is_bool, element) rather than element directly: Python's
        # native hash/eq treat `1 == True`, but Cinder's `==` (`values_equal`)
        # does not, so a bare `set` would wrongly conflate them.
        seen: set = set()
        result = []
        for element in value:
            key = (isinstance(element, bool), element)
            if key not in seen:
                seen.add(key)
                result.append(element)
        return result
    result = []
    for element in value:
        if not any(values_equal(element, kept) for kept in result):
            result.append(element)
    return result


def _unique(arguments: list, line: int, column: int) -> object:
    _require_arity("unique", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"unique() requires a list, got {type_name(value)}", line, column
        )
    return _dedupe(value)


def _require_two_lists(name: str, arguments: list, line: int, column: int) -> tuple:
    _require_arity(name, arguments, 2, line, column)
    list1, list2 = arguments
    if not isinstance(list1, list):
        raise CinderRuntimeError(
            f"{name}() requires a list as its first argument, got {type_name(list1)}",
            line, column,
        )
    if not isinstance(list2, list):
        raise CinderRuntimeError(
            f"{name}() requires a list as its second argument, got {type_name(list2)}",
            line, column,
        )
    return list1, list2


def _contains_value(collection: list, item: object) -> bool:
    return any(values_equal(item, element) for element in collection)


def _union(arguments: list, line: int, column: int) -> object:
    list1, list2 = _require_two_lists("union", arguments, line, column)
    return _dedupe(list1 + list2)


def _intersection(arguments: list, line: int, column: int) -> object:
    list1, list2 = _require_two_lists("intersection", arguments, line, column)
    return [
        element for element in _dedupe(list1) if _contains_value(list2, element)
    ]


def _difference(arguments: list, line: int, column: int) -> object:
    list1, list2 = _require_two_lists("difference", arguments, line, column)
    return [
        element for element in _dedupe(list1) if not _contains_value(list2, element)
    ]


def _reverse(arguments: list, line: int, column: int) -> object:
    _require_arity("reverse", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"reverse() requires a list, got {type_name(value)}", line, column
        )
    return list(reversed(value))


def _copy(arguments: list, line: int, column: int) -> object:
    _require_arity("copy", arguments, 1, line, column)
    value = arguments[0]
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    raise CinderRuntimeError(
        f"copy() requires a list or map, got {type_name(value)}", line, column
    )


def _deep_copy_value(value: object) -> object:
    if isinstance(value, list):
        return [_deep_copy_value(element) for element in value]
    if isinstance(value, dict):
        return {key: _deep_copy_value(val) for key, val in value.items()}
    return value


def _deep_copy(arguments: list, line: int, column: int) -> object:
    _require_arity("deep_copy", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, (list, dict)):
        raise CinderRuntimeError(
            f"deep_copy() requires a list or map, got {type_name(value)}", line, column
        )
    return _deep_copy_value(value)


def _first(arguments: list, line: int, column: int) -> object:
    _require_arity("first", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"first() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("first() called on an empty list", line, column)
    return value[0]


def _last(arguments: list, line: int, column: int) -> object:
    _require_arity("last", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"last() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("last() called on an empty list", line, column)
    return value[-1]


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


def _repeat(arguments: list, line: int, column: int) -> object:
    _require_arity("repeat", arguments, 2, line, column)
    value, n = arguments
    if not isinstance(n, int) or isinstance(n, bool):
        raise CinderRuntimeError(
            f"repeat() requires an int as its second argument, got {type_name(n)}", line, column
        )
    if n < 0:
        raise CinderRuntimeError("repeat() requires a non-negative n", line, column)
    return [value] * n


def _random_int(arguments: list, line: int, column: int) -> object:
    _require_arity("random_int", arguments, 2, line, column)
    minimum, maximum = arguments
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        raise CinderRuntimeError(
            f"random_int() requires an int as its first argument, got {type_name(minimum)}",
            line,
            column,
        )
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        raise CinderRuntimeError(
            f"random_int() requires an int as its second argument, got {type_name(maximum)}",
            line,
            column,
        )
    if minimum > maximum:
        raise CinderRuntimeError(
            "random_int() requires min <= max", line, column
        )
    return random.randint(minimum, maximum)


def _random_choice(arguments: list, line: int, column: int) -> object:
    _require_arity("random_choice", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"random_choice() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError(
            "random_choice() requires a non-empty list", line, column
        )
    return random.choice(value)


def _shuffle(arguments: list, line: int, column: int) -> object:
    _require_arity("shuffle", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"shuffle() requires a list, got {type_name(value)}", line, column
        )
    return random.sample(value, len(value))


def _sample(arguments: list, line: int, column: int) -> object:
    _require_arity("sample", arguments, 2, line, column)
    value, n = arguments
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"sample() requires a list, got {type_name(value)}", line, column
        )
    if not isinstance(n, int) or isinstance(n, bool):
        raise CinderRuntimeError(
            f"sample() requires an int as its second argument, got {type_name(n)}", line, column
        )
    if n < 0:
        raise CinderRuntimeError("sample() requires a non-negative n", line, column)
    if n > len(value):
        raise CinderRuntimeError(
            "sample() n cannot exceed the list length", line, column
        )
    return random.sample(value, n)


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


def _sort_by(arguments: list, line: int, column: int) -> object:
    _require_arity("sort_by", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"sort_by() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"sort_by() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    if not items:
        return []
    keys = [call_value(fn, [item], line, column) for item in items]
    if not (all(_is_numeric(key) for key in keys) or all(isinstance(key, str) for key in keys)):
        raise CinderRuntimeError(
            "sort_by() requires a function returning all numbers or all strings", line, column
        )
    return [item for _, item in sorted(zip(keys, items), key=lambda pair: pair[0])]


def _min_max_by(name: str, arguments: list, line: int, column: int, *, want_min: bool) -> object:
    _require_arity(name, arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"{name}() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"{name}() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    if not items:
        raise CinderRuntimeError(f"{name}() requires a non-empty list", line, column)
    keys = [call_value(fn, [item], line, column) for item in items]
    if not (all(_is_numeric(key) for key in keys) or all(isinstance(key, str) for key in keys)):
        raise CinderRuntimeError(
            f"{name}() requires a function returning all numbers or all strings", line, column
        )
    best_item, best_key = items[0], keys[0]
    for item, key in zip(items[1:], keys[1:]):
        if (key < best_key) if want_min else (key > best_key):
            best_item, best_key = item, key
    return best_item


def _min_by(arguments: list, line: int, column: int) -> object:
    return _min_max_by("min_by", arguments, line, column, want_min=True)


def _max_by(arguments: list, line: int, column: int) -> object:
    return _min_max_by("max_by", arguments, line, column, want_min=False)


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


def _take(arguments: list, line: int, column: int) -> object:
    _require_arity("take", arguments, 2, line, column)
    value, n = arguments
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"take() requires a list as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(n, int) or isinstance(n, bool):
        raise CinderRuntimeError(
            f"take() requires an int as its second argument, got {type_name(n)}",
            line, column,
        )
    if n < 0:
        raise CinderRuntimeError("take() requires a non-negative n", line, column)
    end = _normalize_slice_bound(n, len(value))
    return value[0:end]


def _drop(arguments: list, line: int, column: int) -> object:
    _require_arity("drop", arguments, 2, line, column)
    value, n = arguments
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"drop() requires a list as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(n, int) or isinstance(n, bool):
        raise CinderRuntimeError(
            f"drop() requires an int as its second argument, got {type_name(n)}",
            line, column,
        )
    if n < 0:
        raise CinderRuntimeError("drop() requires a non-negative n", line, column)
    start = _normalize_slice_bound(n, len(value))
    return value[start:len(value)]


def _take_while(arguments: list, line: int, column: int) -> object:
    _require_arity("take_while", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"take_while() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"take_while() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    result = []
    for item in items:
        if not is_truthy(call_value(fn, [item], line, column)):
            break
        result.append(item)
    return result


def _drop_while(arguments: list, line: int, column: int) -> object:
    _require_arity("drop_while", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"drop_while() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"drop_while() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    index = 0
    while index < len(items) and is_truthy(call_value(fn, [items[index]], line, column)):
        index += 1
    return items[index:]


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


def _flatten(arguments: list, line: int, column: int) -> object:
    _require_arity("flatten", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"flatten() requires a list, got {type_name(value)}", line, column
        )
    result = []
    for element in value:
        if isinstance(element, list):
            result.extend(element)
        else:
            result.append(element)
    return result


def _flatten_deep_recurse(value: list) -> list:
    result = []
    for element in value:
        if isinstance(element, list):
            result.extend(_flatten_deep_recurse(element))
        else:
            result.append(element)
    return result


def _flatten_deep(arguments: list, line: int, column: int) -> object:
    _require_arity("flatten_deep", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"flatten_deep() requires a list, got {type_name(value)}", line, column
        )
    return _flatten_deep_recurse(value)


def _flat_map(arguments: list, line: int, column: int) -> object:
    _require_arity("flat_map", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"flat_map() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"flat_map() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    result = []
    for item in items:
        mapped = call_value(fn, [item], line, column)
        if isinstance(mapped, list):
            result.extend(mapped)
        else:
            result.append(mapped)
    return result


def _chunk(arguments: list, line: int, column: int) -> object:
    _require_arity("chunk", arguments, 2, line, column)
    value, size = arguments
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"chunk() requires a list as its first argument, got {type_name(value)}",
            line, column,
        )
    if not isinstance(size, int) or isinstance(size, bool):
        raise CinderRuntimeError(
            f"chunk() requires an int size, got {type_name(size)}", line, column
        )
    if size <= 0:
        raise CinderRuntimeError(
            f"chunk() requires a positive size, got {size}", line, column
        )
    return [value[i:i + size] for i in range(0, len(value), size)]


def _zip(arguments: list, line: int, column: int) -> object:
    _require_arity("zip", arguments, 2, line, column)
    list1, list2 = arguments
    if not isinstance(list1, list):
        raise CinderRuntimeError(
            f"zip() requires a list as its first argument, got {type_name(list1)}",
            line, column,
        )
    if not isinstance(list2, list):
        raise CinderRuntimeError(
            f"zip() requires a list as its second argument, got {type_name(list2)}",
            line, column,
        )
    return [[a, b] for a, b in zip(list1, list2)]


def _zip_with(arguments: list, line: int, column: int) -> object:
    _require_arity("zip_with", arguments, 3, line, column)
    list1, list2, fn = arguments
    if not isinstance(list1, list):
        raise CinderRuntimeError(
            f"zip_with() requires a list as its first argument, got {type_name(list1)}",
            line, column,
        )
    if not isinstance(list2, list):
        raise CinderRuntimeError(
            f"zip_with() requires a list as its second argument, got {type_name(list2)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"zip_with() requires a function as its third argument, got {type_name(fn)}",
            line, column,
        )
    return [call_value(fn, [a, b], line, column) for a, b in zip(list1, list2)]


def _enumerate(arguments: list, line: int, column: int) -> object:
    _require_arity("enumerate", arguments, 1, line, column)
    target = arguments[0]
    if not isinstance(target, list):
        raise CinderRuntimeError(
            f"enumerate() requires a list, got {type_name(target)}", line, column
        )
    return [[index, value] for index, value in enumerate(target)]


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


def _format(arguments: list, line: int, column: int) -> object:
    if not arguments:
        raise CinderRuntimeError("format() expects at least 1 argument, got 0", line, column)
    template, extra = arguments[0], arguments[1:]
    if not isinstance(template, str):
        raise CinderRuntimeError(
            f"format() requires a string template, got {type_name(template)}", line, column
        )
    parts: list = []
    placeholder_count = 0
    i = 0
    length = len(template)
    while i < length:
        ch = template[i]
        if ch == "{":
            if i + 1 < length and template[i + 1] == "}":
                parts.append(None)
                placeholder_count += 1
                i += 2
                continue
            raise CinderRuntimeError(
                "format() template has a '{' that isn't a valid '{}' placeholder",
                line, column,
            )
        parts.append(ch)
        i += 1
    if placeholder_count != len(extra):
        raise CinderRuntimeError(
            f"format() template has {placeholder_count} {{}} placeholder(s) but got "
            f"{len(extra)} argument(s)",
            line, column,
        )
    result = []
    arg_index = 0
    for part in parts:
        if part is None:
            result.append(stringify(extra[arg_index]))
            arg_index += 1
        else:
            result.append(part)
    return "".join(result)


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


def _map_values(arguments: list, line: int, column: int) -> object:
    _require_arity("map_values", arguments, 2, line, column)
    target, fn = arguments
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"map_values() requires a map as its first argument, got {type_name(target)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"map_values() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    return {key: call_value(fn, [value], line, column) for key, value in target.items()}


def _map_keys(arguments: list, line: int, column: int) -> object:
    _require_arity("map_keys", arguments, 2, line, column)
    target, fn = arguments
    if not isinstance(target, dict):
        raise CinderRuntimeError(
            f"map_keys() requires a map as its first argument, got {type_name(target)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"map_keys() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    result: dict = {}
    for key, value in target.items():
        new_key = call_value(fn, [key], line, column)
        if not _is_valid_key(new_key):
            raise CinderRuntimeError(
                f"{type_name(new_key)} is not a valid map key", line, column
            )
        result[new_key] = value
    return result


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


def _group_by(arguments: list, line: int, column: int) -> object:
    _require_arity("group_by", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"group_by() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"group_by() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    groups: dict = {}
    for item in items:
        key = call_value(fn, [item], line, column)
        if not _is_valid_key(key):
            raise CinderRuntimeError(
                f"{type_name(key)} is not a valid map key", line, column
            )
        groups.setdefault(key, []).append(item)
    return groups


def _count_by(arguments: list, line: int, column: int) -> object:
    _require_arity("count_by", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"count_by() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"count_by() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    counts: dict = {}
    for item in items:
        key = call_value(fn, [item], line, column)
        if not _is_valid_key(key):
            raise CinderRuntimeError(
                f"{type_name(key)} is not a valid map key", line, column
            )
        counts[key] = counts.get(key, 0) + 1
    return counts


def _distinct_by(arguments: list, line: int, column: int) -> object:
    _require_arity("distinct_by", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"distinct_by() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"distinct_by() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    seen: set = set()
    result: list = []
    for item in items:
        key = call_value(fn, [item], line, column)
        if not _is_valid_key(key):
            raise CinderRuntimeError(
                f"{type_name(key)} is not a valid map key", line, column
            )
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _partition(arguments: list, line: int, column: int) -> object:
    _require_arity("partition", arguments, 2, line, column)
    items, fn = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"partition() requires a list as its first argument, got {type_name(items)}",
            line, column,
        )
    if not _is_callable(fn):
        raise CinderRuntimeError(
            f"partition() requires a function as its second argument, got {type_name(fn)}",
            line, column,
        )
    matching: list = []
    non_matching: list = []
    for item in items:
        if is_truthy(call_value(fn, [item], line, column)):
            matching.append(item)
        else:
            non_matching.append(item)
    return [matching, non_matching]


def _is_list(arguments: list, line: int, column: int) -> object:
    _require_arity("is_list", arguments, 1, line, column)
    return isinstance(arguments[0], list)


def _is_map(arguments: list, line: int, column: int) -> object:
    _require_arity("is_map", arguments, 1, line, column)
    return isinstance(arguments[0], dict)


def _is_string(arguments: list, line: int, column: int) -> object:
    _require_arity("is_string", arguments, 1, line, column)
    return isinstance(arguments[0], str)


def _is_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_number", arguments, 1, line, column)
    return _is_numeric(arguments[0])


def _is_bool(arguments: list, line: int, column: int) -> object:
    _require_arity("is_bool", arguments, 1, line, column)
    return isinstance(arguments[0], bool)


def _is_nil(arguments: list, line: int, column: int) -> object:
    _require_arity("is_nil", arguments, 1, line, column)
    return arguments[0] is None


def _is_function(arguments: list, line: int, column: int) -> object:
    _require_arity("is_function", arguments, 1, line, column)
    return _is_callable(arguments[0])


_BUILTINS = {
    "print": _print,
    "len": _len,
    "is_empty": _is_empty,
    "type": _type,
    "str": _str,
    "int": _int,
    "float": _float,
    "ord": _ord,
    "chr": _chr,
    "push": _push,
    "pop": _pop,
    "insert": _insert,
    "remove_at": _remove_at,
    "keys": _keys,
    "values": _values,
    "items": _items,
    "get": _get,
    "pluck": _pluck,
    "remove": _remove,
    "merge": _merge,
    "invert": _invert,
    "pick": _pick,
    "omit": _omit,
    "upper": _upper,
    "lower": _lower,
    "capitalize": _capitalize,
    "title": _title,
    "trim": _trim,
    "trim_start": _trim_start,
    "trim_end": _trim_end,
    "split": _split,
    "lines": _lines,
    "words": _words,
    "join": _join,
    "find": _find,
    "starts_with": _starts_with,
    "ends_with": _ends_with,
    "strip_prefix": _strip_prefix,
    "strip_suffix": _strip_suffix,
    "replace": _replace,
    "pad_start": _pad_start,
    "pad_end": _pad_end,
    "abs": _abs,
    "sign": _sign,
    "min": _min,
    "max": _max,
    "clamp": _clamp,
    "round": _round,
    "floor": _floor,
    "ceil": _ceil,
    "pow": _pow,
    "sqrt": _sqrt,
    "sin": _sin,
    "cos": _cos,
    "tan": _tan,
    "log": _log,
    "gcd": _gcd,
    "lcm": _lcm,
    "sum": _sum,
    "mean": _mean,
    "median": _median,
    "any": _any,
    "all": _all,
    "contains": _contains,
    "index_of": _index_of,
    "last_index_of": _last_index_of,
    "find_index": _find_index,
    "count": _count,
    "copy": _copy,
    "deep_copy": _deep_copy,
    "unique": _unique,
    "distinct_by": _distinct_by,
    "union": _union,
    "intersection": _intersection,
    "difference": _difference,
    "reverse": _reverse,
    "first": _first,
    "last": _last,
    "random_int": _random_int,
    "random_choice": _random_choice,
    "shuffle": _shuffle,
    "sample": _sample,
    "sort": _sort,
    "sort_by": _sort_by,
    "min_by": _min_by,
    "max_by": _max_by,
    "range": _range,
    "repeat": _repeat,
    "map": _map,
    "map_values": _map_values,
    "map_keys": _map_keys,
    "filter": _filter,
    "reduce": _reduce,
    "group_by": _group_by,
    "count_by": _count_by,
    "partition": _partition,
    "slice": _slice,
    "take": _take,
    "drop": _drop,
    "take_while": _take_while,
    "drop_while": _drop_while,
    "concat": _concat,
    "flatten": _flatten,
    "flatten_deep": _flatten_deep,
    "flat_map": _flat_map,
    "chunk": _chunk,
    "zip": _zip,
    "zip_with": _zip_with,
    "enumerate": _enumerate,
    "assert": _assert,
    "format": _format,
    "is_list": _is_list,
    "is_map": _is_map,
    "is_string": _is_string,
    "is_number": _is_number,
    "is_bool": _is_bool,
    "is_nil": _is_nil,
    "is_function": _is_function,
}


def create_global_environment() -> Environment:
    env = Environment()
    for name, fn in _BUILTINS.items():
        env.define(name, Builtin(name, fn))
    return env
