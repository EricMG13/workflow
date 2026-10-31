# O7 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (3 High, 5 Medium)

Target: `docs/superpowers/plans/2026-10-31-part-b-o7.md` draft (245 lines). Probe:
`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-tool-use-m365-copilot-research-8ff28f/9d206924-1225-454b-b5b4-bbf09f856c4e/scratchpad/o7probe/plan_order.py` (exit 1).

- **H1** (:13, :142, :171, :196, :205). Dossier and `peers` as "pack sources of run B" cannot exist when
  run B starts: the pack is fixed at start (hash includes `run_id`, contracts.py:82-95); adding them means
  `replace_pack`, which stales every head (execution.py:918-921); `begin("CP-1C")` always raises
  `DossierNotAttached`. Fix: bind CP-DR's settled head to CP-1C and CP-2 as the existing input binding does
  (`CONTEXT_PRODUCERS`, execution.py:227, 254-258); consumers cite the `ev-*` sources; refreshed by
  `invalidate` (:308-323).
- **H2** (:9-13, :136, :172, :238). Replaying run A's CP-0 into run B cannot validate: CP-0's review must
  match the pack hash, assess every source once and every consumer (readiness.py:338-349); OD8 run C fails
  likewise. Fix: one run: supplied evidence enters the pack at start (files dated after the as-of or
  context cutoff refused before preparation); CP-0 and CP-1 run live and anchor in the same run; the brief is
  CP-DR's first owner step, with a source scope excluding research sources; same-evidence replacement is an
  O3 rerun with `repaired={CP-DR, CP-1C, CP-2}`; new evidence means a fresh live run.
- **H3** (:171). With `required ["CP-0","CP-1"]` the registry order is `CP-0, CP-1, CP-1A, CP-3D, CP-1C,
  CP-DR, …`; the walk and receipt follow `registry.plan`. Fix: move the CP-DR row in methodology.json ahead of
  CP-1C; test that for every preset with CP-DR added, CP-DR is planned before CP-1C and CP-2.
- **M1** (:169, :179; Q4). CP-2's `credit_synthesis` has no `sources=True` (ow:369-371); rows carry only
  `cp1a_refs` (cp2_synthesis.py:96-144); a source session needs `step_chain` pack sources (host.py:842-846).
  Fix: CP-2 receives the dossier through the binding plus its `read_inputs` view (owners/cp2.py:14-21) or
  O6's untrusted-evidence block, and never cites it; `test_consumers_cite_dossier_and_evidence` only for CP-1C.
- **M2** (:100, :120, :197). methodology.json's hash is pinned in 44 files covering 14 frozen oracles
  (cases/PINS.json:88, cases/*/manifest.json, leases); no re-pin task; tests/test_host_h1.py:557-561 starts
  CP-DR over CP-0 only. Fix: a re-pin amendment through the oracle process in the same commit as each
  methodology.json change (precedent: the CP-6 freeze re-pin); list test_host_h1.
- **M3** (:25 vs :138, :169, :152). `ev-*` sources reach the model through source-tool results unfenced.
  Fix: source tools wrap research sources in the untrusted-evidence fence; assert across prompt and tool
  results; a body the fence refuses becomes a rejected item.
- **M4** (:139, :151). `build_opener` adds File, FTP, HTTP and Data handlers; `HTTPSHandler` re-resolves the
  host (DNS rebinding); URL origin unstated; no timeout; no `read(cap+1)`. Fix: an `http.client.HTTPSConnection`
  subclass whose `connect()` dials the checked IP with `ssl.create_default_context()` and `server_hostname=host`;
  every redirect hop re-checked; URLs only from a user-supplied list or a ruled search endpoint; a timeout;
  read at most cap+1 bytes.
- **M5** (:120; Q2). O7a leaves the shared branch red until O7b. Fix: O7a additive only (contracts,
  readiness ladder, version constant, decision record); O7b-1 in one commit: methodology/cpdr.md rewrite,
  owner rewrite, old case and tests removed, row move, re-pins.
- Lows: L1 version id in the registry purpose text (:100), tested; L2 TDR.3 per-question rows plus a `total`
  row break one-fact-per-column (contracts.py:284-286); L3 the banned list goes beyond OD11 (:141); L4 the
  decision record amends only 0007's standalone-mode clause (0007 is cited at contracts.py:157,
  cp2_synthesis.py:17, cp4_legal.py:17); do not repoint execution.py:241; L5 `lineage: Literal["LOCAL"]`, test
  that `FULL_CP_OS` is refused (OD10); L6 relabel TDR.1-3 in bindings/cpdr.py when O7b re-keys them; L7 the
  controller writes the oracle brief, not the O7a implementer (:107); L8 refuse user sources named `ev-*`,
  `cp-dr-dossier` or `peers`; map `focus_module` to receivers (primary-full.json:204 uses `CP-DR`); the web
  gate's ruling needs a `configs:` line (R2).
- Answers: Q1 agree as an amendment record (L4); Q2 per M5; Q3 yes but use one run (H2); Q4 per M1; Q5 brief
  as CP-DR's first owner step; Q6 CP-1C reads TDR.6 from the bound CP-DR head and cites `ev-*`; Q7 agree
  (user manifest rows validated); Q8 honest per cp1c-owner/manifest.json:28-30 ("invented test data",
  `case_kind="synthetic"`, `.example` locators, no real publishers).

## Controller rulings (2026-10-31)

- All findings accepted as proposed (H2's one-run route; Q6's bound-head route), with:
- **H3/M2 scope:** the CP-DR row move, the TDR.4-6 tables and the re-pins of methodology.json's hash are
  within B1 ("methodology.json" for O7). The re-pin is mechanical and runs through the oracle process
  (separate preparer, independent `mx-precise` review, never the builder), with `cases/pins.py --check`.
- **M4 URLs:** web retrieval fetches only URLs from the user-supplied research manifest; no search endpoint
  is built (one needs a user ruling). Cost: no discovery of sources the user did not list.
- **L3:** the banned list is the existing list minus the topic bans ("covenant", "recovery", "refinanc"),
  nothing added (OD11).
- **L7:** the controller dispatches the oracle-brief writer (not the O7a implementer).
- **L8:** `focus_module` maps `CP-1C` → CP-1C, `CP-2` → CP-2, `CP-DR` or blank → both. The web gate needs a
  ruling with `lifts: live-provider-pause`, `by: user`, `date:` and `configs:` naming `web-retrieval`.
- Rev 2 (planner, 220 lines) applied all findings. New Q9 → ruling B12 (brief locks before analysis;
  scope excludes `ev-*`); Q10 → ruling B13 (walk continues, `cp_dr_state` recorded).

## Re-review of rev 2 (mx-autonomous), 2026-10-31: fix (2 new Medium)

- H1-H3, M1-M5 fixed; probe `scratchpad/o7probe/plan_order_rev2.py` exit 0 (CP-DR after CP-1, before
  CP-1C and CP-2, six presets). B12 matches :124, :217; B13 matches :167, :170 except N2.
- **N1** (:15, :168). "CP-0 replayed (valid, pack unchanged)" is false: the rerun's pack hash includes the
  new `run_id` (contracts.py:82-95); CP-0's `pack_sha256` is model-written, not prefilled
  (registry.py:286-291); CP-0's validator refuses a review not binding the current pack hash
  (readiness.py:338-339). `test_replay_accepts_unchanged_pack` cannot pass.
- **N2** (:167). A refused CP-DR leaves CP-5's fan-in (registry.py:26) unbound; execution.py:238-240 raises,
  so CP-5 and CP-6 refuse and no report renders.
- Low (:123): a blocked anchor raises `current_inputs`' generic error before `check_anchors`; order the
  anchor check first.

### Controller rulings
- **N2:** state and test the outcome (CP-5 and CP-6 refuse for a missing producer, no report; same as any
  refused module, O3's open item); CP-DR stays in CP-5's fan-in (a settled dossier's claims are reviewed).
  B13 amended.
- **Low:** accepted.
- **N1:** cross-plan (O3 Task 4 replays every module after CP-0 under a new `run_id`); sent for
  investigation before ruling; O7's replacement text waits on it.
- **N1 investigation** (mx-autonomous, probe `scratchpad/o7probe/scripts/replay_identity_fields.py`, exit 1
  at HEAD): CP-0 `pack_sha256` and CP-1 `financials.run_id` are model-written, unprefilled, run-bound;
  every module but CP-OS descends from CP-0. Options: reuse the earlier `run_id` (breaks run identity,
  `supersedes`), or rewrite an allowlist in `replay.py` (recommended).
- **N1 ruling:** allowlist rewrite in O3 Task 4 (`REBOUND_FIELDS`), only when old values equal the earlier
  run's and the pack differs only by `run_id` (else `ReplayPackChanged` before any write); `rebound`
  recorded; a guard test from the probe. O3 plan Task 4 and O7 :15, :168, RED test amended. Cost if
  wrong: a replay is not byte-identical to the earlier submission (the record shows the two paths).
- Re-review of N1/N2/Low: N1, N2, Low fixed; new Medium: pack equality checked only ids/media/sha256/Run
  fields, missing `Source.status`, `spans`, `extraction_status`, `extractor`, `limitation`, `name`
  (contracts.py:115-125). Ruled and applied: whole `PreparedPack` JSON compared with `run.run_id` (and
  hashes derived from it) masked; RED case with only `spans` / `extraction_status` changed.
- Final: approve (O3 :151 whole-pack comparison, :159 RED). O7 plan approved.
