"""Converted bytes per golden HTML source: R1 as written (script/style dropped only) vs also
dropping check.py's SKIP set (head, ix:header) and display:none. Exit 1 when R1 keeps
more than 1% extra hidden text on any source. Args: repo root, corpus root."""
import json, pathlib, sys
sys.argv, (repo, corpus) = sys.argv[:1], map(pathlib.Path, sys.argv[1:3])
import importlib.util
spec = importlib.util.spec_from_file_location("p2", pathlib.Path(__file__).with_name("p2_r1_conversion.py"))
src = spec.loader.get_source("p2").split("variants = {")[0].replace("repo, corpus = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])", "")
ns = {"repo": repo, "corpus": corpus}; exec(src, ns)
worst = 0.0
for case in sorted((repo / "cases/goldens").iterdir()):
    g = case / "module_golden.json"
    if not g.is_file(): continue
    for s in json.loads(g.read_text())["sources"]:
        p = corpus / s["file"]
        if p.suffix.lower() == ".pdf" or not p.is_file(): continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        a = len("\n".join(ns["lines"](raw, ns["R1_BLOCK"], {"script", "style"}, False)).encode())
        b = len("\n".join(ns["lines"](raw, ns["R1_BLOCK"], ns["chk"].SKIP, True)).encode())
        worst = max(worst, (a - b) / b)
        print(case.name, s["source_id"][:24], "R1", a, "hidden-dropped", b, f"extra {(a-b)/b:.1%}")
sys.exit(0 if worst <= 0.01 else 1)
