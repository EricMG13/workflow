"""Library half of the 4 CLI-skipped damaged-member cases (not an imported file).

The imported `test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback` also drives
`deploy_vii.__main__`, which is excluded, so conftest.py skips it. This re-runs its
`validate_portfolio` assertion (the `except DAMAGED` path in portfolio.py) on the same cases.
"""

from pathlib import Path

import pytest

from tests.product import test_inputs_portfolio as imported

_PARAMETRIZE = [
    mark
    for mark in imported.test_a_file_prepare_cannot_read_is_one_issue_not_a_traceback.pytestmark
    if mark.name == "parametrize"
][0]
CASES = _PARAMETRIZE.args[1]
IDS = _PARAMETRIZE.kwargs["ids"]


@pytest.mark.parametrize("raw, problem, fix", CASES, ids=IDS)
def test_validate_portfolio_reports_one_issue_for_a_file_prepare_cannot_read(
    tmp_path: Path, raw: bytes, problem: str, fix: str
) -> None:
    path = tmp_path / imported.FILE
    path.write_bytes(raw)
    expected = (
        f"{imported.FILE}:Mandate!A1: prepare cannot read this file as an OOXML workbook: "
        f"{problem} — fix: {fix}"
    )
    assert imported.rendered(imported.validate_portfolio(path)) == [expected]
