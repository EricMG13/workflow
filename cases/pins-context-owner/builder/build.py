"""Writes cases/pins-context-owner/* (stdlib only; deploy_vii and deploy_workflow are never imported).

Phase 6 Task 0 oracle: pinned assumptions from the context file, for CP-2A, CP-2D, CP-2E, CP-3C, CP-3D
and CP-4C (docs/superpowers/plans/2026-10-31-phase-6-pinned-assumptions.md, Task 0 and the table "What each
pin binds"). Every expected value comes from that plan, the rulings and the FROZEN upstream oracles read here by
sha256 (cases/cp*-owner, cases/snapshot, cases/financial). Nothing is derived from the code the phase builds.

Recomputed cases (CP-2E hedge 60 and 40, CP-4C one multiple) reuse the frozen module builders as an arithmetic
oracle: each builder's source is checked against its pinned sha256, executed with `__name__` set to something
other than "__main__" (so it writes nothing), and its own composer is called on a changed literal. Before use,
each reused composer is run on the base literal and must reproduce the frozen expected.json case exactly.
The cp4c builder carries a stale pin of cases/cp3c-owner/manifest.json (the CP-3C oracle was re-pinned later);
that one hash is replaced in the source text before execution, and the reproduction check above covers it.

Run: python3 -I cases/pins-context-owner/builder/build.py [OUTDIR]   (from the repository root)
Two runs write byte-identical files. OUTDIR defaults to cases/pins-context-owner (a scratch double rebuild
passes another directory and diffs the two).
"""

import copy
import hashlib
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
D = Decimal
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cases" / "pins-context-owner"

# --------------------------------------------------------------------------------------------------
# 0. pinned inputs
# --------------------------------------------------------------------------------------------------
PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/cp2a-owner/manifest.json": "099bfec94b1a7ab19df98646d528ece0871bb411bf45ce79b0d5250677eb3672",
    "cases/cp2a-owner/submissions.json": "4f10743e9203e2fa6e9795f93c33af46d056e3574a58b85e71948a1a206974a3",
    "cases/cp2a-owner/expected.json": "f6b22e02a196b8c621908f365ebbfacc4e7c5d6425d3cb842a99e164409ee66f",
    "cases/cp2d-owner/manifest.json": "d92861e03dc43b6e92504b10b61fdd2d4a61d243c378e2d3b4bf816b3aed4503",
    "cases/cp2d-owner/submissions.json": "cf0a4a773053f5925e0ab69ec64f0962e75d5e051287a1176ff994c74319946c",
    "cases/cp2d-owner/expected.json": "c60797a22c9700fb3ded9cb5de58d64349bf6672a445a6cbbc9c595bc3a124dc",
    "cases/cp2e-owner/manifest.json": "76b3b31f6a46c1dbe40792bd19fbccdaf5bca67b32777fab6ea5b6bf3977fe21",
    "cases/cp2e-owner/submissions.json": "d0e5915d1148d7a895915b70e7c56d937759f4a6eddc0feff0c5e8e163a7a804",
    "cases/cp2e-owner/expected.json": "08a80e96cf23de2a5acbcc8f24ba2c713a1dc02152e3f5b99417d5ced3871592",
    "cases/cp2e-owner/builder/build.py": "3ceb58a4522aa6e781d28f588d48374a21e3d3456d1ae38563a84e69f3dfb908",
    "cases/cp3c-owner/manifest.json": "23f519682ca8caf7cf32a8357316f11ac945e7f717862293d553e7e3ed95c74b",
    "cases/cp3c-owner/submissions.json": "eff5c4fb64452a8aa40a646f58772e6eb55767ea18db9ff54f2f47183d6e2b11",
    "cases/cp3c-owner/expected.json": "c5089cff7c42f2436f957dbaf441b69064bb62f9244bc62c672687f03fe398e3",
    "cases/cp3d-owner/manifest.json": "6fb18d629c9537b72be986c36f660c456768ed44ec25e98080950041d90fef84",
    "cases/cp3d-owner/submissions.json": "c4437879636ed0fe4a8624c71a640873b2c02df789ff9cd5cd05e3bc72bc0579",
    "cases/cp3d-owner/expected.json": "8e28b859d56ba51c3d299c0e35c584bbded6ed18a258dee44c217ae4f43da039",
    "cases/cp3d-owner/builder/build.py": "912f74399b4f8d3e6905bc5496eff74267a51d6f6bc20e38c97fa4feef18afae",
    "cases/cp4c-owner/manifest.json": "1c133a62f34f8fd5e28f451168820fea3a28f1bf49ce0ef2c835a8dc89110fc5",
    "cases/cp4c-owner/submissions.json": "1f76a1d193e04db56a2917b30a4cdc470be54a259858a2c8712e0e4bf1feea68",
    "cases/cp4c-owner/expected.json": "40c6f382cb280e90353da2f041663c907119bfbe6540b0455ef0edc952a911ed",
    "cases/cp4c-owner/builder/build.py": "4c8b07a43d67aa2386355a42135af2a68800106cb208f804e556dd65a7dd21fc",
    "cases/cp3c-owner/builder/build.py": "e6047564c44f2d70e911d1934be8704b23e1e7359b200d1b40c0e7ef7a0cc314",
}

RAW = {}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_pinned(rel):
    data = (ROOT / rel).read_bytes()
    want = PINS[rel]
    assert sha(data) == want, f"input drift: {rel}: {sha(data)} != {want}"
    RAW[rel] = data
    return data


def jpinned(rel):
    return json.loads(read_pinned(rel))


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def dec(d):
    """Plain, normalised decimal text: no exponent, no trailing zeros; zero is "0"."""
    d = D(d)
    return format(d.normalize(), "f") if d != 0 else "0"


def load_oracle(rel_builder, replace=(), inject=None):
    """Execute a frozen module builder as an arithmetic oracle (it writes nothing: its __main__ guard is off)."""
    data = read_pinned(rel_builder)
    src = data.decode("utf-8")
    for old, new in replace:
        assert src.count(old) == 1, (rel_builder, old)
        src = src.replace(old, new)
    ns = {
        "__name__": "pins_oracle_" + Path(rel_builder).parents[1].name,
        "__file__": str(ROOT / rel_builder),
    }
    ns.update(inject or {})
    exec(compile(src, str(ROOT / rel_builder), "exec"), ns)  # noqa: S102  (a hash-checked frozen oracle builder, see the docstring)
    return ns


FIN = jpinned("cases/financial/manifest.json")
SNAP_S = jpinned("cases/snapshot/submissions.json")
jpinned("cases/snapshot/manifest.json")

BASE = {}
for key in ("cp2a", "cp2d", "cp2e", "cp3c", "cp3d", "cp4c"):
    BASE[key] = {
        "man": jpinned(f"cases/{key}-owner/manifest.json"),
        "sub": jpinned(f"cases/{key}-owner/submissions.json"),
        "exp": jpinned(f"cases/{key}-owner/expected.json"),
    }

AS_OF = FIN["run"]["as_of"]
ISSUER_NAME = FIN["run"]["issuer_name"]
ISSUER_ID = FIN["run"]["issuer_id"]
assert (AS_OF, ISSUER_NAME, ISSUER_ID) == (
    "2026-01-10",
    "Northbridge Synthetic Group",
    "northbridge-synthetic",
)
LIMIT_FIN = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
SYNTH = "Synthetic case; not real issuer qualification"


def allocate_pro_rata(members, paid, total):
    """docs/CP4C-OWNER-LEASE.md (rulings round 8 A-1; expected.json waterfall_rules.recipe): a partly paid pro-rata rank
    allocates `paid` by exact largest remainder at the rank quantum q = 10^(paid.adjusted() - 37), ties to the later class
    in claims order, so the distributions sum to `paid` exactly. Returns {class id: Decimal}."""
    from fractions import Fraction

    q = Fraction(10) ** (paid.adjusted() - 37)
    paid_f, total_f = Fraction(paid), Fraction(total)
    assert (paid_f / q).denominator == 1, (
        "paid is not a multiple of the rank quantum (lease state 14)"
    )
    shares = [Fraction(c["claim"]) * paid_f / total_f / q for c in members]
    units = [s.numerator // s.denominator for s in shares]
    spare = int(paid_f / q) - sum(units)
    by_remainder = sorted(
        range(len(members)), key=lambda i: (shares[i] - units[i], i), reverse=True
    )
    for i in by_remainder[:spare]:
        units[i] += 1
    assert sum(units) == int(paid_f / q)
    exp = paid.adjusted() - 37
    return {c["id"]: D(u).scaleb(exp) for c, u in zip(members, units, strict=True)}


# --------------------------------------------------------------------------------------------------
# 1. the module table (plan "What each pin binds"; pathways from the base manifests)
# --------------------------------------------------------------------------------------------------
MODULES = [
    ("CP-2A", "cp2a", "distressed_restructuring"),
    ("CP-2D", "cp2d", "covenant_refinancing"),
    ("CP-2E", "cp2e", "credit_snapshot"),
    ("CP-3C", "cp3c", "covenant_refinancing"),
    ("CP-3D", "cp3d", "relative_value"),
    ("CP-4C", "cp4c", "distressed_restructuring"),
]
PATHWAY = {key: path for _id, key, path in MODULES}
MODULE_ID = {key: mid for mid, key, _p in MODULES}


def base_run(key):
    man = BASE[key]["man"]
    if key == "cp2a":
        return man["cases"]["positive"]["run"]
    if key in ("cp2d", "cp3c"):
        return man["run"]
    if key in ("cp2e", "cp3d"):
        return man["cases"][0]["run"]
    return man["cases"]["positive"]["run"]


for _k, _p in PATHWAY.items():
    _r = base_run(_k)
    assert _r["pathway"] == _p and _r["as_of"] == AS_OF and _r["case_kind"] == "synthetic", (_k, _r)
    assert (_r["issuer_id"], _r["issuer_name"]) == (ISSUER_ID, ISSUER_NAME)

# --------------------------------------------------------------------------------------------------
# 2. pin values: each is the module's existing positive submission value (plan Task 0, Inputs)
# --------------------------------------------------------------------------------------------------
S2A = BASE["cp2a"]["sub"]["positive"]["downside_pathway"]
S2D = BASE["cp2d"]["sub"]["cp2d"]
S2E = BASE["cp2e"]["sub"]["positive"]
S3C = BASE["cp3c"]["sub"]["cp3c"]
S3D = BASE["cp3d"]["sub"]
S4C_POS = BASE["cp4c"]["sub"]["cases"]["positive"]["restructuring_fulcrum"]
S4C_GAP = BASE["cp4c"]["sub"]["cases"]["gap"]["restructuring_fulcrum"]


def PCT(frac):
    return dec(D(frac) * 100)


PIN_SCENARIOS = [(PCT(s["ebitda_decline"]), PCT(s["interest_increase"])) for s in S2A["scenarios"]]
assert PIN_SCENARIOS == [("20", "0"), ("40", "0"), ("40", "20"), ("100", "0")], PIN_SCENARIOS
PIN_HORIZON = str(S2D["positive"]["horizon_months"])
PIN_MINCASH = dec(S2D["positive"]["minimum_cash"]["amount"])
assert (PIN_HORIZON, PIN_MINCASH) == ("24", "10")
PIN_RATES = list(S2E["rate_shocks_bp"])
PIN_FX = list(S2E["fx_shocks_percent"])
assert (PIN_RATES, PIN_FX) == (["100", "200"], ["10"])
assert (
    S2E["hedge_ratio"] is None and S2E["hedge_absence"] is not None
)  # the base submits hedge_absence
PIN_BPS = str(S3C["positive"]["repricing"]["bps"])
assert PIN_BPS == "400"
PIN_RECOVERY = dec(S3D["positive"]["recovery"]["percent_text"])
assert PIN_RECOVERY == "70"
# the chains read the very submissions the pins come from (so every upstream step of a chain matches its own context file)
assert (
    BASE["cp4c"]["sub"]["upstream_step_literals"]["CP-2A"]["source"]["sha256"]
    == PINS["cases/cp2a-owner/submissions.json"]
)
assert (
    "CP-2D positive"
    in next(c for c in BASE["cp3c"]["man"]["cases"] if c["case_id"] == "positive")["base"]
)
PIN_MULTIPLE = "4"  # no frozen CP-4C submission matches it: the base multiples are 4.0, 3.0, 2.0
assert [v["multiple"] for v in S4C_POS["valuation"]] == ["4.0", "3.0", "2.0"]
assert [v["multiple"] for v in S4C_GAP["valuation"]] == ["4.0", "3.0", "not assessed"]

# --------------------------------------------------------------------------------------------------
# 3. context files (cases/context/primary-full.json layout; the literal bytes the form writes)
# --------------------------------------------------------------------------------------------------


def context_obj(pathway, *, hedge="", drop=None):
    assumptions = {
        "cp2a": {
            "scenarios": [
                {"ebitda_decline_pct": d, "interest_increase_pct": i} for d, i in PIN_SCENARIOS
            ],
            "rationale": "Lender downside and severe cases.",
        },
        "cp2d": {
            "horizon_months": PIN_HORIZON,
            "minimum_cash_m": PIN_MINCASH,
            "rationale": "Treasury policy horizon and cushion.",
        },
        "cp2e": {
            "rate_shocks_bps": list(PIN_RATES),
            "fx_shocks_pct": list(PIN_FX),
            "hedge_ratio_pct": hedge,
            "rationale": "Floating-rate exposure shocks.",
        },
        "cp3c": {"repricing_bps": PIN_BPS, "rationale": "Recent repricings in the sector."},
        "cp3d": {"recovery_pct": PIN_RECOVERY, "rationale": "First-lien recovery convention."},
        "cp4c": {
            "ev_multiple": PIN_MULTIPLE,
            "rationale": "Mid-cycle multiple for the stress waterfall.",
        },
    }
    if drop:
        assumptions[drop] = None
    return {
        "schema": "context/1",
        "run": {
            "run_type": "research",
            "pathway": pathway,
            "case_kind": "synthetic",
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
        "assumptions": assumptions,
        "attachments": {
            "portfolio_workbook": False,
            "prior_case": False,
            "management_bridge": False,
            "legal_documents": "executed",
        },
        "research_questions": [],
    }


CONTEXTS = {}  # file name -> (pathway, object, description)
for _pathway in (
    "distressed_restructuring",
    "covenant_refinancing",
    "credit_snapshot",
    "relative_value",
):
    CONTEXTS[f"context-{_pathway}.json"] = (
        _pathway,
        context_obj(_pathway),
        "all six pins; CP-2E hedge pin blank (a partial pin)",
    )
CONTEXTS["context-credit_snapshot-hedge60.json"] = (
    "credit_snapshot",
    context_obj("credit_snapshot", hedge="60"),
    "all six pins; CP-2E hedge pin 60",
)
for _id, _key, _pathway in MODULES:
    CONTEXTS[f"context-{_pathway}-no-{_key}.json"] = (
        _pathway,
        context_obj(_pathway, drop=_key),
        f"all pins except {_key} (null): context present, module pin null",
    )

CTX_BYTES = {name: dumps(obj).encode("utf-8") for name, (_p, obj, _d) in CONTEXTS.items()}
CTX_SHA = {name: sha(b) for name, b in CTX_BYTES.items()}
CTX_LINES = {name: b.decode("utf-8").splitlines() for name, b in CTX_BYTES.items()}


def key_line(name, key):
    hits = [i for i, line in enumerate(CTX_LINES[name], 1) if line.lstrip().startswith(f'"{key}":')]
    assert len(hits) == 1, (name, key, hits)
    return hits[0]


def ctx_for(key, kind="all"):
    """The context file a module's case runs under."""
    pathway = PATHWAY[key]
    if kind == "no_pin":
        return f"context-{pathway}-no-{key}.json"
    if kind == "hedge60":
        assert key == "cp2e"
        return "context-credit_snapshot-hedge60.json"
    return f"context-{pathway}.json"


# --------------------------------------------------------------------------------------------------
# 4. CP-0 and CP-1 assessments of the `context` source (the Phase 2 overlay form, authority unknown)
# --------------------------------------------------------------------------------------------------
CTX_SOURCE_NAME = "context.json"
CTX_LIMIT = (
    "User-supplied run context: its names, periods and figures are the user's statements; "
    "CP-0 classifies its authority as unknown and does not verify them against issuer sources."
)


def cite(name):
    return {
        "source_id": "context",
        "source_sha256": CTX_SHA[name],
        "locator": f"line:{key_line(name, 'issuer_name')}",
        "quote": f'"issuer_name": "{ISSUER_NAME}",',
    }


def overlay(name):
    c = cite(name)
    return {
        "cp0_readiness_source": {
            "source_id": "context",
            "document_family": "User-supplied run context",
            "authority": "unknown",
            "entity": ISSUER_NAME,
            "period": AS_OF,
            "version_relationship": "User-supplied form download for this run",
            "fidelity": "verified",
            "citations": [c],
            "limitations": [CTX_LIMIT],
        },
        "cp1_source_context_source": {
            "source_id": "context",
            "classification": "nonfinancial",
            "document_type": "User-supplied run context",
            "published_on": AS_OF,
            "evidence_class": "internal",
            "evidence_rationale": "User-supplied settings and names; authority unknown (D2)",
            "analytical_use": "Run settings and user-stated names",
            "citations": [c],
            "event_scan": "unassessed",
            "event_scan_explanation": "A user-supplied run context is not event evidence",
        },
    }


def cp0_context_facts(name):
    """The CP-0 facts for the `context` source, in readiness.build_readiness order (P3, P5, T2, T3, T6)."""
    c = cite(name)
    cites = [["context", c["locator"]]]
    return [
        {"fact_id": "P3.context.family", "text": "User-supplied run context", "cites": cites},
        {"fact_id": "P3.context.entity", "text": ISSUER_NAME, "cites": cites},
        {"fact_id": "P3.context.period", "text": AS_OF, "cites": cites},
        {
            "fact_id": "P3.context.version_relationship",
            "text": "User-supplied form download for this run",
            "cites": cites,
        },
        {
            "fact_id": "P5.context.preparation",
            "text": "complete; fidelity verified; No mechanical limitation",
            "cites": [],
        },
        {
            "fact_id": "T2.context.source",
            "text": f"{CTX_SOURCE_NAME}; ready; SHA-256 {CTX_SHA[name]}",
            "cites": [],
        },
        {"fact_id": "T3.context.authority", "text": "unknown", "cites": cites},
        {"fact_id": "T6.context.evidence_0", "text": c["quote"], "cites": cites},
    ]


def table_of(tables, table_id):
    return next(t for t in tables if t["table_id"] == table_id)


def dedupe(items):
    return list(dict.fromkeys(items))


def cp0_limitations(pack_limits, review, *, with_context):
    """readiness.build_readiness limitation order: source limitations, source assessments, consumers, gaps,
    unconfirmed issuer, synthetic case. Dedupe keeps the first occurrence."""
    sources = [*review["sources"]]
    if with_context:
        sources.append({"limitations": [CTX_LIMIT]})
    out = list(pack_limits)
    out += [t for s in sources for t in s["limitations"]]
    out += [t for c in review["consumers"] for t in c["limitations"]]
    out += [g["description"] for g in review["gaps"]]
    if not review["issuer_confirmed"]:
        out.append("Issuer identity is unconfirmed")
    out.append(SYNTH)
    return dedupe(out)


def snapshot_review(*extra_consumers):
    review = copy.deepcopy(SNAP_S["positive"]["readiness_review"])
    review["consumers"] = [*review["consumers"], *copy.deepcopy(list(extra_consumers))]
    return review


def chain_review(key, case="positive"):
    """(pack-source limitations, the CP-0 review literal the chain uses) for a module's base case."""
    if key == "cp2a":
        # the financial-workflow pack (identity + financial); its review literal is built in tests, not frozen:
        # the limitation order is the only thing used here
        review = {
            "sources": [{"limitations": []}, {"limitations": [LIMIT_FIN]}],
            "consumers": [{"limitations": [LIMIT_FIN]}],
            "gaps": [],
            "issuer_confirmed": True,
        }
        return [LIMIT_FIN], review
    if key == "cp2d":
        return [LIMIT_FIN], snapshot_review(BASE["cp2d"]["sub"]["cp0_consumer_delta"])
    if key == "cp3c":
        return [LIMIT_FIN], snapshot_review(*BASE["cp3c"]["sub"]["cp0_consumer_deltas"])
    if key == "cp3d":
        return [LIMIT_FIN], BASE[key]["sub"]["readiness_review"]["positive"]
    if key == "cp2e":
        return [], BASE[key]["sub"]["readiness_review"][
            "positive"
        ]  # the CP-2E pack's financial source carries no limitation
    review = BASE["cp4c"]["sub"]["cases"][case]["cp0_readiness_review"]
    legal = next(s for s in review["sources"] if s["source_id"] == "legal-covenants")
    return [
        legal["limitations"][0]
    ], review  # the legal-covenants pack source carries it as its own limitation


def cp0_block(key, name, case="positive"):
    pack_limits, review = chain_review(key, case)
    before = cp0_limitations(pack_limits, review, with_context=False)
    after = cp0_limitations(pack_limits, review, with_context=True)
    return {
        "added_facts": cp0_context_facts(name),
        "added_facts_position": "after the last T6.<previous source>.evidence_* fact and before the first T4.* fact "
        "(readiness.build_readiness walks pack.sources in order and the context source is last)",
        "limitations_before": before,
        "limitations_after": after,
        "limitation_added": CTX_LIMIT,
        "limitation_position": "after every limitation contributed by the source assessments already in the review "
        "and before the consumers' own limitations that are new to the list",
    }


# self-check of the limitation emulation against the frozen CP-0 lists
for _key in ("cp2e", "cp3d"):
    _frozen = BASE[_key]["exp"]["cp0"]["positive"]["limitations"]
    _pl, _rv = chain_review(_key)
    assert cp0_limitations(_pl, _rv, with_context=False) == _frozen, (_key, _frozen)
assert cp0_limitations(*chain_review("cp2d"), with_context=False) == [LIMIT_FIN, SYNTH]
assert cp0_limitations(*chain_review("cp3c"), with_context=False) == [LIMIT_FIN, SYNTH]

# --------------------------------------------------------------------------------------------------
# 5. issue wording (plan Task 2 `mismatch`) and the pinned sentences (`pinned_line`)
# --------------------------------------------------------------------------------------------------


def mm(path, pin, submitted, at=""):
    where = f"{path} ({at})" if at else path
    return f"{where}: pinned {pin}; submitted {'absence' if submitted is None else submitted}"


def fmt_list(items):
    return ", ".join(items)


PINNED_LINE = {
    "CP-2A": "Scenario shock sizes are user-supplied assumptions pinned in the context file; the submission equals the pins.",
    "CP-2D": "The horizon and minimum cash are user-supplied assumptions pinned in the context file; the submission equals the pins.",
    "CP-2E": "The shock sizes are user-supplied assumptions pinned in the context file; the submission equals the pins.",
    "CP-2E+hedge": "The shock sizes and hedge ratio are user-supplied assumptions pinned in the context file; the submission equals the pins.",
    "CP-3C": "The margin step-up is a user-supplied assumption pinned in the context file; the submission equals the pin.",
    "CP-3D": "The recovery rate is a user-supplied assumption pinned in the context file; the submission equals the pin.",
    "CP-4C": "The EV multiple is a user-supplied assumption pinned in the context file; the submission equals the pin.",
}
LEDGER_LABEL = "Pinned assumptions"
LEDGER_KIND = "Limitation"

# --------------------------------------------------------------------------------------------------
# 6. payload helpers
# --------------------------------------------------------------------------------------------------


def edit(payload, *changes):
    """A deep copy of payload with (path-tuple, value) changes; every change must alter its target."""
    out = copy.deepcopy(payload)
    for path, value in changes:
        node = out
        for step in path[:-1]:
            node = node[step]
        assert node[path[-1]] != value, ("edit changes nothing", path)
        node[path[-1]] = value
    assert out != payload
    return out


def case_entry(key, kind, payload, *, base_case, edit_note):
    return {
        "context": ctx_for(key, kind),
        "base_case": base_case,
        "edit": edit_note,
        "payload": payload,
    }


def ref(key, name):
    return f"submissions.json#/modules/{MODULE_ID[key]}/cases/{name}"


def base_ref(key, case="positive"):
    return {
        "file": f"cases/{key}-owner/expected.json",
        "sha256": PINS[f"cases/{key}-owner/expected.json"],
        "case": case,
    }


SUBMISSIONS = {"modules": {}}
EXPECTED_MODULES = {}


def accepted(**kw):
    return {"outcome": "accepted", "issues": [], **kw}


def refused(issues, **kw):
    return {"outcome": "refused", "issues": issues, **kw}


ORDER_NOTE = (
    "issues = the module's own content issues (the frozen oracle's checker; none unless stated), then the pin lines "
    "in context order (assumption slice field order; scenarios and valuation cases by index), as plan Task 2 and "
    "Tasks 3-8 fix"
)

# ==================================================================================================
# CP-2A
# ==================================================================================================
BASE_PERIOD_ISSUE = "base_period: not an offered period: LTM Q4 24: 2024-01-01 to 2024-12-31"


def p2a_sub(scenarios):
    return {**S2A, "scenarios": scenarios}


def lines_2a(scenarios):
    """Pin lines of a CP-2A submission (scenarios as typed), by plan Task 3 wording."""
    out = []
    if len(scenarios) != len(PIN_SCENARIOS):
        out.append(
            mm("assumptions.cp2a.scenarios", f"{len(PIN_SCENARIOS)} scenarios", str(len(scenarios)))
        )
        return out
    for i, ((pd, pi), s) in enumerate(zip(PIN_SCENARIOS, scenarios, strict=True)):
        for field, pct, typed in (
            ("ebitda_decline_pct", pd, s["ebitda_decline"]),
            ("interest_increase_pct", pi, s["interest_increase"]),
        ):
            frac = dec(D(pct) / 100)
            if D(typed) != D(frac):
                out.append(
                    mm(f"assumptions.cp2a.scenarios[{i}].{field}", f"{frac} ({pct}%)", typed)
                )
    return out


def build_2a():
    key = "cp2a"
    base = S2A
    sc = base["scenarios"]
    # match: every number respelled with trailing zeros up to the four places DECLINE_PATTERN allows
    spelled = [
        {
            **s,
            "ebitda_decline": {"0.20": "0.2000", "0.40": "0.4000", "1.00": "1.0000"}[
                s["ebitda_decline"]
            ],
            "interest_increase": {"0": "0.0000", "0.20": "0.2000"}[s["interest_increase"]],
        }
        for s in sc
    ]
    assert [D(s["ebitda_decline"]) for s in spelled] == [D(s["ebitda_decline"]) for s in sc]
    cases = {
        "match": case_entry(
            key,
            "all",
            p2a_sub(spelled),
            base_case="positive",
            edit_note="every scenario number respelled with trailing zeros (0.2000, 0.0000, 1.0000 ...)",
        ),
        "differs": case_entry(
            key,
            "all",
            edit(base, (("scenarios", 0, "ebitda_decline"), "0.21")),
            base_case="positive",
            edit_note="scenarios[0].ebitda_decline 0.20 -> 0.21",
        ),
        "differs_interest": case_entry(
            key,
            "all",
            edit(base, (("scenarios", 2, "interest_increase"), "0.21")),
            base_case="positive",
            edit_note="scenarios[2].interest_increase 0.20 -> 0.21",
        ),
        "swapped": case_entry(
            key,
            "all",
            p2a_sub([sc[1], sc[0], sc[2], sc[3]]),
            base_case="positive",
            edit_note="scenarios 1 and 2 (indices 0 and 1) swapped as whole objects",
        ),
        "one_scenario": case_entry(
            key, "all", p2a_sub([sc[0]]), base_case="positive", edit_note="only the first scenario"
        ),
        "content_and_pin": case_entry(
            key,
            "all",
            edit(
                base,
                (("base_period",), "LTM Q4 24: 2024-01-01 to 2024-12-31"),
                (("scenarios", 0, "ebitda_decline"), "0.21"),
            ),
            base_case="positive",
            edit_note="base_period not offered (a validator that returns alone, Decision 1) plus scenarios[0].ebitda_decline 0.21",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(base),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(base),
        },
    }
    SUBMISSIONS["modules"]["CP-2A"] = {
        "payload_path": "cases/cp2a-owner/submissions.json#positive.downside_pathway",
        "cases": cases,
    }
    e = BASE[key]["exp"]["cases"]["positive"]
    own = [*e["own_limitations"], PINNED_LINE["CP-2A"]]
    exp = {
        "base": base_ref(key),
        "pins": {
            "context_path": "assumptions.cp2a.scenarios",
            "pin_values_as_typed": [list(p) for p in PIN_SCENARIOS],
            "fractions": [[dec(D(a) / 100), dec(D(b) / 100)] for a, b in PIN_SCENARIOS],
            "unit_conversion": "percent / 100, exact (2 decimal places in, 4 out)",
        },
        "cases": {
            "match": accepted(
                equals_base={
                    "except": ["own_limitations"],
                    "note": "tables, facts, claims, stress, break points, ranking, FP05 and status equal the base case cell for cell",
                },
                own_limitations=own,
                limitation_rows="none: CP-2A limitations are not table rows (T2B.9 is the gaps ledger, unchanged)",
                pinned_line=PINNED_LINE["CP-2A"],
            ),
            "differs": refused(
                lines_2a(edit(base, (("scenarios", 0, "ebitda_decline"), "0.21"))["scenarios"])
            ),
            "differs_interest": refused(
                lines_2a(edit(base, (("scenarios", 2, "interest_increase"), "0.21"))["scenarios"])
            ),
            "swapped": refused(lines_2a([sc[1], sc[0], sc[2], sc[3]])),
            "one_scenario": refused(lines_2a([sc[0]])),
            "content_and_pin": refused(
                [
                    BASE_PERIOD_ISSUE,
                    *lines_2a(
                        edit(base, (("scenarios", 0, "ebitda_decline"), "0.21"))["scenarios"]
                    ),
                ]
            ),
            "no_pin": accepted(
                equals_base={
                    "except": [],
                    "note": "the base positive case unchanged, no pinned line",
                }
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "the frozen CP-2A view of the settled CP-1 head (cases/cp2a-owner/expected.json cases.positive.cp1_inputs)",
        },
        "prompt_submission_form": {
            "scenarios": [
                {"ebitda_decline": dec(D(a) / 100), "interest_increase": dec(D(b) / 100)}
                for a, b in PIN_SCENARIOS
            ]
        },
    }
    # guards on the diff: the swapped/one_scenario/differs lines are the ones plan Task 3 RED states
    assert exp["cases"]["differs"]["issues"] == [
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct: pinned 0.2 (20%); submitted 0.21"
    ]
    assert exp["cases"]["one_scenario"]["issues"] == [
        "assumptions.cp2a.scenarios: pinned 4 scenarios; submitted 1"
    ]
    assert len(exp["cases"]["swapped"]["issues"]) == 2
    assert exp["cases"]["match"]["outcome"] == "accepted" and lines_2a(spelled) == []
    EXPECTED_MODULES["CP-2A"] = exp


# ==================================================================================================
# CP-2D
# ==================================================================================================
def ledger_rows_added(rows_before, table_id, fact_prefix=None):
    n = rows_before + 1
    row_id = f"r{n:02d}"
    return {
        "table_id": table_id,
        "row_id": row_id,
        "fact_id": f"{table_id}.{row_id}",
        "label": LEDGER_LABEL,
        "kind": LEDGER_KIND,
        "position": "appended last (after every existing row; no existing row or fact id moves)",
    }


def build_2d():
    key = "cp2d"
    pos = S2D["positive"]
    gap = S2D["gap_minimum_cash"]
    cases = {
        "match": case_entry(
            key,
            "all",
            edit(pos, (("minimum_cash", "amount"), "10.0")),
            base_case="positive",
            edit_note="minimum_cash.amount 10 -> 10.0 (horizon stays the JSON integer 24: Contract is strict)",
        ),
        "differs": case_entry(
            key,
            "all",
            edit(pos, (("horizon_months",), 25)),
            base_case="positive",
            edit_note="horizon_months 24 -> 25",
        ),
        "differs_minimum_cash": case_entry(
            key,
            "all",
            edit(pos, (("minimum_cash", "amount"), "10.01")),
            base_case="positive",
            edit_note="minimum_cash.amount 10 -> 10.01",
        ),
        "differs_both": case_entry(
            key,
            "all",
            edit(pos, (("horizon_months",), 25), (("minimum_cash", "amount"), "10.01")),
            base_case="positive",
            edit_note="horizon 25 and minimum cash 10.01",
        ),
        "absence": case_entry(
            key,
            "all",
            copy.deepcopy(gap),
            base_case="gap_minimum_cash",
            edit_note="the base gap_minimum_cash payload: minimum_cash null, minimum_cash_absence set",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(pos),
        },
    }
    SUBMISSIONS["modules"]["CP-2D"] = {
        "payload_path": "cases/cp2d-owner/submissions.json#cp2d.<base_case>",
        "cases": cases,
    }
    e = BASE[key]["exp"]["cases"]["positive"]
    t7 = e["T2E.7_rows"]
    assert len(t7) == len(e["own_limitations"]) == 3
    added = ledger_rows_added(len(t7), "T2E.7")
    own = [*e["own_limitations"], PINNED_LINE["CP-2D"]]
    pin_h = "assumptions.cp2d.horizon_months"
    pin_m = "assumptions.cp2d.minimum_cash_m"
    exp = {
        "base": base_ref(key),
        "pins": {
            "horizon_months": PIN_HORIZON,
            "minimum_cash_m": PIN_MINCASH,
            "unit_conversion": "none (minimum cash is the reporting-currency amount in millions, as the submission)",
        },
        "cases": {
            "match": accepted(
                equals_base={
                    "except": ["own_limitations", "T2E.7_rows"],
                    "note": "tables T2E.1-T2E.5, T2E.6_rows, claims and status equal the base case",
                },
                own_limitations=own,
                limitation_rows={
                    **added,
                    "T2E.7_rows_after": [*t7, [LEDGER_LABEL, LEDGER_KIND]],
                    "text": PINNED_LINE["CP-2D"],
                },
                pinned_line=PINNED_LINE["CP-2D"],
            ),
            "differs": refused([mm(pin_h, PIN_HORIZON, "25")]),
            "differs_minimum_cash": refused([mm(pin_m, PIN_MINCASH, "10.01")]),
            "differs_both": refused(
                [mm(pin_h, PIN_HORIZON, "25"), mm(pin_m, PIN_MINCASH, "10.01")]
            ),
            "absence": refused([mm(pin_m, PIN_MINCASH, None)], base_case="gap_minimum_cash"),
            "no_pin": accepted(
                equals_base={
                    "except": [],
                    "note": "the base positive case unchanged, no pinned line",
                }
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "cases/cp2d-owner/manifest.json#view_tree_draft (a pin is not an input)",
        },
        "prompt_submission_form": {
            "horizon_months": PIN_HORIZON,
            "minimum_cash.amount": PIN_MINCASH,
        },
    }
    EXPECTED_MODULES["CP-2D"] = exp


# ==================================================================================================
# CP-3C
# ==================================================================================================
def build_3c():
    key = "cp3c"
    ns = load_oracle("cases/cp3c-owner/builder/build.py")
    pos = S3C["positive"]
    gap = S3C["gap_no_repricing"]
    cases = {
        "match": case_entry(
            key,
            "all",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload: repricing.bps is the JSON integer 400 (no other spelling exists)",
        ),
        "differs": case_entry(
            key,
            "all",
            edit(pos, (("repricing", "bps"), 401)),
            base_case="positive",
            edit_note="repricing.bps 400 -> 401",
        ),
        "absence": case_entry(
            key,
            "all",
            copy.deepcopy(gap),
            base_case="gap_no_repricing",
            edit_note="the base gap_no_repricing payload: repricing null, repricing_absence set",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(pos),
        },
    }
    for name in ("match", "differs", "absence", "no_pin"):
        assert ns["check_payload"](cases[name]["payload"]) == [], (
            name
        )  # the frozen oracle's content rules
    SUBMISSIONS["modules"]["CP-3C"] = {
        "payload_path": "cases/cp3c-owner/submissions.json#cp3c.<base_case>",
        "cases": cases,
    }
    e = BASE[key]["exp"]["cases"]["positive"]
    t8 = e["T3D.8_rows"]
    assert len(t8) == 13 and len(e["own_limitations"]) == 13
    added = ledger_rows_added(len(t8), "T3D.8")
    own = [*e["own_limitations"], PINNED_LINE["CP-3C"]]
    pth = "assumptions.cp3c.repricing_bps"
    exp = {
        "base": base_ref(key),
        "pins": {"repricing_bps": PIN_BPS, "unit_conversion": "none"},
        "cases": {
            "match": accepted(
                equals_base={
                    "except": ["own_limitations", "T3D.8_rows"],
                    "note": "tables T3D.1-T3D.6, T3D.7_rows (the step-up row still reads `400 bp (analyst assumption)`), "
                    "T3D.9_rows, claims and status equal the base case",
                },
                own_limitations=own,
                limitation_rows={
                    **added,
                    "T3D.8_rows_after": [*t8, [LEDGER_LABEL, LEDGER_KIND]],
                    "text": PINNED_LINE["CP-3C"],
                },
                pinned_line=PINNED_LINE["CP-3C"],
            ),
            "differs": refused([mm(pth, PIN_BPS, "401")]),
            "absence": refused([mm(pth, PIN_BPS, None)], base_case="gap_no_repricing"),
            "no_pin": accepted(
                equals_base={
                    "except": [],
                    "note": "the base positive case unchanged, no pinned line",
                }
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "cases/cp3c-owner/cp3c-view-tree.json (a pin is not an input)",
        },
        "prompt_submission_form": {"repricing.bps": PIN_BPS},
    }
    EXPECTED_MODULES["CP-3C"] = exp


# ==================================================================================================
# CP-3D
# ==================================================================================================
def build_3d():
    key = "cp3d"
    ns = load_oracle("cases/cp3d-owner/builder/build.py")
    pos = S3D["positive"]
    gap = S3D["gap_no_recovery"]
    pack_ids = ns["PACK_IDS"]["positive"]
    cases = {
        "match": case_entry(
            key,
            "all",
            edit(pos, (("recovery", "percent_text"), "70.00")),
            base_case="positive",
            edit_note="recovery.percent_text 70 -> 70.00",
        ),
        "differs": case_entry(
            key,
            "all",
            edit(pos, (("recovery", "percent_text"), "70.01")),
            base_case="positive",
            edit_note="recovery.percent_text 70 -> 70.01",
        ),
        "absence": case_entry(
            key,
            "all",
            copy.deepcopy(gap),
            base_case="gap_no_recovery",
            edit_note="the base gap_no_recovery payload: recovery null, recovery_absence set",
        ),
        "non_numeric": case_entry(
            key,
            "all",
            edit(pos, (("recovery", "percent_text"), "x")),
            base_case="positive",
            edit_note="recovery.percent_text 70 -> x",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(pos),
        },
    }
    content = {n: ns["check_submission"](cases[n]["payload"], pack_ids) for n in cases}
    for n in ("match", "differs", "absence", "no_pin"):
        assert content[n] == [], (n, content[n])
    assert content["non_numeric"] == ["recovery: percent must be at least 0 and below 100"], (
        content["non_numeric"]
    )
    SUBMISSIONS["modules"]["CP-3D"] = {
        "payload_path": "cases/cp3d-owner/submissions.json#<base_case>",
        "cases": cases,
    }
    e = BASE[key]["exp"]["cases"]["positive"]
    tbl = copy.deepcopy(table_of(e["tables"], "T3E.9"))
    n0 = len(tbl["rows"])
    assert n0 == 11 == len(e["own_limitations"])
    new_row = copy.deepcopy(tbl["rows"][-1])
    new_row["row_id"] = f"r{n0 + 1:02d}"
    new_row["label"] = f"Limitation {n0 + 1}"
    new_row["facts"][0]["fact_id"] = f"T3E.9.{new_row['row_id']}.text"
    new_row["facts"][0]["text"] = PINNED_LINE["CP-3D"]
    new_row["facts"][0]["shown"] = PINNED_LINE["CP-3D"]
    tbl["rows"].append(new_row)
    cp0_new = cp0_block(key, ctx_for(key, "all"))["limitations_after"]
    own = [*e["own_limitations"], PINNED_LINE["CP-3D"]]
    pth = "assumptions.cp3d.recovery_pct"
    exp = {
        "base": base_ref(key),
        "pins": {"recovery_pct": PIN_RECOVERY, "unit_conversion": "none"},
        "cases": {
            "match": accepted(
                equals_base={
                    "except": ["own_limitations", "tables[T3E.9]", "inherited_limitations"]
                },
                own_limitations=own,
                tables_changed={"T3E.9": tbl},
                limitation_rows={
                    "table_id": "T3E.9",
                    "row_id": new_row["row_id"],
                    "fact_id": new_row["facts"][0]["fact_id"],
                    "label": new_row["label"],
                    "text": PINNED_LINE["CP-3D"],
                    "position": "appended last; no existing row or fact id moves",
                },
                inherited_limitations=[t for t in cp0_new if t not in own],
                pinned_line=PINNED_LINE["CP-3D"],
            ),
            "differs": refused([mm(pth, PIN_RECOVERY, "70.01")]),
            "absence": refused([mm(pth, PIN_RECOVERY, None)], base_case="gap_no_recovery"),
            "non_numeric": refused(
                [*content["non_numeric"], mm(pth, PIN_RECOVERY, "x")],
                note="the content issue first, then the pin mismatch as typed; no exception",
            ),
            "no_pin": accepted(
                equals_base={
                    "except": ["inherited_limitations"],
                    "note": "no pinned line; inherited_limitations gain the CP-0 context limitation (cp0)",
                },
                inherited_limitations=[t for t in cp0_new if t not in e["own_limitations"]],
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "none: CP-3D has no read_inputs view (cases/cp3d-owner/expected.json tool_use_required.read_inputs_calls = 0)",
        },
        "prompt_submission_form": {"recovery.percent_text": PIN_RECOVERY},
    }
    EXPECTED_MODULES["CP-3D"] = exp


# ==================================================================================================
# CP-2E
# ==================================================================================================
def build_2e():
    key = "cp2e"
    ns = load_oracle("cases/cp2e-owner/builder/build.py")
    pos = S2E
    pages = ns["PAGES_OF"]["positive"]
    HEDGE_RATIONALE = "Assumed share of the floating debt that is hedged"
    HEDGE_ASSESS = {
        "section": "hedging",
        "category": "Analyst Interpretation",
        "text": "The share of the floating-rate debt that is hedged is an assumption, not a source statement, so the "
        "effect of each shock after hedges rests on it and is shown beside the effect before hedges.",
        "basis": [],
        "limitation": None,
    }

    def hedged(pct):
        s = copy.deepcopy(pos)
        s["hedge_ratio"] = {"percent_text": pct, "rationale": HEDGE_RATIONALE}
        s["hedge_absence"] = None
        s["assessments"] = [
            HEDGE_ASSESS if a["section"] == "hedging" else a for a in s["assessments"]
        ]
        return s

    cases = {
        "match": case_entry(
            key,
            "all",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload (hedge_absence set; shocks are whole numbers, so no other spelling exists)",
        ),
        "hedge60": case_entry(
            key,
            "hedge60",
            hedged("60.00"),
            base_case="positive",
            edit_note="hedge_ratio 60.00 (percent_text) replaces hedge_absence; the hedging assessment becomes an Analyst Interpretation",
        ),
        "differs": case_entry(
            key,
            "all",
            edit(pos, (("rate_shocks_bp",), ["101", "200"])),
            base_case="positive",
            edit_note="rate_shocks_bp [100, 200] -> [101, 200]",
        ),
        "differs_fx": case_entry(
            key,
            "all",
            edit(pos, (("fx_shocks_percent",), ["11"])),
            base_case="positive",
            edit_note="fx_shocks_percent [10] -> [11]",
        ),
        "differs_hedge": case_entry(
            key,
            "hedge60",
            hedged("61"),
            base_case="positive",
            edit_note="hedge_ratio 61 under the hedge-60 context",
        ),
        "absence_hedge": case_entry(
            key,
            "hedge60",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload (hedge_absence) under the hedge-60 context",
        ),
        "count_order_swapped": case_entry(
            key,
            "all",
            edit(pos, (("rate_shocks_bp",), ["200", "100"])),
            base_case="positive",
            edit_note="rate_shocks_bp [200, 100]",
        ),
        "count_order_one_shock": case_entry(
            key,
            "all",
            edit(pos, (("rate_shocks_bp",), ["100"])),
            base_case="positive",
            edit_note="rate_shocks_bp [100] only",
        ),
        "count_order_fx_two": case_entry(
            key,
            "all",
            edit(pos, (("fx_shocks_percent",), ["10", "20"])),
            base_case="positive",
            edit_note="fx_shocks_percent [10, 20]",
        ),
        "blank_hedge_value": case_entry(
            key,
            "all",
            hedged("40"),
            base_case="positive",
            edit_note="hedge_ratio 40 under the base context (hedge pin blank)",
        ),
        "non_numeric": case_entry(
            key,
            "all",
            edit(pos, (("rate_shocks_bp",), ["abc"])),
            base_case="positive",
            edit_note="rate_shocks_bp [abc]",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(pos),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(pos),
        },
    }
    content = {n: ns["check_submission"](c["payload"], pages) for n, c in cases.items()}
    for n in (
        "match",
        "hedge60",
        "differs",
        "differs_fx",
        "differs_hedge",
        "absence_hedge",
        "count_order_one_shock",
        "count_order_fx_two",
        "blank_hedge_value",
        "no_pin",
    ):
        assert content[n] == [], (n, content[n])
    assert content["count_order_swapped"] == [
        "rate_shocks_bp: shocks must be strictly increasing"
    ], content["count_order_swapped"]
    assert len(content["non_numeric"]) == 1 and content["non_numeric"][0].startswith(
        "rate_shocks_bp[0]: shock must be a whole number"
    ), content["non_numeric"]
    SUBMISSIONS["modules"]["CP-2E"] = {
        "payload_path": "cases/cp2e-owner/submissions.json#positive",
        "cases": cases,
    }

    # --- recomputed cases: reuse the frozen composer; reproduce the frozen positive case first ---------
    frozen_pos = BASE[key]["exp"]["cases"]["positive"]

    def assemble(sub, name):
        d = ns["derive"](ns["inputs_of"](sub))
        tables, claims, own = ns["compose_case"]("positive", sub, d)
        by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
        scan = []
        for cl in claims:
            iss, literal = ns["claim_issues"](cl, by_id)
            assert not iss, (name, cl["claim_id"], iss)
            scan.append({"claim_id": cl["claim_id"], "literal_text_outside_references": literal})
            for r in cl["refs"]:
                assert r in by_id
        return {
            "derived": ns["stored_all"](d),
            "missing_not_zero": [f["fact_id"] for f in by_id.values() if f["status"] == "missing"],
            "not_applicable": [
                f["fact_id"] for f in by_id.values() if f["status"] == "not_applicable"
            ],
            "tables": tables,
            "claims": claims,
            "claim_literal_text": scan,
            "own_limitations": own,
            "tool_use_required": {
                "read_pages_cover": [list(p) for p in ns["cited_pages"](sub)],
                "search_pack_min": 1,
                "read_inputs_calls": 0,
            },
        }

    repro = assemble(ns["LITERALS"]["positive"], "positive")
    for k, v in repro.items():
        assert v == frozen_pos[k], f"cp2e composer does not reproduce the frozen positive case: {k}"
    assert ns["LITERALS"]["positive"] == pos

    def with_pin_row(case_dict, line):
        """Add the pinned limitation as the last row of T2F.9 (and of module_tables) and as the last own limitation."""
        c = copy.deepcopy(case_dict)
        c["own_limitations"] = [*c["own_limitations"], line]
        tbl = table_of(c["tables"], "T2F.9")
        n0 = len(tbl["rows"])
        row = copy.deepcopy(tbl["rows"][-1])
        row["row_id"] = f"r{n0 + 1:02d}"
        row["label"] = f"Limitation {n0 + 1}"
        row["facts"][0]["fact_id"] = f"T2F.9.{row['row_id']}.text"
        row["facts"][0]["text"] = line
        row["facts"][0]["shown"] = line
        tbl["rows"].append(row)
        added = {
            "table_id": "T2F.9",
            "row_id": row["row_id"],
            "fact_id": row["facts"][0]["fact_id"],
            "label": row["label"],
            "text": line,
            "position": "appended last; no existing row or fact id moves",
        }
        return c, added

    cp0_ctx_name = ctx_for(key, "all")
    cp0_new = cp0_block(key, cp0_ctx_name)["limitations_after"]

    def full_case(sub, name, line, ctx_kind):
        base = assemble(sub, name)
        c, added = with_pin_row(base, line)
        c["module_tables"] = [
            {
                "table_id": t["table_id"],
                "title": t["title"],
                "row_header": t["row_header"],
                "columns": t["columns"],
                "rows": [
                    {
                        "row_id": r["row_id"],
                        "label": r["label"],
                        "fact_ids": [f["fact_id"] for f in r["facts"]],
                    }
                    for r in t["rows"]
                ],
            }
            for t in c["tables"]
        ]
        cpn = cp0_block(key, ctx_for(key, ctx_kind))["limitations_after"]
        c["inherited_limitations"] = [t for t in cpn if t not in c["own_limitations"]]
        c["limitation_rows"] = added
        c["pinned_line"] = line
        return c

    # match on the base positive: delta against the frozen case
    match_case, match_added = with_pin_row(frozen_pos, PINNED_LINE["CP-2E"])
    own_match = match_case["own_limitations"]
    inherited_match = [t for t in cp0_new if t not in own_match]
    mt = next(
        {
            "table_id": t["table_id"],
            "title": t["title"],
            "row_header": t["row_header"],
            "columns": t["columns"],
            "rows": [
                {
                    "row_id": r["row_id"],
                    "label": r["label"],
                    "fact_ids": [f["fact_id"] for f in r["facts"]],
                }
                for r in t["rows"]
            ],
        }
        for t in match_case["tables"]
        if t["table_id"] == "T2F.9"
    )
    assert mt == table_of(frozen_pos["module_tables"], "T2F.9") | {"rows": mt["rows"]}

    hedge60 = full_case(hedged("60.00"), "hedge60", PINNED_LINE["CP-2E+hedge"], "hedge60")
    hedge40 = full_case(hedged("40"), "hedge40", PINNED_LINE["CP-2E"], "all")
    assert hedged("60.00") != pos
    # spelling check: 60.00 and 60 give identical cells
    a60, b60 = assemble(hedged("60.00"), "a"), assemble(hedged("60"), "b")
    assert a60 == b60, "the hedge spelling changed a cell"

    pth_r, pth_f, pth_h = (
        "assumptions.cp2e.rate_shocks_bps",
        "assumptions.cp2e.fx_shocks_pct",
        "assumptions.cp2e.hedge_ratio_pct",
    )
    exp = {
        "base": base_ref(key),
        "pins": {
            "rate_shocks_bps": PIN_RATES,
            "fx_shocks_pct": PIN_FX,
            "hedge_ratio_pct": "(blank in the base context; 60 in the hedge-60 context)",
            "unit_conversion": "none (hedge percent compared as Decimal)",
        },
        "cases": {
            "match": accepted(
                equals_base={
                    "except": [
                        "own_limitations",
                        "tables[T2F.9]",
                        "module_tables[T2F.9]",
                        "inherited_limitations",
                    ]
                },
                own_limitations=own_match,
                tables_changed={"T2F.9": table_of(match_case["tables"], "T2F.9")},
                module_tables_changed={"T2F.9": mt},
                limitation_rows=match_added,
                inherited_limitations=inherited_match,
                pinned_line=PINNED_LINE["CP-2E"],
                hedge_pinned=False,
            ),
            "hedge60": accepted(
                context=ctx_for(key, "hedge60"),
                recomputed_case=hedge60,
                note="builder-recomputed with the frozen CP-2E composer (reproduction of the frozen positive case checked); "
                "the hedge ratio is 60 percent, spelled 60.00 in the payload (identical cells to 60)",
                hedge_pinned=True,
            ),
            "differs": refused([mm(pth_r, fmt_list(PIN_RATES), "101, 200")]),
            "differs_fx": refused([mm(pth_f, fmt_list(PIN_FX), "11")]),
            "differs_hedge": refused([mm(pth_h, "60", "61")], context=ctx_for(key, "hedge60")),
            "absence_hedge": refused([mm(pth_h, "60", None)], context=ctx_for(key, "hedge60")),
            "count_order_swapped": refused(
                [*content["count_order_swapped"], mm(pth_r, fmt_list(PIN_RATES), "200, 100")]
            ),
            "count_order_one_shock": refused([mm(pth_r, fmt_list(PIN_RATES), "100")]),
            "count_order_fx_two": refused([mm(pth_f, fmt_list(PIN_FX), "10, 20")]),
            "blank_hedge": {
                "outcome": "accepted",
                "issues": [],
                "context": ctx_for(key, "all"),
                "payloads": {"value": "blank_hedge_value", "absence": "match"},
                "value_case": hedge40,
                "absence_case": "same as `match` (the base hedge_absence payload)",
                "note": "the context hedge pin is blank, so the hedge binds nothing: hedge 40 and hedge_absence are both accepted and "
                "the sentence names shock sizes only",
                "hedge_pinned": False,
            },
            "non_numeric": refused(
                [*content["non_numeric"], mm(pth_r, fmt_list(PIN_RATES), "abc")],
                note="the content issue first, then the pin mismatch as typed; no exception",
            ),
            "no_pin": accepted(
                equals_base={
                    "except": ["inherited_limitations"],
                    "note": "no pinned line; inherited_limitations gain the CP-0 context limitation (cp0)",
                },
                inherited_limitations=[
                    t for t in cp0_new if t not in frozen_pos["own_limitations"]
                ],
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "none: CP-2E has no read_inputs view (tool_use_required.read_inputs_calls = 0)",
        },
        "prompt_submission_form": {
            "base_context": {"rate_shocks_bp": list(PIN_RATES), "fx_shocks_percent": list(PIN_FX)},
            "hedge60_context": {
                "rate_shocks_bp": list(PIN_RATES),
                "fx_shocks_percent": list(PIN_FX),
                "hedge_ratio.percent_text": "60",
            },
            "note": "a blank hedge pin is left out of the form (a partial pin binds nothing)",
        },
    }
    assert exp["cases"]["differs"]["issues"] == [
        "assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted 101, 200"
    ]
    EXPECTED_MODULES["CP-2E"] = exp


# ==================================================================================================
# CP-4C
# ==================================================================================================
def build_4c():
    key = "cp4c"
    ns = load_oracle(
        "cases/cp4c-owner/builder/build.py",
        replace=(
            (
                "2f65c085e164deb2f52f8de58178130caa6811ace704aaccbd6082b905cbb5ca",
                PINS["cases/cp3c-owner/manifest.json"],
            ),
            # the frozen builder divides each class on its own (the pre-ruling form); the lease (round 8 A-1) allocates a
            # partly paid pro-rata rank by exact largest remainder. The two agree on every frozen case (reproduction check
            # below) and differ in the last digit elsewhere (CP-4C one_multiple), so the ruled recipe is used.
            (
                'dist = div(ex(lambda c=c, paid=paid: c["claim"] * paid), tot)',
                'dist = div(ex(lambda c=c, paid=paid: c["claim"] * paid), tot) if paid == tot else _alloc(mem, paid, tot)[c["id"]]',
            ),
        ),
        inject={"_alloc": allocate_pro_rata},
    )
    frozen = BASE[key]["exp"]["cases"]
    # reproduction check: the (re-pinned) oracle reproduces the frozen cases it will be reused for
    for case in ("positive", "gap"):
        built = ns["build_case"](case)
        for k, v in built.items():
            assert json.dumps(v, sort_keys=True, ensure_ascii=True) == json.dumps(
                frozen[case][k], sort_keys=True, ensure_ascii=True
            ), (case, k)

    base = copy.deepcopy(S4C_POS)
    gap_base = copy.deepcopy(S4C_GAP)
    FUL = {
        (
            "equity",
        ): "Every creditor class is paid in full, so equity is the first class that does not receive a full claim.",
        (
            "c02",
            "c03",
        ): "Value runs out among the unsecured operating creditors, who share equally.",
        ("c01",): "Value runs out at the secured term loan, so it is the fulcrum class.",
    }
    PLAN_TXT = {
        ("equity",): "All creditors are unimpaired and equity keeps the residual.",
        (
            "c02",
            "c03",
        ): "The unsecured creditors take the reorganised equity and the old equity is cancelled.",
        (
            "c01",
        ): "The term loan lenders take the reorganised equity and all junior classes are cancelled.",
    }
    VAL_RAT = {
        "v02": "Downside valuation takes the downside forecast earnings of {{FIG:ebitda_down_fy26|US$ m}} at the multiple stated for this case.",
        "v03": "Stress valuation keeps the downside earnings of {{FIG:ebitda_down_fy26|US$ m}} at the multiple stated for this case.",
    }
    ASSESS_RAT = (
        "Against the term loan of {{FIG:total_debt_ltm|US$ m}}, each valuation case is read through the same waterfall, "
        "and the fulcrum class and plan treatment follow its result."
    )

    def treatment(recovery, residual, cls):
        if cls == "equity":
            return "Equity retained" if D(residual) > 0 else "No recovery"
        r = D(recovery[cls])
        return (
            "Paid in full"
            if r == 1
            else "Receives reorganised equity"
            if 0 < r < 1
            else "No recovery"
        )

    def variant(name, multiples):
        """The base positive payload with these multiples; valuation text, fulcrum and plan follow the oracle's waterfall."""
        sub = copy.deepcopy(base)
        for v, m in zip(sub["valuation"], multiples, strict=True):
            v["multiple"] = m
        ns["SUBMISSION"][name] = sub
        ns["PCASE"][name] = (name, *ns["PCASE"]["positive"][1:])
        wf = ns["build_case"](name)["waterfall"]
        for v in sub["valuation"][1:]:
            v["rationale"] = VAL_RAT[v["case_id"]]
        sub["assessment"]["rationale"] = ASSESS_RAT
        for i, v in enumerate(sub["valuation"]):
            cid = v["case_id"]
            brk = tuple(wf[cid]["break"])
            sub["fulcrum"][i] = {**sub["fulcrum"][i], "class_ids": list(brk), "rationale": FUL[brk]}
            sub["plan"][i] = {
                **sub["plan"][i],
                "treatments": [
                    {
                        "class_id": c,
                        "treatment": treatment(wf[cid]["recovery"], wf[cid]["residual"], c),
                    }
                    for c in ("c01", "c02", "c03", "equity")
                ],
                "rationale": PLAN_TXT[brk],
            }
        built = ns["build_case"](name)
        issues = ns["content_issues"](sub, built["waterfall"], ns["pages_of"]("positive"))
        assert issues == [], (name, issues)
        return sub, built

    one_sub, one_built = variant("one_multiple", ["4.0", "4.0", "4.0"])
    match_sub, match_built = variant("match_spelled", ["4.00", "4.00", "4.00"])
    assert one_built == match_built, "the multiple spelling changed a cell"
    diff_sub, _ = variant("differs", ["4.01", "4.0", "4.0"])
    multi_sub, _ = variant("multi_case", ["4.0", "4.5", "4.0"])
    # the base payloads are valid as frozen
    assert (
        ns["content_issues"](
            base, ns["build_case"]("positive")["waterfall"], ns["pages_of"]("positive")
        )
        == []
    )
    assert (
        ns["content_issues"](gap_base, ns["build_case"]("gap")["waterfall"], ns["pages_of"]("gap"))
        == []
    )
    not_numeric = copy.deepcopy(base)
    not_numeric["valuation"][1]["multiple"] = "abc"

    cases = {
        "match": case_entry(
            key,
            "all",
            match_sub,
            base_case="positive",
            edit_note="every multiple 4.00; valuation text, fulcrum and plan follow the waterfall (see build_4c)",
        ),
        "one_multiple": case_entry(
            key,
            "all",
            one_sub,
            base_case="positive",
            edit_note="every multiple 4.0 (the brief's one_multiple)",
        ),
        "differs": case_entry(
            key, "all", diff_sub, base_case="positive", edit_note="multiples 4.01, 4.0, 4.0"
        ),
        "base_positive": case_entry(
            key,
            "all",
            base,
            base_case="positive",
            edit_note="the base positive payload (4.0, 3.0, 2.0)",
        ),
        "not_assessed": case_entry(
            key,
            "all",
            gap_base,
            base_case="gap",
            edit_note="the base gap payload (4.0, 3.0, not assessed)",
        ),
        "multi_case": case_entry(
            key, "all", multi_sub, base_case="positive", edit_note="multiples 4.0, 4.5, 4.0"
        ),
        "non_numeric": case_entry(
            key,
            "all",
            not_numeric,
            base_case="positive",
            edit_note="valuation[1].multiple 3.0 -> abc",
        ),
        "no_pin": case_entry(
            key,
            "no_pin",
            copy.deepcopy(base),
            base_case="positive",
            edit_note="the base positive payload",
        ),
        "no_context": {
            "context": None,
            "base_case": "positive",
            "edit": "the base positive payload, base pack",
            "payload": copy.deepcopy(base),
        },
    }
    SUBMISSIONS["modules"]["CP-4C"] = {
        "payload_path": "cases/cp4c-owner/submissions.json#cases.<base_case>.restructuring_fulcrum",
        "payload_note": "the payloads of match, one_multiple, differs and multi_case are the base positive payload with the multiples "
        "changed and the valuation text, fulcrum and plan re-derived from the frozen oracle's waterfall so that no content "
        "issue arises; every other field (claims, assessment limitation, gaps) is the base's",
        "cases": cases,
    }
    pth = "assumptions.cp4c.ev_multiple"

    def ln(i, typed):
        return mm(pth, PIN_MULTIPLE, typed, at=f"valuation[{i}].multiple")

    shape_issue = f"valuation.1.multiple: {ns['PATTERN']['mult']}"
    frozen_gap = ns["build_case"]("gap")
    assert [v["multiple"] for v in gap_base["valuation"]] == ["4.0", "3.0", "not assessed"]
    own_one = [*one_built["own_limitations"], PINNED_LINE["CP-4C"]]
    one_case = {**one_built, "own_limitations": own_one, "pinned_line": PINNED_LINE["CP-4C"]}
    exp = {
        "base": base_ref(key),
        "pins": {
            "ev_multiple": PIN_MULTIPLE,
            "unit_conversion": "none",
            "binds": "every valuation case's multiple",
        },
        "cases": {
            "match": accepted(
                payload="match (every multiple 4.00)",
                recomputed_case=one_case,
                note="builder-recomputed with the frozen CP-4C builder (reproduction of the frozen positive and gap cases checked). "
                "The 4.00 spelling gives cells identical to 4.0 (asserted). The extra keys of a frozen case (execution, "
                "plan_order, cp0) are the base positive case's, with the cp0 context additions below. Limitations are not table "
                "rows in CP-4C (T4E.10 is the gaps ledger).",
            ),
            "one_multiple": accepted(payload="one_multiple (every multiple 4.0)", same_as="match"),
            "differs": refused([ln(0, "4.01")]),
            "base_positive": refused(
                [ln(1, "3.0"), ln(2, "2.0")], note="no frozen CP-4C submission matches the pin"
            ),
            "not_assessed": refused(
                [ln(1, "3.0"), ln(2, "not assessed")],
                base_case="gap",
                note="the valuation[1] line keeps dict.fromkeys from merging the two",
            ),
            "multi_case": refused([ln(1, "4.5")]),
            "non_numeric": refused(
                [shape_issue],
                issue_kind="shape",
                note="MULTIPLE_PATTERN refuses 'abc' at shape before any pin check: the shape issue alone",
            ),
            "no_pin": accepted(
                equals_base={
                    "except": [],
                    "note": "the base positive case unchanged, no pinned line",
                }
            ),
            "no_context": accepted(
                equals_base={"except": [], "note": "the base positive case unchanged (base pack)"}
            ),
        },
        "view": {
            "unchanged": True,
            "ref": "cases/cp4c-owner/cp4c-view-tree.json (Phase 6 adds nothing to the CP-4C view)",
        },
        "prompt_submission_form": {"valuation[*].multiple": PIN_MULTIPLE},
    }
    assert exp["cases"]["differs"]["issues"] == [
        "assumptions.cp4c.ev_multiple (valuation[0].multiple): pinned 4; submitted 4.01"
    ]
    EXPECTED_MODULES["CP-4C"] = exp
    assert (
        frozen_gap
    )  # (silences linters: the gap case was rebuilt above as part of the reproduction check)


for builder in (build_2a, build_2d, build_2e, build_3c, build_3d, build_4c):
    builder()

# --------------------------------------------------------------------------------------------------
# 7. CP-0 additions per module and case
# --------------------------------------------------------------------------------------------------
for mid, key, _p in MODULES:
    exp = EXPECTED_MODULES[mid]
    ctx_name = ctx_for(key, "all")
    exp["cp0"] = {
        "applies_to": "every case with a context source (match, differs, absence, count_order, blank_hedge, non_numeric, no_pin); "
        "`no_context` has no context source and no addition",
        "context_file_all": ctx_name,
        "positive_chain": cp0_block(key, ctx_name),
    }
    if key == "cp4c":
        exp["cp0"]["gap_chain"] = cp0_block(key, ctx_name, "gap")
    exp["cp0"]["context_source"] = {
        "source_id": "context",
        "name": CTX_SOURCE_NAME,
        "media_type": "text/plain",
        "extractor": "utf8-lines/1",
        "status": "ready",
        "extraction_status": "complete",
        "limitation": None,
        "sha256": "per context file (manifest.json contexts)",
    }
    upstream = {
        "cp3c": " CP-3C also inherits the pinned line of its upstream CP-2D (its submission equals the pin, so CP-2D emits its own pinned line; execution.py:346-367).",
        "cp4c": " CP-4C also inherits the pinned line of its upstream CP-2A (its submission equals the pin, so CP-2A emits its own pinned line; execution.py:346-367).",
    }.get(key, "")
    exp["inherited_limitations_note"] = (
        "a module's inherited limitations are the CP-0 head limitations (then CP-0's inherited) minus its own, so every context "
        "run gains the CP-0 context limitation there (cp2e and cp3d freeze the list; for cp2a, cp2d, cp3c and cp4c it is bound at "
        "run time and gains the same entry); CP-1's own context rows and limitation come from the Phase 2 oracle "
        "(cases/context-identity-periods) and are not enumerated here."
        + upstream
        + " The lists are bound at run time."
    )

# --------------------------------------------------------------------------------------------------
# 8. manifest
# --------------------------------------------------------------------------------------------------


def pack_sources(key):
    man = BASE[key]["man"]
    out = []
    if key in ("cp2e", "cp3d"):
        for s in man["cases"][0]["pack_sources"]:
            out.append(
                {k: v for k, v in s.items() if k in ("source_id", "name", "sha256", "status")}
            )
    elif key == "cp4c":
        out = [
            {"source_id": "identity", "sha256": man["sources"]["identity"]["sha256"]},
            {"source_id": "financial", "sha256": man["sources"]["financial"]["sha256"]},
            {
                "source_id": "legal-covenants",
                "sha256": man["sources"]["legal-covenants"]["positive"]["sha256"],
                "gap_case_sha256": man["sources"]["legal-covenants"]["gap"]["sha256"],
            },
        ]
    elif key == "cp2a":
        out = [
            {"source_id": s["source_id"], "sha256": s["sha256"]}
            for s in man["financial_baseline"]["sources"]
        ]
    else:
        out = [{"source_id": s["source_id"], "sha256": s["sha256"]} for s in man["sources"]]
    return out


MANIFEST = {
    "schema_version": "pins-context-owner-cases/1",
    "scope": "Phase 6 Task 0: pinned assumptions from the context file, for the owners of CP-2A, CP-2D, CP-2E, CP-3C, CP-3D and CP-4C",
    "status": "PREPARED by the Phase 6 Task 0 preparer; independent mx-precise review pending; not frozen, not pinned "
    "(cases/PINS.json is written at the freeze; the glob cases/*-owner/* will then take manifest.json, submissions.json, "
    "expected.json and builder/build.py; until then `python3 -I cases/pins.py --check` lists them as unpinned)",
    "raw_rule": "context files are the literal bytes the form writes (json indent 2, LF, trailing LF); the `context` source sha256 is the sha256 of "
    "those bytes, spans line:N via splitlines. The context files are outside the PINS.json globs, so their sha256 is embedded here.",
    "inputs_pinned": {k: v for k, v in PINS.items()},
    "no_pack_hash": "no base oracle freezes a PreparedPack.content_hash() (each binds it at run time), so the extra `context` source changes "
    "no frozen hash; the only hashes rebuilt here are the context file sha256 values and their citations",
    "context_source": {
        "source_id": "context",
        "name": CTX_SOURCE_NAME,
        "media_type": "text/plain",
        "position": "last in pack.sources (preparation_request appends it)",
    },
    "contexts": {
        name: {
            "pathway": pathway,
            "sha256": CTX_SHA[name],
            "bytes": len(CTX_BYTES[name]),
            "description": desc,
            "issuer_name_line": key_line(name, "issuer_name"),
        }
        for name, (pathway, _obj, desc) in CONTEXTS.items()
    },
    "modules": {},
}
for mid, key, pathway in MODULES:
    MANIFEST["modules"][mid] = {
        "base_oracle": f"cases/{key}-owner",
        "run": base_run(key),
        "pack": {"base_sources": pack_sources(key), "extra_source": "context (text/plain, last)"},
        "context_all": ctx_for(key, "all"),
        "context_no_pin": ctx_for(key, "no_pin"),
        "context_hedge60": ctx_for(key, "hedge60") if key == "cp2e" else None,
        "chain": "the closed chain of the base oracle's positive case (its upstream literals unchanged) plus the context assessments "
        "in submissions.json context_overlays; the run (run_id, pathway, requested_modules) is the base run's",
        "upstream_pins_checked": (
            "every upstream step of the chain submits a value that equals the pin of the same context file "
            "(CP-4C chain: CP-2A scenarios 20/0, 40/0, 40/20, 100/0; CP-3C chain: CP-2D horizon 24 and minimum cash 10)"
            if key in ("cp3c", "cp4c")
            else "no pinned upstream step"
        ),
    }

SUBMISSIONS["schema_version"] = "pins-context-owner-submissions/1"
SUBMISSIONS["note"] = (
    "Per module and case, the complete module step payload (placeholders such as {{FIG:name|token}} and {{FACT:name}} are the base "
    "oracle's and are bound at run time), the context file it runs under (null: the base pack) and the base case it edits. "
    "context_overlays hold the CP-0 readiness `sources` entry and the CP-1 source_context `sources` entry for the `context` source "
    "(authority unknown), per context file; the chain literals of the base oracles are otherwise unchanged. pack_sha256 is bound at run time."
)
SUBMISSIONS["context_overlays"] = {name: overlay(name) for name in CONTEXTS}

EXPECTED = {
    "schema_version": "pins-context-owner-expected/1",
    "status": MANIFEST["status"],
    "derivation": (
        "Values come from the Phase 6 plan (Task 0 table and 'What each pin binds'), the rulings, and the frozen oracles named in "
        "manifest.json inputs_pinned, read by sha256; never from the code under test. Texts marked preparer-fixed are chosen here "
        "(the plan leaves them to Task 0) and the builder copies them verbatim: the pinned sentences, the ledger label and kind, the "
        "CP-0 context rows. Recomputed cases (CP-2E hedge 60/40, CP-4C one multiple) are the frozen module builders run on a changed "
        "literal, after they reproduce the frozen cases."
    ),
    "issue_order": ORDER_NOTE,
    "issue_wording": {
        "form": "<path>[ (<at>)]: pinned <pin as typed>; submitted <value as typed | absence>",
        "cp2a": "pinned <fraction> (<typed percent>%), the submission's units; count: `assumptions.cp2a.scenarios: pinned 4 scenarios; submitted <n>`",
        "lists": "cp2e shocks are compared as lists and printed joined with `, ` (`pinned 100, 200; submitted 101, 200`)",
        "cp4c": "`(valuation[i].multiple)` follows the path; the submitted multiple is printed as typed (3.0, not 3)",
        "preparer_fixed": "the plan fixes the cp2a, cp2e-list, cp3c, cp4c-index wordings; the others follow the same form",
    },
    "own_limitations_rule": "own_limitations excludes the settle-time `Synthetic case; not real issuer qualification` line, as in the base "
    "oracles; a settled module's limitations are own_limitations then that line (dedupe), so the pinned line comes before it",
    "pinned_lines": PINNED_LINE,
    "pinned_line_note": "preparer-fixed: the plan elides the middle of every sentence except CP-2A's and CP-3C's; all share one frame. "
    "No period or currency word (Phase 8 constraint).",
    "ledger_row": {
        "label": LEDGER_LABEL,
        "kind": LEDGER_KIND,
        "note": "preparer-fixed; used by T2E.7 (CP-2D) and T3D.8 (CP-3C); "
        "CP-2E T2F.9 and CP-3D T3E.9 use the oracle's `Limitation <n>` label",
    },
    "modules": EXPECTED_MODULES,
    "concerns": [
        (
            "The plan names only T2E.7 and T3D.8 as limitation tables whose rows become facts; the frozen CP-2E (T2F.9) and CP-3D (T3E.9) "
            "oracles also build their Limitations table from the own-limitation list, so the pinned line is a new last row there too."
        ),
        "CP-1's own output for the `context` source (rows, limitation) is Phase 2's and is not enumerated here.",
    ],
}

# --------------------------------------------------------------------------------------------------
# 9. write
# --------------------------------------------------------------------------------------------------
files = {}
for name, data in CTX_BYTES.items():
    files[name] = data
manifest_final = MANIFEST
files["submissions.json"] = dumps(SUBMISSIONS).encode("utf-8")
files["expected.json"] = dumps(EXPECTED).encode("utf-8")
manifest_final["files_sha256"] = {n: sha(b) for n, b in sorted(files.items())}
manifest_final["files_sha256_note"] = (
    "sha256 of every other file this builder writes (manifest.json and builder/build.py are pinned by PINS.json at the freeze)"
)
files["manifest.json"] = dumps(manifest_final).encode("utf-8")

OUT.mkdir(parents=True, exist_ok=True)
for name, data in files.items():
    (OUT / name).write_bytes(data)
print(f"wrote {len(files)} files to {OUT}")
