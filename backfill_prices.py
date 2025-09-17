# backfill_prices.py
import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path
import yfinance as yf

# --- FRED fallback for non-US 10Y ---
FRED_KEY = os.getenv("FRED_API_KEY")
fred = None
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
    except Exception:
        fred = None

CSV_PATH = Path("data/etf_prices_log.csv")

DATES = [
    "2025-09-05","2025-09-08","2025-09-09","2025-09-10",
    "2025-09-11","2025-09-12","2025-09-15","2025-09-16",
]

HEADERS = [
    "date","EURO/USD","STG/USD","USD/YEN","NIKKEI","DAX","FTSE","DOW","S&P",
    "JAPAN 10 YR (%)","GERMAN 10 YR (%)","UK 10 YR (%)","US 10 YR (%)",
    "GOLD","BRENT CRUDE","BITCOIN"
]

# Yahoo Finance tickers
YF_TICKERS = {
    "EURO/USD": "EURUSD=X",
    "STG/USD": "GBPUSD=X",
    "USD/YEN": "JPY=X",          # USD/JPY
    "NIKKEI": "^N225",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "DOW": "^DJI",
    "S&P": "^GSPC",
    "GOLD": "GC=F",
    "BRENT CRUDE": "BZ=F",
    "BITCOIN": "BTC-USD",
    # US 10Y via Yahoo ^TNX (tenths of a percent; divide by 10)
    "US 10 YR (%)": "^TNX",
}

# FRED fallback (monthly OECD series) for JP/DE/UK 10Y
FRED_SERIES = {
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",
    "UK 10 YR (%)":     "IRLTLT01GBM156N",
    "JAPAN 10 YR (%)":  "IRLTLT01JPM156N",
}

def iso(s): return datetime.strptime(s, "%Y-%m-%d").date()

def get_close_yf(ticker: str, d: date):
    """Daily close on date d. Use 2-day window and take last row (handles TZ)."""
    try:
        df = yf.Ticker(ticker).history(
            start=d, end=d + timedelta(days=2),
            interval="1d", auto_adjust=False
        )
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None

def get_us10y_from_yahoo(d: date):
    """US 10Y from Yahoo ^TNX (reported in tenths of a percent)."""
    v = get_close_yf("^TNX", d)
    if v is None:
        return None
    return v / 10.0  # <-- FIX: convert to percent

def fred_latest_leq(series_id: str, d: date):
    """Most recent FRED value on/before d (handles monthly series). Returns float or None."""
    if not fred:
        return None
    try:
        start = d - timedelta(days=90)  # cover month boundaries
        s = fred.get_series(series_id, observation_start=start, observation_end=d)
        if s is not None:
            s = s.dropna()
            if len(s) > 0:
                return float(s.iloc[-1])
    except Exception:
        pass
    return None

def ensure_header():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(HEADERS)

def load_rows():
    if not CSV_PATH.exists(): return []
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))

def write_rows(headers, rows):
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

def main():
    ensure_header()
    rows = load_rows()
    have = {r["date"] for r in rows if r.get("date")}
    new_rows = []

    for dstr in DATES:
        d = iso(dstr)
        row = next((r for r in rows if r.get("date") == dstr), None)
        if row is None:
            row = {h: "" for h in HEADERS}
            row["date"] = dstr

        # Prices via Yahoo (FX/indices/commodities/BTC)
        for name, t in YF_TICKERS.items():
            if name == "US 10 YR (%)":
                v = get_us10y_from_yahoo(d)
            else:
                v = get_close_yf(t, d)
            if v is not None:
                row[name] = f"{v:.4f}"

        # JP/DE/UK 10Y via FRED carry-forward
        for name, sid in FRED_SERIES.items():
            if not row.get(name):
                v = fred_latest_leq(sid, d)
                if v is not None:
                    row[name] = f"{v:.4f}"

        if dstr in have:
            # update existing row in place
            for i, r in enumerate(rows):
                if r.get("date") == dstr:
                    rows[i] = row
                    break
            print(f"[update] {dstr}")
        else:
            new_rows.append([row[h] for h in HEADERS])
            rows.append(row)
            print(f"[add] {dstr}")

    # Rewrite entire CSV to ensure consistent 4dp formatting
    write_rows(HEADERS, rows)
    print(f"[done] wrote CSV with {len(rows)} total rows (added {len(new_rows)})")

if __name__ == "__main__":
    main()
