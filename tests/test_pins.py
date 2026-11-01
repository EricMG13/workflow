"""The pin module: pinned assumptions read from the frozen context, and their comparison."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import JsonValue

from deploy_vii.execution import MAX_ISSUE_CHARS
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    RunContext,
    load_context,
    preparation_request,
)
from deploy_workflow.owners.pins import (
    _plain,
    form_from_context,
    mismatch,
    pin_issues,
    pin_issues_from_context,
    pinned_line,
    pins_from_context,
    pins_of,
    submission_form,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases" / "context"
ORACLE = ROOT / "cases" / "pins-context-owner"
FULL = (CASES / "primary-full.json").read_bytes()
MODULES = ("CP-2A", "CP-2D", "CP-2E", "CP-3C", "CP-3D", "CP-4C")


def _pack(tmp_path: Path, raw: bytes) -> PreparedPack:
    root = tmp_path / "root"
    root.mkdir()
    (root / "context.json").write_bytes(raw)
    request = preparation_request(
        load_context(raw), run_id="pins-run-1", context_path="context.json", sources=()
    )
    return prepare(request, root, tmp_path / "pack")


def _without_context(pack: PreparedPack) -> PreparedPack:
    kept = tuple(s for s in pack.sources if s.source_id != CONTEXT_SOURCE_ID)
    return pack.model_copy(update={"sources": kept})


def _scenario_rows(form: Mapping[str, JsonValue]) -> list[dict[str, str]]:
    rows = form["scenarios"]
    assert isinstance(rows, list)
    out: list[dict[str, str]] = []
    for row in rows:
        assert isinstance(row, dict)
        out.append({k: v for k, v in row.items() if isinstance(v, str)})
    return out


def _edited(path: str, value: object) -> bytes:
    doc = json.loads(FULL)
    node = doc
    *head, last = path.split(".")
    for part in head:
        node = node[part]
    node[last] = value
    return json.dumps(doc).encode("utf-8")


# (1) no context, or no pin for the module ------------------------------------------------


def test_no_context_source_means_no_pins(tmp_path: Path) -> None:
    pack = _without_context(_pack(tmp_path, FULL))
    for module in MODULES:
        assert pins_of(module, pack) is None
        assert submission_form(module, pack) is None
        assert pin_issues(module, pack, {}) == ()


def test_null_slice_is_no_pin_for_that_module_only(tmp_path: Path) -> None:
    pack = _pack(tmp_path, _edited("assumptions.cp3c", None))
    assert pins_of("CP-3C", pack) is None
    assert submission_form("CP-3C", pack) is None
    assert pin_issues("CP-3C", pack, {"repricing.bps": "1"}) == ()
    for module in ("CP-2A", "CP-2D", "CP-2E", "CP-3D", "CP-4C"):
        assert pins_of(module, pack) is not None


# (2) pin values --------------------------------------------------------------------------


def test_cp2a_percent_becomes_exact_fraction_pairs(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    pins = pins_of("CP-2A", pack)
    assert pins == {
        "assumptions.cp2a.scenarios": (
            (Decimal("0.2"), Decimal("0.1")),
            (Decimal("0.35"), Decimal("0.25")),
        )
    }


def test_other_pins_keep_their_units(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    assert pins_of("CP-2D", pack) == {
        "assumptions.cp2d.horizon_months": Decimal(18),
        "assumptions.cp2d.minimum_cash_m": Decimal(50),
    }
    assert pins_of("CP-2E", pack) == {
        "assumptions.cp2e.rate_shocks_bps": (Decimal(100), Decimal(200)),
        "assumptions.cp2e.fx_shocks_pct": (Decimal(10),),
        "assumptions.cp2e.hedge_ratio_pct": Decimal(60),
    }
    assert pins_of("CP-3C", pack) == {"assumptions.cp3c.repricing_bps": Decimal(50)}
    assert pins_of("CP-3D", pack) == {"assumptions.cp3d.recovery_pct": Decimal(65)}
    assert pins_of("CP-4C", pack) == {"assumptions.cp4c.ev_multiple": Decimal("8.5")}


def test_blank_hedge_has_no_key(tmp_path: Path) -> None:
    pack = _pack(tmp_path, _edited("assumptions.cp2e.hedge_ratio_pct", ""))
    pins = pins_of("CP-2E", pack)
    assert pins is not None
    assert "assumptions.cp2e.hedge_ratio_pct" not in pins
    form = submission_form("CP-2E", pack)
    assert form is not None
    assert "hedge_ratio.percent_text" not in form
    assert (
        pin_issues("CP-2E", pack, {"rate_shocks_bp": ["100", "200"], "fx_shocks_percent": ["10"]})
        == ()
    )


# (3) the submission form -----------------------------------------------------------------


def test_submission_form_values(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    assert submission_form("CP-4C", pack) == {"valuation[*].multiple": "8.5"}
    assert submission_form("CP-2E", pack) == {
        "fx_shocks_percent": ["10"],
        "hedge_ratio.percent_text": "60",
        "rate_shocks_bp": ["100", "200"],
    }
    assert submission_form("CP-2A", pack) == {
        "scenarios": [
            {"ebitda_decline": "0.2", "interest_increase": "0.1"},
            {"ebitda_decline": "0.35", "interest_increase": "0.25"},
        ]
    }
    assert submission_form("CP-2D", pack) == {"horizon_months": "18", "minimum_cash.amount": "50"}
    assert submission_form("CP-3C", pack) == {"repricing.bps": "50"}
    assert submission_form("CP-3D", pack) == {"recovery.percent_text": "65"}


def test_form_strings_are_plain_not_exponent(tmp_path: Path) -> None:
    doc = json.loads(FULL)
    doc["assumptions"]["cp3c"]["repricing_bps"] = "100"
    doc["assumptions"]["cp2a"]["scenarios"][0] = {
        "ebitda_decline_pct": "100",
        "interest_increase_pct": "0",
    }
    doc["assumptions"]["cp2d"]["minimum_cash_m"] = "1000.50"
    pack = _pack(tmp_path, json.dumps(doc).encode("utf-8"))
    assert submission_form("CP-3C", pack) == {"repricing.bps": "100"}
    assert submission_form("CP-2D", pack) == {
        "horizon_months": "18",
        "minimum_cash.amount": "1000.5",
    }
    form = submission_form("CP-2A", pack)
    assert form is not None
    assert _scenario_rows(form)[0] == {"ebitda_decline": "1", "interest_increase": "0"}


# (4) the comparison line -----------------------------------------------------------------


def test_mismatch_lines() -> None:
    assert (
        mismatch("assumptions.cp3c.repricing_bps", "400", "401")
        == "assumptions.cp3c.repricing_bps: pinned 400; submitted 401"
    )
    assert (
        mismatch("assumptions.cp3c.repricing_bps", "400", None)
        == "assumptions.cp3c.repricing_bps: pinned 400; submitted absence"
    )
    assert mismatch("assumptions.cp4c.ev_multiple", "4", "3.0", at="valuation[1].multiple") == (
        "assumptions.cp4c.ev_multiple (valuation[1].multiple): pinned 4; submitted 3.0"
    )


def test_mismatch_clips_the_submitted_text() -> None:
    line = mismatch("assumptions.cp3d.recovery_pct", "70", "9" * 10_000)
    assert len(line) <= MAX_ISSUE_CHARS
    assert line.startswith("assumptions.cp3d.recovery_pct: pinned 70; submitted 999")


@pytest.mark.parametrize("junk", ["abc", "1e5", "", " 70", "70 ", "٧٠", "70\n", "-70", "7,0"])
def test_junk_is_reported_as_typed_never_raised(tmp_path: Path, junk: str) -> None:
    doc = json.loads(FULL)
    doc["assumptions"]["cp3d"]["recovery_pct"] = "70"
    pack = _pack(tmp_path, json.dumps(doc).encode("utf-8"))
    assert pin_issues("CP-3D", pack, {"recovery.percent_text": junk}) == (
        f"assumptions.cp3d.recovery_pct: pinned 70; submitted {junk}",
    )


def test_junk_inside_lists_and_scenarios(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    assert pin_issues(
        "CP-2E",
        pack,
        {"rate_shocks_bp": ["abc"], "fx_shocks_percent": ["10"], "hedge_ratio.percent_text": "60"},
    ) == ("assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted abc",)
    rows: list[dict[str, str | None]] = [
        {"ebitda_decline": "1e-1", "interest_increase": "0.1"},
        {"ebitda_decline": "0.35", "interest_increase": None},
    ]
    issues = pin_issues("CP-2A", pack, {"scenarios": rows})
    assert issues == (
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct: pinned 0.2 (20%); submitted 1e-1",
        "assumptions.cp2a.scenarios[1].interest_increase_pct: pinned 0.25 (25%); submitted absence",
    )


def test_equal_values_with_other_spelling_pass(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    assert (
        pin_issues(
            "CP-2A",
            pack,
            {
                "scenarios": [
                    {"ebitda_decline": "0.2000", "interest_increase": "0.10"},
                    {"ebitda_decline": "0.350", "interest_increase": "0.25"},
                ]
            },
        )
        == ()
    )
    assert pin_issues("CP-2D", pack, {"horizon_months": "18", "minimum_cash.amount": "50.00"}) == ()
    assert pin_issues("CP-4C", pack, {"valuation[*].multiple": ["8.50", "8.5"]}) == ()


def test_pin_issue_order_and_cp2a_count(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    one = {"scenarios": [{"ebitda_decline": "0.2", "interest_increase": "0.1"}]}
    assert pin_issues("CP-2A", pack, one) == (
        "assumptions.cp2a.scenarios: pinned 2 scenarios; submitted 1",
    )
    swapped = {
        "scenarios": [
            {"ebitda_decline": "0.35", "interest_increase": "0.25"},
            {"ebitda_decline": "0.2", "interest_increase": "0.1"},
        ]
    }
    assert pin_issues("CP-2A", pack, swapped) == (
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct: pinned 0.2 (20%); submitted 0.35",
        "assumptions.cp2a.scenarios[0].interest_increase_pct: pinned 0.1 (10%); submitted 0.25",
        "assumptions.cp2a.scenarios[1].ebitda_decline_pct: pinned 0.35 (35%); submitted 0.2",
        "assumptions.cp2a.scenarios[1].interest_increase_pct: pinned 0.25 (25%); submitted 0.1",
    )
    assert pin_issues("CP-2D", pack, {"horizon_months": "12"}) == (
        "assumptions.cp2d.horizon_months: pinned 18; submitted 12",
        "assumptions.cp2d.minimum_cash_m: pinned 50; submitted absence",
    )
    assert pin_issues(
        "CP-2E",
        pack,
        {"rate_shocks_bp": ["100", "300"], "fx_shocks_percent": ["10", "20"]},
    ) == (
        "assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted 100, 300",
        "assumptions.cp2e.fx_shocks_pct: pinned 10; submitted 10, 20",
        "assumptions.cp2e.hedge_ratio_pct: pinned 60; submitted absence",
    )
    assert pin_issues("CP-4C", pack, {"valuation[*].multiple": ["8.5", "3.0", None]}) == (
        "assumptions.cp4c.ev_multiple (valuation[1].multiple): pinned 8.5; submitted 3.0",
        "assumptions.cp4c.ev_multiple (valuation[2].multiple): pinned 8.5; submitted absence",
    )


def test_a_scalar_pin_given_a_list_is_a_caller_error(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    with pytest.raises(TypeError, match="repricing.bps"):
        pin_issues("CP-3C", pack, {"repricing.bps": ["50"]})


def test_cp4c_fails_closed_without_submitted_multiples(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    absence = ("assumptions.cp4c.ev_multiple: pinned 8.5; submitted absence",)
    assert pin_issues("CP-4C", pack, {}) == absence
    assert pin_issues("CP-4C", pack, {"valuation[*].multiple": []}) == absence
    assert pin_issues("CP-4C", pack, {"valuation.multiple": ["8.5"]}) == absence


def test_one_scenario_pin_is_singular(tmp_path: Path) -> None:
    doc = json.loads(FULL)
    doc["assumptions"]["cp2a"]["scenarios"] = doc["assumptions"]["cp2a"]["scenarios"][:1]
    pack = _pack(tmp_path, json.dumps(doc).encode("utf-8"))
    assert pin_issues("CP-2A", pack, {"scenarios": []}) == (
        "assumptions.cp2a.scenarios: pinned 1 scenario; submitted 0",
    )


def test_more_scenarios_than_pinned_is_a_count_line(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    row: dict[str, str | None] = {"ebitda_decline": "0.2", "interest_increase": "0.1"}
    rows = [row, row, row]
    assert pin_issues("CP-2A", pack, {"scenarios": rows}) == (
        "assumptions.cp2a.scenarios: pinned 2 scenarios; submitted 3",
    )


def test_empty_shock_list_is_absence(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    assert pin_issues(
        "CP-2E",
        pack,
        {"rate_shocks_bp": [], "fx_shocks_percent": ["10"], "hedge_ratio.percent_text": "60"},
    ) == ("assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted absence",)


# the form rounds nothing, whatever the caller's decimal context ------------------------------

BIG = "123456789012345678901234567890.5"


def test_form_keeps_more_than_28_digits_and_ignores_caller_precision(tmp_path: Path) -> None:
    doc = json.loads(FULL)
    doc["assumptions"]["cp2d"]["minimum_cash_m"] = BIG
    pack = _pack(tmp_path, json.dumps(doc).encode("utf-8"))
    for prec in (4, 28, 100):
        with localcontext() as ctx:
            ctx.prec = prec
            form = submission_form("CP-2D", pack)
            assert form is not None
            assert form["minimum_cash.amount"] == BIG
            assert (
                pin_issues("CP-2D", pack, {"horizon_months": "18", "minimum_cash.amount": BIG})
                == ()
            )


def test_plain_is_exact_for_tiny_and_trailing_zero_values() -> None:
    with localcontext() as ctx:
        ctx.prec = 4
        assert _plain(Decimal("1E-29")) == "0." + "0" * 28 + "1"
        assert (
            _plain(Decimal("1.2300000000000000000000000000000E+31"))
            == "12300000000000000000000000000000"
        )
        assert _plain(Decimal("10.500")) == "10.5"
        assert _plain(Decimal(100)) == "100"
        assert _plain(Decimal("0.00")) == "0"


# (4c) the pinned sentence ----------------------------------------------------------------


def test_pinned_lines_equal_the_oracle() -> None:
    lines = json.loads((ORACLE / "expected.json").read_text(encoding="utf-8"))["pinned_lines"]
    assert pinned_line("CP-2A") == lines["CP-2A"]
    assert pinned_line("CP-2D") == lines["CP-2D"]
    assert pinned_line("CP-2E") == lines["CP-2E"]
    assert pinned_line("CP-2E", hedge_pinned=True) == lines["CP-2E+hedge"]
    assert pinned_line("CP-3C") == lines["CP-3C"]
    assert pinned_line("CP-3D") == lines["CP-3D"]
    assert pinned_line("CP-4C") == lines["CP-4C"]


@pytest.mark.parametrize("module", MODULES)
def test_pinned_line_is_one_sentence_that_agrees_in_number(module: str) -> None:
    line = pinned_line(module)
    assert line.endswith(".")
    assert line.count(".") == 1
    plural = module in ("CP-2A", "CP-2D", "CP-2E")
    assert (" are " in line) is plural
    assert (" is " in line) is not plural
    assert line.endswith("equals the pins." if plural else "equals the pin.")


def test_hedge_is_named_only_when_pinned() -> None:
    assert "hedge" not in pinned_line("CP-2E")
    assert "hedge" in pinned_line("CP-2E", hedge_pinned=True)
    assert pinned_line("CP-2A", hedge_pinned=True) == pinned_line("CP-2A")


# (5) context against the run -------------------------------------------------------------


def test_context_that_differs_from_the_run_is_refused(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    moved = pack.run.model_copy(update={"as_of": pack.run.as_of.replace(day=30)})
    swapped = pack.model_copy(update={"run": moved})
    with pytest.raises(ContextRefused, match=r"run\.as_of"):
        pins_of("CP-3C", swapped)
    with pytest.raises(ContextRefused, match=r"run\.as_of"):
        submission_form("CP-3C", swapped)
    with pytest.raises(ContextRefused, match=r"run\.as_of"):
        pin_issues("CP-3C", swapped, {"repricing.bps": "50"})


# (7) unknown module ----------------------------------------------------------------------


def test_unknown_module_raises_keyerror_naming_it(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FULL)
    for call in (
        lambda: pins_of("CP-9Z", pack),
        lambda: submission_form("CP-9Z", pack),
        lambda: pin_issues("CP-9Z", pack, {}),
        lambda: pinned_line("CP-9Z"),
    ):
        with pytest.raises(KeyError, match="CP-9Z"):
            call()


# every committed oracle context loads and yields pins ------------------------------------


@pytest.mark.parametrize("path", sorted(ORACLE.glob("context-*.json")), ids=lambda p: p.stem)
def test_oracle_contexts_yield_pins(path: Path, tmp_path: Path) -> None:
    pack = _pack(tmp_path, path.read_bytes())
    for module in MODULES:
        pins = pins_of(module, pack)
        slice_name = module.lower().replace("-", "")
        pinned = getattr(load_context(path.read_bytes()).assumptions, slice_name) is not None
        assert (pins is not None) is pinned


# (6) property ----------------------------------------------------------------------------

_TWO_DP = st.decimals(min_value=Decimal(0), max_value=Decimal("99.99"), places=2, allow_nan=False)


def _context_with(**assumption_edits: object) -> RunContext:
    doc = json.loads(FULL)
    for dotted, value in assumption_edits.items():
        module, field = dotted.split("__")
        doc["assumptions"][module][field] = value
    return load_context(json.dumps(doc).encode("utf-8"))


def _spellings(d: Decimal) -> list[str]:
    plain = format(d, "f")
    return [plain, plain + "0", plain + "00"] if "." in plain else [plain, plain + ".0"]


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(d=_TWO_DP)
def test_form_value_round_trips_and_ignores_trailing_zeros(d: Decimal) -> None:
    text = format(d, "f")
    ctx = _context_with(
        cp3d__recovery_pct=text,
        cp2a__scenarios=[{"ebitda_decline_pct": text, "interest_increase_pct": text}],
        cp2e__hedge_ratio_pct=text,
    )
    for module, key in (("CP-3D", "recovery.percent_text"), ("CP-2E", "hedge_ratio.percent_text")):
        form = form_from_context(module, ctx)
        assert form is not None
        shown = form[key]
        assert isinstance(shown, str)
        assert Decimal(shown) == d
        assert re.fullmatch(r"\d+(\.\d*[1-9])?", shown)
    scenarios = form_from_context("CP-2A", ctx)
    assert scenarios is not None
    assert Decimal(_scenario_rows(scenarios)[0]["ebitda_decline"]) == d / 100
    pins = pins_from_context("CP-3D", ctx)
    assert pins == {"assumptions.cp3d.recovery_pct": d}


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(d=_TWO_DP, data=st.data())
def test_comparison_is_unaffected_by_trailing_zeros(d: Decimal, data: st.DataObject) -> None:
    text = format(d, "f")
    ctx = _context_with(cp3d__recovery_pct=text)
    spelled = data.draw(st.sampled_from(_spellings(d)))
    assert pin_issues_from_context("CP-3D", ctx, {"recovery.percent_text": spelled}) == ()
    other = d + Decimal("0.01")
    assert (
        pin_issues_from_context("CP-3D", ctx, {"recovery.percent_text": format(other, "f")}) != ()
    )
