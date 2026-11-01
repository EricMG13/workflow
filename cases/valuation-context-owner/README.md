# Valuation from the context oracle (Phase 7 Task 0)

Status: prepared, not reviewed, not frozen, not pinned. `cases/PINS.json` and `cases/pins.py` PATTERNS are
changed at the freeze step (the `*-owner` globs already cover `manifest.json`, `expected.json` and
`builder/build.py`; `contexts/*.json` need a PATTERNS line).

Rebuild: `python3 -I cases/valuation-context-owner/builder/build.py` (stdlib only, twice byte-identical).

- `contexts/*.json`: the context files (`context/1`), the literal bytes of the `context` source, one per case.
- `expected.json`: per case, CP-1C T1C.9-T1C.11 (tables, facts with ids, statuses, shown texts, citations as
  `line:N` of the context file), statistics, selection, new limitations; CP-4C binding (EV, implied multiple,
  accepted and refused submissions, the added limitation); `rules` states every convention the oracle fixes.
- `manifest.json`: pinned inputs, packs, runs, sha256 of every output.

T1C.1-T1C.8 are not restated: they equal the frozen `cases/cp1c-owner` `no_peers` case (`positive` for
`credit-plus-comps`). Peer and precedent names are invented and labelled synthetic.
