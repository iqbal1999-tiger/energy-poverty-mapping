"""
visualization_example.py - Complete example showing how to use all visualization
and analysis modules with MEPI results.

This script demonstrates:
  1. Loading MEPI results from sample_data.csv
  2. Running all visualization functions
  3. Generating statistical and spatial analysis reports
  4. Saving plots as PNG and PDF
  5. Exporting Excel and text reports

Run from the repository root:
    python visualization_example.py

Outputs are saved to the ``output/`` directory.
"""

import os
import sys

# Ensure the repository root is on the Python path when run directly
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; change to "TkAgg" for interactive use

import matplotlib.pyplot as plt

from data_utils import load_data, validate_data, handle_missing_values
from mepi_calculator import MEPICalculator
from visualization import MEPIVisualizer
from spatial_analysis import SpatialAnalyzer
from statistical_analysis import StatisticalAnalyzer
from report_generator import ReportGenerator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_FILE = os.path.join(ROOT, "sample_data.csv")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_example():
    print("=" * 60)
    print("MEPI Visualization & Analysis Example")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1 – Load and calculate MEPI
    # ------------------------------------------------------------------
    print("\n[1/5] Loading and calculating MEPI scores ...")
    df = load_data(DATA_FILE)
    df = validate_data(df)
    df = handle_missing_values(df)

    calc = MEPICalculator()
    results = calc.calculate(df)
    print(f"    Calculated MEPI for {len(results)} upazilas.")
    print(f"    Mean MEPI score: {results['mepi_score'].mean():.3f}")

    # ------------------------------------------------------------------
    # Step 2 – Visualizations
    # ------------------------------------------------------------------
    print("\n[2/5] Generating visualizations ...")
    viz = MEPIVisualizer(results)

    charts = [
        ("bar_chart",       viz.plot_mepi_bar_chart(title="MEPI Scores by Upazila")),
        ("heatmap",         viz.plot_dimension_heatmap(top_n=20)),
        ("boxplots",        viz.plot_dimension_boxplots()),
        ("histogram",       viz.plot_mepi_histogram()),
        ("radar",           viz.plot_radar_chart()),
        ("division_compare",viz.plot_regional_comparison(group_col="division")),
        ("stacked_bar",     viz.plot_stacked_dimension_contributions(top_n=20)),
        ("pie_chart",       viz.plot_poverty_pie()),
        ("scatter",         viz.plot_scatter("Availability", "Affordability")),
    ]

    for name, fig in charts:
        png_path = os.path.join(OUTPUT_DIR, f"mepi_{name}.png")
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"    Saved: {png_path}")

    # Violin plot (requires seaborn)
    try:
        fig_violin = viz.plot_violin(group_col="division")
        violin_path = os.path.join(OUTPUT_DIR, "mepi_violin.png")
        fig_violin.savefig(violin_path, dpi=150, bbox_inches="tight")
        plt.close(fig_violin)
        print(f"    Saved: {violin_path}")
    except Exception as exc:
        print(f"    Violin plot skipped: {exc}")

    # ------------------------------------------------------------------
    # Step 3 – Statistical analysis
    # ------------------------------------------------------------------
    print("\n[3/5] Running statistical analysis ...")
    stat = StatisticalAnalyzer(results)

    print("\n  Descriptive statistics:")
    print(stat.descriptive_statistics().to_string())

    print("\n  Dimension contribution:")
    print(stat.dimension_contribution().to_string(index=False))

    print(f"\n  Gini coefficient (MEPI): {stat.gini_coefficient():.4f}")

    # Correlation heatmap
    try:
        corr_fig = stat.plot_correlation_heatmap()
        corr_path = os.path.join(OUTPUT_DIR, "mepi_correlation.png")
        corr_fig.savefig(corr_path, dpi=150, bbox_inches="tight")
        plt.close(corr_fig)
        print(f"\n  Correlation heatmap saved: {corr_path}")
    except Exception as exc:
        print(f"  Correlation heatmap skipped: {exc}")

    # ------------------------------------------------------------------
    # Step 4 – Spatial analysis
    # ------------------------------------------------------------------
    print("\n[4/5] Running spatial analysis ...")
    spatial = SpatialAnalyzer(results)

    print("\n  Spatial statistics:")
    print(spatial.spatial_statistics().to_string(index=False))

    hotspots = spatial.identify_hotspots(threshold=0.6)
    print(f"\n  Hotspots (MEPI ≥ 0.60): {len(hotspots)} upazilas")
    if not hotspots.empty:
        display_cols = [c for c in ["upazila_name", "district", "mepi_score"] if c in hotspots.columns]
        print(hotspots[display_cols].to_string(index=False))

    print("\n  Top 10 most energy-poor upazilas:")
    top10 = spatial.top_n_upazilas(10)
    cols = [c for c in ["rank", "upazila_name", "district", "mepi_score"] if c in top10.columns]
    print(top10[cols].to_string(index=False))

    print("\n  Bottom 10 least energy-poor upazilas:")
    bottom10 = spatial.bottom_n_upazilas(10)
    print(bottom10[cols].to_string(index=False))

    # Export GIS-ready CSV
    gis_path = os.path.join(OUTPUT_DIR, "mepi_gis_ready.csv")
    spatial.export_gis_ready(gis_path)

    # ------------------------------------------------------------------
    # Step 5 – Report generation
    # ------------------------------------------------------------------
    print("\n[5/5] Generating reports ...")
    rg = ReportGenerator(results, title="MEPI Analysis Report – Bangladesh")

    text_path = os.path.join(OUTPUT_DIR, "mepi_report.txt")
    rg.export_text_report(text_path)

    xlsx_path = os.path.join(OUTPUT_DIR, "mepi_report.xlsx")
    rg.export_excel_report(xlsx_path)

    print("\n" + "=" * 60)
    print("Example complete!  All outputs are in the 'output/' directory.")
    print("=" * 60)
    print(f"  Charts   : {len(charts) + 2} PNG files")
    print(f"  GIS CSV  : {gis_path}")
    print(f"  Text RPT : {text_path}")
    print(f"  Excel RPT: {xlsx_path}")


if __name__ == "__main__":
    run_example()
