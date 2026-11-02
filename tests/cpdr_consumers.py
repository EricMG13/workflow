"""Fast CP-DR consumer fixtures (O7c C3): a real store over the CP-DR positive pack with a chosen
requested set. CP-0 and CP-1 (and CP-1A) are hand-built as `cpdr_runs.settled_pair`; CP-DR is
settled through its own core (the brief, then research: two journaled steps), never hand-built.
No model and no socket."""

from pathlib import Path

import cpdr_runs as runs

from deploy_vii.contracts import Fact, Module
from deploy_vii.execution import Execution, Head
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan
from deploy_workflow.owners import cpdr


def command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def store_with(root: Path, requested: tuple[str, ...], name: str = "store") -> Execution:
    """The store `root/<name>` (`execution` is the run layout) and the staging `root/research` over the positive pack, whose
    requested modules are `requested`."""
    pack = runs.make_pack("positive")
    pack = PreparedPack(
        run=pack.run.model_copy(update={"requested_modules": requested}), sources=pack.sources
    )
    runs.stage(root)
    return Execution.create(root / name, pack)


def hand_settle(store: Execution, module_id: str) -> Module:
    """`module_id` settled as a hand-built module over its ticket's inputs (CP-0 carries the T8
    commands for the whole plan)."""
    pack = store.pack(store.read())
    ticket = store.begin(module_id)
    module = Module(
        run_id=pack.run.run_id,
        issuer_id=pack.run.issuer_id,
        as_of=pack.run.as_of,
        module_id=module_id,
        status="candidate",
        attempt=ticket.number,
        inputs=ticket.inputs,
        facts=tuple(command(m) for m in plan(pack.run.requested_modules))
        if module_id == "CP-0"
        else (),
        limitations=(f"{module_id} note",),
    )
    store.finish(ticket.ticket_id, module.model_dump_json(), lambda _module: ())
    return module


def real_cpdr(store: Execution, research: str | None = None) -> None:
    """CP-DR through its core: the anchor check, begin, the defaults-only brief, then research
    (`research` is the payload; default the key's positive submission)."""
    cpdr.check_begin(store, store.read())
    ticket = store.begin(cpdr.MODULE_ID).ticket_id
    brief = cpdr.submit(store, ticket, cpdr.BRIEF_STEP, runs.defaults_only("positive"), None)
    assert brief.journal.steps[-1].status == "valid", brief.journal.steps[-1].issues
    payload = runs.research_payload("positive") if research is None else research
    step = cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, payload, None)
    assert step.journal.steps[-1].status == "valid", step.journal.steps[-1].issues


def settled_through_cpdr(root: Path, requested: tuple[str, ...], name: str = "store") -> Execution:
    """Every module before CP-DR in the plan hand-built, then CP-DR settled by its core."""
    store = store_with(root, requested, name)
    for module_id in plan(requested):
        if module_id == cpdr.MODULE_ID:
            real_cpdr(store)
            break
        hand_settle(store, module_id)
    return store


def head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)
