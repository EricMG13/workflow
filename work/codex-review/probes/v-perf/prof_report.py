import pstats, sys
p = pstats.Stats(sys.argv[1])
want = ["_stage_registers","_validate_stage","narrative_inputs","downstream_inputs","canonical_downstream_readiness","canonical_tables","canonical_narrative","model_report","_quality_stage","content_hash","model_validate_json","pack","_execution_state","_assert_current","read_inputs","submit_step","_verify_cp1_attempt","_verify_cp1_attempt_memoised","cp1_quality_inputs","validate_financial_context","reconcil"]
tot = max(v[3] for v in p.stats.values())
print("total cum max", round(tot,1))
rows=[]
for (f,l,n),(cc,nc,tt,ct,callers) in p.stats.items():
    if any(n==w or (w=="reconcil" and "reconcil" in n) for w in want):
        rows.append((ct,nc,n,f.split('/src/')[-1],l))
for r in sorted(rows,reverse=True)[:40]:
    print(f"{r[0]:8.2f}s ncalls={r[1]:6d} {r[2]} {r[3]}:{r[4]}")
