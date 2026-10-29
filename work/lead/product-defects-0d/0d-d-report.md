# 0d-d report (implementer, uncommitted on lead/0d-d, base 2258d47; `git rev-parse HEAD` matched)

No pytest, no commit, no `cases/` or `src/deploy_workflow` change. Tests were called directly from a runner script (scratchpad `run/run.py`, which puts this worktree's `src` and `tests` on `sys.path`).

## RED (unedited source; every case fails by timing, not by error)
| case | bound s | HEAD s | fix s |
|---|---|---|---|
| shape | 0.5 | 8.02 | 0.052 |
| absence | 0.1 | 0.78 | 0.000 |
| gaps | 1.5 | 5.33 | 0.047 |
| attach | 0.5 | 2.14 | 0.054 |
| refs | 2.0 | 5.38 | 0.222 |
| scans | 1.0 | 2.20 | 0.409 |
| cp1a_sources | 0.2 | 2.22 | 0.009 |
| cp1a_consumers | 0.2 | 2.38 | 0.003 |
| cp1a_conflicts | 0.2 | 2.42 | 0.007 |
| cp1a_translations | 0.2 | 7.26 | 0.010 |
| prefill_books | 2.5 | 11.68 | 0.668 |
| prefill_fx | 1.5 | 5.04 | 0.695 |
| prefill_fxrow | 1.0 | 4.64 | 0.180 |
| prefill_scopes | 2.0 | 5.00 | 1.136 |
| prefill_periods | 1.5 | 4.38 | 0.657 |
| cp4_documents (L1) | 0.2 | 2.06 | 0.002 |
| cp3_instruments (L2) | 0.2 | 2.14 | 0.058 |
| cp3_ordering (L3) | 0.2 | 1.30 | 0.005 |

- End to end: `test_invalid_context_submit_is_linear_end_to_end` HEAD 7.62 s, fix 0.37 s (bound 2.0). `test_absence_claim_submit_is_fast_end_to_end` HEAD 7.58 s, fix 0.03 s (bound 1.0).
- `d20_red_tests_sim.py` on the unedited worktree: exit 1 (run in two subsets under 60 s: all 13 cases it ran FAIL). On the edited tree: exit 0.
- G2 `test_retains_is_set_inclusion`: HEAD ImportError (not a RED), fix PASS.
- G1 `test_shape_issues_equals_the_pairwise_reference`: PASS on HEAD and on the fix.
- Digests G3 (absence, source_context, validate_review, business_context), the L1 (cp4_legal), L2/L3 (cp3_relative_value) guards and G4 (prefill, 120 seeds) were pinned on HEAD. After the edits all seven digests are identical to the pins. The first three and business_context also equal the plan's 16-hex cross-checks (f5a31f14..., a039f8b2..., 73f05ff2..., 3eb2ca18...).

## GREEN: every test function in tests/test_readiness_linear.py called directly, exit 0
18 timed cases pass; 2 end-to-end pass; G1 and G2 pass; the 7 pinned digests match (6 validator names plus prefill).

## Probes on this worktree (plan §7 "Fix" column)
| probe | exit | expected |
|---|---|---|
| d01, d03, d04, d05, d06, d07 | 0 each | 0 |
| d16, d17, d20 | 0 each | 0 |
| d02 `<base> <this>` | 0 (A: 6000 synthetic, 0 mismatches; B: 10013 real, 0 mismatches) | 0 |
| d08 `<base> <this>` | 0 (300 seeds, 0 mismatches) | 0 |
| d09 `<base> <this>` | 0 (139,932 outputs, 0 mismatches) | 0 |

d10 and d13 not run (over 60 s).

## Edits
- readiness.py F1-F3; source_context.py F4; business_context.py F5 (b10 `_blank`/`_populated` hunk skipped, already present); live/submission.py F6; plus L1 (cp4_legal.py `_shape_issues`), L2 and L3 (cp3_relative_value.py `_instrument_issues`, `_preference_issues`), using `Counter` and a set built once. Issue text and order unchanged. Applied via a copy of `d90_make_fix_tree.py` (25 edits, 0 failed) with the two "HEAD" docstring phrases reworded. No new `except`.
- O-a (page-number `int()` raise), O-b and the Modules notes were not touched.

## Gates (venv binaries), on the six sources plus the new test
- `ruff format --check`: exit 0.
- `mypy --strict`: exit 0 (7 files).
- `ruff check`: exit 1, same as before. Before (HEAD sources, plus my test, which had UP035 that I fixed): cp4_legal.py:403 TRY004, source_context.py:578 and :580 ISC004. After: cp4_legal.py:404 TRY004, source_context.py:581 and :583 ISC004. No new finding.

## Pins (report only)
- `python3 -I cases/pins.py --check`: exit 0 ("matches 69 paths"). It does not cover the files below.
- Pins that no longer match after this change (old HEAD hash still in `cases/**`):
  - `src/deploy_vii/business_context.py` (1672ba97...): `cases/cp3c-owner/builder/build.py:32`, `cases/cp3c-owner/manifest.json:49`, `cases/cp4c-owner/builder/build.py:41`, `cases/cp4c-owner/manifest.json:18`.
  - `src/deploy_vii/readiness.py` (1038a37a..., the imported hash): `cases/legal/manifest.json:290`.
- `cp4_legal.py` is pinned at its imported hash 1b2246ff... in `cases/legal/manifest.json:288,339`, `cases/legal/render-expected.json:28` and `cases/legal/source-host-expected.json:19`. That already differed from HEAD (b10) and is unchanged in status.
- I found no textual sha pin of cp3_relative_value.py, source_context.py or live/submission.py in the files I grepped; other `cases/**` files that name cp3_relative_value.py (snapshot, cp3c/cp4/cp1c/cpl10/cp3-cp6 owner expected.json and builders) were not each opened, so snapshot/builder/build_s1_oracle.py and the expected files should be re-pinned by LEAD from a full re-run.

## Records
`docs/reuse/manifest.json` `post_import_patches`: two new entries (readiness.py, imported 1038a37a...; source_context.py, imported bef10963...); entries for submission.py, business_context.py, cp4_legal.py and cp3_relative_value.py updated (sha256, `project_commit` "lead/0d-d (uncommitted)", `review` "work/lead/product-defects-0d/", and the 0d-d reason appended after the existing reason). Shape kept; JSON re-serialised in its existing format.

## Final sha256
- src/deploy_vii/readiness.py 119058ff8a238f29aa418da7d43110686ad0ba9d0362d5d77b989f798d088f1f
- src/deploy_vii/source_context.py d9fb02de160c9710378308a3dc2d4f32096cfb90de5680bf8a48e7d50c9bb9d0
- src/deploy_vii/business_context.py 895cab5e09dd4e3eb48ddc41a2928e0441f74f1acb402539e85622934a2c9cde
- src/deploy_vii/live/submission.py 173547f9a18bc43afaf3acf2ddc569ed398353b672b6856500f29d7f95e75445
- src/deploy_vii/cp4_legal.py 17c96b6f4c2ccf1eaae18f3bb3b4083ffb6603ae54e59f83b8aa170885b26ec0
- src/deploy_vii/cp3_relative_value.py 6c80484307aef1d6c6d3b17d7432f642fdd4b11f0a3db2b26cdb3cbf8f5a9f7f
- tests/test_readiness_linear.py f7e6f3f6e8896a5c5eaf2ae910967f9d0332e852f954a89c71f5614322735ccb
- docs/reuse/manifest.json b040cdb3f8c00f4a7f2914a222e2b833791c9b722c26fc7e83e613ffc121402d

## Deferred pytest (LEAD's final phase)
`"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest tests/test_readiness_linear.py tests/test_financial_workflow.py tests/test_owner_s1a.py tests/test_owner_workflow.py tests/test_source_workflow.py tests/test_rule_issue_bounds.py tests/test_engine_blank_text.py tests/test_earnings_workflow.py tests/test_source_tools.py tests/test_upstream_tools.py tests/test_schema_normalise_escapes.py tests/test_connected_render.py tests/test_earnings_render.py tests/test_cp1b_registration.py`
The repo has no cp3/cp4 test file in `tests/`; L1-L3 are exercised by the new file and by the `cases/cp3*`/`cp4*` builders and the owner tests above.

Not verified: pytest collection and execution of the new file (parametrize ids, the `tmp_path` end-to-end tests); the affected existing tests; d10 and d13; owner, earnings and CP-1A workflows end to end; L1-L3 only at validator level with model-constructed submissions (no connected CP-3/CP-4 workflow); the re-pin of `cases/` pins; the manifest against any checker (none found in tests); the pre-existing ruff findings were not fixed; timing bounds were met on this machine only and under no parallel load.
