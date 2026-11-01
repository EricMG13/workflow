"""T5 third-fix re-review probe q1 (read-only; direct SourceSession use, as the verifiers do).
Steps {source_readiness, source_context, financials} x names {offered tools, "", "foo",
"shell", near-misses, str subclass, int, unencodable str} x arguments {good, deep(105),
surrogate value, surrogate key, non-dict, nan, tuple, empty}. Each case: good call, the
case call, good call on one host; then a fresh SourceSession.from_execution on the same
store and step replays every receipt as invoke(tool, json-roundtripped arguments).
Also checks offers(n) == (stage(n, {}) is not refused not_permitted) for every str name.
argv[1] == "mutant-true"/"mutant-false" patches offers to a constant (the probe must then fail).
Exit 1 on any escape, desync, replay mismatch or offers/stage disagreement."""
import json, sys, tempfile
from pathlib import Path
import test_source_tools as t
from deploy_workflow import host
from deploy_workflow.tools.source import SourceTools, SourceError

if sys.argv[1:] == ["mutant-true"]:
    SourceTools.offers = lambda self, name: True
elif sys.argv[1:] == ["mutant-false"]:
    SourceTools.offers = lambda self, name: False


class S(str):
    pass


def deep(n):
    v = []
    for _ in range(n):
        v = [v]
    return v


STR_NAMES = ["search_pack", "read_pages", "extract_statements", "", "foo", "shell",
             "SEARCH_PACK", "search_pack ", "search_pack\x00", "extract_statements\n"]
NAMES = [(n, n) for n in STR_NAMES] + [
    ("S(search_pack)", S("search_pack")), ("S(extract)", S("extract_statements")),
    ("S('')", S("")), ("int5", 5), ("unenc", "search_pack\ud800"), ("unenc_ext", "extract_statements\ud800")]
ARGS = {
    "good_search": lambda: {"query": "Synthetic"},
    "good_extract": lambda: {"source_id": "fin", "locators": ["page:2"]},
    "empty": lambda: {},
    "deep": lambda: {"query": "x", "extra": deep(105)},
    "surr_val": lambda: {"query": "\ud800"},
    "surr_key": lambda: {"\ud800": 1},
    "non_dict": lambda: [1],
    "nan": lambda: {"query": "x", "n": float("nan")},
    "tuple": lambda: {"query": "x", "n": (1,)},
}
GOOD = ("search_pack", {"query": "Synthetic"})
pack = t.pack.__wrapped__()
bad = 0


def strip(r):
    r = dict(r)
    r.pop("call_id")
    return r


for step in ("source_readiness", "source_context", "financials"):
    for label, name in NAMES:
        for ak, make in ARGS.items():
            for memo in ("_CP1_VERIFIED", "_PARSED_PACKS"):
                getattr(host, memo, {}).clear()
            h, store, ticket = t.session(Path(tempfile.mkdtemp(prefix="t5q1-")), pack, step)
            assert h._binding["step_id"] == step
            try:
                recs = [h.invoke(*GOOD), h.invoke(name, make()), h.invoke(*GOOD)]
            except BaseException as e:  # reported, not hidden
                bad = 1
                print(f"{step:16} {label:22} {ak:12} ESCAPED {type(e).__name__}  <-- FAIL")
                continue
            if [r["sequence"] for r in recs] != [1, 2, 3] or recs[2]["status"] != "ok":
                bad = 1
                print(f"{step:16} {label:22} {ak:12} DESYNC  <-- FAIL")
                continue
            fresh = host.SourceSession.from_execution(store, ticket, step)
            mism = []
            for r in recs:
                rr = json.loads(json.dumps(r))
                rep = fresh.invoke(rr["tool"], rr["arguments"])
                if strip(rep) != strip(rr):
                    mism.append((r["sequence"], (r["tool"], r["status"], r["error_code"]),
                                 (rep["tool"], rep["status"], rep["error_code"])))
            r1 = recs[1]
            line = f"{step:16} {label:22} {ak:12} {(r1['tool'][:20], r1['status'], r1['error_code'], r1['arguments'] == {})}"
            if mism:
                bad = 1
                print(line, "MISMATCH", mism, " <-- FAIL")
            else:
                print(line, "REPLAYS")
    # offers vs stage's own offered check
    h, _, _ = t.session(Path(tempfile.mkdtemp(prefix="t5q1o-")), pack, step)
    for n in STR_NAMES + ["read_pages\ud800"[:-1]]:
        try:
            h._tools.stage(n, {})
            code = "ok"
        except SourceError as e:
            code = e.code
        agree = h._tools.offers(n) == (code != "not_permitted")
        bad |= not agree
        print(f"{step:16} offers({n!r}) = {h._tools.offers(n)} stage(n, {{}}) -> {code} {'AGREE' if agree else 'DISAGREE <-- FAIL'}")
print("EXIT", 1 if bad else 0)
sys.exit(1 if bad else 0)
