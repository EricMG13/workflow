# Owner list closures (one line per `work/build/stage2/lows.md` entry not already marked Closed, plus item 64's user items)

Modules folds these into `lows.md` when it merges `claude/open-items-fd69c5`. "closed by <sha>" = fixed (the commit is in the lane); "decided" = left, with the ruling; "builds" = this branch.

## Already closed in the lane before this session (owner list not updated)
- [G1-X guards] Low, test gap (`==`→`<=`): closed by 0e4fd3f (`tests/test_owner_g1x.py:604-614`).
- [G1-X guards] Info, docstring lengths (:563/:565/:566): closed by 0e4fd3f (reflowed); the three other >100-character lines ride with B3.
- CP-2E (fix1 re-review) Info (a) stale docstring: closed by 0e4fd3f. (b) `Cite`/`Cites` copy/asdict: decided, OI-3. (c) empty summary two issues: B2.
- CP-2A (close release, lease text): closed by a70ee52 (`docs/CP2A-OWNER-LEASE.md:69`).
- CP-2A Low (forged `Upstream`): decided, OI-4.
- Shared defect test Info (`test_defect_classes_selfcheck.py`): closed by acdaee7 (:543-554, `TWO_NOTES`).
- CP-8 L-a: closed by acdaee7 (`tests/test_owner_cp8.py:214-217`).
- CP-8 L-b: closed by acdaee7 (`tests/test_owner_cp8.py:220-259`) with the lease note a70ee52 (`docs/CP8-OWNER-LEASE.md:87`).
- CP-1D L1 (ordinal window): closed by 545e28a (`owners/cp1d.py:644-648`; `tests/test_method_cp1d.py:1336-1339`).
- CP-1D L2 (surviving mutants): closed by acdaee7 (`tests/test_connect_cp1d.py:727, :744, :767`).
- CP-1D L3 (tamper spy, edited output): closed by acdaee7 (`tests/test_owner_cp1d.py:361-381`).
- CP-1D L5 (`type: ignore` in cp1d tests): closed by acdaee7 (none left; totals 13/5).
- CP-1D L6 (note vs core): closed by 545e28a (note aligned to ruling B3; `tests/test_connect_cp1d.py:1111`).
- CP-1D I1 (`context_block` docstring): closed by c824206.
- CP-2G Info (`next(...)` StopIteration): closed by 545e28a (`owners/cp2g.py:3182-3184`; `tests/test_connect_cp2g.py:740`).
- CP-2D (protocol §6): closed by 545e28a.
- Tests (`drive_cp1` literal; cp3c/cp4 duplicates): closed by 0e4fd3f (`tests/s1a_runs.py:282-324`; thin wrappers).
- CP-1D (protocol §6, Info): closed by 545e28a.
- CP-3D (protocol §6): closed by 30a1f7a (`owners/cp3d.py:2126-2138`).
- Owner (predates, D12) `bindings/shipped.py` sha: closed by 5977ae4; the last shipped.py record has carried 8cd0dbc9 since then, and 5c71a311 is the next (report_view) record. The W1 finding was a false positive.
- Stage 3 review (item 22) ruff `financial_workflow.py` 439, 446: closed by 3d93a4c.
- (item 64) G2 R2.5 secondary pointers for cp3d, cp4, cp8 and the `cites` normaliser: closed by 715f5a4 (items 44-48; genuine reruns item 50).
- (item 64) the 11 CP-3C promotion tests: ran green in Stage 5.1 s5 (62 passed with cp3; gated on `CP3C_STORE_RUNS=1`). Stale docstring `tests/test_owner_cp3c.py:11` rides with B1.

## Built on this branch
- Owner (predates, D12) report_view records 3e5b537, 24f879a, 8aef58d (item 22) and (5.3 lens B Low 1) the LEAD records cffdf9f ×9, 1a1a140, bb4553b ×2: closed by a8eb490 (merge 0fc097c; OI-6, OI-17); strict probe df26ea8..HEAD exit 0.
- CP-1 chart oracle `cases/charts/expected.json` not pinned: closed by 1efec9b (merge 0fc097c; OI-7); PINS 87.
- (items 12, 19, 64) DR.6 "Not computable" chip xfail tripwire: closed by 2d12ea5 (RED 2eba590, D12 0abbab9; merge 3236818; OI-13, the user directly).
- CP-2E (fix1 re-review) Info (c) empty summary gets two issues: closed by f589c14 (RED c2d643e; merge of claude/oi-b2-validators); CP-3D's copy by a55a897 (OI-18).
- Owner (predates, Info) well-formed unresolved reference passes the CP-3D validator (CP-DR's copy closed in item 73): closed by f589c14 (OI-1).
- CP-DR (item 73 review, Info, predates) `validate_research` order docstring: closed by f589c14.
- (found by triage, same class as the CP-2D/1D/3D protocol §6 entries) CP-2A `_validate_step` raw `model_validate_json`: closed by f589c14 (OI-2).
- Owner (predates, Low) CP-1 accepts a blank scope or source limitation: closed by c34f81a (RED 84229e8; merge 8b7207a; OI-14, the user directly). Entity and review limitations are covered too.
- (Stage 4 review Info 1) `_verify_publications`: a failed CP-MODEL publication's issues and interruption are not replayed: closed by 3fdda57 + da2bb04 (fast RED e3874bc, cc49257; merge of claude/oi-b3-verifier; OI-5). The interruption text itself stays the forger's choice within the producer's bounds (OI-5 residual).
- [G1-X guards] Info, the three remaining >100-character lines in `owner_workflow.py` (:12, :211, :259): closed by 3fdda57.
- Stage 4 owner fixes (item 41/43) `tests/defect_classes.py:858`, `:863` mypy "Cannot infer type of lambda": closed by e585af3 (merge of claude/oi-b1-tests).
- Stage 3 review (item 22) ruff `tests/test_legal_render.py:220` and Stage 3 Low L1 (item 32) `tests/test_cp1_chart_render.py` FURB157 ×4, C408 :433: closed by 81fd883.
- (5.1 s0, l3, l2) always-skipped "blocked on G2" placeholders `test_owner_cp4c.py:615`, `test_owner_cp4.py:497`, `test_owner_cp2h.py:640`: closed by 89eb960 (OI-8; each comment names its G2 genuine cases).
- (item 64, stale docstring) `tests/test_owner_cp3c.py:11`: closed by a1d5c7b.
- (item 62 Low) `tests/test_shell_css.py:9` first-block parser: closed by 71fc5a3, 51bf88c, 9586860 (RED 8139d49, c9b4746, 24fcdd9; OI-9, OI-19).
- (B6 review Info, OI-20) a blank `event_scan_explanation` passes `validate_source_context` and renders a blank `event_scan` gap row: closed by 4b2fcc2 (RED b6f3469, D12 236260e; merge 8dafc41; OI-20, the user directly).

## Decided
- CP-2E Info (b) `Cite`/`Cites` copy/asdict: OI-3.
- CP-2A Low forged `Upstream`: OI-4.
- (item 35) cp2d plain-string `tabs`: OI-10.
- `financial_workflow.py:914` RUF100 (Stage 3 item 22 :768): CZR-blocked, OI-11.
- (5.3 round 3) `report_view.py` SIM102 and (item 22) `statement_extract.py` TRY004: OI-16.
- (item 55) rewrite-tournament readability rewrites: OI-15 (the user, "Leave unapplied").

## Needs the user
None left: OI-20 was approved by the user and built (B7).
