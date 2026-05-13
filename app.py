# =========================================================
# export_all_xbrl.py
# TEA Institutional Full XBRL Exporter
# STREAMLIT VERSION
# =========================================================

import pandas as pd
import requests
import os
import streamlit as st

# =========================================================
# CONFIG
# =========================================================

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

OUTPUT_FOLDER = "exports"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# =========================================================
# STREAMLIT CONFIG
# =========================================================

st.set_page_config(
    page_title="TEA XBRL Exporter",
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

div[data-testid="stMetric"] {
    background-color: #161b22;
    border-radius: 12px;
    padding: 10px;
}

.stButton button {
    background-color: #ff8c00;
    color: black;
    border-radius: 8px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# GET CIK
# =========================================================

@st.cache_data
def get_cik_from_ticker(ticker):

    url = "https://www.sec.gov/files/company_tickers.json"

    response = requests.get(
        url,
        headers=HEADERS
    )

    data = response.json()

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
# EXPORT ALL XBRL
# =========================================================

def export_all_xbrl(ticker):

    st.write(f"## Exporting {ticker}")

    # =====================================================
    # GET CIK
    # =====================================================

    cik = get_cik_from_ticker(
        ticker
    )

    if cik is None:

        st.error(
            "Ticker not found."
        )

        return None, None

    st.success(f"CIK: {cik}")

    # =====================================================
    # LOAD DATA
    # =====================================================

    data = get_company_facts(cik)

    if "facts" not in data:

        st.error(
            "No facts section found."
        )

        return None, None

    if "us-gaap" not in data["facts"]:

        st.error(
            "No us-gaap section found."
        )

        return None, None

    us_gaap = data["facts"]["us-gaap"]

    # =====================================================
    # STORAGE
    # =====================================================

    rows = []

    metric_count = len(us_gaap)

    progress_bar = st.progress(0)

    status_text = st.empty()

    current_metric = 0

    # =====================================================
    # LOOP THROUGH ALL METRICS
    # =====================================================

    for metric_name, metric_data in us_gaap.items():

        current_metric += 1

        progress = current_metric / metric_count

        progress_bar.progress(progress)

        status_text.text(
            f"[{current_metric}/{metric_count}] "
            f"{metric_name}"
        )

        try:

            if "units" not in metric_data:
                continue

            # =================================================
            # LOOP THROUGH UNITS
            # =================================================

            for unit_name, values in metric_data[
                "units"
            ].items():

                # =============================================
                # KEEP ONLY IMPORTANT UNITS
                # =============================================

                if unit_name not in [
                    "USD",
                    "shares",
                    "USD/shares"
                ]:
                    continue

                # =============================================
                # LOOP THROUGH VALUES
                # =============================================

                for item in values:

                    # =========================================
                    # KEEP ONLY IMPORTANT FORMS
                    # =========================================

                    form = item.get("form")

                    if form not in [
                        "10-K",
                        "10-Q"
                    ]:
                        continue

                    # =========================================
                    # REMOVE FUTURE PERIODS
                    # =========================================

                    end_date = item.get("end")

                    if end_date is not None:

                        try:

                            end_date = pd.to_datetime(
                                end_date
                            )

                            if end_date > pd.Timestamp.now():
                                continue

                        except:
                            pass

                    # =========================================
                    # CREATE ROW
                    # =========================================

                    row = {
                        "Ticker": ticker,
                        "Metric": metric_name,
                        "Unit": unit_name,
                        "Value": item.get("val"),
                        "FY": item.get("fy"),
                        "FP": item.get("fp"),
                        "Form": form,
                        "Filed": item.get("filed"),
                        "Frame": item.get("frame"),
                        "Start": item.get("start"),
                        "End": item.get("end"),
                        "Accession": item.get("accn")
                    }

                    rows.append(row)

                    # =========================================
                    # SAFETY LIMIT
                    # =========================================

                    if len(rows) > 500000:

                        st.warning(
                            "Safety stop reached."
                        )

                        break

        except Exception as e:

            st.warning(
                f"Error on metric "
                f"{metric_name}: {e}"
            )

    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    df = pd.DataFrame(rows)

    if len(df) == 0:

        st.error(
            "No data exported."
        )

        return None, None

    # =====================================================
    # CLEAN DATES
    # =====================================================

    for col in [
        "Filed",
        "Start",
        "End"
    ]:

        if col in df.columns:

            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    # =====================================================
    # SORT
    # =====================================================

    df = df.sort_values([
        "Metric",
        "FY",
        "FP",
        "Filed"
    ])

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    df = df.drop_duplicates()

    # =====================================================
    # EXPORT RAW
    # =====================================================

    raw_path = os.path.join(
        OUTPUT_FOLDER,
        f"{ticker}_all_xbrl.csv"
    )

    df.to_csv(
        raw_path,
        index=False
    )

    # =====================================================
    # CREATE CLEAN FILE
    # =====================================================

    clean_df = df.copy()

    clean_df = clean_df.sort_values([
        "Metric",
        "FY",
        "FP",
        "Filed"
    ])

    clean_df = clean_df.drop_duplicates(
        subset=[
            "Metric",
            "FY",
            "FP",
            "Form",
            "Frame"
        ],
        keep="last"
    )

    clean_path = os.path.join(
        OUTPUT_FOLDER,
        f"{ticker}_financials_clean.csv"
    )

    clean_df.to_csv(
        clean_path,
        index=False
    )

    # =====================================================
    # SUMMARY
    # =====================================================

    st.success(
        "Export completed successfully."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Metrics Exported",
            clean_df["Metric"].nunique()
        )

    with col2:

        st.metric(
            "Rows Exported",
            f"{len(clean_df):,}"
        )

    return df, clean_df


# =========================================================
# UI
# =========================================================

st.title(
    "TEA Institutional XBRL Exporter"
)

st.markdown("""
Export all available SEC XBRL financial data.

Exports:
- Full raw XBRL dataset
- Clean institutional financials dataset
""")

tickers = st.text_area(
    "Tickers (comma separated)",
    value="NVDA"
)

# =========================================================
# EXPORT BUTTON
# =========================================================

if st.button("Export XBRL Data"):

    ticker_list = [
        t.strip().upper()
        for t in tickers.split(",")
    ]

    for ticker in ticker_list:

        raw_df, clean_df = export_all_xbrl(
            ticker
        )

        if clean_df is not None:

            st.divider()

            st.markdown(
                f"## {ticker} Preview"
            )

            st.dataframe(
                clean_df.head(50),
                use_container_width=True
            )

            # =============================================
            # DOWNLOAD BUTTONS
            # =============================================

            raw_csv = raw_df.to_csv(
                index=False
            ).encode("utf-8")

            clean_csv = clean_df.to_csv(
                index=False
            ).encode("utf-8")

            col1, col2 = st.columns(2)

            with col1:

                st.download_button(
                    label=f"Download {ticker} RAW CSV",
                    data=raw_csv,
                    file_name=f"{ticker}_all_xbrl.csv",
                    mime="text/csv"
                )

            with col2:

                st.download_button(
                    label=f"Download {ticker} CLEAN CSV",
                    data=clean_csv,
                    file_name=f"{ticker}_financials_clean.csv",
                    mime="text/csv"
                )
