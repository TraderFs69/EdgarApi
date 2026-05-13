# app.py

import streamlit as st
import pandas as pd
import requests

# =========================================================
# CONFIG
# =========================================================

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

st.set_page_config(
    page_title="TEA SEC Fundamental Scanner",
    layout="wide"
)

# =========================================================
# FUNCTIONS
# =========================================================

@st.cache_data
def get_cik_from_ticker(ticker):

    url = "https://www.sec.gov/files/company_tickers.json"

    data = requests.get(url, headers=HEADERS).json()

    for company in data.values():

        if company["ticker"].upper() == ticker.upper():

            return str(company["cik_str"]).zfill(10)

    return None


@st.cache_data
def get_company_submissions(cik):

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def extract_filings(submissions):

    recent = submissions["filings"]["recent"]

    df = pd.DataFrame({
        "Form": recent["form"],
        "Filing Date": recent["filingDate"],
        "Accession Number": recent["accessionNumber"],
        "Primary Document": recent["primaryDocument"]
    })

    filings = df[
        df["Form"].isin(["10-K", "10-Q"])
    ]

    return filings


def build_filing_url(cik, accession, document):

    accession_clean = accession.replace("-", "")

    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{accession_clean}/{document}"
    )

    return url


@st.cache_data
def get_company_facts(cik):

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def extract_revenue_data(data):

    possible_keys = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues"
    ]

    us_gaap = data["facts"]["us-gaap"]

    for key in possible_keys:

        if key in us_gaap:

            revenues = us_gaap[key]["units"]["USD"]

            df = pd.DataFrame(revenues)

            columns_to_keep = []

            for col in ["fy", "fp", "frame", "val", "filed"]:
                if col in df.columns:
                    columns_to_keep.append(col)

            df = df[columns_to_keep]

            return df

    return None


# =========================================================
# UI
# =========================================================

st.title("TEA SEC Fundamental Scanner")

ticker = st.text_input(
    "Enter Ticker",
    value="NVDA"
)

if st.button("Analyze Company"):

    with st.spinner("Loading SEC data..."):

        # =================================================
        # GET CIK
        # =================================================

        cik = get_cik_from_ticker(ticker)

        if cik is None:

            st.error("Ticker not found.")

            st.stop()

        st.success(f"CIK Found: {cik}")

        # =================================================
        # GET FILINGS
        # =================================================

        submissions = get_company_submissions(cik)

        filings = extract_filings(submissions)

        # Keep only last 5 years approx
        filings = filings.head(25)

        st.subheader("10-K and 10-Q Filings")

        filings_display = filings.copy()

        filing_urls = []

        for _, row in filings.iterrows():

            filing_url = build_filing_url(
                cik,
                row["Accession Number"],
                row["Primary Document"]
            )

            filing_urls.append(filing_url)

        filings_display["SEC URL"] = filing_urls

        st.dataframe(
            filings_display,
            use_container_width=True
        )

        # =================================================
        # COMPANY FACTS
        # =================================================

        facts = get_company_facts(cik)

        revenue_df = extract_revenue_data(facts)

        if revenue_df is not None:

            st.subheader("Revenue Data")

            st.dataframe(
                revenue_df,
                use_container_width=True
            )

            # =============================================
            # CALCULATE REVENUE GROWTH
            # =============================================

            try:

                annual_df = revenue_df[
                    revenue_df["fp"] == "FY"
                ].copy()

                annual_df = annual_df.sort_values("fy")

                annual_df["Revenue Growth %"] = (
                    annual_df["val"].pct_change() * 100
                )

                st.subheader("Annual Revenue Growth")

                st.dataframe(
                    annual_df,
                    use_container_width=True
                )

            except:

                st.warning(
                    "Could not calculate revenue growth."
                )

        else:

            st.warning("Revenue data not found.")
