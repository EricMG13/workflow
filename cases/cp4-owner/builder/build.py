"""Writes cases/cp4-owner/{manifest,submissions,expected}.json (stdlib only).

CP-4 (legal and covenants) owner oracle. An independent transcription of the composition
rules documented in src/deploy_vii/cp4_legal.py, readiness.py and execution.py (read, never
imported or executed by this builder). Source bytes are reused unchanged from the frozen packs:
cases/financial/manifest.json (identity, financial), cases/legal/manifest.json (legal-covenants,
positive and missing-definition variants) and cases/snapshot/submissions.json (the literal CP-0
and CP-1 source_context entries for identity and financial). Every pinned file is hash-checked.

Run: python3 -I cases/cp4-owner/builder/build.py   (from the repository root)
"""

import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp4-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/legal/manifest.json": "dceee076fb74ae79685b1551fb3d35ed92355561793383f29590d90e71801d40",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
}
SOURCE_PINS = {
    "identity": "74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4",
    "financial": "82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429",
    "positive": "0f8accfde3ee2343306db00ead2aec8a15aed5bd84a22f5eb766dd859a6e70ec",
    "gap": "ec59b199fb54fd01c4533c40871031b5bbb780e0275bf8a2fdfeae664914608c",
}
for rel, want in PINS.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    if got != want:
        sys.exit(f"pinned file changed: {rel} {got} != {want}")

FIN = json.loads((ROOT / "cases/financial/manifest.json").read_text())
LEG = json.loads((ROOT / "cases/legal/manifest.json").read_text())
SNAP = json.loads((ROOT / "cases/snapshot/submissions.json").read_text())


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s)


fin_src = {s["source_id"]: s for s in FIN["sources"]}
for sid in ("identity", "financial"):
    assert page_sha([p["text"] for p in fin_src[sid]["pages"]]) == fin_src[sid]["sha256"] == SOURCE_PINS[sid]
leg_case = {c["case_id"]: c for c in LEG["cases"]}
POS_ID, GAP_ID = "legal-current-matching-definition", "legal-current-missing-ebitda-definition"
LEGAL = {"positive": leg_case[POS_ID]["legal_source"], "gap": leg_case[GAP_ID]["legal_source"]}
for k, src in LEGAL.items():
    assert page_sha([p["text"] for p in src["pages"]]) == src["sha256"] == SOURCE_PINS[k], k
RUN_T = LEG["run_template"]
PAGES = {
    "positive": {p["locator"]: p["text"] for p in LEGAL["positive"]["pages"]},
    "gap": {p["locator"]: p["text"] for p in LEGAL["gap"]["pages"]},
}
SHA = {
    "positive": {"identity": SOURCE_PINS["identity"], "financial": SOURCE_PINS["financial"], "legal-covenants": SOURCE_PINS["positive"]},
    "gap": {"identity": SOURCE_PINS["identity"], "financial": SOURCE_PINS["financial"], "legal-covenants": SOURCE_PINS["gap"]},
}
FIN_PAGES = {sid: {p["locator"]: p["text"] for p in fin_src[sid]["pages"]} for sid in ("identity", "financial")}

LIMIT_FIN = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
LEGAL_LIM = LEGAL["positive"]["limitation"]
assert LEGAL_LIM == LEGAL["gap"]["limitation"]
SYNTH = "Synthetic case; not real issuer qualification"
SCHED_LIM = "Covenant EBITDA is defined in incorporated Schedule A, which is not supplied"
SCHED_GAP = (
    "Schedule A defining Covenant EBITDA is not supplied, so its add-backs, exclusions and "
    "relationship to reported EBITDA are not stated"
)
FIG_ID = "<<FIG:net_leverage_reported>>"
FIG_PREDICATE = (
    "covenants[0].metric_ref (S1a rev 2 M2 predicate): select from head_module(CP-1).facts the facts with table_id T4.10, "
    "period 'LTM Q4 25: 2025-01-01 to 2025-12-31' and label 'LTM Q4 25 (2025-01-01 to 2025-12-31) \u00b7 net_leverage_reported'; "
    "exactly one must match (zero or several fail the test: never choose among the equal Q4 25 and FY25 aliases); then its fact_id "
    "must be a ref in the CP-4 context_block cp1_facts whose unit is 'x' and shown is '1.00x'; that fact_id is the value bound into metric_ref"
)

CASES = ("positive", "gap", "gap_false_same_definition")
PACK_CASE = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}
RUN_IDS = {
    "positive": leg_case[POS_ID]["run_id"],
    "gap": leg_case[GAP_ID]["run_id"],
    "gap_false_same_definition": leg_case[GAP_ID]["run_id"],
}
REQUESTED = ["CP-4"]
PLAN = ["CP-0", "CP-1", "CP-4"]


# --- helpers -----------------------------------------------------------------------------


def pack_page(case, sid, locator):
    pc = PACK_CASE[case]
    return FIN_PAGES[sid][locator] if sid in FIN_PAGES else PAGES[pc][locator]


def cite(case, sid, locator, quote):
    assert norm(quote) in norm(pack_page(case, sid, locator)), (case, sid, locator, quote)
    return {"source_id": sid, "source_sha256": SHA[PACK_CASE[case]][sid], "locator": locator, "quote": quote}


def q(case, locator, quote):
    """A model-facing Quote (source_id, locator, quote) of the legal source."""
    assert norm(quote) in norm(pack_page(case, "legal-covenants", locator)), (case, locator, quote)
    return {"source_id": "legal-covenants", "locator": locator, "quote": quote}


# Verbatim legal sentences (checked against the case pages when used).
ATTEST = (
    "Execution attestation: the Borrower and all lenders signed this restatement on December 30, 2025. "
    "It became effective on December 31, 2025 and remains operative without amendment or waiver "
    "through January 10, 2026."
)
BORROWER = "Clause 1.1. Borrower means Northbridge Synthetic Group, the issuer named in the Issuer identity and reporting scope note."
OMITTED = (
    "Security enforcement, guarantee coverage, events of default, cure rights, voting and other "
    "protections are not supplied; no overall lender-protection conclusion may be inferred from their absence."
)
C21 = (
    "Covenant Debt means the Group's total debt at IFRS carrying value excluding both finance and "
    "operating lease obligations, with no other exclusions or pro-forma adjustments."
)
C22 = "Covenant Net Debt means Covenant Debt less Eligible Cash; negative net debt, if any, is not floored at zero."
C23_POS = (
    "Covenant EBITDA means the Group's reported EBITDA: revenue less cost of sales less function-only "
    "operating expenses including depreciation plus depreciation and amortization, over the trailing "
    "twelve months ending on the test date."
)
C23_GAP = "Covenant EBITDA has the meaning assigned in incorporated Schedule A. Schedule A is not supplied with this copy."
C31 = (
    "The Borrower shall maintain the ratio of Covenant Net Debt to Covenant EBITDA at not more than "
    "4.00x, tested at every calendar quarter end from December 31, 2025."
)
C41A = "Existing drawings under Northbridge Term Loan are permitted."
C41B = "Additional debt or an increase in that facility's commitment requires prior written consent of every lender."
C41C = "No additional automatic debt basket is provided by these selected terms."
C51A = "Asset sales must be for fair market value."
C51B = (
    "The Borrower is not required by these selected terms to apply asset-sale proceeds to mandatory "
    "debt prepayment, and no asset-sale sweep is provided."
)
SRC_LIM = (
    "These are selected current executed terms, not a complete legal package. Obtain the omitted "
    "protections named in Clause 1.4 before rating the overall lender-protection package."
)


# --- literal submissions -----------------------------------------------------------------


def readiness_review(case):
    gap_case = PACK_CASE[case] == "gap"
    sn = SNAP["positive"]["readiness_review"]
    legal_cites = [
        cite(case, "legal-covenants", "page:1", BORROWER),
    ]
    legal_assess_limits = [LEGAL_LIM] + ([SCHED_LIM] if gap_case else [])
    cp4_limits = [LEGAL_LIM] + ([SCHED_LIM] if gap_case else [])
    legal_source = {
        "source_id": "legal-covenants",
        "document_family": "Executed term loan covenant terms",
        "authority": "executed",
        "entity": "Northbridge Synthetic Group",
        "period": "Effective December 31, 2025",
        "version_relationship": "Current restatement effective December 31, 2025, with no amendment or waiver through January 10, 2026",
        "fidelity": "verified",
        "citations": [cite(case, "legal-covenants", "page:1", ATTEST)],
        "limitations": legal_assess_limits,
    }
    cp4 = {
        "module_id": "CP-4",
        "readiness": "READY_WITH_LIMITATIONS",
        "evidence_demand": "Located executed covenant clauses, definitions, thresholds and permissions",
        "source_ids": ["legal-covenants"],
        "rationale": (
            "The covenant terms can be interpreted with explicit limits: only selected provisions are supplied"
            + ("; the incorporated EBITDA definition is not" if gap_case else "")
        ),
        "citations": legal_cites,
        "missing_source": None,
        "limitations": cp4_limits,
    }
    gaps = []
    if gap_case:
        gaps.append(
            {
                "gap_id": "schedule-a-missing",
                "kind": "source",
                "severity": "material",
                "description": SCHED_GAP,
                "affected_modules": ["CP-4"],
                "remediation": "Obtain Schedule A of the executed agreement",
                "citations": [cite(case, "legal-covenants", "page:2", C23_GAP)],
            }
        )
    analysis = [
        {
            "claim_id": "source-assessment",
            "text": "Located statements and the executed covenant terms support historical and covenant analysis with limitations.",
            "citations": [
                cite(case, "identity", "page:1", "Northbridge Synthetic Group is the issuer and consolidated group."),
                cite(case, "financial", "page:1", "Currency: USD; amounts in millions."),
                cite(case, "legal-covenants", "page:1", ATTEST),
            ],
            "limitation": LEGAL_LIM,
        }
    ]
    sources = [dict(sn["sources"][0]), dict(sn["sources"][1]), legal_source]
    cp1 = dict(sn["consumers"][0])
    assert cp1["module_id"] == "CP-1" and cp1["source_ids"] == ["identity", "financial"]
    return {
        "pack_sha256": "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>",
        "objective": "Covenant interpretation over the executed term loan terms",
        "reporting_period": "Reported FY2025, test date December 31, 2025",
        "issuer_confirmed": True,
        "sources": sources,
        "consumers": [cp1, cp4],
        "gaps": gaps,
        "analysis": analysis,
    }


def source_context(case):
    sn = SNAP["positive"]["cp1_source_context"]
    assert [s["source_id"] for s in sn["sources"][:2]] == ["identity", "financial"]
    legal = {
        "source_id": "legal-covenants",
        "classification": "nonfinancial",
        "document_type": "Executed term loan covenant terms",
        "published_on": "2025-12-30",
        "evidence_class": "lender_sponsor",
        "evidence_rationale": "Executed by the Borrower and all lenders; not audited financial evidence",
        "analytical_use": "Agreement-specific Borrower, Group perimeter, facility and covenant definitions for CP-4",
        "citations": [cite(case, "legal-covenants", "page:1", BORROWER)],
        "event_scan": "unassessed",
        "event_scan_explanation": "Covenant terms are not an event disclosure",
    }
    return {
        "pack_sha256": "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>",
        "entities": sn["entities"],
        "sources": [sn["sources"][0], sn["sources"][1], legal],
        "limitations": sn["limitations"],
    }


COVENANT_NAME = "Maximum net leverage ratio"
FORMULA = "Covenant Net Debt divided by Covenant EBITDA, tested at each calendar quarter end"
PERIOD = (
    "Every calendar quarter end from December 31, 2025; the December 31, 2025 test uses closing net debt "
    "and trailing twelve-month Covenant EBITDA on the Group perimeter"
)
DEF_POS = (
    "Covenant Net Debt is Covenant Debt less Eligible Cash, where Covenant Debt is the Group's total debt at "
    "IFRS carrying value excluding finance and operating lease obligations (Clause 2.1 and Clause 2.2); Covenant "
    "EBITDA is the Group's reported EBITDA over the trailing twelve months ending on the test date, with no "
    "adjustments, add-backs or pro-forma changes (Clause 2.3)"
)
DEF_GAP = (
    "Covenant Net Debt is Covenant Debt less Eligible Cash (Clause 2.1 and Clause 2.2); Covenant EBITDA has the "
    "meaning assigned in incorporated Schedule A, which is not supplied, so its add-backs, exclusions and "
    "relationship to reported EBITDA are not stated (Clause 2.3)"
)
LIM_POS = "Perimeter is the IFRS consolidated Group; the underlying financial statements are unaudited"


def legal_covenants(case):
    gap_pack = PACK_CASE[case] == "gap"
    basis = {"positive": "Same definition", "gap": "Not determinable", "gap_false_same_definition": "Same definition"}[case]
    false_same = case == "gap_false_same_definition"
    c23 = C23_GAP if gap_pack else C23_POS
    covenant_quotes = [q(case, "page:2", C21), q(case, "page:2", c23), q(case, "page:2", C31)]
    covenant = {
        "name": COVENANT_NAME,
        "kind": "maintenance",
        "document_id": "legal-covenants",
        "clause": "Clause 3.1",
        "definition_text": DEF_GAP if (gap_pack and not false_same) else DEF_POS,
        "test_formula": FORMULA,
        "threshold_text": "4.00x",
        "threshold_unit": "multiple",
        "threshold_value": "4.00",
        "comparison": "<=",
        "metric_ref": FIG_ID,
        "metric_basis": basis,
        "facility_ids": ["term-loan"],
        "period_scope": PERIOD,
        "citations": covenant_quotes,
        "limitation": SCHED_LIM if (gap_pack and not false_same) else LIM_POS,
    }
    documents = [
        {
            "source_id": "legal-covenants",
            "document_family": "Term loan covenant terms, current restatement",
            "governing_entity": "Northbridge Synthetic Group as Borrower, for the IFRS consolidated Group",
            "date_or_amendment": "Executed December 30, 2025; effective December 31, 2025; no amendment or waiver through January 10, 2026",
            "citations": [q(case, "page:1", ATTEST)],
            "limitation": "Selected executed terms only; security, guarantee, default, cure and voting terms are omitted",
        }
    ]
    capacity = [
        {
            "basket": "Existing term loan drawings",
            "permits": "Existing drawings under Northbridge Term Loan",
            "conditions": "None stated beyond the facility terms",
            "citations": [q(case, "page:3", C41A)],
            "limitation": None,
        },
        {
            "basket": "Additional debt or commitment increase",
            "permits": "Additional debt or an increase in the facility commitment only with the consent of every lender",
            "conditions": "Prior written consent of every lender; no automatic additional debt basket is provided",
            "citations": [q(case, "page:3", C41B), q(case, "page:3", C41C)],
            "limitation": "The maintenance ratio limit is not a debt-incurrence permission or an available funding commitment",
        },
        {
            "basket": "Asset sales",
            "permits": "Asset sales for fair market value",
            "conditions": "Fair market value; no mandatory prepayment from proceeds is required",
            "citations": [q(case, "page:3", C51A), q(case, "page:3", C51B)],
            "limitation": None,
        },
    ]
    red_flags = [
        {
            "flag": "No asset-sale prepayment sweep",
            "mechanic": "Asset-sale proceeds need not be applied to mandatory debt prepayment and no asset-sale sweep is provided",
            "implication": "Lenders have no contractual claim on disposal proceeds under the supplied terms",
            "severity": "Material",
            "citations": [q(case, "page:3", C51B)],
        },
        {
            "flag": "Omitted lender protections",
            "mechanic": "Security enforcement, guarantee coverage, default, cure and voting terms are not supplied",
            "implication": "Overall lender protection cannot be assessed from the selected terms",
            "severity": "Material",
            "citations": [q(case, "page:1", OMITTED)],
        },
    ]
    protection = {
        "rating": "Insufficient Information",
        "rationale": "Only selected executed terms are supplied; security, guarantees, defaults, cure and voting terms are omitted",
        "basis": "Clause 1.4 and the source limitation on page 3 name the omitted protections",
        "citations": [q(case, "page:1", OMITTED), q(case, "page:3", SRC_LIM)],
        "limitation": "Overall lender protection cannot be rated until the omitted protections are supplied",
    }
    omitted_gap = {
        "gap": "Security, guarantee, default, cure and voting terms are not supplied",
        "why_it_matters": "Overall lender protection cannot be rated without them",
        "affected_analysis": "Lender protection score",
        "severity": "Material",
        "action": "Obtain the omitted terms of the executed agreement",
    }
    sched_gap = {
        "gap": "Schedule A defining Covenant EBITDA is not supplied",
        "why_it_matters": "Covenant EBITDA cannot be compared with the CP-1 metric without its add-backs and exclusions",
        "affected_analysis": "Covenant tests",
        "severity": "Critical",
        "action": "Obtain Schedule A of the executed agreement",
    }
    gaps = [sched_gap, omitted_gap] if (gap_pack and not false_same) else [omitted_gap]
    return {
        "documents": documents,
        "covenants": [covenant],
        "capacity": capacity,
        "red_flags": red_flags,
        "protection_score": protection,
        "gaps": gaps,
    }


# --- own checks on the literal inputs ----------------------------------------------------

_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
LABELS = [
    re.compile(r"(?:Clause|Section|Schedule|Item|Note|Article) [0-9]{1,4}[A-Z]?(?:\.[0-9]{1,3})*"),
    re.compile(r"CP-[0-9]{1,2}[A-Z]?"),
    re.compile(_MONTH + r" [1-9][0-9]?, (?:19|20)[0-9]{2}"),
    re.compile(r"(?<![0-9A-Za-z])(?:19|20)[0-9]{2}(?![0-9A-Za-z%])"),
    re.compile(r"[Pp]ages? [0-9]{1,4}"),
    re.compile(r"(?:FY|CY) ?(?:(?:19|20)[0-9]{2}|[0-9]{2})|Q[1-4]"),
]
PROHIBITED = [
    "peer ranking", "ranks above", "ranks below", "top quartile", "best-in-class", "best in class",
    "outperforms peers", "versus peers", "relative to peers", "recommend", "buy", "sell", "overweight",
    "underweight", "preferred instrument", "recovery conclusion", "expected recovery", "recovery rate",
    "recovery estimate", "recovery value", "target price", "repaid in full",
]
PYTHON_OWNED = re.compile(
    r"(?<![A-Za-z])(?:headroom|cushion)(?![A-Za-z])|(?:in compliance|compliant|in breach|non-?compliant|has breached|have breached|has complied)",
    re.IGNORECASE,
)
ENUMS = {
    "kind": {"maintenance", "incurrence", "negative", "other"},
    "comparison": {"<=", "<", ">=", ">", "none"},
    "threshold_unit": {"multiple", "percent", "other", "not stated"},
    "metric_basis": {"Same definition", "Different definition", "Not determinable"},
    "rating": {"Strong", "Adequate", "Weak", "Insufficient Information"},
    "severity_flag": {"Critical", "Material", "Minor"},
}
KEYS = {
    "top": ["documents", "covenants", "capacity", "red_flags", "protection_score", "gaps"],
    "documents": ["source_id", "document_family", "governing_entity", "date_or_amendment", "citations", "limitation"],
    "covenants": ["name", "kind", "document_id", "clause", "definition_text", "test_formula", "threshold_text", "threshold_unit", "threshold_value", "comparison", "metric_ref", "metric_basis", "facility_ids", "period_scope", "citations", "limitation"],
    "capacity": ["basket", "permits", "conditions", "citations", "limitation"],
    "red_flags": ["flag", "mechanic", "implication", "severity", "citations"],
    "protection_score": ["rating", "rationale", "basis", "citations", "limitation"],
    "gaps": ["gap", "why_it_matters", "affected_analysis", "severity", "action"],
}
TEXT_FIELDS = {
    "documents": ["document_family", "governing_entity", "date_or_amendment", "limitation"],
    "covenants": ["name", "clause", "definition_text", "test_formula", "period_scope", "limitation"],
    "capacity": ["basket", "permits", "conditions", "limitation"],
    "red_flags": ["flag", "mechanic", "implication"],
    "protection_score": ["rationale", "basis", "limitation"],
    "gaps": ["gap", "why_it_matters", "affected_analysis", "action"],
}


def check_text(where, text):
    rest = text
    for pattern in LABELS:
        rest = pattern.sub(" ", rest)
    assert not re.search(r"[0-9]", rest), f"{where}: bare figure in {text!r}"
    low = text.lower()
    for phrase in PROHIBITED:
        assert not re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", low), f"{where}: prohibited {phrase!r}"
    assert not PYTHON_OWNED.search(text), f"{where}: compliance or headroom language in {text!r}"
    assert text.strip(), where


def check_submission(case, sub):
    assert list(sub) == KEYS["top"], case
    for name in KEYS["top"]:
        rows = sub[name] if isinstance(sub[name], list) else [sub[name]]
        for i, row in enumerate(rows):
            assert list(row) == KEYS[name], (case, name, i, list(row))
            for field in TEXT_FIELDS[name]:
                if row[field] is not None:
                    check_text(f"{case}.{name}[{i}].{field}", row[field])
            for quote in row.get("citations", []):
                assert list(quote) == ["source_id", "locator", "quote"]
                assert norm(quote["quote"]) in norm(PAGES[PACK_CASE[case]][quote["locator"]])
    cov = sub["covenants"][0]
    assert cov["kind"] in ENUMS["kind"] and cov["comparison"] in ENUMS["comparison"]
    assert cov["threshold_unit"] in ENUMS["threshold_unit"] and cov["metric_basis"] in ENUMS["metric_basis"]
    assert sub["protection_score"]["rating"] in ENUMS["rating"]
    for row in sub["red_flags"]:
        assert row["severity"] in ENUMS["severity_flag"]
    for row in sub["gaps"]:
        assert row["severity"] in ENUMS["severity_flag"]
    # threshold_text is part of a quote on the cap side (the direction check of the core)
    assert any("4.00x" in quote["quote"] and "not more than" in quote["quote"] for quote in cov["citations"])
    assert cov["document_id"] in {d["source_id"] for d in sub["documents"]}



# --- the Q1 semantic gate (LEAD ruling H2): a closed marker list frozen from the legal source ---

GATE_MARKERS = ["has the meaning assigned in", "is not supplied with this copy"]
GATE_NEVER = ["defined in", "as defined in", "incorporated"]  # documented in never_markers; never matched


def gate_norm(text):
    return re.sub(r"\s+", " ", text).casefold()


def gate_scope(case, cov):
    """Texts scanned: the covenant row's cited quotes plus the full text of every pack page it cites."""
    texts = [c["quote"] for c in cov["citations"]]
    seen = []
    for c in cov["citations"]:
        key = (c["source_id"], c["locator"])
        if key not in seen:
            seen.append(key)
            texts.append(pack_page(case, c["source_id"], c["locator"]))
    return texts


def gate_matches(case, cov):
    scope = [gate_norm(t) for t in gate_scope(case, cov)]
    return [m for m in GATE_MARKERS if any(m in t for t in scope)]


def gate_issues(case, sub):
    out = []
    for i, cov in enumerate(sub["covenants"]):
        if cov["metric_basis"] != "Same definition":
            continue
        hit = gate_matches(case, cov)
        if hit:
            out.append(GATE_ISSUE.format(i=i, markers="; ".join(f"'{m}'" for m in hit)))
    return out


GATE_ISSUE = (
    "covenants[{i}]: metric_basis 'Same definition' is refused because the cited source text "
    "matches incorporation-by-reference markers: {markers}"
)
# Provenance, frozen from the literal sources: each marker occurs on the gap legal page and in
# no positive legal page, identity page or financial page; the NEVER terms are why they are not used.
GATE_PROVENANCE = {}
for _m in GATE_MARKERS:
    _gap = [loc for loc, t in PAGES["gap"].items() if _m in gate_norm(t)]
    assert _gap == ["page:2"], (_m, _gap)
    assert not any(_m in gate_norm(t) for t in PAGES["positive"].values()), _m
    assert not any(_m in gate_norm(t) for pages in FIN_PAGES.values() for t in pages.values()), _m
    GATE_PROVENANCE[_m] = {"present_in": "gap legal source (cases/legal, missing-ebitda-definition) page:2, Clause 2.3", "absent_from": "positive legal source (all pages), identity (all pages), financial (all pages)"}
assert not any(n in GATE_MARKERS for n in GATE_NEVER)
assert any("defined in" in gate_norm(t) for t in PAGES["positive"].values())  # why 'defined in' is never a marker

# --- Python-owned arithmetic (exact Decimal, from the frozen financial oracle) ------------

DEBT, CASH, EBITDA = Decimal("50"), Decimal("20"), Decimal("30")
ORACLE_NET = FIN["q4_ltm_metric_oracle"]["net_leverage_reported"]
assert (ORACLE_NET["numerator"], ORACLE_NET["denominator"], ORACLE_NET["decimal"], ORACLE_NET["unit"]) == ("30", "30", "1", "MULTIPLE")
assert FIN["q4_ltm_derived_source_units"]["total_debt"] == "50" and FIN["q4_ltm_derived_source_units"]["ebitda"] == "30"
NET_DEBT = DEBT - CASH
METRIC = NET_DEBT / EBITDA
assert NET_DEBT == Decimal("30") and METRIC == Decimal("1")
THRESHOLD = Decimal("4.00")  # parsed from the quoted "4.00x" (a multiple is read as written)
ROOM = THRESHOLD - METRIC
SHARE = ROOM / abs(THRESHOLD)
assert ROOM == Decimal("3") and SHARE == Decimal("0.75")
COV_COMPARISON = "<="
# cp4_legal.py:338-340: room > 0, or room == 0 when the comparison is "<=" (a limit that may be met)
WITHIN = ROOM > 0 or (ROOM == 0 and COV_COMPARISON == "<=")
assert WITHIN
# Independent cross-checks that must never appear as CP-4 values (LEGAL-SOURCE-CONTRACT):
DISTANCE = 4 * EBITDA - NET_DEBT  # USD millions of net debt to the ratio limit
assert DISTANCE == Decimal("90")
UNUSED = Decimal("50") - Decimal("50")
assert UNUSED == Decimal("0")


FOUR_X = Decimal("4") * EBITDA
MUST_NOT_APPEAR = {
    "values": [str(DISTANCE), str(FOUR_X), str(UNUSED)],
    "derivations": {"90": "4 * 30 - (50 - 20)", "120": "4 * 30", "0": "50 - 50"},
    "comparison": "No numeric fact (amount) is Decimal-equal to any listed value, and no cell text equals a listed value after stripping; this is not a substring test (3.00x, 75.0% and any quoted text may contain these digits)",
}
assert FOUR_X == Decimal("120")


def check_no_forbidden(tables):
    forbidden = {Decimal(v) for v in MUST_NOT_APPEAR["values"]}
    for t in tables:
        for r in t["rows"]:
            for f in r["facts"]:
                if f.get("amount") is not None:
                    assert Decimal(f["amount"]) not in forbidden, (t["table_id"], f["fact_id"])
                if f.get("text") is not None:
                    assert f["text"].strip() not in MUST_NOT_APPEAR["values"], (t["table_id"], f["fact_id"])


def false_same_expected(case, sub, cp0):
    """Refusal expectation (LEAD ruling H1): the payload never reaches the journal."""
    issues = gate_issues(case, sub)
    assert issues == [GATE_ISSUE.format(i=0, markers="; ".join(f"'{m}'" for m in GATE_MARKERS))], issues
    return {
        "CP-0": cp0,
        "CP-4": {
            "refusal": {
                "stage": "the CP-4 core precheck(store, binding, stored) hook (docs/G1X-OWNER-CORE-PROTOCOL.md section 4) calling owners.cp4.semantic_issues, run on the filled payload before rules=journaled and before the journal (question 1 = option A)",
                "issues": issues,
                "journaled_steps": 0,
                "journal": "the refused payload is not journaled and consumes no attempt; the CP-4 ticket still has no step and the snapshot is unchanged. G1 records it in the owner-run audit (payloads/<raw sha>, payloads/<filled sha>, bindings/<binding hash>, submissions/<record hash>) and in receipt.submissions as an OwnerSubmission with disposition 'refused', issues equal to the frozen issue string, step_sha256 and step_output_sha256 null, and snapshot_after_sha256 equal to the binding snapshot; _verify_submissions replays it",
                "ticket_after": "pending (same ticket, same bindings)",
                "cp4_head_after": None,
                "receipt_after": "none for CP-4 yet: the run is not closed and no OwnerRunReceipt names a CP-4 head until the corrected resubmission settles",
                "inputs_unchanged": "the CP-0 head, the CP-1 head and the pack are untouched by the refusal",
            },
            "corrected_resubmission": {
                "submission": "gap.legal_covenants (metric_basis Not determinable, Schedule A gap row, DEF_GAP text), on the same ticket",
                "settles": "restricted CP-4 head whose tables, claims, own_limitations, settled_limitations and inherited_limitations equal expected.json gap.CP-4 exactly; headroom and share missing, T4C.9 No",
                "expected_same_as": "gap.CP-4",
                "receipt_after": "verify_owner_run_receipt verifies; exactly one CP-4 step is journaled (the corrected one); receipt.submissions holds two CP-4 records on the same ticket and binding: the refused one, then the valid one, whose call_ids include every call of the epoch made before and after the refusal",
            },
            "semantic_acceptance": {
                "result": "REFUSE_SEMANTIC_ACCEPTANCE",
                "reason": "Missing incorporated Schedule A does not establish Covenant EBITDA equivalence with the CP-1 reported EBITDA metric; no legal pass or headroom may qualify (LEGAL-SOURCE-CONTRACT)",
                "values_the_documented_rules_would_compose_from_these_inputs_and_that_must_not_qualify": {
                    "headroom": f"{ROOM.normalize()} MULTIPLE",
                    "headroom_share": f"{SHARE} PERCENT",
                    "verdict": VERDICT_WITHIN,
                    "T4C.9_calculable": "Yes",
                },
                "basis": "the documented headroom rule (threshold minus metric) applied to the same threshold and metric as the positive case (probe: the product composes these for the payload); listed only so a test can assert they never settle as qualified output; they are not an expected product result and no table of this payload is expected",
                "engine_note": "cp4_legal trusts metric_basis (LEGAL-SOURCE-CONTRACT 'current_engine_limit'); the refusal is the owner gate in semantic_gate",
            },
        },
    }


def semantic_gate_block(subs):
    per = {}
    for c in CASES:
        cov = subs[c]["legal_covenants"]["covenants"][0]
        per[c] = {
            "metric_basis": cov["metric_basis"],
            "gate_applies": cov["metric_basis"] == "Same definition",
            "markers_matched_in_scope": gate_matches(c, cov),
            "issues": gate_issues(c, subs[c]["legal_covenants"]),
            "outcome": {"positive": "passes the gate (no false positive)", "gap": "not gated (Not determinable)", "gap_false_same_definition": "refused before the journal"}[c],
        }
    assert per["positive"]["markers_matched_in_scope"] == [] and per["positive"]["issues"] == []
    assert per["gap"]["issues"] == [] and per["gap"]["markers_matched_in_scope"] == GATE_MARKERS
    assert per["gap_false_same_definition"]["issues"]
    return {
        "owner": "owners.cp4.semantic_issues(pack, submission), called from the CP-4 core precheck(store, binding, stored) hook (G1-X protocol section 4); the step keeps rules=journaled and the gate runs first; mx-adversary reviews it and this list at build",
        "markers": GATE_MARKERS,
        "provenance": GATE_PROVENANCE,
        "never_markers": {
            "defined in": "occurs in the clean positive legal page:2 ('Group perimeter defined in Clause 1.2'): would refuse a correct Same definition",
            "as defined in": "same family as 'defined in'; general cross-reference wording, not specific to an unsupplied definition",
            "incorporated": "bare word is general (incorporation language also describes ordinary cross-references); not specific to an unsupplied definition",
        },
        "match": "normalised (whitespace runs collapsed to one space) and case-folded substring",
        "scope": "the covenant row's cited quote texts plus the full text of every pack page that row cites (source_id and locator); depends only on the submission and the pack, never on which pages a participant read",
        "refuse_when": "covenants[i].metric_basis == 'Same definition' and any marker matches in scope; one issue per refused covenant, markers listed in list order",
        "issue_template": GATE_ISSUE,
        "markers_format": "matched markers in list order, each in single quotes, joined by '; '",
        "per_case": per,
        "verifier_replay": "_verify_submissions recomputes the gate for every CP-4 submission: a refused record must reproduce exactly its issues; a valid step must yield none",
        "acceptance": [
            "positive pack settles: the gate yields no issue (no false positive)",
            "gap pack (Not determinable) settles: the gate does not apply",
            "gap_false_same_definition: refused with the frozen issue string, nothing journaled, ticket pending, no CP-4 head; the corrected resubmission then settles equal to gap.CP-4",
            "tamper: build the tampered run end-to-end with the gate off (patch owners.cp4.semantic_issues to return ()), restore the gate, then verify_owner_run_receipt must refuse identity_mismatch at the gate replay and the store is unchanged",
        ],
    }


def fmt2(d):
    return str(d.quantize(Decimal("0.01")))


assert fmt2(METRIC) + "x" == "1.00x" and fmt2(ROOM) + "x" == "3.00x"
assert str((SHARE * 100).quantize(Decimal("0.1"))) + "%" == "75.0%"

REASON_NOT_DET = "Whether the covenant definition is the CP-1 metric's is not determinable"
CAPACITY_NOT_CALCULATED = (
    "Basket capacity amounts are not calculated: CP-4 quotes and interprets baskets in M8"
)
CAPACITY_REASON = CAPACITY_NOT_CALCULATED + "; unknown capacity is not zero"
assert CAPACITY_REASON == LEG["cases"][0]["expected"]["capacity_reason"]
VERDICT_WITHIN = "Within threshold on the CP-1 metric"
NOT_CALCULABLE = "Not calculable"
COMPARISON_TEXT = "Not more than"  # comparison "<="


# --- composition (transcribed from cp4_legal.py) -----------------------------------------


def trace(cites):
    out = []
    for c in cites:
        s = f"{c['source_id']} {c['locator']}"
        if s not in out:
            out.append(s)
    return "; ".join(out)


def cites_of(row):
    return [[c["source_id"], c["locator"]] for c in row.get("citations", [])]


def tx(text, cites=None, judged=False, column=None):
    return {"text": text, "status": "known", "cites": cites or [], "value_class": "analyst_judgment" if judged else None, "limitation": None}


def gapcell(reason, status="missing"):
    return {"text": None, "status": status, "cites": [], "value_class": None, "limitation": reason}


def said(text, row=None):
    return tx(text, cites_of(row) if row is not None else [], judged=True)


def limit(row):
    return tx(row["limitation"] if row.get("limitation") else "None stated")


def trace_cell(row):
    cites = cites_of(row)
    return tx(trace(row.get("citations", [])) or "No located evidence", cites)


REGISTERS = [
    ("T4.2", "Document register", "Source ID|Document family|Authority|Governing entity|Date / amendment|Source trace|Limitation"),
    ("T4.3", "Covenant register", "Covenant|Kind|Clause|Governing document|Period scope|Facilities|Source trace|Limitation"),
    ("T4.9", "Covenant tests and headroom", "Covenant|Test formula|Threshold|Comparison|CP-1 metric|Current|Headroom|Headroom share|Test on CP-1 metric"),
    ("T4.10", "Capacity and baskets", "Basket|Permits|Conditions|Capacity amount|Source trace|Limitation"),
    ("T4.11", "Red flags", "Flag|Severity|Mechanic|Implication|Source trace"),
    ("T4.12", "CP-4 gaps ledger", "Gap ID|Gap|Why it matters|Severity|Action"),
    ("T4.13", "Lender protection score", "Rating|Rationale|Basis|Source trace|Limitation"),
    ("T4C.2", "Maintenance covenants", "Covenant|Test formula|Threshold|Period scope|Facilities"),
    ("T4C.3", "Incurrence covenants", "Covenant|Test formula|Threshold|Period scope|Facilities"),
    ("T4C.4", "Negative covenants", "Covenant|Clause|Facilities|Source trace"),
    ("T4C.5", "Other covenants", "Covenant|Clause|Facilities|Source trace"),
    ("T4C.6", "Covenant definitions", "Covenant|Definition|Source trace"),
    ("T4C.7", "Threshold check", "Covenant|Threshold text|Unit|Stated value|Parsed value|Comparison"),
    ("T4C.8", "CP-1 metric binding", "Covenant|CP-1 metric|Metric period|Definition basis|Unit"),
    ("T4C.9", "Headroom calculability", "Covenant|Calculable|Reason"),
    ("T4C.11", "Covenant-to-facility map", "Covenant|Facility ID|Facility"),
    ("T4C.12", "Facility coverage", "Facility ID|Facility|Covenants|Status"),
    ("T4D.1", "Pack legal source eligibility", "Source ID|CP-0 authority|Eligible for CP-4 citation|Cited by CP-4|Limitation"),
    ("T4D.2", "Governing entities", "Source ID|Governing entity|Source trace"),
    ("T4D.3", "Dates and amendments", "Source ID|Date / amendment|Source trace"),
    ("T4D.4", "Document quotations", "Quotation|Source|Locator|Quote"),
    ("T4D.5", "Document limitations", "Source ID|Limitation"),
    ("T4D.6", "Capacity conditions", "Basket|Conditions|Source trace"),
    ("T4D.7", "Red flag implications", "Flag|Implication|Severity"),
    ("T4D.8", "Covenants by governing document", "Source ID|Covenants"),
    ("T4F.1", "CP-4 input status", "Input|Status|SHA-256|Note"),
    ("T4F.2", "CP-1 figures referenced", "Value"),
    ("T4F.3", "Headroom calculation trace", "Covenant|Formula|Threshold operand|Metric operand|Result"),
    ("T4F.4", "Protection score basis", "Rating|Basis|Source trace"),
    ("T4F.5", "Inherited CP-1 gaps", "Gap ID|Gap"),
    ("T4F.6", "CP-4 source trace", "Row|Source|Locator|Quote"),
]
UNKEYED = {"T4.13", "T4F.2"}
NONEMPTY = {"T4.2", "T4.3"}
assert len(REGISTERS) == 31


def fields_of(columns):
    labels = columns.split("|")
    return [(re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_"), label) for label in labels]


class Composer:
    def __init__(self):
        self.tables = {}
        self.limitations = []

    def table(self, table_id, rows, empty=None):
        _, title, columns = next(r for r in REGISTERS if r[0] == table_id)
        cols = fields_of(columns)
        keyed = table_id not in UNKEYED
        body_cols = cols[1:] if keyed else cols
        if not rows:
            if table_id in NONEMPTY:
                reason = f"No {title.lower()} rows in the CP-4 submission"
                cell = gapcell(reason, "missing")
                self.limitations.append(reason)
            else:
                cell = gapcell(empty or f"None in the CP-4 submission ({title.lower()})", "not_applicable")
            header = [tx("None")] if keyed else []
            rows = [("none", header + [dict(cell) for _ in body_cols])]
        out_rows = []
        for position, (row_id, cells) in enumerate(rows, 1):
            body = cells[1:] if keyed else cells
            assert len(body) == len(body_cols), (table_id, row_id)
            label = (cells[0]["text"] if keyed else None) or f"{title} {position}"
            facts = []
            for (field, column), cell in zip(body_cols, body, strict=True):
                fact = {"fact_id": f"{table_id}.{row_id}.{field}", "column": column}
                fact.update(cell)
                facts.append(fact)
            out_rows.append({"row_id": row_id, "label": label, "facts": facts})
        self.tables[table_id] = {
            "table_id": table_id,
            "title": title,
            "row_header": cols[0][1] if keyed else None,
            "columns": [{"field": f, "label": l} for f, l in body_cols],
            "rows": out_rows,
        }


def numbered(rows):
    return [(f"r{i:02d}", cells) for i, cells in enumerate(rows, 1)]


LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31) \u00b7 net_leverage_reported"


def metric_current_cell(coord_note):
    """T4.9 Current: carries label, period, basis, calculation_id and citations of the CP-1 fact,
    never its fact id (the id is in T4C.8, T4F.2, T4F.3 metric_operand and the headroom formula)."""
    return {
        "carries_cp1_fact": {
            "label": LTM_LABEL + " (bound from the CP-1 fact)",
            "calculation_id": "bound from the CP-1 fact",
        },
        "carries_cp1_fact_id": False,
        "amount": str(METRIC),
        "unit": "MULTIPLE",
        "status": "known",
        "value_class": "calculated",
        "period": "bound from the CP-1 fact (LTM Q4 25: 2025-01-01 to 2025-12-31)",
        "basis": "bound from the CP-1 fact (IFRS · consolidated group)",
        "cites": "the CP-1 fact's own citations (bound at run time)",
        "limitation": None,
        "note": coord_note,
    }


def metric_copy_cell(coord_note):
    return {
        "copy_of_cp1_fact": FIG_ID,
        "amount": str(METRIC),
        "unit": "MULTIPLE",
        "status": "known",
        "value_class": "calculated",
        "period": "bound from the CP-1 fact (LTM Q4 25: 2025-01-01 to 2025-12-31)",
        "basis": "bound from the CP-1 fact (IFRS · consolidated group)",
        "cites": "the CP-1 fact's own citations (bound at run time)",
        "limitation": None,
        "note": coord_note,
    }


def compose(case, sub):
    gap_pack = PACK_CASE[case] == "gap"
    cov = sub["covenants"][0]
    out = Composer()
    # The CP-0 authority classes the literal readiness review gives (T3), pack order.
    authority = {"identity": "issuer", "financial": "issuer", "legal-covenants": "executed"}
    pack_lims = {"identity": None, "financial": LIMIT_FIN, "legal-covenants": LEGAL_LIM}
    legal = ["legal-covenants"]
    facilities = {"term-loan": "Northbridge Term Loan"}
    basis = cov["metric_basis"]
    # the test (cp4_legal._test)
    reason = None
    if basis == "Different definition":
        reason = "The covenant definition differs from the CP-1 metric"
    elif basis == "Not determinable":
        reason = REASON_NOT_DET
    calculable = reason is None
    gaps = sub["gaps"]
    for g in gaps:
        out.limitations.append(f"Gap ({g['severity']}): {g['gap']}")
    # --- documents
    docs = sub["documents"]
    out.table("T4.2", numbered([[tx(d["source_id"]), said(d["document_family"], d), tx(authority[d["source_id"]]), said(d["governing_entity"], d), said(d["date_or_amendment"], d), trace_cell(d), limit(d)] for d in docs]))
    cited = {c["source_id"] for _, row in iter_rows(sub) for c in row.get("citations", [])}
    out.table("T4D.1", numbered([[tx(sid), tx(authority.get(sid, "not assessed by CP-0")), tx("Yes" if sid in legal else "No"), tx("Yes" if sid in cited else "No"), tx(pack_lims[sid] or "None stated")] for sid in ("identity", "financial", "legal-covenants")]))
    out.table("T4D.2", numbered([[tx(d["source_id"]), said(d["governing_entity"], d), trace_cell(d)] for d in docs]))
    out.table("T4D.3", numbered([[tx(d["source_id"]), said(d["date_or_amendment"], d), trace_cell(d)] for d in docs]))
    quotations = [(c, d) for d in docs for c in d["citations"]]
    out.table("T4D.4", numbered([[tx(f"Quotation {i}"), tx(c["source_id"]), tx(c["locator"]), tx(c["quote"], [[c["source_id"], c["locator"]]])] for i, (c, _) in enumerate(quotations, 1)]))
    out.table("T4D.5", numbered([[tx(d["source_id"]), limit(d)] for d in docs]))
    out.table("T4D.8", numbered([[tx(d["source_id"]), tx("; ".join(c["name"] for c in sub["covenants"] if c["document_id"] == d["source_id"]) or "None")] for d in docs]))
    # --- covenants
    covs = sub["covenants"]
    fac_cell = lambda c: tx("; ".join(f"{i} ({facilities.get(i) or 'name not stated'})" for i in c["facility_ids"]) or "None named")
    thr = lambda c: tx(c["threshold_text"], cites_of(c))
    out.table("T4.3", numbered([[said(c["name"], c), tx(c["kind"]), said(c["clause"], c), tx(c["document_id"]), said(c["period_scope"], c), fac_cell(c), trace_cell(c), limit(c)] for c in covs]))
    if calculable:
        headroom = {
            "fact_id_template": "T4.9.r01.headroom",
            "amount": str(ROOM),
            "unit": "MULTIPLE",
            "status": "known",
            "value_class": "calculated",
            "formula": "4.00 (threshold) - <metric fact_id>",
            "period": "= the metric's period",
            "basis": "= the metric's basis",
            "cites": "the covenant row's quote citations, then the CP-1 fact's own citations (de-duplicated)",
            "limitation": None,
        }
        share = {
            "amount": str(SHARE),
            "unit": "PERCENT",
            "status": "known",
            "value_class": "calculated",
            "formula": "headroom / |threshold|",
            "period": "= the metric's period",
            "basis": "= the metric's basis",
            "cites": "as headroom",
            "limitation": None,
        }
        verdict = tx(VERDICT_WITHIN if WITHIN else "Outside threshold on the CP-1 metric")
    else:
        why = f"{NOT_CALCULABLE}: {reason}"
        headroom, share, verdict = gapcell(why), gapcell(why), tx(NOT_CALCULABLE)
    t9 = [[said(covs[0]["name"], covs[0]), said(covs[0]["test_formula"], covs[0]), thr(covs[0]), tx(COMPARISON_TEXT), tx("net_leverage_reported"), metric_current_cell("T4.10 net_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31"), headroom, share, verdict]]
    out.table("T4.9", numbered(t9))
    if not calculable:
        out.limitations.append(f"Headroom not calculable for {covs[0]['name']}: {reason}")
    for tid, kind in (("T4C.2", "maintenance"), ("T4C.3", "incurrence")):
        out.table(tid, [(f"r{i:02d}", [said(c["name"], c), said(c["test_formula"], c), thr(c), said(c["period_scope"], c), fac_cell(c)]) for i, c in enumerate(covs, 1) if c["kind"] == kind])
    for tid, kind in (("T4C.4", "negative"), ("T4C.5", "other")):
        out.table(tid, [(f"r{i:02d}", [said(c["name"], c), said(c["clause"], c), fac_cell(c), trace_cell(c)]) for i, c in enumerate(covs, 1) if c["kind"] == kind])
    out.table("T4C.6", numbered([[said(c["name"], c), said(c["definition_text"], c), trace_cell(c)] for c in covs]))
    out.table("T4C.7", numbered([[said(c["name"], c), thr(c), tx(c["threshold_unit"]), tx(c["threshold_value"] or "None stated"), tx(str(THRESHOLD)), tx(COMPARISON_TEXT)] for c in covs]))
    out.table("T4C.8", numbered([[said(c["name"], c), tx(FIG_ID + " (the bound CP-1 fact id)"), tx("LTM Q4 25: 2025-01-01 to 2025-12-31 (bound from the CP-1 fact)"), tx(c["metric_basis"]), tx("MULTIPLE")] for c in covs]))
    out.table("T4C.9", numbered([[said(c["name"], c), tx("Yes" if calculable else "No"), tx(reason or "Threshold, metric and definition basis are all present")] for c in covs]))
    pairs = [(c, i) for c in covs for i in c["facility_ids"]]
    out.table("T4C.11", numbered([[said(c["name"], c), tx(i), tx(facilities.get(i) or "None stated")] for c, i in pairs]))
    out.table("T4C.12", numbered([[tx(i), tx(name or "None stated"), tx("; ".join(c["name"] for c, j in pairs if j == i) or "None"), tx("Named by a covenant" if any(j == i for _, j in pairs) else "No covenant names this facility")] for i, name in facilities.items()]))
    out.table("T4F.3", numbered([[said(c["name"], c), tx("threshold minus metric"), tx(str(THRESHOLD)), tx(FIG_ID + " (the bound CP-1 fact id)"), tx(("3.00 (Decimal equal to 3; exponent follows the CP-1 amount)" if calculable else f"{NOT_CALCULABLE}: {reason}"))] for c in covs]))
    # --- judgments
    caps = sub["capacity"]
    amount = gapcell(CAPACITY_REASON)
    out.table("T4.10", numbered([[said(b["basket"], b), said(b["permits"], b), said(b["conditions"], b), dict(amount), trace_cell(b), limit(b)] for b in caps]))
    if caps:
        out.limitations.append(CAPACITY_NOT_CALCULATED)
    out.table("T4D.6", numbered([[said(b["basket"], b), said(b["conditions"], b), trace_cell(b)] for b in caps]))
    flags = sub["red_flags"]
    out.table("T4.11", numbered([[said(f["flag"], f), tx(f["severity"]), said(f["mechanic"], f), said(f["implication"], f), trace_cell(f)] for f in flags]))
    out.table("T4D.7", numbered([[said(f["flag"], f), said(f["implication"], f), tx(f["severity"])] for f in flags]))
    score = sub["protection_score"]
    out.table("T4.13", [("rating", [tx(score["rating"]), said(score["rationale"], score), said(score["basis"], score), trace_cell(score), limit(score)])])
    out.table("T4F.4", [("rating", [tx(score["rating"]), said(score["basis"], score), trace_cell(score)])])
    out.table("T4.12", numbered([[tx(f"CP-4-GAP-{i:03d}"), said(g["gap"]), said(g["why_it_matters"]), tx(g["severity"]), said(g["action"])] for i, g in enumerate(gaps, 1)]))
    # --- inputs
    out.table("T4F.1", [(iid.lower(), [tx(iid), tx(status), tx("<<bound at run time: the head's result_sha256>>"), tx(note)]) for iid, status, note in (("prepared-pack", "accepted", "The prepared pack"), ("CP-0", "restricted", "Source authority classes (T3)"), ("CP-1", "restricted", "Facility register and figure catalogue"))])
    out.table("T4F.5", [("r01..rN", [tx("CP-1-GAP-001..NNN"), tx("<<CP-1 head: its limitations then its inherited_limitations, de-duplicated, in head order; bound at run time>>")])])
    traced = [(path, c) for path, row in iter_rows(sub) for c in row.get("citations", [])]
    out.table("T4F.6", numbered([[tx(path), tx(c["source_id"]), tx(c["locator"]), tx(c["quote"], [[c["source_id"], c["locator"]]])] for path, c in traced]))
    # T4F.2: the referenced CP-1 figure copy
    ref = {
        "table_id": "T4F.2",
        "title": "CP-1 figures referenced",
        "row_header": "CP-1 figure",
        "columns": [{"field": "value", "label": "Value"}],
        "rows": [
            {
                "row_id": "ref01",
                "label": "net_leverage_reported · LTM Q4 25: 2025-01-01 to 2025-12-31 (row label, then the CP-1 period)",
                "facts": [dict(metric_copy_cell("T4.10 net_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31"), fact_id="the CP-1 fact's own fact_id (preserved)", column="Value")],
            }
        ],
    }
    out.tables["T4F.2"] = ref
    order = [r[0] for r in REGISTERS]
    tables = [out.tables[t] for t in order]
    # claims
    claims = [{"claim_id": f"red_flags.r{i:02d}", "text": f"{f['flag']}. Mechanic: {f['mechanic']} Implication: {f['implication']}", "cites": cites_of(f), "limitation": None} for i, f in enumerate(flags, 1)]
    claims.append({"claim_id": "protection_score", "text": f"Lender protection {score['rating']}: {score['rationale']}", "cites": cites_of(score), "limitation": score["limitation"]})
    own = list(dict.fromkeys(out.limitations))
    settled = list(dict.fromkeys([*own, SYNTH]))
    return {"tables": tables, "claims": claims, "own_limitations": own, "settled_limitations": settled}


def iter_rows(sub):
    for name in KEYS["top"]:
        value = sub[name]
        if isinstance(value, dict):
            yield name, value
        else:
            for i, row in enumerate(value):
                yield f"{name}[{i}]", row


def cp0_expected(case):
    gap_case = PACK_CASE[case] == "gap"
    rev = readiness_review(case)
    pack_lims = [LIMIT_FIN, LEGAL_LIM]
    lims = list(pack_lims)
    for a in rev["sources"]:
        lims += a["limitations"]
    for c in rev["consumers"]:
        lims += c["limitations"]
    lims += [g["description"] for g in rev["gaps"]]
    lims.append(SYNTH)
    limitations = list(dict.fromkeys(lims))
    t8 = {}
    for c in rev["consumers"]:
        cl = list(c["limitations"])
        for sid in ("identity", "financial", "legal-covenants"):
            if sid in c["source_ids"]:
                if dict(zip(("identity", "financial", "legal-covenants"), (None, LIMIT_FIN, LEGAL_LIM)))[sid]:
                    cl.append(dict(zip(("identity", "financial", "legal-covenants"), (None, LIMIT_FIN, LEGAL_LIM)))[sid])
                cl += next(a for a in rev["sources"] if a["source_id"] == sid)["limitations"]
        cl += [g["description"] for g in rev["gaps"] if c["module_id"] in g["affected_modules"]]
        t8[c["module_id"]] = {
            "candidate_command": "Run " + c["module_id"],
            "exact_command": "Run " + c["module_id"],
            "sources": ", ".join(c["source_ids"]),
            "limits": "; ".join(dict.fromkeys(cl)) or "None identified",
            "upstream": "CP-0 " + RUN_IDS[case] + "; analytical dependencies checked separately",
        }
    return {
        "status": "restricted",
        "why": "own limitations are non-empty (readiness.py:518-531; execution.py:451-457)",
        "live_consumers": ["CP-1", "CP-4"],
        "plan_order": PLAN,
        "T3_authority": {"identity": "issuer", "financial": "issuer", "legal-covenants": "executed"},
        "T8": t8,
        "limitations": limitations,
        "legal_sources_for_cp4": ["legal-covenants"],
        "gap": rev["gaps"],
    }


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pack_sources(case):
    pc = PACK_CASE[case]
    return [
        {"source_id": "identity", "name": fin_src["identity"]["name"], "status": "ready", "sha256": SOURCE_PINS["identity"], "limitation": None, "origin": "cases/financial/manifest.json#sources[identity]"},
        {"source_id": "financial", "name": fin_src["financial"]["name"], "status": "ready", "sha256": SOURCE_PINS["financial"], "limitation": LIMIT_FIN, "origin": "cases/financial/manifest.json#sources[financial]; limitation per tests/test_financial_workflow.py:22, 48-52"},
        {"source_id": "legal-covenants", "name": LEGAL[pc]["name"], "status": "ready", "sha256": SOURCE_PINS[pc], "limitation": LEGAL[pc]["limitation"], "origin": f"cases/legal/manifest.json#cases[{POS_ID if pc == 'positive' else GAP_ID}].legal_source"},
    ]


def main():
    subs = {c: {"readiness_review": readiness_review(c), "cp1_source_context": source_context(c), "legal_covenants": legal_covenants(c)} for c in CASES}
    for c in CASES:
        check_submission(c, subs[c]["legal_covenants"])
    # the gap submission and the false-same submission differ only where the false judgment is made
    assert subs["gap"]["readiness_review"] == subs["gap_false_same_definition"]["readiness_review"]

    submissions = {
        "schema_version": "cp4-owner-submissions/1",
        "note": "Literal analyst inputs only. Every number CP-4 shows is Python's (cp4_legal): the threshold is parsed from the quote, the headroom is threshold minus the bound CP-1 metric, the verdict follows. Run-time placeholders are listed in `run_time_bindings`.",
        "frozen_inputs": {rel: PINS[rel] for rel in PINS},
        "run_time_bindings": {
            "<<PACK_SHA256...>>": "PreparedPack.content_hash() of the case pack (CP-0 and CP-1 source_context pack_sha256)",
            FIG_ID: FIG_PREDICATE,
        },
        "cp1_later_stages": "CP-1 financials, narrative, readiness and quality are the financial case's literal submissions of tests/test_financial_workflow.py, unchanged except for the bound pack (as cases/snapshot); they are not restated here",
        "positive": subs["positive"],
        "gap": subs["gap"],
        "gap_false_same_definition": {
            "readiness_review": "= gap.readiness_review",
            "cp1_source_context": "= gap.cp1_source_context",
            "legal_covenants": subs["gap_false_same_definition"]["legal_covenants"],
            "purpose": "Adversarial: the exact gap pack with an incorrect Same definition judgment, its offered comparator, no Schedule A gap and a definition_text that asserts equivalence. Must be REFUSED for semantic acceptance (see expected.json).",
        },
    }
    # the false-same case shares CP-0 and CP-1 inputs with the gap case
    assert subs["gap"]["cp1_source_context"] == subs["gap_false_same_definition"]["cp1_source_context"]

    cases_manifest = []
    for c in CASES:
        pc = PACK_CASE[c]
        run = {k: RUN_T[k] for k in ("issuer_id", "issuer_name", "as_of", "method_version", "case_kind", "pathway")}
        run = {"run_id": RUN_IDS[c], **run, "requested_modules": REQUESTED}
        entry = {
            "case_id": {"positive": POS_ID, "gap": GAP_ID, "gap_false_same_definition": GAP_ID + "+false-same-definition"}[c],
            "run": run,
            "pack_sources": pack_sources(c),
            "legal_source_pointer": f"cases/legal/manifest.json#cases[{POS_ID if pc == 'positive' else GAP_ID}].legal_source",
            "plan_order": PLAN,
            "submissions": f"cases/cp4-owner/submissions.json#{c}",
            "expected": f"cases/cp4-owner/expected.json#{c}",
        }
        if c == "gap_false_same_definition":
            entry["note"] = "Same pack and run as the gap case; a separate execution that submits the adversarial legal_covenants payload. Not a second source."
        cases_manifest.append(entry)

    manifest = {
        "schema_version": "cp4-owner-cases/1",
        "scope": "CP-4 (legal and covenants) owner-run inputs: CP-0 -> CP-1 -> CP-4 over the frozen identity and financial sources plus the frozen positive or missing-definition legal source. No new source bytes; no source is edited.",
        "status": "Preparation draft by cp4-owner (2026-10-28), pre-review; not executed against product code beyond the probes named in the preparation report",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json and cases/legal/manifest.json)",
        "frozen_inputs": {rel: {"sha256": PINS[rel]} for rel in PINS},
        "sources": {
            "identity": {"sha256": SOURCE_PINS["identity"], "pointer": "cases/financial/manifest.json#sources[identity]"},
            "financial": {"sha256": SOURCE_PINS["financial"], "pointer": "cases/financial/manifest.json#sources[financial]"},
            "legal-covenants (positive)": {"sha256": SOURCE_PINS["positive"], "pointer": f"cases/legal/manifest.json#cases[{POS_ID}].legal_source"},
            "legal-covenants (missing definition)": {"sha256": SOURCE_PINS["gap"], "pointer": f"cases/legal/manifest.json#cases[{GAP_ID}].legal_source"},
        },
        "pack_rule": "Source(source_id, name, status ready, sha256, spans = the pages, extraction_status complete, limitation) with no media_type, exactly as tests/test_financial_workflow.py make_pack builds identity and financial; the legal source adds the frozen case limitation. One legal source per pack, never both variants.",
        "requested_modules": "[CP-4]: the owner run selects CP-4 alone (plan CP-0, CP-1, CP-4). The frozen legal run_template names (CP-4, CP-5); CP-5 has no owner spec in G1 and no integrity scope for CP-4 (D3), so it is a later delta (see the lease draft, question 2)",
        "cases": cases_manifest,
        "consumers_of_cp4_for_this_plan": [],
        "consumers_note": "Registry edges name CP-3, CP-3C, CP-4C and CP-5 as consumers of CP-4; none is in this plan. CP-5 would sit after CP-4 once selected and once a lease extends its integrity scope to CP-4.",
    }

    exp_cases = {}
    for c in CASES:
        sub = subs[c]["legal_covenants"]
        comp = compose(c, sub)
        gap_pack = PACK_CASE[c] == "gap"
        false_same = c == "gap_false_same_definition"
        cp0 = cp0_expected(c)
        if not false_same:
            check_no_forbidden(comp["tables"])
        if false_same:
            exp_cases[c] = false_same_expected(c, sub, cp0)
            continue
        base = {
            "CP-0": cp0,
            "CP-4": {
                "status": "restricted",
                "why": "own limitations are non-empty and case_kind is synthetic (execution.py:441-457)",
                "attempt_inputs_in_order": ["prepared-pack", "CP-0", "CP-1"],
                "settled_module_inputs": ["prepared-pack", "CP-0", "CP-1", "covenant-interpretation-submission"],
                "tables": comp["tables"],
                "claims": comp["claims"],
                "own_limitations": comp["own_limitations"],
                "settled_limitations": comp["settled_limitations"],
                "inherited_limitations": {
                    "rule": "execution.py:345-366 over the bound inputs in order: CP-0 head (limitations then inherited), then CP-1 head (limitations then inherited_limitations); de-duplicated; own findings removed",
                    "literal_head_from_CP-0": cp0["limitations"],
                    "then": "CP-1 head: its limitations then its inherited_limitations (bound at run time)",
                },
                "figures_referenced": [{"cp1_coordinate": "T4.10 net_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31", "unit_token": "x", "shown": "1.00x"}],
            },
        }
        if c == "positive":
            base["CP-4"]["python_values"] = {
                "net_debt_USDm": {"derivation": "50 - 20", "value": "30", "unit": "USD millions", "period": "2025-12-31 closing", "entity": "Northbridge Synthetic Group (IFRS consolidated group)", "source": "financial page:4; legal Clause 2.1 and Clause 2.2", "role": "source context only: CP-4 does not recompute it"},
                "metric_net_leverage_reported": {"derivation": "30 / 30", "value": "1", "unit": "MULTIPLE", "period": "trailing twelve months 2025-01-01 to 2025-12-31", "display": "1.00x", "source": "cases/financial/manifest.json q4_ltm_metric_oracle.net_leverage_reported"},
                "threshold": {"derivation": "parsed from the quote '4.00x' (a multiple is read as written)", "value": "4.00", "unit": "multiple", "comparison": "<=", "display": "4.00x"},
                "headroom": {"derivation": "4.00 - 1 (threshold minus metric, maximum test)", "value": "3", "unit": "MULTIPLE", "display": "3.00x", "decimal_note": "string form follows the exponent of the CP-1 amount; compare as Decimal == 3"},
                "headroom_share": {"derivation": "3 / |4.00|", "value": "0.75", "unit": "PERCENT", "display": "75.0%", "note": "stored as a fraction; displayed x100 with one decimal"},
                "within": {"derivation": "headroom > 0", "value": True, "verdict": VERDICT_WITHIN},
                "T4C.9_calculable": "Yes",
            }
        else:
            base["CP-4"]["python_values"] = {
                "metric_net_leverage_reported": {"value": "1", "unit": "MULTIPLE", "display": "1.00x", "role": "comparator named so the definition-specific reason is exercised; no legal equivalence"},
                "threshold": {"value": "4.00", "unit": "multiple", "comparison": "<=", "display": "4.00x"},
                "headroom": None,
                "headroom_share": None,
                "verdict": NOT_CALCULABLE,
                "T4C.9_calculable": "No",
                "reason": REASON_NOT_DET,
                "must_not_appear": ["within threshold", "outside threshold", "zero headroom", "3.00x as legal headroom", "75.0% as legal headroom", "90 as legal debt capacity", "reported EBITDA substituted for the missing Covenant EBITDA definition"],
            }
        base["CP-4"]["source_context_only"] = {
            "arithmetic_distance_to_ratio_limit_USDm": {"derivation": "4 * 30 - (50 - 20)", "value": "90", "unit": "USD millions of net debt"},
            "unused_commitment_USDm": {"derivation": "50 - 50", "value": "0", "unit": "USD millions", "source": "financial page:5; legal Clause 1.3"},
            "rule": "Neither figure is a CP-4 output cell. The 90 is not legal debt permission, capacity or funding; the 0 is not the unknown basket capacity. Capacity amount is missing (null, not zero) with the reason below. Unanimous lender consent is required for additional debt or a commitment increase.",
            "capacity_amount": None,
            "capacity_reason": CAPACITY_REASON,
            "must_not_appear_as_cell_values": MUST_NOT_APPEAR,
        }
        base["CP-4"]["semantic_acceptance"] = {
            "result": "ACCEPT_SEMANTICS",
            "positive_basis": "Clause 2.1, Clause 2.2 and Clause 2.3 define the debt, cash and EBITDA terms on the Group perimeter and match the CP-1 reported-EBITDA metric's recipe and basis"
            if c == "positive"
            else "metric_basis Not determinable is the correct judgment: Clause 2.3 incorporates a Schedule A that is not supplied",
            "gate": "positive: semantic_gate matches no marker, the payload passes (no false positive)" if c == "positive" else "gap: metric_basis is Not determinable, so semantic_gate does not apply",
        }
        exp_cases[c] = base

    # FP04 rendering and consumption (shared across cases; per-case cells named)
    sections = {
        "covenant-tests-headroom": ["T4.9"],
        "capacity": ["T4.10"],
        "red-flags": ["T4.11"],
        "lender-protection-score": ["T4.13"],
        "ebitda-definition": ["T4C.6"],
        "documents-structure": ["T4.2", "T4C.12"],
    }
    evidence = ["T4.3", "T4C.2", "T4C.3", "T4C.4", "T4C.5", "T4C.7", "T4C.8", "T4C.11", "T4D.1", "T4D.2", "T4D.3", "T4D.4", "T4D.6", "T4D.7", "T4D.8", "T4F.2", "T4F.3", "T4F.4", "T4F.6"]
    limitations_rail = ["T4.12", "T4C.9", "T4D.5", "T4F.1", "T4F.5"]
    assert sorted(evidence + limitations_rail + [t for v in sections.values() for t in v]) == sorted(r[0] for r in REGISTERS)
    render = {
        "pathway": "covenant_refinancing",
        "sections": {k: {"owner": "CP-4", "kind": "dense", "tables": v, "source": "report_view._COVENANT_REFINANCING; bindings/cp4.py"} for k, v in sections.items()},
        "evidence_rail_tables": evidence,
        "limitations_rail_tables": limitations_rail,
        "other_five_sections": "liquidity-runway (CP-2D), maturity-wall (CP-2D), funding-gap (CP-2D), refinancing-paths (CP-3C), lme-creditor-exposure (CP-3C) are served by the CP-2D and CP-3C D7 _Spec rows: in a run that does not request the owner each renders that owner's empty state ('Not run: <owner> was not requested in this run.'), as pinned in cases/legal/render-expected.json other_front_sections.blocks; they are no longer owner Unbound.",
        "displayed_literals": {
            "positive": {"T4.9": {"threshold": "4.00x", "comparison": "Not more than", "current": "1.00x", "headroom": "3.00x", "headroom_share": "75.0%", "test_on_cp_1_metric": VERDICT_WITHIN}, "T4.10": {"capacity_amount": "gap spelling, a G# gap id (never 0)"}, "T4.13": {"rating": "Insufficient Information"}},
            "gap": {"T4.9": {"threshold": "4.00x", "comparison": "Not more than", "current": "1.00x", "headroom": "gap spelling (G#)", "headroom_share": "gap spelling (G#)", "test_on_cp_1_metric": NOT_CALCULABLE}, "T4C.6": {"definition": "names the missing incorporated Schedule A"}, "T4.10": {"capacity_amount": "gap spelling, a G# gap id (never 0)"}, "T4.13": {"rating": "Insufficient Information"}},
            "method": "display.py spelling (MULTIPLE two decimals, PERCENT fraction x100 one decimal) per cases/legal/render-expected.json independent_display_literals; G# numbers sequential in fact order, not literal",
        },
        "limitations_rail_module_limitations": "Module.limitations of the settled CP-4 head (own_limitations plus the synthetic limitation), then the inherited list",
        "model_blocks": "none for CP-4 (no CP-MODEL in this plan)",
    }
    tool_use = {
        "CP-0": "pack tools (search_pack, read_pages) plus submit; reads legal-covenants page:1 and page:2 (gap case) for the cited quotes",
        "CP-1 source_context": "read_pages identity page:1, financial page:1 and legal-covenants page:1 (every page the source_context literal cites; the legal one is the Clause 1.1 quote); no search required (event_scan unassessed)",
        "CP-4 legal_covenants": {
            "session": "SourceSession.from_execution(store, ticket_id, 'legal_covenants') over the single scope legal-covenants (L2 host: CP-4 admitted, empty scope refused)",
            "read_pages": "legal-covenants pages 1 through 3 in one call (first_page 1, last_page 3), before submit: every cited locator page:1, page:2 and page:3 must be an ok read in this attempt (unread_citation_issues)",
            "search_pack": "at least one scoped search_pack: positive 'Covenant EBITDA'; gap and false-same 'Schedule A'. The rule floor is lower (a search is required only when a row carries an ABSENCE_MARKER such as threshold_unit 'not stated', which no case does); the search is an oracle expectation for complete participation (LEGAL-SOURCE-CONTRACT)",
            "read_inputs": "exactly one read of the CP-4 step context (context_block) per attempt: it is the only way a participant learns the metric_ref (see lease draft, D2)",
            "forbidden": "extract_statements; any read of identity or financial raw; any upstream/full Module dump",
        },
    }
    consumption = {
        "CP-4 attempt inputs": "prepared-pack, CP-0 and CP-1, carrying the heads' result_sha256 at begin (cp4_legal.upstream_of requires CP-0 and CP-1); the settled module adds covenant-interpretation-submission",
        "what CP-4 actually reads": "CP-0: T3 authority per source -> legal_sources; CP-1: T4.10/T4.17 referencable facts, T4.18 facility id and name, limitations and inherited limitations (cp4_upstream)",
        "CP-4 read of CP-1 is proved by": "T4C.8, T4F.2 and T4F.3 (metric operand) and the headroom formula carrying the CP-1 fact's own id; T4.9 'Current' carrying its label, period, basis, calculation_id and citations (not the id); T4F.1 carrying the CP-1 head hash; and T4C.11/T4C.12 naming facility term-loan 'Northbridge Term Loan' from T4.18",
        "consumers_of_CP-4_in_this_run": "none. CP-3 reads CP-4 status and limitations only and needs CP-2 and market sources; CP-5 would review CP-4 only after a lease extends its integrity scope to CP-4 and A4 integrates (D3). So CP-4's own downstream consumption stays open in this run; rendering FP04 and a verified receipt are the completion evidence available here.",
    }
    expected = {
        "schema_version": "cp4-owner-expected/1",
        "derivation": "Hand-transcribed composition rules applied to submissions.json by cases/cp4-owner/builder/build.py (stdlib only; deploy_vii never imported by the builder). Numbers come only from the frozen financial oracle objects (cases/financial/manifest.json q4_ltm_metric_oracle.net_leverage_reported, q4_ltm_derived_source_units) and the quoted threshold. Rule sources: cp4_legal.py 215-258 (upstream), 291-348 (parse_threshold, headroom), 663-770 (registers), 771-1476 (composition), readiness.py 408-531 (CP-0), execution.py 345-366 and 441-457 (inheritance, status).",
        "cell_notation": {
            "text": "exact displayed text; null means unsettled",
            "status": "known | missing | not_applicable",
            "cites": "[source_id, locator] per citation, in order; the quote is in the submission row",
            "value_class": "analyst_judgment where the cell is model-written",
            "numeric cells": "amount as an exact Decimal string with unit; '<<...>>' and 'bound from the CP-1 fact' mark values bound at run time from the CP-1 head",
            "gap_cells": "render as the gap spelling with a report-wide G#, numbered sequentially in fact order; the number is not a literal",
        },
        "row_ids": "r01.. in submission order; ref01 (T4F.2); 'rating' (T4.13, T4F.4); 'none' for an empty register; input rows are the lower-cased input id",
        "table_order": [r[0] for r in REGISTERS],
        "figures": {
            "net_leverage_reported": {
                "cp1_coordinate": "T4.10 net_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31",
                "oracle_ratio": "30/30",
                "unit_token": "x",
                "spelled": "1.00x",
                "predicate": FIG_PREDICATE,
                "predicate_facts": {"table_id": "T4.10", "period": "LTM Q4 25: 2025-01-01 to 2025-12-31", "label": LTM_LABEL, "basis_observed": "IFRS \u00b7 consolidated group", "unit_token": "x", "shown": "1.00x", "excluded_aliases": ["Q4 25: 2025-10-01 to 2025-12-31", "FY25: 2025-01-01 to 2025-12-31"]},
                "predicate_status": "S1a rev 2 M2 predicate (LEAD ruling Q5/M1); the independent review (review-precise-1 Q5) confirmed on a promoted CP-1 head that it selects exactly the fact CP-4 copies into T4F.2; not yet exercised on the legal packs' own CP-1 heads",
            }
        },
        "cp4_step_view": {
            "name": "owners.cp4.view(store, attempt): json.dumps(cp4_legal.context_block(store.pack(), cp4_legal.upstream_of(store, attempt)), ensure_ascii=False, separators=(',', ':'), allow_nan=False)",
            "key_tree": {
                "legal_sources": [{"source_id": "str", "name": "str", "authority": "str", "extraction_coverage": {"located_spans": "int", "first_locator": "str", "last_locator": "str", "coverage_not_retained": [], "pages_missing_between_first_and_last": []}}],
                "other_sources": [{"source_id": "str", "authority": "str"}],
                "cp1_status": "str",
                "inherited_gaps": ["str"],
                "facilities": [{"facility_id": "str", "facility_name": "str"}],
                "cp1_facts": [{"ref": "str", "row": "str", "label": "str", "period": "str", "unit": "str", "shown": "str", "basis": "str"}],
                "cp1_facts_note": "str",
                "headroom_note": "str",
            },
            "status": "key tree observed by a probe of cp4_legal.context_block over a real promoted CP-1 head (read, not derived); no key named quote, citations or record_json occurs, and no legal quote text occurs in the body",
            "expected_values": {
                "legal_sources": ["legal-covenants"],
                "legal_sources[0].authority": "executed",
                "other_sources": ["identity (issuer)", "financial (issuer)"],
                "facilities": [{"facility_id": "term-loan", "facility_name": "Northbridge Term Loan"}],
                "cp1_status": "restricted",
                "metric_selection": FIG_PREDICATE,
            },
        },
        "semantic_gate": semantic_gate_block(subs),
        "run_time_bindings": [
            "PreparedPack.content_hash() of each case pack",
            "the net_leverage_reported fact id (FIG), the CP-1 fact's period, basis, label and citations",
            "T4F.1 SHA-256 cells (the three bound heads' hashes), T4F.5 rows (CP-1 head limitations then inherited, de-duplicated) and the CP-4 inherited list tail",
            "ticket ids and call ids (compared structurally only)",
        ],
        "execution": {
            "plan_order": PLAN,
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent; CP-1 QA score 59 Low)", "CP-4": "restricted", "why": "synthetic case_kind and own limitations (execution.py:441-457)"},
            "tool_use": tool_use,
            "consumption": consumption,
            "published": "no CP-MODEL in the plan; no publication",
        },
        "render": render,
        "d8_table_ids": {
            "new_ids": [],
            "overlap_with_other_modules_existing": {"T4.2": ["CP-1", "CP-1C"], "T4.3": ["CP-1", "CP-1C"], "T4.9": ["CP-1", "CP-1C"], "T4.10": ["CP-1", "CP-1C"], "T4.11": ["CP-1", "CP-1C"], "T4.12": ["CP-1"], "T4.13": ["CP-1"]},
            "rule": "D8: the existing CP-1/CP-4 overlap stays; fact coordinates and bindings are module-qualified (FactCoord.module_id). The 24 other ids (T4C.*, T4D.*, T4F.*) collide with no other module in methodology.json.",
        },
        **exp_cases,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "manifest.json", manifest)
    write(OUT / "submissions.json", submissions)
    write(OUT / "expected.json", expected)
    for name in ("manifest", "submissions", "expected"):
        print(name, hashlib.sha256((OUT / f"{name}.json").read_bytes()).hexdigest())


main()
