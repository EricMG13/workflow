# Phase 3 (market evidence) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-3-market-evidence.md` (draft, mx-feature, 257 lines).

## Controller rulings on the draft's open questions (applied recommendations)
- **Q1** CP-3D takes context quotes only; deal talk has no single price level and stays CP-3's
  indicative_talk range row.
- **Q2** CP-3D has no CP-1 input: one `facility_id` per submission.
- **Q3** a minified `context.json` is cited by anchoring on the quote's JSON object; a residual collision
  becomes a named gap, never a guessed span.
- **Q4** a quote row with no figures becomes a named gap (never zero).
- **Q5** prompt text is O6's (the composer embeds CP-3's context block); Phase 3 adds no prompt text.

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (2 High, 4 Medium)
Probe: `scratchpad/p3probe/probe_phase3.py <repo>` (exit 1).
- **H1** (:127-142) R3 pack keeps `third_party` source `market` with observed and talk rows in the positive
  submission, so talk-only/deal-talk cases are not talk-only; m01/m02 numbering clash; T3.3 order of Python vs
  model rows unstated; "High refused" already true on R3 (CP-2 restricted); `no-quotes` cannot equal R3
  (pack hash). Fix: Task 0 names each file's pack sources and exact submission (`market_evidence: []`, basis
  quotes from Python quotes); Design 2 fixes T3.3 order; full issue strings pinned; "identical except
  `pack_sha256`".
- **H2** (:104-115) O6 overlap unsafe: `relative_value` is an existing O6 step (contract unchanged, o6 :109);
  today's rule (live/prompts.py:583-587) makes basis quotes repeat a `market_evidence` row; O6 rule O3 (context
  never cited), M6 sentinel (no context figure in a prompt), and CP-3D's rule list from
  `cases/cp3d-owner/expected.json` all conflict or miss the new checks.
- **M1** (:45-50) the engine reads unchecked bytes (`prepare` never calls `load_context`): named issues for a
  non-plain number, a non-ISO or post-as-of date, an identity differing from the run; RED tests on a plain
  `prepare` pack.
- **M2** Goal :13-14 vs Designs 4, 8: the model copies `"price"`, `level_text`.
- **M3** CP-3D: `context_observations` never shown; `own_limitations` lacks `run_as_of`; single-dealer text
  (cp3d.py:1655-1660) false for context quotes; `ContextRefused` in `upstream_of` (:1938) is an exception.
- **M4** `market_evidence_note` (:1312-1318) and `confidence_caps` (:1319) ignore context-only evidence and
  the stale cap.
- Lows: caps line :658-662; level phrases :127-144; CP-3D refusals [0..18]; `context_evidence` has three
  signatures; byte-identical and basis-copy tests are guards (pass today), not RED; Design 3 named gap for
  split key/value or non-unique quote text, anchor at the object's `{`; Python cells raw `Cell`s with
  `value_class="source"` (Q-X), not `out.text`.

## Controller rulings (2026-10-31)
- H1, M1, M3, M4 and all Lows accepted as proposed.
- **M2:** no model copies a context figure (plan architecture line). Python's T3.3 rows carry the figures;
  the model refers to them by row id only (basis entries reference Python rows by id; no `price` /
  `level_text` copy). The submission schema change sits in `cp3_relative_value.py` (B6). Cost if wrong: a
  schema change CP-6's reading of T3.3 must follow (check it).
- **H2:** `live/prompts.py` (the `relative_value` contract text) stays unchanged: it is `src/deploy_vii`
  outside B6 and goes to the user (final report). Phase 3 adds a task "O6 follow-through" (after O6 is
  built): the composer embeds Python's evidence rows as a fenced data block for `relative_value` and
  CP-3D, with a step rule "rows from the context are Python's; refer to them by row id; never copy their
  figures"; O6's M6 sentinel test exempts exactly that block; O6 rule O3 stays (the model never cites
  `context`); CP-3D's and CP-3's rule lists gain the new oracle's refusal ids through the O6 rule-list
  process (separate writer, `mx-precise` review). Until the user rules on the contract text, a live CP-3
  run may conflict with the unchanged contract; offline tests drive recorded submissions.

## Re-review of rev 2 (mx-autonomous): fix (2 new Medium)
- H1 (:137-160, :54-57; CP-6 reads only T3.3 `kind` facts, cp6_committee.py:570-576), H2 (:118-135, Task 4
  :227-240), M1 (:45-53, :160), M2 (:71-80, :104-106; within B6), M4 (:92-97) fixed; M3 partly open (N2).
- **N1** (:71, :100) `content_hash` = sha256 of `model_dump_json()` (contracts.py:78-79): new
  `Basis.context_rows=()` / `Observation.context_row=None` change every no-context submission and head hash,
  breaking the byte-identical guard (:194-195). Fix: omit both fields from the dump when empty/None; guard
  pins the R3 positive submission's hash as at HEAD.
- **N2** (:115-116, :211) CP-3D has no view and no CONTEXT block (owner_workflow.py:212-225, :402-405): Task 2
  adds a pure data function to `cp3d.py`, Task 4 embeds it, the test targets it.
- Lows: :35 old `context_evidence(pack)` signature; :257-258 "Design 8" → Design 9.

### Controller rulings
- N1, N2, Lows accepted. N1's omission is done inside the models' own files (`cp3_relative_value.py`
  `Basis`, B6; `owners/cp3d.py` `Observation`), e.g. a wrap serializer that drops the empty field; no
  `contracts.py` change. Also (from Phase 4's review): name Design 3's helper `src/deploy_workflow/context_cites.py`
  (object-anchored citations; Phase 3 builds it, Phase 4 reuses it).

## Re-review of rev 3: approve
- N1 (:75-78, :106-107, guard :202-205), N2 (:121-124, :220), `context_cites.py` (:70-73, :213) fixed. Two Lows
  applied by the controller (CP-3D hash pin in the guard; bid = ask minified fail-safe stated).
  **Phase 3 plan approved.**
