#!/usr/bin/env python3
"""
Generate the calendar day-anomaly export for frontend consumption.

Reads the raw traffic CSV, scores every route × civil date × time-of-day filter
with :mod:`calendar_anomalies`, and writes a single derived CSV:

    data/csv-calendar-anomalies-bangalore.csv

The ``csv-`` prefix is required by the frontend's Worker / Vite CSV proxy
policy (``/api/traffic-csv/<filename>``).

The export is deterministic for unchanged past inputs: a later appended
observation can only change the newest day's provisional/final record, never a
finalised historical one (the reference window ends the day before the target).

Usage:
    python3 generate_calendar_exports.py
    python3 generate_calendar_exports.py --as-of 2026-10-23T22:00
    python3 generate_calendar_exports.py --tod weekday_evening
    python3 generate_calendar_exports.py --audit 'XMW9+G8|WMJR+V4:2026-10-16:weekday_evening'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from calendar_anomalies import (
    CITY_TIMEZONE,
    LOOKBACK_DAYS,
    METHOD_VERSION,
    WINDOW_BY_TOD,
    WINDOW_SPECS,
    build_audit_payload,
    generate_anomaly_records,
    prepare_observations,
)

DATA_DIR = Path(__file__).parent.parent / "data"
TRAFFIC_CSV = DATA_DIR / "csv-traffic-bangalore.csv"
ROUTES_CSV = DATA_DIR / "csv-routes-bangalore.csv"
OUTPUT_CSV = DATA_DIR / "csv-calendar-anomalies-bangalore.csv"

REQUIRED_COLUMNS = ("date", "time", "route_code", "duration", "distance")


def file_digest(path: Path, chunk_size: int = 1 << 20) -> str:
    """Short content digest used as the export's source_revision."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()[:12]


def load_traffic(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise SystemExit(f"ERROR: traffic CSV not found at {csv_path}")
    df = pd.read_csv(csv_path)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise SystemExit(f"ERROR: traffic CSV missing required columns: {sorted(missing)}")
    return df


def parse_audit_args(values: list[str] | None) -> list[tuple[str, str, str]]:
    """Parse ``ROUTE:YYYY-MM-DD:TOD`` triples (route codes contain ``|``)."""
    if not values:
        return []
    triples: list[tuple[str, str, str]] = []
    for value in values:
        parts = value.rsplit(":", 2)
        if len(parts) != 3:
            raise SystemExit(f"ERROR: --audit expects ROUTE:DATE:TOD, got {value!r}")
        route, day, tod = parts
        if tod not in WINDOW_BY_TOD:
            raise SystemExit(
                f"ERROR: unknown tod {tod!r}; expected one of {sorted(WINDOW_BY_TOD)}"
            )
        triples.append((route, day, tod))
    return triples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the calendar anomaly export")
    parser.add_argument("--traffic-csv", type=Path, default=TRAFFIC_CSV)
    parser.add_argument("--routes-csv", type=Path, default=ROUTES_CSV)
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    parser.add_argument(
        "--as-of",
        default=None,
        help=(
            "City-local evaluation moment (YYYY-MM-DD[THH:MM]). Defaults to the "
            "current Asia/Kolkata wall clock."
        ),
    )
    parser.add_argument(
        "--tod",
        action="append",
        default=None,
        help=f"Restrict to a tod bucket (repeatable). Default: all of {[s.tod for s in WINDOW_SPECS]}",
    )
    parser.add_argument(
        "--route",
        action="append",
        default=None,
        help="Restrict to a route_code (repeatable).",
    )
    parser.add_argument(
        "--audit",
        action="append",
        default=None,
        help="Print the audit payload for ROUTE:DATE:TOD (repeatable) instead of writing the export.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    traffic = load_traffic(args.traffic_csv)
    observations = prepare_observations(traffic)

    if not args.quiet:
        print(f"Loaded {len(traffic)} raw rows from {args.traffic_csv.name}")
        print(f"  Usable observations: {len(observations)}")
        if len(observations):
            print(
                "  Date range: "
                f"{observations['date'].min()} to {observations['date'].max()} · "
                f"routes: {observations['route_code'].nunique()}"
            )
        print(f"  Method: {METHOD_VERSION} · lookback {LOOKBACK_DAYS} days · {CITY_TIMEZONE}")

    audit_requests = parse_audit_args(args.audit)
    if audit_requests:
        for route, day, tod in audit_requests:
            try:
                payload = build_audit_payload(
                    observations,
                    route_code=route,
                    target_date=day,
                    tod=tod,
                    as_of=args.as_of,
                )
            except ValueError as exc:
                raise SystemExit(f"ERROR: {exc}") from exc
            # Keep the audit output traceable to the exact input file, exactly
            # like the CSV rows it is meant to explain.
            payload["source_revision"] = file_digest(args.traffic_csv)
            print(json.dumps(payload, indent=2, sort_keys=False))
        return 0

    specs = WINDOW_SPECS
    if args.tod:
        unknown = [t for t in args.tod if t not in WINDOW_BY_TOD]
        if unknown:
            raise SystemExit(f"ERROR: unknown --tod values {unknown}")
        specs = tuple(WINDOW_BY_TOD[t] for t in args.tod)

    records = generate_anomaly_records(
        observations,
        as_of=args.as_of,
        specs=specs,
        route_codes=args.route,
        source_revision=file_digest(args.traffic_csv),
    )

    if records.empty:
        raise SystemExit("ERROR: no anomaly records produced")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records.to_csv(args.output, index=False, na_rep="")

    if not args.quiet:
        status_counts = records["status"].value_counts().to_dict()
        category_counts = records["category"].value_counts(dropna=True).to_dict()
        print(f"\n=== Export written: {len(records)} rows → {args.output} ===")
        print(f"  statuses:   {status_counts}")
        print(f"  categories: {category_counts or '{}'}")

        # Route labels are display metadata owned by the routes CSV, never part
        # of the canonical export.
        label_map: dict[str, str] = {}
        if args.routes_csv.exists():
            routes = pd.read_csv(args.routes_csv)
            if {"route_code", "label_short"}.issubset(routes.columns):
                label_map = dict(zip(routes["route_code"], routes["label_short"]))

        latest = records[records["status"].isin(["final", "provisional"])].tail(4)
        for row in latest.itertuples(index=False):
            label = label_map.get(row.route_code, row.route_code)
            print(
                f"  {row.date} {row.tod_bucket:16s} {label:22.22s} "
                f"{row.status:11s} {str(row.category or '-'):11s} "
                f"{_fmt(row.observed_minutes)} vs {_fmt(row.typical_minutes)} min "
                f"(rank {_fmt(row.rank_score)})"
            )
    return 0


def _fmt(value: object) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "–"
    return f"{float(value):.1f}"


if __name__ == "__main__":
    sys.exit(main())
