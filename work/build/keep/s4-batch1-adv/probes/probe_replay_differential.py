"""Differential probe: `owner._expected_begin(before, m, t)` against the real `Execution.begin(m)`
on a store whose current snapshot is `before`, over seeded random snapshots (heads of every
status, CP-0 commands, prior attempts with matching or perturbed inputs, pending or finished,
with or without issues). Every case must agree: both refuse, or both yield the same attempt."""
import hashlib
import random
import sys
from pathlib import Path

import s1a_runs as runs
from deploy_vii.contracts import Input
from deploy_vii.execution import Attempt, Command, Execution, Head, current_inputs
from deploy_vii.registry import plan
from deploy_workflow.workflow import WorkflowError
import importlib

owner = importlib.import_module("deploy_workflow.owner_workflow")


def h(rng: random.Random) -> str:
    return hashlib.sha256(str(rng.random()).encode()).hexdigest()


def main(root: Path, cases: int, seed: int) -> int:
    rng = random.Random(seed)
    pack = runs.make_pack("positive")
    store = Execution.create(root / "store", pack)
    base = store.read()
    modules = plan(pack.run.requested_modules)
    counts = {"agree-refuse": 0, "agree-attempt": 0}
    numbers = {0: 0, 1: 0}
    disagreements = []
    for i in range(cases):
        heads = []
        for m in modules:
            if rng.random() < 0.3:
                continue
            commands = ()
            if m == "CP-0":
                commands = tuple(
                    Command(row_id=c, text=rng.choice([f"Run {c}", f"Run {c}", "Hold", None]))
                    for c in modules
                    if c not in ("CP-0", "CP-MODEL") and rng.random() < 0.9
                )
            heads.append(
                Head(
                    module_id=m,
                    status=rng.choice(["accepted", "restricted", "blocked", "stale"]),
                    result_sha256=h(rng),
                    inputs=(),
                    commands=commands,
                )
            )
        snap = base.model_copy(update={"heads": tuple(heads)})
        target = rng.choice(modules)
        try:
            good = current_inputs(snap, target)
        except ValueError:
            good = (Input(input_id="prepared-pack", sha256=snap.pack_sha256),)
        attempts = []
        for k in range(rng.choice([0, 0, 1, 1, 2, 3])):
            inputs = good if rng.random() < 0.75 else (*good, Input(input_id="CP-9", sha256=h(rng)))
            attempts.append(
                Attempt(
                    ticket_id=f"t{i}-{k}",
                    module_id=target if rng.random() < 0.85 else rng.choice(modules),
                    inputs=inputs,
                    number=rng.choice([0, 1]),
                    status="pending" if rng.random() < 0.1 else "finished",
                    issues=("x",) if rng.random() < 0.6 else (),
                )
            )
        snap = snap.model_copy(update={"attempts": tuple(attempts)})
        store._write(snap)
        try:
            real = store.begin(target)
        except ValueError as error:
            real = ("refuse", type(error).__name__)
        try:
            expected = owner._expected_begin(snap, target, real.ticket_id if isinstance(real, Attempt) else "probe-ticket")
        except WorkflowError as error:
            expected = ("refuse", error.code)
        if isinstance(real, Attempt) and isinstance(expected, Attempt):
            if real == expected:
                counts["agree-attempt"] += 1
                numbers[real.number] += 1
            else:
                disagreements.append((i, target, real, expected))
        elif not isinstance(real, Attempt) and not isinstance(expected, Attempt):
            counts["agree-refuse"] += 1
        else:
            disagreements.append((i, target, real, expected))
    print("counts", counts, "numbers", numbers, "disagreements", len(disagreements))
    for d in disagreements[:5]:
        print("DISAGREE", d)
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])))
