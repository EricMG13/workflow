"""``RunSettings.cutoff``: the empty string and an absent field are one value (O7b-2 S1 review)."""

from typing import Any

from deploy_workflow.context import RunSettings

BASE: dict[str, Any] = {
    "run_type": "primary",
    "pathway": "credit_snapshot",
    "case_kind": "public",
    "as_of": "2026-06-30",
    "current_period": "FY2025",
    "prior_period": "FY2024",
    "reporting_currency": "USD",
}


def settings(**extra: str) -> RunSettings:
    return RunSettings.model_validate({**BASE, **extra})


def test_an_absent_cutoff_reads_as_empty_and_dumps_without_the_field() -> None:
    absent = settings()
    assert absent.cutoff == ""
    assert "cutoff" not in absent.model_dump(mode="json")


def test_an_explicit_empty_cutoff_is_omitted_and_reads_back_as_empty() -> None:
    explicit = settings(cutoff="")
    dumped = explicit.model_dump(mode="json")
    assert "cutoff" not in dumped
    assert RunSettings.model_validate(dumped).cutoff == ""
    assert dumped == settings().model_dump(mode="json")


def test_a_set_cutoff_round_trips_with_the_field() -> None:
    dumped = settings(cutoff="2026-03-31").model_dump(mode="json")
    assert dumped["cutoff"] == "2026-03-31"
    assert RunSettings.model_validate(dumped).cutoff == "2026-03-31"
