## CP-5 Stage 1 owner core: adversarial review 1 (claude/cp5-stage1 @ 4e2d687)

**Verdict: CHANGES REQUIRED.** The fix is tests only; `cp5.py` needs no change.

I found no defect in `src/deploy_workflow/owners/cp5.py`. It follows lease construction steps 1–6 exactly. My probes found no leak, the body is deterministic, compute and candidate behave correctly, and nothing breaks the standing rules. The problem is the suite: it does not protect the view's no-quote guarantee. Two mutants that put citation quote text into the body pass all 45 tests. The commit touches only the two new files (`git diff --stat c019fac 4e2d687`), and the target tree is clean.

### Findings

**Medium F1: two quote-leaking mutants survive the suite** (`tests/test_method_cp5.py:989-1029`; target code `cp5.py:103-109`)
- The suite builds only one view-detail scenario: one failing citation, on one claim, of an evaluated head (`_failing_view`, line 995).
- **Scenario A02:** a regression cuts only the first per-claim mark: `[mark.split(": ",1)[0] if i == 0 else mark ...]`.
  - The suite gives 45 passed.
  - On a claim with several failing citations, the second mark reaches the body whole, for example `claim_citation: Quote/locator mismatch: ... "Probe failin…`.
- **Scenario A03:** a regression strips quotes only where `module["evaluated"]` is true.
  - The suite gives 45 passed.
  - A blocked head's citation quotes then reach the body verbatim (CP-1A: `'Customers are industrial distributors that serve maintenance, repair and operati…'`).
- Both scenarios fall inside the lease:
  - The "Blocked" rule binds and lists a blocked optional head, and `context_block` lists blocked heads.
  - CP-1A r02, r04 and r05 have two or more citations, and genuine CP-1 claims carry every evidence record's citations (`narrative_projection.py:126,170`).
- Fix: add tests that kill both. `test_adv_cp5.py` (below) has them; it passes on the baseline and kills A02 and A03.
- Probes:
  - `leak_mutant_demo.py` rc=0: on both mutants the suite passes and the leak is observed.
  - `adv_mutate_run.py` rc=0.

**Low F2: construction-fidelity mutants survive** (`tests/test_method_cp5.py:989-1019`, `295-335`)
- These suite survivors change the lease construction but leak nothing:
  - A01: drops the ` on <ref>` part of a mark.
  - A09, the implementer's M14: cuts at `:`.
  - A04: reverses citation order.
  - A05: top level uses `modules[0] subject` in place of `where`; this raises IndexError on an empty evaluated set.
  - A06: refuses only scope issues that start with `Stale`.
  - A11: de-duplicates the top-level findings.
- The `kind on <ref>` mark of lease step 4 is never built.
- M14's justification ("none in the bound heads" has a `:`) holds only for the stand-in.
  - Genuine CP-1 fact ids are `interface-fact:<sha256>` (`financial_periods.py:129-132`), and the CP-1 claim chips name exactly those facts (`narrative_projection.py:89-96,124`). So on a real CP-1 head M14 is not equivalent.
  - The actual code keeps such an id whole: `marks_probe.py` M2 builds `figure_identity on interface-fact:abab…`.
- The stand-in CP-1 has no `:` ids, no `[chip]` references and one citation per claim, which is why these behaviours are invisible.
- Probes: `adv_mutate_run.py` rc=0, `marks_probe.py` rc=0.

**Info**
- **I1:** `CP5Result` does not enforce "issues or a report, never both". `CP5Result(issues=("x",), report=r)` still produces a candidate, and `candidate(positive_result, gap_inputs)` binds the wrong inputs silently (`core_probe.py` C2/C3, rc=0). `compute` never builds such a result, CP-3 has the same shape, and Stage 2's `_candidate(output, attempt)` does not use this function.
- **I2:** `view_body` rebuilds each citation from an allowlist (`CITATION_FIELDS`) instead of deleting `quote`. That is stricter than the lease wording, and `key_tree` would flag any drift.
- **I3: my reading of `WorkflowError` in the pure core.** It is acceptable.
  - Lease step 1 names `identity_mismatch` as the view's refusal, and `owners/cp2.py:19` does the same.
  - `WorkflowError` is a `ValueError` subclass, so pure callers still fail closed.
  - Cost: importing `deploy_workflow.workflow` loads `deploy_workflow.host`, `tools.source`, `deploy_vii.live.tools` and `deploy_vii.render`. These are imported, never called (`io_probe.py` rc=0).
  - During the calls the only file event is the engine registry reading `methodology.json`.
  - Any scope issue raises, not only stale ones (`marks_probe.py` M6).
- **Attack points that held** (`leak_probe.py` rc=0, `determinism_probe.py` rc=0, `core_probe.py` rc=0):
  - **Quote leaks:** the body does not depend on a failing claim quote at all. 48 crafted quotes (`": "` inside, `"`, newlines, unicode, a quote equal to a fact value) gave one identical body.
  - **Fact-citation quotes:** the same holds for failing fact-citation quotes on CP-1, CP-1A and CP-3, including CP-3's T3.3 quote fact.
  - **All literal quotes:** none of the 46 literal quotes in the three submission files appears outside the T3.3 exemption.
  - **Fixture quote choice:** the "first literal quote per locator" rule hides no shown-quote leak. 7 of 9 locators are ambiguous, but no fact shows a quote other than the one assigned.
  - **Digests:** identical under five `PYTHONHASHSEED` values, including a scope with two blocked heads and an identity finding.
  - **Candidate:** the in-memory candidate equals the JSON round-trip candidate. Scope issues take precedence over submission issues.
  - **Lone surrogates:** `Module` JSON rejects them.
- **owner_projection (point 2):** it matches lease step 2. A mutant that keeps only known facts (A10) is killed.

### Items for LEAD (pre-existing or unruled)
1. Controller rulings 1–3 are still open:
   - `WorkflowError` raised inside `view_body` (see I3 above for my reading).
   - The refused-candidate message is unpinned.
   - `python_checks` runs three times per view and three times per `compute`. Its cost on a promoted CP-1 is unmeasured.
2. The CP-3 fact count is confirmed at 42 (positive) and 31 (gap) including the `cp1_references` copies. The lease says 39 and 28.
3. The no-quote assertion is a substring test. The shortest literal quote is 30 characters, so it gives no false positive now. Genuine CP-1 quotes are still to be checked in Stage 4.

### Mutant table
| Source | Mutants | Suite result |
|---|---|---|
| Implementer `mutate_run.py` | M01–M13, M15–M21, O01 (oracle cell) | all killed |
| Implementer `mutate_run.py` | M14 (cut at `:`) | survives (expected) |
| Implementer `oracle_mutation_probe.py` | T5.3 cell, T5B.8 cell, key_tree, refusal issue | all fail a comparison test |
| Adversary | A07 (`sort_keys`), A10 (known facts only) | killed |
| Adversary | A01, A02 (leak), A03 (leak), A04, A05, A06, A09, A11 | survive the suite; all killed by `test_adv_cp5.py` |
| Adversary | A08 (no `allow_nan`) | survives; equivalent, the block holds no float |

### Gates (target root, venv tools)
| Gate | Exit code |
|---|---|
| pytest `tests/test_method_cp5.py` (45 passed) | 0 |
| `ruff check` (both files) | 0 |
| `ruff format --check` (both files) | 0 |
| `MYPYPATH=src mypy --strict` on `cp5.py` | 0 |

### Probes
All are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-adversary/` and take the target root as their argument.

| Probe | Exit code |
|---|---|
| `leak_probe.py` | 0 |
| `marks_probe.py` | 0 |
| `determinism_probe.py` | 0 |
| `core_probe.py` | 0 |
| `io_probe.py` | 0 |
| `adv_mutate_run.py` (log `adv_mutate_run.log`) | 0 |
| `leak_mutant_demo.py` | 0 |
| `test_adv_cp5.py` (7 passed in a baseline copy; shared helper `advfx.py`) | 0 |
| Implementer runs (logs `impl_mutate_run.log`, `impl_oracle_probe.log`) | 0 and 0 |

Not verified:
- The genuine CP-1 head (`interface-fact:` ids, chip-named evidence facts, multi-citation claims, its quotes and limitations, body size, `python_checks` cost).
- `view(historical, attempt)` and `review_scope` over a journal, including a `review_scope` that raises instead of recording an issue.
- The read_inputs digest, the verifier and the tamper, tool-use and blocked-case refusals.
- Whether genuine CP-1 claim prose ever repeats a citation quote: it is model-written, and the lease condition would then fail at run time.
- The TOOL-CONTRACT row (`c019fac`, out of scope).
