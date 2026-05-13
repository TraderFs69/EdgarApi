# =========================================================
# TEA Institutional SEC Scanner
# TRUE QUARTER NORMALIZATION VERSION
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
        "start",
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

    if len(df) == 0:
        return None

    # =====================================================
    # CLEAN TYPES
    # =====================================================

    df["val"] = pd.to_numeric(
        df["val"],
        errors="coerce"
    )

    df = df.dropna(subset=["val"])

    df["filed"] = pd.to_datetime(
        df["filed"]
    )

    df["start"] = pd.to_datetime(
        df["start"]
    )

    df["end"] = pd.to_datetime(
        df["end"]
    )

    # =====================================================
    # DURATION
    # =====================================================

    df["days"] = (
        df["end"] - df["start"]
    ).dt.days

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

    current_date = pd.Timestamp.now()

    for year in years:

        year_df = df[
            df["fy"] == year
        ].sort_values("filed")

        quarter_values = {}

        # =================================================
        # PROCESS EACH PERIOD
        # =================================================

        for period in ["Q1", "Q2", "Q3", "FY"]:

            subset = year_df[
                year_df["fp"] == period
            ]

            if len(subset) == 0:
                continue

            row = subset.iloc[-1]

            value = row["val"]

            days = row["days"]

            quarter_values[period] = {
                "value": value,
                "days": days
            }

        # =================================================
        # TRUE QUARTERS
        # =================================================

        real_q1 = None
        real_q2 = None
        real_q3 = None
        real_q4 = None

        # =============================
        # Q1
        # =============================

        if "Q1" in quarter_values:

            real_q1 = (
                quarter_values["Q1"]["value"]
            )

        # =============================
        # Q2
        # =============================

        if "Q2" in quarter_values:

            q2_val = (
                quarter_values["Q2"]["value"]
            )

            q2_days = (
                quarter_values["Q2"]["days"]
            )

            # Standalone quarter
            if q2_days <= 120:

                real_q2 = q2_val

            # YTD cumulative
            else:

                if real_q1 is not None:

                    real_q2 = (
                        q2_val - real_q1
                    )

        # =============================
        # Q3
        # =============================

        if "Q3" in quarter_values:

            q3_val = (
                quarter_values["Q3"]["value"]
            )

            q3_days = (
                quarter_values["Q3"]["days"]
            )

            # Standalone
            if q3_days <= 120:

                real_q3 = q3_val

            # Cumulative
            else:

                q2_total = (
                    quarter_values["Q2"]["value"]
                    if "Q2" in quarter_values
                    else None
                )

                if q2_total is not None:

                    real_q3 = (
                        q3_val - q2_total
                    )

        # =============================
        # Q4
        # =============================

        if (
            "FY" in quarter_values
            and year < current_date.year
        ):

            fy_val = (
                quarter_values["FY"]["value"]
            )

            q3_total = (
                quarter_values["Q3"]["value"]
                if "Q3" in quarter_values
                else None
            )

            if q3_total is not None:

                real_q4 = (
                    fy_val - q3_total
                )

        # =================================================
        # STORE
        # =================================================

        quarters = {
            "Q1": real_q1,
            "Q2": real_q2,
            "Q3": real_q3,
            "Q4": real_q4
        }

        for q, value in quarters.items():

            if (
                value is None
                or value <= 0
            ):
                continue

            quarter_month = {
                "Q1": 3,
                "Q2": 6,
                "Q3": 9,
                "Q4": 12
            }[q]

            quarter_date = pd.Timestamp(
                year=int(year),
                month=quarter_month,
                day=1
            )

            # Avoid future quarters
            if quarter_date > current_date:
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
    # CLEAN
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
    # FCF
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
    # GROWTH
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
    # TABLES
    # =====================================================

    st.subheader(
        "Annual Revenue"
    )

    st.dataframe(
        revenue,
        use_container_width=True
    )

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
