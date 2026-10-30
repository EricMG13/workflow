"""The navigator module list must not be shrunk under the outline (ruling item 61)."""

import re
from importlib.resources import files

import pytest


def _declarations(css: str, rule_selector: str) -> dict[str, str] | None:
    match = re.search(re.escape(rule_selector) + r"\s*\{([^}]*)\}", css)
    if not match:
        return None
    pairs = (d.split(":", 1) for d in match.group(1).split(";") if d.strip())
    return {k.strip(): v.strip() for k, v in pairs}


def module_list_passes(css: str) -> bool:
    declared = _declarations(css, ".module-list")
    return declared is not None and declared.get("flex-shrink") == "0"


_GOOD = ".module-list{flex-shrink:0}"
_CASES = [
    pytest.param(_GOOD, True, id="plain"),
    pytest.param(".a,.module-list{flex-shrink:0}", True, id="comma-list"),
    pytest.param("@media (max-width:600px){.module-list{flex-shrink:0}}", True, id="in-media"),
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
]


@pytest.mark.parametrize(("css", "expected"), _CASES)
def test_module_list_rule_checker(css: str, expected: bool) -> None:
    assert module_list_passes(css) is expected


def test_module_list_does_not_shrink_under_a_long_outline() -> None:
    css = files("deploy_vii").joinpath("assets/app.css").read_text(encoding="utf-8")
    assert module_list_passes(css)
