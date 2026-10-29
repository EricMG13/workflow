# Stage 2 backlog (AGENTS.md "Stage closure", b570399)

Stage 1 is closed at `codex/checkpoint` e89b2a2. Only a High or Medium defect reopens a Stage 1 module. Everything else lands here, and each module applies its rows once, as its first Stage 2 task. Every row names its source and probe.

## Every module
- **Guard-limit notes in `methods/<cp>.md`**, written with the Stage 2 code:
  - rule W, the accepted cost: a spaced range and a dash bullet are refused (CP-1D, CP-3D, CP-8, CP-2E);
  - B8 (CP-2H);
  - item 8 comma costs: a grouped figure ≥ 1,000, a decimal comma, a comma-space list, a figure after a year, and the day of a "Month D, YYYY" date (CP-1D, CP-3D, CP-8, CP-2E).

  Sources: rulings round 12, round 13 item 8, addendum 2.
- **Blank support and citation quotes** (round 13 addendum 3). Every owner module that takes citations refuses a quote that `is_blank`, with `<path>: empty text`, at the support or citation step, before the page-occurrence check. CP-4C is done in round 13. Inventory the rest first; where the defect is present it is Medium (CP-4C review, `<S>/cp4c-r12-review/p_blank_support_quote.py`).
- **Caller-quoting issue lines** (protocol §6, 0d-c audit `work/build/stage1/0dc/r13-report.md`). When a core gains `RULES` or `_PRECHECKS`, build those lines only through `listed_issues`/`clipped`. The audit lists the f-string sites in cp1c, cp2a, cp2g, cp2h, cp3c, cp1d and cpdr.
- **Owner items:**
  - 30 product `assert`s;
  - jscpd not wired;
  - CP-2E `fx.` paths;
  - the cp2h test loads the cp2g expected without a hash check (Info).

- **Hostile-text set over `SCHEMAS`** (rulings stage2 Q5): add the probe set (`q5_host675_raise_classes.py`: deep arrays/objects, 200k-digit int, NaN, lone surrogate, non-object, duplicate keys, empty text, bracket and `{a|b}` floods) to shared `tests/defect_classes.py`; each `test_connect_<cp>` runs it over its `SCHEMAS` and asserts only `ValueError` subclasses. Modules task, once.

## Per module
| Module | Item | Source |
|---|---|---|
| CP-2H | Pin B8's "any later line": a row after the end, then a trailing one-field note, gets `Trigger terms not found` | cp2h/r12-review.md Low; `<S>/cp2h-r12-review/review_mutants.sh` `after_last_line_only` |
| CP-L10 | Exact subtraction can store `-0` or exponent form; check the render path and normalise if needed | cpl10/r13-review.md Low; `<S>/cpl10-r13-review/edge.py` |
| CP-L10 | Missing-change lineage | Stage 2 release |
| CP-3C | Unsourced currency when `cash_closing` is missing, including all-blank currencies; conflicting status words in the minimum-cash and T4.18 seniority dependants; the `_check_value` message keeps its `CP-1` prefix | cp3c/r13-review.md Info 1–3 (LEAD) |
| CP-2G | Item 5 `base_period` invariant: `CP-2G: CP-2A T2B.1 facts differ in period` | round 13 R1 L2 |
| CP-2G | `Cp2aScenario.name` from `T2B.1.<row>.name` (manifest selection and lease :61) | round 13 R1 L2 (LEAD release) |
| CP-2E | Label decimal: `_Check.labelled` `{label}\s+{v}(?![0-9])` accepts `spread 25.5` | end-review-questions.md (LEAD, open); `<S>/cp2e-r12/p_label_decimal.py` |
| CP-3D | Info: a signed value_text is matched on the plain reading only (`margin -\n425 bps`) | cp3d/r12-review.md Info |
| CP-2D, CP-3C | Oracle re-pin, then remove `PERIOD_DELTA`/`GAP_VALUE_CLASS_DELTA` and the re-pin guard; 6 CP-3C periods to `q4-2025`; CP-3C manifest `fact_copy_rule` and lease :146 | round 13 R1 M1 (LEAD release) |
| CP-3D | Re-pin `amortisation_nonzero`, then remove `STAGE2_REFUSAL_DELTA` | round 13 addendum 2 (LEAD release) |
| CP-1D | Recipe text in `expected.json $.refusal_rules.partly_supported` and builder :1025, with the comma-space wording | round 13 item 7 (LEAD release) |
| All | `prose.is_blank` gains Cc, default-ignorables and U+2800 in LEAD's end batch; the `owners/blank.py` re-export inherits it | round 13 addendum 3 |

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

## Added from LEAD (2026-10-28, after closure)
- **[CP-2D]** A sum copy (T2E.1.r05) takes one operand's status. Treat it as a dependant gap: `Not calculable: Equity issuance is conflicting`. Source: cp2d/r13-review.md L4; addendum 4 (b).
- **[CP-2D]** The copy period rule keys on a copy, meaning a value read from the CP-1 fact. A recomputed cell (undrawn_rcf, liquidity, liquidity_to_debt, commitment less drawn) takes the balance date, not the CP-1 metric's period. No invariant. The tag may stay as a twin pointer. The CP-2D re-pin must use this. Source: addendum 4 (c), (d).
- **[LEAD product]** 0d-d: `readiness._echoes_item_error` is O(errors²). LEAD applies it as its first Stage 2 task (0d-d-plan.md, LEAD worktree).
- **[LEAD product]** `readiness.citation_issues` accepts a whitespace-only quote. Refuse a blank quote.
- **[LEAD product]** 0d-c Lows:
  - R1: the exact summary count;
  - R8-R11, c05 and c08: state the real worst-case record bound;
  - the complexity claim in the tools.py:33-35 docstring;
  - the `clipped` docstring needs limit >= 1.
- **[LEAD release at Stage 2 close]** The CP-3C manifest `frozen_inputs[8]` `use` text names BC_PROHIBITED, BC_NEAR and BC_NOUN. The real names are PROHIBITED, NEAR_INSTRUMENT and INSTRUMENT_NOUN. The other release items are in the per-module table above. The named deltas (CP-2D, CP-3D) are held until then.
- **Correction (LEAD):** the blank support or citation quote fix ran in Stage 1 only in CP-4C, which was its Medium. Every other citation-taking module takes it from this backlog (row "Every module" above).
- **[CP-2E, CP-3D] Info (owner, predates).** The text-occurrence check compares the raw value with the normalised quote: `rb["reference_rate"] not in quote` (cp2e.py:687) and CP-3D `name not in normalise(quote)`. So a U+2212 value never occurs. This fails closed. Sources: cp2e/r13-review.md Info 1; cp2e r13 report.
- **[CP-2E] Info (test strength).** The `w-minus` case in the round 13 B3 test uses an unwrapped quote, so it never reaches the exemption. The library case `w-minus-wrap-text` covers the exemption. Source: cp2e/r13-review.md Info 2.
- **[CP-2D] Low (ruling gap; LEAD).** With a conflicting or not_applicable commitment and missing drawings, the runway, LIQ-01, GAP-01 and the limitation name only "drawings undisclosed". That is true, but it misses the commitment's state, and with a not_applicable commitment it implies a revolver exists. Precedence is at cp2d.py:617. Source: cp2d/r13-fix1-review.md item 4; `<S>/cp2d-r13-fix1-review/f1_state_prose_and_mixed.py`.
- **[CP-2D] Low (wording).** `OPERAND_LABELS["rcf_drawn"]` = "RCF drawings" gives "RCF drawings, which is conflicting" and "RCF drawings is conflicting", where the verb should be plural. This affects cp2d.py:225, 826, 1390 and 1394. Source: cp2d/r13-fix1-review.md L1.
- **[CP-3D] Low.** `_whole_on_page` docstring (cp3d.py:258, :260-261) still describes the old edges; name `_EDGE_BEFORE` and the comma. Source: cp3d/r13-fix1-review.md.
- **[CP-4C] Low (test gap).** These mutants survive (`<S>/cp4c-r13-review/p_mutants_review.py`):
  - `\d` in place of `[0-9]` in the source patterns (Arabic-Indic digits);
  - an unescaped `.` in the d01 pattern;
  - `base_period("s03")` hard-coded at cp4c.py:1411;
  - `base_period` returning None for a shared None period.

  Pin each one. Source: cp4c/r13-review.md.
- **[CP-4C] Low (LEAD, unruled).** cp4c.py:465-468: an unsettled shock with `period=None` raises `differ in period`. It also pre-empts the round 8 A-4 copy of a missing or conflicting `ebitda_decline`. Today this is not reachable. Question: does R1 L2 "if they differ" cover a shock that has no period? Source: cp4c/r13-review.md.
- **[CP-1D] OWNER: two fail-opens that predate round 13** (cp1d/r13-fix1-review.md). Both are exit 1 at d2cb626 and at 9f61127.
  - **Non-ASCII digits.** A second figure written in fullwidth, Arabic-Indic or superscript digits is not seen by `[0-9]`, so a two-figure quote composes. Probe: `<S>/cp1d-r13-fix1-review/p4_unicode_digits.py`.
  - **Digits inside a word.** A run inside a word (`Q2`, `A1`, `2nd`) is read as the basis. Probe: `p9_run_in_word.py`.
  - The owner decides the severity. Neither is ruled.
- **[CP-1D] Low (owner fix re-review L3 + I2; LEAD remedy 2026-10-28).** Ordinal: after the run skip Cf/Mn/Me, NFKC-fold the suffix window, then match `st|nd|rd|th` (any case) with no letter after, so `2ⁿᵈ`, `2ｎｄ`, `2<U+200B>nd`, `2<Mn>nd` refuse and `2nds`/`2ndly` read. Identifier: a left neighbour touches when its category is L*, Mn, Mc, Me or Cf, or its NFKC fold contains a letter. Recipe text rides the next release; a moved frozen value goes to LEAD before merge. Source: stage1/cp1d/owner-fix1-review.md; `<S>/cp1d-owner-fix-review/a7_r1_ordinal_identifier.py`.
- **[CP-1D] Low (L4).** Test comments contradict addendum 5: `tests/test_method_cp1d.py:1279` docstring ("`2nd` reads 2") and :1321 ("an ordinal suffix is a whole run"). Rides with CP-1D's Stage 2 task.
- **[CP-2A] Medium, predates (owner/LEAD).** The adapter passes CP-1 operand facts without checking unit, currency or scale, and the core stamps every amount USD millions (cp2a.py:891-892). A THOUSANDS or EUR T4.10 base composes wrongly with no issue. Not reachable on the frozen pack; a fail-closed offer rule needs a lease amendment. Source: stage2/cp2a/review.md M2; `<S>/cp2a-s2-review/p8_units.py`.
- **[CP-2D] Low, predates (LEAD round 4).** "Equity repurchases is …" has the same verb agreement fault as "RCF drawings is". Source: cp2d/review.md L3.
- **[Shared defect test] Low (round 5 item 10 L2).** Free-text fields null or empty in a positive payload are never fed hostile text (CP-0 gaps/consumers/citations; CP-1 events/scopes). Add a schema-driven fill. Source: defect-classes/review.md L2; `<S>/defect-classes-review/p2_free_text_gaps.py`.
- **[G1] CLOSED (round 5 item 11 I2).** `probe_one_step` does not recompute a valid step's issues; the contract does. Pinned by `tests/test_owner_s1a.py::test_a_valid_step_that_carries_issues_is_refused_by_its_contract` and `::test_forged_issues_on_a_valid_step_are_refused_even_after_a_consistent_reseal` (`StepSubmission.coherent_state` refuses; the verifier returns `identity_mismatch` after a consistent reseal). Not a Medium. Source: cp5/review.md I2; `<S>/stage2-review-C/pg1_forged_valid_step_issues.py`.
- **[G1, owner, predates] `_refusal_code()` misattribution.** A terminal publication refusal is labelled with the walk's first refusal, which can be a module planned after CP-MODEL (or CP-1A at base): `cp3d_not_authorized` where the cause is a blocked CP-1. Source: g1x-order/review.md Info; `<S>/g1x-order-review/p3_later_refused_real_store.py`, `p4_refusal_code_predates.py`.
