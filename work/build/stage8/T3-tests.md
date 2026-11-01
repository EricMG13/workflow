# T3: H10 + H11 + H13, tests that pass for the wrong reason, and the CZR runner exit code (stage contract; mx-feature)

Rules: `L/work/build/stage8/common.md`. Before any edit, run `git checkout -b claude/s8-tests 61a86c10` and confirm the tip.
- Edit only `tests/test_connect_cpdr.py`, `tests/test_connect_cp8.py`, `tests/test_connect_cpl10.py` and `cases/czr-2026q2-earnings-update/partial-builder/run.py`.
- For H10 and H11 the "RED" commit is replaced by a demonstration: the controller runs the old and new tests against a deliberately broken renderer or input using the probes. So make one commit per finding.

## Inputs
- `K/CONSOLIDATED.md` rows H10, H11 and H13.
- Probes `K/probes/v-tools/h10_desired.py`, `h11_desired.py`, `h13_desired.sh`, plus `orig_probe_render_assertions.py` and `orig_probe_padding_variants.py`.

## Findings
- **H10:** two render tests pass while the visible text is wrong (`test_connect_cpdr.py:1333`, `test_connect_cp8.py:1142`). Assert the exact payload `display`/`table_display`, and edit a fact that is bound into the block, so the test fails if the visible text is wrong.
- **H11:** padding variants collapse in a set (`test_connect_cpl10.py:649`). Use a list and assert distinct exponents.
- **H13:** the partial CZR runner exits 0 on missing input or on any BaseException (`run.py:16-21`). Re-raise; pass only on the expected refusal text `CP-1 QA Blocked: confidence 39 (Insufficient Information); a Blocked handoff is not promoted`, matched exactly. Leave every other behaviour of the runner unchanged.
