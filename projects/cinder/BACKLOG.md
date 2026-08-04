# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
All file paths in tasks are relative to this project's directory,
`projects/cinder/` — run the tests and the CLI from there.
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. Language: `not in` — negated membership operator

Build: add `not in` as a single combined binary operator, sugar for
`not (x in y)` but parsed as one operator at `in`'s own precedence
tier rather than as unary `not` applied afterward. Today `in`
(`cinder/parser.py:841-847`, `_membership`) is the only membership
test, and there is no way to negate it except wrapping in parens —
`not (x in y)` — since standalone `not` is a high-precedence unary
operator (`_UNARY = {MINUS, NOT, TILDE}`, `cinder/parser.py:160`,
consumed inside `_unary`, far tighter-binding than `_membership`).
Writing the two keywords adjacent today, `not x in y`, does **not**
give Python-style `not (x in y)` semantics — it parses as `(not x) in
y` (unary `not` binds to `x` first), and the truly adjacent form,
`not in [1]` with nothing between the keywords, is not currently valid
syntax at all: `_unary` consumes `NOT` then recurses into `_unary()`
expecting an operand, but `IN` cannot start an expression, so it's a
`ParseError` today — i.e. `not` immediately followed by `in` is dead
syntax with no existing meaning to preserve, so this is purely
additive with zero regression risk to current programs.

Implementation, modeled on the existing synthesized-operator-token
pattern used for compound assignment desugaring (`qq_operator =
Token(TokenType.QUESTION_QUESTION, "??", None, op_token.line,
op_token.column)`, `cinder/parser.py:757-759`):

1. `cinder/tokens.py`: add `NOT_IN = auto()` to `TokenType` near `IN`
   (`cinder/tokens.py:27`). It is never produced by the lexer directly
   (no entry in `KEYWORDS`) — only synthesized by the parser, the same
   way `TokenType.PLUS` etc. are synthesized from compound-assign
   tokens.
2. `cinder/parser.py`'s `_membership` (`cinder/parser.py:841-847`):
   currently `while self._check(TokenType.IN): ...`. Change the loop
   to also recognize the adjacent two-keyword sequence: when the
   current token is `NOT` and `self._peek_next().type == TokenType.IN`
   (the existing lookahead helper, already used elsewhere e.g.
   `cinder/parser.py:233`), consume both tokens, parse the right
   operand at `_comparison()` precedence (same as the plain `in`
   branch), and build a `Binary` node whose operator is a synthesized
   `Token(TokenType.NOT_IN, "not in", None, not_token.line,
   not_token.column)` (`not_token` being the `NOT` token consumed).
   Keep the plain `IN` branch unchanged; this is a second condition in
   the same loop, not a replacement.
3. `cinder/interpreter.py`'s `_apply_binary_operator`
   (`cinder/interpreter.py:790-836`): next to the existing `if op ==
   TokenType.IN: return contains_value(right, left, operator.line,
   operator.column)` (`cinder/interpreter.py:825-826`), add `if op ==
   TokenType.NOT_IN: return not contains_value(right, left,
   operator.line, operator.column)`. Reuse `contains_value`
   (`cinder/interpreter.py:1014-1034`) as-is — same list
   `==`-membership, map key check, string substring check, and same
   errors (a non-container right-hand side, or a non-string item
   against a string, both already raise `CinderRuntimeError` with
   existing message text — no new error strings to write).
4. Update the parser module docstring's precedence line
   (`cinder/parser.py:6`, `"> ?? (nullish-coalescing, right-assoc) >
   or > and > in"`) to read `"> or > and > in / not in"`.

Acceptance criteria:
- `2 not in [1, 2, 3];` is `false`; `4 not in [1, 2, 3];` is `true`.
- `"a" not in "abc";` is `false` (substring check); `"z" not in
  "abc";` is `true`.
- `"x" not in {"x": 1};` is `false` (map key check); `"y" not in
  {"x": 1};` is `true`.
- `1 not in [2] and 2 not in [1];` is `true` — `not in` participates
  in `and`/`or` chains as a single operator at the same precedence as
  `in`, not as a looser-binding unary `not`.
- `1 < 2 not in [true];` parses as `(1 < 2) not in [true]` — comparison
  binds tighter than `not in`, mirroring `in`'s own existing
  precedence test (`test_comparison_binds_tighter_than_in`,
  `tests/test_parser.py:398-407`).
- `not (2 in [1, 2, 3]);` (existing parenthesized form) still works
  unchanged and agrees with `2 not in [1, 2, 3];` on the same inputs.
- `5 not in 5;` (non-container right-hand side) raises
  `CinderRuntimeError` with the same message `in` already produces for
  this case (`"membership test requires a list, map, or string, got
  int"`) — errors are inherited from `contains_value`, not
  reimplemented.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/parser.py` (`_membership`,
module docstring), `cinder/interpreter.py`
(`_apply_binary_operator`), `tests/test_parser.py` (model new cases on
`test_in_is_binary_op`/`test_in_binds_tighter_than_and`/
`test_comparison_binds_tighter_than_in`, `tests/test_parser.py:376-407`),
`tests/test_interpreter.py`. Once merged, `README.md`'s language
feature bullets and `PROJECT.md`'s roadmap need `not in` added — leave
that to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `chars` — split a string into a list of its characters

Build: add `chars(string)` to `cinder/builtins.py`. `split` deliberately
raises `CinderRuntimeError` on an empty separator
(`cinder/builtins.py:653-654`, `"split() separator must not be empty"`)
rather than falling back to Python's `list(s)`-style per-character
split, so there is currently no builtin way to turn a string into a
list of its individual characters — needed to run any of the existing
list builtins (`map`, `filter`, `reverse`, `sort`, ...) character-by-
character over a string, today only reachable by hand-rolling a `for`
loop and `push`-ing into a fresh list.

Model directly on `_lines`/`_words`'s structure
(`cinder/builtins.py:658-675`): same arity-1 check via
`_require_arity("chars", arguments, 1, line, column)`, same single
type check (the argument a `string` else `CinderRuntimeError` matching
`"chars() requires a string, got {type_name}"`, same message shape
`_lines`/`_words` use). Behavior once validated: return `list(value)`
— Python's built-in per-character split, which already does the right
thing for `""` (`list("")` is `[]`). Register it in the builtins dict
right after `"words": _words,` (`cinder/builtins.py:2647`).

Acceptance criteria:
- `chars("abc");` is `["a", "b", "c"]`.
- `chars("");` is `[]` — empty string, no characters.
- `chars("a");` is `["a"]` — single character.
- `chars(" a ");` is `[" ", "a", " "]` — whitespace is a character
  too, not trimmed (contrast with `words`, which splits on and
  discards whitespace).
- `chars(5);` (non-string argument) raises `CinderRuntimeError` naming
  `chars` and `int` in the message (`type_name(5)` is `"int"`, not
  `"number"`).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `lines`/`words`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `chars` added near `lines`/`words` — leave that to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_even`/`is_odd` — integer parity predicates

Build: add `is_even(number)` and `is_odd(number)` to `cinder/builtins.py`.
There is currently no builtin way to test a number's parity — the
existing type predicates (`is_list`, `is_map`, `is_string`, `is_number`,
`is_bool`, `is_nil`, `is_function`, `cinder/builtins.py:2756-2762` in
the dict) all classify a value's *kind*, not a numeric property of it,
and the closest numeric helper, `sign` (`cinder/builtins.py:901-912`),
classifies a number's sign, not its parity — every Cinder program that
wants "is this number even" today hand-rolls `n % 2 == 0`. This adds
the pair the same way `sign` already sits next to `abs` as a small,
self-contained numeric predicate.

Model both on `_sign`'s structure (`cinder/builtins.py:853-864`): same
arity-1 check via `_require_arity("is_even"/"is_odd", arguments, 1,
line, column)`, but reuse `_require_int` (`cinder/builtins.py:156-161`,
already used by `to_hex`/`to_bin`/`to_oct`) instead of `_is_numeric`
for the type check — parity is only meaningful for integers, so a
`float` argument (even a whole-valued one like `4.0`) is a type error,
not silently truncated; `_require_int`'s existing message shape
(`"{name}() requires an int, got {type_name}"`) applies unchanged, no
new message text to invent. Behavior once validated: `is_even` returns
`value % 2 == 0`; `is_odd` returns `value % 2 != 0` (correct for
negative integers too, since Python's `%` on ints always returns a
non-negative result when the divisor is positive: `-3 % 2 == 1`).
Register both in the builtins dict right after `"sign": _sign,`
(`cinder/builtins.py:2661`), `is_even` before `is_odd`.

Acceptance criteria:
- `is_even(4);` is `true`, `is_odd(4);` is `false`.
- `is_even(3);` is `false`, `is_odd(3);` is `true`.
- `is_even(0);` is `true` — zero is even.
- `is_even(-4);` is `true`, `is_odd(-3);` is `true` — negative integers
  use the same parity rule as positive ones.
- `is_even(4.0);` (float, even though whole-valued) raises
  `CinderRuntimeError` naming `is_even` and `float` in the message
  (`type_name(4.0)` is `"float"`); same for `is_odd(4.0);` naming
  `is_odd`.
- `is_even("4");` (non-numeric argument) raises `CinderRuntimeError`
  naming `is_even` and `string` in the message; same for `is_odd`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for both functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sign`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_even`/`is_odd` added near the other type predicates
(`is_list`/`is_map`/... ) or near `sign` — leave that to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `swap_case` — flip each character's case

Build: add `swap_case(string)` to `cinder/builtins.py`. The existing case
builtins (`upper`, `lower`, `capitalize`, `title`,
`cinder/builtins.py:558-609`) only ever push a string toward one
direction — all upper, all lower, or capitalized at word starts —
there is no builtin that flips each character's existing case in
place (`"Hello World"` → `"hELLO wORLD"`), a common text-processing
operation and the natural fourth member alongside `upper`/`lower`/
`capitalize`/`title` since none of those touch already-correct casing
symmetrically.

Model directly on `_capitalize`'s structure
(`cinder/builtins.py:578-587`): same arity-1 check via
`_require_arity("swap_case", arguments, 1, line, column)`, same single
type check (the argument a `string` else `CinderRuntimeError` matching
`"swap_case() requires a string, got {type_name}"`, same message
shape `_capitalize`/`_title` use). Behavior once validated: return
`value.swapcase()` — Python's built-in per-character case flip, which
already leaves non-alphabetic characters untouched and handles the
empty string correctly. Register it in the builtins dict right after
`"title": _title,` (`cinder/builtins.py:2641`).

Acceptance criteria:
- `swap_case("Hello World");` is `"hELLO wORLD"` — the primary case.
- `swap_case("");` is `""` — empty string, no-op.
- `swap_case("123 abc XYZ");` is `"123 ABC xyz"` — digits/spaces
  untouched, only letters flip.
- `swap_case("ABC");` is `"abc"`, `swap_case("abc");` is `"ABC"` —
  fully-uppercase and fully-lowercase inputs invert cleanly.
- `swap_case(5);` (non-string argument) raises `CinderRuntimeError`
  naming `swap_case` and `int` in the message (`type_name(5)` is
  `"int"`, not `"number"`).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `capitalize`/
`title`, see current line numbers — shift if earlier tasks this cycle
landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `swap_case` added near `capitalize`/`title` —
leave that to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `pad_center` — center a string within a width, padding both sides

Build: add `pad_center(string, width, fill)` to `cinder/builtins.py`.
`pad_start`/`pad_end` (`cinder/builtins.py:844-859`) only ever pad on
one side — the natural third member is centering, padding both sides
so the original content sits in the middle, the same relationship
Python's `str.center` has to `str.ljust`/`str.rjust`.

Model directly on `_pad_start`/`_pad_end`'s structure
(`cinder/builtins.py:844-859`), reusing the existing
`_check_pad_arguments` helper unchanged (`cinder/builtins.py:826-841`)
— same three checks it already runs for `pad_start`/`pad_end`: first
argument a `string` else `CinderRuntimeError` matching `"pad_center()
requires a string as its first argument, got {type_name}"`, second
argument a non-bool, non-negative `int` else `"pad_center() requires
an int width, got {type_name}"` / `"pad_center() width must not be
negative, got {width}"`, third argument a single-character `string`
else `"pad_center() requires a single-character fill string, got
{fill!r}"` (call it as `_check_pad_arguments("pad_center", value,
width, fill, line, column)` — the message text swaps in automatically
via the `name` parameter, no new strings to write). Behavior once
validated: if `len(value) >= width`, return `value` unchanged (same
no-op boundary `pad_start`/`pad_end` use); otherwise return
`value.center(width, fill)` — Python's built-in centering, which puts
any extra (odd) padding character on the left, e.g. `"ab".center(5,
"*")` is `"**ab*"`. Register it in the builtins dict right after
`"pad_end": _pad_end,` (`cinder/builtins.py:2658`, immediately before
`"truncate": _truncate,` — keep the `pad_start`/`pad_end`/`pad_center`
trio contiguous rather than appending after `truncate`).

Acceptance criteria:
- `pad_center("ab", 5, "*");` is `"**ab*"` — odd padding (3 extra
  chars) splits 2 left / 1 right, matching Python's `str.center`.
- `pad_center("ab", 6, "*");` is `"**ab**"` — even padding splits
  evenly.
- `pad_center("hello", 3, "*");` is `"hello"` unchanged — `width`
  smaller than the string, no-op.
- `pad_center("hello", 5, "*");` is `"hello"` unchanged — exactly at
  `width` is not "under" it, matching `_pad_start`/`_pad_end`'s own
  `>=` boundary treatment as a no-op.
- `pad_center("", 3, "*");` is `"***"` — empty string, pure fill.
- `pad_center(5, 3, "*");` (non-string first argument) raises
  `CinderRuntimeError` naming `pad_center` and `int` in the message.
- `pad_center("ab", "3", "*");` (non-int second argument) raises
  `CinderRuntimeError` naming `pad_center` and `string` in the
  message.
- `pad_center("ab", -1, "*");` (negative `width`) raises
  `CinderRuntimeError` naming `pad_center` and `-1` in the message.
- `pad_center("ab", 5, "**");` (multi-character fill) raises
  `CinderRuntimeError` naming `pad_center` and mentioning the
  two-character fill string.
- Wrong arity (not exactly 3 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `pad_start`/
`pad_end`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `pad_center` added near
`pad_start`/`pad_end` — leave that to the Architect's next grooming
pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
