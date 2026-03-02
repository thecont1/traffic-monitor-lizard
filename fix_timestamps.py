"""
fix_timestamps.py – Cycle-aware smart deduplication for traffic data.

Ensures only one reading per cycle per route, where a cycle starts at HH:10
and ends at (HH+1):09. This captures delayed HH:40 backup runs that spill into
the next clock hour while still preserving one data point per intended hour.

Selection Strategy (in priority order):
1. Prefer readings closer to intended cycle offsets (0 or 30 minutes)
2. If both equally close, prefer the later reading (more recent data)
3. Remove all other readings in that cycle

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
CYCLE_START_MINUTE = 10
TARGET_OFFSETS = [0, 30]  # :10 and :40 within a cycle starting at :10


def load_data(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_data(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_row_datetime(row: dict) -> datetime:
    """Parse row date/time into a datetime."""
    return datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")


def get_cycle_start(ts: datetime) -> datetime:
    """
    Map a timestamp to its cycle start.

    A cycle starts at HH:10 and ends at (HH+1):09. This captures delayed
    HH:40 executions that spill into the next clock hour.
    """
    cycle = ts.replace(minute=CYCLE_START_MINUTE, second=0, microsecond=0)
    if ts.minute < CYCLE_START_MINUTE:
        cycle -= timedelta(hours=1)
    return cycle


def cycle_distance_to_target(ts: datetime, cycle_start: datetime) -> int:
    """Distance in minutes to the nearest intended offset (:10 or :40)."""
    offset = int((ts - cycle_start).total_seconds() // 60)
    return min(abs(offset - target) for target in TARGET_OFFSETS)


def select_best_reading(entries: list[tuple[int, datetime, datetime]]) -> int:
    """
    Select the best reading from multiple entries in the same cycle.
    
    Returns the index of the entry to keep.
    
    Strategy:
    1. Prefer readings closest to intended cycle offsets (:10 or :40)
    2. If tied, prefer later reading (more recent)
    """
    if len(entries) == 1:
        return entries[0][0]
    
    # Calculate scores within the same cycle bucket
    scored_entries = []
    for idx, ts, cycle_start in entries:
        distance = cycle_distance_to_target(ts, cycle_start)
        # Score: (distance_to_target, -timestamp)
        # Lower distance is better; for ties keep the later reading.
        scored_entries.append((distance, -ts.timestamp(), idx, ts.strftime("%H:%M")))
    
    # Sort by score (best first)
    scored_entries.sort()
    
    # Return index of best entry
    return scored_entries[0][2]


def deduplicate_same_cycle(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Remove duplicate readings in the same cycle, keeping the best one.
    
    Returns (cleaned_rows, log_lines).
    """
    # Index: (cycle_date, cycle_hour, route_code) -> list of
    # (original_index, timestamp, cycle_start)
    buckets: dict[tuple, list[tuple[int, datetime, datetime]]] = defaultdict(list)
    for i, row in enumerate(rows):
        ts = parse_row_datetime(row)
        cycle_start = get_cycle_start(ts)
        key = (cycle_start.date().isoformat(), f"{cycle_start.hour:02d}", row["route_code"])
        buckets[key].append((i, ts, cycle_start))
    
    # Track which indices to keep
    indices_to_keep = set()
    removed_count = 0
    collision_count = 0
    examples = []
    
    for key, entries in buckets.items():
        unique_times = set(ts.strftime("%H:%M") for _, ts, _ in entries)
        
        if len(unique_times) == 1:
            # All same timestamp - keep first occurrence only
            indices_to_keep.add(entries[0][0])
            if len(entries) > 1:
                removed_count += len(entries) - 1
        elif len(unique_times) > 1:
            # Multiple different timestamps in same cycle - select best
            collision_count += 1
            best_idx = select_best_reading(entries)
            indices_to_keep.add(best_idx)
            removed_count += len(entries) - 1
            
            # Log example
            if len(examples) < 5:
                cycle_date, cycle_hour, route = key
                kept_time = rows[best_idx]["time"]
                all_times = sorted(unique_times)
                examples.append(
                    f"  cycle {cycle_date} {cycle_hour}:10 {route[:15]:15s} → kept {kept_time} from {all_times}"
                )
    
    # Build cleaned rows
    cleaned_rows = [row for i, row in enumerate(rows) if i in indices_to_keep]
    
    # Build log
    log = [
        f"\nDeduplication Summary:",
        f"  Total rows before: {len(rows):,}",
        f"  Total rows after:  {len(cleaned_rows):,}",
        f"  Rows removed:      {removed_count:,}",
        f"",
        f"  Same-cycle collisions found: {collision_count}",
    ]
    
    if examples:
        log.append("")
        log.append("Examples of collision resolution:")
        log.extend(examples)
    
    return cleaned_rows, log


def main():
    parser = argparse.ArgumentParser(
        description="Cycle-aware deduplication: keep one reading per collection cycle per route."
    )
    parser.add_argument(
        "--apply", 
        action="store_true", 
        help="Write changes to CSV (default is dry-run)"
    )
    args = parser.parse_args()
    
    rows = load_data(CSV_PATH)
    fieldnames = ["date", "time", "route_code", "duration", "distance"]
    
    cleaned_rows, log = deduplicate_same_cycle(rows)
    
    for line in log:
        print(line)
    
    if args.apply:
        # Sort by date, time, route_code for clean output
        cleaned_rows.sort(key=lambda r: (r["date"], r["time"], r["route_code"]))
        write_data(CSV_PATH, cleaned_rows, fieldnames)
        print(f"\n✓ Written {len(cleaned_rows):,} rows to {CSV_PATH}")
    else:
        print(f"\nDry run — no changes written. Use --apply to save.")


if __name__ == "__main__":
    main()
