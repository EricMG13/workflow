## R3 report: cross-module consistency and Stage 2 seams (lane 87b2a1a)

**Verdict: FINDINGS.** I found 4 Medium, 3 Low and 3 Info. The four quote readers give the same result in every case except two, and both of those need LEAD (M3 and L1).

I read and probed from a full copy at `<S>/stage1-end-R3/copy` (`git archive 87b2a1a`, run with `PYTHONDONTWRITEBYTECODE=1`). The worktree HEAD is e76b0b3; I used the target commit, not HEAD. All probes are in `<S>/stage1-end-R3/`.

### Medium

**M1. CP-3C accepts whitespace-only text in its analyst `Text` fields.**
- **Where:** `cp3c.py:201`. The loop over `_text_fields` checks only for digits and prohibited phrases.
- **Input and output:** `"   "`, `"\n"` or `"\t "` in `repricing.rationale`, `repricing_absence.reason`/`.follow_up`, or any `paths[*].text`/`.credit_implication` gets `()`, no issue at all. Probe `p_cp3c_blank.py`: exit 1, 33 failures.
- **Rule broken:** round 11 "Blank text is one defect class", which names "CP-3C's other `Text` fields (`min_length=1`)".
- **Why it is new:** CP-3C is not in the class-round table, and the defect-class inventory never ran CP-3C, CP-4C or CP-2H. Its adapters cover 13 modules. CP-3C B5 fixed only the II limitation.

**M2. CP-4C accepts whitespace-only text in its "plain" fields.**
- **Where:** `cp4c.py:926-945`. Fields of kind `plain` go straight to `guard_issues` with no blank check.
- **Input and output:** `"   "`, `"\n"` or `"\t "` in `claims[i].limitation`, `valuation|fulcrum|plan[i].limitation`, `assessment.limitation` or `gaps[i].{gap,why_it_matters,affected_analysis,action}` gets `()`. Probe `p_cp4c_blank.py`: exit 1, 27 failures.
- **Rule broken:** the same round 11 rule. The module already uses `<path>: empty text` for its name and run fields.

**M3. CP-1D reads the digits after a leading point as a whole amount (unruled; to LEAD).**
- **Where:** `cp1d.py:349-352`. `_SIGNED_AMOUNT` has no `(?<![0-9.])` guard.
- **Input and output:**
  - basis quote `saving of .25 per year.` gives amounts `['25']` and no issue;
  - `saving of -.25 per year.` gives `['25']`, so the sign is dropped and the value is 100 times too large.
- **The other readers:** CP-3D, CP-8 and CP-2E refuse the same figure, because their token patterns carry `(?<![0-9.])`.
- **Probes:**
  - `p_cp1d_leading_point.py`: exit 1;
  - `p_readers_diverge.py`: all 404 fuzz divergences are this one class.
- **Why it goes to LEAD:** round 10 gives CP-1D's pattern word for word, without the guard. So the code matches the ruling text, and the gap is in the rule.
- **Proposed fix once ruled:** add the guard to the digits group. A `.25` then gives no amount, and the pinned exactly-one refusal fires.

**M4. A thousands comma is read as two figures in all four readers (unruled; to LEAD).**
- **Cause:** B1's cut tests name a digit, `.`, a minus and accounting parentheses. A `,` is none of them, and round 10's token patterns do not treat `,` as part of the numeral.
- **Input and output:**
  - CP-3D `margin` with `bps_text 250` and the whole quote `The margin is 1,250 basis points.` gets `[]`, so it is accepted;
  - CP-1D basis quote `250 per year.` on the page `saving of 1,250 per year.` is accepted at 250.
- **Probe:** `p_comma_thousands.py`: exit 1.
- **Where:** `cp3d.py:186`, `cp1d.py:349`, `cp8.py:402`, `cp2e.py:497`.
- **Frozen cases:** none of the four modules' frozen cases prints a comma figure, so nothing frozen moves. Real filings commonly print `1,250`.

### Low

**L1. The readers split on a quote-side wrap before a minus the page prints (to LEAD, with Q-wrap-minus).**
- **Input:** the page prints `The reference rate is -0.25 percent today.` without a wrap, and the quote is `…is -\n0.25 percent today.`. `quoted` accepts it through the joined quote, which prints `-0.25`.
- **Output:** CP-8 refuses it. CP-3D (`reference_rate.level` gets `[]`) and CP-2E (`_once` returns True) accept the unsigned 0.25.
- **Cause:** `_whole_on_page` (`cp3d.py:235`), `_once` (`cp2e.py:526`) and `_edge_cut` (`cp1d.py:563`) return "no cut" when the plain needle never occurs on the page. CP-8's `_on_page` (`cp8.py:410-436`) returns `seen`, which is False there.
- **Probe:** `p_quote_wrap_sign.py`: exit 1.
- **Known so far:** only the CP-1D half (I1 in `quote-sign-questions.md`). The question also needs this case for CP-3D, CP-8 and CP-2E.

**L2. CP-2H has a §5 read site that the Stage 2 notes leave out.**
- **Where:** `cp2h.py:1623`, `TriggerSubmission.model_validate_json(payload)` in `payload_issues`.
- **Stale line numbers:** RESUME.md lists cp2g:830 and cp4c:938. They are now `cp2g.py:840` and `cp4c.py:953`; `cpl10.py:926` is unchanged.
- **Every other Stage 1 module:** takes parsed objects, so it has no read site.
- **Outside the cores:** `host.py:675` (H1 host replay) also parses the stored payload raw. It is not a core under the protocol's wording.
- **Protocol text:** the §5 line (d637afc) is not an ancestor of 87b2a1a. It arrives with codex/checkpoint.

**L3. 30 `assert`s are left in product code paths.**
- **Where:** cp2e (`:1174`, `:1210`), cp2d (5, from `:361`), cpl10 (`:1070`), cp2a (3, from `:329`), cp2g (8, from `:1065`), cp4c (11, from `:1155`).
- **What they guard:** they narrow `None` types on invariants. Under `python -O` a broken invariant would pass `None` into gap reasons and text without raising.
- **Rule:** round 11 Q12's reason ("an `assert` is stripped under `python -O`") was applied only to the CP-2G M2 site. That site is now an explicit raise at `cp2g.py:328`.
- **Test run:** the six modules' tests pass under `-O` (1367 passed), so no test depends on an assert firing. This is a policy decision for the owner.

**No catch-all:** every `except` names a specific exception.

### Info

**I1. Issue-frame spellings are consistent within each module.**
- CP-8 always uses `text is empty` (`:584`, `:624`).
- CP-L10 always uses `empty` (`:994`, `:1012`, `:1026`, `:1029`).
- Every other module uses `empty text`.
- The only gaps are M1 (CP-3C has no blank frame at all) and M2 (CP-4C's plain fields have none).
- The CP-2E path spelling is the known owner item.

**I2. How the quote readers compare.**
- **Probe:** `p_readers_diverge.py` ran the library `FIGURE_CASES`, the class-review inputs (wrap-minus, overlap L1, the CP-1D wrap-sign cases, CP-8 cases A-C), 30 extra cases of mine, and 57,302 seeded fuzz quotes.
- **Result:** apart from M3 and L1, every case and every fuzz quote gives the same answer in all four readers.
- **The B3 text check** is the same predicate in `cp3d.py:260`, `cp8.py:441` and `cp2e.py:649`. I checked this by reading.
- **A shared helper at Stage 2: yes, once M3, M4 and L1 are ruled**, because today each helper encodes a different answer to them.
  - Put it in one module-local file under `src/deploy_workflow/owners/`, not in `deploy_vii` (round 11 B3 ruled against a helper there).
  - It would hold: `readings`, the round 10 minus pattern, the unsigned-token spans (with CP-3D's B2 digit-start condition as a parameter), the B1 page test and B3's `wrap_split`.
  - CP-1D keeps its own signed-amount enumerator but calls the shared page test.

**I3. jscpd: not run.**
- **Why not:** there is no jscpd on PATH and no repo tooling or config (no node_modules, no `.jscpd.json`, no pre-commit or CI file). There is an npx cache copy outside the repo, which I did not use.
- **Estimate for the quote helpers:**
  - the only exact clone is the 3-line `_readings` (`cp1d.py:551` = `cp3d.py:207`; `cp2e.py:512` differs only by a comment), which is below jscpd's minimum size;
  - the four helper blocks are 54 + 49 + 26 + 25 code lines implementing one rule four ways, so they are semantic clones that jscpd does not detect.
- **Estimate across all Stage 1 owners:** about 5.0% of code lines sit in exact runs of 5 or more lines (`p_dup_estimate.py`). That is above the 3% threshold, but it comes from the cp4c/cp2g/cp2h cell and builder scaffolding (for example `cp2g.py:873` and `cp4c.py:999`), not from the quote readers. It is a rough line-based count. Since the gate is not wired, this goes to the owner.

### Fix plan (Sonnet, test first, one task each)
1. **CP-3C (M1)**, mx-feature, reviewed by mx-precise:
   - in the `cp3c.py:201` loop, add `if not text.strip(): issues.append(f"{field}: empty text")` (CP-3C pins no frame, so the fallback applies);
   - add a `defect_classes.BLANK_CASES` adapter test over the 7 field paths.
2. **CP-4C (M2)**, mx-feature:
   - in `cp4c.py:926-945`, before `guard_issues`, add: kind `plain` and `not text.strip()` gives `<path>: empty text`;
   - add a `BLANK_CASES` test over the 9 plain paths (`""` included, since there is no schema refusal to stand).
3. **LEAD batch:** add M3, M4 and L1 to `quote-sign-questions.md`. After the rulings, CP-1D's change is the guard on `_SIGNED_AMOUNT`.
4. **Docs (RESUME Stage 2 notes):** add `cp2h:1623` and update the line numbers to 840 and 953.
5. **L3:** goes to the owner as a policy decision.

### Probe exit codes
- Fast lane set: **exit 0** (3629 passed, 2 skipped, 1 xfailed).
- `p_readers_diverge.py`: exit 1. It fails on the 404 M3 cases; the other 0 disagreements are outside the known questions, and its 2 known-question divergences are L1.
- `p_cp1d_leading_point.py`: exit 1.
- `p_comma_thousands.py`: exit 1.
- `p_quote_wrap_sign.py`: exit 1.
- `p_cp3c_blank.py`: exit 1.
- `p_cp4c_blank.py`: exit 1.
- `p_dup_estimate.py` and `p_dup_helpers.py`: exit 0.
- pytest under `-O` on cp2e, cp2d, cpl10, cp2a, cp2g and cp4c: 1367 passed.

Not verified: CP-2H's blank coverage (read, not probed); CP-5, CP-3 and CP-4 (I relied on the inventory); whether each field's empty-text path matches the path of its other issues, beyond the known CP-2E item; the label readers (`_labelled`) across modules; jscpd itself (not run; the figures above are estimates); whether `host.py:675` falls under §5; asserts under `-O` on invalid states; the effect of M3 and M4 on a composed CP-1D result with a stated amount (only the issues and `_basis_amounts` were checked); any overlap with the R1 or R2 findings.
