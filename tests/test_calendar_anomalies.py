"""Tests for the calendar day-anomaly scorer (tools/calendar_anomalies.py).

Covers the acceptance contract in the "Good Days and Bad Days" plan:
like-for-like Friday comparison, strict target-date exclusion, equal-hour
weighting, duplicate immunity, coverage states, provisional prefixes, sparse
history, deterministic ties, route isolation, civil-date timezone independence,
and the export shape the frontend validates.
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from calendar_anomalies import (
    CATEGORY_BETTER,
    CATEGORY_MUCH_BETTER,
    CATEGORY_MUCH_WORSE,
    CATEGORY_USUAL,
    CATEGORY_WORSE,
    CITY_TIMEZONE,
    EXPORT_COLUMNS,
    METHOD_VERSION,
    MIN_HISTORY_DAYS,
    STATUS_FINAL,
    STATUS_INCOMPLETE_WINDOW,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_NOT_STARTED,
    STATUS_PROVISIONAL,
    WINDOW_BY_TOD,
    build_audit_payload,
    build_day_observations,
    build_slot_table,
    classify,
    decode_hourly_slot_mask,
    generate_anomaly_records,
    hourly_slot_mask,
    parse_as_of,
    prepare_observations,
    smoothed_mid_rank,
)

EVENING = WINDOW_BY_TOD["weekday_evening"]
SLOTS = EVENING.hours  # (18, 19, 20, 21)

FRIDAY = "2026-10-23"


# ── Helpers ──────────────────────────────────────────────────────────────


def frame(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["date", "time", "route_code", "duration", "distance"])


def day_rows(
    day: str,
    minutes: dict[int, float],
    *,
    route: str = "R1",
    distance: float = 10.0,
    minute: int = 10,
) -> list[tuple]:
    """One reading per hour in ``minutes`` (hour → duration)."""
    return [
        (day, f"{hour:02d}:{minute:02d}", route, duration, distance)
        for hour, duration in minutes.items()
    ]


def prior_fridays(count: int, end: str = FRIDAY) -> list[str]:
    """The ``count`` Fridays strictly before ``end``, oldest first."""
    end_date = date.fromisoformat(end)
    out: list[str] = []
    cursor = end_date
    while len(out) < count:
        cursor -= timedelta(days=1)
        if cursor.weekday() == 4:
            out.append(cursor.isoformat())
    return sorted(out)


def flat_friday_history(count: int, duration: float, route: str = "R1") -> list[tuple]:
    rows: list[tuple] = []
    for day in prior_fridays(count):
        rows += day_rows(day, {h: duration for h in SLOTS}, route=route)
    return rows


def night_before(day: str) -> str:
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat() + "T00:30"


def score_one(
    rows: list[tuple],
    *,
    day: str = FRIDAY,
    as_of: str | None = None,
    route: str = "R1",
    tod: str = "weekday_evening",
) -> pd.Series:
    obs = prepare_observations(frame(rows))
    result = generate_anomaly_records(
        obs,
        as_of=as_of or night_before(day),
        specs=[WINDOW_BY_TOD[tod]],
        route_codes=[route],
    )
    match = result[(result["date"] == day)]
    assert len(match) == 1, f"expected exactly one record for {day}, got {len(match)}"
    return match.iloc[0]


# ── Observation preparation ──────────────────────────────────────────────


def test_prepare_drops_invalid_measurements_and_exact_duplicates():
    rows = [
        ("2026-10-23", "18:10", "R1", 30, 10.0),   # valid
        ("2026-10-23", "18:10", "R1", 32, 10.0),   # valid, different reading
        ("2026-10-23", "18:10", "R1", 30, 10.0),   # exact duplicate
        ("2026-10-23", "19:10", "R1", 0, 10.0),    # zero duration
        ("2026-10-23", "19:10", "R1", 400, 10.0),  # absurd duration
        ("2026-10-23", "20:10", "R1", 30, 0.0),    # zero distance
        ("2026-10-23", "21:10", "", 30, 10.0),     # no route
    ]
    obs = prepare_observations(frame(rows))
    assert len(obs) == 2
    assert set(obs["hour"]) == {18}


def test_speed_gate_matches_frontend_parser():
    # 10 km in 3 minutes → 200 km/h, rejected by both parsers.
    rows = [("2026-10-23", "18:10", "R1", 3, 10.0)]
    assert prepare_observations(frame(rows)).empty


def test_hourly_medians_equalise_hour_weighting():
    """An hour with three readings must not outvote an hour with one."""
    rows = day_rows("2026-10-23", {18: 30, 19: 40})
    rows += [(FRIDAY, "18:30", "R1", 90, 10.0), (FRIDAY, "18:45", "R1", 90, 10.0)]
    obs = prepare_observations(frame(rows))
    days = build_day_observations(build_slot_table(obs), EVENING)
    day = days[FRIDAY]
    assert day.minutes_by_hour[18] == pytest.approx(90.0)  # median of 30, 90, 90
    assert day.minutes_for((18, 19)) == pytest.approx((90 + 40) / 2)
    # A row-count average would have produced (30+90+90+40)/4 = 62.5
    assert day.minutes_for((18, 19)) != pytest.approx(62.5)


# ── Comparing like with like ─────────────────────────────────────────────


def test_compares_same_weekday_not_all_weekdays():
    """A normal Friday against Fridays: weekly Mon–Thu pattern must not leak in."""
    rows = flat_friday_history(12, 30.0)
    # Eleven extra weekdays at a much faster 20 minutes, plus one Monday.
    for day in ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]:
        rows += day_rows(day, {h: 20.0 for h in SLOTS})
    rows += day_rows(FRIDAY, {h: 31.0 for h in SLOTS})

    row = score_one(rows)
    assert row["status"] == STATUS_FINAL
    assert row["reference_days"] == 12
    assert row["typical_minutes"] == pytest.approx(30.0)
    assert row["category"] == CATEGORY_USUAL  # +1 min is below the 2-minute guard


def test_target_date_never_enters_its_own_reference():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 90.0 for h in SLOTS})

    row = score_one(rows)
    assert row["reference_end_exclusive"] <= FRIDAY
    assert row["reference_days"] == 12
    assert row["typical_minutes"] == pytest.approx(30.0)

    audit = build_audit_payload(
        prepare_observations(frame(rows)),
        route_code="R1",
        target_date=FRIDAY,
        tod="weekday_evening",
        as_of=night_before(FRIDAY),
    )
    assert FRIDAY not in audit["reference_dates"]
    assert all(d < FRIDAY for d in audit["reference_dates"])


def test_appending_future_observations_does_not_restate_a_final_score():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    before = score_one(rows)

    later = rows + day_rows("2026-10-30", {h: 80.0 for h in SLOTS})
    obs = prepare_observations(frame(later))
    after_all = generate_anomaly_records(
        obs,
        as_of="2026-11-02T23:00",
        specs=[EVENING],
        route_codes=["R1"],
    )
    after = after_all[after_all["date"] == FRIDAY].iloc[0]

    for field in (
        "observed_minutes",
        "typical_minutes",
        "delta_minutes",
        "delta_fraction",
        "rank_score",
        "reference_days",
        "category",
        "reference_audit_id",
    ):
        assert after[field] == before[field], field


def test_another_routes_collapse_does_not_change_this_route():
    rows = flat_friday_history(12, 30.0, route="R1")
    rows += flat_friday_history(12, 30.0, route="AIRPORT")
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS}, route="R1")
    rows += day_rows(FRIDAY, {h: 30.0 for h in SLOTS}, route="AIRPORT")
    base = score_one(rows, route="R1")

    # Airport Expy alone deteriorates badly on the same day.
    worse = [
        r for r in rows if not (r[0] == FRIDAY and r[2] == "AIRPORT")
    ] + day_rows(FRIDAY, {h: 140.0 for h in SLOTS}, route="AIRPORT")
    # Airport degradation history too — a citywide shock.
    worse += [
        (d, f"{h:02d}:10", "AIRPORT", 140.0, 10.0)
        for d in prior_fridays(12)
        for h in SLOTS
    ]
    after = score_one(worse, route="R1")

    assert after["observed_minutes"] == base["observed_minutes"]
    assert after["typical_minutes"] == base["typical_minutes"]
    assert after["category"] == base["category"]


def test_citywide_exceptional_delay_is_not_normalised_away():
    rows = flat_friday_history(12, 30.0, route="R1")
    rows += flat_friday_history(12, 30.0, route="R2")
    for route in ("R1", "R2"):
        rows += day_rows(FRIDAY, {h: 60.0 for h in SLOTS}, route=route)

    obs = prepare_observations(frame(rows))
    result = generate_anomaly_records(
        obs, as_of=night_before(FRIDAY), specs=[EVENING], route_codes=["R1", "R2"]
    )
    today = result[result["date"] == FRIDAY]
    assert set(today["category"]) == {CATEGORY_MUCH_WORSE}


# ── Coverage states ──────────────────────────────────────────────────────


def test_missing_peak_hour_is_incomplete_not_normal():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {18: 30.0, 19: 30.0, 21: 30.0})  # 20:00 missing

    row = score_one(rows)
    assert row["status"] == STATUS_INCOMPLETE_WINDOW
    assert pd.isna(row["category"])
    assert row["observed_slot_mask"] == hourly_slot_mask((18, 19, 21))


def test_completed_day_with_fewer_than_four_slots_stays_incomplete():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {18: 30.0, 19: 30.0})
    assert score_one(rows)["status"] == STATUS_INCOMPLETE_WINDOW


def test_today_in_progress_compares_only_the_observed_prefix():
    rows = flat_friday_history(12, 30.0)
    # Target Friday: 18:00 = 40, 19:00 = 50 → prefix mean 45 vs prefix norm 30.
    rows += day_rows(FRIDAY, {18: 40.0, 19: 50.0})

    row = score_one(rows, as_of=f"{FRIDAY}T20:30")
    assert row["status"] == STATUS_PROVISIONAL
    assert decode_hourly_slot_mask(row["observed_slot_mask"]) == (18, 19)
    assert row["observed_minutes"] == pytest.approx(45.0)
    # Reference cohort is the same two hours only, so the historical late tail
    # cannot drag the typical value down.
    assert row["typical_minutes"] == pytest.approx(30.0)
    assert row["category"] == CATEGORY_MUCH_WORSE


def test_single_sampled_hour_is_not_coloured_while_in_progress():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {18: 90.0})
    row = score_one(rows, as_of=f"{FRIDAY}T19:30")
    assert row["status"] == STATUS_INCOMPLETE_WINDOW
    assert pd.isna(row["category"])


def test_all_four_slots_before_window_end_remain_provisional():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    row = score_one(rows, as_of=f"{FRIDAY}T21:10")
    assert row["status"] == STATUS_PROVISIONAL
    assert row["category"] == CATEGORY_MUCH_WORSE

    # After 22:00 the same coverage is final.
    final = score_one(rows, as_of=f"{FRIDAY}T22:01")
    assert final["status"] == STATUS_FINAL


def test_observations_after_the_evaluation_moment_are_invisible():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS}, minute=5)
    row = score_one(rows, as_of=f"{FRIDAY}T20:30")
    # The 21:05 reading is later than the evaluation moment.
    assert decode_hourly_slot_mask(row["observed_slot_mask"]) == (18, 19, 20)
    assert row["last_observed_at"] == f"{FRIDAY}T20:05"


def test_not_started_before_the_window_opens():
    rows = flat_friday_history(12, 30.0)
    obs = prepare_observations(frame(rows))
    result = generate_anomaly_records(
        obs, as_of=f"{FRIDAY}T17:30", specs=[EVENING], route_codes=["R1"]
    )
    today = result[result["date"] == FRIDAY]
    assert len(today) == 1
    assert today.iloc[0]["status"] == STATUS_NOT_STARTED
    assert today.iloc[0]["observed_slot_mask"] == ""


def test_sparse_history_is_reported_not_invented():
    rows = flat_friday_history(MIN_HISTORY_DAYS - 1, 30.0)
    rows += day_rows(FRIDAY, {h: 90.0 for h in SLOTS})

    row = score_one(rows)
    assert row["status"] == STATUS_INSUFFICIENT_HISTORY
    assert row["reference_days"] == MIN_HISTORY_DAYS - 1
    assert pd.isna(row["category"])
    assert pd.isna(row["typical_minutes"])


def test_flat_reference_has_deterministic_tie_handling():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 30.0 for h in SLOTS})
    row = score_one(rows)

    assert row["tie_count"] == 12
    assert row["less_count"] == 0
    assert row["rank_score"] == pytest.approx((0 + 0.5 * 12 + 0.5) / 13)
    assert row["category"] == CATEGORY_USUAL


# ── Scoring primitives ───────────────────────────────────────────────────


def test_smoothed_mid_rank_is_a_rank_not_a_percentile():
    values = [10, 20, 30, 40]
    q, less, ties = smoothed_mid_rank(values, 30)
    assert (less, ties) == (2, 1)
    assert q == pytest.approx((2 + 0.5 + 0.5) / 5)


def test_classify_five_categories_and_guards():
    # typical 30 min → practical guard = max(2, 3) = 3 min
    assert classify(delta_minutes=15, delta_fraction=0.5, rank_score=0.95, typical_minutes=30) == CATEGORY_MUCH_WORSE
    assert classify(delta_minutes=15, delta_fraction=0.5, rank_score=0.81, typical_minutes=30) == CATEGORY_WORSE
    assert classify(delta_minutes=15, delta_fraction=0.5, rank_score=0.60, typical_minutes=30) == CATEGORY_USUAL
    assert classify(delta_minutes=-15, delta_fraction=-0.33, rank_score=0.05, typical_minutes=30) == CATEGORY_MUCH_BETTER
    assert classify(delta_minutes=-15, delta_fraction=-0.33, rank_score=0.19, typical_minutes=30) == CATEGORY_BETTER
    # Too small to matter, however extreme the rank.
    assert classify(delta_minutes=2.5, delta_fraction=0.083, rank_score=0.99, typical_minutes=30) == CATEGORY_USUAL
    # Ten percent of a long journey is a bigger absolute bar than two minutes.
    assert classify(delta_minutes=9, delta_fraction=0.09, rank_score=0.99, typical_minutes=100) == CATEGORY_USUAL


def test_exact_q_boundaries_stay_usual():
    # q = 0.75 exactly and 0.90 exactly must not be promoted to worse bands.
    assert classify(delta_minutes=10, delta_fraction=0.5, rank_score=0.75, typical_minutes=20) == CATEGORY_USUAL
    assert classify(delta_minutes=10, delta_fraction=0.5, rank_score=0.25, typical_minutes=20) == CATEGORY_USUAL


# ── Timezone independence ────────────────────────────────────────────────


def test_civil_date_weekday_does_not_follow_host_timezone():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    obs = prepare_observations(frame(rows))

    results = []
    original = os.environ.get("TZ")
    try:
        for tz in ("UTC", "America/New_York", "Asia/Kolkata"):
            os.environ["TZ"] = tz
            if hasattr(time, "tzset"):
                time.tzset()
            result = generate_anomaly_records(
                obs, as_of=night_before(FRIDAY), specs=[EVENING], route_codes=["R1"]
            )
            row = result[result["date"] == FRIDAY].iloc[0]
            results.append((row["category"], row["status"], row["rank_score"], row["typical_minutes"]))
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        if hasattr(time, "tzset"):
            time.tzset()

    assert len(set(results)) == 1


def test_window_boundaries_match_frontend_filters():
    assert EVENING.hours == (18, 19, 20, 21)
    assert EVENING.window_end == (0, 22)
    assert WINDOW_BY_TOD["late_hours"].hours == (22, 23, 0, 1, 2, 3, 4)
    assert WINDOW_BY_TOD["late_hours"].window_end == (1, 5)
    assert WINDOW_BY_TOD["weekday_morning"].hours == (8, 9, 10, 11)
    assert WINDOW_BY_TOD["weekday_afternoon"].hours == tuple(range(12, 18))
    assert WINDOW_BY_TOD["weekends"].hours == tuple(range(24))


def test_parse_as_of_converts_an_offset_timestamp_to_city_time():
    """The evaluation moment is an instant, not a wall clock in some other zone."""
    assert parse_as_of("2026-10-24T01:30:00+05:30") == datetime(2026, 10, 24, 1, 30)
    # 20:00 UTC on the 23rd is 01:30 the next morning in Kolkata.
    assert parse_as_of("2026-10-23T20:00:00Z") == datetime(2026, 10, 24, 1, 30)
    # The same instant handed over as a tz-aware object must agree.
    assert parse_as_of(datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)) == datetime(
        2026, 10, 24, 1, 30
    )


def test_parse_as_of_keeps_a_plain_date_and_naive_timestamp():
    assert parse_as_of("2026-10-24") == datetime(2026, 10, 24, 0, 0)
    assert parse_as_of("2026-10-24T18:45") == datetime(2026, 10, 24, 18, 45)
    assert parse_as_of(datetime(2026, 10, 24, 18, 45)) == datetime(2026, 10, 24, 18, 45)


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "yesterday", "24/10/2026", "2026-13-45", "2026-10-24T25:00", "2026-10-24T18:45+99:00"],
)
def test_parse_as_of_rejects_unparseable_values(bad):
    """A typo must not silently become midnight — that moves a day by hours."""
    with pytest.raises(ValueError):
        parse_as_of(bad)


def test_late_hours_night_groups_the_readings_around_midnight():
    """22:00–23:00 Friday + 00:00–04:00 Saturday is one Friday night.

    The readings keep their real source dates: the after-midnight slots belong
    to the night that opened at 22:00 on Friday, not to Saturday's own night.
    """
    late = WINDOW_BY_TOD["late_hours"]
    saturday = (date.fromisoformat(FRIDAY) + timedelta(days=1)).isoformat()

    rows = day_rows(FRIDAY, {22: 20.0, 23: 20.0})
    rows += day_rows(saturday, {0: 21.0, 1: 21.0, 2: 21.0, 3: 21.0, 4: 21.0})

    days = build_day_observations(build_slot_table(prepare_observations(frame(rows))), late)

    assert set(days) == {FRIDAY}, "the after-midnight readings must not form their own day"
    night = days[FRIDAY]
    assert night.weekday == 4  # Friday, derived from the date the window opened
    assert tuple(night.minutes_by_hour) == late.hours
    assert night.covers(late.hours)
    # Each hour keeps its own median: 20 before midnight, 21 after.
    assert night.minutes_by_hour[22] == 20.0
    assert night.minutes_by_hour[0] == 21.0


def test_late_hours_does_not_merge_saturday_night_into_friday_night():
    """Saturday's own 22:00 readings must stay a separate night."""
    late = WINDOW_BY_TOD["late_hours"]
    saturday = (date.fromisoformat(FRIDAY) + timedelta(days=1)).isoformat()

    rows = day_rows(FRIDAY, {22: 20.0, 23: 20.0})
    rows += day_rows(saturday, {0: 21.0, 1: 21.0, 2: 21.0, 3: 21.0, 4: 21.0})
    rows += day_rows(saturday, {22: 30.0, 23: 30.0})

    days = build_day_observations(build_slot_table(prepare_observations(frame(rows))), late)
    assert set(days) == {FRIDAY, saturday}
    assert days[FRIDAY].minutes_by_hour[22] == 20.0
    assert days[saturday].minutes_by_hour[22] == 30.0
    assert tuple(days[saturday].minutes_by_hour) == (22, 23)  # its 00–04 belong to Friday


def test_an_open_late_hours_night_keeps_the_slots_it_has():
    """After midnight the window is still open, though the row's date is past.

    v1 grants a provisional colour to the evening window only, so an open night
    still reports incomplete — but it must report the slots it has collected,
    including the after-midnight ones, rather than an empty window.
    """
    late = WINDOW_BY_TOD["late_hours"]
    saturday = (date.fromisoformat(FRIDAY) + timedelta(days=1)).isoformat()
    rows = day_rows(FRIDAY, {22: 20.0, 23: 20.0}) + day_rows(saturday, {0: 21.0})
    obs = prepare_observations(frame(rows))

    during = generate_anomaly_records(obs, as_of=f"{saturday}T01:00", specs=[late])
    friday = during[during["date"] == FRIDAY].iloc[0]
    assert friday["status"] == STATUS_INCOMPLETE_WINDOW
    assert decode_hourly_slot_mask(friday["observed_slot_mask"]) == (0, 22, 23)

    closed = generate_anomaly_records(obs, as_of=f"{saturday}T06:00", specs=[late])
    assert closed[closed["date"] == FRIDAY].iloc[0]["status"] == STATUS_INCOMPLETE_WINDOW


def test_a_complete_24_hour_window_stays_final_before_it_closes():
    """A 24-hour window closes at midnight but is done when its last slot lands.

    Evaluating on the window rather than "is this today" must not punish a
    bucket that has no provisional colour to fall back on.
    """
    full_day = WINDOW_BY_TOD["all"]
    thursday = (date.fromisoformat(FRIDAY) - timedelta(days=1)).isoformat()
    rows = []
    for weeks_ago in range(1, 10):  # enough comparable Thursdays to colour
        prior = (date.fromisoformat(thursday) - timedelta(weeks=weeks_ago)).isoformat()
        rows += day_rows(prior, {h: 30.0 for h in range(24)})
    rows += day_rows(thursday, {h: 45.0 for h in range(24)})
    obs = prepare_observations(frame(rows))

    result = generate_anomaly_records(obs, as_of=f"{FRIDAY}T00:30", specs=[full_day])
    row = result[result["date"] == thursday].iloc[0]
    assert row["status"] == STATUS_FINAL
    assert decode_hourly_slot_mask(row["observed_slot_mask"]) == tuple(range(24))


def test_late_hours_window_completes_on_the_next_civil_day():
    late = WINDOW_BY_TOD["late_hours"]
    saturday = (date.fromisoformat(FRIDAY) + timedelta(days=1)).isoformat()
    rows = day_rows(FRIDAY, {22: 20.0, 23: 20.0})
    rows += day_rows(saturday, {0: 21.0, 1: 21.0, 2: 21.0, 3: 21.0, 4: 21.0})
    obs = prepare_observations(frame(rows))

    # 23:30 on Friday: the window is still open, so only the two started slots count.
    during = generate_anomaly_records(
        obs, as_of=f"{FRIDAY}T23:30", specs=[late], route_codes=["R1"]
    )
    friday = during[during["date"] == FRIDAY].iloc[0]
    assert friday["status"] == STATUS_INCOMPLETE_WINDOW
    assert decode_hourly_slot_mask(friday["observed_slot_mask"]) == (22, 23)

    # 05:30 the next morning: the same Friday night is complete, seven slots.
    after = generate_anomaly_records(
        obs, as_of=f"{saturday}T05:30", specs=[late], route_codes=["R1"]
    )
    friday = after[after["date"] == FRIDAY].iloc[0]
    assert decode_hourly_slot_mask(friday["observed_slot_mask"]) == (0, 1, 2, 3, 4, 22, 23)
    assert friday["observed_minutes"] == pytest.approx((20 * 2 + 21 * 5) / 7, abs=0.01)
    # No comparable late-night history in this fixture, so no colour is claimed.
    assert friday["status"] == STATUS_INSUFFICIENT_HISTORY


# ── Export contract ──────────────────────────────────────────────────────


def test_slot_mask_round_trip():
    for hours in [(18, 19, 20, 21), (0,), tuple(range(24)), (22, 23, 0, 1)]:
        assert decode_hourly_slot_mask(hourly_slot_mask(hours)) == tuple(sorted(hours))
    assert len(hourly_slot_mask(range(24))) == 6


def test_export_columns_and_null_semantics():
    rows = flat_friday_history(MIN_HISTORY_DAYS - 1, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    obs = prepare_observations(frame(rows))

    result = generate_anomaly_records(obs, as_of=night_before(FRIDAY), specs=[EVENING])
    assert list(result.columns) == list(EXPORT_COLUMNS)

    sparse = result[result["status"] == STATUS_INSUFFICIENT_HISTORY]
    assert len(sparse) >= 1
    assert sparse["category"].isna().all()
    assert sparse["typical_minutes"].isna().all()
    # Counts stay integers in the CSV, not floats.
    assert str(result["reference_days"].dtype) == "Int64"
    assert (result["method_version"] == METHOD_VERSION).all()
    assert (result["city_timezone"] == CITY_TIMEZONE).all()


def test_export_is_deterministic_for_unchanged_inputs():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    obs = prepare_observations(frame(rows))

    # generated_at defaults to the wall clock at second precision, so two calls
    # straddling a second boundary would differ there and nowhere else. Pin it:
    # the point of the test is that the scores are reproducible.
    stamped = datetime(2026, 10, 23, 20, 0)
    first = generate_anomaly_records(
        obs, as_of=night_before(FRIDAY), specs=[EVENING], generated_at=stamped
    )
    second = generate_anomaly_records(
        obs, as_of=night_before(FRIDAY), specs=[EVENING], generated_at=stamped
    )
    pd.testing.assert_frame_equal(first, second)


def test_display_label_is_not_route_identity():
    """Renaming a route's label must not split or merge its baseline."""
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    obs = prepare_observations(frame(rows))
    result = generate_anomaly_records(obs, as_of=night_before(FRIDAY), specs=[EVENING])
    assert set(result["route_code"]) == {"R1"}
    assert all("label" not in column for column in result.columns)


def test_distance_variation_is_flagged_not_dropped():
    rows = flat_friday_history(12, 30.0)
    # Target Friday mixes a 9.9 km and an 11.6 km route card.
    rows += [
        (FRIDAY, "18:10", "R1", 30.0, 9.9),
        (FRIDAY, "19:10", "R1", 30.0, 11.6),
        (FRIDAY, "20:10", "R1", 30.0, 9.9),
        (FRIDAY, "21:10", "R1", 30.0, 9.9),
    ]
    row = score_one(rows)
    assert "distance_varied" in row["quality_flags"]
    assert row["status"] == STATUS_FINAL  # flagged for interpretation, still scored
    assert row["distance_min_km"] == pytest.approx(9.9)
    assert row["distance_max_km"] == pytest.approx(11.6)


# ── Published window ─────────────────────────────────────────────────────


def test_publishes_only_target_dates_inside_the_trailing_window():
    """Scoring is full-history; publication is bounded to the last 90 days."""
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    rows += day_rows("2026-07-10", {h: 40.0 for h in SLOTS})  # 105 days before FRIDAY
    result = generate_anomaly_records(
        prepare_observations(frame(rows)),
        as_of=night_before(FRIDAY),
        specs=[EVENING],
        route_codes=["R1"],
    )

    published = set(result["date"])
    assert "2026-07-10" not in published
    # as_of = 2026-10-24T00:30 → the window opens on 2026-07-26.
    assert min(published) >= "2026-07-26"
    assert max(published) <= "2026-10-24"
    assert FRIDAY in published


def test_boundary_date_keeps_the_reference_cohort_that_predates_the_window():
    """A date at the window edge is scored against history the file never shows."""
    boundary = "2026-07-24"  # a Friday
    as_of_day = (date.fromisoformat(boundary) + timedelta(days=90)).isoformat()

    rows = [
        (day, f"{hour:02d}:10", "R1", 30.0, 10.0)
        for day in prior_fridays(12, end=boundary)
        for hour in SLOTS
    ]
    rows += day_rows(boundary, {h: 60.0 for h in SLOTS})

    result = generate_anomaly_records(
        prepare_observations(frame(rows)),
        as_of=as_of_day + "T00:30",
        specs=[EVENING],
        route_codes=["R1"],
    )

    # Every reference Friday is older than the window, so the published rows are
    # the boundary date and the (empty) evaluation day — and the boundary still
    # sees all twelve references.
    assert set(result["date"]) == {boundary, as_of_day}
    record = result[result["date"] == boundary].iloc[0]
    assert pd.isna(result[result["date"] == as_of_day]["category"]).all()
    assert int(record["reference_days"]) == 12
    assert record["reference_start"] < boundary
    assert record["typical_minutes"] == pytest.approx(30.0)
    assert record["category"] == CATEGORY_MUCH_WORSE


def test_window_filter_does_not_change_the_category_of_an_in_window_day():
    """Same target, same inputs, different as_of → identical result."""
    rows = flat_friday_history(12, 30.0) + day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    obs = prepare_observations(frame(rows))

    tight = generate_anomaly_records(obs, as_of=night_before(FRIDAY), specs=[EVENING])
    wide = generate_anomaly_records(
        obs,
        as_of=(date.fromisoformat(FRIDAY) + timedelta(days=30)).isoformat() + "T00:30",
        specs=[EVENING],
    )

    tight_row = tight[tight["date"] == FRIDAY].iloc[0]
    wide_row = wide[wide["date"] == FRIDAY].iloc[0]
    for column in ("category", "status", "typical_minutes", "delta_minutes", "rank_score", "reference_days"):
        assert tight_row[column] == wide_row[column], column


def test_audit_uses_the_in_progress_prefix_when_history_is_insufficient():
    """The audit must explain the comparison that was actually scored.

    Today at 19:30 has a valid two-slot prefix but only seven comparable
    Fridays, so the record ends up insufficient_history. The slots used for the
    comparison are still the prefix, and the audit has to report those — with
    the same seven reference dates the record counted.
    """
    rows: list[tuple] = []
    for prior in prior_fridays(7):          # below MIN_HISTORY_DAYS
        rows += day_rows(prior, {18: 30.0, 19: 30.0})
    rows += day_rows(FRIDAY, {18: 44.0, 19: 45.0})

    payload = build_audit_payload(
        prepare_observations(frame(rows)),
        route_code="R1",
        target_date=FRIDAY,
        tod="weekday_evening",
        as_of=f"{FRIDAY}T19:30",
    )

    assert payload["record"]["status"] == STATUS_INSUFFICIENT_HISTORY
    assert payload["compared_slots"] == [18, 19]
    assert len(payload["reference_dates"]) == 7
    assert int(payload["record"]["reference_days"]) == 7
    assert {s["minutes"] for s in payload["reference_summaries"]} == {30.0}


def test_audit_keeps_the_full_window_for_a_completed_day():
    """A completed day is audited against every slot it was scored on."""
    rows = flat_friday_history(12, 30.0) + day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    payload = build_audit_payload(
        prepare_observations(frame(rows)),
        route_code="R1",
        target_date=FRIDAY,
        tod="weekday_evening",
        as_of=night_before(FRIDAY),
    )
    assert payload["compared_slots"] == list(SLOTS)
    assert len(payload["reference_dates"]) == 12


def test_audit_payload_reconstructs_the_category():
    rows = flat_friday_history(12, 30.0)
    rows += day_rows(FRIDAY, {h: 45.0 for h in SLOTS})
    payload = build_audit_payload(
        prepare_observations(frame(rows)),
        route_code="R1",
        target_date=FRIDAY,
        tod="weekday_evening",
        as_of=night_before(FRIDAY),
    )
    assert payload["method_version"] == METHOD_VERSION
    assert len(payload["reference_dates"]) == 12
    assert payload["compared_slots"] == [18, 19, 20, 21]
    assert payload["record"]["category"] == CATEGORY_MUCH_WORSE
    assert {s["minutes"] for s in payload["reference_summaries"]} == {30.0}
