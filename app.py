# =========================================================
# TEA HTML Filing Parser
# Read REAL SEC Financial Statements
# =========================================================

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# =========================================================
# CONFIG
# =========================================================

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

st.set_page_config(
    page_title="TEA HTML Filing Parser",
    layout="wide"
)

# =========================================================
# FUNCTIONS
# =========================================================

@st.cache_data
def get_cik_from_ticker(ticker):

    url = "https://www.sec.gov/files/company_tickers.json"

    data = requests.get(
        url,
        headers=HEADERS
    ).json()

    for company in data.values():

        if company["ticker"].upper() == ticker.upper():

            return str(
                company["cik_str"]
            ).zfill(10)

    return None


@st.cache_data
def get_company_submissions(cik):

    url = (
        f"https://data.sec.gov/submissions/"
        f"CIK{cik}.json"
    )

    response = requests.get(
        url,
        headers=HEADERS
    )

    return response.json()


def extract_filings(submissions):

    recent = submissions["filings"]["recent"]

    df = pd.DataFrame({
        "form": recent["form"],
        "filingDate": recent["filingDate"],
        "accessionNumber": recent["accessionNumber"],
        "primaryDocument": recent["primaryDocument"]
    })

    filings = df[
        df["form"].isin(["10-K", "10-Q"])
    ].copy()

    return filings


def build_filing_url(
    cik,
    accession,
    document
):

    accession_clean = accession.replace("-", "")

    url = (
        f"https://www.sec.gov/Archives/"
        f"edgar/data/{int(cik)}/"
        f"{accession_clean}/{document}"
    )

    return url


@st.cache_data
def download_filing_html(url):

    response = requests.get(
        url,
        headers=HEADERS
    )

    return response.text


def extract_tables_from_html(html):

    try:

        tables = pd.read_html(html)

        return tables

    except:

        return []


def find_income_statement_tables(tables):

    keywords = [
        "revenue",
        "net income",
        "operating income",
        "gross profit"
    ]

    matching_tables = []

    for i, table in enumerate(tables):

        table_str = str(table).lower()

        matches = sum(
            keyword in table_str
            for keyword in keywords
        )

        if matches >= 2:

            matching_tables.append(
                (i, table)
            )

    return matching_tables


# =========================================================
# UI
# =========================================================

st.title(
    "TEA HTML SEC Filing Parser"
)

ticker = st.text_input(
    "Ticker",
    value="NVDA"
)

if st.button("Load Filings"):

    # =====================================================
    # GET CIK
    # =====================================================

    cik = get_cik_from_ticker(ticker)

    if cik is None:

        st.error("Ticker not found")

        st.stop()

    st.success(f"CIK Found: {cik}")

    # =====================================================
    # GET FILINGS
    # =====================================================

    submissions = get_company_submissions(cik)

    filings = extract_filings(submissions)

    filings = filings.head(10)

    # =====================================================
    # BUILD URLS
    # =====================================================

    filing_urls = []

    for _, row in filings.iterrows():

        filing_url = build_filing_url(
            cik,
            row["accessionNumber"],
            row["primaryDocument"]
        )

        filing_urls.append(filing_url)

    filings["SEC URL"] = filing_urls

    # =====================================================
    # DISPLAY FILINGS
    # =====================================================

    st.subheader("Recent 10-K / 10-Q Filings")

    st.dataframe(
        filings,
        use_container_width=True
    )

    # =====================================================
    # SELECT FILING
    # =====================================================

    filing_options = {}

    for idx, row in filings.iterrows():

        label = (
            f"{row['form']} | "
            f"{row['filingDate']}"
        )

        filing_options[label] = row["SEC URL"]

    selected_filing = st.selectbox(
        "Select Filing",
        list(filing_options.keys())
    )

    filing_url = filing_options[
        selected_filing
    ]

    st.write(filing_url)

    # =====================================================
    # DOWNLOAD HTML
    # =====================================================

    with st.spinner("Downloading filing..."):

        html = download_filing_html(
            filing_url
        )

    st.success("Filing downloaded")

    # =====================================================
    # EXTRACT TABLES
    # =====================================================

    with st.spinner("Extracting tables..."):

        tables = extract_tables_from_html(
            html
        )

    st.success(
        f"{len(tables)} tables extracted"
    )

    # =====================================================
    # FIND FINANCIAL TABLES
    # =====================================================

    financial_tables = (
        find_income_statement_tables(
            tables
        )
    )

    # =====================================================
    # DISPLAY TABLES
    # =====================================================

    st.subheader(
        "Financial Statement Tables"
    )

    if len(financial_tables) == 0:

        st.warning(
            "No financial tables detected"
        )

    else:

        for idx, table in financial_tables:

            st.markdown(
                f"### Table {idx}"
            )

            st.dataframe(
                table,
                use_container_width=True
            )
