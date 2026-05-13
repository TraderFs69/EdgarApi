# =========================================================
# TEA Institutional SEC Scanner
# FULL VERSION WITH IMPORTANT METRICS
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
# FORMATTERS
# =========================================================

def format_number(value):

    if value is None:
        return "N/A"

    value = float(value)

    abs_value = abs(value)

    if abs_value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"

    elif abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    elif abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    elif abs_value >= 1_000:
        return f"{value / 1_000:.2f}K"

    return f"{value:,.0f}"


def format_percent(value):

    if value is None:
        return "N/A"

    return f"{value:.2f}%"


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

    df = df[
        df["fp"] == "FY"
    ].copy()

    if len(df) == 0:
        return None

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["val"]
    )

    df["filed"] = pd.to_datetime(
        df["filed"]
    )

    df = df.sort_values(
        ["fy", "filed"]
    )

    df = df.drop_duplicates(
        subset=["fy"],
        keep="last"
    )

    df = df.sort_values("fy")

    df = df.tail(5)

    return df


# =========================================================
# ADD GROWTH
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
# LATEST VALUE
# =========================================================

def latest(df):

    if df is None:
        return None

    if len(df) == 0:
        return None

    return df.iloc[-1]["val"]


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
    # CIK
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
    # IMPORTANT METRICS
    # =====================================================

    revenue_raw = get_metric(
        data,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues"
        ]
    )

    gross_profit_raw = get_metric(
        data,
        [
            "GrossProfit"
        ]
    )

    operating_income_raw = get_metric(
        data,
        [
            "OperatingIncomeLoss"
        ]
    )

    net_income_raw = get_metric(
        data,
        [
            "NetIncomeLoss"
        ]
    )

    cash_raw = get_metric(
        data,
        [
            "CashAndCashEquivalentsAtCarryingValue"
        ]
    )

    assets_raw = get_metric(
        data,
        [
            "Assets"
        ]
    )

    liabilities_raw = get_metric(
        data,
        [
            "Liabilities"
        ]
    )

    equity_raw = get_metric(
        data,
        [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
        ]
    )

    debt_raw = get_metric(
        data,
        [
            "LongTermDebt",
            "LongTermDebtNoncurrent"
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

    rd_raw = get_metric(
        data,
        [
            "ResearchAndDevelopmentExpense"
        ]
    )

    sga_raw = get_metric(
        data,
        [
            "SellingGeneralAndAdministrativeExpense"
        ]
    )

    # =====================================================
    # CLEAN DATA
    # =====================================================

    revenue = add_growth(
        clean_annual(revenue_raw)
    )

    gross_profit = add_growth(
        clean_annual(gross_profit_raw)
    )

    operating_income = add_growth(
        clean_annual(operating_income_raw)
    )

    net_income = add_growth(
        clean_annual(net_income_raw)
    )

    cash = clean_annual(cash_raw)

    assets = clean_annual(assets_raw)

    liabilities = clean_annual(liabilities_raw)

    equity = clean_annual(equity_raw)

    debt = clean_annual(debt_raw)

    operating_cf = add_growth(
        clean_annual(operating_cf_raw)
    )

    capex = clean_annual(capex_raw)

    rd = clean_annual(rd_raw)

    sga = clean_annual(sga_raw)

    # =====================================================
    # LATEST VALUES
    # =====================================================

    latest_revenue = latest(revenue)
    latest_gross_profit = latest(gross_profit)
    latest_operating_income = latest(operating_income)
    latest_net_income = latest(net_income)
    latest_cash = latest(cash)
    latest_assets = latest(assets)
    latest_liabilities = latest(liabilities)
    latest_equity = latest(equity)
    latest_debt = latest(debt)
    latest_ocf = latest(operating_cf)
    latest_capex = latest(capex)
    latest_rd = latest(rd)
    latest_sga = latest(sga)

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

    gross_margin = None
    operating_margin = None
    net_margin = None
    fcf_margin = None

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
        and latest_operating_income is not None
    ):

        operating_margin = (
            latest_operating_income
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
    # ROE
    # =====================================================

    roe = None

    if (
        latest_equity is not None
        and latest_net_income is not None
    ):

        roe = (
            latest_net_income
            / latest_equity
        ) * 100

    # =====================================================
    # DEBT TO EQUITY
    # =====================================================

    debt_to_equity = None

    if (
        latest_equity is not None
        and latest_debt is not None
    ):

        debt_to_equity = (
            latest_debt
            / latest_equity
        )

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
        "Important Metrics"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Revenue",
            format_number(
                latest_revenue
            )
        )

        st.metric(
            "Revenue Growth",
            format_percent(
                latest_growth
            )
        )

        st.metric(
            "Gross Profit",
            format_number(
                latest_gross_profit
            )
        )

        st.metric(
            "Gross Margin",
            format_percent(
                gross_margin
            )
        )

    with col2:

        st.metric(
            "Operating Income",
            format_number(
                latest_operating_income
            )
        )

        st.metric(
            "Operating Margin",
            format_percent(
                operating_margin
            )
        )

        st.metric(
            "Net Income",
            format_number(
                latest_net_income
            )
        )

        st.metric(
            "Net Margin",
            format_percent(
                net_margin
            )
        )

    with col3:

        st.metric(
            "Operating Cash Flow",
            format_number(
                latest_ocf
            )
        )

        st.metric(
            "Free Cash Flow",
            format_number(
                free_cash_flow
            )
        )

        st.metric(
            "FCF Margin",
            format_percent(
                fcf_margin
            )
        )

        st.metric(
            "Rule of 40",
            format_percent(
                rule_of_40
            )
        )

    with col4:

        st.metric(
            "Cash",
            format_number(
                latest_cash
            )
        )

        st.metric(
            "Debt",
            format_number(
                latest_debt
            )
        )

        st.metric(
            "ROE",
            format_percent(
                roe
            )
        )

        st.metric(
            "Debt / Equity",
            (
                f"{debt_to_equity:.2f}"
                if debt_to_equity is not None
                else "N/A"
            )
        )

    # =====================================================
    # EXTRA METRICS
    # =====================================================

    st.subheader(
        "Additional Metrics"
    )

    col5, col6, col7, col8 = st.columns(4)

    with col5:

        st.metric(
            "Assets",
            format_number(
                latest_assets
            )
        )

    with col6:

        st.metric(
            "Liabilities",
            format_number(
                latest_liabilities
            )
        )

    with col7:

        st.metric(
            "R&D",
            format_number(
                latest_rd
            )
        )

    with col8:

        st.metric(
            "SG&A",
            format_number(
                latest_sga
            )
        )

    # =====================================================
    # TABLES
    # =====================================================

    st.subheader(
        "Annual Revenue"
    )

    st.dataframe(
        revenue,
        use_container_width=True
    )

    # =====================================================
    # CHART
    # =====================================================

    fig = px.line(
        revenue,
        x="fy",
        y="val",
        title=f"{ticker} Revenue"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
