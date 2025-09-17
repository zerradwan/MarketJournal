# patch_missing_nikkei.py
import csv
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

CSV_PATH = Path("data/etf_prices_log.csv")
COL = "NIKKEI"

def get_close(ticker, d):
    try:
        df = yf.Ticker(ticker).history(
            start=d, end=d + timedelta(days=2), interval="1d", auto_adjust=False
        )
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None

def main():
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
        headers = f.fieldnames

    fixed = 0
    for r in rows:
        if r.get("date") == "2025-09-15" and not r.get(COL):
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            v = get_close("^N225", d)
            if v is not None:
                r[COL] = f"{v:.2f}"
                fixed += 1

    if fixed:
        with open(CSV_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            w.writerows(rows)
        print(f"[done] Filled {fixed} missing NIKKEI values.")
    else:
        print("[info] No missing NIKKEI values filled.")

if __name__ == "__main__":
    main()
