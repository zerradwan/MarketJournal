# fetch_prices.py
import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path
import yfinance as yf

# ====== Config ======
CSV_PATH = Path("data/etf_prices_log.csv")

HEADERS = [
    "date","EURO/USD","STG/USD","USD/YEN","NIKKEI","DAX","FTSE","DOW","S&P",
    "JAPAN 10 YR (%)","GERMAN 10 YR (%)","UK 10 YR (%)","US 10 YR (%)",
    "GOLD","BRENT CRUDE","BITCOIN"
]

# Yahoo Finance tickers (everything but JP/DE/UK 10Y)
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
    # US 10Y via ^TNX (value is tenths of a percent; divide by 10)
    "US 10 YR (%)": "^TNX",
}

# FRED fallback for JP/DE/UK 10Y (monthly OECD series, carry-forward)
FRED_KEY = os.getenv("FRED_API_KEY")
fred = None
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
    except Exception:
        fred = None

FRED_SERIES = {
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",
    "UK 10 YR (%)":     "IRLTLT01GBM156N",
    "JAPAN 10 YR (%)":  "IRLTLT01JPM156N",
}

# ====== Helpers ======
def today_str() -> str:
    return date.today().isoformat()

def get_close_yf(ticker: str, d: date):
    """Daily close on date d. Use 2-day window and select last row (handles TZ)."""
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
    return None if v is None else (v / 10.0)

def fred_latest_leq(series_id: str, d: date):
    """Most recent FRED value on/before d (handles monthly series). Returns float or None."""
    if not fred:
        return None
    try:
        start = d - timedelta(days=90)
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

# ====== Main ======
def main(target_date: str | None = None):
    ensure_header()
    rows = load_rows()
    have_by_date = {r.get("date"): i for i, r in enumerate(rows) if r.get("date")}

    dstr = target_date or today_str()
    d = datetime.strptime(dstr, "%Y-%m-%d").date()

    # start with existing row or a fresh one
    if dstr in have_by_date:
        row = rows[have_by_date[dstr]].copy()
    else:
        row = {h: "" for h in HEADERS}
        row["date"] = dstr

    # --- Yahoo prices ---
    for name, t in YF_TICKERS.items():
        if name == "US 10 YR (%)":
            v = get_us10y_from_yahoo(d)
        else:
            v = get_close_yf(t, d)
        if v is not None:
            row[name] = f"{v:.4f}"

    # --- FRED carry-forward for JP/DE/UK 10Y ---
    for name, sid in FRED_SERIES.items():
        if not row.get(name):
            v = fred_latest_leq(sid, d)
            if v is not None:
                row[name] = f"{v:.4f}"

    # upsert
    if dstr in have_by_date:
        rows[have_by_date[dstr]] = row
        action = "updated"
    else:
        rows.append(row)
        action = "added"

    # persist entire file (keeps formatting consistent)
    write_rows(HEADERS, rows)
    print(f"[{action}] {dstr} -> wrote daily closes at 4dp")

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
