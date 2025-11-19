import os
import sys
import requests
import pandas as pd

EODHD_API_TOKEN = os.getenv("EODHD_API_TOKEN")
if not EODHD_API_TOKEN:
    print("ERROR: EODHD_API_TOKEN not set in environment.")
    sys.exit(1)

EODHD_BASE_URL = "https://eodhd.com/api/eod"

# EODHD Government Bond tickers (10Y gov bond, daily data)
# See EODHD docs: DE10Y.GBOND, JP10Y.GBOND, UK10Y.GBOND
GBOND_MAP = {
    "GERMAN 10 YR (%)": "DE10Y.GBOND",  # Germany 10Y
    "JAPAN 10 YR (%)":  "JP10Y.GBOND",  # Japan 10Y
    "UK 10 YR (%)":     "UK10Y.GBOND",  # UK 10Y
}


def fetch_gbond_series(symbol: str, start_date: str, end_date: str) -> pd.Series:
    """
    Fetch daily 10Y government bond data from EODHD for the given symbol
    and return it as a pandas Series indexed by date (Timestamp),
    using the 'close' field as the yield/price.
    """
    params = {
        "api_token": EODHD_API_TOKEN,
        "fmt": "json",
        "from": start_date,
        "to": end_date,
    }

    url = f"{EODHD_BASE_URL}/{symbol}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list):
        print(f"Unexpected response for {symbol}: {data}")
        sys.exit(1)

    dates = []
    values = []
    for row in data:
        # EODHD standard EOD format: {'date': 'YYYY-MM-DD', 'open': ..., 'close': ...}
        date_str = row.get("date")
        close_val = row.get("close")
        if date_str is None or close_val is None:
            continue
        dates.append(date_str)
        values.append(float(close_val))

    if not dates:
        print(f"No data returned for {symbol} between {start_date} and {end_date}.")
        return pd.Series(dtype=float)

    s = pd.Series(values, index=pd.to_datetime(dates))
    s.name = symbol
    return s.sort_index()


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
    before = len(df)
    df = df.dropna(how="all")
    after = len(df)
    if after < before:
        print(f"Dropped {before - after} completely-empty row(s).")

    # Make sure dates are sorted + parsed
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    start_date = df[date_col].min().strftime("%Y-%m-%d")
    end_date = df[date_col].max().strftime("%Y-%m-%d")
    print(f"Fetching bond data from {start_date} to {end_date}.")

    # --- Fetch and align daily 10Y yields -----------------------------------
    for col_name, symbol in GBOND_MAP.items():
        print(f"Fetching {col_name} from EODHD ({symbol})...")
        s = fetch_gbond_series(symbol, start_date, end_date)

        if s.empty:
            print(f"WARNING: No data for {symbol}, leaving {col_name} unchanged.")
            continue

        # Reindex to the CSV's dates and forward-fill across weekends/holidays
        aligned = (
            s.reindex(df[date_col])
             .ffill()
        )

        df[col_name] = aligned.values

    # --- Save back to CSV ----------------------------------------------------
    df.to_csv(csv_path, index=False)
    print(f"Updated {csv_path} with DAILY global 10Y yields and removed empty rows.")


if __name__ == "__main__":
    main()
