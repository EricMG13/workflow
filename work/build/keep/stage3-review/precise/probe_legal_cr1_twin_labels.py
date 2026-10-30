"""Probe: tests/test_legal_render.py::test_cr1_covenant_headroom_figure_matches_oracle never checks
the CR.1 table-twin row labels (cr1_builder_target: "each row label starts with label_parts[0] and
contains each later label_parts entry in order"). Every twin row label is replaced with "WRONG"
(and the companions dropped); the test still passes. Exit 0 = defect reproduced.
Run from s3-i4: PYTHONPATH=src:tests:. python <this file>"""
import sys

import test_legal_render as t

real = t._report


def forged(view, maps=t.SHIPPED_MAPS):
    report = real(view, maps)
    blocks = []
    for b in report.blocks:
        if b.figures:
            figs = []
            for f in b.figures:
                twin = f.chart.table_twin
                rows = tuple(r.model_copy(update={"label": "WRONG"}) for r in twin.rows)
                chart = f.chart.model_copy(update={"table_twin": twin.model_copy(update={"rows": rows})})
                figs.append(f.model_copy(update={"chart": chart}))
            b = b.model_copy(update={"figures": tuple(figs)})
        blocks.append(b)
    return report.model_copy(update={"blocks": tuple(blocks)})


t._report = forged
passed = 0
for case in (0, 1):
    try:
        t.test_cr1_covenant_headroom_figure_matches_oracle(case)
        print(f"case {case}: forged twin labels ACCEPTED")
        passed += 1
    except AssertionError as e:
        print(f"case {case}: refused {e!r}"[:200])
sys.exit(0 if passed == 2 else 1)
