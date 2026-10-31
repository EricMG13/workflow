# Stage 8-vii ledger (deploy_vii Codex fixes; branch claude/s8-vii off lane 5a1d2e2f)

- 08:55 User directly, this session: approved H03, H09, D1-D3, CZR cash scope (AskUserQuestion, all four selected); approved controller running builders' RED/gates with the lane venv ("Yes, you run them (Recommended)").
- 08:55 Sent Modules the D1-D3 extractor contract and 3 questions (D2b/H02, omitted consumption, cash precheck); D1-D3 waits for its answer.
- Ruling: A (H03+H09) and C (cash plan) run in parallel with B later — disjoint files and isolated worktrees, so no conflict — cost if wrong: a merge conflict in tests, cheap to resolve.
- Ruling: whole-branch review by mx-precise, not mx-architect — no Fable after 2026-10-28 (memory) — cost if wrong: a weaker final review.
- 08:57 Modules replied: agree, with a D2 amendment (unit/scale captions and wholly parenthesised labels stay headers; seven filed CZR pages must not change); omitted consumed later by Modules; cash precheck after its T1 merge. Lane has merged T3 (cdfcd5b0); item 82 soon (manifest conflict expected on the D12 commit).
- 08:57 Golden for the seven CZR pages generated at 71a20021 (= 5a1d2e2f code) with the lane venv: czr-extract-golden.json (27/27/33/33/29/38/27 lines).
- Ruling: D1 omitted excludes lines in the returned headers and header-shaped lines ending in a bare year, not every _is_header line — a single-value row naming a month would otherwise vanish silently — cost if wrong: extra omitted candidates Modules must dispose of.
- A built: claude/s8-vii-a RED 4be0c0b7, fix a147d816 (mx-feature).
- 08:59 A RED @4be0c0b7: 6 failed/34 passed for the reported causes; fix @a147d816: 854 passed, 1 skipped; ruff new PLE2515 x2 (tests, literal U+200B) + 2 over-long lines → batched into A's fix round; format 0; mypy 0. mx-precise review dispatched.
- 09:10 A review mx-precise: APPROVE, spec ✅; Lows: L1 pin full TL10.4 string (test_report_view_tl10_4.py:120-122), L2 PLE2515 x2 (test_source_context_blank.py:141/:158), L3 rewrap report_view.py:1606, source_context.py:355/:369 → end batch.
- 09:10 probe_h09 @a147d816: exit 0 (visible publishes; zwsp source context refused with the lacks issues). Stored-journal scan (journal probe + blank-dimension check, lane src): 2 hits, both the Codex-review probe's own zwsp store in its scratchpad; no case, test or kept store has a blank dimension; 86 errors are malformed test blobs in tmp dirs.
- Task A: complete (commits 5a1d2e2..a147d81, review clean; 3 Lows to end batch). agent=mx-feature fix-rounds=0 gates-first-pass=n (new PLE2515)
- 09:10 B built: claude/s8-vii-b RED 24f0a5af, fix 0a4917ed. RED run: collection error (ImportError OmittedLine) — whole file red at RED, golden test not separately red-checked (golden generated at base, so it holds there by construction).
- 09:13 C plan (mx-autonomous) returned → C-cash-plan.md. User directly: "Yes, both (Recommended)" for financial_contracts.py (declaration) and cash_bridge.py (G2/G3).
- Ruling: declaration lists its items (planner fault (a)) instead of a fixed three-balance scope — a fixed scope never passes for issuers without noncurrent restricted cash — cost if wrong: the user wanted exactly three balances; restricting the Literal is a one-line change.
- Ruling: G2/G3 in cash_bridge.py beside the bridge checks; prompts.py not edited (docstrings describe the field); no double-counting validator; no schema bump — cost if wrong: the model may under-use cash_scope until prompts mention it.
- Ruling: no precheck change asked of Modules for CZR (rows on non-statement pages; plan §7); the optional CFS-page rule is offered — cost if wrong: Modules builds it later.
