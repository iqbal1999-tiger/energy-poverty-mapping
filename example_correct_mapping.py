"""
example_correct_mapping.py - Complete working example for Bangladesh MEPI maps

Demonstrates the full workflow:
  1. Load MEPI results (or calculate from sample data)
  2. Validate upazilas against shapefile / coordinate database
  3. Create static choropleth PNG maps
  4. Create interactive HTML maps
  5. Print summary of all outputs

Usage
-----
    python example_correct_mapping.py

Maps are saved to map_outputs/.
"""

from __future__ import annotations

import os
import warnings

import pandas as pd

from data_utils import load_data, validate_data, handle_missing_values
from mepi_calculator import MEPICalculator
from bangladesh_coordinates import UpazilaDatabase, get_database
from correct_spatial_mapping import SpatialMapper
from interactive_folium_maps import InteractiveMapper
from upazila_validator import UpazilaValidator

# Suppress non-critical warnings during demo
warnings.filterwarnings("ignore", category=UserWarning)

OUTPUT_DIR = "map_outputs"
DATA_FILE = "sample_data.csv"


# ---------------------------------------------------------------------------
# Step 1 – Load / calculate MEPI
# ---------------------------------------------------------------------------

def load_mepi_results() -> pd.DataFrame:
    """Load sample data and calculate MEPI scores."""
    print("[1/5] Loading and calculating MEPI ...")
    df = load_data(DATA_FILE)
    df = validate_data(df)
    df = handle_missing_values(df)
    calc = MEPICalculator()
    results = calc.calculate(df)
    print(f"      {len(results)} upazilas processed")
    print(f"      Mean MEPI: {results['mepi_score'].mean():.3f}")
    return results


# ---------------------------------------------------------------------------
# Step 2 – Validate upazilas
# ---------------------------------------------------------------------------

def validate_upazilas(results: pd.DataFrame) -> None:
    """Validate MEPI upazila names against the coordinate database."""
    print("\n[2/5] Validating upazilas ...")
    db = get_database()
    validator = UpazilaValidator(results, mepi_name_col="upazila_name")
    report = validator.validate()
    print(
        f"      Matched {report['matched_count']} / {report['mepi_count']} "
        f"({report['match_rate']}%)"
    )
    if report["unmatched_mepi"]:
        print(f"      ⚠  Unmatched: {report['unmatched_mepi'][:5]}")


# ---------------------------------------------------------------------------
# Step 3 – Static PNG maps
# ---------------------------------------------------------------------------

def create_static_maps(results: pd.DataFrame) -> list:
    """Create all static choropleth PNG maps."""
    print("\n[3/5] Creating static PNG maps ...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    mapper = SpatialMapper(results)
    paths = mapper.create_all_maps(OUTPUT_DIR)

    print(f"      {len(paths)} maps saved to '{OUTPUT_DIR}/'")
    return paths


# ---------------------------------------------------------------------------
# Step 4 – Interactive HTML maps
# ---------------------------------------------------------------------------

def create_interactive_maps(results: pd.DataFrame) -> list:
    """Create all interactive Folium HTML maps."""
    print("\n[4/5] Creating interactive HTML maps ...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        mapper = InteractiveMapper(results)
        paths = mapper.create_all_maps(OUTPUT_DIR)
        print(f"      {len(paths)} interactive maps saved to '{OUTPUT_DIR}/'")
        return paths
    except ImportError as exc:
        print(f"      ⚠  Folium not available ({exc}).  Skipping interactive maps.")
        return []


# ---------------------------------------------------------------------------
# Step 5 – Summary
# ---------------------------------------------------------------------------

def print_summary(results: pd.DataFrame, static_paths: list, interactive_paths: list) -> None:
    """Print a summary of the analysis and output files."""
    print("\n[5/5] Summary")
    print("=" * 60)

    # Poverty breakdown
    cats = results["poverty_category"].value_counts()
    print("  Energy Poverty Classification:")
    for cat, count in cats.items():
        pct = count / len(results) * 100
        print(f"    {cat}: {count} upazilas ({pct:.1f}%)")

    # Top 5 most energy-poor
    top5 = results.nlargest(5, "mepi_score")[
        ["upazila_name", "district", "mepi_score", "poverty_category"]
    ]
    print("\n  Top 5 Most Energy-Poor Upazilas:")
    print(top5.to_string(index=False))

    # Output files
    all_paths = static_paths + interactive_paths
    print(f"\n  Saved {len(all_paths)} map file(s) to '{OUTPUT_DIR}/':")
    for p in all_paths:
        print(f"    - {os.path.basename(p)}")

    print("\n  ✅ Done!  Open the HTML files in a browser for interactive exploration.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("BANGLADESH ENERGY POVERTY MAPPING – COMPLETE EXAMPLE")
    print("=" * 60)

    results = load_mepi_results()
    validate_upazilas(results)
    static_paths = create_static_maps(results)
    interactive_paths = create_interactive_maps(results)
    print_summary(results, static_paths, interactive_paths)


if __name__ == "__main__":
    main()
