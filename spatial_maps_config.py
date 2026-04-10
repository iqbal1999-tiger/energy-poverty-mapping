"""
spatial_maps_config.py - Configuration for the dedicated spatial maps PNG folder

Defines the output directory (default: ~/spatial_maps_png/) and all settings
used exclusively for spatial choropleth maps of the Energy Poverty Index (MEPI).

This folder is completely separate from all other map-output locations in the
project (e.g. ~/map_outputs_energy_poverty/).

Usage
-----
    from spatial_maps_config import SPATIAL_OUTPUT_FOLDER, PNG_DPI
    print(SPATIAL_OUTPUT_FOLDER)   # ~/spatial_maps_png/

Customisation
-------------
    Set the environment variable MEPI_SPATIAL_MAPS_DIR to override the default:
        export MEPI_SPATIAL_MAPS_DIR=/custom/path/spatial_maps_png/

    Or edit SPATIAL_OUTPUT_FOLDER in this file directly.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Output folder – override via environment variable or edit here directly
# ---------------------------------------------------------------------------

#: Dedicated external folder for spatial map PNG files only
SPATIAL_OUTPUT_FOLDER: str = os.environ.get(
    "MEPI_SPATIAL_MAPS_DIR",
    os.path.expanduser("~/spatial_maps_png/"),
)

# ---------------------------------------------------------------------------
# Image quality settings
# ---------------------------------------------------------------------------

#: DPI for saved PNG files (300 = publication quality)
PNG_DPI: int = 300

#: Image format
PNG_FORMAT: str = "png"

#: Figure size in inches (width, height)
FIGURE_SIZE: tuple[int, int] = (16, 12)

# ---------------------------------------------------------------------------
# Color scale – poverty level bands (0 – 1 deprivation score)
# ---------------------------------------------------------------------------

#: Colormap used for choropleth maps (colorblind-friendly sequential palette)
COLORMAP: str = "RdYlGn_r"

#: Poverty classification thresholds and display labels
POVERTY_THRESHOLDS: dict[str, float] = {
    "non_poor": 0.33,
    "moderate": 0.66,
    "severe": 1.00,
}

#: Human-readable labels for each poverty band
POVERTY_LABELS: dict[str, str] = {
    "non_poor": "Non-Poor (0.00–0.33)",
    "moderate": "Moderate Poverty (0.33–0.66)",
    "severe":   "Severe Poverty (0.66–1.00)",
}

#: Colors used in the legend (aligned with POVERTY_LABELS keys)
POVERTY_COLORS: dict[str, str] = {
    "non_poor": "#1a9850",   # green
    "moderate": "#fee08b",   # yellow-amber
    "severe":   "#d73027",   # red
}

# ---------------------------------------------------------------------------
# Dimension map metadata
# ---------------------------------------------------------------------------

#: Names and titles for each MEPI dimension map
DIMENSION_MAP_CONFIGS: list[dict[str, str]] = [
    {
        "column":   "availability",
        "filename": "availability_map.png",
        "title":    "Energy Availability – Bangladesh Upazila Level",
    },
    {
        "column":   "reliability",
        "filename": "reliability_map.png",
        "title":    "Energy Reliability – Bangladesh Upazila Level",
    },
    {
        "column":   "adequacy",
        "filename": "adequacy_map.png",
        "title":    "Energy Adequacy – Bangladesh Upazila Level",
    },
    {
        "column":   "quality",
        "filename": "quality_map.png",
        "title":    "Energy Quality – Bangladesh Upazila Level",
    },
    {
        "column":   "affordability",
        "filename": "affordability_map.png",
        "title":    "Energy Affordability – Bangladesh Upazila Level",
    },
]

#: Overall MEPI map filename and title
MEPI_MAP_FILENAME: str = "mepi_spatial_map.png"
MEPI_MAP_TITLE: str = "Multidimensional Energy Poverty Index (MEPI) – Bangladesh Upazila Level"

# ---------------------------------------------------------------------------
# Shapefile configuration
# ---------------------------------------------------------------------------

#: Default search paths for Bangladesh upazila shapefile
SHAPEFILE_SEARCH_PATHS: list[str] = [
    "shapefiles/bgd_adm2.shp",
    "shapefiles/bgd_admbnda_adm2_bbs_20201113.shp",
    "shapefiles/BGD_adm2.shp",
    "shapefiles/bangladesh_upazila.shp",
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_output_folder() -> Path:
    """Return the resolved absolute Path of the spatial maps output folder."""
    return Path(SPATIAL_OUTPUT_FOLDER).expanduser().resolve()


def get_file_path(filename: str) -> str:
    """
    Return the full string path for a file inside the spatial maps folder.

    Parameters
    ----------
    filename : str
        File basename, e.g. ``"mepi_spatial_map.png"``.

    Returns
    -------
    str
    """
    return str(get_output_folder() / filename)


def validate_write_permissions() -> bool:
    """
    Create the output folder if absent and check write permissions.

    Returns
    -------
    bool
        True if the folder exists and is writable.
    """
    folder = get_output_folder()
    folder.mkdir(parents=True, exist_ok=True)
    return os.access(str(folder), os.W_OK)


def find_shapefile() -> str | None:
    """
    Search default paths for the Bangladesh upazila shapefile.

    Returns
    -------
    str or None
        Path to the first shapefile found, or None.
    """
    for path in SHAPEFILE_SEARCH_PATHS:
        if Path(path).exists():
            return path
    return None


def print_config() -> None:
    """Print the current spatial maps configuration to stdout."""
    folder = get_output_folder()
    writable = validate_write_permissions()
    shapefile = find_shapefile()

    print("=" * 60)
    print("SPATIAL MAPS PNG FOLDER CONFIGURATION")
    print("=" * 60)
    print(f"  Output folder : {folder}")
    print(f"  Writable      : {'✅' if writable else '❌'}")
    print(f"  DPI           : {PNG_DPI}")
    print(f"  Figure size   : {FIGURE_SIZE[0]}\" × {FIGURE_SIZE[1]}\"")
    print(f"  Colormap      : {COLORMAP}")
    print(f"  Shapefile     : {shapefile or '(not found – synthetic map)'}")
    print()
    print("  Maps to be generated:")
    print(f"    {MEPI_MAP_FILENAME}  ←  {MEPI_MAP_TITLE}")
    for cfg in DIMENSION_MAP_CONFIGS:
        print(f"    {cfg['filename']}")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
