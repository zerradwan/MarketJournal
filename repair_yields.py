# repair_yields.py
import os, csv
from pathlib import Path
from datetime import datetime, timedelta, date

CSV_PATH = Path("data/etf_prices_log.csv")

NEEDED_COLS = [
    "US 10 YR (%)",
    "GERMAN 10 YR (%)",
    "UK 10 YR (%)",
    "JAPAN 10 YR (%)",
]

FRED_KEY = os.getenv("FRED_API_KEY")
fred = None
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
    except Exception as e:
        print("[warn] fredapi not available:", e)

SERIES = {
    "US 10 YR (%)":  "DGS10",             # daily
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",# monthly
    "UK 10 YR (%)":     "IRLTLT01GBM156N",# monthly
    "JAPAN 10 YR (%)":  "IRLTLT01JPM156N",# monthly
}

def iso(s:str)->date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()

def latest_leq(series_id: str, d: date):
    if not fred: return None
    try:
        start = d - timedelta(days=90)
        s = fred.get_series(series_id, observation_start=start, observation_end=d)
        if s is not None:
            s = s.dropna()
            if len(s) > 0:
                return float(s.iloc[-1])
    except Exception as e:
        print(f"[warn] FRED fetch failed for {series_id} @ {d}: {e}")
    return None

def main():
    if not CSV_PATH.exists():
        print("[error] CSV not found:", CSV_PATH); return

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    # sanity: ensure needed columns exist in header; add if missing
    changed_header = False
    for col in NEEDED_COLS:
        if col not in headers:
            headers.append(col)
            changed_header = True

    fills = 0
    for r in rows:
        dstr = (r.get("date") or "").strip()
        if not dstr:
            continue
        try:
            d = iso(dstr)
        except Exception:
            print(f"[warn] bad date format in row, skipping: {dstr}")
            continue

        for col in NEEDED_COLS:
            val = (r.get(col) or "").strip()
            if val == "":
                v = latest_leq(SERIES[col], d)
                if isinstance(v, float):
                    r[col] = f"{v:.4f}"
                    fills += 1
                    print(f"[fill] {dstr} {col} -> {r[col]}")

    if fills == 0 and not changed_header:
        print("[info] No missing yields to fill (or FRED unavailable)."); return

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    print(f"[done] Wrote CSV. Filled values: {fills}. Header changed: {changed_header}")

if __name__ == "__main__":
    main()
