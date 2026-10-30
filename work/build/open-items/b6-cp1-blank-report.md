# B6 report: CP-1 refuses a blank limitation (OI-14)

Branch claude/oi-b6-cp1-blank, from 9661c9d.

Commits:
- 84229e8 RED: tests/test_source_context_blank.py (16 failed, 8 passed, run by the controller)
- c34f81a fix: src/deploy_vii/source_context.py
- 7c8985f D12 record, wrongly placed in local_patch_lineage
- c7c1195 D12 record moved into post_import_patches (reason cites OI-14)
- the commit that adds this report

Fields covered in `validate_source_context`: entity.limitations, scope.limitations, source assessment limitations, review.limitations. Each blank gives one issue, `Empty limitation text: <entity_id | scope_id | source_id | review>`, with no echo of the input.

Not covered: the pack-side `source.limitation` and coverage limitations (`gap()` at about :437). They come from PreparedPack, which `validate_source_context` does not validate.

Parity: a stdlib scan of cases/**/*.json found no blank limitation in any frozen `cp1_source_context`. The test asserts it.

D12 probe: exit 0. prior sha d9fb02de -> d50e1bad, project_commit c34f81a.

Not verified: no project Python was run, so the GREEN, lint, type and fast gates are the controller's. The deferred files were not run.

agent=mx-feature fix-rounds=0 gates-first-pass=n
