#!/bin/zsh
# Lens A sweeps over 9f71bfa (run from the lane root). Prints hit counts per pattern.
F=(src/deploy_workflow/owners/ src/deploy_workflow/liquidity_series.py src/deploy_workflow/restructuring_series.py src/deploy_workflow/financial_series.py)
for p in 'float(' 'math.' 'round(' 'suppress(' 'or 0' 'Decimal(0)' 'except Exception' 'except BaseException' 'except:' 'TODO' 'NotImplemented'; do
  print -- "$p: $(git grep -nF -- "$p" 9f71bfa -- $F | wc -l)"
done
print -- "except (all): $(git grep -nwE 'except' 9f71bfa -- $F | wc -l)"
print -- ".get(..., 0|Decimal): $(git grep -nE '\.get\([^)]*, *(0|Decimal|_ZERO)\b' 9f71bfa -- $F | wc -l)"
print -- "sum(: $(git grep -nF 'sum(' 9f71bfa -- $F | wc -l)"
