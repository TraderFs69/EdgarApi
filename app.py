# =========================================================
# TEA SEC HTML Filing Parser
# Improved Financial Table Detection
# =========================================================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# =========================================================
# CONFIG
# =========================================================

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

st.set_page_config(
    page_title="TEA SEC Filing Parser",
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
        "Form": recent["form"],
        "Filing Date": recent["filingDate"],
        "Accession Number": recent["accessionNumber"],
        "Primary Document": recent["primaryDocument"]
    })

    filings = df[
        df["Form"].isin(["10-K", "10-Q"])
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


# =========================================================
# IMPROVED FINANCIAL TABLE DETECTION
# =========================================================

def find_financial_tables(tables):

    keywords = [
        "revenue",
        "revenues",
        "net income",
        "operating income",
        "gross profit",
        "assets",
        "liabilities",
        "cash flows",
        "cash flow",
        "earnings per share",
        "cost of revenue",
        "operating expenses",
        "stockholders’ equity",
        "shareholders’ equity",
        "total assets",
        "total liabilities"
    ]

    results = []

    for idx, table in enumerate(tables):

        try:

            table_str = str(table).lower()

            score = 0

            matched_keywords = []

            for keyword in keywords:

                if keyword in table_str:

                    score += 1
                    matched_keywords.append(keyword)

            # Ignore useless tiny tables
            if (
                score >= 3
                and len(table.columns) >= 2
                and len(table) >= 4
            ):

                results.append({
                    "index": idx,
                    "score": score,
                    "keywords": matched_keywords,
                    "table": table
                })

        except:
            pass

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results


# =========================================================
# UI
# =========================================================

st.title(
    "TEA SEC HTML Filing Parser"
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
    # GET SUBMISSIONS
    # =====================================================

    submissions = get_company_submissions(cik)

    filings = extract_filings(submissions)

    filings = filings.head(10)

    # =====================================================
    # BUILD URLs
    # =====================================================

    filing_urls = []

    for _, row in filings.iterrows():

        filing_url = build_filing_url(
            cik,
            row["Accession Number"],
            row["Primary Document"]
        )

        filing_urls.append(filing_url)

    filings["SEC URL"] = filing_urls

    # =====================================================
    # DISPLAY FILINGS
    # =====================================================

    st.subheader(
        "Recent 10-K / 10-Q Filings"
    )

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
            f"{row['Form']} | "
            f"{row['Filing Date']}"
        )

        filing_options[label] = row["SEC URL"]

    selected_filing = st.selectbox(
        "Select Filing",
        list(filing_options.keys())
    )

    filing_url = filing_options[
        selected_filing
    ]

    st.markdown(
        f"### SEC Filing URL"
    )

    st.write(filing_url)

    # =====================================================
    # DOWNLOAD HTML
    # =====================================================

    with st.spinner(
        "Downloading filing..."
    ):

        html = download_filing_html(
            filing_url
        )

    st.success(
        "Filing downloaded"
    )

    # =====================================================
    # EXTRACT TABLES
    # =====================================================

    with st.spinner(
        "Extracting HTML tables..."
    ):

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
        find_financial_tables(
            tables
        )
    )

    # =====================================================
    # DISPLAY TABLES
    # =====================================================

    st.subheader(
        "Detected Financial Tables"
    )

    if len(financial_tables) == 0:

        st.warning(
            "No financial tables detected"
        )

    else:

        for item in financial_tables:

            idx = item["index"]

            score = item["score"]

            keywords = item["keywords"]

            table = item["table"]

            st.markdown(
                f"""
                ### Table {idx}

                **Detection Score:** {score}

                **Keywords Found:**  
                {', '.join(keywords)}
                """
            )

            st.dataframe(
                table,
                use_container_width=True
            )

            st.markdown("---")
