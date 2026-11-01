Offline runs are included: their costs are computed from recordings, not money.

# Model comparison report

## earnings_update (shc-earnings-update)

| Module | sol-medium | opus-medium |
| --- | --- | --- |
| CP-0 | PASS 1/1 · $0.40 · 1.7k tok · 10 s | FAIL 3/4 · $1.01 · ≥2.7k tok · 40 s |
| CP-1 | PASS 4/4 (1 inherited) · $0.27 · ≥12.0k tok · 32 s | PASS 2/2 · $0.50 · ≥3.9k tok · 30 s |
| CP-1B | FAIL 3/4 · $2.00 reserved · n/r tok · 3 s | — |
| CP-5 | PASS 2/2 · $0.05 · 0.5k tok · 5 s | PASS 1/3 (2 refused) · $0.20 · ≥0.2k tok · 8 s |

## Totals

| Config | Accuracy | Cost (live) | Cost (offline, computed) | Tokens | Median wall time | Retries |
| --- | --- | --- | --- | --- | --- | --- |
| sol-medium | 90.9% (10/11) | $2.72 reserved | $0.00 | ≥14.2k tok | 50 s | 1 |
| opus-medium | 66.7% (6/9) | $0.00 | $1.71 | ≥6.8k tok | 78 s | 0 |

## Faults by class

### product (0)

### prompt (2)

- f1 · shc-earnings-update · CP-1B · sol-medium · fix — · rerun: none
- f2 · shc-earnings-update · CP-1B · sol-medium · fix abc123 · rerun: passed

### harness (0)

### model (1)

- f3 · shc-earnings-update · CP-0 · sol-medium · fix — · rerun: failed

## Accounts

| Account | Spend (live runs) | Usable | Remaining |
| --- | --- | --- | --- |
| openai | $2.72 | $117.00 | $114.29 |
| anthropic | $0.00 | $135.00 | $135.00 |
| openrouter | $0.00 | $18.00 | $18.00 |
