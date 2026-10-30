"""Rails for cp3d (render.blocks "evidence rail" / "limitations rail") and cp8 (render.rails), and
module limitations as the oracle splits them, on real fast pages. The page's limitations are those
of a settled head: own = candidate limitations + the synthetic limitation (execution.py:476-481),
inherited = execution.inherited_limitations over a CP-0 head holding the oracle's CP-0 limitations;
view = dict.fromkeys(own + inherited) (execution.py:957)."""
import copy
import importlib
import sys
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])
import common as C  # noqa: E402

from deploy_vii.contracts import Module  # noqa: E402
from deploy_vii.execution import inherited_limitations  # noqa: E402
from deploy_workflow.owners import cp8  # noqa: E402

SYNTH = "Synthetic case; not real issuer qualification"  # execution.py:477; pinned in cp4-owner settled_limitations


def settled_view_limits(run, candidate_limits, cp0_limits):
    own = tuple(dict.fromkeys((*candidate_limits, *((SYNTH,) if run.case_kind == "synthetic" else ()))))
    cp0 = Module(run_id=run.run_id, issuer_id=run.issuer_id, as_of=run.as_of, module_id="CP-0",
                 status="restricted", limitations=tuple(cp0_limits))
    snap = SimpleNamespace(heads=(SimpleNamespace(module_id="CP-0"),))
    att = SimpleNamespace(inputs=(SimpleNamespace(input_id="CP-0", status="restricted"),))
    inh = inherited_limitations(snap, att, own, lambda h: cp0)
    return tuple(dict.fromkeys((*own, *inh)))


def rule(case_node, run):
    """Oracle split: own, then the synthetic limitation for a synthetic run (settle moves it into own),
    then inherited; de-duplicated."""
    assert run.case_kind != "synthetic" or SYNTH in case_node["inherited_limitations"]
    synth = [SYNTH] if run.case_kind == "synthetic" else []
    return list(dict.fromkeys([*case_node["own_limitations"], *synth, *case_node["inherited_limitations"]]))


def check(payload, module_id, rails, case_node, run):
    m = C.module_payload(payload, module_id)
    assert set(rails) <= {t["table_id"] for t in m["tables"]}, module_id
    assert m["limitations"] == rule(case_node, run), module_id


fails = 0


def try_perturbs(payload, module_id, rails, node, run, extra=()):
    global fails
    def mutate(fn):
        p = copy.deepcopy(payload); fn(p); return p
    mp = lambda p: C.module_payload(p, module_id)
    perturbs = [
        ("rail table missing", mutate(lambda p: mp(p)["tables"].pop(next(i for i, t in enumerate(mp(p)["tables"]) if t["table_id"] == rails[-1])))),
        ("inherited limitation dropped", mutate(lambda p: mp(p)["limitations"].pop())),
        ("own limitation reworded", mutate(lambda p: mp(p)["limitations"].__setitem__(0, mp(p)["limitations"][0] + "."))),
        ("limitations reversed", mutate(lambda p: mp(p)["limitations"].reverse())),
        *extra,
    ]
    for name, p in perturbs:
        try:
            check(p, module_id, rails, node, run)
        except (AssertionError, StopIteration):
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1


base = importlib.import_module("test_connect_cp3d")
E3 = C.oracle("cp3d-owner")
rails3 = [*E3["render"]["blocks"]["evidence rail"], *E3["render"]["blocks"]["limitations rail"]]
for case in ("positive", "gap_no_recovery", "gap_no_market"):
    run = base._pack(case).run
    mod = base._module(case)
    limits = settled_view_limits(run, mod.limitations, E3["cp0"][case]["limitations"])
    mod = mod.model_copy(update={"limitations": limits, "inherited_limitations": ()})
    payload = C.payload_of(C.view_with(run, [mod]))
    node = E3["cases"][case]
    check(payload, "CP-3D", rails3, node, run)
    naive = list(dict.fromkeys([*node["own_limitations"], *node["inherited_limitations"]]))
    print("cp3d", case, "accepts; dict.fromkeys(own + inherited) equals the settled page:", naive == list(limits))
    try_perturbs(payload, "CP-3D", rails3, node, run)

m8 = importlib.import_module("test_method_cp8")
c8 = importlib.import_module("test_connect_cp8")
E8 = C.oracle("cp8-owner")
rails8 = [*E8["render"]["rails"]["evidence"], *E8["render"]["rails"]["limitations"]]
for case in ("positive", "no_outcome"):
    out = m8.report_of(case)
    run = c8._run(case)
    lo = cp8.LedgerOutput(run=run, submission_sha256="a" * 64, facts=out.facts, tables=out.tables,
                          claims=out.claims, limitations=out.limitations)
    mod = cp8.cp8_module(report=lo, inputs=c8._attempt().inputs, attempt=0)
    limits = settled_view_limits(run, mod.limitations, E8["cp0"][case]["limitations"])
    mod = mod.model_copy(update={"status": "restricted", "limitations": limits})
    payload = C.payload_of(C.view_with(run, [mod]))
    node = E8["cases"][case]
    check(payload, "CP-8", rails8, node, run)
    naive = list(dict.fromkeys([*node["own_limitations"], *node["inherited_limitations"]]))
    print("cp8", case, "accepts; dict.fromkeys(own + inherited) equals the settled page:", naive == list(limits))
    try_perturbs(payload, "CP-8", rails8, node, run)
sys.exit(1 if fails else 0)
