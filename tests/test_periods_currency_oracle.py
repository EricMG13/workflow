"""Phase 8 done-when: the frozen oracle `cases/periods-currency-owner/` run as a whole.

Every expected value is read at run time from `expected.json` (`runs/*`, `module_oracles/*`,
`period_basis/*`). The per-module Phase 8 files already compare each module with the key; this
file names those nodes (the mapping below, checked by `test_mapped_nodes_exist`) and adds only
what no node covers: the run-level union of row 1, the R5b CP-L10 refusal of row 4, the source
scan of row 6 and the whole-output token check of row 7.

Row -> existing nodes (file::node), status:
 1  R1 (CP-1C, CP-2D, CP-3C) and no stale literal                                  run
    cp1c::test_composed_facts_tables_and_limitations_equal_the_key (R1, R6)
    cp1c::test_no_stale_period_literal_is_emitted
    usd_key::test_cp2d_usd_2026_equals_the_key, ::test_cp3c_usd_2026_equals_the_key
    stale::test_cp2d_r6_module_has_no_stale_literal, ::test_cp3c_r6_module_has_no_stale_literal
    NEW test_r1_run_level_union (every settled module of R1, R2, R3, R6)
 2  R2 (CP-2A, CP-2G, CP-2H, CP-4C, CP-2E, CP-L10), FY2027-FY2029                    run
    misc::test_cp2a_eur_claims_and_limitations_equal_the_oracle
    cp2g_cp2h::test_cp2g_eur_facts_equal_the_oracle, ::test_b_driver_columns_are_the_three_years_after_the_base
    cp2g_cp2h::test_cp2h_eur_facts_tables_claims_and_limitations_equal_the_oracle
    cp2g_cp2h::test_cp2h_forecast_columns_are_fy2027_to_fy2029
    cp4c::test_eur_facts_equal_the_oracle, ::test_the_forecast_years_are_the_bases_three
    misc::test_cp2e_report_equals_the_oracle_tables_and_claims
    misc::test_cpl10_screen_equals_the_oracle_in_eur, ::test_cpl10_view_equals_the_oracle_in_eur
 3  R3 CP-1B `EUR m` labels, CP-1D amount facts EUR                                  run
    misc::test_composed_row_labels_equal_the_oracle, ::test_composed_prose_equals_the_oracle
    cp1b_labels::test_layouts_in_the_oracle_unit_equal_the_oracle_labels
    cp1d::test_eur_compute_equals_the_oracle_facts_tables_and_limitations
    end1::test_eur_report_amounts_equal_the_r3_run_oracle
 4  R4 mismatch, R5 h2 base refuse; R5b q3 base                                       run
    cp1c::test_currency_mismatch_is_the_keys_validator_issue
    e2e_cp2d::test_cp2d_r4_mismatch_is_an_entry_validator_issue
    e2e_cp3c::test_cp3c_r4_mismatch_is_an_entry_validator_issue
    cp2g_cp2h::test_e_h2_base_is_refused_in_the_cp2g_entry_validator, ..._cp2h_entry_validator
    cp4c::test_an_unsupported_period_is_one_issue_line_and_an_empty_view (R5 CP-4C)
    cp1c::test_unsupported_period_base_is_a_period_basis_issue (R5 CP-1C)
    misc::test_cp2a_offers_a_q3_base_whatever_the_currency (R5, R5b CP-2A)
    misc::test_r5b_q3_base_cp1b_keeps_its_raw_day_refusal, fix1::test_r5b_cp1b_through_the_context_with_the_oracle_pair
    NEW test_r5b_cpl10_refuses_at_the_offering
 5  no-context pack unchanged: fast per-module byte checks (below); the frozen          run (fast
    `cases/*-owner` suites `tests/test_owner_*.py tests/test_connect_*.py` are CI-only    nodes);
    period_basis::test_default_basis_is_todays_literals, ::test_none_context_gives_default  whole suite
    cp1c::test_default_basis_selects_todays_frozen_head                                   gated (CI)
    cp1d::test_frozen_bridge_parses_with_the_default_line, ::test_usd_default_claim_keeps_the_dollar_unit
    cp2d_cp3c::test_default_basis_bindings_are_the_frozen_ones, ::test_no_context_keeps_the_default_basis
    cp2g_cp2h::test_default_composer_is_the_2025_default
    cp4c::test_the_default_output_is_the_frozen_oracle, ::test_the_default_view_equals_the_committed_view_tree
    cp1b_labels::test_default_layouts_equal_the_usd_key, ::test_usd_module_validates_unchanged
    misc::test_eur_evidence_states_the_currency_and_usd_keeps_its_bytes
    misc::test_cpl10_usd_upstream_keeps_the_us_dollar_token
 6  no hard-coded period left in `src/deploy_workflow/owners`: NEW test_no_hardcoded_period_left   run
 7  EUR runs render `EUR m` and no `US$`: BLOCKED, not committed (CP-2H emits no money fact; see report)
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.context_periods import quarters_ending_at
from deploy_workflow.owners import cpl10

ROOT = Path(__file__).resolve().parents[1]
KEY: dict[str, Any] = json.loads(
    (ROOT / "cases" / "periods-currency-owner" / "expected.json").read_text(encoding="utf-8")
)
RUNS: dict[str, Any] = KEY["runs"]
STALE_KEY = "stale_period_literals_forbidden_in_emitted_period_strings"
# The CP-2D fixture pack runs as of 2026-01-10, the frozen run; its as-of literals are not stale
# there (the same exclusion as test_periods_currency_stale.py).
AS_OF = {"As of 2026-01-10", "as of 2026-01-10", "Terms published 2026-01-10"}


# ---- the mapping table is real ----------------------------------------------------------------

MAPPED = {
    "cp1c": [
        "test_composed_facts_tables_and_limitations_equal_the_key",
        "test_no_stale_period_literal_is_emitted",
        "test_currency_mismatch_is_the_keys_validator_issue",
        "test_unsupported_period_base_is_a_period_basis_issue",
        "test_default_basis_selects_todays_frozen_head",
    ],
    "cp1b_labels": ["test_layouts_in_the_oracle_unit_equal_the_oracle_labels"],
    "usd_key": ["test_cp2d_usd_2026_equals_the_key", "test_cp3c_usd_2026_equals_the_key"],
    "stale": [
        "test_cp2d_r6_module_has_no_stale_literal",
        "test_cp3c_r6_module_has_no_stale_literal",
    ],
    "misc": [
        "test_cp2a_eur_claims_and_limitations_equal_the_oracle",
        "test_cp2e_report_equals_the_oracle_tables_and_claims",
        "test_cpl10_screen_equals_the_oracle_in_eur",
        "test_cpl10_view_equals_the_oracle_in_eur",
        "test_composed_row_labels_equal_the_oracle",
        "test_composed_prose_equals_the_oracle",
        "test_cp2a_offers_a_q3_base_whatever_the_currency",
        "test_r5b_q3_base_cp1b_keeps_its_raw_day_refusal",
        "test_eur_evidence_states_the_currency_and_usd_keeps_its_bytes",
        "test_cpl10_usd_upstream_keeps_the_us_dollar_token",
    ],
    "cp2g_cp2h": [
        "test_cp2g_eur_facts_equal_the_oracle",
        "test_b_driver_columns_are_the_three_years_after_the_base",
        "test_cp2h_eur_facts_tables_claims_and_limitations_equal_the_oracle",
        "test_cp2h_forecast_columns_are_fy2027_to_fy2029",
        "test_e_h2_base_is_refused_in_the_cp2g_entry_validator",
        "test_e_h2_base_is_refused_in_the_cp2h_entry_validator",
        "test_default_composer_is_the_2025_default",
    ],
    "cp4c": [
        "test_eur_facts_equal_the_oracle",
        "test_the_forecast_years_are_the_bases_three",
        "test_the_default_output_is_the_frozen_oracle",
        "test_the_default_view_equals_the_committed_view_tree",
        "test_an_unsupported_period_is_one_issue_line_and_an_empty_view",
    ],
    "cp1d": [
        "test_eur_compute_equals_the_oracle_facts_tables_and_limitations",
        "test_frozen_bridge_parses_with_the_default_line",
        "test_usd_default_claim_keeps_the_dollar_unit",
    ],
    "e2e_cp2d": ["test_cp2d_r4_mismatch_is_an_entry_validator_issue"],
    "e2e_cp3c": ["test_cp3c_r4_mismatch_is_an_entry_validator_issue"],
    "end1": ["test_eur_report_amounts_equal_the_r3_run_oracle"],
    "fix1": ["test_r5b_cp1b_through_the_context_with_the_oracle_pair"],
    "cp2d_cp3c": [
        "test_default_basis_bindings_are_the_frozen_ones",
        "test_no_context_keeps_the_default_basis",
    ],
    "period_basis": ["test_default_basis_is_todays_literals", "test_none_context_gives_default"],
}


def _file_of(short: str) -> Path:
    name = short if short == "period_basis" else f"periods_currency_{short}"
    return Path(__file__).parent / f"test_{name}.py"


def test_mapped_nodes_exist() -> None:
    """Every node the mapping table names is a test function of the file named."""
    for short, nodes in MAPPED.items():
        tree = ast.parse(_file_of(short).read_text(encoding="utf-8"))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert [n for n in nodes if n not in defined] == [], short


# ---- row 1: the run-level union -----------------------------------------------------------------


def _settled(run: str) -> dict[str, Any]:
    return {m: d for m, d in RUNS[run]["modules"].items() if d["outcome"] == "settled"}


def _oracle(name: str) -> Any:
    value = KEY["module_oracles"][name]
    return value.get("expected", value)


def test_r1_run_level_union() -> None:
    """R1 settles CP-1C, CP-2D and CP-3C; every settled module of R1, R2, R3 and R6 has an oracle
    that holds none of the run's stale literals. The composed modules equal those oracles (the
    mapped nodes), so no emitted period string holds one."""
    assert set(_settled("R1")) == {"CP-1C", "CP-2D", "CP-3C"}
    for run in ("R1", "R2", "R3", "R6"):
        stale = RUNS[run][STALE_KEY]
        assert stale
        for module, data in _settled(run).items():
            text = json.dumps(_oracle(data["oracle"]), ensure_ascii=False)
            allowed = AS_OF if module == "CP-2D" else set()
            assert [s for s in stale if s in text and s not in allowed] == [], (run, module)


# ---- row 4: R5b CP-L10 ------------------------------------------------------------------------


def test_r5b_cpl10_refuses_at_the_offering() -> None:
    """R5b (q3-2026 base): the shifted register holds T4.14 q1-q4 2026 only, so the four quarters
    ending at q3-2026 need q4-2025, which is unbound: refused, no figure."""
    want = RUNS["R5b"]["modules"]["CP-L10"]
    own: Any = __import__("test_owner_cpl10")
    register = own._t414_rows(*((2026, q) for q in (1, 2, 3, 4)))
    assert quarters_ending_at(RUNS["R5b"]["current_period"]) == tuple(want["quarters_needed"])
    with pytest.raises(cpl10.UpstreamError) as raised:
        cpl10.context_quarters(RUNS["R5b"]["current_period"], register)
    assert want["issue_contains"] in str(raised.value)
    assert want["missing_quarter_id"] in str(raised.value)
    assert want["figures_produced"] is False


# ---- row 6: no hard-coded period left ---------------------------------------------------------

PATTERN = re.compile(r'LTM Q4 25|q4-2025|FY2026, FY2027|"USD"')
OWNERS = ROOT / "src" / "deploy_workflow" / "owners"
DEFAULT_CURRENCY = "the no-context default currency; the frozen USD default of the run basis"
PARSER_DOC = "docstring of a CP-1 fact-label parser reading vii's own `LTM Q4 25: a to b` format"
# (file, stripped source line) -> reason. `period_basis.py` is allowed whole (the one basis).
ALLOWED: dict[tuple[str, str], str] = {
    (
        "cp1b.py",
        'view: ModuleView, submission: EarningsDeltaOwnerReview, *, currency: str = "USD"',
    ): DEFAULT_CURRENCY,
    (
        "cp1b.py",
        'return ContextPair(None, (clipped(("Context refused: ", str(error))),)), "USD"',
    ): "refused context offers no pair; the currency is unused (P8-R5)",
    (
        "cp1b.py",
        'return ContextPair(None, (clipped((str(error),)),)), "USD"',
    ): "refused currency offers no pair; the currency is unused (P8-R5)",
    (
        "cp1b.py",
        "2025 register, q3-2025 -> q4-2025 and fy-2024 -> fy-2025). With a context naming both periods",
    ): "docstring describing the default (no-context) 2025 register pair",
    (
        "cp2a.py",
        '"""The kind of a CP-1 base period, from its label (`LTM Q4 25: ...`, `FY25: ...`,',
    ): PARSER_DOC,
    (
        "cp2a.py",
        '"""The T4.10 column label of a view period: `LTM Q4 25: a to b` -> `LTM Q4 25 (a to b)`."""',
    ): PARSER_DOC,
    (
        "cp2a.py",
        'currency: str = "USD"  # the run\'s reporting currency (`currency_basis`); USD without a context',
    ): DEFAULT_CURRENCY,
    ("cp2a.py", 'def __init__(self, base: BaseOperands, currency: str = "USD") -> None:'): (
        DEFAULT_CURRENCY
    ),
    (
        "cp2a.py",
        'def offered_bases(cp1: Iterable[Fact], currency: str = "USD") -> tuple[OfferedBase, ...]:',
    ): DEFAULT_CURRENCY,
    (
        "cp2a.py",
        'return stated.pop() if len(stated) == 1 else "USD"',
    ): "the T4.14 currency, else USD only for a refused context (no figure is offered)",
    (
        "cp2a.py",
        'pack: PreparedPack, submission: DownsideSubmission, upstream: Upstream, currency: str = "USD"',
    ): DEFAULT_CURRENCY,
    ("cp2e.py", 'if context.run.reporting_currency != "USD":'): (
        "blank base keeps the default year only for the default currency (ruling P8-R3)"
    ),
    ("cpl10.py", 'self, table: str, row: str, cp1: Mapping[str, Fact], currency: str = "USD"'): (
        DEFAULT_CURRENCY
    ),
    (
        "cpl10.py",
        'r: TopicResult, pair_period: str, cp1: Mapping[str, Fact], currency: str = "USD"',
    ): (DEFAULT_CURRENCY),
}


def _hits() -> list[tuple[str, int, str]]:
    found = []
    for path in sorted(OWNERS.glob("*.py")):
        if path.name == "period_basis.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                found.append((path.name, number, line.strip()))
    return found


def test_no_hardcoded_period_left() -> None:
    """The scan `git grep -nE 'LTM Q4 25|q4-2025|FY2026, FY2027|"USD"' src/deploy_workflow/owners`
    matches only `period_basis.py` and the named, reasoned lines of `ALLOWED`."""
    hits = _hits()
    assert [(f, n, s) for f, n, s in hits if (f, s) not in ALLOWED] == []
    assert sorted({(f, s) for f, _, s in hits}) == sorted(ALLOWED)  # no stale allow-list entry
    assert all(ALLOWED[(f, s)] for f, _, s in hits)
