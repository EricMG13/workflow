"""Writes cases/cp3-cp6-owner/{manifest,submissions,expected}.json (stdlib only).

Independent transcription of the composition rules documented in src/deploy_vii/
cp3_relative_value.py, cp6_committee.py, readiness.py and business_context.py (read, never
imported or executed). It reads only data files: the frozen financial manifest and the three S1
oracle files, each checked against a pinned sha256 before use. Every checkable property of the
literal inputs (quotes on page, bare digits in run text, prohibited phrases, reference
existence, ordering, confidence caps) is asserted here, so an inconsistent input fails the build.

Run from the repository root:  python3 -I cases/cp3-cp6-owner/builder/build.py
"""

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp3-cp6-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    # rev 1 (review L2, M4): the two other data files the builder reads. methodology.json changes when the
    # CP-6 freeze registers T6-FINAL (ruling Q7); the pin is then moved with that change.
    "cases/snapshot/cp2-view-tree.json": "f739395cbcf30ae2af710d8423927a8f810c8c4b948c07c6e6583e2a3b86f446",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
}
S1_FILES = ("cases/snapshot/manifest.json", "cases/snapshot/submissions.json", "cases/snapshot/expected.json")


def sha_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load_pinned(rel):
    assert sha_file(rel) == PINS[rel], f"{rel}: sha256 differs from the pin"
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


FIN = load_pinned("cases/financial/manifest.json")
S1M = load_pinned("cases/snapshot/manifest.json")
S1S = load_pinned("cases/snapshot/submissions.json")
S1E = load_pinned("cases/snapshot/expected.json")
CP2_TREE = load_pinned("cases/snapshot/cp2-view-tree.json")

problems = []
ISSUER = FIN["run"]["issuer_name"]
ISSUER_ID = FIN["run"]["issuer_id"]
AS_OF = FIN["run"]["as_of"]
SYNTH = "Synthetic case; not real issuer qualification"
LIMIT_FIN = S1M["financial_pack_limitation"]["text"]
assert LIMIT_FIN == "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
NONE_STATED = "None stated"
LABEL_INS = " [Insufficient Information]"


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s)


def snake(label):
    return re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")


# --- sources -------------------------------------------------------------------------------------
fin_src = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in fin_src.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
BUS = S1M["business_source"]
BUS_PAGES = BUS["positive"]["pages"]
assert page_sha([p["text"] for p in BUS_PAGES]) == BUS["positive"]["sha256"]
BUS_NAME = BUS["common"]["name"]

MARKET_NAME = "Third-party loan market quotation sheet"
M_P1 = "\n".join(
    [
        "SYNTHETIC LOAN MARKET DESK",
        "Secondary loan quotation sheet",
        "Published January 10, 2026. Quotations are as of the close on January 9, 2026.",
        "This invented case is test data, not evidence about a real issuer.",
        "Instrument: Northbridge Term Loan, the senior secured term loan of Northbridge Synthetic Group, with final maturity on December 31, 2029.",
        "Dealer quotation on January 9, 2026: bid 98.50 and offer 99.25, expressed as a percentage of par.",
        "The quotation comes from one dealer. No trade in the instrument was reported in the 30 days to January 9, 2026.",
    ]
)
M_P2 = "\n".join(
    [
        "SYNTHETIC LOAN MARKET DESK",
        "Dealer commentary",
        "Published January 10, 2026.",
        "Dealers describe the indicative fair value of the Northbridge Term Loan as around 99.75. This is talk and not a quotation or a trade.",
        "The commentary does not describe the security package, guarantees or covenants of the instrument.",
        "No rating agency has assigned a rating to the instrument.",
    ]
)
MARKET_PAGES = [("page:1", M_P1), ("page:2", M_P2)]
for _l, _t in MARKET_PAGES:
    assert _t.isascii() and not _t.endswith("\n")
MARKET_SHA = page_sha([t for _, t in MARKET_PAGES])

Q_OBS = "Dealer quotation on January 9, 2026: bid 98.50 and offer 99.25, expressed as a percentage of par."
Q_TALK = "Dealers describe the indicative fair value of the Northbridge Term Loan as around 99.75."
Q_SHEET = "Secondary loan quotation sheet"

PAGES = {
    "identity": {p["locator"]: p["text"] for p in fin_src["identity"]["pages"]},
    "financial": {p["locator"]: p["text"] for p in fin_src["financial"]["pages"]},
    "business": {p["locator"]: p["text"] for p in BUS_PAGES},
    "market": dict(MARKET_PAGES),
}
SHA = {
    "identity": fin_src["identity"]["sha256"],
    "financial": fin_src["financial"]["sha256"],
    "business": BUS["positive"]["sha256"],
    "market": MARKET_SHA,
}
NAMES = {
    "identity": fin_src["identity"]["name"],
    "financial": fin_src["financial"]["name"],
    "business": BUS_NAME,
    "market": MARKET_NAME,
}


def pack_of(case):
    rows = [
        ("identity", NAMES["identity"], "ready", None),
        ("financial", NAMES["financial"], "ready", LIMIT_FIN),
        ("business", NAMES["business"], "ready", None),
    ]
    if case == "positive":
        rows.append(("market", NAMES["market"], "ready", None))
    return rows


def cite(sid, locator, quote):
    assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "source_sha256": SHA[sid], "locator": locator, "quote": quote}


def q(sid, locator, quote):
    """A submission Quote (no hash)."""
    assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "locator": locator, "quote": quote}


# --- runs ---------------------------------------------------------------------------------------
BASE_REQUEST = ["CP-1", "CP-MODEL", "CP-1A", "CP-2"]
RUNS = {
    "R3": {
        "requested_modules": [*BASE_REQUEST, "CP-3"],
        "plan_order": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3"],
        "live_consumers": ["CP-1", "CP-1A", "CP-2", "CP-3"],
        "cp1a_consumers": ["CP-2", "CP-3", "CP-MODEL"],
    },
    "R6": {
        "requested_modules": [*BASE_REQUEST, "CP-3", "CP-5", "CP-6"],
        "plan_order": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3", "CP-5", "CP-6"],
        "live_consumers": ["CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6"],
        "cp1a_consumers": ["CP-2", "CP-3", "CP-5", "CP-6", "CP-MODEL"],
    },
}
# Cross-check the hand-derived plan and consumer lists against the methodology data file (data
# only; the registry code is never run). Rounds: modules whose requirements are all done, in
# methodology order.
METH = load_pinned("src/deploy_vii/methodology.json")
METH_ORDER = [m["module_id"] for m in METH]
NOT_CONSUMERS = {"CP-0", "CP-MODEL", "CP-MEMO", "CP-OS"}
NOT_CP5_FAN_IN = {"CP-5", "CP-6", "CP-8", "CP-MEMO", "CP-OS"}


def meth_plan(requested):
    cat = {m["module_id"]: m for m in METH}
    selected = set(requested)
    pending = list(selected)
    while pending:
        for dep in cat[pending.pop()]["required"]:
            if dep not in selected:
                selected.add(dep)
                pending.append(dep)
    remaining = {m: set(cat[m]["required"]) | (set(cat[m]["optional"]) & selected) for m in selected}
    if "CP-5" in selected:
        remaining["CP-5"] |= selected - NOT_CP5_FAN_IN
    ordered = []
    while remaining:
        ready = [m for m in METH_ORDER if m in remaining and not remaining[m]]
        assert ready
        for m in ready:
            ordered.append(m)
            del remaining[m]
            for r in remaining.values():
                r.discard(m)
    return ordered, selected, cat


for _name, _run in RUNS.items():
    _plan, _sel, _cat = meth_plan(_run["requested_modules"])
    assert _plan == _run["plan_order"], (_name, _plan)
    assert [m for m in _plan if m not in NOT_CONSUMERS] == _run["live_consumers"], _name
    _cons = [
        m
        for m in METH_ORDER
        if m == "CP-MODEL" or (m in _sel and "CP-1A" in (*_cat[m]["required"], *_cat[m]["optional"]))
    ]
    assert _cons == _run["cp1a_consumers"], (_name, _cons)

RUN_IDS = {
    ("R3", "positive"): "slice-cp3-positive",
    ("R3", "gap"): "slice-cp3-gap",
    ("R6", "positive"): "slice-cp6-positive",
    ("R6", "gap"): "slice-cp6-gap",
}

# --- text checks (transcribed from the validators) -------------------------------------------
LABEL_RE = re.compile(
    r"(?:FY|CY) ?(?:(?:19|20)\d\d|\d\d)|\bQ[1-4]\b|\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December) \d{1,2}, (?:19|20)\d\d\b|\b(?:19|20)\d\d\b|\bCP-\d{1,2}[A-Z]?\b"
)
FIG_RE = re.compile(r"\{\{FIG:([a-z_]+)\}\}")
INSTRUMENT_NOUN = (
    r"(?:creditors?|lenders?|noteholders?|bondholders?|holders?|investors|claims?|bonds?|notes?|"
    r"loans?|instruments?|debts?|tranches?|securities|facility|revolver|lien)"
)
PEER = [
    "peer ranking", "ranks above", "ranks below", "ranks among", "ranked first", "ranked last",
    "top quartile", "best-in-class", "best in class", "outperforms peers", "underperforms peers",
    "versus peers", "relative to peers", "compared with peers", "against its peers",
]
RECOVERY = [
    "recovery conclusion", "expected recovery", "recovery rate", "recovery estimate",
    "recovery value of", "recover par",
]
RECOVERY_NEAR = [
    "full recovery", "will recover", "would recover", "expect(?:ed)? to recover",
    "recover(?:y|ies)? (?:of|in full)", "repaid in full",
]
ACTIONS_ALL = [
    "buy", "buys", "buying", "bought", "sell", "sells", "selling", "sold", "overweight",
    "underweight", "recommend", "recommends", "recommended", "recommending", "recommendation",
    "recommendations", "switch into", "switch out of", "switching into", "switching out of",
    "switches into", "switches out of", "switched into", "switched out of",
]
LIFTED = {"overweight", "underweight"} | {p for p in ACTIONS_ALL if p.startswith("recommend")}
CP6_ACTIONS = [p for p in ACTIONS_ALL if p not in LIFTED]
TRADE_TERMS = [
    "target price", "price target", "entry price", "exit price", "entry level", "exit level",
    "position size", "position sizing", "sized at", "size the position",
]
LEVEL_PHRASES = [
    "trades at", "traded at", "trading at", "quoted at", "is quoted", "are quoted", "priced at",
    "bid at", "offered at", "changed hands", "trading around", "trading near", "trades wide",
    "trades tight", "indicated at", "yields",
]
TALK_MARKERS = [
    "talk", "indicative", "guidance", "whisper", "initial price thoughts", "IPT", "IPTs",
    "proposed pricing", "expected pricing",
]


def word(p):
    return re.compile(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", re.IGNORECASE)


def near(p):
    bounded = rf"(?<![A-Za-z])(?:{p})(?![A-Za-z])"
    gap = r"(?:\W+\w+){0,4}?\W+"
    return re.compile(rf"{bounded}{gap}{INSTRUMENT_NOUN}\b|\b{INSTRUMENT_NOUN}{gap}{bounded}", re.IGNORECASE)


CP3_FORBID = [word(p) for p in (*PEER, *RECOVERY, *ACTIONS_ALL)] + [near(p) for p in RECOVERY_NEAR]
CP6_FORBID = [word(p) for p in (*PEER, *CP6_ACTIONS, *TRADE_TERMS)]
LEVELS = [word(p) for p in LEVEL_PHRASES]
TALK = [word(p) for p in TALK_MARKERS]


def run_text_ok(where, text, forbid, *, talk_row=False):
    t = FIG_RE.sub("", text).replace(ISSUER, "")
    t = LABEL_RE.sub("", t)
    if re.search(r"\d", t):
        problems.append(f"{where}: bare figure in {text!r}")
    if re.search(r"[{}\[\]]", t):
        problems.append(f"{where}: reserved character in {text!r}")
    if not text.strip():
        problems.append(f"{where}: empty text")
    for pat in forbid:
        if pat.search(text):
            problems.append(f"{where}: prohibited phrase {pat.pattern!r} in {text!r}")
    if talk_row:
        for pat in LEVELS:
            if pat.search(text):
                problems.append(f"{where}: indicative talk worded as a market level in {text!r}")


# --- cells and tables ---------------------------------------------------------------------------
def C(text, cites=(), judged=False, reason=None, status="known"):
    return {
        "text": text,
        "cites": [[c["source_id"], c["locator"]] for c in cites],
        "judged": judged,
        "reason": reason,
        "status": status,
    }


def fact(tid, rid, field, label, c):
    return {
        "fact_id": f"{tid}.{rid}.{field}",
        "column": label,
        "text": c["text"],
        "status": "known" if c["text"] is not None else c["status"],
        "cites": c["cites"],
        "value_class": "analyst_judgment" if c["judged"] else None,
        "limitation": c["reason"] if c["text"] is None else None,
    }


def table(tid, title, cols, rows, row_header="Item"):
    out_rows = []
    for rid, label, cells in rows:
        assert len(cells) == len(cols), (tid, rid, len(cells), len(cols))
        out_rows.append(
            {"row_id": rid, "label": label, "facts": [fact(tid, rid, f, l, c) for (f, l), c in zip(cols, cells)]}
        )
    return {
        "table_id": tid,
        "title": title,
        "row_header": row_header,
        "columns": [{"field": f, "label": l} for f, l in cols],
        "rows": out_rows,
    }


def front_table(tid, title, lines, row_header):
    """A Front Page table (cp3_relative_value.py _Composer.front, cp6_committee.py front): one `value`
    fact per line whose `column` is the ROW label, as the block shows it (review M1)."""
    return {
        "table_id": tid,
        "title": title,
        "row_header": row_header,
        "columns": [{"field": "value", "label": "Value"}],
        "rows": [
            {"row_id": rid, "label": label, "facts": [fact(tid, rid, "value", label, c)]} for rid, label, c in lines
        ],
    }


def trace(cites):
    seen = []
    for c in cites:
        k = f"{c['source_id']} {c['locator']}"
        if k not in seen:
            seen.append(k)
    return "; ".join(seen)


FIGS = S1S["figures"]
SPELL = {k: v["spelled"] for k, v in FIGS.items()}
assert SPELL == {
    "total_leverage_reported": "1.67x",
    "net_leverage_reported": "1.00x",
    "interest_coverage_reported": "6.00x",
    "fcf_to_debt": "18.0%",
}


class Out:
    """Spells figure references and records first-reference order, as the product composers."""

    def __init__(self):
        self.referenced = []
        self.limitations = []

    def text(self, value):
        def rep(m):
            name = m.group(1)
            assert name in SPELL, name
            if name not in self.referenced:
                self.referenced.append(name)
            return SPELL[name]

        return FIG_RE.sub(rep, value)

    def said(self, value, cites=()):
        return C(self.text(value), cites, judged=True)

    def limit(self, value):
        return C(self.text(value) if value else NONE_STATED)


def figs_in(*texts):
    found = []
    for t in texts:
        for m in FIG_RE.finditer(t or ""):
            if m.group(1) not in found:
                found.append(m.group(1))
    return found


def cp1_ref(name):
    return f"CP-1 <label and period of FIG:{name}>"


def references_table(out, module_label):
    refs = out.referenced
    if not refs:
        return None
    return {
        "table_id": "cp1_references",
        "title": f"CP-1 facts referenced in {module_label} text",
        "row_header": "CP-1 fact",
        "columns": [{"field": "value", "label": "Value"}],
        "rows": [
            {
                "row_id": f"ref{i:02d}",
                "label": f"<label and period of FIG:{n}>",
                "fact_binding": f"the CP-1 fact bound for FIG:{n} (own fact_id, value_class calculated, own citations)",
            }
            for i, n in enumerate(refs, 1)
        ],
    }


def dedupe(items):
    return list(dict.fromkeys(items))


# --- CP-2 catalogue (from the frozen S1 oracle; CP-2 is unchanged in these runs) -----------------
S1P = S1E["positive"]
CP2_TABLES = {t["table_id"]: t for t in S1P["CP-2"]["tables"]}
CP2_REGISTERS = ("T2.1", "T2.7", "T2.10", "T2.11", "T2.12")
CP2_CAT = {}  # ref -> {"label": row label, "name": challenge name, "side": side or None}
for _tid in CP2_REGISTERS:
    for _r in CP2_TABLES[_tid]["rows"]:
        if all(f["status"] != "known" for f in _r["facts"]):
            continue
        cells = {f["fact_id"].split(".")[-1]: f["text"] for f in _r["facts"]}
        CP2_CAT[f"{_tid}.{_r['row_id']}"] = {
            "label": _r["label"],
            "name": cells.get("label") or _r["label"],
            "side": cells.get("side"),
        }
CP2_CLAIMS = [c["claim_id"] for c in S1P["CP-2"]["claims"]]
assert CP2_CLAIMS == ["T2.1.assessment", "T2.10.kf01", "T2.10.kf02", "T2.10.kf03", "T2.10.kf04"]
assert list(CP2_CAT)[:3] == ["T2.1.assessment", "T2.7.thesis", "T2.7.s01"]
assert CP2_CAT["T2.7.s01"]["name"] == "Low reported leverage" and CP2_CAT["T2.7.s01"]["side"] == "Strength"
assert CP2_CAT["T2.7.w01"]["name"] == "Single maturity and no revolver"
assert CP2_CAT["T2.10.kf02"]["name"] == "Key finding 2" and CP2_CAT["T2.10.kf02"]["side"] is None

# =====================================================================================================
# CP-0 (readiness.py:408-531), generalised over pack, consumers and plan
# =====================================================================================================


def cp0_expected(pack, sub, run_id, plan_order, live_consumers):
    facts = []

    def add(table_, row, key, value, cites=()):
        facts.append({"fact_id": f"{table_}.{row}.{key}", "text": value,
                      "cites": [[c["source_id"], c["locator"]] for c in cites]})

    add("T1", "run", "objective", sub["objective"])
    add("T1", "run", "issuer", ISSUER)
    add("T1", "run", "reporting_period", sub["reporting_period"])
    add("T1", "run", "identity_gate", "confirmed" if sub["issuer_confirmed"] else "blocked")
    by = {a["source_id"]: a for a in sub["sources"]}
    assert [p[0] for p in pack] == [a["source_id"] for a in sub["sources"]]
    for sid, name, status, lim in pack:
        a = by[sid]
        for key, value in (("family", a["document_family"]), ("entity", a["entity"] or "Unconfirmed"),
                           ("period", a["period"] or "Unconfirmed"), ("version_relationship", a["version_relationship"])):
            add("P3", sid, key, value, a["citations"])
        add("P5", sid, "preparation", f"complete; fidelity {a['fidelity']}; {lim or 'No mechanical limitation'}")
        add("T2", sid, "source", f"{name}; {status}; SHA-256 {SHA[sid]}")
        add("T3", sid, "authority", a["authority"], a["citations"])
        for i, c in enumerate(a["citations"]):
            add("T6", sid, f"evidence_{i}", c["quote"], [c])
    assert sorted(c["module_id"] for c in sub["consumers"]) == sorted(live_consumers)
    commands = {}
    for c in sorted(sub["consumers"], key=lambda x: plan_order.index(x["module_id"])):
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
        add("T8", m, "upstream", f"CP-0 {run_id}; analytical dependencies checked separately")
    for g in sub["gaps"]:
        add("T5", g["gap_id"], "gap",
            f"{g['kind']}/{g['severity']}: {g['description']}; affects {', '.join(g['affected_modules'])}; {g['remediation']}",
            g["citations"])
    if not sub["gaps"]:
        add("T5", "review", "gaps", "No gaps identified by this supplied review")
    add("T7", "run", "preparation", "<<PreparedPack.content_hash(), bound at run time>>")
    add("T7", "run", "method", "deploy-v-r14")
    add("T7", "run", "assertion_scope", "SOURCE_SUFFICIENCY_ONLY; CP_MODEL_INPUT_CONTRACT_NOT_EVALUATED")
    limitations = dedupe(
        [lim for _, _, _, lim in pack if lim]
        + [t for a in sub["sources"] for t in a["limitations"]]
        + [t for c in sub["consumers"] for t in c["limitations"]]
        + [g["description"] for g in sub["gaps"]]
        + [SYNTH]
    )
    return {
        "status": "restricted",
        "why": "own limitations are non-empty (readiness.py:518-531; execution.py:451-457)",
        "live_consumers": live_consumers,
        "plan_order": plan_order,
        "exact_commands": commands,
        "limitations": limitations,
        "facts": facts,
    }


# Self-check: the transcription reproduces the frozen S1 positive CP-0 section from the frozen
# S1 positive literal review.
_s1_pack = [("identity", NAMES["identity"], "ready", None), ("financial", NAMES["financial"], "ready", LIMIT_FIN),
            ("business", NAMES["business"], "ready", None)]
_s1_pos = cp0_expected(_s1_pack, S1S["positive"]["readiness_review"], "slice-snapshot-positive",
                       ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"], ["CP-1", "CP-1A", "CP-2"])
for _k in ("status", "why", "live_consumers", "plan_order", "exact_commands", "limitations", "facts"):
    assert _s1_pos[_k] == S1P["CP-0"][_k], f"CP-0 transcription differs from the S1 oracle at {_k}"
assert S1P["CP-2"]["catalogue_size"] == 70


def s1_catalogue_size():
    n = 0
    for t in S1P["CP-1A"]["tables"]:
        for r in t["rows"]:
            if any(f["status"] == "known" for f in r["facts"]):
                n += 1
    return n


assert s1_catalogue_size() == 70, s1_catalogue_size()

GAP_MARKET = "No third-party market quotation source in the pack, so CP-3 market evidence is absent"


def readiness_review(case, run):
    sub = copy.deepcopy(S1S["positive"]["readiness_review"])
    ident = sub["sources"][0]["citations"][0]
    fin = sub["sources"][1]["citations"][0]
    bus = sub["sources"][2]["citations"][0]
    by_module = {c["module_id"]: c for c in sub["consumers"]}
    if case == "positive":
        mq = cite("market", "page:1", Q_OBS)
        sub["sources"].append({
            "source_id": "market", "document_family": "Loan market quotation sheet", "authority": "third_party",
            "entity": ISSUER, "period": "January 2026",
            "version_relationship": "Standalone third-party dealer quotation sheet",
            "fidelity": "verified", "citations": [mq], "limitations": [],
        })
        by_module["CP-1A"]["source_ids"] = ["identity", "financial", "business", "market"]
        sub["consumers"].append({
            "module_id": "CP-3", "readiness": "READY",
            "evidence_demand": "Located dated third-party market quotations for the issuer's instrument",
            "source_ids": ["market"],
            "rationale": "The relative value assessment can run on the located dealer quotation and commentary.",
            "citations": [mq], "missing_source": None, "limitations": [],
        })
    else:
        sub["consumers"].append({
            "module_id": "CP-3", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled upstream registers; no third-party market quotation is available",
            "source_ids": ["financial"],
            "rationale": "The relative value assessment can run on settled upstream registers and records the absence of market evidence.",
            "citations": [fin], "missing_source": None, "limitations": [GAP_MARKET],
        })
        sub["gaps"].append({
            "gap_id": "missing-market-source", "kind": "source", "severity": "material",
            "description": GAP_MARKET, "affected_modules": ["CP-3"],
            "remediation": "Supply a dated dealer quotation or trade record", "citations": [],
        })
    if run == "R6":
        for module, demand, rationale in (
            ("CP-5", "Settled upstream heads with their citations and limitations",
             "The evidence trace review can run on the settled heads with inherited limitations."),
            ("CP-6", "Settled CP-2, CP-3 and CP-5 heads",
             "The committee challenge can run on the settled heads with inherited limitations."),
        ):
            sub["consumers"].append({
                "module_id": module, "readiness": "READY_WITH_LIMITATIONS", "evidence_demand": demand,
                "source_ids": ["identity", "financial", "business"], "rationale": rationale,
                "citations": [ident, fin, bus], "missing_source": None, "limitations": [LIMIT_FIN],
            })
    return sub


# =====================================================================================================
# CP-1 source_context and CP-1A deltas
# =====================================================================================================


def cp1_source_context(case):
    sub = copy.deepcopy(S1S["positive"]["cp1_source_context"])
    if case == "positive":
        sub["sources"].append({
            "source_id": "market", "classification": "nonfinancial", "document_type": "Loan market quotation sheet",
            "published_on": "2026-01-10", "evidence_class": "external",
            "evidence_rationale": "Third-party dealer quotation and commentary without issuer or auditor status",
            "analytical_use": "Market evidence for relative value in CP-3",
            "citations": [cite("market", "page:1", Q_SHEET)],
            "event_scan": "unassessed", "event_scan_explanation": "A quotation sheet is not event evidence",
        })
    ids = [s["source_id"] for s in sub["sources"]]
    if ids != [p[0] for p in pack_of(case)]:
        problems.append(f"cp1_source_context[{case}]: sources must assess every pack source exactly once, got {ids}")
    for s in sub["sources"]:
        for c in (*s["citations"], *s.get("event_scan_citations", [])):
            if c["source_id"] != s["source_id"] or norm(c["quote"]) not in norm(PAGES[c["source_id"]][c["locator"]]):
                problems.append(f"cp1_source_context[{case}].{s['source_id']}: bad citation {c['locator']}")
    return sub


MARKET_SOURCE_USE = {
    "source_id": "market", "source_class": "third_party", "quality": "Medium", "period": "January 9, 2026",
    "entity_covered": "Northbridge Term Loan",
    "data_supplied": "Dealer quotation and dealer commentary on the term loan",
    "use": "Supplies market evidence for CP-3 and carries no issuer disclosure",
    "citations": [q("market", "page:1", Q_OBS)],
    "limitation": "Single dealer; no traded price",
}

BUS_P3 = "The only borrowing of the group is the Northbridge Term Loan, a senior secured term loan with final maturity on December 31, 2029."
CONSUMER_ADD = {
    "CP-3": {
        "module_id": "CP-3", "status": "READY_WITH_LIMITATIONS",
        "handoff_item": "The debt facility and business risk rows for instrument selection",
        "why_it_matters": "Instrument selection rests on the issuer's debt structure and the business risk rows",
        "gap": "Market evidence is outside CP-1A and ownership detail is incomplete",
        "required_action": "Cite CP-2 rows for the fundamental view and quote market sources for any market level",
        "citations": [q("business", "page:3", BUS_P3)], "flag_topics": [],
    },
    "CP-5": {
        "module_id": "CP-5", "status": "READY_WITH_LIMITATIONS",
        "handoff_item": "All CP-1A claims and registers for the evidence trace",
        "why_it_matters": "The integrity review checks every claim against its citations",
        "gap": "Undisclosed ownership and customer data are stated as gaps",
        "required_action": "Review each CP-1A claim against its cited source spans",
        "citations": [], "flag_topics": [],
    },
    "CP-6": {
        "module_id": "CP-6", "status": "READY_WITH_LIMITATIONS",
        "handoff_item": "Governance and credit translation rows for the committee challenge",
        "why_it_matters": "The challenge tests the credit view against the governance and disclosure rows",
        "gap": "Ownership and distribution policy terms are not disclosed",
        "required_action": "Challenge the synthesis using the governance and disclosure rows",
        "citations": [], "flag_topics": [],
    },
}


def cp1a_consumers(run):
    base = {c["module_id"]: c for c in S1S["positive"]["business_context"]["consumers"]}
    assert list(base) == ["CP-2", "CP-MODEL"]
    out = []
    for module in RUNS[run]["cp1a_consumers"]:
        row = copy.deepcopy(base.get(module) or CONSUMER_ADD[module])
        for field in ("handoff_item", "why_it_matters", "gap", "required_action"):
            run_text_ok(f"cp1a.consumers.{module}.{field}", row[field], [])
        for c in row["citations"]:
            assert norm(c["quote"]) in norm(PAGES[c["source_id"]][c["locator"]])
        out.append(row)
    return out


def srow(sid, name, u, pack_lim, cited):
    parts = ([u["limitation"]] if u["limitation"] else []) + ([pack_lim] if pack_lim else [])
    parts += [] if sid in cited else ["Not cited by any CP-1A row"]
    limit = C("; ".join(parts) or NONE_STATED)
    said = lambda t: C(t, u["citations"], judged=True)  # noqa: E731
    sc = [C(u["source_class"]), C(u["quality"]), said(u["use"]), limit]
    reg = [C(name), C(u["quality"]), said(u["period"]) if u["period"] else C(NONE_STATED),
           said(u["entity_covered"]), said(u["data_supplied"]), limit, said(u["use"])]
    return sc, reg


def cp1a_delta(case, run):
    tmpl = {t["table_id"]: t for t in S1P["CP-1A"]["tables"]}
    cons = cp1a_consumers(run)
    cols = lambda tid: [(c["field"], c["label"]) for c in tmpl[tid]["columns"]]  # noqa: E731
    delta = {"base": "cases/snapshot/expected.json#positive.CP-1A (every table not listed here is unchanged)", "tables": {}}
    if case == "positive":
        sc, reg = srow("market", NAMES["market"], MARKET_SOURCE_USE, None, {"market"})
        delta["tables"]["source_classification"] = {
            "append_row": table("source_classification", "Source classification", cols("source_classification"),
                                [("r04", "market", sc)], tmpl["source_classification"]["row_header"])["rows"][0]}
        delta["tables"]["T2D.1"] = {
            "append_row": table("T2D.1", "Source register", cols("T2D.1"), [("r04", "market", reg)],
                                tmpl["T2D.1"]["row_header"])["rows"][0]}
    said = lambda t: C(t, (), judged=True)  # noqa: E731
    flags = {}
    gov = [g for g in S1S["positive"]["business_context"]["governance_and_sponsor"] if g["kind"] == "behaviour_flag"]
    for i, g in enumerate(gov, 1):
        flags.setdefault(g["topic"], []).append(f"CP-2C-FLAG-{i:03d}")
    dr, t10 = [], []
    for i, c in enumerate(cons, 1):
        dr.append((f"r{i:02d}", c["module_id"], [C(c["status"]), said(c["gap"]), said(c["required_action"])]))
        named = [f for topic in c["flag_topics"] for f in flags[topic]]
        parts = ([f"Sources: {trace(c['citations'])}"] if c["citations"] else []) + ([f"Flags: {', '.join(dict.fromkeys(named))}"] if named else [])
        link = C("; ".join(parts) or "No source or behaviour flag backs this handoff row", c["citations"])
        t10.append((f"r{i:02d}", c["module_id"], [C(f"CP-2C-HANDOFF-{c['module_id']}"), said(c["handoff_item"]), said(c["why_it_matters"]),
                                                said(c["required_action"]), link, said(c["gap"])]))
    built_dr = table("downstream_readiness", "Downstream readiness", cols("downstream_readiness"), dr,
                     tmpl["downstream_readiness"]["row_header"])
    built_t10 = table("T2D.10", "Cross-module handoff register", cols("T2D.10"), t10, tmpl["T2D.10"]["row_header"])
    # The two S1 rows (CP-2, CP-MODEL) must keep their S1 cell values; only row ids and order move.
    for built, name in ((built_dr, "downstream_readiness"), (built_t10, "T2D.10")):
        s1rows = {r["label"]: r for r in tmpl[name]["rows"]}
        for row in built["rows"]:
            if row["label"] in s1rows:
                old = [(f["column"], f["text"], f["status"], f["cites"], f["value_class"]) for f in s1rows[row["label"]]["facts"]]
                new = [(f["column"], f["text"], f["status"], f["cites"], f["value_class"]) for f in row["facts"]]
                assert old == new, (name, row["label"])
    delta["tables"]["downstream_readiness"] = {"replace_table": built_dr}
    delta["tables"]["T2D.10"] = {"replace_table": built_t10}
    n_new_src = 1 if case == "positive" else 0
    delta["catalogue_size"] = 70 - 4 + 2 * len(cons) + 2 * n_new_src
    delta["consumers_judged"] = [c["module_id"] for c in cons]
    delta["claims_unchanged"] = True
    return delta


# =====================================================================================================
# Shared limitation inheritance (execution.py:345-366)
# =====================================================================================================
CP1_BIND = {"bind": "CP-1 head: its limitations then its inherited_limitations, in head order"}
CP5_BIND = {"bind": "CP-5 head: its limitations then its inherited_limitations, in head order"}


def inherited(own_settled, cp0_lims, own1a, own2, own3=None, cp5=False):
    seq = [*cp0_lims, "<CP1>", *own1a, *own2, *(own3 or []), *(["<CP5>"] if cp5 else [])]
    keep = [t for t in dedupe(seq) if t not in own_settled]
    head = [t for t in keep[: keep.index("<CP1>")]] if "<CP1>" in keep else keep
    tail_start = keep.index("<CP1>") + 1 if "<CP1>" in keep else len(keep)
    tail = [t for t in keep[tail_start:] if t != "<CP5>"]
    out = {"literal_head": head, "then": CP1_BIND, "literal_tail_after_CP-1": tail,
           "order": "inputs in plan order; each head contributes its limitations then its inherited_limitations; de-duplicated at first position; own findings removed"}
    if cp5:
        pos = keep.index("<CP5>") if "<CP5>" in keep else None
        out["CP-5_bind_position"] = "after the literal tail" if pos is not None else "absent"
        out["then_after_tail"] = CP5_BIND
    return out


S1_CP1A_OWN = S1P["CP-1A"]["settled_limitations"]
S1_CP2_OWN = S1P["CP-2"]["settled_limitations_own"]


# =====================================================================================================
# CP-3
# =====================================================================================================
KIND_LABEL = {"observed": "Observed", "indicative_talk": "Indicative talk", "none": "None"}
NO_MARKET = "No market evidence cited."
NO_BASIS = "No CP-2 row, market evidence or CP-1 figure cited"
CP3_REG = {
    "T3.1": ("Instrument relative value", [("facility_id", "Facility ID"), ("fundamental_view", "Fundamental view"),
                                           ("market_observation", "Market observation"), ("basis", "Basis"), ("limitation", "Limitation")]),
    "T3.3": ("Market evidence", [("source", "Source"), ("kind", "Kind"), ("quote", "Quote"), ("as_of", "As of"), ("limitation", "Limitation")]),
    "T3.4": ("Security selection preference", [("ordering", "Ordering"), ("rationale", "Rationale"), ("confidence", "Confidence"),
                                               ("basis", "Basis"), ("limitation", "Limitation")]),
    "T3.9": ("Relative value risks", [("risk", "Risk"), ("mechanic", "Risk mechanic"), ("implication", "Credit implication"),
                                      ("severity", "Severity"), ("basis", "Basis")]),
    "T3.10": ("Gaps ledger", [("gap_id", "Gap ID"), ("gap", "Gap"), ("why_it_matters", "Why it matters"),
                              ("affected_analysis", "Affected analysis"), ("severity", "Severity"), ("action", "Action")]),
}
FACILITY = {"facility_id": "term-loan", "name": "Northbridge Term Loan"}


def qkey(x):
    return (x["source_id"], x["locator"], x["quote"])


def check_cp3_submission(case, sub):
    where = f"cp3[{case}]"
    keys = {"instruments", "market_evidence", "preference", "risks", "gaps"}
    if set(sub) != keys:
        problems.append(f"{where}: keys {sorted(set(sub) ^ keys)}")
    kinds = {}
    for i, row in enumerate(sub["market_evidence"]):
        w = f"{where}.market_evidence[{i}]"
        if set(row) != {"source_id", "kind", "quote", "as_of", "limitation"}:
            problems.append(f"{w}: keys {sorted(row)}")
        run_text_ok(f"{w}.as_of", row["as_of"], CP3_FORBID, talk_row=row["kind"] == "indicative_talk")
        if row["limitation"]:
            run_text_ok(f"{w}.limitation", row["limitation"], CP3_FORBID, talk_row=row["kind"] == "indicative_talk")
        if row["kind"] == "none":
            if row["quote"] is not None or not row["limitation"]:
                problems.append(f"{w}: a none row quotes nothing and states its limitation")
            continue
        quote = row["quote"]
        if quote["source_id"] != row["source_id"] or row["source_id"] != "market":
            problems.append(f"{w}: source")
        if norm(quote["quote"]) not in norm(PAGES[quote["source_id"]][quote["locator"]]):
            problems.append(f"{w}: quote not on page")
        marked = [p.pattern for p in TALK if p.search(quote["quote"])]
        if row["kind"] == "observed" and marked:
            problems.append(f"{w}: observed row quotes indicative talk {marked}")
        if row["kind"] == "indicative_talk" and not marked:
            problems.append(f"{w}: indicative_talk row quotes no talk marker")
        if qkey(quote) in kinds:
            problems.append(f"{w}: duplicate quoted span")
        kinds[qkey(quote)] = row["kind"]
    strength = set(kinds.values())
    offered = {FACILITY["facility_id"]}

    def basis_ok(w, basis):
        for ref in basis["cp2_refs"]:
            if ref not in CP2_CAT:
                problems.append(f"{w}: unknown CP-2 row {ref}")
        for x in basis["quotes"]:
            if qkey(x) not in kinds:
                problems.append(f"{w}: quote not in market_evidence")

    ids = [r["facility_id"] for r in sub["instruments"]]
    if len(set(ids)) != len(ids) or set(ids) - offered:
        problems.append(f"{where}: instruments {ids}")
    for i, row in enumerate(sub["instruments"]):
        w = f"{where}.instruments[{i}]"
        if set(row) != {"facility_id", "fundamental_view", "market_observation", "basis", "limitation"}:
            problems.append(f"{w}: keys")
        basis_ok(w, row["basis"])
        market = row["market_observation"].strip().casefold() != "none"
        if market and not row["basis"]["quotes"]:
            problems.append(f"{w}: a market observation cites a market_evidence quote")
        talk_only = bool(row["basis"]["quotes"]) and {kinds.get(qkey(x)) for x in row["basis"]["quotes"]} <= {"indicative_talk"}
        for f in ("fundamental_view", "market_observation", "limitation"):
            if row[f]:
                run_text_ok(f"{w}.{f}", row[f], CP3_FORBID, talk_row=market and talk_only)
        if not (row["basis"]["cp2_refs"] or row["basis"]["quotes"] or figs_in(row["fundamental_view"], row["market_observation"], row["limitation"])):
            problems.append(f"{w}: no basis")
    pref = sub["preference"]
    if sorted(pref["ordering"]) != sorted(ids):
        problems.append(f"{where}.preference.ordering must hold each instrument exactly once")
    basis_ok(f"{where}.preference", pref["basis"])
    insufficient = pref["confidence"] == "Insufficient Information"
    if insufficient and not pref["limitation"]:
        problems.append(f"{where}.preference: Insufficient Information states its limitation")
    if not strength and not insufficient:
        problems.append(f"{where}.preference: Insufficient Information without market evidence")
    if not insufficient and not pref["basis"]["quotes"]:
        problems.append(f"{where}.preference: a preference cites a market_evidence quote")
    if pref["confidence"] == "High":
        problems.append(f"{where}.preference: CP-2 is restricted, so confidence is capped below High")
    for f in ("rationale", "limitation"):
        if pref[f]:
            run_text_ok(f"{where}.preference.{f}", pref[f], CP3_FORBID)
    for i, row in enumerate(sub["risks"]):
        w = f"{where}.risks[{i}]"
        for ref in row["cp2_refs"]:
            if ref not in CP2_CAT:
                problems.append(f"{w}: unknown CP-2 row {ref}")
        for f in ("risk", "mechanic", "implication"):
            run_text_ok(f"{w}.{f}", row[f], CP3_FORBID)
        if not row["cp2_refs"] and not figs_in(row["risk"], row["mechanic"], row["implication"]):
            problems.append(f"{w}: no basis")
    for i, g in enumerate(sub["gaps"]):
        for f in ("gap", "why_it_matters", "affected_analysis", "action"):
            run_text_ok(f"{where}.gaps[{i}].{f}", g[f], CP3_FORBID)
    for f in figs_in(json.dumps(sub)):
        assert f in SPELL


def cp3_submission(case):
    if case == "positive":
        obs, talk = q("market", "page:1", Q_OBS), q("market", "page:2", Q_TALK)
        return {
            "instruments": [{
                "facility_id": "term-loan",
                "fundamental_view": "The only instrument is a senior secured term loan, and with total leverage of {{FIG:total_leverage_reported}}, net leverage of {{FIG:net_leverage_reported}} and interest cover of {{FIG:interest_coverage_reported}} the CP-2 view supports a moderate, provisional credit assessment for it.",
                "market_observation": "One dealer quotation sits just below par and is the only observed level; indicative dealer talk sits a little higher and is talk, not a quotation.",
                "basis": {"cp2_refs": ["T2.11.r01", "T2.1.assessment", "T2.7.s01"], "quotes": [obs, talk]},
                "limitation": "A single dealer quotation, no reported trade and one instrument, so the level is not a market consensus",
            }],
            "market_evidence": [
                {"source_id": "market", "kind": "observed", "quote": obs, "as_of": "January 9, 2026",
                 "limitation": "Single dealer quotation, not a traded price"},
                {"source_id": "market", "kind": "indicative_talk", "quote": talk, "as_of": "January 10, 2026",
                 "limitation": "Dealer talk, not a quotation or a trade"},
            ],
            "preference": {
                "ordering": ["term-loan"],
                "rationale": "With one instrument the ordering is trivial; the observed quotation just below par and the CP-2 low-leverage view are consistent with fair compensation, and nothing here suggests the loan is mispriced.",
                "basis": {"cp2_refs": ["T2.1.assessment", "T2.7.s01"], "quotes": [obs, talk]},
                "confidence": "Medium",
                "limitation": "One dealer quotation and one instrument, so the preference is provisional",
            },
            "risks": [{
                "risk": "Thin market evidence",
                "mechanic": "One dealer quotation and dealer talk are the only market evidence, so the observed level can move without a trade",
                "implication": "Relative value conclusions stay provisional until more quotations or trades are available",
                "severity": "Material", "cp2_refs": ["T2.11.r01"],
            }],
            "gaps": [
                {"gap": "Only one dealer quotation and no traded price",
                 "why_it_matters": "The observed level may not be a market consensus",
                 "affected_analysis": "Market observation and security selection", "severity": "Material",
                 "action": "Obtain further dated dealer quotations or a trade record"},
                {"gap": "Only one instrument exists, so no intra-issuer comparison is possible",
                 "why_it_matters": "Relative value across the capital structure cannot be assessed",
                 "affected_analysis": "Security selection", "severity": "Minor",
                 "action": "Revisit if the issuer adds debt instruments"},
            ],
        }
    return {
        "instruments": [{
            "facility_id": "term-loan",
            "fundamental_view": "The only instrument is a senior secured term loan, and with total leverage of {{FIG:total_leverage_reported}}, net leverage of {{FIG:net_leverage_reported}} and interest cover of {{FIG:interest_coverage_reported}} the CP-2 view supports a moderate, provisional credit assessment for it.",
            "market_observation": "none",
            "basis": {"cp2_refs": ["T2.11.r01", "T2.1.assessment", "T2.7.s01"], "quotes": []},
            "limitation": "No market level is available for the instrument",
        }],
        "market_evidence": [
            {"source_id": "none", "kind": "none", "quote": None, "as_of": "Not available",
             "limitation": "No third-party market source in the pack"},
        ],
        "preference": {
            "ordering": ["term-loan"],
            "rationale": "With no market evidence the relative value of the instrument is not assessed, although the CP-2 view is unchanged.",
            "basis": {"cp2_refs": ["T2.1.assessment"], "quotes": []},
            "confidence": "Insufficient Information",
            "limitation": "No observed or indicative market evidence reached CP-3",
        },
        "risks": [{
            "risk": "No market evidence",
            "mechanic": "Without a dated quotation the market view of the loan cannot be compared with the fundamental view",
            "implication": "Security selection cannot be supported until market evidence is supplied",
            "severity": "Material", "cp2_refs": ["T2.11.r01"],
        }],
        "gaps": [{
            "gap": "No third-party market source in the pack",
            "why_it_matters": "Relative value and security selection cannot be assessed",
            "affected_analysis": "Relative value and security selection", "severity": "Critical",
            "action": "Supply a dated dealer quotation or trade record",
        }],
    }


def cp3_expected(case, sub):
    check_cp3_submission(case, sub)
    out = Out()
    kinds, cites = {}, {}
    for row in sub["market_evidence"]:
        if row["quote"]:
            kinds[qkey(row["quote"])] = row["kind"]
            cites[qkey(row["quote"])] = cite(row["quote"]["source_id"], row["quote"]["locator"], row["quote"]["quote"])

    def cited(quotes):
        seen, res = set(), []
        for x in quotes:
            c = cites[qkey(x)]
            if qkey(x) not in seen:
                seen.add(qkey(x))
                res.append(c)
        return res

    def basis_cell(cp2_refs, quotes, texts):
        parts = [f"CP-2 {ref} ({CP2_CAT[ref]['label']})" for ref in CP2_CAT if ref in set(cp2_refs)]
        parts += [f"Market evidence {x['source_id']} {x['locator']} ({KIND_LABEL[kinds[qkey(x)]].lower()})"
                  for x in dedupe_q(quotes)]
        parts += [cp1_ref(n) for n in figs_in(*texts)]
        return C("; ".join(parts) or NO_BASIS)

    def dedupe_q(quotes):
        seen, res = set(), []
        for x in quotes:
            if qkey(x) not in seen:
                seen.add(qkey(x))
                res.append(x)
        return res

    # own limitations, in composition order
    for g in sub["gaps"]:
        out.limitations.append(f"Gap ({g['severity']}): {out.text(g['gap'])}")
    strength = set(kinds.values())
    if not strength:
        out.limitations.append("No observed or indicative market evidence: relative value is not assessed")
    elif strength == {"indicative_talk"}:
        out.limitations.append("Market evidence is indicative talk only, not an observed market level")
    tables, lines = [], []
    # T3.1
    rows = []
    for i, row in enumerate(sub["instruments"], 1):
        rid, name = f"i{i:02d}", FACILITY["name"]
        view = out.text(row["fundamental_view"])
        none = row["market_observation"].strip().casefold() == "none"
        market = NO_MARKET if none else out.text(row["market_observation"])
        basis = basis_cell(row["basis"]["cp2_refs"], row["basis"]["quotes"],
                           [row["fundamental_view"], row["market_observation"], row["limitation"] or ""])
        rows.append((rid, name, [C(row["facility_id"]), C(view, judged=True), C(market, judged=not none), basis, out.limit(row["limitation"])]))
        lines.append((rid, name, C(f"{name}: {view} Market: {market}", judged=True)))
    t, cols = CP3_REG["T3.1"]
    tables.append(table("T3.1", t, cols, rows))
    # T3.3
    rows = []
    for i, row in enumerate(sub["market_evidence"], 1):
        x = row["quote"]
        rows.append((f"m{i:02d}", f"Market evidence {i}", [
            C(row["source_id"]), C(KIND_LABEL[row["kind"]]),
            C(x["quote"], [cites[qkey(x)]]) if x else C(NONE_STATED),
            out.said(row["as_of"]), out.limit(row["limitation"])]))
    t, cols = CP3_REG["T3.3"]
    tables.append(table("T3.3", t, cols, rows))
    # T3.4
    pref = sub["preference"]
    ordering = " > ".join(FACILITY["name"] for _ in pref["ordering"]) or "No ordering"
    rationale = out.text(pref["rationale"]) + (LABEL_INS if pref["confidence"] == "Insufficient Information" else "")
    basis = basis_cell(pref["basis"]["cp2_refs"], pref["basis"]["quotes"], [pref["rationale"], pref["limitation"] or ""])
    t, cols = CP3_REG["T3.4"]
    tables.append(table("T3.4", t, cols, [("preference", "Preference", [
        C(ordering, judged=True), C(rationale, judged=True), C(pref["confidence"]), basis, out.limit(pref["limitation"])])]))
    if pref["confidence"] == "Insufficient Information":
        out.limitations.append(f"Relative value preference is Insufficient Information: {out.text(pref['limitation'] or '')}")
    preference_line = C(f"Preference: {ordering}. {rationale}", judged=True)
    # T3.9, T3.10
    t, cols = CP3_REG["T3.9"]
    rows = []
    for i, r in enumerate(sub["risks"], 1):
        rows.append((f"r{i:02d}", f"Risk {i}", [out.said(r["risk"]), out.said(r["mechanic"]), out.said(r["implication"]),
                                                C(r["severity"]), basis_cell(r["cp2_refs"], [], [r["risk"], r["mechanic"], r["implication"]])]))
    tables.append(table("T3.9", t, cols, rows))
    t, cols = CP3_REG["T3.10"]
    rows = []
    for i, g in enumerate(sub["gaps"], 1):
        rows.append((f"g{i:02d}", f"Gap {i}", [C(f"CP-3-GAP-{i:03d}"), out.said(g["gap"]), out.said(g["why_it_matters"]),
                                               out.said(g["affected_analysis"]), C(g["severity"]), out.said(g["action"])]))
    tables.append(table("T3.10", t, cols, rows))
    # front table
    front = [("preference", "Preference", preference_line), *lines]
    tables.append(front_table("cp3.relative_value", "Relative value", front, "Relative value"))
    refs = references_table(out, "CP-3")
    if refs:
        tables.append(refs)
    claims = [{"claim_id": "T3.4.preference", "text": pref["rationale"], "limitation": pref["limitation"],
               "cites": [[c["source_id"], c["locator"]] for c in cited(pref["basis"]["quotes"])]}]
    for i, row in enumerate(sub["instruments"], 1):
        if row["market_observation"].strip().casefold() != "none":
            claims.append({"claim_id": f"T3.1.i{i:02d}", "text": row["market_observation"], "limitation": row["limitation"],
                           "cites": [[c["source_id"], c["locator"]] for c in cited(row["basis"]["quotes"])]})
    own = dedupe(out.limitations)
    cat = {}
    for tb in tables:
        if tb["table_id"] in CP3_REG:
            for r in tb["rows"]:
                if any(f["status"] == "known" for f in r["facts"]):
                    cat[f"{tb['table_id']}.{r['row_id']}"] = r["label"]
    return {
        "tables": tables, "claims": claims, "own_limitations": own,
        "settled_limitations": dedupe([*own, SYNTH]),
        "catalogue": cat, "referenced": out.referenced, "front_lines": [(rid, label, c["text"]) for rid, label, c in front],
        "claim_rows": [c["claim_id"] for c in claims],
    }


# =====================================================================================================
# CP-6
# =====================================================================================================
CP6_FRONT = {
    "cp6.thesis_challenge": "Thesis challenge",
    "cp6.strength_challenges": "Strength challenges",
    "cp6.weakness_challenges": "Weakness challenges",
    "cp6.committee_challenge": "Committee challenge",
}
SIDE_TABLE = {"Thesis": "cp6.thesis_challenge", "Strength": "cp6.strength_challenges", "Weakness": "cp6.weakness_challenges"}
CP6_REG = {
    "T6-FINAL": ("Final bias", [("action_bias", "Action bias"), ("rationale", "Rationale"), ("conditions", "Conditions"),
                                ("confidence", "Confidence"), ("basis", "Basis"), ("limitation", "Limitation")]),
    "T6A.4": ("Bear cross-examination", [("thesis_ref", "CP-2 row"), ("counter_case", "Counter-case"), ("evidence_for", "Evidence for"),
                                         ("evidence_against", "Evidence against"), ("would_change_view", "What would change the view"), ("basis", "Basis")]),
    "T6A.6": ("Chair evidence weighting: recovery view", [("subject", "Subject"), ("view", "View"), ("confidence", "Confidence"),
                                                          ("basis", "Basis"), ("limitation", "Limitation")]),
    "T6A.7": ("Debate resolution matrix: committee risks", [("risk", "Risk"), ("mechanic", "Risk mechanic"), ("implication", "Credit implication"),
                                                            ("severity", "Severity"), ("basis", "Basis")]),
    "T6A.11": ("Gaps ledger", [("gap_id", "Gap ID"), ("gap", "Gap"), ("why_it_matters", "Why it matters"),
                               ("affected_analysis", "Affected analysis"), ("severity", "Severity"), ("action", "Action")]),
}
CONFIDENCES = ["Insufficient Information", "Low", "Medium", "High"]
NO_BASIS6 = "No CP-2, CP-3 or CP-5 row or CP-1 figure cited"
FINDINGS_SUFFIX = "{{CP5_FINDINGS_SUFFIX}}"


def call_scale(conf):
    return 5 if conf == "High" else CONFIDENCES.index(conf) + 1


def b(cp2=(), cp3=(), cp5=()):
    return {"cp2_refs": list(cp2), "cp3_refs": list(cp3), "cp5_refs": list(cp5)}


def cp6_submission(case):
    c_thesis = {
        "thesis_ref": "T2.7.thesis",
        "counter_case": "The thesis may overstate resilience, because one maturity, no revolver and quarterly dividends leave liquidity dependent on steady cash generation.",
        "evidence_for": "Total leverage of {{FIG:total_leverage_reported}} and interest cover of {{FIG:interest_coverage_reported}} support the thesis.",
        "evidence_against": "Dividends continue while their funding source is undisclosed and the statements are unaudited.",
        "would_change_view": "Covenant terms with little headroom or a fall in cash generation would weaken the thesis.",
        "basis": b(cp2=["T2.7.thesis", "T2.11.r01"], cp3=["T3.9.r01"]),
    }
    c_s01 = {
        "thesis_ref": "T2.7.s01",
        "counter_case": "Low leverage on reported EBITDA may flatter the credit if the unaudited earnings prove weaker, since net leverage of {{FIG:net_leverage_reported}} rests on the same figures.",
        "evidence_for": "Total leverage is {{FIG:total_leverage_reported}} and net leverage is {{FIG:net_leverage_reported}} on reported figures.",
        "evidence_against": "No audit report confirms the earnings behind the ratios.",
        "would_change_view": "An audit report that confirms earnings would remove this challenge.",
        "basis": b(cp2=["T2.7.s01"]),
    }
    c_w01 = {
        "thesis_ref": "T2.7.w01",
        "counter_case": "The single maturity may be less of a weakness if cash keeps building, since the term loan is the only borrowing and no other claim competes for repayment.",
        "evidence_for": "All debt is one senior secured term loan with no revolver.",
        "evidence_against": "Free cash flow of {{FIG:fcf_to_debt}} of debt supports servicing the loan before maturity.",
        "would_change_view": "A refinancing plan or a revolver would reduce the weakness; a drop in cash generation would raise it.",
        "basis": b(cp2=["T2.7.w01"], cp3=["T3.1.i01"]),
    }
    c_kf02 = {
        "thesis_ref": "T2.10.kf02",
        "counter_case": "Refinancing risk at the single maturity depends on market access, and the dealer quotation just below par suggests the market sees the loan as fairly priced rather than stressed.",
        "evidence_for": "The term loan matures on a single date with no revolver.",
        "evidence_against": "The only market evidence is one dealer quotation and dealer talk.",
        "would_change_view": "A wider quotation or a failed refinancing would strengthen the finding.",
        "basis": b(cp2=["T2.10.kf02"], cp3=["T3.3.m01"]),
    }
    recovery = {
        "subject": "Recovery in a default",
        "view": "No recovery view is stated because no CP-4 legal or covenant evidence reached the committee through CP-5",
        "confidence": "Insufficient Information",
        "limitation": "CP-4 is not in this run, so no recovery evidence exists",
        "basis": b(),
    }
    gap = {
        "gap": "No legal or covenant analysis reached the committee",
        "why_it_matters": "Recovery and covenant headroom cannot be assessed",
        "affected_analysis": "Recovery view and covenant headroom", "severity": "Material",
        "action": "Run CP-4 on the legal sources",
    }
    if case == "positive":
        return {
            "recommendation": {
                "action_bias": "Neutral",
                "rationale": "The credit is sound on reported figures, with total leverage of {{FIG:total_leverage_reported}} and interest cover of {{FIG:interest_coverage_reported}}, and the single dealer quotation sits just below par, so the committee holds a Neutral bias rather than a positive or negative one.",
                "conditions": "The Neutral bias holds while leverage and cover stay near current levels and further dealer quotations confirm the level; it would move on covenant terms with little headroom or a sharp move in the quotation.",
                "confidence": "Medium",
                "limitation": "One dealer quotation, no traded price, no covenant terms and unaudited statements",
                "basis": b(cp2=["T2.1.assessment", "T2.10.kf01"], cp3=["T3.4.preference", "T3.1.i01"]),
            },
            "thesis_challenges": [c_w01, c_thesis, c_kf02, c_s01],
            "recovery_view": [recovery],
            "risks": [{
                "risk": "Thin market evidence",
                "mechanic": "One dealer quotation and dealer talk are the only market evidence, so the observed level can move without a trade",
                "implication": "Any view on pricing stays provisional until more quotations or trades are available",
                "severity": "Material", "basis": b(cp2=["T2.11.r01"], cp3=["T3.9.r01"]),
            }],
            "gaps": [gap],
        }
    return {
        "recommendation": {
            "action_bias": "Insufficient Information",
            "rationale": "The committee records no action bias because relative value rests on no market evidence, even though leverage of {{FIG:total_leverage_reported}} and cover of {{FIG:interest_coverage_reported}} support the credit.",
            "conditions": "An action bias can be stated once a dated dealer quotation or trade record is supplied.",
            "confidence": "Insufficient Information",
            "limitation": "No observed or indicative market evidence reached CP-3",
            "basis": b(cp2=["T2.1.assessment"], cp3=["T3.4.preference"]),
        },
        "thesis_challenges": [c_s01, c_thesis],
        "recovery_view": [recovery],
        "risks": [{
            "risk": "No market evidence",
            "mechanic": "Without a dated quotation the committee cannot compare the market view of the loan with the fundamental view",
            "implication": "No action bias can be supported until market evidence is supplied",
            "severity": "Material", "basis": b(cp2=["T2.11.r01"], cp3=["T3.9.r01"]),
        }],
        "gaps": [gap],
    }


def check_cp6_submission(case, sub, cp3):
    where = f"cp6[{case}]"
    if set(sub) != {"recommendation", "thesis_challenges", "recovery_view", "risks", "gaps"}:
        problems.append(f"{where}: keys")
    cp3_cat = cp3["catalogue"]

    def basis_ok(w, bs):
        for ref in bs["cp2_refs"]:
            if ref not in CP2_CAT:
                problems.append(f"{w}: unknown CP-2 row {ref}")
        for ref in bs["cp3_refs"]:
            if ref not in cp3_cat:
                problems.append(f"{w}: unknown CP-3 row {ref}")
        if bs["cp5_refs"]:
            problems.append(f"{w}: cp5_refs are bound at run time and are not used by this oracle")

    rec = sub["recommendation"]
    insufficient = rec["action_bias"] == "Insufficient Information"
    if insufficient != (rec["confidence"] == "Insufficient Information"):
        problems.append(f"{where}: action_bias and confidence are Insufficient Information together")
    if insufficient and not rec["limitation"]:
        problems.append(f"{where}: Insufficient Information states its limitation")
    forced = cp3_forces_insufficient(cp3)
    if forced and not insufficient:
        problems.append(f"{where}: CP-3 forces Insufficient Information: {forced}")
    if not forced and insufficient:
        problems.append(f"{where}: Insufficient Information without a forcing reason is allowed but this oracle expects a bias")
    if rec["confidence"] == "High":
        problems.append(f"{where}: CP-5 is restricted, so confidence is capped below High")
    basis_ok(f"{where}.recommendation", rec["basis"])
    claim_rows = {("CP-2", c) for c in CP2_CLAIMS} | {("CP-3", c) for c in cp3["claim_rows"]}
    cited = [("CP-2", r) for r in rec["basis"]["cp2_refs"]] + [("CP-3", r) for r in rec["basis"]["cp3_refs"]]
    support = [k for k in dedupe(cited) if k in claim_rows]
    if not insufficient and not support and not figs_in(rec["rationale"], rec["conditions"]):
        problems.append(f"{where}: recommendation cites no claim row")
    for f in ("rationale", "conditions", "limitation"):
        if rec[f]:
            run_text_ok(f"{where}.recommendation.{f}", rec[f], CP6_FORBID)
    refs = [c["thesis_ref"] for c in sub["thesis_challenges"]]
    if len(set(refs)) != len(refs) or not refs:
        problems.append(f"{where}: thesis_challenges")
    for i, c in enumerate(sub["thesis_challenges"]):
        w = f"{where}.thesis_challenges[{i}]"
        if c["thesis_ref"] not in CP2_CAT or not c["thesis_ref"].startswith(("T2.7.", "T2.10.")):
            problems.append(f"{w}: {c['thesis_ref']} is not challengeable")
        basis_ok(w, c["basis"])
        if not (c["basis"]["cp2_refs"] or c["basis"]["cp3_refs"] or figs_in(*(c[k] for k in ("counter_case", "evidence_for", "evidence_against", "would_change_view")))):
            problems.append(f"{w}: no basis")
        for f in ("counter_case", "evidence_for", "evidence_against", "would_change_view"):
            run_text_ok(f"{w}.{f}", c[f], CP6_FORBID)
    for i, v in enumerate(sub["recovery_view"]):
        w = f"{where}.recovery_view[{i}]"
        if v["confidence"] != "Insufficient Information":
            problems.append(f"{w}: CP-4 evidence is absent, so the view must be Insufficient Information")
        if not v["limitation"]:
            problems.append(f"{w}: states its limitation")
        basis_ok(w, v["basis"])
        for f in ("subject", "view", "limitation"):
            run_text_ok(f"{w}.{f}", v[f], CP6_FORBID)
    for i, r in enumerate(sub["risks"]):
        w = f"{where}.risks[{i}]"
        basis_ok(w, r["basis"])
        if not (r["basis"]["cp2_refs"] or r["basis"]["cp3_refs"]):
            problems.append(f"{w}: no basis")
        for f in ("risk", "mechanic", "implication"):
            run_text_ok(f"{w}.{f}", r[f], CP6_FORBID)
    for i, g in enumerate(sub["gaps"]):
        for f in ("gap", "why_it_matters", "affected_analysis", "action"):
            run_text_ok(f"{where}.gaps[{i}].{f}", g[f], CP6_FORBID)


def cp3_forces_insufficient(cp3):
    kinds = set()
    for t in cp3["tables"]:
        if t["table_id"] == "T3.3":
            for r in t["rows"]:
                for f in r["facts"]:
                    if f["fact_id"].endswith(".kind") and f["status"] == "known":
                        kinds.add(f["text"])
    reasons = []
    if not kinds & {"Observed", "Indicative talk"}:
        reasons.append("CP-3 records no observed or indicative market evidence")
    pref = next(f for t in cp3["tables"] if t["table_id"] == "T3.4" for r in t["rows"] for f in r["facts"]
                if f["fact_id"] == "T3.4.preference.confidence")
    if pref["status"] != "known":
        reasons.append("CP-3 records no preference")
    elif pref["text"] == "Insufficient Information":
        reasons.append("CP-3's preference is Insufficient Information")
    return reasons


def cp6_expected(case, sub, cp3, cp0_lims):
    check_cp6_submission(case, sub, cp3)
    out = Out()
    cp3_cat = cp3["catalogue"]
    tables = []

    def basis_cell(row_basis, texts):
        parts = []
        for module, cat, cited, label in (("CP-2", {k: v["label"] for k, v in CP2_CAT.items()}, set(row_basis["cp2_refs"]), None),
                                          ("CP-3", cp3_cat, set(row_basis["cp3_refs"]), None)):
            parts += [f"{module} {ref} ({lab})" for ref, lab in cat.items() if ref in cited]
        parts += [cp1_ref(n) for n in figs_in(*texts)]
        return C("; ".join(parts) or NO_BASIS6)

    rec = sub["recommendation"]
    insufficient = rec["action_bias"] == "Insufficient Information"
    for g in sub["gaps"]:
        out.limitations.append(f"Gap ({g['severity']}): {out.text(g['gap'])}")
    out.limitations.append(f"CP-5 handoff caps the confidence below High: CP-5 is restricted{FINDINGS_SUFFIX}")
    # _recommendation
    rationale, conditions = out.text(rec["rationale"]), out.text(rec["conditions"])
    cells = [C(rec["action_bias"]), C(rationale, judged=True), C(conditions, judged=True), C(rec["confidence"]),
             basis_cell(rec["basis"], [rec["rationale"], rec["conditions"], rec["limitation"] or ""]), out.limit(rec["limitation"])]
    t, cols = CP6_REG["T6-FINAL"]
    tables.append(table("T6-FINAL", t, cols, [("final_bias", "Recommendation", cells)]))
    if insufficient:
        out.limitations.append(f"Action bias is Insufficient Information: {out.text(rec['limitation'] or '')}")
    action_line = C(f"Action bias: {rec['action_bias']} (confidence {rec['confidence']}). {rationale} Conditions: {conditions}", judged=True)
    # _challenges
    order = {ref: i for i, ref in enumerate(CP2_CAT)}
    challenges = sorted(sub["thesis_challenges"], key=lambda c: order[c["thesis_ref"]])
    rows, lines = [], []
    columns = {k: [] for k in CP6_FRONT}
    for i, c in enumerate(challenges, 1):
        ref = c["thesis_ref"]
        target = CP2_CAT[ref]
        rid, name = f"c{i:02d}", target["name"]
        counter, change = out.text(c["counter_case"]), out.text(c["would_change_view"])
        texts = [c["counter_case"], c["evidence_for"], c["evidence_against"], c["would_change_view"]]
        rows.append((rid, name, [C(f"CP-2 {ref} ({target['label']})"), C(counter, judged=True), out.said(c["evidence_for"]),
                                 out.said(c["evidence_against"]), C(change, judged=True), basis_cell(c["basis"], texts)]))
        lines.append((rid, name, C(f"{name}: {counter} Would change the view: {change}", judged=True)))
        side = SIDE_TABLE.get(target["side"] or "")
        if side:
            columns[side].append((ref.removeprefix("T2.7."), f"Challenge · {name}", C(counter, judged=True)))
    t, cols = CP6_REG["T6A.4"]
    tables.append(table("T6A.4", t, cols, rows))
    for tid in ("cp6.thesis_challenge", "cp6.strength_challenges", "cp6.weakness_challenges"):
        if columns[tid]:
            title = CP6_FRONT[tid]
            tables.append(front_table(tid, title, columns[tid], title))
    # _recovery
    rows = []
    for i, v in enumerate(sub["recovery_view"], 1):
        text = out.text(v["view"])
        if v["confidence"] == "Insufficient Information":
            out.limitations.append(f"Recovery view is Insufficient Information: {out.text(v['limitation'] or '')}")
        rows.append((f"v{i:02d}", f"Recovery view {i}", [out.said(v["subject"]), C(text, judged=True), C(v["confidence"]),
                                                       basis_cell(v["basis"], [v["view"], v["limitation"] or ""]), out.limit(v["limitation"])]))
    t, cols = CP6_REG["T6A.6"]
    tables.append(table("T6A.6", t, cols, rows))
    # risks and gaps
    t, cols = CP6_REG["T6A.7"]
    rows = [(f"r{i:02d}", f"Risk {i}", [out.said(r["risk"]), out.said(r["mechanic"]), out.said(r["implication"]), C(r["severity"]),
                                        basis_cell(r["basis"], [r["risk"], r["mechanic"], r["implication"]])])
            for i, r in enumerate(sub["risks"], 1)]
    tables.append(table("T6A.7", t, cols, rows))
    t, cols = CP6_REG["T6A.11"]
    rows = [(f"g{i:02d}", f"Gap {i}", [C(f"CP-6-GAP-{i:03d}"), out.said(g["gap"]), out.said(g["why_it_matters"]),
                                        out.said(g["affected_analysis"]), C(g["severity"]), out.said(g["action"])])
            for i, g in enumerate(sub["gaps"], 1)]
    tables.append(table("T6A.11", t, cols, rows))
    front = [("recommendation", "Action bias", action_line), *lines]
    title = CP6_FRONT["cp6.committee_challenge"]
    tables.append(front_table("cp6.committee_challenge", title, front, title))
    refs = references_table(out, "CP-6")
    if refs:
        tables.append(refs)
    claims = [{"claim_id": "T6-FINAL.final_bias", "text": rec["rationale"], "limitation": rec["limitation"], "cites": []}]
    claims += [{"claim_id": f"T6A.4.c{i:02d}", "text": c["counter_case"], "limitation": None, "cites": []}
               for i, c in enumerate(challenges, 1)]
    claims += [{"claim_id": f"T6A.6.v{i:02d}", "text": v["view"], "limitation": v["limitation"], "cites": []}
               for i, v in enumerate(sub["recovery_view"], 1) if v["confidence"] != "Insufficient Information"]
    own = dedupe(out.limitations)
    settled = dedupe([*own, SYNTH])
    settled_lit = [t for t in settled]
    cp1a_own = S1_CP1A_OWN
    cp2_own = S1_CP2_OWN
    inh = inherited(settled_lit, cp0_lims, cp1a_own, cp2_own, cp3["settled_limitations"], cp5=True)
    call = {"action_bias": rec["action_bias"], "confidence": rec["confidence"], "meter": call_scale(rec["confidence"])}
    return {
        "tables": tables, "claims": claims, "own_limitations": own, "settled_limitations": settled,
        "inherited_limitations": inh, "referenced": out.referenced, "call": call,
        "front_lines": [(rid, lab, c["text"]) for rid, lab, c in front],
        "strengths_weaknesses_lines": [
            {"section": {"cp6.thesis_challenge": "thesis", "cp6.strength_challenges": "strengths", "cp6.weakness_challenges": "weaknesses"}[tid],
             "cp2_row_key": rid, "label": lab, "text": c["text"]}
            for tid in ("cp6.thesis_challenge", "cp6.strength_challenges", "cp6.weakness_challenges") for rid, lab, c in columns[tid]],
        "forced_insufficient": cp3_forces_insufficient(cp3),
    }


# =====================================================================================================
# Refusal mutations: literal edits of a valid submission, each with the issue text the documented
# validator rule produces (substring, read from the rule's source line, not from running it)
# =====================================================================================================
OBS = {"source_id": "market", "locator": "page:1", "quote": Q_OBS}
TALKQ = {"source_id": "market", "locator": "page:2", "quote": Q_TALK}
REFUSALS = [
    # id, owner, case, edits, expected issue substring, rule source
    ("cp3-confidence-high", "CP-3", "positive", [["set", "preference.confidence", "High"]],
     "preference.confidence: capped below High because CP-2 is restricted", "cp3_relative_value.py _preference_issues"),
    ("cp3-observed-quotes-talk", "CP-3", "positive", [["set", "market_evidence[1].kind", "observed"]],
     "an observed row quotes indicative talk", "cp3_relative_value.py _bind_evidence"),
    ("cp3-unknown-facility", "CP-3", "positive", [["set", "instruments[0].facility_id", "bond-2"]],
     "unknown CP-1 facility bond-2", "cp3_relative_value.py _instrument_issues"),
    ("cp3-ordering-missing", "CP-3", "positive", [["set", "preference.ordering", []]],
     "preference.ordering: term-loan is missing", "cp3_relative_value.py _preference_issues"),
    ("cp3-action-phrase", "CP-3", "positive", [["append_text", "instruments[0].market_observation", " Buy it."]],
     "prohibited conclusion (instrument action)", "cp3_relative_value.py _text_issues, business_context.ACTIONS"),
    ("cp3-basis-quote-not-evidence", "CP-3", "positive",
     [["set", "instruments[0].basis.quotes", [{"source_id": "market", "locator": "page:1", "quote": "Instrument: Northbridge Term Loan"}]]],
     "quotes no market_evidence row", "cp3_relative_value.py _basis_issues"),
    ("cp3-unknown-cp2-row", "CP-3", "positive", [["set", "preference.basis.cp2_refs", ["T2.9.zz"]]],
     "unknown CP-2 row T2.9.zz", "cp3_relative_value.py _basis_issues"),
    ("cp3-talk-worded-as-level", "CP-3", "positive",
     [["set", "market_evidence", "ROW1_ONLY"], ["set", "instruments[0].basis.quotes", [TALKQ]], ["set", "preference.basis.quotes", [TALKQ]],
      ["set", "instruments[0].market_observation", "The loan trades at par on dealer talk."]],
     'indicative talk worded as a market level: "trades at"', "cp3_relative_value.py _instrument_issues, LEVEL_PHRASES"),
    ("cp3-gap-confidence-without-evidence", "CP-3", "gap", [["set", "preference.confidence", "Medium"]],
     "Insufficient Information without observed or indicative market evidence", "cp3_relative_value.py _preference_issues"),
    ("cp3-gap-fabricated-market", "CP-3", "gap",
     [["set", "market_evidence", [{"source_id": "market", "kind": "observed", "quote": OBS, "as_of": "January 9, 2026", "limitation": "Single dealer quotation"}]]],
     "market is not a third_party source (CP-0 T3)", "cp3_relative_value.py _bind_evidence"),
    ("cp6-confidence-high", "CP-6", "positive", [["set", "recommendation.confidence", "High"]],
     "recommendation.confidence: capped below High because CP-5 is restricted", "cp6_committee.py _recommendation_issues"),
    ("cp6-gap-bias-despite-no-evidence", "CP-6", "gap",
     [["set", "recommendation.action_bias", "Neutral"], ["set", "recommendation.confidence", "Medium"]],
     "recommendation.action_bias: Insufficient Information because CP-3 records no observed or indicative market evidence", "cp6_committee.py _recommendation_issues, Upstream.insufficient"),
    ("cp6-thesis-ref-not-challengeable", "CP-6", "positive", [["set", "thesis_challenges[0].thesis_ref", "T2.11.r01"]],
     "is not a CP-2 thesis, strength, weakness or key finding row", "cp6_committee.py _reference_issues"),
    ("cp6-duplicate-challenge", "CP-6", "positive", [["set", "thesis_challenges[0].thesis_ref", "T2.7.thesis"]],
     "thesis_challenges: T2.7.thesis is challenged more than once", "cp6_committee.py _reference_issues"),
    ("cp6-recovery-without-cp4", "CP-6", "positive",
     [["set", "recovery_view[0].confidence", "Medium"], ["set", "recovery_view[0].basis.cp2_refs", ["T2.11.r01"]]],
     "a recovery view that is not Insufficient Information cites a CP-5 finding or limitation carrying CP-4 evidence", "cp6_committee.py _recommendation_issues"),
    ("cp6-trade-term", "CP-6", "positive", [["append_text", "recommendation.conditions", " Set a target price."]],
     'prohibited conclusion (trade terms): "target price"', "cp6_committee.py cp6_prohibited_issues"),
    ("cp6-unknown-cp3-row", "CP-6", "positive", [["set", "recommendation.basis.cp3_refs", ["T3.9.zz"]]],
     "unknown CP-3 row T3.9.zz", "cp6_committee.py _basis_issues"),
    ("cp6-bias-confidence-mismatch", "CP-6", "positive", [["set", "recommendation.confidence", "Insufficient Information"]],
     "recommendation: action_bias and confidence are Insufficient Information together", "cp6_committee.py _recommendation_issues"),
]
TOOL_USE_REFUSALS = [
    {"id": "cp3-unread-page", "owner": "CP-3", "case": "positive",
     "setup": "submit the literal after read_pages of market page:1 only",
     "expect": "invalid step; issue starts 'Cited page not read through read_pages: market page:2' (live/tools.py UNREAD_PAGE); attempt 0 is re-begun as attempt 1 with repair_of set",
     "rule": "applicable_rules('relative_value') == ('unread-citations',)"},
    {"id": "cp6-read-before-submit", "owner": "CP-6", "case": "positive",
     "setup": "submit with no read_inputs on the attempt", "expect": "refused not_permitted (S1a lease: a session-less step needs a read on its own binding)", "rule": "owner_workflow.py:549 as extended by S1a"},
    {"id": "cp6-pack-tool", "owner": "CP-6", "case": "positive",
     "setup": "invoke read_pages or search_pack", "expect": "refused receipt not_permitted (submit-only step)", "rule": "registry.tool_set('committee_challenge') == 'submit-only'"},
    {"id": "cp3-out-of-scope-read", "owner": "CP-3", "case": "positive",
     "setup": "in the CP-3 session invoke read_pages financial page:1 (a pack source outside the CP-0 third_party scope; the session sources are market only)",
     "expect": "refused receipt not_permitted; no read is recorded for financial page:1 (tools/source.py:46-47: a source_id not among the session sources; scope from live/context.py SOURCE_SCOPES via host.py _execution_state)",
     "rule": "SOURCE_SCOPES[relative_value] = the CP-0 third_party sources"},
    {"id": "cp3-out-of-scope-read-gap", "owner": "CP-3", "case": "gap",
     "setup": "in the CP-3 session (readable scope empty: no third_party source) invoke read_pages with any source_id, for example financial page:1",
     "expect": "refused receipt not_permitted, the same rule (tools/source.py:46-47); this refused call is scope evidence only, not an ok call, so the gap case still counts no completion tool use",
     "rule": "SOURCE_SCOPES[relative_value] with an empty scope"},
    {"id": "cp3-stale-snapshot", "owner": "CP-3", "case": "positive",
     "setup": "change the snapshot between the last read and the submit", "expect": "refused stale_binding", "rule": "G1 refusal"},
]

# Review M2 (S1a lease A4 pattern, docs/S1A-OWNER-RUN-LEASE.md): each edit of the closed R3 positive run
# makes verify_owner_run_receipt refuse with identity_mismatch.
TAMPER_REFUSALS = [
    {"id": "cp3-tamper-tool-receipt-body", "owner": "CP-3", "case": "positive", "run": "R3",
     "edit": "forge a consistent CP-3 call: receipt copy whose `read_pages market page:2` OwnerCall has an edited `body`, the audit `calls` file rewritten under the edited call's content hash, `receipt.sha256` rewritten",
     "expect": "`_verify_audit` passes on the forged copy; `_verify_calls_reads` refuses `identity_mismatch` at the SourceSession replay (owner_workflow.py:983-985); `verify_owner_run_receipt` refuses `identity_mismatch`"},
    {"id": "cp3-tamper-step-output", "owner": "CP-3", "case": "positive", "run": "R3",
     "edit": "edit the output of the CP-3 relative_value step",
     "expect": "verify_owner_run_receipt refuses with identity_mismatch (caught by the store's own blob hash check, not by the CP-3 probe's output comparison (recorded limitation, S1a R3-5))"},
    {"id": "cp3-tamper-settled-head", "owner": "CP-3", "case": "positive", "run": "R3",
     "edit": "a receipt copy with the CP-3 head's `status` changed, and one with `result_sha256` set to `\"0\"*64`",
     "expect": "both refused at owner_workflow.py:1120, before the seal check"},
]


# =====================================================================================================
# assembling
# =====================================================================================================
def lines_of(front):
    return [{"text": text, "kind": "pen", "row_id": rid, "label": label} for rid, label, text in front]


def clip(s, n=140):
    return s if len(s) <= n else s[: n - 1] + "…"


def cp3_render(c3):
    lines = lines_of(c3["front_lines"])
    return {
        "FP01.relative-value": {
            "title": "Relative value", "owner": "CP-3", "kind": "prose", "state": "collapsed",
            "summary": clip(lines[0]["text"]), "lines": [{"text": l["text"], "kind": l["kind"]} for l in lines],
            "note": "One line per bound fact, unlabelled; the preference is first and is the collapsed summary clipped to 140 characters (report_view.py:1651, as the S1 transaction-summary block)",
        },
        "rails": {
            "evidence": {"CP-3": ["T3.1", "T3.3", "T3.4", "T3.9", *(["cp1_references"] if c3["referenced"] else [])]},
            "limitations": {"CP-3": ["T3.10"], "module_limitations": {"own_settled": c3["settled_limitations"]}},
        },
    }


def cp6_render(c6):
    lines = lines_of(c6["front_lines"])
    return {
        "FP01.committee-challenge": {
            "title": "Committee challenge", "owner": "CP-6", "kind": "prose", "state": "collapsed",
            "summary": clip(lines[0]["text"]), "lines": [{"text": l["text"], "kind": l["kind"]} for l in lines],
        },
        "FP01.strengths-weaknesses.CP-6-side": {
            "owner": "CP-2 · CP-6", "lines": c6["strengths_weaknesses_lines"],
            "note": "Each line sits in the Binding.section column of the CP-2 row with the same key (bindings/cp6.py); CP-2 rows CP-6 does not challenge get no CP-6 line",
        },
        "call_band": {"Action bias": c6["call"]["action_bias"], "Confidence": c6["call"]["confidence"], "meter": c6["call"]["meter"]},
        "rails": {
            "evidence": {"CP-6": ["T6-FINAL", "T6A.4", "T6A.6", "T6A.7", *(["cp1_references"] if c6["referenced"] else [])]},
            "limitations": {"CP-6": ["T6A.11"], "module_limitations": {"own_settled": c6["settled_limitations"], "inherited": c6["inherited_limitations"]}},
        },
    }


def context_block_cp3(case, c3):
    positive = case == "positive"
    return {
        "upstream_statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "restricted", "CP-2": "restricted"},
        "cp1_facilities": [{"facility_id": FACILITY["facility_id"], "name": FACILITY["name"],
                            "note": "terms and figure ids are CP-1 output, bound at run time and asserted equal to the financial literal (tests/test_financial_workflow.py:474-475)"}],
        "cp2_rows": list(CP2_CAT),
        "optional_upstream": [{"module_id": "CP-1A", "status": "restricted", "limitations": S1_CP1A_OWN},
                              {"module_id": "CP-4", "status": "not in this run", "limitations": []}],
        "market_evidence_sources": [{"source_id": "market", "name": MARKET_NAME, "spans": 2}] if positive else [],
        "market_evidence_note": ("Quote market evidence only from a source listed in market_evidence_sources; classify each quote observed or indicative_talk, never talk as a level."
                                 if positive else "No third_party source: there is no market evidence, so the preference is Insufficient Information."),
        "confidence_caps": ["CP-2 is restricted"],
        "pack_source_authority": {s[0]: ("third_party" if s[0] == "market" else "issuer") for s in pack_of(case)},
    }


BLOCKED_CP1A_LIMIT = "Optional upstream CP-1A blocked: CP-3 reads no business and transaction context"
BLOCKED_PREFIX = "Upstream CP-1A blocked: "


def blocked_cp1a_variant(case, c3, cp0_lims):
    """Review L1 (S1a lease A3b analogue): the closed R3 run in which CP-1A settles blocked (attempts 0 and 1
    both invalid) and CP-3 still runs, because the CP-3 -> CP-1A edge is optional/restricted. Only what the
    product code fixes is pinned; the blocked head's own limitation texts are run-time issue strings."""
    assert case == "positive" and not any(t.startswith("Relative value preference is Insufficient") for t in c3["own_limitations"])
    own = dedupe([*c3["own_limitations"], BLOCKED_CP1A_LIMIT])
    settled = dedupe([*own, SYNTH])
    base_ctx = context_block_cp3(case, c3)
    return {
        "scenario": ("the R3 positive state with CP-1A forced blocked as in S1a lease A3b (CP-1A attempts 0 and 1 both fail a rule, head blocked); "
                     "CP-2 begins with input CP-1A status blocked and CP-3 begins with CP-1A blocked in its inputs"),
        "status": "restricted (own limitations; blocked_ancestors also marks it restricted, execution.py settle)",
        "module_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1A", "CP-2", "relative-value-submission"],
        "input_statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "blocked", "CP-2": "restricted"},
        "context_block_checks": {
            "upstream_statuses": {**base_ctx["upstream_statuses"], "CP-1A": "blocked"},
            "optional_upstream": [{"module_id": "CP-1A", "status": "blocked",
                                   "limitations": "the blocked CP-1A head's limitations (its issue texts), bound at run time"},
                                  base_ctx["optional_upstream"][1]],
            "confidence_caps": ["CP-2 is restricted", "CP-1A is blocked"],
        },
        "own_limitations": own,
        "own_limitations_added": [BLOCKED_CP1A_LIMIT],
        "settled_limitations": settled,
        "inherited_limitations": {
            "literal_head": [t for t in dedupe(cp0_lims) if t not in settled],
            "then": CP1_BIND,
            "then_after_CP-1": {"bind": f"CP-1A blocked head: each of its limitations, each prefixed {BLOCKED_PREFIX!r} (execution.py:361-362); the S1 CP-1A literal limitations are not inherited as such"},
            "then_after_blocked_CP-1A": {"bind": "CP-2 head (the S1a A3b head): its limitations then its inherited_limitations, in head order"},
            "order": "inputs in plan order; entries already listed or equal to an own finding are dropped (execution.py:345-366)",
        },
        "unchanged_from_positive": "all CP-3 tables, claims, cp1_references order and rendering equal the positive R3 values above, with the CP-2 rows read from the A3b CP-2 head (the literal cites T2.11.r01, T2.1.assessment and T2.7.s01, which must resolve there)",
        "tool_use": "as the positive R3 CP-3 (read_pages market page:1 and page:2 before the submit)",
        "host": "H1: the CP-3 session authenticates a blocked CP-1A producer through the failed-producer branch (no submission tail, attempt.issues non-empty); this variant exercises that branch",
        "acceptance": "A3b analogue: the receipt verifies and the CP-3 head is the head the verifier probe re-derives",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {}
    for case in ("positive", "gap"):
        pack = pack_of(case)
        sub3 = cp3_submission(case)
        c3 = cp3_expected(case, sub3)
        reviews, cp0s, deltas = {}, {}, {}
        for run in ("R3", "R6"):
            rv = readiness_review(case, run)
            reviews[run] = rv
            cp0s[run] = cp0_expected(pack, rv, RUN_IDS[(run, case)], RUNS[run]["plan_order"], RUNS[run]["live_consumers"])
            deltas[run] = cp1a_delta(case, run)
        # CP-0 limitations are the same in R3 and R6 (the R6 consumers carry only the financial limitation)
        assert cp0s["R3"]["limitations"] == cp0s["R6"]["limitations"]
        cp0_lims = cp0s["R3"]["limitations"]
        expected_lims = [LIMIT_FIN, SYNTH] if case == "positive" else [LIMIT_FIN, GAP_MARKET, SYNTH]
        assert cp0_lims == expected_lims, cp0_lims
        sub6 = cp6_submission(case)
        c6 = cp6_expected(case, sub6, c3, cp0_lims)
        inh3 = inherited(c3["settled_limitations"], cp0_lims, S1_CP1A_OWN, S1_CP2_OWN)
        inh1a = [t for t in dedupe(cp0_lims) if t not in S1_CP1A_OWN]
        inh2 = [t for t in dedupe(cp0_lims) if t not in S1_CP2_OWN]
        cases[case] = dict(pack=pack, sub3=sub3, c3=c3, reviews=reviews, cp0s=cp0s, deltas=deltas, sub6=sub6, c6=c6,
                           inh3=inh3, inh1a=inh1a, inh2=inh2, cp0_lims=cp0_lims)
    if problems:
        print("INPUT PROBLEMS:")
        for p in problems:
            print(" ", p)
        sys.exit(1)

    run_common = {"issuer_id": ISSUER_ID, "issuer_name": ISSUER, "as_of": AS_OF, "method_version": "deploy-v-r14",
                  "case_kind": "synthetic", "pathway": "credit_snapshot"}
    manifest = {
        "schema_version": "cp3-cp6-owner-cases/1",
        "scope": "CP-3 relative value and CP-6 committee challenge owner inputs on top of the S1 credit-snapshot run (CP-0, CP-1, CP-1A, CP-2, CP-MODEL), plus CP-5 where CP-6 requires it",
        "status": "DRAFT by owner-preparation task cp3-cp6-owner, 2026-10-28; CP-3 half rev 1 (revised after review-precise-r3-1, awaiting scoped re-review); CP-6 half rev 0 draft; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {rel: pin for rel, pin in PINS.items()},
        "reuse": {
            "identity": "cases/financial/manifest.json source identity, bytes unchanged",
            "financial": "cases/financial/manifest.json source financial, bytes unchanged",
            "business": "cases/snapshot/manifest.json business_source.positive, bytes unchanged",
        },
        "market_source": {
            "source_id": "market", "name": MARKET_NAME, "status": "ready", "media_type": "text/plain",
            "extractor": "supplied-representation", "extraction_status": "complete",
            "representation_scope": "Supplied located-page UTF-8 text only; not PDF or text_content extraction",
            "pages": [{"locator": l, "text": t} for l, t in MARKET_PAGES], "sha256": MARKET_SHA, "pack_limitation": None,
            "consistency_with_frozen_sources": [
                "Instrument name, senior secured term loan and final maturity December 31, 2029 equal financial page:5 and business page:3",
                "No other instrument is named: financial page:5 states exactly one debt facility, so CP-3 orders one instrument",
                "As-of: quotations dated January 9, 2026, published January 10, 2026 (the run as-of date)",
                "No rating is stated, consistent with business page:3 (no rating assigned)",
                "No pricing, spread or yield is derived from the quotation anywhere: the contractual spread (0 basis points over SOFR) is untouched and CP-3 computes no number",
            ],
            "quotes": {"observed": Q_OBS, "indicative_talk": Q_TALK, "sheet": Q_SHEET},
        },
        "runs": {
            run: {
                "requested_modules": RUNS[run]["requested_modules"], "plan_order": RUNS[run]["plan_order"],
                "live_consumers_of_cp0": RUNS[run]["live_consumers"], "cp1a_consumers": RUNS[run]["cp1a_consumers"],
                "note": ("CP-3 lease run (CP-5 and CP-6 not selected)" if run == "R3" else "CP-6 lease run; CP-5 is required by CP-6 (methodology.json) and CP-3 is its second consumer"),
            } for run in RUNS
        },
        "cases": [
            {"case_id": f"cp3-cp6-{case}",
             "pack_sources": [{"source_id": s, "name": n, "status": st, "limitation": l} for s, n, st, l in cases[case]["pack"]],
             "runs": {run: {"run": {"run_id": RUN_IDS[(run, case)], **run_common, "requested_modules": RUNS[run]["requested_modules"]}} for run in RUNS},
             "change_from_s1_positive": ("adds the market source (4 sources)" if case == "positive"
                                         else "no market source: the S1 positive three-source pack; CP-0 records the missing market source as a gap that affects CP-3 only"),
             "submissions": f"cases/cp3-cp6-owner/submissions.json#{case}"}
            for case in ("positive", "gap")
        ],
        "table_ids": {
            "CP-3": ["T3.1", "T3.3", "T3.4", "T3.9", "T3.10", "cp3.relative_value", "cp1_references"],
            "CP-6": ["T6-FINAL", "T6A.4", "T6A.6", "T6A.7", "T6A.11", "cp6.committee_challenge", "cp6.thesis_challenge",
                     "cp6.strength_challenges", "cp6.weakness_challenges", "cp1_references"],
        },
    }

    submissions = {
        "schema_version": "cp3-cp6-owner-submissions/1",
        "note": ("Literal analyst submissions. {{FIG:name}} marks a CP-1 figure reference to be replaced mechanically by {<actual CP-1 fact_id>|<unit_token>} "
                 "after the CP-1 head exists, exactly as cases/snapshot/submissions.json (same figures, same selection rule; zero or several candidates fail). "
                 "Every other value is literal input. S1 files are referenced by path and sha256, never copied for edit."),
        "figures": {k: {"unit_token": FIGS[k]["unit_token"], "spelled": FIGS[k]["spelled"], "cp1_coordinate": FIGS[k]["cp1_coordinate"]}
                    for k in ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported", "fcf_to_debt")},
        "s1_base": {rel: PINS[rel] for rel in S1_FILES},
    }
    for case in ("positive", "gap"):
        d = cases[case]
        submissions[case] = {
            "readiness_review": {
                "base": "cases/snapshot/submissions.json#positive.readiness_review",
                "R3": d["reviews"]["R3"], "R6": d["reviews"]["R6"],
            },
            "cp1_source_context": cp1_source_context(case),
            "business_context": {
                "base": "cases/snapshot/submissions.json#positive.business_context",
                "sources_append": [MARKET_SOURCE_USE] if case == "positive" else [],
                "consumers": {run: cp1a_consumers(run) for run in RUNS},
                "note": "Replace sources by base.sources + sources_append and consumers by the run's list; every other key is the S1 positive value",
            },
            "credit_synthesis": {"base": "cases/snapshot/submissions.json#positive.credit_synthesis", "change": "none"},
            "relative_value": d["sub3"],
            "committee_challenge": d["sub6"],
        }
    submissions["refusal_mutations"] = {
        "note": "Each entry edits a deep copy of the case's valid literal (paths use dots and [i]; 'append_text' extends a string; 'ROW1_ONLY' means keep only market_evidence[1])",
        "entries": [{"id": i, "owner": o, "case": c, "edits": e} for i, o, c, e, _x, _r in REFUSALS],
    }
    submissions["cp5_premise"] = {
        "required_by": "CP-6 (methodology.json: CP-6 requires CP-5; registry.edge_rule is block)",
        "premise": "The CP-5 head over the same run settles restricted with: zero T5B.2 rows (unsupported or partly supported), zero T5B.3 rows (contradictions), no flagged claim, no unreadable claim name, and no CP-5 row carrying CP-4 content. Its findings (T5.9) and limitations are whatever CP-5 settles; CP-6 reads them at run time.",
        "binding": "{{CP5_FINDINGS_SUFFIX}} in the expected CP-6 limitation is '' when the CP-5 head has no CP-5-FINDING-NNN row, else '; findings ' + ', '.join(finding ids in head order) (cp6_committee.Upstream.limits)",
        "cp5_refs_used_by_cp6_literals": "none: the literal CP-6 submissions cite no CP-5 row, so no CP-5 id is needed to write them",
        "owner": "The CP-5 literal submission and expected head belong to the CP-5 (S1b) lease; this oracle only fixes the premise above",
    }

    expected = build_expected(cases)
    for name, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in ("manifest.json", "submissions.json", "expected.json"):
        print(name, hashlib.sha256((OUT / name).read_bytes()).hexdigest())


def build_expected(cases):
    exp = {
        "schema_version": "cp3-cp6-owner-expected/1",
        "derivation": ("Hand-transcribed composition rules applied to submissions.json by cases/cp3-cp6-owner/builder/build.py (stdlib only; deploy_vii never imported or run). "
                       "Rule sources: readiness.py:408-531 (CP-0), business_context.py:1551-1590 (CP-1A handoff registers), cp3_relative_value.py:760-1170 (CP-3 composition), "
                       "cp6_committee.py:1100-1330 (CP-6 composition), report_view.py/bindings/cp3.py/bindings/cp6.py (rendering), execution.py:259-267 and 345-366 (inputs, inheritance). "
                       "The CP-0 transcription is checked by the builder against the frozen S1 oracle; the S1 pins are in manifest.json."),
        "cell_notation": S1E["cell_notation"],
        "arithmetic": ("No CP-3 or CP-6 arithmetic exists: neither core computes a price, spread, yield or ranking number (cp3_relative_value.py header: Python owns pricing arithmetic, "
                       "but the core holds none). The only numbers on the rendered sections are Python-spelled CP-1 facts already pinned in the S1 oracle (1.67x = 50/30, 1.00x = 30/30, 6.00x = 30/5, 18.0% = 9/50, "
                       "each from cases/financial/manifest.json q4_ltm_metric_oracle) and quoted source text (the dealer bid 98.50 and offer 99.25 and talk 99.75, which appear only inside cited quotes). "
                       "call_scale maps confidence to a meter: Insufficient Information 1, Low 2, Medium 3, High 5."),
        "table_id_check": {
            "method": "methodology.json table_ids of every module compared for equality with each id below (builder data read, no code run)",
            "CP-3": {"T3.1": "unique to CP-3", "T3.3": "unique to CP-3", "T3.4": "unique to CP-3", "T3.9": "unique to CP-3", "T3.10": "unique to CP-3"},
            "CP-6": {"T6A.4": "unique to CP-6", "T6A.6": "unique to CP-6", "T6A.7": "unique to CP-6", "T6A.11": "unique to CP-6"},
            "unregistered_composed_ids": ["T6-FINAL", "cp3.relative_value", "cp6.committee_challenge", "cp6.thesis_challenge", "cp6.strength_challenges", "cp6.weakness_challenges", "cp1_references"],
            "note": "No collision exists. The unregistered ids are composed by the cores today (cp1_references is shared by every module by design). T6-FINAL is listed for the CP-6 half only: ruling Q7 registers it under CP-6 table_ids with the CP-6 freeze, so the CP-3 build does not assert it either way.",
        },
    }
    meth = {m["module_id"]: m["table_ids"] for m in METH}
    allids = {}
    for mod, ids in meth.items():
        for i in ids:
            allids.setdefault(i, []).append(mod)
    for tid, mod in [(t, "CP-3") for t in exp["table_id_check"]["CP-3"]] + [(t, "CP-6") for t in exp["table_id_check"]["CP-6"]]:
        assert allids[tid] == [mod], (tid, allids.get(tid))
    # T6-FINAL is not asserted here: ruling Q7 registers it under CP-6 with the CP-6 freeze, which asserts it then.
    for tid in exp["table_id_check"]["unregistered_composed_ids"]:
        if tid != "T6-FINAL":
            assert tid not in allids, tid
    for case in ("positive", "gap"):
        d = cases[case]
        c3, c6 = d["c3"], d["c6"]
        entry = {
            "pack_sources": [s[0] for s in d["pack"]],
            "upstream": {
                "premise": "CP-0, CP-1, CP-1A, CP-2 are the S1 positive heads re-run over this pack; only the items listed here differ from cases/snapshot/expected.json#positive",
                "CP-0": {run: d["cp0s"][run] for run in RUNS},
                "CP-1": {
                    "authorization": "T8 exact_command 'Run CP-1' (unchanged)",
                    "source_context": ("S1 positive cp1_source_context plus one market entry (classification nonfinancial, evidence_class external, event_scan unassessed, one page:1 citation); "
                                       "tool use adds read_pages market page:1 before submit" if case == "positive" else
                                       "S1 positive cp1_source_context unchanged (three sources)"),
                    "ratios": S1E["CP-1"]["ratios"],
                    "limitations": "CP-1's own and inherited limitations are CP-1 outputs bound at run time (S1 ruling R3-Q1); in the gap case the CP-0 list gains the market-gap text, which CP-1 inherits through the CP-0 head",
                },
                "CP-1A": {run: d["deltas"][run] for run in RUNS},
                "CP-1A_inherited": {"literal_head": d["inh1a"], "then": CP1_BIND,
                                    "rule": "CP-0 limitations, then the CP-1 head entries; de-duplicated; own findings removed (execution.py:345-366)"},
                "CP-2": {"tables": "unchanged: cases/snapshot/expected.json#positive.CP-2 (the CP-2 literal submission is unchanged and cites no row whose id moves)",
                         "inherited": {"literal_head": d["inh2"], "then": CP1_BIND,
                                       "literal_tail_after_CP-1": [t for t in dedupe([*S1_CP1A_OWN, *d["inh1a"]]) if t not in S1_CP2_OWN and t not in d["cp0_lims"]]},
                         "catalogue_rows_CP-3_may_cite": list(CP2_CAT)},
                "statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "restricted", "CP-2": "restricted", "CP-MODEL": "restricted"},
            },
            "CP-3": {
                "module_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1A", "CP-2", "relative-value-submission"],
                "inputs_note": "prepared-pack (status accepted) and the four heads (status restricted) carry the final result_sha256 at begin (execution.current_inputs: plan order, CP-1A bound because the run selects it); CP-MODEL, CP-4, CP-3C, CP-3D, CP-4C and CP-2D are not inputs",
                "status": "restricted (synthetic case, execution.py:441-457)",
                "context_block_checks": context_block_cp3(case, c3),
                **({"blocked_cp1a_variant": blocked_cp1a_variant(case, c3, d["cp0_lims"])} if case == "positive" else {}),
                "tables": c3["tables"], "claims": c3["claims"],
                "own_limitations": c3["own_limitations"], "settled_limitations": c3["settled_limitations"],
                "inherited_limitations": d["inh3"],
                "cp1_references_order": c3["referenced"],
                "catalogue_for_CP-6": c3["catalogue"],
                "render": cp3_render(c3),
            },
            "CP-6": {
                "module_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "committee-submission"],
                "inputs_note": "CP-1A is the one optional upstream CP-6 reads (status and limitations only); CP-4 is no CP-6 edge",
                "status": "restricted (synthetic case)",
                "forced_insufficient_reasons": c6["forced_insufficient"],
                "confidence_caps": ["CP-5 is restricted"],
                "tables": c6["tables"], "claims": c6["claims"],
                "own_limitations": c6["own_limitations"], "settled_limitations": c6["settled_limitations"],
                "inherited_limitations": c6["inherited_limitations"],
                "cp1_references_order": c6["referenced"],
                "render": cp6_render(c6),
            },
        }
        exp[case] = entry
    exp["run_time_bindings"] = {
        "{{FIG:name}}": "as cases/snapshot/submissions.json: the unique T4.10 twelve-month (LTM) Q4 2025 fact of that metric in the CP-1 head; its fact_id and unit token replace the placeholder in submissions and in expected claims; the test asserts unit equals the unit token and the spelling equals the pinned one (1.67x, 1.00x, 6.00x, 18.0%); zero or several candidates fail",
        "<label and period of FIG:name>": "label and period of that CP-1 fact, shown as 'CP-1 <label> · <period>' in basis cells and as the cp1_references row label",
        "cp1_references": "table rows ref01.. in first-spelling order (cp1_references_order); each carries the CP-1 fact's own fact_id, value_class calculated and own citations",
        "facility": "the T4.18 facility_id cell text is 'term-loan' and its facility_name cell 'Northbridge Term Loan' in the CP-1 head (financial literal, tests/test_financial_workflow.py:474-475); asserted, and the instrument row label is that name",
        "{{CP5_FINDINGS_SUFFIX}}": "'' when the CP-5 head has no CP-5-FINDING-NNN row, else '; findings ' + ', '.join(finding ids in head order) (cp6_committee.Upstream.limits)",
        "CP-1 limitation entries": "CP-1's own and inherited limitation texts bound from the CP-1 head at the 'then' marker of every inherited list (S1 ruling R3-Q1)",
        "CP-5 limitation entries": "CP-5's own and inherited limitation texts bound from the CP-5 head at the CP-5 marker of the CP-6 inherited list",
        "ticket and call ids": "compared structurally only",
        "<<PACK_SHA256...>>": "PreparedPack.content_hash() of the run's pack, as S1",
    }
    exp["refusals"] = {
        "validator_refusals": [{"id": i, "owner": o, "case": c, "issue_contains": x, "rule_source": r} for i, o, c, _e, x, r in REFUSALS],
        "tool_use_refusals": TOOL_USE_REFUSALS,
        "tamper_refusals": TAMPER_REFUSALS,
        "note": "issue_contains is a substring of one issue of the product validator over the mutated literal; the whole submission is refused (no module settles) and nothing is journaled as accepted",
    }
    exp["execution"] = execution_block(cases)
    return exp


def cp2_read_counts(case, delta):
    """Review M4: the per-register row counts of the CP-2 read body (module_context credit_synthesis) in this
    oracle's runs, from the pinned S1 view tree (positive: 70 rows) plus this oracle's CP-1A deltas."""
    counts = {r["ref_prefix"]: r["rows"] for r in CP2_TREE["positive"]["cp1a_registers"]}
    assert sum(counts.values()) == CP2_TREE["positive"]["cp1a_rows"] == 70
    if case == "positive":
        counts["source_classification"] += 1
        counts["T2D.1"] += 1
    for tid in ("downstream_readiness", "T2D.10"):
        counts[tid] = len(delta["tables"][tid]["replace_table"]["rows"])
    total = sum(counts.values())
    assert total == delta["catalogue_size"], (case, total, delta["catalogue_size"])
    return {
        "source_classification": counts["source_classification"], "T2D.1": counts["T2D.1"],
        "downstream_readiness": counts["downstream_readiness"], "T2D.10": counts["T2D.10"],
        "cp1a_rows": total,
    }


def execution_block(cases):
    cp2_counts = {case: {run: cp2_read_counts(case, cases[case]["deltas"][run]) for run in RUNS} for case in cases}
    return {
        "statuses": "every head restricted (synthetic case); CP-MODEL restricted head over promoted CP-1 (S1 precedent)",
        "tool_use": {
            "CP-0": "pack tools; positive adds read_pages market page:1 (cited by the market assessment and the CP-3 consumer); gap unchanged from S1",
            "CP-1": "positive adds read_pages market page:1 before the source_context submit (the market entry cites page:1); gap unchanged from S1",
            "CP-1A": "positive adds read_pages market page:1 (cited by the market source row); search_pack still required by the absence rule of the S1 literal (available No / Not disclosed rows)",
            "CP-2": {
                "tool_set": "unchanged: submit only, read_inputs once per attempt (S1a lease)",
                "read_body": ("module_context('credit_synthesis'): the key tree and every register count of cases/snapshot/cp2-view-tree.json positive "
                              "except the four counts below; cp1a_rows length equals catalogue_size; cp1a_signals equal the positive tree's; "
                              "upstream statuses CP-0, CP-1 and CP-1A restricted (review M4: the S1a assertion, parameterised by these values)"),
                "register_counts_by_case_and_run": cp2_counts,
            },
            "CP-3": {
                "tool_set": "pack (registry.tool_set('relative_value')); scope = readable_sources = the CP-0 third_party sources only (live/context.SOURCE_SCOPES)",
                "rules": "applicable_rules('relative_value') = ('unread-citations',): no absence rule, so no search_pack is required; a search_pack over market is still expected of a real participant but is not a gate",
                "positive": "ok read_pages for market page:1 and market page:2 (the two cited locators) before the submit; the receipt holds both calls",
                "gap": "no readable source (market scope is empty) and the literal cites no locator: the gap case makes no ok call and only refused scope calls (cp3-out-of-scope-read-gap); tool-use completion rests on the positive case",
                "scope_refusals": "read_pages of a source outside the session scope is refused not_permitted: positive financial page:1, gap any source (refusals.tool_use_refusals cp3-out-of-scope-read, cp3-out-of-scope-read-gap)",
                "upstream_view": "none: CP-3 is a pack-tool step with no read_inputs view; its upstream CONTEXT (cp1_facts, cp2_rows) is not available to a JSON-lines participant. Deferred like S1a Q6; the run-time FIG substitution supplies the CP-1 ids",
            },
            "CP-6": {
                "tool_set": "submit-only (registry.tool_set('committee_challenge')); applicable_rules = () ",
                "read_inputs": "exactly one read_inputs per attempt before the submit; body = module_context('committee_challenge') with heads[*].claims[*].citations removed (narrower than the live CONTEXT, D2); digest = sha256 of the body",
                "assertion": "the body's key tree equals the tree frozen by the probe task and no source quote string of the pack occurs in it",
                "ok_pack_calls": 0,
            },
        },
        "consumption": {
            "CP-3": ("A module is consumed only when a consumer core reads its settled output in an actual run (D3). CP-6 reads CP-3 through cp3_catalogue (T3.1, T3.3, T3.4, T3.9, T3.10 rows), "
                     "claim_rows (T3.4.preference and T3.1.iNN), Upstream.insufficient (T3.3 kind cells and T3.4.preference.confidence) and the CP-3 head's claims in context_block. "
                     "Proof: CP-6's table cells name CP-3 rows (basis cells 'CP-3 T3.4.preference (Preference)' and so on), the gap case's action bias is forced to Insufficient Information by the CP-3 head's T3.3/T3.4 cells, and the verifier probe re-runs cp6_committee._validate_step, which reads the bound CP-3 head."),
            "CP-2": ("CP-3 reads the CP-2 head (cp2_catalogue over T2.1, T2.7, T2.10, T2.11, T2.12 and the CP-2 input status for the confidence cap); CP-6 reads it again (cp2_rows, challengeable rows, claim_rows). "
                     "Proof for D3 is the CP-6 table T6A.4 (one challenge per CP-2 row, column 'CP-2 row' = 'CP-2 <ref> (<label>)') and the T6-FINAL basis cell, plus CP-3's basis cells 'CP-2 <ref> (<label>)'. CP-5 is not claimed as a consumer of CP-2 or CP-3 until its own lease extends the integrity scope (D3)."),
            "CP-1A": "optional upstream of CP-3 and CP-6: read for status and limitations only (CONTEXT optional_upstream); not a content consumer, and the optional read is shown by the CP-3/CP-6 CONTEXT block, not by a table cell",
            "optional_producers_never_read": {
                "CP-3": "CP-3C, CP-3D, CP-4C, CP-2D (cp3_relative_value.py:99-104). They are not in requested_modules, so no attempt input exists and the CP-3 module inputs list contains none; the CONTEXT optional_upstream lists only CP-1A and CP-4 (CP-4 'not in this run'). The test asserts the inputs list and the absence of the four ids in the CONTEXT body",
                "CP-6": "CP-2A, CP-2E, CP-2D, CP-3C, CP-3D (cp6_committee.py READ_OPTIONAL comment); only CP-1A is read. CP-4 reaches CP-6 only through CP-5 findings, and CP-6 never has a CP-4 head: every recovery view is Insufficient Information",
            },
            "CP-MODEL": "inputs contain none of CP-3, CP-5, CP-6 (it requires CP-1 only)",
            "CP-6_consumers": "none inside the product beyond the call band; the CP-6 head is consumed by rendering only (FP01 committee-challenge, strengths-weaknesses CP-6 side, the call band, Evidence and Limitations rails)",
        },
    }


if __name__ == "__main__":
    main()
