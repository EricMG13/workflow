# O7b-1c S5 review

| | |
|---|---|
| Reviewer | mx-adversary afc0db61, read-only, independent of the S5 builder a8608a84 |
| Range | 312b2351..72d70067 (bcc39893, 14fb0c32, 72d70067). c6c0f783 leaves every S5 path byte-equal (p03). |
| Probes | `scratchpad/o7b1c-s5-review/probes/` (session scratchpad 9d206924) |
| Rulings | O7-R40 in `o7b1c-rulings.md` |

## Round 0: FIX (M1, L1-L4, I1-I3)

**M1 (Medium).** `src/deploy_vii/methods/cpdr.md:27` describes a cutoff set by the run context. No such cutoff exists.
- Every cutoff the code passes is the as-of date: `run_inputs.py:308`, `owners/cpdr.py:255` and `:368`.
- `context.py` has no cutoff field.
- Plan Q10 and O7-R19 put a context cutoff in O7b-2. The key has `#intake/cutoff == #intake/as_of`.
- p04(a): exit 1.

**L1 (Low).** `cpdr.md:32` says a refused item never reaches the dossier. In fact the dossier lists every refused item, with its locator, family, published date and reason, under `## Rejected items` (`research/dossier.py:171-181`, and the key's dossier `template_text`). It is the item's text that never reaches the pack, a prompt or the dossier. A terminator refusal shows `TERMINATOR_SHOWN` instead of its reason. p04(b): exit 1.

**L2 (Low).** `cpdr.md:3` says items are read "only through `search_pack` and `read_pages`". Under O7-R14 the research prompt carries every accepted item's full text in `UNTRUSTED_EVIDENCE` blocks (`owners/cpdr.py:504-525`, `prompts/compose.py:493-494`, `run_pathway.py:698`). The file's own line 33 says so. p08: exit 1.

**L3 (Low).** `tests/test_method_cpdr.py:162-172` pins the last record's prior sha and review path to S5. A correctly chained follow-up record (O7-R38 form) therefore fails at :172. p07: exit 1.

**L4 (Low, a ruling).** `cp1c.md:22`. No `ev-*` item reaches CP-1C at the tip:
- the H1 scope and `cp1c.SCOPE` exclude it;
- `_inputs` filters by SCOPE;
- the prompt pack block carries metadata only;
- no registry edge leads to CP-DR.

An `ev-*` item can, however, carry market data. "The pack" was already read as CP-1C's scoped sources before S5 (`host.py:102`). p05: exit 0.

**I1.** `cpdr.md:9` and `:61` name CP-1C and CP-2 as consumers, but no module reads CP-DR output before O7d.

**I2.** `test_shipped_maps_carry_cpdr_with_unchanged_slots` and `test_d12_record_carries_the_file_sha256` run `git show`, so they fail outside a git tree, as `test_g8` does. That explains the 11th RED failure on the controller's archive. CI checks out with `fetch-depth: 0`, so this has no CI impact. p03: exit 0.

**I3.** `project_commit` is checked by format only, and that is the single surviving mutant in p06. p01 checks it against git.

**Verified clean:**
- spec coverage, including the question-id bound of 138, which equals `steps.QUESTION_ID_MAX`;
- the labels equal `#cases/positive/tables/TDR.{1,2,3}/title`, and only the labels and the docstring changed (p02: exit 0);
- the D12 records:
  - P7-R4 is restored to 7d164d11;
  - the O7-R38 record matches field for field;
  - the cpdr.md and bindings/cpdr.py records have their prior, sha256 and commit verified;
  - the methodology chain is unbroken (p01: exit 0);
- the vii scope: two files, per-commit split, 312 lines, Sonnet trailers (p03: exit 0);
- the tests catch 19 of 20 mutants (p06: exit 0).

**Reviewer's runs:**
- test_method_cpdr: 11 passed;
- ruff, format and mypy: 0;
- scope `--role builder 312b2351 72d70067`: 0;
- pins: 0 (180);
- affected_tests selects test_method_cpdr.

**Not verified (reviewer):**
- tests/research and test_owner_cpdr (left to the controller's c6c0f783 archive);
- test_owner_rendering (HEAVY);
- the full suite;
- RED on a git checkout at 312b2351;
- complexipy, jscpd and bandit.

## Round 1 (scoped re-review, afc0db61): APPROVE
Commits 0e2843e8, b1598c22 and c5fec22e.

**Closed:**
- **M1.** `cpdr.md:27` now reads "The cutoff is the as-of date." p04(a): exit 0.
- **L1.** The refused-item text matches `dossier.py:171-181` and `_shown_reason`. p04(b): exit 0.
- **L2.** The research prompt carries each accepted item's text in its `UNTRUSTED_EVIDENCE` block. p08: exit 0.
- **I1.** "No module reads CP-DR output until O7d". p05: exit 0.
- **The chained record (c5fec22e)** is checked by p11 (exit 0):
  - prior bd5d5816, sha256 6f808d3e, `project_commit` b1598c22;
  - exactly one record was appended;
  - p01 still exits 0.
- **L3 and I3.** The test follows the chain from the S5 record, and all 20 p06 mutants are caught. p07 was rewritten for the real chain (exit 0); p12 exits 0.

**New:**
- **L5 (Low).** `tests/test_method_cpdr.py:226-227`: the `if _commit_exists(...)` guard skips the commit check for a commit that does not exist. That is a failure-hiding conditional and falls short of O7-R40 I3. Ruling (O7-R41): make it strict by deleting `_commit_exists` (`:180-187`), in the S6 end batch, checked against p09 (exit 1 now, 0 after).
- **I4 (Info).** `cpdr.md:3` says the tools are "the only way" to read the prepared sources. The run-context block, labelled "not a source and never cited", also reaches each prompt (`compose.py:483-488`). p10 exits 1 and is informational. No action (O7-R41).

**Reviewer's runs** (methodology.json clean before and after):
- test_method_cpdr: 11 passed;
- pins: 0 (180);
- ruff, format and mypy: 0.
