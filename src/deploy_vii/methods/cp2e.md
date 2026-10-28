# CP-2E — macro, FX and hedging sensitivity

Method basis: Deploy V r14 module CP-2E (alias CP-2F). The r14 SKILL.md is not in this
repository, so the table definitions are an adaptation recorded here (lease question 6), not r14
text. Execution adaptation: one `macro_fx` step returns verbatim financial-source quotes and
analyst judgment; Python reads each quoted numeral, derives every figure with `Decimal`, composes
the tables, assigns every identifier, spells every figure and sets the status. This changes
transport; the analytical responsibilities below are unchanged.

## Adaptation record
- Tables (D8 ids; `T2G.1-8` stay registered and unproduced): `T2F.1` sourced operands, `T2F.2`
  baseline exposure, `T2F.3` interest rate shock (one row per shock), `T2F.4` currency shock,
  `T2F.5` hedging, `T2F.6` assessments, `T2F.7` missing inputs, `T2F.8` evidence, `T2F.9`
  limitations. Titles and columns are this module's choice, not r14's.
- Shock conventions: a static, parallel, upward rate move applied once to closing balances and
  FY flows; computed only when the quoted floor is 0 (no reference rate level is sourced); a
  fixed-rate facility is a known zero; a missing term is a gap, never 0. A currency move is the
  foreign currency strengthening against the reporting currency. Shock bounds (1 to 1000 bp, 1 to
  50 percent, at most three of each) are screening policy, not a source limit.
- Deliverables: the module page (`Module.tables` layouts) and the Evidence and Limitations
  rails. No Front Page block is assigned (lease D7).
- Consumption (D3) is OPEN: `cp2e_reader` exposes what a consumer must read; no consumer reads
  CP-2E, so the module is not complete.

## Accepted costs of the quote guards (Stage 2 notes)
A quoted figure must occur once in the quote as a whole, unsigned number, and the page must
print it there as the same whole figure. The guards are deliberately strict; each refusal below
is a known cost, not a defect.

Rule W and the round 10 sign rule:
- A `-` before the first digit is a minus when it starts the text or follows a character that is
  neither a letter nor a digit; a numeral in accounting parentheses is negative. Such a printed
  figure is not an occurrence of the unsigned token. A `+` is ignored.
- Rule W lets one space (a line break included, since `normalise` makes any whitespace run one
  space) stand between the sign and the figure, and one space inside each accounting
  parenthesis. Cost: a spaced range (`2 - 5`) and a dash bullet (`- 25 percent`) read the
  following figure as negative, so it is refused as an occurrence of the unsigned value.

Item 8, a comma joins the digit run (`1,25` and `1, 25` continue the number). Costs, each
refused when the value is the figure shown:
- a grouped figure of 1,000 or more (`1,250`);
- a decimal comma (`1,25`);
- a comma-space list (`25, 30`: both figures are refused);
- a figure after a year (`2025, 30`);
- the day of a `Month D, YYYY` date (`January 10, 2026`: the 10 and the 2026 are refused).
A comma beside a letter does not join (`were 25, a share`).

A sentence operand (facility balance, spread, floor) is at most 999.9999, so a balance of 1000
or more cannot be quoted by this step; that is stated, not a source limit.

## Other notes
- A blank quote (`is_blank`: whitespace and Unicode format characters only, or "") is refused
  with `<path>.quote: empty text` before the page check. U+2800 and control or default-ignorable
  blanks wait on the shared `is_blank` batch; the re-export inherits it.
- `reference_rate` is compared normalised with the normalised quote, so a U+2212 name occurs
  where the page prints `-`.
- Open with LEAD, not built here: the label-decimal question (`spread 25.5` is accepted by the
  labelled reader) and the `fx.` paths item.
