# Release I2 report (mx-feature)

I2 is done and committed. Tip SHA is 192772c on `claude/s2-release`, tree clean. The gates exit 0 except `ruff check`, which shows only known findings. One deviation: I set the `gaps` timing bound to 0.8, not 1.0 (step 5).

**Merges** (each --no-ff): f1 a50efb2 clean (4010850), f2 a8e93cf clean (d8be001), qc1 ff1dbce with conflicts (2778c2a).

**qc1 conflicts and how I resolved them**
- **Pin-only hunks:** `cases/cp3c-owner/builder/build.py`, `cases/cp3c-owner/manifest.json`, `cases/cp4c-owner/builder/build.py`, `cases/cp4c-owner/manifest.json`, `tests/cp2d_runs.py`, `tests/cp3c_runs.py`. I took the fix-batch side; the chain then re-pinned them.
- **`docs/CP4-OWNER-LEASE.md`:** kept both amendment lines.
- **`cases/PINS.json`:** took ours, then regenerated it.
- **`cases/legal/render-expected.json`:** auto-merged with Q-C1's values intact. `CP-MODEL` is `unrun`, the `maturity-wall` pin and the `responsibility_context_only` text are present.

**Chain (commit 10ec523)**
- The F tooling would not converge as shipped, for two reasons:
  - `iterate.sh` only re-pins files that differ from HEAD, so the Q-C1 `cp2d-owner/expected.json` pin was never refreshed.
  - It does not re-pin builder-file pins.
- I used a variant of `iterate.sh` that re-pins every owner `manifest`/`submissions`/`expected` json, the three `cases/legal` jsons and every `builder/build.py`. It converged in 3 iterations.
- Q-C1 changed `src/deploy_vii/report_view.py` and `src/deploy_vii/contracts.py`, and the cpos builder pins both. I re-pinned them with the same tool. The brief did not list this. Judge whether it is acceptable.
- Two fresh-copy rebuilds are byte-identical to each other and to the tree. I repeated this on the final tree after all text edits, with the same result.
- `pins.py --check` exits 0 on 75 paths.
- **Shas the chain moved** (first 8 hex characters, relative to d8be001):
  - cp2d builder 0e3bdde3 → 0dd71e00
  - cp3c builder 6b6b9c2f → 6353168e
  - cp3c manifest 551c3125 → 2f65c085
  - cp4 builder 94010ed0 → 62c55210
  - cp4c builder d0908522 → e7628d4d
  - cp4c manifest c9ea23d4 → 62102d7d
  - cpos builder a21cd26c → 37534571
  - cpos manifest 560af9d9 → 1988c98a
  - `tests/cp2d_runs.py` and `tests/cp3c_runs.py` re-pinned to these.
- **Oracle values moved only through Q-C1:**
  - `cp2d expected.json`: ed36f120 → c60797a2.
  - `cp4 expected.json`: 2b98b81b → 1dff2422.
  - `cases/legal/render-expected.json` moved with the Q-C1 values.
  - No other `expected.json` moved.

**Lease headers (81a8ed5):** one "Amended by Modules 2026-10-29 (Stage 2 close release I2 chain)" line each for CP2D, CP3C, CP4, CP4C and CPOS, with the old and new shas.

**Cites (35d8c97)**
- `refresh_view_cites.py` rewrote the cp1d, cp2d and cpl10 view ranges in `docs/TOOL-CONTRACT.md`.
- I corrected the `cp2d_reader` cite in `docs/CP2D-OWNER-LEASE.md` to `cp2d.py:2774-2797`. The old 2761-2784 was already off before this release.
- The cp2a cites did not move.
- `c1_cites_updated.py` exits 0 at HEAD once I updated its expected ranges in the scratch copy.
- `methods/cp1d.md:78` now reads `deploy_workflow.owners.blank.one_per_page`.
- I did not touch the cites in `docs/rulings/`.

**Timing (192772c):** `attach` is 0.4 and `gaps` is 0.8.

| Case | Bound | Tip | Old code | Old-code ratio |
|---|---|---|---|---|
| `gaps` | 0.8 | 0.04s | 4.25s | 5.3x |
| `attach` | 0.4 | 0.03s | 2.05s | 5.1x |

`gaps` at 1.0 gave only 4.3x, so I used 0.8, which the tip passes by 18x.

**Gate exit codes**
- `pins.py --check`: 0.
- Fast set: exit 0, 9448 passed, 4 skipped, 1 xfailed. The xfail is the Q-C1 tripwire `test_fp04_maturity_wall_shows_model_content_first_with_t2e4_as_a_tab`.
- Both S1a tests, run in the background: 3 passed in 659s. No background process is left.
- `ruff format --check` on the 63 changed `src`/`tests` `.py` files: 0.
- `ruff check` on the same files: exit 1, only known findings (`prose.py` ISC004 :114 and :127, `report_view.py:293` SIM102, `test_legal_render.py:220` C408).
- `mypy --strict` on 19 `src` files: 0.
- `noqa` count is 13 and `type: ignore` count is 5.

**Open for the owner:** Q-C1 changed `report_view.py` and `contracts.py`, which are reused files, with no D12 record in `docs/reuse/manifest.json`. I did not check or add one.

Not verified: the slow render suites, `test_source_tools.py` and the genuine `test_owner_<cp>.py` runs; the D12 chain after the Q-C1 changes to `report_view.py` and `contracts.py`; `ruff` on the `cases/**/builder` files, which are unformatted and predate this release; the timing margins under load; the full suite and the bandit, complexipy, jscpd and mutation gates. No test applies to the lease headers and cite text, which are docs.

agent=mx-feature fix-rounds=0 gates-first-pass=n
