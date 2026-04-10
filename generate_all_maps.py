"""
generate_all_maps.py - Master script: generate ALL MEPI maps to external folder

One command to produce every map type and save them to the organised external
folder (default: ~/map_outputs_energy_poverty/).

Steps
-----
  1. Create external folder structure
  2. Load MEPI data (or calculate from sample_data.csv)
  3. Generate spatial maps      → spatial_maps/
  4. Generate regional maps     → regional_maps/
  5. Generate temporal maps     → temporal_maps/
  6. Generate hotspot maps      → hotspot_maps/
  7. Generate analysis maps     → analysis_maps/
  8. Generate interactive maps  → interactive_maps/
  9. Generate index.html + README files
 10. Print summary report

Usage
-----
    python generate_all_maps.py
    python generate_all_maps.py --data path/to/mepi_results.csv
    python generate_all_maps.py --output-dir /custom/path/
    python generate_all_maps.py --no-interactive
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from map_config_external import EXTERNAL_OUTPUT_BASE, print_config
from external_folder_manager import ExternalFolderManager, ensure_external_folders
from spatial_maps_external import SpatialMapsExternal
from regional_maps_external import RegionalMapsExternal
from temporal_maps_external import TemporalMapsExternal
from hotspot_maps_external import HotspotMapsExternal
from analysis_maps_external import AnalysisMapsExternal
from map_index_and_readme import ExternalMapDocGenerator

warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(data_path: str) -> pd.DataFrame:
    """Load MEPI results from CSV or calculate from sample_data.csv."""
    if data_path and Path(data_path).exists():
        print(f"   Loading MEPI data from: {data_path}")
        return pd.read_csv(data_path)

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


def _make_yearly_data(results: pd.DataFrame) -> Dict[int, pd.DataFrame]:
    """Build a synthetic two-year dataset for temporal map demos."""
    rng = np.random.default_rng(42)
    yearly: Dict[int, pd.DataFrame] = {}
    for year in [2020, 2021]:
        df = results.copy()
        noise = rng.normal(0, 0.03, len(df))
        df["mepi_score"] = (df["mepi_score"] + noise).clip(0, 1)
        yearly[year] = df
    return yearly


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def _section(title: str, step: int, total: int) -> None:
    print(f"\n[{step}/{total}] {title} ...")
    print("-" * 50)


def _done(paths: List[str], label: str) -> None:
    print(f"   ✅ {len(paths)} {label} map(s) generated.")


# ---------------------------------------------------------------------------
# Step-level functions
# ---------------------------------------------------------------------------

def step_folders(base_dir: str) -> ExternalFolderManager:
    mgr = ensure_external_folders(base_dir)
    mgr.print_status()
    return mgr


def step_spatial(results: pd.DataFrame, base_dir: str) -> List[str]:
    mapper = SpatialMapsExternal(results, base_dir=base_dir)
    paths = mapper.create_all_maps()
    _done(paths, "spatial")
    return paths


def step_regional(results: pd.DataFrame, base_dir: str) -> List[str]:
    mapper = RegionalMapsExternal(results, base_dir=base_dir)
    paths = mapper.create_all_maps()
    _done(paths, "regional")
    return paths


def step_temporal(results: pd.DataFrame, base_dir: str) -> List[str]:
    yearly_data = _make_yearly_data(results)
    mapper = TemporalMapsExternal(yearly_data, base_dir=base_dir)
    paths = mapper.create_all_maps()
    _done(paths, "temporal")
    return paths


def step_hotspot(results: pd.DataFrame, base_dir: str) -> List[str]:
    mapper = HotspotMapsExternal(results, base_dir=base_dir)
    paths = mapper.create_all_maps()
    _done(paths, "hotspot")
    return paths


def step_analysis(results: pd.DataFrame, base_dir: str) -> List[str]:
    mapper = AnalysisMapsExternal(results, base_dir=base_dir)
    paths = mapper.create_all_maps()
    _done(paths, "analysis")
    return paths


def step_interactive(results: pd.DataFrame, base_dir: str) -> List[str]:
    try:
        from interactive_maps_external import InteractiveMapsExternal
        mapper = InteractiveMapsExternal(results, base_dir=base_dir)
        paths = mapper.create_all_maps()
        _done(paths, "interactive")
        return paths
    except ImportError as exc:
        print(f"   ⚠  Folium not available ({exc}). Skipping interactive maps.")
        return []


def step_docs(base_dir: str) -> None:
    gen = ExternalMapDocGenerator(base_dir=base_dir)
    gen.generate_all()


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def print_summary(
    all_paths: List[str],
    results: pd.DataFrame,
    mgr: ExternalFolderManager,
    elapsed: float,
) -> None:
    print("\n" + "=" * 60)
    print("MAP GENERATION SUMMARY")
    print("=" * 60)

    print(f"\n  Upazilas processed : {len(results)}")
    print(f"  Mean MEPI score    : {results['mepi_score'].mean():.3f}")
    print(f"  Std Dev            : {results['mepi_score'].std():.3f}")

    existing = mgr.list_existing_files()
    total = sum(len(v) for v in existing.values())
    print(f"\n  Total files saved  : {total}")
    for name, files in existing.items():
        if files:
            print(f"    {name}/ – {len(files)} file(s)")

    print(f"\n  Output directory   : {mgr.base_dir}")
    print(f"  Browse maps at     : {mgr.base_dir / 'index.html'}")
    print(f"  Time elapsed       : {elapsed:.1f} seconds")
    print("=" * 60)
    print("✅ All maps generated successfully!")
    print(f"\n  Open this URL in your browser:")
    print(f"  file://{mgr.base_dir / 'index.html'}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main(args: argparse.Namespace) -> None:
    start = time.time()
    base_dir = args.output_dir
    total_steps = 9

    print("=" * 60)
    print("ENERGY POVERTY MAPPING – EXTERNAL FOLDER GENERATION")
    print("=" * 60)
    print_config()

    _section("Loading MEPI data", 1, total_steps)
    results = load_data(args.data)

    _section("Creating external folder structure", 2, total_steps)
    mgr = step_folders(base_dir)
    all_paths: List[str] = []

    _section("Generating spatial maps", 3, total_steps)
    all_paths += step_spatial(results, base_dir)

    _section("Generating regional maps", 4, total_steps)
    all_paths += step_regional(results, base_dir)

    _section("Generating temporal maps", 5, total_steps)
    all_paths += step_temporal(results, base_dir)

    _section("Generating hotspot maps", 6, total_steps)
    all_paths += step_hotspot(results, base_dir)

    _section("Generating analysis maps", 7, total_steps)
    all_paths += step_analysis(results, base_dir)

    if not args.no_interactive:
        _section("Generating interactive maps", 8, total_steps)
        all_paths += step_interactive(results, base_dir)
    else:
        print("\n[8/9] Interactive maps skipped (--no-interactive).")

    _section("Generating index.html and README files", 9, total_steps)
    step_docs(base_dir)

    elapsed = time.time() - start
    print_summary(all_paths, results, mgr, elapsed)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Generate ALL MEPI maps and save to external folder "
            f"(default: {EXTERNAL_OUTPUT_BASE})."
        )
    )
    parser.add_argument(
        "--data", default="",
        help="Path to MEPI results CSV. If not given, uses sample_data.csv.",
    )
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Skip interactive Folium HTML map generation.",
    )
    main(parser.parse_args())
