# CP-2E Stage 2 review (mx-adversary)

## CP-2E Stage 2 review (0fa5b4a on claude/s2-cp2e, base 8973396)

**Verdict: REQUEST CHANGES.** One High and two Medium findings. I re-ran the fast gate set: 893 passed. The worktree is still clean at 0fa5b4a.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-s2-review/`. Mutants ran on a `git archive` copy in `copy/` there, never on the worktree.

### High
**H1. A model summary can make the step validator raise after the binding audit write.** Probes `p1_summary_bracket_raises.py` (exit 1) and `p3_summary_bracket_wedges_run.py` (exit 1).
- A summary such as `"Rates matter [a lot"`, `"{low"` or `"{}"` passes `validate_macro_fx`.
- `macro_fx` then builds `Claim(text=summary)`. `Claim.text` is `RunText`, so `prose.tokenize` rejects the text and `_validate_step` raises a `ValidationError`.
- p3 ran this through the real `OwnerWorkflow` in a scratch store:
  - `submit_review` raised after the binding write, leaving 2 bindings and 1 submission record;
  - `submit_step` had already written a pending step;
  - the valid literal submitted next was refused with `stale_binding`, so the run is stuck.
- This breaks protocol §6 :80. The defect is new: at 8973396 nothing built a `Claim`. CP-2's own validator already tokenises model text itself (`cp2_synthesis.py:387`).
- Fix test-first with a journaled `summary.text` issue. LEAD needs to rule the wording.

### Medium
**M1. Citation quotes that do not support their fact (same defect class as CP-3D).** Probe `p2_citation_wrong_quote.py` (exit 1).
- `_quotes` keeps the first submitted quote for each page, so 6 of the 11 T2F.1 sourced facts in the frozen positive case carry the wrong quote:
  - r04 rate basis, r05 spread 0, r06 floor 0 and r11 debt currency USD carry "…closing facility balance of 50.";
  - r09 free cash flow 9 and r10 FX effect 0 carry "Cash interest paid … 5.00".
- `app.js` `sourceText` shows this quote in the fact inspector.
- The lease and oracle pin only `(source_id, locator)`, so nothing caught it. `test_a_page_citation_carries_the_first_quote…` pins the defect instead of the fix.
- Fix: give each fact the quote of the field it was read from (T2F.1 rows map one-to-one to submission fields). For derived facts, LEAD should rule which quote they take.

**M2. Most lease acceptance store tests are not written, which brief §7 requires now.**
- Written: store bytes unchanged, read-before-submit (receipt reads cover the cited pages, plus the 3 journaled tool-use refusals), and the `extract_statements`/`read_inputs` refusals.
- Missing:
  - tamper at verifier level (acceptance 5; the full recipe is in `expected.tamper`);
  - `stale_binding`;
  - blocked (`negative_cases.blocked_cp2e`);
  - begin refused;
  - the 27 refusals and the hand-built-page refusal as store runs.
- Removing the placeholders was right. Noting the gap under Not verified does not meet §7.
- The acceptance-1 test that was written is weaker than the lease: it compares layouts and claim ids only, and own limitations only as a prefix.
  - Probe `p9_fact_field_mutants.py` (exit 1): five mutants survive the fast tests. They are `value_class`, `formula`, `period`, `limitation` (the gap reason) and `label` in `Cell.fact()`.

### Low
- **L1. `cp2e_upstream` was not built, and `macro_fx` drops `upstream` and returns `MacroFxReport`.**
  - No behaviour is lost: `settle` derives the inherited limitations (the oracle `inherited_rule` cites execution.py), `submit_step` refuses changed inputs, and begin binds CP-0.
  - It is still a deviation from the frozen lease Public API, so LEAD must rule on it or amend the text.
  - The lease Files list also omits the `_ENTRY_VALIDATORS` row, which protocol §2 requires (the same situation as the Q3 ruling). That is lease text and predates this change.
- **L2. Backlog Info 1 widens what the validator accepts.** Probe `p7_reference_rate_widening.py` (exit 1).
  - Names with a soft hyphen, a newline, a leading double space or U+2212 now validate.
  - T2F.1.r04 stores the raw name, so the fact text is not what the page prints.
  - The name cannot match outside the quote. The loose substring match (for example "SOF") predates this change.
  - The backlog row is an owner Info that records a fail-closed check, so widening it goes beyond applying the row. Either store `normalise(name)` or have the owner confirm.
  - Info 2 is correct: the `split_no_exempt` mutant is killed.
- **L3. Mutants that survive.** Probe `p4_mutants.py` (exit 1; 25 of 32 killed).
  - `absence_no_dict_guard`: the guard that stops RULES raising on `{"fx": 5}` is unpinned.
  - `parse_raw_json`: no test pins the protocol §6 parse path.
  - `reader_status_fixed`.
  - `quotes_no_basis`: equivalent on these packs.
  - Three `submit` mutants: `submit` is not exercised by any fast test.
- **L4. The reuse manifest does not record the `shipped.py` patch.** The file is now `01ebc258…`, but the latest `post_import_patches` record says `4ef3f9…`. Plan-draft §1 lists a manifest record per module (AGENTS.md:171). No gate checks it; probe `p8_library_boundary.sh` (exit 0).
- **L5. `methods/cp2e.md` lists the table titles but not the columns.** Lease Files asks for both.

### Info (checks that passed)
- **Adapter:** it returns the Stage 1 `MacroFxInputs` exactly for both cases. A missing operand is a gap with a reason, never 0. Model text is parsed through `json_object` → `exact_json` → `model_validate_json`. The only catch in `src` is the narrow `except ValidationError` in `_parsed`.
- **RULES bounds:** RULES can return 21 lines (the fixed absence line plus 20 from `listed_issues`), each at most 600 characters (`p6_rules_line_bound.py`, exit 0). The product's `ToolRules` combines its lines the same way. The report's "at most 20" is slightly wrong, and no test covers the case with no search.
- **Blank quotes:** the wording `<path>.quote: empty text` matches the CP-4C precedent (`claims[i].support[j].quote`). It is raised after the scope check and before the page check.
- **Registrations:**
  - rows are append-only;
  - the spec equals the lease line;
  - `sources=True` matches the `_OWNER_SCOPES` row;
  - there is no `_PRECHECKS` or `_VIEWS` row, which agrees with the lease (:41, :43);
  - `SHIPPED_MAPS` ends with CP2E, and the lease states no position;
  - the nine binding rows equal `expected.render.bindings`, and their mutants are killed.
- **Library boundary:** clean (p8).
- **Guard-limit notes:** all 14 cases hold (`p5_methods_notes.py`, exit 0).
- **Removed placeholder tests:** see M2.

Not verified: the deferred store runs (`tests/test_owner_cp2e.py`, `cp2e_closed`) were not run, per the build-first rule, apart from the single p3 scratch run. The inherited-limitation equality through `settle` was not run. `probe` and `finish` were not run against a forged store. No render or browser run. The shared hostile-text set has not landed in `tests/defect_classes.py`. I did not confirm whether LEAD or the module task owns the reuse-manifest record.
