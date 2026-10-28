# CP-8 fix round 1 re-review (mx-adversary)

**CP-8 fix round 1 re-review (1a2887f on 8fab26b): APPROVE.** Both Medium findings are closed, the four checks you asked for hold, and there are no new High or Medium findings. The s2-cp8 worktree was left clean (`git status` is empty); every mutant ran on a scratchpad copy.

New probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-s2-rereview/`. The old ones are in the sibling folder `cp8-s2-review/`.

**M1: closed.** Probe `p13_synthetic_ruling.py`, exit 0.
- On a real closed run for both cases, the settled own list is the oracle's own list then the synthetic line, deduplicated: 7 lines for each case.
- Inherited equals what `execution.inherited_limitations` returns, and the synthetic line is not in it.
- `cp8_reader.limitations` returns the settled own list, and the docstring says so.
- My old mutant R1 is now killed.
- `p2` still exits 1, but it encodes the pre-ruling expectation, so it should be retired. p13 replaces it.

**M2: closed.** Probe `p9_m2_store_mutants.py`, exit 0. Each mutant ran only the named test, and all 7 were killed:
- tamper: `cp8.probe` made a no-op;
- blocked: attempt 1 settles as "rejected" instead of "blocked";
- no_record: `begin` skips the CP-0 authority check;
- stale_binding: the snapshot check in `_current` removed;
- r42: the validator de-duplicates its issues;
- RULES issues never appended at submit;
- RULES issues appended before the validator's.

**L1 pins: closed.** I re-ran `p4_review_mutants.py`: 18 of 19 killed, and only S1 survives (exit 1).
- **S1 is equivalent, as the fixer claims.** When RULES returns nothing, `_with_rules.run` hands back the validator's outcome unchanged.
- RULES is pure over fixed evidence, and r42's two lines come from the validator alone (`rules_issues: []`).
- My earlier description of S1 ("de-duplicates r42") was wrong.

**Citations: closed.** Probe `p10_citation_mutants.py`, exit 0.
- `citations()` now keys on `(source_id, locator)` with `setdefault`. That keeps the first quote on each page, in input order, and matches the ruling. The oracle compares page pairs only, and the derived rule is now stated in `methods/cp8.md`.
- Five mutants, all killed: last quote per page, one citation per quote, reversed input order, pages sorted, and an invented (upper-cased) quote.

**Model text: the claim holds.**
- In compose, analyst text reaches only `Claim.text` (`RunText`: at least one character, and no `{`, `}`, `[` or `]` outside a well-formed reference) and `TableRow.label` (`Text`). The validator's `_text` check is stricter on both: it refuses blank text, including format characters, any numeric character, and all four brackets.
- `p11_model_text.py`, exit 0: 53 string sites × 52 hostile or edge values gave 598 accepted. Every accepted value ran through compose, a round trip, `cp8_module` and the type checks, with no raise and no `prose_issues`.
- `p12_model_text_store.py`, exit 0: 8 accepted hostile values (NUL, right-to-left override, 200k characters, emoji, newline, U+FFFE, tab) each settled a restricted head through a real store run, and the receipt verified.
- **Info:** the literal ruling (a `TypeAdapter` and pydantic `<path>: <msg>` wording) is not followed. The behaviour is equivalent, so LEAD should record that the deviation is accepted.

**New findings (Low only; they ride with the next fix):**
- **L-a:** `test_identity_is_outside_the_host_scope` only asserts `status != "ok"`. The product returns `refused` / `not_permitted` (p14), and the test should pin that.
- **L-b:** the `not_permitted` and `stale_binding` tests do not assert the lease's "neither consumes an attempt and both are recorded in the receipt". The product does both (`p14_run_level_refusals.py`, exit 0), so this is a test gap only. The stale test also uses `interrupt`, which consumes the attempt itself, so that test can never check the "no attempt consumed" part.
- **Info:** `brief.md` gained a "Source quotes" ruling after this round was written. I did not review against it.

**Gates:**
- pytest on the 6 named files: 1665 passed, exit 0.
- The noqa count is 13 (≤ 13).
- I also ran `ruff check` and `ruff format --check` on the 4 changed `.py` files: both exit 0.

Not verified: the shared model-text test in `tests/defect_classes.py` is not on the lane, so it has not been run over CP-8's positive payload. `test_owner_workflow.py`, `test_owner_s1a.py`, mypy, and probes p1/p3/p5–p8 were not re-run. No run with CP-6 bound was possible in Stage 2. I did not confirm where the audit directory records refusals (only the receipt check was done). The `docs/reuse/manifest.json` shas were not checked.
