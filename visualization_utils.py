"""
visualization_utils.py - Utility functions for MEPI visualizations

Provides helper functions for consistent styling, color mapping, axis
formatting, and chart construction across all MEPI visualization scripts.
"""

import os
import logging

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from visualization_config import (
    POVERTY_COLORS,
    DIMENSION_COLORS,
    ZONE_COLORS,
    FONT_FAMILY,
    FONT_SIZES,
    PLOT_STYLE,
    PLOT_STYLE_FALLBACK,
    GRID_ALPHA,
    DPI,
    OUTPUT_DIR,
    IMAGE_FORMAT,
    POVERTY_THRESHOLD_MODERATE,
    POVERTY_THRESHOLD_SEVERE,
    THRESHOLD_LINE_STYLE,
    THRESHOLD_LINE_WIDTH,
    DIMENSIONS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Style setup
# ---------------------------------------------------------------------------

def apply_global_style():
    """Apply consistent matplotlib style and font settings globally."""
    try:
        plt.style.use(PLOT_STYLE)
    except OSError:
        try:
            plt.style.use(PLOT_STYLE_FALLBACK)
        except OSError:
            pass  # fall back to matplotlib default

    matplotlib.rcParams.update(
        {
            "font.family": FONT_FAMILY,
            "axes.titlesize": FONT_SIZES["title"],
            "axes.titleweight": "bold",
            "axes.labelsize": FONT_SIZES["axis_label"],
            "xtick.labelsize": FONT_SIZES["tick_label"],
            "ytick.labelsize": FONT_SIZES["tick_label"],
            "legend.fontsize": FONT_SIZES["legend"],
            "figure.dpi": DPI,
            "axes.grid": True,
            "grid.alpha": GRID_ALPHA,
        }
    )


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def get_poverty_color(category: str) -> str:
    """Return colorblind-friendly hex color for a poverty category string."""
    return POVERTY_COLORS.get(category, "#999999")


def get_dimension_color(dimension: str) -> str:
    """Return colorblind-friendly hex color for a dimension name."""
    return DIMENSION_COLORS.get(dimension, "#999999")


def get_zone_color(zone: str) -> str:
    """Return color for a geographic zone."""
    return ZONE_COLORS.get(zone.lower(), "#999999")


def map_poverty_colors(series: pd.Series) -> list:
    """Map a Series of poverty category strings to a list of hex colors."""
    return [get_poverty_color(v) for v in series]


# ---------------------------------------------------------------------------
# Legend helpers
# ---------------------------------------------------------------------------

def poverty_legend_patches() -> list:
    """Return a list of mpatches.Patch for the poverty category legend."""
    return [
        mpatches.Patch(color=color, label=label)
        for label, color in POVERTY_COLORS.items()
    ]


def dimension_legend_patches(dimensions=None) -> list:
    """Return legend patches for dimensions."""
    dims = dimensions or DIMENSIONS
    return [
        mpatches.Patch(color=DIMENSION_COLORS.get(d, "#999999"), label=d)
        for d in dims
    ]


# ---------------------------------------------------------------------------
# Axis helpers
# ---------------------------------------------------------------------------

def add_poverty_threshold_lines(ax, orientation: str = "vertical"):
    """
    Add dashed threshold lines at 0.33 (moderate) and 0.66 (severe) to an axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    orientation : str
        'vertical' for vertical lines (x-axis is score),
        'horizontal' for horizontal lines (y-axis is score).
    """
    if orientation == "vertical":
        ax.axvline(
            POVERTY_THRESHOLD_MODERATE,
            color="#E69F00",
            linestyle=THRESHOLD_LINE_STYLE,
            linewidth=THRESHOLD_LINE_WIDTH,
            label=f"Moderate threshold ({POVERTY_THRESHOLD_MODERATE})",
        )
        ax.axvline(
            POVERTY_THRESHOLD_SEVERE,
            color="#D55E00",
            linestyle=THRESHOLD_LINE_STYLE,
            linewidth=THRESHOLD_LINE_WIDTH,
            label=f"Severe threshold ({POVERTY_THRESHOLD_SEVERE})",
        )
    else:
        ax.axhline(
            POVERTY_THRESHOLD_MODERATE,
            color="#E69F00",
            linestyle=THRESHOLD_LINE_STYLE,
            linewidth=THRESHOLD_LINE_WIDTH,
            label=f"Moderate threshold ({POVERTY_THRESHOLD_MODERATE})",
        )
        ax.axhline(
            POVERTY_THRESHOLD_SEVERE,
            color="#D55E00",
            linestyle=THRESHOLD_LINE_STYLE,
            linewidth=THRESHOLD_LINE_WIDTH,
            label=f"Severe threshold ({POVERTY_THRESHOLD_SEVERE})",
        )


def format_score_axis(ax, axis: str = "x"):
    """Set limits to [0, 1] and label the score axis."""
    label = "MEPI Score (0 = least deprived, 1 = most deprived)"
    if axis == "x":
        ax.set_xlim(0, 1)
        ax.set_xlabel(label)
    else:
        ax.set_ylim(0, 1)
        ax.set_ylabel(label)


def style_axes(ax, title: str = "", xlabel: str = "", ylabel: str = ""):
    """Apply standard title and axis labels to an Axes object."""
    if title:
        ax.set_title(title, fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=FONT_SIZES["axis_label"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=FONT_SIZES["axis_label"])


# ---------------------------------------------------------------------------
# Name column helper
# ---------------------------------------------------------------------------

def get_name_col(df: pd.DataFrame) -> str:
    """Return the upazila name column or first column if name column absent."""
    if "upazila_name" in df.columns:
        return "upazila_name"
    return df.columns[0]


# ---------------------------------------------------------------------------
# Dimension score columns
# ---------------------------------------------------------------------------

def dim_score_cols(df: pd.DataFrame) -> list:
    """Return list of dimension score column names present in df."""
    return [f"{d}_score" for d in DIMENSIONS if f"{d}_score" in df.columns]


# ---------------------------------------------------------------------------
# File saving
# ---------------------------------------------------------------------------

def ensure_output_dir(output_dir: str = OUTPUT_DIR) -> str:
    """Create the output directory if it does not exist and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_figure(fig: plt.Figure, filename: str, output_dir: str = OUTPUT_DIR,
                dpi: int = DPI, bbox_inches: str = "tight") -> str:
    """
    Save a matplotlib Figure to a PNG file.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    filename : str
        Filename without directory prefix (e.g. 'mepi_scores_by_upazila.png').
    output_dir : str
        Directory to save into.
    dpi : int
        Resolution.
    bbox_inches : str
        Passed to fig.savefig.

    Returns
    -------
    str
        Full path of the saved file.
    """
    ensure_output_dir(output_dir)
    if not filename.endswith(f".{IMAGE_FORMAT}"):
        filename = f"{filename}.{IMAGE_FORMAT}"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches, format=IMAGE_FORMAT)
    logger.info("Saved: %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# Zone classification helper
# ---------------------------------------------------------------------------

def classify_zone(district: str, geographic_zones: dict) -> str:
    """
    Return the geographic zone name for a district.

    Parameters
    ----------
    district : str
    geographic_zones : dict
        Mapping of zone_name -> {'districts': [...]}

    Returns
    -------
    str
        Zone name, or 'plain' if not found.
    """
    for zone, info in geographic_zones.items():
        if district in info.get("districts", []):
            return zone
    return "plain"


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def summary_stats(series: pd.Series) -> dict:
    """Return a dict of basic descriptive statistics for a numeric Series."""
    return {
        "mean": series.mean(),
        "median": series.median(),
        "std": series.std(),
        "min": series.min(),
        "max": series.max(),
        "q1": series.quantile(0.25),
        "q3": series.quantile(0.75),
    }
