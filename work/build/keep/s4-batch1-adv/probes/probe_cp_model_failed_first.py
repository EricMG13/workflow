"""P5: the route only the publication-path `_expected_begin` closes. The first CP-MODEL attempt is
begun on forged inputs (CP-1 dropped) and its publication fails (files unwritable), interrupted
by a patched producer; the second publication's genuine `begin` then sees no previous attempt on
its input set and starts another attempt 0, which publishes. The final head is genuine, so the
final deterministic binding passes; only the replay of the first publication's begin refuses.
P6: the same run with that replay made lenient, to show it is the operative check."""
import importlib
from pathlib import Path
from typing import Any

import pytest

import deploy_vii.cp_model_workflow as cpm
import deploy_vii.execution as ex
from deploy_vii.execution import Attempt, Execution

import probe_cp_model as base
from test_owner_s1a import positive_promoted  # noqa: F401

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")


def _run(promoted: Any, root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    workflow = base._walked(promoted, root)
    real_begin, real_inputs, real_write = Execution.begin, ex.current_inputs, cpm._write
    n = [0]

    def begin(self: Execution, module_id: str) -> Attempt:
        attempt = real_begin(self, module_id)
        if module_id != "CP-MODEL" or n[0] > 0:
            return attempt
        n[0] += 1
        snapshot = self.read()
        forged = attempt.model_copy(update={"inputs": base._drop(attempt.inputs, snapshot)})
        self._write(
            snapshot.model_copy(
                update={
                    "parent": snapshot.content_hash(),
                    "attempts": tuple(forged if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts),
                }
            )
        )
        return forged

    def lenient_inputs(snapshot: Any, module_id: str) -> Any:
        pending = [a for a in snapshot.attempts if a.module_id == module_id and a.status == "pending"]
        if module_id == "CP-MODEL" and pending:
            return pending[-1].inputs
        return real_inputs(snapshot, module_id)

    w = [0]

    def failing_once(output: Path, files: dict[str, str]) -> None:
        w[0] += 1
        if w[0] == 1:
            raise OSError("disk full (probe)")
        real_write(output, files)

    monkeypatch.setattr(Execution, "begin", begin)
    monkeypatch.setattr(ex, "current_inputs", lenient_inputs)
    monkeypatch.setattr(cpm, "_write", failing_once)
    first = workflow.publish()
    second = workflow.publish()
    monkeypatch.setattr(ex, "current_inputs", real_inputs)
    attempts = [a for a in Execution(root / "store").read().attempts if a.module_id == "CP-MODEL"]
    print("runs", first["status"], second["status"], workflow._phase,
          [(a.number, a.status, bool(a.issues), any(i.input_id == "CP-1" for i in a.inputs)) for a in attempts])
    return workflow


def test_p5_forged_failed_first_then_second_attempt_zero(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _run(positive_promoted, tmp_path, monkeypatch)
    verdict = base._verdict(workflow, tmp_path)
    print("VERDICT p5-failed-first-forged", verdict)
    assert verdict.endswith("identity_mismatch")


def test_p6_same_with_publication_replay_lenient(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _run(positive_promoted, tmp_path, monkeypatch)
    real = owner._expected_begin

    def lenient(before: Any, module_id: str, ticket_id: str) -> Any:
        if module_id != "CP-MODEL":
            return real(before, module_id, ticket_id)
        final = Execution(tmp_path / "store").read()
        return next(a for a in final.attempts if a.ticket_id == ticket_id)

    monkeypatch.setattr(owner, "_expected_begin", lenient)
    verdict = base._verdict(workflow, tmp_path)
    print("VERDICT p6-publication-replay-lenient", verdict)
