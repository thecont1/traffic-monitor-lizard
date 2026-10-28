"""Export-contract tests for generate_calendar_exports.py.

The frontend parses this file directly, so the CSV text itself is the contract:
blank means "no value", integers stay integers, categories only appear on
scorable statuses, and the reference window never contains the target date.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pytest

from calendar_anomalies import (
    CATEGORY_MUCH_WORSE,
    CITY_TIMEZONE,
    EXPORT_COLUMNS,
    METHOD_VERSION,
    STATUS_FINAL,
    STATUS_INSUFFICIENT_HISTORY,
)
from generate_calendar_exports import main

SLOTS = (18, 19, 20, 21)
TARGET = "2026-10-23"


def write_traffic_csv(path: Path) -> None:
    """Twelve prior Fridays at 30 min, target Friday at 45 min, plus one slow day."""
    rows = [("date", "time", "route_code", "duration", "distance")]
    cursor = date.fromisoformat(TARGET)
    fridays: list[str] = []
    while len(fridays) < 12:
        cursor -= timedelta(days=1)
        if cursor.weekday() == 4:
            fridays.append(cursor.isoformat())
    for friday in sorted(fridays):
        for hour in SLOTS:
            rows.append((friday, f"{hour:02d}:10", "R1", 30, 10.0))
            rows.append((friday, f"{hour:02d}:10", "R2", 32, 10.0))
    for hour in SLOTS:
        rows.append((TARGET, f"{hour:02d}:10", "R1", 45, 10.0))
        rows.append((TARGET, f"{hour:02d}:10", "R2", 32, 10.0))

    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


@pytest.fixture()
def exported(tmp_path: Path) -> list[dict[str, str]]:
    traffic = tmp_path / "traffic.csv"
    write_traffic_csv(traffic)
    out = tmp_path / "csv-calendar-anomalies-bangalore.csv"

    code = main(
        [
            "--traffic-csv",
            str(traffic),
            "--routes-csv",
            str(tmp_path / "missing-routes.csv"),
            "--output",
            str(out),
            "--as-of",
            "2026-10-24T00:30",
            "--tod",
            "weekday_evening",
            "--quiet",
        ]
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "nan" not in text.lower().replace("bangalore", "")
    assert "None" not in text
    assert "NaT" not in text
    return list(csv.DictReader(text.splitlines()))


def test_failed_write_leaves_the_previous_export_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The export is committed by CI; a half-written file must never land."""
    traffic = tmp_path / "traffic.csv"
    write_traffic_csv(traffic)
    out = tmp_path / "csv-calendar-anomalies-bangalore.csv"
    out.write_text("previous export\n", encoding="utf-8")

    def explode(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("pandas.DataFrame.to_csv", explode)

    with pytest.raises(OSError):
        main(
            [
                "--traffic-csv", str(traffic),
                "--routes-csv", str(tmp_path / "missing-routes.csv"),
                "--output", str(out),
                "--as-of", "2026-10-24T00:30",
                "--tod", "weekday_evening",
                "--quiet",
            ]
        )

    assert out.read_text(encoding="utf-8") == "previous export\n"
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(f".{out.name}")]
    assert leftovers == [], f"temporary files left behind: {leftovers}"


def test_header_is_the_documented_contract(exported: list[dict[str, str]]) -> None:
    assert list(exported[0].keys()) == list(EXPORT_COLUMNS)


def test_export_defaults_are_not_placeholders(exported: list[dict[str, str]]) -> None:
    assert {r["method_version"] for r in exported} == {METHOD_VERSION}
    assert {r["city_timezone"] for r in exported} == {CITY_TIMEZONE}
    assert {r["lookback_days"] for r in exported} == {"90"}
    assert all(r["source_revision"].startswith("sha256:") for r in exported)
    assert all(r["generated_at"] for r in exported)


def test_final_rows_have_a_strictly_earlier_reference_window(
    exported: list[dict[str, str]],
) -> None:
    finals = [r for r in exported if r["status"] == STATUS_FINAL]
    assert finals
    for row in finals:
        assert row["reference_end_exclusive"] <= row["date"]
        assert row["reference_start"] < row["date"]
        assert int(row["reference_days"]) >= 8


def test_scored_row_carries_effect_and_rank(exported: list[dict[str, str]]) -> None:
    target = next(
        r for r in exported if r["date"] == TARGET and r["route_code"] == "R1"
    )
    assert target["status"] == STATUS_FINAL
    assert target["category"] == CATEGORY_MUCH_WORSE
    assert float(target["observed_minutes"]) == pytest.approx(45.0)
    assert float(target["typical_minutes"]) == pytest.approx(30.0)
    assert float(target["delta_minutes"]) == pytest.approx(15.0)
    assert float(target["rank_score"]) == pytest.approx(12.5 / 13, abs=1e-4)
    assert target["observed_slot_mask"] == "3c0000"
    assert target["expected_slot_mask"] == "3c0000"


def test_insufficient_history_rows_leave_numbers_blank(
    exported: list[dict[str, str]],
) -> None:
    sparse = [r for r in exported if r["status"] == STATUS_INSUFFICIENT_HISTORY]
    assert sparse
    for row in sparse:
        assert row["category"] == ""
        assert row["typical_minutes"] == ""
        assert row["delta_minutes"] == ""
        assert row["rank_score"] == ""
        # Counts are integers, never blank-as-zero.
        assert row["reference_days"].isdigit()


def test_categories_only_appear_on_scorable_statuses(
    exported: list[dict[str, str]],
) -> None:
    for row in exported:
        if row["category"]:
            assert row["status"] in ("final", "provisional")
