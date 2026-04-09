"""
data_preparation_spatial.py - Prepare MEPI data for GIS / spatial mapping

Responsibilities:
  - Add latitude/longitude coordinates to upazila-level MEPI results.
  - Merge MEPI results with GeoDataFrames (shapefiles / GeoJSON).
  - Assign geographic zones and district metadata.
  - Validate geographic alignment before mapping.
  - Generate synthetic multi-year data for temporal demonstrations when
    only a single-year dataset is available.

Usage:
    from data_preparation_spatial import SpatialDataPrep
    prep = SpatialDataPrep(results_df)
    geo_df = prep.add_coordinates()
    gdf    = prep.merge_with_shapefile("shapefiles/upazilas.geojson")
    multi  = prep.simulate_temporal_data(years=[2020, 2022, 2025])
"""

import os
import warnings

import numpy as np
import pandas as pd

from map_config import UPAZILA_COORDINATES, BANGLADESH_CENTER

try:
    import geopandas as gpd
    from shapely.geometry import Point
    HAS_GEOPANDAS = True
except ImportError:  # pragma: no cover
    HAS_GEOPANDAS = False


class SpatialDataPrep:
    """
    Prepare MEPI result DataFrames for spatial and temporal mapping.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.  Must contain at least
        ``upazila_name`` and ``mepi_score`` columns.
    name_col : str
        Column that holds upazila names (used for coordinate lookup).
    """

    def __init__(self, results_df: pd.DataFrame, name_col: str = "upazila_name"):
        self.df = results_df.copy()
        self.name_col = name_col if name_col in results_df.columns else results_df.columns[0]

    # ------------------------------------------------------------------
    # 1. Coordinate assignment
    # ------------------------------------------------------------------

    def add_coordinates(
        self,
        coord_dict: dict = None,
        fallback_jitter: float = 0.15,
    ) -> pd.DataFrame:
        """
        Add ``latitude`` and ``longitude`` columns to the MEPI DataFrame.

        Parameters
        ----------
        coord_dict : dict, optional
            ``{upazila_name: (lat, lon)}``.  Defaults to
            ``map_config.UPAZILA_COORDINATES``.
        fallback_jitter : float
            Radius (degrees) of random jitter applied to upazilas whose
            coordinates are not found in ``coord_dict``.  The centre used
            for jitter is Bangladesh's geographic centre.

        Returns
        -------
        pd.DataFrame
            Input DataFrame with added ``latitude`` and ``longitude`` columns.
        """
        coords = coord_dict or UPAZILA_COORDINATES
        rng = np.random.default_rng(seed=42)

        def _lookup(name):
            if name in coords:
                return coords[name]
            # Fuzzy match: check if any key is a substring
            for key, val in coords.items():
                if key.lower() in name.lower() or name.lower() in key.lower():
                    return val
            # Fallback: random jitter around Bangladesh centre
            lat = BANGLADESH_CENTER[0] + rng.uniform(-fallback_jitter, fallback_jitter)
            lon = BANGLADESH_CENTER[1] + rng.uniform(-fallback_jitter, fallback_jitter)
            return (lat, lon)

        lats, lons = zip(*[_lookup(n) for n in self.df[self.name_col]])
        df = self.df.copy()
        df["latitude"] = list(lats)
        df["longitude"] = list(lons)
        return df

    # ------------------------------------------------------------------
    # 2. Shapefile / GeoJSON merge
    # ------------------------------------------------------------------

    def merge_with_shapefile(
        self,
        shapefile_path: str,
        shape_name_col: str = "upazila_name",
        how: str = "left",
    ):
        """
        Merge MEPI results with a GeoDataFrame loaded from a shapefile or GeoJSON.

        Parameters
        ----------
        shapefile_path : str
            Path to shapefile (.shp) or GeoJSON (.geojson).
        shape_name_col : str
            Column in the shapefile that contains upazila names.
        how : str
            Merge type (``"left"``, ``"inner"``, etc.).

        Returns
        -------
        geopandas.GeoDataFrame
            Merged GeoDataFrame with MEPI scores and geometries.

        Raises
        ------
        ImportError
            If GeoPandas is not installed.
        FileNotFoundError
            If the shapefile does not exist.
        """
        if not HAS_GEOPANDAS:
            raise ImportError(
                "GeoPandas is required for shapefile merging. "
                "Install with: pip install geopandas"
            )
        if not os.path.exists(shapefile_path):
            raise FileNotFoundError(
                f"Shapefile not found: {shapefile_path}\n"
                "Download Bangladesh upazila boundaries and place them in the "
                "'shapefiles/' directory."
            )

        gdf = gpd.read_file(shapefile_path)
        merged = gdf.merge(
            self.df,
            left_on=shape_name_col,
            right_on=self.name_col,
            how=how,
        )
        unmatched = merged["mepi_score"].isna().sum()
        if unmatched > 0:
            warnings.warn(
                f"{unmatched} shapefile features could not be matched to MEPI results.",
                UserWarning,
                stacklevel=2,
            )
        return merged

    # ------------------------------------------------------------------
    # 3. Temporal / multi-year data simulation
    # ------------------------------------------------------------------

    def simulate_temporal_data(
        self,
        years: list = None,
        trend_noise: float = 0.04,
        seed: int = 42,
    ) -> dict:
        """
        Generate synthetic multi-year MEPI datasets for temporal demonstration.

        The baseline year uses the provided ``results_df``.  Subsequent years
        apply a slight improvement trend with random noise, reflecting
        real-world energy access progress in Bangladesh.

        Parameters
        ----------
        years : list of int
            Years to simulate.  Defaults to ``[2020, 2021, 2022, 2023, 2024, 2025]``.
        trend_noise : float
            Std dev of year-on-year Gaussian noise added to each score.
        seed : int
            Random seed for reproducibility.

        Returns
        -------
        dict
            ``{year: pd.DataFrame}`` – one DataFrame per year, each having
            the same structure as the original results with updated scores.
        """
        years = years or [2020, 2021, 2022, 2023, 2024, 2025]
        rng = np.random.default_rng(seed=seed)
        dim_score_cols = [c for c in self.df.columns if c.endswith("_score") and c != "mepi_score"]

        temporal: dict = {}
        prev_df = self.df.copy()

        for i, year in enumerate(years):
            year_df = prev_df.copy()
            if i > 0:
                # Apply gradual improvement trend (1–2 % per year) + noise
                improvement = rng.uniform(0.01, 0.02)
                noise = rng.normal(0, trend_noise, size=(len(year_df), len(dim_score_cols)))
                for j, col in enumerate(dim_score_cols):
                    year_df[col] = (year_df[col] - improvement + noise[:, j]).clip(0.0, 1.0)

                # Recalculate MEPI score as equal-weighted average of dimension scores
                year_df["mepi_score"] = year_df[dim_score_cols].mean(axis=1).clip(0.0, 1.0)

                # Re-classify poverty
                year_df["poverty_category"] = year_df["mepi_score"].apply(
                    _classify_poverty_simple
                )

            year_df["year"] = year
            temporal[year] = year_df
            prev_df = year_df

        return temporal

    # ------------------------------------------------------------------
    # 4. Build a GeoDataFrame from point coordinates
    # ------------------------------------------------------------------

    def to_geodataframe(self, lat_col: str = "latitude", lon_col: str = "longitude"):
        """
        Convert a DataFrame (with lat/lon) to a GeoDataFrame of Point geometries.

        Parameters
        ----------
        lat_col, lon_col : str
            Column names for latitude and longitude.

        Returns
        -------
        geopandas.GeoDataFrame
            With ``geometry`` column set to Point objects in WGS84.
        """
        if not HAS_GEOPANDAS:
            raise ImportError(
                "GeoPandas is required. Install with: pip install geopandas"
            )
        df = self.df.copy()
        if lat_col not in df.columns or lon_col not in df.columns:
            df = self.add_coordinates()
        geometry = [Point(row[lon_col], row[lat_col]) for _, row in df.iterrows()]
        return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _classify_poverty_simple(score: float) -> str:
    """Simple poverty classification matching config.py thresholds."""
    if score < 0.33:
        return "Non-Poor"
    elif score < 0.66:
        return "Moderately Poor"
    return "Severely Poor"


def load_and_prepare(
    csv_path: str = "sample_data.csv",
    add_coords: bool = True,
) -> pd.DataFrame:
    """
    Convenience wrapper: load MEPI results CSV and optionally add coordinates.

    Parameters
    ----------
    csv_path : str
        Path to CSV file containing MEPI results (output of MEPICalculator).
    add_coords : bool
        If True, append latitude/longitude columns.

    Returns
    -------
    pd.DataFrame
    """
    df = pd.read_csv(csv_path)
    prep = SpatialDataPrep(df)
    if add_coords:
        df = prep.add_coordinates()
    return df
