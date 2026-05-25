# Bangalore Traffic Monitor

The data engine behind [TraffiCOracle](https://github.com/thecont1/TraffiCOracle). This project build a dataset of live hyperlocal traffic and weather readings, and provides a full toolkit for analysing and visualising the results.

It is designed for **civic technologists**, **urban planners**, **data journalists**, and **researchers** who want a transparent, reproducible pipeline for understanding how a city (Bangalore, for now) moves, how traffic patterns evolve, what factors influence travel times, and the characteristics of roads and routes.

---

## What it does

Every 20 minutes of every hour of every day, an automated script asks Google Maps to estimate how long it would take to go from Point A to Point B, for each from a set of [pre-determined routes](https://github.com/thecont1/blr-traffic-monitor/blob/main/data/csv-routes-bangalore.csv), and records the result. Over weeks and months, this builds up a rich dataset. The project also pulls in local weather data so you can later ask whether rain or heat correlate with traffic congestion.

Because everything is stored as plain CSV files in a public GitHub repository, the data is **open** (anyone can download and verify it), **versioned** (every commit is a snapshot in time) and **reusable** (the companion dashboard TraffiCOracle reads these files directly).

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Data](#data)
- [How it works](#how-it-works)
- [Automation & Reliability](#automation--reliability)
- [Tips & Troubleshooting](#tips--troubleshooting)
- [License](#license)

---

## Features

- **Hands-free data collection**  
  A single command launches a headless Chrome browser, visits Google Maps for every configured route, and outputs clean CSV rows. No API keys, no paid services. This repo will always be ready for you with data less than 20 minutes old.

- **30+ built-in visualisations**  
  Hourly heatmaps, time-series decomposition, radar charts, ranking animations, control charts for anomaly detection, travel-time reliability curves, and forecast plots with confidence intervals.

- **Interactive notebooks**  
  Two Jupyter notebooks let you explore the data without writing scripts from scratch: one for quick visual exploration, one for comprehensive worked examples.

- **R³S² scoring**  
  The proprietary *Rolling Relative Route Scoring System* ranks routes by reliability and speed relative to each other. The system is validated with correlation tests, sensitivity-to-outliers checks, and stability-over-time analysis to certify trustworthiness.

- **Statistical rigour**  
  Built-in tests for normality, stationarity, autocorrelation, and variance homogeneity. Outlier detection with IQR, Z-score, or isolation-forest methods.

- **Weather correlation**  
  Each traffic snapshot is paired with temperature, "real feel", humidity, rain status, and air-quality index from a local weather station. Stored alongside the route data for later analysis.

---

## Quick Start

### Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Python** | Runtime (3.13+) | [python.org](https://python.org) or `brew install python` |
| **uv** | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Chrome** | Browser for scraping | [google.com/chrome](https://www.google.com/chrome/) |

### 1. Install dependencies

```bash
git clone https://github.com/thecont1/blr-traffic-monitor.git 
cd blr-traffic-monitor
uv sync
```

`uv sync` reads `pyproject.toml` and installs everything in one step.

### 2. Collect fresh traffic data

```bash
uv run python tools/traffic_snapshot.py
```

This will:
- Launch a headless Chrome window
- Query Google Maps for each route
- Print CSV rows to your terminal
- Print a one-line commit summary as the last line

To **append** the output to the historical dataset:

```bash
uv run python tools/traffic_snapshot.py >> data/csv-traffic-bangalore.csv
```

### 3. Explore the data in a notebook

```bash
# Quick visual exploration
uv run jupyter notebook traffic_visual.ipynb

# Comprehensive analysis examples
uv run jupyter notebook traffic_analysis_examples.ipynb
```

### 4. Run the tests

```bash
uv run pytest tests/
```

### Useful commands

```bash
uv run python tools/weather.py --json        # Collect a fresh weather snapshot
uv run python tools/fix_timestamps.py --apply # Deduplicate the traffic CSV
uv run pytest tests/ --cov=. --cov-report=html # Run tests with coverage
```

---

## Data

### Files overview

| File | Purpose |
|------|---------|
| `data/csv-traffic-bangalore.csv` | All timestamped traffic readings |
| `data/csv-routes-bangalore.csv` | Route definitions and display metadata |
| `data/csv-locations_*.csv` | Location names mapped to Plus Codes |
| `data/csv-weather-snapshot.csv` | Latest weather snapshot for each route |

### Traffic data columns

| Column | Example | Meaning |
|--------|---------|---------|
| `date` | `2025-09-25` | Calendar date of collection |
| `time` | `14:25` | Collection time (24-hour, local IST) |
| `route_code` | `2HM2+P8\|XJV5+RG` | Origin and destination Plus Codes joined by `\|` |
| `duration` | `32` | Travel time in minutes |
| `distance` | `11.0` | Route distance in kilometres |
| `temp` | `24` | Temperature in °C |
| `realfeel` | `23` | "Real feel" temperature in °C |
| `humidity` | `77` | Relative humidity percentage |
| `rsi_flag` | *(empty or rain description)* | Rain / precipitation status |
| `aqi` | `96` | Air quality index value |

### Routes data columns

| Column | Example | Meaning |
|--------|---------|---------|
| `route_code` | `XJG4+7J\|5PX4+HQ` | Same identifier used in the traffic file |
| `label_full` | `MG Road Metro Station → Kempegowda International Airport` | Human-readable long name |
| `label_short` | `Airport Expy` | Short display label |
| `map_link` | `https://maps.app.goo.gl/...` | Direct Google Maps link |
| `accuweather_station` | `shantala-nagar/3352203` | Weather station used for this route |

### Data quality

Before rows are written, the scraper already performs basic sanity checks:

- Missing or unparsable durations are discarded
- Distances are stripped of the `" km"` suffix and converted to numbers
- Any row lacking both a valid distance and a valid duration is dropped

The companion Python module `data_utils.py` adds further cleaning when you load the data for analysis:

- Removes exact duplicates (same route, same day, same hour, same duration and distance)
- Computes `avg_speed` from `distance / (duration / 60)`
- Adds temporal features: `timestamp`, `day_of_week`, `is_weekend`, `time_category`

---

## How it works

### The pipeline

```
cron-job.org  ──►  Cloudflare Worker  ──►  GitHub Actions
 (twice/hour)        (secret check)         (ubuntu runner)
                                              │
                                              ▼
                                        Chrome + Selenium
                                              │
                                              ▼
                                        Google Maps queries
                                              │
                                              ▼
                                        CSV rows appended
                                              │
                                              ▼
                                        Commit to GitHub
                                              │
                                              ▼
                              TraffiCOracle reads the public CSV
```

1. **Scheduling** — `cron-job.org` hits a Cloudflare Worker twice every hour.
2. **Validation** — the Worker checks a shared secret, then dispatches the GitHub Actions workflow.
3. **Scraping** — a GitHub Actions runner installs `uv`, launches Chrome, and runs `traffic_snapshot.py`.
4. **Storage** — new rows are appended to `csv-traffic-bangalore.csv` and committed.
5. **Consumption** — TraffiCOracle (or your own script) fetches the updated CSV from GitHub's raw-content URL.

### Deduplication schedule

A second cron job triggers a deduplication script once per day at 03:00 IST to remove duplicate readings, keeping one row per hour per route. This is so that the current day's analysis can benefit from a higher frequency of data points while the larger dataset does not get inflated; the deduplication process is idempotent. It commits the cleaned file with a commit message stating how many records were removed (or `0` if none).

---

## Tips & Troubleshooting

| Problem | What to try |
|---------|-------------|
| Chrome does not launch | Make sure Google Chrome is installed and up to date. The script uses your existing Chrome, not a bundled one. |
| Google Maps blocks the scraper | The script uses a realistic user-agent and headless mode. If blocked, wait a few minutes and retry. |
| `ModuleNotFoundError` on import | Run `uv sync` again to ensure all dependency groups are installed. |
| Jupyter notebook kernel not found | Launch with `uv run jupyter notebook` so the virtual-environment kernel is available. |
| Missing weather columns in traffic CSV | Weather is collected separately by `tools/weather.py`. It is not automatically merged; you can join on `route_code` and timestamp if needed. |
| Data looks sparse for some hours | Check `tools/fix_timestamps.py --apply` to see if duplicates were recently removed. Some hours may genuinely have no data if the scraper encountered a network error. |

---

## License

MIT
