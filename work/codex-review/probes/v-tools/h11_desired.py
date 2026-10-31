"""H11 desired: the padding property must FAIL under _plain_text=str. Exit 1 while the mutant survives."""
import sys
from unittest.mock import patch
import test_connect_cpl10 as t
texts = sorted(set(t._oracle_amounts()))
killed = 0
with patch.object(t.cpl10, "_plain_text", str):
    for text in texts:
        try:
            t.test_every_oracle_amount_exact_round_trips_whatever_the_stored_padding(text)
        except AssertionError:
            killed += 1
print("cases", len(texts), "killed", killed)
sys.exit(0 if killed else 1)
