"""Causal components over the independent quarter-only case, not participant evidence."""

import hashlib
import io
import json
import re
import shutil
from copy import copy, deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

import pytest

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack

MANIFEST = json.loads((Path(__file__).parents[1] / "cases/financial/manifest.json").read_text())
LIMIT = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
MISSING = "Quarterly financial statements were not supplied."


def make_pack(gap=False):
    run = dict(MANIFEST["run"])
    if gap:
        run["run_id"] = MANIFEST["negative_case"]["run_id"]
    sources = []
    for item in MANIFEST["sources"]:
        missing = gap and item["source_id"] == "financial"
        spans = () if missing else tuple(Span(**page) for page in item["pages"])
        if not missing:
            assert (
                hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest()
                == item["sha256"]
            )
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status="missing" if missing else "ready",
                sha256=None if missing else item["sha256"],
                spans=spans,
                extraction_status="blocked" if missing else "complete",
                limitation=MISSING
                if missing
                else LIMIT
                if item["source_id"] == "financial"
                else None,
            )
        )
    return PreparedPack(run=Run.model_validate_json(json.dumps(run)), sources=tuple(sources))


def cite(source, page, quote):
    item = next(s for s in MANIFEST["sources"] if s["source_id"] == source)
    assert quote in item["pages"][page - 1]["text"]
    return {
        "source_id": source,
        "source_sha256": item["sha256"],
        "locator": f"page:{page}",
        "quote": quote,
    }


IDENTITY = cite("identity", 1, "Northbridge Synthetic Group is the issuer and consolidated group.")
FINANCIAL = cite("financial", 1, "Currency: USD; amounts in millions.")


def readiness(pack, gap=False):
    return json.dumps(
        {
            "pack_sha256": pack.content_hash(),
            "objective": "Historical financial foundation",
            "reporting_period": "Reported FY2025, four calendar quarters and opening balance",
            "issuer_confirmed": True,
            "sources": [
                {
                    "source_id": "identity",
                    "document_family": "Identity note",
                    "authority": "issuer",
                    "entity": MANIFEST["run"]["issuer_name"],
                    "period": "January 2026",
                    "version_relationship": "Accompanying identity note",
                    "fidelity": "verified",
                    "citations": [IDENTITY],
                    "limitations": [],
                },
                {
                    "source_id": "financial",
                    "document_family": "Quarterly financial statements",
                    "authority": "unknown" if gap else "issuer",
                    "entity": None if gap else MANIFEST["run"]["issuer_name"],
                    "period": None if gap else "Four quarters in 2025",
                    "version_relationship": "Not supplied" if gap else "Unaudited quarterly source",
                    "fidelity": "blocked" if gap else "verified",
                    "citations": [] if gap else [FINANCIAL],
                    "limitations": [MISSING if gap else LIMIT],
                },
            ],
            "consumers": [
                {
                    "module_id": "CP-1",
                    "readiness": "CONDITIONAL" if gap else "READY_WITH_LIMITATIONS",
                    "evidence_demand": "Located historical statements, facility terms, definitions and scope",
                    "source_ids": ["identity"] if gap else ["identity", "financial"],
                    "rationale": MISSING
                    if gap
                    else "The selected historical owner method can run with explicit source and scope limitations.",
                    "citations": [IDENTITY] if gap else [IDENTITY, FINANCIAL],
                    "missing_source": "Quarterly financial statements" if gap else None,
                    "limitations": [MISSING if gap else LIMIT],
                }
            ],
            "gaps": [
                {
                    "gap_id": "missing-financial",
                    "kind": "source",
                    "severity": "material",
                    "description": MISSING,
                    "affected_modules": ["CP-1"],
                    "remediation": "Supply quarterly financial statements",
                }
            ]
            if gap
            else [],
            "analysis": [
                {
                    "claim_id": "source-assessment",
                    "text": "Identity is supported; financial source is missing."
                    if gap
                    else "Located quarterly financial statements support historical analysis with limitations.",
                    "citations": [IDENTITY] if gap else [IDENTITY, FINANCIAL],
                    "limitation": MISSING if gap else LIMIT,
                }
            ],
        }
    )


def start(tmp_path, gap=False):
    from deploy_workflow.financial_workflow import FinancialWorkflow

    pack = make_pack(gap)
    return FinancialWorkflow.create(
        tmp_path / "store", pack, model_directory=tmp_path / "model"
    ), pack


def read_sources(workflow, gap=False):
    assert (
        workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})[
            "status"
        ]
        == "ok"
    )
    if not gap:
        assert (
            workflow.invoke(
                "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
            )["status"]
            == "ok"
        )


def test_missing_source_requires_actual_begin_and_publisher_refusal(tmp_path):
    from deploy_workflow.financial_workflow import verify_financial_slice_receipt

    workflow, pack = start(tmp_path, gap=True)
    read_sources(workflow, gap=True)
    outcome = workflow.submit_review(readiness(pack, gap=True))
    assert outcome["status"] == "valid"
    assert outcome["refusal"] == "cp1_not_authorized"
    with pytest.raises(ValueError):
        workflow.write_receipt(tmp_path / "premature.json")
    published = workflow.publish_model()
    assert published["status"] == "refused"
    assert published["error_code"] == "cp1_not_authorized"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(tmp_path / "store")
    verify_financial_slice_receipt(store, receipt, model_directory=None)
    assert receipt.cp1 is receipt.model is None
    assert receipt.refusal == "cp1_not_authorized"
    assert [a.module_id for a in store.read().attempts] == ["CP-0"]
    assert not (tmp_path / "model").exists()


def test_no_input_projection_or_publication_before_authorization(tmp_path):
    workflow, _ = start(tmp_path)
    for operation in (workflow.read_inputs, workflow.publish_model):
        with pytest.raises(ValueError):
            operation()
    assert not (tmp_path / "model").exists()


def context(pack):
    scope_cite = cite("financial", 1, "The opening balance is December 31, 2024.")
    scopes = []
    for period in MANIFEST["periods"]:
        scopes.append(
            {
                "scope_id": period["period_id"],
                "entity_id": "issuer",
                "period_label": period["period_id"],
                "period_kind": "period_end"
                if period["period_type"] == "PERIOD_END"
                else "historical_duration",
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "currency": "USD",
                "unit": "MILLIONS",
                "accounting_basis": "IFRS",
                "entity_perimeter": "consolidated group",
                "citations": [scope_cite],
            }
        )
    return json.dumps(
        {
            "pack_sha256": pack.content_hash(),
            "entities": [
                {
                    "entity_id": "issuer",
                    "name": MANIFEST["run"]["issuer_name"],
                    "entity_type": "group",
                    "roles": ["issuer"],
                    "fiscal_year_end": "December 31",
                    "citations": [IDENTITY],
                    "limitations": [LIMIT],
                }
            ],
            "sources": [
                {
                    "source_id": "identity",
                    "classification": "nonfinancial",
                    "document_type": "Identity note",
                    "published_on": "2026-01-10",
                    "evidence_class": "internal",
                    "evidence_rationale": "Identity only",
                    "analytical_use": "Issuer identity",
                    "citations": [IDENTITY],
                    "event_scan": "unassessed",
                    "event_scan_explanation": "Identity is not event evidence",
                },
                {
                    "source_id": "financial",
                    "classification": "financial",
                    "document_type": "Quarterly statements",
                    "published_on": "2026-01-10",
                    "evidence_class": "unaudited_without_auditor",
                    "evidence_rationale": "No auditor report",
                    "analytical_use": "Historical financial analysis",
                    "citations": [FINANCIAL],
                    "scopes": scopes,
                    "event_scan": "no_events_identified",
                    "event_scan_explanation": "Explicit no-event disclosure through as-of",
                    "event_scan_citations": [
                        cite(
                            "financial",
                            1,
                            "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt changes through January 10, 2026.",
                        )
                    ],
                    "limitations": [LIMIT],
                },
            ],
            "limitations": [LIMIT],
        }
    )


# Source labels -> adopted statement identifiers; remaining printed detail stays other:.
ITEMS = {
    "Cost of sales": "cogs",
    "Gross profit": "gross_profit",
    "Selling general and administrative expenses including depreciation": "sga",
    "Operating expenses excluding cost of sales including depreciation": "opex_including_da",
    "Other operating expenses": "other_operating",
    "Revenue": "revenue",
    "Total operating expenses including depreciation": "opex_including_da",
    "Depreciation and amortization": "depreciation_amortization",
    "Operating profit EBIT": "ebit",
    "Reported EBITDA": "ebitda_reported",
    "Adjusted EBITDA": "ebitda_adjusted",
    "Net interest expense": "interest_expense_total",
    "Interest income": "interest_income",
    "Other non-operating income": "other_non_operating",
    "Profit before tax": "pretax_income",
    "Income tax expense": "income_tax_total",
    "Net profit": "net_income",
    "Exceptionals": "exceptionals",
    "Share based compensation": "sbc",
    "Operating lease cost": "operating_lease_cost",
    "Operating cash flow before working capital": "ocf_before_wc",
    "Working capital cash movement": "working_capital_change",
    "Operating cash flow": "cfo_ncfo",
    "Maintenance capital expenditure": "capex_maintenance",
    "Growth capital expenditure": "capex_growth",
    "Total capital expenditure": "capex_total",
    "Levered free cash flow": "fcf_levered",
    "Acquisitions": "acquisitions",
    "Disposals": "disposals",
    "Net cash used in investing": "investing_cash_flow",
    "Debt issuance": "debt_issuance",
    "Debt repayment": "debt_repayment",
    "Equity issuance": "equity_issuance",
    "Equity repurchases": "equity_buybacks",
    "Dividends paid": "dividends_paid",
    "Net cash used in financing": "financing_cash_flow",
    "Net change in cash": "net_cash_change",
    "Opening cash": "opening_cash",
    "Closing cash": "closing_cash",
    "Cash interest paid": "cash_interest_paid",
    "Cash tax paid": "cash_taxes_paid",
    "Lease payments in financing": "lease_payments_in_financing",
    "Interest paid in financing": "interest_paid_in_financing",
    "FX effect on cash": "fx_cash_effect",
    "Cash and cash equivalents": "cash_and_equivalents",
    "Trade receivables": "trade_receivables",
    "Inventories": "inventory",
    "Total current assets": "total_current_assets",
    "Property plant and equipment": "ppe_net",
    "Other noncurrent assets": "other_noncurrent_assets",
    "Total assets": "total_assets",
    "Senior secured term debt": "senior_secured_debt",
    "Total debt": "total_debt",
    "Trade payables": "trade_payables",
    "Other current liabilities": "other_current_liabilities",
    "Total current liabilities": "total_current_liabilities",
    "Total liabilities": "total_liabilities",
    "Shareholders equity": "shareholders_equity",
    "Total equity": "total_equity",
    "Restricted cash": "restricted_cash",
    "Short-term investments": "short_term_investments",
    "Other current assets": "other_current_assets",
    "Goodwill": "goodwill",
    "Other intangibles": "other_intangibles",
    "Short-term debt": "short_term_debt",
    "Current portion of long-term debt": "current_portion_long_term_debt",
    "Unsecured debt": "senior_unsecured_debt",
    "Subordinated debt": "subordinated_debt",
    "Pension obligations": "pension_obligations",
    "Lease obligations": "lease_obligations",
    "Minority interests": "minority_interests",
    "RCF commitment": "rcf_commitment",
    "RCF drawings": "rcf_drawn",
}


def observation(identifier, amount, citation):
    return {
        "observation_id": identifier,
        "status": "known",
        "amount": str(amount),
        "citations": [citation],
    }


def financials(pack):
    notes = cite(
        "financial",
        1,
        "No acquisitions, disposals, net equity movements, equity issuance, equity repurchases, leases, operating lease costs, lease cash payments, lease payments in financing, interest paid in financing, or other investing/financing cash flows occurred in any quarter or FY2025. Each such flow is explicitly zero.",
    )
    definitions = cite(
        "financial",
        5,
        "Reported EBITDA equals revenue less cost of sales less function-only operating expenses including depreciation plus depreciation and amortization. Each reported quarter and FY2025 use this definition. Adjusted EBITDA equals reported EBITDA because there are no adjustments.",
    )
    terms = cite(
        "financial",
        5,
        "The facility has floating rate type with SOFR reference rate, spread 0 basis points and floor 0 basis points. Fixed coupon is not applicable. Mandatory annual amortisation is 0; final maturity is December 31, 2029.",
    )
    statement_lines = []
    for locator, table in MANIFEST["extraction_expectations"].items():
        statement = {"page:2": "IS", "page:3": "CFS", "page:4": "BS"}[locator]
        source = MANIFEST["sources"][1]["pages"][int(locator[5:]) - 1]["text"]
        for priority, row in enumerate(table["rows"], 1):
            slug = re.sub("[^a-z0-9]+", "-", row["label"].lower()).strip("-")
            item = ITEMS.get(row["label"], "other:" + slug)
            if statement == "CFS" and item == "depreciation_amortization":
                item = "other:" + slug
            line_cite = cite("financial", int(locator[5:]), source.splitlines()[row["line_no"] - 1])
            for period, amount in zip(table["column_order"], row["decimal_values"], strict=True):
                statement_lines.append(
                    {
                        "line_id": statement.lower() + "-" + slug,
                        "statement": statement,
                        "item_id": item,
                        "label": row["label"],
                        "period_id": period,
                        "display_priority": priority,
                        "line_kind": "subtotal"
                        if item
                        in {
                            "cfo_ncfo",
                            "investing_cash_flow",
                            "financing_cash_flow",
                            "ocf_before_wc",
                            "capex_total",
                            "fcf_levered",
                        }
                        else "total"
                        if item.startswith("total_")
                        or item == "net_cash_change"
                        or row["label"] == "Total liabilities and equity"
                        else "detail",
                        "value": observation(
                            statement + "-" + slug + "-" + period, amount, line_cite
                        ),
                        "sign_convention": "outflow_magnitude"
                        if statement == "IS"
                        and item
                        in (
                            "opex_including_da",
                            "depreciation_amortization",
                            "interest_expense_total",
                            "income_tax_total",
                        )
                        else "signed",
                        "sign_citations": [line_cite]
                        if statement == "IS"
                        and item
                        in (
                            "opex_including_da",
                            "depreciation_amortization",
                            "interest_expense_total",
                            "income_tax_total",
                        )
                        else [],
                    }
                )
    periods = []
    accounts, facilities, segments, bridges = [], [], [], []
    for i, period in enumerate(MANIFEST["periods"]):
        pid = period["period_id"]
        periods.append(
            {
                **{key: val for key, val in period.items() if key != "reported"},
                "day_count": period.get("day_count"),
                "audit_status": "unaudited",
                "citations": [FINANCIAL],
                "expense_presentation": "by_function",
                "presentation_citations": [
                    cite("financial", 1, "Expenses are presented by function.")
                ],
                "limitation": "Point-in-time balance, not a duration" if i == 0 else None,
            }
        )
        facility_value = {
            "2024-12-31": "45",
            "2025-03-31": "46.25",
            "2025-06-30": "47.5",
            "2025-09-30": "48.75",
            "2025-12-31": "50",
        }[period["end_date"]]
        facility_cite = cite(
            "financial",
            5,
            next(
                line
                for line in MANIFEST["sources"][1]["pages"][4]["text"].splitlines()
                if line.startswith(period["end_date"])
            ),
        )

        def value(name, amount, citation=facility_cite):
            return observation(name + "-" + pid, amount, citation)

        facilities.append(
            {
                "facility_id": "term-loan",
                "facility_name": "Northbridge Term Loan",
                "period_id": pid,
                "facility_type": "TERM LOAN",
                "currency": "USD",
                "carrying_value": value("carrying", facility_value),
                "principal": value("principal", facility_value),
                "drawn_amount": value("drawn", facility_value),
                "commitment": value("commitment", "50"),
                "secured_status": "SECURED",
                "seniority": "SENIOR",
                "lease_classification": "NOT_LEASE",
                "margin_or_coupon": "SOFR plus zero basis points",
                "maturity_date": "2029-12-31",
                "maturity_limitation": None,
                "rate_type": "FLOATING",
                "reference_rate": "SOFR",
                "spread_bps": value("spread", "0", terms),
                "floor_bps": value("floor", "0", terms),
                "fixed_rate": {
                    "observation_id": "fixed-" + pid,
                    "status": "not_applicable",
                    "amount": None,
                    "citations": [terms],
                    "reason": "Floating instrument",
                },
                "annual_amortisation": value("amortisation", "0", terms),
                "terms_citations": [terms],
            }
        )
        # Explicit accounts supplement equivalent statement items; never substitute a missing zero.
        for metric in ("rcf_commitment", "rcf_drawn", "unsecured_debt"):
            accounts.append(
                {
                    "metric_id": metric,
                    "period_id": pid,
                    "value": value(
                        metric,
                        "0",
                        cite(
                            "financial",
                            5,
                            "No leases, unsecured debt, revolving commitments or revolving drawings exist at any reporting date.",
                        )
                        if metric == "unsecured_debt"
                        else cite(
                            "financial",
                            1,
                            "There is no revolving credit facility: RCF commitment and RCF drawings are each zero at opening and every quarter/FY end.",
                        ),
                    ),
                }
            )
        # BS aliases have identical stated meaning, without a new calculation.
        for metric, label in (
            ("net_accounts_receivable", "Trade receivables"),
            ("accounts_payable", "Trade payables"),
        ):
            row = next(
                r
                for r in statement_lines
                if r["period_id"] == pid and r["statement"] == "BS" and r["label"] == label
            )
            accounts.append(
                {
                    "metric_id": metric,
                    "period_id": pid,
                    "value": {**row["value"], "observation_id": metric + "-" + pid},
                }
            )
        if i:
            net_debt = next(
                r
                for r in statement_lines
                if r["period_id"] == pid
                and r["statement"] == "CFS"
                and r["label"] == "Net debt issuance"
            )
            accounts.append(
                {
                    "metric_id": "net_debt_issue_repay",
                    "period_id": pid,
                    "value": {**net_debt["value"], "observation_id": "net-debt-" + pid},
                }
            )
            for metric in (
                "acquisitions_disposals",
                "net_equity_issue_repay",
                "other_investing_financing",
                "cash_lease_payments",
            ):
                accounts.append(
                    {"metric_id": metric, "period_id": pid, "value": value(metric, "0", notes)}
                )
            segments.append(
                {
                    "segment_id": "operations",
                    "segment_name": "Consolidated Operations",
                    "segment_type": "OPERATING_SEGMENT",
                    "display_priority": 1,
                    "period_id": pid,
                    "revenue": value(
                        "segment-revenue",
                        "120" if period["period_type"] == "FY" else "30",
                        cite(
                            "financial",
                            1,
                            "One operating segment, Consolidated Operations, reports revenue of 30 in each quarter and 120 in FY2025; there are no corporate or elimination segments.",
                        ),
                    ),
                    "classification_citations": [
                        cite(
                            "financial",
                            1,
                            "One operating segment, Consolidated Operations, reports revenue of 30 in each quarter and 120 in FY2025; there are no corporate or elimination segments.",
                        )
                    ],
                }
            )
            bridges.append(
                {
                    "bridge_id": "cash-bridge-" + pid,
                    "period_id": pid,
                    "components": [],
                    "explanation": "No FX or other cash adjustment occurred",
                    "citations": [
                        cite(
                            "financial",
                            1,
                            "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt changes through January 10, 2026.",
                        )
                    ],
                }
            )
    disclosure_cite = cite(
        "financial",
        1,
        "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete.",
    )
    identities = []
    statement_disclosures = []
    for period in MANIFEST["periods"]:
        pid = period["period_id"]
        for statement, page in (
            (("BS", 4),)
            if period["period_type"] == "PERIOD_END"
            else (("IS", 2), ("CFS", 3), ("BS", 4))
        ):
            caption = MANIFEST["extraction_expectations"][f"page:{page}"]["caption"]
            statement_disclosures.append(
                {
                    "statement": statement,
                    "period_id": pid,
                    "disclosure": {
                        "status": "complete",
                        "explanation": "All printed source lines retained; nonreported data remain explicitly unavailable",
                        "citations": [cite("financial", page, caption)],
                    },
                }
            )
        if period["period_type"] == "PERIOD_END":
            continue
        for identity, target, components, source_quote in (
            (
                "cfo",
                "cfs-operating-cash-flow",
                (
                    "cfs-net-profit",
                    "cfs-depreciation-and-amortization",
                    "cfs-working-capital-cash-movement",
                ),
                "CFO equals net profit plus depreciation and amortization plus the signed working-capital cash movement.",
            ),
            (
                "ncf",
                "cfs-net-change-in-cash",
                (
                    "cfs-operating-cash-flow",
                    "cfs-net-cash-used-in-investing",
                    "cfs-net-cash-used-in-financing",
                ),
                "Net cash change equals operating cash flow plus net investing cash flow plus net financing cash flow.",
            ),
        ):
            assert all(
                any(
                    line["period_id"] == pid and line["line_id"] == line_id
                    for line in statement_lines
                )
                for line_id in (target, *components)
            )
            target_line = next(
                line
                for line in statement_lines
                if line["period_id"] == pid and line["line_id"] == target
            )
            assert target_line["line_kind"] in ("subtotal", "total")
            assert len(set(components)) == len(components) and target not in components
            identities.append(
                {
                    "identity_id": identity + "-" + pid,
                    "period_id": pid,
                    "target_line_id": target,
                    "components": [
                        {"line_id": line_id, "coefficient": 1} for line_id in components
                    ],
                    "explanation": source_quote,
                    "citations": [cite("financial", 5, source_quote)],
                }
            )
    equity_note = "The complete equity roll-forward in each quarter consists only of net profit 4 and dividends paid (2.25); FY2025 consists only of net profit 16 and dividends paid (9). Other comprehensive income and every other equity movement were zero throughout these periods: no capital contributions, share issuance, repurchases, revaluations, currency translation, perimeter changes, reserve transfers or other equity adjustments occurred."
    movements, movement_bridges = [], []
    for period in MANIFEST["periods"]:
        if period["period_type"] == "PERIOD_END":
            continue
        pid = period["period_id"]
        dividend = next(
            line
            for line in statement_lines
            if line["period_id"] == pid
            and line["statement"] == "CFS"
            and line["item_id"] == "dividends_paid"
        )
        movements.append(
            {
                "movement_id": "dividends",
                "label": "Dividends paid",
                "period_id": pid,
                "role": "distribution",
                "value": {**dividend["value"], "observation_id": "equity-dividends-" + pid},
                "sign_convention": "signed",
            }
        )
        # Core adds opening total equity and IS net income; naming NI again would double count.
        movement_bridges.append(
            {
                "bridge_id": "equity-bridge-" + pid,
                "period_id": pid,
                "balance_item_id": "total_equity",
                "movement_ids": ["dividends"],
                "disclosure": {
                    "status": "complete",
                    "explanation": "Only sourced net income and signed dividends changed total equity; other movements explicitly zero",
                    "citations": [cite("financial", 1, equity_note)],
                },
            }
        )
    book = {
        "book_id": "consolidated",
        "periods": periods,
        "accounts": accounts,
        "addbacks": [],
        "segments": segments,
        "kpis": [],
        "facilities": facilities,
        "pro_forma": [],
        "statement_lines": statement_lines,
        "statement_identities": identities,
        "statement_disclosures": statement_disclosures,
        "cash_movement_bridges": bridges,
        "balance_movements": movements,
        "balance_movement_bridges": movement_bridges,
        "segment_allocation": [
            {
                "slot_id": "DIVISION_1",
                "slot_label": "Consolidated Operations",
                "component_segment_ids": ["operations"],
                "rationale": "The sole disclosed operating segment",
            }
        ],
        "addback_disclosure": {
            "status": "complete",
            "explanation": "No addbacks occurred",
            "citations": [disclosure_cite],
        },
        "segment_disclosure": {
            "status": "complete",
            "explanation": "Sole segment disclosed",
            "citations": [FINANCIAL],
        },
        "limitations": [LIMIT],
    }
    return {
        "financial": {
            "run_id": pack.run.run_id,
            "issuer_id": pack.run.issuer_id,
            "as_of": pack.run.as_of.isoformat(),
            "books": [book],
            "analysis": [],
            "limitations": [LIMIT],
        },
        "definition": {
            "book_id": "consolidated",
            "assessments": [
                {
                    "assessment_id": "definition-" + item,
                    "metric": item,
                    "canonical_definition": "Historical reported EBITDA bridge; no adjustment is present",
                    "issuer_definition": "Revenue less operating expenses including depreciation plus depreciation and amortization; adjusted equals reported",
                    "status": "aligned",
                    "observation_ids": [
                        line["value"]["observation_id"]
                        for line in statement_lines
                        if line["statement"] == "IS" and line["item_id"] == item
                    ],
                    "citations": [definitions],
                    "materiality": "Material earnings definition",
                    "downstream_impact": "Historical earnings basis only",
                    "recommendation": "Obtain covenant definitions separately",
                }
                for item in ("ebitda_reported", "ebitda_adjusted")
            ],
            "events": [],
            "limitations": ["No covenant definition is supplied"],
        },
        "binding": {"books": [{"book_id": "consolidated", "entity_id": "issuer"}]},
    }


def parsed_evidence(body):
    rows, columns, kind = [], None, None
    for line in body.splitlines():
        if line.startswith("kind="):
            kind = line.split()[0][5:]
            columns = json.loads(line.split(" columns=", 1)[1])
        elif line.startswith("[") and columns:
            rows.append({**dict(zip(columns, json.loads(line), strict=True)), "kind": kind})
    return rows


def narrative(read):
    rows = parsed_evidence(read["body"])
    bs = [r for r in rows if r["kind"] == "statement_BS" and r["line_id"] is not None]
    debt = next(r for r in bs if r["item_id"] == "total_debt" and r["period_id"] == "q4-2025")
    calculated = [r for r in rows if r["kind"] == "kpi" and r["amount"] is not None]
    dimensions = (
        "leverage",
        "coverage",
        "cash_flow_quality",
        "liquidity",
        "data_quality",
        "definition_risks",
        "key_gaps",
    )
    messages = {
        "leverage": (
            "Debt remains material",
            "Debt obligations constrain financial flexibility",
            "Review earnings resilience alongside scheduled debt",
        ),
        "coverage": (
            "Cash interest consumes earnings",
            "Interest service competes with other cash uses",
            "Monitor available earnings for debt service",
        ),
        "cash_flow_quality": (
            "Operating cash supports maintenance spending",
            "Capital requirements reduce cash available to creditors",
            "Retain focus on cash conversion and distributions",
        ),
        "liquidity": (
            "Cash balances support flexibility",
            "Cash is available alongside contractual debt obligations",
            "Assess liquidity within the disclosed consolidated scope",
        ),
        "data_quality": (
            "Historical source remains unaudited",
            "Lack of assurance limits reliance on reported amounts",
            "Seek audited corroboration before stronger conclusions",
        ),
        "definition_risks": (
            "Historical EBITDA has a stated definition",
            "Covenant definitions may differ from the reported measure",
            "Obtain executed covenant definitions for legal analysis",
        ),
        "key_gaps": (
            "Perimeter evidence remains limited",
            "Consolidated resources may differ from creditor-accessible resources",
            "Obtain borrower and guarantor scope evidence",
        ),
    }
    findings, coverage = [], []
    for dimension in dimensions:
        title, risk, credit = messages[dimension]
        chosen = debt
        if dimension in ("leverage", "coverage"):
            key = (
                "total_leverage_reported"
                if dimension == "leverage"
                else "interest_coverage_reported"
            )
            chosen = next(r for r in calculated if r["key"] == key)
        elif dimension == "cash_flow_quality":
            chosen = next(
                r
                for r in rows
                if r["kind"] == "statement_CFS"
                and r["item_id"] == "fcf_levered"
                and r["period_id"] == "q4-2025"
            )
        elif dimension == "liquidity":
            chosen = next(
                r
                for r in bs
                if r["item_id"] == "cash_and_equivalents" and r["period_id"] == "q4-2025"
            )
        elif dimension == "data_quality":
            chosen = next(
                r for r in rows if r["kind"] == "source" and r["source_id"] == "financial"
            )
        elif dimension == "definition_risks":
            chosen = next(
                r for r in rows if r["kind"] == "definition" and r["metric"] == "ebitda_reported"
            )
        elif dimension == "key_gaps":
            chosen = next(r for r in rows if r["kind"] == "entity")
        evidence = [{"kind": "issuer"}, {"kind": "evidence", "evidence_id": chosen["evidence_id"]}]
        findings.append(
            {
                "finding_id": dimension,
                "dimension": dimension,
                "title": title,
                "evidence": evidence,
                "risk_mechanic": [{"kind": "prose", "text": risk}],
                "credit_implication": [{"kind": "prose", "text": credit}],
            }
        )
        coverage.append(
            {
                "dimension": dimension,
                "status": "addressed",
                "finding_ids": [dimension],
                "rationale": [
                    {"kind": "prose", "text": "Assessed within the disclosed historical scope"}
                ],
            }
        )
    return {
        "findings": findings,
        "coverage": coverage,
        "stories": [],
        "funding": {
            "status": "no_material_items",
            "reviewed_statement_ids": [r["evidence_id"] for r in bs],
            "material_statement_ids": [],
            "rationale": [
                {
                    "kind": "prose",
                    "text": "Located balance sheet contains disclosed debt and standard operating liabilities",
                }
            ],
        },
        "limitations": [LIMIT],
    }


def before_financials(root, *, invalid_context_retries=0):
    workflow, pack = start(root)
    read_sources(workflow)
    assert workflow.submit_review(readiness(pack))["status"] == "valid"
    for _ in range(invalid_context_retries):
        assert workflow.submit_review("{}")["status"] == "invalid"
    workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})
    workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    outcome = workflow.submit_review(context(pack))
    assert outcome["status"] == "valid", outcome
    return workflow, pack


def financial_reads(workflow):
    workflow.invoke(
        "extract_statements", {"source_id": "financial", "locators": ["page:2", "page:3", "page:4"]}
    )
    workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})
    workflow.invoke("read_pages", {"source_id": "financial", "first_page": 5, "last_page": 5})
    workflow.invoke("search_pack", {"query": "not disclosed", "source_id": "financial"})


def quality_ready_case(root, *, invalid_context_retries=0):
    workflow, pack = before_financials(root, invalid_context_retries=invalid_context_retries)
    financial_reads(workflow)
    outcome = workflow.submit_review(json.dumps(financials(pack)))
    assert outcome["status"] == "valid", outcome
    read = workflow.read_inputs()
    assert "record_json" not in read["body"] and '"quote"' not in read["body"]
    raw_row = MANIFEST["sources"][1]["pages"][3]["text"].splitlines()[4]
    assert raw_row not in read["body"]
    kpi_ids = {r["evidence_id"] for r in parsed_evidence(read["body"]) if r["kind"] == "kpi"}
    assert (
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})[
            "error_code"
        ]
        == "not_permitted"
    )
    outcome = workflow.submit_review(json.dumps(narrative(read)))
    assert outcome["status"] == "valid", outcome
    read = workflow.read_inputs()
    assert "record_json" not in read["body"] and '"quote"' not in read["body"]
    outcome = workflow.submit_review(json.dumps({"consumers": []}))
    assert outcome["status"] == "valid", outcome
    qa = workflow.read_inputs()
    inputs = json.loads(qa["body"])
    assert "record_json" not in qa["body"] and '"quote"' not in qa["body"]
    # Independent authored judgments: sourced records are Directly Sourced; Python KPIs Calculated.
    raw_qa = {
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "material": True,
                "evidence": [
                    {
                        "evidence_id": evidence_id,
                        "lineage_class": "Calculated"
                        if evidence_id in kpi_ids
                        else "Directly Sourced",
                        "rationale": "Python calculation"
                        if evidence_id in kpi_ids
                        else "Located source balance-sheet observation",
                    }
                    for evidence_id in claim["evidence_ids"]
                ],
                "rationale": "Material historical credit consideration",
            }
            for claim in inputs["claims"]
        ]
    }
    # Freeze inputs/judgments and independently calculated formula before evaluating promotion.
    inventory = {"inputs": inputs, "raw_review": raw_qa}
    (root / "qa-inventory.json").write_text(json.dumps(inventory, indent=2))
    weights = {"Directly Sourced": 10, "Calculated": 9}
    evidence = Fraction(
        sum(
            max(weights[e["lineage_class"]] for e in claim["evidence"])
            for claim in raw_qa["claims"]
        )
        * 10,
        len(raw_qa["claims"]),
    )
    coverage = Fraction(
        sum(c["present"] for c in inputs["coverage"]) * 100, len(inputs["coverage"])
    )
    multiplier = {"pass": Fraction(1), "partial": Fraction(7, 10), "fail": Fraction(0)}[
        inputs["source_gate"]
    ]
    penalties = sum(
        {"CRITICAL": 40, "MATERIAL": 15, "MINOR": 3}[f["severity"]]
        for f in inputs["inherited_findings"]
        if f["status"] == "open"
    )
    raw_score = max(
        Fraction(0),
        min(
            Fraction(100),
            (Fraction(3, 5) * evidence + Fraction(2, 5) * coverage) * multiplier - penalties,
        ),
    )
    score = round(min(raw_score, Fraction(59)))
    (root / "qa-expected.json").write_text(json.dumps({"score": score, "status": "Restricted"}))
    return workflow, raw_qa, score


def promoted_case(root, *, invalid_context_retries=0):
    workflow, raw_qa, score = quality_ready_case(
        root, invalid_context_retries=invalid_context_retries
    )
    outcome = workflow.submit_review(json.dumps(raw_qa))
    assert outcome["status"] == "valid", outcome
    from deploy_vii.cp1_workflow import CP1Handoff

    store = Execution(root / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    handoff = CP1Handoff.model_validate_json(store.step_output(attempt.steps[-1].output_sha256))
    assert handoff.quality.confidence.qa_status == "Restricted"
    assert handoff.quality.confidence.confidence_score == score
    return workflow


def completed_financial_case(root: Path, *, gap: bool = False) -> tuple[Path, Path, Path | None]:
    """Genuine component helper for C2 after integration; never actual participant acceptance."""
    root.mkdir(parents=True, exist_ok=True)
    if gap:
        workflow, pack = start(root, gap=True)
        read_sources(workflow, gap=True)
        assert workflow.submit_review(readiness(pack, gap=True))["status"] == "valid"
    else:
        workflow = promoted_case(root)
    outcome = workflow.publish_model()
    assert outcome["status"] == ("refused" if gap else "ok"), outcome
    receipt_path = root / "receipt.json"
    workflow.write_receipt(receipt_path)
    return root / "store", receipt_path, None if gap else root / "model"


def copy_closed_case(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("store", "model"):
        shutil.copytree(source / name, destination / name)
    for name in ("receipt.json", "qa-inventory.json", "qa-expected.json"):
        shutil.copy2(source / name, destination / name)
    return destination


@pytest.fixture(scope="module")
def genuine_closed_case(tmp_path_factory):
    """Use immutable genuine evidence when available; clean checkouts build it through the API."""
    from deploy_workflow.financial_workflow import (
        FinancialSliceReceipt,
        verify_financial_slice_receipt,
    )

    root = tmp_path_factory.mktemp("financial-closed")
    archive = Path(__file__).parents[1] / "work/qualified-cp1-v4"
    cached = (
        FinancialSliceReceipt.model_validate_json((archive / "receipt.json").read_bytes())
        if (archive / "receipt.json").exists()
        else None
    )
    if cached is not None and cached.pack_sha256 == make_pack().content_hash():
        copy_closed_case(archive, root)
    else:
        completed_financial_case(root)
    receipt = FinancialSliceReceipt.model_validate_json((root / "receipt.json").read_bytes())
    verify_financial_slice_receipt(
        Execution(root / "store"), receipt, model_directory=root / "model"
    )
    return root


def clone_workflow(template, destination):
    """Isolated causal fork of a genuinely reached source-free state; no Module injection."""
    assert template._session is None and template._phase in ("analytical", "promoted")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template._store.directory, destination / "store")
    for name in ("qa-inventory.json", "qa-expected.json"):
        shutil.copy2(template._store.directory.parent / name, destination / name)
    workflow = copy(template)
    workflow._store = Execution(destination / "store")
    workflow._model_directory = destination / "model"
    workflow._operation = Lock()
    for name in ("_calls", "_reads", "_submissions", "_publications", "_epoch_calls"):
        setattr(workflow, name, list(getattr(template, name)))
    workflow._limits = template._limits.copy()
    return workflow


@pytest.fixture(scope="module")
def genuine_quality_case(tmp_path_factory):
    root = tmp_path_factory.mktemp("financial-quality")
    return quality_ready_case(root, invalid_context_retries=2)


@pytest.fixture(scope="module")
def genuine_promoted_case(genuine_quality_case, tmp_path_factory):
    template, review, score = genuine_quality_case
    workflow = clone_workflow(template, tmp_path_factory.mktemp("financial-promoted"))
    outcome = workflow.submit_review(json.dumps(deepcopy(review)))
    assert outcome["status"] == "valid", outcome
    return workflow


def test_full_component_promotes_and_publishes_actual_model(tmp_path, genuine_closed_case):
    from deploy_vii.downstream_readiness import DownstreamReport
    from deploy_workflow.financial_workflow import (
        FinancialSliceReceipt,
        verify_financial_slice_receipt,
    )

    copy_closed_case(genuine_closed_case, tmp_path)
    execution, receipt_path, model = (
        tmp_path / "store",
        tmp_path / "receipt.json",
        tmp_path / "model",
    )
    receipt = FinancialSliceReceipt.model_validate_json(receipt_path.read_bytes())
    store = Execution(execution)
    assert receipt.cp1.status == "restricted"
    attempt = next(a for a in store.read().attempts if a.ticket_id == receipt.cp1.ticket_id)
    downstream = DownstreamReport.model_validate_json(
        store.step_output(attempt.steps[3].output_sha256)
    )
    assert downstream.model.status == "ready"
    assert len(downstream.inputs.model.readiness.selected_quarters) == 4
    # Copy portability includes immutable stores/audits; no original absolute path is authority.
    copied = tmp_path / "portable"
    shutil.copytree(execution, copied / "store")
    shutil.copytree(model, copied / "model")
    verify_financial_slice_receipt(
        Execution(copied / "store"), receipt, model_directory=copied / "model"
    )


@pytest.mark.parametrize("defect", ["unread", "unextracted", "omitted", "swapped"])
def test_financial_evidence_refusal_preserves_prefix(tmp_path, defect):
    workflow, pack = before_financials(tmp_path)
    if defect == "unread":
        workflow.invoke(
            "extract_statements",
            {"source_id": "financial", "locators": ["page:2", "page:3", "page:4"]},
        )
    elif defect == "unextracted":
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 5})
    else:
        financial_reads(workflow)
    payload = financials(pack)
    lines = payload["financial"]["books"][0]["statement_lines"]
    if defect == "omitted":
        lines[:] = [line for line in lines if line["label"] != "Revenue"]
    elif defect == "swapped":
        selected = [
            line
            for line in lines
            if line["label"] == "Cash and cash equivalents"
            and line["period_id"] in ("q1-2025", "q4-2025")
        ]
        selected[0]["value"]["amount"], selected[1]["value"]["amount"] = (
            selected[1]["value"]["amount"],
            selected[0]["value"]["amount"],
        )
    store = Execution(tmp_path / "store")
    before = store.read().content_hash()
    outcome = workflow.submit_review(json.dumps(payload))
    assert outcome["status"] == "refused", outcome
    assert store.read().content_hash() == before
    assert (
        next(a for a in store.read().attempts if a.module_id == "CP-1").steps[0].status == "valid"
    )


def test_current_snapshot_change_refuses_source_and_submission(tmp_path):
    workflow, pack = start(tmp_path)
    store = Execution(tmp_path / "store")
    store.interrupt(store.read().attempts[0].ticket_id, "Causal external transition")
    for operation in (
        lambda: workflow.invoke(
            "read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1}
        ),
        lambda: workflow.submit_review(readiness(pack)),
    ):
        with pytest.raises(ValueError, match="stale_binding"):
            operation()


def test_repeated_identical_invalid_review_uses_core_repair(tmp_path):
    workflow, pack = start(tmp_path)
    read_sources(workflow)
    assert workflow.submit_review(readiness(pack))["status"] == "valid"
    first = workflow.submit_review("{}")
    second = workflow.submit_review("{}")
    assert first["status"] == second["status"] == "invalid"
    assert second["next_step"] == "source_context"
    attempts = [a for a in Execution(tmp_path / "store").read().attempts if a.module_id == "CP-1"]
    assert (
        len(attempts) == 2 and attempts[0].status == "finished" and attempts[1].status == "pending"
    )
    assert len(attempts[0].step_repairs) == len(attempts[0].steps) == 1
    assert (
        workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})[
            "status"
        ]
        == "ok"
    )


def test_qa_lineage_upgrade_refuses_actual_promotion(tmp_path, genuine_quality_case):
    template, raw_review, _ = genuine_quality_case
    workflow = clone_workflow(template, tmp_path)
    review = deepcopy(raw_review)
    calculated = next(
        e for c in review["claims"] for e in c["evidence"] if e["lineage_class"] == "Calculated"
    )
    calculated["lineage_class"] = "Directly Sourced"
    outcome = workflow.submit_review(json.dumps(review))
    assert outcome["status"] == "invalid"
    assert any("lineage upgrade rejected" in issue for issue in outcome["issues"])
    assert not any(
        h.module_id == "CP-1" and h.status in ("accepted", "restricted")
        for h in Execution(tmp_path / "store").read().heads
    )


def test_partial_publication_quarantined_repair_and_history(
    tmp_path, monkeypatch, genuine_promoted_case
):
    import deploy_vii.cp_model_workflow as core
    from deploy_workflow.financial_workflow import verify_financial_slice_receipt

    workflow = clone_workflow(genuine_promoted_case, tmp_path)

    def fail_write(output, files):
        output.mkdir()
        (output / "model.html").write_text(files["model.html"], encoding="utf-8")
        raise OSError("Causal partial publication")

    original_read_bytes = Path.read_bytes

    def unreadable_partial(path):
        if path == tmp_path / "model/model.html":
            raise PermissionError("Causal unreadable partial output")
        return original_read_bytes(path)

    with monkeypatch.context() as patch:
        patch.setattr(core, "_write", fail_write)
        patch.setattr(Path, "read_bytes", unreadable_partial)
        assert workflow.publish_model()["status"] == "refused"
    assert "partial hash failed" in workflow._publications[-1].reason
    assert not (tmp_path / "model").exists()
    assert len(list(tmp_path.glob("model.failed-*"))) == 1
    assert workflow.publish_model()["status"] == "ok"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [p.status for p in receipt.publications] == ["failed", "published"]
    store = Execution(tmp_path / "store")
    omitted = receipt.publications[0]
    forged = receipt.model_copy(update={"publications": receipt.publications[1:]})
    (store.directory / "financial-slice-audit/publications" / omitted.content_hash()).unlink()
    (store.directory / "financial-slice-audit/receipt.sha256").write_text(forged.content_hash())
    with pytest.raises(ValueError):
        verify_financial_slice_receipt(store, forged, model_directory=tmp_path / "model")


def test_finish_and_interrupt_failure_still_quarantines(
    tmp_path, monkeypatch, genuine_promoted_case
):
    workflow = clone_workflow(genuine_promoted_case, tmp_path)

    def unavailable_finish(*args, **kwargs):
        raise OSError("Causal journal write failure")

    monkeypatch.setattr(workflow._store, "finish", unavailable_finish)
    assert workflow.publish_model()["status"] == "refused"
    assert not (tmp_path / "model").exists()
    assert len(list(tmp_path.glob("model.failed-*"))) == 1
    assert workflow._publications[-1].status == "failed"
    assert "interruption failed" in workflow._publications[-1].reason
    with pytest.raises(ValueError):
        workflow.write_receipt(tmp_path / "refused.json")
    assert not (tmp_path / "refused.json").exists()


def test_publication_bytes_live_head_and_foreign_store_refuse(tmp_path, genuine_closed_case):
    from deploy_workflow.financial_workflow import (
        FinancialSliceReceipt,
        verify_financial_slice_receipt,
    )

    root = copy_closed_case(genuine_closed_case, tmp_path / "positive")
    execution, receipt_path, model = root / "store", root / "receipt.json", root / "model"
    receipt = FinancialSliceReceipt.model_validate_json(receipt_path.read_bytes())
    store = Execution(execution)
    for name in ("model.html", "calculation.json", "receipt.json"):
        original = (model / name).read_bytes()
        (model / name).write_bytes(original + b"tamper")
        with pytest.raises(ValueError):
            verify_financial_slice_receipt(store, receipt, model_directory=model)
        (model / name).write_bytes(original)
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-MODEL")
    for changes in (
        {"status": "accepted"},
        {"inputs": ()},
        {
            "qualification": head.qualification.model_copy(
                update={"analytical_qualification": "qualified"}
            )
        },
    ):
        altered = head.model_copy(update=changes)
        store._write(
            snapshot.model_copy(
                update={
                    "heads": tuple(
                        altered if h.module_id == "CP-MODEL" else h for h in snapshot.heads
                    )
                }
            )
        )
        forged_snapshot = store.read().content_hash()
        rebound = receipt.publications[-1].model_copy(
            update={"snapshot_after_sha256": forged_snapshot}
        )
        publications = (*receipt.publications[:-1], rebound)
        publication_audit = store.directory / "financial-slice-audit/publications"
        for path in publication_audit.iterdir():
            path.unlink()
        for publication in publications:
            (publication_audit / publication.content_hash()).write_text(
                publication.model_dump_json()
            )
        forged = receipt.model_copy(
            update={"snapshot_sha256": forged_snapshot, "publications": publications}
        )
        (store.directory / "financial-slice-audit/receipt.sha256").write_text(forged.content_hash())
        with pytest.raises(ValueError):
            verify_financial_slice_receipt(store, forged, model_directory=model)
    (store.directory / "current").write_text(snapshot.content_hash() + "\n")
    for path in publication_audit.iterdir():
        path.unlink()
    for publication in receipt.publications:
        (publication_audit / publication.content_hash()).write_text(publication.model_dump_json())
    (store.directory / "financial-slice-audit/receipt.sha256").write_text(receipt.content_hash())
    gap_store, _, _ = completed_financial_case(tmp_path / "gap", gap=True)
    with pytest.raises(ValueError):
        verify_financial_slice_receipt(Execution(gap_store), receipt, model_directory=model)


def test_invalid_repair_cannot_disappear_from_sealed_audit(tmp_path, genuine_promoted_case):
    from deploy_workflow.financial_workflow import verify_financial_slice_receipt

    workflow = clone_workflow(genuine_promoted_case, tmp_path)
    assert workflow.publish_model()["status"] == "ok"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    rejected = [s for s in receipt.submissions if s.disposition == "invalid"]
    assert len(rejected) == 2
    retained = tuple(
        s.model_copy(update={"sequence": index})
        for index, s in enumerate((s for s in receipt.submissions if s not in rejected), 1)
    )
    forged = receipt.model_copy(update={"submissions": retained})
    store = Execution(tmp_path / "store")
    # Coherently rewrite sequences/audit so journal completeness must detect the omission.
    for path in (store.directory / "financial-slice-audit/submissions").iterdir():
        path.unlink()
    for submission in retained:
        (
            store.directory / "financial-slice-audit/submissions" / submission.content_hash()
        ).write_text(submission.model_dump_json())
    for submission in rejected:
        (
            store.directory / "financial-slice-audit/bindings" / submission.binding.content_hash()
        ).unlink()
    (store.directory / "financial-slice-audit/receipt.sha256").write_text(forged.content_hash())
    with pytest.raises(ValueError):
        verify_financial_slice_receipt(store, forged, model_directory=tmp_path / "model")


def test_existing_destination_preserved_at_setup(tmp_path):
    from deploy_workflow.financial_workflow import FinancialWorkflow

    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep").write_text("Preserve me")
    with pytest.raises(ValueError):
        FinancialWorkflow.create(tmp_path / "store", make_pack(), model_directory=destination)
    assert (destination / "keep").read_text() == "Preserve me"
    assert not (tmp_path / "store").exists()


def test_column_period_identity_and_ambiguity():
    from deploy_workflow.financial_workflow import _column_periods

    q4 = SimpleNamespace(
        period_id="q4",
        period_type="QUARTER",
        fiscal_year="2025",
        fiscal_quarter=4,
        end_date=date(2025, 12, 31),
    )
    fy = SimpleNamespace(
        period_id="fy",
        period_type="FY",
        fiscal_year="2025",
        fiscal_quarter=None,
        end_date=date(2025, 12, 31),
    )
    periods = (q4, fy)
    assert _column_periods(("Period  Q4 2025  FY 2025",), periods) == (
        frozenset({"q4"}),
        frozenset({"fy"}),
    )
    assert _column_periods(("Period end  Q4 2025-12-31  FY 2025-12-31",), periods) == (
        frozenset({"q4"}),
        frozenset({"fy"}),
    )
    assert _column_periods(("Period  Q4 2025",), (*periods, q4)) is None
    assert _column_periods(("Period  FY 2025  FY 2025",), periods) is None
    assert _column_periods(("Unknown  unsupported", "Period  FY 2025"), periods) == (
        frozenset({"fy"}),
    )
    assert _column_periods(("Unknown  unsupported", "Period  FY 2025"), iter(periods)) is None


def test_prose_statement_mention_does_not_require_empty_note_extraction(tmp_path):
    workflow, pack = before_financials(tmp_path)
    financial_reads(workflow)
    assert "No FY2024 annual income statement" in MANIFEST["sources"][1]["pages"][0]["text"]
    outcome = workflow.submit_review(json.dumps(financials(pack)))
    assert outcome["status"] == "valid", outcome


def test_actual_empty_standalone_statement_still_refuses(tmp_path, monkeypatch):
    changed = deepcopy(MANIFEST)
    changed["run"]["run_id"] = "causal-empty-caption"
    financial = changed["sources"][1]
    financial["pages"].append({"locator": "page:6", "text": "CONSOLIDATED INCOME STATEMENT"})
    financial["sha256"] = hashlib.sha256(
        "\f".join(p["text"] for p in financial["pages"]).encode()
    ).hexdigest()
    monkeypatch.setitem(globals(), "MANIFEST", changed)
    monkeypatch.setitem(
        globals(), "FINANCIAL", cite("financial", 1, "Currency: USD; amounts in millions.")
    )
    workflow, pack = before_financials(tmp_path)
    financial_reads(workflow)
    extracted = workflow.invoke(
        "extract_statements", {"source_id": "financial", "locators": ["page:6"]}
    )
    assert extracted["status"] == "ok"
    before = Execution(tmp_path / "store").read().content_hash()
    outcome = workflow.submit_review(json.dumps(financials(pack)))
    assert outcome["status"] == "refused"
    assert any("unmeasured" in issue for issue in outcome["issues"])
    assert Execution(tmp_path / "store").read().content_hash() == before


def test_source_free_refusal_detaches_mutable_arguments(tmp_path, genuine_quality_case):
    workflow = clone_workflow(genuine_quality_case[0], tmp_path)
    arguments = {"source_id": "financial", "scope": {"value": "before"}}
    result = workflow.invoke("read_pages", arguments)
    assert result["error_code"] == "not_permitted" and result["body"] is None
    arguments["scope"]["value"] = "after"
    assert workflow._calls[-1].arguments["scope"]["value"] == "before"
    assert result["arguments"]["scope"]["value"] == "before"


def test_transport_rejects_nonfinite_json_before_tool_invocation(tmp_path):
    from deploy_workflow.financial_workflow import serve_json_lines

    workflow, _ = start(tmp_path)
    writer = io.StringIO()
    reader = io.StringIO('{"operation":"invoke","tool":"read_pages","arguments":{"value":NaN}}\n')
    serve_json_lines(
        workflow, reader, writer, destination=tmp_path / "receipt.json", participant="causal-json"
    )
    assert json.loads(writer.getvalue()) == {"status": "refused", "error_code": "bad_arguments"}
    assert not workflow._calls
