# =========================================================
# TEA Institutional SEC Scanner
# FULL VERSION WITH BEAUTIFUL TABLES
# =========================================================

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
    page_title="TEA Institutional Scanner",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #0e1117;
    color: white;
}

h1, h2, h3 {
    color: #ff8c00;
}

div[data-testid="metric-container"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 15px;
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# FORMATTERS
# =========================================================

def format_number(value):

    if value is None or pd.isna(value):
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

    if value is None or pd.isna(value):
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

        return best_df

    except:
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
# BUILD QUARTERS
# =========================================================

def build_quarters(df):

    if df is None:
        return None

    required = [
        "fy",
        "fp",
        "val",
        "filed",
        "form",
        "end"
    ]

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

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["val"]
    )

    df = df[
        df["form"].isin([
            "10-Q",
            "10-K"
        ])
    ]

    df["filed"] = pd.to_datetime(
        df["filed"]
    )

    df["end"] = pd.to_datetime(
        df["end"]
    )

    today = pd.Timestamp.now()

    df = df[
        df["end"] <= today
    ]

    rows = []

    years = sorted(
        df["fy"]
        .dropna()
        .unique()
    )[-2:]

    current_year = today.year

    for year in years:

        year_df = df[
            df["fy"] == year
        ]

        q1 = year_df[
            (year_df["fp"] == "Q1")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        q2 = year_df[
            (year_df["fp"] == "Q2")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        q3 = year_df[
            (year_df["fp"] == "Q3")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        fy = year_df[
            (year_df["fp"] == "FY")
            &
            (year_df["form"] == "10-K")
        ]["val"]

        q1_val = q1.max() if len(q1) else None
        q2_ytd = q2.max() if len(q2) else None
        q3_ytd = q3.max() if len(q3) else None
        fy_val = fy.max() if len(fy) else None

        real_q1 = q1_val

        real_q2 = (
            q2_ytd - q1_val
            if q2_ytd is not None
            and q1_val is not None
            else None
        )

        real_q3 = (
            q3_ytd - q2_ytd
            if q3_ytd is not None
            and q2_ytd is not None
            else None
        )

        real_q4 = (
            fy_val - q3_ytd
            if fy_val is not None
            and q3_ytd is not None
            and year < current_year
            else None
        )

        quarters = {
            "Q1": real_q1,
            "Q2": real_q2,
            "Q3": real_q3,
            "Q4": real_q4
        }

        for q, value in quarters.items():

            if value is None:
                continue

            rows.append({
                "Quarter": f"{year}-{q}",
                "Revenue": value
            })

    result = pd.DataFrame(rows)

    if len(result) == 0:
        return None

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
# HELPERS
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


def latest(df):

    if df is None or len(df) == 0:
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

    cik = get_cik_from_ticker(
        ticker
    )

    if cik is None:

        st.error("Ticker not found")
        st.stop()

    data = get_company_facts(cik)

    # =====================================================
    # METRICS
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
        ["GrossProfit"]
    )

    operating_income_raw = get_metric(
        data,
        ["OperatingIncomeLoss"]
    )

    net_income_raw = get_metric(
        data,
        ["NetIncomeLoss"]
    )

    operating_cf_raw = get_metric(
        data,
        ["NetCashProvidedByUsedInOperatingActivities"]
    )

    capex_raw = get_metric(
        data,
        ["PaymentsToAcquirePropertyPlantAndEquipment"]
    )

    cash_raw = get_metric(
        data,
        ["CashAndCashEquivalentsAtCarryingValue"]
    )

    debt_raw = get_metric(
        data,
        [
            "LongTermDebt",
            "LongTermDebtNoncurrent"
        ]
    )

    equity_raw = get_metric(
        data,
        [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
        ]
    )

    rd_raw = get_metric(
        data,
        ["ResearchAndDevelopmentExpense"]
    )

    sga_raw = get_metric(
        data,
        ["SellingGeneralAndAdministrativeExpense"]
    )

    assets_raw = get_metric(
        data,
        ["Assets"]
    )

    liabilities_raw = get_metric(
        data,
        ["Liabilities"]
    )

    # =====================================================
    # CLEAN
    # =====================================================

    revenue = add_growth(
        clean_annual(revenue_raw)
    )

    gross_profit = clean_annual(
        gross_profit_raw
    )

    operating_income = clean_annual(
        operating_income_raw
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

    debt = clean_annual(
        debt_raw
    )

    equity = clean_annual(
        equity_raw
    )

    rd = clean_annual(
        rd_raw
    )

    sga = clean_annual(
        sga_raw
    )

    assets = clean_annual(
        assets_raw
    )

    liabilities = clean_annual(
        liabilities_raw
    )

    quarterly_revenue = build_quarters(
        revenue_raw
    )

    # =====================================================
    # VALUES
    # =====================================================

    latest_revenue = latest(revenue)
    latest_growth = revenue.iloc[-1]["Growth %"]

    latest_gross_profit = latest(gross_profit)
    latest_operating_income = latest(operating_income)
    latest_net_income = latest(net_income)

    latest_ocf = latest(operating_cf)
    latest_capex = latest(capex)

    latest_cash = latest(cash)
    latest_debt = latest(debt)
    latest_equity = latest(equity)

    latest_rd = latest(rd)
    latest_sga = latest(sga)

    latest_assets = latest(assets)
    latest_liabilities = latest(liabilities)

    # =====================================================
    # CALCULATIONS
    # =====================================================

    free_cash_flow = (
        latest_ocf - abs(latest_capex)
        if latest_ocf is not None
        and latest_capex is not None
        else None
    )

    gross_margin = (
        latest_gross_profit / latest_revenue * 100
        if latest_revenue
        and latest_gross_profit
        else None
    )

    operating_margin = (
        latest_operating_income / latest_revenue * 100
        if latest_revenue
        and latest_operating_income
        else None
    )

    net_margin = (
        latest_net_income / latest_revenue * 100
        if latest_revenue
        and latest_net_income
        else None
    )

    fcf_margin = (
        free_cash_flow / latest_revenue * 100
        if free_cash_flow
        and latest_revenue
        else None
    )

    roe = (
        latest_net_income / latest_equity * 100
        if latest_net_income
        and latest_equity
        else None
    )

    debt_to_equity = (
        latest_debt / latest_equity
        if latest_debt
        and latest_equity
        else None
    )

    rule_of_40 = (
        latest_growth + operating_margin
        if latest_growth
        and operating_margin
        else None
    )

    # =====================================================
    # OVERVIEW
    # =====================================================

    st.markdown(
        "## Institutional Overview"
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

    with col2:

        st.metric(
            "Gross Margin",
            format_percent(
                gross_margin
            )
        )

        st.metric(
            "Operating Margin",
            format_percent(
                operating_margin
            )
        )

    with col3:

        st.metric(
            "Net Margin",
            format_percent(
                net_margin
            )
        )

        st.metric(
            "FCF Margin",
            format_percent(
                fcf_margin
            )
        )

    with col4:

        st.metric(
            "ROE",
            format_percent(
                roe
            )
        )

        st.metric(
            "Rule of 40",
            format_percent(
                rule_of_40
            )
        )

    # =====================================================
    # 5 YEAR TABLE
    # =====================================================

    st.divider()

    st.markdown(
        "## 5-Year Financial Growth"
    )

    growth_table = pd.DataFrame()

    growth_table["Year"] = revenue["fy"]

    growth_table["Revenue"] = revenue[
        "val"
    ].apply(
        format_number
    )

    growth_table["Revenue Growth"] = revenue[
        "Growth %"
    ].apply(
        lambda x:
        f"{x:.2f}%"
        if pd.notnull(x)
        else "-"
    )

    growth_table["Gross Profit"] = gross_profit[
        "val"
    ].apply(
        format_number
    )

    growth_table["Operating Income"] = operating_income[
        "val"
    ].apply(
        format_number
    )

    growth_table["Net Income"] = net_income[
        "val"
    ].apply(
        format_number
    )

    growth_table["Operating CF"] = operating_cf[
        "val"
    ].apply(
        format_number
    )

    st.dataframe(
        growth_table,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # QUARTERLY TABLE
    # =====================================================

    st.divider()

    st.markdown(
        "## Quarterly Revenue Growth"
    )

    if quarterly_revenue is not None:

        quarterly_display = (
            quarterly_revenue.copy()
        )

        quarterly_display["Revenue"] = (
            quarterly_display["Revenue"]
            .apply(format_number)
        )

        quarterly_display["QoQ Growth %"] = (
            quarterly_display["QoQ Growth %"]
            .apply(
                lambda x:
                f"{x:.2f}%"
                if pd.notnull(x)
                else "-"
            )
        )

        quarterly_display["YoY Growth %"] = (
            quarterly_display["YoY Growth %"]
            .apply(
                lambda x:
                f"{x:.2f}%"
                if pd.notnull(x)
                else "-"
            )
        )

        quarterly_display.columns = [
            "Quarter",
            "Revenue",
            "QoQ Growth",
            "YoY Growth"
        ]

        st.dataframe(
            quarterly_display,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # BALANCE SHEET
    # =====================================================

    st.divider()

    st.markdown(
        "## Balance Sheet Snapshot"
    )

    balance_table = pd.DataFrame()

    balance_table["Metric"] = [
        "Cash",
        "Debt",
        "Assets",
        "Liabilities",
        "Equity",
        "Free Cash Flow",
        "R&D",
        "SG&A"
    ]

    balance_table["Value"] = [
        format_number(latest_cash),
        format_number(latest_debt),
        format_number(latest_assets),
        format_number(latest_liabilities),
        format_number(latest_equity),
        format_number(free_cash_flow),
        format_number(latest_rd),
        format_number(latest_sga)
    ]

    st.dataframe(
        balance_table,
        use_container_width=True,
        hide_index=True
    )
