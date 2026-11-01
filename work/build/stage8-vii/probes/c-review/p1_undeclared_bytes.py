"""Dump no-declaration outputs (bridge, _cash_movement, _period_cash, content hashes) for base-vs-fix diff."""
import sys, hashlib
sys.path.insert(0, sys.argv[2])  # tests dir
import test_cash_scope as t
from deploy_vii.financial_reconciliation import _cash_movement
out = []
for scopes in ({}, None):
    b = t.book(flows=tuple(t.FLOWS), scopes={pid: None for pid in t.FLOWS} if scopes is None else {})
    for br in b.cash_movement_bridges:
        out.append(br.model_dump_json()); out.append(br.content_hash())
    for pid in t.FLOWS:
        r = _cash_movement(b, t.flow(b, pid))
        out.append(r.model_dump_json()); out.append(r.content_hash())
    c = t.constructed(b)
    out.append(c.model_dump_json()); out.append(c.content_hash())
    out.append(b.model_dump_json()); out.append(b.content_hash())
open(sys.argv[1], "w").write("\n".join(out))
print(len(out), "lines")
