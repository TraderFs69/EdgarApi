import requests

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

def get_cik_from_ticker(ticker):

    url = "https://www.sec.gov/files/company_tickers.json"

    data = requests.get(url, headers=HEADERS).json()

    for company in data.values():

        if company['ticker'] == ticker.upper():
            return str(company['cik_str']).zfill(10)

    return None


def get_company_facts(cik):

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)

    return response.json()
