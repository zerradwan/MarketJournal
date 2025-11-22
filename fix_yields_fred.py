# fix_yields_fred.py
# Fetch actual FRED data and update all dates with correct monthly values
import os, csv
from datetime import datetime, date
from pathlib import Path
import requests
import urllib3

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

def fetch_fred_series(series_id: str):
    """Fetch full FRED series and return dict mapping YYYY-MM to value."""
    try:
        params = {
            "series_id": series_id,
            "api_key": FRED_KEY,
            "file_type": "json",
            "observation_start": "2025-01-01",  # Start from beginning of year
        }
        
        resp = requests.get(FRED_BASE_URL, params=params, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
        
        if "observations" not in data:
            return {}
        
        # Create mapping: YYYY-MM -> value
        monthly_values = {}
        for obs in data["observations"]:
            val = obs.get("value", ".")
            if val != "." and val is not None:
                try:
                    date_str = obs["date"]
                    # Extract YYYY-MM from date
                    year_month = date_str[:7]  # "2025-09" from "2025-09-15"
                    monthly_values[year_month] = float(val)
                except (ValueError, TypeError, KeyError):
                    continue
        
        return monthly_values
    except Exception as e:
        print(f"[error] Failed to fetch {series_id}: {e}")
        return {}

def main():
    if not CSV_PATH.exists():
        print(f"[error] CSV not found: {CSV_PATH}")
        return

    # Fetch all FRED series
    print("Fetching FRED data...")
    fred_data = {}
    for col_name, series_id in FRED_SERIES.items():
        print(f"  Fetching {col_name} ({series_id})...")
        monthly_values = fetch_fred_series(series_id)
        if monthly_values:
            fred_data[col_name] = monthly_values
            print(f"    Got {len(monthly_values)} monthly values")
        else:
            print(f"    [warn] No data for {col_name}")

    if not fred_data:
        print("[error] No FRED data retrieved")
        return

    # Load CSV
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    # Update rows with FRED data
    changed = 0
    for row in rows:
        date_str = row.get("date", "").strip()
        if not date_str:
            continue
        
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            year_month = date_str[:7]  # "2025-09"
            
            for col_name in FRED_SERIES.keys():
                if col_name in fred_data:
                    monthly_values = fred_data[col_name]
                    if year_month in monthly_values:
                        new_val = f"{monthly_values[year_month]:.4f}"
                        old_val = row.get(col_name, "").strip()
                        if old_val != new_val:
                            row[col_name] = new_val
                            changed += 1
                            print(f"[update] {date_str} {col_name}: {old_val} -> {new_val}")
        except Exception as e:
            print(f"[error] Processing {date_str}: {e}")
            continue

    if changed == 0:
        print("[info] No changes needed")
        return

    # Write back
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] Updated {changed} values from FRED")

if __name__ == "__main__":
    main()

