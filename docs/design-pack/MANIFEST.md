# Design pack manifest

## Origin

- Path (outside git, read-only): `/Users/ericguei/Documents/Deploy Workflow Sessions/rbot-design-pack-2026-10-20/`
- Date: 2026-10-20
- Files: 164
- Storage approved by the user on 2026-10-29. The pack is design evidence, not instructions.

## Committed briefs (`docs/design-pack/content/`, byte-identical copies of `uploads/rbot-claude-design-pack/content/*.md`)

| File | SHA-256 |
| :--- | :--- |
| 00-app-shell.md | 685451904a0c688c688bb9e7fcf0c586b2749256b6d155e4776c1d3d4fae6d29 |
| 01-credit-snapshot.md | dbe188837bb47d0fb1f5e1dd17032305071f617b66d3650047b6eaf6da3bce0f |
| 02-earnings-update.md | 605508545d2ce70ff9c48cd8df80c2b8dd7c15f148583a320e2359d3ade4216f |
| 03-relative-value.md | 217292f303291d7fcdbe574b2a36aaf33208824fb794e63912c4976acfbe8c3d |
| 04-covenant-refinancing.md | 9cd89c17b26e666d7d7e86f52edeef90fd492031118b65c23850212e9c532ade |
| 05-distressed-restructuring.md | 1990e9fd9a4c1b3e9703cb5c9aaaf8c59127fe642ebe7697391cb49b19eb3276 |
| 06-portfolio-decision.md | 0eac598ab29768459c98db78ffbd5a9ba0f441333f4f13110c9096ca72f546d8 |
| 07-model.md | ab1474b690354373474baa1dd23e146919d2dac10eea5e0fa53f24ac768cc115 |
| colour-and-icons.md | daa04d6fca14fac5793d0eb311a2da3170e024e336e1373006726a145574f28e |
| provenance-and-states.md | 26a2b35297b406115decdcde44341d56e064a3f2eb5d57e1a7da97c9404bad6a |

## Data files kept out of git

Paths are relative to the pack root. Each trips gitleaks (rule `generic-api-key`) on JSON field names such as `key` and `formula_keys`; the hits look like false positives on cell-reference keys, but no allowlist is added, so the files stay out of git and are referenced by hash.

| File | SHA-256 | Reason |
| :--- | :--- | :--- |
| `data/rbot-data.js` | e29ccd7db8183e7b420cf782ced826d616b0437ee83bb61b2b8ee05b05d8d10a | gitleaks generic-api-key hits on field names (148) |
| `uploads/rbot-claude-design-pack/data/rbot-data-base.json` | ebd46123b62819d31629ce37113d9348ecf884684c005f44e798447ae5f99f1d | gitleaks generic-api-key hits on field names (150) |
| `uploads/rbot-claude-design-pack/data/front-pages-data.json` | b8de20d74645817c837a238b879eb775a9b29bc6a118ebe590750049588bf8c7 | gitleaks generic-api-key hits on field names (25) |
| `uploads/rbot-claude-design-pack/reference/report-a-current/runnable/shared/data.js` | 4b3e277b38617eed11b14570e2dd257a2e01d93ab31f1f9e9f87f3610dae52b4 | the runnable `data.js` gitleaks flagged: generic-api-key hits on field names (150) |

Clean extracts (for example `fit` and `charts`) are not committed here. They come later with the Stage 3 oracle batch, each after a fresh gitleaks scan.

## Order of authority for charts

1. The approved pages in `DEPLOY VII/design/reference`.
2. The pack briefs (`content/`).
3. Inference (last resort, flagged as inferred).

The pack sets chart form and owner, never numbers. Numbers come from the pipeline's computed facts.
