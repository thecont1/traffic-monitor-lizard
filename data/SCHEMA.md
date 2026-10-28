# Dataset Schema

This document describes the complete schema for all data files in the `traffic-monitor-lizard` repository. It covers both the **raw CSV files** stored in version control and the **derived columns** computed by the analysis toolkit (`data_utils.py`, `traffic_analyzer.py`).

---

## Overview

| File | Purpose | Storage |
|------|---------|---------|
| `csv-traffic-bangalore.csv` | Timestamped traffic readings (all historical) | Versioned |
| `csv-routes-bangalore.csv` | Route definitions and metadata | Versioned |
| `csv-locations_*.csv` | Location names mapped to Plus Codes | Versioned |
| `csv-weather-snapshot.csv` | Latest weather reading per route | Versioned |
| `csv-calendar-anomalies-bangalore.csv` | Rolling 90-day day-anomaly scores per route × date × time of day | Versioned, regenerated on every snapshot |

The traffic file uses a **long format**: one row per route per reading. Each reading captures the estimated travel time from Google Maps at a specific moment.

---

## Raw Files

### `csv-traffic-bangalore.csv`

The primary dataset. Each row is one traffic snapshot for one route.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `date` | `date` (ISO 8601) | No | Calendar date of collection, e.g. `2025-09-25` |
| `time` | `time` (24-hour, `HH:MM`) | No | Collection time in local timezone, e.g. `14:25` |
| `route_code` | `string` | No | Origin and destination Plus Codes joined by `\|`, e.g. `XJG4+7J\|5PX4+HQ` |
| `duration` | `integer` (minutes) | No | Estimated travel time in minutes |
| `distance` | `float` (km) | No | Route distance in kilometres |
| `temp` | `integer` (°C) | Yes | Temperature at nearest weather station |
| `realfeel` | `integer` (°C) | Yes | "Real feel" temperature |
| `humidity` | `integer` (%) | Yes | Relative humidity percentage |
| `rsi_flag` | `string` | Yes | Rain / precipitation status, e.g. `Heavy Rain` or empty |
| `aqi` | `integer` | Yes | Air quality index value |

**Constraints**
- `duration` > 0
- `distance` > 0
- Rows with missing `duration` or `distance` are discarded by the scraper before writing

**Notes**
- Weather columns may be empty for early readings collected before weather integration was added
- `rsi_flag` is normalised to empty string when the raw value is `"No Precipitation"`
- The file is appended to by the GitHub Actions workflow on every successful scrape

---

### `csv-routes-bangalore.csv`

Metadata for each monitored route. One row per route.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `route_code` | `string` | No | Same identifier used in the traffic file; format: `{origin_plus_code}\|{destination_plus_code}` |
| `label_full` | `string` | No | Human-readable long name, e.g. `MG Road Metro Station → Kempegowda International Airport, Bengaluru` |
| `label_short` | `string` | No | Short display label, e.g. `Airport Expy` |
| `map_link` | `URL` | No | Direct Google Maps directions link |
| `accuweather_station` | `string` | No | AccuWeather station slug used for weather lookups, e.g. `shantala-nagar/3352203` |

**Primary Key**: `route_code`

---

### `csv-locations_{lat}_{lon}.csv`

Maps Plus Codes to human-readable place names. The reference latitude and longitude in the filename are used by the scraper to decode short Plus Codes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `plus_code` | `string` | No | Open Location Code (Plus Code), e.g. `XJG4+7J` |
| `location` | `string` | No | Human-readable place name used in Google Maps queries |

**Primary Key**: `plus_code`

**Relationship to other files**
- `plus_code` appears as the origin or destination part of `route_code` in the routes and traffic files
- The scraper uses this file to translate Plus Codes into queryable place names for Google Maps

---

### `csv-weather-snapshot.csv`

Latest weather reading for each route, updated by the weather snapshot script before each traffic scrape.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `route_code` | `string` | No | Same route identifier |
| `route_name_short` | `string` | No | Short route label (duplicated for convenience) |
| `accuweather_station` | `string` | No | Weather station slug |
| `temp` | `integer` (°C) | No | Current temperature |
| `temp_flag` | `string` | No | Temperature qualifier, e.g. `Cloudy` |
| `realfeel` | `integer` (°C) | No | "Real feel" temperature |
| `realfeel_flag` | `string` | No | Real-feel qualifier, e.g. `Pleasant` |
| `humidity` | `integer` (%) | No | Relative humidity |
| `rsi_flag` | `string` | No | Rain status, e.g. `No Precipitation` |
| `rsi_forecast` | `string` | No | Short precipitation forecast text |
| `aqi` | `integer` | No | Air quality index |
| `aqi_flag` | `string` | No | AQI qualifier, e.g. `Fair` |

**Notes**
- This is overwritten in place on every weather snapshot run
- The traffic scraper reads this file and joins weather fields into each CSV row it outputs
- `rsi_flag` values of `"No Precipitation"` are normalised to empty string in the traffic output

---

---

### `csv-calendar-anomalies-bangalore.csv`

Derived export for the "Good Days and Bad Days" calendar. One row per
route × civil date × time-of-day filter, answering *"was this journey unusually
slow or fast for this weekday and time on this route?"* — never *"was this road
faster than another road today?"*.

Generated by `tools/generate_calendar_exports.py`, which calls the pure scorer
in `tools/calendar_anomalies.py`. The frontend (`src/lib/calendarAnomalies.ts`)
only parses and renders this file; no scoring happens in the browser.

**Scope and retention.** The file is a rolling publication window: it contains
only target dates in `[as_of − 90 days, as_of]`, where `as_of` is the run's
evaluation moment (default: now, city-local). Older dates are not republished —
they remain in `csv-traffic-bangalore.csv` and can be rescored at any time with
`--as-of`. Windowing is a *publication* filter applied after scoring: a date at
the boundary is still scored against its full preceding 90-day cohort, which
reaches back before the published range, so its `reference_days`,
`typical_minutes` and category are identical to a full-history run. Expect
roughly 7000 rows rather than the whole history; the file stays stable in size
as the archive grows.

**Identity and time**

| Column | Type | Description |
|--------|------|-------------|
| `route_code` | `string` | Journey identity, including direction. Never a display label |
| `route_definition_version` | `string` | Blank while no route-geometry version exists upstream |
| `date` | `date` (ISO 8601) | City-local civil date, not a viewer-local date |
| `tod_bucket` | `string` | `weekday_morning`, `weekday_afternoon`, `weekday_evening`, `weekends`, `late_hours`, `all` |
| `city_timezone` | `string` | `Asia/Kolkata`; the zone all civil dates and weekdays are anchored to |
| `method_version` | `string` | `calendar-anomaly-v1`; a viewer must refuse unknown versions |
| `reference_class` | `string` | `same_weekday` — the cohort is weekday-matched |

**Observation**

| Column | Type | Description |
|--------|------|-------------|
| `observed_minutes` | `float` (min) | Equal-weight mean of the hourly slot medians that were compared |
| `observed_slot_mask` | `string` (hex) | 24-bit hour set, bit `h` = hour `h`. `3c0000` = 18–21 |
| `expected_slot_mask` | `string` (hex) | Slots required for a complete window |
| `observation_count` | `integer` | Raw readings used by those slots |
| `last_observed_at` | `datetime` (city-local, no offset) | Newest collection time in the day |

**Reference and result**

| Column | Type | Description |
|--------|------|-------------|
| `lookback_days` | `integer` | 90 — dates in `[date − 90, date)` |
| `reference_start`, `reference_end_exclusive` | `date` | Eligible window bounds (`reference_end_exclusive` ≤ `date`) |
| `reference_days` | `integer` | Eligible earlier dates with complete matching slots |
| `typical_minutes` | `float` (min) | Median of the reference day summaries |
| `delta_minutes` | `float` (min) | `observed − typical`; positive is slower |
| `delta_fraction` | `float` | `observed / typical − 1` |
| `rank_score` | `float` | Smoothed mid-rank `(L + 0.5T + 0.5) / (N + 1)`; descriptive, **not** a p-value or certified percentile |
| `less_count`, `tie_count` | `integer` | `L` and `T` used by the rank |
| `category` | `string` | `much_better`, `better`, `usual`, `worse`, `much_worse`; blank unless scorable |
| `status` | `string` | See below |
| `quality_flags` | `string` | Semicolon list: `distance_varied`, `stale_feed` — flags for interpretation, never exclusions |

**Provenance**

| Column | Type | Description |
|--------|------|-------------|
| `distance_min_km`, `distance_max_km` | `float` (km) | Route-card distance spread within the day |
| `generated_at` | `datetime` | Export run time, city-local |
| `source_revision` | `string` | `sha256:<12 hex>` digest of the input traffic CSV |
| `reference_audit_id` | `string` | Short digest of the eligible reference-date list |

**Statuses**

| Status | Meaning |
|--------|---------|
| `final` | Window complete in city-local time, every expected slot observed |
| `provisional` | Window still open; a contiguous observed prefix was compared against the same prefix historically |
| `not_started` | The evaluation day exists but no slot in its window has begun |
| `no_observations` | The window has opened/closed with no readings |
| `incomplete_window` | A slot is missing (or coverage is non-contiguous); never shown as normal |
| `insufficient_history` | Fewer than 8 eligible reference dates; no category is emitted |
| `future` | Target date is after the evaluation moment |

**Absent dates are meaningful.** A date with no row at all has no observations
for that filter (for example a Saturday under `weekday_evening`), which the
frontend renders as "not applicable"/"no data" rather than as a score.

**Method summary**

1. Readings are validated (`duration` in (0, 300] min, `distance` > 0,
   0 < speed ≤ 150 km/h) and exact duplicate records are dropped.
2. Each hour contributes its median duration, so a burst of samples in one hour
   cannot outvote a sparse hour.
3. A day summary `A` is the equal-weight mean of the hourly medians over the
   required slots. Every required slot must be present, or a day in progress
   must cover a contiguous started prefix.
4. `B` is the median of `A` over eligible earlier dates: same route, same
   weekday, same slot set, within the preceding 90 days. The target date and
   every later observation are excluded, so appending new data can never restate
   a finalised historical row.
5. `category` requires both a practical difference — `|delta| ≥ max(2 min,
   10% of B)` — and a rank band: `≤0.10`/`<0.25` for better bands,
   `>0.75`/`≥0.90` for worse bands. Exact `q = 0.25` and `q = 0.75` stay
   `usual`.

Thresholds are product defaults for backtesting, versioned by `method_version`,
not statistical guarantees.

**Known limitations**

- The dataset records Google Maps *journey estimates* at collection time, not
  completed trips. An evening has four hourly estimates, not continuous
  observation.
- Identity is an origin–destination Plus Code pair, not a fixed road alignment;
  the same route code can return different distances (flagged, not removed).
- The baseline is a calendar-weekday baseline. It is not holiday-adjusted and
  does not match on weather, so a genuine shock is surfaced rather than
  explained away.
- A rolling baseline adapts: "usual relative to the previous 90 days" is not a
  claim that the road is healthy in absolute terms.

**Auditing one date**

```bash
uv run python tools/generate_calendar_exports.py \
  --audit 'XMW9+G8|WMJR+V4:2026-10-16:weekday_evening'
```

Prints the compared slots, their medians, every eligible reference date with
its day summary, and the resulting record — enough to reconstruct why a date
received its category. `reference_audit_id` identifies that reference-date set
so an unchanged audit id implies an unchanged baseline.

## Derived Columns

When you load the traffic data via `data_utils.py` or `traffic_analyzer.py`, the following columns are computed automatically.

### From `preprocess_traffic_data()`

| Column | Type | Formula / Source |
|--------|------|-----------------|
| `avg_speed` | `float` (km/h) | `distance / (duration / 60)` |

### From `compute_temporal_features()`

| Column | Type | Formula / Source |
|--------|------|-----------------|
| `year` | `integer` | Parsed from `date` |
| `month` | `integer` | Parsed from `date` |
| `day` | `integer` | Parsed from `date` |
| `hour` | `integer` (0-23) | Parsed from `time` (`HH:MM`) |
| `timestamp` | `datetime64[ns]` | `pd.to_datetime(df[['year','month','day','hour']])` |
| `day_of_week` | `string` | `timestamp.dt.day_name()`, e.g. `Monday` |
| `is_weekend` | `boolean` | `timestamp.dt.dayofweek >= 5` |
| `time_category` | `Categorical` | Binned from `hour`: |
| | | `late_night` : 00:00 – 06:00 |
| | | `morning` : 06:00 – 08:00 |
| | | `morning_rush` : 08:00 – 11:00 |
| | | `early_afternoon` : 11:00 – 14:00 |
| | | `late_afternoon` : 14:00 – 18:00 |
| | | `evening_rush` : 18:00 – 21:00 |
| | | `night` : 21:00 – 24:00 |

---

## Data Relationships

```
csv-locations_{lat}_{lon}.csv
    plus_code ───┐
                 │
    csv-routes-bangalore.csv
        route_code = origin_plus_code | destination_plus_code
                 │
    csv-traffic-bangalore.csv
        route_code ───┘
        (weather fields copied from csv-weather-snapshot.csv at scrape time)
```

- **Locations ↔ Routes**: A route's `route_code` is built from two `plus_code` values in the locations file
- **Routes ↔ Traffic**: `route_code` is the foreign key linking traffic readings to route metadata
- **Routes ↔ Weather**: `accuweather_station` is shared between routes and the weather snapshot
- **Weather → Traffic**: Weather values are denormalised into the traffic CSV at scrape time; the snapshot file is transient

---

## Quality Rules

Rules enforced by the scraper (`traffic_snapshot.py`) before writing:

1. Durations must be parseable (handles `"25 min"`, `"1 hr 5 min"`, `"2 hr"`, `"7 min"`)
2. Distances must contain `" km"`; the suffix is stripped and converted to float
3. Any row missing both a valid `duration` and a valid `distance` is dropped

Rules enforced by `preprocess_traffic_data()` when loading:

1. Deduplicate on `(route_code, date, hour, duration, distance)` — keeps first occurrence
2. Drop rows with missing `route_code`, `duration`, `distance`, or `avg_speed`
3. Sort by `(year, month, day, hour)`

---

## File Naming Convention

| Pattern | Meaning |
|---------|---------|
| `csv-traffic-{city}.csv` | Traffic readings for a specific city |
| `csv-routes-{city}.csv` | Route definitions for a specific city |
| `csv-locations_{lat}_{lon}.csv` | Location lookup for a city; lat/lon are the reference coordinates used for Plus Code decoding |
| `csv-weather-snapshot.csv` | Single latest weather reading per route (overwritten on every run) |

The current instance covers **Bangalore, India**.
