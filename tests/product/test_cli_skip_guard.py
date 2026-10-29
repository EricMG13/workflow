"""Guard: the deselection in conftest.py is exactly the 8 CLI tests, and none is stale.

Reads the imported test file with `ast`, so it holds when run alone or under `-k`.
"""

import ast
from pathlib import Path

from tests.product.conftest import CLI_DEPENDENT, IMPORTED_TEST

SOURCE = Path(__file__).parent / IMPORTED_TEST
PARAMETRIZED = "test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback"


def _functions() -> dict[str, ast.FunctionDef]:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _uses_cli(function: ast.FunctionDef) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "run_cli"
        for n in ast.walk(function)
    )


def _parametrize_ids(function: ast.FunctionDef) -> list[str]:
    for decorator in function.decorator_list:
        if isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", "") == "parametrize":
            for keyword in decorator.keywords:
                if keyword.arg == "ids":
                    return [
                        str(ast.literal_eval(keyword.value)[i])
                        for i in range(len(ast.literal_eval(keyword.value)))
                    ]
    raise AssertionError("no parametrize ids")


def _expected_ids() -> set[str]:
    ids: set[str] = set()
    for name, function in _functions().items():
        if not name.startswith("test_") or not _uses_cli(function):
            continue
        if name == PARAMETRIZED:
            ids |= {f"{name}[{case}]" for case in _parametrize_ids(function)}
        else:
            ids.add(name)
    return ids


def test_the_skipped_set_is_exactly_the_eight_cli_tests() -> None:
    assert len(CLI_DEPENDENT) == 8
    assert set(CLI_DEPENDENT) == _expected_ids()


def test_every_skipped_id_still_exists_in_the_imported_test() -> None:
    functions = _functions()
    for node_id in CLI_DEPENDENT:
        assert node_id.split("[")[0] in functions, node_id
