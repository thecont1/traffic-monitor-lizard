# Data Archival Migration Guide

## Overview

The traffic monitoring system now uses a data archival strategy to keep the active data file under GitHub's size limits:

- **Active data** (`csv-bangalore_traffic.csv`): Contains only the last 30 days
- **Archive data** (`archive/YYYY/MM/*.csv.gz`): Compressed monthly archives of older data

## Updated Files

### 1. New Files Created
- **`data_manager.py`**: Core module for managing active/archived data
  - `get_active_data()`: Load only active (last 30 days) data
  - `get_merged_data()`: Load combined active + archive data
  - `maintain_active_file()`: Archive old data and keep active file small
  - `get_archive_summary()`: Get summary of archived data

- **`archive_data.py`**: Standalone script for GitHub Actions

### 2. Modified Files
- **`traffic_snapshot.py`**: Now uses data_manager, runs archival maintenance after each snapshot
- **`traffic_snapshot.ipynb`**: Updated to import and use data_manager
- **`.github/workflows/traffic_snapshot.yml`**: Added archival step

## For traffic_visual.ipynb

Since the visualization notebook couldn't be edited directly due to file size, here's what you need to change:

### Cell 1: Add imports
Add to your imports cell:
```python
from data_manager import get_merged_data, get_active_data
```

### Where you load data: Replace
**OLD:**
```python
df = pd.read_csv("csv-bangalore_traffic.csv")
```

**NEW (for full historical analysis):**
```python
df = get_merged_data()  # Loads active + all archives
```

**OR (for recent data only):**
```python
df = get_active_data()  # Loads only last 30 days
```

### For date-filtered analysis:
```python
from datetime import datetime, timedelta

# Get last 90 days including archives
start_date = datetime.now() - timedelta(days=90)
df = get_merged_data(start_date=start_date)
```

## Running Initial Archive

To handle the existing large `csv-bangalore_traffic.csv`:

```bash
python archive_data.py
```

This will:
1. Archive all data older than 30 days into `archive/YYYY/MM/` structure
2. Compress archives with gzip
3. Keep only last 30 days in the active file
4. Show a summary of what was archived

## Archive Structure

```
archive/
├── 2024/
│   ├── 09/
│   │   └── csv-bangalore_traffic_2024-09.csv.gz
│   └── 10/
│       └── csv-bangalore_traffic_2024-10.csv.gz
└── 2025/
    └── 01/
        └── csv-bangalore_traffic_2025-01.csv.gz
```

## GitHub Actions Workflow

The workflow now:
1. Runs the traffic snapshot
2. **NEW**: Runs archival maintenance
3. Commits both the active file and any new archive files

This happens automatically every hour, keeping the active file under 30 days.
