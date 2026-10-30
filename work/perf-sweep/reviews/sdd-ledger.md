# SDD ledger — plan: work/perf-sweep/product-plan.md
Authority: user's own word in this session (07:08Z 2026-10-30): "Yes, apply P1–P3". Base 2bbf633 (codex/checkpoint, Stage 4 release); Stage 5 not landed.
Spec: none beyond the plan; rulings provisional against the brief from Modules (outputs identical, before/after timings).

## Pre-flight scan
| Pair / task | Shared file or interface | Finding |
|---|---|---|
| P1 × P2 | none (earnings_workflow.py vs contracts.py) | independent |
| P1 × P3 | none (earnings_workflow.py vs execution.py); P1 runs after P3's reads | independent |
| P2 × P3 | P3 caches Module.model_validate_json, which runs validate_tables (P2) | independent; P3 measured after P2 |
| P1 self | plan text: _reference(producer_sha256, fact); callers :1704, :1725 | consistent |
| P2 self | plan asks guard = "frozen copy of today's function" in a test | conflicts with jscpd duplication gate → Ruling 2 |
| P3 self | plan says lru_cache(maxsize=32) | 233 MiB RSS per parsed CP-1 Module (probe) → Ruling 1 |

Ruling 1: P3 cache maxsize=4, not 32 — measured ≈233 MiB per parsed 44 MB CP-1 Module (3 parses: maxrss 75→773 MiB), 32 entries could hold ≈7 GiB — if wrong, fewer cache hits than possible; measure hits and RSS.
Ruling 2: P2 guard is a behaviour test of every validate_tables error message plus the pass case, not a frozen copy of the old function in tests — the copy would trip jscpd and freeze dead code; micro_trial.py stays the reviewer probe for old-vs-new identity on the real blob — if wrong, a subtle ordering difference on real data is caught only by the probe.
Ruling 3: P1+P2 go to one mx-feature dispatch (two commits; P1 guard test needs judgment to build a small real producer and report); one mx-precise review with per-task verdicts; P3 to mx-feature; mx-adversary reviews P1 (financial lineage) and P3 (store read path) — if wrong, one extra review round.
Ruling 4: per-change timing on the E-NO-YOY sentinel; the full heavy set only before all and after all — 4.4 h per heavy pass makes per-change heavy passes 13+ h — if wrong, per-change attribution on other heavy tests is inferred, not measured.
- Task 1 (P2+P1): implementer DONE_WITH_CONCERNS, commits 2ded26c (P2), 17e07ba (P1); agent=mx-feature fix-rounds=0 gates-first-pass=n/a (heavy earnings deferred)
- Task 2 (P3): implementer DONE, commit 4af08ce; agent=mx-feature fix-rounds=0 gates-first-pass=n/a (heavy earnings deferred)
- Task 1 review (mx-precise): P2 Spec ✅ Approved, P1 Spec ✅ Approved; 0 High/Medium
- Task 1: minor (deferred): tests/test_validate_tables.py lacks a declared table with no facts (contracts.py:287 default unpinned)
- Task 1 (P2): complete (commits b0ac40c..2ded26c, review clean)
- Task 2 review (mx-precise): Spec ✅ Approved; 0 High/Medium
- Task 2: minor (deferred): execution.py:543 ponytail ceiling omits raw bytes held by the lru key (~1.1 GiB worst case); key on sha256 only would avoid
- Adversary review (mx-adversary): P1 approve, P3 approve; 0 High/Medium; L1 shared-Module comment, L2 memory figures (≈322 MiB/entry; host+base 2.58 GiB) deferred to Low batch
- Task 1 (P1): complete (commits 2ded26c..17e07ba, review clean)
- Task 2 (P3): complete (commits 67e0c51..4af08ce, review clean)
- Ruling: P3 keeps the (sha256, raw) lru key; only the comment is corrected — keying on sha256 alone needs a hand-written cache (host.py style), more code for ≈168 MiB — if wrong, ≈42 MiB per entry stays pinned.
- Ruling: cases/cpos-owner pins of src/deploy_vii/contracts.py go to the owner, not this branch — cases/ is outside the approved scope and the pin was not read by any test; sibling pins there were already stale at base — if wrong, the cpos-owner builder provenance shows a stale contracts.py hash until re-pinned.
- Task 3 (Low batch: L1+L2 comment, P2 empty-table test): DONE commit 66cce2a; mutant ids_by_table[...] → KeyError, reverted; agent=mx-scaffold fix-rounds=0 gates-first-pass=y (17 passed)
- Ruling: whole-branch review runs after the Stage 5 merge, on the final tree, by mx-precise (no Fable: user stopped Fable use in LEAD lane 2026-10-28) — if wrong, a cross-task issue surfaces later than it could.
- Ruling: no rewrite-tournament — P1 is a hoist, P2 a precomputed dict, P3 a cached wrapper of an unchanged body; all trivial by the skill's own exemption and probe-proven identical — if wrong, a simpler form of _canonical_result is missed.
- Final whole-branch review (mx-precise): APPROVE, 0 High/Medium; Low 1–4 (docs) fixed by the controller: progress RSS range, product-plan memory note, CONTRACT authorization, identity log saved (work/perf-sweep/identity-E-NO-YOY.txt).
- Ruling: no heavy/fast tier markers — work/build/keep/fast-set.txt already is the per-change fast set (10,360 passed in 5m10s); markers would duplicate it — if wrong, Modules adds markers later.
