# update_yields_from_fred.py
# Update JAPAN, GERMAN, UK 10 YR (%) values with actual FRED data for all dates after 2025-09-17
import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path
import requests
import urllib3

# Disable SSL warnings (we're using verify=False as workaround for certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FRED_KEY = os.getenv("FRED_API_KEY")
if not FRED_KEY:
    print("[error] FRED_API_KEY not set")
    exit(1)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

CSV_PATH = Path("data/etf_prices_log.csv")

FRED_SERIES = {
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",
    "UK 10 YR (%)":     "IRLTLT01GBM156N",
    "JAPAN 10 YR (%)":  "IRLTLT01JPM156N",
}

TARGET_COLS = list(FRED_SERIES.keys())

def iso(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()

def fred_latest_leq(series_id: str, d: date):
    """Most recent FRED value on/before d (handles monthly series). Returns float or None."""
    try:
        # Look back further to ensure we get the latest monthly value
        start_date = (d - timedelta(days=180)).strftime("%Y-%m-%d")
        end_date = d.strftime("%Y-%m-%d")
        
        params = {
            "series_id": series_id,
            "api_key": FRED_KEY,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
        }
        
        resp = requests.get(FRED_BASE_URL, params=params, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
        
        if "observations" not in data:
            return None
            
        # Get the most recent non-empty value
        values = []
        for obs in data["observations"]:
            val = obs.get("value", ".")
            if val != "." and val is not None:
                try:
                    values.append((obs["date"], float(val)))
                except (ValueError, TypeError):
                    continue
        
        if values:
            # Return the last value (most recent)
            return values[-1][1]
    except Exception as e:
        print(f"[warn] FRED lookup failed for {series_id} on {d}: {e}")
    return None

def main():
    if not CSV_PATH.exists():
        print(f"[error] CSV not found: {CSV_PATH}")
        return

    # Load all rows
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    if not headers:
        print("[error] No headers found")
        return

    # Find cutoff date (2025-09-17)
    cutoff_date = iso("2025-09-17")

    # Update all dates after cutoff with actual FRED data
    changed = 0
    for row in rows:
        dstr = row.get("date", "").strip()
        if not dstr:
            continue
        try:
            d = iso(dstr)
            if d <= cutoff_date:
                continue  # Skip dates on/before cutoff

            # Update each target column with FRED data
            for col in TARGET_COLS:
                series_id = FRED_SERIES[col]
                fred_val = fred_latest_leq(series_id, d)
                
                if fred_val is not None:
                    old_val = row.get(col, "").strip()
                    row[col] = f"{fred_val:.4f}"
                    if old_val != row[col]:
                        changed += 1
                        print(f"[update] {dstr} {col}: {old_val} -> {fred_val:.4f}")
                else:
                    print(f"[warn] {dstr} {col} -> no FRED data available")

        except Exception as e:
            print(f"[error] Processing row {dstr}: {e}")
            continue

    if changed == 0:
        print("[info] No changes needed (all values already match FRED data)")
        return

    # Write back
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] Updated CSV with {changed} values from FRED")

if __name__ == "__main__":
    main()

