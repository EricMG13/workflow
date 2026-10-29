# Stage 2 close release plan (Modules owns; user 2026-10-29: include 0d-d with one review; fix the CP-DR question_id wedge)

Branch: `claude/s2-release` in `../s2-release`, cut at lane f1544a3. Items: `close-release.md`.

1. **W1, integration (mx-feature).** Merge `lead/cp6-freeze` 562a3bc, then `lead/0d-d` 0daac2c. Then re-pin against the tip:
   - `methodology.json` digest consumers;
   - the business_context, readiness and cp4_legal pins;
   - the reuse-manifest `project_commit`.

   Double rebuild must be identical; gates are the fast set and pins.
2. **W2, three agents in parallel from the W1 tip.**
   - **A, oracle re-pins (mx-feature).** Work through every `cases/` item in close-release.md in cascade order. Remove each named test delta (`CP2D_D7_DELTA`, `CP3C_D7_DELTA`, `PERIOD_DELTA`, `GAP_VALUE_CLASS_DELTA`, `STAGE2_REFUSAL_DELTA`, `PRINCIPAL_PERIOD_DELTA`, `GAP_CURRENCY`, `CP1A_BOUND`, the CP-2G blocked xfail and the CP-4C v08 pin). Switch own derived-fact citations to round 3 in CP-2H, CP-1C, CP-2G and CP-4C, together with their oracles. Commit the view trees. Amend the lease pin headers.
   - **B, lease and contract text (mx-feature).** Lease body text, TOOL-CONTRACT rows, the protocol §6 line and `MODULES.csv`. Do not touch lease pin headers; they belong to A.
   - **C, product items and Lows (mx-feature).**
     - `is_blank`: Cc, default-ignorables and U+2800.
     - `citation_issues`: refuse a blank quote.
     - The 0d-c Lows.
     - CP-DR `question_id` length (owner item, fix approved).
     - CP-DR/CP-3D RunText check made unconditional.
     - CP-3D `json_object`.
     - The remaining `lows.md` items.

     C reports any pinned file it changes, and W3 re-pins it.
3. **W3, integration.** Merge A, B and C, then regenerate pins. Gates: fast set, all render suites, pins.
4. **W4, one release review (Opus).** It includes 0d-d's first review, plus a fix batch if needed.
5. Merge into the lane. Stage 2 is closed.
