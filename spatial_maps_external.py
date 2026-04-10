"""
spatial_maps_external.py - Generate spatial MEPI maps and save to external folder

Loads MEPI results, loads Bangladesh shapefiles (if available), and creates
choropleth maps saved to the external ``spatial_maps/`` subfolder.

Maps produced
-------------
  mepi_spatial_map.png             Overall MEPI index – all 492 upazilas
  availability_map.png             Energy availability dimension
  reliability_map.png              Energy reliability dimension
  adequacy_map.png                 Energy adequacy dimension
  quality_map.png                  Energy quality dimension
  affordability_map.png            Energy affordability dimension

Usage
-----
    python spatial_maps_external.py
    python spatial_maps_external.py --data path/to/mepi_results.csv
    python spatial_maps_external.py --output-dir /custom/output/path/
"""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from external_folder_manager import ExternalFolderManager, ensure_external_folders
from map_config_external import DPI, EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)

# Maps each dimension name to its target filename in spatial_maps/
_DIMENSION_FILENAMES: Dict[str, str] = {
    "availability":  "availability_map.png",
    "reliability":   "reliability_map.png",
    "adequacy":      "adequacy_map.png",
    "quality":       "quality_map.png",
    "affordability": "affordability_map.png",
}


# ---------------------------------------------------------------------------
# Spatial map generation
# ---------------------------------------------------------------------------

class SpatialMapsExternal:
    """
    Generate spatial MEPI maps and save to the external ``spatial_maps/`` folder.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with columns: upazila_name, mepi_score, [dimension_score cols].
    base_dir : str, optional
        External output root (defaults to EXTERNAL_OUTPUT_BASE).
    shapefile_path : str, optional
        Path to Bangladesh upazila shapefile.  Auto-detected if omitted.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        base_dir: Optional[str] = None,
        shapefile_path: Optional[str] = None,
    ) -> None:
        self.df = mepi_df
        self._mgr = ensure_external_folders(base_dir)
        self._shapefile_path = shapefile_path

        import matplotlib
        matplotlib.use("Agg")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _out(self, filename: str) -> str:
        """Return the full path for a file in the spatial_maps subfolder."""
        return self._mgr.get_path("spatial_maps", filename)

    def _build_mapper(self):
        """Instantiate OrganisedSpatialMapper targeting the external folder."""
        from updated_correct_spatial_mapping import OrganisedSpatialMapper
        return OrganisedSpatialMapper(
            self.df,
            base_dir=str(self._mgr.base_dir),
            shapefile_path=self._shapefile_path,
        )

    # ------------------------------------------------------------------
    # Public map methods
    # ------------------------------------------------------------------

    def create_mepi_map(self) -> Optional[str]:
        """Create and save the overall MEPI spatial map."""
        try:
            mapper = self._build_mapper()
            path = self._out("mepi_spatial_map.png")
            saved = mapper.create_mepi_map(output_path=path)
            print(f"  Saved: {saved}")
            return saved
        except Exception as exc:
            warnings.warn(f"mepi_spatial_map failed: {exc}", stacklevel=2)
            return None

    def create_dimension_maps(self) -> List[str]:
        """Create one map per MEPI dimension and save them to spatial_maps/."""
        saved: List[str] = []
        try:
            mapper = self._build_mapper()
            # create_dimension_maps saves to output_dir with naming
            # dimension_{dim}_map.png; we write directly to spatial_maps/ dir
            spatial_dir = str(self._mgr.get_subfolder("spatial_maps"))
            dim_paths = mapper.create_dimension_maps(output_dir=spatial_dir)
            # Rename files to match the expected convention (e.g. availability_map.png)
            for p in dim_paths:
                src = Path(p)
                if not src.exists():
                    continue
                stem = src.stem  # e.g. "dimension_availability_map"
                for dim, target_name in _DIMENSION_FILENAMES.items():
                    if dim in stem:
                        dest = src.parent / target_name
                        src.rename(dest)
                        print(f"  Saved: {dest}")
                        saved.append(str(dest))
                        break
                else:
                    print(f"  Saved: {src}")
                    saved.append(str(src))
        except Exception as exc:
            warnings.warn(f"Dimension maps failed: {exc}", stacklevel=2)

        return saved

    def create_all_maps(self) -> List[str]:
        """Create all spatial maps and return list of saved paths."""
        saved: List[str] = []

        print("  Creating MEPI spatial map...")
        p = self.create_mepi_map()
        if p:
            saved.append(p)

        print("  Creating dimension maps...")
        saved.extend(self.create_dimension_maps())

        return saved


# ---------------------------------------------------------------------------
# Data loading helper
# ---------------------------------------------------------------------------

def _load_data(data_path: str) -> pd.DataFrame:
    if data_path and Path(data_path).exists():
        return pd.read_csv(data_path)
    from data_utils import load_data, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator
    df = load_data("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    return MEPICalculator().calculate(df)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate spatial MEPI maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    parser.add_argument("--shapefile", default=None, help="Path to Bangladesh shapefile.")
    args = parser.parse_args()

    print("=" * 60)
    print("SPATIAL MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)
    mapper = SpatialMapsExternal(
        results,
        base_dir=args.output_dir,
        shapefile_path=args.shapefile,
    )
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} spatial map(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('spatial_maps')}")


if __name__ == "__main__":
    main()
