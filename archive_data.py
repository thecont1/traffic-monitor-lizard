#!/usr/bin/env python3
"""
Standalone archival script for GitHub Actions.

This script archives old traffic data from the active file into compressed
monthly archives and keeps only the last 30 days in the active file.

Usage:
    python archive_data.py

Returns:
    Exit code 0 on success, 1 on failure
"""

import sys
from data_manager import maintain_active_file, get_archive_summary


def main():
    """Run the archival maintenance process."""
    print("=" * 60)
    print("Bangalore Traffic Data - Archival Maintenance")
    print("=" * 60)

    try:
        # Run maintenance
        result = maintain_active_file()

        print(f"\n✓ Archival complete!")
        print(f"  Active rows before: {result['active_rows_before']:,}")
        print(f"  Active rows after:  {result['active_rows_after']:,}")
        print(f"  Rows archived:      {result['archived_rows']:,}")

        if result['archived_months']:
            print(f"\n  Archive files updated:")
            for archive_file in result['archived_months']:
                print(f"    - {archive_file}")

        # Show archive summary
        summary = get_archive_summary()
        if not summary.empty:
            print(f"\n  Total archive files: {len(summary)}")
            print(f"  Total archived rows: {summary['rows'].sum():,}")
            print(f"  Total archive size:  {summary['size_kb'].sum() / 1024:.1f} MB")

        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Archival failed: {e}", file=sys.stderr)
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
