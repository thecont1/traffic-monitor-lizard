#!/usr/bin/env python3
"""
Enrich the latest traffic rows with weather data.

Only updates rows from the most recent snapshot time (latest date+time).
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

TRAFFIC_CSV = Path(__file__).parent / "csv-bangalore_traffic.csv"
WEATHER_CSV = Path(__file__).parent / "csv-weather-snapshot.csv"

WEATHER_FIELDS = ["temp", "realfeel_temp", "humidity", "rsi_flag", "aqi_score"]


def load_weather_by_route(path: Path) -> dict:
    """Load weather data keyed by route_code."""
    if not path.exists():
        print("No weather snapshot found", file=sys.stderr)
        return {}

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["route_code"]: {k: row.get(k, "") for k in WEATHER_FIELDS} for row in reader}


def get_latest_timestamp(rows: list) -> tuple:
    """Get the most recent (date, time) from rows."""
    max_key = max((r.get("date", ""), r.get("time", "")) for r in rows)
    return max_key


def main():
    weather_by_route = load_weather_by_route(WEATHER_CSV)
    if not weather_by_route:
        print("No weather data, skipping", file=sys.stderr)
        return

    with open(TRAFFIC_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        # Add weather fields if not present
        for field in WEATHER_FIELDS:
            if field not in fieldnames:
                fieldnames.append(field)
        rows = list(reader)

    latest_date, latest_time = get_latest_timestamp(rows)
    print(f"Enriching rows from {latest_date} {latest_time}")

    enriched_count = 0
    for row in rows:
        if row.get("date") == latest_date and row.get("time") == latest_time:
            route_code = row.get("route_code", "")
            weather = weather_by_route.get(route_code, {})
            for field in WEATHER_FIELDS:
                row[field] = weather.get(field, "")
            enriched_count += 1

    with open(TRAFFIC_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Enriched {enriched_count} traffic rows with weather data")


if __name__ == "__main__":
    main()