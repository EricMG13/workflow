"""Writes cases/context-identity-periods/* (stdlib only; deploy_vii is never imported or run).

Phase 2 Task 0 oracle: context identity and periods. Every expected value comes from the
plan rulings (work/context-plan/reviews/phase-2-plan-review.md, the Phase 2 plan) and from the
already-frozen oracles read here by hash: cases/earnings/expected.json (CP-1B points, gap),
cases/cpl10-owner/expected.json (the four quarters), cases/snapshot/* (pack B sources).

Run: python3 -I cases/context-identity-periods/builder/build.py   (from the repository root)
Two runs write byte-identical files.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "context-identity-periods"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/earnings/expected.json": "041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599",
    "cases/earnings/manifest.json": "60ed95782648064db7806bb7f0714fe030f9563424df50e17500803a2edfb7ec",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "cases/cpl10-owner/expected.json": "285915140dbd7722e406ce96bb11c20ab5f5ce370e6649748299f4809695ce45",
}
RAW = {}
for rel, digest in PINS.items():
    RAW[rel] = (ROOT / rel).read_bytes()
    assert hashlib.sha256(RAW[rel]).hexdigest() == digest, f"input drift: {rel}"
FIN = json.loads(RAW["cases/financial/manifest.json"])
EARN = json.loads(RAW["cases/earnings/expected.json"])
EARN_M = json.loads(RAW["cases/earnings/manifest.json"])
SNAP_M = json.loads(RAW["cases/snapshot/manifest.json"])
SNAP_S = json.loads(RAW["cases/snapshot/submissions.json"])
CPL10 = json.loads(RAW["cases/cpl10-owner/expected.json"])


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def page_sha(pages):
    return sha("\f".join(p["text"] for p in pages).encode("utf-8"))


# --- 1. pack B identity source (preparer-written) ------------------------------------------------
OLD_ID = next(s for s in FIN["sources"] if s["source_id"] == "identity")
assert page_sha(OLD_ID["pages"]) == OLD_ID["sha256"]
OLD_SENTENCE = "No borrower, guarantor or restricted-group perimeter is established by this source set."
NEW_BORROWER = "The borrower is Northbridge Holdings LLC."
NEW_SENTENCE = "No guarantor or restricted-group perimeter is established by this source set."
old_text = OLD_ID["pages"][0]["text"]
assert old_text.endswith(OLD_SENTENCE)
new_text = old_text[: -len(OLD_SENTENCE)] + NEW_BORROWER + "\n" + NEW_SENTENCE
NEW_ID_PAGES = [{"locator": "page:1", "text": new_text}]
NEW_ID_SHA = page_sha(NEW_ID_PAGES)
OLD_ID_SHA = OLD_ID["sha256"]
IDENTITY_B = {
    "source_id": "identity",
    "name": OLD_ID["name"],
    "status": OLD_ID["status"],
    "extraction_status": OLD_ID["extraction_status"],
    "pages": NEW_ID_PAGES,
    "sha256": NEW_ID_SHA,
    "derivation": (
        "cases/financial/manifest.json identity page:1 with its last sentence replaced by two: "
        f"'{NEW_BORROWER}' and '{NEW_SENTENCE}'; every earlier line byte-identical"
    ),
}

# --- 2. pack B submissions: every identity citation re-cut -----------------------------------------
recut = {"citations": 0, "sha_rewritten": 0, "quote_rewritten": 0, "prose_rewritten": 0, "borrower_citations_added": 0}
PROSE = {
    "Confirms the issuer identity and that no borrower, guarantor or restricted-group perimeter is established": (
        "Confirms the issuer identity, the borrower name and that no guarantor or "
        "restricted-group perimeter is established"
    ),
    "operating KPIs are not disclosed and no borrower, guarantor or restricted-group perimeter is established": (
        "operating KPIs are not disclosed and no guarantor or restricted-group perimeter is established"
    ),
}


def recut_walk(obj):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            out[key] = recut_walk(value)
        if (
            out.get("source_id") == "identity"
            and "use" in out
            and "the borrower name" in out["use"]
            and isinstance(out.get("citations"), list)
        ):
            out["citations"] = [
                *out["citations"],
                {"source_id": "identity", "locator": "page:1", "quote": NEW_BORROWER},
            ]
            recut["borrower_citations_added"] += 1
        if out.get("source_id") == "identity" and "quote" in out:
            recut["citations"] += 1
            if out.get("source_sha256") == OLD_ID_SHA:
                out["source_sha256"] = NEW_ID_SHA
                recut["sha_rewritten"] += 1
            if out["quote"] == OLD_SENTENCE:
                out["quote"] = NEW_SENTENCE
                recut["quote_rewritten"] += 1
        return out
    if isinstance(obj, list):
        return [recut_walk(v) for v in obj]
    if isinstance(obj, str):
        for old, new in PROSE.items():
            if old in obj:
                recut["prose_rewritten"] += 1
                obj = obj.replace(old, new)
        return obj
    return obj


SUBMISSIONS_B = recut_walk(SNAP_S)
# P5T3-R7: the positive CP-0 review gains one gap, copied from cases/context-attachments-owner/
# submissions.json (legal-exec-missing-gap): every ctx-b-* context declares executed
# legal_documents and pack B holds no legal source. The S1A plan (CP-1, CP-1A, CP-2) has no legal
# module and the gap validator only admits selected modules or CP-0, so affected_modules is [].
LEGAL_GAP = {
    "gap_id": "legal-documents-missing",
    "kind": "source",
    "severity": "material",
    "description": "The run context declares executed legal_documents but the pack holds no executed or filed source",
    "affected_modules": [],
    "remediation": "Supply the executed legal documents",
    "citations": [],
}
_pos_gaps = SUBMISSIONS_B["positive"]["readiness_review"]["gaps"]
assert all(g["gap_id"] != LEGAL_GAP["gap_id"] for g in _pos_gaps)
_pos_gaps.append(LEGAL_GAP)
SUBMISSIONS_B["note"] = (
    "cases/snapshot/submissions.json with every identity citation re-cut against the pack-B "
    "identity source (new source_sha256; the borrower-denying quote replaced by the guarantor/"
    "restricted-group sentence; two prose strings (each in positive and gap) that said no borrower is established "
    "edited to match; the business_context identity source whose `use` names the borrower gains the citation of the borrower line (page:1 of identity-b)). Positive readiness_review gains the gap legal-documents-missing (P5T3-R7). Nothing else changed. " + SNAP_S["note"]
)
text_old = json.dumps(SNAP_S)
assert OLD_ID_SHA in text_old
assert OLD_ID_SHA not in json.dumps(SUBMISSIONS_B), "a stale identity hash survived"
assert OLD_SENTENCE not in json.dumps(SUBMISSIONS_B), "a stale identity quote survived"
IDENTITY_CITATIONS = recut["citations"]
# the snapshot oracle (expected.json) embeds the old identity hash; the builder of Tasks 1-5 substitutes it
SNAP_EXPECTED_HASH_HITS = RAW["cases/snapshot/expected.json"].decode().count(OLD_ID_SHA)

# --- 3. context inputs ---------------------------------------------------------------------------
AS_OF = EARN_M["cases"][0]["run"]["as_of"]
assert AS_OF == SNAP_M["cases"][0]["run"]["as_of"] == "2026-01-10"
ISSUER_NAME = "Northbridge Synthetic Group"
ISSUER_ID = "northbridge-synthetic"
ALIASES = ["Northbridge", "NBG"]
BORROWER = "Northbridge Holdings LLC"
SECTOR = "Business services"
SPONSOR = "Fictional Partners"


def context(run_type, pathway, cur, pri, *, borrower=BORROWER, aliases=ALIASES, guarantors=(),
            sector=SECTOR, sponsor=SPONSOR):
    return {
        "schema": "context/1",
        "run": {
            "run_type": run_type,
            "pathway": pathway,
            "case_kind": "synthetic",
            "as_of": AS_OF,
            "current_period": cur,
            "prior_period": pri,
            "reporting_currency": "USD",
        },
        "identity": {
            "issuer_name": ISSUER_NAME,
            "issuer_id": ISSUER_ID,
            "borrower_name": borrower,
            "parent_name": "",
            "guarantors": list(guarantors),
            "aliases": list(aliases),
            "listed_equity": False,
            "ticker": "",
            "sector": sector,
            "country": "",
            "sponsor": sponsor,
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
            "portfolio_workbook": False,
            "prior_case": False,
            "management_bridge": False,
            "legal_documents": "executed",
        },
        "research_questions": [],
    }


E_ = ("earnings", "earnings_update")
S_ = ("research", "credit_snapshot")
CONTEXTS = {
    # id: (pack, context object)
    "ctx-match": ("E", context(*E_, "q4-2025", "q3-2025")),
    "ctx-fy": ("E", context(*E_, "fy-2025", "fy-2024")),
    "ctx-h": ("E", context(*E_, "h2-2025", "h1-2025")),
    "ctx-mixed": ("E", context(*E_, "q4-2025", "fy-2024")),
    "ctx-q2031": ("E", context(*E_, "q4-2031", "q3-2031")),
    "ctx-comma": (
        "E",
        context(
            *E_,
            "q4-2025",
            "q3-2025",
            borrower="Northbridge Holdings, LLC",
            aliases=["Northbridge, Inc.", "NBG"],
            guarantors=["Northbridge Opco, LLC", "Northbridge IP LLC"],
        ),
    ),
    "ctx-l10": ("E-l10", context(*S_, "q4-2025", "q3-2025")),
    "ctx-q3": ("E-l10", context(*S_, "q3-2025", "q2-2025")),
    "ctx-fy-l10": ("E-l10", context(*S_, "fy-2025", "fy-2024")),
    "ctx-h-research": ("reader-only", context(*S_, "h2-2025", "h1-2025")),
    "ctx-b-match": ("B", context(*S_, "", "")),
    "ctx-b-punct": ("B", context(*S_, "", "", borrower="Northbridge Holdings, L.L.C.")),
    "ctx-b-mismatch": ("B", context(*S_, "", "", borrower="Southbridge Holdings LLC")),
    "ctx-research": ("B", context(*S_, "", "", borrower="", aliases=[], sector="", sponsor="")),
}

CTX_BYTES = {}
CTX_LINES = {}
for cid, (_pack, obj) in CONTEXTS.items():
    data = dumps(obj).encode("utf-8")
    CTX_BYTES[cid] = data
    CTX_LINES[cid] = data.decode("utf-8").splitlines()


def key_line(cid, key):
    hits = [i for i, line in enumerate(CTX_LINES[cid], 1) if line.lstrip().startswith(f'"{key}":')]
    assert len(hits) == 1, (cid, key, hits)
    return hits[0]


# --- 4. runs ---------------------------------------------------------------------------------------
S1A_MODULES = ["CP-1", "CP-MODEL", "CP-1A", "CP-2"]  # owner_rendering.py s1a-credit-snapshot scope
assert SNAP_M["cases"][0]["run"]["requested_modules"] == S1A_MODULES
EARN_PRESET = ["CP-0", "CP-1", "CP-MODEL", "CP-1B", "CP-1D", "CP-5"]  # contracts.py _PRESETS


def run_for(cid):
    pack = CONTEXTS[cid][0]
    base = {
        "run_id": f"ctxip-{cid}-v1",
        "issuer_id": ISSUER_ID,
        "issuer_name": ISSUER_NAME,
        "as_of": AS_OF,
        "method_version": "deploy-v-r14",
        "case_kind": "synthetic",
    }
    if pack == "E":
        return {**base, "pathway": "earnings_update", "requested_modules": EARN_PRESET,
                "set": "preparation_request preset; no explicit Run"}
    if pack == "E-l10":
        return {**base, "pathway": "credit_snapshot", "requested_modules": ["CP-L10"],
                "set": "explicit Run set after preparation_request"}
    if pack == "B":
        return {**base, "pathway": "credit_snapshot", "requested_modules": S1A_MODULES,
                "set": "explicit Run set after preparation_request"}
    return None


# --- 5. CP-0 / CP-1 context assessments (overlays) -------------------------------------------------
CTX_LIMIT = (
    "User-supplied run context: its names, periods and figures are the user's statements; "
    "CP-0 classifies its authority as unknown and does not verify them against issuer sources."
)


def cite(cid):
    line = key_line(cid, "issuer_name")
    return {
        "source_id": "context",
        "source_sha256": sha(CTX_BYTES[cid]),
        "locator": f"line:{line}",
        "quote": f'"issuer_name": "{ISSUER_NAME}",',
    }


def overlay(cid):
    c = cite(cid)
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


BORROWER_CITE = {
    "source_id": "identity",
    "source_sha256": NEW_ID_SHA,
    "locator": "page:1",
    "quote": NEW_BORROWER,
}
BORROWER_LIMIT = "The identity note does not state the borrower's fiscal year end."
BORROWER_ENTITY = {
    "entity_id": "borrower",
    "name": BORROWER,
    "entity_type": "legal_entity",
    "roles": ["borrower"],
    "fiscal_year_end": None,
    "citations": [BORROWER_CITE],
    "limitations": [BORROWER_LIMIT],
}
BORROWER_SCOPE = {
    "scope_id": "borrower-identity",
    "entity_id": "borrower",
    "period_label": "Unspecified borrower coverage",
    "period_kind": "unspecified",
    "start_date": None,
    "end_date": None,
    "currency": None,
    "unit": None,
    "entity_perimeter": None,
    "accounting_basis": None,
    "citations": [BORROWER_CITE],
    "limitations": [],
}
OVERLAYS = {
    "note": (
        "Per run: the CP-0 readiness `sources` entry and the CP-1 source_context `sources` entry "
        "for the `context` source (every prepared source is assessed exactly once; authority "
        "unknown, ruling D2). Pack B additionally adds the borrower entity to the CP-1 review and "
        "its scope to the pack-B `identity` assessment (a non-financial source's scopes are not "
        "held to the four-strings rule, source_context.py:355-356); this maps the entity to a "
        "reporting scope, so no `Entity is not mapped to a reporting scope` gap arises and "
        "financial scopes are untouched. pack_sha256 is bound at run time."
    ),
    "borrower_entity": BORROWER_ENTITY,
    "borrower_scope_on_identity_assessment": BORROWER_SCOPE,
    "per_context": {
        cid: overlay(cid) for cid, (pack, _o) in CONTEXTS.items() if pack not in ("reader-only",)
        and cid not in ("ctx-h", "ctx-mixed")
    },
}

# --- 6. expected.json ----------------------------------------------------------------------------
PROBLEM_H = "earnings runs compare quarters or fiscal years only."
PROBLEM_MIXED = "must be the same kind as the current period."
pos = EARN["positive"]
assert (pos["case_id"], pos["prior_period_id"], pos["current_period_id"]) == (
    "E-QOQ-FLAT", "q3-2025", "q4-2025")
gap = EARN["gap"]
assert gap["case_id"] == "E-NO-YOY"

# CP-L10 quarters: periods and column labels as frozen in cases/cpl10-owner/expected.json
periods = [v["period"] for v in CPL10["cases"]["positive"]["view_topics"][0]["values"]]
assert periods == [
    "Q1 25: 2025-01-01 to 2025-03-31", "Q2 25: 2025-04-01 to 2025-06-30",
    "Q3 25: 2025-07-01 to 2025-09-30", "Q4 25: 2025-10-01 to 2025-12-31"]
ORD = ["first", "second", "third", "fourth"]
QUARTERS = []
for i, period in enumerate(periods):
    head, dates = period.split(": ")
    QUARTERS.append({
        "context_period": f"q{i + 1}-2025",
        "period": period,
        "column": f"{head} ({dates})",
        "words": f"the {ORD[i]} quarter of 2025",
    })
ROWS_UNCHANGED_KEYS = [
    k for k in CPL10["cases"]["positive"].keys() if k not in ("pair", "view_pair_screens")
]

B_ROWS = {}
for cid in ("ctx-b-match", "ctx-b-punct", "ctx-b-mismatch", "ctx-research"):
    ident = CONTEXTS[cid][1]["identity"]
    rows = []
    if ident["borrower_name"]:
        rows.append({"group": "CP-0", "label": "Borrower", "value": ident["borrower_name"],
                     "key": "borrower_name"})
    if ident["aliases"]:
        rows.append({"group": "CP-0", "label": "Aliases", "value": "; ".join(ident["aliases"]),
                     "key": "aliases"})
    if ident["sector"]:
        rows.append({"group": "CP-1A", "label": "Sector", "value": ident["sector"], "key": "sector"})
    if ident["sponsor"]:
        rows.append({"group": "CP-1A", "label": "Sponsor", "value": ident["sponsor"], "key": "sponsor"})
    for row in rows:
        row["mark"] = f"user-supplied (context source, line {key_line(cid, row['key'])})"
    B_ROWS[cid] = rows

IDENTITY_CHECK = {
    "ctx-match@E": {"outcome": "not_supplied", "gaps": [], "found": []},
    "ctx-b-match@B": {"outcome": "match", "gaps": [], "found": [BORROWER]},
    "ctx-b-punct@B": {"outcome": "match", "gaps": [], "found": [BORROWER]},
    "ctx-b-mismatch@B": {
        "outcome": "mismatch",
        "gaps": [
            'borrower_name_mismatch: context names "Southbridge Holdings LLC", '
            'CP-1 locates "Northbridge Holdings LLC"'
        ],
        "found": [BORROWER],
    },
    "ctx-research@B": {"outcome": "not_supplied", "gaps": [], "found": [BORROWER]},
}

EXPECTED = {
    "schema_version": "context-identity-periods-expected/1",
    "status": "PREPARED by the Phase 2 Task 0 preparer; independent mx-precise review pending; not frozen, not pinned",
    "derivation": (
        "Values come from the Phase 2 plan rulings (work/context-plan/reviews/phase-2-plan-review.md "
        "Q1-Q4, H1-H3, M1-M5, N1-N3) and the frozen files named in `inputs`; never from the code "
        "under test. Texts marked `preparer-fixed` are chosen here (the plan lets Task 0 fix them) "
        "and the builder copies them verbatim."
    ),
    "inputs": {rel: digest for rel, digest in PINS.items()},
    "packs": {
        "E": "byte-identical earnings sources (identity 74fe2ad4..., financial 82d684cc...) + `context`",
        "E-l10": "pack E sources + `context`; Run set explicitly with requested_modules [CP-L10], pathway credit_snapshot",
        "B": "cases/snapshot identity (REPLACED by sources/identity-b.json), financial, business + `context`; Run set explicitly",
    },
    "reader": {
        "refused": {
            "ctx-h": {
                "exception": "ContextRefused",
                "problems": [
                    f"run.current_period: {PROBLEM_H}",
                    f"run.prior_period: {PROBLEM_H}",
                ],
                "note": "preparer-fixed: each h-period is its own problem, current first (run_section loops current_period then prior_period); the earlier-than rule does not fire (h1 < h2)",
            },
            "ctx-mixed": {
                "exception": "ContextRefused",
                "problems": [f"run.prior_period: {PROBLEM_MIXED}"],
                "note": "preparer-fixed: q4-2025 vs fy-2024; fy-2024 is not an h period; the earlier-than rule skips differing kinds",
            },
        },
        "loads": {
            "ctx-h-research": "run_type research with h2-2025 / h1-2025 loads (the rule is earnings runs only)",
            "all_others": [c for c in CONTEXTS if c not in ("ctx-h", "ctx-mixed")],
        },
        "not_frozen": "an earnings pair of kinds q and h (one h period) gets only the h problem; a q/h kind-mismatch problem is not asserted",
    },
    "form": {
        "ctx-comma": {
            "reader_borrower_name": "Northbridge Holdings, LLC",
            "reader_aliases": ["Northbridge, Inc.", "NBG"],
            "reader_guarantors": ["Northbridge Opco, LLC", "Northbridge IP LLC"],
            "model_dump_with_schema_equals_file": True,
            "lines_parser": {
                "input": "Northbridge, Inc.\nNBG",
                "items": ["Northbridge, Inc.", "NBG"],
            },
            "lines_parser_crlf": {"input": "Northbridge, Inc.\r\nNBG", "items": ["Northbridge, Inc.", "NBG"]},
            "comma_list_parser_unchanged": {"input": "a, b", "items": ["a", "b"], "fields": "assumption lists keep t:'list'"},
        }
    },
    "cp1b": {
        "source": "cases/earnings/expected.json positive (E-QOQ-FLAT) and gap (E-NO-YOY); limits are NOT compared",
        "ctx-match": {
            "offered_pair": {"prior_period_id": "q3-2025", "current_period_id": "q4-2025"},
            "case_id": pos["case_id"],
            "days_each": pos["days_each"],
            "points": pos["points"],
        },
        "ctx-fy": {
            "resolved_current": "fy-2025",
            "prior_passed_as_context_string": "fy-2024",
            "gap": {k: gap[k] for k in (
                "case_id", "prior_period_id", "current_period_id", "reason", "all_prior_values",
                "all_delta_values", "all_applicable_growth_values", "prior_and_delta_status",
                "current_revenue", "current_ebitda", "source_locator",
                "opening_2024_not_income_comparative")},
            "is_refusal": False,
        },
        "mismatch": {
            "context": "ctx-match",
            "submitted": {"prior_period_id": "q2-2025", "current_period_id": "q3-2025"},
            "issue_code": "context_period_mismatch",
            "issue_text": "context_period_mismatch: submitted q2-2025 -> q3-2025, context q3-2025 -> q4-2025",
            "note": "preparer-fixed text; names both pairs (prior -> current)",
        },
        "unresolved_current": {
            "context": "ctx-q2031",
            "issue_text": "context_period_unresolved: q4-2031",
        },
        "no_context_or_empty_periods": "behaviour is O1's; unchanged",
    },
    "identity_check": {
        "rule": "casefold, drop every non-alphanumeric character, collapse; only entities whose roles include `borrower` are compared (T4.2 Entity Role split on '; ')",
        "cases": IDENTITY_CHECK,
        "empty_borrower_name": {"outcome": "not_supplied", "gaps": []},
        "gap_code": "borrower_name_mismatch",
        "unchanged": "the CP-0 issuer gate (T1.run.identity_gate `confirmed`) and every CP-1 table other than the T4.2/gap-register deltas in `pack_b_cp1_delta`",
        "pack_b_cp1_delta": {
            "T4.2": "exactly one added row: Entity Name 'Northbridge Holdings LLC', Entity Role 'borrower', Fiscal Year End null, currency/unit/perimeter/basis null, period label 'Unspecified borrower coverage' (entity-scope / borrower / borrower-identity)",
            "gap_register": "the gap `No located borrower scope supplied` (source_context.py:577-578) no longer arises; a gap row (kind entity, subject borrower) with the limitation text `The identity note does not state the borrower's fiscal year end.` arises instead (an incomplete entity requires a limitation, validate_source_context); a scope gap (reference borrower-identity) `Unresolved scope: end_date, currency, unit, entity_perimeter, accounting_basis, period_kind` also arises (observed by running validate_source_context/source_context on the pack, not derived from the oracle); guarantor_group and restricted_group gaps remain",
            "other": "none; financial scopes and facts are untouched",
        },
    },
    "render": {
        "pack": "B",
        "delivery_scope": "s1a-credit-snapshot (credit_snapshot, modules CP-1 CP-MODEL CP-1A CP-2)",
        "section": {"id": "run-context", "title": "Run context", "count_per_page": 1,
                    "groups_in_order": ["CP-0", "CP-1", "CP-1A"]},
        "mark_format": "user-supplied (context source, line N); N = 1-based line of the row's key in the frozen context source (locator line:N)",
        "alias_separator": "; ",
        "rows": {cid: B_ROWS[cid] for cid in B_ROWS},
        "cp0_row": f"issuer {ISSUER_NAME} and the identity gate word `confirmed` printed beside the borrower and alias rows, unchanged",
        "cp1_row": "ctx-b-match, ctx-b-punct: `match`; ctx-b-mismatch: the gap text below; ctx-research: the compare result `not_supplied` (fixed text `not_supplied`, no gap)",
        "ctx-b-mismatch_gap_text": IDENTITY_CHECK["ctx-b-mismatch@B"]["gaps"][0],
        "ctx-research": "a context source always produces the section (plan :258-261): the CP-0 group holds the issuer name and the identity_gate word `confirmed`; the CP-1 group holds the compare result `not_supplied`; no borrower, aliases, sector or sponsor rows",
        "sponsor_vs_business_source": "ctx-b-match shows sponsor 'Fictional Partners' as user-supplied although the business source says it identifies no financial sponsor; no gap is raised",
        "no_context_source": "page bytes equal today's delivery bytes",
        "html_escaping": {"input_name": "<b>", "escaped": "&lt;b&gt;"},
    },
    "cpl10": {
        "source": "cases/cpl10-owner/expected.json cases.positive (sha in `inputs`)",
        "ctx-l10": {
            "pathway": "credit_snapshot",
            "requested_modules": ["CP-L10"],
            "quarters": QUARTERS,
            "rows_unchanged": {
                "keys_equal_to_cpl10_owner_positive": ROWS_UNCHANGED_KEYS,
                "excluded": "pack hash and run id dependent fields only; the pack differs from the cpl10-owner pack by its extra `context` source",
            },
            "cp0_review": "adds the `context` assessment of overlays.json per_context.ctx-l10 (authority unknown); CP-1 source_context likewise",
        },
        "ctx-q3": {
            "quarters_ending_at": ["q4-2024", "q1-2025", "q2-2025", "q3-2025"],
            "refusal": "unbound CP-1 operand: q4-2024 (no CP-1 T4.14 period)",
            "note": "the pack holds no 2024 quarter, so no dates exist for a label; q1-2025 .. q3-2025 resolve",
        },
        "ctx-fy-l10": {
            "step_validation_issue": "CP-L10: context_period_not_quarter",
            "offers_quarter_list": False,
        },
        "prior_period": "not used by CP-L10",
    },
    "periods_resolution": {
        "pack_t414_periods": [p["period_id"] for p in FIN["periods"]],
        "q2031": "q4-2031 and q3-2031 match no period: current unresolved (CP-1B refuses), prior would be passed on as the context string",
    },
    "pack_b_citations": {
        "identity_old_sha256": OLD_ID_SHA,
        "identity_new_sha256": NEW_ID_SHA,
        "identity_citations_recut": IDENTITY_CITATIONS,
        "identity_citations_with_hash": recut["sha_rewritten"],
        "prose_strings_edited": recut["prose_rewritten"],
        "count_note": "the brief says 27; the walk finds this many identity citations (positive and gap) in cases/snapshot/submissions.json",
        "stale_quote_replaced": {"old": OLD_SENTENCE, "new": NEW_SENTENCE},
        "snapshot_expected_json_hash_hits_to_substitute": SNAP_EXPECTED_HASH_HITS,
    },
    "inherited_gaps": [
        "Plan table says ctx-research has identity 'as ctx-match' while the Expected-values text says 'empty optional fields': frozen here as EMPTY optional fields (borrower, aliases, sector, sponsor), which serves both the omitted-optional-rows and borrower-not_supplied expectations (the section itself is still rendered).",
        "Pack B's frozen financial_pack_limitation and the CP-1 entity/review limitations still read 'borrower, guarantor and restricted perimeters unavailable' (a statement about the financial source's perimeters, pinned in cases/financial); beside the new identity borrower line it reads as stale but is left byte-identical.",
        "The snapshot `business` source says it identifies no financial sponsor; a context sponsor on pack B is user-supplied with no gap (plan ruling).",
        "Plan 'scope-mapped' is read as: the borrower entity maps to one `unspecified` scope on the identity assessment (not to financial scopes). If the controller means a financial scope, T4.2 and the facts would change and this case needs a ruling.",
        "Pack E contexts need a `context` assessment in the CP-0 and CP-1 reviews too (every prepared source is assessed once); the existing earnings oracles contain none, so the Task 4 builder must overlay them (overlays.json).",
    ],
}

# --- 7. write ----------------------------------------------------------------------------------------
files = {}
(OUT / "contexts").mkdir(parents=True, exist_ok=True)
(OUT / "sources").mkdir(parents=True, exist_ok=True)
for cid, data in CTX_BYTES.items():
    files[f"contexts/{cid}.json"] = data
files["sources/identity-b.json"] = dumps(IDENTITY_B).encode()
files["submissions-b.json"] = dumps(SUBMISSIONS_B).encode()
files["overlays.json"] = dumps(OVERLAYS).encode()
files["expected.json"] = dumps(EXPECTED).encode()

MANIFEST = {
    "schema_version": "context-identity-periods-cases/1",
    "scope": "Phase 2 Task 0 oracle: context identity and periods (CP-0, CP-1, CP-1A, CP-1B, CP-L10, reader, form)",
    "status": "prepared; not reviewed; not frozen; not pinned (cases/PINS.json and pins.py PATTERNS are changed at the freeze step)",
    "raw_rule": "contexts are the literal bytes the form writes (json indent 2, LF, trailing LF); the `context` source sha256 is sha256 of those bytes, spans line:N via splitlines",
    "inputs_pinned": PINS,
    "packs": {
        "E": {
            "sources": ["identity (cases/financial/manifest.json, byte-identical)",
                        "financial (cases/financial/manifest.json, byte-identical)", "context"],
            "issuer_id": ISSUER_ID, "issuer_name": ISSUER_NAME, "as_of": AS_OF,
            "base": "cases/earnings/manifest.json",
        },
        "B": {
            "sources": ["identity (sources/identity-b.json)", "financial (byte-identical)",
                        "business (cases/snapshot/manifest.json business_source.positive, f79a1ce9...)",
                        "context"],
            "issuer_id": ISSUER_ID, "issuer_name": ISSUER_NAME, "as_of": AS_OF,
            "base": "cases/snapshot/manifest.json snapshot-positive; tests/s1a_runs.py make_pack",
            "submissions": "submissions-b.json (positive)",
            "identity_sha256": NEW_ID_SHA,
        },
    },
    "contexts": {
        cid: {
            "file": f"contexts/{cid}.json",
            "pack": pack,
            "sha256": sha(CTX_BYTES[cid]),
            "run": run_for(cid),
        }
        for cid, (pack, _o) in CONTEXTS.items()
    },
    "builder": {
        "file": "builder/build.py",
        "sha256": sha((HERE / "build.py").read_bytes()),
        "run": "python3 -I cases/context-identity-periods/builder/build.py",
    },
    "files_sha256": {name: sha(data) for name, data in sorted(files.items())},
    "files_sha256_note": "every output except manifest.json and README.md (README is hand-written)",
}
files["manifest.json"] = dumps(MANIFEST).encode()

for name, data in files.items():
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print("wrote", len(files), "files; identity citations re-cut:", IDENTITY_CITATIONS, recut)
