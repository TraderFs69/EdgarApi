# =========================================================
# TEA Institutional SEC Scanner
# CLEAN XBRL VERSION
# Reliable Financial Extraction
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
# GET METRIC
# =========================================================

def get_metric(data, keys):

    try:

        us_gaap = data["facts"]["us-gaap"]

        for key in keys:

            if key in us_gaap:

                units = us_gaap[key]["units"]

                if "USD" in units:

                    df = pd.DataFrame(
                        units["USD"]
                    )

                    return df

    except:
        pass

    return None


# =========================================================
# CLEAN ANNUAL DATA
# =========================================================

def clean_annual(df):

    if df is None:
        return None

    required = ["fy", "fp", "val"]

    for col in required:

        if col not in df.columns:
            return None

    df = df[df["fp"] == "FY"].copy()

    if len(df) == 0:
        return None

    if "frame" in df.columns:
        df = df[df["frame"].isna()]

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(subset=["val"])

    df = df.sort_values("fy")

    df = df.drop_duplicates(
        subset=["fy"],
        keep="last"
    )

    return df


# =========================================================
# BUILD TRUE QUARTERS
# =========================================================

def build_quarters(df):

    if df is None:
        return None

    required = ["fy", "fp", "val"]

    for col in required:

        if col not in df.columns:
            return None

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

    if "frame" in df.columns:
        df = df[df["frame"].isna()]

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(subset=["val"])

    rows = []

    years = sorted(
        df["fy"].dropna().unique()
    )

    for year in years:

        year_df = df[df["fy"] == year]

        q1 = year_df[
            year_df["fp"] == "Q1"
        ]["val"]

        q2 = year_df[
            year_df["fp"] == "Q2"
        ]["val"]

        q3 = year_df[
            year_df["fp"] == "Q3"
        ]["val"]

        fy = year_df[
            year_df["fp"] == "FY"
        ]["val"]

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

        # TRUE QUARTERS

        real_q1 = q1_val

        real_q2 = None
        real_q3 = None
        real_q4 = None

        if (
            q2_ytd is not None
            and q1_val is not None
        ):

            real_q2 = (
                q2_ytd - q1_val
            )

        if (
            q3_ytd is not None
            and q2_ytd is not None
        ):

            real_q3 = (
                q3_ytd - q2_ytd
            )

        if (
            fy_val is not None
            and q3_ytd is not None
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

        for q, value in quarters.items():

            if (
                value is not None
                and value > 0
            ):

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
# GET LATEST VALUE
# =========================================================

def latest(df):

    if df is None:
        return None

    if len(df) == 0:
        return None

    return df.iloc[-1]["val"]


# =========================================================
# GROWTH
# =========================================================

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
    # GET DATA
    # =====================================================

    data = get_company_facts(cik)

    # =====================================================
    # RAW METRICS
    # =====================================================

    revenue_raw = get_metric(
        data,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues"
        ]
    )

    operating_income_raw = get_metric(
        data,
        [
            "OperatingIncomeLoss"
        ]
    )

    gross_profit_raw = get_metric(
        data,
        [
            "GrossProfit"
        ]
    )

    net_income_raw = get_metric(
        data,
        [
            "NetIncomeLoss"
        ]
    )

    operating_cf_raw = get_metric(
        data,
        [
            "NetCashProvidedByUsedInOperatingActivities"
        ]
    )

    capex_raw = get_metric(
        data,
        [
            "PaymentsToAcquirePropertyPlantAndEquipment"
        ]
    )

    cash_raw = get_metric(
        data,
        [
            "CashAndCashEquivalentsAtCarryingValue"
        ]
    )

    # =====================================================
    # CLEAN DATA
    # =====================================================

    revenue = clean_annual(
        revenue_raw
    )

    operating_income = clean_annual(
        operating_income_raw
    )

    gross_profit = clean_annual(
        gross_profit_raw
    )

    net_income = clean_annual(
        net_income_raw
    )

    operating_cf = clean_annual(
        operating_cf_raw
    )

    capex = clean_annual(
        capex_raw
    )

    cash = clean_annual(
        cash_raw
    )

    # =====================================================
    # QUARTERS
    # =====================================================

    quarterly_revenue = build_quarters(
        revenue_raw
    )

    # =====================================================
    # GROWTH
    # =====================================================

    revenue = add_growth(
        revenue
    )

    # =====================================================
    # LATEST VALUES
    # =====================================================

    latest_revenue = latest(
        revenue
    )

    latest_operating_income = latest(
        operating_income
    )

    latest_gross_profit = latest(
        gross_profit
    )

    latest_net_income = latest(
        net_income
    )

    latest_ocf = latest(
        operating_cf
    )

    latest_capex = latest(
        capex
    )

    latest_cash = latest(
        cash
    )

    # =====================================================
    # FREE CASH FLOW
    # =====================================================

    free_cash_flow = None

    if (
        latest_ocf is not None
        and latest_capex is not None
    ):

        free_cash_flow = (
            latest_ocf
            - abs(latest_capex)
        )

    # =====================================================
    # MARGINS
    # =====================================================

    operating_margin = None
    gross_margin = None
    net_margin = None
    fcf_margin = None

    if (
        latest_revenue is not None
        and latest_operating_income is not None
    ):

        operating_margin = (
            latest_operating_income
            / latest_revenue
        ) * 100

    if (
        latest_revenue is not None
        and latest_gross_profit is not None
    ):

        gross_margin = (
            latest_gross_profit
            / latest_revenue
        ) * 100

    if (
        latest_revenue is not None
        and latest_net_income is not None
    ):

        net_margin = (
            latest_net_income
            / latest_revenue
        ) * 100

    if (
        latest_revenue is not None
        and free_cash_flow is not None
    ):

        fcf_margin = (
            free_cash_flow
            / latest_revenue
        ) * 100

    # =====================================================
    # REVENUE GROWTH
    # =====================================================

    latest_growth = None

    if revenue is not None:

        latest_growth = revenue.iloc[-1][
            "Growth %"
        ]

    # =====================================================
    # RULE OF 40
    # =====================================================

    rule_of_40 = None

    if (
        latest_growth is not None
        and operating_margin is not None
    ):

        rule_of_40 = (
            latest_growth
            + operating_margin
        )

    # =====================================================
    # DISPLAY
    # =====================================================

    st.subheader(
        "Key Metrics"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Revenue",
            f"${latest_revenue:,.0f}"
            if latest_revenue
            else "N/A"
        )

        st.metric(
            "Revenue Growth %",
            f"{latest_growth:.2f}%"
            if latest_growth is not None
            else "N/A"
        )

    with col2:

        st.metric(
            "Operating Margin",
            f"{operating_margin:.2f}%"
            if operating_margin is not None
            else "N/A"
        )

        st.metric(
            "Gross Margin",
            f"{gross_margin:.2f}%"
            if gross_margin is not None
            else "N/A"
        )

    with col3:

        st.metric(
            "Net Margin",
            f"{net_margin:.2f}%"
            if net_margin is not None
            else "N/A"
        )

        st.metric(
            "FCF Margin",
            f"{fcf_margin:.2f}%"
            if fcf_margin is not None
            else "N/A"
        )

    with col4:

        st.metric(
            "Rule of 40",
            f"{rule_of_40:.2f}"
            if rule_of_40 is not None
            else "N/A"
        )

        st.metric(
            "Cash",
            f"${latest_cash:,.0f}"
            if latest_cash
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
