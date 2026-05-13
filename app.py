# =========================================================
# REPLACE ONLY build_quarters() WITH THIS VERSION
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
    # KEEP ONLY QUARTERLY + FY
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
    # KEEP ONLY REAL SEC FORMS
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
        # Q1 FROM 10-Q
        # =================================================

        q1 = year_df[
            (year_df["fp"] == "Q1")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # Q2 YTD FROM 10-Q
        # =================================================

        q2 = year_df[
            (year_df["fp"] == "Q2")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # Q3 YTD FROM 10-Q
        # =================================================

        q3 = year_df[
            (year_df["fp"] == "Q3")
            &
            (year_df["form"] == "10-Q")
        ]["val"]

        # =================================================
        # FY FROM 10-K
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
