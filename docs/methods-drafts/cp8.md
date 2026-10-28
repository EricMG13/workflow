# CP-8 method adaptations (draft for `methods/cp8.md`), 2026-10-28, revision 4

Source method: the r14 CP-8 skill and its step bundle (provenance literals in `cases/cp8-owner/manifest.json#method_source`; outside this repository, never read by the builder). This file records every place the oracle departs from, narrows or adds to that text, so a reviewer can accept or reject each. Nothing here is policy until LEAD freezes it.

## Adaptations with no r14 text (review 1 open question 3, accepted)
| # | Adaptation | r14 text | Oracle |
|---|---|---|---|
| A1 | T7.1 Confidence column | T7.1 has no confidence column | decision confidence is a decision field (from CP-6 `CONFIDENCES`); T7.1 shows it |
| A2 | T7.4 split | one column "Variance (direction + magnitude)" | two columns, `direction` and `magnitude`, so Python-derived direction is its own fact |
| A3 | `cp8.what_changed` rails table | none (the skill renders no Front Page block) | one fact per line (decision, three measures, attribution, summary) for the `what-changed` block, Python-resolved claim text |
| A4 | Hit-rate formula | REF_CP-8_07 names "hit rate" without a formula | Thesis Confirmed decisions / decisions labelled other than Insufficient Information; missing when none labelled |
| A5 | Interim wherever the window's closing is not observable | "mark it interim and note the open window" when not observable | not observable -> interim: no source type here states that a window is closed, so every T7.3 row is Interim, including a row with no realised entry (value cells are gaps, the Interim cell a known fact); Final never occurs |
| A6 | One decision per run | a decision population, gate at 3 comparable decisions | one Prior Case record per run, so the gate is never met and T7.6 is always the gate row |
| A7 | Module-status rule | Completed / Completed with Limitations / Blocked by availability | Completed only when no outcome absence, all measures compared and no realised entry Interim (review H2); Blocked never a head status (a missing record is refused at begin through CP-0) |
| A8 | Claim set | none (narrative `### Decision`) | claims `CP-8-VAR-01..03`, `-WIN-01`, `-ATT-01`, `-CAL-01`, `-VIEW-01`, `-OUT-01` (no outcome) |

## Adaptations review 1 listed as unrecorded
| # | Adaptation | r14 text | Oracle |
|---|---|---|---|
| B1 | Opening view length | REF_CP-8_09 / skill: opening view 90-150 words | the synthesis is one sentence of about 50 words (analyst text, digit-free); the length is not validated |
| B2 | Outcome metric set | skill Outcome Metrics: realised spread change, rating migration, default or restructuring incidence, realised recovery against the CP-3A estimate, holding period against plan, exit-trigger discipline | total leverage, interest cover and the loan mid are compared (the only measures the pack's expected side states); the default or restructuring row is a T7.3 statement (M3); spread, rating, recovery, hold and exit are `absence`/gap rows because the Prior Case record states none (T7.2, T7.8) |
| B3 | T7.7 columns as rows | T7.7 "hit rate, realized-vs-expected by cut, attribution distribution, lessons register" | T7.7 is a two-column table (Value, Basis) with one row per measure, per label and per lesson |

## Adaptations added or changed in revision 2 (C1, C4, C12, C13 amended in revision 3; C14-C17 added)
| # | Adaptation | Reason |
|---|---|---|
| C1 | Flagged downside "named and sized" (REF_CP-8_05) | The Prior Case record's downside line carries a stated size (total leverage above 1.75x or interest cover below 5.75x, invented). The analyst records each size in `thesis.downside_sizes` (measure, comparator, level, quote: a `prior_case` span of the downside-paths quote that states `<measure> <comparator> <level>x`); Python decides the breach (strictly beyond the level, Decimal) as `derived.<m>.downside_breach` and the calculated fact `T7.5.<m>.breach` (Breached or Not breached). A Flagged Risk Materialized metric attribution needs a recorded size and a breach; an overall Flagged needs at least one such metric; the `flag_quote` span rule is kept. Replaces revision 2's quote-only `flag_sized` rule (S3). |
| C2 | Attribution bases and synthesis say only what the sources show | leverage up, cover down, beyond the sized thresholds; no source states earnings weakened, so no basis or claim says so (M1) |
| C3 | T7.3 Evidence column (r14 REF_CP-8_03 "Evidence ID") and T7.8 Missing Item column (REF_CP-8_08) added (M2); T7.8 gets the analyst field `missing_item` per extra gap | brings the columns to r14's Output profile |
| C4 | T7.3 default or restructuring row (SKILL.md Outcome Metrics) from a `default_restructuring` submission field `{as_of_text, quote}`: an issuer statement that states default or restructuring incidence (S4), dated after the decision, required with a realised outcome, forbidden with `outcome_absence` (M3) | r14 lists the incidence among outcome metrics; the update note states it |
| C5 | Loan-mid variance magnitude in basis points of par (`basis_points`, "50 bp"), not percent (L2) | 0.500 is points of par; the relative move is 0.506% |
| C6 | Decisions recorded is a Python count of decision-record sources; decisions required is a schema rule and the r14 constant (L1) | neither is an analyst or source value |
| C7 | Distribution and direction counts are null with nothing compared (M4) | a stored 0 would contradict the missing T7.7 distribution |
| C8 | Pre-decision comparative on the update note (twelve months to December 31, 2025, 1.67x) | makes the "realised must be dated after the decision" rule reachable (H4) |
| C9 | Synthetic label on every page and the pack limitation "Synthetic test source (invented); not an issuer or market fact." (H1) | CP-1C precedent; the sources are never part of a product pack |
| C10 | Prior record is an offline hash-bound pack source of authority `unknown`; authenticity is its hash | D5 (lease) |
| C11 | Design band tile (Since last Report, Deteriorated, Prior Case date, N changes) not produced (L4) | no state word is derived; recorded as an unproduced design element |
| C12 | Validator wording, digit rule, prohibited-phrase list, issue strings | proposals; product-produced are `Field required`, the tool-use texts and the three citation failures (source outside the pack, no such locator, quote not found; `readiness.citation_issues`, probed for r03, r04, r54 and the blocked attempt) |
| C13 | One untested validator class: bid exceeds offer (unreachable by construction; reserved id r38). A metric attributed twice is pinned (r42) with its two identical issues, because the validator reports once per occurrence | stated in `expected.json#refusal_coverage` |
| C14 | Complete journaled tuple per refusal: validator issues, then RULES issues. r04 (source outside the pack) and r30 (source outside the host scope) each pin the validator issue and the `Cited page not read through read_pages` issue of the same citation (CP-DR `citation_outside_pack` precedent); the builder asserts the RULES part of every literal | `RULES(text, seen)` is pure over text and `Seen` and cannot know pack membership or scope |
| C15 | The update note carries two more invented lines: no default or restructuring as of December 31, 2025 (makes r57 single-issue under the subject rule) and leverage 1.70x for the twelve months to February 28, 2026 (gives r68 a real quote; fixture_not_breached uses the same figure) | no accepted literal uses either line |
| C16 | Strictly-beyond rule: a figure equal to the level is not breached (fixture_not_breached pins 5.75x against below 5.75x); a size is not checked against a metric without a realised value | the size names a limit that was crossed, not met |
| C17 | Dependent issues are not repeated for an attribution on a measure: when that measure's size entry was itself refused, or its realised observation was refused, the attribution adds no size issue. This is not a general rule: the overall Flagged rule (checked unless nothing is compared) and the fallback for a missing downside-paths quote can still add a dependent issue | one defect, one issue |
