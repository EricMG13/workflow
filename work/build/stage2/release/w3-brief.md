# Stage 2 close release, W3 integration (stage contract)

`L` = the lane, `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only).
`R` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-release`, branch `claude/s2-release`, at fb231d4. This is your worktree.
`F` = `/Users/ericguei/Documents/Deploy Workflow Sessions/lead-cp6-freeze/work/lead/cp6-freeze`: the chain tooling (`chain.sh`, `iterate.sh`, `repin.py`, `fresh_copy.py`, `headers.py`); read-only.

## Inputs
| Item | File | Why |
|---|---|---|
| W2 reports | `L/work/build/stage2/release/w2-{a1,a2,b,c,d}-report.md` | what each lane changed and left for W3 |
| W3 notes | `L/work/build/stage2/release/w3-notes.md` | every carried item and ruling. **Apply every bullet.** |
| W1 report | `L/work/build/stage2/release/w1-report.md` | how W1 ran the chain and double rebuild |
| Rulings | `docs/rulings/2026-10-28-stage2.md` | rounds 1-5 |

## Process
1. **Merge.** Merge into `R`, in this order, with `--no-ff` and one merge commit each:
   - `claude/s2r-b` a70ee52;
   - `claude/s2r-c` c8b708b;
   - `claude/s2r-a2` c824206;
   - `claude/s2r-a1` 3614577;
   - `claude/s2r-d` 291fa8e.

   Resolve conflicts as follows:
   - `cases/PINS.json`: regenerate it; never hand-merge.
   - Lease files: keep both sides (the header lines from A1, A2 and D; the body from B).
   - `tests/cp3c_runs.py` and `tests/cp4_runs.py`: C's shared `drive_cp1`, plus A1's pin lines.
   - Generated `cases/` outputs: rebuild them in step 2; never hand-merge.
2. **Chain.** Run the full builder chain with `F` tooling until it reaches a fixed point. It covers:
   - every stale cross-lane pin named in the notes: cp2g→cp1d, cp2h/cp4c→cp2g, cp4c→cp4 and cp3c, and cpl10→cp3c;
   - the `cases/legal/manifest.json` pin of `readiness.py` (→ 01616654…).

   Two fresh-copy rebuilds must be byte-identical to each other and to the committed tree. Regenerate `cases/PINS.json` after adding the view-tree pattern (W3 notes).
3. **Lease pin headers.** For every oracle or builder sha the chain moved since the lane's last header, add one "Amended by Modules 2026-10-29 (Stage 2 close release W3 chain)" line with old → new.
4. **Text fixes from the notes:**
   - CP3C lease :154;
   - CPL10 lease :13, :131 and :216;
   - the blank definition in `methods/cp1d.md`, `cp2e.md` and `cp1c.md`, which must match the new `prose.is_blank`;
   - the `cp3c.py:2368` comment;
   - the CP-3D builder :1528 wording, under the stated condition.
5. **Rulings.** Append to `docs/rulings/2026-10-28-stage2.md`, under round 5, items 20, 21 and 22, in the words of the W3 notes. Item 20 is the CP-2D `run_rate_annual` text-only ruling. Item 21 is the drawings-precedence wording. Item 22 is the CP-L10 lineage scope. Add one line recording the view-tree pin decision.
6. **D12 check.** Every reused file whose sha changed since fb231d4 must have a record whose `sha256` is the current sha and whose `project_commit` brings the file to it (round 5 item 19). C added prose, readiness, execution and live/tools. Confirm no other reused file changed.
7. **Duplication.** Lane D left four `_one_per_page` copies in cp1c, cp2g, cp2h and cp4c. If they are identical, hoist one copy into a shared owners helper (the stdlib-only module that the owner cores already share; pick the existing one). Then delete the copies. No oracle may move.
8. Commit at each step. Commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/pins.py --check`.
- The fast set, from `R` with `PYTHONPATH=src:tests` and `L/.venv/bin/python -m pytest -q -p no:cacheprovider`:
  - `tests/test_method_*.py` and `tests/test_connect_*.py`;
  - `test_cp1b_registration`, `test_owner_g1x`, `test_host_h1` and `test_schema_normalise_escapes`;
  - `test_defect_classes_selfcheck`, `test_defect_classes_shared` and `test_defect_classes_cp1`;
  - `test_engine_blank_text`, `test_rule_issue_bounds`, `test_owner_blank` and `test_owner_order`;
  - `test_stage2_classes` and `test_stage2_classes_batch`;
  - `test_legal_render` and `test_connected_render`;
  - `test_citation_blank_quote`, `test_readiness_linear` and `test_owner_s1a`.

  Do not run the slow render suites (`test_financial_render`, `test_earnings_render`, `test_cp1_chart_render`) or any `test_owner_<cp>.py` genuine runs; the controller runs those.
- `ruff format --check` and `ruff check` on every changed `.py` file. Known findings that predate the release:
  - cp4_legal TRY004;
  - source_context ISC004 :581 and :583;
  - prose ISC004 :114 and :127;
  - `test_cp1b_registration.py:98` PLW1510;
  - `test_legal_render.py` C408.
- `mypy --strict` on every changed `src/` file.
- `noqa` must stay at 13 or below, and `type: ignore` at 5 or below.

## Outputs (report as text, at most about 2k tokens)
- Tip SHA.
- Merge conflicts and how each was resolved.
- Every sha the chain moved.
- Each W3-notes bullet: done, or why not.
- Gate exit codes.
- A closing `Not verified:` line.
- The ledger line.

Rules: no stub or fake value standing in for real behaviour. No catch-all that hides a failure unless the fail-open is documented and logged. Only a re-pin may move an oracle value in W3; if any value moves, stop and report it.
