"""The navigator module list must not be shrunk under the outline (ruling item 61)."""

import re
from importlib.resources import files

import pytest

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_CLASS_TOKEN = re.compile(r"(?<![\w-])\.module-list(?![\w-])")


def _applies_to_module_list(selectors: str) -> bool:
    """True when a selector of the comma list ends in a compound carrying the class token."""
    return any(
        _CLASS_TOKEN.search(re.split(r"[\s>+~]+", selector.strip())[-1])
        for selector in selectors.split(",")
    )


def module_list_passes(css: str) -> bool:
    """At least one rule applies to `.module-list` (also inside `@media`, or as an override) and
    the last `flex-shrink` declared by those rules, in source order, is `0`."""
    applying = False
    shrinks: list[str] = []
    for selectors, body in _RULE.findall(_COMMENT.sub("", css)):
        if not _applies_to_module_list(selectors):
            continue
        applying = True
        for declaration in body.split(";"):
            name, _, value = declaration.partition(":")
            if name.strip() == "flex-shrink":
                shrinks.append(value.strip())
    return applying and bool(shrinks) and shrinks[-1] == "0"


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
        ".x .module-list{flex-shrink:0}.module-list{display:flex}", False, id="scoped-zero-base-unfixed"
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
]


@pytest.mark.parametrize(("css", "expected"), _CASES)
def test_module_list_rule_checker(css: str, expected: bool) -> None:
    assert module_list_passes(css) is expected


def test_module_list_does_not_shrink_under_a_long_outline() -> None:
    css = files("deploy_vii").joinpath("assets/app.css").read_text(encoding="utf-8")
    assert module_list_passes(css)
