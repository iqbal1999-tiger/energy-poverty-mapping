"""
temporal_analysis.py - Time-based analysis of MEPI trends

Analyses changes in energy poverty across time periods, identifies improving
and deteriorating regions, calculates trends, and prepares time-series data
for animations.

Public API:
    TemporalAnalyzer(temporal_dict)          – main class
    .calculate_change()                       – year-on-year change table
    .classify_trend()                         – improving / stable / worsening
    .trend_statistics()                       – summary stats per year
    .rank_by_change()                         – biggest movers
    .dimension_trends()                       – per-dimension trend table
"""

import warnings

import numpy as np
import pandas as pd


class TemporalAnalyzer:
    """
    Analyse MEPI trends across multiple years.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` – one DataFrame per year, each having the
        same structure as the output of ``MEPICalculator.calculate()``.
    name_col : str
        Column that identifies each upazila.
    score_col : str
        Column holding the overall MEPI score.
    """

    def __init__(
        self,
        temporal_dict: dict,
        name_col: str = "upazila_name",
        score_col: str = "mepi_score",
    ):
        self.temporal = temporal_dict
        self.years = sorted(temporal_dict.keys())
        self.name_col = name_col
        self.score_col = score_col
        self._dim_cols = self._find_dim_cols()

        if len(self.years) < 2:
            raise ValueError(
                "TemporalAnalyzer requires at least two years of data."
            )

    # ------------------------------------------------------------------
    # 1. Wide-format pivot table (upazilas × years)
    # ------------------------------------------------------------------

    def pivot_table(self, column: str = None) -> pd.DataFrame:
        """
        Return a wide-format DataFrame: rows = upazilas, columns = years.

        Parameters
        ----------
        column : str, optional
            Column to pivot.  Defaults to ``self.score_col`` (mepi_score).

        Returns
        -------
        pd.DataFrame
        """
        col = column or self.score_col
        frames = []
        for year, df in self.temporal.items():
            tmp = df[[self.name_col, col]].copy()
            tmp = tmp.rename(columns={col: year})
            frames.append(tmp.set_index(self.name_col))
        return pd.concat(frames, axis=1).reset_index()

    # ------------------------------------------------------------------
    # 2. Year-on-year change
    # ------------------------------------------------------------------

    def calculate_change(self, base_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Calculate absolute and percentage change between base and end years.

        Parameters
        ----------
        base_year : int, optional
            First year.  Defaults to the earliest year in the data.
        end_year : int, optional
            Last year.  Defaults to the most recent year in the data.

        Returns
        -------
        pd.DataFrame
            Columns: upazila_name, base_score, end_score,
            absolute_change, percent_change.
        """
        base_year = base_year or self.years[0]
        end_year = end_year or self.years[-1]

        base_df = self.temporal[base_year][[self.name_col, self.score_col]].rename(
            columns={self.score_col: "base_score"}
        )
        end_df = self.temporal[end_year][[self.name_col, self.score_col]].rename(
            columns={self.score_col: "end_score"}
        )
        merged = base_df.merge(end_df, on=self.name_col)
        merged["absolute_change"] = merged["end_score"] - merged["base_score"]
        merged["percent_change"] = (
            merged["absolute_change"] / merged["base_score"].replace(0, np.nan) * 100
        ).round(2)
        merged["base_year"] = base_year
        merged["end_year"] = end_year
        return merged.sort_values("absolute_change", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 3. Trend classification
    # ------------------------------------------------------------------

    def classify_trend(
        self,
        base_year: int = None,
        end_year: int = None,
        threshold: float = 0.03,
    ) -> pd.DataFrame:
        """
        Classify upazilas as improving, stable, or worsening.

        Parameters
        ----------
        threshold : float
            Absolute change in MEPI required to be classified as
            improving (negative) or worsening (positive).

        Returns
        -------
        pd.DataFrame
            With added ``trend`` column.
        """
        df = self.calculate_change(base_year, end_year)
        df["trend"] = df["absolute_change"].apply(
            lambda x: "Improving" if x < -threshold
            else ("Worsening" if x > threshold else "Stable")
        )
        return df

    # ------------------------------------------------------------------
    # 4. Annual summary statistics
    # ------------------------------------------------------------------

    def trend_statistics(self) -> pd.DataFrame:
        """
        Compute per-year summary statistics for the MEPI score.

        Returns
        -------
        pd.DataFrame
            Rows = years, columns = mean, median, std, min, max,
            n_severe, n_moderate, n_non_poor.
        """
        rows = []
        for year in self.years:
            df = self.temporal[year]
            scores = df[self.score_col]
            row = {
                "year": year,
                "mean_mepi": round(scores.mean(), 4),
                "median_mepi": round(scores.median(), 4),
                "std_mepi": round(scores.std(), 4),
                "min_mepi": round(scores.min(), 4),
                "max_mepi": round(scores.max(), 4),
                "n_upazilas": len(df),
            }
            if "poverty_category" in df.columns:
                row["n_severe"] = (df["poverty_category"] == "Severely Poor").sum()
                row["n_moderate"] = (df["poverty_category"] == "Moderately Poor").sum()
                row["n_non_poor"] = (df["poverty_category"] == "Non-Poor").sum()
            rows.append(row)
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 5. Biggest movers
    # ------------------------------------------------------------------

    def rank_by_change(
        self,
        n: int = 5,
        direction: str = "both",
        base_year: int = None,
        end_year: int = None,
    ) -> pd.DataFrame:
        """
        Return the N upazilas with the largest improvement or deterioration.

        Parameters
        ----------
        n : int
            Number to return per direction.
        direction : str
            ``"improving"``, ``"worsening"``, or ``"both"``.

        Returns
        -------
        pd.DataFrame
        """
        change = self.calculate_change(base_year, end_year)
        direction = direction.lower()
        if direction == "improving":
            return change.nsmallest(n, "absolute_change").reset_index(drop=True)
        elif direction == "worsening":
            return change.nlargest(n, "absolute_change").reset_index(drop=True)
        else:
            top = change.nlargest(n, "absolute_change")
            bot = change.nsmallest(n, "absolute_change")
            return pd.concat([top, bot]).drop_duplicates().reset_index(drop=True)

    # ------------------------------------------------------------------
    # 6. Dimension-level trends
    # ------------------------------------------------------------------

    def dimension_trends(self) -> pd.DataFrame:
        """
        Compute mean dimension scores for each year.

        Returns
        -------
        pd.DataFrame
            Rows = years × dimensions, columns = year, dimension, mean_score.
        """
        rows = []
        for year in self.years:
            df = self.temporal[year]
            for col in self._dim_cols:
                dim = col.replace("_score", "").title()
                rows.append({
                    "year": year,
                    "dimension": dim,
                    "mean_score": round(df[col].mean(), 4),
                })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 7. Time-series data (for animation frame preparation)
    # ------------------------------------------------------------------

    def build_animation_frames(self) -> list:
        """
        Build a list of DataFrames (one per year) suitable for animation.

        Each DataFrame includes upazila name, score, lat, lon if available.

        Returns
        -------
        list of pd.DataFrame
        """
        frames = []
        for year in self.years:
            df = self.temporal[year].copy()
            df["year"] = year
            frames.append(df)
        return frames

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _find_dim_cols(self) -> list:
        first_df = next(iter(self.temporal.values()))
        return [
            c for c in first_df.columns
            if c.endswith("_score") and c != "mepi_score"
        ]


# ---------------------------------------------------------------------------
# Module-level utility functions
# ---------------------------------------------------------------------------

def compare_two_years(
    df_base: pd.DataFrame,
    df_end: pd.DataFrame,
    name_col: str = "upazila_name",
    score_col: str = "mepi_score",
) -> pd.DataFrame:
    """
    Quick comparison of two single-year DataFrames.

    Returns
    -------
    pd.DataFrame
        Merged table with change columns.
    """
    ta = TemporalAnalyzer(
        {0: df_base, 1: df_end},
        name_col=name_col,
        score_col=score_col,
    )
    return ta.calculate_change(0, 1)
