"""Prints which owner_workflow the run imports and whether its two CP-MODEL checks are lenient."""
import importlib
from typing import Any

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")


def test_which_src() -> None:
    text = open(owner.__file__).read()
    print("SRC", owner.__file__, "pub-lenient", "if False and (attempt.module_id" in text,
          "head-lenient", "if False and bound !=" in text)
