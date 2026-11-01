"""M1 re-review: try to get around shadowed_account_ids (read-only, hop level, public case).

Invariant checked on every variant that validates: no prefixed (downgraded) gap at either hop comes
from a check any of whose terms cites an explicit account with no amount whose (period, metric) has
a known printed linked line, and the public 'shadow' variant keeps >= as many BLOCK gaps as the
plain 'disagree' variant.
Variants:
  V1 wrong amount: explicit KNOWN revenue q2 = 31 (printed IS 30) + segment 31.
  V2 alias metrics: explicit missing accounts for ebitda / adjusted_ebitda /
     capex_and_intangible_investment (linked via ebitda_reported / ebitda_adjusted / capex_total).
  V2b statement item id as metric: explicit missing account metric_id 'ebitda_reported'.
  V3 period: shadow on fy-2025 revenue (FY reported) + fy segment 121.
  V4 period hop: Q4 rows dropped (Q4 constructed from FY - Q1..Q3) + q2 shadow + q2 segment 31.
  V5 not_applicable status shadow (q2 revenue not_applicable) + segment 31.
Exit 1 if any invariant breaks (a bypass), else 0."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import PREFIX, build, hops, summary
from deploy_vii.canonical_audit import shadowed_account_ids
from deploy_vii.statement_validation import statement_accounts

FAIL = []


def line(book, period, item, statement="IS"):
    return next(l for l in book["statement_lines"]
                if l["period_id"] == period and l["item_id"] == item and l["statement"] == statement)


def seg(doc, period, amount):
    s = next(s for s in doc["books"][0]["segments"] if s["period_id"] == period)
    s["revenue"]["amount"] = amount


def add_account(doc, period, metric, status="missing", amount=None, item=None, oid=None):
    book = doc["books"][0]
    cites = line(book, period, item or metric)["value"]["citations"]
    v = {"observation_id": oid or f"shadow-{metric}-{period}", "status": status, "amount": amount,
         "citations": cites}
    if status != "known":
        v["reason"] = "Not printed in the filing"
    book["accounts"].append({"metric_id": metric, "period_id": period, "value": v})


def drop_q4(doc):
    book = doc["books"][0]
    for key, rows in list(book.items()):
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "period_id" in rows[0]:
            book[key] = [r for r in rows if r.get("period_id") != "q4-2025"]


def guard_ids(book):
    printed = {(r.period_id, r.metric_id) for r in statement_accounts(book) if r.value.amount is not None}
    return {a.value.observation_id for a in book.accounts
            if a.value.amount is None and (a.period_id, a.metric_id) in printed}


def run(label, mutate):
    try:
        pack, review, definition = build("public", mutate)
        audit, period, gate, recon = hops(pack, review, definition)
    except Exception as error:  # a refusal is the fail-closed outcome; report it, do not hide it
        print(f"== {label}: REFUSED {type(error).__name__}: {str(error)[:180]}")
        return None
    blocks, pre = summary(label, audit, period, gate)
    book = review.books[0]
    guard = guard_ids(book)
    helper = shadowed_account_ids(book)
    print("   independent guard:", sorted(guard), "helper:", sorted(helper))
    if guard - helper:
        FAIL.append((label, "helper misses", guard - helper))
    checks = {c.check_id: c for c in audit.reconciliation.checks}
    if recon is not None:
        checks.update({c.check_id: c for c in recon.checks})
    for g in [*audit.gaps, *period]:
        if not g.description.startswith(PREFIX):
            continue
        ref = g.reference if g.origin == "reconciliation" else g.metric
        c = checks.get(ref) or next((c for c in checks.values() if c.check_id in str(g.model_dump())), None)
        if c is None:
            FAIL.append((label, "prefixed gap without a source check", g.gap_id))
            continue
        ids = set()
        for t in (c.reported, *c.components):
            ids |= set(getattr(t, "observation_ids", ()) or ((t.observation_id,) if getattr(t, "observation_id", None) else ()))
        if ids & guard:
            FAIL.append((label, "downgraded check cites a shadow", c.check_type, sorted(ids & guard)))
    return len(blocks)


def v_disagree(doc):
    seg(doc, "q2-2025", "31")


def v1(doc):
    v_disagree(doc)
    add_account(doc, "q2-2025", "revenue", status="known", amount="31")


def v2(doc):
    add_account(doc, "q2-2025", "ebitda", item="ebitda_reported")
    add_account(doc, "q2-2025", "adjusted_ebitda", item="ebitda_adjusted")


def v2_capex(doc):
    book = doc["books"][0]
    cites = line(book, "q2-2025", "capex_total", "CFS")["value"]["citations"]
    book["accounts"].append({"metric_id": "capex_and_intangible_investment", "period_id": "q2-2025",
        "value": {"observation_id": "shadow-capex-q2", "status": "missing", "amount": None,
                  "citations": cites, "reason": "Not printed"}})


def v2b(doc):
    v_disagree(doc)
    add_account(doc, "q2-2025", "ebitda_reported")


def v3_base(doc):
    seg(doc, "fy-2025", "121")


def v3(doc):
    v3_base(doc)
    add_account(doc, "fy-2025", "revenue")


def v4_base(doc):
    drop_q4(doc)
    v_disagree(doc)


def v4(doc):
    v4_base(doc)
    add_account(doc, "q2-2025", "revenue")


def v5(doc):
    v_disagree(doc)
    add_account(doc, "q2-2025", "revenue", status="not_applicable")


base = run("disagree (baseline)", v_disagree)
run("V1 explicit known wrong amount", v1)
run("V2 alias ebitda/adjusted_ebitda shadow", v2)
run("V2 alias capex shadow", v2_capex)
run("V2b statement item id as metric", v2b)
b3 = run("V3 baseline fy segment 121", v3_base)
s3 = run("V3 fy revenue shadow + fy segment 121", v3)
b4 = run("V4 baseline Q4 constructed + q2 segment 31", v4_base)
s4 = run("V4 Q4 constructed + q2 shadow + q2 segment 31", v4)
s5 = run("V5 not_applicable shadow + segment 31", v5)
for label, b, s in (("V3", b3, s3), ("V4", b4, s4), ("V5", base, s5)):
    if b and s is not None and s < 1:
        FAIL.append((label, "shadow removed every BLOCK", b, s))
print("FAIL" if FAIL else "OK", FAIL)
sys.exit(1 if FAIL else 0)
