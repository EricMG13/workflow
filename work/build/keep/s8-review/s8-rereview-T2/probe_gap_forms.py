# For every composed case, every bound ref, chip and figure form in gaps[0].gap:
# validate() == () must imply compute() succeeds. Also reports masking: an unsettled chip
# alongside another gap-field issue. Exit 1 on any accepted-but-uncomputable text.
import copy, sys
import test_method_cp2h as m
from deploy_workflow.owners import cp2h

bad, masked = [], []
for case in m.COMPOSED:
    inp = m.inputs(case)
    ratings = cp2h.ratings_source(inp.pack)
    source = cp2h.parse_ratings(cp2h.source_pages(ratings))
    book, _ = cp2h._compose(ratings, source, inp.upstream, None)
    bound = cp2h._bound(book, inp.upstream)
    n_unsettled = sum(f.status != "known" for f in bound.values())
    print(case, "bound:", len(bound), "unsettled:", n_unsettled)
    for ref, fact in sorted(bound.items()):
        for text in (f"Coverage of [{ref}] is noted.", f"Coverage of {{{ref}|x}} is noted.",
                     f"Coverage of {{{ref}}} is noted."):
            payload = copy.deepcopy(m.raw_payload(case))
            payload["gaps"][0]["gap"] = text
            inputs = m.inputs(case, payload)
            if cp2h.validate(inputs):
                continue
            try:
                cp2h.compute(inputs)
            except ValueError as e:
                bad.append((case, text, str(e)[:120]))
        if fact.status != "known":
            payload = copy.deepcopy(m.raw_payload(case))
            payload["gaps"][0]["gap"] = f"Coverage of [{ref}] is missing for 1234 days."
            issues = cp2h.validate(m.inputs(case, payload))
            if not any("not settled" in i for i in issues):
                masked.append((case, ref, issues))
print("accepted-but-uncomputable:", bad)
print("masked (unsettled chip hidden by another gap issue):", masked[:3], len(masked))
sys.exit(1 if bad else 0)
