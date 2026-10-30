"""The navigator module list must not be shrunk under the outline (ruling item 61)."""

import re
from importlib.resources import files
from typing import Any

import pytest

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TOKENS = re.compile(r"([^{}]*)\{|(\})|([^{}]+)")
_CLASS_TOKEN = re.compile(r"(?<![\w-])\.module-list(?![\w-])")
_IMPORTANT = re.compile(r"\s*!\s*important\s*$", re.IGNORECASE)
_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")


def _rules(css: str) -> list[tuple[str, str, bool]] | None:
    """Style rules as (selectors, body, inside an at-rule); None when the braces are not a flat
    list of rules and at-rule blocks (CSS nesting is not modelled, so it fails closed)."""
    stack: list[list[Any]] = []  # [prelude, is at-rule, body text]
    rules: list[tuple[str, str, bool]] = []
    for opened, closed, text in _TOKENS.findall(_COMMENT.sub("", css)):
        if closed:
            if not stack:
                return None
            prelude, is_at, body = stack.pop()
            if not is_at:
                rules.append((prelude, body, any(frame[1] for frame in stack)))
        elif text:
            if stack and not stack[-1][1]:
                stack[-1][2] += text
        else:
            if stack and not stack[-1][1]:
                return None
            prelude = opened.rsplit(";", 1)[-1].strip()
            stack.append([prelude, prelude.startswith("@"), ""])
    return None if stack else rules


def _applies_to_module_list(selector: str) -> bool:
    last = re.split(r"[\s>+~]+", selector.strip())[-1]
    return bool(_CLASS_TOKEN.search(last)) and "::" not in last


def _is_zero(name: str, value: str) -> bool:
    """The effective shrink is 0; a value that cannot be read is not 0."""
    tokens = value.split()
    if name == "flex-shrink":
        return len(tokens) == 1 and bool(_NUMBER.fullmatch(tokens[0])) and float(tokens[0]) == 0
    if [t.lower() for t in tokens] == ["none"]:
        return True
    shrink = tokens[1] if len(tokens) in (2, 3) and _NUMBER.fullmatch(tokens[1]) else "1"
    return float(shrink) == 0


def _effect(body: str) -> tuple[bool | None, bool]:
    """(last shrink declaration is 0 or None if none, a non-zero shrink is `!important`)."""
    zero: bool | None = None
    important = False
    for declaration in body.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip().lower()
        if name not in ("flex-shrink", "flex"):
            continue
        flagged = bool(_IMPORTANT.search(value))
        zero = _is_zero(name, _IMPORTANT.sub("", value).strip())
        important = important or (flagged and not zero)
    return zero, important


def module_list_passes(css: str) -> bool:
    """Ruling OI-19: the last shrink of the plain `.module-list` rules (outside at-rules) is 0, and
    no other rule that applies to the list sets a non-zero or unreadable shrink, in any order."""
    rules = _rules(css)
    if rules is None:
        return False
    plain_zero: bool | None = None
    for selectors, body, in_at_rule in rules:
        applying = [s.strip() for s in selectors.split(",") if _applies_to_module_list(s)]
        if not applying:
            continue
        zero, important = _effect(body)
        if important:
            return False
        plain = not in_at_rule and ".module-list" in applying
        if plain and zero is not None:
            plain_zero = zero
        if zero is False and any(s != ".module-list" or in_at_rule for s in applying):
            return False
    return plain_zero is True


_GOOD = ".module-list{flex-shrink:0}"
_CASES = [
    pytest.param(_GOOD, True, id="plain"),
    pytest.param(".a,.module-list{flex-shrink:0}", True, id="comma-list"),
    pytest.param(
        _GOOD + "@media (max-width:600px){.module-list{flex-shrink:0}}",
        True,
        id="media-zero",
    ),
    pytest.param(_GOOD + ".module-list-item{flex-shrink:1}", True, id="item-neighbour-after"),
    pytest.param(".module-list-item{flex-shrink:1}" + _GOOD, True, id="item-neighbour-before"),
    pytest.param(_GOOD + "/* .module-list{flex-shrink:1} */", True, id="comment-override"),
    pytest.param(_GOOD + ".module-list{flex-shrink:1}", False, id="later-override"),
    pytest.param(_GOOD + ".x .module-list{flex-shrink:1}", False, id="later-descendant-override"),
    pytest.param(_GOOD + ".module-list.open{flex-shrink:1}", False, id="later-compound-override"),
    pytest.param(_GOOD + ".a,.module-list{flex-shrink:1}", False, id="later-comma-override"),
    pytest.param(
        _GOOD + "@media (max-width:600px){.module-list{flex-shrink:1}}",
        False,
        id="later-media-override",
    ),
    pytest.param(".module-list{flex-shrink:1}" + _GOOD, True, id="earlier-bad-then-good"),
    pytest.param(".module-list{display:flex}", False, id="no-flex-shrink"),
    pytest.param("", False, id="rule-removed"),
    pytest.param(".module-list-item{flex-shrink:0}", False, id="only-item-rule"),
    pytest.param("/* .module-list{flex-shrink:0} */", False, id="only-commented-out"),
    pytest.param(
        "@media (max-width:600px){.module-list{flex-shrink:0}}",
        False,
        id="only-in-media",
    ),
    pytest.param(_GOOD + ".module-list{flex:1}", False, id="flex-shorthand-later"),
    pytest.param(".module-list{flex-shrink:0;flex:1 1 auto}", False, id="flex-shorthand-same-rule"),
    pytest.param(_GOOD + ".module-list{flex:1 30%}", False, id="flex-grow-basis"),
    pytest.param(_GOOD + ".module-list{flex:inherit}", False, id="flex-inherit"),
    pytest.param(".module-list{flex:none}", True, id="flex-none"),
    pytest.param(".module-list{flex:0 0 auto}", True, id="flex-zero-zero-auto"),
    pytest.param(".module-list{flex-shrink:var(--s)}", False, id="var-unreadable"),
    pytest.param(".x .module-list{flex-shrink:0}", False, id="scoped-zero-only"),
    pytest.param(
        ".x .module-list{flex-shrink:0}.module-list{display:flex}",
        False,
        id="scoped-zero-base-unfixed",
    ),
    pytest.param(
        ".module-list{flex-shrink:1!important}" + _GOOD, False, id="important-earlier-bad"
    ),
    pytest.param(".module-list{flex-shrink:0 !important}", True, id="important-zero"),
    pytest.param(".module-list{flex-shrink:1 !important}", False, id="important-one"),
    pytest.param(".module-list{FLEX-SHRINK:0}", True, id="uppercase-zero"),
    pytest.param(_GOOD + ".module-list{FLEX-SHRINK:1}", False, id="uppercase-override"),
    pytest.param(
        ".module-list{flex-shrink:1}.module-list::before{flex-shrink:0}",
        False,
        id="pseudo-element-good",
    ),
    pytest.param(_GOOD + ".module-list::before{flex-shrink:1}", True, id="pseudo-element-ignored"),
    pytest.param(".nav .module-list{flex-shrink:1}" + _GOOD, False, id="earlier-specific-override"),
    pytest.param(_GOOD + ".module-list{&:hover{color:red}flex-shrink:1}", False, id="nesting"),
    pytest.param(
        ".x .module-list,.module-list{flex-shrink:1}" + _GOOD, False, id="mixed-list-descendant"
    ),
    pytest.param(".module-list.open,.module-list{flex:1}" + _GOOD, False, id="mixed-list-compound"),
    pytest.param(".x .module-list,.module-list{flex-shrink:0}", True, id="mixed-list-zero"),
    pytest.param(".module-list{flex:NONE}", True, id="flex-none-upper"),
]


@pytest.mark.parametrize(("css", "expected"), _CASES)
def test_module_list_rule_checker(css: str, expected: bool) -> None:
    assert module_list_passes(css) is expected


def test_module_list_does_not_shrink_under_a_long_outline() -> None:
    css = files("deploy_vii").joinpath("assets/app.css").read_text(encoding="utf-8")
    assert module_list_passes(css)
