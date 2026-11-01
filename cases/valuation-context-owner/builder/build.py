"""Writes cases/valuation-context-owner/* (stdlib only; deploy_vii and deploy_workflow are never imported).

Phase 7 Task 0 oracle: EV/EBITDA valuation from the context file (CP-1C tables T1C.9-T1C.11 and
the CP-4C multiple binding). Every expected value is derived here, from the manifest below, by a
small reference model written for this oracle (exact Decimal arithmetic, 38 digits, half-even, as
CP-1C's context) and from the frozen upstream oracles named in PINS, read by hash. Nothing is
taken from code the phase will build. Display text follows deploy_vii/display.py (ROUND_HALF_UP,
thousands commas), an existing module the phase does not change.

The hand-derived figures of the Task 0 brief are asserted as literals at the end (HAND_DERIVED);
the build fails if the reference model disagrees with them.

Run: python3 -I cases/valuation-context-owner/builder/build.py   (from the repository root)
Two runs write byte-identical files.
"""

import calendar
import hashlib
import json
from datetime import date
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "valuation-context-owner"

# --- 0. pinned inputs ------------------------------------------------------------------------------
PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/legal/manifest.json": "d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168",
    "cases/cp1c-owner/manifest.json": "6f0b5489d56af478704f5f78f20f20ebce7e95c5ca07d9c09a01db87540ad4a5",
    "cases/cp1c-owner/submissions.json": "13be79735066cd58bdcc4cfa7eebddc0eedbe0abb784153a2950ee38455a8912",
    "cases/cp1c-owner/expected.json": "2165d28d06e80347b8ea9c5a78350a1a41bb60db4b140cfce3e4256bccc57862",
    "cases/cp4c-owner/manifest.json": "62102d7dae0507320e1ae09517322c2db9fdb94b04d0b8f9610f61892ac6dfd8",
    "cases/cp4c-owner/submissions.json": "1f76a1d193e04db56a2917b30a4cdc470be54a259858a2c8712e0e4bf1feea68",
    "cases/cp4c-owner/expected.json": "eb1a897bfbba83298171d82fb399d653d376d2597fecf99b71cfcbc38cd96ab6",
    "cases/pins-context-owner/expected.json": "f2e7ef35fc42ca9605f4e210bbd4dfe9cda6aa7e3144af44b447ee5bc4d42aa8",
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
}
RAW = {}
for rel, digest in PINS.items():
    RAW[rel] = (ROOT / rel).read_bytes()
    assert hashlib.sha256(RAW[rel]).hexdigest() == digest, f"input drift: {rel}"
FIN = json.loads(RAW["cases/financial/manifest.json"])
CP1C_M = json.loads(RAW["cases/cp1c-owner/manifest.json"])
CP1C_E = json.loads(RAW["cases/cp1c-owner/expected.json"])
CP4C_M = json.loads(RAW["cases/cp4c-owner/manifest.json"])
CP4C_E = json.loads(RAW["cases/cp4c-owner/expected.json"])
METH = json.loads(RAW["src/deploy_vii/methodology.json"])


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def line_after(rel, needle, then=None):
    """1-based line of the first `needle` line in pinned file `rel`; with `then`, the first
    later line that contains `then` (used to land on a fact's amount line)."""
    lines = RAW[rel].decode("utf-8").splitlines()
    start = next(i for i, text in enumerate(lines) if needle in text)
    if then is None:
        return start + 1
    return next(i for i in range(start, len(lines)) if then in lines[i]) + 1


# --- 1. exact arithmetic and display (reference model) ---------------------------------------------
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
DISPLAY = Context(prec=120, rounding=ROUND_HALF_UP)  # deploy_vii/display.py _CONTEXT
MIN_ADMITTED = 3
OUTLIER_FRACTION = Decimal("0.5")
THIN_UNIVERSE = 5
PEER_MONTHS, PRECEDENT_MONTHS = 12, 36
NOT_STATED = "Not stated by the user"
WITHIN, OUTLIER = "Within range", "Outlier"
INSUFFICIENT = "Insufficient Information"
GAP_DR = "No peer figures: cp_dr_public peers come from the CP-DR peer pack (Part B O7d)"
GAP_UL = "No peer figures: user_list peers need the peer lookup (O7d)"
NTM_GAP = "NTM needs a forecast EBITDA that CP-1C does not read"
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
SYNTHETIC_LINE = "Synthetic case; not real issuer qualification"


def exact(value: Decimal) -> str:
    """Canonical exact decimal text: no exponent, no trailing zeros."""
    text = format(value.normalize(CTX), "f")
    return "0" if text in ("-0", "0") else text


def fixed(value: Decimal, places: int) -> str:
    q = value.quantize(Decimal(1).scaleb(-places), context=DISPLAY)
    return f"{q:,.{places}f}"


def mult_shown(value: Decimal) -> str:
    return fixed(value, 2) + "x"


def round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def months_back(d: date, months: int) -> date:
    index = d.year * 12 + d.month - 1 - months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


assert months_back(date(2026, 1, 10), 12) == date(2025, 1, 10)
assert months_back(date(2026, 1, 10), 36) == date(2023, 1, 10)
assert months_back(date(2024, 2, 29), 12) == date(2023, 2, 28)
assert months_back(date(2026, 3, 31), 1) == date(2026, 2, 28)


def median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return CTX.divide(CTX.add(ordered[mid - 1], ordered[mid]), Decimal(2))


# --- 2. the run and its closed chain -------------------------------------------------------------
AS_OF = "2026-01-10"
ISSUER_NAME = "Northbridge Synthetic Group"
ISSUER_ID = "northbridge-synthetic"
PATHWAY = "distressed_restructuring"
CP4C_CLOSURE = ["CP-0", "CP-1", "CP-1C", "CP-2A", "CP-4", "CP-2G", "CP-4C"]


def plan_order(requested, extra_optional):
    """registry.plan's algorithm (layers in methodology order), re-implemented over methodology.json
    with CP-4C's optional edge to CP-1C added (idempotent once Task 1 adds it to the file)."""
    cat = {m["module_id"]: m for m in METH}
    selected = set(requested)
    pending = list(selected)
    while pending:
        for dep in cat[pending.pop()]["required"]:
            if dep not in selected:
                selected.add(dep)
                pending.append(dep)
    remaining = {}
    for mid in selected:
        optional = set(cat[mid]["optional"]) | set(extra_optional.get(mid, ()))
        remaining[mid] = set(cat[mid]["required"]) | (optional & selected)
    ordered = []
    while remaining:
        ready = [m["module_id"] for m in METH if m["module_id"] in remaining and not remaining[m["module_id"]]]
        assert ready, "cycle"
        for mid in ready:
            ordered.append(mid)
            del remaining[mid]
            for need in remaining.values():
                need.discard(mid)
    return ordered


EDGE = {"CP-4C": ("CP-1C",)}
assert {m["module_id"]: m for m in METH}["CP-1C"]["required"] == ["CP-0", "CP-1"]
assert {m["module_id"]: m for m in METH}["CP-4C"]["required"] == ["CP-0", "CP-1", "CP-2G", "CP-4", "CP-2A"]
PLAN_BOTH = plan_order(("CP-1C", "CP-4C"), EDGE)
PLAN_1C = plan_order(("CP-1C",), EDGE)
assert PLAN_BOTH == CP4C_CLOSURE, PLAN_BOTH
assert PLAN_1C == ["CP-0", "CP-1", "CP-1C"]
# execution.current_inputs: bound upstream = plan order filtered by dependencies(...)[module]
CP4C_INPUTS = ["prepared-pack", "CP-0", "CP-1", "CP-1C", "CP-2A", "CP-4", "CP-2G"]
assert [i for i in PLAN_BOTH if i != "CP-4C"] == CP4C_INPUTS[1:]

# --- 3. peers and precedents (brief) -------------------------------------------------------------
SRC_PEER = "Synthetic comps desk, invented data"
SRC_PREC = "Synthetic deals desk, invented data"
PEERS = {  # id: (name, as_of, ev, ebitda)
    "A": ("Synthetic Peer A (invented)", "2025-11-30", "540", "60"),
    "B": ("Synthetic Peer B (invented)", "2025-09-30", "330", "55"),
    "C": ("Synthetic Peer C (invented)", "2025-12-31", "700", "100"),
    "D": ("Synthetic Peer D (invented)", "2024-12-31", "400", "50"),
    "E": ("Synthetic Peer E (invented)", "2025-10-15", "0", "10"),
    "W1": ("Synthetic Edge Peer 1 (invented)", "2025-01-10", "450", "50"),
    "W2": ("Synthetic Edge Peer 2 (invented)", "2025-01-09", "400", "50"),
}
PRECEDENTS = {  # id: (target, acquirer, date, ev, ebitda)
    "P1": ("Synthetic Target P1 (invented)", "Synthetic Acquirer P1", "2024-06-30", "900", "100"),
    "P2": ("Synthetic Target P2 (invented)", "Synthetic Acquirer P2", "2023-09-15", "1250", "125"),
    "P3": ("Synthetic Target P3 (invented)", "Synthetic Acquirer P3", "2022-12-31", "800", "100"),
    "P4": ("Synthetic Target P4 (invented)", "Synthetic Acquirer P4", "2025-03-31", "1000", "80"),
    "P5": ("Synthetic Target P5 (invented)", "Synthetic Acquirer P5", "2024-01-31", "600", "100"),
    "P6": ("Synthetic Target P6 (invented)", "Synthetic Acquirer P6", "", "700", "100"),
}
USER_LIST = ["Synthetic Listed Peer 1 (invented)", "Synthetic Listed Peer 2 (invented)", "Synthetic Listed Peer 3 (invented)"]
PIN_RATIONALE = "Synthetic pin used to test precedence over the CP-1C selection"
MARKET_SOURCE = "Synthetic market data screen, invented data"
UM_RATIONALE = "Mid-point of sector LBO range"

# id: spec. peers/precedents list ids; peer_source; basis; case_kind; extras
CASES = {
    "auto-public": dict(peer_source="user_comps", basis="auto", peers=["A", "B", "C", "D", "E"]),
    "auto-thin": dict(peer_source="user_comps", basis="auto", peers=["A", "B", "D"]),
    "public-thin": dict(peer_source="user_comps", basis="public_comps", peers=["A", "B"]),
    "precedents": dict(peer_source="none", basis="precedents", precedents=["P1", "P2", "P3", "P4", "P5", "P6"]),
    "blend": dict(peer_source="user_comps", basis="blend", peers=["A", "B", "C"], precedents=["P1", "P2", "P3", "P4", "P5", "P6"]),
    "blend-thin": dict(peer_source="user_comps", basis="blend", peers=["A", "B", "C"], precedents=["P1", "P2", "P6"]),
    "issuer-trading": dict(peer_source="none", basis="issuer_trading", listed=True, market=dict(cap="200", debt="70", ebitda_basis="LTM", as_of="2026-01-05")),
    "issuer-trading-ntm": dict(peer_source="none", basis="issuer_trading", listed=True, market=dict(cap="200", debt="70", ebitda_basis="NTM", as_of="2026-01-05")),
    "user-multiple": dict(peer_source="none", basis="user_multiple", um=dict(value="8.5", basis="LTM", rationale=UM_RATIONALE)),
    "user-list": dict(peer_source="user_list", basis="public_comps", user_list=USER_LIST),
    "auto-dr-public": dict(peer_source="cp_dr_public", basis="auto"),
    "dr-public": dict(peer_source="cp_dr_public", basis="public_comps"),
    "credit-plus-comps": dict(peer_source="user_comps", basis="auto", peers=["A", "B", "C", "D", "E"], pack="peers", requested=["CP-1C"]),
    "auto-public-private": dict(peer_source="user_comps", basis="auto", peers=["A", "B", "C", "D", "E"], case_kind="private"),
    "pin-vs-selection": dict(peer_source="user_comps", basis="auto", peers=["A", "B", "C", "D", "E"], pin="8.5"),
    "window-edges": dict(peer_source="user_comps", basis="auto", peers=["W1", "W2"]),
}


def context_object(spec):
    peers = []
    if spec["peer_source"] == "user_comps":
        for pid in spec.get("peers", []):
            name, as_of, ev, ebitda = PEERS[pid]
            peers.append({"name": name, "ticker": "", "ev_m": ev, "ebitda_m": ebitda, "as_of": as_of, "source": SRC_PEER})
    elif spec["peer_source"] == "user_list":
        for name in spec["user_list"]:
            peers.append({"name": name, "ticker": "", "ev_m": "", "ebitda_m": "", "as_of": "", "source": ""})
    precedents = []
    for pid in spec.get("precedents", []):
        target, acquirer, when, ev, ebitda = PRECEDENTS[pid]
        precedents.append({"target": target, "acquirer": acquirer, "date": when, "ev_m": ev, "ebitda_m": ebitda, "source": SRC_PREC})
    market = {"market_cap_m": "", "net_debt_m": "", "ev_m": "", "ebitda_basis": "LTM", "as_of": "", "source": ""}
    if "market" in spec:
        mk = spec["market"]
        market = {"market_cap_m": mk["cap"], "net_debt_m": mk["debt"], "ev_m": "", "ebitda_basis": mk["ebitda_basis"], "as_of": mk["as_of"], "source": MARKET_SOURCE}
    um = spec.get("um") or {"value": "", "basis": "LTM", "rationale": ""}
    cp4c = {"ev_multiple": spec["pin"], "rationale": PIN_RATIONALE} if "pin" in spec else None
    return {
        "schema": "context/1",
        "run": {
            "run_type": "research",
            "pathway": PATHWAY,
            "case_kind": spec.get("case_kind", "synthetic"),
            "as_of": AS_OF,
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
            "listed_equity": bool(spec.get("listed")),
            "ticker": "",
            "sector": "",
            "country": "",
            "sponsor": "",
        },
        "deal_terms": [],
        "quotes": [],
        "ratings": [],
        "valuation": {
            "peer_source": spec["peer_source"],
            "basis": spec["basis"],
            "issuer_market": market,
            "peers": peers,
            "precedents": precedents,
            "user_multiple": um,
        },
        "assumptions": {"cp2a": None, "cp2d": None, "cp2e": None, "cp3c": None, "cp3d": None, "cp4c": cp4c},
        "attachments": {"portfolio_workbook": False, "prior_case": False, "management_bridge": False, "legal_documents": "executed"},
        "research_questions": [],
    }


def dump_with_lines(obj):
    """json.dumps(indent=2) text plus a map from every key path to its 1-based line."""
    lines, linemap = [], {}

    def emit(value, path, indent, prefix, comma):
        pad = "  " * indent
        tail = "," if comma else ""
        if isinstance(value, dict) and value:
            lines.append(pad + prefix + "{")
            linemap[path] = len(lines)
            items = list(value.items())
            for i, (key, item) in enumerate(items):
                emit(item, path + (key,), indent + 1, json.dumps(key, ensure_ascii=False) + ": ", i < len(items) - 1)
            lines.append(pad + "}" + tail)
        elif isinstance(value, list) and value:
            lines.append(pad + prefix + "[")
            linemap[path] = len(lines)
            for i, item in enumerate(value):
                emit(item, path + (i,), indent + 1, "", i < len(value) - 1)
            lines.append(pad + "]" + tail)
        else:
            lines.append(pad + prefix + json.dumps(value, ensure_ascii=False) + tail)
            linemap[path] = len(lines)

    emit(obj, (), 0, "", False)
    text = "\n".join(lines) + "\n"
    assert text == dumps(obj), "line map does not follow json.dumps"
    return text, linemap


# --- 4. the reference model ------------------------------------------------------------------------
class Rec:
    def __init__(self, kind, row_id, name, when, source, ev, ebitda, paths, window_months):
        self.kind, self.row_id, self.name, self.when, self.source = kind, row_id, name, when, source
        self.ev = None if ev is None else Decimal(ev)
        self.ebitda = None if ebitda is None else Decimal(ebitda)
        self.paths = paths
        self.months = window_months
        self.start = months_back(date.fromisoformat(AS_OF), window_months)
        self.multiple = None
        self.included = False
        self.reason = ""
        self.deviation = None
        self.flag = None
        if ev is None:  # a user_list name: no figures in the context
            self.reason = "Excluded: no peer figures in the context"
            return
        if self.ev > 0 and self.ebitda > 0:
            self.multiple = CTX.divide(self.ev, self.ebitda)
        if self.ev <= 0:
            self.reason = "Excluded: enterprise value is zero"
        elif self.ebitda <= 0:
            self.reason = "Excluded: EBITDA is not above zero"
        elif not when:
            self.reason = "Excluded: no deal date, the window cannot be checked"
        elif date.fromisoformat(when) < self.start:
            noun, verb = ("figures", "are") if kind == "peer" else ("deal", "is")
            limit = "12-month" if window_months == PEER_MONTHS else "36-month"
            self.reason = f"Excluded: {noun} dated {when} {verb} before {self.start.isoformat()} ({limit} limit)"
        else:
            self.included = True
            self.reason = "Included"

    @property
    def result(self):
        return self.reason


def build_records(spec, cid):
    recs = []
    if spec["peer_source"] == "user_comps":
        for i, pid in enumerate(spec.get("peers", [])):
            name, as_of, ev, ebitda = PEERS[pid]
            base = ("valuation", "peers", i)
            recs.append(Rec("peer", f"e{i + 1:02d}", name, as_of, SRC_PEER, ev, ebitda,
                            {k: base + (k,) for k in ("name", "as_of", "source", "ev_m", "ebitda_m")}, PEER_MONTHS))
    elif spec["peer_source"] == "user_list":
        for i, name in enumerate(spec["user_list"]):
            base = ("valuation", "peers", i)
            recs.append(Rec("peer", f"e{i + 1:02d}", name, "", "", None, None, {"name": base + ("name",)}, PEER_MONTHS))
    for i, pid in enumerate(spec.get("precedents", [])):
        target, acquirer, when, ev, ebitda = PRECEDENTS[pid]
        base = ("valuation", "precedents", i)
        recs.append(Rec("precedent", f"x{i + 1:02d}", target, when, SRC_PREC, ev, ebitda,
                        {k: base + (k,) for k in ("name", "as_of", "source", "ev_m", "ebitda_m")} | {"name": base + ("target",), "as_of": base + ("date",)}, PRECEDENT_MONTHS))
    return recs


class SetStats:
    def __init__(self, set_id, recs):
        self.set_id = set_id
        self.recs = recs
        self.admitted = [r for r in recs if r.included]
        self.n_total, self.n_admitted = len(recs), len(self.admitted)
        mults = [r.multiple for r in self.admitted]
        self.minimum = min(mults) if mults else None
        self.maximum = max(mults) if mults else None
        self.median = median(mults) if self.n_admitted >= MIN_ADMITTED else None
        self.outliers = None
        if self.median is not None:
            count = 0
            for r in self.admitted:
                r.deviation = CTX.divide(CTX.subtract(r.multiple, self.median), self.median)
                r.flag = OUTLIER if r.deviation.copy_abs() > OUTLIER_FRACTION else WITHIN
                count += r.flag == OUTLIER
            self.outliers = count


class Selection:
    def __init__(self):
        self.selected_basis = None  # text of the selected basis, None when a gap
        self.basis_known = False
        self.multiple = None
        self.reason = ""
        self.ebitda_basis = NOT_STATED
        self.ebitda_basis_path = None
        self.gap = None  # reason when selected_multiple is unsettled
        self.derives = []
        self.set_ids = []
        self.formula = ""
        self.cite_paths = []
        self.user_supplied = False


def evaluate(spec, recs, ctx_obj):
    """Returns (public, precedents, issuer_row, user_row, selection)."""
    val = ctx_obj["valuation"]
    peers = [r for r in recs if r.kind == "peer"]
    precs = [r for r in recs if r.kind == "precedent"]
    public = SetStats("public_comps", peers)
    prec = SetStats("precedents", precs)
    basis = val["basis"]
    sel = Selection()
    issuer_row = user_row = None
    if basis == "issuer_trading":
        mk = val["issuer_market"]
        ev = Decimal(mk["ev_m"]) if mk["ev_m"] else Decimal(mk["market_cap_m"]) + Decimal(mk["net_debt_m"])
        issuer_row = dict(ev=ev, ebitda_basis=mk["ebitda_basis"], as_of=mk["as_of"], source=mk["source"], multiple=None)
    if basis == "user_multiple":
        user_row = dict(value=Decimal(val["user_multiple"]["value"]), basis=val["user_multiple"]["basis"], rationale=val["user_multiple"]["rationale"])

    def need(stat, label, months):
        return f"{label} {stat.n_admitted} admitted of {MIN_ADMITTED} required ({months}-month window)"

    sel.requested = basis
    if basis == "auto":
        if val["peer_source"] == "user_list":
            sel.gap = GAP_UL
        elif val["peer_source"] == "cp_dr_public":
            sel.selected_basis, sel.basis_known = INSUFFICIENT, True
            sel.gap = f"{GAP_DR}; precedents {prec.n_admitted} admitted of {MIN_ADMITTED} required"
            sel.reason = sel.gap
        elif public.median is not None:
            sel.selected_basis, sel.basis_known = "public_comps", True
            sel.multiple = round2(public.median)
            sel.reason = f"auto: public comps, {public.n_admitted} admitted of {MIN_ADMITTED} required ({PEER_MONTHS}-month window)"
            sel.set_ids, sel.formula = ["public_comps"], "median of the admitted public comps' multiples, rounded half-even to 2 dp"
        elif prec.median is not None:
            sel.selected_basis, sel.basis_known = "precedents", True
            sel.multiple = round2(prec.median)
            sel.reason = f"auto: precedents, {prec.n_admitted} admitted of {MIN_ADMITTED} required ({PRECEDENT_MONTHS}-month window)"
            sel.set_ids, sel.formula = ["precedents"], "median of the admitted precedents' multiples, rounded half-even to 2 dp"
        else:
            sel.selected_basis, sel.basis_known = INSUFFICIENT, True
            sel.gap = f"auto: {need(public, 'public comps', PEER_MONTHS)}; {need(prec, 'precedents', PRECEDENT_MONTHS)}; no multiple is selected"
            sel.reason = sel.gap
    elif basis == "public_comps":
        if val["peer_source"] == "user_list":
            sel.gap = GAP_UL
        elif val["peer_source"] == "cp_dr_public":
            sel.gap = GAP_DR
        elif public.median is not None:
            sel.selected_basis, sel.basis_known = "public_comps", True
            sel.multiple = round2(public.median)
            sel.reason = f"public_comps: median of {public.n_admitted} admitted public comps ({PEER_MONTHS}-month window)"
            sel.set_ids, sel.formula = ["public_comps"], "median of the admitted public comps' multiples, rounded half-even to 2 dp"
        else:
            sel.gap = f"requested public_comps, {public.n_admitted} admitted of {MIN_ADMITTED} required; no fallback"
    elif basis == "precedents":
        if prec.median is not None:
            sel.selected_basis, sel.basis_known = "precedents", True
            sel.multiple = round2(prec.median)
            sel.reason = f"precedents: median of {prec.n_admitted} admitted precedents ({PRECEDENT_MONTHS}-month window)"
            sel.set_ids, sel.formula = ["precedents"], "median of the admitted precedents' multiples, rounded half-even to 2 dp"
        else:
            sel.gap = f"requested precedents, {prec.n_admitted} admitted of {MIN_ADMITTED} required; no fallback"
    elif basis == "blend":
        if public.median is not None and prec.median is not None:
            sel.selected_basis, sel.basis_known = "blend", True
            sel.multiple = round2(CTX.divide(CTX.add(public.median, prec.median), Decimal(2)))
            sel.reason = (f"blend: plain average of the public comps median {fixed(public.median, 2)} "
                          f"and the precedents median {fixed(prec.median, 2)}")
            sel.set_ids, sel.formula = ["public_comps", "precedents"], "(public comps median + precedents median) / 2, rounded half-even to 2 dp"
        else:
            parts = []
            if public.median is None:
                parts.append(f"public comps {public.n_admitted} admitted of {MIN_ADMITTED} required")
            if prec.median is None:
                parts.append(f"precedents {prec.n_admitted} admitted of {MIN_ADMITTED} required")
            sel.gap = f"requested blend, {'; '.join(parts)}; no fallback"
    elif basis == "issuer_trading":
        sel.ebitda_basis = issuer_row["ebitda_basis"]
        sel.ebitda_basis_path = ("valuation", "issuer_market", "ebitda_basis")
        sel.selected_basis, sel.basis_known = "issuer_trading", True
        if issuer_row["ebitda_basis"] == "NTM":
            sel.gap = NTM_GAP
            sel.reason = NTM_GAP
        elif issuer_row["ev"] <= 0:
            sel.gap = "Not calculable: the issuer's enterprise value is not above zero"
            sel.reason = sel.gap
        else:
            sel.set_ids = ["issuer_trading"]
            sel.formula = "issuer enterprise value / CP-1 LTM adjusted EBITDA, rounded half-even to 2 dp"
            sel.cite_paths = [("valuation", "issuer_market", "market_cap_m"), ("valuation", "issuer_market", "net_debt_m")]
    elif basis == "user_multiple":
        sel.ebitda_basis = user_row["basis"]
        sel.ebitda_basis_path = ("valuation", "user_multiple", "basis")
        sel.selected_basis, sel.basis_known = "user_multiple", True
        sel.multiple = round2(user_row["value"])
        sel.reason = f"user-supplied ({user_row['basis']} basis); rationale: {user_row['rationale']}"
        sel.set_ids, sel.formula = ["user_multiple"], "user-supplied multiple"
        sel.user_supplied = True
        sel.cite_paths = [("valuation", "user_multiple", "value"), ("valuation", "user_multiple", "rationale")]
    sel.public, sel.precedents, sel.issuer_row, sel.user_row = public, prec, issuer_row, user_row
    return sel


ISSUER_EBITDA = Decimal("30")  # CP-1 LTM adjusted EBITDA: financial page:2, cp4c-owner expected cp1_inputs.ebitda


def finish_selection(sel):
    """Issuer multiple and implied EV once the CP-1 EBITDA is known."""
    if sel.issuer_row is not None and sel.gap is None:
        sel.issuer_row["multiple"] = CTX.divide(sel.issuer_row["ev"], ISSUER_EBITDA)
        sel.multiple = round2(sel.issuer_row["multiple"])
        sel.reason = (f"issuer_trading: enterprise value {fixed(sel.issuer_row['ev'], 1)} (market cap "
                      f"{exact(Decimal(CONTEXTS_CUR['market_cap_m']))} plus net debt {exact(Decimal(CONTEXTS_CUR['net_debt_m']))}, "
                      f"as of {sel.issuer_row['as_of']}) over CP-1 LTM adjusted EBITDA {fixed(ISSUER_EBITDA, 1)}")
    sel.implied = CTX.multiply(sel.multiple, ISSUER_EBITDA) if sel.multiple is not None else None


# --- 5. fact emission --------------------------------------------------------------------------------
COLS9 = [("kind", "Kind"), ("name", "Name"), ("figures_date", "Figures dated"), ("source", "Source"),
         ("currency", "Currency"), ("ebitda_period", "EBITDA period"), ("ev", "Enterprise value"),
         ("ebitda", "EBITDA"), ("multiple", "EV/EBITDA"), ("flag", "Outlier flag"), ("result", "Result")]
COLS10 = [("n_total", "Records"), ("n_admitted", "Admitted"), ("min", "Minimum"), ("median", "Median"),
          ("max", "Maximum"), ("outliers", "Outliers")]
COLS11 = [("requested_basis", "Requested basis"), ("selected_basis", "Selected basis"), ("reason", "Reason"),
          ("ebitda_basis", "EBITDA basis"), ("selected_multiple", "Selected multiple"),
          ("issuer_ebitda", "Issuer EBITDA"), ("implied_ev", "Implied enterprise value")]
TITLES = {"T1C.9": "EV/EBITDA records", "T1C.10": "EV/EBITDA statistics", "T1C.11": "Valuation basis selection"}
LABELS = {t: dict(c) for t, c in (("T1C.9", COLS9), ("T1C.10", COLS10), ("T1C.11", COLS11))}


class Emitter:
    def __init__(self, cid):
        self.cid = cid
        self.facts = []
        self.rows = {}  # table -> list of (row_id, label, [fact ids])

    def cite(self, *paths):
        out = []
        for path in paths:
            ln = LINEMAPS[self.cid][path]
            out.append({"source_id": "context", "locator": f"line:{ln}", "quote": LINES[self.cid][ln - 1].strip()})
        return out

    def add(self, table, row, field, *, status="known", text=None, amount=None, unit=None, period=None,
            decimals=None, shown=None, value_class=None, formula=None, derives=None, cites=None, limitation=None,
            currency=None):
        fid = f"{table}.{row}.{field}"
        fact = {"fact_id": fid, "table_id": table, "row_id": row, "field": field, "label": LABELS[table][field], "status": status}
        if unit:
            fact["unit"] = unit
        if period:
            fact["period"] = period
        if status == "known":
            if text is not None:
                fact["text"] = text
            else:
                fact["amount_exact"] = exact(amount)
        else:
            fact["text" if unit is None else "amount_exact"] = None
        fact["shown"] = shown
        if currency:
            fact["currency"] = currency
        if unit == "MILLIONS":
            fact["scale"] = "1000000"
        if decimals is not None:
            fact["decimals"] = decimals
        if status == "known":
            fact["value_class"] = value_class
            if formula:
                fact["formula"] = formula
            if value_class == "calculated":
                fact["calculation_id"] = f"calc:{fid}"
            if derives is not None:
                fact["derives_from"] = derives
            if cites:
                fact["citations"] = cites
        else:
            fact["limitation"] = limitation
        self.facts.append(fact)
        return fid

    def known_text(self, table, row, field, text, value_class, **kw):
        return self.add(table, row, field, text=text, shown=text, value_class=value_class, **kw)

    def unsettled(self, table, row, field, status, reason, unit=None, period=None):
        return self.add(table, row, field, status=status, unit=unit, period=period, limitation=reason)

    def money(self, table, row, field, amount, period, cites, derives=None):
        return self.add(table, row, field, amount=amount, unit="MILLIONS", period=period, decimals=1,
                        shown=fixed(amount, 1), value_class="source", cites=cites)

    def multiple(self, table, row, field, amount, period, formula, derives, cites, value_class="calculated"):
        return self.add(table, row, field, amount=amount, unit="MULTIPLE", period=period, decimals=2,
                        shown=mult_shown(amount), value_class=value_class, formula=formula, derives=derives, cites=cites)

    def count(self, table, row, field, n, period, formula, derives, cites=None):
        return self.add(table, row, field, amount=Decimal(n), unit="records", period=period, shown=f"{n} records",
                        value_class="calculated", formula=formula, derives=derives, cites=cites)

    def row(self, table, row_id, label, fids):
        self.rows.setdefault(table, []).append({"row_id": row_id, "label": label, "fact_ids": fids})


def n_adm_text(n):
    return f"Not calculable: {n} admitted of {MIN_ADMITTED} required"


def emit_t19(em, recs, sel, spec, ctx_obj):
    """T1C.9 rows."""
    sets = {"peer": sel.public, "precedent": sel.precedents}
    if not recs:
        none_reason = "No peer or precedent records are in the context"
        fids = []
        gap = {"cp_dr_public": GAP_DR}.get(ctx_obj["valuation"]["peer_source"])
        status, reason = ("missing", gap) if (gap and ctx_obj["valuation"]["basis"] in ("auto", "public_comps")) else ("not_applicable", none_reason)
        for field, _label in COLS9:
            fids.append(em.unsettled("T1C.9", "none", field, status, reason))
        em.row("T1C.9", "none", "No records", fids)
        return
    for r in recs:
        row = r.row_id
        stat = sets[r.kind]
        set_id = stat.set_id
        kind_text = "Public comp" if r.kind == "peer" else "Precedent"
        period = f"As of {r.when}" if r.when else "Date not stated by the user"
        fids = [em.known_text("T1C.9", row, "kind", kind_text, "normalized"),
                em.known_text("T1C.9", row, "name", r.name, "source", cites=em.cite(r.paths["name"]))]
        if r.ev is None:  # user_list: names only
            for field, _l in COLS9[2:]:
                if field == "flag":
                    fids.append(em.unsettled("T1C.9", row, field, "not_applicable", "Not meaningful: the record is excluded from the statistics"))
                elif field == "result":
                    fids.append(em.known_text("T1C.9", row, "result", r.result, "normalized",
                                              formula="Included when EV and EBITDA are above zero and the record is dated within the window",
                                              derives=[]))
                else:
                    fids.append(em.unsettled("T1C.9", row, field, "missing", GAP_UL,
                                             unit="MILLIONS" if field in ("ev", "ebitda") else ("MULTIPLE" if field == "multiple" else None),
                                             period=None if field not in ("ev", "ebitda", "multiple") else "Date not stated by the user"))
            em.row("T1C.9", row, r.name, fids)
            continue
        ev_id, ebitda_id = f"T1C.9.{row}.ev", f"T1C.9.{row}.ebitda"
        if r.when:
            fids.append(em.known_text("T1C.9", row, "figures_date", r.when, "source", cites=em.cite(r.paths["as_of"])))
        else:
            fids.append(em.unsettled("T1C.9", row, "figures_date", "missing", NOT_STATED))
        fids.append(em.known_text("T1C.9", row, "source", r.source, "source", cites=em.cite(r.paths["source"])))
        fids.append(em.known_text("T1C.9", row, "currency", NOT_STATED, "normalized"))
        fids.append(em.known_text("T1C.9", row, "ebitda_period", NOT_STATED, "normalized"))
        fids.append(em.money("T1C.9", row, "ev", r.ev, period, em.cite(r.paths["ev_m"])))
        fids.append(em.money("T1C.9", row, "ebitda", r.ebitda, period, em.cite(r.paths["ebitda_m"])))
        if r.multiple is not None:
            fids.append(em.multiple("T1C.9", row, "multiple", r.multiple, period, "EV / EBITDA", [ev_id, ebitda_id],
                                    em.cite(r.paths["ev_m"], r.paths["ebitda_m"])))
        else:
            fids.append(em.unsettled("T1C.9", row, "multiple", "not_applicable",
                                     "Not meaningful: " + ("enterprise value is zero" if r.ev <= 0 else "EBITDA is not above zero"),
                                     unit="MULTIPLE", period=period))
        if not r.included:
            fids.append(em.unsettled("T1C.9", row, "flag", "not_applicable", "Not meaningful: the record is excluded from the statistics"))
        elif stat.median is None:
            fids.append(em.unsettled("T1C.9", row, "flag", "missing", n_adm_text(stat.n_admitted)))
        else:
            fids.append(em.known_text("T1C.9", row, "flag", r.flag, "normalized",
                                      formula="Outlier when the absolute deviation from the set median is above one half",
                                      derives=[f"T1C.9.{row}.multiple", f"T1C.10.{set_id}.median"]))
        fids.append(em.known_text("T1C.9", row, "result", r.result, "normalized",
                                  formula="Included when EV and EBITDA are above zero and the record is dated within the window",
                                  derives=[f"T1C.9.{row}.figures_date", ev_id, ebitda_id]))
        em.row("T1C.9", row, r.name, fids)


def window_period(stat):
    months = PEER_MONTHS if stat.set_id == "public_comps" else PRECEDENT_MONTHS
    return f"Window {months_back(date.fromisoformat(AS_OF), months).isoformat()} to {AS_OF}"


def emit_set_row(em, stat, label):
    row = stat.set_id
    period = window_period(stat)
    ids = [r for r in stat.recs]
    row_ids = lambda: [f"T1C.9.{r.row_id}" for r in ids]  # noqa: E731
    fids = []
    fids.append(em.count("T1C.10", row, "n_total", stat.n_total, period, "count of records in the set",
                         [f"{p}.result" for p in row_ids()]))
    fids.append(em.count("T1C.10", row, "n_admitted", stat.n_admitted, period,
                         "count of records admitted (EV and EBITDA above zero, dated within the window)",
                         [f"{p}.result" for p in row_ids()]))
    adm = stat.admitted
    adm_cites = []
    for r in adm:
        adm_cites += em.cite(r.paths["ev_m"], r.paths["ebitda_m"])
    mult_ids = [f"T1C.9.{r.row_id}.multiple" for r in adm]
    if adm:
        fids.append(em.multiple("T1C.10", row, "min", stat.minimum, period, "smallest multiple among the admitted records", mult_ids, adm_cites))
    else:
        fids.append(em.unsettled("T1C.10", row, "min", "missing", "Not calculable: no admitted records", unit="MULTIPLE", period=period))
    if stat.median is not None:
        fids.append(em.multiple("T1C.10", row, "median", stat.median, period,
                                "median of the admitted records' multiples; even count: (a + b) / 2; fewer than 3 admitted: not calculated",
                                mult_ids, adm_cites))
    else:
        fids.append(em.unsettled("T1C.10", row, "median", "missing", n_adm_text(stat.n_admitted), unit="MULTIPLE", period=period))
    if adm:
        fids.append(em.multiple("T1C.10", row, "max", stat.maximum, period, "largest multiple among the admitted records", mult_ids, adm_cites))
    else:
        fids.append(em.unsettled("T1C.10", row, "max", "missing", "Not calculable: no admitted records", unit="MULTIPLE", period=period))
    if stat.outliers is not None:
        fids.append(em.count("T1C.10", row, "outliers", stat.outliers, period,
                             "count of admitted records whose absolute deviation from the median is above one half",
                             [f"T1C.9.{r.row_id}.flag" for r in adm]))
    else:
        fids.append(em.unsettled("T1C.10", row, "outliers", "missing", n_adm_text(stat.n_admitted), unit="records", period=period))
    em.row("T1C.10", row, label, fids)


def emit_single_row(em, row, label, multiple, period, cites, formula, value_class="calculated"):
    """issuer_trading and user_multiple: one value, no outlier test."""
    fids = []
    ok = multiple is not None
    fids.append(em.count("T1C.10", row, "n_total", 1, period, "count of records in the set", []))
    fids.append(em.count("T1C.10", row, "n_admitted", 1 if ok else 0, period, "count of records with a multiple", []))
    for field, word in (("min", "the value"), ("median", "the value"), ("max", "the value")):
        if ok:
            fids.append(em.multiple("T1C.10", row, field, multiple, period, f"{formula} (a single value: min, median and max are {word})", [], cites, value_class=value_class))
        else:
            fids.append(em.unsettled("T1C.10", row, field, "missing", "Not calculable: no multiple", unit="MULTIPLE", period=period))
    fids.append(em.unsettled("T1C.10", row, "outliers", "not_applicable", "Not meaningful: a single value has no outlier test", unit="records", period=period))
    em.row("T1C.10", row, label, fids)


def emit_t1011(em, sel, spec, ctx_obj):
    val = ctx_obj["valuation"]
    basis = val["basis"]
    # T1C.10
    show_public = basis in ("auto", "public_comps", "blend") or sel.public.n_total
    show_prec = basis in ("precedents", "blend") or sel.precedents.n_total
    if show_public:
        emit_set_row(em, sel.public, "Public comps")
    if show_prec:
        emit_set_row(em, sel.precedents, "Precedents")
    if basis == "issuer_trading":
        ir = sel.issuer_row
        mult = ir["multiple"]
        emit_single_row(em, "issuer_trading", "Issuer trading", mult, f"As of {ir['as_of']}",
                        em.cite(*sel.cite_paths) if mult is not None else [],
                        "issuer enterprise value / CP-1 LTM adjusted EBITDA")
    if basis == "user_multiple":
        ur = sel.user_row
        emit_single_row(em, "user_multiple", "User multiple", sel.multiple, NOT_STATED,
                        em.cite(*sel.cite_paths[:1]), "user-supplied multiple", value_class="source")
    # T1C.11
    row = "selection"
    fids = []
    fids.append(em.known_text("T1C.11", row, "requested_basis", basis, "source", cites=em.cite(("valuation", "basis"))))
    if sel.basis_known:
        fids.append(em.known_text("T1C.11", row, "selected_basis", sel.selected_basis, "normalized"))
    else:
        fids.append(em.unsettled("T1C.11", row, "selected_basis", "missing", sel.gap))
    reason = sel.reason if sel.reason else sel.gap
    fids.append(em.known_text("T1C.11", row, "reason", reason, "normalized"))
    if sel.ebitda_basis_path:
        fids.append(em.known_text("T1C.11", row, "ebitda_basis", sel.ebitda_basis, "source", cites=em.cite(sel.ebitda_basis_path)))
    else:
        fids.append(em.known_text("T1C.11", row, "ebitda_basis", NOT_STATED, "normalized"))
    period = f"EBITDA basis: {sel.ebitda_basis}"
    mid = "T1C.11.selection.selected_multiple"
    if sel.multiple is not None:
        derives = [f"T1C.10.{s}.median" for s in sel.set_ids if s in ("public_comps", "precedents")]
        cites = []
        for s in sel.set_ids:
            stat = {"public_comps": sel.public, "precedents": sel.precedents}.get(s)
            if stat is not None:
                for r in stat.admitted:
                    cites += em.cite(r.paths["ev_m"], r.paths["ebitda_m"])
        cites += em.cite(*sel.cite_paths)
        if sel.user_supplied:
            fids.append(em.multiple("T1C.11", row, "selected_multiple", sel.multiple, period, sel.formula, [], cites, value_class="source"))
        else:
            fids.append(em.multiple("T1C.11", row, "selected_multiple", sel.multiple, period, sel.formula, derives, cites))
    else:
        fids.append(em.unsettled("T1C.11", row, "selected_multiple", "missing", sel.gap, unit="MULTIPLE", period=period))
    fids.append(em.add("T1C.11", row, "issuer_ebitda", amount=ISSUER_EBITDA, unit="MILLIONS", period=LTM_PERIOD, decimals=1,
                       shown=fixed(ISSUER_EBITDA, 1), currency="USD", value_class="calculated",
                       formula="CP-1 LTM adjusted EBITDA (T4.10)", derives=["cp1:ebitda"]))
    if sel.implied is not None:
        fids.append(em.add("T1C.11", row, "implied_ev", amount=sel.implied, unit="MILLIONS", period=LTM_PERIOD, decimals=1,
                           shown=fixed(sel.implied, 1), currency="USD", value_class="calculated",
                           formula="selected multiple x CP-1 LTM adjusted EBITDA",
                           derives=[mid, "T1C.11.selection.issuer_ebitda"]))
    else:
        fids.append(em.unsettled("T1C.11", row, "implied_ev", "missing", "Not calculable: no selected multiple",
                                 unit="MILLIONS", period=LTM_PERIOD))
    em.row("T1C.11", row, "Selection", fids)


def tables_of(em):
    out = []
    for table, cols in (("T1C.9", COLS9), ("T1C.10", COLS10), ("T1C.11", COLS11)):
        out.append({"table_id": table, "title": TITLES[table],
                    "columns": [{"field": f, "label": l} for f, l in cols], "rows": em.rows[table]})
    return out


# --- 6. limitations -----------------------------------------------------------------------------------
def limitations_new(spec, recs, sel, ctx_obj):
    val = ctx_obj["valuation"]
    out = []
    figures = [r for r in recs if r.ev is not None]
    if figures:
        out.append("The EV and EBITDA figures of the peers and precedents are the user's own entries in the context file; CP-1C does not verify them against a source.")
        out.append("The peers' and precedents' currency and EBITDA period are not stated by the user; each multiple assumes its EV and EBITDA share both, and the selected multiple is applied to the issuer's LTM Q4 25 EBITDA.")
    shown = [s for s in (sel.public, sel.precedents) if s.n_admitted and MIN_ADMITTED <= s.n_admitted < THIN_UNIVERSE]
    if shown and not spec.get("pack") == "peers":
        out.append("Medians over fewer than five peers move with a single peer.")
    elif shown:
        pass  # the frozen positive list already carries the same sentence
    if val["basis"] == "issuer_trading":
        mk = val["issuer_market"]
        out.append(f"The issuer's trading figures are the user's own entries (source: {mk['source']}, dated {mk['as_of']}); CP-1C does not verify them against a market source.")
    if val["basis"] == "user_multiple":
        um = val["user_multiple"]
        out.append(f"The selected multiple is user-supplied ({um['basis']} basis; rationale: {um['rationale']}); CP-1C does not verify it.")
    if sel.multiple is None:
        out.append(f"Valuation basis not selected: {sel.gap}.")
    return out


def own_limitations_base(spec):
    case = "positive" if spec.get("pack") == "peers" else "no_peers"
    return case, list(CP1C_E["cases"][case]["own_limitations"])


# --- 7. CP-4C -----------------------------------------------------------------------------------------
EB_LINE = {}
for _vid, _eid in (("v01", "T4E.3.v01.ebitda"), ("v02", "T4E.3.v02.ebitda"), ("v03", "T4E.3.v03.ebitda")):
    EB_LINE[_vid] = line_after("cases/cp4c-owner/expected.json", f'"fact_id": "{_eid}"', '"amount_exact"')
_FACTS = {f["fact_id"]: f for f in CP4C_E["cases"]["positive"]["facts"]}
EBITDA_FY26 = {"v01": Decimal(_FACTS["T4E.3.v01.ebitda"]["amount_exact"]),
               "v02": Decimal(_FACTS["T4E.3.v02.ebitda"]["amount_exact"]),
               "v03": Decimal(_FACTS["T4E.3.v03.ebitda"]["amount_exact"])}
assert EBITDA_FY26 == {"v01": Decimal("30.9"), "v02": Decimal("18.54"), "v03": Decimal("18.54")}
CASE_LABEL = {"v01": "Base", "v02": "Downside", "v03": "Stress"}
UPSTREAM_LINES = {
    "cp4c T4E.3.v01.ebitda amount": f"cases/cp4c-owner/expected.json:{EB_LINE['v01']}",
    "cp4c T4E.3.v02.ebitda amount": f"cases/cp4c-owner/expected.json:{EB_LINE['v02']}",
    "cp4c T4E.3.v03.ebitda amount": f"cases/cp4c-owner/expected.json:{EB_LINE['v03']}",
    "cp4c T4E.3.v01.multiple (frozen 4.0 base, analyst input)": "cases/cp4c-owner/expected.json:" + str(line_after("cases/cp4c-owner/expected.json", '"fact_id": "T4E.3.v01.multiple"')),
    "cp4c cp1_inputs.ebitda (CP-1 LTM, 30)": "cases/cp4c-owner/expected.json:" + str(line_after("cases/cp4c-owner/expected.json", '"ebitda": {', '"amount_exact"')),
    "financial page:2 Adjusted EBITDA row (FY 2025 30.0)": "cases/financial/manifest.json page:2 (locator at line "
        + str(line_after("cases/financial/manifest.json", '"locator": "page:2"')) + "), quote 'Adjusted EBITDA  7.5  7.5  7.5  7.5  30.0'",
    "cp1c no_peers own_limitations": "cases/cp1c-owner/expected.json cases.no_peers.own_limitations",
    "cp1c positive facts": "cases/cp1c-owner/expected.json cases.positive.facts",
}
assert Decimal(_FACTS["T4E.3.v01.ebitda"]["amount_exact"]) == Decimal("30.9")


_P6 = RAW["cases/pins-context-owner/expected.json"].decode("utf-8").splitlines()
PHASE6_LINE_NO = next(i for i, t in enumerate(_P6, 1) if t.strip().startswith('"CP-4C": "The EV multiple is'))
PHASE6_PINNED_LINE = json.loads("{" + _P6[PHASE6_LINE_NO - 1].strip().rstrip(",") + "}")["CP-4C"]
assert PHASE6_PINNED_LINE == "The EV multiple is a user-supplied assumption pinned in the context file; the submission equals the pin."


def cp4c_block(cid, spec, sel, ctx_obj):
    bound = sel.multiple is not None
    pin = spec.get("pin")
    block = {"requested_modules": ["CP-1C", "CP-4C"], "plan_order": PLAN_BOTH, "inputs": CP4C_INPUTS}
    if not bound:
        block.update({
            "multiple_rule": "not bound: the selected multiple is unknown, so CP-4C applies no multiple rule",
            "accepted_submissions": [{"multiples": ["4.00", "3.00", "2.00"]}, {"multiples": ["not assessed", "not assessed", "not assessed"]}],
            "formula_suffix": None,
            "added_limitation": None,
        })
        return block
    m = sel.multiple
    basis_text = sel.selected_basis
    ebitda_basis = sel.ebitda_basis
    values = []
    applied = Decimal(pin) if pin else m
    for vid in ("v01", "v02", "v03"):
        eb = EBITDA_FY26[vid]
        ev = eb * applied  # exact: Decimal multiplication of short decimals is exact in the default context
        assert ev == CTX.multiply(eb, applied)
        implied = CTX.divide(ev, ISSUER_EBITDA)
        values.append({
            "case_id": vid, "label": CASE_LABEL[vid], "ebitda_source": UPSTREAM_LINES[f"cp4c T4E.3.{vid}.ebitda amount"],
            "ebitda_exact": exact(eb), "ebitda_shown": fixed(eb, 2),
            "multiple_exact": exact(applied), "multiple_shown": mult_shown(applied),
            "multiple_formula": "analyst input" if pin else f"analyst input, equal to the CP-1C selected multiple (T1C.11, basis {basis_text})",
            "ev_exact": exact(ev), "ev_shown": fixed(ev, 2),
            "implied_ltm_multiple_exact": exact(implied), "implied_ltm_multiple_shown": mult_shown(implied),
        })
    if pin:
        limitation = (f"CP-1C selected {fixed(m, 2)}x (basis {basis_text}, EBITDA basis {ebitda_basis}); the context pins the EV multiple at "
                      f"{pin}, which governs, so the selection is not applied. No alignment is made between an LTM or NTM multiple and a forecast year.")
    else:
        limitation = (f"The EV multiple is the CP-1C selected multiple {fixed(m, 2)}x (basis {basis_text}, EBITDA basis {ebitda_basis}), applied to the "
                      f"CP-2G forecast EBITDA of each valuation case (base case FY2026 for the base valuation); no alignment is made between an LTM or NTM multiple and a forecast year.")
    if pin:
        block["phase6_pinned_line"] = PHASE6_PINNED_LINE
        block["phase6_pinned_line_source"] = f"cases/pins-context-owner/expected.json:{PHASE6_LINE_NO}"
    block.update({"selected_multiple": fixed(m, 2), "pinned_multiple": pin, "valuations": values,
                  "added_limitation": limitation,
                  "formula_suffix": None if pin else f", equal to the CP-1C selected multiple (T1C.11, basis {basis_text})"})
    mtxt = fixed(m, 2)
    if pin:
        block["accepted_submissions"] = [{"multiples": [fixed(Decimal(pin), 2)] * 3}, {"multiples": [pin] * 3}]
        block["refused_submissions"] = {
            "selection-equal-under-pin": {
                "multiples": [mtxt] * 3,
                "issues": [f"assumptions.cp4c.ev_multiple (valuation[{i}].multiple): pinned {pin}; submitted {mtxt}" for i in range(3)],
                "note": "the pin governs: the CP-1C selection rule is skipped, so no 'differs from the CP-1C selected multiple' line; Phase 6's pin text, one line per valuation",
            }}
    else:
        block["accepted_submissions"] = [{"multiples": [mtxt] * 3}, {"multiples": [exact(m)] * 3}]
        block["refused_submissions"] = {
            "ev-multiple-differs": {
                "multiples": ["4.00", mtxt, mtxt],
                "issues": [f"valuation v01: multiple 4.00 differs from the CP-1C selected multiple {mtxt}"],
            },
            "ev-multiple-differs-v03": {
                "multiples": [mtxt, mtxt, "4.00"],
                "issues": [f"valuation v03: multiple 4.00 differs from the CP-1C selected multiple {mtxt}"],
            },
            "ev-not-assessed-when-selected": {
                "multiples": [mtxt, "not assessed", mtxt],
                "issues": [f"valuation v02: multiple not assessed differs from the CP-1C selected multiple {mtxt}"],
            },
        }
    return block


def single_rows(spec, sel):
    """T1C.10 rows of the single-value bases (issuer_trading, user_multiple)."""
    if spec["basis"] not in ("issuer_trading", "user_multiple"):
        return {}
    ok = sel.multiple is not None
    shown = None if not ok else fixed(sel.multiple, 2)
    return {spec["basis"]: {"n_total": 1, "n_admitted": 1 if ok else 0, "min": shown, "median": shown, "max": shown, "outliers": None}}


# --- 8. assemble ---------------------------------------------------------------------------------------
CONTEXTS = {cid: context_object(spec) for cid, spec in CASES.items()}
CONTEXTS_CUR = None
CTX_TEXT, LINEMAPS, LINES, CTX_BYTES = {}, {}, {}, {}
for cid, obj in CONTEXTS.items():
    text, lm = dump_with_lines(obj)
    CTX_TEXT[cid], LINEMAPS[cid] = text, lm
    LINES[cid] = text.splitlines()
    CTX_BYTES[cid] = text.encode("utf-8")

PACKS = {
    "closed-chain": {
        "sources": ["identity", "financial", "legal-covenants", "context"],
        "identity": CP4C_M["sources"]["identity"],
        "financial": CP4C_M["sources"]["financial"],
        "legal-covenants": CP4C_M["sources"]["legal-covenants"]["positive"],
        "context": "contexts/<case>.json via context.prepare (the literal bytes; sha256 in contexts.<case>.sha256)",
        "base": "cases/cp4c-owner/manifest.json positive pack plus the context source",
    },
    "peers": {
        "sources": ["identity", "financial", "peers", "context"],
        "identity": CP4C_M["sources"]["identity"],
        "financial": CP4C_M["sources"]["financial"],
        "peers": {"path": "cases/cp1c-owner/manifest.json", "case": "synthetic_source.positive",
                  "sha256": CP1C_M["synthetic_source"]["positive"]["sha256"]},
        "context": "contexts/credit-plus-comps.json via context.prepare",
        "base": "cases/cp1c-owner/manifest.json positive pack plus the context source",
    },
}

EXPECTED_CASES = {}
MANIFEST_CONTEXTS = {}
SUMMARY = {}
for cid, spec in CASES.items():
    CONTEXTS_CUR = CONTEXTS[cid]["valuation"]["issuer_market"]
    recs = build_records(spec, cid)
    ctx_obj = CONTEXTS[cid]
    sel = evaluate(spec, recs, ctx_obj)
    finish_selection(sel)
    em = Emitter(cid)
    emit_t19(em, recs, sel, spec, ctx_obj)
    # T1C.10 rows and T1C.11 are emitted together so the median fact ids exist before T1C.9 refers to them
    emit_t1011(em, sel, spec, ctx_obj)
    base_case, base_lims = own_limitations_base(spec)
    new_lims = limitations_new(spec, recs, sel, ctx_obj)
    own = base_lims + [t for t in new_lims if t not in base_lims]
    run_cases = spec.get("requested", ["CP-1C", "CP-4C"])
    case_kind = ctx_obj["run"]["case_kind"]
    settled = own + ([SYNTHETIC_LINE] if case_kind == "synthetic" else [])
    entry = {
        "context": f"contexts/{cid}.json",
        "pack": spec.get("pack", "closed-chain") if spec.get("pack") else "closed-chain",
        "run": {
            "run_id": f"valctx-{cid}-v1", "issuer_id": ISSUER_ID, "issuer_name": ISSUER_NAME, "as_of": AS_OF,
            "method_version": "deploy-v-r14", "case_kind": case_kind, "pathway": PATHWAY, "requested_modules": run_cases,
        },
        "plan_order": PLAN_BOTH if run_cases == ["CP-1C", "CP-4C"] else PLAN_1C,
        "cp1c": {
            "base_cells": (f"T1C.1-T1C.8 and their facts, claims and tie-outs equal cases/cp1c-owner/expected.json cases.{base_case}"
                           f" (submission cases/cp1c-owner/submissions.json {base_case}); nothing in them changes"),
            "table_ids": ["T1C.1", "T1C.2", "T1C.3", "T1C.4", "T1C.5", "T1C.6", "T1C.7", "T1C.8", "T1C.9", "T1C.10", "T1C.11"],
            "records": [{"row_id": r.row_id, "kind": r.kind, "name": r.name, "figures_date": r.when or None,
                         "multiple_exact": None if r.multiple is None else exact(r.multiple),
                         "result": r.result, "included": r.included,
                         "deviation_exact": None if r.deviation is None else exact(r.deviation),
                         "deviation_4dp": None if r.deviation is None else fixed(r.deviation, 4)} for r in recs],
            "statistics": {s.set_id: {"n_total": s.n_total, "n_admitted": s.n_admitted,
                                      "min": None if s.minimum is None else fixed(s.minimum, 2),
                                      "median": None if s.median is None else fixed(s.median, 2),
                                      "max": None if s.maximum is None else fixed(s.maximum, 2),
                                      "outliers": s.outliers}
                           for s in (sel.public, sel.precedents) if s.n_total or spec["basis"] in ("auto", "public_comps", "precedents", "blend")},
            "single_value_rows": single_rows(spec, sel),
            "selection": {"requested_basis": spec["basis"], "selected_basis": sel.selected_basis if sel.basis_known else None,
                          "selected_multiple": None if sel.multiple is None else fixed(sel.multiple, 2),
                          "issuer_ebitda": fixed(ISSUER_EBITDA, 1),
                          "implied_ev": None if sel.implied is None else fixed(sel.implied, 1),
                          "reason": sel.reason or sel.gap, "gap": sel.gap, "ebitda_basis": sel.ebitda_basis},
            "tables": tables_of(em),
            "facts": em.facts,
            "own_limitations_new": new_lims,
            "own_limitations": own,
            "settled_limitations": settled,
            "module_status": "restricted",
            "module_status_note": "own limitations are non-empty (as the frozen cp1c cases): restricted; blocked only by the frozen refusal paths",
        },
    }
    if run_cases == ["CP-1C", "CP-4C"]:
        entry["cp4c"] = cp4c_block(cid, spec, sel, ctx_obj)
    EXPECTED_CASES[cid] = entry
    MANIFEST_CONTEXTS[cid] = {"file": f"contexts/{cid}.json", "pack": entry["pack"], "sha256": sha(CTX_BYTES[cid]), "run": entry["run"]}
    SUMMARY[cid] = (sel, recs)

# --- 9. hand-derived figures of the brief (asserted, not computed) ---------------------------------------
HAND_DERIVED = {
    "auto-public": dict(results=["Included", "Included", "Included",
                                 "Excluded: figures dated 2024-12-31 are before 2025-01-10 (12-month limit)",
                                 "Excluded: enterprise value is zero"],
                        stats=dict(n_total=5, n_admitted=3, min="6.00", median="7.00", max="9.00", outliers=0),
                        dev4=["0.2857", "-0.1429", "0.0000"], multiple="7.00", issuer_ebitda="30.0", implied_ev="210.0",
                        cp4c=[("216.30", "7.21x"), ("129.78", "4.33x"), ("129.78", "4.33x")]),
    "auto-thin": dict(n_admitted=2, median=None, basis=INSUFFICIENT, multiple=None),
    "public-thin": dict(n_admitted=2, gap="requested public_comps, 2 admitted of 3 required; no fallback"),
    "precedents": dict(stats=dict(n_total=6, n_admitted=4, min="6.00", median="9.50", max="12.50", outliers=0),
                       multiple="9.50", implied_ev="285.0",
                       p3="Excluded: deal dated 2022-12-31 is before 2023-01-10 (36-month limit)",
                       p6="Excluded: no deal date, the window cannot be checked", p4dev="0.3158"),
    "blend": dict(multiple="8.25", implied_ev="247.5", public_median="7.00", precedents_median="9.50"),
    "issuer-trading": dict(multiple="9.00", implied_ev="270.0"),
    "issuer-trading-ntm": dict(multiple=None, reason=NTM_GAP),
    "user-multiple": dict(multiple="8.50", implied_ev="255.0"),
    "pin-vs-selection": dict(multiple="7.00", cp4c_v01_ev="262.65"),
}
H = HAND_DERIVED
s_, r_ = SUMMARY["auto-public"]
assert [r.result for r in r_] == H["auto-public"]["results"]
ec = EXPECTED_CASES["auto-public"]["cp1c"]
assert ec["statistics"]["public_comps"] == H["auto-public"]["stats"], ec["statistics"]
assert [r["deviation_4dp"] for r in ec["records"][:3]] == ["0.2857", "-0.1429", "0.0000"]
assert ec["selection"]["selected_multiple"] == "7.00" and ec["selection"]["implied_ev"] == "210.0" and ec["selection"]["issuer_ebitda"] == "30.0"
assert [(v["ev_shown"], v["implied_ltm_multiple_shown"]) for v in EXPECTED_CASES["auto-public"]["cp4c"]["valuations"]] == H["auto-public"]["cp4c"]
t = EXPECTED_CASES["auto-thin"]["cp1c"]
assert t["statistics"]["public_comps"]["n_admitted"] == 2 and t["statistics"]["public_comps"]["median"] is None
assert t["selection"]["selected_basis"] == INSUFFICIENT and t["selection"]["selected_multiple"] is None
assert "2 admitted of 3 required (12-month window)" in t["selection"]["reason"] and "(36-month window)" in t["selection"]["reason"]
assert EXPECTED_CASES["auto-thin"]["cp4c"]["added_limitation"] is None
assert EXPECTED_CASES["public-thin"]["cp1c"]["selection"]["gap"] == H["public-thin"]["gap"]
p = EXPECTED_CASES["precedents"]["cp1c"]
assert p["statistics"]["precedents"] == H["precedents"]["stats"]
assert p["records"][2]["result"] == H["precedents"]["p3"] and p["records"][5]["result"] == H["precedents"]["p6"]
assert p["records"][3]["deviation_4dp"] == H["precedents"]["p4dev"]
assert p["selection"]["selected_multiple"] == "9.50" and p["selection"]["implied_ev"] == "285.0"
b = EXPECTED_CASES["blend"]["cp1c"]
assert b["statistics"]["public_comps"]["median"] == "7.00" and b["statistics"]["precedents"]["median"] == "9.50"
assert b["selection"]["selected_multiple"] == "8.25" and b["selection"]["implied_ev"] == "247.5"
bt = EXPECTED_CASES["blend-thin"]["cp1c"]["selection"]
assert bt["selected_multiple"] is None and "precedents 2 admitted of 3 required" in bt["gap"]
i_ = EXPECTED_CASES["issuer-trading"]["cp1c"]["selection"]
assert i_["selected_multiple"] == "9.00" and i_["implied_ev"] == "270.0"
n_ = EXPECTED_CASES["issuer-trading-ntm"]["cp1c"]["selection"]
assert n_["selected_multiple"] is None and n_["reason"] == NTM_GAP
u_ = EXPECTED_CASES["user-multiple"]["cp1c"]["selection"]
assert u_["selected_multiple"] == "8.50" and u_["implied_ev"] == "255.0"
assert EXPECTED_CASES["user-list"]["cp1c"]["selection"]["gap"] == GAP_UL
adr = EXPECTED_CASES["auto-dr-public"]["cp1c"]["selection"]
assert adr["selected_basis"] == INSUFFICIENT and adr["selected_multiple"] is None
assert adr["reason"] == GAP_DR + "; precedents 0 admitted of 3 required"
assert EXPECTED_CASES["dr-public"]["cp1c"]["selection"]["gap"] == GAP_DR
pv = EXPECTED_CASES["pin-vs-selection"]
assert pv["cp1c"]["selection"]["selected_multiple"] == "7.00" and pv["cp4c"]["valuations"][0]["ev_shown"] == "262.65"
we = EXPECTED_CASES["window-edges"]["cp1c"]["records"]
assert [r["result"] for r in we] == ["Included", "Excluded: figures dated 2025-01-09 are before 2025-01-10 (12-month limit)"]
cpc = EXPECTED_CASES["credit-plus-comps"]["cp1c"]
assert cpc["statistics"] == EXPECTED_CASES["auto-public"]["cp1c"]["statistics"]
assert "cp4c" not in EXPECTED_CASES["credit-plus-comps"]
priv = EXPECTED_CASES["auto-public-private"]
assert SYNTHETIC_LINE not in priv["cp1c"]["settled_limitations"]
assert SYNTHETIC_LINE in EXPECTED_CASES["auto-public"]["cp1c"]["settled_limitations"]

# --- 10. files ---------------------------------------------------------------------------------------------
EXPECTED = {
    "schema_version": "valuation-context-owner-expected/1",
    "derivation": (
        "Phase 7 Task 0 oracle. Values come from the plan's Design 3-12 and Ruled Q1-Q7, rulings B8 and B17 items 7-8, the brief's "
        "hand-derived figures (asserted in the builder) and the frozen oracles in manifest.inputs_pinned; never from code the phase builds."
    ),
    "upstream_citations": UPSTREAM_LINES,
    "rules": {
        "window": "12 months for public comps, 36 months for precedents, counted back from the run as-of by calendar month, same day clamped to month end; "
                  "a record dated on the window start is Included; applies to explicit bases as well as auto (Ruled Q2)",
        "admission_order": "EV above zero, EBITDA above zero, a precedent has a date, dated on or after the window start; the first failing test gives the reason",
        "reasons": {
            "ev_zero": "Excluded: enterprise value is zero",
            "ebitda_not_positive": "Excluded: EBITDA is not above zero",
            "no_date": "Excluded: no deal date, the window cannot be checked",
            "stale_peer": "Excluded: figures dated <date> are before <window start> (12-month limit)",
            "stale_precedent": "Excluded: deal dated <date> is before <window start> (36-month limit)",
        },
        "statistics": "median needs 3 admitted records, else missing; min and max are shown from 1 admitted; outlier = absolute relative deviation from the "
                      "set median strictly above 0.5, flag only; deviations in exact 38-digit half-even decimals, given to 4 dp in records[].deviation_4dp",
        "selection": "auto: public comps with >= 3 admitted, else precedents with >= 3 admitted, else Insufficient Information (known text, multiple missing); "
                     "explicit bases never fall back; blend = plain average of both medians, both needed; blend is never automatic; "
                     "selected multiple = chosen value rounded half-even to 2 dp",
        "rounding_of_display": "deploy_vii/display.py: ROUND_HALF_UP on the exact value, thousands commas; MILLIONS amounts at decimals 1, multiples at decimals 2, counts as '<n> records' (no singular)",
        "t1c10_rows": "public_comps for auto, public_comps and blend (or when peer records exist); precedents for precedents and blend (or when precedent records exist); "
                      "issuer_trading and user_multiple rows for those bases (single value: min = median = max = the value, outliers not_applicable, n_total 1)",
        "t1c9_none_row": "when the context has no peer or precedent records T1C.9 holds one row `none` (all cells not_applicable; for peer_source cp_dr_public with a peer basis or auto, "
                         "missing with the Design 8 text); user_list names give rows e01.. with name known and every figure cell missing",
        "citations": "a fact from the user's field cites {source_id context, locator line:N, quote the stripped line}; N is the line of the field in the context file's "
                     "json.dumps(indent=2) text (ensure_ascii False, LF, trailing LF); the citation's source_sha256 is contexts.<case>.sha256 in the manifest",
        "value_classes": "user figures and names: source; Python-composed text and the labels: normalized; multiples, statistics, selection, EBITDA and implied EV: calculated "
                         "(user_multiple's selected_multiple: source); calculation_id is `calc:<fact_id>` on calculated facts",
        "t1c_1_to_8": "unchanged: equal to the frozen cp1c-owner no_peers case (positive for credit-plus-comps); the analyst submission does not change",
        "limitation_order": "the frozen case's own_limitations, then own_limitations_new in order (a new line equal to a frozen line is not repeated), then on a synthetic run the synthetic line",
        "cp4c": "every valuation case (v01-v03, the stress case included) carries the selected multiple M when known; a submitted multiple equal to M numerically is accepted "
                "(7 equals 7.00); another value or `not assessed` is refused with `valuation <case_id>: multiple <submitted as typed> differs from the CP-1C selected multiple <M at 2 dp>`, "
                "one issue per valuation in case order; EV = CP-2G FY2026 EBITDA x M exact; implied LTM multiple = EV / 30; the T4E.3 multiple cell's formula gains the suffix; "
                "when M is unknown CP-4C applies no multiple rule; when the context pins ev_multiple the pin governs (Ruled Q4)",
        "cp4c_inputs": "CP-4C's bound inputs follow plan order over its required and selected optional edges: prepared-pack, CP-0, CP-1, CP-1C, CP-2A, CP-4, CP-2G",
    },
    "refusal_ids": {
        "ev-multiple-differs": {"case": "auto-public", "text": "valuation v01: multiple 4.00 differs from the CP-1C selected multiple 7.00"},
        "ev-not-assessed-when-selected": {"case": "auto-public", "text": "valuation v02: multiple not assessed differs from the CP-1C selected multiple 7.00",
                                          "note": "template applied to the submitted text; the brief names the id, not the text"},
        "pin-differs-under-selection": {"case": "pin-vs-selection", "text": "see cases.pin-vs-selection.cp4c.refused_submissions.selection-equal-under-pin.issues"},
    },
    "hand_derived": {k: v for k, v in H.items()},
    "cases": EXPECTED_CASES,
}

MANIFEST = {
    "schema_version": "valuation-context-owner-cases/1",
    "scope": "Phase 7 Task 0 oracle: EV/EBITDA valuation from the context file (CP-1C T1C.9-T1C.11, CP-4C multiple binding)",
    "status": "prepared; not reviewed; not frozen; not pinned (cases/PINS.json and cases/pins.py PATTERNS are changed at the freeze step)",
    "raw_rule": "contexts are the literal bytes the form writes (json indent 2, LF, trailing LF, ensure_ascii False); the `context` source sha256 is sha256 of those bytes; spans line:N via splitlines",
    "inputs_pinned": PINS,
    "packs": PACKS,
    "contexts": MANIFEST_CONTEXTS,
    "edges": {
        "decision": "Phase 7 Design 11-12: CP-4C gains CP-1C as an optional upstream; the distressed preset gains CP-1C",
        "plan_order_both": PLAN_BOTH,
        "plan_order_cp1c": PLAN_1C,
        "derivation": "registry.plan's layering over methodology.json (required lists asserted at build) with the optional edge CP-4C -> CP-1C added",
    },
    "builder": {"file": "builder/build.py", "sha256": sha((HERE / "build.py").read_bytes()),
                "run": "python3 -I cases/valuation-context-owner/builder/build.py"},
}

files = {f"contexts/{cid}.json": CTX_BYTES[cid] for cid in CASES}
files["expected.json"] = dumps(EXPECTED).encode()
MANIFEST["files_sha256"] = {name: sha(data) for name, data in sorted(files.items())}
MANIFEST["files_sha256_note"] = "every output except manifest.json and README.md (README is hand-written)"
files["manifest.json"] = dumps(MANIFEST).encode()

for name, data in files.items():
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print("wrote", len(files), "files")
