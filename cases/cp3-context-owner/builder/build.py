"""Writes cases/cp3-context-owner/* (stdlib only; deploy_vii and deploy_workflow are never imported).

Phase 3 Task 0 oracle: CP-3 and CP-3D market evidence read from the `context` source. Every expected
value is hand-derived from the Phase 3 plan (Design 1-9), the rulings (B6, B17 item 3, Q-X) and the
frozen R3 oracle read here by hash (cases/cp3-cp6-owner/*); none is read from code the phase builds.

Run: python3 -I cases/cp3-context-owner/builder/build.py   (from the repository root)
Two runs write byte-identical files.
"""

import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "cp3-context-owner"
CASE_DIR = "cases/cp3-context-owner"

# --- 0. frozen inputs, pinned by hash --------------------------------------------------------------
PINS = {
    "cases/cp3-cp6-owner/manifest.json": "18250c810827e45269d06b7647b820064470bf3a5cbb681bc524bb96c8b68857",
    "cases/cp3-cp6-owner/submissions.json": "9f8c10e9e31e88f15f797c89102c6cf2d938b25a1878d2b5aafe5354786dde38",
    "cases/cp3-cp6-owner/expected.json": "8d9cd9522eefe8d6918a551613cd475d9231cd3b0269448dcdef40fdb464118f",
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/cp3d-owner/expected.json": None,  # hash recorded, not asserted here (read for line cites only)
}
RAW = {}
for rel, digest in PINS.items():
    RAW[rel] = (ROOT / rel).read_bytes()
    if digest is not None:
        assert hashlib.sha256(RAW[rel]).hexdigest() == digest, f"input drift: {rel}"
PINS["cases/cp3d-owner/expected.json"] = hashlib.sha256(
    RAW["cases/cp3d-owner/expected.json"]
).hexdigest()
R3_M = json.loads(RAW["cases/cp3-cp6-owner/manifest.json"])
R3_S = json.loads(RAW["cases/cp3-cp6-owner/submissions.json"])
R3_E = json.loads(RAW["cases/cp3-cp6-owner/expected.json"])
FIN = json.loads(RAW["cases/financial/manifest.json"])
SNAP = json.loads(RAW["cases/snapshot/manifest.json"])


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def line_of(rel, needle):
    """1-based line of the first occurrence of `needle` in a pinned input (a path:line cite)."""
    for n, line in enumerate(RAW[rel].decode("utf-8").splitlines(), 1):
        if needle in line:
            return n
    raise AssertionError(f"{rel}: {needle!r} not found")


R3E = "cases/cp3-cp6-owner/expected.json"
R3S = "cases/cp3-cp6-owner/submissions.json"

# --- 1. the run and the pack -----------------------------------------------------------------------
R3_RUN = R3_M["cases"][0]["runs"]["R3"]["run"]
assert R3_RUN["as_of"] == "2026-01-10" and R3_RUN["issuer_id"] == "northbridge-synthetic"
AS_OF = R3_RUN["as_of"]
ISSUER_ID, ISSUER_NAME = R3_RUN["issuer_id"], R3_RUN["issuer_name"]
FACILITIES = {"term-loan"}  # CP-1 T4.18 ids of the pack (cases/cp3-cp6-owner/builder/build.py:788)
FACILITY_NAME = "Northbridge Term Loan"

SRC_SHA = {s["source_id"]: s["sha256"] for s in FIN["sources"]}
SRC_SHA["business"] = SNAP["business_source"]["positive"]["sha256"]
SRC_SHA["market"] = R3_M["market_source"]["sha256"]
PACK_SOURCES_R3 = [
    {
        "source_id": s["source_id"],
        "name": s["name"],
        "status": s["status"],
        "sha256": SRC_SHA[s["source_id"]],
    }
    for s in R3_M["cases"][0]["pack_sources"]
]
assert [s["source_id"] for s in PACK_SOURCES_R3] == ["identity", "financial", "business", "market"]
PACK_SOURCES_S1 = [s for s in PACK_SOURCES_R3 if s["source_id"] != "market"]


# --- 2. context files ------------------------------------------------------------------------------
def quote(fid, kind, as_of, provider, bid="", ask="", price="", yield_pct="", spread_bps=""):
    return {
        "facility_id": fid,
        "kind": kind,
        "bid": bid,
        "ask": ask,
        "price": price,
        "yield_pct": yield_pct,
        "spread_bps": spread_bps,
        "as_of": as_of,
        "provider": provider,
    }


def deal(fid, as_of, provider, sl="", sh="", ol="", oh=""):
    return {
        "facility_id": fid,
        "instrument": FACILITY_NAME,
        "currency": "USD",
        "size_m": "",
        "tenor_years": "",
        "talk_spread_bps_low": sl,
        "talk_spread_bps_high": sh,
        "talk_oid_low": ol,
        "talk_oid_high": oh,
        "floor_pct": "",
        "call_protection": "",
        "use_of_proceeds": "",
        "as_of": as_of,
        "provider": provider,
    }


def context(run_type, quotes=(), deals=(), issuer_id=ISSUER_ID):
    return {
        "schema": "context/1",
        "run": {
            "run_type": run_type,
            "pathway": "credit_snapshot",
            "case_kind": "synthetic",
            "as_of": AS_OF,
            "current_period": "",
            "prior_period": "",
            "reporting_currency": "USD",
        },
        "identity": {
            "issuer_name": ISSUER_NAME,
            "issuer_id": issuer_id,
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
        "deal_terms": list(deals),
        "quotes": list(quotes),
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
            "portfolio_workbook": False,
            "prior_case": False,
            "management_bridge": False,
            "legal_documents": "executed",
        },
        "research_questions": [],
    }


Q1 = quote(
    "term-loan", "observed", "2026-01-09", "Dealer A", "98.50", "99.00", "98.75", "8.25", "340"
)
Q2 = quote(
    "term-loan", "indicative_talk", "2026-01-10", "Dealer B", price="99.25", spread_bps="335"
)
QS1 = quote("term-loan", "observed", "2025-12-11", "Dealer A", "98.25", "98.75", "98.50")
QS2 = quote("term-loan", "observed", "2025-12-10", "Dealer B", "98.00", "98.50", "98.25")
QX = quote("revolver-x", "observed", "2026-01-09", "Dealer C", "99.10", "99.60")
QE = quote("term-loan", "observed", "2026-01-09", "Dealer D")  # every figure empty
BAD_Q = quote("term-loan", "observed", "2026-02-01", "Dealer A", "98.50", "99.00", "98,75")
DEAL = deal("term-loan", "2026-01-08", "Lead arranger", "325", "350", "99.0", "99.5")
QU1 = quote("term-loan", "observed", "2026-01-09", "Dealer A", "98.50", "99.00")
QU2 = quote(
    "term-loan", "observed", "2026-01-10", "Dealer B", "98.50", "99.00"
)  # same prefix, later fields differ
DU1 = deal("term-loan", "2026-01-08", "Lead arranger", "325", "350", "99.0", "99.5")
DU2 = deal("term-loan", "2026-01-09", "Co-arranger", "325", "350", "99.0", "99.5")
DEAL_LONE = deal("term-loan", "2026-01-08", "Lead arranger", sl="325", ol="99.0", oh="99.5")

CONTEXTS = {  # id: (layout, object)
    "observed-and-talk": ("indent", context("secondary", [Q1, Q2])),
    "talk-only": ("indent", context("secondary", [Q2])),
    "stale": ("indent", context("secondary", [QS1, QS2])),
    "unmatched": ("indent", context("secondary", [Q1, QX, QE])),
    "deal-talk": ("indent", context("primary", deals=[DEAL])),
    "deal-lone-bound": ("indent", context("primary", deals=[DEAL_LONE])),
    "unciteable": ("minified", context("secondary", [QU1, QU2])),
    "unciteable-deal": ("minified", context("primary", deals=[DU1, DU2])),
    "no-quotes": ("indent", context("secondary", [])),
    "minified": ("minified", context("secondary", [Q1, Q2])),
    "bad-bytes": ("indent", context("secondary", [BAD_Q], issuer_id="southbridge-synthetic")),
}


def render(layout, obj):
    if layout == "indent":
        return dumps(obj).encode("utf-8")
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )  # one line, no LF


CTX_BYTES = {cid: render(*spec) for cid, spec in CONTEXTS.items()}
CTX_PATH = {cid: f"{CASE_DIR}/contexts/{cid}.json" for cid in CONTEXTS}
assert all(
    (len(CTX_BYTES[c].decode("utf-8").splitlines()) == 1) == (CONTEXTS[c][0] == "minified")
    for c in CONTEXTS
)

# --- 3. citations: Design 3 (hand-derived; Python builds them in the phase) -------------------------
QFIELDS = ("bid", "ask", "price", "yield_pct", "spread_bps")
DFIELDS = ("talk_spread_bps_low", "talk_spread_bps_high", "talk_oid_low", "talk_oid_high")


def member(key, value):
    return f"{json.dumps(key)}: {json.dumps(value)}"


def cites_indent(cid):
    """(section, index, key) -> (line number, quote). The member sits alone on its line, so the
    quote is the member's own JSON text (`"price": "98.75"`, no trailing comma)."""
    lines = CTX_BYTES[cid].decode("utf-8").splitlines()
    out, section, idx = {}, None, -1
    for n, line in enumerate(lines, 1):
        if line in ('  "quotes": [', '  "deal_terms": ['):
            section, idx = line.strip().split('"')[1], -1
        elif section and line in ("  ],", "  ]"):
            section = None
        elif section and line == "    {":
            idx += 1
        elif section and line.startswith('      "'):
            key = line.strip().split('"')[1]
            out[(section, idx, key)] = (n, line.strip().rstrip(","))
    return out


COLLIDES = {}


def cites_minified(cid):
    """One line. The member does not sit alone on its line, so the quote is anchored: the text from
    the quote object's `{` through the figure's closing quote (Design 3). It must be unique."""
    text = CTX_BYTES[cid].decode("utf-8")
    obj = CONTEXTS[cid][1]
    out = {}
    for section in ("quotes", "deal_terms"):
        for idx, row in enumerate(obj[section]):
            row_text = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
            assert text.count(row_text) == 1, (cid, section, idx)
            start = text.index(row_text)
            later_rows = [
                json.dumps(r, separators=(",", ":"), ensure_ascii=False)
                for r in obj[section][idx + 1 :]
            ]
            prev_rows = [
                json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in obj[section][:idx]
            ]
            for key, value in row.items():
                if key not in QFIELDS + DFIELDS or not value:
                    continue  # only a supplied figure is ever cited
                m = f"{json.dumps(key)}:{json.dumps(value)}"
                assert row_text.count(m) == 1
                anchored = row_text[: row_text.index(m) + len(m)]
                if text.count(anchored) != 1:
                    # a residual collision (B20a): another row of this section opens with the same text, so the
                    # quote matches two objects (a guessed span): every colliding row is dropped into a gap.
                    assert any(r.startswith(anchored) for r in prev_rows + later_rows), (
                        "repeat is not a row prefix"
                    )
                    COLLIDES[(cid, section, idx)] = True
                assert (
                    text[start : start + len(anchored)] == anchored
                    or (cid, section, idx) in COLLIDES
                )
                out[(section, idx, key)] = (1, anchored)
    return out


CITES = {
    cid: (cites_minified(cid) if CONTEXTS[cid][0] == "minified" else cites_indent(cid))
    for cid in CONTEXTS
}


# --- 4. Python rows: Design 2, 5, 6, 7 -------------------------------------------------------------
STALE_LIMIT = 30
KIND_LABEL = {"observed": "Observed", "indicative_talk": "Indicative talk"}
USER_LABEL = "Market evidence rows from the context file are user-supplied figures"
CAP_STALE = "a context quote is more than 30 days old"
CAP_TALK = "the market evidence is indicative talk only"
CAP_CP2 = "CP-2 is restricted"
LABEL_TALK_ONLY = "Market evidence is indicative talk only, not an observed market level"


def days_before(row_date, run_date):
    return (date.fromisoformat(run_date) - date.fromisoformat(row_date)).days


def stale_text(fid, as_of, n):
    return f"Stale quote: {fid} quote dated {as_of} is {n} days before the run as-of {AS_OF} (limit {STALE_LIMIT})"


def python_evidence(cid):
    """Rows and own limitations Python builds from the context `cid` (hand-derived)."""
    obj, cites = CONTEXTS[cid][1], CITES[cid]
    rows, own = [], []
    for i, q in enumerate(obj["quotes"]):
        fid = q["facility_id"]
        if fid not in FACILITIES:
            own.append(
                f"Gap (Medium): context quote for facility {fid} matches no CP-1 facility (T4.18); not used"
            )
            continue
        supplied = [k for k in QFIELDS if q[k]]
        if (cid, "quotes", i) in COLLIDES and supplied:
            own.append(
                f"Gap (Medium): context quote row {i + 1} for facility {fid} cannot be cited as one unique span; not used"
            )
            continue
        if not supplied:
            own.append(
                f"Gap (Medium): context quote for facility {fid} carries no figure; not used"
            )
            continue
        parts = []
        for k in supplied:
            v = q[k]
            parts.append(
                {
                    "bid": f"bid {v}",
                    "ask": f"ask {v}",
                    "price": f"price {v}",
                    "yield_pct": f"yield {v}%",
                    "spread_bps": f"spread {v} bps",
                }[k]
            )
        rows.append(
            {
                "from": f"quotes[{i}]",
                "facility_id": fid,
                "kind": q["kind"],
                "quote_cell": f"{fid}: " + ", ".join(parts),
                "as_of": q["as_of"],
                "provider": q["provider"],
                "cite_keys": [("quotes", i, k) for k in supplied],
                "limitation_extra": [],
                "note": None,
            }
        )
    for i, d in enumerate(obj["deal_terms"]):
        fid = d["facility_id"]
        if fid not in FACILITIES:
            own.append(
                f"Gap (Medium): context deal term for facility {fid} matches no CP-1 facility (T4.18); not used"
            )
            continue
        pieces, keys, lone = [], [], []
        for label, lo, hi, unit in (
            ("spread talk", "talk_spread_bps_low", "talk_spread_bps_high", " bps"),
            ("OID talk", "talk_oid_low", "talk_oid_high", ""),
        ):
            if d[lo] and d[hi]:
                pieces.append(f"{label} {d[lo]}-{d[hi]}{unit}")
                keys += [("deal_terms", i, lo), ("deal_terms", i, hi)]
            elif d[lo] or d[hi]:
                lone.append((label, lo if d[lo] else hi, d[lo] or d[hi]))
        if (cid, "deal_terms", i) in COLLIDES and pieces:
            own.append(
                f"Gap (Medium): context deal terms row {i + 1} for facility {fid} cannot be cited as one unique span; not used"
            )
            continue
        if not pieces:
            continue
        rows.append(
            {
                "from": f"deal_terms[{i}]",
                "facility_id": fid,
                "kind": "indicative_talk",
                "quote_cell": f"{fid}: " + "; ".join(pieces),
                "as_of": d["as_of"] or "Not stated",
                "provider": d["provider"],
                "cite_keys": keys,
                "limitation_extra": [],
                "note": None,
                "lone_bounds": [{"label": lb, "field": f, "value": v} for lb, f, v in lone],
            }
        )
    for n, row in enumerate(rows, 1):
        row["row_id"] = f"c{n:02d}"
        row["label"] = f"Context market evidence {n}"
        row["citations"] = [
            {
                "source_id": "context",
                "locator": f"line:{cites[k][0]}",
                "quote": cites[k][1],
                "field": k[2],
            }
            for k in row["cite_keys"]
        ]
        del row["cite_keys"]
        limitation = f"Provider: {row['provider']}; user-supplied figure"
        if row["as_of"] != "Not stated":
            n_days = days_before(row["as_of"], AS_OF)
            row["days_before_run"] = n_days
            row["stale"] = n_days > STALE_LIMIT
            if row["stale"]:
                text = stale_text(row["facility_id"], row["as_of"], n_days)
                limitation += "; " + text
                own.append(text)
        else:
            row["days_before_run"] = None
            row["stale"] = False
        row["limitation"] = limitation
    if rows:
        own.append(USER_LABEL)
    return rows, own


EVIDENCE = {cid: python_evidence(cid) for cid in CONTEXTS if cid != "bad-bytes"}


def row_facts(row):
    base = f"T3.3.{row['row_id']}"
    cites = [[c["source_id"], c["locator"]] for c in row["citations"]]
    return {
        "row_id": row["row_id"],
        "label": row["label"],
        "facts": [
            {
                "fact_id": f"{base}.source",
                "column": "Source",
                "text": "context",
                "status": "known",
                "cites": [],
                "value_class": None,
                "limitation": None,
            },
            {
                "fact_id": f"{base}.kind",
                "column": "Kind",
                "text": KIND_LABEL[row["kind"]],
                "status": "known",
                "cites": [],
                "value_class": None,
                "limitation": None,
            },
            {
                "fact_id": f"{base}.quote",
                "column": "Quote",
                "text": row["quote_cell"],
                "status": "known",
                "cites": cites,
                "cite_quotes": [c["quote"] for c in row["citations"]],
                "value_class": "source",
                "limitation": None,
            },
            {
                "fact_id": f"{base}.as_of",
                "column": "As of",
                "text": row["as_of"],
                "status": "known",
                "cites": [],
                "value_class": "source",
                "limitation": None,
            },
            {
                "fact_id": f"{base}.limitation",
                "column": "Limitation",
                "text": row["limitation"],
                "status": "known",
                "cites": [],
                "value_class": None,
                "limitation": None,
            },
        ],
    }


# Literal cross-checks against the values the Task 0 brief and Design pin verbatim.
_oat = EVIDENCE["observed-and-talk"][0]
assert [r["row_id"] for r in _oat] == ["c01", "c02"]
assert (
    _oat[0]["quote_cell"]
    == "term-loan: bid 98.50, ask 99.00, price 98.75, yield 8.25%, spread 340 bps"
)
assert len(_oat[0]["citations"]) == 5 and len(_oat[1]["citations"]) == 2
assert _oat[1]["quote_cell"] == "term-loan: price 99.25, spread 335 bps"
assert (
    EVIDENCE["deal-talk"][0][0]["quote_cell"]
    == "term-loan: spread talk 325-350 bps; OID talk 99.0-99.5"
)
assert len(EVIDENCE["deal-talk"][0][0]["citations"]) == 4
_st = EVIDENCE["stale"][0]
assert [r["stale"] for r in _st] == [False, True] and [r["days_before_run"] for r in _st] == [
    30,
    31,
]
assert EVIDENCE["stale"][1][0] == (
    "Stale quote: term-loan quote dated 2025-12-10 is 31 days before the run as-of 2026-01-10 (limit 30)"
)
assert EVIDENCE["unmatched"][1][:2] == [
    "Gap (Medium): context quote for facility revolver-x matches no CP-1 facility (T4.18); not used",
    "Gap (Medium): context quote for facility term-loan carries no figure; not used",
]
assert len(EVIDENCE["unmatched"][0]) == 1 and EVIDENCE["no-quotes"] == ([], [])

# --- 5. submissions ---------------------------------------------------------------------------------
RV = deepcopy(R3_S["positive"]["relative_value"])
R3_BASIS_QUOTES = RV["instruments"][0]["basis"]["quotes"]
R3_ROWS = RV["market_evidence"]
assert len(R3_BASIS_QUOTES) == 2 and len(R3_ROWS) == 2


def submission(
    rows,
    *,
    obs=None,
    rationale=None,
    conf="Medium",
    instr_limit=None,
    pref_limit=None,
    gap=None,
    risk=None,
    keep_market=False,
):
    s = deepcopy(RV)
    inst, pref = s["instruments"][0], s["preference"]
    if not keep_market:
        s["market_evidence"] = []
        inst["basis"]["quotes"] = []
        pref["basis"]["quotes"] = []
    inst["basis"]["context_rows"] = list(rows)
    pref["basis"]["context_rows"] = list(rows)
    if obs:
        inst["market_observation"] = obs
    if rationale:
        pref["rationale"] = rationale
    pref["confidence"] = conf
    if instr_limit:
        inst["limitation"] = instr_limit
    if pref_limit:
        pref["limitation"] = pref_limit
    if gap:
        s["gaps"][0]["gap"] = gap
    if risk:
        s["risks"][0]["mechanic"] = risk
    return s


TXT = {
    "talk-only": {
        "obs": "Dealer talk is the only market evidence for the loan and is talk, not a quotation or a trade.",
        "rationale": "With one instrument the ordering is trivial; the dealer talk is the only market evidence and the CP-2 low-leverage view is consistent with fair compensation, so the preference is provisional.",
        "conf": "Low",
        "instr_limit": "Indicative dealer talk only, no quotation and no reported trade, so there is no observed level",
        "pref_limit": "Dealer talk only and one instrument, so the preference is provisional",
        "gap": "Only dealer talk and no observed quotation or traded price",
        "risk": "Dealer talk is the only market evidence, so the level it describes can move without a trade",
    },
    "stale": {
        "obs": "Two user-supplied dealer quotations are the only observed levels and the older one is stale, so neither is treated as a current market level.",
        "rationale": "With one instrument the ordering is trivial; the observed quotations and the CP-2 low-leverage view are consistent with fair compensation, but one quotation is stale, so the preference is provisional.",
        "instr_limit": "User-supplied dealer quotations, one of them stale, and no reported trade, so the level is not a market consensus",
        "pref_limit": "Two user-supplied quotations, one stale, and one instrument, so the preference is provisional",
        "gap": "Only two user-supplied dealer quotations, one of them stale, and no traded price",
    },
    "unmatched": {
        "obs": "One user-supplied dealer quotation sits just below par and is the only observed level that matches the loan.",
        "rationale": "With one instrument the ordering is trivial; the observed quotation just below par and the CP-2 low-leverage view are consistent with fair compensation, and nothing here suggests the loan is mispriced.",
        "instr_limit": "A single user-supplied dealer quotation, no reported trade and one instrument, so the level is not a market consensus",
        "pref_limit": "One user-supplied dealer quotation and one instrument, so the preference is provisional",
        "gap": "Only one usable dealer quotation and no traded price",
    },
    "deal-talk": {
        "obs": "Arranger price talk is the only market evidence and is talk, not a quotation or a trade.",
        "rationale": "With one instrument the ordering is trivial; the arranger price talk is the only market evidence and the CP-2 low-leverage view is consistent with fair compensation, so the preference is provisional.",
        "conf": "Low",
        "instr_limit": "Arranger price talk only, no quotation and no reported trade, so there is no observed level",
        "pref_limit": "Price talk only and one instrument, so the preference is provisional",
        "gap": "Only arranger price talk and no observed quotation or traded price",
        "risk": "Arranger price talk is the only market evidence, so the pricing it describes can move before the loan is placed",
    },
    "deal-lone-bound": None,  # as deal-talk
}
TXT["deal-lone-bound"] = TXT["deal-talk"]
OAT_TXT = {  # observed-and-talk keeps the R3 positive wording (one observed quotation plus talk)
    "obs": None,
    "rationale": None,
}

SUBS = {
    "observed-and-talk": submission(["c01", "c02"]),
    "talk-only": submission(["c01"], **TXT["talk-only"]),
    "stale": submission(["c01", "c02"], **TXT["stale"]),
    "unmatched": submission(["c01"], **TXT["unmatched"]),
    "deal-talk": submission(["c01"], **TXT["deal-talk"]),
    "deal-lone-bound": submission(["c01"], **TXT["deal-lone-bound"]),
    "with-market-row": submission(["c01", "c02"], keep_market=True),
    "no-quotes": deepcopy(RV),
    "minified": submission(["c01", "c02"]),
    "context-only": submission(["c01", "c02"]),
    "unciteable": deepcopy(RV),  # the no-quotes pattern (plan :165): the R3 positive verbatim
    "unciteable-deal": deepcopy(RV),
    "bad-bytes": deepcopy(RV),
}
assert SUBS["no-quotes"] == RV == SUBS["unciteable"] == SUBS["unciteable-deal"]
assert "context_rows" not in json.dumps(SUBS["no-quotes"])
assert SUBS["with-market-row"]["market_evidence"] == R3_ROWS
assert SUBS["with-market-row"]["instruments"][0]["basis"]["quotes"] == R3_BASIS_QUOTES

# a cited-line locator for the context-quote-cited mutation
_price_line = CITES["observed-and-talk"][("quotes", 0, "price")]
MUTATIONS = [
    {
        "id": "ctx-observed-and-talk-high",
        "case": "observed-and-talk",
        "edits": [["set", "preference.confidence", "High"]],
        "issues": ["preference.confidence: capped below High because CP-2 is restricted"],
    },
    {
        "id": "ctx-talk-only-high",
        "case": "talk-only",
        "edits": [["set", "preference.confidence", "High"]],
        "issues": [
            (
                "preference.confidence: capped below High because CP-2 is restricted; "
                "the market evidence is indicative talk only"
            )
        ],
    },
    {
        "id": "ctx-deal-talk-high",
        "case": "deal-talk",
        "edits": [["set", "preference.confidence", "High"]],
        "issues": [
            (
                "preference.confidence: capped below High because CP-2 is restricted; "
                "the market evidence is indicative talk only"
            )
        ],
    },
    {
        "id": "ctx-stale-high",
        "case": "stale",
        "edits": [["set", "preference.confidence", "High"]],
        "issues": [
            (
                "preference.confidence: capped below High because CP-2 is restricted; "
                "a context quote is more than 30 days old"
            )
        ],
    },
    {
        "id": "context-row-submitted",
        "case": "observed-and-talk",
        "edits": [
            [
                "set",
                "market_evidence",
                [
                    {
                        "source_id": "context",
                        "kind": "none",
                        "quote": None,
                        "as_of": "Not stated",
                        "limitation": "Entered by the model",
                    }
                ],
            ]
        ],
        "issues": [
            "market_evidence[0]: context market evidence is built by Python; cite it by row id in a basis"
        ],
    },
    {
        "id": "context-quote-cited",
        "case": "observed-and-talk",
        "edits": [
            [
                "set",
                "instruments[0].basis.quotes",
                [
                    {
                        "source_id": "context",
                        "locator": f"line:{_price_line[0]}",
                        "quote": _price_line[1],
                    }
                ],
            ]
        ],
        "issues": [
            f"instruments[0].basis.quotes[0]: quotes no market_evidence row (context line:{_price_line[0]})"
        ],
    },
    {
        "id": "unknown-context-row",
        "case": "observed-and-talk",
        "edits": [["set", "instruments[0].basis.context_rows", ["c01", "c07"]]],
        "issues": ["instruments[0].basis.context_rows[1]: no context row c07"],
    },
    {
        "id": "talk-level-wording",
        "case": "talk-only",
        "edits": [["set", "preference.rationale", "The loan trades at 99.25 on dealer talk."]],
        "issues": [
            'preference.rationale: indicative talk worded as a market level: "trades at"',
            "preference.rationale: Bare figure: 99.25",
        ],
    },
]

# --- 6. expected: CP-3 ------------------------------------------------------------------------------
R3_CP3 = R3_E["positive"]["CP-3"]
T = {t["table_id"]: t for t in R3_CP3["tables"]}
T31 = {f["fact_id"]: f for f in T["T3.1"]["rows"][0]["facts"]}
T34 = {f["fact_id"]: f for f in T["T3.4"]["rows"][0]["facts"]}
T33_M = T["T3.3"]["rows"]
R3_BASIS_I = T31["T3.1.i01.basis"]["text"]
R3_BASIS_P = T34["T3.4.preference.basis"]["text"]
MKT_PARTS = [
    "Market evidence market page:1 (observed)",
    "Market evidence market page:2 (indicative talk)",
]
assert all(p in R3_BASIS_I and p in R3_BASIS_P for p in MKT_PARTS)


def basis_text(r3_text, rows, keep_market):
    parts = r3_text.split("; ")
    out, injected = [], False
    ctx_parts = [
        f"Market evidence context {r['row_id']} ({KIND_LABEL[r['kind']].lower()})" for r in rows
    ]
    for p in parts:
        if p in MKT_PARTS:
            if keep_market:
                out.append(p)
            continue
        if p.startswith("CP-1 ") and not injected:
            out += ctx_parts
            injected = True
        out.append(p)
    if not injected:
        out += ctx_parts
    return "; ".join(out)


def own_limitations(case_id, submission_obj, rows, ctx_own, strength):
    out = [f"Gap ({g['severity']}): {g['gap']}" for g in submission_obj["gaps"]]
    if not strength:
        out.append("No observed or indicative market evidence: relative value is not assessed")
    elif strength == {"indicative_talk"}:
        out.append(LABEL_TALK_ONLY)
    return out + list(ctx_own)


def strength_of(case_id, rows):
    s = {r["kind"] for r in rows}
    if case_id == "with-market-row":
        s |= {"observed", "indicative_talk"}
    if case_id in ("no-quotes", "bad-bytes", "unciteable", "unciteable-deal"):
        s = {"observed", "indicative_talk"}
    return s


R3_HEAD_SHA = {
    "tables": sha(json.dumps(R3_CP3["tables"], sort_keys=True).encode()),
    "claims": sha(json.dumps(R3_CP3["claims"], sort_keys=True).encode()),
    "own_limitations": sha(json.dumps(R3_CP3["own_limitations"], sort_keys=True).encode()),
}


def pack_for(case_id):
    return "S1+context" if case_id == "context-only" else "R3+context"


def context_block(case_id, rows, ctx_name, stale_any):
    sources = PACK_SOURCES_S1 if case_id == "context-only" else PACK_SOURCES_R3
    authority = {
        s["source_id"]: R3_CP3["context_block_checks"]["pack_source_authority"][s["source_id"]]
        for s in sources
    }
    authority["context"] = "unknown"
    market = (
        []
        if case_id == "context-only"
        else deepcopy(R3_CP3["context_block_checks"]["market_evidence_sources"])
    )
    note_r3 = R3_CP3["context_block_checks"]["market_evidence_note"]
    note = (
        "Market evidence is the rows in context_market_evidence; cite one only by its row id in "
        "basis.context_rows; copy no figure"
        if case_id == "context-only"
        else note_r3
    )
    block = {
        "pack_source_authority": authority,
        "pack_sources_context_entry": {
            "source_id": "context",
            "name": ctx_name,
            "status": "ready",
            "authority": "unknown",
        },
        "market_evidence_sources": market,
        "market_evidence_note": note,
        "context_market_evidence": [
            {
                "row": r["row_id"],
                "facility_id": r["facility_id"],
                "kind": r["kind"],
                "as_of": r["as_of"],
                "provider": r["provider"],
                "stale": r["stale"],
                "figures": r["quote_cell"],
            }
            for r in rows
        ],
        "confidence_caps": [CAP_CP2] + ([CAP_STALE] if stale_any else []),
    }
    if case_id != "context-only":
        block["note_scope"] = (
            "Design 8 states the context-only wording; with a third_party source in the pack the "
            "R3 note is read as unchanged (preparer's reading, see report)"
        )
    return block


def cp3_expected(case_id):
    cid = {"with-market-row": "observed-and-talk", "context-only": "observed-and-talk"}.get(
        case_id, case_id
    )
    rows, ctx_own = EVIDENCE[cid] if cid != "bad-bytes" else ([], [])
    sub = SUBS[case_id]
    keep_market = case_id == "with-market-row"
    strength = strength_of(case_id, rows)
    out = {
        "context": f"contexts/{cid}.json",
        "pack": pack_for(case_id),
        "submission": f"submissions.json#cases.{case_id}",
        "strength": sorted(strength),
        "python_rows": [r["row_id"] for r in rows],
    }
    if case_id == "no-quotes":
        out.update(
            {
                "python_rows": [],
                "t33_row_order": ["m01", "m02"],
                "report_equals_r3_positive": {
                    "source": f"{R3E}#positive.CP-3 (tables, claims, own_limitations)",
                    "sha256_of_canonical_json_sorted_keys": R3_HEAD_SHA,
                    "differs": ["pack_sha256 (the pack gained a source)"],
                    "own_limitations": R3_CP3["own_limitations"],
                    "no_user_supplied_limitation": True,
                },
                "submission_hash_note": "the submission is the R3 positive relative_value verbatim; its content_hash equals the R3 value (empty context_rows omitted from the dump, N1)",
            }
        )
        return out
    if case_id == "bad-bytes":
        out.update(
            {
                "python_rows": [],
                "t33_row_order": [],
                "validator_issues": {
                    "prefix": "context source unreadable: ",
                    "exact": ["context source unreadable: quotes[0].price is not a plain number"],
                    "fragments": [
                        {
                            "must_contain": [
                                "context source unreadable: ",
                                "quotes[0].as_of",
                                "after the run as-of",
                            ],
                            "proposed_exact": "context source unreadable: quotes[0].as_of 2026-02-01 is after the run as-of 2026-01-10",
                        },
                        {
                            "must_contain": [
                                "context source unreadable: ",
                                "issuer_id differs from the run",
                            ],
                            "proposed_exact": "context source unreadable: identity.issuer_id differs from the run",
                        },
                    ],
                    "count": 3,
                    "order": "not pinned (set equality)",
                    "no_other_issue": "the submission is the R3 positive verbatim, which is otherwise valid over a pack with the third_party market source",
                },
                "rows_built": "none (an unreadable context yields issues, never a silent no-evidence)",
                "pack_note": "the pack is `prepare`d only; load_context is never called on it (the engine re-checks what it uses)",
            }
        )
        return out
    t33 = [row_facts(r) for r in rows]
    if keep_market:
        t33 = [deepcopy(m) for m in T33_M] + t33
    out["t33_row_order"] = [r["row_id"] for r in t33]
    out["t33_rows"] = t33
    if keep_market:
        out["t33_m_rows_equal"] = (
            f"{R3E}#positive.CP-3.tables[T3.3].rows (m01, m02) at :{line_of(R3E, 'T3.3.m01.source')} to :{line_of(R3E, 'T3.3.m02.limitation')}"
        )
    stale_any = any(r["stale"] for r in rows)
    own = own_limitations(case_id, sub, rows, ctx_own, strength)
    out["own_limitations"] = {
        "members": own,
        "order": "gaps, evidence label, then context items; the order of the context items is not pinned",
    }
    out["own_limitations_count"] = len(own)
    out["user_supplied_limitation_present"] = USER_LABEL in own
    inst = sub["instruments"][0]
    pref = sub["preference"]
    out["t31_i01_changed_cells"] = {
        "T3.1.i01.market_observation": inst["market_observation"],
        "T3.1.i01.basis": basis_text(R3_BASIS_I, rows, keep_market),
        "T3.1.i01.limitation": inst["limitation"],
        "other_cells": "equal to the R3 positive T3.1 facts (facility_id, fundamental_view)",
    }
    out["t34_changed_cells"] = {
        "T3.4.preference.rationale": pref["rationale"],
        "T3.4.preference.confidence": pref["confidence"],
        "T3.4.preference.basis": basis_text(R3_BASIS_P, rows, keep_market),
        "T3.4.preference.limitation": pref["limitation"],
        "other_cells": "equal to the R3 positive T3.4 ordering fact",
    }
    cl = [[c["source_id"], c["locator"]] for r in rows for c in r["citations"]]
    if keep_market:
        cl = [["market", "page:1"], ["market", "page:2"]] + cl
    out["claims"] = [
        {
            "claim_id": "T3.4.preference",
            "text": pref["rationale"],
            "limitation": pref["limitation"],
            "cites": cl,
        },
        {
            "claim_id": "T3.1.i01",
            "text": inst["market_observation"],
            "limitation": inst["limitation"],
            "cites": cl,
        },
    ]
    out["claims_cite_note"] = (
        "each claim cites every cited row's citations in basis order (Design 4: out.cited counts context rows); the market-row citations come first where the basis quotes them"
    )
    out["unchanged_from_r3_positive"] = [
        "T3.9 risks (r01, mechanic edited only where noted in submissions.json)",
        "T3.10 gaps",
        "cp1_references",
        "cp3.relative_value front-page table follows the changed text",
    ]
    out["cp6_catalogue_t33"] = {f"T3.3.{r['row_id']}": r["label"] for r in t33}
    out["cp6_reads"] = (
        "T3.3 `kind` facts only (cp6_committee.py:575); Python rows carry the same fact fields as model rows"
    )
    out["context_block"] = context_block(
        case_id, rows, f"{CASE_DIR}/contexts/{cid}.json", stale_any
    )
    return out


CP3_CASES = [
    "observed-and-talk",
    "talk-only",
    "stale",
    "unmatched",
    "deal-talk",
    "deal-lone-bound",
    "with-market-row",
    "no-quotes",
    "minified",
    "context-only",
    "unciteable",
    "unciteable-deal",
    "bad-bytes",
]
CASES_EXPECTED = {c: cp3_expected(c) for c in CP3_CASES}

# deal-lone-bound: unpinned wording, structure pinned (the plan fixes no text)
LONE_LIMITATION = (
    "Provider: Lead arranger; user-supplied figure; "
    "spread talk lower bound 325 given without an upper bound; not used"
)
_lone = EVIDENCE["deal-lone-bound"][0][0]
CASES_EXPECTED["deal-lone-bound"]["lone_bound"] = {
    "row_quote_cell": _lone["quote_cell"],
    "citations": len(_lone["citations"]),
    "omitted": _lone["lone_bounds"],
    "limitation": LONE_LIMITATION,
    "wording_status": "Design 2 fixes the prefix and that the lone bound is omitted and named; the naming text is ruled (B20 review) as pinned here, joined with '; ' like the stale text.",
}
assert _lone["quote_cell"] == "term-loan: OID talk 99.0-99.5" and len(_lone["citations"]) == 2
_lim = CASES_EXPECTED["deal-lone-bound"]["t33_rows"][0]["facts"][4]
_lim["text"] = LONE_LIMITATION

for _c, _sec, _what in (
    ("unciteable", "quotes", "quote"),
    ("unciteable-deal", "deal_terms", "deal terms"),
):
    # fix 3: the no-quotes pattern (plan :165) on a pack that keeps the ready third_party `market` source.
    _gaps = [
        f"Gap (Medium): context {_what} row {n} for facility term-loan cannot be cited as one unique span; not used"
        for n in (1, 2)
    ]
    assert EVIDENCE[_c] == ([], _gaps)
    assert SUBS[_c] == RV and strength_of(_c, []) == {"observed", "indicative_talk"}
    _own = (
        list(R3_CP3["own_limitations"]) + _gaps
    )  # B20b: same `Gap (<severity>): ` form as the Design 5 named gaps
    CASES_EXPECTED[_c] = {
        "context": f"contexts/{_c}.json",
        "pack": "R3+context",
        "submission": f"submissions.json#cases.{_c}",
        "kind": "residual key collision (B20a): the two objects are equal through the last cited figure, so every anchored quote matches both objects (a guessed span); every colliding row is dropped. Re-cut on the no-quotes pattern (plan :165, fix 3): the R3 positive submission, the ready third_party market source still in the pack",
        "strength": ["indicative_talk", "observed"],
        "strength_note": f"the market source's rows only ({R3E}:{line_of(R3E, 'T3.3.m01.kind')} and :{line_of(R3E, 'T3.3.m02.kind')}); the context contributes none",
        "python_rows": [],
        "t33_row_order": ["m01", "m02"],
        "dropped_rows": [f"{_sec}[0]", f"{_sec}[1]"],
        "gap_limitations": _gaps,
        "report_equals_r3_positive": {
            "source": f"{R3E}#positive.CP-3 (tables, claims, own_limitations) at :{line_of(R3E, 'T3.3.m01.source')} (T3.3) and :3432-3433 (own_limitations)",
            "submission_source": f"{R3S}:{line_of(R3S, '"relative_value"')} (positive.relative_value, verbatim)",
            "sha256_of_canonical_json_sorted_keys": R3_HEAD_SHA,
            "differs": [
                "pack_sha256 (the pack gained a source)",
                "own_limitations: the R3 positive's two plus gap_limitations (B20b)",
            ],
            "r3_own_limitations": R3_CP3["own_limitations"],
        },
        "own_limitations": {
            "members": _own,
            "order": "R3 positive's two first, then the two gap_limitations (membership and count pinned)",
        },
        "own_limitations_count": len(_own),
        "user_supplied_limitation_present": False,
        "no_user_supplied_limitation": "Design 7 (:96) adds the user-supplied label only when a Python row exists; none does",
        "context_block": {"context_market_evidence": [], "confidence_caps": [CAP_CP2]},
    }
    assert USER_LABEL not in _own and len(_own) == 4

# stale positive: the exact-30 row carries no stale text
assert "Stale quote" not in CASES_EXPECTED["stale"]["t33_rows"][0]["facts"][4]["text"]
assert CASES_EXPECTED["stale"]["t33_rows"][1]["facts"][4]["text"] == (
    "Provider: Dealer B; user-supplied figure; "
    "Stale quote: term-loan quote dated 2025-12-10 is 31 days before the run as-of 2026-01-10 (limit 30)"
)

# --- 7. expected: CP-3D (Design 9) -------------------------------------------------------------------
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def offered(cid):
    """o01.. in context order: observed -> bid (its bid), offer (its ask); indicative_talk -> its price."""
    obj, cites = CONTEXTS[cid][1], CITES[cid]
    out = []
    for i, q in enumerate(obj["quotes"]):
        items = (
            [("bid", "bid"), ("offer", "ask")]
            if q["kind"] == "observed"
            else [("indicative_talk", "price")]
        )
        for kind, field in items:
            if not q[field]:
                continue
            n, text = cites[("quotes", i, field)]
            out.append(
                {
                    "row": f"o{len(out) + 1:02d}",
                    "kind": kind,
                    "facility_id": q["facility_id"],
                    "source_id": "context",
                    "locator": f"line:{n}",
                    "quote": text,
                    "level_text": q[field],
                    "as_of_text": long_date(q["as_of"]),
                    "quote_as_of": q["as_of"],
                }
            )
    return out


O = {cid: offered(cid) for cid in ("observed-and-talk", "stale", "unmatched")}
_o = O["observed-and-talk"]
assert [(x["row"], x["kind"], x["level_text"], x["as_of_text"]) for x in _o] == [
    ("o01", "bid", "98.50", "January 9, 2026"),
    ("o02", "offer", "99.00", "January 9, 2026"),
    ("o03", "indicative_talk", "99.25", "January 10, 2026"),
]
SINGLE_DEALER_R3 = (
    "Single dealer quotation; the sheet reports no trade in the period to the quotation date"
)
SINGLE_DEALER_CTX = (
    "Single dealer quotation from the context file (user-supplied); trading activity is not read"
)


def stand_alone(kind, row, **filled):
    base = {
        "kind": kind,
        "source_id": "",
        "locator": "",
        "quote": "",
        "level_text": "",
        "as_of_text": None,
        "context_row": row,
    }
    base.update(filled)
    return base


CP3D = {
    "scope": "Quotes only (ruling Q1); deal talk is a range and is never offered. The rest of each CP-3D submission is the frozen cases/cp3d-owner positive; only `observations` is replaced.",
    "base_submission": "cases/cp3d-owner/submissions.json#positive (observations replaced)",
    "offered_observations": {
        cid: [
            {k: v for k, v in x.items() if k not in ("facility_id", "quote_as_of")}
            | {"facility_id": x["facility_id"], "quote_as_of": x["quote_as_of"]}
            for x in rows
        ]
        for cid, rows in O.items()
    },
    "expansion": "The model submits {kind, context_row} with every other field empty; Python expands it to the offered row (context_row kept) before submission_issues. An expanded observation skips only the third_party, _labelled and as_of_text-in-quote checks; on_page, occurs, shape, range (0, 200] and bid <= offer still run.",
    "positive_observed_and_talk": {
        "context": "contexts/observed-and-talk.json",
        "submitted_observations": [
            stand_alone("bid", "o01"),
            stand_alone("offer", "o02"),
            stand_alone("indicative_talk", "o03"),
        ],
        "expanded_equals_offered": ["o01", "o02", "o03"],
        "quotation_period": "Quotation of 2026-01-09",
        "talk_period": "Commentary published 2026-01-10",
        "context_dates": {"o03": "2026-01-10"},
        "published_source": "the context quote as_of (Design 9: context_dates feeds published)",
        "own_limitations": {
            "replaces": SINGLE_DEALER_R3,
            "with": SINGLE_DEALER_CTX,
            "unchanged": "every other own limitation equals cases/cp3d-owner/expected.json (talk line, DM, risk-neutral, terms, alignment ...)",
            "stale": [],
        },
    },
    "stale": {
        "context": "contexts/stale.json",
        "offered": "see offered_observations.stale",
        "cites_exactly_30_days": {
            "submitted_observations": [stand_alone("bid", "o01"), stand_alone("offer", "o02")],
            "own_limitations_stale": [],
        },
        "cites_31_days": {
            "submitted_observations": [stand_alone("bid", "o03"), stand_alone("offer", "o04")],
            "own_limitations_stale": [stale_text("term-loan", "2025-12-10", 31)],
            "single_dealer": SINGLE_DEALER_CTX,
        },
        "note": "own_limitations takes run_as_of (Design 9); the stale text is Design 6's, unchanged; its position among the own limitations is not pinned",
    },
    "refusals": [
        {
            "id": "cp3d-filled-context-row",
            "context": "contexts/observed-and-talk.json",
            "observations": [
                stand_alone(
                    "bid",
                    "o01",
                    source_id="context",
                    locator=_o[0]["locator"],
                    quote=_o[0]["quote"],
                    level_text="98.50",
                    as_of_text="January 9, 2026",
                ),
                stand_alone("offer", "o02"),
                stand_alone("indicative_talk", "o03"),
            ],
            "issues": ["observations[0]: context_row must stand alone and name a listed row"],
        },
        {
            "id": "cp3d-unknown-context-row",
            "context": "contexts/observed-and-talk.json",
            "observations": [
                stand_alone("bid", "o09"),
                stand_alone("offer", "o02"),
                stand_alone("indicative_talk", "o03"),
            ],
            "issues": ["observations[0]: context_row must stand alone and name a listed row"],
        },
        {
            "id": "cp3d-mixed-facilities",
            "context": "contexts/unmatched.json",
            "observations": [stand_alone("bid", "o01"), stand_alone("offer", "o04")],
            "issues": ["observations mix context facilities"],
            "note": "o01 is term-loan, o04 is revolver-x; the dates are equal and bid <= offer, so this is the only observation issue",
        },
        {
            "id": "context-unreadable",
            "context": "contexts/bad-bytes.json",
            "issue_prefix": "context source unreadable: ",
            "reader_problems_in_order": [
                "quotes[0].price: no thousands separators; write 1250, not 1,250.",
                "quotes[0].as_of: is after the run as-of date (2026-01-10); sources dated after it are refused.",
            ],
            "issues": [
                "context source unreadable: quotes[0].price: no thousands separators; write 1250, not 1,250.",
                "context source unreadable: quotes[0].as_of: is after the run as-of date (2026-01-10); sources dated after it are refused.",
            ],
            "issues_note": "one issue per ContextRefused.problems entry of load_context (context.py:315-354), in order (B20); the validator returns them, no exception escapes upstream_of",
        },
    ],
    "observations_data_function": "context_observations_data(upstream) -> list[dict] returns, per offered row, {row, kind, source_id, locator, quote, level_text, as_of_text}; list equals offered_observations for the case",
    "fail_safe": "Known: in a minified file where bid equals ask the anchored quote holds the number twice and CP-3D refuses the observation it offered (stated in the plan; not a defect, not tested here).",
}

# --- 8. context-file reader parity (hand-derived from context.py; checked by the preparer's validator run)
PARITY = {
    "files": {cid: CTX_PATH[cid] for cid in CONTEXTS},
    "load_context_accepts": [c for c in CONTEXTS if c != "bad-bytes"],
    "load_context_refuses": ["bad-bytes"],
    "limit": "STALE_LIMIT is 30 days (Design 6; a drift test pins it, context.py is unchanged)",
}

EXPECTED = {
    "schema_version": "cp3-context-owner-expected/1",
    "derivation": (
        "Hand-derived from docs/superpowers/plans/2026-10-31-phase-3-market-evidence.md Design 1-9, rulings B6/B17 "
        "item 3 (docs/rulings/2026-10-31-context-plan.md), Q-X and the questions file; upstream values are copied "
        "from the frozen R3 oracle (cases/cp3-cp6-owner/expected.json, cited by line). Written by cases/cp3-context-owner/"
        "builder/build.py (stdlib only; no code of the phase is run)."
    ),
    "run": {
        "issuer_id": ISSUER_ID,
        "issuer_name": ISSUER_NAME,
        "as_of": AS_OF,
        "case_kind": "synthetic",
        "pathway": "credit_snapshot",
        "cp1_facility": "term-loan",
        "cp1_facility_name": FACILITY_NAME,
        "cp1_facility_source": "cases/cp3-cp6-owner/builder/build.py:788",
    },
    "interpretation": {
        "locator": "line:<n> of the span holding the figure in the rebuilt text; the context span ids are line:1..N (preparation.py:79)",
        "citation_quote": 'indented file: the member\'s own JSON text alone on its line (`"price": "98.75"`). One-line (minified) file: the member does not sit alone on its line, so the quote is anchored on the quote object (`{` through the figure\'s closing quote), unique in the line (Design 3).',
        "value_class": "Python's Quote and As of cells carry value_class `source` (Q-X); Source, Kind and Limitation cells carry none; model-written cells keep analyst_judgment.",
        "cell_text": "Quote cell and As of cell are the context's own strings; no arithmetic (only whole calendar days for staleness).",
        "row_order": "model market_evidence rows (m01..) first, then Python rows c01.. in context order, quotes before deal_terms (Design 2).",
        "unpinned": "The order of the context items within own_limitations, the Basis-cell wording for a context row and the c-row labels are not fixed by the plan; the oracle pins them as stated here (see the report).",
    },
    "cell_notation": R3_E["cell_notation"]
    | {"cite_quotes": "the quote of each citation, in order, parallel to cites (Python rows only)"},
    "r3_cites": {
        "T3.3.m01": f"{R3E}:{line_of(R3E, 'T3.3.m01.source')}",
        "T3.1.basis_text": f"{R3E}:{line_of(R3E, 'T3.1.i01.basis')}",
        "T3.4.basis_text": f"{R3E}:{line_of(R3E, 'T3.4.preference.basis')}",
        "own_limitations": f"{R3E}:3432-3433",
        "confidence_caps": f"{R3E}:{line_of(R3E, 'CP-2 is restricted')}",
        "level_phrases": "src/deploy_vii/cp3_relative_value.py:127-144 (existing rule, unchanged)",
    },
    "upstream": {
        "premise": "CP-0, CP-1, CP-1A, CP-2 are the R3 positive heads re-run over the pack plus the `context` source; the CP-0 and CP-1 context assessments are the Phase 2 pattern (cases/context-identity-periods/overlays.json). Only the CP-3 report is pinned here.",
        "cp2_status": "restricted",
        "confidence_caps": [CAP_CP2],
        "inherited_limitations_note": "the settled head also inherits the CP-0 context limitation (authority unknown); the report-level own limitations below exclude inherited ones (execution.settle)",
    },
    "cp3": CASES_EXPECTED,
    "model_side_refusals": MUTATIONS,
    "cp3d": CP3D,
    "reader_parity": PARITY,
    "unreadable_wording_note": "Only quotes[0].price's text is fixed verbatim by the brief; the as_of and issuer_id issues are pinned by fragments with a proposed exact text.",
}

SUBMISSIONS = {
    "schema_version": "cp3-context-owner-submissions/1",
    "note": (
        "Literal CP-3 relative_value submissions for the context cases. Each is a deep copy of the R3 positive "
        "relative_value (cases/cp3-cp6-owner/submissions.json#positive.relative_value) with market_evidence [] and "
        "basis.context_rows citing Python's rows by id, except no-quotes/bad-bytes (the R3 positive verbatim) and "
        "with-market-row (the R3 market rows kept, context rows added). {{FIG:name}} marks a CP-1 figure reference "
        "bound mechanically after the CP-1 head exists, as in the R3 file. Texts differ from R3 only where the "
        "evidence differs (talk-only, stale, unmatched, deal-talk)."
    ),
    "base": {"path": R3S, "sha256": PINS[R3S], "selector": "positive.relative_value"},
    "cases": SUBS,
    "refusal_mutations": {
        "note": "Each entry edits a deep copy of cases.<case> (paths use dots and [i]; 'set' replaces the value)",
        "entries": [{"id": m["id"], "case": m["case"], "edits": m["edits"]} for m in MUTATIONS],
    },
}

# --- 9. write -----------------------------------------------------------------------------------------
files = {}
for cid, data in CTX_BYTES.items():
    files[f"contexts/{cid}.json"] = data
files["submissions.json"] = dumps(SUBMISSIONS).encode()
files["expected.json"] = dumps(EXPECTED).encode()

README = """# CP-3 / CP-3D context market evidence oracle (Phase 3 Task 0)

Status: prepared, not reviewed, not frozen, not pinned. `cases/PINS.json` and `cases/pins.py` PATTERNS are changed
at the freeze step (the PATTERNS glob `cases/*-owner/*` matches manifest, submissions, expected and builder here but
not `contexts/*.json`: the freeze adds `cases/cp3-context-owner/contexts/*.json`).

Rebuild: `python3 -I cases/cp3-context-owner/builder/build.py` (stdlib only, twice byte-identical).

- `contexts/*.json`: the context files (`context/1`), the literal bytes of each pack's `context` source
  (`bad-bytes` is refused by `load_context` on purpose; the rest are accepted).
- `submissions.json`: the CP-3 submissions (R3 positive with `market_evidence: []` and `basis.context_rows`) and the
  model-side refusal mutations.
- `expected.json`: per case the Python rows, T3.3 facts, strength, own limitations, context block, cap issues; the CP-3D
  offered observations and refusals.
- `manifest.json`: run, pack sources, context sources and the sha256 of every output.
"""
files["README.md"] = README.encode()

MANIFEST = {
    "schema_version": "cp3-context-owner-cases/1",
    "scope": "CP-3 and CP-3D market evidence built by Python from the context file's quotes and deal_terms talk (Phase 3)",
    "status": "prepared, not reviewed, not frozen, not pinned",
    "pins": PINS,
    "run": {
        "run_id": "ctx3-<case>-v1",
        "issuer_id": ISSUER_ID,
        "issuer_name": ISSUER_NAME,
        "as_of": AS_OF,
        "method_version": R3_RUN["method_version"],
        "case_kind": "synthetic",
        "pathway": "credit_snapshot",
        "requested_modules": R3_RUN["requested_modules"],
        "set": "explicit Run set after preparation_request, as the R3 positive run",
    },
    "packs": {
        "R3+context": {
            "sources": PACK_SOURCES_R3
            + [
                {
                    "source_id": "context",
                    "media_type": "text/plain",
                    "extractor": "utf8-lines/1",
                    "authority": "unknown",
                }
            ]
        },
        "S1+context": {
            "sources": PACK_SOURCES_S1
            + [
                {
                    "source_id": "context",
                    "media_type": "text/plain",
                    "extractor": "utf8-lines/1",
                    "authority": "unknown",
                }
            ],
            "note": "the R3 pack without the third_party market source (the context-only case)",
        },
    },
    "contexts": {
        cid: {
            "path": CTX_PATH[cid],
            "layout": CONTEXTS[cid][0],
            "run_type": CONTEXTS[cid][1]["run"]["run_type"],
            "bytes": len(CTX_BYTES[cid]),
            "spans": len(CTX_BYTES[cid].decode().splitlines()),
            "sha256": sha(CTX_BYTES[cid]),
        }
        for cid in CONTEXTS
    },
    "cases": [
        {
            "case_id": c,
            "pack": pack_for(c),
            "context": ("observed-and-talk" if c in ("with-market-row", "context-only") else c),
            "run_id": f"ctx3-{c}-v1",
            "run_type": CONTEXTS[
                ("observed-and-talk" if c in ("with-market-row", "context-only") else c)
            ][1]["run"]["run_type"],
        }
        for c in CP3_CASES
    ],
    "outputs": {name: sha(data) for name, data in sorted(files.items())},
}
files["manifest.json"] = dumps(MANIFEST).encode()

for name, data in files.items():
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print(f"wrote {len(files)} files under {OUT.relative_to(ROOT)}")
