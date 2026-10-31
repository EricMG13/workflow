from decimal import Decimal
from unittest.mock import patch
import test_connect_cpl10 as t
seen=[]
with patch.object(t.cpl10,'_plain_text',lambda value: seen.append(str(value)) or str(value)):
    for text in sorted(set(t._oracle_amounts())):
        t.test_every_oracle_amount_exact_round_trips_whatever_the_stored_padding(text)
    # Independent requirement: lossless storage padding must not be exposed in the view.
    assert t.cpl10._plain_text(Decimal('17.50')) != '17.5'
print('All',len(set(t._oracle_amounts())),'parameter cases PASS with str(value) mutant')
print('Called representations before independent counterexample:',seen[:-1])
print('Independent counterexample: str(Decimal(17.50)) returns 17.50, expected 17.5')
print('set([Decimal(17.5), Decimal(17.50)]) cardinality:',len({Decimal('17.5'), Decimal('17.50')}))
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
with TemporaryDirectory(dir='/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-tools/legacy/evidence',prefix='padding-store-') as tmp:
    def mktemp(name):
        root=Path(tmp)/name
        root.mkdir()
        return root
    fixture=t.settled.__wrapped__(SimpleNamespace(mktemp=mktemp))
    store=next(fixture)
    t.test_view_is_the_oracle_tree(store)
    with patch.object(t.cpl10,'_plain_text',str):
        try:
            t.test_view_is_the_oracle_tree(store)
        except AssertionError:
            print('Refutation/control: sibling test_view_is_the_oracle_tree KILLS str(value) mutant')
        else:
            raise AssertionError('sibling oracle did not kill mutant')
    fixture.close()
