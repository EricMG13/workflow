# Q6 (host.py for H1): copied verbatim from LEAD's untracked `work/lead/cp3-cp6-owner-preparation/review-precise-r3-1.md` (worktree review-wip-worktrees-0145fe), 2026-10-28

## Q6: host.py for H1 (against L2's host.py)
(a) `_SOURCE_STEPS` (:44-48) add `"CP-3": ("relative_value",)` after `"CP-1A": ("business_context",)`.
(b) Replace `if producer.module_id != "CP-0": return producer.inputs == expected` (:491-492):
```python
    if producer.module_id != "CP-0":
        return _submission_producer_inputs(store, snapshot, producer, expected)

def _submission_producer_inputs(store, snapshot, producer, expected) -> bool:
    selected = [a for a in snapshot.attempts
                if a.module_id == producer.module_id and a.result_sha256 == producer.content_hash()]
    if len(selected) != 1:
        return False
    attempt = selected[0]
    if (attempt.status != "finished" or attempt.interruption is not None
            or attempt.number != producer.attempt or attempt.inputs != expected
            or attempt.payload_sha256 is None or producer.inputs[: len(expected)] != expected):
        return False
    tail = producer.inputs[len(expected):]
    if producer.status in ("accepted", "restricted"):
        if attempt.issues or len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
            return False
        step = attempt.steps[0]
        if len(tail) != 1 or not tail[0].input_id.endswith("-submission"):
            return False
        submission = STEPS[step.step_id].schema.model_validate_json(store.payload(step.payload_sha256))
        if tail[0].sha256 != submission.content_hash():
            return False
    elif tail or not attempt.issues:   # a rejected/blocked head carries attempt.inputs only (execution.py:426-437)
        return False
    finished, result = settle(snapshot, attempt, store.payload(attempt.payload_sha256),
                              lambda _: attempt.issues, pack=store.pack(snapshot), load=store.head_module)
    return finished == attempt and result == producer
```
`STEPS` from `deploy_vii.live.submission`. Failed-head branch keeps today's acceptance of blocked producers (no tail); an issue-free-only rule would break CP-3 under a blocked CP-1A (restricted edge). Measured on real heads: old rule `False` for CP-1A and CP-2 (tails `business-context-submission`, `credit-synthesis-submission`); new settled branch passes (unique finished attempt, issue-free, prefix equal, tail digest = retained submission `content_hash()`, settle replay returns attempt and head). Replay ~0.74 s per producer; `_execution_state` runs on `from_execution` and twice per `invoke`/`bind_submission` (`_assert_current`, :741-751): memoise per (snapshot hash, producer hash) as `_verify_cp1_attempt_memoised` (:453). Do not add CP-4's empty-scope refusal (:667): the gap case needs a zero-source session to bind its submission; G1 opens a `SourceSession` for every `sources=True` step (`owner_workflow.py:436`), so H1 is needed in both cases.

Not verified: no pytest; no end-to-end owner run, R3 CP-1 promotion, integrated G1/S1a/H1 or receipt verifier; CP-1 head from the 3-source S1 pack (R3 narrative/quality/limitations unchecked); R3 CP-2 head not re-composed; CP-0 built by `build_readiness`, not settled; H1 failed-producer branch and memo not executed; L2's tests under the new rule not run; FP01/rail not rendered; tool-use refusals, stale-snapshot refusal, attempt-1 re-begin not exercised; `rules="journaled"`, `upstream_grant` not checked against integrated S1a; CP-6 half out of scope.
