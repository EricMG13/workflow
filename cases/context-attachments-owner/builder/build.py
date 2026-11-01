"""Writes cases/context-attachments-owner/* (stdlib only; deploy_vii and deploy_workflow are never imported).

Phase 5 Task 0 oracle: declared attachments and draft legal documents from the context file.
Every expected value comes from the plan (docs/superpowers/plans/2026-10-31-phase-5-attachments-modes.md,
Task 0 and Task 3 "Behaviour"), the brief (.superpowers/sdd/2026-10-31-phase-5-attachments-modes/task-0-brief.md)
and the rulings (docs/rulings/2026-10-31-context-plan.md B7, B17 items 4-6), never from code under test.
Upstream values are copied from the frozen, pinned cases/cp4-owner files and cases/financial, cases/legal.

Run: python3 -I cases/context-attachments-owner/builder/build.py   (from the repository root)
Two runs write byte-identical files.
"""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "context-attachments-owner"
CASE = "cases/context-attachments-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/legal/manifest.json": "d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168",
    "cases/cp4-owner/manifest.json": "2c12bf6836f54b704201af217866002d279b51cd8f1ed6094154aec9198f6b23",
    "cases/cp4-owner/submissions.json": "f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461",
    "cases/cp4-owner/expected.json": "1dff2422178235931f0ad39a27eabc813700a2dcfd86748ba0f17bfdb16e5d78",
}
RAW = {}
for rel, digest in PINS.items():
    RAW[rel] = (ROOT / rel).read_bytes()
    assert hashlib.sha256(RAW[rel]).hexdigest() == digest, f"input drift: {rel}"
FIN = json.loads(RAW["cases/financial/manifest.json"])
LEG = json.loads(RAW["cases/legal/manifest.json"])
CP4M = json.loads(RAW["cases/cp4-owner/manifest.json"])
CP4S = json.loads(RAW["cases/cp4-owner/submissions.json"])
CP4E = json.loads(RAW["cases/cp4-owner/expected.json"])


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def page_sha(pages):
    return sha("\f".join(p["text"] for p in pages).encode("utf-8"))


def norm(s):
    return re.sub(r"\s+", " ", s)


# --- fixed identifiers, texts (brief and plan, verbatim) ---------------------------------------
ISSUER_ID, ISSUER_NAME, AS_OF = "northbridge-synthetic", "Northbridge Synthetic Group", "2026-01-10"
MISMATCH_AS_OF = "2026-01-11"
DRAFT_LIMITATION = (
    "Legal documents in this run are drafts, not executed or filed instruments; "
    "covenant terms may change before signing."
)
# Task 0 table (abs-refused): field order and the id each field names (plan Task 3 ATTACHMENT_IDS).
ATTACHMENT_IDS = (
    ("portfolio_workbook", "portfolio"),
    ("prior_case", "prior_case"),
    ("management_bridge", "bridge"),
)


def absent_issue(field, source_id):
    return f"attachments.{field}: source '{source_id}' is declared but not in the pack; add a source gap naming it"


EXEC_MISSING_ISSUE = (
    "attachments.legal_documents: 'executed' documents are declared but no source is assessed "
    "executed or filed; add a source gap naming legal_documents"
)
MISMATCH_ISSUE = (
    f"Context refused: run.as_of: context has '{MISMATCH_AS_OF}' but the run has '{AS_OF}'"
)  # "Context refused: " + the problem text of context.py:763-768 (frozen format)
DRAFT_WRONG_CONTEXT = "Draft authority needs a context that declares draft legal documents: {source_id}"
# cp4_legal.py:476-478 (frozen wording, plan Q2); the row path is cp4_legal.py:397 `<field>[<index>]`.
NOT_LEGAL_ISSUE = (
    "{path}: {source_id} is not an executed or filed source (CP-0 authority "
    "{authority}, or the source is not ready)"
)
SOURCE_ID_RE = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"  # plan Task 3 (L5)

# --- contexts (the form's layout; run_type research, no deal rows needed) -----------------------


def context(*, as_of=AS_OF, portfolio=False, prior=False, bridge=False, legal="none"):
    return {
        "schema": "context/1",
        "run": {
            "run_type": "research",
            "pathway": "credit_snapshot",
            "case_kind": "synthetic",
            "as_of": as_of,
            "current_period": "",
            "prior_period": "",
            "reporting_currency": "USD",
        },
        "identity": {
            "issuer_name": ISSUER_NAME,
            "issuer_id": ISSUER_ID,
            "borrower_name": "",
            "parent_name": "",
            "guarantors": [],
            "aliases": [],
            "listed_equity": False,
            "ticker": "",
            "sector": "",
            "country": "",
            "sponsor": "",
        },
        "deal_terms": [],
        "quotes": [],
        "ratings": [],
        "valuation": {
            "peer_source": "cp_dr_public",
            "basis": "auto",
            "issuer_market": {
                "market_cap_m": "",
                "net_debt_m": "",
                "ev_m": "",
                "ebitda_basis": "LTM",
                "as_of": "",
                "source": "",
            },
            "peers": [],
            "precedents": [],
            "user_multiple": {"value": "", "basis": "LTM", "rationale": ""},
        },
        "assumptions": {k: None for k in ("cp2a", "cp2d", "cp2e", "cp3c", "cp3d", "cp4c")},
        "attachments": {
            "portfolio_workbook": portfolio,
            "prior_case": prior,
            "management_bridge": bridge,
            "legal_documents": legal,
        },
        "research_questions": [],
    }


CONTEXTS = {
    "context-abs": context(portfolio=True, prior=True, bridge=True, legal="executed"),
    "context-bridge": context(bridge=True, legal="none"),
    "context-none": context(),
    "context-executed": context(legal="executed"),
    "context-draft": context(legal="draft"),
    "context-mismatch": context(as_of=MISMATCH_AS_OF),
}
CTX_BYTES = {cid: dumps(obj).encode("utf-8") for cid, obj in CONTEXTS.items()}
CTX_SHA = {cid: sha(data) for cid, data in CTX_BYTES.items()}


def key_line(cid, key):
    lines = CTX_BYTES[cid].decode("utf-8").splitlines()
    hits = [i for i, line in enumerate(lines, 1) if line.lstrip().startswith(f'"{key}":')]
    assert len(hits) == 1, (cid, key, hits)
    return hits[0]


# --- the preparer-written bridge source (a new source; no upstream bytes) --------------------
BRIDGE_TEXT = (
    "NORTHBRIDGE SYNTHETIC GROUP\n"
    "Synthetic management bridge note\n"
    "This invented note is test data, not evidence about a real issuer.\n"
    "Management states that its adjusted view of EBITDA differs from the reported view by named items.\n"
    "No item is verified against the issuer statements."
)
BRIDGE_BYTES = BRIDGE_TEXT.encode("utf-8")
BRIDGE_SHA = sha(BRIDGE_BYTES)
BRIDGE_LINE = "Synthetic management bridge note"  # line 2, quoted by the CP-0 assessment

# --- upstream sources (cases/cp4-owner/manifest.json pack_sources, copied) -------------------
POS = next(c for c in CP4M["cases"] if c["case_id"] == "legal-current-matching-definition")
GAPC = next(c for c in CP4M["cases"] if c["case_id"] == "legal-current-missing-ebitda-definition")
BASE = {s["source_id"]: deepcopy(s) for s in POS["pack_sources"]}  # identity, financial, legal-covenants
assert list(BASE) == ["identity", "financial", "legal-covenants"]
LEGAL_DRAFT_SRC = deepcopy(GAPC["pack_sources"][2])  # the other frozen legal bytes, id changed
assert LEGAL_DRAFT_SRC["source_id"] == "legal-covenants"
LEGAL_DRAFT_SRC["source_id"] = "legal-draft"
LEGAL_DRAFT_SRC["origin"] = (
    "cases/cp4-owner/manifest.json:101-135 (gap case legal source, bytes unchanged), source_id changed "
    "so a draft source can sit beside the executed one"
)

fin_src = {s["source_id"]: s for s in FIN["sources"]}
leg_case = {c["case_id"]: c for c in LEG["cases"]}
PAGES = {
    "identity": {p["locator"]: p["text"] for p in fin_src["identity"]["pages"]},
    "financial": {p["locator"]: p["text"] for p in fin_src["financial"]["pages"]},
    "legal-covenants": {
        p["locator"]: p["text"]
        for p in leg_case["legal-current-matching-definition"]["legal_source"]["pages"]
    },
    "legal-draft": {
        p["locator"]: p["text"]
        for p in leg_case["legal-current-missing-ebitda-definition"]["legal_source"]["pages"]
    },
    "bridge": {"line:2": BRIDGE_LINE},
}
SHA = {sid: s["sha256"] for sid, s in {**BASE, "legal-draft": LEGAL_DRAFT_SRC}.items()}
SHA["bridge"] = BRIDGE_SHA
for sid in ("identity", "financial"):
    assert page_sha(fin_src[sid]["pages"]) == SHA[sid]
assert page_sha(leg_case["legal-current-matching-definition"]["legal_source"]["pages"]) == SHA["legal-covenants"]
assert page_sha(leg_case["legal-current-missing-ebitda-definition"]["legal_source"]["pages"]) == SHA["legal-draft"]

LIMIT_FIN = BASE["financial"]["limitation"]
LEGAL_LIM = BASE["legal-covenants"]["limitation"]
BORROWER = (
    "Clause 1.1. Borrower means Northbridge Synthetic Group, the issuer named in the Issuer identity "
    "and reporting scope note."
)
CTX_LIMIT = (
    "User-supplied run context: its names, periods and figures are the user's statements; "
    "CP-0 classifies its authority as unknown and does not verify them against issuer sources."
)
DRAFT_NOTE = (
    "Declared draft by the run context; the page text describes itself as an executed restatement, "
    "so execution is not established."
)


def cite(sid, locator, quote):
    if sid == "bridge":
        assert quote == BRIDGE_LINE
    else:
        assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "source_sha256": SHA[sid], "locator": locator, "quote": quote}


def cite_ctx(cid):
    line = key_line(cid, "issuer_name")
    return {
        "source_id": "context",
        "source_sha256": CTX_SHA[cid],
        "locator": f"line:{line}",
        "quote": f'"issuer_name": "{ISSUER_NAME}",',
    }


# --- pack definitions ----------------------------------------------------------------------


def ctx_source(cid):
    return {
        "source_id": "context",
        "path": f"{CASE}/{cid}.json",
        "media_type": "text/plain",
        "built_by": "prepare (SourceRequest(source_id='context', path, media_type='text/plain')); context.preparation_request is not used",
        "sha256": CTX_SHA[cid],
        "status": "ready",
    }


def bridge_source(ready):
    if ready:
        return {
            "source_id": "bridge",
            "path": f"{CASE}/bridge.txt",
            "media_type": "text/plain",
            "built_by": "prepare (SourceRequest); the file bytes are bridge.txt in this case directory",
            "sha256": BRIDGE_SHA,
            "status": "ready",
        }
    return {
        "source_id": "bridge",
        "path": f"{CASE}/bridge-absent.txt",
        "media_type": "text/plain",
        "built_by": "prepare with no bytes (prepare_source(request, None)): status missing, extraction_status blocked, limitation 'Requested file is absent'; the file does not exist",
        "sha256": None,
        "status": "missing",
        "limitation": "Requested file is absent",
    }


def frozen(sid):
    if sid == "legal-draft":
        return LEGAL_DRAFT_SRC
    return BASE[sid]


# --- CP-0 review pieces ---------------------------------------------------------------------
POS_REVIEW = CP4S["positive"]["readiness_review"]
A_IDENTITY, A_FINANCIAL, A_LEGAL_EXEC = (deepcopy(s) for s in POS_REVIEW["sources"])
C_CP1, C_CP4 = (deepcopy(c) for c in POS_REVIEW["consumers"])
assert (A_IDENTITY["source_id"], A_FINANCIAL["source_id"], A_LEGAL_EXEC["source_id"]) == (
    "identity",
    "financial",
    "legal-covenants",
)
assert (C_CP1["module_id"], C_CP4["module_id"]) == ("CP-1", "CP-4")
PLACEHOLDER = POS_REVIEW["pack_sha256"]
assert PLACEHOLDER.startswith("<<PACK_SHA256")


def a_legal(sid, authority):
    if authority == "executed":
        a = deepcopy(A_LEGAL_EXEC)
        a["source_id"] = sid
        a["authority"] = authority
        a["citations"] = [cite(sid, "page:1", q["quote"]) for q in a["citations"]]
        return a
    assert authority == "draft"
    return {
        "source_id": sid,
        "document_family": "Draft term loan covenant terms",
        "authority": "draft",
        "entity": ISSUER_NAME,
        "period": "Effective December 31, 2025",
        "version_relationship": "Draft restatement as declared by the run context; not a signed instrument",
        "fidelity": "verified",
        "citations": [cite(sid, "page:1", BORROWER)],
        "limitations": [LEGAL_LIM, DRAFT_NOTE],
    }


def a_context(cid):
    return {
        "source_id": "context",
        "document_family": "User-supplied run context",
        "authority": "unknown",
        "entity": ISSUER_NAME,
        "period": AS_OF,
        "version_relationship": "User-supplied form download for this run",
        "fidelity": "verified",
        "citations": [cite_ctx(cid)],
        "limitations": [CTX_LIMIT],
    }


def a_bridge(ready):
    if ready:
        return {
            "source_id": "bridge",
            "document_family": "Management bridge note",
            "authority": "management",
            "entity": ISSUER_NAME,
            "period": AS_OF,
            "version_relationship": "Management-supplied note for this run",
            "fidelity": "verified",
            "citations": [cite("bridge", "line:2", BRIDGE_LINE)],
            "limitations": ["Management statements; not verified against issuer statements."],
        }
    return {
        "source_id": "bridge",
        "document_family": "Management bridge note",
        "authority": "unknown",
        "entity": None,
        "period": None,
        "version_relationship": "Not supplied",
        "fidelity": "blocked",
        "citations": [],
        "limitations": ["Requested file is absent"],
    }


def consumer_cp4(legal_ids):
    c = deepcopy(C_CP4)
    c["source_ids"] = list(legal_ids)
    c["citations"] = [cite(legal_ids[0], "page:1", BORROWER)]
    return c


C_CP4_BLOCKED = {
    "module_id": "CP-4",
    "readiness": "BLOCKED",
    "evidence_demand": "Located executed covenant clauses, definitions, thresholds and permissions",
    "source_ids": [],
    "rationale": "No legal source is in the pack, so covenant terms cannot be interpreted",
    "citations": [],
    "missing_source": "legal-covenants",
    "limitations": ["No legal source is in the pack"],
}


def gap(gap_id, description, remediation, modules):
    return {
        "gap_id": gap_id,
        "kind": "source",
        "severity": "material",
        "description": description,
        "affected_modules": modules,
        "remediation": remediation,
        "citations": [],
    }


def analysis(legal_id):
    cites = [cite("identity", "page:1", "Northbridge Synthetic Group is the issuer and consolidated group."),
             cite("financial", "page:1", "Currency: USD; amounts in millions.")]
    if legal_id:
        cites.append(cite(legal_id, "page:1", BORROWER))
    return [
        {
            "claim_id": "source-assessment",
            "text": "Located statements and the supplied sources support historical analysis with limitations.",
            "citations": cites,
            "limitation": LIMIT_FIN,
        }
    ]


def review(sources, consumers, gaps, legal_id):
    return {
        "pack_sha256": PLACEHOLDER,
        "objective": "Attachment and legal-document consumption check over the supplied sources",
        "reporting_period": "Reported FY2025, test date December 31, 2025",
        "issuer_confirmed": True,
        "sources": sources,
        "consumers": consumers,
        "gaps": gaps,
        "analysis": analysis(legal_id),
    }


def std(cid, *, legal, extras=(), gaps=(), with_context=True, cp4=None):
    """Sources in pack order: identity, financial, legal ids, extras, context. `legal` = ((id, authority), ...)."""
    sources = [deepcopy(A_IDENTITY), deepcopy(A_FINANCIAL)]
    sources += [a_legal(sid, auth) for sid, auth in legal]
    sources += list(extras)
    if with_context:
        sources.append(a_context(cid))
    legal_ids = [sid for sid, _ in legal]
    consumers = [deepcopy(C_CP1), cp4 if cp4 is not None else consumer_cp4(legal_ids)]
    return review(sources, consumers, list(gaps), legal_ids[0] if legal_ids else None)


# --- the cases ------------------------------------------------------------------------------
ABS_GAPS = [
    gap(
        "portfolio-missing",
        "Source 'portfolio' is declared in the run context but is not supplied in the pack",
        "Supply the portfolio workbook as source 'portfolio'",
        ["CP-0"],
    ),
    gap(
        "prior-case-missing",
        "Source 'prior_case' is declared in the run context but is not supplied in the pack",
        "Supply the prior case as source 'prior_case'",
        ["CP-0"],
    ),
    gap(
        "bridge-missing",
        "Source 'bridge' is declared in the run context but is not supplied in the pack",
        "Supply the management bridge as source 'bridge'",
        ["CP-0"],
    ),
]
# each gap description names exactly its own id under the regex of plan Task 3 (L5)
for _g, (_f, _id) in zip(ABS_GAPS, ATTACHMENT_IDS, strict=True):
    for _f2, _id2 in ATTACHMENT_IDS:
        assert bool(re.search(SOURCE_ID_RE.format(re.escape(_id2)), _g["description"])) == (_id2 == _id), (_g["gap_id"], _id2)
EXEC_GAP = gap(
    "legal-documents-missing",
    "The run context declares executed legal_documents but the pack holds no executed or filed source",
    "Supply the executed legal documents",
    ["CP-4"],
)
assert "legal_documents" in EXEC_GAP["description"]
WRONG_CTX_GAP = gap(
    "legal-documents-unconfirmed",
    "The run context does not declare draft legal_documents, so no executed source is confirmed for the legal source",
    "Supply the executed legal documents or declare draft legal documents in the context",
    ["CP-4"],
)
assert "legal_documents" in WRONG_CTX_GAP["description"]

CTX_OF = {  # case -> context file
    "abs-refused": "context-abs",
    "abs-gap-ok": "context-abs",
    "abs-present": "context-bridge",
    "abs-unready": "context-bridge",
    "none-declared": "context-none",
    "legal-exec-missing": "context-executed",
    "legal-exec-missing-gap": "context-executed",
    "draft-ok": "context-draft",
    "draft-wrong-context": "context-executed",
    "draft-wrong-context-no-context": None,
    "draft-cited-other": "context-draft",
    "draft-uncited": "context-draft",
    "mismatch": "context-mismatch",
}
LEGAL_EXEC = (("legal-covenants", "executed"),)
LEGAL_DRAFT = (("legal-covenants", "draft"),)
PACK_SIDS = {  # ordered source ids; context last (prepare appends it, context.py preparation_request)
    "abs-refused": ["identity", "financial", "legal-covenants"],
    "abs-gap-ok": ["identity", "financial", "legal-covenants"],
    "abs-present": ["identity", "financial", "legal-covenants", "bridge"],
    "abs-unready": ["identity", "financial", "legal-covenants", "bridge(missing)"],
    "none-declared": ["identity", "financial", "legal-covenants"],
    "legal-exec-missing": ["identity", "financial"],
    "legal-exec-missing-gap": ["identity", "financial"],
    "draft-ok": ["identity", "financial", "legal-covenants"],
    "draft-wrong-context": ["identity", "financial", "legal-covenants"],
    "draft-wrong-context-no-context": ["identity", "financial", "legal-covenants"],
    "draft-cited-other": ["identity", "financial", "legal-covenants"],
    "draft-uncited": ["identity", "financial", "legal-covenants", "legal-draft"],
    "mismatch": ["identity", "financial", "legal-covenants"],
}


def pack_for(case):
    out = []
    for sid in PACK_SIDS[case]:
        if sid == "bridge":
            out.append(bridge_source(True))
        elif sid == "bridge(missing)":
            out.append(bridge_source(False))
        else:
            spec = deepcopy(frozen(sid))
            spec["built_by"] = "frozen cases/cp4-owner pack source (Source with spans = the pages, no media_type)"
            out.append(spec)
    if CTX_OF[case]:
        out.append(ctx_source(CTX_OF[case]))
    return out


REVIEWS = {
    "abs-refused": std("context-abs", legal=LEGAL_EXEC),
    "abs-gap-ok": std("context-abs", legal=LEGAL_EXEC, gaps=ABS_GAPS),
    "abs-present": std("context-bridge", legal=LEGAL_EXEC, extras=[a_bridge(True)]),
    "abs-unready": std("context-bridge", legal=LEGAL_EXEC, extras=[a_bridge(False)]),
    "none-declared": std("context-none", legal=LEGAL_EXEC),
    "legal-exec-missing": std("context-executed", legal=(), cp4=C_CP4_BLOCKED),
    "legal-exec-missing-gap": std("context-executed", legal=(), cp4=C_CP4_BLOCKED, gaps=[EXEC_GAP]),
    "draft-ok": std("context-draft", legal=LEGAL_DRAFT),
    "draft-wrong-context": std("context-executed", legal=LEGAL_DRAFT, gaps=[WRONG_CTX_GAP]),
    "draft-wrong-context-no-context": std(None, legal=LEGAL_DRAFT, with_context=False),
    "draft-cited-other": std("context-draft", legal=LEGAL_DRAFT),
    "draft-uncited": std(
        "context-draft", legal=(("legal-covenants", "executed"), ("legal-draft", "draft"))
    ),
    "mismatch": std("context-mismatch", legal=LEGAL_EXEC),
}
# abs-unready: the pack carries the missing bridge before the context source (pack order)
assert [s["source_id"] for s in REVIEWS["abs-unready"]["sources"]] == [
    "identity", "financial", "legal-covenants", "bridge", "context",
]

# --- CP-4 submissions (copied from the frozen cp4-owner positive payload) -------------------
CP4_BASE = CP4S["positive"]["legal_covenants"]
CP4_EXTRA_BASKET = {
    "basket": "Issuer identity note",
    "permits": "Identification of the issuer",
    "conditions": "None stated",
    "citations": [
        {"source_id": "identity", "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}
    ],
    "limitation": None,
}
assert norm(CP4_EXTRA_BASKET["citations"][0]["quote"]) in norm(PAGES["identity"]["page:1"])
CP4_OTHER = deepcopy(CP4_BASE)
CP4_OTHER["capacity"].append(CP4_EXTRA_BASKET)
assert len(CP4_BASE["capacity"]) == 3 and len(CP4_OTHER["capacity"]) == 4
assert list(CP4_BASE) == ["documents", "covenants", "capacity", "red_flags", "protection_score", "gaps"]

# CP-1 source_context for the end-to-end draft run (Task 4): the frozen positive one, the legal entry
# restated as draft, plus the context entry (the overlay pattern of cases/context-identity-periods).
CP1_SC = deepcopy(CP4S["positive"]["cp1_source_context"])
_legal_entry = CP1_SC["sources"][2]
assert _legal_entry["source_id"] == "legal-covenants"
_legal_entry["document_type"] = "Draft term loan covenant terms"
_legal_entry["evidence_rationale"] = "Declared draft by the run context; not audited financial evidence"
CP1_SC["sources"].append(
    {
        "source_id": "context",
        "classification": "nonfinancial",
        "document_type": "User-supplied run context",
        "published_on": AS_OF,
        "evidence_class": "internal",
        "evidence_rationale": "User-supplied settings and names; authority unknown (D2)",
        "analytical_use": "Run settings and user-stated names",
        "citations": [cite_ctx("context-draft")],
        "event_scan": "unassessed",
        "event_scan_explanation": "A user-supplied run context is not event evidence",
    }
)

SUBMISSIONS = {
    "schema_version": "context-attachments-owner-submissions/1",
    "note": (
        "Literal inputs per case: the CP-0 readiness review (pack_sha256 bound at run time) and, for the three "
        "draft cases that reach CP-4, the CP-4 legal_covenants payload. The review pieces for identity, financial, "
        "the CP-1 consumer and the CP-4 consumer are copied from cases/cp4-owner/submissions.json#positive.readiness_review "
        "(pinned); the CP-4 payload is cases/cp4-owner/submissions.json#positive.legal_covenants unchanged "
        "(draft-cited-other appends one capacity row quoting `identity`)."
    ),
    "frozen_inputs": {rel: {"sha256": digest} for rel, digest in sorted(PINS.items())},
    "run_time_bindings": {"pack_sha256": PLACEHOLDER},
    "cases": {},
    "cp1_source_context_draft_ok": CP1_SC,
}
for case in CTX_OF:
    entry = {"cp0_review": REVIEWS[case]}
    if case in ("draft-ok", "draft-uncited"):
        entry["cp4_legal_covenants"] = CP4_BASE
        entry["cp4_source"] = "cases/cp4-owner/submissions.json#positive.legal_covenants (cites legal-covenants only)"
    if case == "draft-cited-other":
        entry["cp4_legal_covenants"] = CP4_OTHER
        entry["cp4_source"] = "positive.legal_covenants plus capacity[3] quoting `identity` (CP-0 authority issuer)"
    SUBMISSIONS["cases"][case] = entry

# --- expected (hand-derived; tags P precheck refusal, V validate_review, M module output) ------
CP4_OWN = CP4E["positive"]["CP-4"]["own_limitations"]
assert len(CP4_OWN) == 2


def t3(case):
    return {s["source_id"]: s["authority"] for s in REVIEWS[case]["sources"]}


EXPECTED_CASES = {
    "abs-refused": {
        "P": {
            "issues": [absent_issue(f, i) for f, i in ATTACHMENT_IDS],
            "count": 3,
            "order": "portfolio_workbook, prior_case, management_bridge",
            "journaled_steps": 0,
            "attempt_consumed": False,
        },
        "V": "not reached (the precheck refuses first)",
        "M": None,
    },
    "abs-gap-ok": {
        "P": {"issues": []},
        "V": {"issues": [], "note": "the review settles; asserted by the builder of Task 3 through submit_review, shape-checked by the preparer with validate_review"},
        "M": {
            "T3": t3("abs-gap-ok"),
            "T5_gap_ids": [g["gap_id"] for g in ABS_GAPS],
            "note": "T3 authority per source and the three gaps are the review's own statements (readiness.py build_readiness T3/T5)",
        },
    },
    "abs-present": {"P": {"issues": []}, "V": {"issues": []}, "M": None, "path_note": "unit test of precheck"},
    "abs-unready": {
        "P": {
            "issues": [absent_issue("management_bridge", "bridge")],
            "rule": "a pack source whose status is not ready is absent; the issue text is the same template as for a source that is not in the pack at all (plan Task 3: 'absent when no pack source has the id with status ready')",
        },
        "V": "unit test of precheck only",
        "M": None,
    },
    "none-declared": {"P": {"issues": []}, "V": {"issues": []}, "M": {"T3": t3("none-declared"), "note": "equals today"}},
    "legal-exec-missing": {
        "P": {"issues": [EXEC_MISSING_ISSUE], "journaled_steps": 0, "attempt_consumed": False},
        "V": "not reached",
        "M": None,
    },
    "legal-exec-missing-gap": {
        "P": {"issues": [], "note": "same pack, context and sources as legal-exec-missing, plus one `source` gap whose description contains legal_documents"},
        "V": {"issues": []},
        "M": {"T3": t3("legal-exec-missing-gap"), "T5_gap_ids": [EXEC_GAP["gap_id"]]},
    },
    "draft-ok": {
        "P": {"issues": []},
        "V": {"issues": [], "note": "today a shape error on authority 'draft'; Task 1 admits it for a draft context"},
        "M": {
            "CP-0": {"T3.legal-covenants.authority": "draft", "other_T3": {"identity": "issuer", "financial": "issuer", "context": "unknown"}},
            "CP-4": {
                "admitted": True,
                "legal_sources": ["legal-covenants"],
                "own_limitations": {
                    "contains_once": DRAFT_LIMITATION,
                    "also_contains": CP4_OWN,
                    "source": "the frozen cases/cp4-owner expected.json positive.CP-4.own_limitations (the same CP-4 payload) plus DRAFT_LIMITATION appended (plan Task 2: after the gap limitations; dedup)",
                    "total_count": 3,
                },
                "T4D.1": {
                    "legal-covenants": {"CP-0 authority": "draft", "Eligible for CP-4 citation": "Yes", "Cited by CP-4": "Yes"},
                    "identity": {"CP-0 authority": "issuer", "Eligible for CP-4 citation": "No", "Cited by CP-4": "No"},
                    "financial": {"CP-0 authority": "issuer", "Eligible for CP-4 citation": "No", "Cited by CP-4": "No"},
                    "context": {"CP-0 authority": "unknown", "Eligible for CP-4 citation": "No", "Cited by CP-4": "No"},
                    "columns": "cp4_legal.py:1209-1222 (Source ID|CP-0 authority|Eligible for CP-4 citation|Cited by CP-4|Limitation)",
                },
            },
        },
    },
    "draft-wrong-context": {
        "P": {"issues": [], "why": "the context declares `executed`; the review assesses no executed or filed source, but its `source` gap names legal_documents, so the executed rule passes; all attachments are false"},
        "V": {"issues": [DRAFT_WRONG_CONTEXT.format(source_id="legal-covenants")]},
        "M": None,
    },
    "draft-wrong-context-no-context": {
        "P": {"issues": [], "why": "no context source: context_facts returns None, the precheck gives ()"},
        "V": {"issues": [DRAFT_WRONG_CONTEXT.format(source_id="legal-covenants")]},
        "M": None,
    },
    "draft-cited-other": {
        "P": {"issues": []},
        "V": {"issues": []},
        "M": {
            "CP-4": {
                "step_validation_issues_include": [
                    NOT_LEGAL_ISSUE.format(path="capacity[3]", source_id="identity", authority="issuer")
                ],
                "wording": "frozen (plan Q2): the text keeps 'executed or filed'; `is not an executed, filed or draft source` is NOT used",
                "journal": "the CP-4 step is rejected; the legal documents row still cites legal-covenants (draft) and is not among the issues",
                "not_among_issues": "documents[0] / the covenant rows quoting legal-covenants",
            }
        },
    },
    "draft-uncited": {
        "P": {"issues": []},
        "V": {"issues": []},
        "M": {
            "CP-0": {"T3": t3("draft-uncited")},
            "CP-4": {
                "own_limitations": {"contains_once": DRAFT_LIMITATION, "also_contains": CP4_OWN, "total_count": 3},
                "T4D.1": {
                    "legal-covenants": {"CP-0 authority": "executed", "Eligible for CP-4 citation": "Yes", "Cited by CP-4": "Yes"},
                    "legal-draft": {"CP-0 authority": "draft", "Eligible for CP-4 citation": "Yes", "Cited by CP-4": "No"},
                },
                "rule": "eligibility, not citation, triggers the limitation (plan Q4 and Task 2(c))",
            },
        },
    },
    "mismatch": {
        "P": {"issues": [MISMATCH_ISSUE], "count": 1, "journaled_steps": 0, "attempt_consumed": False},
        "V": "not reached",
        "M": None,
    },
}

EXPECTED = {
    "schema_version": "context-attachments-owner-expected/1",
    "derivation": (
        "Hand-derived from the plan Task 0 table and Task 3 behaviour, the brief, and the rulings; builder "
        "cases/context-attachments-owner/builder/build.py (stdlib only). Upstream CP-4 limitations, T3 and source "
        "texts are copied from the pinned cases/cp4-owner files. No value comes from running the code under test."
    ),
    "tags": {
        "P": "submit_review precheck refusal (owner_workflow _gate, run first; recomputed in replay)",
        "V": "validate_review (reached only when the precheck passes)",
        "M": "module output",
    },
    "draft_limitation": DRAFT_LIMITATION,
    "texts": {
        "absent_template": "attachments.<field>: source '<id>' is declared but not in the pack; add a source gap naming it",
        "legal_executed_missing": EXEC_MISSING_ISSUE,
        "context_refused_prefix": "Context refused: ",
        "draft_wrong_context": DRAFT_WRONG_CONTEXT,
        "not_legal_source (frozen, cp4_legal.py:476-478)": NOT_LEGAL_ISSUE,
        "gap_match_regex": SOURCE_ID_RE.format("<id>"),
    },
    "attachment_ids": {f: i for f, i in ATTACHMENT_IDS},
    "max_issues": 4,
    "cases": EXPECTED_CASES,
    "not_frozen_here": [
        "the 'draft' declared but no draft-assessed source issue text (no case in the Task 0 table; the plan gives no wording)",
        "the Task 1 (h) `Context source cannot be classified <authority>` and (d) `Draft authority refused, context invalid: <first problem>` lines belong to the Task 1 tests, which use these packs",
    ],
}

# --- write ----------------------------------------------------------------------------------
files = {}
for cid, data in CTX_BYTES.items():
    files[f"{cid}.json"] = data
files["bridge.txt"] = BRIDGE_BYTES
files["submissions.json"] = dumps(SUBMISSIONS).encode("utf-8")
files["expected.json"] = dumps(EXPECTED).encode("utf-8")

RUN_BASE = {
    "issuer_id": ISSUER_ID,
    "issuer_name": ISSUER_NAME,
    "as_of": AS_OF,
    "method_version": "deploy-v-r14",
    "case_kind": "synthetic",
    "pathway": "credit_snapshot",
    "requested_modules": ["CP-4"],
}
MANIFEST = {
    "schema_version": "context-attachments-owner-cases/1",
    "scope": "Phase 5 Task 0 oracle: declared attachments (CP-0 precheck) and the draft-documents mode",
    "status": "prepared by preparer; not reviewed; not frozen; not pinned (cases/PINS.json and pins.py PATTERNS are changed at the freeze step)",
    "pack_rule": "Packs are built through prepare with Run(requested_modules=('CP-4',)): the frozen identity, financial and legal sources as cases/cp4-owner pack_sources (no source bytes edited); the `context` source from context-*.json and the `bridge` source from bridge.txt via SourceRequest(media_type='text/plain'). preparation_request is not used (the credit_snapshot preset is CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, ... contracts.py:49-51; the walk is sequential so a preset run would need CP-1A and CP-2 inputs this case does not freeze). Each context repeats run.as_of, issuer and pathway or context_facts refuses (context.py:756-769) except `mismatch`, which breaks run.as_of on purpose.",
    "raw_rule": "context files are the literal bytes the form writes (json indent 2, LF, trailing LF); the `context` source sha256 is sha256 of those bytes, spans line:N via splitlines",
    "pattern_note": "cases/pins.py PATTERNS (cases/pins.py:20-30) do not match context-*.json or bridge.txt (M2): their sha256 is recorded below and a test re-hashes each file against it",
    "frozen_inputs": {
        **{rel: {"sha256": digest, "role": role} for (rel, digest), role in zip(
            sorted(PINS.items()),
            [
                "cases/cp4-owner/expected.json: positive.CP-4.own_limitations (the two CP-4 limitations a draft run adds to)",
                "cases/cp4-owner/manifest.json:52-86 pack_sources of the positive case (identity, financial, legal-covenants); :101-135 the gap legal source reused as legal-draft",
                "cases/cp4-owner/submissions.json: positive.readiness_review pieces, cp1_source_context, legal_covenants",
                "cases/financial/manifest.json: identity and financial pages",
                "cases/legal/manifest.json: legal pages (positive and missing-definition bytes)",
            ],
            strict=True,
        )},
        **{f"{CASE}/{cid}.json": {"sha256": CTX_SHA[cid], "role": "context file (M2: not covered by PINS PATTERNS)"} for cid in sorted(CTX_BYTES)},
        f"{CASE}/bridge.txt": {"sha256": BRIDGE_SHA, "role": "bridge source bytes (M2: not covered by PINS PATTERNS)"},
    },
    "contexts": {
        cid: {
            "file": f"{CASE}/{cid}.json",
            "sha256": CTX_SHA[cid],
            "attachments": CONTEXTS[cid]["attachments"],
            "run_as_of": CONTEXTS[cid]["run"]["as_of"],
        }
        for cid in sorted(CONTEXTS)
    },
    "cases": [
        {
            "case_id": case,
            "run": {**RUN_BASE, "run_id": f"ctxatt-{case}"},
            "context": f"{CASE}/{CTX_OF[case]}.json" if CTX_OF[case] else None,
            "pack_sources": pack_for(case),
            "paths_tested": [k for k in ("P", "V", "M") if EXPECTED_CASES[case].get(k) not in (None,)],
            "submissions": f"{CASE}/submissions.json#cases.{case}",
            "expected": f"{CASE}/expected.json#cases.{case}",
        }
        for case in CTX_OF
    ],
    "upstream_line_citations": {
        "context.py:756-769": "src/deploy_workflow/context.py context_facts pairs and `{path}: context has {theirs!r} but the run has {ours!r}` (verified at 73e254fd: pairs :756-762, problems :763-768, raise :769)",
        "contracts.py:49-51": "src/deploy_vii/contracts.py _PRESETS credit_snapshot (CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, ...)",
        "owner_workflow _gate": "src/deploy_workflow/owner_workflow.py:837-855; _PRECHECKS :625-627 holds only CP-4 today (the CP-0 row is Task 3)",
        "cp4_legal.py:476-478": "the frozen 'is not an executed or filed source (CP-0 authority ..., or the source is not ready)' row issue",
    },
    "builder": {"file": f"{CASE}/builder/build.py", "run": "python3 -I cases/context-attachments-owner/builder/build.py"},
    "files_sha256": {name: sha(data) for name, data in sorted(files.items())},
    "files_sha256_note": "every output except manifest.json; builder/build.py is pinned by cases/pins.py at the freeze step",
}
files["manifest.json"] = dumps(MANIFEST).encode("utf-8")

for name, data in files.items():
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print("wrote", len(files), "files")
