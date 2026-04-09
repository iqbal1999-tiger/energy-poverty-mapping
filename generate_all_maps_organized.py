"""
generate_all_maps_organized.py - Master script: generate and organise all MEPI maps

Runs the complete mapping pipeline and saves every output to the correct
subfolder of the organised map_outputs/ hierarchy.

Steps
-----
  1. Load sample / user-provided MEPI data
  2. Create folder structure
  3. Generate spatial maps          → map_outputs/spatial_maps/
  4. Generate regional maps         → map_outputs/regional_maps/
  5. Generate hotspot maps          → map_outputs/hotspot_maps/
  6. Generate analysis maps         → map_outputs/analysis_maps/
  7. Generate interactive maps      → map_outputs/interactive_maps/
  8. Organise any stray files       (map_organizer)
  9. Generate index / README files  (map_index_generator)
 10. Print summary report

Usage
-----
    python generate_all_maps_organized.py
    python generate_all_maps_organized.py --data path/to/mepi_results.csv
    python generate_all_maps_organized.py --no-interactive
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path
from typing import List

import pandas as pd

from config import POVERTY_THRESHOLDS, POVERTY_LABELS
from map_output_manager import MapOutputManager, BASE_OUTPUT_DIR, ensure_all_folders
from map_organizer import MapOrganizer
from map_index_generator import MapIndexGenerator
from updated_correct_spatial_mapping import OrganisedSpatialMapper
from updated_spatio_temporal_hotspot import HotspotAnalyser

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(data_path: str) -> pd.DataFrame:
    """Load MEPI results CSV or calculate from sample data."""
    if data_path and Path(data_path).exists():
        print(f"   Loading MEPI data from: {data_path}")
        return pd.read_csv(data_path)

    # Fall back to sample data + calculator
    print("   No data file specified – using sample_data.csv")
    from data_utils import load_data as _load, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator

    df = _load("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    calc = MEPICalculator()
    results = calc.calculate(df)
    print(f"   {len(results)} upazilas processed, mean MEPI: {results['mepi_score'].mean():.3f}")
    return results


# ---------------------------------------------------------------------------
# Step-level functions
# ---------------------------------------------------------------------------

def step_setup(base_dir: str) -> MapOutputManager:
    print("\n[1] Creating folder structure ...")
    mgr = ensure_all_folders(base_dir)
    mgr.print_status()
    return mgr


def step_spatial(results: pd.DataFrame, base_dir: str) -> List[str]:
    print("\n[2] Generating spatial maps ...")
    mapper = OrganisedSpatialMapper(results, base_dir=base_dir)
    paths = mapper.create_all_maps()
    print(f"   {len(paths)} spatial / hotspot maps saved.")
    return paths


def step_regional(results: pd.DataFrame, base_dir: str) -> List[str]:
    print("\n[3] Generating regional maps ...")
    mapper = OrganisedSpatialMapper(results, base_dir=base_dir)
    paths = mapper.create_regional_maps()
    print(f"   {len(paths)} regional maps saved.")
    return paths


def step_hotspot(results: pd.DataFrame, base_dir: str) -> List[str]:
    print("\n[4] Generating hotspot & vulnerability maps ...")
    analyser = HotspotAnalyser(results, base_dir=base_dir)
    paths = analyser.create_all_hotspot_maps()
    print(f"   {len(paths)} hotspot maps saved.")
    return paths


def step_analysis(results: pd.DataFrame, base_dir: str) -> List[str]:
    print("\n[5] Generating analysis maps ...")
    paths = _create_analysis_maps(results, base_dir)
    print(f"   {len(paths)} analysis maps saved.")
    return paths


def _create_analysis_maps(results: pd.DataFrame, base_dir: str) -> List[str]:
    """Create top-10 rankings, heatmaps, correlation, and distribution maps."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from map_output_manager import get_output_path

    saved: List[str] = []
    analysis_dir = os.path.join(base_dir, "analysis_maps")
    os.makedirs(analysis_dir, exist_ok=True)

    dim_score_cols = [c for c in results.columns if c.endswith("_score") and c != "mepi_score"]

    # -- Top 10 most energy poor --
    try:
        top_poor = results.nlargest(10, "mepi_score")
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.barh(top_poor["upazila_name"], top_poor["mepi_score"], color="#e74c3c", alpha=0.85)
        ax.set_xlabel("MEPI Score", fontsize=11)
        ax.set_title("Top 10 Most Energy-Poor Upazilas", fontsize=14, fontweight="bold")
        ax.set_xlim(0, 1)
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        for bar, score in zip(bars, top_poor["mepi_score"]):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{score:.3f}", va="center", fontsize=8)
        plt.tight_layout()
        p = os.path.join(analysis_dir, "top10_most_poor.png")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"   Saved: {p}")
        saved.append(os.path.abspath(p))
    except Exception as exc:
        warnings.warn(f"top10_most_poor failed: {exc}", stacklevel=2)

    # -- Top 10 least energy poor --
    try:
        top_least = results.nsmallest(10, "mepi_score")
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.barh(top_least["upazila_name"], top_least["mepi_score"], color="#2ecc71", alpha=0.85)
        ax.set_xlabel("MEPI Score", fontsize=11)
        ax.set_title("Top 10 Least Energy-Poor Upazilas", fontsize=14, fontweight="bold")
        ax.set_xlim(0, 1)
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        for bar, score in zip(bars, top_least["mepi_score"]):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{score:.3f}", va="center", fontsize=8)
        plt.tight_layout()
        p = os.path.join(analysis_dir, "top10_least_poor.png")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"   Saved: {p}")
        saved.append(os.path.abspath(p))
    except Exception as exc:
        warnings.warn(f"top10_least_poor failed: {exc}", stacklevel=2)

    # -- Dimension heatmap --
    if dim_score_cols:
        try:
            heat_data = results[dim_score_cols].copy()
            heat_data.columns = [c.replace("_score", "").capitalize() for c in dim_score_cols]
            fig, ax = plt.subplots(figsize=(10, max(6, len(results) * 0.12)))
            sns.heatmap(
                heat_data.T,
                cmap="YlOrRd",
                vmin=0, vmax=1,
                xticklabels=False,
                yticklabels=True,
                ax=ax,
                cbar_kws={"label": "Deprivation Score"},
            )
            ax.set_title("Energy Poverty Dimension Scores – All Upazilas",
                         fontsize=13, fontweight="bold")
            ax.set_xlabel("Upazilas", fontsize=10)
            plt.tight_layout()
            p = os.path.join(analysis_dir, "dimension_heatmap.png")
            fig.savefig(p, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"   Saved: {p}")
            saved.append(os.path.abspath(p))
        except Exception as exc:
            warnings.warn(f"dimension_heatmap failed: {exc}", stacklevel=2)

    # -- Dimension correlation --
    if len(dim_score_cols) >= 2:
        try:
            corr = results[dim_score_cols + ["mepi_score"]].corr()
            labels = [c.replace("_score", "").capitalize() for c in corr.columns]
            fig, ax = plt.subplots(figsize=(8, 7))
            sns.heatmap(
                corr, annot=True, fmt=".2f", cmap="coolwarm",
                vmin=-1, vmax=1, ax=ax,
                xticklabels=labels, yticklabels=labels,
            )
            ax.set_title("Dimension Score Correlation Matrix",
                         fontsize=13, fontweight="bold")
            plt.tight_layout()
            p = os.path.join(analysis_dir, "dimension_correlation.png")
            fig.savefig(p, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"   Saved: {p}")
            saved.append(os.path.abspath(p))
        except Exception as exc:
            warnings.warn(f"dimension_correlation failed: {exc}", stacklevel=2)

    # -- Poverty classification distribution --
    try:
        if "poverty_category" in results.columns:
            counts = results["poverty_category"].value_counts()
        else:
            moderate_lo, moderate_hi = POVERTY_THRESHOLDS["moderate"]
            severe_lo, severe_hi = POVERTY_THRESHOLDS["severe"]
            bins = [0, moderate_lo, severe_lo, 1.01]
            labels_cat = [
                POVERTY_LABELS["non_poor"],
                POVERTY_LABELS["moderate"],
                POVERTY_LABELS["severe"],
            ]
            cats = pd.cut(results["mepi_score"], bins=bins, labels=labels_cat, include_lowest=True)
            counts = cats.value_counts()

        colors = {"Non-Poor": "#2ecc71", "Moderately Poor": "#f39c12", "Severely Poor": "#e74c3c"}
        bar_colors = [colors.get(c, "#3498db") for c in counts.index]

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(counts.index, counts.values, color=bar_colors, alpha=0.85, edgecolor="white")
        ax.set_ylabel("Number of Upazilas", fontsize=11)
        ax.set_title("Poverty Classification Distribution", fontsize=14, fontweight="bold")
        ax.grid(True, axis="y", alpha=0.3)
        for bar, val in zip(bars, counts.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    str(val), ha="center", va="bottom", fontsize=11)
        plt.tight_layout()
        p = os.path.join(analysis_dir, "poverty_classification_distribution.png")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"   Saved: {p}")
        saved.append(os.path.abspath(p))
    except Exception as exc:
        warnings.warn(f"distribution plot failed: {exc}", stacklevel=2)

    # -- Regional comparison (by division) --
    try:
        if "division" in results.columns:
            div_means = results.groupby("division")["mepi_score"].mean().sort_values(ascending=False)
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(div_means.index, div_means.values, color="#3498db", alpha=0.8)
            ax.set_xlabel("Mean MEPI Score", fontsize=11)
            ax.set_title("Mean Energy Poverty by Division", fontsize=14, fontweight="bold")
            ax.set_xlim(0, 1)
            ax.axvline(POVERTY_THRESHOLDS["moderate"][0], color="#f39c12", linestyle="--", linewidth=1, label="Moderate threshold")
            ax.axvline(POVERTY_THRESHOLDS["severe"][0], color="#e74c3c", linestyle="--", linewidth=1, label="Severe threshold")
            ax.legend(fontsize=9)
            ax.grid(True, axis="x", alpha=0.3)
            plt.tight_layout()
            p = os.path.join(analysis_dir, "regional_comparison.png")
            fig.savefig(p, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"   Saved: {p}")
            saved.append(os.path.abspath(p))
    except Exception as exc:
        warnings.warn(f"regional_comparison failed: {exc}", stacklevel=2)

    return saved


def step_interactive(results: pd.DataFrame, base_dir: str) -> List[str]:
    """Generate interactive Folium HTML maps."""
    print("\n[6] Generating interactive maps ...")
    try:
        from updated_interactive_folium_maps import OrganisedInteractiveMapper
        mapper = OrganisedInteractiveMapper(results, base_dir=base_dir)
        paths = mapper.create_all_maps()
        print(f"   {len(paths)} interactive maps saved.")
        return paths
    except ImportError as exc:
        print(f"   ⚠  Folium not available ({exc}). Skipping interactive maps.")
        return []


def step_organise(base_dir: str) -> None:
    """Sort any stray files into subfolders."""
    print("\n[7] Organising stray files ...")
    organizer = MapOrganizer(base_dir=base_dir)
    moved = organizer.organize()
    total = sum(len(v) for v in moved.values())
    if total:
        print(f"   {total} file(s) moved to correct subfolders.")
    else:
        print("   No stray files found.")


def step_index(base_dir: str) -> None:
    """Generate README and index files."""
    print("\n[8] Generating index and README files ...")
    gen = MapIndexGenerator(base_dir=base_dir)
    gen.generate_all()


def print_summary(
    all_paths: List[str],
    results: pd.DataFrame,
    base_dir: str,
) -> None:
    """Print a summary report of the generation run."""
    print("\n" + "=" * 60)
    print("MAP GENERATION SUMMARY")
    print("=" * 60)

    # MEPI statistics
    print(f"\n  Upazilas: {len(results)}")
    print(f"  Mean MEPI: {results['mepi_score'].mean():.3f}")
    print(f"  Std Dev:   {results['mepi_score'].std():.3f}")
    if "poverty_category" in results.columns:
        cats = results["poverty_category"].value_counts()
        for cat, count in cats.items():
            pct = count / len(results) * 100
            print(f"    {cat}: {count} ({pct:.1f}%)")

    # Files generated
    mgr = MapOutputManager(base_dir)
    existing = mgr.list_existing_files()
    total = sum(len(v) for v in existing.values())
    print(f"\n  Total map files: {total}")
    for name, files in existing.items():
        if files:
            print(f"    {name}/ – {len(files)} file(s)")

    print(f"\n  Output directory: {Path(base_dir).resolve()}")
    print(f"  Browse maps:      {Path(base_dir).resolve() / 'index.html'}")
    print("=" * 60)
    print("✅ Done!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args: argparse.Namespace) -> None:
    print("=" * 60)
    print("ENERGY POVERTY MAPPING – FULL GENERATION PIPELINE")
    print("=" * 60)

    base_dir = args.base_dir
    results = load_data(args.data)
    all_paths: List[str] = []

    mgr = step_setup(base_dir)
    all_paths += step_spatial(results, base_dir)
    all_paths += step_regional(results, base_dir)
    all_paths += step_hotspot(results, base_dir)
    all_paths += step_analysis(results, base_dir)

    if not args.no_interactive:
        all_paths += step_interactive(results, base_dir)

    step_organise(base_dir)
    step_index(base_dir)

    print_summary(all_paths, results, base_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate all MEPI maps and organise into subfolders."
    )
    parser.add_argument(
        "--data", default="",
        help="Path to MEPI results CSV (default: calculate from sample_data.csv).",
    )
    parser.add_argument(
        "--base-dir", default=BASE_OUTPUT_DIR,
        help=f"Top-level output directory (default: {BASE_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Skip interactive Folium HTML map generation.",
    )
    main(parser.parse_args())
