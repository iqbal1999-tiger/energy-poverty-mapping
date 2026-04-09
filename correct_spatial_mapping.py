"""
correct_spatial_mapping.py - Correct choropleth maps for Bangladesh MEPI

Creates publication-quality PNG maps showing MEPI scores and dimension
scores at the upazila level.  Requires either:
  a) A Bangladesh upazila shapefile in the ``shapefiles/`` directory, OR
  b) Falls back to a scatter-plot based map using centroid coordinates.

Usage
-----
    from correct_spatial_mapping import SpatialMapper
    mapper = SpatialMapper(mepi_df)
    mapper.create_mepi_map("map_outputs/spatial_mepi_map.png")
    mapper.create_dimension_maps("map_outputs/")
    mapper.create_hotspot_map("map_outputs/hotspot_map.png")
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    _HAS_GEOPANDAS = True
except ImportError:
    _HAS_GEOPANDAS = False

from bangladesh_coordinates import (
    BANGLADESH_BOUNDS,
    BANGLADESH_CENTER,
    UpazilaDatabase,
    get_database,
)
from config import DIMENSIONS

# ---------------------------------------------------------------------------
# Color scheme matching poverty classification
# ---------------------------------------------------------------------------
POVERTY_COLORS = {
    "Non-Poor":          "#2ecc71",   # green
    "Moderately Poor":   "#f39c12",   # orange
    "Severely Poor":     "#e74c3c",   # red
}

# Continuous colormap: green (low) → yellow → orange → red (high)
MEPI_CMAP = LinearSegmentedColormap.from_list(
    "mepi",
    ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
    N=256,
)

DIMENSION_CMAPS = {
    "Availability":   "YlOrRd",
    "Reliability":    "YlOrBr",
    "Adequacy":       "PuRd",
    "Quality":        "RdPu",
    "Affordability":  "OrRd",
}

OUTPUT_DIR = "map_outputs"
DPI = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _add_colorbar(ax, cmap, vmin: float, vmax: float, label: str, fig) -> None:
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.03, pad=0.02)
    cbar.set_label(label, fontsize=10)


def _add_north_arrow(ax) -> None:
    """Add a simple north arrow to an axes."""
    ax.annotate(
        "N",
        xy=(0.97, 0.12),
        xytext=(0.97, 0.05),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5),
        ha="center", va="center",
        fontsize=12, fontweight="bold",
    )


def _add_legend_patches(ax, labels_colors: Dict[str, str], title: str = "") -> None:
    patches = [
        mpatches.Patch(color=c, label=l)
        for l, c in labels_colors.items()
    ]
    ax.legend(
        handles=patches,
        title=title,
        loc="lower left",
        fontsize=8,
        title_fontsize=9,
        framealpha=0.9,
    )


def _set_bangladesh_extent(ax, margin: float = 0.3) -> None:
    b = BANGLADESH_BOUNDS
    ax.set_xlim(b["min_lon"] - margin, b["max_lon"] + margin)
    ax.set_ylim(b["min_lat"] - margin, b["max_lat"] + margin)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SpatialMapper:
    """
    Create choropleth and scatter maps of MEPI results.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results (output of MEPICalculator.calculate()).
    shapefile_path : str, optional
        Path to Bangladesh upazila shapefile.  Auto-detected if not given.
    name_col : str
        Column in mepi_df containing upazila names.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        shapefile_path: Optional[str] = None,
        name_col: str = "upazila_name",
    ):
        self.df = mepi_df.copy()
        self.name_col = name_col
        self._db = get_database()
        self._gdf: Optional["gpd.GeoDataFrame"] = None
        self._shp_name_col: Optional[str] = None
        self._merged: Optional["gpd.GeoDataFrame"] = None

        # Try to load shapefile
        if _HAS_GEOPANDAS:
            self._try_load_shapefile(shapefile_path)

        # Attach centroid coordinates from database (used for scatter fallback)
        self._attach_coordinates()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _try_load_shapefile(self, path: Optional[str]) -> None:
        from shapefile_loader import ShapefileLoader, find_shapefile

        if path is None:
            path = find_shapefile(".")

        if path is None or not Path(path).exists():
            warnings.warn(
                "Bangladesh shapefile not found.  Using coordinate-based scatter maps "
                "instead of choropleth maps.  Download a shapefile and place it in "
                "'shapefiles/' for proper choropleth maps.  "
                "See instructions_shapefile.md for details.",
                UserWarning,
                stacklevel=3,
            )
            return

        try:
            loader = ShapefileLoader(path)
            self._gdf = loader.load()
            self._shp_name_col = loader.name_col
            print(f"Shapefile loaded: {path} ({len(self._gdf)} features)")
        except Exception as exc:
            warnings.warn(
                f"Failed to load shapefile ({exc}).  Falling back to scatter maps.",
                UserWarning,
                stacklevel=3,
            )

    def _attach_coordinates(self) -> None:
        """Add lat/lon centroid columns to the MEPI DataFrame via the database."""
        if "lat" in self.df.columns and "lon" in self.df.columns:
            return

        lats, lons = [], []
        for name in self.df[self.name_col]:
            record = self._db.get_by_name(str(name))
            if record:
                lats.append(record["lat"])
                lons.append(record["lon"])
            else:
                lats.append(np.nan)
                lons.append(np.nan)

        self.df["lat"] = lats
        self.df["lon"] = lons

    def _merge_with_shapefile(self) -> Optional["gpd.GeoDataFrame"]:
        """Merge MEPI data with the shapefile GeoDataFrame."""
        if self._gdf is None or self._shp_name_col is None:
            return None
        if self._merged is not None:
            return self._merged

        from upazila_validator import UpazilaValidator
        validator = UpazilaValidator(
            self.df,
            self._gdf,
            mepi_name_col=self.name_col,
            shapefile_name_col=self._shp_name_col,
        )
        validator.validate()
        merged = validator.merge(how="left")
        self._merged = merged
        return merged

    # ------------------------------------------------------------------
    # Map creation helpers
    # ------------------------------------------------------------------

    def _setup_map_axes(
        self,
        figsize: Tuple[int, int] = (12, 14),
        title: str = "",
    ) -> Tuple["plt.Figure", "plt.Axes"]:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax.set_title(title, fontsize=15, fontweight="bold", pad=14)
        ax.set_xlabel("Longitude", fontsize=11)
        ax.set_ylabel("Latitude", fontsize=11)
        ax.grid(True, alpha=0.25, linestyle="--")
        _set_bangladesh_extent(ax)
        return fig, ax

    def _choropleth(
        self,
        ax,
        fig,
        score_col: str,
        cmap,
        vmin: float = 0.0,
        vmax: float = 1.0,
        label: str = "Score",
        missing_color: str = "#cccccc",
    ) -> None:
        """Draw a choropleth layer on *ax* using the merged GeoDataFrame."""
        merged = self._merge_with_shapefile()

        if merged is not None and hasattr(merged, "geometry"):
            # True choropleth
            merged_no_data = merged[merged[score_col].isna()]
            if len(merged_no_data):
                merged_no_data.plot(
                    ax=ax, color=missing_color, edgecolor="grey",
                    linewidth=0.3, label="No data",
                )

            merged_with_data = merged[merged[score_col].notna()]
            if len(merged_with_data):
                merged_with_data.plot(
                    ax=ax,
                    column=score_col,
                    cmap=cmap,
                    vmin=vmin,
                    vmax=vmax,
                    edgecolor="white",
                    linewidth=0.3,
                    legend=False,
                )

            # Draw full outline
            self._gdf.boundary.plot(
                ax=ax, color="grey", linewidth=0.2, alpha=0.5
            )
        else:
            # Scatter fallback
            self._scatter_layer(ax, fig, score_col, cmap, vmin, vmax, label)

        _add_colorbar(ax, cmap, vmin, vmax, label, fig)

    def _scatter_layer(
        self,
        ax,
        fig,
        score_col: str,
        cmap,
        vmin: float = 0.0,
        vmax: float = 1.0,
        label: str = "Score",
    ) -> None:
        """Draw scatter dots on *ax* when no shapefile is available."""
        df = self.df.dropna(subset=["lat", "lon", score_col])
        sc = ax.scatter(
            df["lon"],
            df["lat"],
            c=df[score_col],
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            s=80,
            edgecolors="grey",
            linewidth=0.4,
            alpha=0.85,
            zorder=5,
        )

    def _annotate_scatter_note(self, ax) -> None:
        ax.text(
            0.5, 0.01,
            "ℹ Scatter plot (centroid dots) – shapefile not found. "
            "See instructions_shapefile.md.",
            transform=ax.transAxes,
            fontsize=7.5,
            ha="center",
            color="grey",
            style="italic",
        )

    # ------------------------------------------------------------------
    # Public map creation methods
    # ------------------------------------------------------------------

    def create_mepi_map(
        self,
        output_path: str = "map_outputs/spatial_mepi_map.png",
        title: str = "Multidimensional Energy Poverty Index (MEPI)\nBangladesh – Upazila Level",
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """
        Create the main MEPI choropleth map.

        Parameters
        ----------
        output_path : str
            File path for the output PNG.
        title : str
            Map title.
        figsize : tuple
            Figure size in inches.

        Returns
        -------
        str
            Absolute path to the saved PNG.
        """
        _ensure_dir(os.path.dirname(output_path) or ".")
        fig, ax = self._setup_map_axes(figsize=figsize, title=title)

        score_col = "mepi_score"
        self._choropleth(
            ax, fig,
            score_col=score_col,
            cmap=MEPI_CMAP,
            vmin=0.0,
            vmax=1.0,
            label="MEPI Score (0 = no poverty, 1 = max poverty)",
        )

        # Classification legend
        _add_legend_patches(
            ax, POVERTY_COLORS, title="Energy Poverty Category"
        )

        _add_north_arrow(ax)

        # Scatter notes if shapefile missing
        if self._gdf is None:
            self._annotate_scatter_note(ax)

        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_dimension_maps(
        self,
        output_dir: str = "map_outputs",
        figsize: Tuple[int, int] = (11, 13),
    ) -> List[str]:
        """
        Create one map per MEPI dimension.

        Returns
        -------
        list of str
            Paths to saved PNG files.
        """
        _ensure_dir(output_dir)
        saved_paths = []

        for dim in DIMENSIONS:
            score_col = f"{dim}_score"
            if score_col not in self.df.columns:
                warnings.warn(
                    f"Column '{score_col}' not found; skipping {dim} map.",
                    UserWarning,
                    stacklevel=2,
                )
                continue

            output_path = os.path.join(
                output_dir,
                f"dimension_{dim.lower()}_map.png",
            )
            cmap = DIMENSION_CMAPS.get(dim, "YlOrRd")
            title = (
                f"{dim} Dimension Score\n"
                "Bangladesh Energy Poverty – Upazila Level"
            )

            fig, ax = self._setup_map_axes(figsize=figsize, title=title)
            self._choropleth(
                ax, fig,
                score_col=score_col,
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
                label=f"{dim} Score (0 = no deprivation, 1 = max deprivation)",
            )

            if self._gdf is None:
                self._annotate_scatter_note(ax)

            _add_north_arrow(ax)
            plt.tight_layout()
            fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {output_path}")
            saved_paths.append(os.path.abspath(output_path))

        return saved_paths

    def create_hotspot_map(
        self,
        output_path: str = "map_outputs/hotspot_map.png",
        threshold: float = 0.66,
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """
        Create a map highlighting hotspot (severely energy-poor) upazilas.

        Parameters
        ----------
        output_path : str
        threshold : float
            MEPI score above which an upazila is considered a hotspot.

        Returns
        -------
        str
        """
        _ensure_dir(os.path.dirname(output_path) or ".")

        title = (
            f"Energy Poverty Hotspots (MEPI ≥ {threshold:.2f})\n"
            "Bangladesh – Upazila Level"
        )
        fig, ax = self._setup_map_axes(figsize=figsize, title=title)

        df = self.df.copy()
        df["is_hotspot"] = df["mepi_score"] >= threshold

        merged = self._merge_with_shapefile()

        if merged is not None and hasattr(merged, "geometry"):
            # Background
            self._gdf.plot(
                ax=ax,
                color="#f0f0f0",
                edgecolor="grey",
                linewidth=0.3,
                alpha=0.6,
            )

            # Hotspots
            if "is_hotspot" in merged.columns:
                merged[merged["is_hotspot"] == True].plot(
                    ax=ax, color="#e74c3c", edgecolor="darkred",
                    linewidth=0.5, alpha=0.9, label="Hotspot (Severely Poor)",
                )
                merged[merged["is_hotspot"] == False].plot(
                    ax=ax, color="#2ecc71", edgecolor="grey",
                    linewidth=0.2, alpha=0.5, label="Not a Hotspot",
                )
            else:
                warnings.warn("is_hotspot column missing after merge.", UserWarning, stacklevel=2)

        else:
            # Scatter fallback
            df_valid = df.dropna(subset=["lat", "lon"])
            hot = df_valid[df_valid["is_hotspot"]]
            not_hot = df_valid[~df_valid["is_hotspot"]]

            if len(not_hot):
                ax.scatter(
                    not_hot["lon"], not_hot["lat"],
                    color="#2ecc71", s=70, edgecolors="grey",
                    linewidth=0.4, alpha=0.7, label="Not a Hotspot",
                )
            if len(hot):
                ax.scatter(
                    hot["lon"], hot["lat"],
                    color="#e74c3c", s=100, edgecolors="darkred",
                    linewidth=0.5, alpha=0.9, label="Hotspot (Severely Poor)",
                    marker="o",
                )
            self._annotate_scatter_note(ax)

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_poverty_category_map(
        self,
        output_path: str = "map_outputs/poverty_category_map.png",
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """
        Create a map showing poverty categories (non-poor / moderate / severe).
        """
        _ensure_dir(os.path.dirname(output_path) or ".")
        title = "Energy Poverty Category\nBangladesh – Upazila Level"
        fig, ax = self._setup_map_axes(figsize=figsize, title=title)

        df = self.df.copy()
        if "poverty_category" not in df.columns:
            df["poverty_category"] = pd.cut(
                df["mepi_score"],
                bins=[0.0, 0.33, 0.66, 1.01],
                labels=["Non-Poor", "Moderately Poor", "Severely Poor"],
                include_lowest=True,
            )

        merged = self._merge_with_shapefile()

        if merged is not None and hasattr(merged, "geometry"):
            for cat, color in POVERTY_COLORS.items():
                subset = merged[merged["poverty_category"] == cat]
                if len(subset):
                    subset.plot(
                        ax=ax, color=color, edgecolor="white",
                        linewidth=0.3, alpha=0.85, label=cat,
                    )
            self._gdf.boundary.plot(
                ax=ax, color="grey", linewidth=0.2, alpha=0.4
            )
        else:
            df_valid = df.dropna(subset=["lat", "lon"])
            for cat, color in POVERTY_COLORS.items():
                subset = df_valid[df_valid["poverty_category"] == cat]
                if len(subset):
                    ax.scatter(
                        subset["lon"], subset["lat"],
                        color=color, s=80, edgecolors="grey",
                        linewidth=0.4, alpha=0.85, label=cat,
                    )
            self._annotate_scatter_note(ax)

        _add_legend_patches(ax, POVERTY_COLORS, title="Energy Poverty Category")
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_all_maps(self, output_dir: str = "map_outputs") -> List[str]:
        """
        Convenience method: create all standard maps.

        Returns
        -------
        list of str
            All saved output paths.
        """
        _ensure_dir(output_dir)
        paths = []
        paths.append(self.create_mepi_map(
            os.path.join(output_dir, "spatial_mepi_map.png")
        ))
        paths.append(self.create_poverty_category_map(
            os.path.join(output_dir, "poverty_category_map.png")
        ))
        paths.append(self.create_hotspot_map(
            os.path.join(output_dir, "hotspot_map.png")
        ))
        paths.extend(self.create_dimension_maps(output_dir))
        return paths
