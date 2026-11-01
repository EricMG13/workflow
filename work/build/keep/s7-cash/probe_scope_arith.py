"""Recompute both NCF_CASH_MOVEMENT checks from the printed filing lines, under the
current formula (BS cash only) and under the CFS's printed cash scope (cash + restricted
cash + restricted/escrow cash in other long-term assets). Exits 1 if any quoted line is
not found verbatim. Usage (repo root): python3 -I <this>"""
import sys
from pathlib import Path
D = Path("cases/czr-2026q2-earnings-update/documents")
K, Q = (D / "CZR_FY2025_10K.txt").read_text(), (D / "CZR_Q2_2026_10Q.txt").read_text()
need = {
    K: ["Decrease in cash, cash equivalents and restricted cash | (32) | (127) | (160)",
        "Cash and cash equivalents | $887 | $866 | $1,005", "Restricted cash | 85 | 95 | 122",
        "Restricted and escrow cash included in other long-term assets, net | 12 | 55 | 16",
        "Total cash, cash equivalents and restricted cash | $984 | $1,016 | $1,143"],
    Q: ["Increase in cash, cash equivalents and restricted cash | 93 | 70",
        "Cash and cash equivalents | $965 | $887", "Restricted cash | 96 | 85",
        "Restricted and escrow cash included in other long-term assets, net | 16 | 19",
        "Total cash, cash equivalents and restricted cash | $1,077 | $1,086"],
}
bad = [(s) for txt, ss in need.items() for s in ss if s not in txt]
for s in bad: print("NOT FOUND:", s)
fy = dict(ncf=-32, cash=(887, 866), rc=(85, 95), lt=(12, 55))
h1 = dict(ncf=93, cash=(965, 887), rc=(96, 85), lt=(16, 12))  # 12 = 10-K FY2025 column
for name, p in (("fy-2025", fy), ("h1-2026", h1)):
    cur = p["cash"][0] - p["cash"][1]
    scope = sum(a - b for a, b in (p["cash"], p["rc"], p["lt"]))
    print(name, "reported", p["ncf"], "current-formula", cur, "diff", cur - p["ncf"],
          "| scope-formula", scope, "diff", scope - p["ncf"],
          "| restricted delta", p["rc"][0] - p["rc"][1], "LT delta", p["lt"][0] - p["lt"][1])
sys.exit(1 if bad else 0)
