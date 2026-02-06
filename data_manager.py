"""
Data Manager Module for Bangalore Traffic Monitor

Handles the archival strategy:
- Active data file (csv-bangalore_traffic.csv) contains only last 30 days
- Archive data is stored in archive/YYYY/MM/csv-bangalore_traffic_YYYY-MM.csv.gz
- Provides utilities to load merged data (active + archive) for analysis
"""

import os
import gzip
import shutil
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


# Configuration
ACTIVE_FILE = "csv-bangalore_traffic.csv"
ARCHIVE_DIR = "archive"
KEEP_DAYS = 30
DATE_COLUMN = "date"
DATE_FORMAT = "%Y-%m-%d"


def ensure_archive_structure():
    """Create archive directory if it doesn't exist."""
    Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)


def get_archive_path(year: int, month: int) -> Path:
    """Get the archive file path for a given year/month."""
    return Path(ARCHIVE_DIR) / str(year) / f"{month:02d}" / f"csv-bangalore_traffic_{year}-{month:02d}.csv.gz"


def load_csv_file(filepath: str) -> pd.DataFrame:
    """Load a CSV file, handling potential errors."""
    try:
        return pd.read_csv(filepath)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=["date", "time", "route_code", "duration", "distance"])


def load_gzipped_csv(filepath: Path) -> pd.DataFrame:
    """Load a gzipped CSV file."""
    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            return pd.read_csv(f)
    except (FileNotFoundError, OSError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=["date", "time", "route_code", "duration", "distance"])


def parse_date(date_val) -> Optional[datetime]:
    """Parse date from various formats."""
    if pd.isna(date_val):
        return None
    if isinstance(date_val, datetime):
        return date_val
    try:
        return pd.to_datetime(date_val)
    except (ValueError, TypeError):
        return None


def get_cutoff_date() -> datetime:
    """Get the cutoff date for active data (30 days ago)."""
    return datetime.now() - timedelta(days=KEEP_DAYS)


def archive_old_data(df: pd.DataFrame, cutoff_date: datetime) -> dict:
    """
    Archive data older than cutoff_date into monthly gzip files.
    Returns a dict mapping archive paths to archived data.
    """
    ensure_archive_structure()
    
    # Parse dates
    df['date_parsed'] = df[DATE_COLUMN].apply(parse_date)
    
    # Get old data
    old_data = df[df['date_parsed'] < cutoff_date].copy()
    
    if old_data.empty:
        return {}
    
    # Group by year-month and archive
    archived = {}
    old_data['year'] = old_data['date_parsed'].dt.year
    old_data['month'] = old_data['date_parsed'].dt.month
    
    for (year, month), group in old_data.groupby(['year', 'month']):
        archive_path = get_archive_path(year, month)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Drop helper columns before saving
        save_data = group.drop(columns=['date_parsed', 'year', 'month'], errors='ignore')
        
        # If archive exists, load and merge, then re-archive
        if archive_path.exists():
            existing = load_gzipped_csv(archive_path)
            save_data = pd.concat([existing, save_data], ignore_index=True)
            # Deduplicate
            save_data = save_data.drop_duplicates(subset=['date', 'time', 'route_code'], keep='last')
        
        # Write to gzip
        save_data = save_data[["date", "time", "route_code", "duration", "distance"]]
        with gzip.open(archive_path, 'wt', encoding='utf-8', newline='') as f:
            save_data.to_csv(f, index=False)
        
        archived[str(archive_path)] = len(save_data)
    
    return archived


def get_active_data() -> pd.DataFrame:
    """Load only the active data (last 30 days)."""
    return load_csv_file(ACTIVE_FILE)


def get_all_archived_data(start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Load all archived data, optionally filtered by date range.
    
    Args:
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)
    """
    ensure_archive_structure()
    
    all_data = []
    
    # Find all archive files
    pattern = Path(ARCHIVE_DIR) / "*" / "*" / "csv-bangalore_traffic_*.csv.gz"
    archive_files = glob.glob(str(pattern))
    
    for archive_file in sorted(archive_files):
        df = load_gzipped_csv(Path(archive_file))
        if not df.empty:
            all_data.append(df)
    
    if not all_data:
        return pd.DataFrame(columns=["date", "time", "route_code", "duration", "distance"])
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # Apply date filters if provided
    if start_date is not None or end_date is not None:
        combined['date_parsed'] = combined[DATE_COLUMN].apply(parse_date)
        
        if start_date is not None:
            combined = combined[combined['date_parsed'] >= start_date]
        if end_date is not None:
            combined = combined[combined['date_parsed'] <= end_date]
        
        combined = combined.drop(columns=['date_parsed'], errors='ignore')
    
    return combined


def get_merged_data(start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    include_active: bool = True) -> pd.DataFrame:
    """
    Get merged data from both active file and archives.
    
    Args:
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)
        include_active: Whether to include active data (default: True)
    
    Returns:
        DataFrame with all matching data, deduplicated
    """
    data_parts = []
    
    # Load archived data
    archived = get_all_archived_data(start_date, end_date)
    if not archived.empty:
        data_parts.append(archived)
    
    # Load active data if requested
    if include_active:
        active = get_active_data()
        if not active.empty:
            # Apply date filters to active data too
            if start_date is not None or end_date is not None:
                active['date_parsed'] = active[DATE_COLUMN].apply(parse_date)
                if start_date is not None:
                    active = active[active['date_parsed'] >= start_date]
                if end_date is not None:
                    active = active[active['date_parsed'] <= end_date]
                active = active.drop(columns=['date_parsed'], errors='ignore')
            data_parts.append(active)
    
    if not data_parts:
        return pd.DataFrame(columns=["date", "time", "route_code", "duration", "distance"])
    
    # Merge and deduplicate
    merged = pd.concat(data_parts, ignore_index=True)
    merged = merged.drop_duplicates(subset=['date', 'time', 'route_code'], keep='last')
    
    # Sort by date and time
    merged = merged.sort_values(['date', 'time', 'route_code']).reset_index(drop=True)
    
    return merged


def maintain_active_file() -> dict:
    """
    Main maintenance function:
    1. Load current active data
    2. Archive data older than 30 days
    3. Keep only last 30 days in active file
    4. Save updated active file
    
    Returns:
        Dict with summary of actions taken
    """
    result = {
        'active_rows_before': 0,
        'active_rows_after': 0,
        'archived_rows': 0,
        'archived_months': [],
        'error': None
    }
    
    try:
        # Load current data
        df = get_active_data()
        result['active_rows_before'] = len(df)
        
        if df.empty:
            return result
        
        # Parse dates
        df['date_parsed'] = df[DATE_COLUMN].apply(parse_date)
        
        # Get cutoff date
        cutoff = get_cutoff_date()
        
        # Archive old data
        archived = archive_old_data(df, cutoff)
        result['archived_months'] = list(archived.keys())
        result['archived_rows'] = sum(archived.values())
        
        # Keep only recent data
        recent_mask = df['date_parsed'] >= cutoff
        recent_data = df[recent_mask].copy()
        
        # Clean up helper column
        recent_data = recent_data.drop(columns=['date_parsed'], errors='ignore')
        
        # Deduplicate
        recent_data = recent_data.drop_duplicates(subset=['date', 'time', 'route_code'], keep='last')
        
        # Save back to active file
        recent_data = recent_data[["date", "time", "route_code", "duration", "distance"]]
        recent_data.to_csv(ACTIVE_FILE, index=False)
        result['active_rows_after'] = len(recent_data)
        
    except Exception as e:
        result['error'] = str(e)
        raise
    
    return result


def get_archive_summary() -> pd.DataFrame:
    """Get a summary of all archived data."""
    ensure_archive_structure()
    
    summaries = []
    pattern = Path(ARCHIVE_DIR) / "*" / "*" / "csv-bangalore_traffic_*.csv.gz"
    archive_files = sorted(glob.glob(str(pattern)))
    
    for archive_file in archive_files:
        path = Path(archive_file)
        df = load_gzipped_csv(path)
        
        if not df.empty and 'date' in df.columns:
            dates = pd.to_datetime(df['date'], errors='coerce')
            summaries.append({
                'archive_file': str(path.relative_to(ARCHIVE_DIR)),
                'rows': len(df),
                'size_kb': path.stat().st_size / 1024,
                'date_min': dates.min(),
                'date_max': dates.max()
            })
    
    if summaries:
        return pd.DataFrame(summaries)
    return pd.DataFrame(columns=['archive_file', 'rows', 'size_kb', 'date_min', 'date_max'])


if __name__ == "__main__":
    # Run maintenance when called directly
    print("Running data archival maintenance...")
    result = maintain_active_file()
    print(f"Active rows before: {result['active_rows_before']}")
    print(f"Active rows after: {result['active_rows_after']}")
    print(f"Archived rows: {result['archived_rows']}")
    print(f"Archive files updated: {result['archived_months']}")
    if result['error']:
        print(f"Error: {result['error']}")
