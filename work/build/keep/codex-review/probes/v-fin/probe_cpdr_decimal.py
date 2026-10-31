"""Nondefault-context hypothesis only: not claimed to occur in the supported default CLI.
No product code sets global precision (static rg result in report); public caller scope below
explicitly changes it. Positive controls are default 28 and the precision-4 boundary.
"""
import json
import tempfile
from decimal import localcontext
from pathlib import Path
import cpdr_runs as r

OUT = Path('/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-fin/cpdr')
results = {}
for precision in (28,4,3):
    root = Path(tempfile.mkdtemp(prefix='decimal-',dir=OUT/'tmp'))
    wf, pack = r.start(root)
    r.replay(wf,r.calls_of('partial'))
    entry = {}
    try:
        with localcontext() as ctx:
            ctx.prec = precision
            entry['outcome'] = wf.submit_review(r.literal('partial'))
    except Exception as exc:
        entry['error'] = {'type':type(exc).__name__,'message':str(exc)}
        attempt = next(a for a in wf._store.read().attempts if a.module_id == 'CP-DR')
        entry['after_error'] = {'attempt_status':attempt.status,'steps':[s.status for s in attempt.steps]}
        try:
            entry['retry'] = wf.submit_review(r.literal('partial'))
        except Exception as retry_exc:
            entry['retry_error'] = {'type':type(retry_exc).__name__,'message':str(retry_exc)}
    results[str(precision)] = entry
assert results['28']['outcome']['status'] == 'valid'
assert results['4']['outcome']['status'] == 'valid'
assert 'error' not in results['3'] and results['3']['outcome']['status'] == 'valid', results['3']
(OUT/'cpdr-decimal-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
