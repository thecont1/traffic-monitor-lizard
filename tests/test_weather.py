"""Tests for tools/weather.py — the all-stations-empty abort guard."""

import sys

import pytest
from curl_cffi import requests

import weather


def _station():
    return {"station": "shantala-nagar/3352203", "label": "Airport Expy", "route_code": "X|Y"}


def _raise(*args, **kwargs):
    raise requests.RequestsError("blocked")


def _run_main(monkeypatch, tmp_path, stations, **extractors):
    monkeypatch.setattr(weather, "read_stations", lambda: stations)
    monkeypatch.setattr(weather, "extract_minute_weather", extractors.get("minute", _raise))
    monkeypatch.setattr(weather, "extract_current_weather", extractors.get("current", _raise))
    monkeypatch.setattr(weather, "extract_aqi", extractors.get("aqi", _raise))
    monkeypatch.setattr(weather, "WEATHER_CSV_PATH", tmp_path / "weather.csv")
    monkeypatch.setattr(weather.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(sys, "argv", ["weather.py", "--json"])


class TestNoDataAbort:
    def test_aborts_when_all_stations_empty(self, monkeypatch, tmp_path):
        out = tmp_path / "weather.csv"
        _run_main(monkeypatch, tmp_path, [_station()])
        with pytest.raises(SystemExit) as exc:
            weather.main()
        assert exc.value.code == 1
        assert not out.exists()

    def test_writes_when_any_data_present(self, monkeypatch, tmp_path):
        out = tmp_path / "weather.csv"
        _run_main(
            monkeypatch,
            tmp_path,
            [_station()],
            current=lambda url: {
                "temp": "29",
                "temp_flag": "Sunny",
                "realfeel": "32",
                "realfeel_flag": "Hot",
                "humidity": "48",
            },
        )
        weather.main()
        assert out.exists()
        assert "29" in out.read_text()
