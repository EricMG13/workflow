## CP-4C round 13 adversarial review (805315e against 3cc72f7)

**Verdict: APPROVE.** I found no High or Medium finding, and no stub, fake value or catch-all that hides a failure. There are two Low findings: one is a test gap, the other is unruled and goes to LEAD. There are also two Info notes.

I ran everything from `git archive` copies of 805315e and 3cc72f7 under `<S>/cp4c-r13-review/{copy,parent}`, using `python -I -B` with `PYTHONDONTWRITEBYTECODE=1`. Every probe named below is in that folder.

### What holds
- **Item 2, scenario row** (`p_source_forge.py`, exit 0).
  - 77 forged d01/d02 pairs raise exactly the ruled invariant at all three points: `_scenario_row`, the validator (`payload_issues`) and `compute`. The pairs covered leading and trailing whitespace, tab, CR, CRLF, `\n` (fullmatch takes no `$`), NBSP, ZWSP, BOM, U+2028, NUL, doubled spaces, Arabic-Indic, full-width and superscript digits, `s3`, `s003`, case changes, dot wildcards, swapped or duplicated fields, mixed rows, `cp2a:` spelling and `""`.
  - The same holds for d01 or d02 `missing`, `conflicting` or `not_applicable` (no text), and for a known amount Fact. The product `Fact` refuses an unsettled fact that carries text.
  - Rows s01 to s04 resolve correctly.
  - `derives_from` is gone from `Cp2gEbitda`. The only lineage left in cp4c.py is CP-4C's own output lineage (`_Book`, :1015-1276). No upstream lineage is read.
  - In all 7 CP-2G oracle cases, the source row equals the d26-d28 `cp2a:` row (`p_source_vs_lineage.py`, exit 0).
  - Frozen parity: the 40 refusals and the 5 cases dump byte-identical on target and parent (`p_frozen_dump.py`, then `cmp`, exit 0).
- **Item 5, `base_period`.** It raises the exact string for differing periods, at the method and at compute. It never defaults: the head key is gone and the only reader is :1411 (`p_base_period.py`, exit 0).
- **Blank quotes** (`p_blank_quotes.py`, exit 0).
  - A schema walk finds only two Quote paths, `claims[].amount_quote` and `claims[].support[]`. `_citation` (:1288) is the only Citation constructor.
  - 18 blank values were tried on `support[0]`, an added `support[1]`, `amount_quote` on claims 1 and 2, and a blank quote with an out-of-scope source. Each gives exactly `(<path>: empty text,)`. Compute raises the module's `CP-4C submission has issues` ValueError, never a pydantic error.
  - A blank locator or source_id is refused by its own existing check, and no composed citation is blank.
- **Money path.** The diff does not touch `_allocate` or `waterfall`.
  - `probe_alloc_reference.py` (n=300): exit 0, with 0 mismatches over 5 seeds.
  - `probe_hypothesis_big.py` (300 examples, seeds 1 and 2): exit 0, and all 5 properties pass.
- **Plain-field B7 pin.** The "B7 also on plain fields" mutant is now killed.
- **Survivor "d01 row accepts `s[0-9]+`": equivalent, confirmed.** The d02 pattern still pins `s[0-9]{2}` and the two rows must be equal. Brute force over 16,129 row pairs gives identical outcomes (`p_equiv_survivor.py`, exit 0). Its d02 twin survives for the same reason.

### Findings

**Low: test gap; rides with the next fix.**
- **Where:** the forged-pair list at tests/test_method_cp4c.py:1521-1541, plus nothing pinning cp4c.py:1411.
- **What:** the code is right, but these non-equivalent mutants survive the module test (`p_mutants_review.py`, exit 1):
  - `[0-9]` changed to `\d` in both patterns. A source `CP-2A T2B.1.s٠٣.ebitda_decline` is then accepted, and a different CP-2A-fact invariant raises instead of the ruled one.
  - an unescaped `.` in the d01 pattern, which accepts `CP-2A T2BX1Xs03Xebitda_decline`.
  - `base_period("s03")` hard-coded at :1411: no test makes the scenario row's period differ from s03's.
  - `base_period` returning `None` for a shared `None` period: the both-None case is not pinned.
- **Rule:** R1 M2 ("must fullmatch … Otherwise raise the invariant") and R1 L2 ("the row's … facts"). The brief also names Unicode digits as a forged text.

**Low: unruled; LEAD.**
- **Where:** cp4c.py:465-468.
- **Inputs and outputs:**
  - **Both shocks missing with `period=None`:** this raises `CP-4C: CP-2A T2B.1 facts differ in period`, though the periods do not differ.
  - **Missing or conflicting `ebitda_decline` with `period=None` and a known `interest_increase`:** compute now raises. The parent composed a T4E.3 `missing` or `conflicting` copy, which is the round 8 A-4 path ("unknown upstream copies keep their status"). The new raise pre-empts that path.
- **Effect:** both cases fail closed and nothing defaults.
- **Reachability:** none today. CP-2A emits the shocks only as known analyst inputs carrying the base period (cp2a.py:958-965).
- **Question for LEAD:** does R1 L2 "if they differ" cover an unsettled shock that has no period?

**Info.**
- **Blank `amount_quote` on a non-`source_row` class.**
  - What it gets: only `claims[i].amount_quote: only a source_row class cites an amount row`. A blank quote on a kind/source-mismatched class gets only the mismatch issue.
  - Why it fails closed: the validator refuses the payload, and compute raises the module ValueError.
  - Why no blank issue: that quote never reaches a citation or page-occurrence step, so this is round 12 B9's first-failing-check rule. No action is needed.
- **The two `_scenario_row` call sites.** In compute, `content_issues` → `_references` (:2159) always raises before the `_resolve` site (:1384). Both raise the identical ruled string, so this is not a defect.

### Exit codes
- **Gate** (pytest on test_method_cp4c and test_defect_classes_selfcheck, in the copy): **exit 0**, 1501 passed.
- **Static checks:** `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files each exit 0.
- **Mutants:**
  - `<S>/cp4c-r13/mutants13.py`: exit 1, 11 of 12 killed; the survivor is the equivalent one.
  - `<S>/cp4c-r12/mutants.py`: exit 0, 9 of 9 killed.
  - `<S>/cp4c-r12-review/p_mutants_extra.py`: exit 1. B7-on-plain is killed; "blank not exclusive" survives, already judged equivalent in round 12.
- **My probes:**

| Probe | Exit |
|---|---|
| `p_source_forge.py` | 0 |
| `p_source_vs_lineage.py` | 0 |
| `p_base_period.py` | 0 |
| `p_blank_quotes.py` | 0 |
| `p_equiv_survivor.py` | 0 |
| `p_frozen_dump.py` parity (`cmp`) | 0 |
| `p_mutants_review.py` | 1 (7 killed; 5 survive: 1 equivalent, the other 4 are the first Low) |

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: I did not run the full suite, GitNexus `detect_changes`, or LEAD's `p13_cp4c_source_row.py` and `p13_l2_sources.py` (`p_source_vs_lineage.py` replaces part A). There is no Stage 2 `cp2g_reader`, so the source Facts were built only by the test helper. I did not check whether a promoted CP-2A head can ever carry an unsettled or period-less T2B.1 shock. The CP-4C and CP-2G lease headers were read, not tested.