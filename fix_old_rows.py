# fix_old_rows.py
import csv
import shutil
from pathlib import Path
import argparse

CSV_PATH = Path("data/etf_prices_log.csv")

US_COL   = "US 10 YR (%)"
FOUR_DP_COLS = ["JAPAN 10 YR (%)", "GERMAN 10 YR (%)", "UK 10 YR (%)", US_COL]

def parse_args():
    p = argparse.ArgumentParser(description="Fix historical yield rows in CSV.")
    p.add_argument("--all", action="store_true",
                   help="Multiply ALL non-empty US 10Y values by 10 (not just small ones).")
    return p.parse_args()

def to_float(s):
    try:
        return float(str(s).strip())
    except:
        return None

def main():
    args = parse_args()

    if not CSV_PATH.exists():
        print(f"[error] CSV not found: {CSV_PATH}")
        return

    # Backup first
    bk = CSV_PATH.with_suffix(".bak")
    shutil.copyfile(CSV_PATH, bk)
    print(f"[backup] Wrote {bk}")

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    if US_COL not in headers:
        print(f"[error] Column not found: {US_COL}")
        return

    us_scaled = 0
    four_dp_set = 0

    for r in rows:
        # 1) Fix US 10Y scaling
        usv = to_float(r.get(US_COL, ""))
        if usv is not None:
            if args.all:
                usv *= 10.0
                r[US_COL] = f"{usv:.4f}"
                us_scaled += 1
            else:
                # Safe heuristic: scale only clearly-too-small modern values
                if 0 < usv < 2.0:
                    usv *= 10.0
                    r[US_COL] = f"{usv:.4f}"
                    us_scaled += 1
                else:
                    # still normalize to 4dp
                    r[US_COL] = f"{usv:.4f}"
                    four_dp_set += 1

        # 2) Normalize JP/DE/UK to 4dp
        for c in ["JAPAN 10 YR (%)", "GERMAN 10 YR (%)", "UK 10 YR (%)"]:
            v = to_float(r.get(c, ""))
            if v is not None:
                r[c] = f"{v:.4f}"
                four_dp_set += 1

    # 3) Sort rows by date ascending (if 'date' present)
    if "date" in headers:
        rows.sort(key=lambda x: x.get("date", ""))

    # 4) Write back
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    print(f"[done] US 10Y scaled: {us_scaled} rows; 4dp normalized: {four_dp_set} cells")
    print(f"[ok] Updated {CSV_PATH}")

if __name__ == "__main__":
    main()
