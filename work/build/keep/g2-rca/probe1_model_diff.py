"""Probe 1: diff G2's delivered model/ files against (a) its own input publication and
(b) the separate financial run's publication. Read-only. Usage: python probe1_model_diff.py [pytest-dir]"""
import difflib, hashlib, json, sys
from pathlib import Path
P = Path(sys.argv[1] if len(sys.argv) > 1 else
         "/private/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/pytest-of-ericguei/pytest-2279")
T = P / "test_genuine_cp1_model_positiv0"
g2_out = T / "out/delivery/model"
g2_in = T / "inputs-positive-0/model"
fin_pub = P / "g2-cp1-model0/fin-positive/model"
fin_out = T / "financial-delivery/model"
rc = 0
for name in ("model.html", "calculation.json", "receipt.json"):
    files = {k: (d / name).read_bytes() for k, d in
             {"g2_out": g2_out, "g2_in": g2_in, "fin_pub": fin_pub, "fin_out": fin_out}.items()}
    print(name, {k: hashlib.sha256(v).hexdigest()[:12] for k, v in files.items()})
    print("  g2_out==g2_in:", files["g2_out"] == files["g2_in"],
          " fin_out==fin_pub:", files["fin_out"] == files["fin_pub"],
          " g2_out==fin_pub:", files["g2_out"] == files["fin_pub"])
    if files["g2_out"] != files["g2_in"]:
        rc = 1  # G2 delivery defect
    if files["g2_out"] != files["fin_pub"]:
        a, b = files["g2_out"].decode().splitlines(), files["fin_pub"].decode().splitlines()
        for line in difflib.unified_diff(a, b, "g2_out", "fin_pub", n=0, lineterm=""):
            print("   ", line[:200])
sys.exit(rc)
