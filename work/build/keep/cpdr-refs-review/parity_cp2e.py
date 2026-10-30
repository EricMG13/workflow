"""Probe: CP-DR answer rule vs cp2e.run_text on a token corpus (post-fix code). For each text:
CP-DR issues from _model_text_issues (path stripped) == cp2e Issues.run_text messages. Also: a
malformed answer gives only RunText lines; no line echoes the input. Exit 0 = parity holds."""
import copy, json, sys
from pathlib import Path
ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from deploy_workflow.owners import cpdr, cp2e
import test_method_cpdr as t

texts = ["plain text", "Rates {fact_a|x} up", "Rates {fact_a} up", "See [fact_a] here",
         "See [G1] here", "Rates [a lot", "Rates {} up", "Rates {f| } up", "x]y", "[" + "a"*300 + "]",
         "SECRETTOKEN [fact_zz", "{fact_a|%}", "[fact_a][fact_b]"]
fail = 0
for text in texts:
    payload = copy.deepcopy(t.SUBMISSIONS["cpdr"]["partial"])
    payload["gaps"][0]["questions"][0]["answer"] = text
    d = [i.split(": ", 1)[1] for i in cpdr._model_text_issues(t.submission(payload))
         if i.startswith("gaps[0].questions[0].answer")]
    iss = cp2e.Issues() if hasattr(cp2e, "Issues") else None
    got = []
    class Rec:
        def add(self, line): got.append(line)
    cp2e_cls = [v for v in vars(cp2e).values() if isinstance(v, type) and hasattr(v, "run_text")][0]
    rec = Rec()
    cp2e_cls.run_text(rec, "P", text)
    e = [g.split(": ", 1)[1] for g in got]
    ok = d == e and not any("SECRETTOKEN" in x or "fact_a" in x for x in d)
    if text.startswith("SECRET") or "[a lot" in text:
        ok = ok and "text carries a reference" not in d
    print("OK " if ok else "BAD", repr(text[:30]), d)
    fail |= not ok
sys.exit(1 if fail else 0)
