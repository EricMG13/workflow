"""Lens A probe: rounding sites vs lease rules on half-way inputs (exit 1 on mismatch)."""
from decimal import Decimal as D
from fractions import Fraction
from deploy_workflow.owners import cp2d, cp3c, cpdr, cp3d, cpl10
bad = []
def chk(name, got, want):
    ok = got == want and str(got) == str(want)
    print(("OK  " if ok else "BAD ") + f"{name}: got {got!r} want {want!r}")
    if not ok: bad.append(name)
# CP-2D: max(0,start)/(-F/12), 1 dp half-up. start = cash+undrawn-min = 1; F=-48 -> 0.25 -> 0.3
st, r, m = cp2d._runway(annual=D(-48), cash=D(11), undrawn=D(0), minimum_cash=D(10))
chk("cp2d runway 0.25", m, D("0.3"))
st, r, m = cp2d._runway(annual=D(-6), cash=D(20), undrawn=D(0), minimum_cash=D(10))
chk("cp2d runway oracle fixture_burn", m, D("20.0"))
st, r, m = cp2d._runway(annual=D(-48), cash=D(11), undrawn=D(0), minimum_cash=None)
chk("cp2d runway missing min", (st, m), ("missing", None))
# CP-3C ratios stored 4 dp half-up
chk("cp3c r4 0.00025", cp3c._r4(D("0.00025")), D("0.0003"))
chk("cp3c r4 -0.00025", cp3c._r4(D("-0.00025")), D("-0.0003"))
# CP-DR answered share a/n 4 dp half-up: 1/32 = 0.03125 -> 0.0313
chk("cpdr share 1/32", cpdr._share(1, 32), D("0.0313"))
chk("cpdr share 2/3", cpdr._share(2, 3), D("0.6667"))
# CP-3D stored outputs quantised half-up
chk("cp3d q 0.125@2", cp3d._q(D("0.125"), 2), D("0.13"))
chk("cp3d q None", cp3d._q(None, 2), None)
# CPL10 38-digit half-even quotient
chk("cpl10 q38 1/3", cpl10._q38(Fraction(1, 3)), D("0." + "3" * 38))
chk("cpl10 q38 2/3", cpl10._q38(Fraction(2, 3)), D("0." + "6" * 37 + "7"))
raise SystemExit(1 if bad else 0)
