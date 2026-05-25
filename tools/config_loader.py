"""Shared config loader for traffic-monitor-lizard.

Reads config/city.json from the project root and exposes paths and settings.
"""

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "city.json"


def _load_raw() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"City config not found: {_CONFIG_PATH}")
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# Module-level singleton so each import pays the cost once
_RAW = _load_raw()

CITY = _RAW["city"]
DISPLAY_NAME = _RAW["display_name"]
COUNTRY_CODE = _RAW["country_code"]
TIMEZONE = _RAW["timezone"]


def data_path(key: str) -> Path:
    """Return an absolute Path for a data file defined in config.data.<key>."""
    try:
        relative = _RAW["data"][key]
    except KeyError:
        raise KeyError(f"Unknown data path key: {key!r}. Available: {list(_RAW['data'])}")
    return _PROJECT_ROOT / relative
