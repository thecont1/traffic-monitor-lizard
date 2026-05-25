"""
fix_timestamps.py – Simple deduplication for traffic data.

Keeps only one reading per route per hour.
Only processes records older than 24 hours; recent data is left untouched.

Usage:
    python fix_timestamps.py              # dry-run (preview only)
    python fix_timestamps.py --apply      # write changes to CSV
"""

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "csv-traffic-bangalore.csv"
FIELDNAMES = ["date", "time", "route_code", "duration", "distance", "temp", "realfeel", "humidity", "rsi_flag", "aqi"]


def load_data(path: Path) -> list[dict]:
    """Load CSV, skipping empty or malformed rows that lack required keys."""
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip None keys caused by extra trailing commas/columns
            row = {k: v for k, v in row.items() if k is not None}
            if not row.get("date") or not row.get("time") or not row.get("route_code"):
                continue
            rows.append(row)
    return rows


def write_data(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_row_datetime(row: dict) -> datetime:
    return datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")


def deduplicate(rows: list[dict]) -> tuple[list[dict], int]:
    """
    Keep only one reading per route per hour.
    Key is (date, hour, route_code). Keeps the first occurrence.
    Returns (cleaned_rows, removed_count).
    """
    seen: set[tuple[str, str, str]] = set()
    cleaned = []
    removed = 0
    for row in rows:
        hour = row["time"].split(":")[0]
        key = (row["date"], hour, row["route_code"])
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        cleaned.append(row)
    return cleaned, removed


def main():
    parser = argparse.ArgumentParser(
        description="Keep one reading per route per hour for data older than 24 hours."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to CSV (default is dry-run)"
    )
    args = parser.parse_args()

    rows = load_data(CSV_PATH)

    # Only deduplicate records older than 24 hours from now (IST).
    cutoff = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(hours=24)
    cutoff_naive = cutoff.replace(tzinfo=None)

    old_rows = []
    recent_rows = []
    for row in rows:
        ts = parse_row_datetime(row)
        if ts < cutoff_naive:
            old_rows.append(row)
        else:
            recent_rows.append(row)

    cleaned_old, removed = deduplicate(old_rows)

    # Merge deduplicated old rows with untouched recent rows
    cleaned_rows = cleaned_old + recent_rows
    cleaned_rows.sort(key=lambda r: (r["date"], r["time"], r["route_code"]))

    print(f"\nDeduplication Summary:")
    print(f"  Total rows before:      {len(rows):,}")
    print(f"  Old rows (deduped):     {len(old_rows):,}")
    print(f"  Old duplicates removed: {removed:,}")
    print(f"  Recent rows (preserved):{len(recent_rows):,}")
    print(f"  Total rows after:       {len(cleaned_rows):,}")

    if args.apply:
        write_data(CSV_PATH, cleaned_rows)
        print(f"\n✓ Written {len(cleaned_rows):,} rows to {CSV_PATH}")
    else:
        print(f"\nDry run — no changes written. Use --apply to save.")


if __name__ == "__main__":
    main()
