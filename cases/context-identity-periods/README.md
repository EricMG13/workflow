# Context identity and periods oracle (Phase 2 Task 0)

Status: prepared, not reviewed, not frozen, not pinned. `cases/PINS.json` and `cases/pins.py`
PATTERNS are changed at the freeze step; file hashes are recorded in `manifest.json`.

Rebuild: `python3 -I cases/context-identity-periods/builder/build.py` (stdlib only, twice byte-identical).

- `contexts/*.json`: the context files (`context/1`), the literal bytes of the `context` source.
- `sources/identity-b.json`: pack B's preparer-written identity source (adds the borrower line).
- `submissions-b.json`: the snapshot submissions with every identity citation re-cut.
- `overlays.json`: per-run `context` assessments (CP-0, CP-1) and pack B's borrower entity and scope.
- `expected.json`: reader problems, CP-1B, identity check, render, CP-L10 and form expectations,
  plus `inherited_gaps`.
- `manifest.json`: pack definitions, runs, sha256 of every output.

Packs: E (earnings sources, byte-identical), E-l10 (same sources, CP-L10 run), B (snapshot sources
with the new identity source). `ctx-research` is frozen with empty optional fields (see
`expected.json` `inherited_gaps`).
