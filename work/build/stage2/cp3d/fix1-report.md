# CP-3D fix round 1 report (mx-feature)

CP-3D fix round 1 is committed as 9d74fc7 on claude/s2-cp3d, on top of d8c3512. All the fast gates and the reviewer's probes pass. The store-run file ran for the first time and 39 tests pass in 3.6 s.

**M1, citation quotes: fixed**
- The cause was `page_quotes` keeping the first submitted quote per page for every fact on that page.
- I changed the Stage 1 composer to carry provenance per cell:
  - `_trace` now returns `Cites`, a tuple subclass.
  - It compares equal to the plain page-pair tuple, so the oracle's page-level cites and every frozen test are unchanged.
  - It also carries each page's supporting submitted quotes, in order.
  - Claims merge their cells' quotes.
- `page_quotes` is removed. `cite_of(pack, cites, pair)` cites the cell's own quote and raises if the cell has none.
- How derived facts are cited: a derived fact (discount margin, price metrics, default intensity, yield) rests on several input quotes. It gets one `Citation` per page, which keeps the page-level cites unchanged. The quote is the first of its own input quotes on that page, for example the bid quote for T3E.3.r03.mid, with the margin quote on the financial page. No quote is invented. A test pins this rule.
- A quoted reference rate level now cites its own quote on all three T3E.3.r04 facts.
- New tests, which failed against d8c3512: 5 of the new tests failed there, at the first run. They cover each terms fact's own quote, observation and margin quotes, the quoted-level case, the technicals' basis quotes, `Cites` itself, and the fail-closed missing-quote case. There is also a passing invariant that every citation quote is one the submission gave for that page.

**M2, lease Acceptance 5 and 6: written and run** (all in `tests/test_owner_cp3d.py`, each a few seconds)
- `begin` refused when CP-0 settles blocked: no CP-3D attempt is consumed and the refusal is retained.
- `stale_binding`.
- A consistent-forgery probe tamper. The forged step output is stored under its own hash and the attempt names it, so only `probe` refuses it with `identity_mismatch`. The genuine attempt passes the same call.
- Not written: `begin` refused on a stale CP-0. The blocked-CP-0 test is the only edge-`block` test.
- I dropped a probe test on a changed attempt number. `settle` raises a plain `ValueError` there, not `identity_mismatch`. This is shared `probe_one_step` behaviour, so CP-1A and CP-2 have it too.

**L1 and L2**
- Added tests for:
  - each absence path alone (R1–R3, R5);
  - the reader refusing a head with a missing pinned fact (D2);
  - the reader refusing another module's head even when the facts are present (D1);
  - `_settle` refusing a step output that differs from the trusted validation (S1);
  - `_third_party` reading only the T3 authority fact (A1).
- C3: `page_quotes` is gone, so that mutant no longer exists. The new technicals test covers the same ground.
- L2: the blank-quote inventory now uses a literal that has a level, so it covers the eighth site, `terms.reference_rate.level.quote`.

**Probe exit codes** (run with the venv python)
- `p_citation_wrong_quote`: 0
- `p_blank_all_sites`: 0
- `p_cited_refs_equiv`: 0 (28 compared, 0 differences)
- `p_rules_each_absence`: 0
- `p_mutants`: 0. R1–R3, R5, D1, D2, A1, S1 and C3 are killed. Four mutants survive and the reviewer already listed them as equivalent: R7, D3, S4, B1. C1 and C2 did not apply, because `page_quotes` is gone. I replaced them in `<S>/cp3d-s2/mutate.py` with M1 mutants: last-quote-instead-of-first, wrong cite for amortisation and for the instrument, technicals basis dropped, and the L1 mutants. All 40 of those mutants are killed.

**Gates**
- pytest over `test_connect_cp3d`, `test_method_cp3d`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck` and `test_owner_cp3d`: 1320 passed.
- `ruff check` and `ruff format --check` on the changed cp3d files: exit 0.
- `mypy --strict` on those files plus the tests: exit 0.
- Frozen cases: `test_method_cp3d` passes unchanged, with 868 tests and every oracle value and refusal intact. `STAGE2_REFUSAL_DELTA` is untouched.

**For LEAD: a finding from the first real store run**
- The store's settlement (`execution.settle` with `case_kind` synthetic, `execution.py:475`) appends "Synthetic case; not real issuer qualification" to the settled module's own `limitations`. It removes the same line from `inherited_limitations`.
- The oracle's `expected.json` own and inherited lists are the candidate's, before that step. Because of this, the head module has the oracle's own limitations plus that line, and the oracle's inherited list minus it.
- `test_owner_cp3d.py` asserts this behaviour. The oracle itself is unchanged.

Not verified: the FP03 render of the `market-against-fundamentals` block. The full suite. The PR size gate. `begin` refused on a stale CP-0. Real `Execution.finish` settlement for `submit` on an invalid first attempt that is repaired as attempt 1 (only the blocked and refusal cases ran). The reader on a stale or blocked head (the reviewer's Info on this stands). The pending `sources == _OWNER_SCOPES` guard commit, which is not in this tree. A reader-over-real-store test beyond the three closed cases.

agent=mx-feature fix-rounds=1 gates-first-pass=n (the first mypy run failed on a test assertion and the first ruff run failed on a lint in the new composer code; the 5 new M1 tests failed first as intended)
