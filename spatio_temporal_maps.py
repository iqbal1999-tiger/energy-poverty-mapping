"""
spatio_temporal_maps.py - Combined spatio-temporal MEPI visualisations

Creates multi-panel comparison maps, poverty-change maps, and animated GIFs
showing how energy poverty evolves across Bangladesh over time.

Public API:
    create_temporal_comparison_map(temporal_dict, output_path)
    create_poverty_change_map(df_base, df_end, output_path)
    create_temporal_animation(temporal_dict, output_path)
    create_hotspot_evolution_map(temporal_dict, output_path)
    create_all_spatio_temporal_maps(temporal_dict, output_dir)
"""

import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from map_config import (
    BANGLADESH_BOUNDS,
    IMPROVING_COLOR,
    MAP_DPI,
    MAP_FIGURE_SIZE,
    MAP_FIGURE_SIZE_WIDE,
    MAP_OUTPUTS_DIR,
    MEPI_COLORMAP,
    OUTPUT_FILES,
    STABLE_COLOR,
    WORSENING_COLOR,
    ANIMATION_DURATION_S,
    ANIMATION_LOOP,
)
from data_preparation_spatial import SpatialDataPrep
from spatial_mapping import _draw_bd_outline, _set_axis_limits, _add_north_arrow, _ensure_output_dir
from temporal_analysis import TemporalAnalyzer

try:
    import imageio.v2 as imageio
    HAS_IMAGEIO = True
except ImportError:  # pragma: no cover
    try:
        import imageio
        HAS_IMAGEIO = True
    except ImportError:
        HAS_IMAGEIO = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_coords(df: pd.DataFrame) -> pd.DataFrame:
    if "latitude" not in df.columns or "longitude" not in df.columns:
        prep = SpatialDataPrep(df)
        df = prep.add_coordinates()
    return df


# ---------------------------------------------------------------------------
# 1. Multi-panel temporal comparison map
# ---------------------------------------------------------------------------

def create_temporal_comparison_map(
    temporal_dict: dict,
    output_path: str = None,
    max_panels: int = 6,
) -> str:
    """
    Create a multi-panel map showing MEPI distribution for multiple years.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` of MEPI results.
    output_path : str, optional
        Output PNG path.
    max_panels : int
        Maximum number of year panels to show.

    Returns
    -------
    str
        Saved file path.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["temporal_comparison"])

    years = sorted(temporal_dict.keys())[:max_panels]
    n = len(years)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(ncols * 5, nrows * 5),
        dpi=MAP_DPI,
    )
    axes = np.array(axes).flatten()

    for idx, year in enumerate(years):
        ax = axes[idx]
        df = _ensure_coords(temporal_dict[year].copy())

        ax.set_facecolor("#dbe9f4")
        _draw_bd_outline(ax, lw=0.6)

        sc = ax.scatter(
            df["longitude"], df["latitude"],
            c=df["mepi_score"], cmap=MEPI_COLORMAP,
            vmin=0, vmax=1,
            s=80, edgecolors="black", linewidths=0.3, zorder=5,
        )
        ax.set_xlim(BANGLADESH_BOUNDS[0], BANGLADESH_BOUNDS[2])
        ax.set_ylim(BANGLADESH_BOUNDS[1], BANGLADESH_BOUNDS[3])
        ax.set_aspect("equal")
        ax.set_title(str(year), fontsize=11, fontweight="bold")
        ax.tick_params(labelsize=6)
        ax.grid(True, linestyle="--", linewidth=0.3, alpha=0.4)

    # Hide unused axes
    for ax in axes[n:]:
        ax.set_visible(False)

    # Shared colourbar
    sm = plt.cm.ScalarMappable(cmap=MEPI_COLORMAP, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes[:n], fraction=0.015, pad=0.02)
    cbar.set_label("MEPI Score", fontsize=10)

    fig.suptitle(
        f"MEPI Temporal Comparison ({years[0]}–{years[-1]})\nBangladesh Upazilas",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 2. Poverty change map
# ---------------------------------------------------------------------------

def create_poverty_change_map(
    temporal_dict: dict,
    output_path: str = None,
    base_year: int = None,
    end_year: int = None,
    threshold: float = 0.03,
) -> str:
    """
    Create a map showing where energy poverty improved or deteriorated.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` of MEPI results.
    output_path : str, optional
        Output PNG path.
    base_year : int, optional
        Starting year for comparison.
    end_year : int, optional
        Ending year for comparison.
    threshold : float
        Minimum absolute MEPI change to classify as improving/worsening.

    Returns
    -------
    str
        Saved file path.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["poverty_change"])

    ta = TemporalAnalyzer(temporal_dict)
    change_df = ta.classify_trend(base_year, end_year, threshold=threshold)

    years = sorted(temporal_dict.keys())
    base_year = base_year or years[0]
    end_year = end_year or years[-1]

    # Merge coordinates from the base-year data
    base_df = _ensure_coords(temporal_dict[base_year].copy())
    name_col = "upazila_name" if "upazila_name" in base_df.columns else base_df.columns[0]
    coord_df = base_df[[name_col, "latitude", "longitude"]]
    plot_df = change_df.merge(coord_df, on=name_col, how="left")

    color_map = {
        "Improving": IMPROVING_COLOR,
        "Stable": STABLE_COLOR,
        "Worsening": WORSENING_COLOR,
    }

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)
    ax.set_facecolor("#dbe9f4")
    _draw_bd_outline(ax)

    for trend, grp in plot_df.groupby("trend"):
        ax.scatter(
            grp["longitude"], grp["latitude"],
            c=color_map.get(trend, "#cccccc"),
            s=200, edgecolors="black", linewidths=0.5, zorder=5, label=trend,
        )

    # Legend
    patches = [
        mpatches.Patch(color=IMPROVING_COLOR, label=f"Improving (Δ < −{threshold})"),
        mpatches.Patch(color=STABLE_COLOR, label=f"Stable (|Δ| ≤ {threshold})"),
        mpatches.Patch(color=WORSENING_COLOR, label=f"Worsening (Δ > {threshold})"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8, framealpha=0.9)

    _set_axis_limits(ax)
    _add_north_arrow(ax)
    ax.set_title(
        f"Energy Poverty Change Map: {base_year}→{end_year}\n"
        "Green = Improving | Amber = Stable | Red = Worsening",
        fontsize=11, fontweight="bold",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 3. Temporal animation (GIF)
# ---------------------------------------------------------------------------

def create_temporal_animation(
    temporal_dict: dict,
    output_path: str = None,
) -> str:
    """
    Create an animated GIF showing MEPI changes year by year.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` of MEPI results.
    output_path : str, optional
        Output GIF path.

    Returns
    -------
    str
        Saved file path.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["temporal_animation"])

    if not HAS_IMAGEIO:
        print("imageio not installed – skipping GIF animation. "
              "Install with: pip install imageio")
        return ""

    years = sorted(temporal_dict.keys())
    tmp_frames = []
    tmp_dir = os.path.join(MAP_OUTPUTS_DIR, "_tmp_frames")
    os.makedirs(tmp_dir, exist_ok=True)

    for year in years:
        df = _ensure_coords(temporal_dict[year].copy())

        fig, ax = plt.subplots(figsize=(8, 7), dpi=100)
        ax.set_facecolor("#dbe9f4")
        _draw_bd_outline(ax, lw=0.8)

        sc = ax.scatter(
            df["longitude"], df["latitude"],
            c=df["mepi_score"], cmap=MEPI_COLORMAP,
            vmin=0, vmax=1,
            s=120, edgecolors="black", linewidths=0.4, zorder=5,
        )
        cbar = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.02)
        cbar.set_label("MEPI Score", fontsize=8)

        mean_score = df["mepi_score"].mean()
        ax.set_xlim(BANGLADESH_BOUNDS[0], BANGLADESH_BOUNDS[2])
        ax.set_ylim(BANGLADESH_BOUNDS[1], BANGLADESH_BOUNDS[3])
        ax.set_aspect("equal")
        ax.tick_params(labelsize=7)
        ax.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
        ax.set_title(
            f"Energy Poverty Index (MEPI) – {year}\nMean MEPI = {mean_score:.3f}",
            fontsize=11, fontweight="bold",
        )

        frame_path = os.path.join(tmp_dir, f"frame_{year}.png")
        fig.savefig(frame_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        tmp_frames.append(frame_path)

    # Build GIF
    images = [imageio.imread(f) for f in tmp_frames]
    imageio.mimsave(
        output_path,
        images,
        duration=ANIMATION_DURATION_S,
        loop=ANIMATION_LOOP,
    )

    # Clean up temporary frames
    for f in tmp_frames:
        os.remove(f)
    os.rmdir(tmp_dir)

    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 4. Hotspot evolution map
# ---------------------------------------------------------------------------

def create_hotspot_evolution_map(
    temporal_dict: dict,
    output_path: str = None,
    threshold: float = 0.60,
) -> str:
    """
    Create a map showing persistent vs emerging vs resolved hotspots.

    A location is a hotspot in a given year if its MEPI ≥ ``threshold``.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` of MEPI results.
    output_path : str, optional
        Output PNG path.
    threshold : float
        MEPI hotspot threshold.

    Returns
    -------
    str
        Saved file path.
    """
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, "hotspot_evolution_map.png")

    years = sorted(temporal_dict.keys())
    first_year = years[0]
    last_year = years[-1]

    base_df = _ensure_coords(temporal_dict[first_year].copy())
    end_df = _ensure_coords(temporal_dict[last_year].copy())
    name_col = "upazila_name" if "upazila_name" in base_df.columns else base_df.columns[0]

    base_df["hot_base"] = base_df["mepi_score"] >= threshold
    end_df["hot_end"] = end_df["mepi_score"] >= threshold
    merged = base_df[[name_col, "latitude", "longitude", "hot_base"]].merge(
        end_df[[name_col, "hot_end"]], on=name_col
    )

    def _classify(row):
        if row["hot_base"] and row["hot_end"]:
            return "Persistent"
        elif row["hot_base"] and not row["hot_end"]:
            return "Resolved"
        elif not row["hot_base"] and row["hot_end"]:
            return "Emerging"
        return "Non-Hotspot"

    merged["hotspot_status"] = merged.apply(_classify, axis=1)

    colors = {
        "Persistent": "#c0392b",
        "Emerging": "#e67e22",
        "Resolved": "#27ae60",
        "Non-Hotspot": "#ecf0f1",
    }

    fig, ax = plt.subplots(figsize=MAP_FIGURE_SIZE, dpi=MAP_DPI)
    ax.set_facecolor("#dbe9f4")
    _draw_bd_outline(ax)

    for status, grp in merged.groupby("hotspot_status"):
        ax.scatter(
            grp["longitude"], grp["latitude"],
            c=colors.get(status, "#cccccc"),
            s=200, edgecolors="black", linewidths=0.5, zorder=5,
            marker="*" if status != "Non-Hotspot" else "o",
        )

    patches = [
        mpatches.Patch(color=colors["Persistent"], label="Persistent Hotspot"),
        mpatches.Patch(color=colors["Emerging"], label="Emerging Hotspot"),
        mpatches.Patch(color=colors["Resolved"], label="Resolved Hotspot"),
        mpatches.Patch(color=colors["Non-Hotspot"], label="Non-Hotspot"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8)
    _set_axis_limits(ax)
    _add_north_arrow(ax)
    ax.set_title(
        f"Hotspot Evolution: {first_year}→{last_year}\n"
        f"(Threshold: MEPI ≥ {threshold})",
        fontsize=11, fontweight="bold",
    )
    plt.tight_layout()
    fig.savefig(output_path, dpi=MAP_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 5. Convenience: generate all spatio-temporal maps
# ---------------------------------------------------------------------------

def create_all_spatio_temporal_maps(
    temporal_dict: dict,
    output_dir: str = None,
) -> dict:
    """
    Generate the full suite of spatio-temporal maps.

    Parameters
    ----------
    temporal_dict : dict
        ``{year: pd.DataFrame}`` of MEPI results.
    output_dir : str, optional
        Directory for output files.

    Returns
    -------
    dict
        ``{map_name: file_path}``.
    """
    output_dir = output_dir or MAP_OUTPUTS_DIR
    _ensure_output_dir(output_dir)
    saved = {}

    saved["temporal_comparison"] = create_temporal_comparison_map(
        temporal_dict, os.path.join(output_dir, OUTPUT_FILES["temporal_comparison"])
    )
    saved["poverty_change"] = create_poverty_change_map(
        temporal_dict, os.path.join(output_dir, OUTPUT_FILES["poverty_change"])
    )
    saved["hotspot_evolution"] = create_hotspot_evolution_map(
        temporal_dict, os.path.join(output_dir, "hotspot_evolution_map.png")
    )
    saved["temporal_animation"] = create_temporal_animation(
        temporal_dict, os.path.join(output_dir, OUTPUT_FILES["temporal_animation"])
    )

    print(f"\nAll spatio-temporal maps saved to: {output_dir}")
    return saved
