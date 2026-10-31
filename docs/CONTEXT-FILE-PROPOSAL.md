# Run context file (proposal)

Status: proposal, 2026-10-31. Nothing reads the context file yet. Changing `Run`
(`src/deploy_vii/contracts.py:82`) and adding module modes are the user's decisions
(AGENTS.md: shared interfaces and `src/deploy_vii` go to the user).

## Purpose

The user fills one **context form** (`docs/templates/context-form.html`) next to the
issuer's filings. It writes `context.json` (schema `context/1`), which gives the
modules what the filings cannot: run type, entity names, periods, market terms,
valuation choices, optional pinned assumptions and research questions.

## User rulings (2026-10-31)

1. The deal-type field is called **run type**.
2. **CP-DR sources public peers by default** so CP-1C can produce peer EV/EBITDA
   multiples that value a **private** issuer. For a **listed** issuer the user gives
   the issuer's own market figures in the context form. Valuation uses public trading
   multiples, web-sourced private-transaction multiples, or both, chosen by evidence
   quality and availability. The user may instead give their own peer comps or their
   own multiple.
3. The context file is an **HTML form**: easy to use, shows what each choice does,
   marks the default. It uses the deliverables' palette (`src/deploy_vii/assets/tokens.css`)
   with a different layout from the report shell.

## Four kinds of content

| Kind | Examples | Treatment |
|---|---|---|
| Run settings | run type, pathway, as-of, periods, currency, filing status | Map onto `Run`; steer the run; not cited |
| Evidence | price talk, quotes, ratings, issuer market data, user peer comps | Enters the pack as a hashed source; CP-0 classes it `third_party` (user-supplied); Python reads typed fields, never model-chosen quotes |
| Pinned assumptions | stress shocks, horizon, minimum cash, recovery %, EV multiple | Optional; replace the model's choice; labelled "user-supplied assumption" instead of "analyst assumption" |
| Steers | research questions | Data, never instructions to the model |

The context form supplies; the filings confirm. A name or term that conflicts with a
cited filing becomes an issue, never an override.

## Modules that need context

| Module | Context | Today (code) |
|---|---|---|
| CP-0 | Issuer/borrower names, run type | An unconfirmed issuer blocks every consumer (`readiness.py:419`) |
| CP-1 | Borrower, guarantor, restricted group names; as-of | Roles only from filings; missing role is a gap (`source_context.py:571`) |
| CP-1A | Sector, sponsor, transaction, use of proceeds | Cited rows only, else a gap |
| CP-1B | Current and prior period | Hard-coded per test `run_id` (`earnings_workflow.py:1655`) |
| CP-1C | Peers; issuer's name as written in the peer table | `peers` source; credit metrics only (margin, leverage, coverage, FFO/debt), **no EV/EBITDA** (`cp1c.py:158`) |
| CP-1D | Management or marketing EBITDA bridge | Optional `bridge` source |
| CP-2A | Stress sizes, watch levels | Model-chosen |
| CP-2D | Horizon, minimum cash, currency | Model-chosen; currency fixed USD |
| CP-2E | Rate/FX shocks, hedge ratio | Model-chosen |
| CP-2G | Forecast drivers, minimum liquidity | Model-chosen; LTM Q4 25 / FY2026-28 fixed |
| CP-2H | Agency ratings, outlooks, triggers | `ratings` source; parser fixed to the synthetic agency headers |
| CP-3 | Price talk or quotes, dated | Talk caps confidence below High; none gives Insufficient Information |
| CP-3B / CP-6A | Portfolio workbook | Aliases of CP-3 / CP-6; workbook not read yet |
| CP-3C | Repricing step-up, proposed terms | Model-chosen; market pricing not read |
| CP-3D | Quotes, recovery %, rate level | `market` source; recovery model-chosen |
| CP-4 | Run type (primary deals have drafts) | Executed or filed documents only |
| CP-4C | EV multiple, claim ranking | Model-chosen multiple, or "not assessed" |
| CP-8 | Prior decision (`prior_case`) | Required; absent blocks the module |
| CP-DR | Peer sourcing; user research questions | LOCAL gap research only |
| CP-L10 | Comparison periods | Four fixed 2025 quarters |

## Valuation design (ruling 2)

- **Private issuer (default):** CP-DR researches public peers (planned web mode) →
  CP-1C computes each peer's EV/EBITDA (new metric: needs peer EV, a new operand) →
  peer median multiple × issuer EBITDA (CP-1) gives an EV range. Optionally CP-DR also
  sources precedent private-transaction multiples.
- **Listed issuer:** the user gives market cap, net debt or EV, EBITDA basis, date and
  source in the form; Python computes the issuer's own EV/EBITDA.
- **Basis choice:** `auto` (default) uses each multiple set that has enough dated,
  comparable points, blends them when both qualify, uses one when only one does, and
  states Insufficient Information when none does. The thresholds (minimum count,
  maximum age, blend weights) are open questions, not decided here.
- **User overrides:** the user's own peer list, own peer comps table, or own multiple
  (with rationale). These replace the sourced set and are labelled user-supplied.
- **Consumers:** CP-4C's EV multiple (today model-chosen) and the credit snapshot.

## `context/1` shape

```json
{
  "schema": "context/1",
  "run": {"run_type": "research", "pathway": "credit_snapshot", "case_kind": "public",
          "as_of": "2026-10-31", "current_period": "q3-2026", "prior_period": "q2-2026",
          "reporting_currency": "USD"},
  "identity": {"issuer_name": "", "issuer_id": "", "borrower_name": "", "parent_name": "",
               "guarantors": [], "aliases": [], "listed_equity": false, "ticker": "",
               "sector": "", "country": "", "sponsor": ""},
  "deal_terms": [{"facility_id": "", "instrument": "", "currency": "USD", "size_m": "",
                  "tenor_years": "", "talk_spread_bps_low": "", "talk_spread_bps_high": "",
                  "talk_oid_low": "", "talk_oid_high": "", "floor_pct": "",
                  "call_protection": "", "use_of_proceeds": "", "as_of": "", "provider": ""}],
  "quotes": [{"facility_id": "", "kind": "observed", "bid": "", "ask": "", "price": "",
              "yield_pct": "", "spread_bps": "", "as_of": "", "provider": ""}],
  "ratings": [{"agency": "", "scope": "issuer", "rating": "", "outlook": "", "as_of": ""}],
  "valuation": {"peer_source": "cp_dr_public", "basis": "auto",
                "issuer_market": {"market_cap_m": "", "net_debt_m": "", "ev_m": "",
                                  "ebitda_basis": "LTM", "as_of": "", "source": ""},
                "peers": [{"name": "", "ticker": "", "ev_m": "", "ebitda_m": "",
                           "as_of": "", "source": ""}],
                "precedents": [{"target": "", "acquirer": "", "date": "", "ev_m": "",
                                "ebitda_m": "", "source": ""}],
                "user_multiple": {"value": "", "basis": "LTM", "rationale": ""}},
  "assumptions": {"cp2a": null, "cp2d": null, "cp2e": null, "cp3c": null,
                  "cp3d": null, "cp4c": null},
  "attachments": {"portfolio_workbook": false, "prior_case": false,
                  "management_bridge": false, "legal_documents": "executed"},
  "research_questions": [{"text": "", "focus_module": ""}]
}
```

Numbers are strings holding plain decimals (Python parses them as `Decimal`; empty
means not supplied, never zero). Money is in millions of the stated currency.

## Built today vs planned

Built: the form and its validation only. Planned, each needing its own lease:
`context.json` reader and `Run` mapping; CP-DR web peer and precedent sourcing (live
provider calls are paused); CP-1C EV/EBITDA; valuation basis selection; CP-1B period
pair from context; CP-4 draft-document mode; CP-DR user questions; pinned assumptions;
non-USD currency; real agency names in CP-2H; replacing `rv_quotes` with `quotes`.
