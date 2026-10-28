<!-- Draft of src/deploy_vii/methods/cp2a.md (documentation, D12). Lands at LEAD freeze. LEAD adaptation per ruling Q2; no r14 CP-2A text exists in the repo. -->
# CP-2A Downside pathway: method (LEAD adaptation, draft)

Purpose (methodology.json): what breaks first and how far it falls. CP-2A is a static, single-period stress of one CP-1 base period, computed in Python from settled CP-1 facts. The analyst chooses the base period, the scenarios, the shock sizes and the watch levels (labelled analyst assumptions, uncited; confidence is never High).

## What it computes
- Stressed EBITDA `E(1-s)`, cash interest `I(1+k)`, free cash flow `F - E s - I k`, total and net leverage, interest coverage, FCF to debt (T2B.3, T2B.4), with an unstressed control row s00 reconciled to CP-1's reported ratios (T2B.5).
- Break points: the EBITDA decline at which FCF reaches zero, EBITDA stops covering cash interest, and each analyst watch level is reached (T2B.6), ranked first to last (T2B.7), and each scenario set against each break (T2B.8).
- Ratios are calculable only where CP-1 itself has a twelve-month basis; CP-2A never annualises a quarter. Zero, missing, not applicable and blocked stay distinct.

## What is held or left out (each recorded as an own limitation)
1. **Liquidity.** Stressed free cash flow is not set against cash or any undrawn facility; no runway or liquidity break is computed (CP-2D).
2. **Debt and cash in the period.** Debt and cash are held at the base closing balances; net leverage does not move with stressed free cash flow; no forward path (CP-2G).
3. **Covenant tests.** Watch levels are not covenants; covenant compliance and headroom are CP-4's.
4. **Maturities and refinancing walls.** Not stressed (CP-2D, CP-3C).
5. **Working capital, capex, tax response.** Held at the base period; no tax shield.
Also stated: break points hold cash interest at base (no interest increase), and the EBITDA-equals-interest break is gated like a ratio; a metric not calculable under a scenario shows Not calculable even where its break lies below that decline.

## Tables
T2B.1 scenarios, T2B.2 base operands, T2B.3 stressed flows, T2B.4 stressed metrics, T2B.5 reconciliation, T2B.6 break points, T2B.7 ranking, T2B.8 scenario against break, T2B.9 gaps; `cp1_references` carries the CP-1 facts the prose names. T5.1-T5.7 stay CP-5's (D8).

## Review challenge (ruling Q2)
The independent review must challenge this adaptation against methodology.json's purpose; the static slice is defensible for a first owner (ranking and required decline are answered) but defers the forward path to CP-2G.
