import json
from pathlib import Path
from czr_runs import make_pack
from deploy_vii.statement_extract import extract_statement_lines, _NUMERIC_CELL
G = json.loads(Path("tests/czr_extract_golden.json").read_text())
pack = make_pack()
for e in G:
    s = next(s for s in pack.sources if s.source_id == e["source_id"])
    t = next(x.text for x in s.spans if x.locator == e["locator"])
    tab = extract_statement_lines(t, e["locator"], e["source_id"])
    print(e["source_id"], e["locator"], "lines", len(tab.lines), "omitted", len(tab.omitted))
    for o in tab.omitted: print("   ", o.line_no, repr(o.text[:110]))
for tok in ["-", "---", "—", "–"]:
    print(repr(tok), bool(_NUMERIC_CELL.fullmatch(tok)))
sep = extract_statement_lines("Label | 2025 | 2024\n- | - | -\n--- | --- | ---\nCash | 1 | 2", "p")
print(sep.headers, [l.label for l in sep.lines], sep.omitted)
