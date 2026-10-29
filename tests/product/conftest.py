"""Deselect the imported portfolio tests that need the excluded `deploy_vii.__main__` CLI."""

import pytest

SKIP_REASON = (
    "deploy_vii.__main__ is excluded from the import (docs/reuse/manifest.json "
    "excluded_python_modules); CLI is outside the PD.1/CP-3B need"
)
IMPORTED_TEST = "test_inputs_portfolio.py"
CLI_DEPENDENT = (
    "test_cli_portfolio_prints_ok_and_exits_zero",
    "test_cli_portfolio_prints_one_line_per_issue_and_exits_one",
    "test_cli_portfolio_json_prints_the_report",
    "test_cli_refuses_noncanonical_cells_with_exit_one",
    "test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback[not-a-zip]",
    "test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback[zip-not-ooxml]",
    "test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback[corrupt-deflate]",
    "test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback[encrypted-member]",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    marker = pytest.mark.skip(reason=SKIP_REASON)
    for item in items:
        if item.path.name == IMPORTED_TEST and item.name in CLI_DEPENDENT:
            item.add_marker(marker)
