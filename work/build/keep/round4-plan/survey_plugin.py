"""pytest plugin (survey only): records every text checked by prose.issues / valid_syntax
(RunText) with the calling module, and every known text Fact built, with its building module.
At session end writes a JSON summary to $SURVEY_OUT."""
import json, os, sys
from collections import defaultdict
import deploy_vii.prose as prose

VALIDATED = defaultdict(set)   # text -> {caller module}
RUNTEXT = set()
FACTS = {}                     # (builder, table_id, field) -> list of sample texts
RES = defaultdict(list)        # (builder, table_id, field) -> texts holding reserved chars
HIT = defaultdict(list)        # (builder, table_id, field) -> validated-by callers


def _caller(skip):
    f = sys._getframe(2)
    while f is not None:
        name = f.f_globals.get("__name__", "")
        if name not in skip and not name.startswith(("pydantic", "typing", "functools")):
            return name
        f = f.f_back
    return "?"


_issues, _vs = prose.issues, prose.valid_syntax


def issues(text, *a, **k):
    VALIDATED[text].add(_caller({"deploy_vii.prose", __name__}))
    return _issues(text, *a, **k)


def valid_syntax(value):
    RUNTEXT.add(value)
    return _vs(value)


prose.issues, prose.valid_syntax = issues, valid_syntax
import deploy_vii.contracts as contracts  # noqa: E402  (after the patch: RunText binds the wrapper)

Fact = contracts.Fact
_init = Fact.__init__


def _record(fact, builder):
    if fact.status != "known" or fact.text is None:
        return
    key = (builder, fact.table_id, fact.field)
    FACTS.setdefault(key, []).append(fact.text)
    if prose._RESERVED.search(fact.text):
        RES[key].append(fact.text)


SKIP = {"deploy_vii.contracts", __name__, "deploy_vii.registry"}


def __init__(self, *a, **k):
    _init(self, *a, **k)
    _record(self, _caller(SKIP))


Fact.__init__ = __init__
_mc = Fact.model_copy


def model_copy(self, *a, **k):
    out = _mc(self, *a, **k)
    if (k.get("update") or {}).get("text") is not None:
        _record(out, _caller(SKIP))
    return out


Fact.model_copy = model_copy


def pytest_sessionfinish(session, exitstatus):
    out = {}
    for key, texts in FACTS.items():
        val = set()
        for t in set(texts):
            if t in VALIDATED and len(t) > 12:
                val |= VALIDATED[t]
        run = sum(1 for t in set(texts) if t in RUNTEXT and len(t) > 12)
        out["|".join(key)] = {
            "n": len(texts),
            "validated_by": sorted(val - {"deploy_vii.report_view"}),
            "equals_runtext": run,
            "reserved": sorted(set(RES.get(key, [])))[:3],
        }
    tok = defaultdict(int)
    for t, callers in VALIDATED.items():
        if prose._TOKEN.search(t):
            for c in callers:
                tok[c] += 1
    out["__validated_with_token__"] = dict(tok)
    with open(os.environ["SURVEY_OUT"], "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
