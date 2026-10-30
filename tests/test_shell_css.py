"""The navigator module list must not be shrunk under the outline (ruling item 61)."""

import re
from importlib.resources import files


def _declarations(rule_selector: str) -> dict[str, str]:
    css = files("deploy_vii").joinpath("assets/app.css").read_text(encoding="utf-8")
    match = re.search(re.escape(rule_selector) + r"\s*\{([^}]*)\}", css)
    assert match, rule_selector
    pairs = (d.split(":", 1) for d in match.group(1).split(";") if d.strip())
    return {k.strip(): v.strip() for k, v in pairs}


def test_module_list_does_not_shrink_under_a_long_outline() -> None:
    assert _declarations(".module-list").get("flex-shrink") == "0"
