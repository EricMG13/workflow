"""Writes cases/cpdr-context-cutoff/{manifest,context,expected}.json (stdlib only, imports nothing from src/).

Frozen key for the context cutoff (O7b-2 D9, O7-R19, OD5): run.cutoff 2025-12-31 over the five research rows of
cases/cpdr-research-owner, as-of 2026-01-10. Every hash is computed here from the embedded evidence bytes; the
text forms copied from existing code are cited in `_source` notes beside them. SYNTHETIC test data only.

Run: python3 -I cases/cpdr-context-cutoff/builder/build.py [OUT_DIR]   (from the repository root)
"""

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "cases" / "cpdr-context-cutoff"
SRC_MANIFEST = "cases/cpdr-research-owner/manifest.json"
SRC_PIN = "c4f3a66f2a627dce038f78685024901b81590aa87c23e2c140e09950393d7c6c"

raw = (ROOT / SRC_MANIFEST).read_bytes()
assert hashlib.sha256(raw).hexdigest() == SRC_PIN
SRC = json.loads(raw.decode("utf-8"))

AS_OF, CUTOFF = "2026-01-10", "2025-12-31"
BAD = {"cutoff_after_as_of": "2026-01-11", "cutoff_malformed": "31/12/2025"}
assert SRC["run"]["as_of"] == AS_OF
assert (
    date.fromisoformat(CUTOFF)
    < date.fromisoformat(AS_OF)
    < date.fromisoformat(BAD["cutoff_after_as_of"])
)


def dump(obj, indent):
    return json.dumps(obj, indent=indent, ensure_ascii=False) + "\n"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- evidence: same bytes as the research-owner key, hashes recomputed here -----------------------------
EV = {e["key"]: e for e in SRC["evidence"]}
assert sorted(EV) == list("ABCDE")
EVIDENCE_SHA = {}
for k, e in EV.items():
    assert len(e["pages"]) == 1
    EVIDENCE_SHA[k] = sha(e["pages"][0]["text"])
    assert EVIDENCE_SHA[k] == e["page_join_sha256"], k

ROWS = SRC["research_manifest"]["rows"]
FILE_BYTES = dump(ROWS, 1)
assert FILE_BYTES == SRC["research_manifest"]["file_bytes"]
assert sha(FILE_BYTES) == SRC["research_manifest"]["file_sha256"]

# --- context.json: the context/1 shape of cases/context/research-minimal.json, field order as the form saves it
CONTEXT = {
    "schema": "context/1",
    "run": {
        "run_type": "research",
        "pathway": "credit_snapshot",
        "case_kind": "public",
        "as_of": AS_OF,
        "cutoff": CUTOFF,
        "current_period": "",
        "prior_period": "",
        "reporting_currency": "USD",
    },
    "identity": {
        "issuer_name": "Northbridge Synthetic Group",
        "issuer_id": "northbridge-synthetic",
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
    "assumptions": {k: None for k in ("cp2a", "cp2d", "cp2e", "cp3c", "cp3d", "cp4c")},
    "attachments": {
        "portfolio_workbook": False,
        "prior_case": False,
        "management_bridge": False,
        "legal_documents": "executed",
    },
    "research_questions": SRC["context"]["research_questions"],
}
CONTEXT_BYTES = dump(CONTEXT, 2)

MANIFEST = {
    "schema_version": "cpdr-context-cutoff-cases/1",
    "scope": "Key for the run.cutoff context field (O7b-2 D9): intake, brief and brief view use min(as_of, run.cutoff). "
    "SYNTHETIC data; the five evidence items are those of cases/cpdr-research-owner.",
    "status": "frozen",
    "research_manifest": {"file": "research-manifest.json", "rows": ROWS, "file_bytes": FILE_BYTES},
    "evidence_source": "cases/cpdr-research-owner/manifest.json#evidence",
    "evidence_sha256": EVIDENCE_SHA,
    "context_file": "context.json",
    "context_file_sha256": sha(CONTEXT_BYTES),
    "run": {"as_of": AS_OF, "cutoff": CUTOFF},
    "bad_contexts": BAD,
}
MANIFEST_BYTES = dump(MANIFEST, 2)

# --- expected.json: derived from the manifest as written, not from the sources above ----------------------
M = json.loads(MANIFEST_BYTES)
C = json.loads(CONTEXT_BYTES)
assert C["run"]["cutoff"] == M["run"]["cutoff"] and C["run"]["as_of"] == M["run"]["as_of"]
assert sha(CONTEXT_BYTES) == M["context_file_sha256"]
assert M["research_manifest"]["file_bytes"] == dump(M["research_manifest"]["rows"], 1)
cutoff_d = date.fromisoformat(M["run"]["cutoff"])
effective = min(date.fromisoformat(M["run"]["as_of"]), cutoff_d).isoformat()
assert effective == CUTOFF

KEY_OF = {r["locator"]: k for r, k in zip(M["research_manifest"]["rows"], "ABCDE")}
accepted, refused, entries = [], [], []
for row in M["research_manifest"]["rows"]:
    key = KEY_OF[row["locator"]]
    pub = row.get("published")
    base = {
        "locator": row["locator"],
        "family": row["family"],
        "published": pub,
    }  # product order (O7-R48 H1)
    if pub is None:
        reason = f"undated evidence item refused: as_of {AS_OF} is before today"
    elif pub > effective:
        reason = f"evidence item {row['locator']} is after the cutoff"
    else:
        accepted.append(
            {
                "item_id": f"ev-{len(accepted) + 1}",
                "key": key,
                **base,
                "path": row["path"],
                "sha256": M["evidence_sha256"][key],
            }
        )
        continue
    refused.append({"key": key, **base, "path": row["path"], "reason": reason})
    entries.append({**base, "reason": reason})
entries.sort(key=lambda e: e["locator"])
assert [a["key"] for a in accepted] == ["A", "C"] and [r["key"] for r in refused] == ["B", "D", "E"]
REJECTED_BYTES = dump(entries, 1)
b_text = next(r["reason"] for r in refused if r["key"] == "B")

EXPECTED = {
    "schema_version": "cpdr-context-cutoff-expected/1",
    "derivation_note": "Built by cases/cpdr-context-cutoff/builder/build.py from manifest.json; hashes from embedded evidence bytes.",
    "cutoff": {
        "as_of": M["run"]["as_of"],
        "context": C["run"]["cutoff"],
        "effective": effective,
        "absent_effective": M["run"]["as_of"],
        "rule": "min(as_of, run.cutoff); absent run.cutoff is the as-of date (OD5)",
    },
    "intake": {
        "accepted": accepted,
        "accepted_ids": [a["item_id"] for a in accepted],
        "refused": refused,
        "refusal_texts": {
            "cutoff_b": {
                "text": b_text,
                "_source": "src/deploy_workflow/research/contracts.py:57-60 (CutoffViolation: 'evidence item {item_id} is after the cutoff'); "
                "a refused item has no ev-<n> id, so the locator stands for {item_id}, as in cases/cpdr-research-owner/expected.json#intake/refusal_texts/cutoff",
            },
            "undated_e": {
                "text": refused[2]["reason"],
                "_source": "src/deploy_workflow/research/intake.py:130 (holds for any run date after as_of)",
            },
        },
        "rejected_json": {
            "entries": entries,
            "file_bytes": REJECTED_BYTES,
            "file_sha256": sha(REJECTED_BYTES),
            "shape": "[{locator, family, published, reason}] sorted by locator",
        },
        "pack_sources": ["identity", "financial"] + [a["item_id"] for a in accepted],
    },
    "brief": {"cutoff": effective, "as_of": M["run"]["as_of"]},
    "brief_view": {"cutoff": effective},
    "context": {
        "refusals": {
            "cutoff_after_as_of": {
                "run.cutoff": M["bad_contexts"]["cutoff_after_as_of"],
                "problems": [
                    f"run.cutoff: is after the run as-of date ({AS_OF}); sources dated after it are refused."
                ],
                "_source": "src/deploy_workflow/context.py:436-439 (_Rules.date, after=True) with bad() at :394-395 prefixing the path",
            },
            "cutoff_malformed": {
                "run.cutoff": M["bad_contexts"]["cutoff_malformed"],
                "problems": ["run.cutoff: enter a date as YYYY-MM-DD."],
                "_source": "src/deploy_workflow/context.py:433-434 (_Rules.date) with bad() at :394-395",
            },
        },
        "absent": {"cutoff": ""},
    },
    "form": {
        "field": {
            "section": "s3",
            "data_k": "cutoff",
            "type": "date",
            "rule": "{t:'date', after:true}",
            "label": "Research cutoff",
        },
        "_note": '"s3" is the `fld` section variable and the id prefix (the field id is s3-cutoff), not the element id sec3 (O7-R48 L1)',
    },
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "manifest.json").write_bytes(MANIFEST_BYTES.encode("utf-8"))
(OUT / "context.json").write_bytes(CONTEXT_BYTES.encode("utf-8"))
(OUT / "expected.json").write_bytes(dump(EXPECTED, 1).encode("utf-8"))
print(f"wrote {OUT}")
