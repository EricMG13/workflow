"""Attempts 1 and 3 (adversary). Usage from W:
PYTHONPATH=src:tests <lane>/.venv/bin/python <probe-dir>/probe_a_parent_child.py

0. baseline: public synthetic case, no mutation (expect 0 BLOCK).
A. parent whose child disagrees: drop the working-capital leaf from the q2-2025 CFO identity, so
   the printed CFO (4.75) no longer equals NP 4 + D&A 1.25 = 5.25. The child source-statement
   identity and CFO_IDENTITY compute a 0.5 difference; the NCF_IDENTITY parent gets a blocker built
   from the child's explanation (difference None) and is downgraded. Exit 1 if no BLOCK remains.
B. under-declared disclosure: the same disagreement, plus the q2-2025 CFS disclosure declared
   'partial'. Expect: every check on the disagreement turns into a prefixed WARN (0 BLOCK) on public,
   and BLOCK on synthetic. Prints the disclosure WARN gap that is the ruled mitigation.
Exit code: 0 if A keeps >=1 reconciliation BLOCK (attack 1 fails) else 1.
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import PREFIX, build, hops, summary


def drop_wc(doc):
    book = doc["books"][0]
    ident = next(i for i in book["statement_identities"] if i["identity_id"] == "cfo-q2-2025")
    ident["components"] = [c for c in ident["components"]
                           if c["line_id"] != "cfs-working-capital-cash-movement"]


def drop_wc_partial(doc):
    drop_wc(doc)
    book = doc["books"][0]
    row = next(r for r in book["statement_disclosures"]
               if r["statement"] == "CFS" and r["period_id"] == "q2-2025")
    row["disclosure"]["status"] = "partial"
    row["disclosure"]["explanation"] = "Cash flow statement captured in part"


audit, period, gate, _ = hops(*build("public"))
summary("0 baseline public", audit, period, gate)

audit, period, gate, recon = hops(*build("public", drop_wc))
blocks_a, pre_a = summary("A public, CFO leaf dropped (child disagrees)", audit, period, gate)
for c in audit.reconciliation.checks:
    if c.period_id == "q2-2025" and c.status != "PASS":
        print("   check", c.check_type, c.metric_id, c.status, "diff", c.difference, "|", c.explanation[:120])
misleading = [g for g in pre_a if "Difference exceeds" in g.description]
print("  prefixed WARN that quote a computed difference:", len(misleading))
for g in misleading:
    print("    ", g.origin, "|", g.description[:220])

audit, period, gate, _ = hops(*build("public", drop_wc_partial))
blocks_b, pre_b = summary("B public, CFO leaf dropped + CFS q2 disclosure partial", audit, period, gate)
for g in pre_b:
    if "q2" in str(getattr(g, "period_ids", "")) or True:
        pass
disc = [g for g in audit.gaps if g.origin == "disclosure"]
print("  disclosure gaps:", [(g.severity, g.description) for g in disc])
audit, period, gate, _ = hops(*build("synthetic", drop_wc_partial))
blocks_bs, _ = summary("B synthetic, same input", audit, period, gate)

recon_blocks_a = [g for g in blocks_a if g.origin in {"reconciliation", "period_reconciliation"}]
print("RESULT A: reconciliation BLOCK kept =", len(recon_blocks_a))
print("RESULT B: public BLOCK =", len(blocks_b), " synthetic BLOCK =", len(blocks_bs))
sys.exit(0 if recon_blocks_a else 1)
