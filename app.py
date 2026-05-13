# =========================================================
# TEA Institutional SEC Scanner
# FINAL VERSION - CORRECT Q4 LOGIC
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

    df["days"] = (
        df["end"] - df["start"]
    ).dt.days

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
        # STORE PERIODS
        # =================================================

        for period in ["Q1", "Q2", "Q3", "FY"]:

            subset = year_df[
                year_df["fp"] == period
            ]

            if len(subset) == 0:
                continue

            row = subset.iloc[-1]

            quarter_values[period] = {
                "value": row["val"],
                "days": row["days"]
            }

        # =================================================
        # REAL QUARTERS
        # =================================================

        real_q1 = None
        real_q2 = None
        real_q3 = None
        real_q4 = None

        # =================================================
        # Q1
        # =================================================

        if "Q1" in quarter_values:

            real_q1 = (
                quarter_values["Q1"]["value"]
            )

        # =================================================
        # Q2
        # =================================================

        if "Q2" in quarter_values:

            q2_val = (
                quarter_values["Q2"]["value"]
            )

            q2_days = (
                quarter_values["Q2"]["days"]
            )

            # Standalone
            if q2_days <= 120:

                real_q2 = q2_val

            # Cumulative
            else:

                if real_q1 is not None:

                    real_q2 = (
                        q2_val - real_q1
                    )

        # =================================================
        # Q3
        # =================================================

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

        # =================================================
        # Q4
        # =================================================

        if (
            "FY" in quarter_values
            and year < current_date.year
        ):

            fy_val = (
                quarter_values["FY"]["value"]
            )

            if "Q3" in quarter_values:

                q3_val = (
                    quarter_values["Q3"]["value"]
                )

                q3_days = (
                    quarter_values["Q3"]["days"]
                )

                # =========================================
                # Q3 STANDALONE
                # =========================================

                if q3_days <= 120:

                    total = 0

                    if real_q1 is not None:
                        total += real_q1

                    if real_q2 is not None:
                        total += real_q2

                    if real_q3 is not None:
                        total += real_q3

                    real_q4 = fy_val - total

                # =========================================
                # Q3 CUMULATIVE
                # =========================================

                else:

                    real_q4 = (
                        fy_val - q3_val
                    )

        # =================================================
        # STORE QUARTERS
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
