# CP-3 / CP-3D context market evidence oracle (Phase 3 Task 0)

Status: prepared, not reviewed, not frozen, not pinned. `cases/PINS.json` and `cases/pins.py` PATTERNS are changed
at the freeze step (the PATTERNS glob `cases/*-owner/*` matches manifest, submissions, expected and builder here but
not `contexts/*.json`: the freeze adds `cases/cp3-context-owner/contexts/*.json`).

Rebuild: `python3 -I cases/cp3-context-owner/builder/build.py` (stdlib only, twice byte-identical).

- `contexts/*.json`: the context files (`context/1`), the literal bytes of each pack's `context` source
  (`bad-bytes` is refused by `load_context` on purpose; the rest are accepted).
- `submissions.json`: the CP-3 submissions (R3 positive with `market_evidence: []` and `basis.context_rows`) and the
  model-side refusal mutations.
- `expected.json`: per case the Python rows, T3.3 facts, strength, own limitations, context block, cap issues; the CP-3D
  offered observations and refusals.
- `manifest.json`: run, pack sources, context sources and the sha256 of every output.
