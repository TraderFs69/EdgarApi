# =========================================================
# export_all_xbrl.py
# TEA Institutional Full XBRL Exporter
# Export ALL available SEC financial data
# =========================================================

import pandas as pd
import requests
import os

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
# GET CIK
# =========================================================

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
# EXPORT ALL US-GAAP TAGS
# =========================================================

def export_all_xbrl(ticker):

    print(f"\nExporting ALL XBRL data for {ticker}...\n")

    # =====================================================
    # GET CIK
    # =====================================================

    cik = get_cik_from_ticker(
        ticker
    )

    if cik is None:

        print("Ticker not found.")
        return

    print(f"CIK: {cik}")

    # =====================================================
    # LOAD DATA
    # =====================================================

    data = get_company_facts(cik)

    if "facts" not in data:

        print("No facts found.")
        return

    if "us-gaap" not in data["facts"]:

        print("No us-gaap section.")
        return

    us_gaap = data["facts"]["us-gaap"]

    # =====================================================
    # STORAGE
    # =====================================================

    rows = []

    # =====================================================
    # LOOP THROUGH ALL METRICS
    # =====================================================

    for metric_name, metric_data in us_gaap.items():

        try:

            if "units" not in metric_data:
                continue

            # =================================================
            # LOOP THROUGH UNITS
            # =================================================

            for unit_name, values in metric_data[
                "units"
            ].items():

                # =================================================
                # LOOP THROUGH ENTRIES
                # =================================================

                for item in values:

                    row = {
                        "Ticker": ticker,
                        "Metric": metric_name,
                        "Unit": unit_name,
                        "Value": item.get("val"),
                        "FY": item.get("fy"),
                        "FP": item.get("fp"),
                        "Form": item.get("form"),
                        "Filed": item.get("filed"),
                        "Frame": item.get("frame"),
                        "Start": item.get("start"),
                        "End": item.get("end"),
                        "Fiscal Year": item.get("fy"),
                        "Fiscal Period": item.get("fp"),
                        "Accession": item.get("accn")
                    }

                    rows.append(row)

        except Exception as e:

            print(
                f"Error on metric {metric_name}: {e}"
            )

    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    df = pd.DataFrame(rows)

    if len(df) == 0:

        print("No data exported.")
        return

    # =====================================================
    # CLEAN DATES
    # =====================================================

    date_columns = [
        "Filed",
        "Start",
        "End"
    ]

    for col in date_columns:

        if col in df.columns:

            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    # =====================================================
    # SORT
    # =====================================================

    sort_columns = [
        col for col in [
            "Metric",
            "FY",
            "FP",
            "Filed"
        ]
        if col in df.columns
    ]

    df = df.sort_values(
        sort_columns
    )

    # =====================================================
    # EXPORT FULL RAW DATA
    # =====================================================

    raw_path = os.path.join(
        OUTPUT_FOLDER,
        f"{ticker}_all_xbrl.csv"
    )

    df.to_csv(
        raw_path,
        index=False
    )

    print(
        f"\nFull XBRL exported:"
    )

    print(raw_path)

    # =====================================================
    # CREATE CLEANED FINANCIALS FILE
    # =====================================================

    clean_df = df.copy()

    # =====================================================
    # KEEP MOST IMPORTANT FORMS
    # =====================================================

    clean_df = clean_df[
        clean_df["Form"].isin([
            "10-K",
            "10-Q"
        ])
    ]

    # =====================================================
    # REMOVE FUTURE DATES
    # =====================================================

    today = pd.Timestamp.now()

    clean_df = clean_df[
        (
            clean_df["End"].isna()
        )
        |
        (
            clean_df["End"] <= today
        )
    ]

    # =====================================================
    # REMOVE EMPTY VALUES
    # =====================================================

    clean_df = clean_df.dropna(
        subset=["Value"]
    )

    # =====================================================
    # SORT
    # =====================================================

    clean_df = clean_df.sort_values([
        "Metric",
        "FY",
        "FP",
        "Filed"
    ])

    # =====================================================
    # EXPORT CLEAN
    # =====================================================

    clean_path = os.path.join(
        OUTPUT_FOLDER,
        f"{ticker}_financials_clean.csv"
    )

    clean_df.to_csv(
        clean_path,
        index=False
    )

    print(
        f"\nClean financials exported:"
    )

    print(clean_path)

    # =====================================================
    # SUMMARY
    # =====================================================

    unique_metrics = (
        clean_df["Metric"]
        .nunique()
    )

    total_rows = len(clean_df)

    print("\n==============================")
    print("EXPORT SUMMARY")
    print("==============================")

    print(
        f"Metrics exported: {unique_metrics}"
    )

    print(
        f"Rows exported: {total_rows:,}"
    )

    print("==============================\n")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    ticker = input(
        "Ticker: "
    ).upper()

    export_all_xbrl(ticker)
