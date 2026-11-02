# O7b-2 S5 review (mx-adversary a07e4091), 81695d13..3f19109e

Probes: `scratchpad/o7b2-s5-review/probes/`. Rulings: O7-R56.

## Round 0: FIX (M-1)
The two-line edit is clean:
- both lines equal the key;
- the D12 chain holds: after 6f808d3e, `project_commit` 3415f682 holds 3f361350…, and the tip equals it;
- B1 holds: only cpdr.md lines 27-28 moved;
- the S5 test is RED on the old text, GREEN on the new, and kills m1-m3 (p01, p03).

**Findings:**
- **M-1.** `cpdr.md:3`, "No web, provider or credential is used", contradicts the new line 28 (p02).
- **L-1.** `cpdr.md:26` says each item names a file; an admitted web item names a url (p02).
- **L-2.** Plan row 27's node id does not exist (p04). The controller corrected it.
- **L-3.** Line 28 describes S3/S4 behaviour that is not built yet. Release hold; S6 re-runs p02.
- **I-1.** The claims hold against S1 and S2: "the same byte cap", the five recorded fields, https only, public addresses, three redirects, line 31 against H2.
- **I-3.** O7b-1c's p11 is out of date.
- **I-4.** The locator fence must be checked before the fetch (goes to S3).

Not verified (reviewer): the O7b-1c p04 and p08 ran over a working tree holding S3's uncommitted edits; the S3/S4 claims await those stages.

## Round 1 (ff43668e, ce918beb, 61e33570, 4a5b379a): APPROVE
- M-1 and L-1 are fixed.
- The key's `#method/sentences[2]` and `[3]` equal O7-R56 exactly. It rebuilds byte-identically, and only the two pins moved.
- Lines 3 and 26 swap only the ruled clauses.
- The test is RED before the fix, GREEN after, and catches reverts.
- The chain 14fb0c32 → b1598c22 → 3415f682 → 61e33570 is unbroken, and the file at HEAD equals the tip (06322fe0…).
- p01 (re-pointed), p02 (check 2 narrowed to "names a file, a family") and p05 (new, 40 checks) exit 0.

Not verified (reviewer): the O7b-1c p04 and p08 against the new line 3; p02's AHEAD lines (S3/S4). The L-3 release hold stands.

**S5 is complete, under the L-3 hold.**
