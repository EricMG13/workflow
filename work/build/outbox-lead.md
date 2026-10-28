# Undelivered to LEAD (app paused session messaging, 2026-10-28)

Modules: rounds 6f and 6g are on the lane (eb88467).
- **CP-3D:** the 6g leading-zero rule went into its running 6e task.
- **CP-1C:** the 6g rule lands after its scoped review.
- **CP-2D:** 6f lands together with A1/A5 once the oracle batch arrives.
- **CP-2H:** its adversary reviewer will show a mutant for each of the 29 refusals.

**CP-8 round 6c** is applied in a5c4011: 129 passed, and 26 of 26 mutants were killed using a full-copy runner. The earlier runs edited the file in place, so they were not shadowed. Its first adversary review has been dispatched.

**One case is still unruled.** It is reachable, fails closed, and is pinned by a test.
- **The case:** a quotation split on one side and missing on the other, without `outcome_absence`. Example: the expected bid and offer are dated differently, and no realized quotation is supplied.
- **The current code:** `_unpinned("a loan_mid row with a split and a missing side")`. Before 6c, the code silently wrote the "Realized …" row.
- **Needed from LEAD:** the T7.8 `not_compared_loan_mid` wording for this combination, and whether the missing side adds anything else.

---

**CP-3C round 5** is applied in 196b174, with 129 passed; the report is at `work/build/stage1/cp3c/round5-report.md`. C-7's test also caught a real defect: gap copies were dropping the upstream period, and that is now fixed.

Choices beyond the rulings, for you to confirm (full text in the report, "For LEAD" 1–7):
1. **Claim forms.**
   - Every unruled claim slot uses the figure-or-chip form.
   - The NEED-01 and LME-01 cause is the reason with `Not calculable: ` dropped.
   - The LME-01 FX form stacks semicolons.
2. **T3D.8 labels and kinds,** mirrored from CP-2D D-1:
   - `Facility currency (<id>)`, a Limitation;
   - `Facility schedule`, a Gap;
   - `CP-2D maturity wall cross-check (<id>)`, a Limitation;
   - `Facility register and wall (<id>)`, a Gap.
3. **The unmatched-facility own line** repeats the reason verbatim. A facility missing from the register is labelled by its id.
4. **Precedence.**
   - An unmatched facility counts as unranked.
   - An empty register overrides every other reason.
   - Amortisation comes before FX.
   - When pro forma cover is not meaningful, it takes the cash-interest reason.
   - The FX reason prints the run currency.
5. **Still raising "(not pinned)":**
   - a USD facility with its wall principal missing;
   - a missing maturity date, months, inside flag, horizon or name;
   - a negative total principal;
   - a T4.18 principal with no currency.
6. **Wall-disagreement "shows both"** is Stage 2, like CP-2D L4.

Its next round batches these answers with A1, A5 and the oracle-batch re-pin, and then the first adversary review runs.

---

**CP-3D rounds 6e and 6g** are applied (fc8c505, 215 passed) and under scoped review. Two points for your information:
- The leading-zero issue uses the frame's `<path>`, which is `observations[i]` for levels. Every pinned level issue uses that form; the ruling's example used `level:`.
- Recovery `percent_text` is not quoted and is not in the 6g field list, so it gets no leading-zero check.
