#!/usr/bin/env python3
import csv
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "csv-routes-bangalore.csv"
WEATHER_CSV_PATH = DATA_DIR / "csv-weather-snapshot.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

HEADERS_FOLLOWUP = {**HEADERS, "Sec-Fetch-Site": "same-origin", "Referer": "https://www.accuweather.com/"}

_local = threading.local()


def _get_session() -> requests.Session:
    """Return a thread-local session, primed with AccuWeather homepage to avoid 403 on follow-up pages."""
    if not getattr(_local, "session", None):
        _local.session = requests.Session()
        try:
            _local.session.get("https://www.accuweather.com/", headers=HEADERS, timeout=20)
            time.sleep(1)
        except requests.RequestException:
            pass
    return _local.session


def _get_with_retry(url: str, retries: int = 4, delay: float = 3.0) -> requests.Response:
    """GET with retry on 403/5xx, using follow-up headers and exponential back-off."""
    session = _get_session()
    last_exc: Exception = requests.RequestException(f"No attempts made for {url}")
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS_FOLLOWUP, timeout=20)
            if resp.status_code == 403:
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(2)
        except requests.RequestException as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(2)
    raise last_exc


def extract_aqi(url: str) -> dict:
    """Scrape AQI number and category from an AccuWeather air-quality-index page."""
    resp = _get_with_retry(url)
    soup = BeautifulSoup(resp.text, "lxml")

    aqi_value = None
    aqi_category = None

    num_el = soup.select_one("#current .aq-number")
    if num_el:
        m = re.search(r"(\d+)", num_el.get_text(strip=True))
        if m:
            aqi_value = m.group(1)

    cat_el = soup.select_one("#current .category-text")
    if cat_el:
        aqi_category = cat_el.get_text(strip=True) or None

    return {"aqi": aqi_value, "aqi_flag": aqi_category}


def build_minutecast_url(station: str) -> str:
    """Build AccuWeather minute-weather-forecast URL from 'name/id' (e.g. 'jogupalya/3352209')."""
    parts = station.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Expected 'name/id', got '{station}'")
    name, lid = parts
    return f"https://www.accuweather.com/en/in/{name}/{lid}/minute-weather-forecast/{lid}?unit=c"


def build_current_weather_url(station: str) -> str:
    """Build AccuWeather current-weather URL from 'name/id'."""
    parts = station.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Expected 'name/id', got '{station}'")
    name, lid = parts
    return f"https://www.accuweather.com/en/in/{name}/{lid}/current-weather/{lid}?unit=c"


def extract_current_weather(url: str) -> dict:
    """Extract temp, temp_flag, realfeel, realfeel_flag and humidity from current-weather page."""
    resp = _get_with_retry(url)
    soup = BeautifulSoup(resp.text, "lxml")

    temp = None
    temp_flag = None
    realfeel = None
    realfeel_flag = None
    humidity = None

    # temp: innermost div inside .current-weather-info > div > div
    temp_el = soup.select_one(".current-weather-info > div > div")
    if temp_el:
        m = re.search(r"(\d+)", temp_el.get_text(strip=True))
        if m:
            temp = m.group(1)

    # temp_flag: .current-weather .phrase
    phrase_el = soup.select_one(".current-weather .phrase")
    if phrase_el:
        temp_flag = phrase_el.get_text(strip=True) or None

    # realfeel: first div inside .current-weather-extra, integer only
    realfeel_el = soup.select_one(".current-weather-extra.no-realfeel-phrase > div")
    if realfeel_el:
        m = re.search(r"(\d+)", realfeel_el.get_text(strip=True))
        if m:
            realfeel = m.group(1)

    # realfeel_flag: nested div > div > div inside .current-weather-extra
    realfeel_flag_el = soup.select_one(".current-weather-extra.no-realfeel-phrase > div > div > div")
    if realfeel_flag_el:
        realfeel_flag = realfeel_flag_el.get_text(strip=True) or None

    # humidity: 5th detail item, 2nd cell
    humidity_el = soup.select_one(".current-weather-details.no-realfeel-phrase.odd > div:nth-child(5) > div:nth-child(2)")
    if humidity_el:
        m = re.search(r"(\d+)", humidity_el.get_text(strip=True))
        if m:
            humidity = m.group(1)

    return {"temp": temp, "temp_flag": temp_flag, "realfeel": realfeel, "realfeel_flag": realfeel_flag, "humidity": humidity}


def extract_minute_weather(url: str) -> dict:
    """Scrape rsi_flag and rsi_forecast from minute-weather-forecast page."""
    resp = _get_with_retry(url)
    soup = BeautifulSoup(resp.text, "lxml")

    rsi_flag = None
    rsi_forecast = None

    # rsi_flag: .conditions-icon .icon-phrase
    flag_el = soup.select_one(".conditions-icon p.icon-phrase")
    if flag_el:
        rsi_flag = flag_el.get_text(strip=True) or None

    # rsi_forecast: .summary
    summary_el = soup.select_one(".summary")
    if summary_el:
        rsi_forecast = summary_el.get_text(strip=True) or None

    return {"rsi_flag": rsi_flag, "rsi_forecast": rsi_forecast}


def build_aqi_url(station: str) -> str:
    """Build AccuWeather air-quality-index URL from 'name/id'."""
    parts = station.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Expected 'name/id', got '{station}'")
    name, lid = parts
    return f"https://www.accuweather.com/en/in/{name}/{lid}/air-quality-index/{lid}?unit=c"


def read_stations() -> list:
    """Return unique stations from the CSV, preserving first occurrence of each station."""
    stations = []
    seen = set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            station = row.get("accuweather_station", "").strip()
            if station and station not in seen:
                seen.add(station)
                stations.append({
                    "station": station,
                    "label": row.get("label_short", station),
                    "route_code": row.get("route_code", ""),
                })
    return stations


CSV_FIELDS = [
    "route_code", "aqi", "aqi_category", "condition",
    "temp_c", "realfeel_c", "realfeel_word", "humidity_pct", "wind_gust_kmh", "uv_index",
]

# Column order for snapshot CSV (used by --json flag)
SNAPSHOT_FIELDS = [
    "route_code", "route_name_short", "accuweather_station", "temp", "temp_flag",
    "realfeel", "realfeel_flag", "humidity", "rsi_flag", "rsi_forecast",
    "aqi", "aqi_flag"
]


def _csv_val(v: Optional[str]) -> str:
    return v if v is not None else ""


def write_csv(rows: list, output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "route_code": r["route_code"],
                "aqi": _csv_val(r.get("aqi_value")),
                "aqi_category": _csv_val(r.get("aqi_category")),
                "condition": _csv_val(r.get("status")),
                "temp_c": _csv_val(r.get("temp")),
                "realfeel_c": _csv_val(r.get("realfeel_temp")),
                "realfeel_word": _csv_val(r.get("realfeel_word")),
                "humidity_pct": _csv_val(r.get("humidity")),
                "wind_gust_kmh": _csv_val(r.get("wind")),
                "uv_index": _csv_val(r.get("uv_index")),
            })


def write_snapshot_csv(rows: list, output_path: Path) -> None:
    """Write weather snapshot CSV with specific column order for DB import."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SNAPSHOT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: _csv_val(r.get(k)) for k in SNAPSHOT_FIELDS})



def print_table(rows: list) -> None:
    """Print weather data as a neat table."""
    if not rows:
        print("No data to display")
        return

    # Determine column widths
    route_w = 10
    label_w = 6
    weather_w = 12
    end_w = 20
    temp_w = 5
    rf_w = 8
    rf_status_w = 10

    for r in rows:
        route_w = max(route_w, len(str(r.get("route_code", ""))))
        label_w = max(label_w, len(str(r.get("route_name_short", ""))))

    # Print header
    print(f"{'route_code':<{route_w}}  {'route_name_short':<{label_w}}  {'temp':>{temp_w}}  {'realfeel_temp':>{rf_w}}  {'realfeel_status':<{rf_status_w}}  {'rsi_flag':<{weather_w}}  {'rsi_forecast':<{end_w}}  {'humidity':>4}  {'aqi_score':>4}  {'aqi_flag':>8}")
    print("-" * (route_w + label_w + weather_w + end_w + rf_status_w + 50))

    # Print rows
    for r in rows:
        route = str(r.get("route_code", ""))[:route_w]
        label = str(r.get("route_name_short", ""))[:label_w]
        temp = str(r.get("temp", "")) if r.get("temp") else "null"
        rf = str(r.get("realfeel_temp", "")) if r.get("realfeel_temp") else "null"
        rf_status = str(r.get("realfeel_status", "")) if r.get("realfeel_status") else "null"
        rsi_flag = str(r.get("rsi_flag", "")) if r.get("rsi_flag") else "null"
        rsi_forecast = str(r.get("rsi_forecast", "")) if r.get("rsi_forecast") else "null"
        hum = str(r.get("humidity", "")) if r.get("humidity") else "null"
        aqi_score = str(r.get("aqi_score", "")) if r.get("aqi_score") else "null"
        aqi_flag = str(r.get("aqi_flag", "")) if r.get("aqi_flag") else "null"

        print(f"{route:<{route_w}}  {label:<{label_w}}  {temp:>{temp_w}}  {rf:>{rf_w}}  {rf_status:<{rf_status_w}}  {rsi_flag:<{weather_w}}  {rsi_forecast:<{end_w}}  {hum:>4}  {aqi_score:>4}  {aqi_flag:>8}")


def main() -> None:
    """Fetch weather for all stations, write snapshot CSV, and print a table or JSON."""
    import argparse
    parser = argparse.ArgumentParser(description="Fetch AccuWeather data for Bangalore route stations.")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of table")
    args = parser.parse_args()

    stations = read_stations()
    print(f"Fetching weather for {len(stations)} stations...", file=sys.stderr)

    def fetch_station(s: dict) -> dict:
        time.sleep(random.uniform(0.5, 2.5))  # jitter to avoid simultaneous bursts
        minute_url = build_minutecast_url(s["station"])
        current_url = build_current_weather_url(s["station"])
        aqi_url = build_aqi_url(s["station"])
        try:
            data = extract_minute_weather(minute_url)
        except requests.RequestException:
            data = {k: None for k in ["rsi_flag", "rsi_forecast"]}

        try:
            current_data = extract_current_weather(current_url)
            data.update(current_data)
        except requests.RequestException:
            data.update({k: None for k in ["temp", "temp_flag", "realfeel", "realfeel_flag", "humidity"]})

        try:
            aqi_data = extract_aqi(aqi_url)
            data.update(aqi_data)
        except requests.RequestException:
            data.update({"aqi": None, "aqi_flag": None})

        data["route_code"] = s.get("route_code", "")
        data["route_name_short"] = s.get("label", s["station"])
        data["accuweather_station"] = s["station"]
        return data

    rows_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch_station, s): s for s in stations}
        for future in as_completed(futures):
            s = futures[future]
            try:
                result = future.result()
                rows_map[s["route_code"]] = result
                print(f"  {s['station']} ok", file=sys.stderr)
            except Exception as exc:
                print(f"  {s['station']} FAILED: {exc}", file=sys.stderr)
                rows_map[s["route_code"]] = {
                    k: None for k in ["temp", "temp_flag", "realfeel", "realfeel_flag",
                                      "humidity", "rsi_flag", "rsi_forecast",
                                      "aqi", "aqi_flag",
                                      "route_code", "route_name_short", "accuweather_station"]
                }

    # Preserve original station order
    rows = [rows_map[s["route_code"]] for s in stations if s["route_code"] in rows_map]

    write_snapshot_csv(rows, WEATHER_CSV_PATH)
    print(f"Wrote {WEATHER_CSV_PATH}", file=sys.stderr)

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print()
        print_table(rows)


if __name__ == "__main__":
    main()