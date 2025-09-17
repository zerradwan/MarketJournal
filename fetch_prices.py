#!/usr/bin/env python3
import os, sys, csv
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
import requests

# --- Config ---
CSV_PATH = Path("data/etf_prices_log.csv")  # output file
DATE_FMT = "%Y-%m-%d"                       # ISO date

# Tickers (Yahoo)
YF_TICKERS = {
    "EURO/USD": "EURUSD=X",
    "STG/USD": "GBPUSD=X",
    "USD/YEN": "JPY=X",
    "NIKKEI": "^N225",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "DOW": "^DJI",
    "S&P": "^GSPC",
    "US 10 YR (%)": "^TNX",  # divide by 10 later
    "GOLD": "GC=F",
    "BRENT CRUDE": "BZ=F",
}

# FRED series for non-US 10Y
FRED_SERIES = {
    "JAPAN 10 YR (%)": "IRLTLT01JPM156N",
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",
    "UK 10 YR (%)": "IRLTLT01GBM156N",
}

# Fields order for CSV
FIELDS = [
    "date",
    "EURO/USD","STG/USD","USD/YEN",
    "NIKKEI","DAX","FTSE","DOW","S&P",
    "JAPAN 10 YR (%)","GERMAN 10 YR (%)","UK 10 YR (%)","US 10 YR (%)",
    "GOLD","BRENT CRUDE","BITCOIN"
]

def prev_close(ticker: str):
    """
    Return most recent fully-settled daily close from Yahoo Finance.
    """
    try:
        hist = yf.Ticker(ticker).history(period="10d", interval="1d", auto_adjust=False)
        if hist.empty:
            return None
        close = float(hist["Close"].dropna().iloc[-1])
        return close
    except Exception:
        return None

def fred_latest(series_id: str):
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return None
    try:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={key}&file_type=json&sort_order=asc"
        )
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        j = r.json()
        obs = [o for o in j.get("observations", []) if o.get("value") not in (".", None)]
        if not obs:
            return None
        return float(obs[-1]["value"])
    except Exception:
        return None

def btc_usd():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=30
        )
        r.raise_for_status()
        j = r.json()
        val = j.get("bitcoin", {}).get("usd")
        return float(val) if isinstance(val, (int, float)) else None
    except Exception:
        return None

def read_existing_dates(path: Path):
    if not path.exists():
        return set()
    dates = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if "date" in row and row["date"]:
                dates.add(row["date"])
    return dates

def ensure_header(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()

def main():
    today = datetime.now(timezone.utc).date().strftime(DATE_FMT)

    ensure_header(CSV_PATH)
    existing = read_existing_dates(CSV_PATH)
    if today in existing:
        print(f"[info] Row for {today} already exists. Skipping.")
        return

    row = {"date": today}

    # FX / indices / commodities
    for label, ticker in YF_TICKERS.items():
        val = prev_close(ticker)
        if label == "US 10 YR (%)" and val is not None:
            val = round(val / 10.0, 4)  # ^TNX = yield * 10
        row[label] = round(val, 6) if isinstance(val, float) else None

    # Yields (JP/DE/UK) from FRED
    for label, series in FRED_SERIES.items():
        val = fred_latest(series)
        row[label] = round(val, 6) if isinstance(val, float) else None

    # BTC
    row["BITCOIN"] = btc_usd()

    # Append
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writerow(row)

    print(f"[ok] Appended {today}:")
    for k in FIELDS[1:]:
        print(f"  {k}: {row.get(k)}")

if __name__ == "__main__":
    sys.exit(main() or 0)
