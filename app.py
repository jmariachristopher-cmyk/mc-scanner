import streamlit as st
import pandas as pd
from datetime import datetime, date
from screener import run_scan
from universe import DEFAULT_SYMBOLS

st.set_page_config(page_title="JMC Upstox Screener", page_icon="📈", layout="wide")

st.title("📈 JMC Upstox Gap + RSI + Camarilla + Donchian Screener")
st.caption("NSE Equity scanner • Upstox API • CALL / PUT momentum candidates")

with st.sidebar:
    st.header("Scanner Settings")

    timeframe_label = st.selectbox(
        "Analysis timeframe",
        ["5 minute", "15 minute", "30 minute", "60 minute"],
        index=0,
    )
    timeframe_map = {
        "5 minute": 5,
        "15 minute": 15,
        "30 minute": 30,
        "60 minute": 60,
    }
    interval = timeframe_map[timeframe_label]

    gap_min = st.number_input(
        "Minimum gap (₹)", min_value=0.10, max_value=100.0,
        value=3.0, step=0.5
    )
    gap_max = st.number_input(
        "Maximum gap (₹)", min_value=0.10, max_value=100.0,
        value=5.0, step=0.5
    )
    rsi_length = st.number_input("RSI length", 2, 100, 14)
    donchian_length = st.number_input("Donchian length", 2, 200, 55)

    symbols_text = st.text_area(
        "Symbols (comma separated)",
        value=",".join(DEFAULT_SYMBOLS),
        height=170,
    )

    st.divider()
    st.write("**CALL**")
    st.write("Open ₹3–₹5 above previous close + RSI > 50 + price > R3 + price > Donchian 55 upper.")

    st.write("**PUT**")
    st.write("Open ₹3–₹5 below previous close + RSI < 50 + price < S3 + price < Donchian 55 lower.")

if gap_min > gap_max:
    st.error("Minimum gap cannot be greater than maximum gap.")
    st.stop()

symbols = [x.strip().upper() for x in symbols_text.split(",") if x.strip()]

if st.button("🔎 RUN SCANNER", type="primary", use_container_width=True):
    if not symbols:
        st.error("Enter at least one symbol.")
        st.stop()

    with st.spinner(f"Scanning {len(symbols)} symbols through Upstox..."):
        try:
            calls, puts, diagnostics = run_scan(
                symbols=symbols,
                interval=interval,
                gap_min=gap_min,
                gap_max=gap_max,
                rsi_length=int(rsi_length),
                donchian_length=int(donchian_length),
            )
        except Exception as e:
            st.error(f"Scanner error: {e}")
            st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("CALL signals", len(calls))
    c2.metric("PUT signals", len(puts))
    c3.metric("Scanned", len(diagnostics))

    st.subheader("🟢 CALL SIDE")
    if calls.empty:
        st.info("No CALL candidate matched all conditions.")
    else:
        st.dataframe(calls, use_container_width=True, hide_index=True)

    st.subheader("🔴 PUT SIDE")
    if puts.empty:
        st.info("No PUT candidate matched all conditions.")
    else:
        st.dataframe(puts, use_container_width=True, hide_index=True)

    with st.expander("Diagnostics / rejected symbols"):
        st.dataframe(diagnostics, use_container_width=True, hide_index=True)

st.divider()
st.markdown("""
### Formula used

**Camarilla**
- `R3 = Previous Close + (Previous High - Previous Low) × 1.1 / 4`
- `S3 = Previous Close - (Previous High - Previous Low) × 1.1 / 4`

**Donchian 55**
- Upper = highest high of the previous 55 completed candles
- Lower = lowest low of the previous 55 completed candles

The current candle is excluded from the Donchian calculation, so the current price does not create its own breakout level.

### Gap interpretation
The scanner uses an **absolute ₹3–₹5 gap**, exactly as requested:
- CALL: `Open - Previous Close >= ₹3` and `<= ₹5`
- PUT: `Previous Close - Open >= ₹3` and `<= ₹5`

This is not a percentage-gap filter.
""")
