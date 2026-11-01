"""T5 third-fix re-review probe q3: end-to-end financial run (python-api) with host-refused
argument calls injected in the financials step, where extract_statements IS offered, and in
source_context, where it is not; then promote, publish, write_receipt and
verify_financial_slice_receipt (whose replay re-runs invoke(call.tool, call.arguments) on a
SourceSession of the same binding/step, financial_workflow.py:~1131).
argv[1] == "mutant-true" patches SourceTools.offers to always True (the probe must then fail).
Exit 1 if an injected reply is not the plan's code or the run cannot seal and verify."""
import sys, tempfile
from pathlib import Path
import test_financial_workflow as tf
from deploy_vii.execution import Execution
from deploy_workflow.financial_workflow import verify_financial_slice_receipt
from deploy_workflow.tools.source import SourceTools

if sys.argv[1:] == ["mutant-true"]:
    SourceTools.offers = lambda self, name: True
bad = 0


def deep(n):
    v = []
    for _ in range(n):
        v = [v]
    return v


def inject(w, offered):
    global bad
    for name in ("extract_statements", "search_pack", "foo", ""):
        for kind, args in (("deep", {"source_id": "financial", "x": deep(105)}),
                           ("surr", {"source_id": "\ud800"}), ("non_dict", [1])):
            r = w.invoke(name, args)
            want = (name, {}, "refused", "bad_arguments" if name in offered else "not_permitted")
            got = (r["tool"], r["arguments"], r["status"], r["error_code"])
            bad |= got != want
            print(f"{w._binding.step_id:16} {name!r:22} {kind:9} {got} {'OK' if got == want else 'want ' + str(want) + ' <-- FAIL'}")


orig_start, orig_reads, orig_context = tf.start, tf.financial_reads, tf.context


def start(root, gap=False):
    w, pack = orig_start(root, gap)
    w._participant, w._transport = "t5", "python-api"
    return w, pack


def context(pack):
    inject(CURRENT[0], {"search_pack", "read_pages"})
    return orig_context(pack)


def financial_reads(w):
    inject(w, {"search_pack", "read_pages", "extract_statements"})
    orig_reads(w)


CURRENT = []
tf.start, tf.financial_reads, tf.context = start, financial_reads, context
root = Path(tempfile.mkdtemp(prefix="t5q3-"))
real_before = tf.before_financials


def before_financials(r, **kw):
    w, pack = start(r)
    CURRENT.append(w)
    tf.read_sources(w)
    assert w.submit_review(tf.readiness(pack))["status"] == "valid"
    for p in (("identity", 1), ("financial", 1)):
        w.invoke("read_pages", {"source_id": p[0], "first_page": 1, "last_page": 1})
    w.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    outcome = w.submit_review(context(pack))
    assert outcome["status"] == "valid", outcome
    return w, pack


tf.before_financials = before_financials
try:
    w = tf.promoted_case(root)
    assert w.publish_model()["status"] == "ok"
    receipt = w.write_receipt(root / "receipt.json")
    verify_financial_slice_receipt(Execution(root / "store"), receipt, model_directory=root / "model")
    print("sealed and verified")
except Exception as e:  # reported, not hidden
    bad = 1
    print("SEAL/VERIFY FAILED", type(e).__name__, getattr(e, "code", e), " <-- FAIL")
print("EXIT", 1 if bad else 0)
sys.exit(1 if bad else 0)
