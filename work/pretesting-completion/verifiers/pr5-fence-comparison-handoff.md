# PR5 prompt-fence same-base comparison

## Scope and provenance

Compared the exact PR verification base `be9fc49a4a6340ade8165f8ae85b1d8315059619` in the isolated `pt-pr5-prompt-fence-compare` worktree. Its `tests/prompts/test_fence.py` started at blob `459de9cce6bd9e1dec9afabbc4b5e979f9a41835`, with context construction outside the `pytest.raises(FenceError)` block.

Applied only the already reviewed one-hunk change from `3883b5d2db21993fc4ffcb66f34f977e8abba330` (controller copy `b050d03032ca8d0e66b9b7b3b17c8a691dea8ab1`). The resulting file SHA-256 is `45074abf2d8521cb1beb6254b37ff2e986700f4a5b1aa8c14ebeb3137de0c1fc`. The change puts both context construction and `run_context_block` inside `pytest.raises((ContextRefused, FenceError))`; all eight marker cases still require an actual refusal. No product/parser code, skip, xfail, source pins, or other files changed.

The earlier diagnosis at `work/pretesting-completion/reviews/prompt-fence-diagnosis.md` found all eight marker payloads refused by `load_context` with `ContextRefused` before the previous assertion began. The independent test-only review at `work/pretesting-completion/reviews/prompt-fence-test-alignment.md` recorded Spec/Quality PASS, author confidence review, Ruff/diff clean, and 26 focused tests passing on the reviewed prior base. The original PR5 fast-shard report had eight failures among 1,912 passes on shard 3; those eight names match the diagnosed stale assertion. The release source pin remains the historical pre-correction value `a1a925ae7682e1cb1d2a07498fc219bb75698690a9bfa00ad771adfc302f473d`; this comparison does not rewrite that release record.

## Same-base result

On the exact PR base with only this reviewed test hunk applied:

```text
PYTHONPATH=src:tests:tests/prompts:root /Users/ericguei/Documents/Deploy\ Workflow/.venv/bin/python -B -m pytest -o pythonpath= -p no:cacheprovider -q tests/prompts/test_fence.py::test_a_research_question_with_a_marker_is_refused
```

Exit 0; 8 passed in 0.09 seconds (1.14 seconds wall time). Ruff check and format check passed for `tests/prompts/test_fence.py`; `git diff --check` passed. The original direct-refusal controls were not rerun; their unchanged 26-test prior review is reused. This establishes the known eight prompt-fence CI failures as stale test expectations on this PR base; it does not establish whole-shard, full-CI, or Product parser qualification. Type-check and build were not applicable to this test-only expectation edit and were not run.

## Confidence review

Least confident about (ranked):

1. The source hunk may not apply to the exact PR base or may have drifted from the reviewed correction. Investigated by verifying starting HEAD, base test blob, applying only commit `3883b5d2`, and checking the resulting SHA-256 against the reviewed expected hash. Verdict: fine; exact expected bytes.
2. The assertion could be weakened so a marker is accepted. The `pytest.raises` scope encloses both context construction and `run_context_block`; normal completion still fails. The exact eight parameter nodes passed on the PR base, and no skip/xfail was added. Verdict: fine for these eight nodes.
3. The PR failures may indicate a Product/parser regression rather than a stale test boundary. The prior diagnosis shows all eight fail before fence evaluation because `load_context` refuses them; this change adjusts only the test to accept either refusal stage and changes no parser behavior. Verdict: diagnosed stale expectation, scoped to these nodes.
4. Historical pin or broader test implications could be misstated. Verified that the release pin remains unchanged and the integration contains only this test hunk plus the two leased records. Verdict: no pin rewrite; full CI remains unverified.

Fixed: no Product behavior; reused the reviewed test-only correction on the exact PR base.
Verified fine: source SHA matches review, focused eight-node test passes, Ruff and diff checks clean.
By-design: both refusal stages satisfy the existing fail-closed test intent.
Still open: full PR CI result, other shard 4 failures, whole-shard behavior, and Product qualification. The current PR does not include this test correction yet.
