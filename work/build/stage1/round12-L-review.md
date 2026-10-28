**Verdict: APPROVE.** I found no High or Medium findings.

**Checks**
1. **`is_blank` and B10.** `is_blank` is `all(ch.isspace() or category(ch) == "Cf")`, so `""` is blank. It lives in `src/deploy_workflow/owners/blank.py`, not deploy_vii.
   - Blank cases checked: U+200B, U+FEFF, U+00AD, U+2060, ` ​\n`.
   - Not-blank cases checked: `a​` and others.
   - The hypothesis properties are sound.
2. **Rule W.** All five cases in the ruling's shared-test list are present, for both figures:
   - spaced minus, `w-minus-space`;
   - interior `-\n`, `w-minus-wrap`;
   - U+2212 then NBSP, `w-minus-nbsp`;
   - `(\n25)`, `w-parens-wrap`;
   - edge figure after a page `- `, `w-edge-minus-space`.
   - Each refused case has an accepted twin, and my check found 15 W cases with the twin accepted.
   - Controls: `w-break`, `w-letter-wrap`, `w-2024-2025-wrap`, and the existing `sign-95-96`.
   - The diff removes no case. It only touches docstrings, and the `whitespace_only` comment and docstring. No pre-round-12 case changed its expected outcome.
3. **BLANK_VALUES.** The four ruled values are added as blank-5 to blank-8 with ruling `R12_B10`. The old ids are unchanged. `whitespace_only` is `value != ""`, which is correct for all nine values. I confirmed `blank_failure` demands the frame for the non-empty ones and takes any refusal for `""`. A strip-based reader fails exactly the four `Cf` cases (selfcheck test).
4. **Stub and catch-all.** There is no stub, fake value or catch-all. The selfcheck imports no owner. It imports `deploy_vii.quotes`, as it did before this round, and that is not an owner. Its `_blank` is written independently from the ruling.

**Findings**
- **Low:** The library has no W cases in `label_cases` or `LABEL_TEMPLATES`. The ruling names the CP-8 `_labelled` and CP-2E labelled-reader change, and Part M's CP-8 and CP-2E rounds would get no shared-class coverage of it. The brief and the ruling's shared-test list name only the five cases above, so this is within scope. I recommend adding one or two labelled W cases (such as `bid - 1.25` and `bid -\n1.25`) at the start of the CP-8 and CP-2E rounds, or as a library follow-up.
- **Info:** Probe A of the ruling lists more variants than the library carries: `(-\n`, U+2212 then a line break, U+2212 then a thin space, CRLF, and `-\n` at the quote edge. Normalisation reduces them to one space, so the five ruled cases cover the class. They are not required.
- **Info:** `w-2024-2025-wrap` is a new id that CP-1D (quote prints two figures) and CP-2E (2025 above the share bound) must add to their pinned not-applicable sets. The report already says this.

**Probes** (saved in `<S>/round12-lib-review/`)
- `mutants.py` (copied from `<S>/round12-lib/`, which works from a full temp copy with PYTHONDONTWRITEBYTECODE=1): **exit 0**. The baseline copy passes with 226 tests, and all 10 mutants are killed.
- `ref_reader_w.py w`: **exit 0**, 89 cases, 0 mismatches.
- `ref_reader_w.py r10`: **exit 1**, as intended. 10 mismatches, which are exactly the new W refusals.
- `p_lib_vs_lead_ref.py`, run with `<S>/round12-lib/p_sign_breaks.py` as the argument: **exit 0**, no disagreements over 76 figure cases, 10 W refusals.
- My own `p_review_checks.py`: **exit 0**. It checks the `is_blank` edge cases, the `whitespace_only` split, the W twins, and that the `R12_B10` values are the four ruled ones.

**Gates** (run in the worktree with the venv binaries)
- pytest on the selfcheck and `test_owner_blank.py`: exit 0, 226 passed.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict` on the 4 files: exit 0.

I did not edit or commit anything in the worktree. `git status` there was clean.

Not verified: W against real module readers (only reference readers were used, and Part M covers the modules); the expected-red counts in `tests/test_method_*.py` (609 failures; I took the report's figure); the full test suite; GitNexus `detect_changes`; the U+2212 and thin-space variants beyond the five cases; labelled-reader W behaviour.
