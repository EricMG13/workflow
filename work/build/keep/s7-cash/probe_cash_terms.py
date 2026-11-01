"""Replay CZR partial submissions to the QA refusal; dump every NCF_CASH_MOVEMENT,
NCF_IDENTITY, CFO_IDENTITY check (all periods) with terms, plus the book's cash
accounts, periods, cash bridges, and CFS lines carrying cash items. Read-only.
Usage (repo root): PYTHONPATH=src:tests .venv/bin/python <this> <empty-dir> <out.json>"""
import sys, json
from pathlib import Path
import deploy_vii.canonical_audit as ca
from deploy_vii.statement_validation import effective_accounts
import czr_runs

cap = {}
_real = ca.reconcile_financials
def spy(pack, review, book_id):
    r = _real(pack, review, book_id)
    cap["report"], cap["review"], cap["book_id"] = r, review, book_id
    return r
ca.reconcile_financials = spy
try:
    czr_runs.czr_closed(Path(sys.argv[1]), Path("cases/czr-2026q2-earnings-update/submissions-partial.json"))
    print("CLOSED (unexpected)")
except BaseException as e:
    print("RAISED", type(e).__name__, str(e)[:300])
rep, review = cap["report"], cap["review"]
book = next(b for b in review.books if b.book_id == cap["book_id"])
out = {"checks": [], "periods": [], "accounts": [], "bridges": [], "cfs_lines": [], "bs_lines": []}
for k in rep.checks:
    if k.check_type in {"NCF_CASH_MOVEMENT", "NCF_IDENTITY", "CFO_IDENTITY"}:
        out["checks"].append(json.loads(k.model_dump_json()))
for p in book.periods:
    out["periods"].append(json.loads(p.model_dump_json()))
for a in effective_accounts(book):
    if any(s in a.metric_id for s in ("cash", "ncf", "cfo", "investing", "financing", "fx")):
        out["accounts"].append(json.loads(a.model_dump_json()))
for b in book.cash_movement_bridges:
    out["bridges"].append(json.loads(b.model_dump_json()))
for r in book.statement_lines:
    if r.statement == "CFS" or (r.statement == "BS" and "cash" in r.item_id):
        out["cfs_lines" if r.statement == "CFS" else "bs_lines"].append(json.loads(r.model_dump_json()))
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str))
print("wrote", sys.argv[2])
