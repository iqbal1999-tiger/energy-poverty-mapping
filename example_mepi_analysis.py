"""
example_mepi_analysis.py - Complete worked example of the MEPI calculation pipeline

This script demonstrates the full workflow:
  1. Load sample data
  2. Validate and pre-process
  3. Calculate MEPI scores
  4. Analyse and rank results
  5. Run a sensitivity analysis with alternative weights
  6. Export to CSV and Excel

Run from the project root directory:
    python example_mepi_analysis.py
"""

import os

import pandas as pd

# ── project modules ──────────────────────────────────────────────────────────
from data_utils import (
    load_data,
    validate_data,
    handle_missing_values,
    assign_geographic_zone,
    data_summary,
)
from mepi_calculator import MEPICalculator
from analysis import (
    summarise_results,
    print_summary,
    rank_upazilas,
    aggregate_by_district,
    aggregate_by_division,
    aggregate_by_zone,
    build_summary_table,
    export_results,
    sensitivity_comparison_table,
)
from config import (
    DEFAULT_WEIGHTS,
    DIMENSION_WEIGHTS_ALT1,
    DIMENSION_WEIGHTS_ALT2,
)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – Load data
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 1: Loading sample data")
print("=" * 60)

data_path = os.path.join(os.path.dirname(__file__), "sample_data.csv")
df = load_data(data_path)
print(df[["upazila_name", "district", "division"]].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – Validate & pre-process
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Validation and pre-processing")
print("=" * 60)

df = validate_data(df)
df = handle_missing_values(df, strategy="mean")
df = assign_geographic_zone(df)

print("\nDescriptive statistics for indicator columns:")
print(data_summary(df).to_string())

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – Calculate MEPI (equal weights)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: Calculating MEPI (equal weights)")
print("=" * 60)

calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
results = calc.calculate(df)

print("\nTop 5 rows of MEPI results:")
display_cols = [
    "upazila_name",
    "district",
    "mepi_score",
    "poverty_category",
    "Availability_score",
    "Reliability_score",
    "Adequacy_score",
    "Quality_score",
    "Affordability_score",
]
print(results[display_cols].round(4).to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 – Summarise and rank
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Summary statistics and ranking")
print("=" * 60)

summary = summarise_results(results)
print_summary(summary)

print("\nTop 5 most energy-deprived upazilas:")
top5 = rank_upazilas(results, by="mepi_score", ascending=False, top_n=5)
print(top5[["rank", "upazila_name", "district", "mepi_score", "poverty_category"]].to_string(index=False))

print("\nTop 5 least energy-deprived upazilas:")
bottom5 = rank_upazilas(results, by="mepi_score", ascending=True, top_n=5)
bottom5["rank"] = range(len(results), len(results) - 5, -1)
print(bottom5[["rank", "upazila_name", "district", "mepi_score", "poverty_category"]].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – Aggregate by administrative unit and zone
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5: Aggregation by district, division, and geographic zone")
print("=" * 60)

print("\nDistrict-level MEPI summary:")
district_summary = aggregate_by_district(results)
print(district_summary[["district", "mepi_score", "n_upazilas"]].round(4).to_string(index=False))

print("\nDivision-level MEPI summary:")
division_summary = aggregate_by_division(results)
print(division_summary[["division", "mepi_score", "n_upazilas"]].round(4).to_string(index=False))

print("\nGeographic zone MEPI summary:")
zone_summary = aggregate_by_zone(results)
print(zone_summary[["geographic_zone", "mepi_score", "n_upazilas"]].round(4).to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 – Sensitivity analysis with alternative weights
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6: Sensitivity analysis – alternative weighting schemes")
print("=" * 60)

weight_schemes = [DEFAULT_WEIGHTS, DIMENSION_WEIGHTS_ALT1, DIMENSION_WEIGHTS_ALT2]
scheme_labels = ["Equal (0.2 each)", "Alt-1 (Availability+Affordability)", "Alt-2 (Reliability+Adequacy)"]

sensitivity_results = calc.calculate_with_sensitivity(df, weight_schemes)
comparison = sensitivity_comparison_table(sensitivity_results, scheme_labels=scheme_labels)

print("\nSensitivity comparison (MEPI score under each weight scheme):")
print(comparison[["upazila_name"] + scheme_labels + ["score_range"]].round(4).to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 – Export results
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7: Exporting results")
print("=" * 60)

output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(output_dir, exist_ok=True)

# Export full results to CSV
csv_path = os.path.join(output_dir, "mepi_results.csv")
export_results(results, csv_path)

# Export multi-sheet Excel workbook
xlsx_path = os.path.join(output_dir, "mepi_results.xlsx")
export_results(
    results,
    xlsx_path,
    include_district_summary=True,
    include_division_summary=True,
)

# Export publication-ready summary table to CSV
summary_table = build_summary_table(results)
summary_table_path = os.path.join(output_dir, "mepi_summary_table.csv")
summary_table.to_csv(summary_table_path, index=False)
print(f"Summary table saved to: {summary_table_path}")

# Export sensitivity comparison
sensitivity_path = os.path.join(output_dir, "sensitivity_comparison.csv")
comparison.to_csv(sensitivity_path, index=False)
print(f"Sensitivity comparison saved to: {sensitivity_path}")

print("\n✅ Analysis complete. All outputs saved to the 'output/' directory.")
