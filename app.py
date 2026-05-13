# =========================================================
# TEA Institutional SEC Scanner
# COMPLETE CORRECTED VERSION
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
    page_title="TEA Institutional Scanner",
    layout="wide"
)

# =========================================================
# GET CIK
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


# =========================================================
# GET COMPANY FACTS
# =========================================================

@st.cache_data
def get_company_facts(cik):

    url = (
        f"https://data.sec.gov/api/xbrl/"
        f"companyfacts/CIK{cik}.json"
    )

    response = requests.get(
        url,
        headers=HEADERS
    )

    return response.json()


# =========================================================
# GET BEST METRIC
# =========================================================

def get_metric(data, keys):

    try:

        us_gaap = data["facts"]["us-gaap"]

        best_df = None
        best_latest_year = 0
        best_key = None

        for key in keys:

            if key not in us_gaap:
                continue

            units = us_gaap[key]["units"]

            if "USD" not in units:
                continue

            df = pd.DataFrame(
                units["USD"]
            )

            if "fy" not in df.columns:
                continue

            years = pd.to_numeric(
                df["fy"],
                errors="coerce"
            ).dropna()

            if len(years) == 0:
                continue

            latest_year = years.max()

            if latest_year > best_latest_year:

                best_latest_year = latest_year
                best_df = df
                best_key = key

        if best_key is not None:

            st.info(
                f"Using XBRL tag: {best_key}"
            )

        return best_df

    except Exception as e:

        st.error(
            f"Metric error: {e}"
        )

    return None


# =========================================================
# CLEAN ANNUAL
# =========================================================

def clean_annual(df):

    if df is None:
        return None

    required = [
        "fy",
        "fp",
        "val",
        "filed"
    ]

    for col in required:

        if col not in df.columns:
            return None

    # Annual only
    df = df[
        df["fp"] == "FY"
    ].copy()

    if len(df) == 0:
        return None

    # Numeric
    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["val"]
    )

    # Filed date
    df["filed"] = pd.to_datetime(
        df["filed"]
    )

    # Sort
    df = df.sort_values(
        ["fy", "filed"]
    )

    # Keep newest filing
    df = df.drop_duplicates(
        subset=["fy"],
        keep="last"
    )

    # Sort again
    df = df.sort_values("fy")

    # Last 5 years
    df = df.tail(5)

    return df


# =========================================================
# BUILD TRUE QUARTERS
# =========================================================

def build_quarters(df):

    if df is None:
        return None

    required = [
        "fy",
        "fp",
        "val",
        "filed",
        "form"
    ]

    for col in required:

        if col not in df.columns:
            return None

    # =====================================================
    # KEEP ONLY RELEVANT PERIODS
    # =====================================================

    df = df[
        df["fp"].isin([
            "Q1",
            "Q2",
            "Q3",
            "FY"
        ])
    ].copy()

    if len(df) == 0:
        return None

    # =====================================================
    # NUMERIC
    # =====================================================

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["val"]
    )

    # =====================================================
    # KEEP ONLY REAL FILINGS
    # =====================================================

    df = df[
        df["form"].isin([
            "10-Q",
            "10-K"
        ])
    ]

    # =====================================================
    # FILED DATE
    # =====================================================

    df["filed"] = pd.to_datetime(
        df["filed"]
    )

    # =====================================================
    # SORT
    # =====================================================

    df = df.sort_values(
        ["fy", "filed"]
    )

    rows = []

    years = sorted(
        df["fy"]
        .dropna()
        .unique()
    )

    years = years[-5:]

    current_year = pd.Timestamp.now().year

    for year in years:

        year_df = df[
            df["fy"] == year
        ].sort_values("filed")

        # =================================================
        # Q1
        # =================================================

        q1 = year_df[
            (year_df["fp"] == "Q1")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # Q2 YTD
        # =================================================

        q2 = year_df[
            (year_df["fp"] == "Q2")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # Q3 YTD
        # =================================================

        q3 = year_df[
            (year_df["fp"] == "Q3")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # FY
        # =================================================

        fy = year_df[
            (year_df["fp"] == "FY")
            &
            (year_df["form"] == "10-K")
        ]["val"]

        # =================================================
        # VALUES
        # =================================================

        q1_val = (
            q1.iloc[-1]
            if len(q1)
            else None
        )

        q2_ytd = (
            q2.iloc[-1]
            if len(q2)
            else None
        )

        q3_ytd = (
            q3.iloc[-1]
            if len(q3)
            else None
        )

        fy_val = (
            fy.iloc[-1]
            if len(fy)
            else None
        )

        # =================================================
        # TRUE QUARTERS
        # =================================================

        real_q1 = q1_val

        real_q2 = None
        real_q3 = None
        real_q4 = None

        # Q2
        if (
            q2_ytd is not None
            and q1_val is not None
        ):

            real_q2 = (
                q2_ytd - q1_val
            )

        # Q3
        if (
            q3_ytd is not None
            and q2_ytd is not None
        ):

            real_q3 = (
                q3_ytd - q2_ytd
            )

        # Q4
        if (
            fy_val is not None
            and q3_ytd is not None
            and year < current_year
        ):

            real_q4 = (
                fy_val - q3_ytd
            )

        quarters = {
            "Q1": real_q1,
            "Q2": real_q2,
            "Q3": real_q3,
            "Q4": real_q4
        }

        # =================================================
        # STORE
        # =================================================

        for q, value in quarters.items():

            if (
                value is None
                or value <= 0
            ):
                continue

            rows.append({
                "Quarter": f"{year}-{q}",
                "Revenue": value
            })

    if len(rows) == 0:
        return None

    result = pd.DataFrame(rows)

    result = result.sort_values(
        "Quarter"
    )

    # =====================================================
    # GROWTH
    # =====================================================

    result["QoQ Growth %"] = (
        result["Revenue"]
        .pct_change() * 100
    )

    result["YoY Growth %"] = (
        result["Revenue"]
        .pct_change(4) * 100
    )

    return result


# =========================================================
# HELPERS
# =========================================================

def latest(df):

    if df is None:
        return None

    if len(df) == 0:
        return None

    return df.iloc[-1]["val"]


def add_growth(df):

    if df is None:
        return None

    df = df.copy()

    df["Growth %"] = (
        df["val"]
        .pct_change() * 100
    )

    return df


# =========================================================
# UI
# =========================================================

st.title(
    "TEA Institutional SEC Scanner"
)

ticker = st.text_input(
    "Ticker",
    value="NVDA"
)

if st.button("Analyze"):

    # =====================================================
    # GET CIK
    # =====================================================

    cik = get_cik_from_ticker(
        ticker
    )

    if cik is None:

        st.error(
            "Ticker not found"
        )

        st.stop()

    st.success(
        f"CIK: {cik}"
    )

    # =====================================================
    # LOAD DATA
    # =====================================================

    data = get_company_facts(cik)

    # =====================================================
    # REVENUE
    # =====================================================

    revenue_raw = get_metric(
        data,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues"
        ]
    )

    # =====================================================
    # CLEAN
    # =====================================================

    revenue = clean_annual(
        revenue_raw
    )

    quarterly_revenue = build_quarters(
        revenue_raw
    )

    revenue = add_growth(
        revenue
    )

    latest_revenue = latest(
        revenue
    )

    latest_growth = None

    if revenue is not None:

        latest_growth = revenue.iloc[-1][
            "Growth %"
        ]

    # =====================================================
    # DISPLAY
    # =====================================================

    st.subheader(
        "Key Metrics"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Revenue",
            f"${latest_revenue:,.0f}"
            if latest_revenue
            else "N/A"
        )

    with col2:

        st.metric(
            "Revenue Growth %",
            f"{latest_growth:.2f}%"
            if latest_growth is not None
            else "N/A"
        )

    # =====================================================
    # ANNUAL TABLE
    # =====================================================

    st.subheader(
        "Annual Revenue"
    )

    st.dataframe(
        revenue,
        use_container_width=True
    )

    # =====================================================
    # QUARTERLY TABLE
    # =====================================================

    st.subheader(
        "Quarterly Revenue"
    )

    if quarterly_revenue is not None:

        st.dataframe(
            quarterly_revenue,
            use_container_width=True
        )

        # Validation
        st.subheader(
            "Quarter Validation"
        )

        validation = (
            quarterly_revenue
            .groupby(
                quarterly_revenue[
                    "Quarter"
                ].str[:4]
            )["Revenue"]
            .sum()
            .reset_index()
        )

        validation.columns = [
            "Year",
            "Quarter Sum"
        ]

        st.dataframe(
            validation,
            use_container_width=True
        )

    else:

        st.warning(
            "Quarterly revenue unavailable"
        )

    # =====================================================
    # CHARTS
    # =====================================================

    fig_annual = px.line(
        revenue,
        x="fy",
        y="val",
        title=f"{ticker} Annual Revenue"
    )

    st.plotly_chart(
        fig_annual,
        use_container_width=True
    )

    if quarterly_revenue is not None:

        fig_q = px.line(
            quarterly_revenue,
            x="Quarter",
            y="Revenue",
            title=f"{ticker} Quarterly Revenue"
        )

        st.plotly_chart(
            fig_q,
            use_container_width=True
        )
