import os
import sys
import requests
import pandas as pd

FRED_API_KEY = os.getenv("FRED_API_KEY")
if not FRED_API_KEY:
    print("ERROR: FRED_API_KEY not set in environment.")
    sys.exit(1)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED series IDs (10Y gov bond yields, %)
SERIES_MAP = {
    "GERMAN 10 YR (%)": "IRLTLT01DEM156N",  # Germany :contentReference[oaicite:0]{index=0}
    "JAPAN 10 YR (%)":  "IRLTLT01JPM156N",  # Japan :contentReference[oaicite:1]{index=1}
    "UK 10 YR (%)":     "IRLTLT01GBM156N",  # United Kingdom :contentReference[oaicite:2]{index=2}
}

def fetch_fred_series(series_id: str) -> pd.Series:
    """
    Fetch a FRED series and return it as a pandas Series indexed by date (Timestamp),
    with float values. Missing values ('.') are dropped.
    """
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        # You can tighten this if you want, but this is fine for a small series.
        "observation_start": "1990-01-01",
    }

    resp = requests.get(FRED_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()["observations"]

    dates = []
    values = []
    for obs in data:
        v = obs["value"]
        if v == ".":
            continue
        dates.append(obs["date"])
        values.append(float(v))

    s = pd.Series(values, index=pd.to_datetime(dates))
    s.name = series_id
    return s


def main():
    # --- Load markets.csv ----------------------------------------------------
    csv_path = os.path.join("data", "markets.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # Figure out the date column name (likely "Date" or "DATE")
    date_col = None
    for candidate in ["Date", "DATE", "date"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None:
        print("ERROR: Could not find a date column (looked for 'Date', 'DATE', 'date').")
        sys.exit(1)

    # --- Clean the "empty row" ----------------------------------------------
    # Drop rows that are completely empty (all NaN)
    before = len(df)
    df = df.dropna(how="all")
    after = len(df)
    if after < before:
        print(f"Dropped {before - after} completely-empty row(s).")

    # Make sure dates are sorted + parsed
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    # --- Fetch and align global 10Y yields ----------------------------------
    for col_name, series_id in SERIES_MAP.items():
        print(f"Fetching {col_name} from FRED ({series_id})...")
        s = fetch_fred_series(series_id)  # monthly series

        # Reindex to the CSV's dates and forward-fill (e.g., monthly value across days)
        aligned = s.reindex(df[date_col]).ffill()

        # If the column doesn't exist yet, create it; otherwise overwrite
        df[col_name] = aligned.values

    # --- Save back to CSV ----------------------------------------------------
    df.to_csv(csv_path, index=False)
    print(f"Updated {csv_path} with global 10Y yields and removed empty rows.")


if __name__ == "__main__":
    main()
