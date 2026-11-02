"""CP-DR LOCAL run driver: pack assembly, literal submissions, run-time bindings, tool calls.

One closed CP-DR run (CP-0, CP-1, CP-DR) over the pinned oracle in `cases/cpdr-research-owner`,
driven through the public `OwnerWorkflow` API only. G2 imports `cpdr_closed`; the CP-DR tests
import the stage functions to fork a run at any point. Nothing here asserts expected values: the
oracle files are read, never derived or edited.

The pack is the frozen financial pack (`manifest.json#financial_baseline`) plus the three accepted
evidence items as `text/plain` sources with `line:N` spans, plus the run's `context` file, the one
place the context questions live (`manifest.json#context`). The oracle's CP-0 and CP-1 source lists
do not name the context file, so the driver adds its one row to each, built from the file's own
first quoted line. The staging a `run_pathway` run writes under `<run>/research/` is written by
`stage`: the evidence record and the rejected items from `expected.json#intake`.
"""

import copy
import hashlib
import importlib
import json
import re
import socket
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cpdr_s1_support import ResearchCase

from deploy_vii.contracts import Fact, Module, Run, Source, Span
from deploy_vii.execution import Execution, head_of
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow import run_pathway as rp
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.redact import Redactor
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow
from deploy_workflow.owners import cpdr
from deploy_workflow.prompts.factory import prompt_factory
from deploy_workflow.replay import replay_module
from deploy_workflow.research import evidence as record
from deploy_workflow.research.intake import AcceptedItem, RefusedItem, write_rejected
from deploy_workflow.run_inputs import RunOutcome, check_arguments

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cpdr-research-owner"
CASES = ("positive", "v2")
RUN_KEY = {"positive": "run", "v2": "run_v2"}
SUBMISSION_KEY = {"positive": "research_v1", "v2": "research_v2"}
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
GAP_MARKER = "{{GAP_IDS}}"
RETRIEVED = "2026-01-11T08:00:00Z"  # a UTC-second time the fence header accepts (Q4)
BRIEF_MARKERS = ("{{CP0_RESULT_SHA256}}", "{{CP1_RESULT_SHA256}}")
RUN_FIELDS = (
    "run_id",
    "issuer_id",
    "issuer_name",
    "as_of",
    "method_version",
    "case_kind",
    "pathway",
    "requested_modules",
)
CONTEXT_BASE = ROOT / "cases" / "context" / "research-minimal.json"


def _driver(name: str) -> Any:
    return importlib.import_module(name)


def oracle() -> dict[str, Any]:
    """The three pinned oracle files (`cases/PINS.json`); a drifted file fails."""
    pins = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for name in ("manifest", "submissions", "expected"):
        path = CASE / f"{name}.json"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != pins[f"cases/cpdr-research-owner/{name}.json"]:
            raise RuntimeError(f"oracle drift: {name}.json")
        out[name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def run_of(case: str) -> Run:
    manifest = oracle()["manifest"]
    fields = {k: v for k, v in manifest[RUN_KEY[case]].items() if k in RUN_FIELDS}
    return Run.model_validate_json(json.dumps(fields))


def context_source(case: str) -> Source:
    """The run's `context` source: the minimal research context with the case's identity and the
    two context questions of `manifest.json#context`."""
    manifest = oracle()["manifest"]
    run = manifest[RUN_KEY[case]]
    document = json.loads(CONTEXT_BASE.read_text(encoding="utf-8"))
    document["run"].update(
        pathway=run["pathway"],
        case_kind=run["case_kind"],
        as_of=run["as_of"],
        reporting_currency="USD",
    )
    document["identity"].update(issuer_name=run["issuer_name"], issuer_id=run["issuer_id"])
    document["attachments"]["legal_documents"] = (
        "none"  # no legal document is declared for this run
    )
    document["research_questions"] = manifest["context"]["research_questions"]
    raw = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    return prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"), raw
    )


def evidence_sources() -> tuple[Source, ...]:
    """The three accepted evidence items as prepared `text/plain` sources, spans `line:1..line:N`
    (`manifest.json#evidence`, the item hash `page_join_sha256`)."""
    built = []
    for number, entry in enumerate(oracle()["manifest"]["evidence"][:3], 1):
        lines = entry["pages"][0]["text"].split("\n")
        built.append(
            Source(
                source_id=f"ev-{number}",
                name=entry["path"],
                status="ready",
                sha256=entry["page_join_sha256"],
                media_type="text/plain",
                spans=tuple(Span(locator=f"line:{n}", text=t) for n, t in enumerate(lines, 1)),
            )
        )
    return tuple(built)


def make_pack(case: str) -> PreparedPack:
    """Identity and financial (the financial slice's, hash-checked), `ev-1..3`, then `context`."""
    if case not in CASES:
        raise ValueError(f"unknown CP-DR case {case}")
    held = _driver("test_financial_workflow").make_pack().sources
    items = evidence_sources()
    return PreparedPack(run=run_of(case), sources=(*held, *items, context_source(case)))


# --- the staging a run_pathway run writes under <run>/research ------------------------------------


def accepted_items() -> tuple[AcceptedItem, ...]:
    """`expected.json#intake/accepted` with the text of `manifest.json#evidence`."""
    material = oracle()
    texts = {e["path"]: e["pages"][0]["text"] for e in material["manifest"]["evidence"]}
    return tuple(
        AcceptedItem(
            item_id=a["item_id"],
            path=a["path"],
            family=a["family"],
            published=date.fromisoformat(a["published"]),
            locator=a["locator"],
            sha256=a["sha256"],
            text=texts[a["path"]],
            origin="supplied",
            url=None,
        )
        for a in material["expected"]["intake"]["accepted"]
    )


def refused_items() -> tuple[RefusedItem, ...]:
    entries = oracle()["expected"]["intake"]["rejected_json"]["entries"]
    return tuple(
        RefusedItem(
            locator=e["locator"],
            family=e["family"],
            published=date.fromisoformat(e["published"]) if e["published"] else None,
            reason=e["reason"],
        )
        for e in entries
    )


def stage(root: Path) -> None:
    """`root/research/{evidence.json, rejected.json}` and `root/sources/ev-<n>.txt`, as staging
    writes them."""
    research = root / record.RESEARCH_DIR
    research.mkdir(parents=True, exist_ok=True)
    items = accepted_items()
    record.write_evidence(research / record.EVIDENCE_FILE, items, RETRIEVED)
    write_rejected(research / record.REJECTED_FILE, refused_items())
    (root / "sources").mkdir(exist_ok=True)
    for item in items:
        (root / "sources" / f"{item.item_id}.txt").write_bytes(item.text.encode("utf-8"))


# --- CP-0 and CP-1 ----------------------------------------------------------------------------------


def _citation(pack: PreparedPack) -> dict[str, str]:
    source = next(s for s in pack.sources if s.source_id == "context")
    name = pack.run.issuer_name
    span = next(s for s in source.spans if name in s.text)
    return {
        "source_id": "context",
        "source_sha256": source.sha256 or "",
        "locator": span.locator,
        "quote": name,
    }


def cp0_text(pack: PreparedPack, case: str) -> str:
    """`submissions.json#cp0_readiness_review` with the pack hash bound and one row for the
    context file."""
    review = copy.deepcopy(oracle()["submissions"]["cp0_readiness_review"])
    review["sources"].append(
        {
            "source_id": "context",
            "document_family": "Run context",
            "authority": "issuer",
            "entity": pack.run.issuer_name,
            "period": "January 2026",
            "version_relationship": "Run context file of this run",
            "fidelity": "verified",
            "citations": [_citation(pack)],
            "limitations": [],
        }
    )
    return json.dumps(review, ensure_ascii=False).replace(PACK_PLACEHOLDER, pack.content_hash())


def cp1_context_text(pack: PreparedPack) -> str:
    """`submissions.json#cp1_source_context` with the pack hash bound and one row for the
    context file."""
    stage_one = copy.deepcopy(oracle()["submissions"]["cp1_source_context"])
    stage_one["sources"].append(
        {
            "source_id": "context",
            "classification": "nonfinancial",
            "document_type": "Run context file",
            "published_on": pack.run.as_of.isoformat(),
            "evidence_class": "internal",
            "evidence_rationale": "The run's own context file",
            "analytical_use": "Research questions and run identity",
            "citations": [_citation(pack)],
            "event_scan": "unassessed",
            "event_scan_explanation": "A context file is not event evidence",
        }
    )
    return json.dumps(stage_one, ensure_ascii=False).replace(PACK_PLACEHOLDER, pack.content_hash())


def start(case: str, root: Path, store: str = "store") -> tuple[OwnerWorkflow, PreparedPack]:
    """The workflow over `root/<store>`, the staging under `root`, nothing settled."""
    pack = make_pack(case)
    stage(root)
    return OwnerWorkflow.create(root / store, pack, publication_directory=None), pack


def read_cited(workflow: OwnerWorkflow, payload: str) -> None:
    """One ok `read_pages` call per cited locator (`page:N` or `line:N`) of the payload."""
    cited = sorted(cited_locators(payload))
    for source, locator in cited:
        number = int(locator.split(":")[1])
        call = workflow.invoke(
            "read_pages", {"source_id": source, "first_page": number, "last_page": number}
        )
        if call["status"] != "ok":
            raise RuntimeError(f"read_pages {source} {locator}: {call['error_code']}")


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> dict[str, Any]:
    review = cp0_text(pack, case)
    read_cited(workflow, review)
    valid: dict[str, Any] = _driver("s1a_runs").submit_valid(workflow, review)
    return valid


def _bind(value: Any, rules: Mapping[str, str], inputs: Any, gaps: list[str]) -> Any:
    """`value` with each `{{EVID:*}}` marker bound by its `run_time_bindings` predicate and the
    `{{GAP_IDS}}` element by every narrative gap id; any other marker fails."""
    if isinstance(value, dict):
        return {key: _bind(item, rules, inputs, gaps) for key, item in value.items()}
    if isinstance(value, list):
        out: list[Any] = []
        for item in value:
            out.extend(gaps if item == GAP_MARKER else [_bind(item, rules, inputs, gaps)])
        return out
    if isinstance(value, str) and value.startswith("{{EVID:") and value in rules:
        return _driver("cp1c_runs").evidence_id(inputs, value, rules[value])
    if isinstance(value, str) and "{{" in value:
        raise RuntimeError(f"unbound readiness marker {value}")
    return value


def readiness_literal(workflow: OwnerWorkflow) -> str:
    """`submissions.json#cp1_readiness.payload` bound to the readiness step's inputs, exactly as
    the CP-1C driver binds its own; `inputs_sha256` is prefilled by Python and left out."""
    readiness = oracle()["submissions"]["cp1_readiness"]
    inputs = _driver("cp1d_runs").downstream_inputs(workflow)
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]
    document = copy.deepcopy(readiness["payload"])
    document.pop("inputs_sha256")
    return json.dumps(
        _bind(document, readiness["run_time_bindings"], inputs, gaps), ensure_ascii=False
    )


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
    """CP-1 to its promotion (a genuine one, about two minutes): the source_context literal after
    its cited reads and the no-event search, the financial slice's financials and narrative, the
    bound readiness literal and the quality review built from the read inputs."""
    fw, s1a = _driver("test_financial_workflow"), _driver("s1a_runs")
    context = cp1_context_text(pack)
    read_cited(workflow, context)
    s1a.search(workflow, "financial", "subsequent")
    s1a.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    s1a.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    s1a.submit_valid(workflow, json.dumps(fw.narrative(read)))
    workflow.read_inputs()
    s1a.submit_valid(workflow, readiness_literal(workflow))
    inputs = json.loads(workflow.read_inputs()["body"])
    s1a.submit_valid(workflow, _driver("cp2g_runs")._quality_review(fw, read, inputs))


def promoted(case: str, root: Path, store: str = "store") -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled and CP-DR begun at its `brief` step."""
    workflow, pack = start(case, root, store)
    drive_cp0(workflow, pack, case)
    drive_cp1(workflow, pack)
    return workflow, pack


# --- a store with CP-0 and CP-1 seeded (fast) -------------------------------------------------------


def _command(module_id: str) -> Fact:
    """CP-0's T8 command that authorizes `module_id` to begin."""
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def settled_pair(case: str, root: Path, modules: tuple[str, ...] = ("CP-0", "CP-1")) -> Execution:
    """A real store with `modules` settled as hand-built modules (`begin` and `finish`) and the
    staging under `root`; CP-DR is not begun."""
    pack = make_pack(case)
    stage(root)
    store = Execution.create(root / "store", pack)
    for module_id in modules:
        ticket = store.begin(module_id)
        module = Module(
            run_id=pack.run.run_id,
            issuer_id=pack.run.issuer_id,
            as_of=pack.run.as_of,
            module_id=module_id,
            status="candidate",
            inputs=ticket.inputs,
            facts=tuple(_command(m) for m in ("CP-1", cpdr.MODULE_ID))
            if module_id == "CP-0"
            else (),
            limitations=(f"{module_id} note",),
        )
        store.finish(ticket.ticket_id, module.model_dump_json(), lambda _module: ())
    return store


def seeded(case: str, root: Path) -> tuple[Execution, str]:
    """CP-0 and CP-1 settled in a real store as hand-built modules, the staging under `root`, then
    CP-DR begun after its anchor check. Returns the store and the CP-DR ticket, at the brief step.
    No workflow journal: the connect tests and the defect classes run the core's own `submit`
    over it."""
    store = settled_pair(case, root)
    cpdr.check_begin(store, store.read())
    return store, store.begin(cpdr.MODULE_ID).ticket_id


def locked(case: str, root: Path) -> tuple[Execution, str]:
    """`seeded`, then the defaults-only brief submitted through the core and locked on disk: the
    research step is next."""
    store, ticket = seeded(case, root)
    submitted = cpdr.submit(store, ticket, cpdr.BRIEF_STEP, defaults_only(case), None)
    if submitted.journal.steps[-1].status != "valid":
        raise RuntimeError(f"brief not valid: {submitted.journal.steps[-1].issues}")
    return store, ticket


# --- CP-DR ------------------------------------------------------------------------------------------


def brief_payload(case: str, questions: list[dict[str, Any]] | None = None) -> str:
    """The brief submission: `submissions.json#brief/model_tailored` (the 40 it tailors, or the
    given list) wrapped with the run id."""
    body = oracle()["submissions"]["brief"]["model_tailored"] if questions is None else questions
    return json.dumps({"run_id": run_of(case).run_id, "questions": body}, ensure_ascii=False)


def defaults_only(case: str) -> str:
    body = oracle()["submissions"]["brief"]["model_tailored_defaults_only"]
    return brief_payload(case, body)


def research_payload(case: str) -> str:
    return json.dumps(oracle()["submissions"][SUBMISSION_KEY[case]], ensure_ascii=False)


def run_calls(workflow: OwnerWorkflow, calls: Iterable[Mapping[str, Any]]) -> None:
    """A literal tool sequence (`tool_calls/research`): each call ok, each read returning every
    `expect_spans` locator, each search its `expect_header`."""
    for call in calls:
        if call["tool"] == "read_inputs":
            workflow.read_inputs()
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {outcome['error_code']}")
        body = str(outcome["body"])
        for span in call.get("expect_spans", ()):
            if f"locator={span['locator']} | " not in body:
                raise RuntimeError(f"{call['tool']}: no {span['source_id']} {span['locator']}")
        header = call.get("expect_header")
        if header is not None and not re.search(re.escape(header), body):
            raise RuntimeError(f"{call['tool']}: header {header!r} not in the body")


def drive_brief(workflow: OwnerWorkflow, case: str, payload: str | None = None) -> dict[str, Any]:
    """The brief step's `read_inputs`, then the brief submission (default: the defaults only, the
    brief both closed runs answer; `brief_payload` is the 40 tailored)."""
    workflow.read_inputs()
    outcome: dict[str, Any] = workflow.submit_review(
        defaults_only(case) if payload is None else payload
    )
    return outcome


def drive_research(
    workflow: OwnerWorkflow, case: str, payload: str | None = None
) -> dict[str, Any]:
    """The recorded research tool use (`tool_calls/research`), then the research submission."""
    run_calls(workflow, oracle()["submissions"]["tool_calls"]["research"])
    outcome: dict[str, Any] = workflow.submit_review(
        research_payload(case) if payload is None else payload
    )
    return outcome


def closed_walk(
    case: str,
    root: Path,
    store: str = "store",
    between: Callable[[OwnerWorkflow, PreparedPack], None] | None = None,
) -> OwnerWorkflow:
    """CP-0, CP-1 and CP-DR driven to the end over `root/<store>`. `between` runs with the
    workflow at the `research` step, after the brief is locked and before research is driven."""
    workflow, pack = promoted(case, root, store)
    brief = drive_brief(workflow, case)
    if brief["status"] != "valid":
        raise RuntimeError(f"CP-DR brief not valid: {brief['issues']}")
    if between is not None:
        between(workflow, pack)
    research = drive_research(workflow, case)
    if research["status"] != "valid":
        raise RuntimeError(f"CP-DR research not valid: {research['issues']}")
    return workflow


def cpdr_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-DR run of `case` under `root`: (store, sealed receipt, no publication)."""
    workflow = closed_walk(case, root)
    receipt = root / "owner-receipt.json"
    workflow.write_receipt(receipt)
    return root / "store", receipt, None


# --- a closed run finished the way `run_pathway` finishes one ---------------------------------------


@dataclass(frozen=True)
class ClosedRun:
    """`root` is a run directory: `execution/`, `research/`, `sources/`, and what `_finish_run`
    wrote (`owner-run.json`, `delivery/`, `run.json`). `fence` holds what the research step showed
    the model about `ev-3` (the composed prompt, a `read_pages` body) and the sockets opened."""

    root: Path
    prompt: str
    read_body: str
    sockets: int


_CLOSED: dict[str, ClosedRun] = {}


class _Sockets:
    def __init__(self) -> None:
        self.opened = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.opened += 1
        raise AssertionError("a test opened a socket")


def _research_view(
    root: Path, workflow: OwnerWorkflow, pack: PreparedPack, item: str, locator: str
) -> tuple[str, str]:
    """The composed research prompt, and the `read_pages` body of `item` at `locator`."""
    spec = next(
        step for step in OWNER_SPECS[cpdr.MODULE_ID].steps if step.step_id == cpdr.RESEARCH_STEP
    )
    compose = prompt_factory(
        pack, Execution(root / "execution"), untrusted_for=cpdr.untrusted_items(root / "research")
    )
    prompt = "\n".join(message.text for message in compose(workflow.binding, spec, ()))
    number = int(locator.split(":")[1])
    call = workflow.invoke(
        "read_pages", {"source_id": item, "first_page": number, "last_page": number}
    )
    return prompt, str(call["body"])


def closed_run(case: str, factory: pytest.TempPathFactory) -> ClosedRun:
    """One closed run of `case`, built once per process (the two test files share it), finished by
    `run_pathway._finish_run` so `run.json` is the file a run writes. Sockets are patched to
    raise while it runs."""
    if case in _CLOSED:
        return _CLOSED[case]
    root = factory.mktemp(f"cpdr-{case}") / "run"
    root.mkdir()
    fixture = oracle()["submissions"]["fence_fixture"]
    seen: dict[str, str] = {}

    def between(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
        seen["prompt"], seen["body"] = _research_view(
            root, workflow, pack, fixture["in_item"], fixture["locator"]
        )

    sockets = _Sockets()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "socket", sockets)
        patch.setattr(record, "research_clock", lambda: datetime(2026, 11, 2, tzinfo=UTC))
        workflow = closed_walk(case, root, "execution", between)
        base = factory.mktemp(f"cpdr-{case}-args")
        checked = check_arguments(**ResearchCase(base).arguments(base))
        meta = rp._Meta(checked, (), False, Redactor())
        outcome = rp._finish_run(workflow, root, meta, Budget(Decimal(1), root / "execution"))
    if outcome.outcome != "settled":
        raise RuntimeError(f"the closed run did not settle: {outcome.stopped_reason}")
    if not (root / "delivery" / "render-receipt.json").is_file():
        raise RuntimeError("the closed run settled without a render receipt")
    made = ClosedRun(root, seen["prompt"], seen["body"], sockets.opened)
    _CLOSED[case] = made
    return made


def rerun_from(v1_root: Path, root: Path) -> RunOutcome:
    """The same-evidence replacement of the closed `positive` run at `v1_root` (OD8), under the new
    run directory `root`: the `v2` pack (the same sources, the key's `run_v2` id), CP-0 and CP-1
    replayed from `v1_root` through `replay_module`, then CP-DR driven live with `research_v2` and
    the run finished by `run_pathway._finish_run` with `replayed_from` the earlier run id. No model
    is called, so the rerun writes no `calls.jsonl`. `v1_root` is only read."""
    root.mkdir(parents=True)
    earlier_id = run_of("positive").run_id
    pack = make_pack("v2")
    stage(root)
    execution = root / "execution"
    sockets = _Sockets()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "socket", sockets)
        patch.setattr(record, "research_clock", lambda: datetime(2026, 11, 2, tzinfo=UTC))
        workflow = OwnerWorkflow.create(execution, pack, publication_directory=None)
        for module_id in ("CP-0", "CP-1"):
            replay_module(workflow, v1_root, module_id, execution=execution)
        brief = drive_brief(workflow, "v2")
        if brief["status"] != "valid":
            raise RuntimeError(f"CP-DR brief not valid: {brief['issues']}")
        research = drive_research(workflow, "v2")
        if research["status"] != "valid":
            raise RuntimeError(f"CP-DR research not valid: {research['issues']}")
        base = root.parent / f"{root.name}-args"
        base.mkdir()
        checked = check_arguments(**ResearchCase(base).arguments(base, run_id=pack.run.run_id))
        meta = rp._Meta(checked, (), False, Redactor(), replayed_from=earlier_id)
        return rp._finish_run(workflow, root, meta, Budget(Decimal(1), execution))


# --- shared checks of the key's rules ---------------------------------------------------------------


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def brief_file(template: str, cp0: str, cp1: str) -> tuple[str, str]:
    """The key's brief file with the run-time markers substituted, and its brief_sha256, by the
    key's own rule (`brief/brief_sha256_rule`): the body without `brief_sha256`, sorted keys,
    compact separators, UTF-8, after the two result hashes are substituted."""
    text = template.replace("{{CP0_RESULT_SHA256}}", cp0).replace("{{CP1_RESULT_SHA256}}", cp1)
    body = json.loads(text)
    body.pop("brief_sha256")
    digest = sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return text.replace("{{BRIEF_SHA256}}", digest), digest


def edit_head(
    store: Execution, module_id: str, forged: Module | None = None, **update: Any
) -> None:
    """Write a head the journal would not: `update` changes the head's fields; `forged` is a module
    stored as a blob and made the head's result (a consistent blob and head). The store has no
    public way to do either; the anchors and the probe exist for exactly this tampering."""
    snapshot = store.read()
    heads = []
    for head in snapshot.heads:
        if head.module_id == module_id:
            if forged is not None:
                store._store(forged.model_dump_json())
                head = head_of(forged, head.qualification)
            head = head.model_copy(update=update)
        heads.append(head)
    store._write(
        snapshot.model_copy(update={"parent": snapshot.content_hash(), "heads": tuple(heads)})
    )
