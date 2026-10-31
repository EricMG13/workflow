"""In-memory coverage-function examples only; no journal, settlement, or receipt."""
import hashlib, json
from datetime import date
from types import SimpleNamespace as N
from deploy_vii.contracts import Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.financial_contracts import FinancialReview
from deploy_vii.source_context import SourceContextReview
from deploy_workflow.financial_workflow import _evidence_issues
from deploy_workflow.workflow import SourceEvidence
from test_financial_workflow import make_pack


def check(start_month, wrong_amount=False, mismatch=None):
    text = 'CONSOLIDATED STATEMENTS OF CASH FLOWS\nSix Months Ended June 30,\n(In millions) | 2026 | 2025\nNet cash from operating activities | 600 | 500'
    digest=hashlib.sha256(text.encode()).hexdigest()
    citation=dict(source_id='filing', source_sha256=digest, locator='page:1', quote=text.splitlines()[-1])
    run=make_pack().run
    pack=PreparedPack(run=run, sources=(Source(source_id='filing',name='Interim statement',status='ready',sha256=digest,spans=(Span(locator='page:1',text=text),),extraction_status='complete'),))
    context=SourceContextReview.model_validate_json(json.dumps(dict(pack_sha256=pack.content_hash(),entities=[],sources=[dict(source_id='filing',classification='financial',document_type='Interim statement',published_on=None,evidence_class='unaudited_without_auditor',evidence_rationale='Unaudited',analytical_use='Historical cash flows',citations=[citation],event_scan_explanation='Not assessed')],limitations=[])))
    periods=[]
    lines=[]
    dimensions=dict(currency='USD',unit='MILLIONS',accounting_basis='US GAAP',entity_perimeter='consolidated')
    for year, amount in [(2026,600),(2025,500)]:
        start=date(year if start_month==1 else year-1,start_month,1); end=date(year,6,30)
        pid=f'ytd{year}'
        periods.append(dict(period_id=pid,period_type='YTD',fiscal_year=str(year),fiscal_quarter=2 if start_month==1 else 3,start_date=start.isoformat(),end_date=end.isoformat(),day_count=(end-start).days+1,audit_status='unaudited',citations=[citation],**dimensions))
        lines.append(dict(line_id='cashflows',statement='CFS',item_id='cfo_ncfo',label='Net cash from operating activities',period_id=pid,display_priority=1,line_kind='total',value=dict(observation_id=f'obs{year}',status='known',amount=str(amount+int(wrong_amount)),citations=[citation])))
    for line in lines:
        if mismatch == 'statement': line['statement'] = 'IS'
        if mismatch == 'label': line['label'] = 'A different label'
        if mismatch == 'citation': line['value']['citations'] = [{**citation, 'quote': 'Six Months Ended June 30,'}]
    disclosure=dict(status='not_disclosed',explanation='Not in this example',citations=[citation])
    book=dict(book_id='book',periods=periods,statement_lines=lines,accounts=[],addbacks=[],segments=[],kpis=[],facilities=[],pro_forma=[],segment_allocation=[],addback_disclosure=disclosure,segment_disclosure=disclosure,**dimensions)
    review=FinancialReview.model_validate_json(json.dumps(dict(pack_sha256=pack.content_hash(),run_id=run.run_id,issuer_id=run.issuer_id,as_of='2026-08-01',books=[book],analysis=[])))
    submission=FinancialSubmission.model_validate_json(json.dumps(dict(context_step_sha256='0'*64,financial=review.model_dump(mode='json'),definition=dict(financial_review_sha256=review.content_hash(),book_id='book'),binding=dict(financial_review_sha256=review.content_hash(),source_context_review_sha256=context.content_hash(),books=[dict(book_id='book',entity_id='issuer')]))))
    # Only the three read methods required by _evidence_issues; no persisted state is fabricated.
    store=N(read=lambda:N(attempts=(N(ticket_id='ticket',steps=(N(payload_sha256='context'),)),)),payload=lambda _:context.model_dump_json(),pack=lambda:pack)
    evidence=SourceEvidence(extracted=(('filing','page:1'),),searched=('filing',))
    return _evidence_issues(store,N(step_id='financials',ticket_id='ticket'),submission.model_dump_json(),evidence)

correct, wrong = check(1), check(10)
print('six-month correct coverage:', correct)
print('nine-month incorrect coverage:', wrong)
wa = check(10, True)
assert any('Uncovered extracted statement line:' in i for i in wa), wa  # control
for m in ('statement', 'label', 'citation'):
    assert any('Uncovered extracted statement line:' in i for i in check(10, mismatch=m)), m  # controls
assert correct == (), correct
# Desired: a 273-day YTD must not cover a "Six Months Ended" column.
assert any('Uncovered extracted statement line:' in i for i in wrong), 'H01 DEFECT: nine-month periods cover six-month source'
print('PASS')
