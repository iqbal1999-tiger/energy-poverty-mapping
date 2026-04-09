"""
example_spatio_temporal_maps.py - Complete worked example for spatio-temporal mapping

Demonstrates the full pipeline:
  1. Load and calculate MEPI from sample_data.csv
  2. Prepare spatial data (add coordinates)
  3. Generate all static spatial maps
  4. Simulate multi-year temporal data
  5. Create temporal comparison and change maps
  6. Build animated GIF
  7. Create interactive Folium maps

Run this script from the repository root:
    python example_spatio_temporal_maps.py
"""

import os
import sys

# Ensure repository root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from config import DIMENSION_INDICATORS
from data_utils import load_data
from mepi_calculator import MEPICalculator
from data_preparation_spatial import SpatialDataPrep
from spatial_mapping import create_all_spatial_maps
from temporal_analysis import TemporalAnalyzer
from spatio_temporal_maps import create_all_spatio_temporal_maps
from interactive_maps import (
    create_interactive_map,
    create_dimension_layer_map,
    create_hotspot_interactive_map,
)
from map_config import MAP_OUTPUTS_DIR


def main():
    print("=" * 60)
    print("  Energy Poverty Spatio-Temporal Mapping Pipeline")
    print("=" * 60)

    # ------------------------------------------------------------------ #
    # Step 1 – Load and calculate MEPI
    # ------------------------------------------------------------------ #
    print("\n[1/6] Loading sample data and calculating MEPI...")
    data_path = os.path.join(os.path.dirname(__file__), "sample_data.csv")
    df = load_data(data_path)
    calc = MEPICalculator()
    results = calc.calculate(df)
    print(f"      {len(results)} upazilas processed.")
    print(results[["upazila_name", "mepi_score", "poverty_category"]].to_string(index=False))

    # ------------------------------------------------------------------ #
    # Step 2 – Add coordinates
    # ------------------------------------------------------------------ #
    print("\n[2/6] Adding geographic coordinates...")
    prep = SpatialDataPrep(results)
    results_geo = prep.add_coordinates()
    print("      Coordinates added.")

    # ------------------------------------------------------------------ #
    # Step 3 – Generate all static spatial maps
    # ------------------------------------------------------------------ #
    print("\n[3/6] Generating static spatial maps...")
    saved_maps = create_all_spatial_maps(results_geo, output_dir=MAP_OUTPUTS_DIR)
    print(f"\n      Saved {len(saved_maps)} static maps.")

    # ------------------------------------------------------------------ #
    # Step 4 – Simulate multi-year temporal data
    # ------------------------------------------------------------------ #
    print("\n[4/6] Simulating multi-year MEPI data (2020–2025)...")
    prep2 = SpatialDataPrep(results)
    temporal_dict = prep2.simulate_temporal_data(years=[2020, 2021, 2022, 2023, 2024, 2025])

    # Show trend statistics
    ta = TemporalAnalyzer(temporal_dict)
    stats = ta.trend_statistics()
    print(stats[["year", "mean_mepi", "n_severe", "n_moderate", "n_non_poor"]].to_string(index=False))

    # Top improvers and deteriorators
    rank = ta.rank_by_change(n=5, direction="both")
    print("\n  Top movers (improvement / deterioration):")
    print(rank[["upazila_name", "base_score", "end_score", "absolute_change"]].to_string(index=False))

    # ------------------------------------------------------------------ #
    # Step 5 – Spatio-temporal maps
    # ------------------------------------------------------------------ #
    print("\n[5/6] Generating spatio-temporal maps and animation...")
    saved_temporal = create_all_spatio_temporal_maps(temporal_dict, output_dir=MAP_OUTPUTS_DIR)
    print(f"\n      Saved {len(saved_temporal)} spatio-temporal maps.")

    # ------------------------------------------------------------------ #
    # Step 6 – Interactive HTML maps
    # ------------------------------------------------------------------ #
    print("\n[6/6] Generating interactive Folium HTML maps...")
    create_interactive_map(results_geo)
    create_dimension_layer_map(results_geo)
    create_hotspot_interactive_map(results_geo)
    print("      Interactive maps saved to map_outputs/")

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("  All outputs written to:", os.path.abspath(MAP_OUTPUTS_DIR))
    print("=" * 60)
    print("\nFiles generated:")
    for fname in sorted(os.listdir(MAP_OUTPUTS_DIR)):
        fpath = os.path.join(MAP_OUTPUTS_DIR, fname)
        size_kb = os.path.getsize(fpath) // 1024
        print(f"  {fname:<48} {size_kb:>5} KB")


if __name__ == "__main__":
    main()
