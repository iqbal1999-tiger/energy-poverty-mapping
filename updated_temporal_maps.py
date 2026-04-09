"""
updated_temporal_maps.py - Temporal visualisation saved to organised folders

Creates time-series and change maps showing how energy poverty evolved over
multiple years.  All outputs are saved to temporal_maps/ inside the organised
map_outputs/ hierarchy.

Maps produced
-------------
  temporal_{year}_comparison.png   Side-by-side map for each data year
  poverty_change_map.png           Change in MEPI between first and last year
  improvement_areas.png            Upazilas with improving poverty scores
  deterioration_areas.png          Upazilas with worsening poverty scores
  temporal_animation.gif           Animated GIF cycling through all years

Usage
-----
    from updated_temporal_maps import TemporalMapper
    mapper = TemporalMapper(yearly_data)
    mapper.create_all_temporal_maps()

    # yearly_data: dict mapping year (int/str) to MEPI DataFrame, e.g.
    #   {2020: df_2020, 2021: df_2021, 2022: df_2022}
    # Each DataFrame must have columns: upazila_name, mepi_score, lat, lon
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

try:
    from PIL import Image as PilImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

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
    """Add lat/lon columns to *df* via the upazila coordinate database."""
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


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TemporalMapper:
    """
    Create temporal and change maps for multi-year MEPI data.

    Parameters
    ----------
    yearly_data : dict
        Mapping of year → pd.DataFrame.  Each DataFrame must contain columns
        ``upazila_name``, ``mepi_score``, and optionally ``lat``/``lon``.
    base_dir : str
        Top-level output directory.
    name_col : str
        Column containing upazila names.
    """

    def __init__(
        self,
        yearly_data: Dict,
        base_dir: str = BASE_OUTPUT_DIR,
        name_col: str = "upazila_name",
    ) -> None:
        self.yearly_data: Dict[str, pd.DataFrame] = {
            str(yr): _attach_coords(df.copy(), name_col)
            for yr, df in yearly_data.items()
        }
        self.years: List[str] = sorted(self.yearly_data.keys())
        self.name_col = name_col
        self._mgr = MapOutputManager(base_dir)
        self._mgr.create_all_folders()

    # ------------------------------------------------------------------
    # Path helper
    # ------------------------------------------------------------------

    def _path(self, filename: str) -> str:
        return self._mgr.get_path("temporal_maps", filename)

    # ------------------------------------------------------------------
    # Map axes setup
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

    def _scatter_mepi(
        self,
        ax: plt.Axes,
        fig: plt.Figure,
        df: pd.DataFrame,
        label: str = "MEPI Score",
        s: int = 80,
    ) -> None:
        valid = df.dropna(subset=["lat", "lon", "mepi_score"])
        sc = ax.scatter(
            valid["lon"],
            valid["lat"],
            c=valid["mepi_score"],
            cmap=MEPI_CMAP,
            vmin=0.0,
            vmax=1.0,
            s=s,
            edgecolors="grey",
            linewidth=0.4,
            alpha=0.85,
            zorder=5,
        )
        _add_colorbar(ax, MEPI_CMAP, 0.0, 1.0, label, fig)

    # ------------------------------------------------------------------
    # Individual year comparison maps
    # ------------------------------------------------------------------

    def create_year_map(self, year: str) -> Optional[str]:
        """
        Create a MEPI map for a single year.

        Returns
        -------
        str or None
        """
        df = self.yearly_data.get(str(year))
        if df is None:
            warnings.warn(f"No data for year {year}.", UserWarning, stacklevel=2)
            return None

        output_path = self._path(f"temporal_{year}_comparison.png")
        title = f"Energy Poverty Index – {year}\nBangladesh – Upazila Level"

        fig, ax = self._setup_axes(title=title)
        self._scatter_mepi(ax, fig, df)
        _add_north_arrow(ax)

        ax.text(
            0.5, 0.01,
            f"Year: {year}  |  n = {len(df)} upazilas",
            transform=ax.transAxes,
            fontsize=8, ha="center", color="grey", style="italic",
        )

        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_all_year_maps(self) -> List[str]:
        """Create one comparison map per year."""
        paths: List[str] = []
        for yr in self.years:
            p = self.create_year_map(yr)
            if p:
                paths.append(p)
        return paths

    # ------------------------------------------------------------------
    # Change maps
    # ------------------------------------------------------------------

    def _compute_change(self) -> Optional[pd.DataFrame]:
        """Compute MEPI change between first and last year."""
        if len(self.years) < 2:
            warnings.warn(
                "Need at least 2 years to compute change.",
                UserWarning, stacklevel=2,
            )
            return None

        first_yr, last_yr = self.years[0], self.years[-1]
        df_first = self.yearly_data[first_yr][
            [self.name_col, "mepi_score", "lat", "lon"]
        ].rename(columns={"mepi_score": "mepi_first"})

        df_last = self.yearly_data[last_yr][
            [self.name_col, "mepi_score"]
        ].rename(columns={"mepi_score": "mepi_last"})

        merged = df_first.merge(df_last, on=self.name_col, how="inner")
        merged["change"] = merged["mepi_last"] - merged["mepi_first"]
        merged["direction"] = merged["change"].apply(
            lambda x: "Improved" if x < -0.02 else ("Deteriorated" if x > 0.02 else "Stable")
        )
        merged["first_year"] = first_yr
        merged["last_year"] = last_yr
        return merged

    def create_change_map(self) -> Optional[str]:
        """Create poverty_change_map.png showing MEPI change across years."""
        change_df = self._compute_change()
        if change_df is None:
            return None

        first_yr = change_df["first_year"].iloc[0]
        last_yr = change_df["last_year"].iloc[0]
        output_path = self._path("poverty_change_map.png")
        title = f"MEPI Change ({first_yr} → {last_yr})\nBangladesh – Upazila Level"

        fig, ax = self._setup_axes(title=title)
        valid = change_df.dropna(subset=["lat", "lon", "change"])

        change_cmap = plt.cm.RdYlGn_r
        vabs = max(abs(valid["change"].max()), abs(valid["change"].min()), 0.05)

        sc = ax.scatter(
            valid["lon"],
            valid["lat"],
            c=valid["change"],
            cmap=change_cmap,
            vmin=-vabs,
            vmax=vabs,
            s=90,
            edgecolors="grey",
            linewidth=0.4,
            alpha=0.85,
            zorder=5,
        )
        _add_colorbar(ax, change_cmap, -vabs, vabs, "MEPI Change (negative = improved)", fig)

        # Legend
        patches = [
            mpatches.Patch(color="#2ecc71", label="Improved"),
            mpatches.Patch(color="#f39c12", label="Stable"),
            mpatches.Patch(color="#e74c3c", label="Deteriorated"),
        ]
        ax.legend(handles=patches, loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_improvement_map(self) -> Optional[str]:
        """Create improvement_areas.png – only improving upazilas highlighted."""
        change_df = self._compute_change()
        if change_df is None:
            return None

        first_yr = change_df["first_year"].iloc[0]
        last_yr = change_df["last_year"].iloc[0]
        output_path = self._path("improvement_areas.png")
        title = f"Improving Energy Poverty Areas ({first_yr} → {last_yr})\nBangladesh"

        fig, ax = self._setup_axes(title=title)
        valid = change_df.dropna(subset=["lat", "lon"])

        improved = valid[valid["direction"] == "Improved"]
        others = valid[valid["direction"] != "Improved"]

        if len(others):
            ax.scatter(others["lon"], others["lat"],
                       color="#cccccc", s=60, edgecolors="grey",
                       linewidth=0.3, alpha=0.5, zorder=4, label="No improvement")
        if len(improved):
            ax.scatter(improved["lon"], improved["lat"],
                       color="#27ae60", s=110, edgecolors="darkgreen",
                       linewidth=0.6, alpha=0.9, zorder=6, label="Improved")

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_deterioration_map(self) -> Optional[str]:
        """Create deterioration_areas.png – only worsening upazilas highlighted."""
        change_df = self._compute_change()
        if change_df is None:
            return None

        first_yr = change_df["first_year"].iloc[0]
        last_yr = change_df["last_year"].iloc[0]
        output_path = self._path("deterioration_areas.png")
        title = f"Deteriorating Energy Poverty Areas ({first_yr} → {last_yr})\nBangladesh"

        fig, ax = self._setup_axes(title=title)
        valid = change_df.dropna(subset=["lat", "lon"])

        deteriorated = valid[valid["direction"] == "Deteriorated"]
        others = valid[valid["direction"] != "Deteriorated"]

        if len(others):
            ax.scatter(others["lon"], others["lat"],
                       color="#cccccc", s=60, edgecolors="grey",
                       linewidth=0.3, alpha=0.5, zorder=4, label="Stable / improved")
        if len(deteriorated):
            ax.scatter(deteriorated["lon"], deteriorated["lat"],
                       color="#c0392b", s=110, edgecolors="darkred",
                       linewidth=0.6, alpha=0.9, zorder=6, label="Deteriorated")

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Animated GIF
    # ------------------------------------------------------------------

    def create_animation(self, frame_duration_ms: int = 800) -> Optional[str]:
        """
        Create temporal_animation.gif cycling through all years.

        Requires ``Pillow`` (``pip install Pillow``).

        Returns
        -------
        str or None
        """
        if not _HAS_PIL:
            warnings.warn(
                "Pillow is not installed – cannot create GIF animation. "
                "Install with: pip install Pillow",
                UserWarning, stacklevel=2,
            )
            return None

        # Generate individual frames as PNG bytes
        frames: List[PilImage.Image] = []
        for yr in self.years:
            df = self.yearly_data[yr]
            valid = df.dropna(subset=["lat", "lon", "mepi_score"])

            fig, ax = self._setup_axes(
                figsize=(8, 9),
                title=f"MEPI – {yr}\nBangladesh Upazila Level",
            )
            ax.scatter(
                valid["lon"], valid["lat"],
                c=valid["mepi_score"],
                cmap=MEPI_CMAP,
                vmin=0.0, vmax=1.0,
                s=70, edgecolors="grey", linewidth=0.3, alpha=0.85,
            )
            _add_colorbar(ax, MEPI_CMAP, 0.0, 1.0, "MEPI Score", fig)
            _add_north_arrow(ax)
            plt.tight_layout()

            # Save to buffer
            import io
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            frames.append(PilImage.open(buf).copy())

        if not frames:
            return None

        output_path = self._path("temporal_animation.gif")
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0,
        )
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_temporal_maps(self) -> List[str]:
        """
        Create the complete set of temporal maps.

        Returns
        -------
        list of str
            Paths to all saved files.
        """
        paths: List[str] = []
        paths.extend(self.create_all_year_maps())

        change_path = self.create_change_map()
        if change_path:
            paths.append(change_path)

        improvement_path = self.create_improvement_map()
        if improvement_path:
            paths.append(improvement_path)

        deterioration_path = self.create_deterioration_map()
        if deterioration_path:
            paths.append(deterioration_path)

        animation_path = self.create_animation()
        if animation_path:
            paths.append(animation_path)

        return paths
