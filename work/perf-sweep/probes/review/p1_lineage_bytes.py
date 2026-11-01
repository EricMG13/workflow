"""P1 probe: _operands output bytes are identical at b0ac40c and 17e07ba.

Usage: python p1_lineage_bytes.py <tree>  (tree made by p1_test_on_base.sh: <scratch>/base or /head)
Prints sha256 of the JSON of every OperandLineage plus the producer hash; compare the two runs.
"""
import hashlib
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii.contracts import Citation, Fact, Module  # noqa: E402
from deploy_workflow import earnings_workflow as core  # noqa: E402
from deploy_workflow.earnings import EarningsDeltaPoint, EarningsDeltaReport  # noqa: E402

assert core.__file__.startswith(sys.argv[1]), core.__file__


def fact(fid):
    return Fact(fact_id=fid, label=fid, text="x", period="FY2025", basis="IFRS")


producer = Module(run_id="run-1", issuer_id="issuer-1", as_of=date(2025, 12, 31), module_id="CP-1",
                  facts=tuple(fact(f) for f in ("prior.revenue", "current.revenue", "metric.revenue", "current.ebitda", "metric.ebitda")))
base = {"prior_value": Decimal("30.00"), "current_value": Decimal("30.0"), "prior_status": "known",
        "current_status": "known", "delta": Decimal("0.00"), "delta_status": "known", "delta_unit": "MILLIONS",
        "growth": Decimal("0.0"), "growth_status": "known", "reason": None, "unit": "MILLIONS",
        "currency": "USD", "scale": Decimal(1000000)}
report = EarningsDeltaReport(
    producer_sha256=producer.content_hash(), prior_period_id="FY2024", current_period_id="FY2025",
    prior_basis_id="IFRS", current_basis_id="IFRS",
    points=(EarningsDeltaPoint(measure_id="revenue", prior_fact_id="prior.revenue", current_fact_id="current.revenue",
                               companion_fact_ids=("metric.revenue", "metric.ebitda"), **base),
            EarningsDeltaPoint(measure_id="ebitda", prior_fact_id=None, current_fact_id="current.ebitda",
                               companion_fact_ids=("metric.ebitda",), **base)),
    limitations=())
out = core._operands(producer, report)
print("producer", producer.content_hash())
for lin in out:
    print(lin.measure_id, hashlib.sha256(lin.model_dump_json().encode()).hexdigest())
