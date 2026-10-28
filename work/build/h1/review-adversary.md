# H1 adversary review (mx-adversary; controller-saved)

# H1 adversarial review: `git diff 181e633 2bd61a7` (host.py, tests/test_host_h1.py)

**Verdict: CHANGES REQUIRED.** The code holds under every attack I ran. No scope escape, no byte leak, no forged tail passing, no stale or poisoned memo entry, and the live path behaves exactly as at base. Two Medium findings remain:
- **F2** is a test defect inside this diff and can be fixed inside the brief.
- **F1** is a conflict between the specs and needs a ruling from LEAD.

The target worktree is clean at `2bd61a7`; I edited nothing. All probes and mutant runners are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-review/`, referred to below as `<R>/`. Run them from a worktree root with `PYTHONPATH=src:tests:<R>`.

## Gates (target root)
| Gate | Exit |
|---|---|
| `pytest tests/test_host_h1.py tests/test_owner_g1x.py` | 0 (33 passed) |
| `ruff check` on both files | 0 |
| `ruff format --check` on both files | 0 |
| `MYPYPATH=src mypy --strict src` | 0 (111 files) |

## Findings

### Medium

**F2: the forged-tail tests never reach the tail checks.** `tests/test_host_h1.py:547-564` and the checks at `host.py:606` and `:611`.
- `test_forged_settled_tail_is_refused` changes only the head and the attempt's `result_sha256`. The settle replay (`host.py:615-623`) refuses every variant before the tail checks matter.
- Three checks at the heart of Q6 (b) can be deleted with the suite still green:
  - M24: `len(tail) != 1` → `< 1`
  - M25: drop `endswith("-submission")`
  - M26: drop the tail digest check
- Failure scenario: someone calls `Execution.submit_step` with a bypass validator, then `Execution.finish` with a candidate they built (tail digest wrong, tail id wrong, or two tails). Only those three checks refuse it. A regression that drops any of them ships undetected.
- `<R>/p02_producer_forgery.py` builds exactly these journals. It exits 0 on the target, and exits 1 under each of M24, M25 and M26.
- Fix: add the p02 variants (self-consistent journals) to the test.

**F1: settled owner-only producers are always refused, but leases say the rule covers them.** `host.py:608`, open point 4.
- Q6 as written uses `STEPS[step.step_id]`, so a settled owner-only producer raises `KeyError`. `_execution_state` maps that to `identity_mismatch`.
- `<R>/p05_owner_producer.py` (exit 0) settles a CP-3D head with the lease's `market-implied-submission` tail and gets `KeyError 'market_implied'`.
- The same probe shows which consumers bind owner-only producers when co-planned:
  - CP-3 binds CP-1C, CP-2H, CP-2G, CP-1D, CP-3D, CP-3C, CP-4C and CP-2D.
  - CP-4 binds CP-1D.
  - CP-3D binds CP-2H.
  - CP-1B is a live-contract module whose step `earnings_delta` is not in `STEPS` either; CP-1D binds it.
- `docs/CP3D-OWNER-LEASE.md:46` says the generic rule "covers CP-3D's tail". The CP-4C lease reads owner-only CP-2A and CP-2G heads.
- So the implementer's "No producer in today's rows hits it" holds only until the first owner-only producer is registered and co-planned with a sourced consumer.
- It fails closed, but it blocks those Stage 2 runs. The brief pinned Q6 "as written", so this needs a ruling from LEAD rather than a fix by the implementer. One option is the `_fill` pattern: `STEPS[s].schema if s in STEPS else _CORES[m].SCHEMAS[s]`.

### Low (test gaps; the code is correct)
- **L1** `host.py:740-745`. M07 (remove the live-contract guard in `_owner_sequence`) survives. `test_owner_scope_never_applies_to_a_live_contract_module` (:472) refuses only because CP-1A has no `_CORES` entry. `<R>/p01_scope.py` registers a core for CP-1A, which isolates the guard and kills M07.
- **L2** `host.py:750-751`. M10 (no str check) and M11 (no distinct check) on `STEP_IDS` survive. p01 kills both.
- **L3** `host.py:589`. M15 (drop `len(selected) != 1`) survives. Without that line, a producer with no producing attempt raises `IndexError`, which is not in the except tuple at :887, instead of refusing. `<R>/p03_memo.py` kills it.
- **L4** memo at `host.py:638-651`. Four mutants survive the suite; p03 (exit 0 on the target) kills all four:
  - M33: failures cached (a miss returns the real verdict, a later hit returns True)
  - M35: key on the snapshot only
  - M36: key on the producer only
  - M37: no eviction
  
  The brief names "passes only" and the (snapshot, producer) key, but no test pins either.

### Info
- **I1: composition is not authenticated.** A head finished with a hand-built candidate (a forged limitation) over the genuine submission and tail passes Q6 (b) (p02 "content forged, genuine tail": new rule True). Only the receipt verifier's `_PROBES` rebuilds composition. LEAD should confirm this is the intended boundary for the host.
- **I2: interruption-blocked producers are refused.** `<R>/p04_blocked_width.py` (exit 0): a validator-blocked CP-1A head passes both rules; an interruption-blocked head passes the old rule and fails the new one. The cause is the replay itself, not only the check (M17 is equivalent: `settle` is called without `interruption`). This is narrower than Q6's prose "keeps today's acceptance of blocked producers". It is latent: G1 interrupts only CP-MODEL publication.
- **I3: the p05 exit-1 claim is confirmed.** `p05_open_items.py` exits 1 at both base `181e633` and the target, from `owner_workflow.py:582` (`_ENTRY_VALIDATORS`). Part 5 output is identical at both. `p05h1_part5_mapped.py` and `p00_cp1a_cheap.py` both exit 0.
- **I4: no stubs, no new catch-alls.** `host.py` has no stub. The diff adds no catch-all: the `try/except ValueError` at :740 is narrow control flow. Mapping `KeyError` to `identity_mismatch` is the existing :887 tuple and fails closed.

### Attacks that held
- **Scope** (p01, exit 0):
  - CP-3D refuses `not_permitted` for: reading identity, a search scoped to identity, `extract_statements`, an unknown source and an unknown tool.
  - An unscoped search surfaces only market and financial.
  - An `unreadable` market source that carries spans answers `unavailable`, and its bytes never appear in search.
  - CP-1D's scope is (identity, financial, bridge) on the positive pack and (identity, financial) on the statements_only pack.
- **Live path** (`<R>/p06_live_path_equivalence.py`, exit 0): base and target `_execution_state` give identical outcomes for CP-0 `source_readiness`, CP-1A `business_context`, CP-1 `source_context`, wrong step, wrong order, unknown ticket and a missing pack blob.
- **Memo** (p03): with 8 threads over 40 keys there were 0 errors and the memo stayed at 16. A complete store copy hits; a copy missing a touched blob refuses.

## Mutant table (40 mutants of host.py, full copies)
- **Killed by the suite:** M01–M06, M08, M13, M14, M29, M32, M34, M38, M39, M40.
- **Survived, killed by review probes:** M07, M10, M11 (p01); M15, M33, M35, M36, M37 (p03); M24, M25, M26 (p02).
- **Survived, equivalent:**
  - M09: an empty sequence is refused by the length check anyway.
  - M12: owner modules have no `WITHIN_ATTEMPT_REPAIR`.
  - M16: a pending attempt is never selected.
  - M17: the replay refuses an interruption anyway.
  - M18, M19, M21, M23, M27, M28, M30, M31: implied by the replay or `finished == attempt`.
- **Survived, matter only for self-consistent forgeries:** M20 (a reordered prefix) and M22 (a multi-step attempt). A p02-style test would cover them.

The first-batch M33 forced `True`, so the suite killed it; the table uses the corrected rerun. Runner: `<R>/mutate_h1.py`. Outputs: `<R>/mutants_*.out`.

## Implementer's open points
1. **Held-but-not-ready sources in scope:** not a defect (p01 shows no bytes leak). Question for LEAD: the same not-ready source answers `unavailable` for CP-3D and CP-1D but `not_permitted` for CP-DR, and CP-3's live scope filters to ready sources. Pick one convention.
2. **CP-1D statements_only:** not a defect. It matches lease :30 and the manifest `plan.host_scope`.
3. **Unmapped sourced steps fail after writes:** G1-side follow-up. p05 part 5 reproduces it at both base and target: CP-3D begin is written, then the CP-0 submit raises and the workflow is left bound to CP-3D with a CP-0 session.
4. **Owner-only producers refused:** a real gap (F1); needs a ruling from LEAD.
5. **`STEP_IDS` must be a tuple:** G1-side follow-up. `_check_steps` accepts any iterable, so a list passes create and then fails at `_activate` after begin is written. Only `cpl10` defines `STEP_IDS` today (a tuple); cp1d, cp3d and cpdr define none yet.
6. **Other leases name H1 rows:** question for LEAD. Confirmed by grep: CP-2E (financial), CP-4C (financial and legal-covenants), CP-8 (prior_case, update, market_update).

## Points for LEAD
- Rule on F1 before any CP-3, CP-4 or CP-3D Stage 2 run co-planned with an owner-only producer.
- Confirm the I1 boundary.
- Confirm or amend Q6's blocked-producer prose given I2.
- Open points 1 and 6.

Not verified: `tests/test_source_tools.py`, `tests/test_source_workflow.py`, `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` were not run (deferred by the build-first rule); there was no CP-3 or CP-1D session and no CP-4 session or CP-2/CP-4 producer under the new rule (each needs a promoted CP-1), so CP-3's third_party scope was not exercised; CP-3D and CP-DR ran only with test fake cores, not the real Stage 1 cores; the memo was not exercised through the receipt verifier; there was no end-to-end owner run; the mutants cover only host.py, not the test file.
