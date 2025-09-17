import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path
import yfinance as yf

# --- FRED (yields) ---
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

YF_TICKERS = {
    "EURO/USD": "EURUSD=X",
    "STG/USD": "GBPUSD=X",
    "USD/YEN": "JPY=X",   # USD/JPY
    "NIKKEI": "^N225",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "DOW": "^DJI",
    "S&P": "^GSPC",
    "GOLD": "GC=F",
    "BRENT CRUDE": "BZ=F",
    "BITCOIN": "BTC-USD",
}

FRED_SERIES = {
    "US 10 YR (%)": "DGS10",
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",
    "UK 10 YR (%)": "IRLTLT01GBM156N",
    "JAPAN 10 YR (%)": "IRLTLT01JPM156N",
}

def iso(s): return datetime.strptime(s, "%Y-%m-%d").date()

def get_close_yf(ticker: str, d: date):
    try:
        df = yf.Ticker(ticker).history(start=d, end=d + timedelta(days=1), interval="1d", auto_adjust=False)
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None

def get_fred(series: str, d: date):
    if not fred: return None
    try:
        s = fred.get_series(series, observation_start=d, observation_end=d)
        if s is not None and len(s) > 0:
            return float(s.iloc[-1])
    except Exception:
        pass
    return None

def ensure_header():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(HEADERS)

def existing_dates():
    if not CSV_PATH.exists(): return set()
    with open(CSV_PATH, newline="") as f:
        return {r["date"] for r in csv.DictReader(f) if r.get("date")}

def main():
    ensure_header()
    have = existing_dates()
    rows = []

    for dstr in DATES:
        if dstr in have:
            print(f"[skip] {dstr} already present"); continue
        d = iso(dstr)
        row = {h: "" for h in HEADERS}
        row["date"] = dstr

        # FX, indices, gold, brent, btc
        for name, t in YF_TICKERS.items():
            v = get_close_yf(t, d)
            if v is None: continue
            row[name] = f"{v:.4f}" if "USD/" in name else f"{v:.2f}"

        # Yields (percent)
        for name, series in FRED_SERIES.items():
            v = get_fred(series, d)
            if v is not None:
                row[name] = f"{v:.2f}"

        rows.append([row[h] for h in HEADERS])
        print(f"[ok] prepared {dstr}")

    if not rows:
        print("Nothing to append."); return

    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerows(rows)

    print(f"[done] Appended {len(rows)} rows to {CSV_PATH}")

if __name__ == "__main__":
    main()
