import streamlit as st
import pandas as pd

from utils.sec_api import (
    get_cik_from_ticker,
    get_company_facts
)

st.set_page_config(layout="wide")

st.title("TEA Fundamental Scanner")

ticker = st.text_input("Ticker", "NVDA")

if st.button("Analyze"):

    cik = get_cik_from_ticker(ticker)

    if cik is None:
        st.error("Ticker not found")
    else:

        st.success(f"CIK found: {cik}")

        data = get_company_facts(cik)

        st.success("Financial data loaded")

        try:

            revenues = data['facts']['us-gaap'][
                'RevenueFromContractWithCustomerExcludingAssessedTax'
            ]['units']['USD']

            df = pd.DataFrame(revenues)

            df = df[['fy', 'fp', 'val']]

            df.columns = [
                'Fiscal Year',
                'Quarter',
                'Revenue'
            ]

            st.subheader("Revenue Data")

            st.dataframe(df)

        except:
            st.error("Revenue data not found")
