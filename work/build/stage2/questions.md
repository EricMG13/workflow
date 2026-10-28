# Stage 2 questions and controller decisions

The source is `work/build/stage2/plan-draft.md` §6. Line references are against lane 5c9c60e.

## Controller decisions (LEAD may overrule)
- **Q1, block chain.** The Stage 2 chain closes at `_Spec`. `DELIVERY_SCOPES` and `owner_rendering.py` do not exist yet; they are G2, Stage 3. Each module reports the scope row it intends, and the Stage 2 review checks the chain up to `_Spec`.
- **Q6, reader types.** The producer owns `<cp>_reader` and the Head type it returns, as each lease says. The consumer's existing local type (`Cp2gHead`, `Cp2aHead`, `Cp4Head` in cp4c and cp2g) is switched to the producer's type in the consumer's own Stage 2 task.
- **Q10, compositions.** The module the lease names creates its `report_view.py` composition: CP-2A `_DISTRESSED`, CP-3D `_RELATIVE_VALUE`, CP-1D `_EARNINGS_QUALITY`. It merges before any module that appends rows to that composition.
- **Q11, shared quote reader.** No shared quote-reader helper in Stage 2.
- **Cohorts.** Every module merges serially, and registrations are append-only. These start first:
  - G1-X ride-along: the round 10 item 6 `_check_steps` guards;
  - CP-2D, CP-2A, CP-DR.

  CP-4 waits on Q3 and Q4. CP-3D waits for its round 13 merge.

## For LEAD
- **Q2.** The CP-6 half of the CP-3/CP-6 lease is draft rev 0, which blocks CP-3's D3 and CP-5's driver (`cp6_closed`). Should we freeze CP-6, or give CP-5 its own driver?
- **Q3.** Protocol §2 requires a CP-4 `_ENTRY_VALIDATORS` row, but the CP-4 lease file list (:36-41) omits it. Is the row in?
- **Q4.** The CP-4 `StepSpec.inputs="step_context"` literal (`owner_workflow.py:152`; CP-4 lease :37-38): does it go in the CP-4 module, or in the G1-X ride-along?
- **Q5.** Is `host.py:675` (`schema.model_validate_json(store.payload(...))` on raw text) covered by protocol §5?
- **Q7.** `methodology.json`: the only pending edit we found is CP-3's optional `T6-FINAL`. Do you want it?
- **Q8.** Is a `MODULE_FAMILY` row (`report_view.py:99-120`) for CP-DR, CP-L10 and CP-8 an admitted D12 one-liner?
- **Q9.** When is the release re-pin? It is needed for the CP-2D and CP-3C deltas, CP-3D `amortisation_nonzero`, the CP-1D recipe text, and `is_blank` Cc.
- **Info.** Stale lease cites:
  - CP-4 `owner_workflow.py:558`/`:530`;
  - CP-3C lease :185 "CP-4C has no core";
  - the plan's CP-2D stale-head cite (:452-456 is now :770-774);
  - the RESUME §5 lines (now cp2g 841, cp4c 959, cpl10 935-937, cp2h 1629).
