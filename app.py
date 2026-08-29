import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from scanner import AngelScanner

st.set_page_config(page_title="NSE Gap + RSI + Camarilla R4", layout="wide")

st.title("NSE ₹5 Gap + RSI + Camarilla R4 Scanner")
st.caption("Angel One SmartAPI • NSE Equity • Scanner only — no orders are placed")

with st.sidebar:
    st.header("Scanner Settings")
    gap_points = st.number_input("Minimum gap (₹)", min_value=0.0, value=5.0, step=0.5)
    rsi_length = st.number_input("RSI length", min_value=2, max_value=100, value=14, step=1)
    min_rsi = st.number_input("Minimum RSI", min_value=0.0, max_value=100.0, value=50.0, step=1.0)
    timeframe = st.selectbox("RSI timeframe", ["5minute", "15minute", "30minute", "60minute", "ONE_DAY"], index=0)
    batch_size = st.number_input("Symbols per API batch", min_value=1, max_value=50, value=40, step=1)
    max_symbols = st.number_input("Maximum symbols to scan", min_value=1, max_value=2000, value=500, step=50)
    st.divider()
    st.subheader("Conditions")
    st.write("✓ Current Open − Previous Close ≥ gap")
    st.write("✓ RSI > minimum RSI")
    st.write("✓ Current Price > Camarilla R4")
    st.divider()
    refresh = st.button("🔄 Run Scanner", type="primary", use_container_width=True)

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if refresh or st.session_state.last_result is None:
    try:
        scanner = AngelScanner.from_streamlit_secrets()
        with st.spinner("Connecting to Angel One and scanning NSE stocks..."):
            result = scanner.scan(
                gap_points=float(gap_points),
                rsi_length=int(rsi_length),
                min_rsi=float(min_rsi),
                timeframe=timeframe,
                batch_size=int(batch_size),
                max_symbols=int(max_symbols),
            )
        st.session_state.last_result = result
    except Exception as e:
        st.error(f"Scanner error: {e}")
        st.info("Check your Streamlit secrets and Angel One SmartAPI credentials.")
        st.stop()

result = st.session_state.last_result
if result is None:
    st.stop()

st.success(f"Scan completed: {result['scanned']} symbols checked at {result['timestamp']}")

if result["errors"]:
    with st.expander(f"Warnings / skipped symbols ({len(result['errors'])})"):
        st.write(result["errors"][:50])

df = result["matches"]

if df.empty:
    st.warning("No stocks currently satisfy all three conditions.")
else:
    cols = [
        "symbol", "previous_close", "today_open", "gap_rupees", "gap_percent",
        "ltp", "high", "low", "volume", "rsi", "camarilla_r4"
    ]
    display = df[cols].copy()
    display.columns = [
        "Symbol", "Prev Close", "Open", "Gap ₹", "Gap %",
        "LTP", "High", "Low", "Volume", "RSI", "Camarilla R4"
    ]
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Gap ₹": st.column_config.NumberColumn(format="₹%.2f"),
            "Gap %": st.column_config.NumberColumn(format="%.2f%%"),
            "Prev Close": st.column_config.NumberColumn(format="₹%.2f"),
            "Open": st.column_config.NumberColumn(format="₹%.2f"),
            "LTP": st.column_config.NumberColumn(format="₹%.2f"),
            "High": st.column_config.NumberColumn(format="₹%.2f"),
            "Low": st.column_config.NumberColumn(format="₹%.2f"),
            "Camarilla R4": st.column_config.NumberColumn(format="₹%.2f"),
            "RSI": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.download_button(
        "⬇️ Download signals CSV",
        df.to_csv(index=False).encode("utf-8"),
        "nse_gap_rsi_camarilla_signals.csv",
        "text/csv",
    )

st.divider()
st.caption(
    "Formula: Gap ₹ = Today's Open − Previous Trading Day Close. "
    "Camarilla R4 = Previous Close + (Previous High − Previous Low) × 1.1 / 2. "
    "RSI is calculated from the selected Angel One candle timeframe."
)
