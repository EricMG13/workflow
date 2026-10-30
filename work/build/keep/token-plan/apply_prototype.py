"""Apply the recommended rule to the scratch tree copy only (argv[1] = tree root)."""
import sys
from pathlib import Path

root = Path(sys.argv[1])
rv = root / "src/deploy_vii/report_view.py"
s = rv.read_text()
old = s[s.index("def _carries_reference(text: str) -> bool:"):s.index("def _token_runs(")]
new = '''# Text facts a producer composes as run text, by (module id, table id). CP-8 writes its
# what-changed lines from its own claims and keeps an unsettled figure as a gap chip for the page
# to resolve (``cp8._resolved``). Every other known text fact is shown as written, whatever
# brackets it holds: analyst free text and verbatim source text are not run text.
_RUN_TEXT_TABLES: frozenset[tuple[str, str]] = frozenset({("CP-8", "cp8.what_changed")})


def _carries_reference(module_id: str, fact: Fact) -> bool:
    """Whether a known text fact is producer-composed run text that holds reference syntax.

    Only a table in ``_RUN_TEXT_TABLES`` holds run text. There, any ``{}[]`` sends the text to
    ``resolve``, which fails closed on a malformed or foreign reference. Anywhere else the text
    is shown as written (``[sic]``, ``[Reserved]``, ``[Insufficient Information]``).
    """
    return (
        (module_id, fact.table_id) in _RUN_TEXT_TABLES
        and fact.text is not None
        and prose._RESERVED.search(fact.text) is not None  # the characters resolve() parses
    )


'''
s = s.replace(old, new)
s = s.replace("                if _carries_reference(fact.text):", "                if _carries_reference(module.module_id, fact):")
rv.write_text(s)
rd = root / "src/deploy_vii/render.py"
t = rd.read_text()
a = 'if fact.status == "known" and fact.text is not None and _carries_reference(fact.text):'
assert a in t
t = t.replace(a, 'if fact.status == "known" and _carries_reference(module.module_id, fact):')
rd.write_text(t)
print("patched")
