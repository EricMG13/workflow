"""Exact-Decimal receipts for derived facts in module_golden.json (stdlib only).

    python3 -I derive.py          verify every derivation and print the receipt (exit 1 on mismatch)
    python3 -I derive.py --write  compute the derived values and store them in module_golden.json
"""
import decimal
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
GOLDEN = HERE / "module_golden.json"
# (derived fact_id, op, operand fact_ids); order matters when a derived fact feeds another.
DERIVATIONS = [
    [
        "CP-2.debt_stack.term_loan_facilities_aggregate.principal_outstanding_from_table_lines.2025-09-30",
        "sum",
        [
            "CP-2.debt_stack.current_portion_of_senior_secured_credit_facility.principal_current_portion.2025-09-30",
            "CP-2.debt_stack.term_loan_facilities_aggregate.principal_long_term_portion.2025-09-30"
        ]
    ],
    [
        "CP-2.debt_stack.term_loan_facilities_sum_of_original_tranche_amounts.original_aggregate_principal",
        "sum",
        [
            "CP-2.debt_stack.term_a_1.original_aggregate_principal",
            "CP-2.debt_stack.term_a_2.original_aggregate_principal",
            "CP-2.debt_stack.term_b_before_2025_refinancing.original_aggregate_principal"
        ]
    ],
    [
        "CP-2.debt_stack.revolving_credit_facility.availability_commitment_less_drawn_less_letters_of_credit.2025-09-30",
        "difference",
        [
            "CP-2.debt_stack.revolving_credit_facility.commitment.2025-09-30",
            "CP-2.debt_stack.revolving_credit_facility.drawn_principal.2025-09-30",
            "CP-2.debt_stack.revolving_credit_facility.letters_of_credit_outstanding.2025-09-30"
        ]
    ],
    [
        "CP-2.debt_stack.revolving_credit_facility.drawn_share_of_commitment.2025-09-30",
        "ratio",
        [
            "CP-2.debt_stack.revolving_credit_facility.drawn_principal.2025-09-30",
            "CP-2.debt_stack.revolving_credit_facility.commitment.2025-09-30"
        ]
    ],
    [
        "CP-2.debt_stack.total_debt.principal_from_components.2025-09-30",
        "sum",
        [
            "CP-2.debt_stack.term_loan_facilities_aggregate.principal_outstanding.2025-09-30",
            "CP-2.debt_stack.revolving_credit_facility.drawn_principal.2025-09-30",
            "CP-2.debt_stack.9_500_senior_secured_notes_due_2029.principal_outstanding.2025-09-30",
            "CP-2.debt_stack.other_debt_atmaas_financing_program.principal_outstanding.2025-09-30"
        ]
    ],
    [
        "CP-2.debt_stack.total_debt.carrying_amount_from_balance_sheet_lines.2025-09-30",
        "sum",
        [
            "CP-2.debt_stack.total_short_term_borrowings.carrying_amount.2025-09-30",
            "CP-2.debt_stack.total_long_term_debt.carrying_amount.2025-09-30"
        ]
    ],
    [
        "CP-2.debt_stack.total_debt.principal_less_carrying.2025-09-30",
        "difference",
        [
            "CP-2.debt_stack.total_debt.principal_stated.2025-09-30",
            "CP-2.debt_stack.total_debt.carrying_amount_from_balance_sheet_lines.2025-09-30"
        ]
    ],
    [
        "CP-2.liquidity.total_debt_principal_less_cash_and_cash_equivalents.amount.2025-09-30",
        "difference",
        [
            "CP-2.debt_stack.total_debt.principal_stated.2025-09-30",
            "CP-2.liquidity.cash_and_cash_equivalents.balance.2025-09-30"
        ]
    ]
]


def compute(op, vals):
    ctx = decimal.Context(prec=60, traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Inexact])
    if op == "sum":
        total = vals[0]
        for v in vals[1:]:
            total = ctx.add(total, v)
        return total
    if op == "difference":
        total = vals[1]
        for v in vals[2:]:
            total = ctx.add(total, v)
        return ctx.subtract(vals[0], total)
    if op == "ratio":
        return ctx.divide(vals[0], vals[1])
    raise ValueError(f"unsupported op {op}")


def fmt(d):
    s = format(d.normalize(), "f")
    return s


def main(write):
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    facts = {f["fact_id"]: f for f in data["facts"]}
    bad = 0
    for fid, op, operands in DERIVATIONS:
        vals = [decimal.Decimal(facts[o]["value"]) for o in operands]
        result = compute(op, vals)
        shown = ", ".join(f"{o.rsplit('.', 2)[-2] if False else o}={facts[o]['value']}" for o in operands)
        print(f"{fid} = {op}({shown}) = {fmt(result)}")
        if write:
            facts[fid]["value"] = fmt(result)
        elif decimal.Decimal(facts[fid]["value"]) != result:
            print(f"  MISMATCH: stored {facts[fid]['value']}")
            bad += 1
    if write:
        GOLDEN.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv[1:]))
