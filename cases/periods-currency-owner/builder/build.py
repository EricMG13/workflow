"""Writes cases/periods-currency-owner/{manifest,submissions,expected}.json (stdlib only).

Phase 8 Task 0 oracle (periods and currency from the context file). deploy_vii and deploy_workflow
are never imported or run here. Every figure is read BY VALUE from the pinned, frozen upstream
oracles (cases/cp1c-owner, cp1d-owner, cp2a-owner, cp2d-owner, cp2e-owner, cp2g-owner, cp2h-owner,
cp3c-owner, cp4c-owner, cpl10-owner, cases/earnings) and mapped by exactly four rules (the brief's
table), applied to every string and key of the copied data:

  1. every calendar year +1, once and simultaneously (one regex pass, so 2024 -> 2025 and never 2026);
  2. every two-digit period label +1 (`LTM Q4 25`, `Q3 25`, `FY25`; lower-case ids such as `_fy25` are
     structural names that keep their spelling, ruling "Ids stay");
  3. EUR runs: `US$` and `USD` -> `EUR` (so `US$ m` -> `EUR m`);
  4. every 64-hex source digest -> the digest of the shifted source bytes (recomputed here).

Provenance text (`validated_on`, `note`, `derivation`, ...) is dropped, not mapped. Amounts are never
touched. Independent cross-checks (section 6) recompute the headline figures from the shifted
statements with exact rational arithmetic and compare them with the mapped oracle values.

Run: python3 -I cases/periods-currency-owner/builder/build.py [--out DIR]   (from the repository root)
Two runs write byte-identical files.
"""

import calendar
import datetime as dt
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASE = "periods-currency-owner"
OUT = ROOT / "cases" / CASE
if len(sys.argv) == 3 and sys.argv[1] == "--out":
    OUT = Path(sys.argv[2]).resolve()
elif len(sys.argv) != 1:
    sys.exit("usage: build.py [--out DIR]")

# --- 0. pinned inputs ----------------------------------------------------------------------------

PINS_JSON = json.loads((ROOT / "cases/PINS.json").read_text(encoding="utf-8"))
# not listed in cases/PINS.json; the same digests the sibling preparers assert (cases/cp2e-owner and
# cases/cp4c-owner manifests `pins`, cases/context-identity-periods/builder/build.py:24-33)
EXTERNAL_PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/legal/manifest.json": "d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168",
    "cases/earnings/expected.json": "041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599",
    "cases/earnings/manifest.json": "60ed95782648064db7806bb7f0714fe030f9563424df50e17500803a2edfb7ec",
}
INPUT_SHAS = {}


def load_pinned(rel):
    data = (ROOT / rel).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    want = PINS_JSON.get(rel) or EXTERNAL_PINS.get(rel)
    assert want is not None, f"no pin for {rel}"
    assert digest == want, f"input drift: {rel}"
    INPUT_SHAS[rel] = digest
    return json.loads(data)


def owner(case, name):
    return load_pinned(f"cases/{case}-owner/{name}.json")


FIN = load_pinned("cases/financial/manifest.json")
SNAP = load_pinned("cases/snapshot/manifest.json")
LEGAL = load_pinned("cases/legal/manifest.json")
EARN = load_pinned("cases/earnings/expected.json")
EARN_OWNER = json.loads((ROOT / "cases/earnings/owner-expected.json").read_bytes())
INPUT_SHAS["cases/earnings/owner-expected.json"] = hashlib.sha256((ROOT / "cases/earnings/owner-expected.json").read_bytes()).hexdigest()
UP = {}
for _c in ("cp1c", "cp1d", "cp2a", "cp2d", "cp2e", "cp2g", "cp2h", "cp3c", "cp4c", "cpl10"):
    UP[_c] = {n: owner(_c, n) for n in ("manifest", "submissions", "expected")}


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def page_sha(pages):
    return sha("\f".join(p["text"] for p in pages).encode("utf-8"))


# --- 1. the mapping ---------------------------------------------------------------------------------

_MAP_RE = re.compile(
    r"(?P<hex>[0-9a-f]{40,})"
    r"|(?<!\d)(?P<y4>(?:19|20)\d\d)(?!\d)"
    r"|(?<![A-Za-z0-9_])(?P<pre>(?:LTM )?(?:Q[1-4] |FY|H[12] ))(?P<y2>\d\d)(?!\d)"
)
SHIFTED_YEARS = set()
SHIFTED_Y2 = set()


class Tx:
    """The four-rule mapping for one run currency (USD keeps the unit tokens)."""

    def __init__(self, ccy, shamap):
        self.ccy = ccy
        self.shamap = shamap
        self.unmapped_hex = set()

    def text(self, s):
        def sub(m):
            if m.group("hex"):
                h = m.group("hex")
                if h in self.shamap:
                    return self.shamap[h]
                self.unmapped_hex.add(h)
                return h
            if m.group("y4"):
                y = int(m.group("y4"))
                SHIFTED_YEARS.add(y)
                return str(y + 1)
            y2 = int(m.group("y2"))
            SHIFTED_Y2.add(y2)
            return m.group("pre") + f"{y2 + 1:02d}"

        out = _MAP_RE.sub(sub, s)
        if self.ccy == "EUR":
            out = out.replace("US$", "EUR").replace("USD", "EUR")
        return out

    def obj(self, x, drop=frozenset()):
        if isinstance(x, dict):
            # `source: {path, sha256}` names the frozen oracle file a literal came from: provenance, not data
            return {self.text(k): self.obj(v, drop) for k, v in x.items() if k not in drop and not (k == "source" and isinstance(v, dict) and "sha256" in v)}
        if isinstance(x, list):
            return [self.obj(v, drop) for v in x]
        if isinstance(x, str):
            return self.text(x)
        return x


# the rule is simultaneous: a sequential replace would shift 2024 twice
_probe = Tx("USD", {})
assert _probe.text("2024 2025 2026 2029 Q4 2025 LTM Q4 25 q4-2025 FY2025 FY25 _fy25") == (
    "2025 2026 2027 2030 Q4 2026 LTM Q4 26 q4-2026 FY2026 FY26 _fy25"
)
assert _probe.text("0" * 3 + "a1996b" * 8) == "0" * 3 + "a1996b" * 8  # a year inside a hex digest is not a year
assert Tx("EUR", {}).text("120 US$ m; Currency: USD") == "120 EUR m; Currency: EUR"
SHIFTED_YEARS.clear()
SHIFTED_Y2.clear()

# provenance and process text is dropped, not mapped (it describes the frozen oracle's own history)
DROP = frozenset({"validated_on", "replaces", "settled_limitations_note", "run_time_bindings", "note", "execution", "cp0", "plan_order", "derivation", "claims_note", "derivation_note", "not_verified", "source_variant"})

# --- 2. shifted sources --------------------------------------------------------------------------------

FIN_SRC = {s["source_id"]: s for s in FIN["sources"]}
CP1C_SS = UP["cp1c"]["manifest"]["synthetic_source"]
CP1D_SS = UP["cp1d"]["manifest"]["synthetic_source"]
CP2H_SS = UP["cp2h"]["manifest"]["synthetic_source"]
BUS = SNAP["business_source"]
LEG = LEGAL["cases"][0]["legal_source"]
assert LEGAL["cases"][0]["case_id"] == "legal-current-matching-definition"

BASES = {  # source_id -> (frozen meta without pages/sha256, frozen pages, frozen sha256, frozen manifest path)
    "identity": ({k: FIN_SRC["identity"][k] for k in ("source_id", "name", "status", "extraction_status")}, FIN_SRC["identity"]["pages"], FIN_SRC["identity"]["sha256"], "cases/financial/manifest.json#sources[identity]"),
    "financial": ({k: FIN_SRC["financial"][k] for k in ("source_id", "name", "status", "extraction_status")}, FIN_SRC["financial"]["pages"], FIN_SRC["financial"]["sha256"], "cases/financial/manifest.json#sources[financial]"),
    "peers": ({k: CP1C_SS[k] for k in ("source_id", "name", "status", "media_type", "extractor", "extraction_status", "pack_limitation")}, CP1C_SS["positive"]["pages"], CP1C_SS["positive"]["sha256"], "cases/cp1c-owner/manifest.json#synthetic_source.positive"),
    "bridge": ({**{k: CP1D_SS[k] for k in ("source_id", "name", "status", "media_type", "extractor", "extraction_status")}, "pack_limitation": CP1D_SS["pack_limitation_positive"]}, CP1D_SS["positive"]["pages"], CP1D_SS["positive"]["sha256"], "cases/cp1d-owner/manifest.json#synthetic_source.positive"),
    "ratings": ({**{k: CP2H_SS[k] for k in ("source_id", "name", "status", "media_type", "extractor", "extraction_status")}, "pack_limitation": CP2H_SS["pack_limitation_positive"]}, CP2H_SS["positive"]["pages"], CP2H_SS["positive"]["sha256"], "cases/cp2h-owner/manifest.json#synthetic_source.positive"),
    "business": ({**BUS["common"], "pack_limitation": BUS["positive"]["pack_limitation"]}, BUS["positive"]["pages"], BUS["positive"]["sha256"], "cases/snapshot/manifest.json#business_source.positive"),
    "legal-covenants": ({k: v for k, v in LEG.items() if k not in ("pages", "sha256")}, LEG["pages"], LEG["sha256"], "cases/legal/manifest.json#cases[0].legal_source"),
}
for _sid, (_meta, _pages, _sha, _ref) in BASES.items():
    assert page_sha(_pages) == _sha, _sid
    assert _meta["source_id"] == _sid, _sid

SOURCES = {}  # "<id>@<CCY>" or "<id>" -> shifted source record
OLD2NEW = {"USD": {}, "EUR": {}}
for _sid, (_meta, _pages, _sha, _ref) in BASES.items():
    built = {}
    for ccy in ("USD", "EUR"):
        t = Tx(ccy, {})
        pages = [{"locator": p["locator"], "text": t.text(p["text"])} for p in _pages]
        meta = {k: t.text(v) if isinstance(v, str) else v for k, v in _meta.items()}
        built[ccy] = {**meta, "frozen_from": _ref, "frozen_sha256": _sha, "pages": pages, "sha256": page_sha(pages)}
        OLD2NEW[ccy][_sha] = built[ccy]["sha256"]
    if built["USD"] == built["EUR"]:  # no currency token anywhere in the source or its metadata
        SOURCES[_sid] = built["USD"]
    else:
        SOURCES[f"{_sid}@USD"] = built["USD"]
        SOURCES[f"{_sid}@EUR"] = built["EUR"]
CURRENCY_FREE = sorted(k for k in SOURCES if "@" not in k)
CURRENCY_BEARING = sorted({k.split("@")[0] for k in SOURCES if "@" in k})


def source_key(sid, ccy):
    return sid if sid in CURRENCY_FREE else f"{sid}@{ccy}"


def pack(ids, ccy):
    return [source_key(i, ccy) for i in ids]


# a USD pack is the frozen pack with the years shifted: every currency-bearing source differs from its EUR twin only by the currency token
for _sid in CURRENCY_BEARING:
    _u, _e = SOURCES[f"{_sid}@USD"]["pages"], SOURCES[f"{_sid}@EUR"]["pages"]
    assert any(a["text"] != b["text"] for a, b in zip(_u, _e)), _sid
    for a, b in zip(_u, _e):
        assert a["text"].replace("USD", "EUR").replace("US$", "EUR") == b["text"]

TX = {c: Tx(c, OLD2NEW[c]) for c in ("USD", "EUR")}


def page_text(sid, ccy, locator):
    for p in SOURCES[source_key(sid, ccy)]["pages"]:
        if p["locator"] == locator:
            return p["text"]
    raise KeyError((sid, locator))


# --- 3. the period and currency strings, derived from the shifted statements ---------------------------------

FIN_P = {c: {p["locator"]: p["text"] for p in SOURCES[source_key("financial", c)]["pages"]} for c in ("USD", "EUR")}
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def derive_basis(ccy):
    """The PeriodBasis strings of the shifted calendar-year pack, parsed from its own statement text
    (page:1 'FY2026 ... January 1-December 31, 2026 (365 days)', page:4 balance-sheet header)."""
    p1, p4 = FIN_P[ccy]["page:1"], FIN_P[ccy]["page:4"]
    m = re.search(r"annual totals for January 1-December 31, (\d{4}) \((\d+) days\)", p1)
    year, days = int(m.group(1)), int(m.group(2))
    assert year == 2026 and days == 365
    start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    assert (end - start).days + 1 == days
    q4 = re.search(r"October 1-December 31 \((\d+) days\)", p1)
    q4_start = dt.date(year, 10, 1)
    assert (end - q4_start).days + 1 == int(q4.group(1)) == 92
    hdr = re.search(r"Period end\s+Opening (\S+)\s+Q1 \S+\s+Q2 \S+\s+Q3 \S+\s+Q4 (\S+)\s+FY (\S+)", p4)
    assert hdr.group(2) == hdr.group(3) == end.isoformat() and hdr.group(1) == "2025-12-31"
    yy = f"{year % 100:02d}"
    unit = "US$ m" if ccy == "USD" else "EUR m"
    return {
        "currency": ccy,
        "money_unit": unit,
        "base_year": year,
        "years": [year + 1, year + 2, year + 3],
        "year_labels": [f"FY{year + 1}", f"FY{year + 2}", f"FY{year + 3}"],
        "not_reached_text": f"Not reached by FY{year + 3}",
        "ltm_start": start.isoformat(),
        "ltm_end": end.isoformat(),
        "q4_start": q4_start.isoformat(),
        "ltm_tag": f"LTM Q4 {yy}",
        "ltm_column": f"LTM Q4 {yy} ({start.isoformat()} to {end.isoformat()})",
        "ltm_period": f"LTM Q4 {yy}: {start.isoformat()} to {end.isoformat()}",
        "t45_period": f"LTM Q4 {yy} · {start.isoformat()} to {end.isoformat()}",
        "t46_period": f"q4-{year} · {q4_start.isoformat()} to {end.isoformat()}",
        "schedule_period": f"q4-{year}",
        "bs_period": f"Q4 {year}: {end.isoformat()}",
        "bs_column": f"Q4 {end.isoformat()}"[:3] + f"{year}-12-31",
        "bridge_basis_line": f"Basis: FY{year} (January 1-December 31, {year})",
        "balance_date_text": f"{end.day} {MONTHS[end.month]} {end.year}",
        "cp2e_periods": {
            "flow": f"FY {year}: {start.isoformat()} to {end.isoformat()}",
            "balance": f"Balance at {end.isoformat()}",
            "shock": f"FY {year}",
        },
    }


# the frozen defaults (cp1c.py:1523-1524, cp2d.py:1854-1855, cp4c.py:1391-1392, cp1d.py:380 as quoted in the brief table)
FROZEN_DEFAULT = {
    "ltm_column": "LTM Q4 25 (2025-01-01 to 2025-12-31)",
    "ltm_period": "LTM Q4 25: 2025-01-01 to 2025-12-31",
    "t45_period": "LTM Q4 25 · 2025-01-01 to 2025-12-31",
    "t46_period": "q4-2025 · 2025-10-01 to 2025-12-31",
    "schedule_period": "q4-2025",
    "bs_period": "Q4 2025: 2025-12-31",
    "bs_column": "Q4 2025-12-31",
    "bridge_basis_line": "Basis: FY2025 (January 1-December 31, 2025)",
}
BASIS = {c: derive_basis(c) for c in ("USD", "EUR")}
for _c in ("USD", "EUR"):
    for _k, _v in FROZEN_DEFAULT.items():
        assert TX["USD"].text(_v) == BASIS[_c][_k], (_k, TX["USD"].text(_v), BASIS[_c][_k])
    assert BASIS[_c]["bs_column"] == "Q4 2026-12-31"
assert TX["USD"].text("FY2026, FY2027, FY2028; Not reached by FY2028") == "FY2027, FY2028, FY2029; Not reached by FY2029"
assert BASIS["EUR"]["not_reached_text"] == "Not reached by FY2029"
assert BASIS["EUR"]["balance_date_text"] == "31 December 2026"
# the bridge basis line is in the shifted bridge, in the run currency
for _c in ("USD", "EUR"):
    _b = page_text("bridge", _c, "page:1")
    assert _b.split("\n")[4].startswith(BASIS[_c]["bridge_basis_line"] + f"; {_c}; amounts in millions"), _b.split("\n")[4]

# --- 4. day counts and the 29 February 2028 check ----------------------------------------------------------


def add_months(d, n):
    """End-of-month-clamped month arithmetic, as the owners do it (cp2d.py:395, cp3c.py:605-610)."""
    month0 = d.month - 1 + n
    y, m = d.year + month0 // 12, month0 % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def leap_and_day_count_checks():
    p1 = FIN_P["USD"]["page:1"]
    quarters = {}
    for label, (a, b), stated in (("Q1", ((1, 1), (3, 31)), 90), ("Q2", ((4, 1), (6, 30)), 91), ("Q3", ((7, 1), (9, 30)), 92), ("Q4", ((10, 1), (12, 31)), 92)):
        n = (dt.date(2026, *b) - dt.date(2026, *a)).days + 1
        assert n == stated and f"({stated} days)" in p1, (label, n)
        quarters[label] = n
    fy = (dt.date(2026, 12, 31) - dt.date(2026, 1, 1)).days + 1
    assert fy == 365 and "(365 days)" in p1 and not calendar.isleap(2026) and not calendar.isleap(2025)
    feb29 = dt.date(2028, 2, 29)
    base_end = dt.date(2026, 12, 31)
    horizons = {}
    for months in (24, 60):
        frozen_end = add_months(dt.date(2025, 12, 31), months)
        shifted_end = add_months(base_end, months)
        # month arithmetic lands on 31 December both times; no end-of-month clamp (February) is taken
        assert (frozen_end.month, frozen_end.day) == (12, 31) == (shifted_end.month, shifted_end.day)
        horizons[str(months)] = {"frozen": frozen_end.isoformat(), "shifted": shifted_end.isoformat(), "interval_crosses_29_feb_2028": base_end < feb29 < shifted_end, "interval_is_month_based": True}
    maturity_old, maturity_new = dt.date(2029, 12, 31), dt.date(2030, 12, 31)
    months_old = (maturity_old.year - 2025) * 12 + maturity_old.month - 12
    months_new = (maturity_new.year - 2026) * 12 + maturity_new.month - 12
    assert months_old == months_new == 48
    for months in (24, 60):
        assert (maturity_old <= add_months(dt.date(2025, 12, 31), months)) == (maturity_new <= add_months(base_end, months))
    return {
        "statement_day_counts": {**quarters, "FY": fy},
        "statement_year_2026_is_leap": False,
        "owner_date_arithmetic": "month-based only (add_months with end-of-month clamp, annual forecast steps); no module computes an actual day count",
        "horizons_from_balance_date_2026_12_31": horizons,
        "facility_maturity": {"frozen": "2029-12-31", "shifted": "2030-12-31", "months_after_balance_date": 48, "same_side_of_24_and_60_month_horizon": True},
        "feb_29_2028": "inside the 24-month horizon and the FY2028 forecast year; only month-end and annual-step arithmetic is applied across it, so no figure changes; the statement periods themselves (all 2026) contain no 29 February",
    }


LEAP = leap_and_day_count_checks()

# --- 5. module oracles -------------------------------------------------------------------------------------


def dig(x, path):
    for k in path:
        x = x[k]
    return x


# module -> (submission picks: name -> (case, path in submissions.json), expected picks: name -> (case, path in expected.json), frozen case id used)
SPECS = {
    "CP-1C": ("cp1c", "positive", {"submission": ["positive"], "cp0_consumer_row": None}, [("cases", "positive")], [("policy_constants",)]),
    "CP-1D": ("cp1d", "positive", {"submission": ["positive"], "figures": ["figures"]}, [("cases", "positive")], []),
    "CP-2A": ("cp2a", "positive", {"cp0_consumer_row_cp2a": ["cp0_consumer_row_cp2a"], "cp1_downstream_review": ["cp1_downstream_review"], "submission": ["positive"], "figures": ["figures"]}, [("cases", "positive")], []),
    "CP-2D": ("cp2d", "positive", {"cp0_consumer_delta": ["cp0_consumer_delta"], "submission": ["cp2d", "positive"]}, [("cases", "positive")], [("source_facts",), ("method_rules",)]),
    "CP-3C": ("cp3c", "positive", {"cp0_consumer_deltas": ["cp0_consumer_deltas"], "cp1a_consumer_deltas": ["cp1a_consumer_deltas"], "cp1_downstream_review": ["cp1_downstream_review"], "submission": ["cp3c", "positive"]}, [("cases", "positive")], [("source_facts",), ("method_rules",)]),
    "CP-2G": ("cp2g", "gap", {"cp0_consumer_row_cp2g": ["cp0_consumer_row_cp2g"], "cp0_consumer_row_cp2a": ["cp0_consumer_row_cp2a"], "upstream_step_literals_CP-2A": ["upstream_step_literals", "CP-2A"], "submission": ["cases", "gap"], "figures": ["figures"]}, [("cases", "gap")], []),
    "CP-2H": ("cp2h", "positive", {"agency_source": ["agency_source", "positive"], "upstream_step_literals_CP-2A": ["upstream_step_literals", "CP-2A"], "upstream_step_literals_CP-2G": ["upstream_step_literals", "CP-2G"], "submission": ["cases", "positive"], "figures": ["figures"]}, [("cases", "positive")], []),
    "CP-4C": ("cp4c", "positive", {"upstream_step_literals_CP-2A": ["upstream_step_literals", "CP-2A"], "upstream_step_literals_CP-2G": ["upstream_step_literals", "CP-2G"], "upstream_step_literals_CP-4": ["upstream_step_literals", "CP-4", "positive"], "submission": ["cases", "positive"], "figures": ["figures"]}, [("cases", "positive")], []),
    "CP-2E": ("cp2e", "positive", {"readiness_review": ["readiness_review", "positive"], "submission": ["positive"]}, [("cases", "positive")], []),
    "CP-L10": ("cpl10", "positive", {"cp0_consumer_row_cpl10": ["cp0_consumer_row_cpl10"], "cp1_downstream_review": ["cp1_downstream_review"], "submission": ["positive"]}, [("cases", "positive")], []),
}
# CP-1C cp0_consumer_row_cp1c lives inside the positive submission set; no separate pick
SPECS["CP-1C"][2].pop("cp0_consumer_row")
# CP-2G in a distressed run has no CP-1D (the preset omits it, contracts.py:70-72): the frozen `gap` case is the CP-1D-unbound run.
FROZEN_CASE = {m: s[1] for m, s in SPECS.items()}

EXPECTED_KEEP_DROP = frozenset({"cp1_readiness"}) | DROP  # readiness literals are submission-side, not module output


_ORACLE_CACHE = {}


def module_oracle(module, ccy):
    if (module, ccy) not in _ORACLE_CACHE:
        o = _module_oracle(module, ccy)
        # every currency a fact carries is the run currency; none is left over from the frozen USD
        found = set()
        stack = [o["expected"], o["submission"]]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if isinstance(x.get("currency"), str) and re.fullmatch(r"[A-Z]{3}", x["currency"]):
                    found.add(x["currency"])
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
        assert found <= {ccy}, (module, ccy, found)
        _ORACLE_CACHE[(module, ccy)] = o
    return _ORACLE_CACHE[(module, ccy)]


def _module_oracle(module, ccy):
    case, frozen_case, sub_picks, exp_cases, exp_top = SPECS[module]
    t = TX[ccy]
    sub = {name: t.obj(dig(UP[case]["submissions"], path), DROP) for name, path in sub_picks.items()}
    exp_block = t.obj(dig(UP[case]["expected"], list(exp_cases[0])), EXPECTED_KEEP_DROP)
    top = {"/".join(p): t.obj(dig(UP[case]["expected"], list(p)), DROP) for p in exp_top}
    return {
        "frozen_case": f"cases/{case}-owner (case {frozen_case})",
        "currency": ccy,
        "money_unit": BASIS[ccy]["money_unit"],
        "submission": sub,
        "expected": {**exp_block, **({"top_level": top} if top else {})},
    }


# --- 6. CP-1B from cases/earnings (E-QOQ-FLAT) -------------------------------------------------------------

# bindings/cp1b.py:32-49 (transcribed, the nine money labels carry `{unit}`; B18)
CP1B_LAYOUT = {
    "T1B.1": [("revenue", "Revenue ({unit})"), ("ebitda", "Reported EBITDA ({unit})"), ("adjusted_ebitda", "Adjusted EBITDA ({unit})"), ("ebitda_margin", "EBITDA margin (%; change pp)"), ("cfo_reported", "Reported CFO ({unit})"), ("capex", "Signed capex ({unit})"), ("fcf", "Levered FCF ({unit})")],
    "T1B.2": [("cash_closing", "Closing cash ({unit})"), ("total_debt", "Total debt ({unit})"), ("net_debt", "Net debt ({unit})")],
}
CP1B_MONEY_ROWS = ["revenue", "ebitda", "adjusted_ebitda", "cfo_reported", "capex", "fcf", "cash_closing", "total_debt", "net_debt"]


def cp1b_oracle(ccy):
    t = TX[ccy]
    pos = EARN["positive"]
    assert pos["case_id"] == "E-QOQ-FLAT" and pos["days_each"] == 92
    points = t.obj(pos["points"])
    money = [p for p in points if p["measure_id"] in CP1B_MONEY_ROWS]
    assert [p["measure_id"] for p in money] == CP1B_MONEY_ROWS
    assert all(p["unit"] == "MILLIONS" and p["currency"] == ccy and p["scale"] == "1000000" for p in money)
    non_money = [p for p in points if p["measure_id"] not in CP1B_MONEY_ROWS]
    assert all(p["currency"] is None for p in non_money)
    unit = BASIS[ccy]["money_unit"]
    owner_x = EARN_OWNER
    return {
        "frozen_case": "cases/earnings (case E-QOQ-FLAT)",
        "currency": ccy,
        "money_unit": unit,
        "prior_period_id": t.text(pos["prior_period_id"]),
        "current_period_id": t.text(pos["current_period_id"]),
        "days_each": pos["days_each"],
        "points": points,
        "dimension_check": {"unit": "MILLIONS", "currency": ccy, "passes": True},
        "money_fact_currency": {"rows": CP1B_MONEY_ROWS, "fields": ["prior", "current", "delta"], "currency": ccy, "unit": "MILLIONS", "scale": "1000000", "note": "C = currency of cp1b:T1B.1:revenue:current (B18); growth and non-money rows carry no currency"},
        "row_labels": {tid: [{"row_id": r, "label": lab.format(unit=unit)} for r, lab in rows] for tid, rows in CP1B_LAYOUT.items()},
        "layout_check": "accepts these labels over facts of this currency; refuses the other currency's labels over them",
        "assessments": t.obj(owner_x["assessments"]["E-QOQ-FLAT"], DROP),
        "claim_text": t.text(owner_x["claim"]["texts"]["E-QOQ-FLAT"]),
        "claim_limitation": t.text(owner_x["claim"]["limitations"]["E-QOQ-FLAT"]),
        "own_limitations": t.obj(owner_x["own_limitations"]["E-QOQ-FLAT"]),
        "source_locators": t.obj(pos["source_locators"]),
    }


# --- 7. independent figure cross-checks (exact arithmetic on the shifted statement text) ---------------------


def stmt_row(ccy, page, label, col):
    """The `col`-th number (0-based) of the statement row `label` on a shifted statement page."""
    for line in FIN_P[ccy][page].split("\n"):
        if line.startswith(label + "  "):
            nums = re.findall(r"\(?-?\d+(?:\.\d+)?\)?", line[len(label):])
            vals = [Fraction(n.strip("()")) * (-1 if n.startswith("(") else 1) for n in nums]
            return vals[col]
    raise KeyError(label)


def crosscheck(ccy):
    fy = 4  # FY column of the quarterly/FY statements
    ebitda = stmt_row(ccy, "page:2", "Reported EBITDA", fy)
    rev = stmt_row(ccy, "page:2", "Revenue", fy)
    interest = stmt_row(ccy, "page:3", "Cash interest paid", fy)
    fcf = stmt_row(ccy, "page:3", "Levered free cash flow", fy)
    cfo = stmt_row(ccy, "page:3", "Operating cash flow", fy)
    debt = stmt_row(ccy, "page:4", "Total debt", 5)
    cash = stmt_row(ccy, "page:4", "Cash and cash equivalents", 5)
    ltm = {
        "revenue": rev, "ebitda": ebitda, "interest": interest, "fcf": fcf, "cfo": cfo,
        "total_debt": debt, "cash": cash, "net_debt": debt - cash,
        "total_leverage": debt / ebitda, "net_leverage": (debt - cash) / ebitda,
        "interest_coverage": ebitda / interest, "fcf_to_debt": fcf / debt,
    }
    # quarters for CP-1B: Q3 and Q4 columns (0-based 2 and 3 on flows, 3 and 4 on the balance sheet whose first column is Opening)
    q = {}
    for name, page, label, flow in (("revenue", "page:2", "Revenue", True), ("ebitda", "page:2", "Reported EBITDA", True), ("adjusted_ebitda", "page:2", "Adjusted EBITDA", True), ("cfo_reported", "page:3", "Operating cash flow", True), ("capex", "page:3", "Total capital expenditure", True), ("fcf", "page:3", "Levered free cash flow", True), ("cash_closing", "page:4", "Cash and cash equivalents", False), ("total_debt", "page:4", "Total debt", False)):
        prior, cur = (stmt_row(ccy, page, label, 2), stmt_row(ccy, page, label, 3)) if flow else (stmt_row(ccy, page, label, 3), stmt_row(ccy, page, label, 4))
        q[name] = (prior, cur)
    q["net_debt"] = (q["total_debt"][0] - q["cash_closing"][0], q["total_debt"][1] - q["cash_closing"][1])
    return ltm, q


def dec(s):
    return Fraction(s)


def exact(v):
    """A Fraction as an exact decimal when it terminates, else as a ratio."""
    d = v.denominator
    for f in (2, 5):
        while d % f == 0:
            d //= f
    if d != 1:
        return f"{v.numerator}/{v.denominator}"
    from decimal import Decimal, localcontext
    with localcontext() as c:
        c.prec = 60
        return format(Decimal(v.numerator) / Decimal(v.denominator), "f").rstrip("0").rstrip(".") if v.denominator != 1 else str(v.numerator)


def check_against_oracles():
    ltm, q = crosscheck("USD")
    ltm_e, q_e = crosscheck("EUR")
    assert ltm == ltm_e and q == q_e  # amounts unchanged by the currency token
    checks = {}
    a = module_oracle("CP-2A", "USD")["expected"]
    for k, v in a["base_operands"].items():
        assert dec(v) == ltm[k], ("CP-2A", k)
    assert dec(a["stress"]["s00"]["total_leverage"]) == ltm["total_leverage"].limit_denominator(10**40) or abs(dec(a["stress"]["s00"]["total_leverage"]) - ltm["total_leverage"]) < Fraction(1, 10**30)
    assert dec(a["stress"]["s00"]["interest_coverage"]) == ltm["interest_coverage"] and dec(a["stress"]["s00"]["fcf_to_debt"]) == ltm["fcf_to_debt"]
    g = module_oracle("CP-2G", "USD")["expected"]
    for k, v in g["base_operands"].items():
        if k in ltm:
            assert dec(v) == ltm[k], ("CP-2G", k)
        elif k == "taxes":
            assert dec(v) == stmt_row("USD", "page:3", "Cash tax paid", 4)
        elif k == "wc":
            assert dec(v) == -stmt_row("USD", "page:3", "Working capital cash movement", 4)
        elif k == "capex":
            assert dec(v) == -stmt_row("USD", "page:3", "Total capital expenditure", 4)
        elif k == "undrawn":
            assert dec(v) == stmt_row("USD", "page:4", "RCF commitment", 5) - stmt_row("USD", "page:4", "RCF drawings", 5)
    pts = {p["measure_id"]: p for p in cp1b_oracle("USD")["points"]}
    for name, (prior, cur) in q.items():
        assert dec(pts[name]["prior_value"]) == prior and dec(pts[name]["current_value"]) == cur and dec(pts[name]["delta"]) == cur - prior, name
    assert dec(pts["total_leverage_reported"]["current_value"]) - ltm["total_leverage"] == 0 or abs(dec(pts["total_leverage_reported"]["current_value"]) - ltm["total_leverage"]) < Fraction(1, 10**30)
    checks["ltm_figures"] = {k: exact(v) for k, v in ltm.items()}
    checks["cp1b_q3_to_q4"] = {k: {"prior": exact(v[0]), "current": exact(v[1]), "delta": exact(v[1] - v[0])} for k, v in q.items()}
    return checks


CROSSCHECK = check_against_oracles()

# --- 8. contexts and runs ------------------------------------------------------------------------------------

PRESETS = {  # contracts.py:50-72 (transcribed)
    "relative_value": ["CP-0", "CP-1", "CP-MODEL", "CP-1C", "CP-2", "CP-2D", "CP-3", "CP-3C", "CP-3D", "CP-5"],
    "distressed_restructuring": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2A", "CP-2G", "CP-2H", "CP-4", "CP-4C", "CP-5"],
    "earnings_update": ["CP-0", "CP-1", "CP-MODEL", "CP-1B", "CP-1D", "CP-5"],
}
ISSUER = {"issuer_name": "Northbridge Synthetic Group", "issuer_id": "northbridge-synthetic"}
AS_OF = "2027-01-10"


def context(run_type, pathway, current, prior, ccy):
    """context/1 as the form writes it (cases/context-identity-periods/contexts/ctx-research.json key order); fields not set are defaults."""
    return {
        "schema": "context/1",
        "run": {"run_type": run_type, "pathway": pathway, "case_kind": "synthetic", "as_of": AS_OF, "current_period": current, "prior_period": prior, "reporting_currency": ccy},
        "identity": {**ISSUER, "borrower_name": "", "parent_name": "", "guarantors": [], "aliases": [], "listed_equity": False, "ticker": "", "sector": "", "country": "", "sponsor": ""},
        "deal_terms": [],
        "quotes": [],
        "ratings": [],
        "valuation": {"peer_source": "cp_dr_public", "basis": "auto", "issuer_market": {"market_cap_m": "", "net_debt_m": "", "ev_m": "", "ebitda_basis": "LTM", "as_of": "", "source": ""}, "peers": [], "precedents": [], "user_multiple": {"value": "", "basis": "LTM", "rationale": ""}},
        "assumptions": {"cp2a": None, "cp2d": None, "cp2e": None, "cp3c": None, "cp3d": None, "cp4c": None},
        "attachments": {"portfolio_workbook": False, "prior_case": False, "management_bridge": False, "legal_documents": "executed"},
        "research_questions": [],
    }


RV_PACK = ["identity", "financial", "peers", "business"]
DIST_PACK = ["identity", "financial", "business", "legal-covenants", "ratings"]
EARN_PACK = ["identity", "financial", "bridge"]

RUNS = [
    # id, run_type, pathway, extra modules, current, prior, ccy (context), pack ids, pack ccy
    ("R1", "rv-fy2026-usd", "research", "relative_value", [], "fy-2026", "fy-2025", "USD", RV_PACK, "USD"),
    ("R2", "dist-q4-2026-eur", "research", "distressed_restructuring", ["CP-2E", "CP-L10"], "q4-2026", "q3-2026", "EUR", DIST_PACK, "EUR"),
    ("R3", "earn-q4-2026-eur", "earnings", "earnings_update", [], "q4-2026", "q3-2026", "EUR", EARN_PACK, "EUR"),
    ("R4", "mismatch-eur-on-usd", "research", "relative_value", [], "fy-2026", "fy-2025", "EUR", RV_PACK, "USD"),
    ("R5", "base-h2", "research", "distressed_restructuring", [], "h2-2026", "h1-2026", "USD", DIST_PACK, "USD"),
    ("R5b", "base-q3", "research", "distressed_restructuring", ["CP-L10", "CP-1B"], "q3-2026", "q2-2026", "USD", DIST_PACK, "USD"),
    ("R6", "rv-fy2026-eur", "research", "relative_value", [], "fy-2026", "fy-2025", "EUR", RV_PACK, "EUR"),
]

H2_REFUSAL = "run.current_period h2-2026: forecast years need an fy or q4 base"
MISMATCH_REFUSAL = "reporting_currency EUR, but CP-1 reports USD"
RESIDUAL = {"CP-1C": "Period basis: " + MISMATCH_REFUSAL}


def module_entry(module, ccy, extra=None):
    key = f"{module}@{ccy}"
    token = BASIS[ccy]["money_unit"]
    blob = json.dumps(cp1b_oracle(ccy) if module == "CP-1B" else module_oracle(module, ccy), ensure_ascii=False)
    other = ("US$", "USD") if ccy == "EUR" else ("EUR",)
    assert token in blob and not any(o in blob for o in other), (module, ccy)
    entry = {"outcome": "settled", "oracle": key, "money_unit": token, "required_tokens": [token], "forbidden_tokens": list(other)}
    entry.update(extra or {})
    return entry


def refused_entry(module, text, exact=None):
    e = {"outcome": "refused", "layer": "entry validator", "issue_contains": text, "figures_produced": False}
    if exact:
        e["issue_exact"] = exact
    return e


STALE = {  # literals that a still-hard-coded owner would emit on a 2026 pack (brief table, "Frozen (2025)" column)
    "period_literals": ["LTM Q4 25", "q4-2025 · 2025-10-01 to 2025-12-31", "Q4 2025: 2025-12-31", "Q4 2025-12-31", "2025-01-01 to 2025-12-31", "Basis: FY2025 (January 1-December 31, 2025)", "Not reached by FY2028", "31 December 2025", "Run as of 2026-01-10"],
}


def run_record(spec):
    rid, run_id, run_type, pathway, extra, cur, pri, ctx_ccy, pack_ids, pack_ccy = spec
    requested = PRESETS[pathway] + extra
    ctx = context(run_type, pathway, cur, pri, ctx_ccy)
    rec = {
        "label": rid,
        "run": {"run_id": run_id, **ISSUER, "as_of": AS_OF, "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": pathway, "requested_modules": requested},
        "requested_modules_note": "pathway preset" + (f" plus {extra} through Run.model_copy(update={{'requested_modules': ...}}); neither is in any preset" if extra else ""),
        "pack_sources": pack(pack_ids, pack_ccy),
        "pack_currency": pack_ccy,
        "context": ctx,
        "context_sha256": sha(dumps(ctx).encode("utf-8")),
    }
    return rec, ctx


def issuer_metrics(ccy):
    cells = [f for f in module_oracle("CP-1C", ccy)["expected"]["facts"] if f["fact_id"].startswith("T1C.3.issuer.")]
    assert [f["field"] for f in cells] == ["adjusted_ebitda_margin", "total_leverage_adjusted", "interest_coverage_adjusted", "ffo_to_debt"]
    assert all(f["copied_from_cp1"].startswith(BASIS[ccy]["ltm_column"] + " \u00b7 ") and f["period"] == BASIS[ccy]["ltm_period"] for f in cells)
    return [{"fact_id": f["fact_id"], "cp1_fact_label": f["copied_from_cp1"], "amount_exact": f["amount_exact"], "shown": f["shown"], "period": f["period"]} for f in cells]


def binding_check(module, ccy):
    """Each T4.5 / T4.6 / T4.10 period string that the frozen module oracle holds occurs, shifted, in the module oracle,
    and no frozen (2025) form is left. Returns which of the four strings the oracle itself carries."""
    case = SPECS[module][0]
    frozen_blob = json.dumps(dig(UP[case]["expected"], list(SPECS[module][3][0])), ensure_ascii=False)
    blob = json.dumps(module_oracle(module, ccy)["expected"], ensure_ascii=False)
    b = BASIS[ccy]
    present = {}
    for k in ("t45_period", "t46_period", "ltm_period", "schedule_period"):
        in_frozen = FROZEN_DEFAULT[k] in frozen_blob
        present[k] = b[k] in blob
        assert present[k] == in_frozen, (module, k)
    assert any(present.values()), module
    assert not any(v in blob for k, v in FROZEN_DEFAULT.items() if k != "bs_column"), module
    return present


def build_expected_runs():
    out = {}
    for spec in RUNS:
        rid, _run_id, _rt, _pw, _extra, cur, pri, ctx_ccy, _pids, pack_ccy = spec
        rec = {"run_id": _run_id, "current_period": cur, "prior_period": pri, "reporting_currency": ctx_ccy, "pack_currency": pack_ccy}
        mods = {}
        if rid == "R1":
            rec["period_basis"] = BASIS["USD"]
            for m in ("CP-1C", "CP-2D", "CP-3C"):
                mods[m] = module_entry(m, "USD")
            mods["CP-1C"]["issuer_period"] = f"Mixed: issuer {BASIS['USD']['ltm_tag']}, each peer's own twelve months"
            mods["CP-1C"]["t410_column_selected"] = BASIS["USD"]["ltm_column"]
            mods["CP-1C"]["t410_facts_selected"] = 4
            mods["CP-1C"]["issuer_metrics"] = issuer_metrics("USD")
            for m in ("CP-2D", "CP-3C"):
                mods[m]["bindings_carried_by_oracle"] = binding_check(m, "USD")
                mods[m]["bindings"] = {"T4.5": BASIS["USD"]["t45_period"], "T4.6": BASIS["USD"]["t46_period"], "T4.10": BASIS["USD"]["ltm_period"], "SCHEDULE_PERIOD": BASIS["USD"]["schedule_period"]}
        elif rid == "R6":
            rec["period_basis"] = BASIS["EUR"]
            for m in ("CP-1C", "CP-2D", "CP-3C"):
                mods[m] = module_entry(m, "EUR")
            mods["CP-1C"]["issuer_period"] = f"Mixed: issuer {BASIS['EUR']['ltm_tag']}, each peer's own twelve months"
            mods["CP-1C"]["t410_column_selected"] = BASIS["EUR"]["ltm_column"]
            mods["CP-1C"]["t410_facts_selected"] = 4
            mods["CP-1C"]["issuer_metrics"] = issuer_metrics("EUR")
            for m in ("CP-2D", "CP-3C"):
                mods[m]["bindings_carried_by_oracle"] = binding_check(m, "EUR")
                mods[m]["bindings"] = {"T4.5": BASIS["EUR"]["t45_period"], "T4.6": BASIS["EUR"]["t46_period"], "T4.10": BASIS["EUR"]["ltm_period"], "SCHEDULE_PERIOD": BASIS["EUR"]["schedule_period"]}
            rec["peers_basis_clause"] = "Basis: twelve months to the period end shown; EUR; amounts in millions; unaudited desk summaries."
            assert rec["peers_basis_clause"] in page_text("peers", "EUR", "page:1")
        elif rid == "R2":
            rec["period_basis"] = BASIS["EUR"]
            for m in ("CP-2A", "CP-2G", "CP-2H", "CP-4C", "CP-2E", "CP-L10"):
                mods[m] = module_entry(m, "EUR")
            mods["CP-2A"]["offering"] = "the frozen CP-2A bases with 2026 labels (base period " + BASIS["EUR"]["ltm_period"] + ")"
            mods["CP-2G"]["forecast_columns"] = BASIS["EUR"]["year_labels"]
            mods["CP-2G"]["cp1d"] = "unbound (CP-1D is not in the distressed_restructuring preset); the frozen CP-2G gap case is the oracle"
            mods["CP-2H"]["first_reached_text"] = BASIS["EUR"]["not_reached_text"]
            mods["CP-4C"]["claims_period_column"] = BASIS["EUR"]["bs_column"]
            mods["CP-4C"]["balance_date_limitation"] = BASIS["EUR"]["balance_date_text"]
            mods["CP-2E"]["periods"] = {**BASIS["EUR"]["cp2e_periods"], "run": f"Run as of {AS_OF}"}
            mods["CP-2E"]["basis_source"] = "the statement's own `FY 2026` header and run.current_period (Task 7); no CP-1 input"
            mods["CP-L10"]["quarters"] = ["Q1 26", "Q2 26", "Q3 26", "Q4 26"]
            mods["CP-L10"]["scope"] = "Phase 2 owns the offering; Phase 8 checks the currency token only"
        elif rid == "R3":
            rec["period_basis"] = BASIS["EUR"]
            mods["CP-1B"] = module_entry("CP-1B", "EUR")
            mods["CP-1D"] = module_entry("CP-1D", "EUR")
            mods["CP-1D"]["basis_line"] = BASIS["EUR"]["bridge_basis_line"]
            mods["CP-1D"]["amount_fact_currency"] = "EUR"
            money = [f for f in module_oracle("CP-1D", "EUR")["expected"]["facts"] if f.get("unit") == "MILLIONS" and f.get("status") == "known"]
            assert money and all(f.get("currency") == "EUR" for f in money)
            mods["CP-1D"]["millions_facts_checked_eur"] = len(money)
        elif rid == "R4":
            rec["period_basis"] = None
            for m in ("CP-1C", "CP-2D", "CP-3C"):
                mods[m] = refused_entry(m, MISMATCH_REFUSAL, RESIDUAL.get(m))
            rec["refusal"] = {"exception": "PeriodRefused", "message": MISMATCH_REFUSAL, "rule": "Task 1: T4.14 currency must equal run.reporting_currency; Task 2 prefixes CP-1C's issue with 'Period basis: '"}
        elif rid == "R5":
            rec["period_basis"] = None
            for m in ("CP-2G", "CP-2H", "CP-4C"):
                mods[m] = refused_entry(m, H2_REFUSAL)
            mods["CP-2A"] = module_entry("CP-2A", "USD", {"offering": "unchanged: period-agnostic (cp2a.py:160-173); the frozen CP-2A bases, base period " + BASIS["USD"]["ltm_period"]})
            rec["refusal"] = {"exception": "PeriodRefused", "message": H2_REFUSAL}
        elif rid == "R5b":
            rec["period_basis"] = None
            rec["currency_basis"] = {"currency": "USD", "money_unit": "US$ m"}
            mods["CP-2A"] = module_entry("CP-2A", "USD", {"offering": "unchanged: period-agnostic; a q3 base is not a refusal for a currency-only module (M3)"})
            mods["CP-1B"] = {"outcome": "refused", "layer": "build_earnings_delta", "error": "incompatible_periods", "issue_contains": "incompatible_periods", "figures_produced": False, "is_period_refused": False, "ruling": "controller: freeze today's refusal; earnings.py:316-318 compares period lengths in raw days (prior q2-2026 = 91, current q3-2026 = 92); a pre-existing defect reported to the owner; if the owner fixes it this case is re-cut"}
            quarters = ["q4-2025", "q1-2026", "q2-2026", "q3-2026"]
            assert "q4-2025" not in {f"q{n}-2026" for n in range(1, 5)} and quarters[0] == "q4-2025"
            mods["CP-L10"] = {"outcome": "refused", "layer": "offering", "issue_contains": "unbound CP-1 operand: q4-2025 (no CP-1 T4.14 period)", "missing_quarter_id": "q4-2025", "quarters_needed": quarters, "figures_produced": False, "is_period_refused": False, "ruling": "controller: Phase 2 plan :114 (q3-2025 current -> q4-2024 missing) shifted one year; the shifted pack holds T4.14 periods q1-2026..q4-2026 only"}
        mods_clean = mods
        rec["modules"] = mods_clean
        rec["stale_period_literals_forbidden_in_emitted_period_strings"] = STALE["period_literals"] if rid in ("R1", "R2", "R3", "R6") else []
        out[rid] = rec
    return out


# --- 9. assemble the three files ---------------------------------------------------------------------------------

NEEDED = {  # module oracles referenced by the runs
    "USD": ["CP-1C", "CP-2D", "CP-3C", "CP-2A"],
    "EUR": ["CP-1C", "CP-2D", "CP-3C", "CP-2A", "CP-2G", "CP-2H", "CP-4C", "CP-2E", "CP-L10", "CP-1D"],
}


def citation_check(oracle_key, oracle, ccy, ids):
    """Every quote in the mapped oracle is a substring of the shifted page it cites."""
    bad, n = [], 0
    stack = [oracle]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            sid, loc, q = x.get("source_id"), x.get("locator"), x.get("quote")
            if isinstance(sid, str) and isinstance(loc, str) and isinstance(q, str) and sid in ids:
                n += 1
                if q not in page_text(sid, ccy, loc):
                    bad.append((sid, loc, q[:60]))
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
    return n, bad


def main():
    runs_manifest, expected_runs = [], build_expected_runs()
    contexts = {}
    for spec in RUNS:
        rec, ctx = run_record(spec)
        runs_manifest.append(rec)
        contexts[spec[0]] = ctx
    oracles_sub, oracles_exp, cite_report = {}, {}, {}
    for ccy, mods in NEEDED.items():
        for m in mods:
            o = module_oracle(m, ccy)
            key = f"{m}@{ccy}"
            oracles_sub[key] = {"frozen_case": o["frozen_case"], "currency": ccy, **o["submission"]}
            oracles_exp[key] = {k: v for k, v in o.items() if k != "submission"}
            ids = set(SOURCES_BY_CCY(ccy))
            n, bad = citation_check(key, o["submission"], ccy, ids)
            n2, bad2 = citation_check(key, o["expected"], ccy, ids)
            cite_report[key] = {"quotes_checked": n + n2, "quotes_not_in_shifted_page": len(bad) + len(bad2), "samples": (bad + bad2)[:2]}
    oracles_exp["CP-1B@EUR"] = cp1b_oracle("EUR")
    oracles_exp["CP-1B@USD"] = cp1b_oracle("USD")
    # no US$ / USD anywhere in an EUR oracle, no EUR in a USD oracle
    for key, o in oracles_exp.items():
        blob = json.dumps(o, ensure_ascii=False)
        sblob = json.dumps(oracles_sub.get(key, {}), ensure_ascii=False)
        if key.endswith("@EUR"):
            assert "US$" not in blob + sblob and "USD" not in blob + sblob, key
        else:
            assert "EUR" not in blob + sblob, key
    unmapped = sorted({h for c in TX.values() for h in c.unmapped_hex})
    manifest = {
        "schema_version": "periods-currency-owner-cases/1",
        "scope": "Phase 8 Task 0: periods and currency from the run context. Seven runs (R1-R6, R5b) over the frozen Northbridge pack with every calendar year +1, in USD and EUR.",
        "status": "DRAFT by the Phase 8 Task 0 preparer, 2026-11-01; not executed; unreviewed",
        "builder_rule": "cases/periods-currency-owner/builder/build.py reads the frozen oracles by value from their pinned files and maps them by four rules; no product code is imported or run",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "inputs_pinned": dict(sorted(INPUT_SHAS.items())),
        "mapping_rules": {
            "years": "every 4-digit calendar year +1 in one regex pass over every string and key (2024->2025, 2025->2026, 2026->2027, 2029->2030; the business note's 2011 and 2019 shift too, 'every calendar year')",
            "period_labels": "two-digit labels +1: `LTM Q4 25`, `Q1 25`..`Q4 25`, `FY25`; lower-case structural ids such as `change_vs_fy25`, `total_leverage_fy28` keep their spelling (Phase 8 plan, Decisions: Ids stay)",
            "currency": "EUR runs: `US$` and `USD` -> `EUR`; USD runs keep `US$ m`; amounts are never changed",
            "digests": "every 40+-hex digest -> the sha256 of the shifted source it names (computed here from the shifted bytes)",
            "dropped_keys": sorted(DROP),
            "years_shifted": sorted(SHIFTED_YEARS),
            "two_digit_years_shifted": sorted(SHIFTED_Y2),
        },
        "sources": SOURCES,
        "source_ids_currency_free": CURRENCY_FREE,
        "source_ids_currency_bearing": CURRENCY_BEARING,
        "old_to_new_source_sha256": OLD2NEW,
        "runs": runs_manifest,
        "default_period_literals_mapped": FROZEN_DEFAULT,
    }
    submissions = {
        "schema_version": "periods-currency-owner-submissions/1",
        "note": "Literal analyst submissions, one set per module and run currency: the frozen owner submissions (positive case, or the CP-1D-unbound gap case for CP-2G) with the four-rule mapping applied. Quotes are checked below to be substrings of the shifted pages. CP-1 step literals are produced by the test harness from the shifted pack text; none is stored here.",
        "contexts": contexts,
        "modules": oracles_sub,
    }
    expected = {
        "schema_version": "periods-currency-owner-expected/1",
        "derivation": "Figures are the frozen oracle figures read by value from the pinned files listed in manifest.inputs_pinned and mapped by manifest.mapping_rules. Statuses, refusals and token expectations come from the Phase 8 plan Task 0 table. Section `figure_crosscheck` recomputes the headline figures from the shifted statements.",
        "period_basis": BASIS,
        "runs": expected_runs,
        "module_oracles": oracles_exp,
        "figure_crosscheck": CROSSCHECK,
        "leap_year_and_day_counts": LEAP,
        "quote_substring_check": cite_report,
        "residual_2025_note": "A 2026 pack still holds 2025 dates: the opening balance (2025-12-31) is the shifted 2024-12-31, and rating dates. 'No stale literal' (STALE) is therefore the testable form of 'no 2025 period string'; a bare '2025' check would fail on the opening balance.",
        "unmapped_digests": unmapped,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(dumps(manifest), encoding="utf-8")
    (OUT / "submissions.json").write_text(dumps(submissions), encoding="utf-8")
    (OUT / "expected.json").write_text(dumps(expected), encoding="utf-8")
    bad = {k: v for k, v in cite_report.items() if v["quotes_not_in_shifted_page"]}
    print("wrote", OUT, "quotes with no shifted page match:", sum(v["quotes_not_in_shifted_page"] for v in cite_report.values()), "unmapped digests:", len(unmapped))
    if bad:
        for k, v in bad.items():
            print("  ", k, v)


def SOURCES_BY_CCY(ccy):
    return {k.split("@")[0] for k in SOURCES if k == k.split("@")[0] or k.endswith("@" + ccy)}


main()
