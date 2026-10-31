# Codex findings + active-session open items (2026-10-31 08:30)

Base: `codex/checkpoint` 3888fe0 (local; `origin` still at 2bbf633).
Codex sources:
- the handoff `~/Documents/Codex/2026-10-30/workflow-claude-handoff-2026-10-30/CLAUDE-HANDOFF.md` (H01–H13);
- the perf review at cbb5806 (P1–P4);
- the DPP parser comparison (D1–D5);
- the evaluation-framework session on `codex/deliverable-design`.

Every Codex item below was re-checked at 3888fe0 by an independent mx-precise reviewer, read-only, against an archive of HEAD. Probes are in `probes/<group>/`. Each one asserts the desired behaviour, so it exits 1 while the defect is open. Seven probes still read inputs from this session's scratchpad (the HEAD tree and the CZR store); point them at a fresh archive before rerunning.

## 1. Waiting on the user

| # | Decision | Raised by | Notes |
|---|---|---|---|
| U1 | Push `codex/checkpoint` (local 3888fe0, origin 2bbf633) | PR manager | Several releases ahead of origin |
| U2 | Release item 82 to `codex/checkpoint` after it merges | Modules | Merge waits on the earnings rerun (about 29% at 08:25) |
| U3 | CZR cash-scope rule (restricted cash in the CFS scope) | Modules | src/deploy_vii: financial_reconciliation, period_reconciliation, statement_validation. The add-back schedule is case files only |
| U4 | CP-1 quality read is uncapped: serve `quality_scope`? | Modules owner list (from the Tool-use research session) | Same root as the Codex evaluation blocker: a 21 MB quality-step result against the 1 MiB provider-result guard, which stops every full public run. CZR read is 16.9 MB. See also P1 |
| U5 | Integrate the perf sweep `claude/vigilant-mendel-070f6d` (679ab5a) | Cut test-suite time session | −30% on E-NO-YOY, byte-identical outputs. Not pushed or merged |
| U6 | F1: duplicate parse cache (about 2.6 GB in a long-lived host) | Cut test-suite time session | The host `_ParsedExecution` (7d0b671f) and the sweep's `Execution.result` lru_cache. **Decide before fixing P3u**, which needs one digest-memoised parse |
| U7 | F2: stale `contracts.py` hash pinned in `cases/cpos-owner` | Cut test-suite time session | |
| U8 | src/deploy_vii fixes from Codex: H03, H09, H12, D1–D3, P1 | this review | Each needs the user's own word (2026-10-30 narrowing) |
| U9 | Codex worktree `codex/deliverable-design` has uncommitted edits to `src/deploy_vii/assets/{app.css,app.js,shell.html}` | this review | Based on S5 05c3b27, not the lane |
| U10 | API key in plain text at `~/Documents/OP Router.rtf`; Codex was pointed at it | this review | Move it to Keychain or 1Password. Rotate it if any transcript printed it (not checked) |
| U11 | Archive finished sessions: open-items, Workflow Test, LEAD multi-round, LEAD | this review | Each reports nothing open; their branches are merged |

### User decisions (2026-10-31, in this session; relayed to Modules and the PR manager)
- U1: push via the PR manager. **Done:** the perf branch 679ab5a was merged as 3aaeb35 (parents 3888fe0 and 679ab5a), and origin `codex/checkpoint` is now at 3aaeb35. No tests were run on the merge.
- U3: approve the declared cash scope.
- U4: serve `quality_scope`; the review stays bound to the full inputs.
- U5–U7: merge the perf branch; fix F1 and F2.
- U8: approve H03, H09 and D1–D3. P1 and H12 are not approved.
- U9: leave the Codex asset edits; review them before any merge.
- U10: the user's own action.
- U11: archived open-items, Workflow Test and LEAD multi-round. LEAD was kept, because its worktree has 182 untracked `work/lead` files and 7 commits not in checkpoint.
- Because of the 2026-10-30 "direct check", the src/deploy_vii items (U3, U8) still need the user's word in the Modules session.

## 2. Codex findings confirmed at 3888fe0

`M` = Medium, `L` = Low. "vii" means the fix lands in user-owned src/deploy_vii.

| ID | Sev | Finding (HEAD location) | Fix direction | Probe |
|---|---|---|---|---|
| H01 | M | A 6-month source satisfies a 9-month YTD period (`financial_workflow.py:536`; duration dropped at :470, :493, :565) | Keep the month count in the flow spec; match the span; fail closed | v-cp1/probe_h01_h02_h08.py, probe_h01_coverage.py |
| H02 | M | An annual header with full-date cells falls through to balance specs, so Q4 satisfies FY (`:588-611`, `_hit` :538) | No balance fallback after a flow span row. Also keep labelled data rows out of `headers` (see D2b) | v-cp1/probe_h01_h02_h08.py |
| H08 | M | A caption with INCOME on a CFS page is classed as IS (`:435`) | **Ruled (Modules item 84):** the page heading wins when the page names exactly one statement. The caption decides only when the page names none or several, and only if it names a statement outright. `tests/test_czr_fixes.py:194-195` are reversed. One owner-list task with H01+H02; it waits for item 82 to merge and for the user's go-ahead | v-cp1/probe_h01_h02_h08.py |
| H05 | M | A lone-surrogate, surrogate-key or 210-deep frame is refused, then every later call gets `identity_mismatch` (`host.py:1053-1060`, `owner_workflow.py:1189`, `financial_workflow.py:726`) | Validate the UTF-8 encode and depth in `_json_arguments` before the session advances. Do not skip the sequence check. Sequence after P3u (both touch host.py) | v-tools/h05_desired.py |
| H06 | M | CP-2H limitation panels show raw `{T2R…}` tokens (`cp2h.py:1862`, :2115; app.js :552/:593/:668) | Build the gap limitation from resolved text | v-render/probe_h06_cp2h.py |
| H07 | M | CP-8 accepts `None`/`none`/`null`/`nan`, then render raises (`cp8.py:621`; guard `report_view.py:145`). Wider than Codex stated | Refuse the renderer's null spellings in `_text` via the shared constant | v-render/probe_h07_none.py |
| H03 | M vii | CP-L10 TL10.4 decision_impact shows a raw token (`report_view.py:1608` `_RUN_TEXT_FIELDS`) | Add `("CP-L10","TL10.4","decision_impact")` | v-render/probe_h03_tl10.py |
| H09 | M vii | Blank or U+200B `accounting_basis`/`entity_perimeter` settle 12 `known` T4.14 facts; `publish_model` then refuses (`source_context.py:353-386`) | Apply `is_blank` in `_lacks` and `_disagreements`. Same class as OI-14/OI-20, but book-level dimensions were never covered | v-fin/probe_h09.py |
| H04 | **L** (Codex: M) | CP-2G over-repayment check uses the ambient Decimal context; negative debt settles at prec ≤ 10 (`cp2g.py:863`, :397). No production code changes the context | `localcontext(_EXACT)` for the loop; `copy_negate()`. CPDR `_share` (`cpdr.py:390`) rides along | v-fin/probe_h04.py, probe_cpdr_decimal.py |
| H10 | L | Two render tests pass while the visible text is wrong (`test_connect_cpdr.py:1333`, `test_connect_cp8.py:1142`) | Assert the exact payload `display`/`table_display`; edit a fact bound into the block | v-tools/h10_desired.py |
| H11 | L | Padding variants collapse in a set (`test_connect_cpl10.py:649`) | Use a list; assert distinct exponents | v-tools/h11_desired.py |
| H12 | L vii | `render(view, report)` accepts another view's report (`render.py:128`). Only tests pass a report | Make the argument private or test-only | v-render/probe_h12_report_binding.py |
| H13 | L | The partial CZR runner exits 0 on missing input or any BaseException (`cases/czr-2026q2-earnings-update/partial-builder/run.py:16-21`) | Re-raise; pass only on the expected QA-39 refusal | v-tools/h13_desired.sh |
| P1 | M vii (runtime) | `_stage_registers` rebuilds the narrative/readiness intermediates; it is called 4 times per run, about 29 s of the 57 s CZR run (`cp1_workflow.py:256-283`) | Reuse the prefix intermediates inside one call; keep every `retained_as` check. Needs mx-adversary review. Keep delivery's triple verification (by design) | v-perf/probe_p1_registers.py |
| P2 | M (latent) | `_IntegrityCatalog.ref()` hashes the full producer on every call: 122 ms/ref on the real 37k-fact CP-1 (`tools/upstream.py:1191`, also :930, :1288, :1457, :1553, :1715). No production caller yet | Hash once in `__init__`; the producer is frozen, so the tamper guarantee holds. Same pattern as sweep P1 (17e07ba). Do it before CP-5 v2 is wired | v-perf/probe_p2_ref.py |
| P3u | M | `upstream._context` re-reads and re-hashes the producer: about 0.5 s, 2–3 times per CP-1B call (`upstream.py:304-378`). The host part is already fixed by 7d0b671f | Route through one digest-memoised parse (after U6) | v-perf/probe_p4_p3.py |
| P4 | L | Full scan or sort per page or lookup, 9–23 ms (`upstream.py:562`, :1731) | Ride with P3u | v-perf/probe_p4_p3.py |
| D1 | M vii | The statement extractor silently drops lines it cannot parse; nothing records them (`statement_extract.py:8`, :133) | Return omitted candidate lines; the precheck refuses or requires a disposition | v-parse/probe_d1_d3flag.py |
| D2 | M vii | Rows whose amounts look like years are dropped or taken into headers; this hides the D3 flag (`statement_extract.py:135`, :141, :227) | Keep labelled rows out of headers; do not drop year-valued data rows | v-parse/probe_d2_d3.py |
| D3 | L vii | A footnote `(1)` is read as −1. It fails closed (column-count mismatch at `financial_workflow.py:396`), so a filed page cannot pass | Treat `(n≤2 digits)` after the label as a marker when the columns are known | v-parse/probe_d2_d3.py |
| D4 | — | Coverage starts from the extracted lines, so it cannot see D1/D2 omissions | Fixed by D1/D2; no separate task | — |

Not verified for any of these: a full CP-1 promotion or delivery run on a genuine store (proofs are at component level), the full test suite, or end-to-end P2/P3u costs (estimated from per-call timings).

## 3. Conflicts and sequencing

- Modules' in-flight item 82 touches only `canonical_audit.py`, `canonical_gaps.py`, `tests/test_cp1_absent_input.py` and the manifest, so no Codex fix collides with it.
- U4 (quality read) would touch `host.py`/`owner_workflow.py` `read_inputs` and `financial_workflow.py:306`. Those are different functions from H01/H02/H05/H08, but the same files, so run them one at a time.
- `host.py`: U6 decision → P3u → H05.
- `financial_workflow.py`: H01+H02+H08 as one task (H08 ruled in item 84), after item 82 merges.
- `statement_extract.py` (vii): D1+D2+D3 as one task, and coordinate the header block with H02.

## 4. Sessions checked

| Session | State | Open |
|---|---|---|
| Modules | idle; runs in flight | Item 82 earnings rerun, then merge; cp4c never-wedges (about 5 h, from 08:00); U2–U4; two item 82 period-hop Lows (end batch) |
| PR manager | idle | U1 |
| Cut full test-suite time | done | U5–U7 |
| Close remaining open owner items | done | Nothing. Merged as f25f62d; deferred runs passed (item 78) |
| Workflow Test | done | Nothing. Its partial runner is H13 |
| Tool use vs M365 Copilot research | done | U4 |
| LEAD multi-round behavior | done | Nothing (it replied: ed5c1c8 is in checkpoint) |
| LEAD | stopped (user) | Nothing new; Modules owns its work |
| Codex evaluation (`codex/deliverable-design`) | external, in progress | Blocked by U4; U9, U10 |
