## Stage 5.3 whole-branch review, lens A (calculation invariants): `4822066..9f71bfa`

**Spec verdict: PASS.** All three Review Focus items hold in everything I sampled.
**Quality verdict: PASS.** I found no stub, no fake value and no catch-all that hides a failure.

### Findings
- **High:** none.
- **Medium:** none.
- **Low:** none.
- **Info (nothing to fix):**
  1. `src/deploy_workflow/owners/cp2d.py:615-616`: CP-2D's runway division runs in the 60-digit context `localcontext(_CONTEXT)` (entered at :678), then rounds to 1 dp half-up in a wider context. In theory the 60-digit step could round once before the 1 dp step. Reaching it needs a quotient with 50+ nines after a "…x4" digit. That can't happen with 2-dp source amounts, so I'm not raising it.
  2. `src/deploy_workflow/owners/cpdr.py:370`: `_share` divides in whatever decimal context the caller has (28 digits by default), then rounds to 4 dp half-up. The inputs are whole numbers and the denominator has at most 4 digits, so the result is exact enough. The probe confirms it (below).

### Process results
1. **Zero vs missing.** I read every sum and every zero-default hit in context, and none turns a missing value into 0:
   - `cp2d.py:356-361` and `cp3c.py:486-489` return the first gap before summing.
   - `cp1d.py:1138-1139` sums the claimed amounts only when every one is stated. The `Decimal(0)` at :758 is CP-1D ruling 1D2 (a recurring item counts as zero), not a default for a missing amount.
   - `cp4c.py:326-331` returns the first missing claim before summing; `cp4c.py:2135-2139` does the same for distributions.
   - `cp4c.py:276` uses `math.floor` on a `Fraction`, which is exact.
   - `cpdr.py:305` uses `counted.get(gap_id, 0)`, which is a count of questions, so 0 is the right answer for an absent key.
   - In the chart series, `liquidity_series.py:91-97` and `restructuring_series.py:103-109` map an unsettled fact to a gap and raise when there is no limitation text.
2. **Decimal exactness.** No `float(`, no `round(` and no float maths anywhere in scope. Every context is explicit and set per module, and the exact contexts trap rounding instead of hiding it: `cp1d.py:527-528`, `cp2a.py:82`, `cp8.py:125` and `cpl10.py:77-78`.
   - **Rounding spot-check on 5 modules** (CP-2D, CP-3C, CP-DR, CP-3D, CP-L10), comparing each module's own rounding code with its lease and oracle text on half-way values: all agree. This includes the oracle case `fixture_burn`, where the runway is `"20.0"`.
   - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/A/probe_rounding.py`, **exit 0**.
   - Stage 1 tests: `tests/test_method_*.py` on a copy of 9f71bfa gave 6044 passed, 1 skipped (`test_method_cp1d.py:1528`, which needs a store and is deferred to Stage 2/4), in 30.8 s.
3. **Stage 1 inputs vs settled heads** (three modules checked):
   - **CP-2D** (`cp2d.py:2108-2133`, `_operand_of` :1972-1981, `_inputs_from` :2179-2187): every field of `Operands` is built from `OPERAND_NAMES`, which is all the dataclass fields (:1914). `Operands` has no defaults, so a missing field would fail at construction. Each binding must match exactly one fact or it raises. A fact that isn't known keeps its status and CP-1's limitation text, with no amount.
   - **CP-2A** (`cp2a.py:1547-1557`, `offered_bases` :1517-1544): the inputs are the head's T4.10 facts for the periods it offers. A period offered without a complete set of USD-millions facts is skipped, by design: the analyst then cannot choose it and the module fails closed.
   - **CP-2E / CP-3D** (`cp2e.py:445-519`, `cp3d.py:501-523`): their inputs come from the validated submission, not a head. Every field is set explicitly and `None` means missing.
4. **Catch-alls.** I read all 56 `except` clauses. None is broad: each catches a named exception (`ValidationError`, `ValueError`, `SourceIssue`, `PeerTableError`, `Inexact`, `UnicodeDecodeError`, `UpstreamError`), and each either re-raises, records the error as a refusal or staleness issue, or returns an empty result that the docstring says is fail-closed. Examples: `cp4.py:146-149` and `cp2h.py:2143-2150`.

### Sweeps and hit counts
Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/A/sweeps.sh`, exit 0. It searches `owners/` and the three series modules at 9f71bfa.

| Pattern | Hits | Notes |
|---|---|---|
| `float(` | 0 | |
| `math.` | 1 | exact floor of a `Fraction` |
| `round(` | 0 | |
| `suppress(` | 0 | |
| `or 0` | 0 | |
| `Decimal(0)` | 21 | all reviewed |
| `except Exception` / `BaseException` / bare `except:` | 0 / 0 / 0 | |
| `except` (all) | 56 | all narrow |
| `TODO` / `NotImplemented` | 0 / 0 | |
| `sum(` | 20 | all reviewed |
| `.get(…, 0)` | 1 | `cpdr.py:305`; `git grep -E` showed 0 because it ignored `\b`, and plain grep found it |

The copied source tree was deleted afterwards. Only the two probe files remain under `s53/A/`.

Not verified: I did not read the earlier stage reviews in full. I have no findings, so nothing re-reports them, but I can't rule out a regression of an earlier finding in code I didn't sample. Not checked by me:
- each module's rounding against its oracle beyond the 5 modules probed (the other modules rely on their Stage 1 tests passing);
- the Stage 2 adapters of the modules other than CP-2D, CP-2A, CP-2E and CP-3D;
- the full workflow, store, promotion and render suites (the controller is running those);
- the whole of the ~31k-line diff (searched and sampled, not read line by line).
