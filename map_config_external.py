"""
map_config_external.py - Configuration for external map output folder

Defines the external output directory (default: ~/map_outputs_energy_poverty/)
and related settings for saving PNG/HTML map files outside the repository.

Usage
-----
    from map_config_external import EXTERNAL_OUTPUT_BASE, get_subfolder_path
    print(EXTERNAL_OUTPUT_BASE)          # ~/map_outputs_energy_poverty/
    print(get_subfolder_path("spatial_maps"))

Customisation
-------------
    Set the environment variable MEPI_MAP_OUTPUT_DIR to override the default:
        export MEPI_MAP_OUTPUT_DIR=/custom/path/map_outputs/

    Or edit EXTERNAL_OUTPUT_BASE in this file directly.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Output root – override via environment variable or edit here directly
# ---------------------------------------------------------------------------

#: Default external output directory (outside the repository)
EXTERNAL_OUTPUT_BASE: str = os.environ.get(
    "MEPI_MAP_OUTPUT_DIR",
    os.path.expanduser("~/map_outputs_energy_poverty/"),
)

# ---------------------------------------------------------------------------
# Subfolder names
# ---------------------------------------------------------------------------

#: Names of all subfolders created under EXTERNAL_OUTPUT_BASE
SUBFOLDERS: list[str] = [
    "spatial_maps",
    "regional_maps",
    "temporal_maps",
    "hotspot_maps",
    "analysis_maps",
    "interactive_maps",
]

# ---------------------------------------------------------------------------
# Image quality settings
# ---------------------------------------------------------------------------

#: DPI used when saving PNG files (300 = publication quality)
DPI: int = 300

#: Default image format for raster outputs
IMAGE_FORMAT: str = "png"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_base_path() -> Path:
    """Return the absolute Path of the external output root."""
    return Path(EXTERNAL_OUTPUT_BASE).expanduser().resolve()


def get_subfolder_path(subfolder: str) -> Path:
    """
    Return the absolute Path of a named subfolder inside the external root.

    Parameters
    ----------
    subfolder : str
        One of the names listed in SUBFOLDERS.

    Returns
    -------
    Path
    """
    return get_base_path() / subfolder


def get_file_path(subfolder: str, filename: str) -> str:
    """
    Return the string path for a file inside the external folder structure.

    Parameters
    ----------
    subfolder : str
        Target subfolder name (e.g. "spatial_maps").
    filename : str
        File basename (e.g. "mepi_spatial_map.png").

    Returns
    -------
    str
    """
    return str(get_subfolder_path(subfolder) / filename)


def validate_write_permissions() -> dict[str, bool]:
    """
    Check write permissions for each subfolder (creates them first if absent).

    Returns
    -------
    dict
        Mapping of subfolder name -> bool (True = writable).
    """
    results: dict[str, bool] = {}
    base = get_base_path()
    base.mkdir(parents=True, exist_ok=True)

    for name in SUBFOLDERS:
        folder = base / name
        folder.mkdir(parents=True, exist_ok=True)
        results[name] = os.access(str(folder), os.W_OK)

    return results


def print_config() -> None:
    """Print the current configuration to stdout."""
    base = get_base_path()
    print("=" * 60)
    print("EXTERNAL MAP OUTPUT CONFIGURATION")
    print("=" * 60)
    print(f"  Output base : {base}")
    print(f"  DPI         : {DPI}")
    print(f"  Format      : {IMAGE_FORMAT}")
    print()
    print("  Subfolders:")
    for name in SUBFOLDERS:
        print(f"    {base / name}")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
    perms = validate_write_permissions()
    print("\nWrite permission check:")
    for name, ok in perms.items():
        marker = "✅" if ok else "❌"
        print(f"  {marker} {name}/")
