from common import *
from deploy_vii.statement_extract import extract_statement_lines
from collections import defaultdict

# (source, page, statement, [period ids per value column])
TABLES = [
    (Q, 2, "BS", ["bs-2026-06-30", "bs-2025-12-31"]),
    (K, 54, "BS", ["bs-2025-12-31", "bs-2024-12-31"]),
    (Q, 4, "IS", ["q2-2026", "q2-2025", "h1-2026", "h1-2025"]),
    (R, 6, "IS", ["q2-2026", "q2-2025", "h1-2026", "h1-2025"]),
    (K, 56, "IS", ["fy-2025", "fy-2024", "fy-2023"]),
    (Q, 9, "CFS", ["h1-2026", "h1-2025"]),
    (K, 60, "CFS", ["fy-2025", "fy-2024", "fy-2023"]),
]
ITEM = {
    "BS": {
        "Cash and cash equivalents": "cash_and_equivalents", "Restricted cash": "restricted_cash",
        "Accounts receivable, net": "trade_receivables", "Inventories": "inventory",
        "Prepayments and other current assets": "other_current_assets", "Total current assets": "total_current_assets",
        "Property and equipment, net": "ppe_net", "Goodwill": "goodwill", "Intangible assets other than goodwill": "other_intangibles",
        "Other long-term assets, net": "other_noncurrent_assets", "Total assets": "total_assets",
        "Accounts payable": "trade_payables", "Accrued other liabilities": "other_current_liabilities",
        "Current portion of long-term debt": "current_portion_long_term_debt", "Total current liabilities": "total_current_liabilities",
        "Other long-term liabilities": "other_noncurrent_liabilities", "Total liabilities": "total_liabilities",
        "Caesars stockholders’ equity": "shareholders_equity", "Caesars stockholders' equity": "shareholders_equity",
        "Noncontrolling interests": "minority_interests", "Total stockholders’ equity": "total_equity",
    },
    "IS": {
        "Net revenues": "revenue", "Total operating expenses": "opex_including_da",
        "Depreciation and amortization": "depreciation_amortization", "Operating income": "ebit",
        "Loss before income taxes": "pretax_income", "Net loss": "net_income", "Net income (loss)": "net_income",
    },
    "CFS": {
        "Net loss": "net_income", "Net income (loss)": "net_income",
        "Net cash provided by operating activities": "cfo_ncfo", "Purchase of property and equipment": "capex_total",
        "Net cash used in investing activities": "investing_cash_flow", "Net cash used in financing activities": "financing_cash_flow",
        "Increase in cash, cash equivalents and restricted cash": "net_cash_change",
        "Decrease in cash, cash equivalents and restricted cash": "net_cash_change",
        "Cash, cash equivalents and restricted cash, beginning of period": "opening_cash",
        "Cash, cash equivalents and restricted cash, end of period": "closing_cash",
        "Proceeds from long-term debt and revolving credit facilities": "debt_issuance",
        "Repayments of long-term debt and revolving credit facilities": "debt_repayment",
        "Repurchase of common stock": "equity_buybacks", "Cash paid for asset acquisitions": "acquisitions",
        "Proceeds from sale of property and equipment": "disposals",
        "Proceeds from sale of property, equipment, trademark and businesses": "disposals",
    },
}
MAGNITUDE = {("IS", "opex_including_da"), ("IS", "depreciation_amortization")}
SUBTOTAL = {"revenue", "ebit", "pretax_income", "net_income", "cfo_ncfo", "investing_cash_flow", "financing_cash_flow", "net_cash_change"}

def slug(text, n=70):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n].strip("-")

NIL = "The statement prints an em dash (nil) for this cell; no amount is stated, and zero is not asserted"

def build_lines():
    """statement lines for the book: one per (line key, period), merged across documents."""
    lines = {}      # (stmt, key) -> dict
    order = defaultdict(int)
    obs = {}        # (line_id, period) -> {amount, cites}
    used_item = {}  # (period, stmt, item) -> line_id
    for src, page, stmt, periods in TABLES:
        text = PAGES[src][page - 1]
        tbl = extract_statement_lines(text, f"page:{page}", source_id=src)
        raw = text.split("\n")
        counts = defaultdict(int)
        for l in tbl.lines:
            counts[l.label] += 1
        for l in tbl.lines:
            assert len(l.values) == len(periods), (src, page, l.label)
            suffix = ("-" + slug(l.caption, 20)) if counts[l.label] > 1 else ""
            key = (l.label, suffix)
            if (stmt, key) not in lines:
                order[stmt] += 1
                base = f"{stmt.lower()}-{slug(l.label)}{suffix}"
                while any(e["line_id"] == base for e in lines.values()):
                    base += "-b"
                lines[(stmt, key)] = {"line_id": base, "stmt": stmt, "label": l.label, "priority": order[stmt], "item": ITEM[stmt].get(l.label)}
            ent = lines[(stmt, key)]
            line_text = raw[l.line_no - 1]
            assert l.label in line_text
            for period, value in zip(periods, l.values):
                o = obs.setdefault((ent["line_id"], period), {"amount": value, "cites": [], "stmt": stmt, "ent": ent})
                assert o["amount"] == value, (ent["line_id"], period, o["amount"], value)
                c = (src, page, line_text)
                if c not in o["cites"]:
                    o["cites"].append(c)
    # unique ids
    ids = [e["line_id"] for e in lines.values()]
    assert len(ids) == len(set(ids)), "line id collision"
    # canonical item uniqueness per (period, statement, item): the first line keeps it; a line that
    # loses in any period keeps an issuer id in every period (one definition per line id)
    loser = set()
    for (lid, period), o in obs.items():
        ent = o["ent"]
        if ent["item"]:
            k = (period, ent["stmt"], ent["item"])
            if used_item.setdefault(k, lid) != lid:
                loser.add(lid)
    for (lid, period), o in obs.items():
        ent = o["ent"]
        o["item_final"] = ent["item"] if (ent["item"] and lid not in loser) else "other:" + lid
    # an item id must be the same for one line_id in all periods (metadata): resolve per line
    per_line = {}
    for (lid, period), o in obs.items():
        per_line.setdefault(lid, set()).add(o["item_final"])
    for lid, items in per_line.items():
        assert len(items) == 1, (lid, items)
    return lines, obs

def line_kind(stmt, label, item):
    if label.startswith("Total"):
        return "total"
    if item in SUBTOTAL:
        return "subtotal"
    return "detail"

def cite_tuple(c):
    return cite(c[0], c[1], c[2])

def statement_lines():
    lines, obs = build_lines()
    res = []
    for (lid, period), o in obs.items():
        ent = o["ent"]
        item = o["item_final"]
        cites = [cite_tuple(c) for c in o["cites"]]
        if o["amount"] is None:
            value = {"observation_id": f"{lid}--{period}", "status": "not_applicable", "amount": None, "citations": cites, "reason": NIL}
        else:
            value = {"observation_id": f"{lid}--{period}", "status": "known", "amount": str(o["amount"]), "citations": cites}
        row = {"line_id": lid, "statement": ent["stmt"], "item_id": item, "label": ent["label"], "period_id": period,
               "display_priority": ent["priority"], "line_kind": line_kind(ent["stmt"], ent["label"], item), "value": value}
        if (ent["stmt"], item) in MAGNITUDE:
            row["sign_convention"] = "outflow_magnitude"
            row["sign_citations"] = cites
        res.append(row)
    return res

def periods():
    def per(pid, ptype, fy, fq, s, e, days, audit, hdr, pres, lim=None):
        return {"period_id": pid, "fiscal_year": fy, "fiscal_quarter": fq, "period_type": ptype, "start_date": s, "end_date": e,
                "day_count": days, "audit_status": audit, "citations": hdr,
                "expense_presentation": "by_function" if pres else "unknown", "presentation_citations": pres or [], "limitation": lim}
    k_is = [cite(K, 56, "Years Ended December 31,"), cite(K, 56, "(In millions, except per share data) | 2025 | 2024 | 2023")]
    k_pres = [cite(K, 56, "OPERATING EXPENSES:")]
    q_hdr = [cite(Q, 4, "Three Months Ended June 30, | Six Months Ended June 30,"), cite(Q, 4, "(In millions, except per share data) | 2026 | 2025 | 2026 | 2025"),
             cite(R, 6, "Three Months Ended June 30, | Six Months Ended June 30,")]
    q_pres = [cite(Q, 4, "OPERATING EXPENSES:")]
    bs_k = [cite(K, 54, "December 31,"), cite(K, 54, "(Dollars in millions, except par value) | 2025 | 2024")]
    bs_q = [cite(Q, 2, "(In millions) | June 30, 2026 | December 31, 2025")]
    pe = "Point-in-time balance sheet date, not a duration"
    return [
        per("fy-2023", "FY", "2023", None, "2023-01-01", "2023-12-31", 365, "audited", k_is, k_pres),
        per("fy-2024", "FY", "2024", None, "2024-01-01", "2024-12-31", 366, "audited", k_is, k_pres),
        per("fy-2025", "FY", "2025", None, "2025-01-01", "2025-12-31", 365, "audited", k_is, k_pres),
        per("q2-2025", "QUARTER", "2025", 2, "2025-04-01", "2025-06-30", 91, "unaudited", q_hdr, q_pres),
        per("q2-2026", "QUARTER", "2026", 2, "2026-04-01", "2026-06-30", 91, "unaudited", q_hdr, q_pres),
        per("h1-2025", "YTD", "2025", 2, "2025-01-01", "2025-06-30", 181, "unaudited", q_hdr, q_pres),
        per("h1-2026", "YTD", "2026", 2, "2026-01-01", "2026-06-30", 181, "unaudited", q_hdr, q_pres),
        per("bs-2024-12-31", "PERIOD_END", "2024", None, None, "2024-12-31", None, "audited", bs_k, None, pe),
        per("bs-2025-12-31", "PERIOD_END", "2025", None, None, "2025-12-31", None, "audited", bs_k + bs_q, None, pe),
        per("bs-2026-06-30", "PERIOD_END", "2026", None, None, "2026-06-30", None, "unaudited", bs_q, None, pe),
    ]

def disclosures(lines):
    heads = {
        ("IS", "fy"): cite(K, 56, "CONSOLIDATED STATEMENTS OF OPERATIONS"), ("CFS", "fy"): cite(K, 60, "CONSOLIDATED STATEMENTS OF CASH FLOWS"),
        ("IS", "int"): cite(Q, 4, "CONSOLIDATED CONDENSED STATEMENTS OF OPERATIONS"), ("CFS", "int"): cite(Q, 9, "CONSOLIDATED CONDENSED STATEMENTS OF CASH FLOWS"),
        ("BS", "k"): cite(K, 54, "CONSOLIDATED BALANCE SHEETS"), ("BS", "q"): cite(Q, 2, "CONSOLIDATED CONDENSED BALANCE SHEETS"),
    }
    have = {(l["statement"], l["period_id"]) for l in lines}
    res = []
    for (stmt, period) in sorted(have):
        if period.startswith("fy"):
            h = heads[(stmt, "fy")]
        elif period.startswith("bs-2026"):
            h = heads[("BS", "q")]
        elif period.startswith("bs"):
            h = heads[("BS", "k")]
        else:
            h = heads[(stmt, "int")]
        res.append({"statement": stmt, "period_id": period, "disclosure": {
            "status": "complete", "explanation": "Every printed data line of the statement page is retained as a statement line; lines the page does not print are not stated", "citations": [h]}})
    return res

def stage():
    lines = statement_lines()
    rel_addback = cite(R, 7, line_of(R, 7, "RECONCILIATION OF NET INCOME")) if False else None
    book = {
        "book_id": "consolidated",
        "periods": periods(),
        "accounts": [], "addbacks": [], "segments": [], "kpis": [], "facilities": [], "pro_forma": [],
        "statement_lines": lines,
        "statement_identities": [],
        "statement_disclosures": disclosures(lines),
        "cash_movement_bridges": [], "balance_movements": [], "balance_movement_bridges": [],
        "segment_allocation": [],
        "addback_disclosure": {"status": "partial", "explanation": "The release and the annual report print an Adjusted EBITDA reconciliation, but this book carries no add-back schedule and no Adjusted EBITDA account, so no adjusted metric is built from it",
                               "citations": [cite(R, 3, "The reconciliation of net income (loss) attributable to Caesars to Adjusted EBITDA is attached at the end of this press release.")]},
        "segment_disclosure": {"status": "partial", "explanation": "Segment net revenues are printed in the release and the management discussion, but this book carries no segment schedule",
                               "citations": [cite(R, 1, "Net Revenues")]},
        "limitations": [
            "Per-share lines are U.S. dollars per share and share counts are millions of shares; the book unit MILLIONS applies to dollar amounts only.",
            "Cells the statements print as an em dash are recorded as not applicable with a reason, not as zero.",
            "No debt facility rows, add-backs, segment schedule or KPI schedule are submitted in this book; the debt note is read by later modules.",
        ],
    }
    sub = {
        "financial": {"run_id": czr_runs.RUN_ID, "issuer_id": "CZR", "as_of": "2026-10-02", "books": [book], "analysis": [],
                      "limitations": ["Statements are taken from the three filed documents only; nothing is restated or adjusted."]},
        "definition": {"book_id": "consolidated", "assessments": [], "events": [],
                       "limitations": ["No metric definition is assessed: the book carries no Adjusted EBITDA and no covenant definition is in the pack."]},
        "binding": {"books": [{"book_id": "consolidated", "entity_id": "issuer"}]},
    }
    calls = [{"tool": "extract_statements", "arguments": {"source_id": s, "locators": [f"page:{p}" for p in pgs]}}
             for s, pgs in ((Q, (2, 4, 9)), (K, (54, 56, 60)), (R, (6,)))]
    calls += [{"tool": "read_pages", "arguments": {"source_id": R, "first_page": p, "last_page": p}} for p in (1, 3)]
    return {"step": "financials", "calls": calls, "submission": sub}
