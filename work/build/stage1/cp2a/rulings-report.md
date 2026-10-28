# CP-2A rulings round report (controller-saved; replaces the stale branch copy of report.md on merge)

- **Commit:** fe44e52 on `worktree-agent-a34fec3e9469279cd`, on top of the lane-tip merge e292975.
- **Changes:** rulings A1–A8 plus M4, applied test-first. A4 and the A8 missing-operand check already held and are now pinned by tests.
- **Tests:** 86 passed, 1 skipped (v17, Stage 2), in 1.22 s.
- **Gates:** ruff check 0, ruff format --check 0, `MYPYPATH=src mypy --strict` on both files 0. Not green on the first run: one reformat and three UP031 findings.
- **Input fields:** as in report.md at 5626b90, with two changes:
  - interest is `I = -cash_interest` (A7);
  - the gate wording depends on `period_kind` (A6).
- **Engine/oracle disagreements:** none open; A5 settled v02.

## Rulings applied
- **A5.** A v01 or v02 issue ends validation. v02 is asserted live, and the strict xfail is gone. The reviewer's mutant now fails the suite.
- **A7.** There is no positive-interest refusal: +5 gives I = −5, so both coverage breaks are Not calculable.
- **A1.**
  - D ≤ 0 gives "Not reached", not_applicable, not ranked.
  - I ≤ 0 gives "Not calculable", missing.
- **A8.** Order of checks: missing operand, then the CP-1 gate, then the short-circuit, then s*.
- **A6.** Quarter bases keep their wording. FY and LTM bases read "CP-1 reports no value for this ratio for this period (...)", with no twelve-month line. `period_kind` raises on an unknown label.
- **A3.**
  - A limitation figure joins `cp1_references` after its row's rationale.
  - The prohibited check covers scenario names and threshold labels.
  - Limitations get the rationale prose checks.
- **A4.** The F-before-I wordings are pinned.
- **A2.** Property scopes as ruled.
- **M4.** `scenarios[i].name: empty text` / `thresholds[i].label: empty text`.

## Probes (scratchpad/cp2a/)
| Probe | Exit | Notes |
|---|---|---|
| `probe.py` | 0 | A1, A3 |
| `probe2.py` | 0 | A6, A1, A8 |
| `probe4.py` | 0 | A7 |
| `probe5.py` | 1 | Intended: `compute` called on limitation text that `validate` now refuses |
| `probe6.py` | 0 | M4, A7 |
| `probe7.py` | 0 | A3 |
| `mutant_v02.py` | 0 | The mutant now fails the suite |
| `fuzz6.py` | 0 | 92,160 inputs; no raise after validation |

## For LEAD
1. Confirm the M4 wording `<path>: empty text`.
2. **Stage 2:** `validate` raises when an offered period lacks exactly one T4.10 fact per metric. That is CP-1 head integrity; it needs a G1-X precheck or a check at begin.
3. **Stage 2:** cross-check `period_kind` against the view's `base_periods[*].kind`.
4. A resolved `{ref|unit}` in a limitation is shown raw, because `Claim.limitation` is plain text.
5. These still compose:
   - a newline in a name;
   - `|` in a label;
   - a scenario named "Base (no stress)";
   - two thresholds with the same label.
6. The CP-1 gate is applied per ratio, and its limitation line appears only where a cell shows the gate reason. Unchanged.

Not verified: real CP-1 head facts; FY base periods (no FY fixture, so the FY wording is exercised only through LTM); v17; any store, journal, view, probe, G1-X or rendering path; pydantic versions other than 2.14.1.

agent=general-purpose(opus) fix-rounds=2 gates-first-pass=n
