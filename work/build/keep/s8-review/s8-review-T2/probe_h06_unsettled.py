# A gap text that references an unsettled bound fact: validate accepts it, compute raises?
# Exit 1 when validate passes and compute raises (accepted-but-uncomputable).
import copy, sys
import test_method_cp2h as m
from deploy_workflow.owners import cp2h

bad = []
for case in m.COMPOSED:
    inp = m.inputs(case)
    up = inp.upstream
    ratings = cp2h.ratings_source(inp.pack)
    source = cp2h.parse_ratings(cp2h.source_pages(ratings))
    book, _ = cp2h._compose(ratings, source, up, None)
    bound = cp2h._bound(book, up)
    unsettled = [k for k, f in bound.items() if f.status != "known"]
    print(case, "unsettled bound:", unsettled[:5])
    if not unsettled:
        continue
    ref = unsettled[0]
    payload = copy.deepcopy(m.raw_payload(case))
    payload["gaps"][0]["gap"] = "Coverage is missing for [%s]." % ref
    inputs = m.inputs(case, payload)
    issues = cp2h.validate(inputs)
    print("  validate:", issues)
    if issues:
        continue
    try:
        cp2h.compute(inputs)
        print("  compute OK")
    except ValueError as e:
        print("  COMPUTE RAISED:", e)
        bad.append(case)
print("accepted-but-uncomputable:", bad)
sys.exit(1 if bad else 0)
