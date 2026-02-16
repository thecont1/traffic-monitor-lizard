"""
fix_timestamps.py – Fix same-hour timestamp collisions in traffic data.

When two recordings land in the same hour for the same route (e.g. 09:04 and
09:28), the earlier one was a delayed run intended for the previous hour.  This
script reassigns it to {prev_hour}:50 so each hour has at most one reading per
route.

Usage:
    python fix_timestamps.py              # dry-run (preview only)
    python fix_timestamps.py --apply      # write changes to CSV
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

CSV_PATH = Path(__file__).parent / "csv-bangalore_traffic.csv"
REASSIGN_MINUTE = 50  # earlier collision gets snapped to {prev_hour}:50


def load_data(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_data(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fix_collisions(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Find and fix same-hour collisions, returning (fixed_rows, log_lines)."""

    # Index: (date, hour, route_code) -> list of (original_index, time_str)
    buckets: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for i, row in enumerate(rows):
        hour = row["time"].split(":")[0]
        key = (row["date"], hour, row["route_code"])
        buckets[key].append((i, row["time"]))

    # Track which (date, hour, route_code) slots are occupied
    occupied: set[tuple] = set()
    for key in buckets:
        occupied.add(key)

    changes: list[tuple[int, str, str, str, str]] = []  # (idx, route, old_dt, new_date, new_time)

    for key, entries in buckets.items():
        if len(set(t for _, t in entries)) < 2:
            continue  # all same timestamp — no collision

        date_str, hour_str, route = key

        # Find the distinct timestamps, sort to identify the earlier one
        unique_times = sorted(set(t for _, t in entries))
        earlier_time = unique_times[0]

        # Compute previous hour slot
        dt = datetime.strptime(f"{date_str} {earlier_time}", "%Y-%m-%d %H:%M")
        prev_dt = dt.replace(minute=REASSIGN_MINUTE) - timedelta(hours=1)
        new_date = prev_dt.strftime("%Y-%m-%d")
        new_time = prev_dt.strftime("%H:%M")
        prev_hour = prev_dt.strftime("%H")

        # Check if previous hour is already occupied for this route
        prev_key = (new_date, prev_hour, route)
        if prev_key in occupied:
            changes.append(None)  # marker for skipped
            # Log will note this was skipped
            continue

        # Apply: reassign all rows with the earlier timestamp in this bucket
        for idx, t in entries:
            if t == earlier_time:
                changes.append(
                    (idx, route, f"{date_str} {t}", new_date, new_time)
                )
                rows[idx]["date"] = new_date
                rows[idx]["time"] = new_time

        occupied.add(prev_key)

    # Build log
    log: list[str] = []
    skipped = 0
    fixed = 0
    seen_corrections: set[str] = set()

    for c in changes:
        if c is None:
            skipped += 1
            continue
        idx, route, old_dt, new_date, new_time = c
        correction_key = f"{old_dt} → {new_date} {new_time}"
        if correction_key not in seen_corrections:
            seen_corrections.add(correction_key)
            fixed += 1
            log.append(f"  {old_dt}  →  {new_date} {new_time}  ({route[:12]}… +{len([x for x in changes if x and x[2]==old_dt])-1} more routes)")

    log.insert(0, f"\nCollisions found: {fixed + skipped}")
    log.insert(1, f"  Fixed:   {fixed} (across all routes)")
    log.insert(2, f"  Skipped: {skipped} (previous hour already occupied)")
    log.insert(3, "")
    if fixed:
        log.insert(4, "Corrections:")

    return rows, log


def main():
    parser = argparse.ArgumentParser(description="Fix same-hour timestamp collisions.")
    parser.add_argument("--apply", action="store_true", help="Write changes to CSV (default is dry-run)")
    args = parser.parse_args()

    rows = load_data(CSV_PATH)
    fieldnames = ["date", "time", "route_code", "duration", "distance"]

    fixed_rows, log = fix_collisions(rows)

    for line in log:
        print(line)

    if args.apply:
        # Sort by date, time, route_code for clean output
        fixed_rows.sort(key=lambda r: (r["date"], r["time"], r["route_code"]))
        write_data(CSV_PATH, fixed_rows, fieldnames)
        print(f"\n✓ Written to {CSV_PATH}")
    else:
        print(f"\nDry run — no changes written. Use --apply to save.")


if __name__ == "__main__":
    main()
