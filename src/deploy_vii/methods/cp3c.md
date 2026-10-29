# CP-3C — refinancing and liability-management risk

Method basis: docs/CP3C-OWNER-LEASE.md (Method, as amended by the Stage 1 rulings) and the
recorded adaptation `docs/methods-drafts/cp3c.md` (the r14 CP-3C SKILL.md is not in this
repository). One `refinancing_risk` step returns judgments and references only; Python composes
every table (T3D.1 refinancing need by maturity, T3D.2 refinancing burden, T3D.3 refinancing cost
sensitivity, T3D.4 creditor position, T3D.5 LME capacity, T3D.6 refinancing paths, T3D.7 analyst
judgments, T3D.8 gaps ledger, T3D.9 upstream trace), spells every figure, assigns every
identifier and sets the status. T3D.10 and T3D.11 are registered and unused.

Role: senior leveraged-finance credit analyst, creditor perspective. Reader question: what falls
due, what the resources at each maturity cover, what a refinancing would cost, and which
refinancing paths are open?

Evidence is upstream only. You receive no source text and quote nothing. Your read view lists
the CP-1 and CP-2D facts the bindings name (`ref`, `name`, `source`, `label`, `period`, `unit`,
`shown`, `status`, `limitation`), a missing one included: a fact whose status is not known is a
gap, never a zero. It also lists each facility (text fields only), the optional edges this
version does not read (CP-1A, CP-2A, CP-4, CP-3D), the bounds and the inherited limitations.
Cite a fact only by its `ref` in `basis_refs`.

What to return: exactly one of `repricing` (a margin step-up in basis points, 0 to 1000, an
analyst assumption, with its rationale) and `repricing_absence` (why none is assessed and the
follow-up), and exactly one assessment per path kind (`repay_from_resources`,
`amend_and_extend`, `market_refinancing`, `asset_sale_or_equity`, `liability_management`). A
High, Medium or Low feasibility cites at least one fact; the feasibility is Insufficient
Information exactly when the category is; an Insufficient Information assessment states its
limitation and no other does. The liability-management path is Insufficient Information: the
legal covenant capacity evidence is not bound. Text carries no figure and no digit.

Method:

- Facilities in maturity-date order, ties by facility id; an undated facility after every dated
  one. Months from the balance date follow CP-2D's whole-month rule.
- Principal payable at maturity = principal less amortisation to the maturity date (annual
  amortisation x months / 12, capped at principal).
- Resources at maturity = cash + undrawn revolver - minimum cash + run-rate flow x months / 12 -
  amortisation of every facility to that date - principal paid from resources at earlier
  maturities. Resources applied = min(principal payable, max(0, resources)). Refinancing need =
  principal payable - resources applied; a computed 0 is no need, distinct from missing.
- Cost: the step-up applies to the whole principal payable at maturity; added annual cash
  interest = principal repriced x step-up / 10000; pro forma interest cover = adjusted EBITDA /
  (cash interest paid + added interest). A 0 bp step-up is a known 0; no step-up makes the cost
  cells gaps.
- Creditor position: secured before unsecured, then seniority; claims at or ahead of a facility
  sum the principal ranking at or ahead of it. T3D.5 Base is the largest of them; the LME and
  Stress columns are gaps (CP-4 and CP-2A are not read).
- Zero, missing, not applicable and blocked stay distinct; nothing defaults to 0 or N/A.

Derived cells and citations (lease acceptance 1; manifest `fact_copy_rule`):

- A copied cell (one that carries a `cp1_operand` or `cp2d_operand` and no formula) keeps its
  upstream fact's value, unit, period, value class, citations and calculation id. CP-1's T4.18
  terms and CP-2D's principal and maturity date are `source`; CP-2D's months and inside-horizon
  flag are `calculated`; CP-2D's horizon and minimum cash are `analyst_judgment`.
- A known computed cell is `calculated`, names its formula and carries `calc:<fact_id>` as its
  calculation id, with no citation of its own.
- An analyst-judgment cell and a gap cell carry neither a citation nor a calculation id, unless
  the gap is a copy (it then keeps its upstream fact's).
- Every US$ m cell, a gap included, carries currency USD and scale 1e6, as CP-1 and CP-2D write
  theirs. A claim cites what the bound names and the referenced cells it lists cite, each
  citation once; a copy of an analyst fact is never referenced by a claim.

Guard limits (accepted costs, recorded with the Stage 2 connection):

- The prohibited-conclusion check is a phrase guard, not a semantic review:
  `business_context.prohibited_issues` with its default kinds (peer ranking, instrument
  recommendation, recovery conclusion) plus a CP-3C list for covenant-compliance and
  refinancing-outcome wording. A conclusion no listed phrase names is not caught. The pinned
  probe (`expected.json#prohibited_probe`) records eight analyst sentences the guard passes:
  "Expected recoveries are high.", "We advise lenders to extend.", "Holders should avoid this
  credit.", "Default is likely.", "We suggest an amend and extend.", "Lenders should extend the
  maturity.", "Refinancing is likely." and "The issuer is in breach."; "The recovery is high."
  is permitted by the product. A listed word inside a neutral sentence is refused ("The loan is
  held in compliance with no stated covenant evidence."). Rephrase.
- Any digit in an analyst text field is refused, including a year or a quarter label.
- A basis_refs id the view does not offer is refused; a ref is matched exactly.
- The adapter refuses (the step stays pending; nothing is settled) when a CP-1 binding selects
  zero or several facts, a CP-1 money fact is not in millions, a fact is `normalized`, a
  facility lacks a term CP-3C reads, the FY alias of a facility disagrees with its quarter row,
  or `cp2d_reader` and the CP-2D head's cells disagree. These are upstream integrity failures,
  not analyst issues.
- The reporting currency is CP-1 `cash_closing`'s, which must be set. When cash closing is not
  known, it is the currency the known US$ m facts state; when none states one, the run raises
  (an invariant), never a stamped default. Every other known US$ m fact must state the same.
- A term CP-1 or CP-2D reports missing makes its dependants gaps that say it is not stated; a
  conflicting or not applicable term (or minimum cash) names that status in the same frame.
- The run-rate flow (CP-2D T2E.3.r01) is read from its cell: `cp2d_reader` does not expose it
  yet (`expected.json#consumption.pin_extension_needed`).
