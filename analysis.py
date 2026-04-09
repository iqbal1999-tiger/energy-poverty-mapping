"""
analysis.py - Statistical analysis, ranking, and export utilities

This module provides functions to:
  - Compute summary statistics on MEPI results
  - Rank upazilas by overall or dimension-level poverty
  - Produce district/division-level aggregations
  - Export results to CSV and Excel
  - Build formatted summary tables

Usage:
    from analysis import summarise_results, rank_upazilas, export_results
    summary = summarise_results(results_df)
    ranked = rank_upazilas(results_df)
    export_results(results_df, "output/mepi_results.xlsx")
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd

from config import (
    DIMENSIONS,
    POVERTY_LABELS,
    POVERTY_THRESHOLDS,
    UPAZILA_ID_COLUMN,
    UPAZILA_NAME_COLUMN,
    DISTRICT_COLUMN,
    DIVISION_COLUMN,
)


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================


def summarise_results(results_df: pd.DataFrame) -> dict:
    """
    Compute overall and dimension-level summary statistics from MEPI results.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.

    Returns
    -------
    dict with keys:
      - ``"overall"``     : Series with mean, median, std, min, max of mepi_score
      - ``"by_category"`` : DataFrame with counts and percentages per poverty category
      - ``"by_dimension"`` : DataFrame with mean scores for each dimension
      - ``"n_deprived"``  : Series summarising n_dimensions_deprived distribution
    """
    summary = {}

    # Overall MEPI statistics
    summary["overall"] = results_df["mepi_score"].agg(
        ["mean", "median", "std", "min", "max"]
    )

    # Poverty category breakdown
    cat_counts = (
        results_df["poverty_category"]
        .value_counts()
        .rename("count")
        .to_frame()
    )
    cat_counts["percentage"] = (
        cat_counts["count"] / len(results_df) * 100
    ).round(1)
    summary["by_category"] = cat_counts

    # Dimension-level mean deprivation scores
    dim_score_cols = [f"{d}_score" for d in DIMENSIONS if f"{d}_score" in results_df.columns]
    summary["by_dimension"] = (
        results_df[dim_score_cols]
        .agg(["mean", "median", "std"])
        .rename(columns={f"{d}_score": d for d in DIMENSIONS})
    )

    # Distribution of number of dimensions deprived
    if "n_dimensions_deprived" in results_df.columns:
        summary["n_deprived"] = results_df["n_dimensions_deprived"].value_counts().sort_index()

    return summary


def print_summary(summary: dict):
    """Pretty-print the output of ``summarise_results``."""
    print("=" * 60)
    print("MULTIDIMENSIONAL ENERGY POVERTY INDEX – SUMMARY")
    print("=" * 60)

    print("\n── Overall MEPI Score ──")
    overall = summary["overall"]
    for stat, val in overall.items():
        print(f"  {stat:<8}: {val:.4f}")

    print("\n── Poverty Category Breakdown ──")
    cat_df = summary["by_category"]
    print(cat_df.to_string())

    print("\n── Mean Deprivation Score by Dimension ──")
    dim_df = summary["by_dimension"]
    print(dim_df.round(4).to_string())

    if "n_deprived" in summary:
        print("\n── Distribution: Number of Dimensions Deprived ──")
        for n, count in summary["n_deprived"].items():
            print(f"  {n} dimension(s): {count} upazila(s)")

    print("=" * 60)


# =============================================================================
# RANKING
# =============================================================================


def rank_upazilas(
    results_df: pd.DataFrame,
    by: str = "mepi_score",
    ascending: bool = False,
    top_n: int = None,
) -> pd.DataFrame:
    """
    Rank upazilas by MEPI score or a dimension score.

    Parameters
    ----------
    results_df : pd.DataFrame
        MEPI results DataFrame.
    by : str, optional
        Column to rank by.  Default ``"mepi_score"``.
    ascending : bool, optional
        If False (default), highest score (most deprived) ranks first.
    top_n : int, optional
        Return only the top N upazilas.

    Returns
    -------
    pd.DataFrame
        Ranked DataFrame with an added ``rank`` column (1 = most deprived).
    """
    if by not in results_df.columns:
        raise ValueError(f"Column '{by}' not found in results DataFrame.")

    ranked = results_df.sort_values(by, ascending=ascending).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))

    if top_n is not None:
        ranked = ranked.head(top_n)

    return ranked.reset_index(drop=True)


# =============================================================================
# AGGREGATION BY ADMINISTRATIVE UNIT
# =============================================================================


def aggregate_by_district(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate MEPI results to district level.

    Parameters
    ----------
    results_df : pd.DataFrame
        MEPI results with a ``district`` column.

    Returns
    -------
    pd.DataFrame
        District-level summary: mean MEPI, mean dimension scores,
        upazila count, and poverty category distribution.
    """
    if DISTRICT_COLUMN not in results_df.columns:
        raise ValueError(
            f"Column '{DISTRICT_COLUMN}' not found. Cannot aggregate by district."
        )

    dim_score_cols = [
        f"{d}_score" for d in DIMENSIONS if f"{d}_score" in results_df.columns
    ]
    agg_cols = ["mepi_score"] + dim_score_cols

    district_mean = (
        results_df.groupby(DISTRICT_COLUMN)[agg_cols].mean().round(4)
    )
    district_count = (
        results_df.groupby(DISTRICT_COLUMN)
        .size()
        .rename("n_upazilas")
    )

    # Poverty category shares
    cat_dummies = pd.get_dummies(results_df["poverty_category"])
    cat_dummies[DISTRICT_COLUMN] = results_df[DISTRICT_COLUMN].values
    cat_share = (
        cat_dummies.groupby(DISTRICT_COLUMN).mean().round(3) * 100
    )

    district_df = pd.concat([district_mean, district_count, cat_share], axis=1)
    district_df = district_df.sort_values("mepi_score", ascending=False)
    return district_df.reset_index()


def aggregate_by_division(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate MEPI results to division level.

    Parameters
    ----------
    results_df : pd.DataFrame
        MEPI results with a ``division`` column.

    Returns
    -------
    pd.DataFrame
        Division-level summary similar to ``aggregate_by_district``.
    """
    if DIVISION_COLUMN not in results_df.columns:
        raise ValueError(
            f"Column '{DIVISION_COLUMN}' not found. Cannot aggregate by division."
        )

    dim_score_cols = [
        f"{d}_score" for d in DIMENSIONS if f"{d}_score" in results_df.columns
    ]
    agg_cols = ["mepi_score"] + dim_score_cols

    division_mean = (
        results_df.groupby(DIVISION_COLUMN)[agg_cols].mean().round(4)
    )
    division_count = (
        results_df.groupby(DIVISION_COLUMN)
        .size()
        .rename("n_upazilas")
    )

    cat_dummies = pd.get_dummies(results_df["poverty_category"])
    cat_dummies[DIVISION_COLUMN] = results_df[DIVISION_COLUMN].values
    cat_share = (
        cat_dummies.groupby(DIVISION_COLUMN).mean().round(3) * 100
    )

    division_df = pd.concat([division_mean, division_count, cat_share], axis=1)
    division_df = division_df.sort_values("mepi_score", ascending=False)
    return division_df.reset_index()


def aggregate_by_zone(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate MEPI results by geographic zone (if ``geographic_zone`` column exists).

    Parameters
    ----------
    results_df : pd.DataFrame
        MEPI results with a ``geographic_zone`` column added by
        ``data_utils.assign_geographic_zone()``.

    Returns
    -------
    pd.DataFrame
        Zone-level mean MEPI scores.
    """
    zone_col = "geographic_zone"
    if zone_col not in results_df.columns:
        raise ValueError(
            "Column 'geographic_zone' not found. "
            "Run data_utils.assign_geographic_zone() first."
        )

    dim_score_cols = [
        f"{d}_score" for d in DIMENSIONS if f"{d}_score" in results_df.columns
    ]
    agg_cols = ["mepi_score"] + dim_score_cols
    zone_df = (
        results_df.groupby(zone_col)[agg_cols].mean().round(4)
    )
    zone_df["n_upazilas"] = results_df.groupby(zone_col).size()
    return zone_df.sort_values("mepi_score", ascending=False).reset_index()


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================


def export_results(
    results_df: pd.DataFrame,
    filepath: str,
    include_district_summary: bool = True,
    include_division_summary: bool = True,
) -> str:
    """
    Export MEPI results to CSV or Excel.

    Parameters
    ----------
    results_df : pd.DataFrame
        Full MEPI results DataFrame.
    filepath : str
        Destination file path.  Use ``.csv`` for CSV, ``.xlsx`` for Excel.
    include_district_summary : bool, optional
        If True and format is Excel, add a district-summary sheet.
    include_division_summary : bool, optional
        If True and format is Excel, add a division-summary sheet.

    Returns
    -------
    str
        Absolute path to the saved file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    ext = os.path.splitext(filepath)[-1].lower()

    if ext == ".csv":
        results_df.to_csv(filepath, index=False)
        print(f"Results exported to CSV: {filepath}")

    elif ext in (".xlsx", ".xls"):
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            results_df.to_excel(writer, sheet_name="MEPI_Results", index=False)

            if include_district_summary and DISTRICT_COLUMN in results_df.columns:
                try:
                    district_df = aggregate_by_district(results_df)
                    district_df.to_excel(
                        writer, sheet_name="District_Summary", index=False
                    )
                except Exception as exc:
                    print(f"Warning: Could not write district summary – {exc}")

            if include_division_summary and DIVISION_COLUMN in results_df.columns:
                try:
                    division_df = aggregate_by_division(results_df)
                    division_df.to_excel(
                        writer, sheet_name="Division_Summary", index=False
                    )
                except Exception as exc:
                    print(f"Warning: Could not write division summary – {exc}")

        print(f"Results exported to Excel: {filepath}")
    else:
        raise ValueError(
            f"Unsupported export format '{ext}'. Use .csv or .xlsx."
        )

    return os.path.abspath(filepath)


# =============================================================================
# SUMMARY TABLE HELPERS
# =============================================================================


def build_summary_table(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a concise summary table suitable for publication or reporting.

    Returns a DataFrame with one row per upazila containing:
    rank, name, district, division, MEPI score, poverty category,
    and dimension scores (all rounded).

    Parameters
    ----------
    results_df : pd.DataFrame
        MEPI results DataFrame.

    Returns
    -------
    pd.DataFrame
    """
    cols = []
    for c in [
        UPAZILA_ID_COLUMN,
        UPAZILA_NAME_COLUMN,
        DISTRICT_COLUMN,
        DIVISION_COLUMN,
    ]:
        if c in results_df.columns:
            cols.append(c)

    cols.append("mepi_score")
    cols.append("poverty_category")

    for dim in DIMENSIONS:
        sc = f"{dim}_score"
        if sc in results_df.columns:
            cols.append(sc)

    if "n_dimensions_deprived" in results_df.columns:
        cols.append("n_dimensions_deprived")

    table = results_df[cols].sort_values("mepi_score", ascending=False).copy()
    table.insert(0, "rank", range(1, len(table) + 1))

    # Round numeric columns
    numeric_cols = table.select_dtypes(include="number").columns
    table[numeric_cols] = table[numeric_cols].round(4)

    return table.reset_index(drop=True)


def sensitivity_comparison_table(
    sensitivity_results: dict,
    scheme_labels: list = None,
) -> pd.DataFrame:
    """
    Create a side-by-side comparison of MEPI scores across weight schemes.

    Parameters
    ----------
    sensitivity_results : dict
        Output of ``MEPICalculator.calculate_with_sensitivity()``.
    scheme_labels : list, optional
        Human-readable labels for each scheme (e.g. ["Equal", "Alt-1", "Alt-2"]).

    Returns
    -------
    pd.DataFrame
        Pivot table with upazilas as rows and weight schemes as columns.
    """
    frames = []
    for i, result_df in sensitivity_results.items():
        label = scheme_labels[i] if scheme_labels and i < len(scheme_labels) else f"Scheme_{i}"
        admin_cols = [
            c for c in [UPAZILA_ID_COLUMN, UPAZILA_NAME_COLUMN] if c in result_df.columns
        ]
        sub = result_df[admin_cols + ["mepi_score"]].copy()
        sub = sub.rename(columns={"mepi_score": label})
        frames.append(sub)

    if not frames:
        return pd.DataFrame()

    comparison = frames[0]
    admin_cols = [
        c for c in [UPAZILA_ID_COLUMN, UPAZILA_NAME_COLUMN] if c in comparison.columns
    ]
    for frame in frames[1:]:
        merge_on = [c for c in admin_cols if c in frame.columns]
        comparison = comparison.merge(frame, on=merge_on, how="outer")

    # Add a column showing the range (max - min) across schemes
    score_cols = [c for c in comparison.columns if c not in admin_cols]
    comparison["score_range"] = comparison[score_cols].max(axis=1) - comparison[score_cols].min(axis=1)

    return comparison.round(4)
