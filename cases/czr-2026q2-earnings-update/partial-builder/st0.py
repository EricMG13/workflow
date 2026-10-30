from common import *

def stage():
    k1 = cite(K, 1, "For the fiscal year ended December 31, 2025")
    k1b = cite(K, 1, "Commission File No. 001-36629")
    k51 = cite(K, 51, "In our opinion, the financial statements present fairly, in all material respects, the financial position of the Company as of December 31, 2025 and 2024")
    q1 = cite(Q, 1, "For the quarterly period ended June 30, 2026")
    q1b = cite(Q, 1, "Commission File No. 001-36629")
    r1 = cite(R, 1, "Caesars Entertainment, Inc. Reports Second Quarter 2026 Results")
    r1b = cite(R, 1, "Consolidated Adjusted EBITDA of $920 million versus $955 million for the comparable prior-year period.")
    q33 = cite(Q, 33, "The pending Merger may have significant effects on us, including, among others, the significant diversion of management and employee attention from ordinary course matters.")
    r3 = cite(R, 3, "Due to the Company’s pending definitive agreement to be acquired by Fertitta Entertainment, Inc. announced on May 28, 2026, Caesars will not be hosting a quarterly conference call.")
    conv = "The documents are text conversions of the filings: tables are pipe-delimited lines and the pages are cut by the case page rule, not the printed pagination."
    rows = [
        ("CP-1", "Located historical statements for the quarter, six months and fiscal year, with filing dates, scope and units",
         [K, Q, R], "The three filings carry the balance sheets, statements of operations and statements of cash flows that the historical financial foundation extracts.",
         [k1, q1, r1], ["The quarterly statements are unaudited; the pack holds no auditor report on them.", conv]),
        ("CP-1A", "Located business, operating, ownership and transaction facts with quotes",
         [K, Q, R], "The annual report business section and the quarterly report overview and merger note describe operations, segments, leases and the pending Merger.",
         [k1, q1, q33], ["Business facts come from filing text and carry the filing's own limitations; the pending Merger has not closed.", conv]),
        ("CP-2", "Settled CP-1 figures and CP-1A registers for a historical credit synthesis",
         [K, Q, R], "A historical synthesis can run on settled upstream registers; the pack holds no forecast, peer or covenant document, so the synthesis stays historical and limited.",
         [k1, q1, r1b], ["No forecast, guidance, peer or market data is in the pack.", "No credit agreement, indenture or lease document is in the pack; terms come only from filing summaries.", "The Merger with Fertitta Entertainment, Inc. is pending."]),
        ("CP-5", "Settled upstream modules and the debt table of the quarterly report for an integrity review",
         [K, Q, R], "The integrity review can compare upstream claims with the located debt table and statements; it inherits every upstream limitation.",
         [q1, k1, r1b], ["Face-value and book-value debt come from the quarterly report debt note only.", "The Merger with Fertitta Entertainment, Inc. is pending and its effect on the debt is not determinable from the pack."]),
    ]
    consumers = []
    for mod, demand, sids, rationale, cites, limits in rows:
        consumers.append({"module_id": mod, "readiness": "READY_WITH_LIMITATIONS", "evidence_demand": demand,
                          "source_ids": sids, "rationale": rationale, "citations": cites, "missing_source": None, "limitations": limits})
    sub = {
        "pack_sha256": PACK,
        "objective": "Historical credit review of Caesars Entertainment, Inc. after the second quarter of 2026: financial foundation, business context, credit synthesis and integrity review",
        "reporting_period": "Quarter and six months ended June 30, 2026, with the fiscal year ended December 31, 2025 as the audited baseline",
        "issuer_confirmed": True,
        "sources": [
            {"source_id": K, "document_family": "Annual report on Form 10-K", "authority": "filed",
             "entity": "Caesars Entertainment, Inc.", "period": "Fiscal year ended December 31, 2025",
             "version_relationship": "Original annual report with an unqualified audit opinion; the audited baseline for the quarterly report",
             "fidelity": "verified", "citations": [k1, k1b, k51], "limitations": [conv]},
            {"source_id": Q, "document_family": "Quarterly report on Form 10-Q", "authority": "filed",
             "entity": "Caesars Entertainment, Inc.", "period": "Quarter and six months ended June 30, 2026",
             "version_relationship": "Interim report signed July 28, 2026 that updates the annual report",
             "fidelity": "verified", "citations": [q1, q1b], "limitations": ["Interim statements are unaudited and the pack holds no auditor report on them.", conv]},
            {"source_id": R, "document_family": "Earnings release (Exhibit 99.1)", "authority": "issuer",
             "entity": "Caesars Entertainment, Inc.", "period": "Quarter and six months ended June 30, 2026",
             "version_relationship": "Same-day issuer release of the unaudited results; the Form 10-Q is the controlling filing",
             "fidelity": "verified", "citations": [r1, r1b], "limitations": ["Unaudited; Adjusted EBITDA and net debt are non-GAAP measures defined by the issuer.", conv]},
        ],
        "consumers": consumers,
        "gaps": [
            {"gap_id": "no-forecast", "kind": "scope", "severity": "material",
             "description": "The pack holds no forecast, guidance or projected financials, so no forward credit metric can be sourced.",
             "affected_modules": ["CP-2"], "remediation": "Add an issuer or sponsor projection document before any forward-looking module runs.", "citations": [r3]},
            {"gap_id": "no-peer-data", "kind": "source", "severity": "material",
             "description": "The pack holds no peer, market-price or trading-level data.",
             "affected_modules": ["CP-2"], "remediation": "Add a peer set and pricing source before any relative-value module runs.", "citations": []},
            {"gap_id": "no-debt-documents", "kind": "scope", "severity": "material",
             "description": "No credit agreement, indenture, lease agreement or covenant certificate is in the pack; debt, guarantor and restricted-group terms are known only from filing summaries.",
             "affected_modules": ["CP-2", "CP-5"], "remediation": "Add the executed debt and lease documents before any covenant or legal module runs.", "citations": []},
            {"gap_id": "pending-merger", "kind": "scope", "severity": "material",
             "description": "The pending Merger with Fertitta Entertainment, Inc. has not closed; its closing, financing and effect on the capital structure cannot be determined from the pack, and all figures are pre-closing.",
             "affected_modules": ["CP-1", "CP-1A", "CP-2", "CP-5"], "remediation": "Refresh the pack after closing or termination of the Merger.", "citations": [q33, r3]},
        ],
        "analysis": [
            {"claim_id": "source-assessment",
             "text": "The pack holds three documents of one registrant: the audited annual report for the fiscal year ended December 31, 2025, the unaudited quarterly report for the period ended June 30, 2026 and the same-day earnings release. They locate the historical statements, the debt note and the business description that the selected modules need.",
             "citations": [k1, q1, r1], "limitation": "Only these three documents are in the pack; every conclusion is limited to them."},
            {"claim_id": "pending-merger-limit",
             "text": "The registrant is party to a pending merger agreement, so the filings describe a company that has not yet closed the transaction and the issuer gives no earnings call.",
             "citations": [q33, r3], "limitation": "The outcome and any effect on the capital structure are not determinable from the pack."},
        ],
    }
    reads = [(K, 1), (K, 51), (Q, 1), (Q, 33), (R, 1), (R, 3)]
    calls = [{"tool": "read_pages", "arguments": {"source_id": s, "first_page": p, "last_page": p}} for s, p in reads]
    return {"step": "source_readiness", "calls": calls, "submission": sub}
