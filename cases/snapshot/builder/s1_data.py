"""S1 literal inputs: the new business source and the analyst submissions (stdlib only).

Nothing here imports deploy_vii. Every sentence a submission cites is checked against the
literal page text by build_s1_oracle.py (own quote and run-text checks), not by the product.
"""

# --- the new synthetic business source (pages are literal UTF-8 LF, no terminal LF) ------------

BUSINESS_PAGES = [
    (
        "page:1",
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Business and ownership note\n"
        "Published January 10, 2026.\n"
        "This invented case is test data, not evidence about a real issuer.\n"
        "Northbridge Synthetic Group is an industrial products manufacturer. It designs, "
        "manufactures and sells fastening and sealing components for industrial equipment.\n"
        "Customers are industrial distributors that serve maintenance, repair and operations "
        "demand, and original-equipment manufacturers supplied under annual supply agreements.\n"
        "All operations and all reported revenue are in the United States.\n"
        "Management describes the group as a leading supplier with a resilient aftermarket "
        "franchise.\n"
        "Revenue is reported as one operating segment, Consolidated Operations. The split of "
        "revenue between fastening and sealing components, and between distributors and "
        "original-equipment manufacturers, is not disclosed.\n"
        "The share of revenue from the largest customer is not disclosed.",
    ),
    (
        "page:2",
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Operating model and ownership\n"
        "List prices are reviewed once a year. Management states that raw-material cost "
        "increases are passed to customers with a lag of one to two quarters.\n"
        "Volumes follow distributor restocking cycles and original-equipment production "
        "schedules.\n"
        "Cost of sales consists mainly of steel, elastomer and manufacturing labour.\n"
        "Capital expenditure maintains existing plants; no growth capital programme is under "
        "way.\n"
        "Working capital consists of trade receivables, inventories and trade payables.\n"
        "The issuer is wholly owned by Harbour Ridge Holdings Limited, a synthetic holding "
        "company.\n"
        "Harbour Ridge Holdings Limited is held by private investors. The identity and "
        "percentage holdings of those investors are not disclosed.\n"
        "The issuer paid a dividend to Harbour Ridge Holdings Limited in each quarter of 2025 "
        "under a shareholder distribution policy approved by the board.\n"
        "No dividend recapitalisation, shareholder loan or related-party payment other than "
        "these dividends is reported.\n"
        "The source set identifies no financial sponsor.",
    ),
    (
        "page:3",
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Financing, transactions and history\n"
        "The only borrowing of the group is the Northbridge Term Loan, a senior secured term "
        "loan with final maturity on December 31, 2029.\n"
        "No acquisition, disposal, new financing, refinancing or change of ownership occurred "
        "in 2025, and none is announced or pending as of January 10, 2026.\n"
        "This note does not describe the security package, guarantees or covenants of the "
        "Northbridge Term Loan.\n"
        "The business was founded in 2011 as a family-owned manufacturer. Harbour Ridge "
        "Holdings Limited acquired the group in 2019.\n"
        "No credit rating from a rating agency has been assigned.",
    ),
]
BUSINESS_NAME = "Business and ownership note"
BUSINESS_MISSING_LIMITATION = "Business and ownership note was not supplied"


def Q(source_id, locator, quote):
    return {"source_id": source_id, "locator": locator, "quote": quote}


# Quotes (each a contiguous substring of one frozen page after whitespace normalisation).
ID_ISSUER = Q("identity", "page:1", "Northbridge Synthetic Group is the issuer and consolidated group.")
ID_PERIMETER = Q(
    "identity", "page:1", "No borrower, guarantor or restricted-group perimeter is established by this source set."
)
FIN_UNAUDITED = Q("financial", "page:1", "Unaudited quarterly and reported FY2025 financial statements")
FIN_SEGMENT = Q(
    "financial",
    "page:1",
    "One operating segment, Consolidated Operations, reports revenue of 30 in each quarter and 120 in FY2025",
)
FIN_NO_ADJ = Q(
    "financial", "page:1", "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete."
)
FIN_NO_ACQ = Q(
    "financial", "page:1", "No acquisitions, disposals, net equity movements, equity issuance, equity repurchases"
)
FIN_CAPEX = Q("financial", "page:1", "Capital expenditure is entirely maintenance investment; growth capex is zero.")
FIN_KPI = Q("financial", "page:1", "Operational KPIs and source-reported unlevered free cash flow are not disclosed.")
FIN_NO_RCF = Q(
    "financial",
    "page:1",
    "There is no revolving credit facility: RCF commitment and RCF drawings are each zero at opening and every quarter/FY end.",
)
FIN_DIV = Q("financial", "page:3", "Dividends paid (2.25) (2.25) (2.25) (2.25) (9.00)")
FIN_ONE_FACILITY = Q(
    "financial", "page:5", "There is exactly one debt facility: Northbridge Term Loan, facility_id term-loan."
)
FIN_MATURITY = Q("financial", "page:5", "Mandatory annual amortisation is 0; final maturity is December 31, 2029.")
B1_BUSINESS = Q(
    "business",
    "page:1",
    "It designs, manufactures and sells fastening and sealing components for industrial equipment.",
)
B1_SECTOR = Q("business", "page:1", "Northbridge Synthetic Group is an industrial products manufacturer.")
B1_CUSTOMERS = Q(
    "business",
    "page:1",
    "Customers are industrial distributors that serve maintenance, repair and operations demand, and original-equipment manufacturers supplied under annual supply agreements.",
)
B1_COUNTRY = Q("business", "page:1", "All operations and all reported revenue are in the United States.")
B1_MGMT = Q(
    "business",
    "page:1",
    "Management describes the group as a leading supplier with a resilient aftermarket franchise.",
)
B1_SPLIT = Q(
    "business",
    "page:1",
    "The split of revenue between fastening and sealing components, and between distributors and original-equipment manufacturers, is not disclosed.",
)
B1_TOPCUST = Q("business", "page:1", "The share of revenue from the largest customer is not disclosed.")
B2_PRICING = Q(
    "business",
    "page:2",
    "Management states that raw-material cost increases are passed to customers with a lag of one to two quarters.",
)
B2_VOLUME = Q(
    "business", "page:2", "Volumes follow distributor restocking cycles and original-equipment production schedules."
)
B2_COST = Q("business", "page:2", "Cost of sales consists mainly of steel, elastomer and manufacturing labour.")
B2_CAPEX = Q(
    "business", "page:2", "Capital expenditure maintains existing plants; no growth capital programme is under way."
)
B2_WC = Q("business", "page:2", "Working capital consists of trade receivables, inventories and trade payables.")
B2_OWNER = Q(
    "business",
    "page:2",
    "The issuer is wholly owned by Harbour Ridge Holdings Limited, a synthetic holding company.",
)
B2_INVESTORS = Q(
    "business",
    "page:2",
    "The identity and percentage holdings of those investors are not disclosed.",
)
B2_DIVIDEND = Q(
    "business",
    "page:2",
    "The issuer paid a dividend to Harbour Ridge Holdings Limited in each quarter of 2025 under a shareholder distribution policy approved by the board.",
)
B2_NO_RECAP = Q(
    "business",
    "page:2",
    "No dividend recapitalisation, shareholder loan or related-party payment other than these dividends is reported.",
)
B2_NO_SPONSOR = Q("business", "page:2", "The source set identifies no financial sponsor.")
B3_LOAN = Q(
    "business",
    "page:3",
    "The only borrowing of the group is the Northbridge Term Loan, a senior secured term loan with final maturity on December 31, 2029.",
)
B3_NO_TXN = Q(
    "business",
    "page:3",
    "No acquisition, disposal, new financing, refinancing or change of ownership occurred in 2025, and none is announced or pending as of January 10, 2026.",
)
B3_NO_SECURITY = Q(
    "business",
    "page:3",
    "This note does not describe the security package, guarantees or covenants of the Northbridge Term Loan.",
)
B3_FOUNDED = Q("business", "page:3", "The business was founded in 2011 as a family-owned manufacturer.")
B3_ACQUIRED = Q("business", "page:3", "Harbour Ridge Holdings Limited acquired the group in 2019.")

FLAG_TOPIC = "Quarterly dividends to the sole shareholder"

# --- CP-1A positive submission ------------------------------------------------------------------


def _g(kind, topic, fact, direction, dimension, mech, impl, quality, category, cites, limitation,
       btype=None, amount=None, legal=None):
    return {
        "kind": kind, "topic": topic, "documented_fact": fact, "direction": direction,
        "behaviour_type": btype, "amount_funding_source": amount, "legal_capacity_link": legal,
        "dimension": dimension, "risk_mechanic": mech, "credit_implication": impl,
        "evidence_quality": quality, "category": category, "citations": cites, "limitation": limitation,
    }


G_DEBT = _g(
    "governance_topic", "Debt structure and leverage tolerance",
    "The group has one senior secured term loan and no revolving facility, lease or other debt",
    "Neutral", "Leverage tolerance",
    "A single secured instrument with no revolver leaves no committed liquidity backstop beyond cash and concentrates refinancing at one maturity",
    "Liquidity depends on cash and operating cash flow; refinancing risk is concentrated at the single final maturity",
    "High", "Documentary Fact", [FIN_ONE_FACILITY, FIN_NO_RCF],
    "No leverage policy, covenant certificate or security terms are in the source set",
)
G_ACQ_POS = _g(
    "governance_topic", "Acquisition and disposal activity",
    "No acquisition or disposal occurred in any quarter of FY2025 or in the full year, and none is announced or pending",
    "Neutral", "Acquisition appetite",
    "No acquisition spending draws on cash or debt capacity, so integration and acquisition-funding risk is absent in the period",
    "No acquisition-driven change in leverage follows from the documented position; appetite beyond FY2025 is not inferred from one year",
    "High", "Documentary Fact", [FIN_NO_ACQ, B3_NO_TXN], None,
)
G_ACQ_GAP = dict(G_ACQ_POS, documented_fact="No acquisition or disposal occurred in any quarter of FY2025 or in the full year",
                 citations=[FIN_NO_ACQ],
                 limitation="Whether any acquisition or disposal is announced or pending is not documented because the business source is missing")
G_REPORTING = _g(
    "governance_topic", "Financial reporting and disclosure",
    "Quarterly and annual statements and a complete facility schedule are supplied, but the statements are unaudited, operating KPIs are not disclosed and no borrower, guarantor or restricted-group perimeter is established",
    "Mixed", "Disclosure transparency",
    "Unaudited statements and absent KPIs limit independent verification of reported earnings and cash conversion",
    "Monitoring relies on unaudited issuer figures; assurance and perimeter gaps lower confidence in covenant and leverage readings",
    "Medium", "Documentary Fact", [FIN_UNAUDITED, FIN_KPI, ID_PERIMETER],
    "No audit report or perimeter definition is supplied",
)
G_DIVIDEND_POS = _g(
    "behaviour_flag", FLAG_TOPIC,
    "A dividend was paid to the sole shareholder in each quarter of FY2025 under a board-approved distribution policy; no dividend recapitalisation, shareholder loan or other related-party payment is reported",
    "Mixed", "Shareholder extraction risk",
    "Recurring distributions remove cash that could service or repay debt, and the funding source of the distributions is not stated",
    "Distributions compete with debt service and deleveraging; extraction cannot be concluded or excluded from this source set",
    "High", "Documentary Fact", [B2_DIVIDEND, B2_NO_RECAP, FIN_DIV],
    "The funding source of the dividends is not stated",
    btype="distribution",
    amount="Amounts are in the cash flow statement of the financial source; the funding source is not stated",
    legal="Distribution capacity under the Northbridge Term Loan is not in this source set; legal capacity, willingness and feasibility are not assessed together here",
)
G_DIVIDEND_GAP = dict(
    G_DIVIDEND_POS,
    documented_fact="A dividend was paid in each quarter of FY2025; the recipient and the distribution policy are not documented",
    citations=[FIN_DIV],
    limitation="The recipient, the policy and the funding source of the dividends are not documented",
)

POSITIVE_CP1A = {
    "sources": [
        {"source_id": "identity", "source_class": "issuer", "quality": "High",
         "period": "January 10, 2026", "entity_covered": "Northbridge Synthetic Group, consolidated group",
         "data_supplied": "Issuer identity, fiscal year end and perimeter statement",
         "use": "Confirms the issuer identity and that no borrower, guarantor or restricted-group perimeter is established",
         "citations": [ID_ISSUER, ID_PERIMETER], "limitation": "Synthetic test data, not evidence about a real issuer"},
        {"source_id": "financial", "source_class": "issuer", "quality": "High",
         "period": "FY2025", "entity_covered": "Northbridge Synthetic Group, consolidated group",
         "data_supplied": "Quarterly and annual statements, the facility schedule and statements of what did not occur",
         "use": "Documents the single operating segment, the single debt facility, distributions and the absence of acquisitions and adjustments",
         "citations": [FIN_SEGMENT, FIN_ONE_FACILITY], "limitation": "Unaudited; borrower, guarantor and restricted-group perimeters are not established"},
        {"source_id": "business", "source_class": "issuer", "quality": "Medium",
         "period": "January 10, 2026", "entity_covered": "Northbridge Synthetic Group",
         "data_supplied": "Business description, customers, operating model, ownership, financing and history",
         "use": "Supplies the business, ownership and transaction facts and carries management characterisations",
         "citations": [B1_BUSINESS, B2_OWNER, B3_LOAN],
         "limitation": "Issuer-authored note with management statements; customer concentration and ultimate owners are not disclosed"},
    ],
    "company": [
        {"aspect": "business_description",
         "text": "Designs, manufactures and sells fastening and sealing components for industrial equipment, supplied to industrial distributors and original-equipment manufacturers",
         "category": "Documentary Fact", "citations": [B1_BUSINESS, B1_CUSTOMERS], "limitation": None},
        {"aspect": "country", "text": "United States", "category": "Documentary Fact",
         "citations": [B1_COUNTRY], "limitation": None},
        {"aspect": "sector", "text": "Industrial products manufacturing", "category": "Documentary Fact",
         "citations": [B1_SECTOR], "limitation": None},
    ],
    "business_lines": [
        {"name": "Consolidated Operations (single reported operating segment)",
         "revenue_mix": "All reported revenue is reported in this one operating segment", "period": "FY2025",
         "category": "Documentary Fact", "citations": [FIN_SEGMENT], "limitation": None},
        {"name": "Fastening and sealing components (product lines)",
         "revenue_mix": "Split between product lines not disclosed", "period": "FY2025",
         "category": "Insufficient Information", "citations": [B1_SPLIT],
         "limitation": "The source states that the product-line and customer-type revenue split is not disclosed, so product-line mix cannot be assessed"},
    ],
    "owners": [
        {"owner": "Harbour Ridge Holdings Limited (sole shareholder)",
         "control": "Wholly owns the issuer; board composition and control rights beyond ownership are not disclosed",
         "economic_interest": "The whole equity of the issuer as stated; the holding company is held by private investors who are not identified",
         "credit_relevance": "Dividend decisions rest with a single shareholder whose own owners are not identified",
         "evidence_quality": "High",
         "credit_mechanic": "A single holding-company shareholder receives the dividends, so cash leaves the group at the shareholder's discretion and the ultimate owners cannot be assessed for support willingness",
         "credit_implication": "Shareholder distributions are a leakage channel competing with debt service; the lack of ultimate-owner disclosure limits the assessment of equity support and monitoring posture",
         "category": "Documentary Fact", "citations": [B2_OWNER, B2_INVESTORS],
         "limitation": "Ultimate owners and percentage holdings are not disclosed; no percentage is inferred"},
    ],
    "operating_drivers": [
        {"driver": "Pricing",
         "measure": "List prices are reviewed once a year; management states that raw-material cost increases are passed to customers with a lag of one to two quarters",
         "period": "FY2025", "status": "Partially disclosed",
         "credit_relevance": "A pass-through lag exposes margin to temporary squeezes when input costs rise",
         "category": "Management Language", "citations": [B2_PRICING],
         "limitation": "Pass-through is a management statement; its realised effect on margin is not disclosed"},
        {"driver": "Volume drivers",
         "measure": "Distributor restocking cycles and original-equipment production schedules",
         "period": "FY2025", "status": "Disclosed",
         "credit_relevance": "Volumes follow customer inventory and production cycles, which moves revenue with the cycle",
         "category": "Documentary Fact", "citations": [B2_VOLUME], "limitation": None},
        {"driver": "Cost structure",
         "measure": "Cost of sales consists mainly of steel, elastomer and manufacturing labour",
         "period": "FY2025", "status": "Disclosed",
         "credit_relevance": "Commodity and labour inputs drive margin resilience",
         "category": "Documentary Fact", "citations": [B2_COST], "limitation": None},
        {"driver": "Capital spending",
         "measure": "Maintenance of existing plants; no growth capital programme",
         "period": "FY2025", "status": "Disclosed",
         "credit_relevance": "Capital spending is discretionary-light, which supports cash conversion",
         "category": "Documentary Fact", "citations": [B2_CAPEX, FIN_CAPEX], "limitation": None},
        {"driver": "Working capital",
         "measure": "Trade receivables, inventories and trade payables",
         "period": "FY2025", "status": "Disclosed",
         "credit_relevance": "Receivables and inventory absorb cash when volumes grow",
         "category": "Documentary Fact", "citations": [B2_WC], "limitation": None},
        {"driver": "Customer concentration", "measure": None, "period": "FY2025", "status": "Not disclosed",
         "credit_relevance": "Concentration cannot be assessed, so loss of a major customer cannot be sized",
         "category": "Insufficient Information", "citations": [B1_TOPCUST],
         "limitation": "The share of revenue from the largest customer is not disclosed; concentration risk cannot be assessed"},
        {"driver": "Aftermarket franchise (management characterisation)",
         "measure": "Management describes the group as a leading supplier with a resilient aftermarket franchise",
         "period": "FY2025", "status": "Partially disclosed",
         "credit_relevance": "Resilience is asserted by management and is not evidenced by retention or share data",
         "category": "Management Language", "citations": [B1_MGMT],
         "limitation": "No customer retention, market share or aftermarket revenue data is supplied"},
    ],
    "transactions": [
        {"transaction": "Northbridge Term Loan: the only borrowing of the group, a senior secured term loan with final maturity on December 31, 2029; no new financing, acquisition, disposal or change of ownership is announced or pending",
         "status": "Completed",
         "credit_relevance": "The sole debt instrument concentrates refinancing exposure at one maturity date, and no new transaction is in front of the committee",
         "category": "Documentary Fact", "citations": [B3_LOAN, B3_NO_TXN], "limitation": None},
    ],
    "events": [
        {"date_window": "2011", "event": "Business founded as a family-owned manufacturer",
         "credit_relevance": "Establishes an operating history of more than a decade", "status": "Completed",
         "category": "Documentary Fact", "citations": [B3_FOUNDED], "limitation": None},
        {"date_window": "2019", "event": "Harbour Ridge Holdings Limited acquired the group",
         "credit_relevance": "The current ownership structure dates from this acquisition; its terms and financing are not disclosed",
         "status": "Completed", "category": "Documentary Fact", "citations": [B3_ACQUIRED],
         "limitation": "Acquisition terms and financing are not disclosed"},
        {"date_window": "FY2025", "event": "Dividend paid to Harbour Ridge Holdings Limited in each quarter",
         "credit_relevance": "A recurring cash distribution to the sole shareholder", "status": "Completed",
         "category": "Documentary Fact", "citations": [B2_DIVIDEND], "limitation": None},
        {"date_window": "December 31, 2029", "event": "Final maturity of the Northbridge Term Loan",
         "credit_relevance": "The single maturity date for all debt is a refinancing event", "status": "Pending",
         "category": "Documentary Fact", "citations": [B3_LOAN, FIN_MATURITY], "limitation": None},
    ],
    "governance_and_sponsor": [G_DIVIDEND_POS, G_ACQ_POS, G_REPORTING, G_DEBT],
    "capital_allocation": [
        {"item": "Shareholder distributions",
         "fact": "Dividends were paid in every quarter of FY2025 and no equity was issued or repurchased",
         "direction": "Mixed",
         "risk_mechanic": "Distributions reduce cash available for debt service and no equity contribution offsets them",
         "credit_implication": "Cash leakage to the shareholder competes with deleveraging; the funding source is not documented",
         "evidence_quality": "High", "category": "Documentary Fact", "citations": [FIN_DIV, FIN_NO_ACQ],
         "limitation": "The funding source of the dividends is not stated"},
        {"item": "Capital expenditure",
         "fact": "Capital expenditure is entirely maintenance investment and growth capital expenditure is zero",
         "direction": "Neutral",
         "risk_mechanic": "Maintenance-only spending keeps cash conversion high but defers any growth investment",
         "credit_implication": "Free cash flow is not constrained by an investment programme; growth depends on existing capacity",
         "evidence_quality": "High", "category": "Documentary Fact", "citations": [FIN_CAPEX], "limitation": None},
    ],
    "acquisitions": [],
    "disclosure_items": [
        {"item": "Debt schedule", "available": "Yes",
         "detail": "A complete facility schedule with balances at each reporting date is supplied",
         "credit_relevance": "Needed to track debt and maturity", "severity": "Minor", "follow_up": "None required",
         "citations": [FIN_ONE_FACILITY]},
        {"item": "Maturity schedule", "available": "Yes",
         "detail": "Final maturity and mandatory amortisation of the single facility are stated",
         "credit_relevance": "Needed to size refinancing exposure", "severity": "Minor", "follow_up": "None required",
         "citations": [FIN_MATURITY]},
        {"item": "Covenant certificate", "available": "No",
         "detail": "No covenant certificate or covenant terms are in the CP-1A source set",
         "credit_relevance": "Headroom to financial covenants cannot be monitored", "severity": "Material",
         "follow_up": "Obtain the covenant certificate and the executed covenant terms", "citations": []},
        {"item": "Add-back bridge", "available": "Yes",
         "detail": "The source states that no EBITDA adjustments or add-backs occurred and that the disclosure is complete",
         "credit_relevance": "Reported and adjusted EBITDA are the same, so no add-back risk arises",
         "severity": "Minor", "follow_up": "None required", "citations": [FIN_NO_ADJ]},
        {"item": "Security package and guarantees", "available": "No",
         "detail": "The business note states that it does not describe the security package, guarantees or covenants",
         "credit_relevance": "Recovery prospects and creditor control cannot be assessed without them",
         "severity": "Material", "follow_up": "Obtain the security and guarantee terms", "citations": []},
    ],
    "credit_translations": [
        {"theme": "Revenue Durability",
         "evidence": "Revenue comes from distributors serving maintenance demand and from original-equipment manufacturers on annual supply agreements; the revenue split and customer concentration are not disclosed",
         "risk_mechanic": "Maintenance demand is recurring but annual supply agreements reset each year, so revenue visibility is limited to the contract year",
         "credit_implication": "Debt service capacity rests on annual contract renewals; undisclosed concentration limits confidence in any durability view",
         "confidence": "Medium", "countervailing_conflict_ids": [], "citations": [B1_CUSTOMERS],
         "limitation": "Customer concentration and the revenue split are not disclosed"},
        {"theme": "Margin/CF Risk",
         "evidence": "Management states that raw-material cost increases are passed to customers with a lag",
         "risk_mechanic": "The lag exposes margin to a temporary squeeze when steel and elastomer costs rise",
         "credit_implication": "Cash conversion and debt service cover can weaken for the length of the lag; the pass-through is a management statement not tested in the source set",
         "confidence": "Low", "countervailing_conflict_ids": [], "citations": [B2_PRICING, B2_COST],
         "limitation": "Realised pass-through is not evidenced"},
        {"theme": "Concentration Risk",
         "evidence": "No customer concentration disclosure is supplied",
         "risk_mechanic": "Loss of a major customer could remove a large share of revenue, but the share is unknown",
         "credit_implication": "Concentration risk is unassessed and is treated as neither adverse nor benign",
         "confidence": "Insufficient Information", "countervailing_conflict_ids": [], "citations": [B1_TOPCUST],
         "limitation": "The share of revenue from the largest customer is not disclosed"},
        {"theme": "Sponsor Alignment",
         "evidence": "The sole shareholder is a holding company held by undisclosed private investors and receives a dividend every quarter; no financial sponsor is identified",
         "risk_mechanic": "Without identified ultimate owners, support willingness cannot be inferred, and distributions are the only documented owner behaviour",
         "credit_implication": "Equity support is not assumed in the credit view, and distributions are monitored against debt service",
         "confidence": "Medium", "countervailing_conflict_ids": [], "citations": [B2_OWNER, B2_DIVIDEND, B2_NO_SPONSOR],
         "limitation": "Ultimate owners and the terms of the distribution policy are not disclosed"},
        {"theme": "Key Uncertainties",
         "evidence": "No covenant certificate, security package, guarantee terms, audit report or customer concentration disclosure is in the source set",
         "risk_mechanic": "Unverified creditor protections and unaudited figures leave covenant headroom and recovery prospects untested",
         "credit_implication": "The monitoring posture should treat the credit view as provisional until these items are obtained",
         "confidence": "Medium", "countervailing_conflict_ids": [], "citations": [FIN_UNAUDITED, B3_NO_SECURITY],
         "limitation": None},
    ],
    "conflicts": [],
    "gaps": [
        {"gap": "No covenant certificate or covenant terms in the CP-1A source set",
         "why_it_matters": "Headroom to financial covenants cannot be monitored",
         "affected_analysis": "Key uncertainties translation and the financial risk view of the credit synthesis",
         "severity": "Material", "action": "Obtain the covenant certificate and the executed covenant terms"},
        {"gap": "Customer concentration and product-line revenue split not disclosed",
         "why_it_matters": "Revenue durability and concentration risk cannot be confirmed",
         "affected_analysis": "Revenue durability and concentration translations",
         "severity": "Material", "action": "Request the largest-customer share and revenue by product line"},
        {"gap": "Owners of the holding company and distribution policy terms not disclosed",
         "why_it_matters": "Support willingness and distribution capacity cannot be assessed",
         "affected_analysis": "Sponsor alignment translation and the governance score",
         "severity": "Material", "action": "Request the ownership chain and the distribution policy"},
    ],
    "consumers": [
        {"module_id": "CP-2", "status": "READY",
         "handoff_item": "Business, ownership and operating registers and the governance score for the credit synthesis",
         "why_it_matters": "Business risk in the synthesis rests on these rows",
         "gap": "No blocking gap; material gaps are listed in the gaps ledger",
         "required_action": "Cite CP-1A rows for business risk and restate material gaps in the synthesis gaps ledger",
         "citations": [], "flag_topics": [FLAG_TOPIC]},
        {"module_id": "CP-MODEL", "status": "READY_WITH_LIMITATIONS",
         "handoff_item": "Issuer name, country, sector, shareholders, transaction summary and business description",
         "why_it_matters": "The Model snapshot shows these fields with their source",
         "gap": "Owners behind the holding company are not disclosed",
         "required_action": "Show the snapshot fields with their sources and mark undisclosed ones as gaps",
         "citations": [B1_COUNTRY], "flag_topics": []},
    ],
}

# --- gap case: business note present but without ownership and transaction content ------------------

_P2 = BUSINESS_PAGES[1][1].split("\n")
BUSINESS_GAP_PAGES = [
    BUSINESS_PAGES[0],
    ("page:2", "\n".join(["NORTHBRIDGE SYNTHETIC GROUP", "Operating model", *_P2[2:7]])),
]
BUSINESS_GAP_LIMITATION = "Business note supplies no ownership or transaction content"
LIMIT_FIN = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."

GAP_CP1A = {
    "sources": [
        POSITIVE_CP1A["sources"][0],
        POSITIVE_CP1A["sources"][1],
        {"source_id": "business", "source_class": "issuer", "quality": "Medium",
         "period": "January 10, 2026", "entity_covered": "Northbridge Synthetic Group",
         "data_supplied": "Business description, customers and operating model; no ownership, transaction or history content",
         "use": "Supplies business and operating facts; ownership and transaction rows stay unsettled",
         "citations": [B1_BUSINESS, B2_PRICING],
         "limitation": "Issuer-authored note with management statements; it supplies no ownership or transaction content"},
    ],
    "company": POSITIVE_CP1A["company"],
    "business_lines": POSITIVE_CP1A["business_lines"],
    "owners": [
        {"owner": "Ownership not established",
         "control": "Not established", "economic_interest": "Not established",
         "credit_relevance": "Control and support willingness cannot be assessed without ownership evidence",
         "evidence_quality": "Insufficient",
         "credit_mechanic": "Distributions, support and control cannot be traced to an owner",
         "credit_implication": "Sponsor alignment is unassessed and is not treated as adverse",
         "category": "Insufficient Information", "citations": [],
         "limitation": "The business note supplies no ownership content"},
    ],
    "operating_drivers": POSITIVE_CP1A["operating_drivers"],
    "transactions": [
        {"transaction": "Transaction context not established: the business note supplies no transaction content",
         "status": "Insufficient Information",
         "credit_relevance": "Debt raised, use of proceeds, parties and sponsor involvement cannot be assessed",
         "category": "Insufficient Information", "citations": [],
         "limitation": "The business note supplies no transaction content"},
    ],
    "events": [],
    "governance_and_sponsor": [G_DIVIDEND_GAP, G_ACQ_GAP, G_REPORTING, G_DEBT],
    "capital_allocation": [POSITIVE_CP1A["capital_allocation"][0], POSITIVE_CP1A["capital_allocation"][1]],
    "acquisitions": [],
    "disclosure_items": [
        {"item": "Ownership and transaction disclosure", "available": "No",
         "detail": "The business note supplies no ownership or transaction content",
         "credit_relevance": "Owner behaviour, support willingness and transaction context cannot be assessed",
         "severity": "Critical", "follow_up": "Obtain the ownership and transaction documents and rerun CP-1A",
         "citations": []},
        {"item": "Debt schedule", "available": "Yes",
         "detail": "A complete facility schedule with balances at each reporting date is supplied",
         "credit_relevance": "Needed to track debt and maturity", "severity": "Minor", "follow_up": "None required",
         "citations": [FIN_ONE_FACILITY]},
        {"item": "Covenant certificate", "available": "No",
         "detail": "No covenant certificate or covenant terms are in the CP-1A source set",
         "credit_relevance": "Headroom to financial covenants cannot be monitored", "severity": "Material",
         "follow_up": "Obtain the covenant certificate and the executed covenant terms", "citations": []},
    ],
    "credit_translations": [
        POSITIVE_CP1A["credit_translations"][0],
        POSITIVE_CP1A["credit_translations"][1],
        POSITIVE_CP1A["credit_translations"][2],
        {"theme": "Sponsor Alignment",
         "evidence": "No ownership evidence is supplied, so the owners and their behaviour are not documented",
         "risk_mechanic": "Without identified owners, support willingness and distribution behaviour cannot be traced",
         "credit_implication": "Sponsor alignment is unassessed and is treated as neither adverse nor benign",
         "confidence": "Insufficient Information", "countervailing_conflict_ids": [], "citations": [],
         "limitation": "The business note supplies no ownership content"},
        {"theme": "Key Uncertainties",
         "evidence": "No ownership, transaction, covenant, security or audit disclosure is in the source set",
         "risk_mechanic": "Unverified owner behaviour, creditor protections and unaudited figures leave support, covenant headroom and recovery prospects untested",
         "credit_implication": "The monitoring posture should treat the credit view as provisional until these items are obtained",
         "confidence": "Medium", "countervailing_conflict_ids": [], "citations": [FIN_UNAUDITED, ID_PERIMETER],
         "limitation": None},
    ],
    "conflicts": [],
    "gaps": [
        {"gap": "Ownership and transaction content not supplied in the business note",
         "why_it_matters": "Owner behaviour, support willingness and transaction context cannot be assessed",
         "affected_analysis": "Ownership register, transaction summary, sponsor alignment and the governance score",
         "severity": "Critical", "action": "Supply the ownership and transaction documents and rerun CP-1A"},
        {"gap": "No covenant certificate or covenant terms in the CP-1A source set",
         "why_it_matters": "Headroom to financial covenants cannot be monitored",
         "affected_analysis": "Key uncertainties translation and the financial risk view of the credit synthesis",
         "severity": "Material", "action": "Obtain the covenant certificate and the executed covenant terms"},
    ],
    "consumers": [
        {"module_id": "CP-2", "status": "READY_WITH_LIMITATIONS",
         "handoff_item": "Business, operating and governance rows; ownership and transaction rows are unsettled",
         "why_it_matters": "Business risk in the synthesis can rest on the located rows but not on ownership or transaction facts",
         "gap": "Ownership and transaction content is missing from the business note",
         "required_action": "Work from located rows and CP-1 figures, state the limit and restate the Critical gap",
         "citations": [FIN_SEGMENT], "flag_topics": [FLAG_TOPIC]},
        {"module_id": "CP-MODEL", "status": "CONDITIONAL",
         "handoff_item": "Issuer name, country, sector and business description are located; shareholders and transaction summary are gaps",
         "why_it_matters": "The Model snapshot shows located fields with their source and the others as gaps",
         "gap": "Ownership and transaction content is missing from the business note",
         "required_action": "Show the unlocated fields as gaps and do not infer them",
         "citations": [B1_COUNTRY], "flag_topics": []},
    ],
}

# --- CP-2 submissions -----------------------------------------------------------------------------
# {{FIG:<name>}} marks a CP-1 figure reference. Instantiation replaces it with {<fact_id>|<unit>}
# once the actual CP-1 head is inspected; unreplaced, the text is malformed run text and fails closed.

FIGS = {
    # name: (CP-1 coordinate, oracle numerator/denominator, unit token, spelled text)
    "total_leverage_reported": ("T4.10 total_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31", "50/30", "x", "1.67x"),
    "net_leverage_reported": ("T4.10 net_leverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31", "30/30", "x", "1.00x"),
    "interest_coverage_reported": ("T4.10 interest_coverage_reported, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31", "30/5", "x", "6.00x"),
    "fcf_to_debt": ("T4.10 fcf_to_debt, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31", "9/50", "%", "18.0%"),
}


def F(name):
    return "{{FIG:" + name + "}}"


POSITIVE_CP2 = {
    "assessment": {
        "rationale": f"The fundamental credit view is moderate and provisional: total leverage is {F('total_leverage_reported')} and net leverage {F('net_leverage_reported')} on reported EBITDA for the twelve months to FY2025, and interest cover is {F('interest_coverage_reported')}, but a single maturity, undisclosed customer concentration, unaudited statements and absent covenant terms keep confidence below High.",
        "category": "Analyst Interpretation", "confidence": "Medium",
        "cp1a_refs": ["revenue_business_mix.r01", "credit_translation.r05"],
        "limitation": "Unaudited statements, no covenant terms, undisclosed customer concentration and an undisclosed ownership chain",
    },
    "thesis": {
        "text": "Northbridge Synthetic Group is a low-leverage, cash-generative industrial manufacturer whose credit strength rests on unaudited figures and a single maturity, so the view is a provisional stable thesis pending covenant terms and customer disclosure.",
        "category": "Analyst Interpretation", "cp1a_refs": ["credit_translation.r01", "credit_translation.r05"], "limitation": None,
    },
    "strengths": [
        {"label": "Low reported leverage",
         "text": f"Total leverage is {F('total_leverage_reported')} and net leverage is {F('net_leverage_reported')} on reported EBITDA for the twelve months to FY2025.",
         "category": "Documentary Fact", "cp1a_refs": [], "limitation": None},
        {"label": "Cash generation and cover",
         "text": f"Interest cover is {F('interest_coverage_reported')} and free cash flow is {F('fcf_to_debt')} of debt, with capital expenditure entirely for maintenance.",
         "category": "Documentary Fact", "cp1a_refs": ["operating_model.r04"], "limitation": None},
        {"label": "No acquisition pressure",
         "text": "No acquisition or disposal occurred in the period, so there is no integration or acquisition-funding pressure on cash flow.",
         "category": "Documentary Fact", "cp1a_refs": ["T2D.3.r01"], "limitation": None},
    ],
    "weaknesses": [
        {"label": "Single maturity and no revolver",
         "text": "All debt is one senior secured term loan with no revolving facility, so liquidity rests on cash and operating cash flow and refinancing is concentrated at one date.",
         "category": "Analyst Interpretation", "cp1a_refs": ["transaction_summary.r01", "T2D.3.r03"], "limitation": None},
        {"label": "Customer concentration unassessed",
         "text": "Customer concentration and the revenue split are not disclosed, so revenue durability cannot be confirmed.",
         "category": "Insufficient Information", "cp1a_refs": ["operating_model.r06", "revenue_business_mix.r02"],
         "limitation": "The largest-customer share and the product-line split are not disclosed, so their effect on revenue durability is unknown"},
        {"label": "Distributions and unaudited reporting",
         "text": "Dividends are paid to the sole shareholder every quarter, the funding source is not documented and the statements are unaudited, which weakens confidence in cash available for debt service.",
         "category": "Analyst Interpretation", "cp1a_refs": ["T2D.4.r01", "T2D.3.r02"], "limitation": None},
    ],
    "key_findings": [
        {"text": f"Leverage is low: total {F('total_leverage_reported')} and net {F('net_leverage_reported')} on reported EBITDA for the twelve months to FY2025, with interest cover of {F('interest_coverage_reported')}.",
         "cp1a_refs": []},
        {"text": "All debt is a single senior secured term loan maturing on December 31, 2029 with no revolver, which concentrates refinancing risk at one date.",
         "cp1a_refs": ["transaction_summary.r01"]},
        {"text": "Quarterly dividends to the sole shareholder continue while their funding source and the owners behind the holding company are undisclosed.",
         "cp1a_refs": ["T2D.4.r01", "ownership_register.r01"]},
        {"text": "Customer concentration, covenant terms and an audit report are missing, so the credit view stays provisional.",
         "cp1a_refs": ["gaps_ledger.r01", "gaps_ledger.r02"]},
    ],
    "risks": [
        {"risk": "Refinancing concentration",
         "mechanic": "One term loan matures on a single date with no revolver, so market access at that date decides whether the debt can be refinanced",
         "implication": "Refinancing risk rises as the maturity nears if leverage or earnings weaken, so monitoring should track the maturity profile",
         "severity": "Material", "cp1a_refs": ["transaction_summary.r01", "events_timeline.r04"]},
        {"risk": "Shareholder distributions",
         "mechanic": "Quarterly dividends remove cash that could service or repay debt, and their funding source is undisclosed",
         "implication": "Distribution capacity under the debt documents is the key unknown for the monitoring posture",
         "severity": "Material", "cp1a_refs": ["T2D.4.r01", "T2D.5.r01"]},
        {"risk": "Unverified earnings quality",
         "mechanic": "Unaudited statements and absent KPIs limit verification of earnings and cash conversion",
         "implication": "Leverage and cover readings carry reporting risk until an audit report or KPIs are obtained",
         "severity": "Minor", "cp1a_refs": ["T2D.3.r02"]},
    ],
    "gaps": [
        {"gap": "Covenant certificate and covenant terms",
         "why_it_matters": "Headroom to financial covenants cannot be monitored",
         "affected_analysis": "Financial risk and liquidity view", "severity": "Material",
         "action": "Obtain the certificate and the executed terms", "cp1a_refs": ["gaps_ledger.r01"]},
        {"gap": "Customer concentration and revenue split",
         "why_it_matters": "Revenue durability cannot be confirmed",
         "affected_analysis": "Business risk assessment", "severity": "Material",
         "action": "Obtain the largest-customer share and revenue by product line", "cp1a_refs": ["gaps_ledger.r02"]},
        {"gap": "Ownership chain and distribution policy terms",
         "why_it_matters": "Support willingness and distribution capacity cannot be assessed",
         "affected_analysis": "Sponsor alignment in the assessment", "severity": "Material",
         "action": "Obtain the ownership chain and the policy", "cp1a_refs": ["gaps_ledger.r03"]},
    ],
}

GAP_CP2 = {
    "assessment": {
        "rationale": f"The credit view combines CP-1 figures with located business and operating facts: total leverage is {F('total_leverage_reported')} and net leverage {F('net_leverage_reported')} for the twelve months to FY2025, but ownership and transaction context was not supplied, so confidence is Low.",
        "category": "Analyst Interpretation", "confidence": "Low",
        "cp1a_refs": ["revenue_business_mix.r01"],
        "limitation": "Ownership and transaction content missing; sponsor alignment and transaction context are unassessed",
    },
    "thesis": {
        "text": "Financial leverage is low and the operating model is simple, but without ownership and transaction evidence the thesis is incomplete and cannot support a view of owner behaviour.",
        "category": "Analyst Interpretation", "cp1a_refs": ["credit_translation.r05"], "limitation": None,
    },
    "strengths": [
        {"label": "Low reported leverage",
         "text": f"Total leverage is {F('total_leverage_reported')} and net leverage is {F('net_leverage_reported')} on reported EBITDA for the twelve months to FY2025.",
         "category": "Documentary Fact", "cp1a_refs": [], "limitation": None},
    ],
    "weaknesses": [
        {"label": "Ownership and transactions unassessed",
         "text": "No ownership or transaction content was supplied, so owner behaviour and transaction context cannot be assessed.",
         "category": "Insufficient Information", "cp1a_refs": ["gaps_ledger.r01"],
         "limitation": "The business note supplies no ownership or transaction content"},
    ],
    "key_findings": [
        {"text": f"Leverage is low on the supplied statements: total {F('total_leverage_reported')} and net {F('net_leverage_reported')} for the twelve months to FY2025.", "cp1a_refs": []},
        {"text": "The business note supplies no ownership or transaction content, so the credit view cannot cover owner behaviour or transaction context.", "cp1a_refs": ["gaps_ledger.r01"]},
    ],
    "risks": [
        {"risk": "Unassessed owner behaviour",
         "mechanic": "Without ownership evidence, support willingness and distribution behaviour cannot be traced",
         "implication": "The monitoring posture should treat the view as incomplete until the ownership documents are obtained",
         "severity": "Material", "cp1a_refs": ["gaps_ledger.r01"]},
    ],
    "gaps": [
        {"gap": "Ownership and transaction content not supplied, with no ownership and transaction disclosure",
         "why_it_matters": "Owner behaviour, support willingness and transaction context cannot be assessed",
         "affected_analysis": "Sponsor alignment and transaction context in the assessment", "severity": "Critical",
         "action": "Supply the ownership and transaction documents, rerun CP-1A and then CP-2",
         "cp1a_refs": ["gaps_ledger.r01", "T2D.7.r01"]},
        {"gap": "CP-1A judges CP-2 ready with limitations",
         "why_it_matters": "The synthesis inherits the missing ownership and transaction evidence",
         "affected_analysis": "Confidence of the credit assessment", "severity": "Material",
         "action": "Keep confidence below High until CP-1A is rerun with the ownership and transaction documents",
         "cp1a_refs": ["downstream_readiness.r01"]},
    ],
}
