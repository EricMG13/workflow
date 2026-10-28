## CP-4C Stage 1 adversarial review at `bdde577`

**Verdict: CHANGES REQUIRED.** One Medium finding: a source-row claim can be read from a different row than the one it cites. The A-1 arithmetic itself held under every attack.

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/`. Each one runs as `<venv python> <probe> <target root>`. The target worktree was left clean (`git status` empty, HEAD `bdde577`).

### Gates (from the target root)
| Gate | Exit |
|---|---|
| pytest `tests/test_method_cp4c.py`: 148 passed | 0 |
| `ruff check` on both files | 0 |
| `ruff format --check` on both files | 0 |
| `MYPYPATH=src mypy --strict` on both files | 0 |

I added `--cache-dir` pointing into the scratchpad so mypy wrote nothing into the worktree.

### What held
- **A-1 against an independent reference.** A Fraction-only implementation of the rule was compared with `waterfall()` over 24,000 generated waterfalls across 6 seeds. They agree exactly: same shares, recoveries, shortfalls and residual, and the same raise (state 13 or none). The generators cover very large, very small and 37-decimal amounts, up to 12 tied classes, zero EV, full payment and 2×EV. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_alloc_reference.py`, exit 0.
- **State 14.** It fires for claims finer than q and for a `paid` wider than 38 digits. 3,000 random carrying sums never broke conservation. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_state14.py`, exit 0.
- **Frozen values.** v02 gives 3.7466666666666666666666666666666666667 and 1.8733333333333333333333333333333333333, and every rank of every frozen case equals the rule. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_v02_frozen.py`, exit 0.
- **End to end.** 750 `compute()` runs (3 seeds) with 1–5 extra classes, ranks 2–4, up to 12-decimal EBITDA and random multiples. T4E.9 balance is a known, exact 0 throughout. Distributions plus residual equal EV exactly, ranks sum exactly, and recovery and shortfall are rounded at 38 digits. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_t4e9_compute.py`, exit 0.
- **Hypothesis.** All five properties pass at 5,000 examples for each of seeds 0, 1, 2, 31337 and 20261028. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_hypothesis_big.py`, exit 0.
- **Waterfall against the lease Method.** Rank order, the secured class first, the blocking rules, the reason order and the break all match the builder's `waterfall()` (build.py:390-453). Missing never becomes 0.
- **The 38-digit trap (#13).** Every sum, difference and product is trapped and named: rank total, claims through, value left and EV. The only rounding left is what is pinned: the ratio divisions, the shortfall and the pp change. No arithmetic runs in the default 28-digit context; negation uses `copy_negate`. `_exact_sum` is sized so its unwrapped Inexact cannot fire.
- **A-2 wording.** Checked byte for byte against templates cut from the ruling text. #2 (including its position before the per-source checks), #3, #5 (both reasons), #6, #7 (claim with canonical amount, EV reason, EV own line), #9, #11 and the #13 operation names all match. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_states_wording.py`, exit 0.
- **A-2 invariants.** #10, #12, negative EV and total debt from another period are reachable only from a malformed upstream head, never from the submission. The product `Fact` validator makes the #12 "no limitation" raise unreachable.
- **A-4.** The CP-4 facility, CP-2G base and down first-break, CP-2A name and decline copies all keep `conflicting` and the limitation verbatim, and no other cell changes. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_a4_conflicting.py`, exit 0.
- **A-5.** `_RATIO` is no longer used for any sum.
- **Quote reads and signs (the CP-8 class) are ruled out.** CP-4C matches quotes raw (cp4c.py:712 and :769). A quote that matches only after `quotes.normalise` (a soft hyphen in the label or figure, single spaces) is refused as v04, both as `amount_quote` and as support. Figures come from the page line, never from the quote text, and no sign is lost. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_quote_normalise.py`, exit 0.
- **Standing rules.** No stub or fake value, and no I/O, store, host, session or render call (`fact_spelling` is pure). There is no catch-all: the three handlers are `Inexact` re-raised as a ValueError, `InvalidOperation` mapped to the #11 issue, and `ValidationError` returned as shape issues. No §2 protocol name is defined.

### Findings

**M1 (Medium): a claim can be read from a row other than the one it cites.**
- **Where:** cp4c.py:515-516 in `_row_amount`. The validator only checks that the quote is on the page (:711-713). `claim_classes` (:558) then reads the amount, and T4E.2 cites the quote (:1480).
- **Cause:** the label is the quote's first cell, and the amount comes from the *first* page line that starts with that label, not the line the quote sits on. The lease says claims are "read from the cited balance-sheet row".
- **Failure, duplicate label:** the page has `Other  1  1  1  1  5  5` and `Other  9  9  9  9  9  9`. The analyst quotes the second line. The validator returns no issue, and T4E.2.c03.claim = 5, cited with the quote whose Q4 cell is 9.
- **Failure, suffix label:** the page has `Provisions  1 … 5  6` and `Other Provisions  7 … 11  12`, and the quote is `Provisions  7 … 11  12`. The claim is 5 against a cited Q4 of 11.
- **Realism:** IFRS balance sheets often repeat labels in their current and non-current sections ("Provisions", "Borrowings", "Lease liabilities").
- **Scope:** the frozen page:4 has unique labels, so no frozen value moves. The builder's `row_cells` (build.py:158-163) uses the same first-match rule.
- **Fix:** it needs a LEAD wording ruling. Either read the line that holds the quote, or fail closed when the quote does not start a line or its label names more than one line.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_quote_row.py`, exit 0 (both cases reproduce).

**L1 (Low): a row with a blank cell silently reads the next column.**
- **Where:** cp4c.py:520-523.
- **Cause:** splitting on two spaces collapses a blank cell. Only a row that is short at its tail is guarded (`index >= len(cells)`).
- **Failure:** `Deferred items  1  1    1  5.00  7.00` reads Q4 as 7.00, the FY figure.
- **Fix:** treat `len(cells) != len(header)` as "no number", using the #11 wording. Every frozen row has 7 cells, so this holds on the frozen page. The lease pins "header cells split on two spaces", so LEAD may rule it Stage 2.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_quote_row.py`, exit 0.

**L2 (Low): a known CP-1 EBITDA with text and no amount is reported as missing.**
- **Where:** cp4c.py:1532 in `_cp1_ebitda`.
- **Failure:** this is a valid product `Fact`, but the module reports "Not calculable: EBITDA is missing in CP-1 …". That reason is false, and ruling #5 words only "missing or unsettled". The same upstream break raises for CP-1 total debt (:537) and CP-2G EBITDA (:593).
- **Test strength:** my mutant that makes it raise survives, so no test pins either behaviour.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_cp1_known_text.py`, exit 0.

**L3 (Low, test strength): the `state_14_claims_only` mutant is not equivalent.**
- **Where:** the check at cp4c.py:230.
- **Why it is not equivalent:** the justification holds for `compute()` only. `waterfall()` is lease Public API, and the property tests call it directly.
- **Failure:** with a 41-digit EV that partly pays rank 1, the real code raises state 14. The mutant returns shares that sum to 1 against a `paid` of 1.0000000000000000000000000000000000000001, with residual 0, losing 1E-40 silently. No test kills it.
- **Fix:** add a test that calls `waterfall()` with an EV over 38 digits and expects state 14.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_state14_paid_mutant.py`, exit 0.

**L4 (Low, test strength): 8 of my mutants survive and are not equivalent.**
- **Survivors:** `through_reason_group_first`, `rank_first_missing_is_last`, `rank_total_allows_zero`, `negative_claim_unchecked`, `fits_zero_is_partial`, `row_amount_infinite_ok`, `no_cp2g_id_period_check`, `no_cp2a_lineage_check`. The last two are the untested #10 raises the implementer declared.
- **Current code:** correct and consistent with the builder on each distinguishing input, so each input can become the killing test.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_survivors.py`, exit 0.

**Info**
- **I1.** The cells `(5.00)`, `−5.00` (U+2212) and `1,234.00` all read as "the quoted row has no number". They are refused, so no sign is lost, but the wording is wrong for a negative or comma-separated figure, and comma figures are falsely refused. The frozen page has none. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_quote_row.py`.
- **I2.** Under A-1, a class can be allocated 0 while its rank's recovery is positive. Example: claims 0.1 and 9999999999999999999999999999999999999.8 sharing 1E+36 give c01 a distribution of 0 and a recovery of 0.1, so plan fit requires "Receives reorganised equity". This follows from the rule itself, and only with 38-digit amounts. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_zero_share_positive_recovery.py`, exit 0.

### Pre-existing or unruled, for LEAD
- **A-2 #9 is reachable from a validated payload.** A valuation label "Base FY2026" passes `payload_issues`, then `compute()` raises "Bare figure: fy2026", so the run fails closed with no repair issue for the analyst. The class name "Notes due 2030" composes fine. The ruling says it "stays an invariant raise", and the code complies. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_label_figure.py`, exit 0.
- **CP-1 total debt `not_applicable`** raises a ValueError out of `payload_issues`, as already sent to LEAD. Confirmed by `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/probe_cp1_known_text.py`.
- **Builder rules shared with M1 and L1.** `row_cells` and the two-space split in build.py:158-171 are the oracle's own rules.
- **Raw quote matching is stricter than the product's `citation_issues`.** At Stage 2, a quote the host accepts may still be refused by CP-4C.

### Mutant table
All runs used full temporary copies (src, cases, the test and `pyproject.toml`), with `pytest -x` and hypothesis seed 0.

**Implementer's script** (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r6h-8/mutants.py`): exit 0, baseline passed. Output saved at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/implementer_mutants.out`.

| Result | Count | Mutants |
|---|---|---|
| Killed | 19 | as the round 8 report lists, each by the test it names |
| Survived, equivalent | 2 | `exact_sum_without_80_floor`, `no_balance_invariant` |
| Survived, **not** equivalent | 1 | `state_14_claims_only` (L3) |

**My script** (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/mutants_adversary.py`): exit 0, baseline passed, 46 mutants. Output saved at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-adversary/mutants_adversary.out`.

| Result | Count | Mutants |
|---|---|---|
| Killed | 33 | break at a fully paid rank, break at the last rank, blocked reason group-first, a blocked rank keeping its available value, ahead = group, recovery over available, EV 0 raising, EV 0 missing, CP-1 EBITDA 0 accepted, conflicting debt raising, copy status forced to missing, dividing by EBITDA 0, a claim of 0 accepted, no #3, no #2, #2 ignoring seniority, no #9 multi-line check, no #9 empty-name check, Inexact escaping, remainder in the wrong units, largest share first, leftover in claims order, `_exact_sum` using the max exponent, T4E.9 blocked → 0, blocked distribution → 0, missing residual → 0, CP-3C status ignored, CP-4 conditions unchecked, CP-1 period unchecked, pp sign flipped, the secured claim unchecked, the negative-EV case word, shortfall made exact |
| Survived, equivalent | 4 | `later_block_overrides_reason` (later blocks inherit the first reason through `available`); `balance_only_positive`; `fulcrum_unchecked_at_compose` (`_resolve` refuses first); `recovery_after_allocation` |
| Survived, test gap | 8 | the L4 list |
| Survived, fix-direction | 1 | `cp1_ebitda_known_text_raises` (L2) |

Not verified: Stage 2 binders and real packs, including how often duplicate or suffix labels and blank cells occur in the packs Stage 2 will bind; the full repo suite and other modules (not run, per the brief); mutmut or any automated mutation tool (hand mutants only); decimal Emax/Emin extremes; class names and labels with prose content beyond the two I probed; that the in-suite hypothesis generators never reach state 14 (it is covered only by my reference and state-14 probes).
