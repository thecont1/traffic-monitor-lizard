#!/usr/bin/env python3
"""
Add weather columns to the traffic CSV if they don't exist.
"""
import csv
from pathlib import Path

TRAFFIC_CSV = Path(__file__).parent / "csv-bangalore_traffic.csv"
WEATHER_FIELDS = ["temp", "realfeel_temp", "humidity", "rsi_flag", "aqi_score"]


def main():
    with open(TRAFFIC_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # Check if weather fields need to be added
    needs_update = False
    for field in WEATHER_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
            needs_update = True

    if not needs_update:
        print("Weather fields already exist in CSV")
        return

    # Add empty weather fields to existing rows
    for row in rows:
        for field in WEATHER_FIELDS:
            if field not in row:
                row[field] = ""

    with open(TRAFFIC_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Added weather fields to {len(rows)} rows in CSV")