import requests

HEADERS = {
    "User-Agent": "TradingEnAction fsanscartier@hotmail.com"
}

def get_company_facts(cik):

    cik = str(cik).zfill(10)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)

    return response.json()
