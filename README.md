# JMC Upstox Gap + RSI + Camarilla + Donchian Screener

Streamlit scanner using the Upstox API.

## Conditions

### CALL
- Opening price is ₹3 to ₹5 above previous day's close.
- RSI > 50.
- Current price > previous day's Camarilla R3.
- Current price > Donchian 55 upper channel.

### PUT
- Opening price is ₹3 to ₹5 below previous day's close.
- RSI < 50.
- Current price < previous day's Camarilla S3.
- Current price < Donchian 55 lower channel.

## Important calculation detail

Camarilla R3/S3 uses the previous trading day's High, Low and Close.

Donchian 55 uses the previous 55 completed candles. The current candle is shifted out of the calculation to avoid self-referencing.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Create `.streamlit/secrets.toml`:

```toml
UPSTOX_ACCESS_TOKEN = "YOUR_CURRENT_TOKEN"
```

## Streamlit Cloud

1. Create a GitHub repository.
2. Upload all project files.
3. Deploy the repository as a Streamlit app.
4. In Streamlit Cloud open App Settings -> Secrets.
5. Add:

```toml
UPSTOX_ACCESS_TOKEN = "YOUR_CURRENT_TOKEN"
```

6. Main file: `app.py`.

Never upload `secrets.toml` to GitHub.

## Upstox authentication

This project intentionally uses an access token from Streamlit Secrets rather than putting credentials in source code.

Upstox uses OAuth 2.0. Access tokens expire according to the Upstox authentication flow, so when the token expires, replace the Streamlit secret with a fresh token.

## Scanner timeframe

Default is 5-minute. You can select 15, 30 or 60 minutes.

The ₹3–₹5 gap is an absolute rupee difference, not a percentage.
