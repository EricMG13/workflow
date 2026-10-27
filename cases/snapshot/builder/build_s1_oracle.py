"""Writes cases/snapshot/{manifest,submissions,expected}.json from s1_data.py (stdlib only).

This is an independent transcription of the composition rules documented in
src/deploy_vii/business_context.py and cp2_synthesis.py (read, never imported or executed).
It also runs its own checks on the literal inputs: quotes against page text, run-text digits,
prohibited phrases, enum values, reference existence and the signal rules.

Run: python3 -I cases/snapshot/builder/build_s1_oracle.py   (from the repository root)
"""

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import s1_data as D  # noqa: E402

OUT = ROOT / "cases" / "snapshot"
FIN = json.loads((ROOT / "cases" / "financial" / "manifest.json").read_text())
FIN_SHA = hashlib.sha256((ROOT / "cases" / "financial" / "manifest.json").read_bytes()).hexdigest()

ISSUER = FIN["run"]["issuer_name"]
AS_OF = FIN["run"]["as_of"]
SYNTH = "Synthetic case; not real issuer qualification"


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s)


# --- packs -----------------------------------------------------------------------------------

fin_src = {s["source_id"]: s for s in FIN["sources"]}
for sid, s in fin_src.items():
    assert page_sha([p["text"] for p in s["pages"]]) == s["sha256"], sid
BUS_TEXT = [t for _, t in D.BUSINESS_PAGES]
BUS_SHA = page_sha(BUS_TEXT)
BUS_GAP_TEXT = [t for _, t in D.BUSINESS_GAP_PAGES]
BUS_GAP_SHA = page_sha(BUS_GAP_TEXT)
for _t in (*BUS_TEXT, *BUS_GAP_TEXT):
    assert not _t.endswith("\n") and _t.isascii()
assert D.BUSINESS_GAP_PAGES[0] == D.BUSINESS_PAGES[0]

PAGES_BY_CASE = {
    case: {
        "identity": {p["locator"]: p["text"] for p in fin_src["identity"]["pages"]},
        "financial": {p["locator"]: p["text"] for p in fin_src["financial"]["pages"]},
        "business": {loc: t for loc, t in pages},
    }
    for case, pages in (("positive", D.BUSINESS_PAGES), ("gap", D.BUSINESS_GAP_PAGES))
}
CASE_SHA = {
    "positive": {"identity": fin_src["identity"]["sha256"], "financial": fin_src["financial"]["sha256"], "business": BUS_SHA},
    "gap": {"identity": fin_src["identity"]["sha256"], "financial": fin_src["financial"]["sha256"], "business": BUS_GAP_SHA},
}
CUR = {"case": "positive"}

# Pack-source limitations are pack-construction inputs (tests/test_financial_workflow.py:22, 48-52).
PACKS = {
    "positive": [
        ("identity", fin_src["identity"]["name"], "ready", None),
        ("financial", fin_src["financial"]["name"], "ready", D.LIMIT_FIN),
        ("business", D.BUSINESS_NAME, "ready", None),
    ],
    "gap": [
        ("identity", fin_src["identity"]["name"], "ready", None),
        ("financial", fin_src["financial"]["name"], "ready", D.LIMIT_FIN),
        ("business", D.BUSINESS_NAME, "ready", D.BUSINESS_GAP_LIMITATION),
    ],
}

# --- own checks on the literal inputs ----------------------------------------------------------

LABEL_RE = re.compile(
    r"(?:FY|CY) ?(?:(?:19|20)\d\d|\d\d)|\bQ[1-4]\b|\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December) \d{1,2}, (?:19|20)\d\d\b|\b(?:19|20)\d\d\b|\bCP-\d{1,2}[A-Z]?\b"
)
PROHIBITED = [
    "peer ranking", "ranks above", "ranks below", "ranked first", "top quartile", "best-in-class",
    "best in class", "outperforms peers", "versus peers", "relative to peers", "compared with peers",
    "we recommend", "recommend", "buy", "sell", "overweight", "underweight", "preferred instrument",
    "recovery conclusion", "expected recovery", "recovery rate", "recovery estimate", "recovery value",
    "recover par", "full recovery", "will recover", "would recover", "repaid in full", "prefer the",
]
problems = []


def run_text_ok(where, text):
    t = re.sub(r"\{\{FIG:[a-z_]+\}\}", "", text)
    t = t.replace(ISSUER, "")
    t = LABEL_RE.sub("", t)
    if re.search(r"\d", t):
        problems.append(f"{where}: bare figure in {text!r}")
    for p in PROHIBITED:
        if re.search(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", text, re.I):
            problems.append(f"{where}: prohibited phrase {p!r}")
    if re.search(r"[{}\[\]]", t):
        problems.append(f"{where}: reserved character in {text!r}")


def check_quote(where, q):
    page = PAGES_BY_CASE[CUR["case"]][q["source_id"]].get(q["locator"])
    if page is None or norm(q["quote"]) not in norm(page):
        problems.append(f"{where}: quote not in {q['source_id']} {q['locator']}: {q['quote'][:70]!r}")


SKIP = {"source_id", "module_id", "conflict_id"}


def walk_rows(prefix, sub):
    for name, rows in sub.items():
        items = rows if isinstance(rows, list) else [rows]
        for i, row in enumerate(items):
            for k, v in row.items():
                where = f"{prefix}.{name}[{i}].{k}"
                if k == "citations":
                    for q in v:
                        check_quote(where, q)
                elif isinstance(v, str) and k not in SKIP and v not in ENUMS:
                    run_text_ok(where, v)
                elif isinstance(v, list) and k in ("flag_topics",):
                    for x in v:
                        run_text_ok(where, x)


ENUMS = set(
    "Documentary Fact|Management Language|Analyst Interpretation|Insufficient Information|High|Medium|Low|"
    "Insufficient|Critical|Material|Minor|Disclosed|Partially disclosed|Not disclosed|Completed|Pending|"
    "Announced|Proposed|Terminated|Subsequent event|Supportive|Neutral|Mixed|Extraction-Oriented|"
    "Creditor-Adverse|Adverse|Yes|No|Partial|READY|READY_WITH_LIMITATIONS|CONDITIONAL|BLOCKED|"
    "business_description|country|sector|issuer|unknown|governance_topic|behaviour_flag|distribution|"
    "Revenue Durability|Margin/CF Risk|Concentration Risk|Sponsor Alignment|Key Uncertainties|"
    "CP-2|CP-MODEL|Leverage tolerance|Shareholder extraction risk|Acquisition appetite|"
    "Disclosure transparency".split("|")
)
# --- schema-key check: field names and enums transcribed from the product models (read, not imported)
# business_context.py:75-123 (enums), 132-323 (models); cp2_synthesis.py:96-156; readiness.py:26-87;
# contracts.py:201-205 (Claim), 139-143 (Citation).
CAT = ["Documentary Fact", "Management Language", "Analyst Interpretation", "Insufficient Information"]
EQ = ["High", "Medium", "Low", "Insufficient"]
CONF = ["High", "Medium", "Low", "Insufficient Information"]
SEV = ["Critical", "Material", "Minor"]
DIR = ["Supportive", "Neutral", "Mixed", "Extraction-Oriented", "Creditor-Adverse", "Insufficient Information"]
DIMS = ["Leverage tolerance", "Shareholder extraction risk", "Acquisition appetite", "Support behavior",
        "Disclosure transparency", "Creditor treatment / amendment behavior", "Legal-capacity linkage",
        "Reporting quality", "Related-party leakage risk"]
RDY = ["READY", "READY_WITH_LIMITATIONS", "CONDITIONAL", "BLOCKED"]
AUTH = ["filed", "executed", "issuer", "management", "sponsor", "third_party", "unknown"]
MODELS = {  # name: (ordered fields, {field: allowed values})
    "Quote": (["source_id", "locator", "quote"], {}),
    "SourceUse": (["source_id", "source_class", "quality", "period", "entity_covered", "data_supplied", "use", "citations", "limitation"], {"source_class": AUTH, "quality": EQ}),
    "CompanyFact": (["aspect", "text", "category", "citations", "limitation"], {"aspect": ["business_description", "country", "sector"], "category": CAT}),
    "BusinessLine": (["name", "revenue_mix", "period", "category", "citations", "limitation"], {"category": CAT}),
    "Owner": (["owner", "control", "economic_interest", "credit_relevance", "evidence_quality", "credit_mechanic", "credit_implication", "category", "citations", "limitation"], {"evidence_quality": EQ, "category": CAT}),
    "OperatingDriver": (["driver", "measure", "period", "status", "credit_relevance", "category", "citations", "limitation"], {"status": ["Disclosed", "Partially disclosed", "Not disclosed"], "category": CAT}),
    "Transaction": (["transaction", "status", "credit_relevance", "category", "citations", "limitation"], {"status": ["Completed", "Pending", "Announced", "Proposed", "Terminated", "Insufficient Information"], "category": CAT}),
    "Event": (["date_window", "event", "credit_relevance", "status", "category", "citations", "limitation"], {"status": ["Completed", "Announced", "Pending", "Subsequent event"], "category": CAT}),
    "GovernanceItem": (["kind", "topic", "documented_fact", "direction", "behaviour_type", "amount_funding_source", "legal_capacity_link", "dimension", "risk_mechanic", "credit_implication", "evidence_quality", "category", "citations", "limitation"], {"kind": ["governance_topic", "behaviour_flag"], "direction": DIR, "dimension": DIMS + [None], "evidence_quality": EQ, "category": CAT, "behaviour_type": ["dividend recap", "distribution", "support", "LME", "amendment", "acquisition", "disposal", "reporting", "other", None]}),
    "CapitalAllocation": (["item", "fact", "direction", "risk_mechanic", "credit_implication", "evidence_quality", "category", "citations", "limitation"], {"direction": ["Supportive", "Neutral", "Mixed", "Adverse", "Insufficient Information"], "evidence_quality": EQ, "category": CAT}),
    "DisclosureItem": (["item", "available", "detail", "credit_relevance", "severity", "follow_up", "citations"], {"available": ["Yes", "No", "Partial", "Insufficient Information"], "severity": SEV}),
    "CreditTranslation": (["theme", "evidence", "risk_mechanic", "credit_implication", "confidence", "countervailing_conflict_ids", "citations", "limitation"], {"theme": ["Revenue Durability", "Margin/CF Risk", "Concentration Risk", "Sponsor Alignment", "Key Uncertainties"], "confidence": CONF}),
    "Conflict": (["conflict_id", "conflict", "materiality", "downstream_impact", "citations"], {"materiality": SEV}),
    "Gap": (["gap", "why_it_matters", "affected_analysis", "severity", "action"], {"severity": SEV}),
    "Consumer": (["module_id", "status", "handoff_item", "why_it_matters", "gap", "required_action", "citations", "flag_topics"], {"status": RDY}),
    "Assessment": (["rationale", "category", "confidence", "cp1a_refs", "limitation"], {"category": CAT, "confidence": CONF}),
    "Thesis": (["text", "category", "cp1a_refs", "limitation"], {"category": CAT}),
    "Point": (["label", "text", "category", "cp1a_refs", "limitation"], {"category": CAT}),
    "Finding": (["text", "cp1a_refs"], {}),
    "Risk": (["risk", "mechanic", "implication", "severity", "cp1a_refs"], {"severity": SEV}),
    "SynthesisGap": (["gap", "why_it_matters", "affected_analysis", "severity", "action", "cp1a_refs"], {"severity": SEV}),
    "Citation": (["source_id", "source_sha256", "locator", "quote"], {}),
    "SourceAssessment": (["source_id", "document_family", "authority", "entity", "period", "version_relationship", "fidelity", "citations", "limitations"], {"authority": AUTH, "fidelity": ["verified", "degraded", "blocked"]}),
    "ConsumerReadiness": (["module_id", "readiness", "evidence_demand", "source_ids", "rationale", "citations", "missing_source", "limitations"], {"readiness": RDY}),
    "ReadinessGap": (["gap_id", "kind", "severity", "description", "affected_modules", "remediation", "citations"], {"kind": ["source", "parse", "identity", "period", "conflict", "authority", "scope"], "severity": ["critical", "material", "minor"]}),
    "Claim": (["claim_id", "text", "citations", "limitation"], {}),
}
SECTION_MODEL = {
    "sources": "SourceUse", "company": "CompanyFact", "business_lines": "BusinessLine", "owners": "Owner",
    "operating_drivers": "OperatingDriver", "transactions": "Transaction", "events": "Event",
    "governance_and_sponsor": "GovernanceItem", "capital_allocation": "CapitalAllocation",
    "disclosure_items": "DisclosureItem", "credit_translations": "CreditTranslation", "conflicts": "Conflict",
    "gaps": "Gap", "consumers": "Consumer", "acquisitions": "Acquisition",
}
TOP_1A = ["sources", "company", "business_lines", "owners", "operating_drivers", "transactions", "events", "governance_and_sponsor", "capital_allocation", "acquisitions", "disclosure_items", "credit_translations", "conflicts", "gaps", "consumers"]
TOP_2 = ["assessment", "thesis", "strengths", "weaknesses", "key_findings", "risks", "gaps"]
TOP_0 = ["pack_sha256", "objective", "reporting_period", "issuer_confirmed", "sources", "consumers", "gaps", "analysis"]
SECTION_2 = {"assessment": "Assessment", "thesis": "Thesis", "strengths": "Point", "weaknesses": "Point", "key_findings": "Finding", "risks": "Risk", "gaps": "SynthesisGap"}
SECTION_0 = {"sources": "SourceAssessment", "consumers": "ConsumerReadiness", "gaps": "ReadinessGap", "analysis": "Claim"}


def check_shape(where, model, row):
    fields, enums = MODELS[model]
    if set(row) != set(fields):
        problems.append(f"{where}: keys differ from {model}: extra {sorted(set(row) - set(fields))} missing {sorted(set(fields) - set(row))}")
    for k, allowed in enums.items():
        if k in row and row[k] not in allowed:
            problems.append(f"{where}.{k}: {row[k]!r} not an allowed value")
    for i, q in enumerate(row.get("citations", [])):
        check_shape(f"{where}.citations[{i}]", "Citation" if "source_sha256" in q else "Quote", q)


def check_submission(prefix, sub, top, sections):
    if list(sub) != top:
        problems.append(f"{prefix}: top-level keys {list(sub)} differ from {top}")
    for name, rows in sub.items():
        if not isinstance(rows, (list, dict)):
            continue
        for i, row in enumerate(rows if isinstance(rows, list) else [rows]):
            model = sections.get(name)
            if model is None or model == "Acquisition":
                if rows:
                    problems.append(f"{prefix}.{name}: no transcribed model")
                continue
            check_shape(f"{prefix}.{name}[{i}]", model, row)


for _case, _sub in (("positive", D.POSITIVE_CP1A), ("gap", D.GAP_CP1A)):
    CUR["case"] = _case
    check_submission(f"{_case}_cp1a", _sub, TOP_1A, SECTION_MODEL)
    walk_rows(f"{_case}_cp1a", _sub)
for _case, _sub in (("positive", D.POSITIVE_CP2), ("gap", D.GAP_CP2)):
    CUR["case"] = _case
    check_submission(f"{_case}_cp2", _sub, TOP_2, SECTION_2)
    walk_rows(f"{_case}_cp2", _sub)

# --- CP-1A composition (transcribed rules) -------------------------------------------------------

LABEL = {
    "Management Language": " [Management Language]",
    "Analyst Interpretation": " [Analyst Interpretation]",
    "Insufficient Information": " [Insufficient Information]",
}
NONE_STATED = "None stated"
NO_EVIDENCE = "No located evidence"
STATUS_OF_CATEGORY = {
    "Documentary Fact": "Documented",
    "Management Language": "Management Language",
    "Analyst Interpretation": "Analyst Interpretation",
    "Insufficient Information": "Insufficient Information",
}
CONSEQUENCE = {"Critical": "High", "Material": "Medium", "Minor": "Low"}
QUALITY_OF_CONFIDENCE = {"High": "High", "Medium": "Medium", "Low": "Low", "Insufficient Information": "Insufficient"}
DIMENSIONS = [
    "Leverage tolerance", "Shareholder extraction risk", "Acquisition appetite", "Support behavior",
    "Disclosure transparency", "Creditor treatment / amendment behavior", "Legal-capacity linkage",
    "Reporting quality", "Related-party leakage risk",
]


def snake(label):
    return re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")


def reg(tid, title, cols):
    return (tid, title, cols.split("|"))


REGS = {r[0]: r for r in [
    reg("source_classification", "Source classification", "Source ID|Source class|Quality|Use|Limitation"),
    reg("transaction_summary", "Transaction summary", "Transaction|Status|Credit relevance|Source"),
    reg("company_description", "Company description", "Issuer|Business description|Country|Sector"),
    reg("revenue_business_mix", "Revenue and business mix", "Business line|Revenue mix|Period|Status|Limitation"),
    reg("ownership_register", "Ownership register", "Owner / class|Control|Economic interest|Credit relevance|Source"),
    reg("operating_model", "Operating model", "Operating driver|Measure|Period|Status|Credit relevance"),
    reg("events_timeline", "Events timeline", "Date / window|Event|Credit relevance|Status|Source"),
    reg("credit_translation", "Credit translation", "Evidence|Risk mechanic|Credit implication|Confidence|Limitation"),
    reg("gaps_ledger", "Gaps ledger", "Gap|Affected analysis|Severity|Action|Status"),
    reg("conflict_log", "Conflict log", "Conflict|Sources|Materiality|Resolution|Downstream impact"),
    reg("downstream_readiness", "Downstream readiness", "Module|Status|Gap|Required action"),
    reg("T2D.1", "Source register", "source_document_id|source_document_name|source_quality|period|entity_covered|data_supplied|limitation|downstream_use"),
    reg("T2D.2", "Ownership and control register", "Item|Source-Supported Fact|Evidence Quality|Source Trace|Credit Mechanic|Credit Implication|Limitation"),
    reg("T2D.3", "Governance register", "Governance Topic|Source-Supported Fact|Risk Direction|Risk Mechanic|Credit Implication|Evidence Quality|Source Trace|Limitation"),
    reg("T2D.4", "Behaviour flag register", "Flag ID|Behavior Type|Documented Action|Behavior Category|Amount / Funding Source|Legal-Capacity Link|Risk Mechanic|Credit Implication|Evidence Quality|Source Trace|Limitation"),
    reg("T2D.5", "Capital allocation risk table", "Capital Allocation Item|Source-Supported Fact|Direction|Risk Mechanic|Credit Implication|Evidence Quality|Source Trace|Limitation"),
    reg("T2D.6", "Acquisition appetite and integration", "Acquisition / Period|Source-Supported Fact|Funding Mix|EBITDA / Pro Forma Basis|Integration Evidence|Leverage / Liquidity Effect|Risk Mechanic|Credit Implication|Source Trace|Limitation"),
    reg("T2D.7", "Disclosure quality log", "Disclosure Item|Available?|Source-Supported Detail|Credit Relevance|Severity|Source Trace|Required Follow-Up"),
    reg("T2D.8", "Governance and sponsor score", "Dimension|Assessment|Evidence|Risk Mechanic|Credit Implication|Score|Evidence Quality|Source Trace|Limitation"),
    reg("T2D.9", "Sponsor risk-level drivers", "Risk-Level Driver|Evidence|Risk Mechanic|Credit Implication|Evidence Quality|Source Trace|Countervailing Evidence|Limitation"),
    reg("T2D.10", "Cross-module handoff register", "Downstream Module|Handoff Tag|Handoff Item|Why It Matters|Required Consumer Action|Source / Flag Link|Limitation"),
    reg("T2D.11", "Governance gaps ledger", "Gap ID|Missing Data|Why It Matters|Affected Section / Flag / Export Record|Consequence for Confidence|Required Follow-Up Source"),
    reg("cp1a.cp_model_snapshot_fields", "CP-MODEL snapshot fields", "field_id|value|status|source_id|source_locator|as_of"),
]}
UNKEYED = {"company_description", "credit_translation", "transaction_summary", "events_timeline"}
NONEMPTY = {"source_classification", "company_description", "credit_translation", "downstream_readiness", "T2D.1", "T2D.10"}


def C(text, cites=(), judged=False, reason=None, status="known"):
    return {"text": text, "cites": [[q["source_id"], q["locator"]] for q in cites], "judged": judged,
            "reason": reason, "status": status}


def gapcell(reason):
    return C(None, reason=reason, status="missing")


def trace(cites):
    seen = []
    for q in cites:
        k = f"{q['source_id']} {q['locator']}"
        if k not in seen:
            seen.append(k)
    return "; ".join(seen)


class Composer:
    def __init__(self, module, regs, subject, subs=lambda s: s):
        self.module, self.regs, self.subject, self.subs = module, regs, subject, subs
        self.tables, self.limitations = [], []

    def table(self, tid, rows, required=None, keyed=None):
        _, title, labels = self.regs[tid]
        keyed = (tid not in UNKEYED) if keyed is None else keyed
        required = (tid in NONEMPTY) if required is None else required
        cols = labels[1:] if keyed else labels
        if not rows:
            tl = title.lower()
            if required:
                reason = f"No {tl} rows in the {self.subject} submission"
                self.limitations.append(reason)
                cell = C(None, reason=reason, status="missing")
            else:
                cell = C(None, reason=f"None in the {self.subject} submission ({tl})", status="not_applicable")
            rows = [("none", [*( [C("None")] if keyed else []), *[cell for _ in cols]])]
        out_rows = []
        for pos, (rid, allc) in enumerate(rows, 1):
            cells = allc[1:] if keyed else allc
            assert len(cells) == len(cols), (tid, rid, len(cells), len(cols))
            label = (allc[0]["text"] if keyed else None) or f"{title} {pos}"
            facts = []
            for lab, c in zip(cols, cells):
                facts.append({
                    "fact_id": f"{tid}.{rid}.{snake(lab)}", "column": lab, "text": c["text"],
                    "status": "known" if c["text"] is not None else c["status"],
                    "cites": c["cites"], "value_class": "analyst_judgment" if c["judged"] else None,
                    "limitation": c["reason"] if c["text"] is None else None,
                })
            out_rows.append({"row_id": rid, "label": label, "facts": facts})
        self.tables.append({"table_id": tid, "title": title, "row_header": labels[0] if keyed else None,
                            "columns": [{"field": snake(x), "label": x} for x in cols], "rows": out_rows})


def tag(text, cat):
    return text + LABEL.get(cat, "")


def numbered(rows):
    return [(f"r{i:02d}", r) for i, r in enumerate(rows, 1)]


def cp1a_expected(case, sub):
    pack = PACKS[case]
    cm = Composer("CP-1A", REGS, "CP-1A")
    # business_context.py:1673: gap limitations are added before any register is composed
    cm.limitations.extend(f"Gap ({g['severity']}): {g['gap']}" for g in sub["gaps"])
    Q_ = lambda row: row.get("citations", [])
    cited_sources = set()
    for key in sub:
        rows = sub[key]
        for row in rows if isinstance(rows, list) else []:
            for q in row.get("citations", []):
                cited_sources.add(q["source_id"])
    uses = {u["source_id"]: u for u in sub["sources"]}
    srcrows_sc, srcrows_t = [], []
    for sid, name, status, lim in pack:
        u = uses[sid]
        parts = ([u["limitation"]] if u["limitation"] else []) + ([lim] if lim else [])
        parts += [] if sid in cited_sources else ["Not cited by any CP-1A row"]
        limit = C("; ".join(parts) or NONE_STATED)
        said = lambda t: C(t, Q_(u), judged=True)
        srcrows_sc.append([C(sid), C(u["source_class"]), C(u["quality"]), said(u["use"]), limit])
        srcrows_t.append([C(sid), C(name), C(u["quality"]), said(u["period"]) if u["period"] else C(NONE_STATED),
                          said(u["entity_covered"]), said(u["data_supplied"]), limit, said(u["use"])])
    cm.table("source_classification", numbered(srcrows_sc))
    cm.table("T2D.1", numbered(srcrows_t))
    # facts
    comp = {c["aspect"]: c for c in sub["company"]}
    J = lambda t, row: C(t, Q_(row), judged=True)
    TG = lambda t, row: C(tag(t, row["category"]), Q_(row), judged=True)
    cm.table("company_description", [("company", [C(ISSUER), *[TG(comp[a]["text"], comp[a]) for a in ("business_description", "country", "sector")]])])
    cm.table("transaction_summary", numbered([[TG(t["transaction"], t), C(t["status"]), J(t["credit_relevance"], t), C(trace(Q_(t)) or NO_EVIDENCE, Q_(t))] for t in sub["transactions"]]))
    limit_of = lambda row: C(row["limitation"] if row.get("limitation") else NONE_STATED)
    cm.table("revenue_business_mix", numbered([[J(b["name"], b), TG(b["revenue_mix"], b), J(b["period"], b), C(STATUS_OF_CATEGORY[b["category"]]), limit_of(b)] for b in sub["business_lines"]]))
    cm.table("ownership_register", numbered([[TG(o["owner"], o), J(o["control"], o), J(o["economic_interest"], o), J(o["credit_relevance"], o), C(trace(Q_(o)) or NO_EVIDENCE, Q_(o))] for o in sub["owners"]]))
    und = gapcell("Not disclosed by the source: left unsettled, never shown as zero")
    cm.table("operating_model", numbered([[J(d["driver"], d), TG(d["measure"], d) if d["measure"] is not None else und, J(d["period"], d), C(d["status"]), J(d["credit_relevance"], d)] for d in sub["operating_drivers"]]))
    cm.table("events_timeline", numbered([[J(e["date_window"], e), TG(e["event"], e), J(e["credit_relevance"], e), C(e["status"]), C(trace(Q_(e)) or NO_EVIDENCE, Q_(e))] for e in sub["events"]]))
    cm.table("credit_translation", numbered([[J(c["evidence"], c), J(c["risk_mechanic"], c), J(c["credit_implication"], c), C(c["confidence"]), limit_of(c)] for c in sub["credit_translations"]]))
    cm.table("gaps_ledger", numbered([[C(g["gap"], judged=True), C(g["affected_analysis"], judged=True), C(g["severity"]), C(g["action"], judged=True), C("Open")] for g in sub["gaps"]]))
    cm.table("conflict_log", [])
    # governance
    cm.table("T2D.2", numbered([[J(o["owner"], o), TG(f"Control: {o['control']}; economic interest: {o['economic_interest']}", o), C(o["evidence_quality"]), C(trace(Q_(o)) or NO_EVIDENCE, Q_(o)), J(o["credit_mechanic"], o), J(o["credit_implication"], o), limit_of(o)] for o in sub["owners"]]))
    gov = sub["governance_and_sponsor"]
    topics = [g for g in gov if g["kind"] == "governance_topic"]
    flags = [g for g in gov if g["kind"] == "behaviour_flag"]
    cm.table("T2D.3", numbered([[J(g["topic"], g), TG(g["documented_fact"], g), C(g["direction"]), J(g["risk_mechanic"], g), J(g["credit_implication"], g), C(g["evidence_quality"]), C(trace(Q_(g)) or NO_EVIDENCE, Q_(g)), limit_of(g)] for g in topics]))
    cm.table("T2D.4", numbered([[C(f"CP-2C-FLAG-{i:03d}"), C(g["behaviour_type"]), TG(g["documented_fact"], g), C(g["direction"]), J(g["amount_funding_source"], g), J(g["legal_capacity_link"], g), J(g["risk_mechanic"], g), J(g["credit_implication"], g), C(g["evidence_quality"]), C(trace(Q_(g)) or NO_EVIDENCE, Q_(g)), limit_of(g)] for i, g in enumerate(flags, 1)]))
    cm.table("T2D.5", numbered([[J(c["item"], c), TG(c["fact"], c), C(c["direction"]), J(c["risk_mechanic"], c), J(c["credit_implication"], c), C(c["evidence_quality"]), C(trace(Q_(c)) or NO_EVIDENCE, Q_(c)), limit_of(c)] for c in sub["capital_allocation"]]))
    cm.table("T2D.6", [])
    cm.table("T2D.7", numbered([[J(d["item"], d), C(d["available"]), J(d["detail"], d), J(d["credit_relevance"], d), C(d["severity"]), C(trace(Q_(d)) or NO_EVIDENCE, Q_(d)), J(d["follow_up"], d)] for d in sub["disclosure_items"]]))
    # T2D.8 / T2D.9
    scorable = lambda g: g["dimension"] is not None and g["direction"] != "Insufficient Information" and g["category"] != "Insufficient Information" and g["evidence_quality"] != "Insufficient"
    rows8, scores = [], []
    for i, dim in enumerate(DIMENSIONS, 1):
        drows = [g for g in gov if scorable(g) and g["dimension"] == dim]
        dirs = {g["direction"] for g in drows}
        if not drows:
            score, deciding = "Not Scorable", []
        elif dirs == {"Supportive"}:
            score, deciding = "1", drows
        elif dirs & {"Extraction-Oriented", "Creditor-Adverse"} and "Supportive" not in dirs:
            score, deciding = "5", [g for g in drows if g["direction"] in ("Extraction-Oriented", "Creditor-Adverse")]
        else:
            score, deciding = "3", drows
        scores.append(score)
        assess = {"1": "Creditor-favorable", "3": "Mixed", "5": "Adverse", "Not Scorable": "Not Scorable"}[score]
        cites = []
        for g in deciding:
            for q in g["citations"]:
                if q not in cites:
                    cites.append(q)
        unscored = "No evidenced governance or sponsor row informs this dimension"
        joined = lambda key: "; ".join(dict.fromkeys(g[key] for g in deciding))

        def chain(key):
            j = joined(key)
            return C(j, cites, judged=True) if j else gapcell(unscored)

        qual = next((q for q in ("High", "Medium", "Low") if q in {g["evidence_quality"] for g in deciding}), "Insufficient")
        lims = [g["limitation"] for g in deciding if g["limitation"]]
        rows8.append((f"d{i:02d}", [C(dim), C(assess), chain("documented_fact"), chain("risk_mechanic"), chain("credit_implication"), C(score), C(qual), C(trace(cites) or NO_EVIDENCE, cites), C("; ".join(dict.fromkeys(lims)) or NONE_STATED)]))
    scored = [s for s in scores if s != "Not Scorable"]
    high_action = any(g["direction"] in ("Extraction-Oriented", "Creditor-Adverse") and g["evidence_quality"] == "High" and g["category"] != "Insufficient Information" for g in gov)
    if len(scored) < 4:
        composite, level = "Not Scorable", ("High" if high_action else "Insufficient Information")
    else:
        composite = max(scored, key=int)
        level = {"1": "Low", "3": "Medium", "5": "High"}[composite]
    if composite != "Not Scorable":
        rule = "The most adverse dimension score; at least four dimensions are scored"
    elif high_action:
        rule = "Fewer than four dimensions are scored; one Extraction-Oriented or Creditor-Adverse row on High-quality evidence sets the level High"
    else:
        rule = "Fewer than four dimensions are scored, so no composite is calculated"
    lvl = f"Sponsor / Governance Risk Level: {level}"
    rows8.append(("composite", [C("Composite"), C(lvl), C(f"{len(scored)} of {len(DIMENSIONS)} scoring dimensions supported"), C(rule), C(lvl), C(composite), C("Derived from the dimension rows"), C("The dimension rows above"), C(NONE_STATED)]))
    cm.table("T2D.8", rows8)
    conflicts = {c["conflict_id"]: c for c in sub["conflicts"]}
    cm.table("T2D.9", numbered([[C(c["theme"]), J(c["evidence"], c), J(c["risk_mechanic"], c), J(c["credit_implication"], c), C(QUALITY_OF_CONFIDENCE[c["confidence"]]), C(trace(Q_(c)) or NO_EVIDENCE, Q_(c)), C("; ".join(dict.fromkeys(conflicts[x]["conflict"] for x in c["countervailing_conflict_ids"])) or "Insufficient Information: no logged conflict counters this driver"), limit_of(c)] for c in sub["credit_translations"]]))
    # handoff
    run_modules = ["CP-2", "CP-MODEL"]  # registry order of the consumers of CP-1A for the S1 plan
    cons = sorted(sub["consumers"], key=lambda c: run_modules.index(c["module_id"]))
    cm.table("downstream_readiness", numbered([[C(c["module_id"]), C(c["status"]), C(c["gap"], judged=True), C(c["required_action"], judged=True)] for c in cons]))
    flag_ids = {}
    for i, g in enumerate(flags, 1):
        flag_ids.setdefault(g["topic"], []).append(f"CP-2C-FLAG-{i:03d}")

    def link(c):
        named = [i for t in c["flag_topics"] for i in flag_ids.get(t, [])]
        parts = [f"Sources: {trace(c['citations'])}"] if c["citations"] else []
        parts += [f"Flags: {', '.join(dict.fromkeys(named))}"] if named else []
        return C("; ".join(parts) or "No source or behaviour flag backs this handoff row", c["citations"])

    cm.table("T2D.10", numbered([[C(c["module_id"]), C(f"CP-2C-HANDOFF-{c['module_id']}"), C(c["handoff_item"], judged=True), C(c["why_it_matters"], judged=True), C(c["required_action"], judged=True), link(c), C(c["gap"], judged=True)] for c in cons]))
    cm.table("T2D.11", [(f"r{i:02d}", [C(f"CP-1A-GAP-{i:03d}"), C(g["gap"], judged=True), C(g["why_it_matters"], judged=True), C(g["affected_analysis"], judged=True), C(CONSEQUENCE[g["severity"]]), C(g["action"], judged=True)]) for i, g in enumerate(sub["gaps"], 1)])
    # snapshot fields
    supplied = {
        "sector": [(comp["sector"]["text"], comp["sector"])],
        "country": [(comp["country"]["text"], comp["country"])],
        "shareholders": [(o["owner"], o) for o in sub["owners"]],
        "transaction_summary": [(t["transaction"], t) for t in sub["transactions"]],
        "business_description": [(comp["business_description"]["text"], comp["business_description"])],
    }
    snap = [("issuer_name", [C("issuer_name"), C(ISSUER), C("READY"), C("prepared-pack"), C("run.issuer_name"), C(AS_OF)])]
    for field, pairs in supplied.items():
        texts = [tag(t, r["category"]) for t, r in pairs]
        cites = []
        for _, r in pairs:
            for q in r.get("citations", []):
                if q not in cites:
                    cites.append(q)
        if not texts or not cites:
            g = gapcell(f"CP-1A has no located {field.replace('_', ' ')}")
            snap.append((field, [C(field), g, C("GAP"), g, g, C(AS_OF)]))
        else:
            snap.append((field, [C(field), C("; ".join(dict.fromkeys(texts)), cites, judged=True), C("READY"), C(", ".join(dict.fromkeys(q["source_id"] for q in cites))), C("; ".join(dict.fromkeys(q["locator"] for q in cites))), C(AS_OF)]))
    cm.table("cp1a.cp_model_snapshot_fields", snap)
    order = ["source_classification", "T2D.1", "company_description", "transaction_summary", "revenue_business_mix", "ownership_register", "operating_model", "events_timeline", "credit_translation", "gaps_ledger", "conflict_log", "T2D.2", "T2D.3", "T2D.4", "T2D.5", "T2D.6", "T2D.7", "T2D.8", "T2D.9", "downstream_readiness", "T2D.10", "T2D.11", "cp1a.cp_model_snapshot_fields"]
    assert [t["table_id"] for t in cm.tables] == order, [t["table_id"] for t in cm.tables]
    claims = [{"claim_id": f"credit_translation.r{i:02d}", "text": f"{c['evidence']} Risk mechanic: {c['risk_mechanic']} Credit implication: {c['credit_implication']}", "limitation": c["limitation"], "cites": [[q['source_id'], q['locator']] for q in c['citations']]} for i, c in enumerate(sub["credit_translations"], 1)]
    return {
        "tables": cm.tables, "claims": claims,
        "own_limitations": list(dict.fromkeys(cm.limitations)),
        "settled_limitations": list(dict.fromkeys([*cm.limitations, SYNTH])),
        "governance": {"scores": dict(zip(DIMENSIONS, scores)), "composite": composite, "risk_level": level, "dimensions_scored": len(scored), "high_risk_action": high_action},
    }


# --- CP-2 composition ---------------------------------------------------------------------------


def catalogue(cp1a):
    rows = {}
    for t in cp1a["tables"]:
        for r in t["rows"]:
            if all(f["status"] != "known" for f in r["facts"]):
                continue
            rows[f"{t['table_id']}.{r['row_id']}"] = r["label"]
    return rows


def signals(cp1a):
    by = {t["table_id"]: t for t in cp1a["tables"]}
    out = []
    for tid in ("gaps_ledger", "T2D.7"):
        for r in by[tid]["rows"]:
            sev = next(f for f in r["facts"] if f["fact_id"].endswith(".severity"))
            if sev["text"] == "Critical":
                out.append({"source": tid, "ref": f"{tid}.{r['row_id']}", "status": "Critical"})
    judged = [r for r in by["downstream_readiness"]["rows"] if r["label"] == "CP-2"]
    if not judged:
        out.append({"source": "downstream_readiness", "ref": None, "status": "absent"})
    for r in judged:
        st = next(f for f in r["facts"] if f["fact_id"].endswith(".status"))["text"]
        if st != "READY":
            out.append({"source": "downstream_readiness", "ref": f"downstream_readiness.{r['row_id']}", "status": st})
    return out


FIG_RE = re.compile(r"\{\{FIG:([a-z_]+)\}\}")


def spell(text):
    return FIG_RE.sub(lambda m: D.FIGS[m.group(1)][3], text)


def figs_in(*texts):
    found = []
    for t in texts:
        for m in FIG_RE.finditer(t or ""):
            if m.group(1) not in found:
                found.append(m.group(1))
    return found


CP2_REGS = {
    "T2.1": ("T2.1", "Credit assessment", ["Assessment", "Category", "Confidence", "Basis", "Limitation"]),
    "T2.7": ("T2.7", "Thesis, strengths and weaknesses", ["Side", "Label", "Text", "Category", "Basis", "Limitation"]),
    "T2.10": ("T2.10", "Key findings", ["Finding", "Basis"]),
    "T2.11": ("T2.11", "Key credit risks", ["Risk", "Risk mechanic", "Credit implication", "Severity", "Basis"]),
    "T2.12": ("T2.12", "Gaps ledger", ["Gap ID", "Gap", "Why it matters", "Affected analysis", "Severity", "Action", "Basis"]),
}


# cp2_synthesis.py:500-548: field ids are explicit, not derived from labels (T2.11 mechanic / implication)
FIELDS2 = {
    "T2.1": ["assessment", "category", "confidence", "basis", "limitation"],
    "T2.7": ["side", "label", "text", "category", "basis", "limitation"],
    "T2.10": ["finding", "basis"],
    "T2.11": ["risk", "mechanic", "implication", "severity", "basis"],
    "T2.12": ["gap_id", "gap", "why_it_matters", "affected_analysis", "severity", "action", "basis"],
}


def cp2_expected(sub, cp1a, name):
    cat = catalogue(cp1a)
    sigs = signals(cp1a)
    for sec in ("assessment", "thesis"):
        for ref in sub[sec]["cp1a_refs"]:
            assert ref in cat, (name, sec, ref)
    for sec in ("strengths", "weaknesses", "key_findings", "risks", "gaps"):
        for row in sub[sec]:
            for ref in row["cp1a_refs"]:
                assert ref in cat, (name, sec, ref)
    restated = {r for g in sub["gaps"] for r in g["cp1a_refs"]}
    for s in sigs:
        if s["ref"]:
            assert s["ref"] in restated, (name, "signal not restated", s)
    if sigs:
        assert sub["assessment"]["confidence"] != "High"
    cm = Composer("CP-2", {k: v for k, v in CP2_REGS.items()}, "CP-2")

    def basis(row, fig_names):
        cited = set(row["cp1a_refs"])
        parts = [f"CP-1A {ref} ({label})" for ref, label in cat.items() if ref in cited]
        parts += [f"CP-1 <label and period of FIG:{n}>" for n in fig_names]
        return C("; ".join(parts) or "No CP-1A row or CP-1 figure cited")

    def S(t):
        return C(spell(t), judged=True)

    def T(t, c):
        return C(spell(t) + LABEL.get(c, ""), judged=True)

    def L(t):
        return C(spell(t) if t else NONE_STATED)

    A, Th = sub["assessment"], sub["thesis"]
    cm.limitations.extend(f"Gap ({g['severity']}): {spell(g['gap'])}" for g in sub["gaps"])
    cm.table("T2.1", [("assessment", [T(A["rationale"], A["category"]), C(A["category"]), C(A["confidence"]), basis(A, figs_in(A["rationale"], A["limitation"])), L(A["limitation"])])], keyed=False, required=True)
    if "Insufficient Information" in (A["category"], A["confidence"]):
        cm.limitations.append(f"Credit assessment is Insufficient Information: {spell(A['limitation'] or '')}")
    # T2.7 rows
    rows = [("thesis", [C("Thesis"), C("Thesis"), T(Th["text"], Th["category"]), C(Th["category"]), basis(Th, figs_in(Th["text"], Th["limitation"])), L(Th["limitation"])])]
    front = {"cp2.thesis": [("thesis", "Thesis", T(Th["text"], Th["category"]))]}
    for side, prefix, key, fid in (("Strength", "s", "strengths", "cp2.strengths"), ("Weakness", "w", "weaknesses", "cp2.weaknesses")):
        lines = []
        for i, p in enumerate(sub[key], 1):
            rid = f"{prefix}{i:02d}"
            label = spell(p["label"])
            text = T(p["text"], p["category"])
            rows.append((rid, [C(side), C(label, judged=True), text, C(p["category"]), basis(p, figs_in(p["label"], p["text"], p["limitation"])), L(p["limitation"])]))
            lines.append((rid, label, text))
        front[fid] = lines
    # labels of T2.7 rows: thesis -> "Thesis", s01 -> "Strength 1"
    labelled = []
    for rid, cells in rows:
        lab = "Thesis" if rid == "thesis" else f"{'Strength' if rid[0] == 's' else 'Weakness'} {int(rid[1:])}"
        labelled.append((rid, lab, cells))
    # key findings
    kf_rows, kf_lines = [], []
    for i, f in enumerate(sub["key_findings"], 1):
        kf_rows.append((f"kf{i:02d}", f"Key finding {i}", [S(f["text"]), basis(f, figs_in(f["text"]))]))
        kf_lines.append((f"kf{i:02d}", f"Key finding {i}", S(f["text"])))
    front["cp2.key_findings"] = kf_lines
    risk_rows = [(f"r{i:02d}", f"Risk {i}", [S(r["risk"]), S(r["mechanic"]), S(r["implication"]), C(r["severity"]), basis(r, figs_in(r["risk"], r["mechanic"], r["implication"]))]) for i, r in enumerate(sub["risks"], 1)]
    gap_rows = [(f"g{i:02d}", f"Gap {i}", [C(f"CP-2-GAP-{i:03d}"), S(g["gap"]), S(g["why_it_matters"]), S(g["affected_analysis"]), C(g["severity"]), S(g["action"]), basis(g, figs_in(g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"]))]) for i, g in enumerate(sub["gaps"], 1)]

    def lt(tid, trs, required):
        _, title, labels = CP2_REGS[tid]
        flds = FIELDS2[tid]
        out_rows = []
        for rid, lab, cells in trs:
            facts = [{"fact_id": f"{tid}.{rid}.{f}", "column": l, "text": c["text"], "status": "known", "cites": [], "value_class": "analyst_judgment" if c["judged"] else None, "limitation": None} for f, l, c in zip(flds, labels, cells)]
            out_rows.append({"row_id": rid, "label": lab, "facts": facts})
        return {"table_id": tid, "title": title, "row_header": "Item", "columns": [{"field": f, "label": l} for f, l in zip(flds, labels)], "rows": out_rows}

    tables = [
        cm.tables[0],  # T2.1 composed via Composer (row label below)
    ]
    tables[0]["rows"][0]["label"] = "Credit assessment"
    tables[0]["row_header"] = "Item"
    # Front tables are composed in this order by the core: thesis, strengths, weaknesses, T2.7, kf, T2.10 ... see order list
    def front_table(tid, title, lines):
        return {"table_id": tid, "title": title, "row_header": title, "columns": [{"field": "value", "label": "Value"}],
                "rows": [{"row_id": rid, "label": lab, "facts": [{"fact_id": f"{tid}.{rid}.value", "column": lab, "text": c["text"], "status": "known", "cites": [], "value_class": "analyst_judgment", "limitation": None}]} for rid, lab, c in lines]}

    tables += [
        front_table("cp2.thesis", "Thesis", front["cp2.thesis"]),
        front_table("cp2.strengths", "Strengths", front["cp2.strengths"]),
        front_table("cp2.weaknesses", "Weaknesses", front["cp2.weaknesses"]),
        lt("T2.7", labelled, True),
        lt("T2.10", kf_rows, True),
        front_table("cp2.key_findings", "Key findings", front["cp2.key_findings"]),
        lt("T2.11", risk_rows, True),
        lt("T2.12", gap_rows, False),
    ]
    # first-spelling order of CP-1 references = composition order (cp2_synthesis.py:582-592, 835-860)
    seq = [A["rationale"], A["limitation"], Th["text"], Th["limitation"]]
    for key in ("strengths", "weaknesses"):
        for p in sub[key]:
            seq += [p["label"], p["text"], p["limitation"]]
    seq += [f["text"] for f in sub["key_findings"]]
    for r in sub["risks"]:
        seq += [r["risk"], r["mechanic"], r["implication"]]
    for g in sub["gaps"]:
        seq += [g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"]]
    used = figs_in(*seq)
    if used:
        tables.append({
            "table_id": "cp1_references", "title": "CP-1 facts referenced in CP-2 text", "row_header": "CP-1 fact",
            "columns": [{"field": "value", "label": "Value"}],
            "rows": [{"row_id": f"ref{i:02d}", "label": f"<label and period of FIG:{n}>",
                      "facts": [{"fact_id": f"<fact_id of the CP-1 fact for FIG:{n}, bound at run time>", "column": "Value",
                                 "text": None, "spelled_as": D.FIGS[n][3], "status": "known",
                                 "note": "cp2_synthesis.py:837-857: the copy keeps the CP-1 fact's own fact_id and changes only table_id=cp1_references, row_id=refNN, field=value; the row's fact_ids are that id",
                                 "table_coordinate": f"cp1_references.ref{i:02d}.value",
                                 "cites": "<the CP-1 fact's own citations, bound at run time>",
                                 "value_class": "calculated", "limitation": None}]}
                     for i, n in enumerate(used, 1)],
        })
    return {
        "tables": tables, "front": front, "signals": sigs, "catalogue_size": len(cat),
        "figures_referenced": [{"name": n, "cp1_coordinate": D.FIGS[n][0], "oracle_ratio": D.FIGS[n][1], "unit_token": D.FIGS[n][2], "spelled": D.FIGS[n][3]} for n in used],
        "own_limitations": list(dict.fromkeys(cm.limitations)),
        "settled_limitations_own": list(dict.fromkeys([*cm.limitations, SYNTH])),
        "claims": [{"claim_id": "T2.1.assessment", "text": A["rationale"], "limitation": A["limitation"]}, *[{"claim_id": f"T2.10.kf{i:02d}", "text": f["text"]} for i, f in enumerate(sub["key_findings"], 1)]],
    }


# --- FP01 visible content -----------------------------------------------------------------------


def cell_view(f):
    if f["text"] is None:
        state = "not_meaningful" if f["status"] == "not_applicable" else "gap"
        return {"shown": "∅ G# n.m." if state == "not_meaningful" else "∅ G#", "state": state, "reason": f["limitation"]}
    return {"shown": f["text"], "state": "known", "synthetic_ref": bool(f["cites"]), "cites": f["cites"]}


def facts_of(exp, tid, row_id=None):
    t = next(t for t in exp["tables"] if t["table_id"] == tid)
    return [(r, f) for r in t["rows"] if row_id in (None, r["row_id"]) for f in r["facts"]]


def table_tab(exp, tid, label):
    t = next(t for t in exp["tables"] if t["table_id"] == tid)
    return {"tab": label, "row_header": t["row_header"], "columns": [c["label"] for c in t["columns"]],
            "rows": [{"row_id": r["row_id"], "label": r["label"], "cells": [cell_view(f) for f in r["facts"]]} for r in t["rows"]]}


def clip(s, n=140):
    return s if len(s) <= n else s[: n - 1] + "…"


def fp01(cp1a, cp2):
    comp = facts_of(cp1a, "company_description", "company")
    company_tab = {"tab": "Company", "row_header": None, "columns": ["Value"],
                   "rows": [{"row_id": f["fact_id"], "label": f["column"], "cells": [cell_view(f)]} for _, f in comp]}
    own = table_tab(cp1a, "ownership_register", "Ownership")
    summary = clip(f"{own['rows'][0]['label']}: " + ", ".join(c["shown"] for c in own["rows"][0]["cells"]))

    def lines(exp, tids):
        out = []
        for tid in tids:
            for r, f in facts_of(exp, tid):
                if f["text"] is None:
                    # report_view.py:1407-1410: an unlabelled gap line is "<fact label>:" then the gap spelling
                    spelling = "\u2205 G# n.m." if f["status"] == "not_applicable" else "\u2205 G#"
                    out.append({"text": f"{f['column']}: {spelling}", "kind": "gap", "reason": f["limitation"], "fact_id": f["fact_id"]})
                    continue
                out.append({"text": f["text"], "kind": "pen" if f["value_class"] == "analyst_judgment" else "text", "synthetic_ref": bool(f["cites"]), "fact_id": f["fact_id"]})
        return out

    tx_lines = lines(cp1a, ["transaction_summary", "events_timeline"])  # report_view.py:1651 summary = first line, clipped to 140
    sw = []
    for sec, tid in (("thesis", "cp2.thesis"), ("strengths", "cp2.strengths"), ("weaknesses", "cp2.weaknesses")):
        for r, f in facts_of(cp2, tid):
            sw.append({"section": sec, "label": r["label"], "text": f["text"], "kind": "pen"})
    return {
        "key-findings": {"title": "Key findings", "owner": "CP-2", "kind": "prose", "numbered": True, "state": "populated",
                         "lines": [{"n": i, "text": l["text"], "kind": "pen"} for i, l in enumerate(lines(cp2, ["cp2.key_findings"]), 1)]},
        "company-operating-model": {"title": "Company and operating model", "owner": "CP-1A", "kind": "keyvalue", "state": "populated",
                                    "primary": company_tab, "tabs": [table_tab(cp1a, "operating_model", "Operating model")]},
        "company-profile": {"title": "Company profile", "owner": "CP-1A", "kind": "keyvalue", "state": "collapsed", "summary": summary,
                            "primary": own, "tabs": [table_tab(cp1a, "revenue_business_mix", "Revenue and business mix")]},
        "strengths-weaknesses": {"title": "Strengths and weaknesses", "owner": "CP-2 · CP-6", "kind": "prose", "state": "populated", "lines": sw,
                                 "note": "Only CP-2 binds this block. In S1a CP-6 is not_in_pathway (registry.py:95-105, requested modules CP-1, CP-MODEL, CP-1A, CP-2), so it adds no line and the block's own head still reads CP-2 \u00b7 CP-6"},
        "transaction-summary": {"title": "Transaction summary and new debt issues", "owner": "Primary", "kind": "prose", "state": "collapsed",
                                "summary": clip(tx_lines[0]["text"]),
                                "lines": tx_lines,
                                "note": "Not one of the S1 named sections; shown because the CP-1A binding map places two registers here"},
    }


CP1_BIND = {"bind": "CP-1 head: its limitations then its inherited_limitations, in head order"}


def inheritance(cp0, cp1a, cp2):
    """execution.py:345-366 inherited_limitations over the bound inputs in order
    (execution.py:259-267: prepared-pack, required upstream in plan order, then the CP-1 context).

    CP-0 and CP-1A text is literal. CP-1 text is a CP-1 output (QA line, register, statement,
    narrative and gap-ledger limitations: canonical_tables.py:841-846, cp1_workflow.py:365-393,
    canonical_gaps.py:467-472) that depends on the QA score and cannot be derived without running
    CP-1; it is bound at run time. The filtering rule is pinned: each entry is kept once, at its
    first position, and dropped when the module's own list already holds it (own synthetic-case
    text, and any CP-1 entry equal to an earlier CP-0 entry)."""
    own1 = cp1a["settled_limitations"]
    own2 = cp2["settled_limitations_own"]
    inh1 = [t for t in dict.fromkeys([*cp0["limitations"]]) if t not in own1]
    inh2 = [t for t in dict.fromkeys([*cp0["limitations"], *own1, *inh1]) if t not in own2]
    return {
        "CP-1A": {"literal_head": inh1, "then": CP1_BIND, "order": "CP-0 limitations, then the CP-1 head entries; de-duplicated across both; own findings removed"},
        "CP-2": {"literal_head": [t for t in dict.fromkeys([*cp0["limitations"]]) if t not in own2], "then": CP1_BIND,
                 "literal_tail_after_CP-1": [t for t in dict.fromkeys([*own1, *inh1]) if t not in own2 and t not in cp0["limitations"]],
                 "order": "CP-0 limitations, CP-1 head entries, then CP-1A own and inherited limitations; de-duplicated; own findings removed"},
        "rule": "execution.py:345-366",
    }


def rails(cp1a, cp2, cp0):
    ev1 = ["credit_translation", "T2D.8", "T2D.9", "conflict_log", "source_classification", "T2D.1", "T2D.2", "T2D.3", "T2D.4", "T2D.5", "T2D.6", "T2D.7", "T2D.10", "cp1a.cp_model_snapshot_fields"]
    ev2 = ["T2.1", "T2.7", "T2.10", "T2.11", "cp1_references"]
    inh = inheritance(cp0, cp1a, cp2)
    return {
        "evidence": {"CP-1A": ev1, "CP-2": ev2, "note": "cp1_references (CP-2) lists the CP-1 facts the CP-2 text spells, in first-spelling order; CP-1A references none"},
        "limitations": {"CP-1A": ["gaps_ledger", "downstream_readiness", "T2D.11"], "CP-2": ["T2.12"],
                        "module_limitations": {"CP-0": cp0["limitations"], "CP-1A": {"own_settled": cp1a["settled_limitations"], "inherited": inh["CP-1A"]},
                                               "CP-2": {"own_settled": cp2["settled_limitations_own"], "inherited": inh["CP-2"]}},
                        "inheritance_rule": inh["rule"]},
    }


# --- CP-0 literal submission and expectations (readiness.py:37-87, 305-531) --------------------------

GAP_DESC = "Ownership and transaction content is absent from the business note, so CP-1A ownership and transaction rows are unsettled"


def cite(case, source_id, locator, quote):
    page = PAGES_BY_CASE[case][source_id][locator]
    assert norm(quote) in norm(page)
    return {"source_id": source_id, "source_sha256": CASE_SHA[case][source_id], "locator": locator, "quote": quote}


def cp0_submission(case):
    gap = case == "gap"
    ident = cite(case, "identity", "page:1", D.ID_ISSUER["quote"])
    fin = cite(case, "financial", "page:1", "Currency: USD; amounts in millions.")
    bus = cite(case, "business", "page:1", D.B1_SECTOR["quote"])
    bus_lim = [D.BUSINESS_GAP_LIMITATION] if gap else []
    all3 = ["identity", "financial", "business"]
    return {
        "pack_sha256": "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>",
        "objective": "Historical financial foundation, business context and credit synthesis",
        "reporting_period": "Reported FY2025, four calendar quarters and opening balance",
        "issuer_confirmed": True,
        "sources": [
            {"source_id": "identity", "document_family": "Identity note", "authority": "issuer", "entity": ISSUER,
             "period": "January 2026", "version_relationship": "Accompanying identity note", "fidelity": "verified",
             "citations": [ident], "limitations": []},
            {"source_id": "financial", "document_family": "Quarterly financial statements", "authority": "issuer", "entity": ISSUER,
             "period": "Four quarters in 2025", "version_relationship": "Unaudited quarterly source", "fidelity": "verified",
             "citations": [fin], "limitations": [D.LIMIT_FIN]},
            {"source_id": "business", "document_family": "Business note" if gap else "Business and ownership note", "authority": "issuer",
             "entity": ISSUER, "period": "January 2026", "version_relationship": "Issuer-authored note accompanying the statements",
             "fidelity": "verified", "citations": [bus], "limitations": bus_lim},
        ],
        "consumers": [
            {"module_id": "CP-1", "readiness": "READY_WITH_LIMITATIONS",
             "evidence_demand": "Located historical statements, facility terms, definitions and scope",
             "source_ids": ["identity", "financial"],
             "rationale": "The selected historical owner method can run with explicit source and scope limitations.",
             "citations": [ident, fin], "missing_source": None, "limitations": [D.LIMIT_FIN]},
            {"module_id": "CP-1A", "readiness": "READY_WITH_LIMITATIONS",
             "evidence_demand": "Located business, operating, ownership and transaction facts with quotes",
             "source_ids": all3,
             "rationale": ("The business and operating fact pack can be built from the located note; ownership and transaction rows will be unsettled."
                           if gap else "The business, ownership and transaction fact pack can be built from the located note with explicit source limitations."),
             "citations": [ident, fin, bus], "missing_source": None, "limitations": [D.LIMIT_FIN, *bus_lim]},
            {"module_id": "CP-2", "readiness": "READY_WITH_LIMITATIONS",
             "evidence_demand": "Settled CP-1 figures and CP-1A registers",
             "source_ids": all3,
             "rationale": "The synthesis can run on settled upstream registers with inherited limitations.",
             "citations": [ident, fin, bus], "missing_source": None, "limitations": [D.LIMIT_FIN, *bus_lim]},
        ],
        "gaps": ([{"gap_id": "missing-ownership-transaction", "kind": "scope", "severity": "material", "description": GAP_DESC,
                   "affected_modules": ["CP-1A", "CP-2"], "remediation": "Supply the ownership and transaction documents", "citations": []}]
                 if gap else []),
        "analysis": [{"claim_id": "source-assessment",
                      "text": ("Identity, financial and business operating sources are located; ownership and transaction content is absent."
                               if gap else "Located statements and the business note support historical, business and ownership analysis with limitations."),
                      "citations": [ident, fin, bus], "limitation": D.LIMIT_FIN}],
    }


# --- CP-1 source_context literal submission (source_context.py:41-139, validator :172-305) -----------
# Structure follows tests/test_financial_workflow.py:196-262 (context), with one added entry for the
# business source (validator source_context.py:183-187: every prepared source exactly once).
SC_ENTITY = {"entity_id", "name", "entity_type", "roles", "fiscal_year_end", "citations", "limitations"}
SC_SOURCE_REQ = {"source_id", "classification", "document_type", "published_on", "evidence_class", "evidence_rationale", "analytical_use", "citations", "event_scan", "event_scan_explanation"}
SC_SOURCE_ALL = SC_SOURCE_REQ | {"scopes", "event_ids", "event_scan_citations", "limitations"}
SC_SCOPE = {"scope_id", "entity_id", "period_label", "period_kind", "start_date", "end_date", "currency", "unit", "entity_perimeter", "accounting_basis", "citations"}


def cp1_source_context(case):
    gap = case == "gap"
    ident = cite(case, "identity", "page:1", D.ID_ISSUER["quote"])
    scope_cite = cite(case, "financial", "page:1", "The opening balance is December 31, 2024.")
    fin = cite(case, "financial", "page:1", "Currency: USD; amounts in millions.")
    noevent = cite(case, "financial", "page:1", "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt changes through January 10, 2026.")
    scopes = []
    for p in FIN["periods"]:
        scopes.append({"scope_id": p["period_id"], "entity_id": "issuer", "period_label": p["period_id"],
                       "period_kind": "period_end" if p["period_type"] == "PERIOD_END" else "historical_duration",
                       "start_date": p["start_date"], "end_date": p["end_date"], "currency": "USD", "unit": "MILLIONS",
                       "accounting_basis": "IFRS", "entity_perimeter": "consolidated group", "citations": [scope_cite]})
    bus_cite = cite(case, "business", "page:1", D.B1_SECTOR["quote"])
    business = {
        "source_id": "business", "classification": "nonfinancial",
        "document_type": "Business note" if gap else "Business and ownership note", "published_on": "2026-01-10",
        "evidence_class": "internal", "evidence_rationale": "Issuer-authored note without auditor or filing status",
        "analytical_use": "Business, operating, ownership and transaction context for CP-1A",
        "citations": [bus_cite],
    }
    if gap:
        # No explicit event disclosure in the gap note: the scan is not asserted (cf. the identity entry).
        business.update({"event_scan": "unassessed", "event_scan_explanation": "The note contains no disclosure about subsequent events", "limitations": [D.BUSINESS_GAP_LIMITATION]})
    else:
        # page:3 states that no change is announced or pending as of the as-of date: an explicit no-event disclosure.
        business.update({"event_scan": "no_events_identified", "event_scan_explanation": "Explicit no-event disclosure through as-of",
                         "event_scan_citations": [cite(case, "business", "page:3", D.B3_NO_TXN["quote"])]})
    return {
        "pack_sha256": "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>",
        "entities": [{"entity_id": "issuer", "name": ISSUER, "entity_type": "group", "roles": ["issuer"], "fiscal_year_end": "December 31",
                      "citations": [ident], "limitations": [D.LIMIT_FIN]}],
        "sources": [
            {"source_id": "identity", "classification": "nonfinancial", "document_type": "Identity note", "published_on": "2026-01-10",
             "evidence_class": "internal", "evidence_rationale": "Identity only", "analytical_use": "Issuer identity", "citations": [ident],
             "event_scan": "unassessed", "event_scan_explanation": "Identity is not event evidence"},
            {"source_id": "financial", "classification": "financial", "document_type": "Quarterly statements", "published_on": "2026-01-10",
             "evidence_class": "unaudited_without_auditor", "evidence_rationale": "No auditor report", "analytical_use": "Historical financial analysis",
             "citations": [fin], "scopes": scopes, "event_scan": "no_events_identified", "event_scan_explanation": "Explicit no-event disclosure through as-of",
             "event_scan_citations": [noevent], "limitations": [D.LIMIT_FIN]},
            business,
        ],
        "limitations": [D.LIMIT_FIN],
    }


def check_context(case, sub):
    where = f"{case}_cp1_source_context"
    if not set(sub) <= {"pack_sha256", "entities", "sources", "events", "limitations"}:
        problems.append(f"{where}: unknown top-level keys {sorted(set(sub))}")
    for e in sub["entities"]:
        if set(e) - SC_ENTITY:
            problems.append(f"{where}.entities: extra keys {sorted(set(e) - SC_ENTITY)}")
    ids = [x["source_id"] for x in sub["sources"]]
    if sorted(ids) != sorted(s for s, *_ in PACKS[case]) or len(set(ids)) != len(ids):
        problems.append(f"{where}: sources must assess every pack source exactly once, got {ids}")
    for x in sub["sources"]:
        if set(x) - SC_SOURCE_ALL or SC_SOURCE_REQ - set(x):
            problems.append(f"{where}.{x['source_id']}: keys extra {sorted(set(x) - SC_SOURCE_ALL)} missing {sorted(SC_SOURCE_REQ - set(x))}")
        if x["classification"] not in ("financial", "nonfinancial", "unassessed") or x["event_scan"] not in ("events_identified", "no_events_identified", "unassessed"):
            problems.append(f"{where}.{x['source_id']}: bad enum")
        if x["event_scan"] != "unassessed" and not x.get("event_scan_citations"):
            problems.append(f"{where}.{x['source_id']}: event scan needs located evidence (source_context.py:292-293)")
        for c in (*x["citations"], *x.get("event_scan_citations", [])):
            if c["source_id"] != x["source_id"]:
                problems.append(f"{where}.{x['source_id']}: cites another source")
            if norm(c["quote"]) not in norm(PAGES_BY_CASE[case][c["source_id"]][c["locator"]]):
                problems.append(f"{where}.{x['source_id']}: quote not on page")
        for sc in x.get("scopes", []):
            if set(sc) - SC_SCOPE:
                problems.append(f"{where}.scope {sc['scope_id']}: extra keys")


PLAN_ORDER = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]  # registry.py:108-124 over registry order (methodology.json)


def cp0_expected(case, sub):
    """readiness.py:408-531 build_readiness, transcribed."""
    pack = PACKS[case]
    facts = []

    def add(table, row, key, value, cites=()):
        facts.append({"fact_id": f"{table}.{row}.{key}", "text": value, "cites": [[c["source_id"], c["locator"]] for c in cites]})

    add("T1", "run", "objective", sub["objective"])
    add("T1", "run", "issuer", ISSUER)
    add("T1", "run", "reporting_period", sub["reporting_period"])
    add("T1", "run", "identity_gate", "confirmed" if sub["issuer_confirmed"] else "blocked")
    by = {a["source_id"]: a for a in sub["sources"]}
    for sid, name, status, lim in pack:
        a = by[sid]
        for key, value in (("family", a["document_family"]), ("entity", a["entity"] or "Unconfirmed"), ("period", a["period"] or "Unconfirmed"), ("version_relationship", a["version_relationship"])):
            add("P3", sid, key, value, a["citations"])
        add("P5", sid, "preparation", f"complete; fidelity {a['fidelity']}; {lim or 'No mechanical limitation'}")
        add("T2", sid, "source", f"{name}; {status}; SHA-256 {CASE_SHA[case][sid]}")
        add("T3", sid, "authority", a["authority"], a["citations"])
        for i, c in enumerate(a["citations"]):
            add("T6", sid, f"evidence_{i}", c["quote"], [c])
    commands = {}
    for c in sorted(sub["consumers"], key=lambda x: PLAN_ORDER.index(x["module_id"])):
        m = c["module_id"]
        add("T4", m, "demand", c["evidence_demand"], c["citations"])
        add("T4", m, "readiness", c["readiness"])
        add("T4", m, "rationale", c["rationale"], c["citations"])
        add("T8", m, "candidate_command", "Run " + m)
        commands[m] = "Run " + m if c["readiness"] in ("READY", "READY_WITH_LIMITATIONS") else "DO NOT RUN"
        add("T8", m, "exact_command", commands[m])
        add("T8", m, "sources", ", ".join(c["source_ids"]) or "None")
        lims = list(c["limitations"])
        for sid, name, status, lim in pack:
            if sid in c["source_ids"]:
                if lim:
                    lims.append(lim)
                lims.extend(by[sid]["limitations"])
        lims.extend(g["description"] for g in sub["gaps"] if m in g["affected_modules"])
        add("T8", m, "limits", "; ".join(dict.fromkeys(lims)) or "None identified")
        add("T8", m, "upstream", f"CP-0 {RUN_ID[case]}; analytical dependencies checked separately")
    for g in sub["gaps"]:
        add("T5", g["gap_id"], "gap", f"{g['kind']}/{g['severity']}: {g['description']}; affects {', '.join(g['affected_modules'])}; {g['remediation']}", g["citations"])
    if not sub["gaps"]:
        add("T5", "review", "gaps", "No gaps identified by this supplied review")
    add("T7", "run", "preparation", "<<PreparedPack.content_hash(), bound at run time>>")
    add("T7", "run", "method", "deploy-v-r14")
    add("T7", "run", "assertion_scope", "SOURCE_SUFFICIENCY_ONLY; CP_MODEL_INPUT_CONTRACT_NOT_EVALUATED")
    limitations = list(dict.fromkeys(
        [lim for _, _, _, lim in pack if lim]
        + [t for a in sub["sources"] for t in a["limitations"]]
        + [t for c in sub["consumers"] for t in c["limitations"]]
        + [g["description"] for g in sub["gaps"]]
        + [SYNTH]
    ))
    return {"status": "restricted", "why": "own limitations are non-empty (readiness.py:518-531; execution.py:451-457)",
            "live_consumers": ["CP-1", "CP-1A", "CP-2"], "plan_order": PLAN_ORDER,
            "exact_commands": commands, "limitations": limitations, "facts": facts}


RUN_ID = {"positive": "slice-snapshot-positive", "gap": "slice-snapshot-gap"}


# --- write -----------------------------------------------------------------------------------------


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if problems:
        print("INPUT PROBLEMS:")
        for p in problems:
            print(" ", p)
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    run_common = {"issuer_id": FIN["run"]["issuer_id"], "issuer_name": ISSUER, "as_of": AS_OF, "method_version": "deploy-v-r14",
                  "case_kind": "synthetic", "pathway": "credit_snapshot", "requested_modules": ["CP-1", "CP-MODEL", "CP-1A", "CP-2"]}
    manifest = {
        "schema_version": "snapshot-s1-cases/1",
        "scope": "S1 credit-snapshot slice inputs: CP-0 to CP-1 to CP-MODEL to CP-1A to CP-2 over the frozen financial sources plus one new literal business source",
        "status": "DRAFT for independent review; not adopted, not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "financial_baseline": {
            "path": "cases/financial/manifest.json", "manifest_sha256": FIN_SHA,
            "sources": [{"source_id": s, "sha256": fin_src[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; copied by reference, never edited"} for s in ("identity", "financial")],
            "oracle_pointers": ["q4_ltm_metric_oracle.total_leverage_reported", "q4_ltm_metric_oracle.net_leverage_reported", "q4_ltm_metric_oracle.interest_coverage_reported", "q4_ltm_metric_oracle.fcf_to_debt"],
        },
        "business_source": {
            "common": {"source_id": "business", "name": D.BUSINESS_NAME, "status": "ready", "media_type": "text/plain",
                       "extractor": "supplied-representation", "extraction_status": "complete",
                       "representation_scope": "Supplied located-page UTF-8 text only; not PDF or text_content extraction"},
            "positive": {"pages": [{"locator": loc, "text": text} for loc, text in D.BUSINESS_PAGES], "sha256": BUS_SHA, "pack_limitation": None},
            "gap": {"pages": [{"locator": loc, "text": text} for loc, text in D.BUSINESS_GAP_PAGES], "sha256": BUS_GAP_SHA,
                    "pack_limitation": D.BUSINESS_GAP_LIMITATION,
                    "derivation": "page:1 byte-identical to the positive page:1; page:2 keeps only the operating-model lines of the positive page:2; the positive page:2 ownership lines and all of page:3 (financing, transactions, history) are absent"},
            "consistency_with_frozen_financials": [
                "One operating segment Consolidated Operations (financial page:1); the note adds product lines without a revenue split",
                "Dividends paid in each quarter of 2025 (financial page:3 shows 2.25 per quarter, 9.00 for FY2025)",
                "Maintenance-only capital expenditure, no growth programme (financial page:1)",
                "No acquisition, disposal, financing or ownership change in 2025 and none pending at 2026-01-10 (financial page:1: no subsequent events through January 10, 2026)",
                "One senior secured term loan, final maturity December 31, 2029, no revolver (financial pages 1 and 5)",
                "No figure in the note restates a financial number; the only numbers are years, a date and counts in words",
            ],
        },
        "financial_pack_limitation": {"source_id": "financial", "text": D.LIMIT_FIN, "basis": "established pack construction, tests/test_financial_workflow.py:22, 48-52; applied to both cases (LEAD ruling on finding 4)"},
        "cases": [
            {"case_id": "snapshot-positive", "run": {"run_id": RUN_ID["positive"], **run_common},
             "pack_sources": [{"source_id": sid, "name": n, "status": st, "limitation": lim} for sid, n, st, lim in PACKS["positive"]],
             "business_source_sha256": BUS_SHA, "submissions": "cases/snapshot/submissions.json#positive"},
            {"case_id": "snapshot-gap-business-without-ownership-transaction", "run": {"run_id": RUN_ID["gap"], **run_common},
             "change": "business source present with page:1 unchanged, page:2 reduced to operating-model lines, no page:3: no ownership, dividend, transaction or history content; pack limitation as listed; identity and financial unchanged",
             "pack_sources": [{"source_id": sid, "name": n, "status": st, "limitation": lim} for sid, n, st, lim in PACKS["gap"]],
             "business_source_sha256": BUS_GAP_SHA, "submissions": "cases/snapshot/submissions.json#gap",
             "not_in_s1": "A wholly missing module source (CP-0 CONDITIONAL / DO NOT RUN, no ticket) is covered by cases/financial negative_case and is not repeated here"},
        ],
        "consumers_of_cp1a_for_this_plan": ["CP-2", "CP-MODEL"],
        "consumers_note": "Registry order. Adding CP-5 to requested_modules adds CP-5 between CP-2 and CP-MODEL and changes the T2D.10 and downstream_readiness rows; see open questions.",
    }
    submissions = {
        "schema_version": "snapshot-s1-submissions/1",
        "note": "Literal analyst submissions for the business_context and credit_synthesis steps. {{FIG:name}} marks a CP-1 figure reference to be replaced mechanically by {<actual CP-1 fact_id>|<unit_token>} after the CP-1 head is inspected; unreplaced it is malformed run text and fails closed. figures lists each name's CP-1 coordinate, oracle ratio and unit token.",
        "figures": {n: {"cp1_coordinate": v[0], "oracle_ratio": v[1], "unit_token": v[2], "spelled": v[3]} for n, v in D.FIGS.items()},
        "positive": {"readiness_review": cp0_submission("positive"), "cp1_source_context": cp1_source_context("positive"), "business_context": D.POSITIVE_CP1A, "credit_synthesis": D.POSITIVE_CP2},
        "gap": {"readiness_review": cp0_submission("gap"), "cp1_source_context": cp1_source_context("gap"), "business_context": D.GAP_CP1A, "credit_synthesis": D.GAP_CP2},
        "cp1_submission": "CP-1 runs with this literal source_context submission per case (positive.cp1_source_context, gap.cp1_source_context: identity, financial and business each assessed once) and the financial case's literal financials, narrative, readiness and quality submissions of tests/test_financial_workflow.py, unchanged except for the bound pack; those later stages are not restated here",
    }
    pos1, gap1 = cp1a_expected("positive", D.POSITIVE_CP1A), cp1a_expected("gap", D.GAP_CP1A)
    pos2, gap2 = cp2_expected(D.POSITIVE_CP2, pos1, "positive"), cp2_expected(D.GAP_CP2, gap1, "gap")
    pos0 = cp0_expected("positive", submissions["positive"]["readiness_review"])
    gap0 = cp0_expected("gap", submissions["gap"]["readiness_review"])
    for case, sub in (("positive", submissions["positive"]["readiness_review"]), ("gap", submissions["gap"]["readiness_review"])):
        CUR["case"] = case
        check_submission(f"{case}_cp0", sub, TOP_0, SECTION_0)
        check_context(case, submissions[case]["cp1_source_context"])
        for claim in sub["analysis"]:
            run_text_ok(f"{case}_cp0.analysis", claim["text"])
    if problems:
        print("INPUT PROBLEMS:")
        for p in problems:
            print(" ", p)
        sys.exit(1)
    execution = {
        "plan_order": PLAN_ORDER,
        "statuses_S1a": {"CP-0": "restricted", "CP-1": "restricted (financial precedent: restricted, adopted with source/scope restrictions)", "CP-MODEL": "restricted head over promoted CP-1 (financial precedent)", "CP-1A": "restricted", "CP-2": "restricted", "why": "synthetic case_kind (execution.py:441-457)"},
        "tool_use": {
            "CP-0": "pack tools (search_pack, read_pages) plus submit; the review cites located spans",
            "CP-1": {"positive": "CP-1 source_context: read_pages business page:1 and page:3 and search_pack over business before submit (page:1 backs the classification, page:3 the no_events_identified scan; live/tools.py:1082-1085)",
                     "gap": "CP-1 source_context cites business page:1 only for the classification (page:2 is the reduced operating-model page and is read as part of the source); event_scan is unassessed, so no search_pack over business is required"},
            "CP-1A": "pack tools plus the single submit step business_context; reads every pack source (registry.py:351-356 pack_sources; live/context.py:85-87 fallback, LEAD ruling Q3)",
            "CP-2": "submit only: no pack tools and no SOURCE block (registry.py:357-360); evidence is upstream heads only",
        },
        "consumption": {
            "CP-1A": "attempt inputs: prepared-pack, CP-0 head, and the CP-1 head as context (execution.py:226, 253-258) because CP-1 settles before CP-1A in plan order; figures only as {ref|unit} to accepted CP-1 facts",
            "CP-2": "attempt inputs: prepared-pack, CP-0, CP-1 and CP-1A heads, hash-bound (execution.py:247-249, 259-267); a stale or unrun required head refuses with 'Required upstream is unrun, stale or blocked' (execution.py:236-240)",
            "CP-MODEL": "requires CP-1 only (methodology.json); cp_model_workflow has no CP-1A path, so CP-MODEL does not read CP-1A and the CP-MODEL handoff row of CP-1A is analyst input only",
            "consumers_of_CP-2_in_S1a": "none: CP-3, CP-5 and CP-6 are not in S1a requested modules (CP-5 belongs to S1b)",
        },
        "gap_case_authorization": "CP-0 pins READY_WITH_LIMITATIONS for CP-1A, so T8 exact_command is 'Run CP-1A' and CP-2 is ticketed (LEAD ruling on review-precise-1 finding 1)",
    }
    expected = {
        "schema_version": "snapshot-s1-expected/2",
        "derivation": "Hand-transcribed composition rules applied to submissions.json by cases/snapshot/builder/build_s1_oracle.py (stdlib only; deploy_vii never imported or run). Numbers come only from cases/financial/manifest.json oracle objects; each is listed with its ratio. Rule sources: readiness.py:408-531 (CP-0), business_context.py:908-1728 (CP-1A), cp2_synthesis.py:185-883 (CP-2), report_view.py:1389-1451, 1618-1700 (FP01), display.py:36-52 (spelling), execution.py:345-366 (inheritance).",
        "cell_notation": {"text": "exact displayed text; null means unsettled", "status": "known | missing | not_applicable", "cites": "[source_id, locator] per citation, in order; the quote is in the submission row", "value_class": "analyst_judgment where the cell is model-written", "gap_cells": "render as the gap spelling with a report-wide G# numbered sequentially in the order of the facts of each module (LEAD ruling Q7); the number is not a literal here"},
        "row_ids": "r01.. in submission order; company, composite, d01..d09, kf01.., s01.., w01.., g01.., none for an empty register",
        "execution": execution,
        "CP-1": {"authorization": "T8 exact_command 'Run CP-1' on both cases",
                 "ratios": D.FIGS,
                 "basis": "metric_coordinate_rule (cases/financial/manifest.json): Q4 leverage, coverage and flow-to-debt recipes use twelve-month operands, so the four ratios are the LTM-basis (twelve months to Q4 2025) T4.10 facts, not the FY2025 reported-annual facts; the spelled values are equal either way, the basis cell and reference label differ",
                 "submission": "S1 ships its own literal source_context submission per case (submissions.json positive.cp1_source_context and gap.cp1_source_context) assessing identity, financial and business exactly once (source_context.py:183-187); the financial case's literal financials, narrative, readiness and quality submissions stay unchanged except for the bound pack",
                 "business_entry": {"positive": "classification nonfinancial, evidence_class internal, one cited page:1 quote, event_scan no_events_identified backed by the page:3 no-change statement; tool use: read_pages business page:1 and page:3 and search_pack over business before submit (live/tools.py:1082-1085)",
                                    "gap": "same classification and citation (page:1; the note has page:1 and page:2); event_scan unassessed because the reduced note holds no event disclosure, so no search_pack over business is required; source limitation carried"},
                 "limitations": "CP-1's own and inherited limitations are CP-1 outputs depending on the QA score; they are bound at run time (see inherited_limitations), not hand-derived"},
        "positive": {
            "figures_from_oracle": D.FIGS,
            "CP-0": pos0,
            "CP-1A": {**pos1}, "CP-2": {**pos2},
            "inherited_limitations": inheritance(pos0, pos1, pos2),
            "FP01": fp01(pos1, pos2), "rails": rails(pos1, pos2, pos0),
        },
        "gap_business_without_ownership_transaction": {
            "branch": "CP-0 READY_WITH_LIMITATIONS for CP-1A; CP-1A settles restricted with Insufficient Information rows for ownership and transaction (never a placeholder); CP-2 ticketed",
            "CP-0": gap0,
            "CP-1A": {**gap1}, "CP-2": {**gap2},
            "inherited_limitations": inheritance(gap0, gap1, gap2),
            "FP01": fp01(gap1, gap2), "rails": rails(gap1, gap2, gap0),
            "must_not_appear": ["a zero, N/A, TBD or empty string standing for ownership, shareholders or transaction", "any invented owner or transaction", "a CP-2 confidence of High"],
        },
    }
    dump(OUT / "manifest.json", manifest)
    dump(OUT / "submissions.json", submissions)
    dump(OUT / "expected.json", expected)
    print("business sha256", BUS_SHA, "gap", BUS_GAP_SHA)
    print("CP-1A positive tables", len(pos1["tables"]), "gap", len(gap1["tables"]))
    print("governance positive", pos1["governance"])
    print("governance gap", gap1["governance"])
    print("CP-2 signals positive", pos2["signals"], "gap", [s["ref"] for s in gap2["signals"]])


main()
