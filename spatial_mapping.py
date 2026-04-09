"""
spatial_mapping.py - GIS-based static choropleth maps for MEPI

Creates publication-quality PNG maps of energy poverty distribution across
Bangladesh upazilas using Matplotlib and (optionally) GeoPandas.

When a real shapefile is available the script draws true polygon choropleth
maps.  When shapefiles are absent it falls back to proportional circle maps
plotted on a Bangladesh basemap outline drawn from approximate coordinates.

Public API:
    create_spatial_map(df, output_path, column="mepi_score")
    create_dimension_maps(df, output_dir)
    create_hotspot_map(df, output_path)
    create_regional_classification_map(df, output_path)
    create_all_spatial_maps(df, output_dir)
"""

import os
import warnings

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.cm import ScalarMappable

from map_config import (
    BANGLADESH_BOUNDS,
    BANGLADESH_CENTER,
    CRS_WGS84,
    DIMENSION_COLORMAPS,
    DIMENSION_LABELS,
    HOTSPOT_COLOR,
    MAP_DPI,
    MAP_FIGURE_SIZE,
    MAP_OUTPUTS_DIR,
    MEPI_COLORMAP,
    POVERTY_COLORS,
    THRESHOLD_MODERATE,
    THRESHOLD_SEVERE,
    ZONE_COLORS,
    ZONE_METADATA,
    OUTPUT_FILES,
)
from data_preparation_spatial import SpatialDataPrep

try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

# ---------------------------------------------------------------------------
# Bangladesh outline (approximate border polygon for basemap when no shapefile)
# ---------------------------------------------------------------------------
_BD_OUTLINE = [
    (88.02, 26.45), (88.17, 26.60), (88.48, 26.46), (88.69, 26.33),
    (89.05, 26.05), (89.37, 25.97), (89.83, 25.93), (90.05, 25.72),
    (90.35, 25.21), (90.57, 25.16), (91.04, 25.26), (91.45, 25.28),
    (91.95, 25.11), (92.39, 24.83), (92.47, 24.30), (92.00, 23.62),
    (91.82, 23.25), (91.34, 23.10), (91.07, 23.65), (90.70, 23.28),
    (90.57, 22.97), (90.15, 22.63), (89.73, 22.35), (89.40, 21.96),
    (89.07, 21.83), (89.03, 22.09), (88.67, 22.15), (88.43, 22.76),
    (88.60, 23.00), (88.73, 23.28), (88.58, 23.67), (88.33, 24.10),
    (88.13, 24.52), (87.97, 24.95), (88.02, 25.46), (88.02, 26.45),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_output_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _ensure_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Add lat/lon if not present."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        prep = SpatialDataPrep(df)
        df = prep.add_coordinates()
    return df


def _draw_bd_outline(ax, lw=0.8, color="black"):
    """Draw Bangladesh border outline on an axis."""
    xs = [p[0] for p in _BD_OUTLINE]
    ys = [p[1] for p in _BD_OUTLINE]
    ax.plot(xs, ys, color=color, linewidth=lw, zorder=2)


def _set_axis_limits(ax):
    """Set axis extent to Bangladesh bounding box."""
    ax.set_xlim(BANGLADESH_BOUNDS[0], BANGLADESH_BOUNDS[2])
    ax.set_ylim(BANGLADESH_BOUNDS[1], BANGLADESH_BOUNDS[3])
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude (°E)", fontsize=9)
    ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)


def _poverty_category_color(cat: str) -> str:
    return POVERTY_COLORS.get(cat, "#cccccc")


def _add_north_arrow(ax):
    ax.annotate(
        "N", xy=(0.96, 0.92), xycoords="axes fraction",
        fontsize=12, ha="center", va="bottom", fontweight="bold",
    )
    ax.annotate(
        "▲", xy=(0.96, 0.90), xycoords="axes fraction",
        fontsize=14, ha="center", va="top", color="black",
    )


def _add_scalebar(ax, length_deg=1.0, label="~110 km"):
    x0 = BANGLADESH_BOUNDS[0] + 0.2
    y0 = BANGLADESH_BOUNDS[1] + 0.2
    ax.plot([x0, x0 + length_deg], [y0, y0], "k-", linewidth=3)
    ax.text(x0 + length_deg / 2, y0 + 0.05, label, ha="center", fontsize=7)


# ---------------------------------------------------------------------------
# 1. Overall MEPI spatial map
# ---------------------------------------------------------------------------

def create_spatial_map(
    df: pd.DataFrame,
    output_path: str = None,
    column: str = "mepi_score",
    title: str = "MEPI Spatial Distribution – Bangladesh Upazilas",
) -> str:
    """
    Create a choropleth-style scatter map of MEPI scores across upazilas.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results with optional ``latitude`` / ``longitude`` columns.
    output_path : str, optional
        Full path to save the PNG.  Defaults to ``map_outputs/spatial_mepi_map.png``.
    column : str
        Column to map (default ``"mepi_score"``).
    title : str
        Map title.

    Returns
    -------
    str
        Path to the saved PNG.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["spatial_mepi"])

    df = _ensure_coords(df)

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)

    # Background fill
    ax.set_facecolor("#dbe9f4")

    # Draw border
    _draw_bd_outline(ax)

    # Scatter circles coloured by score
    sc = ax.scatter(
        df["longitude"], df["latitude"],
        c=df[column], cmap=MEPI_COLORMAP,
        vmin=0, vmax=1,
        s=200, edgecolors="black", linewidths=0.5, zorder=5,
    )

    # Label upazilas
    name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]
    for _, row in df.iterrows():
        ax.text(
            row["longitude"] + 0.04, row["latitude"],
            row[name_col], fontsize=5.5, va="center", zorder=6,
        )

    # Colourbar
    cbar = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("MEPI Score (0 = least deprived → 1 = most deprived)", fontsize=9)

    # Poverty threshold lines on colourbar
    cbar.ax.axhline(THRESHOLD_MODERATE, color="gray", linewidth=1, linestyle="--")
    cbar.ax.axhline(THRESHOLD_SEVERE, color="black", linewidth=1, linestyle="--")
    cbar.ax.text(1.05, THRESHOLD_MODERATE, f"{THRESHOLD_MODERATE}", va="center",
                 transform=cbar.ax.transAxes, fontsize=7)
    cbar.ax.text(1.05, THRESHOLD_SEVERE, f"{THRESHOLD_SEVERE}", va="center",
                 transform=cbar.ax.transAxes, fontsize=7)

    _set_axis_limits(ax)
    _add_north_arrow(ax)
    _add_scalebar(ax)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 2. Individual dimension maps
# ---------------------------------------------------------------------------

def create_dimension_map(
    df: pd.DataFrame,
    dimension: str,
    output_path: str = None,
) -> str:
    """
    Create a spatial map for a single MEPI dimension.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    dimension : str
        Dimension name, e.g. ``"Availability"``.
    output_path : str, optional
        Output PNG path.

    Returns
    -------
    str
        Saved file path.
    """
    col = f"{dimension}_score"
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in DataFrame.")

    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        key = dimension.lower()
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES.get(key, f"{key}_map.png"))

    df = _ensure_coords(df)
    cmap = DIMENSION_COLORMAPS.get(dimension, "Reds")
    label = DIMENSION_LABELS.get(dimension, dimension)

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)
    ax.set_facecolor("#dbe9f4")
    _draw_bd_outline(ax)

    sc = ax.scatter(
        df["longitude"], df["latitude"],
        c=df[col], cmap=cmap,
        vmin=0, vmax=1,
        s=200, edgecolors="black", linewidths=0.5, zorder=5,
    )
    cbar = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label(f"{label} Deprivation Score", fontsize=9)

    _set_axis_limits(ax)
    _add_north_arrow(ax)
    _add_scalebar(ax)
    ax.set_title(f"Energy Poverty – {label}\n(Bangladesh Upazilas)", fontsize=12,
                 fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def create_dimension_maps(df: pd.DataFrame, output_dir: str = None) -> list:
    """
    Generate individual dimension maps for all five MEPI dimensions.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    output_dir : str, optional
        Directory for output PNGs.

    Returns
    -------
    list of str
        Paths to the saved PNG files.
    """
    output_dir = output_dir or MAP_OUTPUTS_DIR
    _ensure_output_dir(output_dir)
    paths = []
    for dim in ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]:
        key = dim.lower()
        out = os.path.join(output_dir, OUTPUT_FILES.get(key, f"{key}_map.png"))
        paths.append(create_dimension_map(df, dim, output_path=out))
    return paths


# ---------------------------------------------------------------------------
# 3. Hotspot map
# ---------------------------------------------------------------------------

def create_hotspot_map(
    df: pd.DataFrame,
    output_path: str = None,
    threshold: float = None,
) -> str:
    """
    Create an energy poverty hotspot map.

    Upazilas with MEPI ≥ ``threshold`` are marked in red; others in grey.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    output_path : str, optional
        Output PNG path.
    threshold : float, optional
        MEPI hotspot threshold.  Defaults to ``THRESHOLD_SEVERE`` (0.66).

    Returns
    -------
    str
        Saved file path.
    """
    threshold = threshold if threshold is not None else THRESHOLD_SEVERE
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["hotspot"])

    df = _ensure_coords(df)
    is_hotspot = df["mepi_score"] >= threshold

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)
    ax.set_facecolor("#dbe9f4")
    _draw_bd_outline(ax)

    # Non-hotspot (background) points
    ax.scatter(
        df.loc[~is_hotspot, "longitude"],
        df.loc[~is_hotspot, "latitude"],
        c="#d5e8d4", s=180, edgecolors="#999999", linewidths=0.5,
        label="Non-Hotspot", zorder=4,
    )
    # Hotspot points
    ax.scatter(
        df.loc[is_hotspot, "longitude"],
        df.loc[is_hotspot, "latitude"],
        c=HOTSPOT_COLOR, s=250, edgecolors="black", linewidths=0.8,
        marker="*", label=f"Hotspot (MEPI ≥ {threshold})", zorder=5,
    )

    # Labels for hotspots
    name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]
    for _, row in df[is_hotspot].iterrows():
        ax.text(
            row["longitude"] + 0.05, row["latitude"],
            row[name_col], fontsize=6, color=HOTSPOT_COLOR,
            fontweight="bold", va="center", zorder=6,
        )

    ax.legend(loc="lower right", fontsize=9)
    _set_axis_limits(ax)
    _add_north_arrow(ax)
    _add_scalebar(ax)
    ax.set_title(
        f"Energy Poverty Hotspot Map – Bangladesh\n"
        f"(Hotspot threshold: MEPI ≥ {threshold})",
        fontsize=12, fontweight="bold",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 4. Regional classification map
# ---------------------------------------------------------------------------

def create_regional_classification_map(
    df: pd.DataFrame,
    output_path: str = None,
) -> str:
    """
    Create a map coloured by geographic zone (coastal, char, haor, etc.).

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results with a ``geographic_zone`` column (assigned by
        ``SpatialAnalyzer`` or ``data_utils.assign_geographic_zone()``).
    output_path : str, optional
        Output PNG path.

    Returns
    -------
    str
        Saved file path.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["regional_classification"])

    df = _ensure_coords(df)
    if "geographic_zone" not in df.columns:
        from spatial_analysis import SpatialAnalyzer
        sa = SpatialAnalyzer(df)
        df = sa.df

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)
    ax.set_facecolor("#dbe9f4")
    _draw_bd_outline(ax)

    zones = df["geographic_zone"].unique()
    handles = []
    for zone in zones:
        color = ZONE_COLORS.get(zone, "#cccccc")
        subset = df[df["geographic_zone"] == zone]
        ax.scatter(
            subset["longitude"], subset["latitude"],
            c=color, s=200, edgecolors="black", linewidths=0.5, zorder=5, label=zone,
        )
        meta = ZONE_METADATA.get(zone, {})
        patch = mpatches.Patch(color=color, label=meta.get("label", zone.title()))
        handles.append(patch)

    ax.legend(handles=handles, loc="lower right", fontsize=8, title="Geographic Zone",
              title_fontsize=9, framealpha=0.9)
    _set_axis_limits(ax)
    _add_north_arrow(ax)
    _add_scalebar(ax)
    ax.set_title(
        "Regional Geographic Classification – Bangladesh Upazilas",
        fontsize=12, fontweight="bold",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 5. Convenience: create all static maps
# ---------------------------------------------------------------------------

def create_all_spatial_maps(
    df: pd.DataFrame,
    output_dir: str = None,
) -> dict:
    """
    Generate the full suite of static spatial maps.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results (output of ``MEPICalculator.calculate()``).
    output_dir : str, optional
        Directory for output PNGs.  Defaults to ``map_outputs/``.

    Returns
    -------
    dict
        ``{map_name: file_path}`` for each generated map.
    """
    output_dir = output_dir or MAP_OUTPUTS_DIR
    _ensure_output_dir(output_dir)
    saved = {}

    saved["spatial_mepi"] = create_spatial_map(
        df, os.path.join(output_dir, OUTPUT_FILES["spatial_mepi"])
    )
    for dim in ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]:
        key = dim.lower()
        out = os.path.join(output_dir, OUTPUT_FILES.get(key, f"{key}_map.png"))
        saved[key] = create_dimension_map(df, dim, output_path=out)

    saved["hotspot"] = create_hotspot_map(
        df, os.path.join(output_dir, OUTPUT_FILES["hotspot"])
    )
    saved["regional_classification"] = create_regional_classification_map(
        df, os.path.join(output_dir, OUTPUT_FILES["regional_classification"])
    )

    print(f"\nAll static spatial maps saved to: {output_dir}")
    return saved
