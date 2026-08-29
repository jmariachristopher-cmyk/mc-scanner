import io
import json
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import pyotp
from SmartApi import SmartConnect


IST = ZoneInfo("Asia/Kolkata")
NSE = "NSE"
SCRIP_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"


def rsi(series: pd.Series, length: int = 14) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < length + 1:
        return float("nan")
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    out = 100 - (100 / (1 + rs))
    if avg_loss.iloc[-1] == 0 and avg_gain.iloc[-1] > 0:
        return 100.0
    return float(out.iloc[-1])


class AngelScanner:
    def __init__(self, api_key, client_id, pin, totp_secret):
        self.api_key = api_key
        self.client_id = client_id
        self.pin = str(pin)
        self.totp_secret = totp_secret
        self.obj = SmartConnect(api_key=api_key)
        self.auth = None
        self.symbols = None

    @classmethod
    def from_streamlit_secrets(cls):
        import streamlit as st
        required = ["ANGEL_API_KEY", "ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]
        missing = [x for x in required if not st.secrets.get(x)]
        if missing:
            raise RuntimeError("Missing Streamlit secrets: " + ", ".join(missing))
        return cls(
            st.secrets["ANGEL_API_KEY"],
            st.secrets["ANGEL_CLIENT_ID"],
            st.secrets["ANGEL_PIN"],
            st.secrets["ANGEL_TOTP_SECRET"],
        )

    def login(self):
        totp = pyotp.TOTP(self.totp_secret).now()
        self.auth = self.obj.generateSession(self.client_id, self.pin, totp)
        if not self.auth or not self.auth.get("status"):
            raise RuntimeError(f"Angel One login failed: {self.auth}")
        return self.auth

    def load_nse_equities(self):
        r = requests.get(SCRIP_MASTER_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)
        # NSE equity cash symbols: exchange == NSE, instrumenttype blank, symbol ending EQ.
        df = df[(df["exch_seg"] == "NSE") & (df["symbol"].astype(str).str.endswith("-EQ"))].copy()
        df["symbol_clean"] = df["symbol"].str.replace("-EQ", "", regex=False)
        df["token"] = df["token"].astype(str)
        # Remove obvious non-equity artifacts.
        df = df[df["symbol_clean"].str.len() > 0]
        df = df.drop_duplicates("symbol_clean").sort_values("symbol_clean")
        self.symbols = df[["symbol_clean", "token"]].reset_index(drop=True)
        return self.symbols

    def market_quote(self, tokens, batch_size=40):
        quotes = {}
        for i in range(0, len(tokens), batch_size):
            chunk = [str(x) for x in tokens[i:i + batch_size]]
            payload = {"mode": "FULL", "exchangeTokens": {NSE: chunk}}
            resp = self.obj.getMarketData(payload)
            if not resp or not resp.get("status"):
                raise RuntimeError(f"Angel market data error: {resp}")
            for item in resp.get("data", {}).get("fetched", []) or []:
                token = str(item.get("symbolToken", item.get("token", "")))
                quotes[token] = item
            time.sleep(0.15)
        return quotes

    def candle(self, token, interval, start, end):
        params = {
            "exchange": NSE,
            "symboltoken": str(token),
            "interval": interval,
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": end.strftime("%Y-%m-%d %H:%M"),
        }
        resp = self.obj.getCandleData(params)
        if not resp or not resp.get("status"):
            return pd.DataFrame()
        rows = resp.get("data") or []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        return df.dropna(subset=["datetime", "close"]).sort_values("datetime").reset_index(drop=True)

    def previous_daily_ohlc(self, token):
        now = datetime.now(IST)
        start = now - timedelta(days=12)
        df = self.candle(token, "ONE_DAY", start, now)
        if df.empty:
            return None
        # Last completed daily candle before today.
        today = now.date()
        df = df[df["datetime"].dt.date < today]
        if df.empty:
            return None
        return df.iloc[-1]

    def current_rsi(self, token, interval, length):
        now = datetime.now(IST)
        days = 10 if interval != "ONE_DAY" else 120
        df = self.candle(token, interval, now - timedelta(days=days), now)
        if df.empty:
            return float("nan")
        # Drop today's incomplete daily candle only for ONE_DAY.
        if interval == "ONE_DAY":
            df = df[df["datetime"].dt.date < now.date()]
        return rsi(df["close"], length)

    def scan(self, gap_points=5.0, rsi_length=14, min_rsi=50.0,
             timeframe="5minute", batch_size=40, max_symbols=500):
        self.login()
        universe = self.load_nse_equities().head(max_symbols).copy()
        tokens = universe["token"].tolist()
        quotes = self.market_quote(tokens, batch_size=batch_size)

        matches = []
        errors = []

        for _, row in universe.iterrows():
            symbol = row["symbol_clean"]
            token = str(row["token"])
            q = quotes.get(token)
            if not q:
                errors.append(f"{symbol}: no market quote")
                continue
            try:
                ltp = float(q.get("ltp") or 0)
                today_open = float(q.get("open") or 0)
                high = float(q.get("high") or 0)
                low = float(q.get("low") or 0)
                volume = float(q.get("tradeVolume") or q.get("volume") or 0)

                prev = self.previous_daily_ohlc(token)
                if prev is None:
                    errors.append(f"{symbol}: no previous daily candle")
                    continue

                prev_close = float(prev["close"])
                prev_high = float(prev["high"])
                prev_low = float(prev["low"])
                r4 = prev_close + ((prev_high - prev_low) * 1.1 / 2.0)
                gap = today_open - prev_close
                gap_pct = (gap / prev_close * 100.0) if prev_close else 0.0
                current_rsi = self.current_rsi(token, timeframe, rsi_length)

                if (
                    gap >= gap_points
                    and current_rsi > min_rsi
                    and ltp > r4
                ):
                    matches.append({
                        "symbol": symbol,
                        "previous_close": prev_close,
                        "today_open": today_open,
                        "gap_rupees": gap,
                        "gap_percent": gap_pct,
                        "ltp": ltp,
                        "high": high,
                        "low": low,
                        "volume": volume,
                        "rsi": current_rsi,
                        "camarilla_r4": r4,
                    })
            except Exception as e:
                errors.append(f"{symbol}: {e}")

        df = pd.DataFrame(matches)
        if not df.empty:
            df = df.sort_values(["gap_rupees", "rsi"], ascending=False).reset_index(drop=True)

        return {
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "scanned": len(universe),
            "matches": df,
            "errors": errors,
        }
