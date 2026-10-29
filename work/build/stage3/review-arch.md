## Stage 3 end check — `claude/s3-i5` 18dc1fa (base 697fe8a)

**Verdict: REVISE** (one Medium; gates pending)

Probe folder: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/arch/` (run from the s3-i4 worktree with `PYTHONPATH=src:tests L/.venv/bin/python <script>`; not `-I`, it drops PYTHONPATH).

### Findings

**M1 — CR.3 has no G2 delivery scope; `cp3c-fp04-refinancing` is still gated after its prerequisites landed.** `src/deploy_workflow/owner_rendering.py:361` (`DELIVERY_SCOPES`, 17 rows), `tests/test_owner_rendering.py:63,152` (asserts the row is absent). Rev 2 D2 (`docs/OWNER-RENDERING-LEASE.md:313`) gated the row "until the Q-C2 wiring moves the binding and re-pins `cp3c-owner/E#/fp04_render`"; both are done on this tree (`src/deploy_vii/bindings/cp3c.py:43` binds T3D.1 to `funding-gap`; `cases/cp3c-owner/expected.json` fp04_render rebuilt at f71a105; CR.3 oracle frozen, item 11). Rulings item 4 Q-S2 says the row "ships with the Q-C2 wiring in Stage 3". Scenario: a CP-3C FP-04 receipt is refused `owner_render_scope`, so CR.3, one of the nine Stage 3 figures, is never proved rendered-from-settled through G2 (review focus 5), and the rev 3 R3.2 row for `cp3c-fp04-refinancing` has no test. Code is honest (refuses, no fake), so Medium not High. Probe: `p2_cp3c_scope_refused.py` (exit 0 = refused, confirmed). Fix: add the rev 2 row with its banner (`:271`), the R3.2 CR.3 figure assertions, drop it from `GATED_IDS`; or an explicit ruling that it moves to the owner items.

**L1 — `ruff format --check` fails on 5 changed files** (gate, §3): `cases/cp1c-owner/builder/build.py`, `cases/cp3c-owner/builder/build.py`, `cases/cp4c-owner/builder/build.py`, `cases/pins.py`, `src/deploy_workflow/financial_series.py` (already named in `int-report.md:37`, still unfixed). Probe: the ruff command in this report's shell history; rc=1.

**L2 — Item 20 Q1 (S.4 title exact match on the FP-04 fixture) not yet applied**: `tests/test_owner_rendering.py:928` still uses `title_prefix`. Ruled Low for the Stage 3 fix round; rides with M1.

**I1 — S.4 on FP-04 (`maturity-wall`, frozen `s4fp04-expected.json`) sits in no scope row** (probe 1 output: `maturity-wall ... scopes=[]`). Rev 3 R3.2 `:408` and rev 2 D1 defer this to a later CP-2D amendment; documented, owner item.

**I2 — FP-05 CR.2** (`liquidity-runway` on `distressed_restructuring`) has a producer and no scope row (probe 1 `FIGURE-NO-SCOPE`); item 6.2 ruled it renders only on request, no driver case. Documented.

**I3 — DR.6 chip xfail** (`tests/test_chart_render_dr6.py:147`) stands per item 19. Item 20 Q3 verified: in the `gap` case the reason suffix is exactly `(∅ G23, …, ∅ G34)` and every ref resolves to a gap the page index cites; `positive` has none. Probe: `p3_dr6_gap_refs_resolve.py`, exit 0.

**Stubs / catch-alls:** none found. New `except` sites are narrow and re-raise as refusals (`owners/cpos.py:113,124`; `charts.py:931` ParseError). `_chart_fact_cell` strict path raises without a G# (w1). CP-OS `#workbench` exclusion is documented as the recorded shell defect (`cpos.py:39-40`). Legal workaround (item 13) is removed; `test_legal_render.py:358` reads producers from the legal oracle and `:370` asserts the CR.1 figure (item 18 met).

### Pathway × block (gaps only)
| Pathway | Gap |
|---|---|
| credit_snapshot | none (S.5 producer filtered to this pathway; `cp1-model` covers strip, S.5) |
| earnings_update | none assigned (S.5 correctly not drawn, item 9 M1) |
| relative_value | none (RV.3a/b in `cp1c-fp03-peers`) |
| covenant_refinancing | `funding-gap` CR.3: producer and oracle, **no CP-3C scope row** (M1); `maturity-wall` S.4: wired, no scope row (I1) |
| distressed_restructuring | `liquidity-runway` CR.2: producer, no scope row (I2, ruled); DR.6 chip xfail (I3, ruled) |
| portfolio_decision | nothing assigned; PD.1 deferred (inventory) |

### Gate runs (read last, 14:48)
`A.status`, `B.status`, `C.status` empty: **pending**. `fast.log` at ~90%, no failure marker yet: **pending**. `cpos.log`, `czrlong.log` 0 lines: **pending**. No step has passed.

Probe 1 cross-table: `p1_pathway_blocks.py` (its oracle-claims column is empty; the oracle walker did not match the `render` shapes, so oracle backing was read by hand from rev 3 R3.2 `:388-411`).

Not verified: any gate exit code (all lanes pending); the genuine G2 runs on real stores (deferred per items 17/20); figure comparison on genuine owner-run payloads; browser rendering; mypy and suppression counts; mutation testing; whether `cases/PINS.json` was regenerated after the oracle moves (item 6.7); CZR long gate and that the heading fix moves no synthetic oracle.
