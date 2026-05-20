#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CSV_PATH = Path(__file__).parent / "csv-routes-bangalore.csv"
WEATHER_MD_PATH = Path(__file__).parent / "weather.md"
WEATHER_CSV_PATH = Path(__file__).parent / "weather_snapshot.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    """Return a shared session, primed with AccuWeather homepage to avoid 403 on AQI pages."""
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        try:
            _SESSION.get("https://www.accuweather.com/", headers=HEADERS, timeout=20)
        except requests.RequestException:
            pass
    return _SESSION


def extract_aqi(url: str) -> dict:
    """Scrape AQI number and category from an AccuWeather air-quality-index page."""
    resp = _get_session().get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    aqi_value = None
    aqi_category = None

    card = soup.select_one(".air-quality-card")
    if card:
        num_el = card.select_one(".aq-number")
        if num_el:
            m = re.search(r"(\d+)", num_el.get_text(strip=True))
            if m:
                aqi_value = m.group(1)

        data_el = card.select_one("h3.air-quality-data")
        if data_el:
            aqi_category = data_el.get_text(" ", strip=True).split()[0]

    if not aqi_value:
        page_text = soup.get_text(" ", strip=True)
        m = re.search(r"(\d{1,3})\s*AQI", page_text)
        if m:
            aqi_value = m.group(1)

    return {"aqi_value": aqi_value, "aqi_category": aqi_category}


def extract_current_weather(url: str) -> dict:
    resp = _get_session().get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    temp = None
    realfeel_temp = None
    realfeel_word = None
    humidity = None
    wind = None
    uv_index = None
    visibility = None
    pressure = None
    dew_point = None
    status = None

    card = soup.select_one(".current-weather-card")
    if card:
        temp_el = card.select_one(".temp")
        if temp_el:
            m = re.search(r"(\d+)", temp_el.get_text(strip=True))
            if m:
                temp = m.group(1)

        phrase = card.select_one(".phrase")
        if phrase:
            status = phrase.get_text(strip=True)

        label = card.select_one(".current-weather-extra .label.clickable")
        if label:
            realfeel_word = label.get_text(strip=True)

        for item in card.select(".detail-item"):
            text = item.get_text(" ", strip=True)
            if text.startswith("RealFeel®") or text.startswith("RealFeel "):
                m = re.search(r"(\d+)", text)
                if m:
                    realfeel_temp = m.group(1)
            elif text.startswith("Humidity") and "Indoor" not in text:
                m = re.search(r"(\d+)", text)
                if m:
                    humidity = m.group(1)
            elif text.startswith("Wind"):
                m = re.search(r"(\d+)\s*km/h", text)
                if m:
                    wind = m.group(1)
            elif text.startswith("UV Index"):
                m = re.search(r"(\d+)", text.split("UV Index", 1)[-1])
                if m:
                    uv_index = m.group(1)
            elif text.startswith("Visibility"):
                visibility = text.split("Visibility", 1)[-1].strip()
            elif text.startswith("Pressure"):
                pressure = text.split("Pressure", 1)[-1].strip()
            elif text.startswith("Dew Point"):
                dew_point = text.split("Dew Point", 1)[-1].strip()

    # Fallback: regex on full page text if card selectors missed
    if not any([realfeel_temp, humidity, status]):
        page_text = soup.get_text(" ", strip=True)

        m = re.search(r"RealFeel(?:®)?\s*(\d+)[°º]?", page_text)
        if m:
            realfeel_temp = m.group(1)

        m = re.search(r"(?<!Indoor )Humidity\s*(\d+)", page_text)
        if m:
            humidity = m.group(1)

    return {
        "temp": temp,
        "status": status,
        "realfeel_temp": realfeel_temp,
        "realfeel_word": realfeel_word,
        "humidity": humidity,
        "wind": wind,
        "uv_index": uv_index,
        "visibility": visibility,
        "pressure": pressure,
        "dew_point": dew_point,
    }


def build_url(station: str) -> str:
    """Build AccuWeather current-weather URL from 'name/id' (e.g. 'jogupalya/3352209')."""
    parts = station.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Expected 'name/id', got '{station}'")
    name, lid = parts
    return f"https://www.accuweather.com/en/in/{name}/{lid}/current-weather/{lid}"


def build_aqi_url(station: str) -> str:
    """Build AccuWeather air-quality-index URL from 'name/id'."""
    parts = station.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Expected 'name/id', got '{station}'")
    name, lid = parts
    return f"https://www.accuweather.com/en/in/{name}/{lid}/air-quality-index/{lid}"


def read_stations() -> list[dict]:
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


def _val(v: str | None, suffix: str = "") -> str:
    return f"{v}{suffix}" if v else "—"


CSV_FIELDS = [
    "route_code", "aqi", "aqi_category", "condition",
    "temp_c", "realfeel_c", "realfeel_word", "humidity_pct", "wind_gust_kmh", "uv_index",
]


def _csv_val(v: str | None) -> str:
    return v if v is not None else ""


def write_csv(rows: list[dict], output_path: Path) -> None:
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


def fetch_all_and_write(output_path: Path) -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist).strftime("%d %b %Y, %H:%M IST")

    stations = read_stations()
    print(f"Fetching weather for {len(stations)} stations…", file=sys.stderr)

    _get_session()  # prime session once before any AQI fetches

    rows = []
    for s in stations:
        weather_url = build_url(s["station"])
        aqi_url = build_aqi_url(s["station"])
        print(f"  {s['station']} … ", end="", file=sys.stderr)
        try:
            data = extract_current_weather(weather_url)
            data["error"] = None
        except requests.HTTPError as e:
            data = {k: None for k in ["temp", "status", "realfeel_temp", "realfeel_word",
                                       "humidity", "wind", "uv_index", "visibility",
                                       "pressure", "dew_point"]}
            data["error"] = f"HTTP {e.response.status_code}"
        except requests.RequestException as e:
            data = {k: None for k in ["temp", "status", "realfeel_temp", "realfeel_word",
                                       "humidity", "wind", "uv_index", "visibility",
                                       "pressure", "dew_point"]}
            data["error"] = str(e)

        try:
            aqi_data = extract_aqi(aqi_url)
        except requests.RequestException:
            aqi_data = {"aqi_value": None, "aqi_category": None}

        data.update(aqi_data)
        print(f"weather={'ok' if not data['error'] else data['error']} aqi={aqi_data['aqi_value']}", file=sys.stderr)
        rows.append({**s, **data})

    lines = [
        f"# Bangalore Weather Snapshot",
        f"",
        f"*Fetched: {now}*",
        f"",
        f"| Station | Route | AQI | AQI Category | Condition | Temp | RealFeel | Feel | Humidity | Wind (km/h) | UV Index |",
        f"|---------|-------|-----|--------------|-----------|------|----------|------|----------|----|----------|",
    ]
    for r in rows:
        station_link = f"[{r['station']}]({build_url(r['station'])})"
        if r.get("error"):
            lines.append(
                f"| {station_link} | {r['label']} | {_val(r['aqi_value'])} | {_val(r['aqi_category'])} | ⚠ {r['error']} | — | — | — | — | — | — |"
            )
        else:
            lines.append(
                f"| {station_link} | {r['label']} "
                f"| {_val(r['aqi_value'])} "
                f"| {_val(r['aqi_category'])} "
                f"| {_val(r['status'])} "
                f"| {_val(r['temp'])} "
                f"| {_val(r['realfeel_temp'])} "
                f"| {_val(r['realfeel_word'])} "
                f"| {_val(r['humidity'])} "
                f"| {_val(r['wind'])} "
                f"| {_val(r['uv_index'])} |"
            )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}", file=sys.stderr)

    write_csv(rows, WEATHER_CSV_PATH)
    print(f"Wrote {WEATHER_CSV_PATH}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch AccuWeather data for all Bangalore route stations and write to weather.md"
    )
    parser.add_argument(
        "location",
        nargs="?",
        help="Single AccuWeather station as name/id (e.g. 'jogupalya/3352209'). "
             "If omitted, fetches all stations from the CSV and writes weather.md.",
    )
    parser.add_argument(
        "--output",
        default=str(WEATHER_MD_PATH),
        help="Output Markdown file path (default: weather.md next to this script)",
    )
    args = parser.parse_args()

    if args.location:
        try:
            url = build_url(args.location)
            result = extract_current_weather(url)
        except requests.HTTPError as e:
            print(f"HTTP error: {e}", file=sys.stderr)
            sys.exit(1)
        except requests.RequestException as e:
            print(f"Request failed: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, indent=2))
    else:
        fetch_all_and_write(Path(args.output))


if __name__ == "__main__":
    main()