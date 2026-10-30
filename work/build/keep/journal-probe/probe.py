"""Stage 6 journal probe: stored CP-1 source-context payloads vs OI-14/OI-20 (read-only).

Stores: directories holding `current`/`snapshots/`/`blobs/` (deploy_vii.execution.Execution).
Every snapshot file is read; CP-1 attempts' `source_context` steps (and step_repairs) are
loaded via Execution.payload and validated against Execution.pack(snapshot). JSON files are
walked for embedded SourceContextReview payloads (dicts or JSON strings); those are validated
against any collected pack with the same content hash, else only the OI-14/OI-20 blank checks
run. Every error is recorded and reported, never swallowed. Exit 1 if any payload fails a
blank check, 0 otherwise.
"""

import hashlib
import json
import os
import re
import sys
from collections import Counter
sys.path.insert(0, "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/src")
from pathlib import Path

from deploy_vii.execution import Execution, ExecutionSnapshot
from deploy_vii.prose import is_blank
from deploy_vii.source_context import SourceContextReview, source_context, validate_source_context

WT = Path("/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees")
LANE = WT / "module-dev-status-review-0981b6"
TMP = Path("/private/tmp/claude-501")
PRUNE = {".venv", ".git", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
BLANK_PREFIXES = ("Empty limitation text", "Empty event scan explanation")


def location(path: Path) -> str:
    s = str(path)
    if s.startswith(str(LANE / "cases")):
        return "lane/cases (control)"
    if s.startswith(str(LANE / "tests")):
        return "lane/tests"
    if s.startswith(str(LANE / "work/build/keep")):
        return "lane/work/build/keep"
    if s.startswith(str(LANE)):
        return "lane/other"
    if s.startswith(str(WT)):
        rel = Path(s).relative_to(WT).parts
        sub = rel[1] if len(rel) > 1 else ""
        return f"other-worktrees/{sub if sub in ('cases', 'tests', 'work') else 'other'}"
    return "scratchpads"


def blank_issues(review: SourceContextReview) -> list[str]:
    out = []
    for e in review.entities:
        out += [f"Empty limitation text: {e.entity_id}" for t in e.limitations if is_blank(t)]
    for s in review.sources:
        for sc in s.scopes:
            out += [f"Empty limitation text: {sc.scope_id}" for t in sc.limitations if is_blank(t)]
        out += [f"Empty limitation text: {s.source_id}" for t in s.limitations if is_blank(t)]
        if is_blank(s.event_scan_explanation):
            out.append(f"Empty event scan explanation: {s.source_id}")
    out += ["Empty limitation text: review" for t in review.limitations if is_blank(t)]
    return out


def walk(roots):
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in PRUNE]
            yield Path(dirpath), dirnames, filenames


roots = [WT] + sorted(p for p in TMP.iterdir() if p.name.startswith("-Users-ericguei-Documents-Deploy-Workflow"))
stores, jsons = [], []
for d, dirnames, filenames in walk(roots):
    if "snapshots" in dirnames and "blobs" in dirnames:
        stores.append(d)
        dirnames[:] = [x for x in dirnames if x not in ("snapshots", "blobs")]
    for f in filenames:
        if f.endswith(".json"):
            jsons.append(d / f)

packs = {}  # pack content hash -> PreparedPack
results = []  # (kind, path, loc, status, validate_issues, blank, rebuild_error)
errors = []
store_counts, store_payloads = Counter(), Counter()
seen_store_payloads = set()

for d in stores:
    store_counts[location(d)] += 1
    ex = Execution(d)
    for snap_path in sorted((d / "snapshots").glob("*.json")):
        try:
            snap = ExecutionSnapshot.model_validate_json(snap_path.read_bytes())
        except Exception as err:  # recorded and reported below
            errors.append((str(snap_path), f"snapshot unreadable: {type(err).__name__}: {str(err)[:160]}"))
            continue
        for att in snap.attempts:
            if att.module_id != "CP-1":
                continue
            for step in (*att.steps, *att.step_repairs):
                if step.step_id != "source_context":
                    continue
                key = (str(d), step.payload_sha256, step.status)
                if key in seen_store_payloads:
                    continue
                seen_store_payloads.add(key)
                try:
                    pack = ex.pack(snap)
                    packs[pack.content_hash()] = pack
                    review = SourceContextReview.model_validate_json(ex.payload(step.payload_sha256))
                except Exception as err:
                    errors.append((f"{d} blob {step.payload_sha256}", f"{type(err).__name__}: {str(err)[:160]}"))
                    continue
                store_payloads[location(d)] += 1
                issues = validate_source_context(pack, review)
                rebuild = None
                if step.status == "valid":
                    try:
                        source_context(pack, review)
                    except ValueError as err:
                        rebuild = str(err)[:300]
                results.append(("store", f"{d} payload {step.payload_sha256} ticket {att.ticket_id}", location(d), step.status, issues, blank_issues(review), rebuild))


def embedded(value, path=""):
    if isinstance(value, dict):
        if {"entities", "sources", "pack_sha256"} <= value.keys():
            yield path, value
        for k, v in value.items():
            yield from embedded(v, f"{path}/{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from embedded(v, f"{path}[{i}]")
    elif isinstance(value, str) and '"event_scan_explanation"' in value:
        try:
            yield from embedded(json.loads(value), path + "(str)")
        except ValueError:
            pass


json_counts, json_payloads = Counter(), Counter()
seen_json = {}
for p in jsons:
    try:
        raw = p.read_bytes()
    except OSError as err:
        errors.append((str(p), f"unreadable: {err}"))
        continue
    if b"event_scan_explanation" not in raw:
        continue
    json_counts[location(p)] += 1
    try:
        data = json.loads(raw)
    except ValueError as err:
        errors.append((str(p), f"bad JSON: {err}"))
        continue
    for sub, value in embedded(data):
        value = dict(value)
        placeholder = not re.fullmatch(r"[0-9a-f]{64}", str(value.get("pack_sha256")))
        if placeholder:  # run-time-bound template; no pack can match, blank checks only
            value["pack_sha256"] = "0" * 64
        try:
            review = SourceContextReview.model_validate_json(json.dumps(value))
        except Exception as err:
            errors.append((f"{p}{sub}", f"not a SourceContextReview: {str(err)[:160]}"))
            continue
        json_payloads[location(p)] += 1
        digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        seen_json.setdefault(digest, []).append(str(p))
        pack = packs.get(review.pack_sha256)
        issues = None if pack is None else validate_source_context(pack, review)
        results.append(("json", f"{p}{sub}", location(p), "template" if placeholder else "recorded", issues, blank_issues(review), None))

print("== stores by location:", dict(store_counts))
print("== CP-1 source_context store payloads by location:", dict(store_payloads))
print("== JSON files mentioning event_scan_explanation by location:", dict(json_counts))
print("== embedded SourceContextReview payloads in JSON by location:", dict(json_payloads))
print("== distinct JSON payloads:", len(seen_json), "packs collected:", len(packs))
bad = 0
for kind, path, loc, status, issues, blank, rebuild in results:
    other = [] if issues is None else [i for i in issues if not i.startswith(BLANK_PREFIXES)]
    if blank:
        bad += 1
        print(f"FAIL-BLANK [{loc}] {kind} {status} {path}\n    blank: {blank}\n    rebuild: {rebuild}")
    if status == "valid" and other:
        print(f"VALID-NOW-OTHER [{loc}] {path}\n    {other[:5]}")
    if issues is None and kind == "json":
        pass
nopack = sum(1 for r in results if r[0] == "json" and r[4] is None)
print("== json payloads without a matching pack (blank checks only):", nopack)
print("== status counts:", dict(Counter((r[0], r[3]) for r in results)))
for where, what in errors:
    print("ERROR", where, what)
print("== blank failures:", bad, "errors:", len(errors))
sys.exit(1 if bad else 0)
