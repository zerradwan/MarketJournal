# fill_missing_yields.py
import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path

FRED_KEY = os.getenv("FRED_API_KEY")
fred = None
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
    except Exception:
        fred = None

CSV_PATH = Path("data/etf_prices_log.csv")
TARGET_DATES = {
    "2025-09-05","2025-09-08","2025-09-09","2025-09-10",
    "2025-09-11","2025-09-12","2025-09-15","2025-09-16",
}

FRED_SERIES = {
    "US 10 YR (%)":  {"id": "DGS10"},             # daily
    "GERMAN 10 YR (%)": {"id": "IRLTLT01DEM156N"},# monthly
    "UK 10 YR (%)":     {"id": "IRLTLT01GBM156N"},# monthly
    "JAPAN 10 YR (%)":  {"id": "IRLTLT01JPM156N"},# monthly
}

def iso(s): return datetime.strptime(s, "%Y-%m-%d").date()

def fred_latest_leq(series_id: str, d: date):
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

def main():
    if not CSV_PATH.exists():
        print("CSV not found:", CSV_PATH); return

    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
        headers = f.fieldnames

    changed = 0
    for r in rows:
        dstr = r.get("date", "")
        if dstr not in TARGET_DATES:
            continue
        d = iso(dstr)
        for col, meta in FRED_SERIES.items():
            if r.get(col, "").strip() == "":
                val = fred_latest_leq(meta["id"], d)
                if isinstance(val, float):
                    r[col] = f"{val:.2f}"
                    changed += 1
                    print(f"[fill] {dstr} {col} -> {r[col]}")

    if changed == 0:
        print("No fills applied (either already filled, or FRED unavailable).")
        return

    # Write back (overwrite CSV)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"[done] Updated CSV with {changed} filled values.")

if __name__ == "__main__":
    main()
