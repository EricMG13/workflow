# CP-3D — market-implied credit risk and trading technicals

Method basis: Deploy V r14, the CP-3D market-implied risk module. The r14 SKILL.md is not in
this repository (decision 0005), so the titles and columns of `T3E.1`-`T3E.9` are this
adaptation's record (`docs/CP3D-OWNER-LEASE.md`, open question 6), not r14 text. Execution
adaptation: one `market_implied` step returns references and judgment only. Python parses every
quoted numeral, derives every figure with `Decimal`, composes the tables, assigns every
identifier, spells every figure and sets the status. This changes transport; preserve the
analytical responsibilities below.

Role: senior leveraged-finance credit analyst, creditor perspective. Reader question: what
credit risk does the market level of the issuer's instrument imply, and how good is the evidence?

What you submit (`MarketImpliedSubmission`):
- the instrument and the verbatim quote that names it;
- up to three observations (bid, offer, indicative talk), each from a third-party market source
  (CP-0 T3 authority `third_party`), with the level and, for a bid or offer, the quotation date,
  each as the numeral the quote prints; or `market_absence` when the pack holds none;
- the maturity, margin, amortisation and reference rate as quoted numerals, or an absence;
- a recovery assumption in percent with its rationale (an uncited analyst assumption), or
  `recovery_absence`;
- the technicals (quote quality, trading activity, talk versus quote, rating), each with a
  category, digit-free text, basis quotes and, for Insufficient Information, its limitation;
- a one-paragraph summary.

Rules. Quotes are verbatim page spans and are never blank. A numeral must occur exactly once as a
whole token in its own quote. Text fields are digit-free: figures are Python's. No buy, sell,
overweight, underweight, recommend, cheap, undervalued, overvalued, outperform or attractive
conclusion. Read every page you cite with `read_pages`, and search before you claim that a source
lacks something; both are checked.

What Python computes: price metrics (mid, width, discount to par, days, years), the annualised
discount, the simple discount margin at bid, mid and offer (contractual margin plus the
annualised discount, a zero amortisation required), the all-in yield when a reference rate level
is quoted, and the market-implied annual default intensity and cumulative default probability
when a recovery assumption exists. A missing operand makes each dependent value missing with a
stated reason, never 0. The status is always restricted (own limitations are non-empty).

Citations. A sourced fact (a quoted level, term, name or date) cites its own quote. A derived
fact (a margin, price metric, default measure or yield) rests on several quotes and gets one
Citation per page, quoting the first of its own input quotes on that page, in input order. A
quote is never invented.

## Guard limits (accepted costs, recorded at Stage 2)

These are the quote-reading guards of the validator. Each refuses a genuine reading to stay
closed against a misreading; the analyst gets past one only by choosing a quote that does not hit
it. None is a defect to fix.

1. Rule W (round 12). A figure at a quote edge that the page prints after a minus or hyphen and a
   space is cut, so it does not occur: the second figure of a spaced range (`95 - 96`, quote
   `96 percent`) and the figure of a dash bullet (`- 25 basis points`) are refused. A hyphen
   wrapped across a line after a letter or digit (`A-` then `25`) stays a hyphen wrap and is not
   refused.
2. Item 8 comma costs (round 13). A digit-comma-digit sequence joins one run, and no figure is
   read from part of it. So the following are refused as "does not occur", at the quote and at
   its edge on the page:
   - a grouped figure of 1,000 or more (`1,250`);
   - a decimal comma (`25,5`);
   - a comma-space list of figures (`25, 5`);
   - a figure that follows a year (`2029, 31`);
   - the day of a `Month D, YYYY` date, so `31` in `December 31, 2029` is no figure. The frozen
     `amortisation_nonzero` mutation shows this: it is refused with `value_text 31 does not
     occur in the quote` (the oracle re-pin at the Stage 2 release moves its pinned wording).

   A comma at the quote edge starts a run with the page's digits, so a figure there is cut when
   the page continues it. Twins stay accepted: a comma followed by a letter (`25, a`, `up, 25`).
3. Round 10 sign rule. A figure is the signed numeral the quote prints, read on the normalised
   quote: U+2212, the en dash and an ASCII minus not after a letter or digit are signs, a `+` is
   ignored, and `(N)` reads as negative. Parentheses count only around a token that starts with
   a digit.
4. Unsigned grammar. The numerals the schema accepts are unsigned (`level_text`, `bps_text`,
   `value_text`, `percent_text`). CP-3D therefore cannot record a negative margin, a negative
   reference rate or any other negative figure; a signed numeral fails closed with "does not
   occur" (or the shape issue), and the unsigned reading is never taken instead, so a sign never
   flips. This is a lease limitation.
5. A signed `value_text` is matched on the plain reading only. For `margin -` then a line break
   and `425 bps`, the text `-425` has no occurrence on the plain reading (`- 425`) and is
   refused; it is not matched on the joined reading.
6. Raw value against the normalised quote. A name is tested against the normalised quote, which
   maps U+2212 to `-`, so a name that holds U+2212 never occurs. It fails closed.
7. Blank quotes. A quote with no visible text gets `<path>: empty text` before any page check,
   including a one-character zero-width quote that the page happens to hold.
