# Controller findings for the golden fix round (batch with the reviewer findings)

- **G-1 (all cases), scale.** Store values as printed. Facts printed in USD thousands take `scale: "thousands"` with the unscaled value; the checker change is in flight.
  - SHC rescaled thousands to millions, which breaks "do not rescale".
  - BGS used `scale: null` for thousands.
  - Ruling (controller, 2026-10-31): keep printed units; conversion happens in scoring code.
- **G-2 (all cases), zero-width characters.** The checker will delete U+200B, U+200C, U+200D, U+2060 and U+FEFF from both text and quote. Strip them from your quotes.
- **G-3 (BGS), context.json.** `peer_source: "user_list"` with no peers. Use the form default `cp_dr_public` unless the user supplies peers; check `build()`.
- **G-4 (SHC), dash as zero.** A printed dash is recorded as 0. Acceptable under SEC convention (dash = nil). Keep the dash in `printed`; the gap_reason stays null.
- **G-5 (TDG), report missing.** `prepare-report.md` is missing. Write it from the preparer's hand-back (counts, judgment calls, limitations, Not verified).
- **G-6 (TDG), legal_documents.** context.json sets `attachments.legal_documents: "none"`, yet the golden expects CP-4 covenant facts, and "none" makes CP-4 blocked ("CP-4 has no sources"). The proposal says CP-4 takes "executed or filed documents", and the 10-K is filed. Ruling: use `"executed"` (the form default) and note in limitations that the credit agreement itself is not in the corpus.
- **G-7 (IHRT), mixed scales.** Once the mixed-scale checker lands, add the omitted derived facts (participation, post-exchange totals) and store "$3.9 billion" as decimal 3.9 with scale billions.
- **G-8 (NATL), CP-0 coverage.** CP-0 is listed in not_golden, but the pathway needs CP-0 identity and document facts like the other cases. Add them. The "Technology" sector label is the preparer's own and not from a source: cite the filing's description or leave sector empty and list it in needs_user_input.
