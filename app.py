# app.py

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
    page_title="TEA Institutional Fundamental Scanner",
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
def get_company_facts(cik):

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def get_financial_metric(data, possible_keys):

    us_gaap = data["facts"]["us-gaap"]

    for key in possible_keys:

        if key in us_gaap:

            try:

                metric = us_gaap[key]["units"]["USD"]

                df = pd.DataFrame(metric)

                return df

            except:
                pass

    return None


def clean_annual_data(df):

    if df is None:
        return None

    if "fp" not in df.columns:
        return None

    df = df[df["fp"] == "FY"].copy()

    columns = []

    for col in ["fy", "val", "filed"]:
        if col in df.columns:
            columns.append(col)

    df = df[columns]

    df = df.sort_values("fy")

    df = df.drop_duplicates(subset=["fy"], keep="last")

    return df


def latest_value(df):

    if df is None or len(df) == 0:
        return None

    return df.iloc[-1]["val"]


def calculate_growth(df):

    if df is None:
        return None

    df["Growth %"] = df["val"].pct_change() * 100

    return df


# =========================================================
# UI
# =========================================================

st.title("TEA Institutional Fundamental Scanner")

ticker = st.text_input(
    "Ticker",
    value="NVDA"
)

if st.button("Analyze"):

    cik = get_cik_from_ticker(ticker)

    if cik is None:

        st.error("Ticker not found")

        st.stop()

    st.success(f"CIK: {cik}")

    data = get_company_facts(cik)

    # =====================================================
    # EXTRACT METRICS
    # =====================================================

    revenue = clean_annual_data(
        get_financial_metric(
            data,
            [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "Revenues"
            ]
        )
    )

    operating_income = clean_annual_data(
        get_financial_metric(
            data,
            [
                "OperatingIncomeLoss"
            ]
        )
    )

    net_income = clean_annual_data(
        get_financial_metric(
            data,
            [
                "NetIncomeLoss"
            ]
        )
    )

    gross_profit = clean_annual_data(
        get_financial_metric(
            data,
            [
                "GrossProfit"
            ]
        )
    )

    operating_cash_flow = clean_annual_data(
        get_financial_metric(
            data,
            [
                "NetCashProvidedByUsedInOperatingActivities"
            ]
        )
    )

    capex = clean_annual_data(
        get_financial_metric(
            data,
            [
                "PaymentsToAcquirePropertyPlantAndEquipment"
            ]
        )
    )

    assets = clean_annual_data(
        get_financial_metric(
            data,
            [
                "Assets"
            ]
        )
    )

    liabilities = clean_annual_data(
        get_financial_metric(
            data,
            [
                "Liabilities"
            ]
        )
    )

    cash = clean_annual_data(
        get_financial_metric(
            data,
            [
                "CashAndCashEquivalentsAtCarryingValue"
            ]
        )
    )

    # =====================================================
    # CALCULATIONS
    # =====================================================

    latest_revenue = latest_value(revenue)

    latest_operating_income = latest_value(operating_income)

    latest_net_income = latest_value(net_income)

    latest_gross_profit = latest_value(gross_profit)

    latest_ocf = latest_value(operating_cash_flow)

    latest_capex = latest_value(capex)

    latest_assets = latest_value(assets)

    latest_liabilities = latest_value(liabilities)

    latest_cash = latest_value(cash)

    free_cash_flow = None

    if latest_ocf and latest_capex:

        free_cash_flow = latest_ocf - abs(latest_capex)

    # =====================================================
    # MARGINS
    # =====================================================

    operating_margin = None
    net_margin = None
    gross_margin = None
    fcf_margin = None

    if latest_revenue and latest_operating_income:
        operating_margin = (
            latest_operating_income / latest_revenue
        ) * 100

    if latest_revenue and latest_net_income:
        net_margin = (
            latest_net_income / latest_revenue
        ) * 100

    if latest_revenue and latest_gross_profit:
        gross_margin = (
            latest_gross_profit / latest_revenue
        ) * 100

    if latest_revenue and free_cash_flow:
        fcf_margin = (
            free_cash_flow / latest_revenue
        ) * 100

    # =====================================================
    # REVENUE GROWTH
    # =====================================================

    revenue = calculate_growth(revenue)

    latest_growth = None

    if revenue is not None:

        latest_growth = revenue.iloc[-1]["Growth %"]

    # =====================================================
    # RULE OF 40
    # =====================================================

    rule_of_40 = None

    if latest_growth and operating_margin:

        rule_of_40 = (
            latest_growth + operating_margin
        )

    # =====================================================
    # SCORECARDS
    # =====================================================

    st.subheader("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Revenue",
            f"${latest_revenue:,.0f}"
            if latest_revenue else "N/A"
        )

        st.metric(
            "Revenue Growth %",
            f"{latest_growth:.2f}%"
            if latest_growth else "N/A"
        )

    with col2:

        st.metric(
            "Operating Margin",
            f"{operating_margin:.2f}%"
            if operating_margin else "N/A"
        )

        st.metric(
            "Gross Margin",
            f"{gross_margin:.2f}%"
            if gross_margin else "N/A"
        )

    with col3:

        st.metric(
            "Net Margin",
            f"{net_margin:.2f}%"
            if net_margin else "N/A"
        )

        st.metric(
            "FCF Margin",
            f"{fcf_margin:.2f}%"
            if fcf_margin else "N/A"
        )

    with col4:

        st.metric(
            "Rule of 40",
            f"{rule_of_40:.2f}"
            if rule_of_40 else "N/A"
        )

        st.metric(
            "Cash",
            f"${latest_cash:,.0f}"
            if latest_cash else "N/A"
        )

    # =====================================================
    # BALANCE SHEET
    # =====================================================

    st.subheader("Balance Sheet")

    balance_df = pd.DataFrame({
        "Metric": [
            "Assets",
            "Liabilities",
            "Cash",
            "Free Cash Flow"
        ],
        "Value": [
            latest_assets,
            latest_liabilities,
            latest_cash,
            free_cash_flow
        ]
    })

    st.dataframe(
        balance_df,
        use_container_width=True
    )

    # =====================================================
    # REVENUE TABLE
    # =====================================================

    st.subheader("Revenue History")

    st.dataframe(
        revenue,
        use_container_width=True
    )

    # =====================================================
    # CHART
    # =====================================================

    chart_df = revenue.copy()

    fig = px.line(
        chart_df,
        x="fy",
        y="val",
        title=f"{ticker} Revenue Growth"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
