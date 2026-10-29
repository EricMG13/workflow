CP-3D round 13 fix round 1 (finding M1) is committed as 543376c on claude/r13-cp3d. The worktree was clean at a212da3 before I started, and the commit touches only `src/deploy_workflow/owners/cp3d.py` and `tests/test_method_cp3d.py`.

**Fix:** in `cp3d.py`, `_EDGE_AFTER` is now `("", ".", ",")`, and a new `_EDGE_BEFORE = ("", ",", ", ")` replaces the old `m.start() == 0` start-edge test with `needle[:m.start()] in _EDGE_BEFORE`. `_cut` is unchanged.

**Test:** `test_r13_m1_a_quote_edge_at_a_comma_beside_the_figure_is_an_edge` runs through `_MARGIN_CLASS`, the real `occurs` path, and has 8 cases.
- **Refused:** the six cases you listed (`fee of 1,` on `1,250`, `1, 250` and `1,\n250`; `,250 per year`; `, 250 per year`; `margin of 25,`). Each must give the pinned "bps_text <v> does not occur in the quote" issue.
- **Accepted twins:** `fee of 1,` on `1, payable yearly.`, and `, 250 per year` on `up, 250 per year`.
- **Red on a212da3:** I ran it before the fix. The 6 refusals failed and the 2 twins passed.

**Probes** (`<S>` = the scratchpad path you gave):
- `<S>/cp3d-r13-review/p_comma_edge.py` exits 0. It did not hardcode the copy path, so I ran it unchanged. All 6 cases and the control print as refused.
- `p_fuzz_join.py` reports `violations {'comma_edge': 0, 'other': 0}`. I piped its output through `tail`, so I didn't capture its own exit code.
- `<S>/cp3d-r13/mutants.py` exits 0 with 18 of 18 mutants killed. I added four mutants for the new edge forms: `edge-after-comma-dropped`, `edge-before-comma-dropped`, `edge-before-comma-space-dropped` and `edge-before-empty-only`.

**Gates (all exit 0):**
- pytest on `tests/test_method_cp3d.py` and `tests/test_defect_classes_selfcheck.py`: 1091 passed.
- `ruff check` and `ruff format --check`: clean.
- `MYPYPATH=src mypy --strict` on the two changed files: no issues.
- The frozen triples and refusal mutations are covered by that pytest run and still pass. I did not edit any frozen data, and `STAGE2_REFUSAL_DELTA` is unchanged.

Not verified: no run of the full suite or any other owner's tests. No cross-check against the lane's CP-1D edge behaviour beyond the listed cases. No run of the frozen triples outside the two pytest files. Items 7 and 8 were taken from your summary, not re-read in the lane ruling file.

agent=mx-feature fix-rounds=1 gates-first-pass=y