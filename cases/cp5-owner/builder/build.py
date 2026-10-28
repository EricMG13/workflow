"""Writes cases/cp5-owner/{manifest,submissions,expected}.json (stdlib only).

Independent transcription of the composition rules documented in src/deploy_vii/cp5_integrity.py
(`REGISTERS`, `_inputs_tables` .. `_status_tables`, `_review_issues`, `settle`) and
docs/methods/cp5.md (src/deploy_vii/methods/cp5.md). Product code is read, never imported or
executed. The builder reads only data files, each checked against a pinned sha256 before use:
the serialised methodology, the frozen S1 oracle and the CP-3 oracle (whose CP-1A, CP-2 and CP-3
heads are the evaluated set of the CP-5 review). Nothing outside the repository is read.

Python owns arithmetic: CP-5 has none. No amount is derived here; every figure of the evaluated
heads is a `{{FIG:name}}` reference resolved at run time exactly as in the S1 and CP-3 oracles.

Run from the repository root:  python3 -I cases/cp5-owner/builder/build.py
To build into a scratch directory outside the repository:
    python3 -I cases/cp5-owner/builder/build.py --out <scratch dir>

Revision 1 (LEAD rulings, 2026-10-28): one oracle only. The run does not request CP-MODEL (ruling 1:
cases/cp3-cp6-owner R6 was amended to match); the owner view, TOOL-CONTRACT row and run-time
assertions are pinned below (rulings 2, 3, 5, 6).
"""

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp5-owner"
if "--out" in sys.argv:
    OUT = Path(sys.argv[sys.argv.index("--out") + 1])
    assert not str(OUT.resolve()).startswith(str(ROOT)), "--out must be outside the repository"

PINS = {
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "cases/cp3-cp6-owner/manifest.json": "893c6310212113c3a5a31fc9804f22550ba4e297e51f14ba03952a2a7444a60b",
    "cases/cp3-cp6-owner/submissions.json": "eaecbcd012c3d157d96362c288b842e7c25157aabffff831e68dcd23bffe6b0b",
    "cases/cp3-cp6-owner/expected.json": "7428c9340cae7221157657bdc628e43717b3f61716c86d6b6775c5b46b162a3e",
}


def sha_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load_pinned(rel):
    assert sha_file(rel) == PINS[rel], f"{rel}: sha256 differs from the pin"
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


METH = load_pinned("src/deploy_vii/methodology.json")
S1M = load_pinned("cases/snapshot/manifest.json")
S1E = load_pinned("cases/snapshot/expected.json")
C3M = load_pinned("cases/cp3-cp6-owner/manifest.json")
C3S = load_pinned("cases/cp3-cp6-owner/submissions.json")
C3E = load_pinned("cases/cp3-cp6-owner/expected.json")
load_pinned("cases/snapshot/submissions.json")  # pinned for the record: the CP-1 literals are not read

SYNTH = "Synthetic case; not real issuer qualification"
NONE_STATED = "None stated"
SCOPE_NOTE = (
    "Describes the evaluated set only: a module outside it, unrun, blocked or not selected, "
    "is not implied to pass"
)
# narrative_projection.py:171-175 (read, not imported): the limitation of every CP-1 narrative claim.
CP1_CLAIM_LIMITATION = (
    "Analyst synthesis over referenced prior records. Inspect Evidence Trace for exact values, "
    "units, periods, roles and hashes. Semantic qualification is unrun."
)
# tests/test_financial_workflow.py: narrative() dimensions; finding_id == dimension == CP-1 claim_id
# (narrative_projection.py:167). Asserted again at run time (run_time_bindings).
CP1_DIMENSIONS = (
    "leverage",
    "coverage",
    "cash_flow_quality",
    "liquidity",
    "data_quality",
    "definition_risks",
    "key_gaps",
)

# LEAD ruling 3: the text docs/TOOL-CONTRACT.md's CP-5 row takes when this lease freezes (LEAD amends the doc).
TOOL_CONTRACT_ROW = {
    "today": "CP-5 integrity_review | explicitly granted bound CP-1 canonical fact/status view; includes missing facts; single-producer no-claim integrity scope | none",
    "amended_to": (
        "CP-5 integrity_review | exactly the owner view of docs/CP5-OWNER-LEASE.md: cp5_integrity.context_block over the bound heads "
        "(every fact of the non-CP-1 bound heads; for CP-1 the facts integrity_projection keeps), no `quote` key at any depth and no citation quote string outside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`; CP-3's settled market-evidence facts, not citations), "
        "python_findings reduced to the kind label plus where; served by read_inputs on the G1 pathway only. The v1 and CP5-v2 upstream-tool "
        "grants stay for the earnings pathway | none"
    ),
    "python_findings_rule": "top level '<KIND_LABEL[kind]>: <where>' (no detail); per claim the mark cut at its first ': ' (kind, or 'kind on ref')",
}

# L1 (review-precise-1): the (source_id, locator) of each CP-1 claim's first citation, as observed on the S1 CP-1 head.
CP1_C1 = {
    "leverage": ("financial", "page:4"),
    "coverage": ("financial", "page:2"),
    "cash_flow_quality": ("financial", "page:3"),
    "liquidity": ("financial", "page:4"),
    "data_quality": ("financial", "page:1"),
    "definition_risks": ("financial", "page:5"),
    "key_gaps": ("identity", "page:1"),
}
assert sorted(CP1_C1) == sorted(CP1_DIMENSIONS)

problems = []

# --- registry order and plan (methodology.json is the registry order, registry.py:35-37) ------------
ORDER = [m["module_id"] for m in METH]
CP5_ENTRY = next(m for m in METH if m["module_id"] == "CP-5")


def rank(module_id):
    # registry.py `_rank`: non-modules (the prepared pack) first, then registry order
    return (module_id in ORDER, ORDER.index(module_id) if module_id in ORDER else 0, module_id)


REQUESTED = ["CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6"]
# CP-5 fan-in: every selected module except CP-5, CP-6, CP-8, CP-MEMO, CP-OS (registry.py:24-25, 67-69),
# plus its required CP-0. Bound inputs follow plan order (execution.py:247-248).
FAN_IN = [m for m in REQUESTED if m not in ("CP-5", "CP-6")]
PLAN = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6"]
assert set(PLAN) == set(["CP-0"] + REQUESTED)
# Ruling 1: this run is the cp3-cp6 oracle's R6, which no longer requests CP-MODEL.
assert C3M["runs"]["R6"]["requested_modules"] == REQUESTED, C3M["runs"]["R6"]["requested_modules"]
assert C3M["runs"]["R6"]["plan_order"] == PLAN, C3M["runs"]["R6"]["plan_order"]
assert "CP-MODEL" not in PLAN
INPUT_ORDER = [m for m in PLAN if m in ["CP-0"] + FAN_IN]
EVALUATED = sorted([m for m in INPUT_ORDER if m != "CP-0"], key=rank)  # NOT_EVALUATED = {CP-0}
assert INPUT_ORDER[0] == "CP-0"

# --- D8: the CP-5 registers equal the methodology entry, and no other module shares an id ---------
REGISTERS = [
    ("T5.1", "Evaluated set", "Input|Bound status|Bound SHA-256|Evaluation"),
    ("T5.2", "Material claim register", "Claim|Module|Citations|Limitation"),
    ("T5.3", "Citation trace", "Record|Module|Source trace|Result"),
    ("T5.4", "Claim figure resolution", "Claim|Module|Result"),
    ("T5.5", "Figure identity by fact id", "Fact id|Modules|Result"),
    ("T5.6", "Figure identity by coordinate", "Coordinate|Modules|Result"),
    ("T5.7", "Input currency", "Input|Bound status|Result"),
    ("T5.8", "Gap propagation", "Item|Module|Result"),
    ("T5.9", "Findings register", "Finding|Kind|Origin|Where|Detail"),
    ("T5B.1", "Material support review", "Claim|Module|Support|Upstream refs|Rationale"),
    ("T5B.2", "Unsupported and partly supported claims", "Claim|Module|Support|Rationale"),
    ("T5B.3", "Cross-module contradictions", "Contradiction|Claims|Nature|Severity|Rationale"),
    ("T5B.4", "Verdict consistency", "Claim|Module|Python findings|Support|Result"),
    ("T5B.5", "Integrity gaps", "Gap ID|Gap|Why it matters|Affected modules|Severity|Action"),
    ("T5B.6", "Module integrity status", "Module|Head status|CP-5 findings|Result"),
    ("T5B.7", "Report-level limitations", "Limitation ID|Limitation|Origin"),
    ("T5B.8", "Integrity verdict", "Item|Value"),
]
TABLE_IDS = [r[0] for r in REGISTERS]
assert TABLE_IDS == CP5_ENTRY["table_ids"], "CP-5 methodology table_ids differ from the transcribed registers"
collisions = {
    m["module_id"]: sorted(set(m["table_ids"]) & set(TABLE_IDS)) for m in METH if m["module_id"] != "CP-5"
}
collisions = {k: v for k, v in collisions.items() if v}
assert not collisions, collisions
LIMITATIONS_RAIL = ["T5.9", "T5B.2", "T5B.3", "T5B.5", "T5B.7"]  # bindings/cp5.py:16
EVIDENCE_RAIL = [t for t in TABLE_IDS if t not in LIMITATIONS_RAIL]


def snake(label):
    return re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")


# --- cells and tables -------------------------------------------------------------------------------
def cell(text, judged=False):
    return {"text": text, "judged": judged}


def table(table_id, rows, *, bound_rows=None):
    """One register as the CP-5 composer writes it. `rows` are (row_id, label, [cells]); an empty list
    gives the single `none` row of not_applicable cells (cp5_integrity._Tables.add)."""
    _, title, columns = next(r for r in REGISTERS if r[0] == table_id)
    labels = columns.split("|")
    cols = [{"field": snake(label), "label": label} for label in labels[1:]]
    out_rows = []
    if not rows and not bound_rows:
        reason = f"None in this CP-5 review ({title.lower()})"
        out_rows = [
            {
                "row_id": "none",
                "label": "None",
                "facts": [
                    {
                        "fact_id": f"{table_id}.none.{c['field']}",
                        "column": c["label"],
                        "text": None,
                        "status": "not_applicable",
                        "cites": [],
                        "value_class": None,
                        "limitation": reason,
                    }
                    for c in cols
                ],
            }
        ]
    for row_id, label, cells in rows:
        assert len(cells) == len(cols), (table_id, row_id, "Report row does not match its columns")
        out_rows.append(
            {
                "row_id": row_id,
                "label": label,
                "facts": [
                    {
                        "fact_id": f"{table_id}.{row_id}.{c['field']}",
                        "column": c["label"],
                        "text": x["text"],
                        "status": "known",
                        "cites": [],
                        "value_class": "analyst_judgment" if x["judged"] else None,
                        "limitation": None,
                    }
                    for c, x in zip(cols, cells, strict=True)
                ],
            }
        )
    result = {
        "table_id": table_id,
        "title": title,
        "row_header": labels[0],
        "columns": cols,
        "rows": out_rows,
    }
    if bound_rows:
        result["bound_rows"] = bound_rows
    return result


def numbered(pairs):
    return [(f"r{i:03d}", label, cells) for i, (label, cells) in enumerate(pairs, 1)]


# --- the evaluated heads: claims -----------------------------------------------------------------
def facts_of(tables):
    return {f["fact_id"] for t in tables for r in t["rows"] for f in r.get("facts", [])}


S1P = S1E["positive"]
# CP-1A: the S1 positive head; the CP-3 oracle changes four of its tables, none holds a claim cell
CP1A_TABLES = S1P["CP-1A"]["tables"]
for case in ("positive", "gap"):
    delta = C3E[case]["upstream"]["CP-1A"]["R6"]
    assert delta["claims_unchanged"] is True
    assert "credit_translation" not in delta["tables"]
CP1A_FACTS = facts_of(CP1A_TABLES)
CP2_TABLES = S1P["CP-2"]["tables"]
CP2_FACTS = facts_of(CP2_TABLES)
FIGURES = [f["name"] for f in S1P["CP-2"]["figures_referenced"]]
assert FIGURES == ["total_leverage_reported", "net_leverage_reported", "interest_coverage_reported", "fcf_to_debt"]
CP2_FIGURE_NAMES = FIGURES


def claims_of(case):
    """Per evaluated module the (claim_id, limitation, cites) the head carries, from the pinned oracles."""
    cites = lambda c: [list(x) for x in c.get("cites", [])]  # noqa: E731
    heads = {
        "CP-1": [
            {"claim_id": d, "limitation": CP1_CLAIM_LIMITATION, "cites": None} for d in CP1_DIMENSIONS
        ],
        "CP-1A": [
            {"claim_id": c["claim_id"], "limitation": c.get("limitation"), "cites": cites(c)}
            for c in S1P["CP-1A"]["claims"]
        ],
        "CP-2": [
            {"claim_id": c["claim_id"], "limitation": c.get("limitation"), "cites": cites(c)}
            for c in S1P["CP-2"]["claims"]
        ],
        "CP-3": [
            {"claim_id": c["claim_id"], "limitation": c.get("limitation"), "cites": cites(c)}
            for c in C3E[case]["CP-3"]["claims"]
        ],
    }
    for module_id, claims in heads.items():
        ids = [c["claim_id"] for c in claims]
        assert len(set(ids)) == len(ids), module_id
    return {m: sorted(heads[m], key=lambda c: c["claim_id"]) for m in EVALUATED}


def cp3_facts(case):
    return facts_of(C3E[case]["CP-3"]["tables"])


# --- the literal submissions (analyst judgment as literal input) ---------------------------------
def fig(name):
    assert name in FIGURES
    return "{{FIG:" + name + "}}"


def cite_refs(claim_id, n):
    return [f"{claim_id}#c{i}" for i in range(1, n + 1)]


RATIONALE = {
    # CP-1: the narrative claims cite the evidence records they name (narrative_projection.py)
    "CP-1": {
        "leverage": "The claim's own citations carry the debt record it describes as material, and the claim adds only a mechanism and an implication.",
        "coverage": "The claim's own citations carry the interest service record it describes, and its mechanism and implication stay inside that record.",
        "cash_flow_quality": "The claim's own citations carry the cash flow record behind the capital requirement point, and nothing in it goes beyond that record.",
        "liquidity": "The claim's own citations carry the cash record it relies on, and the stated flexibility is no stronger than that record.",
        "data_quality": "The claim's own citations carry the source description that records the missing assurance, which is what the claim says.",
        "definition_risks": "The claim's own citations carry the earnings definition it describes, and the covenant caveat is stated as a caveat.",
        "key_gaps": "The claim's own citations carry the entity record that limits the perimeter, and the claim restates that limit.",
    },
    "CP-1A": {
        "credit_translation.r01": "The cited business page states the distributor and manufacturer revenue sources and that the split is not disclosed, as the claim says.",
        "credit_translation.r02": "The cited business page states the pass-through lag as a management statement, and the claim keeps it as a statement.",
        "credit_translation.r03": "The cited business page states that no concentration disclosure is supplied, which is the claim.",
        "credit_translation.r04": "The cited business page states the ownership and the quarterly distributions, and the claim stops at what is stated.",
        "credit_translation.r05": "The cited financial page states the unaudited title, the cited business page states that no security, guarantee or covenant detail is supplied, and the evidence cell with the concentration citation of the neighbouring row states the missing concentration disclosure, which together are the claim.",
    },
    "CP-2": {
        "T2.1.assessment": "The assessment cell and the copied reference figures state the leverage and cover reading, and its basis cells name the CP-1A rows that state the caveats the cell lists.",
        "T2.10.kf01": "The key finding cell and the copied reference figures state the low leverage reading for the stated period.",
        "T2.10.kf02": "The key finding cell and its basis cell state the single term loan and the single maturity date.",
        "T2.10.kf03": "The key finding cell and its basis cell state the shareholder distributions and the undisclosed owners.",
        "T2.10.kf04": "The key finding cell and its basis cell state the missing concentration and covenant items, and the assessment limitation cell states the unaudited statements.",
    },
}


def review_for(case, module_id, claim):
    cid = claim["claim_id"]
    cites = claim["cites"]
    if module_id == "CP-1":
        refs = [f"{cid}#c1"]  # at least one citation is asserted at run time (run_time_bindings)
        why = RATIONALE["CP-1"][cid]
    elif module_id == "CP-1A":
        n = len(cites)
        assert n >= 1
        refs = [f"{cid}#c1", f"{cid}.evidence"]
        assert refs[1] in CP1A_FACTS, refs[1]
        if cid == "credit_translation.r05":
            # F2: the security, guarantee and covenant absence is in #c2; the concentration absence is in r03#c1
            assert n >= 2
            r03 = next(c for c in S1P["CP-1A"]["claims"] if c["claim_id"] == "credit_translation.r03")
            assert len(r03.get("cites", [])) >= 1
            refs += [f"{cid}#c2", "credit_translation.r03#c1"]
        why = RATIONALE["CP-1A"][cid]
    elif module_id == "CP-2":
        refs = [f"{cid}.assessment" if cid == "T2.1.assessment" else f"{cid}.finding"]
        if cid in ("T2.1.assessment", "T2.10.kf01"):
            refs += [fig("total_leverage_reported"), fig("net_leverage_reported"), fig("interest_coverage_reported")]
        else:
            refs += [f"{cid}.basis"] if f"{cid}.basis" in CP2_FACTS else []
            if cid == "T2.10.kf04":
                refs += ["T2.1.assessment.limitation"]  # F2: the unaudited point
        if cid == "T2.1.assessment":
            refs += ["T2.1.assessment.basis", "T2.10.kf02.basis"]  # F2: the caveats are carried by the basis cells
        for r in refs:
            assert r.startswith("{{FIG:") or r in CP2_FACTS, r
        why = RATIONALE["CP-2"][cid]
    elif module_id == "CP-3":
        facts = cp3_facts(case)
        if case == "positive" and cid == "T3.4.preference":
            refs = ["T3.4.preference.rationale", "T3.4.preference.basis", *cite_refs(cid, len(cites))]
            why = "The preference cell, its basis cell and the cited market pages state the ordering of the single instrument and its provisional status."
        elif case == "positive" and cid == "T3.1.i01":
            refs = ["T3.1.i01.fundamental_view", "T3.1.i01.market_observation", "T3.3.m01.quote", *cite_refs(cid, len(cites))]
            why = "The instrument cells and the cited market pages state the single dealer quotation and the indicative talk, and the claim keeps talk apart from a quotation."
        else:
            assert case == "gap" and cid == "T3.4.preference"
            refs = ["T3.4.preference.rationale", "T3.3.m01.kind", "T3.3.m01.limitation"]
            why = "The market evidence cells record that no market source exists, which is exactly what the claim says."
        for r in refs:
            assert "#c" in r or r in facts, r
    else:
        raise AssertionError(module_id)
    for r in refs:
        m = re.search(r"#c(\d+)$", r)
        if m and cites is not None:
            assert 1 <= int(m.group(1)) <= len(cites), r
    return {
        "claim_ref": cid,
        "producer_module": module_id,
        "support": "supported",
        "rationale": why,
        "upstream_refs": refs,
    }


GAPS = {
    "legal": {
        "gap": "Legal documents and covenant terms are outside the evaluated set",
        "why_it_matters": "The credit view and the relative value view both rest on the absence of covenant evidence, and this review cannot test any covenant statement.",
        "affected_modules": ["CP-2", "CP-3"],
        "severity": "Material",
        "action": "Review the credit view again once the legal documents and covenant terms are supplied.",
    },
    "market": {
        "gap": "No market quotation source reached the evaluated set",
        "why_it_matters": "The relative value claim rests on the absence of market evidence, so this review can confirm only that the absence is recorded.",
        "affected_modules": ["CP-3"],
        "severity": "Material",
        "action": "Review the relative value claim again once a dated market quotation source is supplied.",
    },
}


def submission_for(case):
    claims = claims_of(case)
    reviews = [review_for(case, m, c) for m in EVALUATED for c in claims[m]]
    gaps = [GAPS["legal"]] if case == "positive" else [GAPS["market"], GAPS["legal"]]
    return {"claim_reviews": reviews, "contradictions": [], "gaps": gaps}


# --- composition ----------------------------------------------------------------------------------
def claim_label(m, k):
    return f"{m} {k}"


def trace(m, claim):
    if claim["cites"] is None:
        return "{{TRACE:" + claim_label(m, claim["claim_id"]) + "}}"
    return "; ".join(f"{claim['claim_id']}#c{n} {s} {loc}" for n, (s, loc) in enumerate(claim["cites"], 1)) or "No citation"


def has_citation(claim):
    return True if claim["cites"] is None else bool(claim["cites"])


def inherited_segments(case):
    """The scope.inherited sequence (execution.inherited_limitations over the bound heads with own=()):
    each bound head's settled limitations then its inherited_limitations, de-duplicated at first
    position. Every head's inherited list is made of earlier heads' entries, so only each head's own
    settled limitations open a new position (derivation in `derivation`)."""
    cp0 = C3E[case]["upstream"]["CP-0"]["R6"]["limitations"]
    segments = [{"literal": cp0}, {"bind": "CP-1 head: its limitations then its inherited_limitations, in head order"}]
    literal = []
    literal += S1P["CP-1A"]["settled_limitations"]
    literal += S1P["CP-2"]["settled_limitations_own"]
    literal += C3E[case]["CP-3"]["settled_limitations"]
    segments.append({"literal": literal})
    return segments


def flatten(segments, bound=()):
    out = []
    for s in segments:
        items = s["literal"] if "literal" in s else list(bound)
        for t in items:
            if t not in out:
                out.append(t)
    return out


def compose(case, submission):
    claims = claims_of(case)
    keys = [(m, c) for m in EVALUATED for c in claims[m]]
    out = {}

    inputs = ["prepared-pack"] + INPUT_ORDER
    inputs_sorted = sorted(inputs, key=rank)

    def evaluation(i):
        if i == "prepared-pack":
            return "Prepared pack: the citation checks read its sources"
        if i == "CP-0":
            return "Source-readiness gate: bound, not an analyst; outside the evaluated set"
        return "Evaluated"

    def sha(i):
        return "{{PACK_SHA256}}" if i == "prepared-pack" else "{{SHA256:" + i + "}}"

    out["T5.1"] = table("T5.1", numbered((i, [cell("accepted" if i == "prepared-pack" else "{{STATUS:" + i + "}}"), cell(sha(i)), cell(evaluation(i))]) for i in inputs_sorted))
    out["T5.2"] = table(
        "T5.2",
        numbered(
            (claim_label(m, c["claim_id"]), [cell(m), cell(trace(m, c)), cell(c["limitation"] or NONE_STATED)])
            for m, c in keys
        ),
    )
    holds = "Holds in the prepared pack"
    out["T5.3"] = table(
        "T5.3",
        numbered(
            (f"{m} claim {c['claim_id']}", [cell(m), cell(trace(m, c)), cell(holds)])
            for m, c in keys
            if has_citation(c)
        ),
    )
    resolves = "Every figure reference resolves to the module's own facts"
    out["T5.4"] = table("T5.4", numbered((claim_label(m, c["claim_id"]), [cell(m), cell(resolves)]) for m, c in keys))

    # identity groups: a CP-1 fact copied verbatim into other modules' cp1_references (same fact_id)
    copies = {"CP-2": list(CP2_FIGURE_NAMES), "CP-3": list(C3E[case]["CP-3"]["cp1_references_order"])}
    assert "CP-1A references none" in S1P["rails"]["evidence"]["note"]
    members = []
    for name in FIGURES:
        mods = ["CP-1"] + [m for m in ("CP-1A", "CP-2", "CP-3") if name in copies.get(m, [])]
        mods = sorted(mods, key=rank)
        members.append({"figure": name, "modules": mods})
    same_fid = (
        "Identical value (amount times scale), unit, currency, period and placement "
        "(a CP-1 reference copy's placement is assigned by its composer)"
    )
    out["T5.5"] = table(
        "T5.5",
        [],
        bound_rows={
            "rule": "one row per figure, rows ordered ascending by the bound CP-1 fact_id string (cp5_integrity.identity_groups sorts by subject 'fact_id <id>'), row_id r001.. in that order, label = the bound fact_id",
            "members": [
                {"figure": g["figure"], "label": fig(g["figure"]), "cells": [", ".join(g["modules"]), same_fid]}
                for g in members
            ],
        },
    )
    out["T5.6"] = table("T5.6", [])

    seg = inherited_segments(case)
    out["T5.8"] = table(
        "T5.8",
        [],
        bound_rows={
            "rule": "no blocked or unsettled row exists; one row per entry of inherited_limitations.sequence in order, row_id r001.., label 'Inherited limitation'",
            "cells": ["Bound inputs", "<the entry text>"],
        },
    )
    out["T5.7"] = table("T5.7", numbered((i, [cell("accepted" if i == "prepared-pack" else "{{STATUS:" + i + "}}"), cell("Bound as listed; a stale bound input refuses the review, and none is recorded")]) for i in inputs_sorted))
    out["T5.9"] = table("T5.9", [])

    reviews = {(r["producer_module"], r["claim_ref"]): r for r in submission["claim_reviews"]}
    assert set(reviews) == {(m, c["claim_id"]) for m, c in keys}
    out["T5B.1"] = table(
        "T5B.1",
        numbered(
            (
                claim_label(m, c["claim_id"]),
                [cell(m), cell("Supported"), cell(", ".join(reviews[(m, c["claim_id"])]["upstream_refs"])), cell(reviews[(m, c["claim_id"])]["rationale"], True)],
            )
            for m, c in keys
        ),
    )
    out["T5B.2"] = table("T5B.2", [])
    out["T5B.3"] = table("T5B.3", [])
    out["T5B.4"] = table(
        "T5B.4",
        numbered(
            (claim_label(m, c["claim_id"]), [cell(m), cell("None"), cell("Supported"), cell("Consistent: no Python finding touches the claim")])
            for m, c in keys
        ),
    )
    out["T5B.5"] = table(
        "T5B.5",
        [
            (
                f"g{i:03d}",
                f"CP-5-GAP-{i:03d}",
                [cell(g["gap"], True), cell(g["why_it_matters"], True), cell(", ".join(g["affected_modules"]) or "Report level"), cell(g["severity"]), cell(g["action"], True)],
            )
            for i, g in enumerate(submission["gaps"], 1)
        ],
    )
    out["T5B.6"] = table(
        "T5B.6",
        numbered((m, [cell("{{STATUS:" + m + "}}"), cell("None"), cell("Evaluated: no finding")]) for m in EVALUATED),
    )
    own = [f"Gap ({g['severity']}): {g['gap']}" for g in submission["gaps"]]
    out["T5B.7"] = table(
        "T5B.7",
        numbered((f"L{i:03d}", [cell(t), cell("CP-5 gap")]) for i, t in enumerate(own, 1)),
        bound_rows={
            "rule": "after the own rows: one row per entry of inherited_limitations.sequence in order, row_id continuing r00(n+1).., label L(n+1).. (cp5_integrity._status_tables: enumerate(scope.inherited, len(own)+1))",
            "cells": ["<the entry text>", "Inherited"],
            "first_index": len(own) + 1,
        },
    )
    status = "restricted"  # own limitations (gaps) exist
    out["T5B.8"] = table(
        "T5B.8",
        [
            ("status", "Status", [cell("Restricted over the evaluated set")]),
            ("evaluated", "Evaluated set", [cell(", ".join(EVALUATED))]),
            ("not_evaluated", "Not evaluated", [cell("CP-0")]),
            ("scope", "Scope", [cell(SCOPE_NOTE)]),
        ],
    )
    tables = [out[t] for t in TABLE_IDS]
    for t in tables:  # LEAD table shape: one fact per column in every row
        for r in t["rows"]:
            assert len(r["facts"]) == len(t["columns"]), (t["table_id"], r["row_id"])
    return {
        "report_status": status,
        "module_inputs": ["prepared-pack"] + INPUT_ORDER + ["integrity-submission"],
        "evaluated": EVALUATED,
        "not_evaluated": ["CP-0"],
        "claim_count": len(keys),
        "claims_to_review": [[m, c["claim_id"]] for m, c in keys],
        "tables": tables,
        "findings": [],
        "own_limitations": own,
        "settled_limitations": own + [SYNTH],
        "inherited_limitations": {
            "sequence": seg,
            "order": "inputs in plan order, each head's settled limitations then its inherited_limitations; de-duplicated at first position; scope.inherited (own=()) shows the 'Synthetic' entry",
            "settled_inherited": "the sequence minus every entry equal to an own settled limitation (execution.settle: inherited_limitations(snapshot, attempt, own, load)); the head's inherited_limitations",
            "flattened_without_bound_CP-1": flatten(seg),
        },
        "status": "restricted",
        "status_why": "own limitations are non-empty (the gaps and the synthetic entry; execution.py:446-453)",
    }


def blocked_note():
    return {
        "attempts": "attempt 0 invalid (any validator refusal below) is re-begun; attempt 1 invalid settles CP-5 blocked (status blocked, limitations = the issue lines; cp5_integrity.submit_cp5_step; execution.settle)",
        "consequence": "registry.edge_rule('CP-6','CP-5') is block (CP-5 is in CP-6 required), so execution.current_inputs raises 'Required upstream is unrun, stale or blocked' for CP-6; G1 retains a RefusedBegin for CP-6 and begins nothing more",
        "expect": "CP-5 head blocked; exactly one RefusedBegin for CP-6 whose reason equals the ValueError text; no CP-6 attempt, step or head; receipt verifies",
    }


# --- refusal mutations (applied to the positive literal) -------------------------------------------
def mutations(sub_pos):
    claims = claims_of("positive")
    idx = {(r["producer_module"], r["claim_ref"]): i for i, r in enumerate(sub_pos["claim_reviews"])}
    i_kf01 = idx[("CP-2", "T2.10.kf01")]
    i_kf02 = idx[("CP-2", "T2.10.kf02")]
    listed = ", ".join(EVALUATED)
    rows = [
        {
            "id": "cp5-unreviewed-claim",
            "op": {"remove_review": ["CP-2", "T2.10.kf02"]},
            "issues": ["Incomplete review: unreviewed material claims: CP-2 T2.10.kf02"],
            "rule_source": "cp5_integrity._review_issues (missing)",
        },
        {
            "id": "cp5-doubly-reviewed",
            "op": {"duplicate_review": ["CP-2", "T2.10.kf01"]},
            "issues": ["CP-2 T2.10.kf01 is reviewed more than once"],
            "rule_source": "cp5_integrity._review_issues (count > 1)",
        },
        {
            "id": "cp5-unresolved-claim-ref",
            "op": {"set": [["claim_reviews", i_kf02, "claim_ref"], "T2.10.kf09"]},
            "issues": [
                f"claim_reviews[{i_kf02}]: unresolved claim_ref T2.10.kf09 in CP-2",
                "Incomplete review: unreviewed material claims: CP-2 T2.10.kf02",
            ],
            "rule_source": "cp5_integrity._resolve",
        },
        {
            "id": "cp5-producer-not-evaluated",
            "op": {"set": [["claim_reviews", i_kf02, "producer_module"], "CP-4"]},
            "issues": [
                f"claim_reviews[{i_kf02}]: producer_module CP-4 is not an evaluated module ({listed})",
                "Incomplete review: unreviewed material claims: CP-2 T2.10.kf02",
            ],
            "rule_source": "cp5_integrity._resolve",
        },
        {
            "id": "cp5-unresolved-upstream-ref",
            "op": {"append": [["claim_reviews", i_kf02, "upstream_refs"], "T2.10.kf02.nope"]},
            "issues": [f"claim_reviews[{i_kf02}]: unresolved upstream_ref T2.10.kf02.nope in CP-2"],
            "rule_source": "cp5_integrity._review_issues (refs)",
        },
        {
            "id": "cp5-supported-names-no-ref",
            "op": {"set": [["claim_reviews", i_kf02, "upstream_refs"], []]},
            "issues": [f"claim_reviews[{i_kf02}]: a supported verdict names no upstream_ref"],
            "rule_source": "cp5_integrity._review_issues (supported without ref)",
        },
        {
            "id": "cp5-figure-in-rationale",
            "op": {"set": [["claim_reviews", i_kf01, "rationale"], "The reading of 5 in the cell is the claim."]},
            "issues": [f"claim_reviews[{i_kf01}].rationale: Bare figure: 5"],
            "rule_source": "cp5_integrity._text_issues (prose.issues against no facts)",
        },
        {
            "id": "cp5-claim-id-in-rationale",
            "op": {"set": [["claim_reviews", i_kf01, "rationale"], "The cell T2.10.kf01 states the claim."]},
            "issues": [f"claim_reviews[{i_kf01}].rationale: Bare figure: T2.10.kf01"],
            "rule_source": "cp5_integrity._text_issues (a claim id is not a label)",
        },
        {
            "id": "cp5-empty-rationale",
            "op": {"set": [["claim_reviews", i_kf01, "rationale"], " "]},
            "issues": [f"claim_reviews[{i_kf01}].rationale: empty text"],
            "rule_source": "cp5_integrity._text_issues",
        },
        {
            "id": "cp5-contradiction-one-module",
            "op": {
                "set": [
                    ["contradictions"],
                    [
                        {
                            "claim_refs": [
                                {"producer_module": "CP-2", "claim_ref": "T2.10.kf01"},
                                {"producer_module": "CP-2", "claim_ref": "T2.10.kf02"},
                            ],
                            "nature": "Scope differs between the two claims",
                            "rationale": "The two claims read the same cell differently.",
                            "severity": "Minor",
                        }
                    ],
                ]
            },
            "issues": ["contradictions[0]: a contradiction names claims of at least two modules"],
            "rule_source": "cp5_integrity._review_issues (contradictions)",
        },
        {
            "id": "cp5-gap-unbound-module",
            "op": {"set": [["gaps", 0, "affected_modules"], ["CP-4"]]},
            "issues": ["gaps[0]: CP-4 is not a bound module"],
            "rule_source": "cp5_integrity._review_issues (gaps)",
        },
        {
            "id": "cp5-shape-unknown-support",
            "op": {"set": [["claim_reviews", i_kf01, "support"], "sound"]},
            "issues_contains": [f"claim_reviews.{i_kf01}.support: "],
            "rule_source": "readiness.shape_issues (pydantic literal error, short form '<path>: <message>')",
        },
    ]
    return rows


def apply_op(sub, op):
    sub = copy.deepcopy(sub)
    if "remove_review" in op:
        m, c = op["remove_review"]
        sub["claim_reviews"] = [r for r in sub["claim_reviews"] if (r["producer_module"], r["claim_ref"]) != (m, c)]
    elif "duplicate_review" in op:
        m, c = op["duplicate_review"]
        r = next(r for r in sub["claim_reviews"] if (r["producer_module"], r["claim_ref"]) == (m, c))
        sub["claim_reviews"].append(copy.deepcopy(r))
    elif "set" in op or "append" in op:
        path, value = op.get("set") or op["append"]
        target = sub
        for p in path[:-1]:
            target = target[p]
        if "set" in op:
            target[path[-1]] = value
        else:
            target[path[-1]].append(value)
    return sub


# --- build -------------------------------------------------------------------------------------
def build():
    sub = {c: submission_for(c) for c in ("positive", "gap")}
    assert (len(sub["positive"]["claim_reviews"]), len(sub["gap"]["claim_reviews"])) == (19, 18)  # ruling 7: 37 judgments
    comp = {c: compose(c, sub[c]) for c in ("positive", "gap")}
    muts = mutations(sub["positive"])
    for m in muts:
        mutated = apply_op(sub["positive"], m["op"])
        assert mutated != sub["positive"], m["id"]
    cp3_cases = {c["case_id"]: c for c in C3M["cases"]}
    r6 = {
        "requested_modules": REQUESTED,
        "plan_order": PLAN,
        "live_consumers_of_cp0": [m for m in PLAN if m != "CP-0"],
        "note": "CP-5 and CP-6 share one run (D3: CP-6 is the consumer that proves CP-5; LEAD ruling 4: no R5 run, no extra promotion). This run is the cp3-cp6-owner R6, amended in revision 1 (LEAD ruling 1) so that CP-MODEL is not requested: CP-5 follows every selected analyst and G1 publishes CP-MODEL last, so a run requesting it could never begin CP-5. CP-5's consumption of CP-MODEL (DC-5) is therefore not proved here; it stays open on the CP-MODEL row (G1-X section 5: add it when a lease needs it).",
    }
    manifest = {
        "schema_version": "cp5-owner-cases/1",
        "scope": "CP-5 integrity review (integrity_review) as a G1 owner over the CP-1, CP-1A, CP-2 and CP-3 heads of the CP-3/CP-6 credit-snapshot run; consumed by CP-6",
        "status": "DRAFT revision 2 by owner-preparation task cp5-owner, 2026-10-28 (LEAD rulings 1-9 applied; review-precise-1 fix round 1: F1, F2, L1, L2, L3); not executed",
        "pins": PINS,
        "reuse": {
            "pack sources": "cases/cp3-cp6-owner/manifest.json cases[*].pack_sources (and, through it, cases/financial/manifest.json and cases/snapshot/manifest.json business_source), bytes unchanged. CP-5 reads no pack source: it is a submit-only step and the prepared pack only serves its citation checks.",
            "heads": "the CP-1A, CP-2 and CP-3 heads are the CP-3 oracle's (cases/cp3-cp6-owner/expected.json) and the S1 oracle's (cases/snapshot/expected.json); the CP-1 head is the genuine promotion, bound at run time",
        },
        "run": r6,
        "rulings_applied": {
            "1": "CP-MODEL is not requested; cp3-cp6-owner R6 amended and re-pinned here (asserted against its manifest)",
            "2": "owner view = context_block with every fact of the non-CP-1 heads plus the integrity_projection facts of CP-1, no citation quote, bound as view(historical, attempt) -> (sha256, body): expected.json view",
            "3": "TOOL-CONTRACT CP-5 row amended to the owner view; python_findings reduced to kind label plus where: expected.json view.binding and TOOL_CONTRACT_ROW in execution.tool_use",
            "4": "CP-5 runs only inside the CP-6 run (R6); no R5 run, no extra promotion: run.note",
            "5": "mechanical findings asserted at run time (RT-1, RT-2); analyst finding categories not built",
            "6": "each CP-1 claim carries at least one citation: run-time assertion RT-3",
            "7": "independent semantic review of the 37 literal support judgments (19 positive, 18 gap) by review-precise-1: semantic_review",
            "8": "docs/MODULES.csv CP-5 row moves only after the R6 run; the earnings pathway stays separate",
            "9": "noted: the CP-0 literals already list CP-5; {{CP5_FINDINGS_SUFFIX}} is '' in both cases",
        },
        "run_time_bindings": {
            "note": "Assertions the owner test makes against the actual run (the CP-1 head is a genuine promotion; none of these is derivable here). A failure of any is reported to LEAD, not absorbed into the oracle.",
            "RT-1": {
                "ruling": 5,
                "assert": "the bound CP-1 head's claim ids equal, as a set and in count, exactly " + ", ".join(sorted(CP1_DIMENSIONS)) + " (seven narrative claims; the frozen id list), each with the shared limitation text CP1_CLAIM_LIMITATION; no other CP-1 claim exists",
            },
            "RT-2": {
                "ruling": 5,
                "assert": "cp5_integrity.python_checks over the bound scope returns zero findings: the owner view's python_findings is [] at the top level and for every claim, blocked_upstream is [], T5.9 holds only its `none` row, and no CP-5-FINDING-NNN exists in the settled head",
            },
            "RT-3": {
                "ruling": 6,
                "assert": "each of the seven CP-1 claims carries at least one citation (len(claim.citations) >= 1), so the `<claim>#c1` upstream_ref and the T5.3 trace row exist; a claim with none fails the run and the oracle must switch that claim to a fact ref. Also (revision 2, L1) the first citation's (source_id, locator) equals the one observed on S1: " + ", ".join(f"{k} {a} {b}" for k, (a, b) in CP1_C1.items()),
                "c1_source_locator": {k: list(v) for k, v in CP1_C1.items()},
            },
        },
        "semantic_review": {
            "ruling": 7,
            "who": "review-precise-1, independent of the oracle author",
            "scope": "the 37 literal support judgments (positive 19, gap 18) in submissions.json: each rationale and 'supported' verdict against the cited cells (S1 oracle for CP-1A and CP-2, CP-3 oracle for CP-3, the run's CP-1 head for the seven narrative claims)",
            "note": "mechanical cleanliness (prose.issues, the validator) is not support",
        },
        "cases": [
            {
                "case_id": "cp5-positive",
                "pack_sources": cp3_cases["cp3-cp6-positive"]["pack_sources"],
                "run": {**cp3_cases["cp3-cp6-positive"]["runs"]["R6"]["run"], "requested_modules": REQUESTED},
                "submissions": "cases/cp5-owner/submissions.json#positive",
            },
            {
                "case_id": "cp5-gap",
                "pack_sources": cp3_cases["cp3-cp6-gap"]["pack_sources"],
                "run": {**cp3_cases["cp3-cp6-gap"]["runs"]["R6"]["run"], "requested_modules": REQUESTED},
                "change_from_positive": "no market source: CP-0 records the gap, CP-3 settles Insufficient Information (cp3-cp6 oracle gap case)",
                "submissions": "cases/cp5-owner/submissions.json#gap",
            },
        ],
    }
    submissions = {
        "schema_version": "cp5-owner-submissions/1",
        "note": "Literal analyst judgment only: reviews, contradictions and gaps. Python writes every finding, id and status. A {{FIG:name}} reference is a CP-2 fact_id (the CP-1 fact_id of a verbatim cp1_references copy), replaced at run time as in cases/snapshot/submissions.json. Support judgments are the oracle author's; they need independent semantic review (mechanical cleanliness is not support).",
        "positive": submission_for("positive"),
        "gap": submission_for("gap"),
        "refusal_mutations": [{k: v for k, v in m.items() if k not in ("issues", "issues_contains", "rule_source")} | {"id": m["id"]} for m in muts],
    }
    expected = {
        "schema_version": "cp5-owner-expected/1",
        "derivation": "Hand-transcribed composition rules of cp5_integrity.py applied to submissions.json and to the heads of the pinned S1 and CP-3 oracles by cases/cp5-owner/builder/build.py. No value is computed by product code, and CP-5 computes none: every figure stays a {{FIG:name}} reference. Table ids, titles and columns are the 17 registers of the methodology entry CP-5 (D8: no id is shared with another module).",
        "cell_notation": {
            "text": "exact displayed text; null means unsettled (the `none` placeholder row)",
            "status": "known | not_applicable",
            "cites": "always [] (CP-5 cells carry no citation)",
            "value_class": "analyst_judgment where the cell is model-written (judged); otherwise null",
            "markers": "{{...}} markers are run-time bindings (see run_time_bindings)",
        },
        "table_id_check": {
            "method": "methodology.json table_ids of every module compared for equality with each CP-5 id (builder data read, no code run)",
            "CP-5": TABLE_IDS,
            "collisions": {},
            "serialised_change": "CP-2A no longer lists T5.*; CP-0's T5 is a different string; CP-5's methodology entry already lists exactly the 17 composed ids, so no D8 registration is needed",
            "composed_unregistered_ids": [],
        },
        "evaluated_set": {
            "bound_inputs_in_order": ["prepared-pack"] + INPUT_ORDER,
            "evaluated": EVALUATED,
            "gate_not_evaluated": ["CP-0"],
            "rule": "registry.dependencies: CP-5 fan-in = every selected module outside {CP-5, CP-6, CP-8, CP-MEMO, CP-OS}, plus required CP-0; execution.current_inputs binds them in plan order; ReviewScope.evaluated sorts by registry rank",
            "cp4_note": "CP-4 is not selected, so no CP-5 row carries CP-4 content (cp5_premise)",
        },
        "python_checks": {
            "expected_findings": [],
            "status": "ASSERTED AT RUN TIME. The CP-1 head (tens of thousands of facts, seven narrative claims) is produced by the promotion, so the mechanical checks over it cannot be derived here. Why none is expected: citation checks run on citations the stages validated against the same pack; every claim resolves its own facts (narrative_projection.py:375-377 and the CP-2/CP-3/CP-1A validators run prose.issues on them); the only figures shared across modules are verbatim cp1_references copies (T5.5 rows, identical by construction); no module but CP-1 holds a numeric fact outside cp1_references (T5.6 empty); no claim cites a non-known fact without a stated limitation. A finding in a real run is reported to LEAD, not absorbed: cases/cp3-cp6-owner premise (zero T5B.2/T5B.3 rows, nothing flagged) would then need review.",
            "categories_exercised_by_the_cases": "none of the eight mechanical categories fires; the three analyst categories do not fire (all supported, no contradiction); the refusal mutations exercise the validator, not the findings",
        },
        "positive": comp["positive"],
        "gap": comp["gap"],
        "run_time_bindings": {
            "{{PACK_SHA256}}": "PreparedPack.content_hash() of the run's pack",
            "{{SHA256:<module>}}": "result_sha256 of the module's settled head bound as CP-5 input (the attempt input's sha256)",
            "{{STATUS:<module>}}": "the bound head status: restricted for every head (synthetic case; S1 oracle). CP-1 is restricted (financial precedent)",
            "{{FIG:name}}": "as cases/snapshot/submissions.json: the unique T4.10 twelve-month (LTM) Q4 2025 fact of that metric in the CP-1 head; its fact_id is also the fact_id of the verbatim copy in the cp1_references of CP-2 (and CP-3 for the first three); zero or several candidates fail",
            "{{TRACE:CP-1 <claim_id>}}": "'; '.join('<claim_id>#c<n> <source_id> <locator>') over the bound CP-1 claim's citations, 1-based; each of the seven CP-1 claims must carry at least one citation (asserted), else T5.3 and the 'c1' reference are wrong and the run fails",
            "CP-1 claim ids": "exactly " + ", ".join(sorted(CP1_DIMENSIONS)) + " (asserted against the bound CP-1 head: manifest run_time_bindings RT-1; RT-2 zero Python findings; RT-3 at least one citation per CP-1 claim)",
            "CP-1 limitation entries": "CP-1's own and inherited limitation texts, bound from the CP-1 head at the bind marker of inherited_limitations.sequence",
            "T5.5 and T5.8 and T5B.7 rows": "T5.5 rows ascending by bound fact_id; T5.8 and T5B.7 inherited rows follow the flattened sequence",
            "ticket and call ids": "compared structurally only",
        },
        "view": {
            "step": "integrity_review",
            "input": "module_context (G1-X _VIEWS['integrity_review'] = owners.cp5.view)",
            "binding": {
                "signature": "view(historical, attempt) -> (sha256, body)  (docs/G1X-OWNER-CORE-PROTOCOL.md section 2; registered in the fixed dict _VIEWS['integrity_review'])",
                "historical": "the G1 historical Execution of the ticket's snapshot (owner_workflow._owner_historical): the view is recomputed from the journal, never from the live store, exactly as owners.cp2.view",
                "construction": [
                    "scope = cp5_integrity.review_scope(historical, attempt); a non-empty scope.issues raises WorkflowError('identity_mismatch')",
                    "P(head) = integrity_projection(scope)(head) for the CP-1 head (live.context.integrity_projection: facts a claim names as {ref|unit}, members of an identity group, references a Python check flags) and head.facts, every fact, for every other head",
                    "block = cp5_integrity.context_block(scope, facts=P)",
                    "for every modules[*].claims[*]: citations[*] keeps ref, source_id and locator only (the quote key is deleted) and python_findings[i] is cut at its first ': ' (the kind, or 'kind on ref', with no detail)",
                    "block['python_findings'][i] = KIND_LABEL[f.kind] + ': ' + f.where for f in python_checks(scope).findings (no detail: the detail of a citation finding can carry a quote fragment); TOOL-CONTRACT ruling 3",
                    "body = json.dumps(block, ensure_ascii=False, separators=(',', ':'), allow_nan=False)",
                    "return (hashlib.sha256(body.encode()).hexdigest(), body)",
                ],
                "digest": "sha256 of the UTF-8 body; read_inputs returns it, the journal records it, and the verifier compares it with view(historical, attempt)[0] (owner_workflow._verify_calls_reads; the cp5-tamper-read-body refusal)",
                "no_quote": "two conditions (revision 2, F1): (1) no `quote` key at any depth; (2) no citation quote string anywhere in the body except inside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`), which are CP-3's settled market-evidence facts, not citations (P keeps every CP-3 fact and the positive literal names T3.3.m01.quote). No python_findings string carries a detail.",
            },
            "body": "cp5_integrity.context_block(scope, facts=P) as compact JSON, with every modules[*].claims[*].citations[*].quote removed and python_findings reduced to the kind label plus where (see binding.construction), where P keeps every fact of each head except CP-1, and for CP-1 the facts live.context.integrity_projection keeps",
            "size_probe": {
                "what": "a measurement on a scratch copy of the S1 positive store (slice-snapshot-positive: CP-0, CP-1, CP-1A, CP-2 restricted; no CP-3 head exists in S1), the same construction as binding.construction, ReviewScope built directly from the stored heads; probe scratchpad/cp5r1/probe/view_size.py, 3.3 s, original store untouched",
                "owner_view_body_bytes": 147174,
                "owner_view_sha256_of_that_body": "424adb041d40007b1f5e79062122fe315bfabb31ea15dfb3d86523d8255592e8",
                "per_module_bytes": {"CP-1": 11744, "CP-1A": 103479, "CP-2": 30794},
                "facts_per_module": {"CP-1": 11, "CP-1A": 410, "CP-2": 106},
                "live_projection_with_quotes_bytes": 26989,
                "cp3_not_measured": "the CP-3 head adds 39 facts and 2 claims in the positive case (28 facts and 1 claim in the gap case) by the CP-3 oracle count; at the CP-2 density (about 290 bytes per fact) that is about 11 KB, an estimate, not a measurement",
                "citation_check": "of the 24,884 citations of the three heads (mostly CP-1 facts, which the projection omits), none of the quote strings occurs verbatim in the body, and the string \"quote\" does not occur as a key (S1 has no CP-3 head; on a CP-3 positive head the T3.3.m01.quote and T3.3.m02.quote facts equal the citation quotes of T3.1.i01 and T3.4.preference, the exempt case of view.binding.no_quote)",
                "status": "informational. The run recomputes the size; no size bound is asserted (none was ruled).",
            },
            "key_tree": {
                "top": ["note", "sources", "modules", "claims_to_review", "python_findings", "blocked_upstream", "inherited_limitations"],
                "sources[*]": ["source_id", "name", "status"],
                "modules[*]": ["module_id", "status", "evaluated", "facts", "claims", "limitations", "inherited_limitations"],
                "modules[*].facts[*]": ["ref", "label", "table_id", "row_id", "field", "period", "status", "shown", "limitation"],
                "modules[*].claims[*]": ["claim_id", "text", "limitation", "citations", "python_findings"],
                "modules[*].claims[*].citations[*]": ["ref", "source_id", "locator"],
            },
            "counts": {
                case: {
                    "sources": len(cp3_cases["cp3-cp6-positive" if case == "positive" else "cp3-cp6-gap"]["pack_sources"]),
                    "modules": len(EVALUATED),
                    "module_order": EVALUATED,
                    "claims_to_review": comp[case]["claims_to_review"],
                    "python_findings": [],
                    "blocked_upstream": [],
                    "body_bytes": "recomputed in the run (S1 probe: 147174 for CP-1, CP-1A, CP-2; CP-3 adds about 11 KB, estimated)",
                    "inherited_limitations": "the flattened sequence (bound CP-1)",
                }
                for case in ("positive", "gap")
            },
            "assertions": [
                "the key tree equals the tree above",
                "no `quote` key at any depth, and no citation quote string of a bound head occurs in the body outside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`); re-asserted in the run",
                "no python_findings string (top level or per claim) carries a finding detail: top-level entries are exactly '<KIND_LABEL>: <where>', per-claim entries contain no ': '",
                "every upstream_ref of the literal submission is listed in the body as a fact ref or a citation ref, except CP-1 facts the literal does not use",
                "the digest recorded for the read equals sha256 of the body",
            ],
        },
        "refusals": {
            "validator_refusals": [{k: v for k, v in m.items() if k != "op"} | {"case": "positive", "owner": "CP-5"} for m in muts],
            "tool_use_refusals": [
                {"id": "cp5-read-before-submit", "case": "positive", "setup": "submit with no read_inputs on the attempt", "expect": "refused not_permitted (a session-less step with inputs != none needs a read on its own binding)"},
                {"id": "cp5-pack-tool", "case": "positive", "setup": "invoke read_pages or search_pack", "expect": "refused receipt not_permitted (submit-only step: registry.tool_set('integrity_review') == 'submit-only')"},
                {"id": "cp5-upstream-tool", "case": "positive", "setup": "invoke lookup_upstream or read_integrity_scope", "expect": "refused receipt not_permitted (upstream_grant is None; G1 cannot verify grant calls, owner_workflow create refuses a spec with a grant)"},
                {"id": "cp5-stale-snapshot", "case": "positive", "setup": "change the snapshot between the last read and the submit", "expect": "refused stale_binding"},
            ],
            "blocked_case": blocked_note(),
            "tamper_refusals": [
                {"id": "cp5-tamper-read-body", "case": "positive", "edit": "forge a consistent read: receipt copy whose CP-5 read_inputs record has an edited `body` (and its inputs_sha256 recomputed), the audit input_reads file rewritten under the new content hash, receipt.sha256 rewritten", "expect": "_verify_audit passes on the forged copy; _verify_calls_reads refuses identity_mismatch because the view is recomputed from the historical snapshot (owner_workflow.py:1278-1291); verify_owner_run_receipt refuses identity_mismatch"},
                {"id": "cp5-tamper-step-output", "case": "positive", "edit": "edit the output of the CP-5 integrity_review step in the store", "expect": "verify_owner_run_receipt refuses identity_mismatch (the store's blob hash check, not the probe's output comparison: recorded limitation S1a R3-5)"},
                {"id": "cp5-tamper-settled-head", "case": "positive", "edit": "a receipt copy with the CP-5 head's `status` changed, and one with `result_sha256` set to '0'*64", "expect": "both refused (head check before the seal check)"},
            ],
            "note": "issues is the exact validate_integrity result for the mutated literal (a tuple in this order, de-duplicated); issues_contains is a prefix of one issue. The whole submission is refused as an invalid step: nothing settles accepted.",
        },
        "execution": {
            "statuses": "every head restricted (synthetic case); CP-5 restricted (own gaps and the synthetic entry)",
            "tool_use": {
                "CP-5": {
                    "tool_set": "submit-only; applicable_rules = ()",
                    "read_inputs": "exactly one read_inputs per attempt before the submit; body = the owner view above (narrower than the live CONTEXT in quotes, wider in facts; bound as view(historical, attempt) -> (sha256, body)); this satisfies D2 as the adopted view frozen in this lease",
                    "tool_contract_row": TOOL_CONTRACT_ROW,
                    "ok_pack_calls": 0,
                }
            },
            "consumption": {
                "CP-5_of_CP-1_CP-1A_CP-2_CP-3": "D3 scope extension by this lease: the CP-5 attempt inputs bind each head's settled hash (T5.1 rows) and the settled review cites each head's facts (T5B.1 refs): CP-1 citation refs, CP-1A evidence cells and citations, CP-2 key finding cells and copied reference figures, CP-3 preference, instrument and market cells. The verifier probe re-runs cp5_integrity._validate_step on the frozen snapshot, which reads exactly those heads.",
                "CP-6_of_CP-5": "CP-6 reads the CP-5 head through cp5_catalogue (T5.9, T5B.6, T5B.7, T5B.8 rows), cp5_review (T5.9 findings, T5B.4 flagged claims, T5B.2 and T5B.3 counts, T5B.6/T5B.8 verdict) and the status. Expected reads: findings (), flagged claims (), unsupported 0, contradictions 0, cp4_rows (), verdict {status: 'Restricted over the evaluated set', evaluated: '" + ", ".join(EVALUATED) + "', not_evaluated: 'CP-0', scope: the scope note}, status restricted, so the CP-6 cap 'CP-5 is restricted' is the only CP-5 cap and {{CP5_FINDINGS_SUFFIX}} is ''. Proof: the CP-6 attempt inputs bind the CP-5 hash and the CP-6 own limitation 'CP-5 handoff caps the confidence below High: CP-5 is restricted' exists; CP-6 begin is refused when CP-5 is blocked.",
                "CP-5_consumers_inside_the_product": "CP-6 only; the Evidence and Limitations rails render the tables (no Front Page block).",
            },
        },
        "render": {
            "block": "none: bindings/cp5.py binds the 17 tables to the Evidence and Limitations rails only; no FP01 block, no D7 block",
            "rails": {
                "evidence": {"CP-5": EVIDENCE_RAIL},
                "limitations": {"CP-5": LIMITATIONS_RAIL, "module_limitations": {"own_settled": comp["positive"]["settled_limitations"]}},
            },
            "slots": {t: "cp5-" + t.lower().replace(".", "-") for t in TABLE_IDS},
            "gap_module_limitations_own_settled": comp["gap"]["settled_limitations"],
        },
    }
    return manifest, submissions, expected


def dump(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def main():
    manifest, submissions, expected = build()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / name).write_text(dump(obj), encoding="utf-8")
        print(name, hashlib.sha256(dump(obj).encode()).hexdigest())
    if problems:
        print("\n".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
