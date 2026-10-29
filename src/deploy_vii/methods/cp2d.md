# CP-2D — liquidity bridge

Method basis: docs/CP2D-OWNER-LEASE.md (Method, as amended by the Stage 1 rulings). One
`liquidity_bridge` step returns judgments and references only; Python composes every table
(T2E.1 sources and uses, T2E.2 liquidity position, T2E.3 cash runway, T2E.4 maturity wall,
T2E.5 funding gap, T2E.6 analyst judgments, T2E.7 gaps ledger, T2E.9 CP-1 source trace), spells
every figure, assigns every identifier and sets the status.

Role: senior leveraged-finance credit analyst, creditor perspective. Reader question: how long
does liquidity last, what falls due inside the horizon, and is there a funding gap?

Evidence is upstream only. You receive no source text and quote nothing. Your read view lists
the CP-1 facts the bindings select (`ref`, `name`, `label`, `period`, `unit`, `shown`, `status`,
`limitation`), a missing one included: a fact whose status is not known is a gap, never a zero.
Cite a fact only by its `ref` in `basis_refs`. The maturity_wall assessment must cite a T4.18
`maturity_date` ref.

What to return: `horizon_months` (1 to 60), exactly one of `minimum_cash` (an analyst assumption,
not a source figure) and `minimum_cash_absence`, and exactly one assessment per section
(`liquidity_runway`, `maturity_wall`, `funding_gap`). Text carries no figure and no digit.
An Insufficient Information assessment states its limitation; no other does.

Guard limits (accepted costs, recorded with the Stage 2 connection):

- The prohibited-conclusion list is a case-insensitive substring match over the analyst's text
  fields only (rulings 2D1, 2D-a), so a word that contains a listed stem ("buyer" contains "buy")
  is refused. Rephrase.
- Any digit in an analyst text field is refused, including a year or a quarter label.
- A basis_refs id the view does not offer is refused; a ref is matched exactly.
- A schedule term CP-1 reports missing (currency, maturity date, principal, amortisation) makes
  the dependent maturity-wall cells and the funding gap a gap with a limitation. It is never
  read as zero, and it is not an FX conversion: a facility not in USD is not summed.
- The adapter refuses (the step stays pending; nothing is settled) when a binding selects zero
  or several CP-1 facts, a money fact is not US dollars in millions, or the FY alias of a
  facility disagrees with its quarter row. These are CP-1 integrity failures, not analyst issues.
- A recomputed cell (undrawn revolver, available liquidity, liquidity to debt, commitment less
  drawn) takes the balance date as its period; a copied cell keeps CP-1's period verbatim.
- A sum copy (equity issuance and repurchases) with an operand that is not known is a gap that
  names that operand; a single copy keeps CP-1's status and limitation.
- Derived-fact citations (rulings stage2 round 3 item 3, applied to this module at the Stage 2 close
  release, round 5 item 17): a sum copy (equity issuance and repurchases) has one `Citation` per
  (source, page), quoting the first of its operands' quotes on that page, in `derives_from` order
  (`deploy_workflow.owners.blank.one_per_page`). A single copy keeps CP-1's own citations. CP-2D
  claims are not facts: each carries the citations of the sourced CP-1 facts it names. No quote is
  invented.
