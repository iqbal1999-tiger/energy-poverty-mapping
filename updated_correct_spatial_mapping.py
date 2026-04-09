"""
updated_correct_spatial_mapping.py - Spatial maps saved to organised folders

Drop-in replacement for correct_spatial_mapping.py that saves maps to the
correct subfolders of the organised map_outputs/ hierarchy:

  spatial_maps/  ← MEPI + dimension maps
  hotspot_maps/  ← hotspot and poverty-category maps

Usage
-----
    from updated_correct_spatial_mapping import OrganisedSpatialMapper
    mapper = OrganisedSpatialMapper(mepi_df)
    mapper.create_all_maps()          # uses organised folders automatically
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Re-use all rendering logic from the original module
from correct_spatial_mapping import SpatialMapper, OUTPUT_DIR, DPI

from map_output_manager import MapOutputManager, ensure_all_folders, BASE_OUTPUT_DIR

# ---------------------------------------------------------------------------
# Subclass with organised output paths
# ---------------------------------------------------------------------------

class OrganisedSpatialMapper(SpatialMapper):
    """
    Extension of :class:`SpatialMapper` that routes outputs to the organised
    folder structure managed by :class:`MapOutputManager`.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results (output of MEPICalculator.calculate()).
    base_dir : str
        Top-level output directory (default: ``map_outputs``).
    shapefile_path : str, optional
        Path to Bangladesh upazila shapefile.  Auto-detected if not given.
    name_col : str
        Column in mepi_df containing upazila names.
    """

    def __init__(
        self,
        mepi_df,
        base_dir: str = BASE_OUTPUT_DIR,
        shapefile_path: Optional[str] = None,
        name_col: str = "upazila_name",
    ) -> None:
        super().__init__(
            mepi_df,
            shapefile_path=shapefile_path,
            name_col=name_col,
        )
        self._mgr = MapOutputManager(base_dir)
        self._mgr.create_all_folders()

    # ------------------------------------------------------------------
    # Organised output helpers
    # ------------------------------------------------------------------

    def _spatial_path(self, filename: str) -> str:
        return self._mgr.get_path("spatial_maps", filename)

    def _hotspot_path(self, filename: str) -> str:
        return self._mgr.get_path("hotspot_maps", filename)

    # ------------------------------------------------------------------
    # Overridden public methods
    # ------------------------------------------------------------------

    def create_mepi_map(
        self,
        output_path: Optional[str] = None,
        title: str = "Multidimensional Energy Poverty Index (MEPI)\nBangladesh – Upazila Level",
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """Save MEPI map to spatial_maps/mepi_spatial_map.png."""
        if output_path is None:
            output_path = self._spatial_path("mepi_spatial_map.png")
        return super().create_mepi_map(output_path=output_path, title=title, figsize=figsize)

    def create_dimension_maps(
        self,
        output_dir: Optional[str] = None,
        figsize: Tuple[int, int] = (11, 13),
    ) -> List[str]:
        """Save each dimension map to spatial_maps/ with consistent naming."""
        if output_dir is None:
            output_dir = self._mgr.get_subfolder_path("spatial_maps")
        return super().create_dimension_maps(output_dir=output_dir, figsize=figsize)

    def create_hotspot_map(
        self,
        output_path: Optional[str] = None,
        threshold: float = 0.66,
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """Save hotspot map to hotspot_maps/hotspot_clusters.png."""
        if output_path is None:
            output_path = self._hotspot_path("hotspot_clusters.png")
        return super().create_hotspot_map(
            output_path=output_path, threshold=threshold, figsize=figsize
        )

    def create_poverty_category_map(
        self,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 14),
    ) -> str:
        """Save poverty-category map to spatial_maps/poverty_category_map.png."""
        if output_path is None:
            output_path = self._spatial_path("poverty_category_map.png")
        return super().create_poverty_category_map(
            output_path=output_path, figsize=figsize
        )

    def create_all_maps(self, output_dir: Optional[str] = None) -> List[str]:
        """
        Create all standard maps routed to the organised subfolder hierarchy.

        Returns
        -------
        list of str
            All saved output paths.
        """
        paths: List[str] = []
        paths.append(self.create_mepi_map())
        paths.append(self.create_poverty_category_map())
        paths.append(self.create_hotspot_map())
        paths.extend(self.create_dimension_maps())
        return paths

    def create_regional_maps(self) -> List[str]:
        """
        Create maps broken down by geographic zone (coastal, char, haor, etc.).

        Saves to regional_maps/ subfolder.

        Returns
        -------
        list of str
        """
        import warnings
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from config import GEOGRAPHIC_ZONES
        from correct_spatial_mapping import MEPI_CMAP, _add_north_arrow, _add_colorbar

        regional_dir = self._mgr.get_subfolder_path("regional_maps")
        os.makedirs(regional_dir, exist_ok=True)
        saved: List[str] = []

        for zone_key, zone_info in GEOGRAPHIC_ZONES.items():
            if zone_key == "plain":
                continue  # skip generic zone

            districts = zone_info.get("districts", [])
            if not districts:
                continue

            mask = self.df.get("district", "").str.lower().isin(
                [d.lower() for d in districts]
            )
            zone_df = self.df[mask]
            if zone_df.empty:
                warnings.warn(
                    f"No data for zone '{zone_key}' – skipping.", UserWarning, stacklevel=2
                )
                continue

            filename = f"{zone_key}_analysis_map.png"
            output_path = os.path.join(regional_dir, filename)

            title = (
                f"{zone_info.get('description', zone_key)}\n"
                "Bangladesh Energy Poverty – Upazila Level"
            )
            fig, ax = self._setup_map_axes(title=title)
            self._choropleth(
                ax, fig,
                score_col="mepi_score",
                cmap=MEPI_CMAP,
                vmin=0.0,
                vmax=1.0,
                label="MEPI Score",
            )

            # Highlight zone upazilas
            if self._gdf is None:
                zone_valid = zone_df.dropna(subset=["lat", "lon"])
                ax.scatter(
                    zone_valid["lon"], zone_valid["lat"],
                    color="blue", s=120, edgecolors="darkblue",
                    linewidth=0.8, alpha=0.85, zorder=6,
                    label=f"{zone_key} upazilas",
                )
                self._annotate_scatter_note(ax)

            ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
            _add_north_arrow(ax)
            plt.tight_layout()
            fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {output_path}")
            saved.append(os.path.abspath(output_path))

        # Urban vs rural comparison
        urban_path = self._create_urban_rural_map(regional_dir)
        if urban_path:
            saved.append(urban_path)

        return saved

    def _create_urban_rural_map(self, output_dir: str) -> Optional[str]:
        """Create a simple urban/rural comparison map."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from correct_spatial_mapping import MEPI_CMAP, _add_north_arrow

        output_path = os.path.join(output_dir, "urban_rural_comparison.png")

        # Simple proxy: upazilas with 'sadar' or city-corporation names = urban
        df = self.df.copy()
        urban_keywords = ["sadar", "city", "municipal", "paurashava"]
        mask = df.get("upazila_name", "").str.lower().apply(
            lambda x: any(kw in x for kw in urban_keywords)
        )
        df["area_type"] = "Rural"
        df.loc[mask, "area_type"] = "Urban"

        fig, ax = self._setup_map_axes(
            title="Urban vs Rural Energy Poverty\nBangladesh – Upazila Level"
        )
        self._choropleth(
            ax, fig,
            score_col="mepi_score",
            cmap=MEPI_CMAP,
            vmin=0.0,
            vmax=1.0,
            label="MEPI Score",
        )

        if self._gdf is None:
            urban_df = df[df["area_type"] == "Urban"].dropna(subset=["lat", "lon"])
            rural_df = df[df["area_type"] == "Rural"].dropna(subset=["lat", "lon"])
            if len(urban_df):
                ax.scatter(urban_df["lon"], urban_df["lat"],
                           color="steelblue", s=100, edgecolors="navy",
                           linewidth=0.6, alpha=0.85, zorder=6, label="Urban")
            if len(rural_df):
                ax.scatter(rural_df["lon"], rural_df["lat"],
                           color="goldenrod", s=70, edgecolors="grey",
                           linewidth=0.3, alpha=0.6, zorder=5, label="Rural")
            self._annotate_scatter_note(ax)

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        _add_north_arrow(ax)
        plt.tight_layout()
        fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)
