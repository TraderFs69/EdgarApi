# =========================================================
# export_all_xbrl.py
# TEA Institutional Full XBRL Exporter
# OPTIMIZED VERSION
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
# EXPORT ALL XBRL
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

        print("No facts section found.")
        return

    if "us-gaap" not in data["facts"]:

        print("No us-gaap section found.")
        return

    us_gaap = data["facts"]["us-gaap"]

    # =====================================================
    # STORAGE
    # =====================================================

    rows = []

    metric_count = len(us_gaap)

    current_metric = 0

    # =====================================================
    # LOOP THROUGH ALL METRICS
    # =====================================================

    for metric_name, metric_data in us_gaap.items():

        current_metric += 1

        print(
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

                        print(
                            "\nSafety stop reached."
                        )

                        break

        except Exception as e:

            print(
                f"Error on metric "
                f"{metric_name}: {e}"
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

    print("\n==============================")
    print("RAW EXPORT COMPLETE")
    print("==============================")

    print(raw_path)

    # =====================================================
    # CREATE CLEAN FINANCIALS
    # =====================================================

    clean_df = df.copy()

    # =====================================================
    # KEEP LATEST FILING
    # =====================================================

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

    # =====================================================
    # SORT AGAIN
    # =====================================================

    clean_df = clean_df.sort_values([
        "Metric",
        "FY",
        "FP"
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

    print("\n==============================")
    print("CLEAN EXPORT COMPLETE")
    print("==============================")

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
        f"Metrics exported: "
        f"{unique_metrics}"
    )

    print(
        f"Rows exported: "
        f"{total_rows:,}"
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
