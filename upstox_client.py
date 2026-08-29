import requests
import streamlit as st
from datetime import date, timedelta

BASE = "https://api.upstox.com"

class UpstoxClient:
    def __init__(self):
        token = st.secrets.get("UPSTOX_ACCESS_TOKEN", "")
        if not token:
            raise RuntimeError(
                "Missing UPSTOX_ACCESS_TOKEN in Streamlit Secrets. "
                "Add your current Upstox access token."
            )
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def instrument_search(self, symbol):
        url = f"{BASE}/v2/instruments/search"
        params = {
            "query": symbol,
            "exchanges": "NSE",
            "segments": "EQ",
            "instrument_types": "EQ",
            "page_number": 1,
            "records": 30,
        }
        r = requests.get(url, headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", [])
        exact = [x for x in rows if x.get("trading_symbol", "").upper() == symbol.upper()]
        if exact:
            return exact[0]
        if rows:
            return rows[0]
        raise RuntimeError(f"Instrument not found: {symbol}")

    def historical_days(self, instrument_key, from_date, to_date):
        url = (
            f"{BASE}/v3/historical-candle/"
            f"{instrument_key}/days/1/{to_date}/{from_date}"
        )
        r = requests.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()
        return r.json().get("data", {}).get("candles", [])

    def intraday(self, instrument_key, minutes):
        url = (
            f"{BASE}/v3/historical-candle/intraday/"
            f"{instrument_key}/minutes/{minutes}"
        )
        r = requests.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()
        return r.json().get("data", {}).get("candles", [])
