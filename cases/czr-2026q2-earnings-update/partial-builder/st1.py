from common import *

DIMS = {"currency": "USD", "unit": "MILLIONS", "entity_perimeter": "Caesars Entertainment, Inc. and its consolidated subsidiaries", "accounting_basis": "US GAAP"}

def scope(sid, label, kind, start, end, cites):
    return {"scope_id": sid, "entity_id": "issuer", "period_label": label, "period_kind": kind,
            "start_date": start, "end_date": end, **DIMS, "citations": cites}

def stage():
    k_fy_hdr = [cite(K, 56, "Years Ended December 31,"), cite(K, 56, "(In millions, except per share data) | 2025 | 2024 | 2023")]
    k_pe_hdr = [cite(K, 54, "December 31,"), cite(K, 54, "(Dollars in millions, except par value) | 2025 | 2024")]
    q_ops = [cite(Q, 4, "Three Months Ended June 30, | Six Months Ended June 30,"), cite(Q, 4, "(In millions, except per share data) | 2026 | 2025 | 2026 | 2025")]
    q_bs = [cite(Q, 2, "(In millions) | June 30, 2026 | December 31, 2025")]
    r_ops = [cite(R, 6, "Three Months Ended June 30, | Six Months Ended June 30,"), cite(R, 6, "(In millions, except per share data) | 2026 | 2025 | 2026 | 2025")]
    k_scopes = [
        scope("k-fy2025", "FY2025", "historical_duration", "2025-01-01", "2025-12-31", k_fy_hdr),
        scope("k-fy2024", "FY2024", "historical_duration", "2024-01-01", "2024-12-31", k_fy_hdr),
        scope("k-fy2023", "FY2023", "historical_duration", "2023-01-01", "2023-12-31", k_fy_hdr),
        scope("k-pe-2025-12-31", "Balance sheet at December 31, 2025", "period_end", None, "2025-12-31", k_pe_hdr),
        scope("k-pe-2024-12-31", "Balance sheet at December 31, 2024", "period_end", None, "2024-12-31", k_pe_hdr),
    ]
    def flows(prefix, hdr):
        return [
            scope(f"{prefix}-q2-2026", "Q2 2026 (three months ended June 30, 2026)", "historical_duration", "2026-04-01", "2026-06-30", hdr),
            scope(f"{prefix}-q2-2025", "Q2 2025 (three months ended June 30, 2025)", "historical_duration", "2025-04-01", "2025-06-30", hdr),
            scope(f"{prefix}-h1-2026", "H1 2026 (six months ended June 30, 2026)", "historical_duration", "2026-01-01", "2026-06-30", hdr),
            scope(f"{prefix}-h1-2025", "H1 2025 (six months ended June 30, 2025)", "historical_duration", "2025-01-01", "2025-06-30", hdr),
        ]
    q_scopes = flows("q", q_ops) + [
        scope("q-pe-2026-06-30", "Balance sheet at June 30, 2026", "period_end", None, "2026-06-30", q_bs),
        scope("q-pe-2025-12-31", "Balance sheet at December 31, 2025", "period_end", None, "2025-12-31", q_bs),
    ]
    r_scopes = flows("r", r_ops)
    merger_q = cite(Q, 33, "entered into an Agreement and Plan of Merger (the “Merger Agreement”), pursuant to which Merger Sub will merge with and into the Company, with the Company continuing as the surviving corporation and direct wholly owned subsidiary of Fertitta Gaming (the “Merger”).")
    merger_r = cite(R, 3, "Due to the Company’s pending definitive agreement to be acquired by Fertitta Entertainment, Inc. announced on May 28, 2026, Caesars will not be hosting a quarterly conference call.")
    alberta = cite(Q, 32, "Subsequent to June 30, 2026, we launched mobile sports betting and iGaming in Alberta, Canada on July 13, 2026.")
    conv = "The document is a text conversion of the filing: tables are pipe-delimited lines and pages follow the case page rule, not the printed pagination."
    sub = {
        "pack_sha256": PACK,
        "entities": [{
            "entity_id": "issuer", "name": "Caesars Entertainment, Inc.", "entity_type": "group", "roles": ["issuer"],
            "fiscal_year_end": "December 31",
            "citations": [cite(K, 1, "CAESARS ENTERTAINMENT, INC."), cite(K, 1, "For the fiscal year ended December 31, 2025")],
            "limitations": ["The three documents report one consolidated group; they give no separate borrower, guarantor or restricted-group financial statements."],
        }],
        "sources": [
            {"source_id": K, "classification": "financial", "document_type": "Annual report on Form 10-K", "published_on": "2026-02-17",
             "evidence_class": "audited_financial_statements",
             "evidence_rationale": "The document contains the independent registered public accounting firm's opinion that the financial statements present fairly the financial position and results",
             "analytical_use": "Audited annual statements for FY2023 to FY2025 and balance sheets at December 31, 2025 and 2024; business description",
             "citations": [cite(K, 51, "In our opinion, the financial statements present fairly, in all material respects, the financial position of the Company as of December 31, 2025 and 2024")],
             "scopes": k_scopes,
             "event_scan": "unassessed",
             "event_scan_explanation": "The Form 10-K carries no subsequent-events note that the search located, so no event is asserted or ruled out from it; the Merger postdates its signature date",
             "event_scan_citations": [],
             "limitations": [conv]},
            {"source_id": Q, "classification": "financial", "document_type": "Quarterly report on Form 10-Q", "published_on": "2026-07-28",
             "evidence_class": "unaudited_without_auditor",
             "evidence_rationale": "The condensed statements are marked unaudited and the document carries no auditor report",
             "analytical_use": "Quarter and six-month statements, balance sheet at June 30, 2026, debt note, merger note and management discussion",
             "citations": [cite(Q, 1, "For the quarterly period ended June 30, 2026"), cite(Q, 52, "Date: July 28, 2026 | /s/ Thomas R. Reeg")],
             "scopes": q_scopes,
             "event_scan": "events_identified", "event_ids": ["merger-agreement", "alberta-launch"],
             "event_scan_explanation": "The report discloses the pending Merger agreement and a launch after the quarter end",
             "event_scan_citations": [merger_q, alberta],
             "limitations": ["Interim statements are unaudited.", conv]},
            {"source_id": R, "classification": "financial", "document_type": "Earnings release, Exhibit 99.1", "published_on": "2026-07-28",
             "evidence_class": "unaudited_without_auditor",
             "evidence_rationale": "The release statement of operations is marked unaudited and the document carries no auditor report",
             "analytical_use": "Same-day restatement of the quarterly statement of operations, segment results, Adjusted EBITDA and net debt",
             "citations": [cite(R, 1, "Caesars Entertainment, Inc. Reports Second Quarter 2026 Results"), cite(R, 6, "CONSOLIDATED CONDENSED STATEMENTS OF OPERATIONS")],
             "scopes": r_scopes,
             "event_scan": "events_identified", "event_ids": ["merger-agreement"],
             "event_scan_explanation": "The release states the pending definitive agreement to be acquired",
             "event_scan_citations": [merger_r],
             "limitations": ["Unaudited; Adjusted EBITDA and net debt are non-GAAP measures defined by the issuer.", conv]},
        ],
        "events": [
            {"event_id": "merger-agreement", "reporting_scope_id": "k-fy2025", "event_date": "2026-05-27", "known_on": "2026-05-28",
             "status": "announced",
             "description": "Agreement and Plan of Merger signed with Fertitta Gaming Holdco, LLC and Empire Merger Sub, Inc.; the Merger is pending",
             "effect": "The Company would become a wholly owned subsidiary of Fertitta Gaming if the Merger closes; closing, financing and any effect on the capital structure are not determinable from the pack",
             "citations": [merger_q, merger_r]},
            {"event_id": "alberta-launch", "reporting_scope_id": "q-q2-2026", "event_date": "2026-07-13", "known_on": "2026-07-28",
             "status": "completed",
             "description": "Launch of mobile sports betting and iGaming in Alberta, Canada on July 13, 2026",
             "effect": "An operating event after the quarter end; it does not enter the reported figures for the quarter ended June 30, 2026",
             "citations": [alberta]},
        ],
        "limitations": ["The pack holds three documents of one registrant; no peer, forecast, covenant or debt-agreement document is in it.",
                        "The pending Merger has not closed and every figure is pre-closing."],
    }
    pages = {(K, 1), (K, 51), (K, 54), (K, 56), (Q, 1), (Q, 2), (Q, 4), (Q, 32), (Q, 33), (Q, 52), (R, 1), (R, 3), (R, 6)}
    calls = [{"tool": "read_pages", "arguments": {"source_id": s, "first_page": p, "last_page": p}} for s, p in sorted(pages)]
    for s in (K, Q, R):
        calls.append({"tool": "search_pack", "arguments": {"query": "subsequent", "source_id": s}})
    return {"step": "source_context", "calls": calls, "submission": sub}
