"""Which realistic free/verbatim strings _carries_reference flags, and what resolve() does with
them against an empty module. Exit 1 if any free/verbatim string is flagged (the defect class)."""
import sys
from deploy_vii import prose
from deploy_vii.report_view import _carries_reference, resolve

CASES = [
    "Was the waiver granted after its end [sic]?",
    "Section 7.11 [Reserved].",
    "[Reserved]",
    "as defined in the Credit Agreement [1]",
    "the ratio of {a|b} in prose",
    "[Insufficient Information]",
    "the amount of [●] dollars",
    "see [Exhibit 10.1] attached",
    "Credit Agreement [Amended], p. 4",
]
flagged = 0
for text in CASES:
    hit = _carries_reference(text)
    outcome = "as written"
    if hit:
        flagged += 1
        try:
            resolve(text, {}, {})
            outcome = "resolved"
        except ValueError as e:
            outcome = "RAISES: " + str(e)[:90]
    print(f"{hit!s:5}  {text!r:50} {outcome}")
print("flagged:", flagged)
sys.exit(1 if flagged else 0)
