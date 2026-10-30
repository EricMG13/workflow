"""Lens B step 2: cross-check the merged registration tables at 9f71bfa.
Run from the extracted tree with PYTHONPATH=src. Exit 1 on any inconsistency."""
import importlib, sys
from collections import Counter
import deploy_workflow.owner_workflow as ow
import deploy_workflow.host as host
import deploy_workflow.owner_rendering as orr
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii import report_view as rv
from deploy_vii.contracts import PATHWAY_MODULES

bad = []
def check(cond, msg):
    if not cond: bad.append(msg)

specs = ow.OWNER_SPECS
mods = set(specs)
print("OWNER_SPECS", sorted(mods))
# every spec key equals its module_id
for m, s in specs.items():
    check(s.module_id == m, f"spec key {m} != module_id {s.module_id}")
# step ids unique across all modules
steps = [st.step_id for s in specs.values() for st in s.steps]
dup = [k for k, n in Counter(steps).items() if n > 1]
check(not dup, f"duplicate step ids across OWNER_SPECS: {dup}")
step_owner = {st.step_id: m for m, s in specs.items() for st in s.steps}
# _PROBES / _QUALIFICATION cover exactly the specs (CP-0 has no qualification)
det = {m for m, s in specs.items() if s.kind == "deterministic"}  # CP-MODEL: verified by _verify_publications
check(set(ow._PROBES) == mods - det, f"_PROBES vs specs: extra {set(ow._PROBES)-(mods-det)} missing {(mods-det)-set(ow._PROBES)}")
qual_expected = mods - {"CP-0"}
check(set(ow._QUALIFICATION) <= mods, f"_QUALIFICATION orphan {set(ow._QUALIFICATION)-mods}")
print("specs without qualification", sorted(mods - set(ow._QUALIFICATION)))
# _CORES = owner_core entries
cores = {m for m, s in specs.items() if s.entry == "owner_core"}
check(set(ow._CORES) == cores, f"_CORES vs entry=owner_core: extra {set(ow._CORES)-cores} missing {cores-set(ow._CORES)}")
for m, core in ow._CORES.items():
    check(getattr(core, "MODULE_ID", m) == m, f"_CORES[{m}].MODULE_ID={getattr(core,'MODULE_ID',None)}")
    check(tuple(core.STEP_IDS) == tuple(st.step_id for st in specs[m].steps), f"{m} STEP_IDS {core.STEP_IDS} != spec steps")
    check(core.QUALIFICATION is ow._QUALIFICATION.get(m), f"{m} QUALIFICATION row is not the core's")
    check(ow._PROBES.get(m) is core.probe, f"{m} _PROBES row is not core.probe")
    check(ow._ENTRY_VALIDATORS.get(m) is core.ENTRY_VALIDATOR, f"{m} _ENTRY_VALIDATORS row is not the core's")
# _VIEWS: exactly the module_context/step_context steps, view belongs to the owning module
ctx = {st.step_id for s in specs.values() for st in s.steps if st.inputs in ("module_context", "step_context")}
check(set(ow._VIEWS) == ctx, f"_VIEWS vs context steps: extra {set(ow._VIEWS)-ctx} missing {ctx-set(ow._VIEWS)}")
for step, fn in ow._VIEWS.items():
    owner = step_owner.get(step)
    modname = fn.__module__.rsplit(".", 1)[-1]
    check(owner and modname.replace("_", "").lower() == owner.replace("-", "").lower(), f"_VIEWS[{step}] -> {fn.__module__} but step owner {owner}")
# _ENTRY_VALIDATORS: analytical modules except CP-0/CP-1 (and CP-MODEL deterministic)
ev_expected = {m for m, s in specs.items() if s.kind == "analytical"} - ow._FINANCIAL_MODULES
check(set(ow._ENTRY_VALIDATORS) == ev_expected, f"_ENTRY_VALIDATORS: extra {set(ow._ENTRY_VALIDATORS)-ev_expected} missing {ev_expected-set(ow._ENTRY_VALIDATORS)}")
# host._SOURCE_STEPS = steps with sources=True
src = {m: tuple(st.step_id for st in s.steps if st.sources) for m, s in specs.items()}
src = {m: v for m, v in src.items() if v}
check(dict(host._SOURCE_STEPS) == src, f"_SOURCE_STEPS mismatch: host={dict(host._SOURCE_STEPS)} specs={src}")
# _OWNER_SCOPES: keys are sourced owner-core steps
for (m, st) in host._OWNER_SCOPES:
    check(st in host._SOURCE_STEPS.get(m, ()), f"_OWNER_SCOPES orphan {(m, st)}")
owner_only_sourced = {(m, st) for m, v in src.items() for st in v if specs[m].entry == "owner_core"}
check(set(host._OWNER_SCOPES) == owner_only_sourced, f"_OWNER_SCOPES vs owner-core sourced: extra {set(host._OWNER_SCOPES)-owner_only_sourced} missing {owner_only_sourced-set(host._OWNER_SCOPES)}")
# SHIPPED_MAPS: one map per module, no duplicate slots
mids = [bm.module_id for bm in SHIPPED_MAPS]
check(len(mids) == len(set(mids)), f"SHIPPED_MAPS duplicate module {[k for k,n in Counter(mids).items() if n>1]}")
slots = [e.slot for bm in SHIPPED_MAPS for e in bm.entries]  # (block_id, cell_slot), bindings/__init__.py rule
check(len(slots) == len(set(slots)), f"duplicate cell_slot {[k for k,n in Counter(slots).items() if n>1]}")
for bm in SHIPPED_MAPS:
    for e in bm.entries:
        check(e.fact_coord.module_id == bm.module_id, f"map {bm.module_id} binds foreign coord {e.fact_coord.module_id}")
print("owner specs without binding map:", sorted(mods - set(mids)))
blocks_of = {bm.module_id: {e.block_id for e in bm.entries} for bm in SHIPPED_MAPS}
compose = {p: set(b) for p, _t, _q, b in rv._PRESETS}
# DELIVERY_SCOPES: row count == dict size; match keys unique; modules registered; sections bound and in pathway
rows = orr._DELIVERY_ROWS
check(len(rows) == len(orr.DELIVERY_SCOPES), f"duplicate scope_id: {[k for k,n in Counter(r.scope_id for r in rows).items() if n>1]}")
keys = [(r.pathway, r.requested_modules, r.case_kind) for r in rows]
check(len(keys) == len(set(keys)), f"duplicate scope match key {[k for k,n in Counter(keys).items() if n>1]}")
for r in rows:
    for m in r.requested_modules:
        check(m in mods or m == "CP-MODEL", f"scope {r.scope_id}: module {m} not in OWNER_SPECS")
        check(m in mids, f"scope {r.scope_id}: module {m} has no binding map")
    bound = set().union(*(blocks_of.get(m, set()) for m in r.requested_modules))
    for sec in r.sections:
        check(sec in compose[r.pathway], f"scope {r.scope_id}: section {sec} not composed in {r.pathway}")
        check(sec in bound, f"scope {r.scope_id}: section {sec} not bound by {r.requested_modules}")

# SUPPORTED_ANALYTICAL = analytical specs
an = {m for m, s in specs.items() if s.kind == "analytical"}
check(set(ow.SUPPORTED_ANALYTICAL) == an, f"SUPPORTED_ANALYTICAL vs analytical specs: extra {set(ow.SUPPORTED_ANALYTICAL)-an} missing {an-set(ow.SUPPORTED_ANALYTICAL)}")
# block specs: one spec per block id across compositions (_spec_of is first-match)
seen = {}
for comp in rv._COMPOSITIONS:
    for b, sp in comp.items():
        if b in seen and seen[b] != sp:
            bad.append(f"block {b}: shadowed spec in a later composition ({seen[b].producers} wins over {sp.producers})")
        seen.setdefault(b, sp)
# every binding into a composed block comes from a listed producer or the Model-owned strip
binders = {}
for bm in SHIPPED_MAPS:
    for e in bm.entries:
        binders.setdefault(e.block_id, set()).add(bm.module_id)
for b, sp in seen.items():
    got = binders.get(b, set())
    if not set(sp.producers) <= got | {"CP-MODEL"}:
        print(f"note: block {b} producers {sp.producers} but bound by {sorted(got)}")
    if got - set(sp.producers) - {"CP-MODEL"}:
        print(f"note: block {b} bound by non-producer {sorted(got - set(sp.producers))}")

# every composed block is in some pathway preset; every figure producer's pathways list that block
allblocks = set().union(*compose.values())
for b in seen:
    check(b in allblocks, f"composition row {b} is in no pathway preset (orphan)")
for b, (_fn, pws) in rv._FIGURE_PRODUCERS.items():
    holders = {p for p, bl in compose.items() if b in bl}
    check(holders and (pws is None or pws <= holders), f"figure producer {b} pathways {pws} vs pathways holding it {holders}")
    if pws is None and len(holders) > 1:
        print(f"note: figure producer {b} draws on every pathway holding it: {sorted(holders)}")
# every preset block that a binding fills has a composition spec (else _spec_of falls back to Unbound)
for p, bl in compose.items():
    for b in bl:
        if b in binders and b not in seen and b not in ("evidence", "limitations", "header"):
            print(f"note: {p}/{b} is bound by {sorted(binders[b])} but has no _Spec row (Unbound owner)")
print("scopes", len(rows))
for b in bad: print("BAD:", b)
sys.exit(1 if bad else 0)
