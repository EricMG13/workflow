"""H04 desired behaviour: over-repayment refuses regardless of ambient Decimal precision,
no negative closing_debt settles, and sign reversal is exact. Exit 1 while defect present."""
import json, sys, tempfile
from pathlib import Path
from decimal import Context, Decimal, localcontext
import test_connect_cp2g as adapter
import test_method_cp2g as fixture
from deploy_workflow.owners import cp2g

failures = []
root = Path(tempfile.mkdtemp(prefix='adapter-', dir=sys.argv[1]))
store, pack, attempt = adapter.seed(root)
payload = fixture._bind_all(fixture._payload('positive'))
payload['base_drivers']['debt_repayment']['values'] = ['49.9999', '0.0002', '0']
text = json.dumps(payload)
sub = cp2g.ForwardSubmission.model_validate_json(text)
upstream = cp2g.cp2g_upstream(store=store, attempt=attempt)
issues_by_prec = {}
for precision in (28, 5):
    with localcontext(Context(prec=precision)):
        issues_by_prec[precision] = cp2g.validate_forward(pack=pack, submission=sub, upstream=upstream)
    print('validate_forward prec', precision, issues_by_prec[precision])
if not issues_by_prec[28]:
    failures.append('control: prec 28 did not refuse over-repayment')
if not issues_by_prec[5]:
    failures.append('prec 5 validate_forward returned no issues')
with localcontext(Context(prec=5)):
    done = cp2g.submit(store, attempt.ticket_id, cp2g.STEP_ID, text, None)
    print('submit prec 5', done.journal.status, done.journal.issues)
heads = [h for h in store.read().heads if h.module_id == 'CP-2G']
if heads:
    settled = store.head_module(heads[0])
    amt = next(f.amount for f in settled.facts if f.fact_id == 'T2H.5.b27.closing_debt')
    print('settled T2H.5.b27.closing_debt', amt)
    if amt is not None and amt < 0:
        failures.append(f'negative closing debt settled: {amt}')
else:
    print('no CP-2G head settled')

# unary negation
ctx = fixture._context('positive')
original = cp2g.select_cp1(ctx.cp1_facts)['cash_interest']
record = original.model_dump()
record['amount'] = Decimal('-1.234567890123456789012345678901')
modified = type(original).model_validate(record)
facts = tuple(modified if f.fact_id == modified.fact_id else f for f in ctx.cp1_facts)
for precision in (28, 60):
    with localcontext(Context(prec=precision)):
        got = cp2g.Operands.from_cp1(facts).interest.amount
    exp = modified.amount.copy_negate()
    print('interest prec', precision, 'actual', got, 'expected', exp)
    if got != exp:
        failures.append(f'negation rounded at prec {precision}: {got} != {exp}')
print('FAILURES', failures)
sys.exit(1 if failures else 0)
