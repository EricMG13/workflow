"""Apply the round 4 registry change to a tree copy (argv[1]); exits 1 if the anchor is absent."""
import sys
from pathlib import Path
p = Path(sys.argv[1]) / "src/deploy_vii/report_view.py"
s = p.read_text()
old = '_RUN_TEXT_TABLES = frozenset({("CP-8", "cp8.what_changed")})'
new = '''_RUN_TEXT_FIELDS = frozenset(
    {
        ("CP-8", "cp8.what_changed", "value"),
        ("CP-L10", "TL10.3", "assessment"),
        ("CP-L10", "TL10.3", "credit_transmission"),
        ("CP-2H", "T2R.10", "gap"),
        ("CP-2H", "T2R.10", "why_it_matters"),
        ("CP-2H", "T2R.10", "affected_analysis"),
        ("CP-2H", "T2R.10", "action"),
    }
)'''
old2 = "(module_id, fact.table_id) in _RUN_TEXT_TABLES"
new2 = "(module_id, fact.table_id, fact.field) in _RUN_TEXT_FIELDS"
if old not in s or old2 not in s:
    sys.exit(1)
p.write_text(s.replace(old, new).replace(old2, new2))
