"""T5 third-fix re-review probe q2: the earnings foundation replay (_source_session,
earnings_workflow.py:~2181), which re-runs every foundation call on a fresh SourceSession of
the same binding at submit_review. In each source phase (source_readiness, source_context,
financials) calls are injected, then the phase is completed as drive_fresh_foundation does.
Earnings' own _json_copy refuses every argument form the host refuses (depth, NaN, surrogate)
before any sequence is taken, so the injected host refusals are: an unencodable str name
(host name branch) and offered/unoffered str names with valid arguments (stage path);
surrogate arguments are injected only to confirm they stop before the host.
extract_statements is offered only in financials. argv[1] == "mutant-true" patches
SourceTools.offers to always True; it still exits 0, which shows the offers branch is not
reachable from the earnings workflow.
Exit 1 if an injected reply is not the plan's code, or a phase submission is not valid."""
import json, sys, tempfile
from pathlib import Path
import test_earnings_workflow as te
from test_financial_workflow import context, financials
from deploy_workflow.tools.source import SourceTools

if sys.argv[1:] == ["mutant-true"]:
    SourceTools.offers = lambda self, name: True
core = te.api()
OFFERED = {"source_readiness": {"search_pack", "read_pages"},
           "source_context": {"search_pack", "read_pages"},
           "financials": {"search_pack", "read_pages", "extract_statements"}}
bad = 0


def inject(w, phase):
    global bad
    for name in ("search_pack", "extract_statements", "foo"):
        try:
            w.invoke(name, {"query": "\ud800"})
            bad = 1
            print(phase, name, "surrogate args reached the host  <-- FAIL")
        except core.OwnerError as e:
            print(f"{phase:16} {name!r:22} surrogate args refused before host: {e.code}")
    for name, args, want in (
        ("search_pack\ud800", {"query": "x"}, ("", {}, "refused", "not_permitted")),
        ("extract_statements\ud800", {"source_id": "financial", "locators": ["page:2"]}, ("", {}, "refused", "not_permitted")),
        ("foo", {"query": "x"}, ("foo", {"query": "x"}, "refused", "not_permitted")),
        ("", {}, ("", {}, "refused", "not_permitted")),
        ("extract_statements", {"source_id": "financial"}, ("extract_statements", {"source_id": "financial"}, "refused", "bad_arguments" if phase == "financials" else "not_permitted")),
    ):
        if True:
            r = w.invoke(name, args)
            got = (r["tool"], r["arguments"], r["status"], r["error_code"])
            ok = got == want
            bad |= not ok
            print(f"{phase:16} {name!r:28} {got} {'OK' if ok else 'want ' + str(want) + ' <-- FAIL'}")


case_id = "E-QOQ-FLAT"
pack = te.pack_for(case_id)
w = core.EarningsWorkflow.create(Path(tempfile.mkdtemp(prefix="t5q2-")) / "owner", pack,
                                 case_manifest=te.CASE_MANIFEST, case_id=case_id)
assert w.state().phase == "source_readiness"
inject(w, "source_readiness")
for source in ("identity", "financial"):
    assert w.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})["status"] == "ok"
o = w.submit_review(te.foundation_review(pack, False))
print("source_readiness submit", o.disposition, getattr(o, "error_codes", None))
bad |= o.disposition != "valid"
if o.disposition == "valid":
    inject(w, "source_context")
    for source in ("identity", "financial"):
        assert w.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})["status"] == "ok"
    assert w.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})["status"] == "ok"
    o = w.submit_review(context(pack))
    print("source_context submit", o.disposition, getattr(o, "error_codes", None))
    bad |= o.disposition != "valid"
if o.disposition == "valid":
    inject(w, "financials")
    assert w.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 5})["status"] == "ok"
    assert w.invoke("extract_statements", {"source_id": "financial", "locators": ["page:2", "page:3", "page:4"]})["status"] == "ok"
    assert w.invoke("search_pack", {"query": "not disclosed", "source_id": "financial"})["status"] == "ok"
    o = w.submit_review(json.dumps(financials(pack)))
    print("financials submit", o.disposition, getattr(o, "error_codes", None))
    bad |= o.disposition != "valid"
print("EXIT", 1 if bad else 0)
sys.exit(1 if bad else 0)
