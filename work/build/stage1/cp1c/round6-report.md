# CP-1C follow-up (round 5 P1 and round 6 B1): controller-saved

- **Commit:** `74a2c72` on `worktree-cp1c-stage1` (parent 1696f5a).
- **Tests:** 120 passed. 14 of the 15 new tests failed first for the reported causes. The wrong-unit test guards behaviour that already existed.
- **Gates:** all three exit 0. The first ruff run failed on ISC004, so the gates did not pass on the first run.

## Rulings → tests
| Ruling | Test(s) |
|---|---|
| P1 | `test_round5_p1_not_ready_peer_source_own_line` |
| B1 `_cp1_facts` | `test_b1_known_cp1_fact_with_the_wrong_unit_still_raises` |
| B1 `_Composer.copy` (the latent defect) | `test_b1_copies_carry_cp1_status_and_limitation` |
| B1 T1C.4; peer statistics unchanged | `test_b1_peer_statistics_unchanged_and_issuer_cells_not_compared` |
| B1 T1C.5 issuer | `test_b1_issuer_outlier_cells_use_the_issuer_wording` (`ISSUER_NOT_STATED`, `ISSUER_NOT_MEANINGFUL`) |
| B1 T1C.6 | `test_b1_tie_out_not_compared` |
| B1 claim | `test_b1_claims` |
| B1 own line | `test_b1_own_lines_follow_the_peer_source_lines_in_metrics_order` |
| B1 precedence | `test_b1_precedence_no_peer_source_then_median_missing` |
| B1 probe | `test_b1_probe_payload_is_refused_not_raised` |

## Probes
- `stage1-review-B/probe_b1_cp1c_cp1_ratio_not_known.py` now exits 1. That is the expected result: its semantics are inverted, so 1 means no crash. `calculation_issues` returns `('Figure reference names a gap: T1C.3.issuer.interest_coverage_adjusted',)`.
- probe3 to probe8 exit 0. probe4 ran 2000 valid seeds.
- `cp1c-r6/new_strings.py` exits 0, with no `prose.issues` or `bare_figures` hits.

## Choices
**To LEAD:**
1. The own-line label is used as it stands ("Adjusted EBITDA margin"). The module's other mid-sentence lines lower-case it.

**Confirmed by the controller:**
2. The B1 claim sentence is skipped when the median is missing or there is no peer source, following the 1C1 order.
3. The own line is emitted whenever the CP-1 ratio is not known, including in the no-peers state.
4. A CP-1 fact that is `conflicting` or absent still raises (fail closed).
5. Unsettled copies keep CP-1's currency, scale, decimals, value_class and calculation_id verbatim. An unsettled non-None unit that differs from the metric's is copied verbatim, because round 4 (f) checks units on known facts only.
6. CP-1's limitation goes verbatim inside the parentheses, so a CP-1 limitation with digits could produce a bare figure.

Not verified:
- No oracle case pins B1, so the new cells, claim and own line are checked against the ruling text only.
- No mutation run on the new code.
- The full suite was not run.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
