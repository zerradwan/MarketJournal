# reformat_yields_4dp.py
import csv
from pathlib import Path

CSV_PATH = Path("data/etf_prices_log.csv")
COLS = ["JAPAN 10 YR (%)", "GERMAN 10 YR (%)", "UK 10 YR (%)"]

def main():
    if not CSV_PATH.exists():
        print("CSV not found:", CSV_PATH); return
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
        headers = f.fieldnames

    changed = 0
    for r in rows:
        for c in COLS:
            s = (r.get(c) or "").strip()
            if s:
                try:
                    r[c] = f"{float(s):.4f}"
                    changed += 1
                except:
                    pass

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"Reformatted {changed} values to 4dp.")

if __name__ == "__main__":
    main()
