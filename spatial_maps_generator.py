"""
spatial_maps_generator.py - Generate spatial choropleth maps for MEPI Bangladesh

Loads MEPI results and Bangladesh upazila shapefiles, then creates and saves
6 high-resolution PNG choropleth maps exclusively to ~/spatial_maps_png/:

  mepi_spatial_map.png      Overall MEPI score by upazila
  availability_map.png      Energy availability dimension
  reliability_map.png       Energy reliability dimension
  adequacy_map.png          Energy adequacy dimension
  quality_map.png           Energy quality dimension
  affordability_map.png     Energy affordability dimension

Each map includes:
  - Upazila boundaries (from shapefile when available)
  - Colour-coded poverty levels (green → yellow → red)
  - Title, legend, colour-bar, north arrow, and coordinate grid
  - Scale bar (km)
  - 300 DPI publication-ready quality

Usage
-----
    python spatial_maps_generator.py
    python spatial_maps_generator.py --data path/to/mepi_results.csv
    python spatial_maps_generator.py --output-dir /custom/spatial_maps_png/
    python spatial_maps_generator.py --shapefile shapefiles/bgd_adm2.shp
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    _HAS_GEOPANDAS = True
except ImportError:
    _HAS_GEOPANDAS = False

from spatial_maps_config import (
    SPATIAL_OUTPUT_FOLDER,
    PNG_DPI,
    FIGURE_SIZE,
    COLORMAP,
    POVERTY_COLORS,
    POVERTY_LABELS,
    POVERTY_THRESHOLDS,
    DIMENSION_MAP_CONFIGS,
    MEPI_MAP_FILENAME,
    MEPI_MAP_TITLE,
    find_shapefile,
)
from spatial_folder_manager import SpatialFolderManager, ensure_spatial_folder

warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _poverty_color(score: float) -> str:
    """Return a hex colour for a deprivation score in [0, 1]."""
    if score < POVERTY_THRESHOLDS["non_poor"]:
        return POVERTY_COLORS["non_poor"]
    if score < POVERTY_THRESHOLDS["moderate"]:
        return POVERTY_COLORS["moderate"]
    return POVERTY_COLORS["severe"]


def _add_north_arrow(ax: plt.Axes) -> None:
    """Add a north arrow annotation to the map axes."""
    ax.annotate(
        "N",
        xy=(0.96, 0.12),
        xytext=(0.96, 0.05),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5),
        ha="center", va="center",
        fontsize=12, fontweight="bold",
    )


def _add_legend(ax: plt.Axes) -> None:
    """Add a poverty-level colour legend to the axes."""
    patches = [
        mpatches.Patch(color=POVERTY_COLORS["non_poor"],  label=POVERTY_LABELS["non_poor"]),
        mpatches.Patch(color=POVERTY_COLORS["moderate"],  label=POVERTY_LABELS["moderate"]),
        mpatches.Patch(color=POVERTY_COLORS["severe"],    label=POVERTY_LABELS["severe"]),
    ]
    ax.legend(
        handles=patches,
        title="Poverty Level",
        loc="lower left",
        fontsize=8,
        title_fontsize=9,
        framealpha=0.9,
    )


def _add_colorbar(ax: plt.Axes, fig: plt.Figure, label: str) -> None:
    """Add a continuous colour-bar to the right of the map."""
    cmap = plt.get_cmap(COLORMAP)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0.0, vmax=1.0))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.03, pad=0.02)
    cbar.set_label(label, fontsize=9)
    cbar.set_ticks([0.0, 0.33, 0.66, 1.0])
    cbar.ax.set_yticklabels(["0.00\n(non-poor)", "0.33", "0.66", "1.00\n(severe)"], fontsize=7)


def _add_grid_and_labels(ax: plt.Axes) -> None:
    """Add coordinate grid lines to the map."""
    ax.grid(True, linestyle="--", linewidth=0.4, color="gray", alpha=0.5)
    ax.set_xlabel("Longitude (°E)", fontsize=9)
    ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.tick_params(labelsize=8)


def _add_scale_bar(ax: plt.Axes, length_km: float = 100) -> None:
    """
    Add a simple scale bar to the lower-right of the map.

    This is an approximate bar based on the Bangladesh geographic extent
    (~1° longitude ≈ 91 km at latitude 23°N).
    """
    deg_per_km = 1.0 / 91.0
    bar_len = length_km * deg_per_km
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_start = xlim[1] - bar_len - (xlim[1] - xlim[0]) * 0.03
    x_end = x_start + bar_len
    y_pos = ylim[0] + (ylim[1] - ylim[0]) * 0.04
    ax.plot([x_start, x_end], [y_pos, y_pos], color="black", linewidth=2)
    ax.text(
        (x_start + x_end) / 2, y_pos + (ylim[1] - ylim[0]) * 0.015,
        f"{int(length_km)} km",
        ha="center", va="bottom", fontsize=7, color="black",
    )


def _setup_axes(fig: plt.Figure, title: str) -> plt.Axes:
    """Create and configure a single map axes."""
    ax = fig.add_subplot(111)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    ax.set_aspect("equal")
    return ax


# ---------------------------------------------------------------------------
# Shapefile-based choropleth
# ---------------------------------------------------------------------------

def _choropleth_geopandas(
    gdf: gpd.GeoDataFrame,
    score_series: pd.Series,
    ax: plt.Axes,
    fig: plt.Figure,
    title: str,
    colorbar_label: str,
) -> None:
    """Render a choropleth on *ax* using a GeoDataFrame."""
    cmap = plt.get_cmap(COLORMAP)
    norm = mcolors.Normalize(vmin=0.0, vmax=1.0)

    gdf = gdf.copy()
    gdf["_score"] = score_series.values

    gdf.plot(
        column="_score",
        cmap=cmap,
        norm=norm,
        linewidth=0.3,
        edgecolor="white",
        missing_kwds={"color": "lightgrey", "label": "No data"},
        ax=ax,
        legend=False,
    )

    _add_colorbar(ax, fig, colorbar_label)
    _add_north_arrow(ax)
    _add_legend(ax)
    _add_grid_and_labels(ax)
    _add_scale_bar(ax)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)

    # Coordinate info
    ax.text(
        0.01, 0.01, "WGS 84 / Geographic Coordinates",
        transform=ax.transAxes, fontsize=6, color="grey",
        verticalalignment="bottom",
    )


# ---------------------------------------------------------------------------
# Scatter-plot fallback (no shapefile)
# ---------------------------------------------------------------------------

def _scatter_map(
    df: pd.DataFrame,
    score_col: str,
    ax: plt.Axes,
    fig: plt.Figure,
    title: str,
    colorbar_label: str,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> None:
    """Fallback: scatter plot using latitude/longitude coordinates."""
    try:
        from bangladesh_coordinates import UpazilaDatabase, BANGLADESH_BOUNDS
    except ImportError:
        ax.text(0.5, 0.5, "bangladesh_coordinates module not available",
                transform=ax.transAxes, ha="center", va="center", fontsize=11)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
        return

    db = UpazilaDatabase()
    rows = []
    for _, row in df.iterrows():
        name = str(row.get("upazila_name", row.get("upazila", "")))
        record = db.get_by_name(name)
        if record is None:
            matched = db.find_match(name)
            if matched:
                record = db.get_by_name(matched)
        if record and record.get("latitude") and record.get("longitude"):
            rows.append({
                "lat": record["latitude"],
                "lon": record["longitude"],
                "score": row[score_col],
            })

    if not rows:
        ax.text(0.5, 0.5, "No coordinate data available",
                transform=ax.transAxes, ha="center", va="center", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
        return

    pts = pd.DataFrame(rows)
    cmap = plt.get_cmap(COLORMAP)
    norm = mcolors.Normalize(vmin=0.0, vmax=1.0)

    sc = ax.scatter(
        pts["lon"], pts["lat"],
        c=pts["score"], cmap=cmap, norm=norm,
        s=40, alpha=0.85, edgecolors="none",
    )

    b = BANGLADESH_BOUNDS
    ax.set_xlim(b["min_lon"] - 0.3, b["max_lon"] + 0.3)
    ax.set_ylim(b["min_lat"] - 0.3, b["max_lat"] + 0.3)

    _add_colorbar(ax, fig, colorbar_label)
    _add_north_arrow(ax)
    _add_legend(ax)
    _add_grid_and_labels(ax)
    _add_scale_bar(ax)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    ax.text(
        0.01, 0.01, "WGS 84 / Geographic Coordinates (scatter approximation)",
        transform=ax.transAxes, fontsize=6, color="grey",
        verticalalignment="bottom",
    )


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------


class SpatialMapsGenerator:
    """
    Generate all 6 spatial choropleth maps and save to ~/spatial_maps_png/.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with columns: upazila_name (or upazila), mepi_score,
        availability, reliability, adequacy, quality, affordability.
    output_dir : str, optional
        Override the default output folder (~/spatial_maps_png/).
    shapefile_path : str, optional
        Path to Bangladesh upazila shapefile. Auto-detected if omitted.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        output_dir: Optional[str] = None,
        shapefile_path: Optional[str] = None,
    ) -> None:
        self.df = mepi_df.copy()
        self._mgr = ensure_spatial_folder(output_dir)
        self._shapefile_path = shapefile_path or find_shapefile()
        self._gdf: Optional[gpd.GeoDataFrame] = None

        # Normalise upazila column name
        if "upazila_name" not in self.df.columns and "upazila" in self.df.columns:
            self.df = self.df.rename(columns={"upazila": "upazila_name"})

        # Normalise dimension column names: accept both 'availability' and
        # 'Availability_score' formats produced by MEPICalculator
        self._normalise_dimension_columns()

        self._load_shapefile()

    # ------------------------------------------------------------------
    # Column normalisation
    # ------------------------------------------------------------------

    def _normalise_dimension_columns(self) -> None:
        """
        Ensure dimension score columns are accessible under their short names.

        MEPICalculator produces ``Availability_score``, ``Reliability_score``,
        etc.  The config expects ``availability``, ``reliability``, etc.
        Add aliases so both forms work.
        """
        from spatial_maps_config import DIMENSION_MAP_CONFIGS as _DIMS
        for cfg in _DIMS:
            col = cfg["column"]          # e.g. "availability"
            if col in self.df.columns:
                continue
            # Try "Availability_score" (capitalised, with _score suffix)
            candidate = f"{col.capitalize()}_score"
            if candidate in self.df.columns:
                self.df[col] = self.df[candidate]
                continue
            # Try "{col}_score" (lowercase with _score suffix)
            candidate_lower = f"{col}_score"
            if candidate_lower in self.df.columns:
                self.df[col] = self.df[candidate_lower]

    # ------------------------------------------------------------------
    # Shapefile loading
    # ------------------------------------------------------------------

    def _load_shapefile(self) -> None:
        """Attempt to load the Bangladesh upazila shapefile."""
        if not _HAS_GEOPANDAS:
            return
        if not self._shapefile_path:
            return
        try:
            self._gdf = gpd.read_file(self._shapefile_path)
            print(f"  Shapefile loaded: {self._shapefile_path} ({len(self._gdf)} features)")
        except Exception as exc:
            warnings.warn(f"Shapefile load failed ({exc}); using scatter fallback.", stacklevel=2)
            self._gdf = None

    def _merge_gdf(self, score_col: str) -> Optional[gpd.GeoDataFrame]:
        """Merge the GeoDataFrame with the MEPI score column."""
        if self._gdf is None:
            return None
        # Try common name columns in the shapefile
        name_candidates = ["NAME_2", "ADM2_EN", "ADM2_NAME", "name", "upazila"]
        shp_name_col = None
        for c in name_candidates:
            if c in self._gdf.columns:
                shp_name_col = c
                break

        if shp_name_col is None:
            warnings.warn("Cannot identify name column in shapefile; using scatter fallback.", stacklevel=2)
            return None

        merged = self._gdf.merge(
            self.df[["upazila_name", score_col]],
            left_on=shp_name_col,
            right_on="upazila_name",
            how="left",
        )
        return merged

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _render_map(self, score_col: str, title: str, colorbar_label: str) -> plt.Figure:
        """Create a single map figure for *score_col*."""
        fig = plt.figure(figsize=FIGURE_SIZE, dpi=PNG_DPI)

        merged = self._merge_gdf(score_col)
        ax = _setup_axes(fig, title)

        if merged is not None and score_col in merged.columns:
            _choropleth_geopandas(merged, merged[score_col], ax, fig, title, colorbar_label)
        else:
            _scatter_map(self.df, score_col, ax, fig, title, colorbar_label)

        plt.tight_layout()
        return fig

    def _save_map(self, fig: plt.Figure, filename: str) -> str:
        """Save *fig* as a PNG to the spatial maps folder."""
        path = self._mgr.get_path(filename)
        fig.savefig(path, dpi=PNG_DPI, bbox_inches="tight", format="png")
        plt.close(fig)
        print(f"  Saved: {path}")
        return path

    # ------------------------------------------------------------------
    # Public map methods
    # ------------------------------------------------------------------

    def create_mepi_map(self) -> str:
        """Create and save the overall MEPI spatial map."""
        print("  Generating overall MEPI spatial map ...")
        score_col = "mepi_score"
        if score_col not in self.df.columns:
            raise ValueError(f"Column '{score_col}' not found in MEPI data.")
        fig = self._render_map(score_col, MEPI_MAP_TITLE, "MEPI Deprivation Score (0–1)")
        return self._save_map(fig, MEPI_MAP_FILENAME)

    def create_dimension_maps(self) -> List[str]:
        """Create and save one map per MEPI dimension."""
        saved: List[str] = []
        for cfg in DIMENSION_MAP_CONFIGS:
            col = cfg["column"]
            if col not in self.df.columns:
                warnings.warn(f"Column '{col}' not found; skipping {cfg['filename']}.", stacklevel=2)
                continue
            print(f"  Generating {cfg['filename']} ...")
            fig = self._render_map(col, cfg["title"], f"{col.capitalize()} Deprivation Score (0–1)")
            path = self._save_map(fig, cfg["filename"])
            saved.append(path)
        return saved

    def create_all_maps(self) -> List[str]:
        """Create all 6 spatial maps and return a list of saved file paths."""
        saved: List[str] = []

        mepi_path = self.create_mepi_map()
        saved.append(mepi_path)

        dim_paths = self.create_dimension_maps()
        saved.extend(dim_paths)

        return saved


# ---------------------------------------------------------------------------
# Data loading helper
# ---------------------------------------------------------------------------

def _load_mepi_data(data_path: str) -> pd.DataFrame:
    """Load MEPI results from CSV, or calculate from sample_data.csv."""
    if data_path and Path(data_path).exists():
        print(f"   Loading MEPI data from: {data_path}")
        return pd.read_csv(data_path)

    if data_path:
        raise FileNotFoundError(
            f"Data file not found: {data_path}\n"
            "Please check the path and try again."
        )

    sample_csv = Path("sample_data.csv")
    if not sample_csv.exists():
        raise FileNotFoundError(
            "sample_data.csv not found in the current directory.\n"
            "Please provide a MEPI results CSV with --data <path> or ensure "
            "sample_data.csv exists in the working directory."
        )

    print("   No CSV specified – computing MEPI from sample_data.csv ...")
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
        description="Generate spatial MEPI choropleth maps to ~/spatial_maps_png/"
    )
    parser.add_argument(
        "--data", default="",
        help="Path to MEPI results CSV (default: uses sample_data.csv).",
    )
    parser.add_argument(
        "--output-dir", default=SPATIAL_OUTPUT_FOLDER,
        help=f"Output folder (default: {SPATIAL_OUTPUT_FOLDER}).",
    )
    parser.add_argument(
        "--shapefile", default=None,
        help="Path to Bangladesh upazila shapefile.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SPATIAL MAPS GENERATOR")
    print("=" * 60)

    df = _load_mepi_data(args.data)
    generator = SpatialMapsGenerator(
        df,
        output_dir=args.output_dir,
        shapefile_path=args.shapefile,
    )
    saved = generator.create_all_maps()

    print(f"\n✅ {len(saved)} spatial map(s) saved to:")
    print(f"   {generator._mgr.folder}")
    for p in saved:
        print(f"   ├── {Path(p).name}")


if __name__ == "__main__":
    main()
