# NSE ₹5 Gap + RSI + Camarilla R4 — Angel One Streamlit Scanner

Scanner conditions:

1. Today's Open - Previous Trading Day Close >= configurable gap (default ₹5)
2. RSI > configurable minimum (default 50)
3. Current LTP > Previous Day Camarilla R4

## Angel One credentials

Required Streamlit secrets:

- ANGEL_API_KEY
- ANGEL_CLIENT_ID
- ANGEL_PIN
- ANGEL_TOTP_SECRET

### Local

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`, then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Community Cloud

Push this repository to GitHub and deploy `app.py`.

In Streamlit Cloud:
App -> Settings -> Secrets

Paste:

```toml
ANGEL_API_KEY = "..."
ANGEL_CLIENT_ID = "..."
ANGEL_PIN = "..."
ANGEL_TOTP_SECRET = "..."
```

Never commit real credentials.

## Important

This project is a scanner only. It does not place trades.

The first version downloads Angel One's instrument master and scans NSE equity symbols. The symbol universe can be capped from the sidebar to reduce API load.

Camarilla R4 formula used:

R4 = Previous Close + (Previous High - Previous Low) * 1.1 / 2

RSI is calculated from the selected candle timeframe.

For live production use, consider replacing repeated historical calls with a cached/in-memory data layer or WebSocket-driven candles to reduce API requests.
