import sys
from pathlib import Path as _P
sys.path[:0] = [str(_P.cwd() / "src"), str(_P.cwd() / "tests")]
"""CP-1 quality's read body is a JSON object; CP-5 facts are nested and carry no unit."""
import inspect

import czr_runs
from pydantic import BaseModel
from deploy_vii.cp1_quality import QualityInputs
from deploy_vii.contracts import Fact
from decimal import Decimal
from deploy_workflow import financial_workflow

src = inspect.getsource(financial_workflow._projection)
assert "inputs.model_dump_json()" in src
assert issubclass(QualityInputs, BaseModel)
print("quality body = QualityInputs.model_dump_json() -> _read_body gives",
      type(czr_runs._read_body({"body": '{"scope": {}}'})).__name__)

fact = Fact(fact_id="f1", label="Revenue", table_id="T1", period="Q2 26",
            amount=Decimal(2900), unit="USD", scale=Decimal(1000000))
cp5_body = {"modules": [{"module_id": "CP-1", "facts": [{"ref": "f1", "shown": "$2,900"}]}]}
sel = {"module_id": "CP-1", "table_id": "T1", "period": "Q2 26", "label": "Revenue",
       "unit_token": "USD_M", "spelled": "$2,900"}
try:
    czr_runs.bind_stage_figures("{{FIG:rev}}", {"rev": sel}, cp5_body, lambda m: (fact,))
    print("CP-5 shape bound")
except RuntimeError as e:
    print("CP-5 shape:", e)
