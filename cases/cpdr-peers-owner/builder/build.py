"""Writes cases/cpdr-peers-owner/{manifest,submissions,expected}.json (stdlib only, imports nothing from src/).

Oracle for the opt-in CP-DR peer pack (tables TDR.4-6) and CP-1C reading it (Part B O7d D0a). Every value is
derived here from the invented pages below, the method texts (methods/cp1c.md), the rulings O7-R47 Q4-Q6 and the
policy constants of cases/cp1c-owner/expected.json. A rule restated from cp1c.py names its source line. All
evidence is SYNTHETIC; every page says so.

Run: python3 -I cases/cpdr-peers-owner/builder/build.py [OUT_DIR]   (from the repository root)
"""

import calendar
import copy
import hashlib
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, Context, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "cases" / "cpdr-peers-owner"
PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/cp1c-owner/submissions.json": "13be79735066cd58bdcc4cfa7eebddc0eedbe0abb784153a2950ee38455a8912",
    "cases/cp1c-owner/expected.json": "daccb5832d816e70e9893152980b3f56564c5eeb9305273564a2c1ba173452df",
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(rel):
    raw = (ROOT / rel).read_bytes()
    assert rel not in PINS or hashlib.sha256(raw).hexdigest() == PINS[rel], rel
    return json.loads(raw)


FIN, CP1C, CP1C_EXP = (load(p) for p in PINS)
CTXF = load("cases/context/research-minimal.json")
assert CTXF["valuation"]["peer_source"] == "cp_dr_public" and CTXF["valuation"]["basis"] == "auto"
RUN_CUR = CTXF["run"]["reporting_currency"]
assert RUN_CUR == "USD" and CTXF["run"]["current_period"] == ""
SHA = {s["source_id"]: s["sha256"] for s in FIN["sources"]}
ISSUER_ID, ISSUER_NAME, AS_OF = (FIN["run"][k] for k in ("issuer_id", "issuer_name", "as_of"))
assert (ISSUER_ID, AS_OF) == ("northbridge-synthetic", "2026-01-10")
CUTOFF, VERSION, RUN_ID = AS_OF, "cp-dr/2026-10-31", "cpdr-peers-owner-positive"
SYNTH = "This invented case is test data, not evidence about real issuers."
MIN_PEERS = CP1C_EXP["policy_constants"][
    "minimum_included_peers"
]  # inclusion: Comparable, Partly comparable
assert MIN_PEERS == 3 and CP1C_EXP["policy_constants"]["inclusion"].startswith(
    "Comparable and Partly"
)
INCLUDED = ("Comparable", "Partly comparable")
CTX = Context(
    prec=38, rounding=ROUND_HALF_EVEN
)  # cp1c.md "What the module does": 38 digits half-even


def nd(text):  # the digit rule of the research texts: analyst text holds no digit
    assert not re.search(r"[0-9]", text), text
    return text


def canon(
    d,
):  # canonical exact decimal text (cases/cp1c-owner/expected.json cell_notation amount_exact)
    return format(d.normalize(CTX), "f")


def table(rows, *names):
    return [dict(zip(names, r.split("|"), strict=True)) for r in rows.strip().splitlines()]


# --- rules restated from cp1c.py (each names its source) --------------------------------------------------------
OPS = ("revenue", "ebitda", "debt", "interest", "ffo")  # OPERANDS :158-164
LABEL = dict(
    zip(OPS, ("revenue", "adjusted EBITDA", "total debt", "interest expense", "FFO"), strict=True)
)
METRICS = (  # METRICS :192-211: key, numerator, denominator
    ("adjusted_ebitda_margin", "ebitda", "revenue"),
    ("total_leverage_adjusted", "debt", "ebitda"),
    ("interest_coverage_adjusted", "ebitda", "interest"),
    ("ffo_to_debt", "ffo", "debt"),
)
AMOUNT = re.compile(
    r"-?[0-9]+(?:\.([0-9]+))?"
)  # AMOUNT :105, with at most one decimal place (SHEET_DECIMALS)
NOT_READABLE, AFTER_CUTOFF = "figure not readable from the quote", "period end after the cutoff"


def amount_of(quote):
    m = AMOUNT.fullmatch(quote)
    return Decimal(quote) if m and len(m.group(1) or "") <= 1 else None


def ratio(
    a, num, den
):  # ratio :426-440: a missing operand gives a missing ratio (denominators here are positive)
    return None if a[num] is None or a[den] is None else CTX.divide(a[num], a[den])


def median(vals):  # median :447-455
    v, mid = sorted(vals), len(vals) // 2
    return v[mid] if len(v) % 2 else CTX.divide(CTX.add(v[mid - 1], v[mid]), Decimal(2))


# --- the invented peers and evidence (| tables; figure tokens by operand) -------------------------------------
PEERS = {
    r["id"]: {**r, "toks": r["toks"].split()}
    for r in table(
        """
p01|Alder Ridge Holdings|Comparable|2025-12-31|USD|200.0 52.0 104.0 8.0 41.6|reports under IFRS with one operating segment and a December 31 year end.|IFRS reporter with one operating segment and a December year end.
p02|Brookmere Industries|Comparable|2025-12-31|USD|150.0 33.0 99.0 11.0 30.0|reports under IFRS with one operating segment and a December 31 year end.|IFRS reporter with one operating segment and a December year end.
p03|Calder Vale Group|Comparable|2025-12-31|USD|96.0 27.0 40.5 4.5 18.9|reports under IFRS with one operating segment and a December 31 year end.|IFRS reporter with one operating segment and a December year end.
p04|Dunmore Cross Corporation|Partly comparable|2025-09-30|USD|300.0 48.0 240.0 24.00 30.0|reports under IFRS with one operating segment and a June 30 year end; its twelve months end on September 30, 2025.|IFRS reporter with one operating segment and a June year end; its twelve months end in September.
p05|Ellsworth Park Limited|Not comparable|2025-12-31|USD|500.0 150.0 75.0 7.5 60.0|reports under US GAAP with six operating segments and a December 31 year end; the desk offers it as a size reference only.|US GAAP reporter with several operating segments; offered as a size reference only.
p06|Garrowby Holdings SE||2025-12-31|EUR|180.0 45.0 90.0 6.0 36.0|reports under IFRS in euros with one operating segment and a December 31 year end.|IFRS reporter in euros with one operating segment and a December year end.
""",
        "id",
        "name",
        "cmp",
        "pe",
        "cur",
        "toks",
        "basis",
        "note",
    )
}
for _p in PEERS.values():
    nd(_p["name"]), nd(_p["note"])
# p03.revenue is stated only by ev-3, for a period ending after the cutoff; p04.interest is stated with two decimals,
# outside the amount rule. Both become missing cells; every other figure is readable and in time.
LATE = {("p03", "revenue"): "2026-03-31"}
USD_BASIS = "Basis: twelve months to the period end shown; USD; amounts in millions; unaudited desk summaries."


def stated(pid, op, tail=""):
    p = PEERS[pid]
    return f"{p['name']} {LABEL[op]} for the twelve months to {p['pe']}{tail}: {p['toks'][OPS.index(op)]}"


USD = ("p01", "p02", "p03", "p04", "p05")
BODY = {
    "ev-1": [USD_BASIS]
    + [f"{PEERS[p]['name']} {PEERS[p]['basis']}" for p in USD]
    + [stated(p, op) for p in USD for op in OPS if (p, op) not in LATE],
    "ev-2": [f"{PEERS['p06']['name']} {PEERS['p06']['basis']}"]
    + [stated("p06", op, " in EUR millions") for op in OPS],
    "ev-3": [
        f"Calder Vale Group indicates revenue of {PEERS['p03']['toks'][0]} (USD millions) for the twelve months to 2026-03-31, a period that has not closed."
    ],
}


def longdate(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{calendar.month_name[m]} {d}, {y}"


ITEMS = table(
    """
ev-1|evidence/a-peer-desk-summary.txt|peer-desk-summaries|2026-01-05|https://peer-desk.example/2026/summaries/industrial-producers-twelve-months|SYNTHETIC PEER DESK|Peer desk summary: reporting bases and twelve-month figures|desk|five candidate peers on the run's currency basis; one figure written with two decimals
ev-2|evidence/b-registry-extract.txt|registry-filings|2025-12-30|https://harbour-registry.example/filings/garrowby-holdings/annual-extract|SYNTHETIC HARBOUR REGISTRY OFFICE|Annual filing extract: Garrowby Holdings SE|registry office|one candidate peer reporting in euros
ev-3|evidence/c-outlook-note.txt|trade-press-archive|2026-01-05|https://trade-press.example/2026/archive/calder-vale-outlook|SYNTHETIC TRADE PRESS ARCHIVE|Calder Vale Group outlook note|archive|one figure whose period end is after the cutoff
""",
    "id",
    "path",
    "family",
    "published",
    "locator",
    "desk",
    "title",
    "who",
    "role",
)
EVS = [i["id"] for i in ITEMS]
TEXT = {
    i["id"]: "\n".join(
        [
            i["desk"],
            i["title"],
            f"Published {longdate(i['published'])}.",
            f"{SYNTH} The {i['who']} and every company named below do not exist.",
            *BODY[i["id"]],
        ]
    )
    for i in ITEMS
}
LINES = {k: v.split("\n") for k, v in TEXT.items()}
PSHA = {k: sha(v) for k, v in TEXT.items()}
PACK_SOURCES = ["identity", "financial", *EVS]


def cite(ev, quote, line=None):
    line = line or next(n for n, t in enumerate(LINES[ev], 1) if quote in t)
    assert quote in LINES[ev][line - 1], (ev, line, quote)
    return {"source_id": ev, "source_sha256": PSHA[ev], "locator": f"line:{line}", "quote": quote}


def where(pid, op):  # the item and line that state the figure
    ev = "ev-3" if (pid, op) in LATE else ("ev-2" if pid == "p06" else "ev-1")
    want = (
        BODY["ev-3"][0]
        if ev == "ev-3"
        else stated(pid, op, " in EUR millions" if pid == "p06" else "")
    )
    return ev, LINES[ev].index(want) + 1


# --- the research submission's peer pack (shape declared by this oracle; the model never types an amount) ----------
CAND = [
    {
        "peer_id": k,
        "name": p["name"],
        "basis_note": p["note"],
        "citation": cite("ev-2" if k == "p06" else "ev-1", f"{p['name']} {p['basis']}"),
    }
    for k, p in PEERS.items()
]
OBS = [
    {
        "peer_id": o["p"],
        "dimension": o["d"],
        "observation": nd(o["t"]),
        "citation": cite(o["ev"], o["q"]),
    }
    for o in table(
        """
p04|period|The twelve months end in September, which is not the issuer's year end.|ev-1|its twelve months end on September 30, 2025
p05|segment|A diversified group with several operating segments.|ev-1|six operating segments
p05|definition|The US GAAP basis differs from the IFRS basis of the other candidates.|ev-1|reports under US GAAP
p06|currency|Figures are stated in euros, not in the run's currency.|ev-2|in euros
""",
        "p",
        "d",
        "t",
        "ev",
        "q",
    )
]
FIGS = [
    {
        "peer_id": k,
        "operand": op,
        "unit": "millions",
        "currency": p["cur"],
        "period_end": LATE.get((k, op), p["pe"]),
        "citation": cite(where(k, op)[0], p["toks"][i], where(k, op)[1]),
    }
    for k, p in PEERS.items()
    for i, op in enumerate(OPS)
]
assert all(
    5 <= int(c["citation"]["locator"][5:]) <= len(LINES[c["citation"]["source_id"]])
    for c in FIGS + CAND + OBS
)
SEARCH = "licensing shipments covenant"  # a span matches when it holds any query term, case-insensitive substring
assert not any(w in t.lower() for w in SEARCH.split() for ls in LINES.values() for t in ls)
NONE_FOUND = {
    "kind": "none_found",
    "searched": EVS,
    "limitation": "Only the supplied items were searched; sources outside them were not.",
}
CTX_Q = {
    "text": nd(
        "Which candidate peers do the supplied items name, and what twelve-month figures do they locate for each?"
    ),
    "focus_module": "CP-1C",
}
DEFAULTS = table(
    """
competition|default_1|The issuer reports a single operating segment. Which producers supply the sector covered by the supplied notes, and how concentrated is supply?
metric-definitions|default_2|The issuer reports adjusted EBITDA equal to reported EBITDA with no add-backs. How do producers in the sector define adjusted EBITDA?
valuation-context|default_3|What trading level or spread figure do the supplied items state for the sector?
market-demand|default_4|How have customers' orders and shipments in the sector moved over the latest year?
industry-structure|default_5|The issuer's capital expenditure is entirely maintenance. How are producers in the sector structured by size and product focus?
regulation|default_6|Which licensing or other regulatory rules bear on producers in the sector?
""",
    "question_id",
    "kind",
    "text",
)  # the Codex defaults, copied from cases/cpdr-research-owner/submissions.json brief.model_tailored_defaults_only
QUESTIONS = [
    {
        "question_id": "ctx-1",
        "text": CTX_Q["text"],
        "kind": "context",
        "receivers": ["CP-1C"],
        "focus_module": "CP-1C",
    }
] + [
    {**d, "text": nd(d["text"]), "receivers": ["CP-1C", "CP-2"], "focus_module": None}
    for d in DEFAULTS
]
ANSWERS = [
    {
        "question_id": "ctx-1",
        "answer_state": "answered",
        "searched": [],
        "limitation": None,
        "contrary": [NONE_FOUND],
        "claims": [
            {
                "claim_id": "ctx-1.c1",
                "independent_items": ["ev-1", "ev-2"],
                "citations": [cite("ev-1", USD_BASIS), cite("ev-2", "in euros")],
                "text": nd(
                    "The peer desk summary names five peers on the run's currency basis and the registry extract names a sixth that reports in euros."
                ),
            }
        ],
        "uncertainty": nd(
            "The candidates are those the supplied items name; peers they do not name are not considered."
        ),
    }
] + [
    {
        "question_id": d["question_id"],
        "answer_state": "not_found",
        "claims": [],
        "contrary": [],
        "uncertainty": None,
        "searched": EVS,
        "limitation": nd("The searched items state nothing that answers this question."),
    }
    for d in DEFAULTS
]


def read(ev, lo, hi):
    spans = [{"source_id": ev, "locator": f"line:{n}"} for n in range(lo, hi + 1)]
    return {
        "tool": "read_pages",
        "arguments": {"source_id": ev, "first_page": lo, "last_page": hi},
        "expect_spans": spans,
    }


READ_INPUTS = {"tool": "read_inputs", "arguments": None}
TOOL_RESEARCH = [READ_INPUTS, *(read(ev, 5, len(LINES[ev])) for ev in EVS)] + [
    {
        "tool": "search_pack",
        "arguments": {"query": SEARCH, "source_id": ev},
        "expect_header": f"0 spans match '{SEARCH}'; showing 0.",
        "expect_matching_spans": [],
    }
    for ev in EVS
]

# --- TDR.4-6 facts and tables ---------------------------------------------------------------------------------------
COLS = {
    "TDR.4": ("name", "basis_note", "evidence_id", "locator"),
    "TDR.5": ("observation", "evidence_id", "locator"),
    "TDR.6": ("amount", "unit", "currency", "period_end", "evidence_id", "locator", "quote"),
}
TITLES = {
    "TDR.4": ("Candidate peers", "peer_id"),
    "TDR.5": ("Provisional alignment observations", "peer_id.dimension"),
    "TDR.6": ("Located peer/transaction figures", "peer_id.operand"),
}  # the O7 plan R7 list
FORBIDDEN = ["included", "comparability", "normalised", "median", "position", "flag", "outlier"]
assert not set(FORBIDDEN) & {c for cols in COLS.values() for c in cols}
FACTS, ROWS = {}, {t: [] for t in COLS}


def cell(t, r, f, shown, vc, cites=(), **kw):
    d = {
        "fact_id": f"{t}.{r}.{f}",
        "table_id": t,
        "row_id": r,
        "field": f,
        "label": f.replace("_", " "),
    }
    d |= kw or {"text": shown, "status": "known"}
    d |= {"value_class": vc} | ({"citations": list(cites)} if cites else {})
    return d, shown


def add(t, r, cells):
    FACTS[f"{t}.{r}"] = [c[0] for c in cells]
    ROWS[t].append([r, dict(zip(COLS[t], (c[1] for c in cells), strict=True))])


for c in CAND:
    r, ci = c["peer_id"], c["citation"]
    add(
        "TDR.4",
        r,
        [
            cell("TDR.4", r, "name", c["name"], "analyst_judgment", [ci]),
            cell("TDR.4", r, "basis_note", c["basis_note"], "analyst_judgment"),
            cell("TDR.4", r, "evidence_id", ci["source_id"], "source"),
            cell("TDR.4", r, "locator", ci["locator"], "source"),
        ],
    )
for o in OBS:
    r, ci = f"{o['peer_id']}.{o['dimension']}", o["citation"]
    add(
        "TDR.5",
        r,
        [
            cell("TDR.5", r, "observation", o["observation"], "analyst_judgment", [ci]),
            cell("TDR.5", r, "evidence_id", ci["source_id"], "source"),
            cell("TDR.5", r, "locator", ci["locator"], "source"),
        ],
    )
CELL_WHY = {}
for g in FIGS:
    r, ci = f"{g['peer_id']}.{g['operand']}", g["citation"]
    amt = amount_of(ci["quote"])
    why = NOT_READABLE if amt is None else (AFTER_CUTOFF if g["period_end"] > CUTOFF else None)
    if why:
        CELL_WHY[r] = why
        a = cell(
            "TDR.6",
            r,
            "amount",
            f"missing: {why}",
            "analyst_judgment",
            status="missing",
            limitation=why,
        )
    else:
        a = cell(
            "TDR.6",
            r,
            "amount",
            ci["quote"],
            "source",
            [ci],
            amount=canon(amt),
            unit="MILLIONS",
            currency=g["currency"],
            scale="1000000",
            decimals=1,
            period=f"Twelve months to {g['period_end']}",
            status="known",
        )
    tx = [
        cell("TDR.6", r, f, v, "source")
        for f, v in (
            ("unit", g["unit"]),
            ("currency", g["currency"]),
            ("period_end", g["period_end"]),
            ("evidence_id", ci["source_id"]),
            ("locator", ci["locator"]),
            ("quote", ci["quote"]),
        )
    ]
    add("TDR.6", r, [a, *tx])
assert CELL_WHY == {"p03.revenue": AFTER_CUTOFF, "p04.interest": NOT_READABLE}

# --- CP-1C over the bound head: the sheet and the statistics ---------------------------------------------------
SHEET = []
for k, p in PEERS.items():
    pes = {
        f["period_end"] for f in FIGS if f["peer_id"] == k and f"{k}.{f['operand']}" not in CELL_WHY
    }
    assert pes == {p["pe"]}, (
        k
    )  # the readable, in-time figures of a peer share one period end: the sheet row's
    am = {
        op: None if f"{k}.{op}" in CELL_WHY else amount_of(p["toks"][i]) for i, op in enumerate(OPS)
    }
    SHEET.append(
        {
            "peer_id": k,
            "name": p["name"],
            "currency": p["cur"],
            "cmp": p["cmp"],
            "period_end": p["pe"],
            "amounts": am,
        }
    )
ADMITTED = [s for s in SHEET if s["currency"] == RUN_CUR]  # unit is millions on every row
NOT_ADMITTED = [
    {
        "peer_id": s["peer_id"],
        "name": s["name"],
        "currency": s["currency"],
        "unit": "millions",
        "reason": f"currency {s['currency']} is not the run's {RUN_CUR}",
    }
    for s in SHEET
    if s["currency"] != RUN_CUR
]
PEER_METRICS = {
    s["peer_id"]: {
        k: None if (x := ratio(s["amounts"], n, d)) is None else canon(x) for k, n, d in METRICS
    }
    for s in ADMITTED
}
STATS = {}
for k, n, d in METRICS:
    vals = [
        x for s in ADMITTED if s["cmp"] in INCLUDED if (x := ratio(s["amounts"], n, d)) is not None
    ]
    STATS[k] = {
        "n": len(vals),
        "sorted_included_values": [canon(x) for x in sorted(vals)],
        "median": canon(median(vals)) if len(vals) >= MIN_PEERS else None,
    }
INCLUDED_COUNT = sum(s["cmp"] in INCLUDED for s in ADMITTED)
assert (INCLUDED_COUNT, len(ADMITTED)) == (4, 5)
assert {k: v["n"] for k, v in STATS.items()} == {
    "adjusted_ebitda_margin": 3,
    "total_leverage_adjusted": 4,
    "interest_coverage_adjusted": 3,
    "ffo_to_debt": 4,
}
FROZEN = CP1C_EXP["cases"]["positive"][
    "operands_summary"
]  # same peers and figures bar the two missing cells: unaffected values agree
assert all(
    v == FROZEN["peer_metrics"][f"{p}.{k}"]
    for p, m in PEER_METRICS.items()
    for k, v in m.items()
    if v is not None
)
assert all(
    STATS[k]["median"] == FROZEN["stats"][k]["median"]
    for k in ("total_leverage_adjusted", "ffo_to_debt")
)
GAP_NEW = "No peer figures: the CP-DR peer pack carries no enterprise value figure"
GAP_OLD = (
    "No peer figures: cp_dr_public peers come from the CP-DR peer pack (Part B O7d)"  # cp1c.py:1416
)

# --- the CP-0 and CP-1 literals, adapted from cases/cp1c-owner/submissions.json positive as cpdr-research-owner does ---
POS = CP1C["positive"]
LIM_U = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
LIM_R = "Synthetic research note; invented test data; not a market fact."
cover = {i: cite(i, LINES[i][4]) for i in EVS}
cp0 = copy.deepcopy(POS["readiness_review"])
cp0["objective"] = (
    "Historical financial foundation, LOCAL research and a peer benchmark over supplied evidence"
)
cp0["sources"] = [s for s in cp0["sources"] if s["source_id"] != "peers"] + [
    {
        "source_id": i["id"],
        "document_family": i["family"],
        "authority": "third_party",
        "entity": f"Synthetic {i['who']}",
        "period": longdate(i["published"]),
        "version_relationship": "Supplied research item",
        "fidelity": "verified",
        "citations": [cover[i["id"]]],
        "limitations": [LIM_R],
    }
    for i in ITEMS
]
rows = {c["module_id"]: c for c in cp0["consumers"]}
base = rows["CP-1"]["citations"] + list(cover.values())
cpdr_row = {
    "module_id": "CP-DR",
    "readiness": "READY_WITH_LIMITATIONS",
    "evidence_demand": "Supplied research items, located and dated, that answer the locked brief and locate peer figures",
    "source_ids": PACK_SOURCES,
    "rationale": "Research can run on the supplied items; questions they cannot answer stay missing.",
    "citations": base,
    "missing_source": None,
    "limitations": [LIM_U, LIM_R],
}
cp1c_row = rows["CP-1C"] | {
    "source_ids": PACK_SOURCES,
    "evidence_demand": "Settled CP-1 ratios and located peer figures on aligned definitions",
    "citations": base,
    "limitations": [LIM_U, LIM_R],
    "rationale": "The benchmark can run on settled CP-1 figures and the located peer figures of the CP-DR pack with explicit limitations.",
}
cp0["consumers"] = [rows["CP-1"], cpdr_row, cp1c_row]
cp0["analysis"] = [
    {
        "claim_id": "source-assessment",
        "citations": base[:2] + [cover["ev-1"]],
        "limitation": LIM_U,
        "text": "Located statements and the supplied research items support a research dossier and a peer benchmark with limitations.",
    }
]
cp1_ctx = copy.deepcopy(POS["cp1_source_context"])
cp1_ctx["sources"] = [s for s in cp1_ctx["sources"] if s["source_id"] != "peers"] + [
    {
        "source_id": i["id"],
        "classification": "nonfinancial",
        "document_type": "Supplied research item (synthetic)",
        "published_on": i["published"],
        "evidence_class": "external",
        "evidence_rationale": "Third-party research item without auditor or filing status",
        "analytical_use": "Research and peer figures for CP-DR and CP-1C",
        "citations": [cover[i["id"]]],
        "event_scan": "unassessed",
        "event_scan_explanation": "A research item is not event evidence",
    }
    for i in ITEMS
]
rr = POS["cp1_readiness"]
c1c = rr["payload"]["consumers"][0]
cpdr_gaps = [
    dict(
        c1c["gaps"][0],
        rationale="Every retained source-context and audit warning bears on the reliability of the issuer facts the research questions are tailored from.",
    )
]
cpdr_req = [
    {
        "requirement": "consumer_specific_cp1_sufficiency",
        "status": "limited",
        "evidence_ids": c1c["requirements"][0]["evidence_ids"],
        "actions": ["Retain the unaudited-statement limitation in the dossier."],
        "rationale": "The settled CP-1 statements support the research brief tailoring; the statements are unaudited.",
    }
]
cp1_ready = {
    "step": "readiness",
    "derived_from": "cases/cp1c-owner/submissions.json positive.cp1_readiness: entry CP-1C kept, entry CP-DR added as cases/cpdr-research-owner does",
    "payload": {
        "inputs_sha256": "{{PREFILLED:inputs_sha256}}",
        "consumers": [{"entry": "CP-DR", "requirements": cpdr_req, "gaps": cpdr_gaps}, c1c],
    },
    "run_time_bindings": rr["run_time_bindings"],
    "validated": "NOT run: no CP-1 catalogue exists without a promoted run; both entries reuse the validated cp1c-owner evidence ids and gap scope",
}

# --- CP-1C analyst submission, refusal inputs, submissions ------------------------------------------------------------
CP1C_SUB = copy.deepcopy(POS["peer_benchmark"])
QUOTE = {p: f"{PEERS[p]['name']} {PEERS[p]['basis']}" for p in ("p01", "p02", "p03")} | {
    "p04": "its twelve months end on September 30, 2025",
    "p05": "six operating segments",
}
for a, (p, q) in zip(CP1C_SUB["assessments"], QUOTE.items(), strict=True):
    assert (a["peer"], a["comparability"]) == (PEERS[p]["name"], PEERS[p]["cmp"]), p
    a["evidence"] = [cite("ev-1", q)]
CP1C_SUB["overall"].update(
    rationale="The issuer's total leverage of {T1C.3.issuer.total_leverage_adjusted|x} is below the peer median of {T1C.4.total_leverage_adjusted.median|x}, its interest coverage of "
    "{T1C.3.issuer.interest_coverage_adjusted|x} equals the median of {T1C.4.interest_coverage_adjusted.median|x}, and its adjusted EBITDA margin of {T1C.3.issuer.adjusted_ebitda_margin|%} is above "
    "the median of {T1C.4.adjusted_ebitda_margin.median|%}. The outlier register shows which peers distort a metric, so the median is the reference.",
    limitation="The universe is a small set of located figures, and two figures are missing from it.",
)
CP1C_SUB["gaps"] = [
    {
        "gap": "One candidate peer reports in euros and is not in the peer sheet.",
        "why_it_matters": "It cannot enter the statistics on the run's currency basis.",
        "affected_analysis": "Peer universe",
        "severity": "Material",
        "action": "Obtain the peer's figures in the run's currency basis and widen the universe.",
    }
]
cited = sorted(int(e["locator"][5:]) for a in CP1C_SUB["assessments"] for e in a["evidence"])
fig = {(f["peer_id"], f["operand"]): f for f in FIGS}
REFUSAL_INPUTS = {
    "operand_unknown": fig["p01", "revenue"] | {"operand": "gross_margin"},
    "not_in_tdr4": fig["p01", "revenue"] | {"peer_id": "p07"},
    "typed_amount": fig["p01", "revenue"] | {"amount": "200.0"},
    "leak_field": OBS[1] | {"included": False},
    "both_sources": "the same store with the cp1c-owner positive peers source added to the pack: cases/cp1c-owner/manifest.json#synthetic_source/positive",
    "note": "each object replaces the same-position entry of research_peers.peers",
}
SUBMISSIONS = {
    "schema_version": "cpdr-peers-owner-cases/1",
    "note": "Literal reference-and-judgment payloads. Analyst text is digit-free; evidence ids live in structured fields. The peers payload (candidates, observations, figures; a figure carries peer_id, operand, unit, currency, period_end and a citation, never an amount) is declared by this oracle for O7d to match.",
    "cp0_readiness_review": cp0,
    "cp1_source_context": cp1_ctx,
    "cp1_readiness": cp1_ready,
    "brief": {"context_research_questions": [CTX_Q], "model_tailored_defaults_only": DEFAULTS},
    "research_peers": {
        "run_id": RUN_ID,
        "answers": ANSWERS,
        "peers": {"candidates": CAND, "observations": OBS, "figures": FIGS},
    },
    "tool_calls": {
        "research": TOOL_RESEARCH,
        "cp1c": [READ_INPUTS, read("ev-1", cited[0], cited[-1])],
    },
    "cp1c_peers": CP1C_SUB,
    "refusal_inputs": REFUSAL_INPUTS,
}

# --- manifest ---------------------------------------------------------------------------------------------------------------
ROWS_BYTES = (
    json.dumps(
        [
            {k: i[k] for k in ("path", "family", "published", "locator")} | {"tag": "research"}
            for i in ITEMS
        ],
        indent=1,
    )
    + "\n"
)
RUN = {
    "run_id": RUN_ID,
    "issuer_id": ISSUER_ID,
    "issuer_name": ISSUER_NAME,
    "as_of": AS_OF,
    "method_version": "deploy-v-r14",
    "case_kind": "synthetic",
    "pathway": "relative_value",
    "requested_modules": ["CP-1C", "CP-DR"],
    "cp_dr_invoked": True,
    "cp_dr_version": VERSION,
    "cp_dr_lineage": "LOCAL",
}
MANIFEST = {
    "schema_version": "cpdr-peers-owner-cases/1",
    "scope": "CP-DR LOCAL research with the opt-in peer pack (TDR.4-6) and CP-1C reading TDR.6 as its peer sheet (cp-dr/2026-10-31; Part B O7d D0a)",
    "status": "Preparation oracle (pre-code); UNFROZEN: pins are written at freeze, after independent review; not executed",
    "raw_rule": "Literal UTF-8 LF, no terminal LF per page; an item's sha256 is the sha256 of its single page text",
    "pins": PINS,
    "financial_baseline": {
        "path": "cases/financial/manifest.json",
        "sources": [
            {
                "source_id": k,
                "sha256": SHA[k],
                "reuse": "page texts and locators byte-identical; read by reference",
            }
            for k in ("identity", "financial")
        ],
    },
    "synthetic_source": {
        "SYNTHETIC": True,
        "label": "Invented test data. The peers and publishers do not exist; no figure is a real market fact; every page says so.",
        "sentence_on_every_page": SYNTH,
        "locator_rule": "every locator is an .example URL; no real publisher, regulator, index or company",
        "rules_from": "cases/cp1c-owner/manifest.json#synthetic_source",
    },
    "run": RUN,
    "plan": {
        "requested_modules": RUN["requested_modules"],
        "plan_order": ["CP-0", "CP-1", "CP-DR", "CP-1C"],
        "_source": "deploy_vii.registry.plan(('CP-1C','CP-DR')) == ('CP-0','CP-1','CP-DR','CP-1C'), run read-only at HEAD 0d37ba89",
    },
    "context": {
        "base": "cases/context/research-minimal.json",
        "peer_source": "cp_dr_public",
        "basis": "auto",
        "reporting_currency": RUN_CUR,
        "research_questions": [CTX_Q],
        "_note": "the base file as it is; the one context question (focus CP-1C) is the only addition",
    },
    "cutoff": CUTOFF,
    "research_manifest": {
        "file": "research-manifest.json",
        "file_bytes": ROWS_BYTES,
        "file_sha256": sha(ROWS_BYTES),
    },
    "evidence": [
        {k: i[k] for k in ("id", "path", "family", "published", "locator", "role")}
        | {
            "tag": "research",
            "pages": [{"locator": "file", "text": TEXT[i["id"]]}],
            "page_join_sha256": PSHA[i["id"]],
        }
        for i in ITEMS
    ],
    "host_scope": {
        "CP-DR": {"brief": ["identity", "financial"], "research": PACK_SOURCES},
        "CP-1C": {"peer_benchmark": PACK_SOURCES},
        "_rule": "CP-1C: identity, financial, peers when held (none here), then every held ev-* in pack order (cases/cpdr-research-owner/expected.json#consumers/cp1c_scope)",
    },
    "cp0_cp1_pair": {
        "reused_from": "cases/cp1c-owner/submissions.json positive (readiness_review, cp1_source_context, cp1_readiness)",
        "sources_adapted": "the cp1c 'peers' source is dropped; one row per ev-* item is added (every prepared source is assessed once); consumers CP-1, CP-DR and CP-1C",
    },
    "run_time_markers": "as cases/cpdr-research-owner/manifest.json#run_time_markers, plus {{EVID:SP}} and {{EVID:CON}} (copied from cases/cp1c-owner)",
    "cases": [
        {
            "case_id": "positive",
            "run_id": RUN_ID,
            "submission": "submissions.json#research_peers",
            "expected": "expected.json",
        },
        {
            "case_id": "both_sources",
            "submission": "submissions.json#refusal_inputs/both_sources",
            "expected": "expected.json#refusals/peers/both_sources_conflict",
        },
    ],
}

# --- expected ---------------------------------------------------------------------------------------------------------------
MATRIX = [
    [ps, cd, cr, cd and cr and ps == "cp_dr_public"]
    for ps in ("cp_dr_public", "user_list", "user_comps", "none")
    for cd in (True, False)
    for cr in (True, False)
]
assert sum(r[3] for r in MATRIX) == 1


def reason_case(
    template, **values
):  # a template and one worked example (the example's reason is the template filled)
    return {"template": template, "example": {**values, "reason": template.format(**values)}}


# O7-R66: the peers.py reason texts at HEAD (research/peers.py _basis_refusal, _admit, _sheet and the _Unusable raises).
# None names model text: a currency or unit is echoed only after _unsafe passed it (fence and cell rule), a row id and a
# field are Identifiers ([A-Za-z0-9_.:-]), and an unsafe text is never quoted. Each is short and cell-safe.
NOT_ADMITTED_REASONS = {
    "currency": reason_case(
        "currency {currency} is not the run's {run_currency}", currency="EUR", run_currency=RUN_CUR
    ),
    "unit": reason_case("unit {unit} is not millions", unit="thousands"),
    "different_dates": reason_case("the located figures end on different dates"),
    "no_figure": reason_case("no figure is located"),
    "no_amount": reason_case("no figure amount is located"),
    "issuer": reason_case("named as the issuer"),
}
assert NOT_ADMITTED_REASONS["currency"]["example"]["reason"] == NOT_ADMITTED[0]["reason"]
PACK_UNUSABLE = {
    "malformed_cell": reason_case(
        "{where}: the {field} cell is not a stated text", where="TDR.4 p01", field="name"
    ),
    "malformed_amount_cell": reason_case(
        "{where}: the amount cell is neither located nor missing", where="TDR.6 p01.revenue"
    ),
    "duplicate_name": reason_case("TDR.4: two peers share one name"),
    "unknown_operand": reason_case(
        "{where}: not a TDR.4 peer's CP-1C operand", where="TDR.6 p01.gross_margin"
    ),
    "non_ev_citation": reason_case(
        "{where}: the amount cell is not one number quoted from an ev-* item",
        where="TDR.6 p01.revenue",
    ),
    "unsafe_delimiter": reason_case(
        "{where} {field}: holds a block delimiter or a lookalike of one",
        where="TDR.4 p01",
        field="name",
    ),
    "unsafe_cell": reason_case(
        "{where} {field}: holds a line break or a pipe character", where="TDR.4 p01", field="name"
    )
    | {
        "code_text_at_head": "{where} {field}: holds a line break or a |",
        "unfit": "the code text holds a | and so cannot itself sit in a dossier table cell; the builder changes it to the template",
    },
    "repeated_cell": reason_case(
        "{where}: the {field} cell appears twice", where="TDR.6 p01.revenue", field="unit"
    ),
    "period_end_not_a_date": reason_case(
        "{where}: period_end is not a calendar date", where="TDR.6 p01.revenue"
    ),
}
for _c in (
    *NOT_ADMITTED_REASONS.values(),
    *PACK_UNUSABLE.values(),
):  # cell-safe: no line break or <<< in an example
    assert not any(t in _c["example"]["reason"] for t in ("\n", "\r", "<<<")), _c
assert all(
    "|" not in c["template"] and "|" not in c["example"]["reason"] for c in PACK_UNUSABLE.values()
)

EXPECTED = {
    "schema_version": "cpdr-peers-owner-expected/1",
    "derivation_note": "Derived by builder/build.py with the stdlib from the invented pages, O7-R47 Q4-Q6 and the method texts; no product module is imported or run. Each _source names where a value comes from.",
    "version": VERSION,
    "intake": {
        "cutoff": CUTOFF,
        "pack_sources": PACK_SOURCES,
        "accepted": [
            {k: i[k] for k in ("id", "family", "published", "locator", "path")}
            | {"sha256": PSHA[i["id"]], "disposition": "accepted"}
            for i in ITEMS
        ],
    },
    "brief": {
        "question_ids": [q["question_id"] for q in QUESTIONS],
        "kinds": [q["kind"] for q in QUESTIONS],
        "receivers": {q["question_id"]: q["receivers"] for q in QUESTIONS},
        "focus_modules": {q["question_id"]: q["focus_module"] for q in QUESTIONS},
        "anchor": {"cp0_sha256": "{{CP0_RESULT_SHA256}}", "cp1_sha256": "{{CP1_RESULT_SHA256}}"},
        "peer_pack": True,
        "cutoff": CUTOFF,
        "as_of": AS_OF,
        "version": VERSION,
        "_source": "O7-R47 Q4: peer_pack = cp_dr invoked and peer_source == cp_dr_public and CP-1C in requested_modules; all three hold in this run (manifest#run, #context)",
    },
    "cp0_cp1_pair": {
        "statuses": {"CP-0": "restricted", "CP-1": "restricted"},
        "status_source": "cases/cp1c-owner/expected.json execution.statuses, by reference, not run with the ev-* sources",
    },
    "opt_in_matrix": {
        "rule": "peer_pack = cp_dr and cp1c_requested and peer_source == cp_dr_public (O7-R47 Q4); with cp_dr false no brief exists and no pack is requested (O7 plan OD9)",
        "columns": ["peer_source", "cp_dr", "cp1c_requested", "peer_pack"],
        "rows": MATRIX,
        "frozen_case": {
            "case": "cpdr-research-owner",
            "peer_source": "cp_dr_public",
            "cp_dr": True,
            "cp1c_requested": False,
            "peer_pack": False,
            "key": "cases/cpdr-research-owner/expected.json#brief/peer_pack",
        },
    },
    "tables": {
        t: {
            "title": TITLES[t][0],
            "row_header": TITLES[t][1],
            "columns": list(COLS[t]),
            "rows": ROWS[t],
        }
        for t in COLS
    }
    | {
        "_source": "rows are [row_id, {column: shown}] in submission order; peer_id.dimension and peer_id.operand are the O7 plan R7 row ids; a missing cell shows 'missing: <limitation>' (cpdr-research-owner dossier layout); a locator is the citation's line:<n>"
    },
    "facts": {
        "_source": "one fact per column (contracts.validate_tables); key = <table_id>.<row_id>, value = the row's facts in column order; amount is canonical (decimals 1 = the quote's digits); a missing fact carries the limitation without the 'missing: ' prefix"
    }
    | FACTS,
    "no_ownership_leak": {
        "forbidden_fields": FORBIDDEN,
        "columns": {t: list(c) for t, c in COLS.items()},
        "intersection": [],
        "_source": "plan O7d D0a: CP-1C owns inclusion, normalisation and every statistic; a submission carrying one of these fields is a shape refusal",
    },
    "cp1c": {
        "sheet_rows": [
            {k: s[k] for k in ("peer_id", "name", "period_end")}
            | {"amounts": {k: None if v is None else canon(v) for k, v in s["amounts"].items()}}
            for s in ADMITTED
        ],
        "sheet_count": len(ADMITTED),
        "not_admitted": NOT_ADMITTED,
        "included_count": INCLUDED_COUNT,
        "comparability": {s["peer_id"]: s["cmp"] for s in ADMITTED},
        "_sheet_source": "TDR.4 name; TDR.6 amounts (null for a missing cell); period_end = the common period end of the peer's located figures; rows admitted when currency == the run's USD and unit == millions (plan O7d D2 route, O7-R47 Q5)",
        "peer_metrics": PEER_METRICS,
        "medians": STATS,
        "_median_source": "cp1c.md Statistics: over included peers with a calculated value, at least three; a missing operand gives a missing ratio (cp1c.py:426-440; cases/cp1c-owner/expected.json#cases/gap); 38-digit half-even; leverage and ffo medians equal cases/cp1c-owner/expected.json#cases/positive (same four peers, same values)",
        "t1c6": {
            "status": "not_applicable",
            "limitation": "the CP-DR peer pack carries no issuer line",
            "rows": [k for k, _, _ in METRICS],
            "cells": ["sheet", "difference"],
            "result": "Not compared",
            "_source": "O7-R47 Q6: a pack sheet has no issuer row; the cp1 cell stays the copied CP-1 value; 'Not compared' is cp1c.py _tie_out's result text (:1177)",
        },
        "t1c9_gap_reason": GAP_NEW,
        "t1c9_gap_reason_replaces": GAP_OLD,
        "t1c11_reason": f"{GAP_NEW}; precedents 0 admitted of {MIN_PEERS} required",
        "_gap_source": "PUBLIC_GAPS['cp_dr_public'] (cp1c.py:1416) amended per O7-R47 Q5; T1C.11 under auto appends '; precedents N admitted of 3 required' (cp1c.py:1696-1699, valuation_basis.MIN_ADMITTED); the context lists no precedent",
        "head_binds_input": "CP-DR",
        "citation_rule": "every TDR.6-derived fact's citation is an ev-* quote",
    },
    "refusals": {
        "peers": {
            "unlocated_figure": f"missing: {NOT_READABLE}",
            "after_cutoff": f"missing: {AFTER_CUTOFF}",
            "operand_unknown": "p01.gross_margin: operand is not a CP-1C operand",
            "not_in_tdr4": "p07.revenue: peer_id is not a TDR.4 candidate",
            "pack_not_requested": "peer pack not requested",
            "pack_missing": "peer pack requested; peers missing",
            "both_sources_conflict": "Peer source conflict: the pack holds a peers source and the CP-DR head carries TDR.6",
            "inputs": {
                "unlocated_figure": "TDR.6.p04.interest.amount (quote 24.00)",
                "after_cutoff": "TDR.6.p03.revenue.amount (period_end 2026-03-31)",
                "operand_unknown": "submissions.json#refusal_inputs.operand_unknown",
                "not_in_tdr4": "submissions.json#refusal_inputs.not_in_tdr4",
                "typed_amount": "submissions.json#refusal_inputs.typed_amount (shape refusal)",
                "leak_field": "submissions.json#refusal_inputs.leak_field (shape refusal)",
            },
            "not_admitted_reasons": NOT_ADMITTED_REASONS,
            "pack_unusable": PACK_UNUSABLE,
            "_source": "unlocated_figure and after_cutoff are the plan's fixed texts (O7d D0a); pack_not_requested and pack_missing the plan's D1a texts; both_sources_conflict the plan's section 1 issue text; operand_unknown and not_in_tdr4 are preparer texts in the research-review form '<where>: <text>'",
        }
    },
    "bindings": {
        "evidence": ["TDR.1", "TDR.2", "TDR.4", "TDR.5", "TDR.6"],
        "limitations": ["TDR.3"],
        "_source": "plan O7d D0a; O7 plan R7 list (TDR.4-6 on the Evidence rail)",
    },
    "tool_use": {
        "research": "read_inputs once; read_pages over line:<n> for every cited line (ranges in tool_calls.research); search_pack over each searched item backs each not_found answer",
        "calls": "submissions.json tool_calls.research",
        "CP-DR": "brief: read_inputs once; source scope every held non-ev source (identity and financial in this pack), zero ev-* reads; research: read_inputs once, ok read_pages over line:<n> for every cited line, TDR.4, TDR.5 and TDR.6 citations included (ranges in tool_calls.research), search_pack over each searched item backs each not_found answer",
        "CP-1C": "read_inputs once (the module_context view, CP-DR upstream row included); ok read_pages over line:<n> of every ev-* line the assessments cite (range in tool_calls.cp1c); source scope identity, financial and every held ev-* item, no peers source; the figures come from the TDR.6 head facts, not from a model quote",
    },
    "not_verified": [
        "no product code ran; every value is derived from the pages and the cited texts",
        "the Fact field layout, the row-id forms and the peers payload shape are declared by this oracle for the builders to match",
        "T1C.7 rows for not-admitted peers are keyed as peer and reason only; the gap-row columns are the D2 builder's",
    ],
}


def dump(
    o, limit, level=0
):  # one-space indent down to `limit` levels; a list's elements stay on one line each
    if level >= limit or not isinstance(o, dict | list) or not o:
        return json.dumps(o, ensure_ascii=False)
    pad, end = " " * (level + 1), "\n" + " " * level
    if isinstance(o, dict):
        return (
            "{\n"
            + ",\n".join(f"{pad}{json.dumps(k)}: {dump(v, limit, level + 1)}" for k, v in o.items())
            + end
            + "}"
        )
    if not any(isinstance(v, dict | list) for v in o):
        return json.dumps(o, ensure_ascii=False)
    return "[\n" + ",\n".join(pad + json.dumps(v, ensure_ascii=False) for v in o) + end + "]"


def write(
    name, obj, limits
):  # limits: depth per top-level key (default 1: the key's value on one line)
    top = ",\n".join(f" {json.dumps(k)}: {dump(v, limits.get(k, 1), 1)}" for k, v in obj.items())
    (OUT / name).write_text("{\n" + top + "\n}\n", encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
write("manifest.json", MANIFEST, {"evidence": 2})
write(
    "submissions.json",
    SUBMISSIONS,
    {"research_peers": 4, "tool_calls": 3, "cp1c_peers": 3, "refusal_inputs": 2},
)
write(
    "expected.json", EXPECTED, {"tables": 4, "facts": 2, "cp1c": 3, "opt_in_matrix": 2, "intake": 3}
)
