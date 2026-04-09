"""
updated_spatio_temporal_hotspot.py - Hotspot analysis maps saved to organised folders

Generates clustering and vulnerability maps that highlight spatial concentrations
of energy poverty.  All outputs are saved to hotspot_maps/ in the organised
map_outputs/ hierarchy.

Maps produced
-------------
  hotspot_clusters.png      Severely poor upazilas colour-coded as hotspots
  vulnerability_map.png     Composite vulnerability score map
  hotspot_intensity.png     Kernel density / intensity of hotspot clustering
  cluster_analysis.png      Summary of hotspot clusters with statistics

Usage
-----
    from updated_spatio_temporal_hotspot import HotspotAnalyser
    analyser = HotspotAnalyser(mepi_df)
    analyser.create_all_hotspot_maps()
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
import numpy as np
import pandas as pd

from map_output_manager import MapOutputManager, BASE_OUTPUT_DIR
from bangladesh_coordinates import BANGLADESH_BOUNDS, get_database
from correct_spatial_mapping import (
    MEPI_CMAP,
    POVERTY_COLORS,
    DPI,
    _add_north_arrow,
    _add_colorbar,
    _set_bangladesh_extent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attach_coords(df: pd.DataFrame, name_col: str = "upazila_name") -> pd.DataFrame:
    if "lat" in df.columns and "lon" in df.columns:
        return df
    db = get_database()
    lats, lons = [], []
    for name in df[name_col]:
        rec = db.get_by_name(str(name))
        lats.append(rec["lat"] if rec else np.nan)
        lons.append(rec["lon"] if rec else np.nan)
    df = df.copy()
    df["lat"] = lats
    df["lon"] = lons
    return df


def _gaussian_kde(x: np.ndarray, y: np.ndarray, grid_size: int = 100):
    """Compute a simple Gaussian KDE over a 2-D grid."""
    try:
        from scipy.stats import gaussian_kde
        positions = np.vstack([x, y])
        kde = gaussian_kde(positions)
        xi = np.linspace(x.min() - 0.5, x.max() + 0.5, grid_size)
        yi = np.linspace(y.min() - 0.5, y.max() + 0.5, grid_size)
        Xi, Yi = np.meshgrid(xi, yi)
        Zi = kde(np.vstack([Xi.ravel(), Yi.ravel()])).reshape(Xi.shape)
        return xi, yi, Zi
    except ImportError:
        return None, None, None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class HotspotAnalyser:
    """
    Generate hotspot / vulnerability / cluster maps for MEPI data.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with ``upazila_name``, ``mepi_score``, and dimension
        score columns.
    base_dir : str
        Top-level output directory.
    name_col : str
        Column containing upazila names.
    hotspot_threshold : float
        MEPI score above which an upazila is classified as a hotspot.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        base_dir: str = BASE_OUTPUT_DIR,
        name_col: str = "upazila_name",
        hotspot_threshold: float = 0.66,
    ) -> None:
        self.df = _attach_coords(mepi_df.copy(), name_col)
        self.name_col = name_col
        self.threshold = hotspot_threshold
        self._mgr = MapOutputManager(base_dir)
        self._mgr.create_all_folders()

        # Identify hotspot flag
        self.df["is_hotspot"] = self.df["mepi_score"] >= self.threshold

    # ------------------------------------------------------------------
    # Path helper
    # ------------------------------------------------------------------

    def _path(self, filename: str) -> str:
        return self._mgr.get_path("hotspot_maps", filename)

    # ------------------------------------------------------------------
    # Axes helper
    # ------------------------------------------------------------------

    def _setup_axes(
        self, figsize: Tuple[int, int] = (12, 14), title: str = ""
    ) -> Tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("Longitude", fontsize=10)
        ax.set_ylabel("Latitude", fontsize=10)
        ax.grid(True, alpha=0.25, linestyle="--")
        _set_bangladesh_extent(ax)
        return fig, ax

    # ------------------------------------------------------------------
    # Hotspot clusters map
    # ------------------------------------------------------------------

    def create_hotspot_clusters_map(self) -> str:
        """
        Create hotspot_clusters.png showing hotspot vs non-hotspot upazilas.
        """
        output_path = self._path("hotspot_clusters.png")
        title = (
            f"Energy Poverty Hotspot Clusters (MEPI ≥ {self.threshold:.2f})\n"
            "Bangladesh – Upazila Level"
        )
        fig, ax = self._setup_axes(title=title)
        df = self.df.dropna(subset=["lat", "lon"])

        not_hot = df[~df["is_hotspot"]]
        hot = df[df["is_hotspot"]]

        if len(not_hot):
            ax.scatter(not_hot["lon"], not_hot["lat"],
                       color="#2ecc71", s=60, edgecolors="grey",
                       linewidth=0.3, alpha=0.6, zorder=4, label="Not a hotspot")
        if len(hot):
            ax.scatter(hot["lon"], hot["lat"],
                       color="#e74c3c", s=120, edgecolors="darkred",
                       linewidth=0.7, alpha=0.9, zorder=6, label=f"Hotspot (MEPI ≥ {self.threshold:.2f})")

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)

        ax.text(
            0.5, 0.01,
            f"Hotspots: {int(df['is_hotspot'].sum())} / {len(df)} upazilas "
            f"({100*df['is_hotspot'].mean():.1f}%)",
            transform=ax.transAxes, fontsize=8,
            ha="center", color="grey", style="italic",
        )

        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Vulnerability map
    # ------------------------------------------------------------------

    def create_vulnerability_map(self) -> str:
        """
        Create vulnerability_map.png – composite vulnerability derived from
        number of dimensions with high deprivation.
        """
        output_path = self._path("vulnerability_map.png")
        title = "Multi-Dimensional Vulnerability\nBangladesh – Upazila Level"
        fig, ax = self._setup_axes(title=title)

        df = self.df.copy()
        dim_score_cols = [c for c in df.columns if c.endswith("_score") and c != "mepi_score"]

        # Count dimensions above deprivation threshold (0.33)
        if dim_score_cols:
            df["n_deprived"] = df[dim_score_cols].apply(
                lambda row: (row > 0.33).sum(), axis=1
            )
        else:
            df["n_deprived"] = df["mepi_score"].apply(lambda s: int(s * 5))

        valid = df.dropna(subset=["lat", "lon", "n_deprived"])
        n_max = max(valid["n_deprived"].max(), 1)

        vuln_cmap = plt.cm.YlOrRd
        sc = ax.scatter(
            valid["lon"], valid["lat"],
            c=valid["n_deprived"],
            cmap=vuln_cmap,
            vmin=0, vmax=5,
            s=90, edgecolors="grey", linewidth=0.4, alpha=0.85, zorder=5,
        )
        _add_colorbar(ax, vuln_cmap, 0, 5, "Number of deprived dimensions (0–5)", fig)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Hotspot intensity (KDE) map
    # ------------------------------------------------------------------

    def create_hotspot_intensity_map(self) -> str:
        """
        Create hotspot_intensity.png using kernel density estimation of hotspot
        upazila locations.
        """
        output_path = self._path("hotspot_intensity.png")
        title = "Hotspot Intensity (Kernel Density)\nBangladesh – Upazila Level"
        fig, ax = self._setup_axes(title=title)

        hot = self.df[self.df["is_hotspot"]].dropna(subset=["lat", "lon"])

        if len(hot) >= 3:
            xi, yi, Zi = _gaussian_kde(hot["lon"].values, hot["lat"].values)
            if Zi is not None:
                kde_cmap = plt.cm.hot_r
                ax.contourf(xi, yi, Zi, levels=15, cmap=kde_cmap, alpha=0.75, zorder=3)
                sm = plt.cm.ScalarMappable(cmap=kde_cmap)
                sm.set_array([])
                fig.colorbar(sm, ax=ax, orientation="vertical",
                             fraction=0.03, pad=0.02, label="Hotspot density")
            else:
                # Fallback scatter
                ax.scatter(hot["lon"], hot["lat"],
                           color="#e74c3c", s=100, alpha=0.7, zorder=5, label="Hotspot")
        else:
            ax.scatter(hot["lon"], hot["lat"],
                       color="#e74c3c", s=100, alpha=0.7, zorder=5, label="Hotspot")

        # Overlay all upazilas lightly
        all_valid = self.df.dropna(subset=["lat", "lon"])
        ax.scatter(all_valid["lon"], all_valid["lat"],
                   color="none", edgecolors="grey",
                   s=30, linewidth=0.3, alpha=0.4, zorder=2)

        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Cluster analysis summary map
    # ------------------------------------------------------------------

    def create_cluster_analysis_map(self) -> str:
        """
        Create cluster_analysis.png – a two-panel figure showing the spatial
        distribution and a MEPI score bar chart for hotspot upazilas.
        """
        output_path = self._path("cluster_analysis.png")

        fig = plt.figure(figsize=(16, 8))
        ax_map = fig.add_subplot(1, 2, 1)
        ax_bar = fig.add_subplot(1, 2, 2)

        # --- Left panel: scatter map ---
        ax_map.set_title(
            f"Hotspot Clusters (MEPI ≥ {self.threshold:.2f})",
            fontsize=13, fontweight="bold",
        )
        ax_map.set_xlabel("Longitude", fontsize=9)
        ax_map.set_ylabel("Latitude", fontsize=9)
        ax_map.grid(True, alpha=0.2, linestyle="--")
        _set_bangladesh_extent(ax_map)

        df = self.df.dropna(subset=["lat", "lon"])
        not_hot = df[~df["is_hotspot"]]
        hot = df[df["is_hotspot"]]

        if len(not_hot):
            ax_map.scatter(not_hot["lon"], not_hot["lat"],
                           color="#2ecc71", s=40, alpha=0.5, zorder=4, label="Not a hotspot")
        if len(hot):
            ax_map.scatter(hot["lon"], hot["lat"],
                           color="#e74c3c", s=80, alpha=0.85, zorder=6,
                           label=f"Hotspot ({len(hot)})")

        ax_map.legend(loc="lower left", fontsize=8, framealpha=0.9)
        _add_north_arrow(ax_map)

        # --- Right panel: top hotspot upazilas ---
        top_hot = (
            self.df[self.df["is_hotspot"]]
            .nlargest(min(20, len(hot)), "mepi_score")
            [["upazila_name", "mepi_score"]]
        )

        if not top_hot.empty:
            ax_bar.barh(
                top_hot["upazila_name"],
                top_hot["mepi_score"],
                color="#e74c3c",
                alpha=0.8,
            )
            ax_bar.axvline(self.threshold, color="darkred", linestyle="--",
                           linewidth=1.2, label=f"Threshold ({self.threshold:.2f})")
            ax_bar.set_xlim(0, 1)
            ax_bar.set_xlabel("MEPI Score", fontsize=10)
            ax_bar.set_title("Top Hotspot Upazilas", fontsize=13, fontweight="bold")
            ax_bar.legend(fontsize=9)
            ax_bar.invert_yaxis()
        else:
            ax_bar.text(0.5, 0.5, "No hotspots found",
                        ha="center", va="center", fontsize=12, color="grey",
                        transform=ax_bar.transAxes)

        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_hotspot_maps(self) -> List[str]:
        """
        Create the complete set of hotspot / vulnerability maps.

        Returns
        -------
        list of str
        """
        paths: List[str] = []
        paths.append(self.create_hotspot_clusters_map())
        paths.append(self.create_vulnerability_map())
        paths.append(self.create_hotspot_intensity_map())
        paths.append(self.create_cluster_analysis_map())
        return paths
