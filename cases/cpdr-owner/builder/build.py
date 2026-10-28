"""Writes cases/cpdr-owner/{manifest,submissions,expected}.json (stdlib only, imports nothing from src/).

Independent oracle for the CP-DR (Deep research, LOCAL) owner. Every count, share and status is
derived here, with Decimal, from literal submissions and the FROZEN source bytes
(cases/financial/manifest.json identity and financial pages, cases/snapshot/manifest.json
business_source.gap pages). Method rules are written in
work/lead/cpdr-owner-preparation/lease-draft.md section "Method". No product module is imported
or executed. Search hit counts follow the documented search_pack rule (a span matches when it
contains any whitespace-separated query term, case-insensitive substring); they are expectations
for the tool-use check, not outputs of code under test.

Run: python3 -I cases/cpdr-owner/builder/build.py   (from the repository root)
"""

import copy
import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cpdr-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
}
for rel, want in PINS.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert got == want, (rel, got)

FIN = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAP = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
SNAPSUB = json.loads((ROOT / "cases/snapshot/submissions.json").read_text())
METH = json.loads((ROOT / "src/deploy_vii/methodology.json").read_text())


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s["pages"] for s in FIN["sources"]}
SHA = {s["source_id"]: s["sha256"] for s in FIN["sources"]}
SRC["business"] = SNAP["business_source"]["gap"]["pages"]
SHA["business"] = SNAP["business_source"]["gap"]["sha256"]
for sid, pages in SRC.items():
    assert page_sha([p["text"] for p in pages]) == SHA[sid], sid
TEXT = {(sid, p["locator"]): p["text"] for sid, pages in SRC.items() for p in pages}
ORDER = ("identity", "financial", "business")
LIMIT_FIN = SNAP["financial_pack_limitation"]["text"]
BUS_LIMIT = SNAP["business_source"]["gap"]["pack_limitation"]
SYNTH = "Synthetic case; not real issuer qualification"
RUN_ID = "slice-cpdr-gap"
AS_OF = "2026-01-10"
ISSUER = FIN["run"]["issuer_name"]

# --- D8: table ids ------------------------------------------------------------------------------
ENTRY = next(m for m in METH if m["module_id"] == "CP-DR")
assert ENTRY["required"] == ["CP-0"] and ENTRY["optional"] == []
assert ENTRY["table_ids"] == ["TDR.1", "TDR.2", "TDR.3"]
for m in METH:
    if m["module_id"] != "CP-DR":
        assert not set(m["table_ids"]) & set(ENTRY["table_ids"]), m["module_id"]
assert not [m for m in METH if "CP-DR" in m["required"] + m["optional"]], "a consumer edge exists"

# the not_found claims below rest on these absences in every prepared page
for key, text in TEXT.items():
    for needle in ("owned by", "Holdings", "Harbour", "shareholder loan", "distribution policy"):
        assert needle not in text, (key, needle)


def find_quote(source, locator, quote):
    assert quote in TEXT[(source, locator)], (source, locator, quote)
    return {
        "source_id": source,
        "source_sha256": SHA[source],
        "locator": locator,
        "quote": quote,
    }


# --- CP-0 literal (delta of cases/snapshot/submissions.json#gap.readiness_review) ---------------
base = SNAPSUB["gap"]["readiness_review"]
cp1a = next(c for c in base["consumers"] if c["module_id"] == "CP-1A")
review = copy.deepcopy(base)
consumer = copy.deepcopy(cp1a)
consumer["module_id"] = "CP-DR"
consumer["evidence_demand"] = "Located spans in the prepared sources that answer the open readiness gaps"
consumer["rationale"] = (
    "Research can run on the located sources; questions the sources cannot answer stay unresolved."
)
review["consumers"] = [consumer]
GAP_ID = "missing-ownership-transaction"
GAP_DESC = "Ownership and transaction content is absent from the business note"
review["gaps"] = [
    {
        "gap_id": GAP_ID,
        "kind": "scope",
        "severity": "material",
        "description": GAP_DESC,
        "affected_modules": ["CP-DR"],
        "remediation": "Supply the ownership and transaction documents",
        "citations": [],
    }
]
review["analysis"] = copy.deepcopy(base["analysis"])
CP0_DELTA = [
    "consumers: the single CP-1A..CP-2 entries are replaced by one CP-DR entry copied from the CP-1A entry "
    "(sources, citations, limitations unchanged; demand and rationale reworded)",
    "gaps: gap_id, kind, severity and remediation unchanged; description drops the clause naming CP-1A rows; "
    "affected_modules = [CP-DR] (a gap may only name selected modules, readiness.py validate_review)",
    "sources, objective, reporting_period, analysis: unchanged from the snapshot gap literal",
]

# upstream facts the CP-DR reader parses (readiness.py build_readiness field() rules)
G = review["gaps"][0]
T5_TEXT = (
    f"{G['kind']}/{G['severity']}: {G['description']}; affects {', '.join(G['affected_modules'])}; "
    f"{G['remediation']}"
)
T5_FACT_ID = f"T5.{GAP_ID}.gap"
EMPTY_REVIEW = copy.deepcopy(review)
EMPTY_REVIEW["gaps"] = []
EMPTY_FACT_ID = "T5.review.gaps"
EMPTY_FACT_TEXT = "No gaps identified by this supplied review"


def cp0_limitations(rv):
    """CP-0 module limitations in order, de-duplicated (readiness.build_readiness rule, re-derived here)."""
    return list(
        dict.fromkeys(
            [LIMIT_FIN, BUS_LIMIT]
            + [t for s in rv["sources"] for t in s["limitations"]]
            + [t for c in rv["consumers"] for t in c["limitations"]]
            + [g["description"] for g in rv["gaps"]]
            + [SYNTH]
        )
    )


def t8_limits(rv):
    """T8.CP-DR.limits text: the consumer's, its sources' and the affected gaps' limitations."""
    cons = rv["consumers"][0]
    out = list(cons["limitations"])
    for sid in cons["source_ids"]:
        src_limit = {"financial": LIMIT_FIN, "business": BUS_LIMIT}.get(sid)
        if src_limit:
            out.append(src_limit)
        out += next(s for s in rv["sources"] if s["source_id"] == sid)["limitations"]
    out += [g["description"] for g in rv["gaps"] if "CP-DR" in g["affected_modules"]]
    return "; ".join(dict.fromkeys(out))


CP0_LIMITATIONS = cp0_limitations(review)
CP0_LIMITATIONS_EMPTY = cp0_limitations(EMPTY_REVIEW)
T8_LIMITS = t8_limits(review)
T8_LIMITS_EMPTY = t8_limits(EMPTY_REVIEW)

# --- the three research submissions -------------------------------------------------------------
Q_TRANS = "Did the group complete an acquisition, a disposal or any other transaction in the reporting period or after its end?"
A_TRANS = (
    "The financial statements report no acquisitions or disposals in any quarter or the full year "
    "and no subsequent events up to the publication date."
)
Q_DIST = "Were distributions paid to the shareholder during the reporting period?"
A_DIST = (
    "The statements show dividends paid in every quarter and for the full year, and the equity "
    "roll-forward consists only of net profit and those dividends."
)
Q_OWN = "Who owns the issuer and in what proportions?"
L_OWN = "No prepared source names the owners of the issuer or their holdings."
Q_POL = "Which policy governs distributions to the owners of the issuer?"
L_POL = "No prepared source describes a distribution policy; the statements show only the amounts paid."

CIT_TRANS = [
    find_quote(
        "financial",
        "page:1",
        "No acquisitions, disposals, net equity movements, equity issuance, equity repurchases, "
        "leases, operating lease costs, lease cash payments, lease payments in financing, interest "
        "paid in financing, or other investing/financing cash flows occurred in any quarter or FY2025.",
    ),
    find_quote(
        "financial",
        "page:1",
        "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt "
        "changes through January 10, 2026.",
    ),
]
CIT_DIST = [
    find_quote(
        "financial",
        "page:1",
        "The complete equity roll-forward in each quarter consists only of net profit 4 and "
        "dividends paid (2.25); FY2025 consists only of net profit 16 and dividends paid (9).",
    ),
    find_quote("financial", "page:3", "Dividends paid  (2.25)  (2.25)  (2.25)  (2.25)  (9.00)"),
]


def question(qid, text, outcome, *, answer=None, category=None, citations=(), searched, limitation=None):
    return {
        "question_id": qid,
        "text": text,
        "outcome": outcome,
        "answer": answer,
        "category": category,
        "citations": list(citations),
        "searched_sources": list(searched),
        "limitation": limitation,
    }


def research(*qs):
    return {"gaps": [{"gap_id": GAP_ID, "questions": list(qs)}]}


Q1 = question("transactions", Q_TRANS, "answered", answer=A_TRANS, category="Documentary Fact",
              citations=CIT_TRANS, searched=["financial"])
Q2 = question("distributions", Q_DIST, "answered", answer=A_DIST, category="Documentary Fact",
              citations=CIT_DIST, searched=["financial"])
Q3 = question("owner-identity", Q_OWN, "not_found", searched=list(ORDER), limitation=L_OWN)
Q4 = question("distribution-policy", Q_POL, "not_found", searched=list(ORDER), limitation=L_POL)

SUB = {
    "partial": research(Q1, Q2, Q3),
    "unresolved": research(Q3, Q4),
    "empty_agenda": {"gaps": []},
}
# the answers, questions and limitations are digit-free and carry no prohibited conclusion
PROHIBITED = ("recommend", "refinanc", "covenant", "recovery")
for _sub in SUB.values():
    for _g in _sub["gaps"]:
        for _x in _g["questions"]:
            for _t in (_x["text"], _x["answer"], _x["limitation"]):
                if _t:
                    assert not any(ch.isdigit() for ch in _t), _t
                    assert not any(w in _t.lower() for w in PROHIBITED), _t

# tool calls (arguments literal); expected search header counts follow the documented rule
QUERY_OWN = "owner shareholder investor holding"
QUERY_POL = "distribution policy"
QUERY_TRANS = "acquisition disposal subsequent events"
QUERY_DIV = "dividends paid"


def spans_matching(query, scope):
    terms = [t.lower() for t in dict.fromkeys(query.split())]
    sources = ORDER if scope is None else (scope,)
    return [
        {"source_id": s, "locator": loc}
        for s in sources
        for (sid, loc), text in TEXT.items()
        if sid == s and any(t in text.lower() for t in terms)
    ]


def search(query, scope):
    hits = spans_matching(query, scope)
    args = {"query": query, "source_id": scope}
    return {
        "tool": "search_pack",
        "arguments": args,
        "expect_header": f"{len(hits)} spans match {query!r}; showing {min(10, len(hits))}.",
        "expect_matching_spans": hits,
    }


def read(source, first, last=None):
    last = first if last is None else last
    return {
        "tool": "read_pages",
        "arguments": {"source_id": source, "first_page": first, "last_page": last},
        "expect_spans": [{"source_id": source, "locator": f"page:{n}"} for n in range(first, last + 1)],
    }


CALLS = {
    "partial": [
        {"tool": "read_inputs", "arguments": None},
        search(QUERY_TRANS, "financial"),
        read("financial", 1),
        search(QUERY_DIV, "financial"),
        read("financial", 3),
        *[search(QUERY_OWN, s) for s in ORDER],
    ],
    "unresolved": [
        {"tool": "read_inputs", "arguments": None},
        *[search(QUERY_OWN, s) for s in ORDER],
        *[search(QUERY_POL, s) for s in ORDER],
    ],
    "empty_agenda": [{"tool": "read_inputs", "arguments": None}],
}
CALLS["blocked"] = CALLS["partial"]
# search hit sanity: the unresolved answers rest on searches that surface no answering span
for s in ORDER:
    for hit in spans_matching(QUERY_OWN, s) + spans_matching(QUERY_POL, s):
        assert hit["source_id"] == s

# --- the oracle's own reference validator (stdlib; derives every journaled issue tuple) ------------
# Rules, in order (lease "Validator rules"): the validator's content rules, then the core's RULES(text, seen)
# tool-use evidence rules (G1-X protocol section 2) in the product's order: absence issues, then unread-page issues,
# each sorted (live/tools.py ToolRules.issues). RULES is pure over the payload
# text and the session's Seen, so it does not know pack membership: an out-of-pack source adds its RULES issue
# to the membership issue (two issues for one defect, listed in full).
UNREAD_PAGE = "Cited page not read through read_pages"  # live/tools.py UNREAD_PAGE
UNBACKED_ABSENCE = "Absence claim without a recorded search"  # live/tools.py UNBACKED_ABSENCE
# Oracle simplifications of this reference validator (the product functions are the rule; rev 4, review L-2):
# - citation_issue checks pack membership and a raw substring match only; readiness.citation_issues also refuses a
#   changed source_sha256 and normalises whitespace, quote marks and dashes before matching.
# - the unread-page rule considers page:N locators only (tools.py _PAGE, fullmatch), as unread_citation_issues does;
#   any other locator is left to the quote/locator check.
# - Seen is rebuilt from the literal call list: a scoped search_pack covers its source, an unscoped one every source.
# - the absence line's remainder after UNBACKED_ABSENCE is the core's wording (the product has no CP-DR line).


def calls_seen(calls):
    searched, pages = set(), set()
    for c in calls:
        if c["tool"] == "search_pack":
            scope = c["arguments"]["source_id"]
            searched |= set(ORDER) if scope is None else {scope}
        elif c["tool"] == "read_pages":
            a = c["arguments"]
            pages |= {(a["source_id"], f"page:{n}") for n in range(a["first_page"], a["last_page"] + 1)}
    return searched, pages


def citation_issue(c):
    if c["source_id"] not in SRC:
        return f"Unavailable or changed source: {c['source_id']}"
    if c["quote"] not in TEXT.get((c["source_id"], c["locator"]), ""):
        assert len(c["quote"]) <= 200  # readiness.citation_issues shows a quote whole up to 200 characters
        return (
            f"Quote/locator mismatch: quote not found under {c['source_id']} {c['locator']} "
            f'(normalised whitespace, quote marks and dashes): "{c["quote"]}"'
        )
    return None


def oracle_issues(payload, calls, agenda):
    searched, pages = calls_seen(calls)
    issues, seen_gaps, seen_q, counted = [], set(), set(), {}
    unread, unbacked = set(), []
    for g in payload["gaps"]:
        gid = g["gap_id"]
        if gid not in agenda:
            issues.append(f"gap_id is not in the CP-0 agenda: {gid}")
        elif gid in seen_gaps:
            issues.append(f"gap_id appears twice: {gid}")
        else:
            counted[gid] = len(g["questions"])
        seen_gaps.add(gid)
    for gid in agenda:
        if not 1 <= counted.get(gid, 0) <= 4:
            issues.append(f"a gap takes 1 to 4 research questions: {gid}")
    for g in payload["gaps"]:
        for x in g["questions"]:
            qid = x["question_id"]
            if qid in seen_q:
                issues.append(f"question_id appears twice: {qid}")
            seen_q.add(qid)
            if x["outcome"] == "answered":
                if not (x["answer"] and x["category"] and x["citations"]):
                    issues.append(f"an answered question needs an answer, a category and at least one citation: {qid}")
                if x["limitation"]:
                    issues.append(f"an answered question carries no limitation: {qid}")
            else:
                if x["answer"] or x["category"] or x["citations"]:
                    issues.append(f"a not_found question carries no answer, category or citation: {qid}")
                if not x["limitation"]:
                    issues.append(f"a not_found question states its limitation: {qid}")
            if not x["searched_sources"]:
                issues.append(f"searched_sources must name at least one prepared source: {qid}")
            for sid in x["searched_sources"]:
                if sid not in SRC:
                    issues.append(f"searched source is not a ready prepared source: {qid} {sid}")
                if x["outcome"] == "not_found" and sid not in searched:  # RULES: absence backed by a search
                    unbacked.append(
                        f"{UNBACKED_ABSENCE}: {qid} not_found for {sid}; search_pack that source before claiming it is not found"
                    )
            for c in x["citations"]:
                found = citation_issue(c)
                if found:
                    issues.append(found)
                if re.fullmatch(r"page:[0-9]+", c["locator"]) and (c["source_id"], c["locator"]) not in pages:
                    unread.add((c["source_id"], c["locator"]))  # RULES: cited page:N read (tools.py _PAGE)
            texts = [t for t in (x["text"], x["answer"], x["limitation"]) if t]
            if any(ch.isdigit() for t in texts for ch in t):  # str.isdigit(), any character
                issues.append(f"text must not contain a figure: {qid}")
            if any(w in t.lower() for t in texts for w in PROHIBITED):
                issues.append(f"text carries a prohibited conclusion: {qid}")
    # product order (live/tools.py ToolRules.issues): absence issues, then unread-page issues, each sorted
    issues += sorted(unbacked) + [f"{UNREAD_PAGE}: {sid} {loc}" for sid, loc in sorted(unread)]
    return tuple(dict.fromkeys(issues))


AGENDA = {"partial": [GAP_ID], "unresolved": [GAP_ID], "empty_agenda": []}
for _name, _sub in SUB.items():
    assert oracle_issues(_sub, CALLS[_name], AGENDA[_name]) == (), _name

# --- refusal inputs: one literal payload per class ----------------------------------------------
PARTIAL = SUB["partial"]


def variant(mutator, *, calls=None, agenda="partial"):
    payload = copy.deepcopy(PARTIAL)
    mutator(payload)
    return {"payload": payload, "calls": calls if calls is not None else "partial", "cp0": agenda}


def q(payload, index):
    return payload["gaps"][0]["questions"][index]


def drop_search(source):
    return [
        c
        for c in CALLS["partial"]
        if not (c["tool"] == "search_pack" and c["arguments"]["source_id"] == source and c["arguments"]["query"] == QUERY_OWN)
    ]


FORGED_QUOTE = "The group completed an acquisition in the third quarter."


def forged(p):
    q(p, 0)["citations"][0]["quote"] = FORGED_QUOTE


def bad_source(p):
    q(p, 0)["citations"][0] = {
        "source_id": "web",
        "source_sha256": "0" * 64,
        "locator": "page:1",
        "quote": "Northbridge Synthetic Group announced a new owner.",
    }


def five(p):
    p["gaps"][0]["questions"] = [
        dict(copy.deepcopy(q(p, 2)), question_id=f"extra-{i}") for i in range(5)
    ]


def second_gap(p):
    p["gaps"].append({"gap_id": "invented-gap", "questions": [copy.deepcopy(q(p, 2))]})
    p["gaps"][1]["questions"][0]["question_id"] = "invented-owner"


def repeated_gap(p):
    # the copy renames every question id so the only defect is the repeated gap_id (review M1)
    p["gaps"].append(copy.deepcopy(p["gaps"][0]))
    for x in p["gaps"][1]["questions"]:
        x["question_id"] = f"{x['question_id']}-repeat"


def repeated_qid(p):
    q(p, 1)["question_id"] = "transactions"


NO_READ_P3 = [c for c in CALLS["partial"] if not (c["tool"] == "read_pages" and c["arguments"]["first_page"] == 3)]
REFUSAL_SPECS = {
    "gap_unaddressed": variant(lambda p: p.update(gaps=[])),
    "gap_with_five_questions": variant(five),
    "unknown_gap": variant(second_gap),
    "gap_repeated": variant(repeated_gap),
    "question_id_repeated": variant(repeated_qid),
    "answered_without_citation": variant(lambda p: q(p, 0).update(citations=[])),
    "not_found_with_answer": variant(lambda p: q(p, 2).update(answer="Held by investors.", category="Analyst Interpretation")),
    "not_found_without_limitation": variant(lambda p: q(p, 2).update(limitation=None)),
    "answered_with_limitation": variant(lambda p: q(p, 0).update(limitation="Partly covered.")),
    "no_searched_source": variant(lambda p: q(p, 2).update(searched_sources=[])),
    "searched_source_not_in_pack": variant(lambda p: q(p, 2).update(searched_sources=["web"])),
    "searched_source_not_searched": variant(lambda p: None, calls=drop_search("business")),
    "cited_page_not_read": variant(lambda p: None, calls=NO_READ_P3),
    "quote_not_verbatim": variant(forged),
    "citation_outside_pack": variant(bad_source),
    "digit_in_text": variant(lambda p: q(p, 0).update(answer="Nothing happened in 2025.")),
    "prohibited_conclusion": variant(lambda p: q(p, 2).update(limitation="We recommend asking the sponsor.")),
    "submission_against_empty_agenda": variant(lambda p: None, agenda="empty_agenda"),
}
QUOTE_ISSUE = (
    "Quote/locator mismatch: quote not found under financial page:1 "
    f'(normalised whitespace, quote marks and dashes): "{FORGED_QUOTE}"'
)
# the complete step.issues tuple of each refusal, pinned by hand and asserted against the reference validator.
# The two out-of-pack classes pin both issues (one defect, both consequences) in product sorted order: RULES is pure over text and Seen.
PINNED = {
    "gap_unaddressed": [f"a gap takes 1 to 4 research questions: {GAP_ID}"],
    "gap_with_five_questions": [f"a gap takes 1 to 4 research questions: {GAP_ID}"],
    "unknown_gap": ["gap_id is not in the CP-0 agenda: invented-gap"],
    "gap_repeated": [f"gap_id appears twice: {GAP_ID}"],
    "question_id_repeated": ["question_id appears twice: transactions"],
    "answered_without_citation": ["an answered question needs an answer, a category and at least one citation: transactions"],
    "not_found_with_answer": ["a not_found question carries no answer, category or citation: owner-identity"],
    "not_found_without_limitation": ["a not_found question states its limitation: owner-identity"],
    "answered_with_limitation": ["an answered question carries no limitation: transactions"],
    "no_searched_source": ["searched_sources must name at least one prepared source: owner-identity"],
    "searched_source_not_in_pack": [
        "searched source is not a ready prepared source: owner-identity web",
        f"{UNBACKED_ABSENCE}: owner-identity not_found for web; search_pack that source before claiming it is not found",
    ],
    "searched_source_not_searched": [
        f"{UNBACKED_ABSENCE}: owner-identity not_found for business; search_pack that source before claiming it is not found"
    ],
    "cited_page_not_read": [f"{UNREAD_PAGE}: financial page:3"],
    "quote_not_verbatim": [QUOTE_ISSUE],
    "citation_outside_pack": ["Unavailable or changed source: web", f"{UNREAD_PAGE}: web page:1"],
    "digit_in_text": ["text must not contain a figure: transactions"],
    "prohibited_conclusion": ["text carries a prohibited conclusion: owner-identity"],
    "submission_against_empty_agenda": [f"gap_id is not in the CP-0 agenda: {GAP_ID}"],
}
assert set(PINNED) == set(REFUSAL_SPECS)
refusal_inputs, refusal_expected = {}, {}
for name, spec in REFUSAL_SPECS.items():
    call_list = CALLS["partial"] if spec["calls"] == "partial" else spec["calls"]
    agenda = AGENDA[spec["cp0"]]
    derived = oracle_issues(spec["payload"], call_list, agenda)
    assert list(derived) == PINNED[name], (name, derived)
    refusal_inputs[name] = {
        "payload": spec["payload"],
        "calls": spec["calls"],
        "cp0": "cp0_readiness_review" if spec["cp0"] == "partial" else "cp0_readiness_review_empty_agenda",
    }
    refusal_expected[name] = {
        "disposition": "invalid",
        "attempt": 0,
        "step_issues": PINNED[name],
        "result_status": "rejected",
        "limitations": PINNED[name],
    }

# blocked: attempt 0 and attempt 1 both invalid (a forged quote, then a figure in text)
BLOCKED = {"attempt_0": variant(forged)["payload"], "attempt_1": variant(lambda p: q(p, 0).update(answer="Nothing happened in 2025."))["payload"]}
assert oracle_issues(BLOCKED["attempt_0"], CALLS["blocked"], [GAP_ID]) == (QUOTE_ISSUE,)
assert oracle_issues(BLOCKED["attempt_1"], CALLS["blocked"], [GAP_ID]) == ("text must not contain a figure: transactions",)

# --- Python bookkeeping (the oracle's own composer) ---------------------------------------------
D = Decimal


def share(num, den):
    return (D(num) / D(den)).quantize(D("0.0001"), rounding=ROUND_HALF_UP)


def shown_pct(amount):
    return str((amount * 100).quantize(D("0.1"), rounding=ROUND_HALF_UP)) + "%"


def gap_status(answered, total):
    if answered == total:
        return "Resolved"
    return "Unresolved" if answered == 0 else "Partially resolved"


def bookkeeping(payload):
    gaps, total_q, total_a = [], 0, 0
    for g in payload["gaps"]:
        n = len(g["questions"])
        a = sum(1 for x in g["questions"] if x["outcome"] == "answered")
        gaps.append(
            {"gap_id": g["gap_id"], "questions": n, "answered": a, "unresolved": n - a,
             "answered_share": share(a, n), "status": gap_status(a, n)}
        )
        total_q, total_a = total_q + n, total_a + a
    statuses = [x["status"] for x in gaps]
    return {
        "gaps": gaps,
        "gaps_total": len(gaps),
        "gaps_resolved": statuses.count("Resolved"),
        "gaps_partial": statuses.count("Partially resolved"),
        "gaps_unresolved": statuses.count("Unresolved"),
        "questions_total": total_q,
        "answered_total": total_a,
        "unresolved_total": total_q - total_a,
        # no question, no denominator: the share is not applicable, never 0 (empty agenda, lease M5)
        "answered_share": share(total_a, total_q) if total_q else None,
    }


GAP_NOTE = "G# is the report-wide gap number, bound at run time (A7 exception)"
FORMULA_COUNT = "counts of the submitted questions by outcome; share = answered / total, 4 dp half-up"
FORMULA_STATUS = "Resolved if every question is answered, Unresolved if none is, else Partially resolved"
FORMULA_OUTCOME = "the submitted outcome of the question, accepted only when Python's checks pass (answered needs a cited answer)"
NA_LIMITATION = "No research question was submitted, so an answered share has no denominator."
EMPTY_LIMITATION = "No gaps identified by this supplied review; no research question was submitted."
BASE_LIMITATION = "Research used the prepared local sources only; nothing outside the pack was searched."


def evidence_text(cites):
    return "; ".join(dict.fromkeys(f"{c['source_id']} {c['locator']}" for c in cites))


def build_case(case_id, payload):
    bk = bookkeeping(payload)
    empty = not payload["gaps"]
    cp0_limits = CP0_LIMITATIONS_EMPTY if empty else CP0_LIMITATIONS
    tables, facts = {}, []

    def add(table, row, field, label, **kw):
        fid = f"{table}.{row}.{field}"
        facts.append({"fact_id": fid, "table_id": table, "row_id": row, "field": field, "label": label, **kw})
        return fid

    def text_cell(table, row, field, text, klass=None, calc=None, formula=None, citations=()):
        kw = {"text": text, "status": "known"}
        if klass:
            kw["value_class"] = klass
        if calc:
            kw.update(calculation_id=calc, formula=formula)
        if citations:
            kw["citations"] = list(citations)
        fid = add(table, row, field, field.replace("_", " "), **kw)
        return {"fact": fid, "shown": text, "state": "known", "text": text, "unit": None, "value_class": klass}

    def num_cell(table, row, field, amount, unit, shown):
        fid = add(table, row, field, field.replace("_", " "), amount=str(amount), unit=unit, period=AS_OF,
                  value_class="calculated", status="known", calculation_id=f"cpdr-{row}-{field}"
                  if table == "TDR.1" else f"cpdr-total-{field}", formula=FORMULA_COUNT)
        return {"fact": fid, "shown": shown, "state": "known", "amount": str(amount), "unit": unit, "value_class": "calculated"}

    def missing_cell(table, row, field, limitation):
        fid = add(table, row, field, field.replace("_", " "), status="missing", limitation=limitation,
                  value_class="analyst_judgment")
        return {"fact": fid, "shown": "∅ G#", "state": "gap", "note": GAP_NOTE}

    def na_cell(table, row, field, unit, calc):
        fid = add(table, row, field, field.replace("_", " "), unit=unit, period=AS_OF, value_class="calculated",
                  status="not_applicable", calculation_id=calc, formula=FORMULA_COUNT, limitation=NA_LIMITATION)
        return {"fact": fid, "shown": "∅ G# n.m.", "state": "not_meaningful", "note": GAP_NOTE}

    if not empty:
        t1 = []
        for g, b in zip(payload["gaps"], bk["gaps"]):
            gid = g["gap_id"]
            t1.append([gid, {
                "description": text_cell("TDR.1", gid, "description", GAP_DESC),
                "kind_severity": text_cell("TDR.1", gid, "kind_severity", "scope/material"),
                "named_consumers": text_cell("TDR.1", gid, "named_consumers", "CP-DR"),
                "questions": num_cell("TDR.1", gid, "questions", b["questions"], "questions", f"{b['questions']} questions"),
                "answered": num_cell("TDR.1", gid, "answered", b["answered"], "questions", f"{b['answered']} questions"),
                "unresolved": num_cell("TDR.1", gid, "unresolved", b["unresolved"], "questions", f"{b['unresolved']} questions"),
                "answered_share": num_cell("TDR.1", gid, "answered_share", b["answered_share"], "decimal_fraction",
                                           shown_pct(b["answered_share"])),
                "status": text_cell("TDR.1", gid, "status", b["status"], "calculated", f"cpdr-{gid}-status", FORMULA_STATUS),
            }])
        tables["TDR.1"] = {"title": "Research agenda and gap status", "row_header": "Gap", "rows": t1}

        t2 = []
        for g in payload["gaps"]:
            for x in g["questions"]:
                qid, ans = x["question_id"], x["outcome"] == "answered"
                t2.append([qid, {
                    "gap": text_cell("TDR.2", qid, "gap", g["gap_id"]),
                    "question": text_cell("TDR.2", qid, "question", x["text"], "analyst_judgment"),
                    "outcome": text_cell("TDR.2", qid, "outcome", "Answered" if ans else "Not found", "calculated",
                                         f"cpdr-{qid}-outcome", FORMULA_OUTCOME),
                    "answer": (text_cell("TDR.2", qid, "answer", x["answer"], "analyst_judgment", citations=x["citations"])
                               if ans else missing_cell("TDR.2", qid, "answer", x["limitation"])),
                    "evidence": (text_cell("TDR.2", qid, "evidence", evidence_text(x["citations"]), citations=x["citations"])
                                 if ans else missing_cell("TDR.2", qid, "evidence", x["limitation"])),
                    "searched": text_cell("TDR.2", qid, "searched", ", ".join(x["searched_sources"])),
                }])
        tables["TDR.2"] = {"title": "Research questions and cited answers", "row_header": "Question", "rows": t2}

    total_keys = ("gaps_total", "gaps_resolved", "gaps_partial", "gaps_unresolved",
                  "questions_total", "answered_total", "unresolved_total", "answered_share")
    total_cells = {}
    for k in total_keys:
        if k == "answered_share":
            total_cells[k] = (na_cell("TDR.3", "total", k, "decimal_fraction", "cpdr-total-answered_share")
                              if bk[k] is None else
                              num_cell("TDR.3", "total", k, bk[k], "decimal_fraction", shown_pct(bk[k])))
        else:
            word = "gaps" if k.startswith("gaps") else "questions"
            total_cells[k] = num_cell("TDR.3", "total", k, bk[k], word, f"{bk[k]} {word}")
    t3 = [["total", total_cells]]  # the total row only: a declared ReportTable needs one fact per column in every row
    own_limits = [BASE_LIMITATION]
    if empty:
        own_limits.append(EMPTY_LIMITATION)
    for g in payload["gaps"]:
        for x in g["questions"]:
            if x["outcome"] == "not_found":
                # the limitation lives on the missing TDR.2 answer/evidence facts and here, in own limitations
                own_limits.append(f"Unresolved: {x['text']} {x['limitation']}")
    tables["TDR.3"] = {"title": "Research coverage totals", "row_header": "Total", "rows": t3}

    ref = lambda k, u: "{TDR.3.total." + k + "|" + u + "}"  # noqa: E731
    if empty:
        summary = (f"Research covered {ref('questions_total', 'questions')} because the supplied readiness "
                   f"review identified {ref('gaps_total', 'gaps')}.")
        spelled = (f"Research covered {bk['questions_total']} questions because the supplied readiness "
                   f"review identified {bk['gaps_total']} gaps.")
    else:
        summary = (
            f"Research covered {ref('questions_total', 'questions')}; local sources answered "
            f"{ref('answered_total', 'questions')} ({ref('answered_share', '%')}) and "
            f"{ref('unresolved_total', 'questions')} remain unresolved."
        )
        spelled = (f"Research covered {bk['questions_total']} questions; local sources answered "
                   f"{bk['answered_total']} questions ({shown_pct(bk['answered_share'])}) and "
                   f"{bk['unresolved_total']} questions remain unresolved.")
    claims = [{"claim_id": "CPDR-SUM-01", "text": summary, "citations": [], "spelled": spelled}]
    for g in payload["gaps"]:
        for x in g["questions"]:
            if x["outcome"] == "answered":
                claims.append({"claim_id": f"CPDR-ANS-{x['question_id']}", "text": x["answer"],
                               "citations": x["citations"], "spelled": x["answer"]})
    settled = list(dict.fromkeys([*own_limits, SYNTH]))  # execution.py:444-447 appends the synthetic line
    inherited = [t for t in cp0_limits if t not in settled]  # execution.py:345-366
    unresolved_ids = [x["question_id"] for g in payload["gaps"] for x in g["questions"] if x["outcome"] == "not_found"]
    return {
        "case_id": case_id,
        "bookkeeping": {**{k: (str(v) if isinstance(v, Decimal) else v) for k, v in bk.items() if k != "gaps"},
                        "gaps": [{**g, "answered_share": str(g["answered_share"])} for g in bk["gaps"]]},
        "tables": tables,
        "facts": facts,
        "claims": claims,
        "own_limitations": own_limits,
        "settled_limitations": settled,
        "inherited_limitations": inherited,
        "module_status": "restricted",
        "module_status_why": "synthetic case_kind and non-empty own limitations (execution.py:441-457)",
        "consumption_facts": {
            "per_gap": [f"TDR.1.{g['gap_id']}.{f}" for g in bk["gaps"]
                        for f in ("questions", "answered", "unresolved", "answered_share", "status")],
            "totals": [f"TDR.3.total.{k}" for k in total_keys],
            "missing_for_unresolved": [f"TDR.2.{qid}.answer" for qid in unresolved_ids],
        },
    }


CASES = {k: build_case(k, v) for k, v in SUB.items()}
FIXTURES = {}
for name, pay in {
    "fixture_resolved": research(Q1, Q2),
    "fixture_two_gaps": {"gaps": [research(Q1, Q2)["gaps"][0], {"gap_id": "second-gap", "questions": [Q3]}]},
}.items():
    bk = bookkeeping(pay)
    FIXTURES[name] = {
        "note": "composer-only derivation: no run, no tables",
        "derived": {**{k: (str(v) if isinstance(v, Decimal) else v) for k, v in bk.items() if k != "gaps"},
                    "answered_share_shown": shown_pct(bk["answered_share"]),
                    "gaps": [{**g, "answered_share": str(g["answered_share"]), "shown": shown_pct(g["answered_share"])}
                             for g in bk["gaps"]]},
    }

# --- rendering pin (lease M6, acceptance 7): re-pinned 2026-10-28 to the landed 0d render fixes (41a8fdb, b4ae187) ---
# Literals observed by running the committed product render on a pre-run view of this run, then checked by hand against the rule:
# a module the requested_modules override leaves out of the run but inside registry.dependencies(PATHWAY_MODULES[pathway]) reads
# "Not run: <codes> was not requested in this run."; a module outside those dependencies keeps "Not in this Pathway".
RENDER = {
    "observed_with": "report_view.build(Execution.create(pack).view(), credit_snapshot pathway, SHIPPED_MAPS); modules CP-0 and CP-DR unrun; "
                     "report_view.py sha256 51a6853ec0e80393a50cdf8ed577cddaf2eee8e26246609b85dea01712560e12 (after 0d 41a8fdb and 0d(c) b4ae187)",
    "call_withheld": "not_requested",
    "call_band": {"state": "not-requested", "words": "Not run"},
    "navigator_words_scope": "modules outside the run's plan only; CP-0 and CP-DR follow their head status",
    "navigator_words": {
        "Not run": ["CP-1", "CP-1A", "CP-2", "CP-3", "CP-4", "CP-5", "CP-6", "CP-MODEL"],
        "Not in this Pathway": ["CP-1B", "CP-1C", "CP-1D", "CP-2A", "CP-2E", "CP-2G", "CP-2H", "CP-4C", "CP-8", "CP-L10",
                                "CP-MEMO", "CP-OS", "CP-2D", "CP-3D", "CP-3C"],
    },
    "blocks": [
        {"block_id": b, "state": st, "note": note}
        for b, st, note in (
            ("key-findings", "not_run", "Not run: CP-2 was not requested in this run."),
            ("company-operating-model", "not_run", "Not run: CP-1A was not requested in this run."),
            ("model-chart-strip", "not_run", "Not run: CP-1 was not requested in this run."),
            ("capital-structure", "not_run", "Not run: CP-1 was not requested in this run."),
            ("financials-credit-metrics", "not_run", "Not run: CP-1 was not requested in this run."),
            ("strengths-weaknesses", "not_run", "Not run: CP-2 · CP-6 was not requested in this run."),
            ("relative-value", "not_run", "Not run: CP-3 was not requested in this run."),
            ("company-profile", "not_run", "Not run: CP-1A was not requested in this run."),
            ("transaction-summary", "absent", "Absent: No module produces this block yet."),
            ("portfolio-fit", "absent", "Absent: No module produces this block yet."),
            ("committee-challenge", "not_run", "Not run: CP-6 was not requested in this run."),
            ("what-changed", "not_in_pathway", "Not in this Pathway: CP-8 is not part of Credit Snapshot."),
        )
    ],
    "note": "the override-slice wording defect of the first pin is fixed by 0d (docs/reviews/0d-product-defects.md); "
            "CP-8 is outside registry.dependencies of the Credit Snapshot preset, so it keeps 'Not in this Pathway'",
    "pin": "product output at the report_view.py sha256 above; the pin changes only with a change to that render",
}
assert len(RENDER["blocks"]) == 12

# --- tamper recipe (lease M4): a consistent forgery so only cpdr.probe refuses ---------------------
TAMPER = {
    "case": "partial (closed run: CP-0 and CP-DR settled, receipt sealed)",
    "target_fact": "TDR.1.missing-ownership-transaction.status",
    "from": "Partially resolved",
    "to": "Resolved",
    "why_this_fact": "the table cell holds the fact id and the step output holds the submission references, so the status lives only in the "
                     "result Module; it is the one fact the probe's rebuild (bookkeeping over the journaled payload) contradicts",
    "recipe": [
        "1. Copy the closed partial store directory (blobs, snapshots, current, audit) to a scratch path.",
        "2. Load the CP-DR head's result Module; replace only the text of fact TDR.1.missing-ownership-transaction.status; leave every other "
        "fact (TDR.1 questions 3, answered 2, unresolved 1, share 0.6667; every TDR.3.total.* fact), table, claim and limitation unchanged.",
        "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
        "4. Build a new ExecutionSnapshot equal to the current one with the CP-DR Attempt.result_sha256 and Head.result_sha256 set to R2 "
        "(status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json "
        "and rewrite current to that digest.",
        "5. In the retained receipt: set the CP-DR SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named "
        "the old final snapshot (the CP-DR settling OwnerSubmission.snapshot_after_sha256: owner_workflow.py _advance -> _finish_walk; its "
        "record is retained as audit/submissions/<content_hash> by _retain) to the new digest; delete audit/submissions/<old record hash> and "
        "write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with "
        "the forged receipt's content_hash (S1a R3-5 and CP-3 A4 pattern: the audit file travels under its new hash).",
    ],
    "expect": {
        "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and "
                  "publication records, call and read replay, journaled-step replay (the payload and step are untouched)",
        "refuses": "cpdr.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
        "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass (as CP-3 A4 (a)); then cpdr.probe raises "
                        "identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached.",
    },
    "step_output_edit": "an edited CP-DR step output is caught by the store's own blob hash check, not by the probe's output comparison "
                        "(recorded limitation, S1a R3-5)",
}

# --- manifest ------------------------------------------------------------------------------------
manifest = {
    "schema_version": "cpdr-owner-cases/1",
    "scope": "CP-DR LOCAL deep research: resolves CP-0 readiness gaps from the prepared pack through pack tools",
    "status": "Preparation oracle (pre-code); revision 4; not executed",
    "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256",
    "frozen_inputs": [{"path": p, "sha256": h} for p, h in PINS.items()],
    "sources": [
        {"source_id": "identity", "ref": "cases/financial/manifest.json#sources[identity]", "sha256": SHA["identity"]},
        {"source_id": "financial", "ref": "cases/financial/manifest.json#sources[financial]", "sha256": SHA["financial"],
         "limitation": LIMIT_FIN},
        {"source_id": "business", "ref": "cases/snapshot/manifest.json#business_source.gap", "sha256": SHA["business"],
         "limitation": BUS_LIMIT},
    ],
    "run": {
        "run_id": RUN_ID, "issuer_id": "northbridge-synthetic", "issuer_name": ISSUER, "as_of": AS_OF,
        "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "credit_snapshot",
        "requested_modules": ["CP-DR"],
    },
    "run_note": "requested_modules overrides the pathway preset (contracts.Run); plan = CP-0, CP-DR; no CP-1 promotion. "
                "One CP-0 settlement is cloned for the partial, unresolved and blocked attempts and for each refusal "
                "(attempt 0, own clone); the empty-agenda case has its own CP-0 settlement.",
    "plan_order_expected": ["CP-0", "CP-DR"],
    "cp0_delta": CP0_DELTA + [
        "empty agenda variant (submissions.json#cp0_readiness_review_empty_agenda): the same review with gaps = []; "
        "validate_review accepts it and build_readiness emits only T5.review.gaps",
    ],
    "upstream_facts_read": {
        "gap_fact": {"fact_id": T5_FACT_ID, "text": T5_TEXT,
                     "parse": "kind/severity = text before ': '; affects = between the last '; affects ' and the next '; '; remediation = rest"},
        "empty_agenda_fact": {"fact_id": EMPTY_FACT_ID, "text": EMPTY_FACT_TEXT,
                              "rule": "the only T5 fact of a review with no gap; no T5.<gap_id>.gap fact exists, so the agenda is empty"},
        "cp0_limitations": CP0_LIMITATIONS,
        "cp0_limitations_empty_agenda": CP0_LIMITATIONS_EMPTY,
        "T8.CP-DR.limits": T8_LIMITS,
        "T8.CP-DR.limits_empty_agenda": T8_LIMITS_EMPTY,
    },
    "view_tree_draft": {
        "note": "draft proposal, not an observation; no quote, citation or record_json at any depth",
        "keys": {
            "gaps": [{"gap_id": GAP_ID, "kind": "scope", "severity": "material", "description": GAP_DESC,
                      "named_consumers": ["CP-DR"], "remediation": "Supply the ownership and transaction documents"}],
            "sources": [{"source_id": s, "status": "ready"} for s in ORDER],
            "question_limits": {"min_per_gap": 1, "max_per_gap": 4},
            "upstream": {"CP-0": "restricted"},
        },
        "empty_agenda": "the same keys with gaps = []",
    },
    "cases": [
        {"case_id": "partial", "submission": "submissions.json#cpdr.partial", "kind": "positive"},
        {"case_id": "unresolved", "submission": "submissions.json#cpdr.unresolved", "kind": "gap"},
        {"case_id": "empty_agenda", "submission": "submissions.json#cpdr.empty_agenda", "kind": "empty_agenda",
         "cp0": "submissions.json#cp0_readiness_review_empty_agenda"},
        {"case_id": "blocked", "submission": "submissions.json#cpdr.blocked", "kind": "blocked"},
    ],
    "fixtures": list(FIXTURES),
    "consumer": {
        "settled_reader": "cpdr_reader(store, head)",
        "registry_consumer": "CP-5 (edge_rule('CP-5','CP-DR') == restricted; fan-in registry.py)",
        "consumption": "OPEN: no core reads CP-DR today; CP-5 counts only after a D3 scope lease",
    },
}

submissions = {
    "schema_version": "cpdr-owner-submissions/1",
    "note": "Literal reference-and-judgment payloads. Figures never appear in analyst text; counts and shares are Python's. "
            "pack_sha256 token is bound at run time.",
    "cp0_readiness_review": review,
    "cp0_readiness_review_empty_agenda": EMPTY_REVIEW,
    "cpdr": {"partial": SUB["partial"], "unresolved": SUB["unresolved"], "empty_agenda": SUB["empty_agenda"],
             "blocked": BLOCKED},
    "tool_calls": CALLS,
    "refusal_inputs": refusal_inputs,
}

expected = {
    "schema_version": "cpdr-owner-expected/1",
    "derivation_note": "Python's bookkeeping rules applied by cases/cpdr-owner/builder/build.py to submissions.json; "
                       "no product code consulted. share = answered / total quantised to 4 dp ROUND_HALF_UP, displayed x100 at 1 dp. "
                       "Every issue tuple below is also derived by the builder's reference validator and asserted equal to the pinned text.",
    "method_rules": {
        "gap_status": "Resolved if every question answered; Unresolved if none; else Partially resolved",
        "counts": "questions, answered, unresolved per gap and in total (integers, unit questions); gaps by status (unit gaps)",
        "share": "answered / questions, Decimal, 4 dp half-up, unit decimal_fraction; with zero questions the share is not_applicable (cell '∅ G# n.m.'), never 0",
        "never": "a not_found question is never filled: its TDR.2 answer and evidence facts are status missing (analyst's limitation), cells spelled '∅ G#', never 0 or N/A",
        "facts_behind_cells": "every cell of TDR.1-TDR.3 has a fact (cell.fact); formula and calculation_id only on calculated facts",
    },
    "cp0_upstream": {"gap_fact_id": T5_FACT_ID, "gap_fact_text": T5_TEXT, "module_limitations": CP0_LIMITATIONS,
                     "status": "restricted"},
    "cp0_upstream_empty_agenda": {"gap_facts": [], "review_gaps_fact_id": EMPTY_FACT_ID,
                                  "review_gaps_fact_text": EMPTY_FACT_TEXT, "module_limitations": CP0_LIMITATIONS_EMPTY,
                                  "status": "restricted (synthetic case_kind; not run)"},
    "cases": CASES,
    "fixtures": FIXTURES,
    "empty_agenda": {
        "state": "a valid settled state, not a refusal: the only valid submission is {\"gaps\": []}",
        "submission": "submissions.json#cpdr.empty_agenda (one read_inputs, no search, no read)",
        "case": "cases.empty_agenda: TDR.1 and TDR.2 have no rows and are not emitted; TDR.3 holds the total row with counts known 0 and answered_share not_applicable",
        "limitation": EMPTY_LIMITATION,
        "refusal": "refusals.submission_against_empty_agenda (a non-empty submission against the empty agenda)",
        "pinned_limitation": "an answered share over zero questions is not computed; this is the pinned limitation (NA_LIMITATION on the share fact)",
        "share_fact_limitation": NA_LIMITATION,
    },
    "blocked": {
        "attempt_0": {"step": "invalid", "issues": [QUOTE_ISSUE]},
        "attempt_1": {"step": "invalid", "issues": ["text must not contain a figure: transactions"], "repair_of": "attempt 0"},
        "module_status": "blocked",
        "tables": "none; a blocked head carries no TDR table and no claims",
        "head": "published; cpdr_reader exposes the status and no counts",
    },
    "refusals": refusal_expected,
    "refusal_note": "No precheck (LEAD ruling): every refusal is one journaled invalid CP-DR step on attempt 0 of its own clone of the settled "
                    "CP-0 store (the 'submission_against_empty_agenda' clone is the empty-agenda CP-0 store). The attempt is consumed, the "
                    "result is rejected with limitations = the issues, and step_issues is the complete tuple that "
                    "_verify_submissions replays exactly (S1a R3-2). The tool-use items (cited page read, absence backed by a "
                    "search) are the core's RULES(text, seen) (G1-X protocol section 2; live/tools.py unread_citation_issues and "
                    "UNBACKED_ABSENCE, product sorted order), called by G1-X at submit and in the verifier with rules='journaled'; "
                    "RULES is pure over text and Seen and does not know pack membership: the two out-of-pack classes are one defect with both consequences, "
                    "the membership issue then the RULES issue, in that order.",
    "rendering": RENDER,
    "tamper": TAMPER,
    "tool_use": {
        "CP-DR": "exactly one ok read_inputs per attempt before submit; ok search_pack covering every searched source of every "
                 "question; ok read_pages for every cited locator; zero web or provider calls (no such tool exists); "
                 "an invoke of any other tool is a refused not_permitted receipt",
        "search_rule": "a span matches when it contains any query term (case-insensitive substring); header "
                       "'<n> spans match <query!r>; showing <min(10,n)>.' (live/tools.py search_pack)",
    },
    "attempt_inputs": ["prepared-pack", "CP-0"],
    "settled_module_adds_input": "research-submission",
    "inherited_limitations_rule": "CP-0 head limitations, de-duplicated, own (settled) removed (execution.py:345-366); pinned per case in cases.<case>.inherited_limitations",
    "evidence_rail": ["TDR.1", "TDR.2"],
    "limitations_rail": ["TDR.3"],
    "table_id_collision_check": "methodology.json: TDR.1-TDR.3 appear only in the CP-DR entry (asserted by the builder); src/ and tests/ scan reported separately",
    "consumption": {
        "reader": "cpdr_reader(store, head) exposes: head hash, status, per gap {gap_id, status, questions, answered}, totals, unresolved question ids",
        "consumer": "none today; CP-5 is the only registry edge (restricted); status OPEN",
        "future_cp5_binding": "the CP-5 attempt binds the CP-DR head result_sha256 as an Input and its review cites the facts listed in cases.<case>.consumption_facts",
        "facts_to_cite": "TDR.1.<gap>.{questions,answered,unresolved,answered_share,status}; TDR.3.total.* (gaps_total, gaps_resolved, gaps_partial, "
                         "gaps_unresolved, questions_total, answered_total, unresolved_total, answered_share); and, for each unresolved item, the "
                         "missing fact TDR.2.<qid>.answer (its limitation is the unresolved reason)",
    },
    "not_verified": [
        "whether an answering quote actually answers its question is analyst judgment; only verbatim location and tool use are checked",
        "hit counts follow the documented search rule and were checked against PackTools headers by a revision probe, not by product code under test",
        "the empty-agenda CP-0 settles restricted is derived from the synthetic case_kind rule, not run; a Module with TDR.1 and TDR.2 absent is not constructed",
    ],
}


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
dump("manifest.json", manifest)
dump("submissions.json", submissions)
dump("expected.json", expected)
