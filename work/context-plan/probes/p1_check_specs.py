"""G1 headline: which presets pass OwnerWorkflow._check_specs (and where they fail)."""
import datetime as dt, sys, tempfile, traceback
from pathlib import Path
from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owner_workflow as ow

passed = []
with tempfile.TemporaryDirectory() as tmp:
    for pathway in PATHWAY_MODULES:
        run = Run(run_id="r1", issuer_id="i1", issuer_name="I", as_of=dt.date(2026, 1, 1),
                  case_kind="synthetic", pathway=pathway)
        pack = PreparedPack(run=run, sources=())
        try:
            planned = ow._check_specs(pack, ow.OWNER_SPECS, Path(tmp) / f"pub-{pathway}", Path(tmp) / f"ex-{pathway}")
            passed.append(pathway)
            print(pathway, "PASS", planned)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)[-1]
            print(pathway, "REFUSED", type(e).__name__, e, f"at line {tb.lineno}")
print("passed:", passed)
sys.exit(0 if passed == ["distressed_restructuring"] else 1)
