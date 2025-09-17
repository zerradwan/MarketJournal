# update_market_journal.py
import os
from datetime import datetime, date, timezone
import pandas as pd
import pytz
import yfinance as yf

# ---------- Helpers ----------
NY_TZ = pytz.timezone("America/New_York")

def prev_trading_close(ticker: str):
    """
    Return the most recent fully-settled DAILY Close for a Yahoo ticker.
    We pull 10d of daily history and take the last row whose date is < today's date in New York.
    This avoids intraday/unfinished sessions.
    """
    try:
        hist = yf.Ticker(ticker).history(period="10d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        # Convert the index to NY date
        idx = hist.index.tz_localize("UTC") if hist.index.tz is None else hist.index
        idx_ny = idx.tz_convert(NY_TZ)
        hist = hist.copy()
        hist["_date_ny"] = idx_ny.date

        today_ny = datetime.now(NY_TZ).date()
        settled = hist[hist["_date_ny"] < today_ny]
        if settled.empty:
            # If you run very late at night, today might be settled already; fall back to last available
            settled = hist
        return float(settled["Close"].dropna().iloc[-1])
    except Exception:
        return None

def fred_latest(series_id: str):
    """
    Get latest (most recent non-NaN) value from FRED.
    Requires env var FRED_API_KEY to be set.
    """
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return None
    try:
        from fredapi import Fred
        fred = Fred(api_key=key)
        s = fred.get_series(series_id)
        if s is None:
            return None
        s = s.dropna()
        if s.empty:
            return None
        return float(s.iloc[-1])
    except Exception:
        return None

def build_row():
    """
    Build a {column_name: value} dict that matches your Excel headers.
    """
    row = {}
    # FX
    row["EURO/USD"] = prev_trading_close("EURUSD=X")
    row["STG/USD"]  = prev_trading_close("GBPUSD=X")
    row["USD/YEN"]  = prev_trading_close("JPY=X")        # USD/JPY

    # Indices
    row["NIKKEI"] = prev_trading_close("^N225")
    row["DAX"]   = prev_trading_close("^GDAXI")         # note trailing space
    row["FTSE"]   = prev_trading_close("^FTSE")
    row["DOW"]    = prev_trading_close("^DJI")
    row["S&P"]    = prev_trading_close("^GSPC")

    # Yields
    # US 10Y from ^TNX (Yahoo quote is yield * 10)
    tnx = prev_trading_close("^TNX")
    row["US 10 YR (%)"] = round(tnx / 10.0, 4) if tnx is not None else None

    # JP / DE / UK 10Y via FRED (needs FRED_API_KEY)
    # These are long-term government bond yields, 10-year maturity (OECD harmonized)
    row["JAPAN 10 YR (%)"]  = fred_latest("IRLTLT01JPM156N")
    row["GERMAN 10 YR (%)"] = fred_latest("IRLTLT01DEM156N")
    row["UK 10 YR (%)"]     = fred_latest("IRLTLT01GBM156N")

    # Commodities & Crypto
    row["GOLD"]         = prev_trading_close("GC=F")     # Gold futures
    row["BRENT CRUDE"] = prev_trading_close("BZ=F")     # Brent futures (note trailing space)
    row["BITCOIN"]     = prev_trading_close("BTC-USD")  # BTC spot in USD (note trailing space)
    return row

def append_to_excel(xlsx_path: str, sheet_name: str = "Template"):
    # Load current sheet to preserve column order
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

    # Prepare new record covering every existing column
    new_rec = {col: None for col in df.columns}

    # Date as mm/dd/YYYY (match your sheet style)
    new_rec["DATE"] = date.today().strftime("%m/%d/%Y")

    # Fill values we fetched where headers match
    vals = build_row()
    for k, v in vals.items():
        if k in new_rec:
            new_rec[k] = v

    # Append & save
    out = pd.concat([df, pd.DataFrame([new_rec])], ignore_index=True)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="w") as w:
        out.to_excel(w, index=False, sheet_name=sheet_name)

    print(f"Appended previous-closing prices for {new_rec['DATE']} to {xlsx_path} [{sheet_name}]")

if __name__ == "__main__":
    append_to_excel("/Users/home/Desktop/dmj/journals.xlsx")



