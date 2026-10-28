"""
Calendar day-anomaly scoring
============================

Canonical implementation of the "Good Days and Bad Days" day-anomaly measure.

The question this answers is *"was this journey unusually slow or fast for this
weekday and time on this route?"* — not *"was this road faster than another road
today?"*. For a target date it compares one origin–destination journey summary
against the same route, same weekday, same hourly slots over the preceding
LOOKBACK_DAYS days.

Method (see data/SCHEMA.md for the published contract):

  1. Observations are reduced to hourly slot medians of estimated journey
     duration, so an hour with more readings cannot dominate an hour with fewer.
  2. A day summary A_d is the equal-weight mean of its hourly medians over the
     window's required slots. A day only counts when every required slot is
     covered (or, for a day still in progress, a contiguous observed prefix).
  3. The reference B_d is the median of the same summary over eligible earlier
     dates in [target - LOOKBACK_DAYS, target). The target date and everything
     after it is always excluded.
  4. Effect: delta = A_d - B_d (minutes) and fraction = A_d / B_d - 1.
  5. Unusualness: a smoothed mid-rank q = (L + 0.5T + 0.5) / (N + 1) of A_d
     among the reference summaries (`L` strictly below, `T` tied). This is a
     descriptive rank score, not a p-value or a certified population percentile.
  6. Category: history guard (MIN_HISTORY_DAYS), practical-difference guard
     (max(2 minutes, 10 % of the typical value)), then rank band.

All civil-date, weekday and window-boundary arithmetic is done on the source
`date`/`time` strings in the city timezone (Asia/Kolkata) with no browser or
host timezone involvement, so a viewer in UTC or US timezones sees the same
categories.

Nothing here is a modification of R³S²: R³S² remains the city-relative
route-quality score and is exported separately.
"""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta
from statistics import median
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import pandas as pd

# ============================================================================
# Method constants — versioned. Change them only with METHOD_VERSION.
# ============================================================================

METHOD_VERSION = "calendar-anomaly-v1"

CITY_TIMEZONE = "Asia/Kolkata"

#: Reference window: dates in [target - LOOKBACK_DAYS, target).
LOOKBACK_DAYS = 90

#: Fewer eligible reference dates than this produces no anomaly colour.
MIN_HISTORY_DAYS = 8

#: Practical-difference guard: |delta| must reach max(this minutes, fraction * B).
PRACTICAL_MIN_MINUTES = 2.0
PRACTICAL_MIN_FRACTION = 0.10

#: Smoothed mid-rank cut-offs for the five-category scale.
MUCH_BETTER_MAX_RANK = 0.10
BETTER_MAX_RANK = 0.25
WORSE_MIN_RANK = 0.75
MUCH_WORSE_MIN_RANK = 0.90

#: Distance heterogeneity flag (audit only — never removes a day).
DISTANCE_VARIED_FRACTION = 0.10

#: A day in progress whose newest reading is older than this is flagged stale.
STALE_AFTER_MINUTES = 180

# Same validity gates the frontend applies when parsing the raw CSV.
MIN_DURATION_MIN = 0.0
MAX_DURATION_MIN = 300.0
MAX_SPEED_KMH = 150.0
MIN_SPEED_KMH = 0.0

# ============================================================================
# Categories and statuses
# ============================================================================

CATEGORY_MUCH_BETTER = "much_better"
CATEGORY_BETTER = "better"
CATEGORY_USUAL = "usual"
CATEGORY_WORSE = "worse"
CATEGORY_MUCH_WORSE = "much_worse"

CATEGORIES: tuple[str, ...] = (
    CATEGORY_MUCH_BETTER,
    CATEGORY_BETTER,
    CATEGORY_USUAL,
    CATEGORY_WORSE,
    CATEGORY_MUCH_WORSE,
)

STATUS_FINAL = "final"
STATUS_PROVISIONAL = "provisional"
STATUS_NOT_STARTED = "not_started"
STATUS_NO_OBSERVATIONS = "no_observations"
STATUS_INCOMPLETE_WINDOW = "incomplete_window"
STATUS_INSUFFICIENT_HISTORY = "insufficient_history"
STATUS_FUTURE = "future"

STATUSES: tuple[str, ...] = (
    STATUS_FINAL,
    STATUS_PROVISIONAL,
    STATUS_NOT_STARTED,
    STATUS_NO_OBSERVATIONS,
    STATUS_INCOMPLETE_WINDOW,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_FUTURE,
)

#: Statuses whose records may carry a category colour.
SCORABLE_STATUSES: tuple[str, ...] = (STATUS_FINAL, STATUS_PROVISIONAL)


# ============================================================================
# Time-of-day window definitions
# ============================================================================

@dataclass(frozen=True)
class WindowSpec:
    """A time-of-day bucket expressed as an ordered set of hourly slots.

    ``weekday_class`` is ``"weekday"`` (Mon–Fri), ``"weekend"`` (Sat/Sun) or
    ``None`` (every civil date). ``hours`` is ordered by wall clock within the
    named civil date, which is what the frontend's ``matchesToD`` does — a
    late-hours reading at 02:00 belongs to the same civil date label as the
    22:00 reading before it.
    """

    tod: str
    hours: tuple[int, ...]
    weekday_class: str | None = None
    provisional_min_slots: int | None = None

    @property
    def partition(self) -> str:
        """Whether cohorts are matched on weekday ("same_weekday") or pooled."""
        return "same_weekday"

    @property
    def window_end(self) -> tuple[int, int]:
        """(day offset, hour) at which the window is over, in city-local time."""
        last = self.hours[-1]
        end_hour = (last + 1) % 24
        offset = 1 if end_hour <= self.hours[0] else 0
        return offset, end_hour

    def window_end_at(self, day: str) -> datetime:
        base = datetime.combine(parse_civil_date(day), datetime.min.time())
        offset, hour = self.window_end
        return base + timedelta(days=offset, hours=hour)

    def window_start_at(self, day: str) -> datetime:
        base = datetime.combine(parse_civil_date(day), datetime.min.time())
        return base + timedelta(hours=self.hours[0])

    def slot_start(self, day: str, hour: int) -> datetime:
        """City-local start of a slot inside the named civil date."""
        base = datetime.combine(parse_civil_date(day), datetime.min.time())
        return base + timedelta(hours=hour)

    def allows_weekday(self, weekday: int) -> bool:
        # Monday=0 … Sunday=6, matching date.weekday()
        if self.weekday_class == "weekend":
            return weekday >= 5
        if self.weekday_class == "weekday":
            return weekday < 5
        return True


#: The six frontend time filters, with identical slot sets and boundaries.
WINDOW_SPECS: tuple[WindowSpec, ...] = (
    WindowSpec("weekday_morning", (8, 9, 10, 11), "weekday"),
    WindowSpec("weekday_afternoon", (12, 13, 14, 15, 16, 17), "weekday"),
    # Evening is the only window with a provisional colour in v1.
    WindowSpec("weekday_evening", (18, 19, 20, 21), "weekday", provisional_min_slots=2),
    WindowSpec("weekends", tuple(range(24)), "weekend"),
    WindowSpec("late_hours", (22, 23, 0, 1, 2, 3, 4)),
    WindowSpec("all", tuple(range(24))),
)

WINDOW_BY_TOD: dict[str, WindowSpec] = {s.tod: s for s in WINDOW_SPECS}


# ============================================================================
# Civil-date helpers (never the host timezone)
# ============================================================================

def parse_civil_date(value: str) -> Date:
    """Parse ``YYYY-MM-DD`` as a civil date without any timezone conversion."""
    return Date.fromisoformat(str(value).strip()[:10])


def city_now() -> datetime:
    """Naive city-local wall clock, used as the default evaluation moment."""
    return datetime.now(ZoneInfo(CITY_TIMEZONE)).replace(tzinfo=None)


def parse_as_of(value: str | datetime | None) -> datetime:
    """Parse an ``--as-of`` value as a naive city-local datetime."""
    if value is None:
        return city_now()
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.combine(parse_civil_date(text), datetime.min.time())


# ============================================================================
# Observation preparation
# ============================================================================

OBSERVATION_COLUMNS = (
    "route_code",
    "date",
    "time",
    "hour",
    "duration_min",
    "distance_km",
    "collected_at",
)


def prepare_observations(traffic_df: pd.DataFrame) -> pd.DataFrame:
    """Validate the raw traffic frame into one row per usable reading.

    Applies the same gates as the frontend parser (positive duration <= 300,
    positive distance, 0 < speed <= 150 km/h) and drops exact duplicate
    records — identical date, time, route, duration and distance — keeping the
    first occurrence. Sampling frequency above one reading per hour is kept:
    it is reduced by the hourly median later, never by row count.
    """
    required = {"date", "time", "route_code", "duration", "distance"}
    missing = required - set(traffic_df.columns)
    if missing:
        raise ValueError(f"traffic frame missing required columns: {sorted(missing)}")

    df = traffic_df.copy()

    if "date" not in df.columns:
        raise ValueError("traffic frame must have a date column")

    df["date"] = df["date"].astype(str).str.strip().str.slice(0, 10)
    df["time"] = df["time"].astype(str).str.strip().str.slice(0, 5)
    df["route_code"] = df["route_code"].astype(str).str.strip()

    df["duration_min"] = pd.to_numeric(df["duration"], errors="coerce")
    df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce")

    df = df.dropna(subset=["duration_min", "distance_km"])
    df = df[df["route_code"] != ""]
    df = df[(df["duration_min"] > MIN_DURATION_MIN) & (df["duration_min"] <= MAX_DURATION_MIN)]
    df = df[df["distance_km"] > 0]

    df["speed_kmh"] = 60.0 * df["distance_km"] / df["duration_min"]
    df = df[(df["speed_kmh"] > MIN_SPEED_KMH) & (df["speed_kmh"] <= MAX_SPEED_KMH)]

    # Exact duplicates only — same reading captured twice.
    df = df.drop_duplicates(subset=["date", "time", "route_code", "duration_min", "distance_km"], keep="first")

    # Parse the civil timestamp with an explicit format and no timezone.
    parsed = pd.to_datetime(
        df["date"] + "T" + df["time"],
        format="%Y-%m-%dT%H:%M",
        errors="coerce",
    )
    df = df[parsed.notna()].copy()
    parsed = parsed[parsed.notna()]
    df["collected_at"] = parsed.dt.strftime("%Y-%m-%dT%H:%M")
    df["hour"] = parsed.dt.hour
    df["weekday"] = parsed.dt.dayofweek

    return df[list(OBSERVATION_COLUMNS) + ["weekday"]].reset_index(drop=True)


def build_slot_table(observations: pd.DataFrame) -> pd.DataFrame:
    """One row per route × date × hour: median duration plus quality metadata."""
    if observations.empty:
        return pd.DataFrame(
            columns=[
                "route_code", "date", "weekday", "hour", "minutes",
                "observation_count", "last_observed_at",
                "distance_min", "distance_max",
            ]
        )
    grouped = (
        observations.groupby(["route_code", "date", "weekday", "hour"], as_index=False)
        .agg(
            minutes=("duration_min", "median"),
            observation_count=("duration_min", "size"),
            last_observed_at=("collected_at", "max"),
            distance_min=("distance_km", "min"),
            distance_max=("distance_km", "max"),
        )
        .sort_values(["route_code", "date", "hour"])
        .reset_index(drop=True)
    )
    return grouped


# ============================================================================
# Day summaries
# ============================================================================

@dataclass(frozen=True)
class DayObservation:
    """One route's usable slot values for one civil date and time filter."""

    date: str
    weekday: int
    minutes_by_hour: Mapping[int, float]
    observation_count: int
    last_observed_at: str | None
    distance_min: float | None
    distance_max: float | None

    def covers(self, slots: Sequence[int]) -> bool:
        return all(h in self.minutes_by_hour for h in slots)

    def minutes_for(self, slots: Sequence[int]) -> float:
        values = [self.minutes_by_hour[h] for h in slots]
        return sum(values) / len(values)

    def observed_slots(self, spec: WindowSpec) -> tuple[int, ...]:
        return tuple(h for h in spec.hours if h in self.minutes_by_hour)


def build_day_observations(
    slot_table: pd.DataFrame,
    spec: WindowSpec,
) -> dict[str, DayObservation]:
    """Group a route's slot table into day summaries for one time filter."""
    if slot_table.empty:
        return {}

    sub = slot_table[slot_table["hour"].isin(set(spec.hours))].copy()

    # A window that opens late spans midnight: ``late_hours`` runs 22:00 → 04:00
    # the next morning, so its after-midnight slots belong to the night that
    # began on the previous civil date. Without this rollback the 00:00–04:00
    # slots would be grouped with that same date's 22:00–23:00 readings — i.e.
    # two different nights merged into one day, and no night ever complete.
    start_hour = spec.hours[0]
    if start_hour > 0 and not sub.empty:
        wrapped = sub["hour"] < start_hour
        if bool(wrapped.any()):
            overnight = sub[wrapped].copy()
            opened_on = [parse_civil_date(d) - timedelta(days=1) for d in overnight["date"]]
            overnight["date"] = [d.isoformat() for d in opened_on]
            overnight["weekday"] = [d.weekday() for d in opened_on]
            sub = pd.concat([sub[~wrapped], overnight], ignore_index=True)

    days: dict[str, DayObservation] = {}
    for date_key, group in sub.groupby("date", sort=True):
        weekday = int(group["weekday"].iloc[0])
        if not spec.allows_weekday(weekday):
            continue
        minutes_by_hour = {
            int(row.hour): float(row.minutes) for row in group.itertuples(index=False)
        }
        days[str(date_key)] = DayObservation(
            date=str(date_key),
            weekday=weekday,
            minutes_by_hour=minutes_by_hour,
            observation_count=int(group["observation_count"].sum()),
            last_observed_at=str(group["last_observed_at"].max()),
            distance_min=float(group["distance_min"].min()),
            distance_max=float(group["distance_max"].max()),
        )
    return days


# ============================================================================
# Scoring primitives
# ============================================================================

def smoothed_mid_rank(values: Sequence[float], target: float, epsilon: float = 1e-9) -> tuple[float, int, int]:
    """Return (q, less_count, tie_count) for ``target`` among ``values``.

    ``q = (L + 0.5T + 0.5) / (N + 1)`` — a descriptive rank score with a
    deterministic tie convention. It is not a p-value and not a population
    percentile estimate.
    """
    n = len(values)
    if n == 0:
        return float("nan"), 0, 0
    less = sum(1 for v in values if v < target - epsilon)
    ties = sum(1 for v in values if abs(v - target) <= epsilon)
    q = (less + 0.5 * ties + 0.5) / (n + 1)
    return q, less, ties


def classify(
    delta_minutes: float,
    delta_fraction: float,
    rank_score: float,
    typical_minutes: float,
) -> str:
    """Map effect size + rank to one of the five categories.

    History and practical-difference guards are applied by the caller; this
    function assumes both have already passed.
    """
    practical = max(PRACTICAL_MIN_MINUTES, PRACTICAL_MIN_FRACTION * typical_minutes)
    if abs(delta_minutes) < practical:
        return CATEGORY_USUAL

    if delta_fraction < 0:
        if rank_score <= MUCH_BETTER_MAX_RANK:
            return CATEGORY_MUCH_BETTER
        if rank_score < BETTER_MAX_RANK:
            return CATEGORY_BETTER
        return CATEGORY_USUAL

    if delta_fraction > 0:
        if rank_score >= MUCH_WORSE_MIN_RANK:
            return CATEGORY_MUCH_WORSE
        if rank_score > WORSE_MIN_RANK:
            return CATEGORY_WORSE
        return CATEGORY_USUAL

    return CATEGORY_USUAL


def reference_audit_id(reference_dates: Sequence[str]) -> str:
    """Stable short id for the eligible reference-date set of one record."""
    payload = ",".join(reference_dates).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


# ============================================================================
# Scoring one route × time filter
# ============================================================================

def hourly_slot_mask(hours: Iterable[int]) -> str:
    """Compact 24-bit hour-set encoding (``bit hour`` set), e.g. ``00f000``.

    A mask keeps the export small for the 24-slot ``all``/``weekends`` windows
    while staying human-decodable in a debug view.
    """
    value = 0
    for hour in hours:
        value |= 1 << int(hour)
    return f"{value:06x}"


def decode_hourly_slot_mask(mask: str) -> tuple[int, ...]:
    """Decode :func:`hourly_slot_mask` back into ascending hours."""
    if mask is None or str(mask).strip() == "":
        return ()
    value = int(str(mask).strip(), 16)
    return tuple(hour for hour in range(24) if value & (1 << hour))


EMPTY_ROW_BASE: dict[str, object] = {
    "route_code": "",
    "route_definition_version": "",
    "date": "",
    "tod_bucket": "",
    "city_timezone": CITY_TIMEZONE,
    "method_version": METHOD_VERSION,
    "reference_class": "same_weekday",
    "observed_minutes": None,
    "observed_slot_mask": "",
    "expected_slot_mask": "",
    "observation_count": 0,
    "last_observed_at": None,
    "lookback_days": LOOKBACK_DAYS,
    "reference_start": None,
    "reference_end_exclusive": None,
    "reference_days": None,
    "typical_minutes": None,
    "delta_minutes": None,
    "delta_fraction": None,
    "rank_score": None,
    "less_count": None,
    "tie_count": None,
    "category": None,
    "status": "",
    "quality_flags": "",
    "distance_min_km": None,
    "distance_max_km": None,
    "generated_at": "",
    "source_revision": "",
    "reference_audit_id": "",
}


def _empty_row(
    route_code: str,
    spec: WindowSpec,
    day: str,
    *,
    status: str,
    generated_at: str,
    source_revision: str,
) -> dict[str, object]:
    row = dict(EMPTY_ROW_BASE)
    row.update(
        route_code=route_code,
        date=day,
        tod_bucket=spec.tod,
        expected_slot_mask=hourly_slot_mask(spec.hours),
        status=status,
        generated_at=generated_at,
        source_revision=source_revision,
    )
    return row


def _quality_flags(
    day: DayObservation,
    as_of: datetime,
    *,
    has_observations: bool,
    is_evaluation_day: bool,
) -> str:
    """Interpretation flags. They never remove a day from the scoring set."""
    flags: list[str] = []
    if (
        day.distance_min is not None
        and day.distance_max is not None
        and day.distance_min > 0
        and (day.distance_max - day.distance_min) / day.distance_min > DISTANCE_VARIED_FRACTION
    ):
        flags.append("distance_varied")
    if has_observations and is_evaluation_day and day.last_observed_at:
        last = datetime.strptime(day.last_observed_at, "%Y-%m-%dT%H:%M")
        if (as_of - last) > timedelta(minutes=STALE_AFTER_MINUTES):
            flags.append("stale_feed")
    return ";".join(flags)


def _in_progress_status(
    spec: WindowSpec,
    day: DayObservation,
    as_of: datetime,
) -> tuple[str, tuple[int, ...]]:
    """Status and comparison slots for a day whose window is still open.

    Only a contiguous observed prefix that has already started is usable. An
    absent internal slot means incomplete coverage, not an early cutoff.
    """
    scheduled = tuple(h for h in spec.hours if spec.slot_start(day.date, h) <= as_of)

    if not scheduled:
        return STATUS_NOT_STARTED, ()

    # Only slots that have already started can be part of the comparison; a
    # reading for a slot that has not begun yet is ignored, not a gap.
    observed = tuple(h for h in day.observed_slots(spec) if h in scheduled)

    prefix: list[int] = []
    for hour in scheduled:
        if hour in day.minutes_by_hour:
            prefix.append(hour)
        else:
            break

    if not prefix:
        return STATUS_NO_OBSERVATIONS, ()

    # Any reading outside the contiguous prefix (e.g. a gap at 19:00 with
    # readings at 18:00 and 20:00) is incomplete coverage, not a cutoff.
    if any(h not in prefix for h in observed):
        return STATUS_INCOMPLETE_WINDOW, ()

    minimum = spec.provisional_min_slots
    if minimum is None or len(prefix) < minimum:
        return STATUS_INCOMPLETE_WINDOW, ()

    return STATUS_PROVISIONAL, tuple(prefix)


def score_series(
    route_code: str,
    spec: WindowSpec,
    days: Mapping[str, DayObservation],
    *,
    as_of: datetime,
    generated_at: str,
    source_revision: str,
) -> list[dict[str, object]]:
    """Score every observed date for one route × time filter."""
    rows: list[dict[str, object]] = []
    today = as_of.date()

    dates_sorted = sorted(days)
    by_weekday: dict[int, list[str]] = defaultdict(list)
    for d in dates_sorted:
        by_weekday[days[d].weekday].append(d)

    for day_key in dates_sorted:
        day = days[day_key]
        row = dict(EMPTY_ROW_BASE)
        row.update(
            route_code=route_code,
            date=day_key,
            tod_bucket=spec.tod,
            expected_slot_mask=hourly_slot_mask(spec.hours),
            observation_count=day.observation_count,
            last_observed_at=day.last_observed_at,
            distance_min_km=None if day.distance_min is None else round(day.distance_min, 2),
            distance_max_km=None if day.distance_max is None else round(day.distance_max, 2),
            generated_at=generated_at,
            source_revision=source_revision,
        )

        is_evaluation_day = parse_civil_date(day_key) == today
        day_date = parse_civil_date(day_key)
        if day_date > today:
            row["status"] = STATUS_FUTURE
            row["observed_slot_mask"] = hourly_slot_mask(day.observed_slots(spec))
            row["observed_minutes"] = (
                round(day.minutes_for(day.observed_slots(spec)), 2)
                if day.observed_slots(spec)
                else None
            )
            row["quality_flags"] = _quality_flags(
                day, as_of, has_observations=True, is_evaluation_day=False
            )
            rows.append(row)
            continue

        if day_date == today and as_of < spec.window_end_at(day_key):
            status, compare_slots = _in_progress_status(spec, day, as_of)
        elif day.covers(spec.hours):
            status, compare_slots = STATUS_FINAL, tuple(spec.hours)
        else:
            status, compare_slots = STATUS_INCOMPLETE_WINDOW, ()

        row["status"] = status
        row["quality_flags"] = _quality_flags(
            day, as_of, has_observations=True, is_evaluation_day=is_evaluation_day
        )

        if status == STATUS_NOT_STARTED:
            # No slot in the window has begun yet; nothing has been observed
            # for this comparison even if later readings exist in the feed.
            rows.append(row)
            continue

        row["observed_slot_mask"] = hourly_slot_mask(day.observed_slots(spec))
        # Report the value actually compared (a provisional day uses its
        # observed prefix, not hours that have not started yet).
        compared = compare_slots or day.observed_slots(spec)
        row["observed_minutes"] = round(day.minutes_for(compared), 2) if compared else None

        if status in (STATUS_NOT_STARTED, STATUS_NO_OBSERVATIONS):
            rows.append(row)
            continue

        if status == STATUS_INCOMPLETE_WINDOW:
            # Coverage problem must not be disguised as a normal day, but the
            # typical value is still useful context for the UI.
            reference = _reference_dates(
                day, spec, days, by_weekday, required=tuple(spec.hours)
            )
            typical = _typical_minutes(days, reference, spec.hours)
            row["reference_days"] = len(reference)
            enough_history = len(reference) >= MIN_HISTORY_DAYS
            row["typical_minutes"] = (
                None if typical is None or not enough_history else round(typical, 2)
            )
            if reference:
                row["reference_start"] = reference[0]
                row["reference_end_exclusive"] = _day_after(reference[-1])
                row["reference_audit_id"] = reference_audit_id(reference)
            rows.append(row)
            continue

        observed_summary = day.minutes_for(compare_slots)
        reference = _reference_dates(day, spec, days, by_weekday, required=compare_slots)

        row["reference_days"] = len(reference)
        if reference:
            row["reference_start"] = reference[0]
            row["reference_end_exclusive"] = _day_after(reference[-1])
            row["reference_audit_id"] = reference_audit_id(reference)

        # Too little comparable history: report the count, never a score.
        if len(reference) < MIN_HISTORY_DAYS:
            row["status"] = STATUS_INSUFFICIENT_HISTORY
            rows.append(row)
            continue

        typical = _typical_minutes(days, reference, compare_slots)
        if typical is None:
            row["status"] = STATUS_INSUFFICIENT_HISTORY
            rows.append(row)
            continue

        row["typical_minutes"] = round(typical, 2)
        reference_values = [days[d].minutes_for(compare_slots) for d in reference]
        q, less, ties = smoothed_mid_rank(reference_values, observed_summary)
        delta = observed_summary - typical
        fraction = observed_summary / typical - 1.0 if typical > 0 else 0.0

        row["delta_minutes"] = round(delta, 2)
        row["delta_fraction"] = round(fraction, 6)
        row["rank_score"] = round(q, 4)
        row["less_count"] = less
        row["tie_count"] = ties

        if len(reference) < MIN_HISTORY_DAYS:
            row["status"] = STATUS_INSUFFICIENT_HISTORY
            rows.append(row)
            continue

        row["category"] = classify(delta, fraction, q, typical)
        rows.append(row)

    # A row for the evaluation day, so the UI can distinguish "not started"
    # from "no observations" without inventing state client-side.
    today_key = today.isoformat()
    if today_key not in days and spec.allows_weekday(today.weekday()):
        if as_of < spec.window_start_at(today_key):
            status = STATUS_NOT_STARTED
        elif as_of < spec.window_end_at(today_key):
            status = STATUS_NO_OBSERVATIONS
        else:
            status = STATUS_NO_OBSERVATIONS
        rows.append(
            _empty_row(
                route_code,
                spec,
                today_key,
                status=status,
                generated_at=generated_at,
                source_revision=source_revision,
            )
        )

    rows.sort(key=lambda r: str(r["date"]))
    return rows


def _day_after(day: str) -> str:
    return (parse_civil_date(day) + timedelta(days=1)).isoformat()


def _reference_dates(
    day: DayObservation,
    spec: WindowSpec,
    days: Mapping[str, DayObservation],
    by_weekday: Mapping[int, list[str]],
    *,
    required: Sequence[int],
) -> list[str]:
    """Eligible earlier dates: same weekday, complete required slots, in window."""
    target = parse_civil_date(day.date)
    start = (target - timedelta(days=LOOKBACK_DAYS)).isoformat()
    candidates = by_weekday.get(day.weekday, [])
    lo = bisect_left(candidates, start)
    hi = bisect_left(candidates, day.date)  # exclusive: strictly earlier dates
    return [d for d in candidates[lo:hi] if days[d].covers(required)]


def _typical_minutes(
    days: Mapping[str, DayObservation],
    reference: Sequence[str],
    slots: Sequence[int],
) -> float | None:
    if not reference:
        return None
    values = [days[d].minutes_for(slots) for d in reference]
    typical = median(values)
    return typical if typical > 0 else None


# ============================================================================
# Public entry point
# ============================================================================

EXPORT_COLUMNS: tuple[str, ...] = (
    "route_code",
    "route_definition_version",
    "date",
    "tod_bucket",
    "city_timezone",
    "method_version",
    "reference_class",
    "observed_minutes",
    "observed_slot_mask",
    "expected_slot_mask",
    "observation_count",
    "last_observed_at",
    "lookback_days",
    "reference_start",
    "reference_end_exclusive",
    "reference_days",
    "typical_minutes",
    "delta_minutes",
    "delta_fraction",
    "rank_score",
    "less_count",
    "tie_count",
    "category",
    "status",
    "quality_flags",
    "distance_min_km",
    "distance_max_km",
    "generated_at",
    "source_revision",
    "reference_audit_id",
)

_INT_COLUMNS = (
    "observation_count",
    "lookback_days",
    "reference_days",
    "less_count",
    "tie_count",
)


def visible_observations(observations: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """Drop readings collected after the evaluation moment.

    Enforces the walk-forward rule: no observation from the target date or
    later may enter a comparison, and a backtest cannot see the future.
    """
    if observations.empty:
        return observations
    cutoff = as_of.strftime("%Y-%m-%dT%H:%M")
    return observations[observations["collected_at"] <= cutoff]


def generate_anomaly_records(
    observations: pd.DataFrame,
    *,
    as_of: datetime | str | None = None,
    specs: Iterable[WindowSpec] = WINDOW_SPECS,
    route_codes: Sequence[str] | None = None,
    generated_at: datetime | None = None,
    source_revision: str = "",
) -> pd.DataFrame:
    """Score every observed route × date × time filter into export rows.

    Parameters
    ----------
    observations
        Output of :func:`prepare_observations`.
    as_of
        City-local evaluation moment. Only observations strictly before the
        target date, and only completed windows, can produce final scores.
    specs
        Time-of-day windows to score (defaults to all six frontend filters).
    route_codes
        Restrict to these route codes (defaults to every route in the frame).
    source_revision
        Provenance string for the export (e.g. a CSV digest).

    Notes
    -----
    Scoring always sees the full history up to ``as_of``. Only the *returned*
    target dates are narrowed to the trailing :data:`LOOKBACK_DAYS` window, so
    the published file stays bounded while every score keeps its complete
    preceding cohort — including dates at the boundary, whose reference window
    opens before the published range.
    """
    as_of_dt = parse_as_of(as_of)
    stamped = (generated_at or city_now()).strftime("%Y-%m-%dT%H:%M:%S")

    observations = visible_observations(observations, as_of_dt)
    if observations.empty:
        return pd.DataFrame(columns=list(EXPORT_COLUMNS))

    slot_table = build_slot_table(observations)
    codes = list(route_codes) if route_codes is not None else sorted(observations["route_code"].unique())

    rows: list[dict[str, object]] = []
    for route_code in codes:
        route_slots = slot_table[slot_table["route_code"] == route_code]
        if route_slots.empty:
            continue
        for spec in specs:
            days = build_day_observations(route_slots, spec)
            if not days:
                continue
            rows.extend(
                score_series(
                    route_code,
                    spec,
                    days,
                    as_of=as_of_dt,
                    generated_at=stamped,
                    source_revision=source_revision,
                )
            )

    df = pd.DataFrame(rows)
    for column in EXPORT_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df = df[list(EXPORT_COLUMNS)]

    # Publish a rolling window, not the whole history. Only target dates inside
    # [as_of - LOOKBACK_DAYS, as_of] are exported, so the committed CSV stays
    # bounded. This is a publication filter applied after scoring: a date at the
    # boundary was still scored against its full preceding cohort above, which
    # reaches further back than the window being published.
    if not df.empty:
        window_start = (as_of_dt.date() - timedelta(days=LOOKBACK_DAYS)).isoformat()
        window_end = as_of_dt.date().isoformat()
        df = df[(df["date"] >= window_start) & (df["date"] <= window_end)]
        df = df.reset_index(drop=True)

    for column in _INT_COLUMNS:
        df[column] = pd.array(
            [None if pd.isna(v) else int(v) for v in df[column]], dtype="Int64"
        )

    df = df.sort_values(["route_code", "tod_bucket", "date"]).reset_index(drop=True)
    return df


def build_audit_payload(
    observations: pd.DataFrame,
    *,
    route_code: str,
    target_date: str,
    tod: str,
    as_of: datetime | str | None = None,
) -> dict[str, object]:
    """Reconstruct why one date received its category.

    Returns the eligible reference dates, their day summaries, the slot medians
    for the target date, and the resulting score inputs. Intended for
    ``generate_calendar_exports.py --audit``.
    """
    spec = WINDOW_BY_TOD.get(tod)
    if spec is None:
        raise ValueError(f"unknown tod_bucket {tod!r}; expected one of {sorted(WINDOW_BY_TOD)}")

    as_of_dt = parse_as_of(as_of)
    visible = visible_observations(observations, as_of_dt)
    slot_table = build_slot_table(visible)
    route_slots = slot_table[slot_table["route_code"] == route_code]
    days = build_day_observations(route_slots, spec)
    if target_date not in days:
        raise ValueError(f"no usable {tod} observations for {route_code} on {target_date}")

    rows = score_series(
        route_code,
        spec,
        days,
        as_of=as_of_dt,
        generated_at=as_of_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        source_revision="",
    )
    record = next(r for r in rows if r["date"] == target_date)

    day = days[target_date]
    # Mirror the scorer's slot selection, which depends on *when* the day is
    # being evaluated — not on the status that comes out the other end. An
    # in-progress day with a valid prefix scores against that prefix even when
    # the outcome is insufficient_history (fewer than MIN_HISTORY_DAYS matching
    # references), so the audit must use the same slots or its reference_dates
    # and reference_summaries would describe a different comparison.
    compare_slots = tuple(spec.hours)
    in_progress = (
        parse_civil_date(target_date) == as_of_dt.date()
        and as_of_dt < spec.window_end_at(target_date)
    )
    if in_progress:
        _, prefix = _in_progress_status(spec, day, as_of_dt)
        if prefix:
            compare_slots = prefix

    by_weekday: dict[int, list[str]] = defaultdict(list)
    for d in sorted(days):
        by_weekday[days[d].weekday].append(d)
    reference = _reference_dates(day, spec, days, by_weekday, required=compare_slots)

    return {
        "method_version": METHOD_VERSION,
        "route_code": route_code,
        "date": target_date,
        "tod_bucket": tod,
        "city_timezone": CITY_TIMEZONE,
        "as_of": as_of_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "expected_slots": list(spec.hours),
        "observed_slot_mask": record["observed_slot_mask"],
        "expected_slot_mask": record["expected_slot_mask"],
        "compared_slots": list(compare_slots),
        "target_slot_minutes": {
            str(h): round(day.minutes_by_hour[h], 2)
            for h in day.observed_slots(spec)
        },
        "reference_dates": reference,
        "reference_summaries": [
            {
                "date": d,
                "minutes": round(days[d].minutes_for(compare_slots), 3),
            }
            for d in reference
        ],
        "record": json.loads(
            pd.DataFrame([record]).to_json(orient="records", date_format="iso")
        )[0],
    }
