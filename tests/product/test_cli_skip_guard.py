"""Guard: the deselection in conftest.py is exactly the 8 CLI tests, and none is stale."""

from pathlib import Path

import pytest

from tests.product.conftest import CLI_DEPENDENT, IMPORTED_TEST, SKIP_REASON


def test_the_skipped_set_is_exactly_the_eight_cli_tests(request: pytest.FixtureRequest) -> None:
    skipped = {
        item.name
        for item in request.session.items
        if any(
            m.name == "skip" and m.kwargs.get("reason") == SKIP_REASON for m in item.iter_markers()
        )
    }
    assert len(CLI_DEPENDENT) == 8
    assert skipped == set(CLI_DEPENDENT)


def test_every_skipped_id_still_exists_in_the_imported_test(request: pytest.FixtureRequest) -> None:
    collected = {item.name for item in request.session.items if item.path.name == IMPORTED_TEST}
    assert set(CLI_DEPENDENT) <= collected
    source = (Path(__file__).parent / IMPORTED_TEST).read_text(encoding="utf-8")
    assert source.count("deploy_vii.__main__") >= 1
