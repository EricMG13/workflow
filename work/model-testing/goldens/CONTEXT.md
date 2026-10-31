# Stage: public-issuer goldens (gap layer)

**Purpose.** Answer keys used to judge whether a live model run populated the deliverable accurately, for six real issuers, one per pathway. Codex's reviewed financial goldens (`public-financial-gold/1`) supply the CP-1 history. This stage builds what they lack:
- a context file per issuer;
- module-level facts for the pathway's modules beyond CP-1.

User rulings (2026-10-31): "build goldens now"; "Reuse + fill gaps (Recommended)"; every test run must use the context form.

## Inputs
| Layer | File | Section | Why |
|---|---|---|---|
| L3 | `/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1/<ISSUER>/` | all | Primary SEC sources (sha256 in `../manifest.csv`, all verified). The **only** evidence you may cite |
| L3 | `git show 5325c209:docs/CONTEXT-FILE-PROPOSAL.md` | "context/1 shape", "Modules that need context" | Shape of `context.json` and which modules read which fields |
| L3 | `git show 5325c209:docs/templates/context-form.html` | `build()` (:721-806) and the rule checks near :651 | Normative rules for `context.json` (enums, number format, dates) |
| L3 | `src/deploy_vii/contracts.py:36-71` | `PathwayId`, `_PRESETS` | Modules requested per pathway |
| L3 | `/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1-codex-gold-20261031/<issuer>/financial_gold.json` | `periods`, `cutoff` | Period ids and the cutoff to align with. **Do not copy its values; module facts must come from the sources** |
| L4 | `work/model-testing/goldens/briefs/<issuer>.md` | all | Per-issuer scope |

## Process
1. Read the brief. List the pathway's modules and what each needs from the filings.
2. Extract facts from the primary sources only. To read HTML, write throwaway stdlib scripts in your scratch directory (`python3 -I`). Never cite a source dated after the cutoff.
3. Record every fact in `module_golden.json` (schema below), with evidence a checker can re-find.
4. Compute any derived value with a small stdlib Python script, `derive.py`, kept in the case directory. It prints the receipt and uses exact `Decimal`. No arithmetic by hand or by model.
5. Write `context.json` (context/1) from the filings. Fields the filings cannot supply stay empty (`""`, `[]` or `null` as the shape says) and are listed in `needs_user_input`. Never invent market data, peers, ratings, holdings or a prior decision.
6. Self-check every quote with the normalisation below. Write `prepare-report.md` ending with a `Not verified:` line.

**Visible-text normalisation** (the checker uses exactly this):
- parse with stdlib `html.parser`;
- drop text inside `script`, `style`, `head`, `ix:header`, and any element whose `style` contains `display:none`;
- unescape entities; map NBSP (U+00A0) and other Unicode spaces to a space;
- insert a space at the start and end of every block-level tag (`td`, `th`, `tr`, `p`, `div`, `br`, `li`, and the full list in `cases/goldens/check.py` `BLOCK`). Inline tags add nothing, so `(`, `1,234` and `)` in separate spans read as `(1,234)`;
- collapse every whitespace run to one space; strip.
- **Run the checker on your case before returning:** `python3 -I cases/goldens/check.py cases/goldens/<case_id>`. It must exit 0.
- A quote must be a substring of the resulting document text. A table row normally reads `Label $ 1,234 $ 1,111`.

## Outputs (only in `cases/goldens/<case_id>/`; touch nothing else)
- **`context.json`.** Schema `context/1`, exactly the proposal's shape and the form's rules:
  - numbers are plain decimal strings, empty means not supplied;
  - `case_kind` is `"public"`; `as_of` is the cutoff date;
  - periods are `q[1-4]|h[12]|fy-YYYY` in the issuer's fiscal labelling, stated in the report.
- **`module_golden.json`.** Schema `module-golden/1`:
  ```json
  {"schema_version": "module-golden/1", "case_id": "", "issuer_id": "", "pathway": "",
   "cutoff": "YYYY-MM-DD", "context_file": "context.json",
   "financial_gold": {"path": "<abs path of the Codex snapshot file>", "sha256": ""},
   "sources": [{"source_id": "", "file": "<path under artifacts/public-corpus/v1>", "sha256": "",
                "url": "", "form": "", "period_end": "", "filed": ""}],
   "facts": [{"fact_id": "<MODULE>.<topic>.<subject>.<field>[.<period_end>]",
              "module": "CP-2", "topic": "debt_stack", "subject": "Term loan Tranche J",
              "field": "principal_outstanding", "period_end": "YYYY-MM-DD or null",
              "status": "known|missing|conflicting|not_applicable",
              "value": "decimal string, text, or ISO date; null unless known",
              "value_type": "decimal|text|date|percent|bps",
              "unit": "USD|percent|bps|null", "scale": "millions|units|null",
              "evidence": [{"source_id": "", "locator": "Note 8 Debt > table > row > column",
                            "quote": "exact normalised visible text, <= 300 chars",
                            "printed": "the value as printed, e.g. (1,234) or 4.75%"}],
              "derivation": null,
              "gap_reason": null}],
   "not_golden": [{"module": "", "why": ""}],
   "needs_user_input": [{"context_path": "", "modules": [""], "why": ""}],
   "limitations": [], "preparer": "<your agent id>"}
  ```
  `derivation` is `{"op": "sum|difference|negate|product|ratio", "operands": ["fact_id", ...], "script": "derive.py"}`.
  - Non-derived known facts need at least one `evidence` entry whose `quote` contains `printed`.
  - `missing` needs a `gap_reason` and a null `value`.
  - `conflicting` lists each source in `evidence` and keeps `value` null.
  - Units and scale stay as printed. Do not rescale.
- **`derive.py`.** Only if anything is derived.
- **`prepare-report.md`.** What was covered per module, judgment calls, period labelling, open questions, and a `Not verified:` line.

## Rules
- **No stub or fake values.** No catch-all that hides a failure.
- **Missing stays missing.** Zero is a value; zero is never missing.
- **Keep the distinctions:**
  - loan commitment vs funded balance;
  - borrower vs listed parent;
  - principal vs carrying amount;
  - fair value vs quote.
- **Judgment modules** (CP-5, CP-6, CP-MODEL, CP-2A stress choices) go in `not_golden` with the reason. CP-1 goes in `not_golden` as "covered by financial_gold".
- **Do not commit.** The controller commits. Do not edit any other path.
