import numpy as np
import pandas as pd

def calculate_rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / length, adjust=False, min_periods=length
    ).mean()
    avg_loss = loss.ewm(
        alpha=1 / length, adjust=False, min_periods=length
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)

def camarilla_r3_s3(high, low, close):
    rng = high - low
    r3 = close + rng * 1.1 / 4
    s3 = close - rng * 1.1 / 4
    return r3, s3

def add_indicators(df, rsi_length=14, donchian_length=55):
    df = df.copy()
    df["rsi"] = calculate_rsi(df["close"], rsi_length)

    # Shift by one candle: current candle is excluded.
    df["donchian_upper"] = (
        df["high"].rolling(donchian_length).max().shift(1)
    )
    df["donchian_lower"] = (
        df["low"].rolling(donchian_length).min().shift(1)
    )
    return df
