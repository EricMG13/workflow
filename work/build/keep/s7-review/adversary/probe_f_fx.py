"""Attempt: an FX term ends up WARN. The term loan is made a EUR facility with no FX conversion
row, so every carrying-value normalisation has a null amount and a reason. The audit-hop debt
term carries `normalization` (helper keeps BLOCK); the period-hop debt term is a PeriodTerm that
carries no normalisation field, so the helper cannot see FX there.
Prints BLOCK gaps and the prefixed WARN gaps that name the facility. Exit 0 when a BLOCK gap
remains on the public case (attack fails for QA), else 1."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness import PREFIX, build, hops, summary


def mutate(doc):
    for f in doc["books"][0]["facilities"]:
        f["currency"] = "EUR"


audit, period, gate, _ = hops(*build("public", mutate))
blocks, pre = summary("public: EUR facility without a rate", audit, period, gate)
fx_warn = [g for g in pre if "term-loan" in g.description or "fac" in g.description.lower()]
print("  prefixed WARN gaps naming the FX facility:", len(fx_warn))
for g in fx_warn[:3]:
    print("   WARN", g.origin, "|", g.description[len(PREFIX):][:200])
sys.exit(0 if blocks else 1)
