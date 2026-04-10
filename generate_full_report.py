"""
generate_full_report.py - Master one-command script to generate the complete MEPI report.

This script:
  1. Loads MEPI results (from CSV or recalculates from sample data)
  2. Validates and pre-processes data
  3. Calculates MEPI scores (if not already present)
  4. Runs the full report generation pipeline:
       - Generates all charts and graphs
       - Loads spatial maps from ~/spatial_maps_png/
       - Builds 10-chapter PDF report with embedded figures
       - Builds editable DOCX report
       - Writes text summary

Run from the project root directory:
    python generate_full_report.py

Output files:
    ~/energy_poverty_reports/Energy_Poverty_Index_Report_2026.pdf
    ~/energy_poverty_reports/Energy_Poverty_Index_Report_2026.docx
    ~/energy_poverty_reports/report_summary.txt
"""

import os
import sys
from typing import Optional

import pandas as pd

# ── Project root on path ─────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ── Project imports ───────────────────────────────────────────────────────────
from data_utils import load_data, validate_data, handle_missing_values, assign_geographic_zone
from mepi_calculator import MEPICalculator
from config import DEFAULT_WEIGHTS
from report_generator_full import FullReportGenerator

# =============================================================================
# Configuration – edit these as needed
# =============================================================================

# Path to input data (CSV with upazila-level indicators)
# Set to None to use the bundled sample_data.csv
INPUT_DATA_PATH: Optional[str] = None

# Path to pre-computed MEPI results CSV (skips recalculation if provided)
# Set to None to always recalculate
RESULTS_CSV_PATH: Optional[str] = os.path.join(_SCRIPT_DIR, "output", "mepi_results.csv")

# Spatial maps directory (PNG files from the spatial mapping scripts)
SPATIAL_MAPS_DIR: str = os.path.expanduser("~/spatial_maps_png")

# Report output directory
REPORT_OUTPUT_DIR: str = os.path.expanduser("~/energy_poverty_reports")

# Citation style: "APA", "Harvard", or "IEEE"
CITATION_STYLE: str = "APA"


# =============================================================================
# Helper: load or calculate MEPI results
# =============================================================================

def load_or_calculate_results() -> pd.DataFrame:
    """
    Load pre-computed MEPI results from CSV, or recalculate from raw data.

    Returns
    -------
    pd.DataFrame
        MEPI results with dimension scores and poverty categories.
    """
    # 1. Try to load pre-computed results
    if RESULTS_CSV_PATH and os.path.isfile(RESULTS_CSV_PATH):
        print(f"Loading pre-computed results from: {RESULTS_CSV_PATH}")
        results = pd.read_csv(RESULTS_CSV_PATH)
        if "mepi_score" in results.columns:
            return results
        print("  mepi_score column not found – will recalculate.")

    # 2. Load raw data
    if INPUT_DATA_PATH and os.path.isfile(INPUT_DATA_PATH):
        data_path = INPUT_DATA_PATH
    else:
        data_path = os.path.join(_SCRIPT_DIR, "sample_data.csv")
        print(f"Using bundled sample data: {data_path}")

    print(f"Loading raw data from: {data_path}")
    df = load_data(data_path)
    df = validate_data(df)
    df = handle_missing_values(df, strategy="mean")
    df = assign_geographic_zone(df)

    # 3. Calculate MEPI
    print("Calculating MEPI scores …")
    calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
    results = calc.calculate(df)

    # 4. Cache results
    output_dir = os.path.join(_SCRIPT_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    cache_path = os.path.join(output_dir, "mepi_results.csv")
    results.to_csv(cache_path, index=False)
    print(f"  Results cached to: {cache_path}")

    return results


# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "=" * 60)
    print("  ENERGY POVERTY INDEX – FULL REPORT GENERATOR")
    print("=" * 60)

    # Step 1: Load / calculate results
    print("\nStep 1: Loading MEPI results …")
    results = load_or_calculate_results()
    print(f"  {len(results)} upazilas | mean MEPI = {results['mepi_score'].mean():.4f}")

    # Step 2: Run the full report generation pipeline
    print("\nStep 2: Generating full report …")
    generator = FullReportGenerator(
        results_df=results,
        output_dir=REPORT_OUTPUT_DIR,
        spatial_maps_dir=SPATIAL_MAPS_DIR,
        citation_style=CITATION_STYLE,
    )
    paths = generator.generate()

    # Step 3: Print output location
    print("\n" + "=" * 60)
    print("  OUTPUT FILES")
    print("=" * 60)
    for label, key in [("PDF Report", "pdf"), ("DOCX Report", "docx"), ("Summary", "summary")]:
        path = paths.get(key)
        status = "✓" if path and os.path.isfile(str(path)) else "✗"
        print(f"  {status}  {label:12s}: {path or 'Not generated'}")
    print("=" * 60)
    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
