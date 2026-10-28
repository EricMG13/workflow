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
