import pandas as pd
from datetime import date, timedelta
from upstox_client import UpstoxClient
from indicators import add_indicators, camarilla_r3_s3

def candles_to_df(candles):
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for c in ["open", "high", "low", "close", "volume", "oi"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("timestamp").reset_index(drop=True)

def run_scan(symbols, interval, gap_min, gap_max, rsi_length, donchian_length):
    client = UpstoxClient()

    calls = []
    puts = []
    diagnostics = []

    today = date.today()
    from_date = today - timedelta(days=120)

    for symbol in symbols:
        try:
            instrument = client.instrument_search(symbol)
            key = instrument["instrument_key"]

            daily = candles_to_df(
                client.historical_days(
                    key,
                    from_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                )
            )

            if len(daily) < 2:
                raise RuntimeError("Not enough daily candles.")

            prev = daily.iloc[-2]

            # Current trading day's intraday candles.
            intraday = candles_to_df(client.intraday(key, interval))
            if intraday.empty:
                raise RuntimeError("No intraday data.")

            row = intraday.iloc[-1]
            opening = float(intraday.iloc[0]["open"])
            current_price = float(row["close"])

            # Previous day's Camarilla levels.
            r3, s3 = camarilla_r3_s3(
                float(prev["high"]),
                float(prev["low"]),
                float(prev["close"]),
            )

            work = add_indicators(
                intraday,
                rsi_length=rsi_length,
                donchian_length=donchian_length,
            )
            row = work.iloc[-1]

            rsi_value = float(row["rsi"])
            dc_upper = float(row["donchian_upper"]) if pd.notna(row["donchian_upper"]) else float("nan")
            dc_lower = float(row["donchian_lower"]) if pd.notna(row["donchian_lower"]) else float("nan")

            gap_up = opening - float(prev["close"])
            gap_down = float(prev["close"]) - opening

            call_gap = gap_min <= gap_up <= gap_max
            put_gap = gap_min <= gap_down <= gap_max

            call_rsi = rsi_value > 50
            put_rsi = rsi_value < 50

            call_r3 = current_price > r3
            put_s3 = current_price < s3

            call_dc = pd.notna(dc_upper) and current_price > dc_upper
            put_dc = pd.notna(dc_lower) and current_price < dc_lower

            base = {
                "Symbol": symbol,
                "Open": round(opening, 2),
                "Prev Close": round(float(prev["close"]), 2),
                "Current": round(current_price, 2),
                "Gap ₹": round(gap_up if gap_up >= 0 else -gap_down, 2),
                "RSI": round(rsi_value, 2),
                "R3": round(r3, 2),
                "S3": round(s3, 2),
                "DC55 Upper": round(dc_upper, 2) if pd.notna(dc_upper) else None,
                "DC55 Lower": round(dc_lower, 2) if pd.notna(dc_lower) else None,
            }

            if call_gap and call_rsi and call_r3 and call_dc:
                calls.append({
                    **base,
                    "Signal": "CALL",
                    "Gap Test": "PASS",
                    "RSI Test": "PASS",
                    "R3 Test": "PASS",
                    "Donchian Test": "PASS",
                })

            if put_gap and put_rsi and put_s3 and put_dc:
                puts.append({
                    **base,
                    "Signal": "PUT",
                    "Gap ₹": round(-gap_down if gap_down > 0 else gap_up, 2),
                    "Gap Test": "PASS",
                    "RSI Test": "PASS",
                    "S3 Test": "PASS",
                    "Donchian Test": "PASS",
                })

            diagnostics.append({
                **base,
                "CALL": "YES" if call_gap and call_rsi and call_r3 and call_dc else "NO",
                "PUT": "YES" if put_gap and put_rsi and put_s3 and put_dc else "NO",
                "Error": "",
            })

        except Exception as e:
            diagnostics.append({
                "Symbol": symbol,
                "Open": None,
                "Prev Close": None,
                "Current": None,
                "Gap ₹": None,
                "RSI": None,
                "R3": None,
                "S3": None,
                "DC55 Upper": None,
                "DC55 Lower": None,
                "CALL": "ERROR",
                "PUT": "ERROR",
                "Error": str(e),
            })

    return (
        pd.DataFrame(calls),
        pd.DataFrame(puts),
        pd.DataFrame(diagnostics),
    )
