"""Ruling 27: replays the 08c2eec model/ assertions (test_owner_rendering.py:697-714) on synthetic
publications, with the store ticket lists stubbed. Each wrong delivery must be refused."""
import json, sys, tempfile
from pathlib import Path

def pub(root, ticket, extra=""):
    root.mkdir(parents=True)
    (root / "model.html").write_bytes(b"<html>m</html>")
    (root / "calculation.json").write_bytes(b'{"x":1}')
    (root / "receipt.json").write_bytes(json.dumps({"ticket_id": ticket, "sha": "a" + extra}).encode())
    return root

def check(model, fin_model, destination, fin_destination, tickets):
    for name in ("model.html", "calculation.json", "receipt.json"):
        assert (destination / "model" / name).read_bytes() == (model / name).read_bytes()
        assert (fin_destination / "model" / name).read_bytes() == (fin_model / name).read_bytes()
    for name in ("model.html", "calculation.json"):
        assert (destination / "model" / name).read_bytes() == (fin_destination / "model" / name).read_bytes()
    receipts = []
    for owned, delivery in (("g2", destination), ("fin", fin_destination)):
        parsed = json.loads((delivery / "model" / "receipt.json").read_bytes())
        assert tickets[owned] == [parsed.pop("ticket_id")]
        receipts.append(parsed)
    assert receipts[0] == receipts[1]

r = Path(tempfile.mkdtemp())
model, fin_model = pub(r / "m", "t1"), pub(r / "fm", "t2")
tickets = {"g2": ["t1"], "fin": ["t2"]}
cases = {
    "honest": (pub(r / "d/model", "t1"), pub(r / "fd/model", "t2"), True),
    "G2 delivers financial publication": (pub(r / "d2/model", "t2"), pub(r / "fd2/model", "t2"), False),
    "receipt differs in another field": (pub(r / "d3/model", "t1", "b"), pub(r / "fd3/model", "t2"), False),
}
bad = 0
for name, (d, fd, ok) in cases.items():
    try:
        check(model, fin_model, d.parent, fd.parent, tickets); got = True
    except AssertionError:
        got = False
    print(name, "accepted" if got else "refused"); bad += got != ok
# own publication itself differs in a non-ticket field vs the financial one: refused at receipts compare
fm2 = pub(r / "fm2", "t2", "z")
try:
    check(model, fm2, pub(r / "d4/model", "t1").parent, pub(r / "fd4/model", "t2", "z").parent, tickets); print("non-ticket cross-run diff accepted"); bad += 1
except AssertionError:
    print("non-ticket cross-run diff refused")
sys.exit(1 if bad else 0)
