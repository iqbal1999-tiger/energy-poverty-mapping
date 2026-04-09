"""
data_utils.py - Data loading, validation, and pre-processing utilities

Provides helper functions for:
  - Loading CSV / Excel files
  - Validating that required indicator columns are present
  - Handling missing values
  - Min-max normalisation
  - Aggregating data to upazila level (if raw household data is supplied)

Usage:
    from data_utils import load_data, validate_data, handle_missing_values
    df = load_data("my_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
"""

import os
import warnings

import numpy as np
import pandas as pd

from config import (
    INDICATOR_COLUMNS,
    UPAZILA_ID_COLUMN,
    UPAZILA_NAME_COLUMN,
    DISTRICT_COLUMN,
    DIVISION_COLUMN,
    MISSING_VALUE_STRATEGY,
    GEOGRAPHIC_ZONES,
)


# =============================================================================
# DATA LOADING
# =============================================================================


def load_data(filepath: str, sheet_name=0) -> pd.DataFrame:
    """
    Load upazila-level indicator data from a CSV or Excel file.

    Parameters
    ----------
    filepath : str
        Path to a ``.csv`` or ``.xlsx`` / ``.xls`` file.
    sheet_name : str or int, optional
        Sheet name/index for Excel files.  Ignored for CSV.

    Returns
    -------
    pd.DataFrame
        Raw data with all columns preserved.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file extension is not supported.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")

    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".csv":
        df = pd.read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath, sheet_name=sheet_name)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Use .csv, .xlsx, or .xls."
        )

    print(f"Loaded {len(df)} rows and {len(df.columns)} columns from '{filepath}'.")
    return df


# =============================================================================
# DATA VALIDATION
# =============================================================================


def validate_data(df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
    """
    Validate that the DataFrame contains the required indicator columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.
    strict : bool, optional
        If True, raise an error when required columns are missing.
        If False (default), print a warning and continue.

    Returns
    -------
    pd.DataFrame
        The (unmodified) input DataFrame if validation passes.

    Raises
    ------
    ValueError
        If ``strict=True`` and required columns are missing.
    """
    missing_cols = [c for c in INDICATOR_COLUMNS if c not in df.columns]
    if missing_cols:
        msg = (
            f"The following required indicator columns are missing from the data:\n"
            f"  {missing_cols}\n"
            "Add these columns or adjust DIMENSION_INDICATORS in config.py."
        )
        if strict:
            raise ValueError(msg)
        warnings.warn(msg, UserWarning, stacklevel=2)

    # Check administrative columns (warn only)
    admin_cols = [
        UPAZILA_ID_COLUMN,
        UPAZILA_NAME_COLUMN,
        DISTRICT_COLUMN,
        DIVISION_COLUMN,
    ]
    missing_admin = [c for c in admin_cols if c not in df.columns]
    if missing_admin:
        warnings.warn(
            f"Administrative columns {missing_admin} not found. "
            "Results will lack location labels.",
            UserWarning,
            stacklevel=2,
        )

    # Check for duplicate upazila identifiers
    if UPAZILA_ID_COLUMN in df.columns and df[UPAZILA_ID_COLUMN].duplicated().any():
        n_dupes = df[UPAZILA_ID_COLUMN].duplicated().sum()
        warnings.warn(
            f"{n_dupes} duplicate upazila IDs detected. "
            "Consider aggregating to upazila level first.",
            UserWarning,
            stacklevel=2,
        )

    print(
        f"Validation complete. {len(df)} rows, "
        f"{len(missing_cols)} missing indicator column(s)."
    )
    return df


# =============================================================================
# MISSING VALUE HANDLING
# =============================================================================


def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = MISSING_VALUE_STRATEGY,
    columns: list = None,
) -> pd.DataFrame:
    """
    Handle missing values in indicator columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input data (will not be modified in place).
    strategy : str, optional
        One of ``"mean"``, ``"median"``, or ``"drop"``.
        Default is taken from ``config.MISSING_VALUE_STRATEGY``.
    columns : list, optional
        Columns to impute.  Defaults to ``config.INDICATOR_COLUMNS``.

    Returns
    -------
    pd.DataFrame
        DataFrame with missing values handled.
    """
    df = df.copy()
    cols = [c for c in (columns or INDICATOR_COLUMNS) if c in df.columns]

    total_missing = df[cols].isnull().sum().sum()
    if total_missing == 0:
        print("No missing values detected in indicator columns.")
        return df

    print(f"Found {total_missing} missing value(s) in indicator columns.")

    if strategy == "drop":
        before = len(df)
        df = df.dropna(subset=cols)
        print(f"Dropped {before - len(df)} row(s) with missing indicator values.")
    elif strategy in ("mean", "median"):
        fill_fn = df[cols].mean() if strategy == "mean" else df[cols].median()
        df[cols] = df[cols].fillna(fill_fn)
        print(f"Imputed missing values using column {strategy}.")
    else:
        raise ValueError(
            f"Unknown missing value strategy '{strategy}'. "
            "Choose 'mean', 'median', or 'drop'."
        )

    return df


# =============================================================================
# NORMALISATION
# =============================================================================


def normalise_minmax(
    df: pd.DataFrame,
    columns: list = None,
    feature_range: tuple = (0.0, 1.0),
) -> pd.DataFrame:
    """
    Apply min-max normalisation to the specified columns.

    This is a *standalone* utility; the MEPICalculator applies its own
    direction-aware normalisation internally.  Use this function when you want
    a simple 0-1 scaling for exploratory analysis or visualisation.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.
    columns : list, optional
        Columns to normalise.  Defaults to ``config.INDICATOR_COLUMNS``.
    feature_range : tuple, optional
        Desired output range (min, max).  Default ``(0.0, 1.0)``.

    Returns
    -------
    pd.DataFrame
        New DataFrame with the specified columns normalised.
    """
    df = df.copy()
    cols = [c for c in (columns or INDICATOR_COLUMNS) if c in df.columns]
    lo, hi = feature_range

    for col in cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max == col_min:
            df[col] = lo  # constant column → assign lower bound
        else:
            df[col] = lo + (df[col] - col_min) / (col_max - col_min) * (hi - lo)

    return df


# =============================================================================
# UPAZILA-LEVEL AGGREGATION
# =============================================================================


def aggregate_to_upazila(
    df: pd.DataFrame,
    group_col: str = UPAZILA_ID_COLUMN,
    agg_func: str = "mean",
    keep_cols: list = None,
) -> pd.DataFrame:
    """
    Aggregate household-level (or survey-level) data to upazila level.

    Parameters
    ----------
    df : pd.DataFrame
        Raw household-level data that includes an upazila identifier.
    group_col : str, optional
        Column used to group rows.  Default: ``config.UPAZILA_ID_COLUMN``.
    agg_func : str, optional
        Aggregation function: ``"mean"`` (default), ``"median"``, or ``"sum"``.
    keep_cols : list, optional
        Non-numeric administrative columns to include via ``first()`` aggregation.
        Defaults to ``[upazila_name, district, division]``.

    Returns
    -------
    pd.DataFrame
        Upazila-level DataFrame with numeric indicators aggregated.
    """
    if group_col not in df.columns:
        raise ValueError(
            f"Group column '{group_col}' not found in the DataFrame."
        )

    if keep_cols is None:
        keep_cols = [
            c
            for c in [UPAZILA_NAME_COLUMN, DISTRICT_COLUMN, DIVISION_COLUMN]
            if c in df.columns
        ]

    indicator_cols = [c for c in INDICATOR_COLUMNS if c in df.columns]

    agg_map = {c: agg_func for c in indicator_cols}
    agg_map.update({c: "first" for c in keep_cols})

    aggregated = df.groupby(group_col).agg(agg_map).reset_index()
    print(
        f"Aggregated {len(df)} rows to {len(aggregated)} upazilas "
        f"using '{agg_func}'."
    )
    return aggregated


# =============================================================================
# GEOGRAPHIC ZONE ASSIGNMENT
# =============================================================================


def assign_geographic_zone(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a ``geographic_zone`` column based on the district.

    Uses the zone definitions in ``config.GEOGRAPHIC_ZONES``.
    Upazilas whose district does not appear in any zone list are
    classified as ``"plain"``.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``district`` column.

    Returns
    -------
    pd.DataFrame
        Copy of the DataFrame with an additional ``geographic_zone`` column.
    """
    if DISTRICT_COLUMN not in df.columns:
        warnings.warn(
            f"Column '{DISTRICT_COLUMN}' not found; cannot assign geographic zones.",
            UserWarning,
            stacklevel=2,
        )
        return df

    df = df.copy()

    # Build a lookup: district_name -> zone_name
    district_to_zone = {}
    for zone, info in GEOGRAPHIC_ZONES.items():
        for district in info.get("districts", []):
            # A district can appear in multiple zones (e.g. Satkhira in both
            # coastal and sundarbans); the last one listed wins – override below
            # if a more specific zone is preferred.
            district_to_zone[district] = zone

    df["geographic_zone"] = df[DISTRICT_COLUMN].map(
        lambda d: district_to_zone.get(d, "plain")
    )
    return df


# =============================================================================
# SUMMARY HELPERS
# =============================================================================


def data_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return descriptive statistics for all indicator columns in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.

    Returns
    -------
    pd.DataFrame
        Transposed describe() output for indicator columns.
    """
    cols = [c for c in INDICATOR_COLUMNS if c in df.columns]
    return df[cols].describe().T
