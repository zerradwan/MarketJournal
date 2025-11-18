# backfill_yields_after_917.py
# Backfill JAPAN, GERMAN, UK 10 YR (%) values for all dates after 2025-09-17
import os, csv
from datetime import datetime, timedelta, date
from pathlib import Path

FRED_KEY = os.getenv("FRED_API_KEY")
fred = None
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
        print(f"[ok] FRED API initialized")
    except Exception as e:
        print(f"[warn] FRED API not available: {e}")
        fred = None
else:
    print("[warn] FRED_API_KEY not set, will use carry-forward only")

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
    if not fred:
        return None
    try:
        start = d - timedelta(days=90)  # cover month boundaries
        s = fred.get_series(series_id, observation_start=start, observation_end=d)
        if s is not None:
            s = s.dropna()
            if len(s) > 0:
                return float(s.iloc[-1])
    except Exception as e:
        print(f"[warn] FRED lookup failed for {series_id} on {d}: {e}")
    return None

def parse_float(s: str) -> float | None:
    """Parse a float from string, return None if empty/invalid."""
    if not s or not s.strip():
        return None
    try:
        return float(s.strip())
    except ValueError:
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
    cutoff_str = "2025-09-17"

    # Track last known values (carry-forward)
    last_known = {col: None for col in TARGET_COLS}

    # First pass: find last known values before/on cutoff
    for row in rows:
        dstr = row.get("date", "").strip()
        if not dstr:
            continue
        try:
            d = iso(dstr)
            if d <= cutoff_date:
                # Update last known values
                for col in TARGET_COLS:
                    val = parse_float(row.get(col, ""))
                    if val is not None:
                        last_known[col] = val
        except Exception:
            continue

    print(f"[info] Last known values before {cutoff_str}:")
    for col in TARGET_COLS:
        print(f"  {col}: {last_known[col]}")

    # Second pass: fill missing values for dates after cutoff
    changed = 0
    for row in rows:
        dstr = row.get("date", "").strip()
        if not dstr:
            continue
        try:
            d = iso(dstr)
            if d <= cutoff_date:
                continue  # Skip dates on/before cutoff

            # Check if any of the target columns are missing
            needs_update = False
            for col in TARGET_COLS:
                val = parse_float(row.get(col, ""))
                if val is None:
                    needs_update = True
                    break

            if not needs_update:
                continue  # All values already present

            # Try to get FRED values, fallback to carry-forward
            for col in TARGET_COLS:
                current_val = parse_float(row.get(col, ""))
                if current_val is not None:
                    # Already has value, update last_known and skip
                    last_known[col] = current_val
                    continue

                # Try FRED first
                series_id = FRED_SERIES[col]
                fred_val = fred_latest_leq(series_id, d)
                
                if fred_val is not None:
                    # Use FRED value
                    row[col] = f"{fred_val:.4f}"
                    last_known[col] = fred_val
                    changed += 1
                    print(f"[fill] {dstr} {col} -> {fred_val:.4f} (FRED)")
                elif last_known[col] is not None:
                    # Carry forward last known value
                    row[col] = f"{last_known[col]:.4f}"
                    changed += 1
                    print(f"[fill] {dstr} {col} -> {last_known[col]:.4f} (carry-forward)")
                else:
                    print(f"[warn] {dstr} {col} -> no value available (no FRED, no last known)")

        except Exception as e:
            print(f"[error] Processing row {dstr}: {e}")
            continue

    if changed == 0:
        print("[info] No changes needed (all values already present or unavailable)")
        return

    # Write back
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] Updated CSV with {changed} filled values")

if __name__ == "__main__":
    main()

