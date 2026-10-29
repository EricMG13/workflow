# G2 rev 2 review (mx-precise a6a7d04d, dbd4c7c)

**Verdict: REVISE.** I found two Medium findings. All file:line references are in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-g2scope/docs/OWNER-RENDERING-LEASE.md` at `dbd4c7c`.

**Spec verdict: REVISE (one Medium).** Row coverage, triples, sections, pathway order, the Q-C1/Q-C2 handling and item 4 are correct. CP-8's refused outcome is wrongly deferred.

**Quality verdict: REVISE (one Medium).** The body's `complete` rule contradicts 16 of the 19 rows, and rev 2 never overrides it.

Diff ceiling: the change is docs only (+149 lines), within the ceiling. Negative constraints: the amendment calls for no stub, no fake value and no catch-all. It keeps rev 0's "no relabelling catch-all" (body :101), and every unsupported or unmatched case raises `owner_render_*`.

### Checks that pass
1. **Row coverage and triples.** `probe_triples.py` (exit 0) builds every case of all 15 driver modules through `make_pack(case).run` (cp4 via `test_method_cp4.make_pack`) without any owner run. All 55 cases match exactly one row, and the table's 19 triples are distinct. Every case's `case_kind` is `synthetic`. CP-2G is the only module with two tuples, as R2.3 says. The `cp6-fp01-committee` tuple equals `cases/cp3-cp6-owner/manifest.json` R6. No row is invented, and the R2.9 exclusions (CP-OS, CP-1B, CP-5) are justified.
2. **Sections.** All block ids are real (`report_view.py:485-580`, `_Spec` rows `:1090-1250`) and in pathway order. CP-4 is reordered against its oracle on purpose (D6). `maturity-wall` is left out per Q-C1 / item 2 / D1. `funding-gap` heads the cp3c row, which stays gated per Q-C2 and item 4. `probe_pointers.py` exit 1 is expected: its only two failures are CP-3, where the oracle key is `FP01.relative-value`, as R2.5:285 itself says. Every other pointer resolves and holds the listed blocks.
3. **Refused outcomes.** For cp1c, cp2a, cp2g, cp2h and cp4c, `cases/refused` pins heads `["CP-0"]` and one RefusedBegin on CP-1, and each driver lists `refused` in `CASES`.

### Findings

**M1 (Medium): the CP-8 refused outcome is deferred on a false premise.** Lines :235, :298, :303 and :316 (D8).
- The amendment says the CP-8 driver lacks the refused run. In fact `cp8_runs.start("no_record", root)` produces it, and `workflow.write_receipt` then gives a verified receipt with one refusal (`CP-8`, NotAuthorized). `tests/test_owner_cp8.py:121-130` does exactly this, and `make_pack("no_record")` builds the `("CP-8",)` triple (probe).
- The oracle pins it at `cp8-owner/expected.json#/refused/no_record`, including the rendered state `what-changed` not_run.
- Failure: by M1 and the amendment's own driver test (R2.1:213), the row must support `refused`. As written, G2 would refuse a valid, oracle-pinned refused receipt, and no acceptance test would cover it.
- Fix: give `cp8-fp01-what-changed` the outcome `refused`, with refused case `no_record` and pointer `#/refused/no_record` (driver `start` + `write_receipt`). It needs its own banner: the shared "an earlier owner was not authorized" text is false here, because CP-0 refused CP-8 itself (missing prior case). Update :303 and D8 to name only cp1d and cpl10. Their refused runs are built only in test files (`test_owner_cpl10.py:58-88`), not in the drivers, so deferring them stays right.

**M2 (Medium): the body's `complete` rule requires a published model, and 16 rows have none.** Body :59 (still in force), R2.1:208-214, R2.8:336.
- Body :59 says "`complete` requires every planned analytical head to be accepted or restricted, and the model published." Rev 2 overrides the body only where it says so. R2.8 #7 says rows without CP-MODEL deliver no `model/`, but no line amends the outcome rule at :59.
- The oracles confirm there is no publication, e.g. `cp2a-owner/expected.json:13133` `"model_publication": "not planned"`.
- Failure: a builder who follows the body refuses every complete receipt for 16 of the 19 rows. A builder who follows R2.8 #7 has to drop a frozen rule without being told to. Either way the result is a contradiction, or quiet loosening of the rule.
- Fix: add a line to R2.1. `complete` requires `receipt.model` set and published if and only if `"CP-MODEL" in requested_modules`. Otherwise it requires `receipt.model is None` and no publication directory, and a model or directory where none is expected is refused.

**L1 (Low): one banner overclaims.** Line :256.
- `cp1c-fp03-peers` complete says "the issuer against a synthetic peer set". The supported complete case `no_peers` has `peer_source: null` (`cp1c-owner/expected.json` cases/no_peers).
- Banners are fixed per outcome, not per case, so this claim is false for one supported case.
- Fix before the freeze: "Peer positioning only. Every other block on this page remains unqualified."

**L2 (Low): the refused-page expectation is not in the oracle.** Line :332.
- R2.8 #3 asserts the refused blocks' `not_run`-family state from `report_view.py:1304-`. The module oracles' `cases/refused` pin heads, begins and the receipt, but no rendered block tree. So the expectation comes from core code, not from the oracle; it does not come from G2.
- Fix: either say the refused-page expectation comes from `report_view._honest_state` on purpose, or require the test to take only the producer ids from the oracle's `refused_begins` and `heads`.

**I1 (Info): R2.10 Q-S1/Q-S2 (:346-347) are answered by rulings item 4.** The table already matches those answers (CP-DR has a row; cp3c is gated until Q-C2 lands; cp6 is gated). The question text can go when M1/M2 are fixed.

**I2 (Info): rails-only rows are well defined.** With `sections=()`, the "assigned blocks populated, bound facts non-empty" rule is vacuous, and the proof is the rails alone (:210). For CP-2E, D3 adds a module-page check against the oracle.

### Probes
Run them from the s3-g2scope root:
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2scope-review/probe_triples.py` (`uv run python …`): exit 0.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2scope-review/probe_pointers.py` (`python3 …`): exit 1, only from the expected CP-3 `FP01.` key prefix.

Side effect: running the first probe with `uv run` created an untracked `.venv` in the s3-g2scope worktree. `git status` stays clean.

Not verified: no owner run, G2 or render was run. The rendered block trees were not compared to oracle content beyond block keys. The `cp1-model` row rests on rev 0 and was not probed. I did not run the CP-8 `no_record` receipt myself; that finding relies on `test_owner_cp8.py:121-130` and on `make_pack`. The banners of the other refused rows were checked against the oracles' `refusal`/`refused_begins` text only.
