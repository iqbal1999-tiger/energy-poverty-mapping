"""
spatial_analysis.py - Spatial analysis functions for MEPI results

Provides tools to:
  - Identify energy poverty hotspots (high-MEPI clusters)
  - Calculate spatial statistics and region-wise comparisons
  - Rank upazilas by overall and dimension-level poverty
  - Compare geographic zones (coastal, char, haor, hill tract, Sundarbans)
  - Export GIS-ready data with coordinates

Usage:
    from spatial_analysis import SpatialAnalyzer
    sa = SpatialAnalyzer(results_df)
    hotspots = sa.identify_hotspots()
    rankings = sa.top_n_upazilas(n=10)
    zone_stats = sa.zone_comparison()
"""

import warnings

import numpy as np
import pandas as pd

from config import DIMENSIONS, GEOGRAPHIC_ZONES, DISTRICT_COLUMN, DIVISION_COLUMN


class SpatialAnalyzer:
    """
    Spatial and regional analysis of MEPI results.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.
    """

    def __init__(self, results_df: pd.DataFrame):
        self.df = results_df.copy()
        self._dim_score_cols = [
            f"{d}_score" for d in DIMENSIONS if f"{d}_score" in self.df.columns
        ]
        self._name_col = (
            "upazila_name" if "upazila_name" in self.df.columns else self.df.columns[0]
        )

        # Assign geographic zones if not already present
        if "geographic_zone" not in self.df.columns:
            self.df = self._assign_zones(self.df)

    # ------------------------------------------------------------------
    # Zone assignment
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_zones(df: pd.DataFrame) -> pd.DataFrame:
        """Assign geographic zones from config.GEOGRAPHIC_ZONES."""
        if DISTRICT_COLUMN not in df.columns:
            warnings.warn(
                "No 'district' column found; geographic_zone set to 'unknown'.",
                UserWarning,
                stacklevel=2,
            )
            df = df.copy()
            df["geographic_zone"] = "unknown"
            return df

        district_to_zone: dict = {}
        for zone, info in GEOGRAPHIC_ZONES.items():
            for district in info.get("districts", []):
                district_to_zone[district] = zone

        df = df.copy()
        df["geographic_zone"] = df[DISTRICT_COLUMN].map(
            lambda d: district_to_zone.get(d, "plain")
        )
        return df

    # ------------------------------------------------------------------
    # 1. Hotspot identification
    # ------------------------------------------------------------------

    def identify_hotspots(
        self,
        threshold: float = 0.66,
        min_n: int = 1,
    ) -> pd.DataFrame:
        """
        Identify high-MEPI clusters (hotspots).

        An upazila is a hotspot if its MEPI score exceeds ``threshold``.

        Parameters
        ----------
        threshold : float, optional
            MEPI score above which an upazila is a hotspot.  Default: 0.66
            (i.e. severely poor).
        min_n : int, optional
            Minimum number of upazilas to return.  If fewer than ``min_n``
            upazilas exceed ``threshold``, the threshold is relaxed to return
            at least ``min_n`` upazilas.

        Returns
        -------
        pd.DataFrame
            Hotspot upazilas sorted by descending MEPI score.
        """
        hotspots = self.df[self.df["mepi_score"] >= threshold].sort_values(
            "mepi_score", ascending=False
        )

        if len(hotspots) < min_n:
            # Relax to top-n by score
            hotspots = self.df.nlargest(min_n, "mepi_score")
            warnings.warn(
                f"Fewer than {min_n} upazilas exceed threshold {threshold}. "
                f"Returning top {min_n} upazilas instead.",
                UserWarning,
                stacklevel=2,
            )

        cols = [self._name_col] + (
            [DISTRICT_COLUMN] if DISTRICT_COLUMN in self.df.columns else []
        ) + (
            [DIVISION_COLUMN] if DIVISION_COLUMN in self.df.columns else []
        ) + ["geographic_zone", "mepi_score"] + self._dim_score_cols

        cols = [c for c in cols if c in hotspots.columns]
        return hotspots[cols].reset_index(drop=True)

    # ------------------------------------------------------------------
    # 2. Spatial statistics
    # ------------------------------------------------------------------

    def spatial_statistics(self) -> pd.DataFrame:
        """
        Calculate key spatial statistics for the MEPI results.

        Returns
        -------
        pd.DataFrame
            One row per statistic, columns: Metric, Value.
        """
        scores = self.df["mepi_score"]
        stats = {
            "Total upazilas": len(self.df),
            "Mean MEPI": round(scores.mean(), 4),
            "Median MEPI": round(scores.median(), 4),
            "Std Dev": round(scores.std(), 4),
            "Min MEPI": round(scores.min(), 4),
            "Max MEPI": round(scores.max(), 4),
            "Range": round(scores.max() - scores.min(), 4),
            "Coefficient of Variation (%)": round(scores.std() / scores.mean() * 100, 2)
            if scores.mean() != 0
            else None,
        }

        # Poverty category counts
        if "poverty_category" in self.df.columns:
            for cat in ["Non-Poor", "Moderately Poor", "Severely Poor"]:
                n = (self.df["poverty_category"] == cat).sum()
                pct = round(n / len(self.df) * 100, 1)
                stats[f"  {cat} (n)"] = n
                stats[f"  {cat} (%)"] = pct

        rows = [{"Metric": k, "Value": v} for k, v in stats.items()]
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 3. Zone comparison
    # ------------------------------------------------------------------

    def zone_comparison(self) -> pd.DataFrame:
        """
        Summarise MEPI scores by geographic zone.

        Returns
        -------
        pd.DataFrame
            Zone-level statistics including mean, median, std, n_upazilas,
            and mean dimension scores.
        """
        zone_col = "geographic_zone"
        if zone_col not in self.df.columns:
            raise ValueError("'geographic_zone' column not found. Run assign_zones first.")

        score_cols = ["mepi_score"] + self._dim_score_cols
        agg = (
            self.df.groupby(zone_col)[score_cols]
            .agg(["mean", "median", "std"])
        )
        agg.columns = ["_".join(c) for c in agg.columns]
        agg["n_upazilas"] = self.df.groupby(zone_col).size()
        agg = agg.sort_values("mepi_score_mean", ascending=False)
        return agg.round(4).reset_index()

    # ------------------------------------------------------------------
    # 4. Division / district comparison
    # ------------------------------------------------------------------

    def division_comparison(self) -> pd.DataFrame:
        """
        Compare MEPI scores across administrative divisions.

        Returns
        -------
        pd.DataFrame
            Division-level mean MEPI and dimension scores.
        """
        if DIVISION_COLUMN not in self.df.columns:
            raise ValueError(f"Column '{DIVISION_COLUMN}' not found.")

        score_cols = ["mepi_score"] + self._dim_score_cols
        div = (
            self.df.groupby(DIVISION_COLUMN)[score_cols]
            .mean()
            .round(4)
        )
        div["n_upazilas"] = self.df.groupby(DIVISION_COLUMN).size()
        div = div.sort_values("mepi_score", ascending=False)
        return div.reset_index()

    def district_comparison(self) -> pd.DataFrame:
        """
        Compare MEPI scores across districts.

        Returns
        -------
        pd.DataFrame
            District-level mean MEPI and dimension scores.
        """
        if DISTRICT_COLUMN not in self.df.columns:
            raise ValueError(f"Column '{DISTRICT_COLUMN}' not found.")

        score_cols = ["mepi_score"] + self._dim_score_cols
        dist = (
            self.df.groupby(DISTRICT_COLUMN)[score_cols]
            .mean()
            .round(4)
        )
        dist["n_upazilas"] = self.df.groupby(DISTRICT_COLUMN).size()
        dist = dist.sort_values("mepi_score", ascending=False)
        return dist.reset_index()

    # ------------------------------------------------------------------
    # 5. Rankings
    # ------------------------------------------------------------------

    def top_n_upazilas(self, n: int = 10) -> pd.DataFrame:
        """
        Return the N most energy-poor upazilas (highest MEPI scores).

        Parameters
        ----------
        n : int, optional
            Number of upazilas to return.  Default: 10.

        Returns
        -------
        pd.DataFrame
            Ranked upazilas with scores.
        """
        ranked = self.df.nlargest(n, "mepi_score").copy()
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        return ranked.reset_index(drop=True)

    def bottom_n_upazilas(self, n: int = 10) -> pd.DataFrame:
        """
        Return the N least energy-poor upazilas (lowest MEPI scores).

        Parameters
        ----------
        n : int, optional
            Number of upazilas to return.  Default: 10.

        Returns
        -------
        pd.DataFrame
            Ranked upazilas from least to most deprived.
        """
        ranked = self.df.nsmallest(n, "mepi_score").copy()
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        return ranked.reset_index(drop=True)

    def dimension_rankings(self, dimension: str) -> pd.DataFrame:
        """
        Rank upazilas by a specific dimension score.

        Parameters
        ----------
        dimension : str
            Dimension name (e.g. ``"Availability"``).

        Returns
        -------
        pd.DataFrame
            Upazilas ranked by dimension score (most deprived first).

        Raises
        ------
        ValueError
            If the dimension score column is not in the data.
        """
        col = f"{dimension}_score"
        if col not in self.df.columns:
            raise ValueError(f"Column '{col}' not found.")

        ranked = self.df.sort_values(col, ascending=False).copy()
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        keep = [
            c for c in [
                "rank",
                self._name_col,
                DISTRICT_COLUMN,
                DIVISION_COLUMN,
                "geographic_zone",
                col,
                "mepi_score",
            ]
            if c in ranked.columns
        ]
        return ranked[keep].reset_index(drop=True)

    # ------------------------------------------------------------------
    # 6. GIS-ready export
    # ------------------------------------------------------------------

    def export_gis_ready(
        self,
        filepath: str,
        lat_col: str = None,
        lon_col: str = None,
    ) -> str:
        """
        Export MEPI results to a CSV file formatted for GIS mapping.

        If latitude and longitude columns are present they are retained;
        otherwise a placeholder message is added to the output.

        Parameters
        ----------
        filepath : str
            Path to save the CSV (e.g. ``"output/mepi_gis.csv"``).
        lat_col : str, optional
            Name of the latitude column in the data.
        lon_col : str, optional
            Name of the longitude column in the data.

        Returns
        -------
        str
            Absolute path to the saved file.
        """
        import os

        gis_df = self.df.copy()

        if lat_col and lat_col in gis_df.columns:
            gis_df = gis_df.rename(columns={lat_col: "latitude"})
        elif "latitude" not in gis_df.columns:
            gis_df["latitude"] = None

        if lon_col and lon_col in gis_df.columns:
            gis_df = gis_df.rename(columns={lon_col: "longitude"})
        elif "longitude" not in gis_df.columns:
            gis_df["longitude"] = None

        # Reorder: admin columns first, then coords, then scores
        priority_cols = [
            c for c in [
                "upazila_id", "upazila_name", "district", "division",
                "geographic_zone", "latitude", "longitude",
                "mepi_score", "poverty_category",
            ]
            if c in gis_df.columns
        ]
        remaining = [c for c in gis_df.columns if c not in priority_cols]
        gis_df = gis_df[priority_cols + remaining]

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        gis_df.to_csv(filepath, index=False)
        print(f"GIS-ready CSV saved: {filepath}")
        return os.path.abspath(filepath)
