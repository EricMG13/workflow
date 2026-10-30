from common import *
import os, json
D = os.path.join(os.path.dirname(__file__), "dumps")

BASIS_TEXT = {
    "citation": "Located source value or text cited to a filed page",
    "calculation": "Python calculation over located source values",
    "gap": "A recorded gap, not a located value",
    "missing": "No located value is available",
    "coverage": "A coverage record, not a located value",
    "estimate": "An estimate from located inputs",
}

def stage():
    inputs = json.load(open(os.path.join(D, "quality.txt")))
    ceilings = {c["evidence_id"]: c for c in inputs["ceilings"]}
    claims = []
    for claim in inputs["claims"]:
        evidence = []
        for eid in claim["evidence_ids"]:
            c = ceilings[eid]
            evidence.append({"evidence_id": eid, "lineage_class": c["ceiling"], "rationale": BASIS_TEXT[c["basis"]]})
        claims.append({"claim_id": claim["claim_id"], "material": True, "evidence": evidence,
                       "rationale": "Material credit consideration drawn from located filing text and statement rows"})
    sub = {"claims": claims, "findings": []}
    return {"step": "quality", "calls": [{"tool": "read_inputs"}], "submission": sub}
