# O6 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (4 High, 7 Medium)

Target: `docs/superpowers/plans/2026-10-31-part-b-o6.md` draft (216 lines).

- **H1** (:109, :118). Rule 5 "as `build` does" gives the 12 read_inputs steps without pack tools
  (narrative, readiness, quality, credit_synthesis, integrity_review, committee_challenge, cp2a, cp2d,
  cpl10, cp2g, cp3c, CP-1B) `submit_only_rule` ("your one tool is {submit}… every input is in this
  prompt", prompts.py:917-923); unchanged contracts name blocks never sent ("SOURCE block id=step:financials";
  "`integrity-scope` CONTEXT block", CP5_SCOPE_RULE :620; "`cp2_rows` in the CONTEXT block", CP-6); the
  faithful test would lock it in. Fix: composer's own rule 5 for `inputs != "none"` naming read_inputs and
  mapping each named block to the read_inputs result; RED test: no such prompt contains "every input is in
  this prompt"; faithful test only where the tool set matches `build`'s.
- **H2** (:87, :113). CP-3 has `inputs="none"` and no `view` (owners/cp3.py) but its rules need
  `market_evidence_sources`, `cp1_facilities`, `cp2_rows`, `cp1_facts` in CONTEXT (prompts.py:~584-597);
  CP-1A loses `cp1_facts`; cp3d, cp2e, cp8 get no source list. Fix: `PromptRequest` carries store and
  attempt; the composer embeds `module_context(store, attempt, "relative_value")` and settled CP-1 facts as
  `build` does, and a pack-facts body from public `PreparedPack` fields; RED test: CP-3's prompt lists the
  attempt's `cp1_facilities`.
- **H3** (:41, :135, :170). CP-1B targets the schema O1 replaces: O1 Task 3's `EarningsDeltaOwnerReview`
  (two period ids + three assessment literals; Python derives the 12 selections; o1.md:239-241, Q3 :361),
  `rules="none"`, core in `owners/cp1b.py`. Fix: use `cp1b.SCHEMAS["earnings_delta"]`, `cp1b.view`, its
  entry validator; check 7 becomes "a period pair `build_earnings_delta` accepts, plus the three literals".
- **H4** (:115, Q4 :209). "Names only" for pins breaks D4 and the O6 row (:367; Phase 6 item 2): cp2a, cp2d,
  cp3c have no pack tools, so attempt 0 fails by construction; rule O3 forbids what D4 requires.
- **M1** (:180-184). G8 fault branch cannot fire: `validate_review` already refuses a review not assessing
  every live consumer once (readiness.py:345-350); Python writes `exact_command` ("Run <id>" for READY and
  READY_WITH_LIMITATIONS, "DO NOT RUN" otherwise, readiness.py:502-508); test (3) needs a forged head; O3
  journals `RefusedBegin.missing_commands`. Fix: drop `MissingRunCommand`; the RED test drives a CONDITIONAL
  judgment and asserts O3's record; sentence: "Python writes Run <id> for READY or READY_WITH_LIMITATIONS;
  any lower readiness stops that module in this run."
- **M2** (:141). The 12 existing contracts carry `a.`, `b.` letters, not `[<id>]` tokens. Fix: the composer
  appends a rule-id index line for them; the test checks it.
- **M3** (:135, :139). The AST extractor finds only `validate_ledger` in cp8 (its checks are
  `_Checker._decision`, `_thesis`, `_sizes`… appending to `self.found`, cp8.py:544-990); cp2e and cp3d build
  issues inline. Frozen oracles list every check: `cases/<m>-owner/expected.json` `refusals` (cp2a 31, cp8 69,
  cp2e 27, cp3d 19, cpl10 19) plus `tool_use_refusals`. Fix: `checks` holds oracle refusal ids; test 1
  requires every content refusal id covered; AST over issue sites reachable from `ENTRY_VALIDATOR` as a
  cross-check; a mutation probe inserting an inline issue.
- **M4** (:104). O5 builds REPAIR with `build(..., repair_issues=)` (o5.md:172); `build` raises for the 14 new
  steps (prompts.py:1152-1154) and CP-5 (:1172). Fix: Task 2 changes `loop.py` so repair goes through
  `prompt_for(PromptRequest(repair_issues=…))`; RED tests on a new step and CP-5.
- **M5** (:136). Rule statements and texts from the same agent prove only self-consistency. Fix: freeze the
  rule lists (ids, checks, statements) in Task 3 by a different agent, reviewed by `mx-precise`, before any
  writer starts; writers cannot edit them (golden file).
- **M6** (:115, :122). `Run` carries `issuer_id`/`issuer_name` (context.py:711-714) and `build` dumps
  `pack.run`, so the sentinel test and the faithful test conflict; the `context` file is an ordinary pack
  source (context.py:728) readable by pack-tool steps. Fix: exclude fields mapped onto `Run` from the
  sentinel test; a rule that the `context` source is never cited and no figure is copied from it except a
  pinned field.
- **M7** (:134, :180). `source_readiness` already runs a-h (h is `analysis`, prompts.py:701). Fix: id
  `source_readiness.g8`.
- Lows: L1 CP-2E and CP-L10 are in no preset (`plan()`), inventory still right via `OWNER_SPECS`; L2 `build`
  cites stale (:1183-1218 is 1161-1201); L3 Task 1 commits a failing test: use strict xfail; L4 multi-line
  rules truncated by "statement = the line itself".
- Answers: Q1 sound; CP-5 sees `cp5.view_body` (cp5.py:105-134), less than `integrity_scope`
  (live/context.py:181-184), both with `claims_to_review`; state `SCOPE_BLOCKS` is reused for its label only
  and map rule a's "CONTEXT block" onto the tool result. Q2 agree (.md). Q3 agree (`PROMPT_SET_SHA256`).
  Q4 reject "names only": a fenced, hashed `<<<CONTEXT id=pinned-assumptions>>>` JSON block with the step's
  own module's pins as exact normalised strings; rule: "a field this block pins is submitted with exactly
  that value; the block is not a source, is never cited, quoted in prose or computed from"; no rationales or
  other modules' pins; narrow check 4 and rule O3; gate the block on the owner checking the pin (Phase 6).
  Q5 adapt, and change the repair call site (M4). Q6 nobody (M1).
- Injection: rule O2 (ignore directives in tool results) must exempt the submit tool's verdicts and the
  REPAIR block.

## Controller rulings (2026-10-31)

- All findings accepted as proposed; Q1-Q6 as the reviewer answered (Q4: the pinned-assumptions block).
- The pinned-assumptions block is built in O6 but gated off until Phase 6 adds the owner's pin check for
  that module; Phase 6 turns it on module by module.
