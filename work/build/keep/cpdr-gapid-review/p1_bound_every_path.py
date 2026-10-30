"""Probe 1: for gap ids of 138, 139, 153 chars, run validate_research, ENTRY_VALIDATOR, compose,
research_module, cpdr_reader (in-memory), and the real-store submit (CP-0 settled with the long id).
Exit 0 iff: 138 passes validation and composes/settles/reads; 139 and 153 are refused at
validation with the expected issue, compose raises, and the real-store submit journals an invalid
step without raising."""
import copy, json, os, sys, tempfile
sys.path[:0] = [os.path.join(os.getcwd(), "src"), os.path.join(os.getcwd(), "tests")]
from pathlib import Path
import test_connect_cpdr as t
from deploy_workflow.owners import cpdr

OLD = "missing-ownership-transaction"
fail = []
print("GAP_ID_MAX", cpdr.GAP_ID_MAX)
# derived id lengths at the bound
L = cpdr.GAP_ID_MAX
fams = {f"TDR.1.<g>.{f}": 6 + L + 1 + len(f) for f, _ in cpdr.TDR1_COLUMNS}
fams |= {f"cpdr-<g>-{f}": 5 + L + 1 + len(f) for f, _ in cpdr.TDR1_COLUMNS}
fams |= {f"consumed TDR.1.<g>.{f}": 6 + L + 1 + len(f) for f in cpdr.PER_GAP_CONSUMED}
print("max derived id at bound:", max(fams.values()), max(fams, key=fams.get))
for n in (cpdr.GAP_ID_MAX, cpdr.GAP_ID_MAX + 1, t.CP0_GAP_ID_LONGEST):
    gid = "g" * n
    for case in ("partial", "unresolved"):
        payload, module = t._with_gap_id(gid) if case == "partial" else (None, None)
        if case == "unresolved":
            (fact, other) = t.cp0_facts(empty=False)
            renamed = fact.model_copy(update={"fact_id": f"T5.{gid}.gap", "row_id": gid})
            module = t.cp0_module(empty=False).model_copy(update={"facts": (renamed, other)})
            payload = copy.deepcopy(t.SUBMISSIONS["cpdr"]["unresolved"])
            payload["gaps"][0]["gap_id"] = gid
        attempt, store = t.attempt_of(module, json.dumps(payload))
        sub = t.submission(payload)
        inputs = cpdr._inputs(store, attempt, sub)
        issues = cpdr.validate_research(submission=sub, upstream=inputs.agenda, pack=t.sources())
        ev = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
        try:
            rep = cpdr.compose(inputs)
            mod = cpdr.research_module(report=rep, inputs=inputs, attempt=attempt, run=store.read().run)
            served, head = t.settled(mod)
            got = cpdr.cpdr_reader(served, head)
            composed = f"ok facts={len(rep.facts)} reader_gaps={[len(g.gap_id) for g in got.gaps]}"
        except Exception as e:  # probe records the failure class, does not hide it
            composed = f"raised {type(e).__name__}"
        print(n, case, "issues=", [i[:60] for i in issues], "ev_out=", ev.output is not None, composed)
        if n <= cpdr.GAP_ID_MAX:
            if issues or ev.output is None or not composed.startswith("ok"):
                fail.append((n, case, "accepted path broken"))
        else:
            if not any("too long to compose" in i for i in issues) or ev.output is not None or composed.startswith("ok"):
                fail.append((n, case, "not refused"))
# real store end-to-end
for n in (cpdr.GAP_ID_MAX, cpdr.GAP_ID_MAX + 1, t.CP0_GAP_ID_LONGEST):
    gid = "g" * n
    with tempfile.TemporaryDirectory() as d:
        pack = t.prepared_pack()
        store = t.Execution.create(Path(d) / "store", pack)
        text = json.dumps(t.SUBMISSIONS["cp0_readiness_review"]).replace(t.PACK_MARK, pack.content_hash()).replace(OLD, gid)
        cp0 = t.submit_cp0_review(store, store.begin("CP-0").ticket_id, text)
        if cp0.status != "finished" or cp0.issues:
            print(n, "real-store: CP-0 did not settle", cp0.status, cp0.issues[:2]); fail.append((n, "cp0")); continue
        payload = copy.deepcopy(t.SUBMISSIONS["cpdr"]["partial"])
        payload["gaps"][0]["gap_id"] = gid
        calls = [c for c in t.SUBMISSIONS["tool_calls"]["partial"] if c["tool"] != "read_inputs"]
        try:
            att = t.run_cpdr(store, payload, calls)
            res = f"status={att.status} step={att.steps[0].status} issues={[i[:50] for i in att.issues][:3]}"
            ok = (att.status == "finished" and att.steps[0].status == "valid") if n <= cpdr.GAP_ID_MAX else att.steps[0].status == "invalid"
            if ok and n <= cpdr.GAP_ID_MAX:
                h = t.cpdr_head(store); got = cpdr.cpdr_reader(store, h); res += f" reader_gaps={[len(g.gap_id) for g in got.gaps]}"
        except Exception as e:
            res, ok = f"raised {type(e).__name__}: {str(e)[:120]}", False
        print(n, "real-store", res)
        if not ok: fail.append((n, "real-store"))
print("FAIL", fail)
sys.exit(1 if fail else 0)
