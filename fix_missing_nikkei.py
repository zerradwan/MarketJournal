# fix_missing_nikkei.py
# Fix missing NIKKEI values for Japanese market holidays by using previous trading day
import csv
from pathlib import Path

CSV_PATH = Path("data/etf_prices_log.csv")
COL = "NIKKEI"

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

    # Track last known NIKKEI value
    last_nikkei = None
    
    fixed = 0
    for row in rows:
        dstr = row.get("date", "").strip()
        if not dstr:
            continue
            
        current_nikkei = row.get(COL, "").strip()
        
        # Update last known value if current row has a value
        if current_nikkei:
            try:
                last_nikkei = float(current_nikkei)
            except ValueError:
                pass
        
        # Fill missing value with last known (carry-forward)
        if not current_nikkei and last_nikkei is not None:
            row[COL] = f"{last_nikkei:.2f}"
            fixed += 1
            print(f"[fill] {dstr} {COL} -> {last_nikkei:.2f} (previous trading day)")

    if fixed == 0:
        print("[info] No missing NIKKEI values to fill")
        return

    # Write back
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] Filled {fixed} missing NIKKEI values")

if __name__ == "__main__":
    main()
