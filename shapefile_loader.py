"""
shapefile_loader.py - Load and validate Bangladesh upazila shapefiles

Supports Shapefile (.shp) and GeoJSON (.geojson / .json) formats.
Reprojects to WGS84 (EPSG:4326) automatically if required.

Usage
-----
    from shapefile_loader import ShapefileLoader
    loader = ShapefileLoader("shapefiles/bgd_adm2.shp")
    gdf = loader.load()
    loader.print_summary()
    loader.validate()
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    _HAS_GEOPANDAS = True
except ImportError:
    _HAS_GEOPANDAS = False

from bangladesh_coordinates import BANGLADESH_BOUNDS, BANGLADESH_CENTER

# ---------------------------------------------------------------------------
# Default shapefile search paths (relative to repo root)
# ---------------------------------------------------------------------------
DEFAULT_SHAPEFILE_PATHS: List[str] = [
    "shapefiles/bgd_adm2.shp",
    "shapefiles/bgd_adm2.geojson",
    "shapefiles/bgd_adm2.json",
    "shapefiles/BGD_adm2.shp",
    "shapefiles/bangladesh_upazilas.shp",
    "shapefiles/bangladesh_upazilas.geojson",
    "shapefiles/gadm41_BGD_3.shp",          # GADM level-3 (upazila)
    "shapefiles/gadm41_BGD_3.geojson",
    "shapefiles/gadm36_BGD_3.shp",
    "shapefiles/gadm36_BGD_3.geojson",
]

# Common column names used by different shapefile sources for the upazila name
NAME_COLUMN_CANDIDATES: List[str] = [
    "NAME_3", "NAME_2", "ADM3_EN", "ADM2_EN",
    "upazila", "Upazila", "UPAZILA",
    "name", "Name", "NAME",
    "upazila_name", "UpazilaName",
    "adm3_en", "adm2_en",
    "GEO_NAME", "geo_name",
]

DISTRICT_COLUMN_CANDIDATES: List[str] = [
    "NAME_2", "NAME_1", "ADM2_EN", "ADM1_EN",
    "district", "District", "DISTRICT",
    "district_name", "DistrictName",
]

DIVISION_COLUMN_CANDIDATES: List[str] = [
    "NAME_1", "ADM1_EN",
    "division", "Division", "DIVISION",
    "division_name", "DivisionName",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_geopandas() -> None:
    if not _HAS_GEOPANDAS:
        raise ImportError(
            "geopandas is required: pip install geopandas"
        )


def _find_column(gdf, candidates: List[str]) -> Optional[str]:
    """Return the first column from *candidates* that exists in *gdf*."""
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


def find_shapefile(search_dir: str = ".") -> Optional[str]:
    """
    Search *search_dir* (and the standard paths) for a Bangladesh shapefile.

    Returns the first found path or None.
    """
    search_dir = Path(search_dir)
    # Check predefined paths first
    for rel_path in DEFAULT_SHAPEFILE_PATHS:
        full = search_dir / rel_path
        if full.exists():
            return str(full)
    # Recursive glob fallback
    for pattern in ["**/*.shp", "**/*.geojson", "**/*.json"]:
        for found in sorted(search_dir.glob(pattern)):
            if "bgd" in found.name.lower() or "bangladesh" in found.name.lower():
                return str(found)
    return None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ShapefileLoader:
    """
    Load, validate, and inspect a Bangladesh upazila shapefile.

    Parameters
    ----------
    path : str or Path
        Path to the shapefile (.shp) or GeoJSON file.
    name_col : str, optional
        Column containing upazila names.  Auto-detected if not provided.
    district_col : str, optional
        Column containing district names.  Auto-detected if not provided.
    division_col : str, optional
        Column containing division names.  Auto-detected if not provided.
    """

    def __init__(
        self,
        path: str | Path,
        name_col: Optional[str] = None,
        district_col: Optional[str] = None,
        division_col: Optional[str] = None,
    ):
        _require_geopandas()
        self.path = Path(path)
        self._name_col = name_col
        self._district_col = district_col
        self._division_col = division_col
        self._gdf: Optional[gpd.GeoDataFrame] = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> "gpd.GeoDataFrame":
        """
        Load the shapefile into a GeoDataFrame.

        Reprojects to WGS84 (EPSG:4326) if the CRS differs.

        Returns
        -------
        geopandas.GeoDataFrame
        """
        if not self.path.exists():
            raise FileNotFoundError(
                f"Shapefile not found: {self.path}\n"
                "Please download a Bangladesh upazila shapefile and place it in the "
                "'shapefiles/' folder.  See instructions_shapefile.md for details."
            )

        gdf = gpd.read_file(str(self.path))

        # Reproject to WGS84 if needed
        if gdf.crs is None:
            warnings.warn(
                "Shapefile has no CRS defined.  Assuming WGS84 (EPSG:4326).",
                UserWarning,
                stacklevel=2,
            )
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            print(f"Reprojecting from {gdf.crs} → EPSG:4326 (WGS84).")
            gdf = gdf.to_crs("EPSG:4326")

        # Auto-detect name columns
        if self._name_col is None:
            self._name_col = _find_column(gdf, NAME_COLUMN_CANDIDATES)
        if self._district_col is None:
            self._district_col = _find_column(gdf, DISTRICT_COLUMN_CANDIDATES)
        if self._division_col is None:
            self._division_col = _find_column(gdf, DIVISION_COLUMN_CANDIDATES)

        self._gdf = gdf
        return gdf

    @property
    def gdf(self) -> "gpd.GeoDataFrame":
        """Return the loaded GeoDataFrame (loading on first access)."""
        if self._gdf is None:
            self.load()
        return self._gdf

    # ------------------------------------------------------------------
    # Column accessors
    # ------------------------------------------------------------------

    @property
    def name_col(self) -> Optional[str]:
        """Detected upazila name column."""
        _ = self.gdf  # trigger load
        return self._name_col

    @property
    def district_col(self) -> Optional[str]:
        """Detected district name column."""
        _ = self.gdf
        return self._district_col

    @property
    def division_col(self) -> Optional[str]:
        """Detected division name column."""
        _ = self.gdf
        return self._division_col

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> dict:
        """
        Validate the shapefile and return a summary dict with:
          - total_features
          - null_geometries
          - invalid_geometries
          - out_of_bounds
          - crs
          - extent
          - name_column
        """
        gdf = self.gdf
        b = BANGLADESH_BOUNDS

        null_geom = gdf.geometry.isna().sum()
        invalid_geom = (~gdf.geometry.is_valid).sum()

        # Check bounding box of each feature
        def _centroid_in_bounds(geom) -> bool:
            if geom is None or geom.is_empty:
                return False
            c = geom.centroid
            return (
                b["min_lat"] <= c.y <= b["max_lat"]
                and b["min_lon"] <= c.x <= b["max_lon"]
            )

        out_of_bounds = (~gdf.geometry.apply(_centroid_in_bounds)).sum()

        total_bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)

        report = {
            "total_features": len(gdf),
            "null_geometries": int(null_geom),
            "invalid_geometries": int(invalid_geom),
            "out_of_bounds_centroids": int(out_of_bounds),
            "crs": str(gdf.crs),
            "extent": {
                "min_lon": round(float(total_bounds[0]), 4),
                "min_lat": round(float(total_bounds[1]), 4),
                "max_lon": round(float(total_bounds[2]), 4),
                "max_lat": round(float(total_bounds[3]), 4),
            },
            "name_column": self._name_col,
            "district_column": self._district_col,
            "division_column": self._division_col,
        }
        return report

    def check_integrity(self) -> bool:
        """Return True if the shapefile passes all integrity checks."""
        report = self.validate()
        ok = (
            report["null_geometries"] == 0
            and report["invalid_geometries"] == 0
            and report["out_of_bounds_centroids"] == 0
        )
        return ok

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def list_upazila_names(self) -> List[str]:
        """Return a sorted list of upazila names from the shapefile."""
        gdf = self.gdf
        if self._name_col is None:
            warnings.warn("No upazila name column detected.", UserWarning, stacklevel=2)
            return []
        return sorted(gdf[self._name_col].dropna().tolist())

    def print_summary(self) -> None:
        """Print a human-readable summary of the shapefile."""
        report = self.validate()
        print("=" * 60)
        print("SHAPEFILE SUMMARY")
        print("=" * 60)
        print(f"  File           : {self.path}")
        print(f"  Features       : {report['total_features']}")
        print(f"  CRS            : {report['crs']}")
        ext = report["extent"]
        print(
            f"  Extent         : lon {ext['min_lon']}–{ext['max_lon']}, "
            f"lat {ext['min_lat']}–{ext['max_lat']}"
        )
        print(f"  Name column    : {report['name_column']}")
        print(f"  District col   : {report['district_column']}")
        print(f"  Division col   : {report['division_column']}")
        print(f"  Null geometries: {report['null_geometries']}")
        print(f"  Invalid geoms  : {report['invalid_geometries']}")
        print(f"  Out-of-bounds  : {report['out_of_bounds_centroids']}")
        status = "✅ OK" if self.check_integrity() else "⚠️  Issues found"
        print(f"  Status         : {status}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot(
        self,
        output_path: Optional[str] = None,
        title: str = "Bangladesh Upazila Boundaries",
        figsize: Tuple[int, int] = (10, 12),
    ) -> "plt.Figure":
        """
        Plot the shapefile boundaries.

        Parameters
        ----------
        output_path : str, optional
            If given, saves the figure to this path (PNG, 300 DPI).
        title : str
            Figure title.
        figsize : tuple
            Figure size in inches.

        Returns
        -------
        matplotlib.figure.Figure
        """
        gdf = self.gdf
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        gdf.plot(
            ax=ax,
            color="lightblue",
            edgecolor="navy",
            linewidth=0.4,
            alpha=0.8,
        )

        ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
        ax.set_xlabel("Longitude", fontsize=11)
        ax.set_ylabel("Latitude", fontsize=11)

        # Set Bangladesh extent with small margin
        b = BANGLADESH_BOUNDS
        margin = 0.3
        ax.set_xlim(b["min_lon"] - margin, b["max_lon"] + margin)
        ax.set_ylim(b["min_lat"] - margin, b["max_lat"] + margin)

        # Feature count annotation
        ax.text(
            0.02, 0.98,
            f"Features: {len(gdf)}",
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

        ax.grid(True, alpha=0.3, linestyle="--")
        plt.tight_layout()

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig.savefig(output_path, dpi=300, bbox_inches="tight")
            print(f"Saved: {output_path}")

        return fig
