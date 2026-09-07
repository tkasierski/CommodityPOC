# Aluminum Market-Implied Price Outlook

Streamlit proof of concept for a management-facing aluminum hedging dashboard.

## What it shows

For each procurement / option expiry, the dashboard compares:

- **Current Lock-In Price** — futures or forward price.
- **Market-Implied Price Scenario** — call strike with delta closest to a selected target (default 0.50).
- **Potential Hedge Protection** — scenario price minus current lock-in price.
- **Potential Hedge Protection %** — protection divided by current lock-in price.

The app is intentionally snapshot-based. Users click **Refresh Market Data** to recalculate the table and charts from one coherent market-data snapshot.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Data modes

### 1. Demo data

The default mode generates clearly labeled illustrative futures and option-chain data so the dashboard can be reviewed without a live market-data feed.

### 2. CSV upload

Upload both files, then click **Refresh Market Data**.

**Futures CSV**

```csv
expiry,forward_price
2026-10-31,2600
2026-11-30,2615
```

**Options CSV**

```csv
expiry,strike,call_delta
2026-10-31,2600,0.55
2026-10-31,2650,0.49
2026-11-30,2625,0.53
2026-11-30,2675,0.48
```

## POC methodology

For each expiry:

1. Pull the futures / forward price.
2. Find the call strike whose delta is closest to the configured target delta.
3. Treat that strike as the simple **Market-Implied Price Scenario**.
4. Calculate potential hedge protection in dollars per tonne and percent.
5. Render the table and charts from the same snapshot.

This is deliberately simplified for management communication and proof-of-concept use. Delta should not be interpreted as an exact real-world probability. A production implementation could use a full implied distribution, live market-data APIs, regional premiums / basis, historical snapshots, and configurable hedge-policy thresholds.

## Next implementation steps

- Replace demo / CSV data with the selected aluminum market-data provider.
- Add regional premium and basis inputs if procurement economics require them.
- Persist daily snapshots for backtesting.
- Add configurable decision bands or hedge recommendations after governance thresholds are defined.
