# Stage 1 end-of-stage review (Opus, read-only)

The plan, `docs/superpowers/plans/2026-10-28-verified-module-builds.md` ("Stage review" and "Review Focus"), asks for one Opus review of Stage 1 before Stage 2 starts. Three reviewers each take one lens across all modules. Their findings go to fix rounds. The reviewers do not edit or commit.

## Target
The lane worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`, at the commit named in your dispatch. Read it, and run probes from a full temporary copy (`git archive <commit> | tar -x -C <dir>`), with `PYTHONDONTWRITEBYTECODE=1`.

There are 16 Stage 1 modules, each with `src/deploy_workflow/owners/<cp>.py`, `tests/test_method_<cp>.py`, `docs/<CP>-OWNER-LEASE.md` and `cases/<cp>-owner/`: CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3, CP-2G, CP-8, CP-5, CP-4C, CP-2H and CP-3C. `cp1a.py` and `cp2.py` are not Stage 1 modules of this lane; leave them out.

## Already covered (do not re-raise)
- Layer reviews `work/build/stage1/review-{A,B,C}.md`, which cover CP-2E, CP-2D, CP-2A, CP-1C, CP-1D, CP-L10, CP-3D, CP-DR, CP-4 and CP-3.
- The per-module reviews in `work/build/stage1/<cp>/`.
- Open LEAD questions: `work/build/stage1/*/questions.md` and `stage1/quote-sign-questions.md`.
- The riding-Lows batch in flight: `work/build/stage1/lows-brief.md`.
- Stage 2 notes in `work/build/RESUME.md` ("Stage 2 notes collected").
A finding already in one of these is not new. Cite it if it bears on yours.

## Lenses (one per reviewer)
- **R1, Stage 2 readiness (Review Focus 3).** For each module, check that the Stage 1 input object is exactly what a Stage 2 adapter can fill from a settled head.
  - List every input field with its lease source, giving the table id and predicate.
  - Check each field against `cases/<cp>-owner/manifest.json` `fact_bindings`, and against the producing module's actual output (for example, CP-1D's T1D.3 for CP-2G).
  - Report each field with no binding, any unit, currency or period mismatch, any status the producer can emit that the consumer cannot take (for example `not_applicable`, `conflicting`, `composer_only`), and any field a Stage 1 test fills by hand that no producer emits.
- **R2, arithmetic (Review Focus 1–2).** Across all modules:
  - a missing operand never becomes 0;
  - no `float` appears anywhere in a calculation;
  - quantisation and rounding follow each lease (mode, places, and whether stored quantised);
  - division by zero and a zero denominator are handled as each lease says;
  - sign conventions match.
  Sweep by grep and probe, then trace any doubtful site against the lease text.
- **R3, cross-module consistency and Stage 2 seams.**
  - Shared defect classes: the four quote readers (CP-1D, CP-3D, CP-8, CP-2E) each built round 11 B1/B3 separately. Compare their behaviour with one probe over the library cases plus `<S>/defect-classes/` and the class-review probes. Report every behavioural divergence that is not a known LEAD question, and say whether the shared parts belong in one helper at Stage 2. jscpd is a project gate (threshold 3), so measure the duplication.
  - Issue-frame spellings across modules (`empty`, `empty text`, `text is empty`): is each module internally consistent?
  - Protocol §5: cores read model payload only through `json_object`/`payload_document`. List every other read site, beyond cp2g:830, cp4c:938 and cpl10:926.
  - Any `assert` left in product code paths, and any catch-all.

## Rules
- Read-only. No edits, no commits.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Save each probe under `<S>/stage1-end-<R1|R2|R3>/` and name it in its finding.
- Grade findings High, Medium, Low or Info. Give each a file:line, a concrete input and its wrong output, and the lease or ruling text it breaks.
  - Pre-existing defects go to the owner; mark them so.
  - Unruled cases go to LEAD; mark them so.
- Run the fast lane set once at the target and report its exit code:
  `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_*.py tests/test_cp1b_registration.py tests/test_owner_g1x.py tests/test_host_h1.py tests/test_schema_normalise_escapes.py tests/test_defect_classes_selfcheck.py`.

## Report (as text, at most about 2k tokens)
- the verdict: PASS, or FINDINGS;
- the findings, ordered by severity;
- the probe exit codes;
- `Not verified:`.
