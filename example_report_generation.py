"""
example_report_generation.py - Usage example for the MEPI report generation system.

Demonstrates how to:
  - Generate a report from sample data (default)
  - Customise report metadata (title, author, organisation)
  - Change citation style
  - Override output paths
  - Generate only PDF or only DOCX
  - Add or remove individual charts

Run from the project root directory:
    python example_report_generation.py
"""

import os
import sys

# ── Project root on sys.path ─────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ── Standard imports ──────────────────────────────────────────────────────────
import pandas as pd

from data_utils import load_data, validate_data, handle_missing_values, assign_geographic_zone
from mepi_calculator import MEPICalculator
from config import DEFAULT_WEIGHTS


# =============================================================================
# EXAMPLE 1 – Quickstart: generate a complete report from sample data
# =============================================================================

def example_1_quickstart():
    """Generate the full report using sample data and default settings."""
    print("\n" + "=" * 60)
    print("  EXAMPLE 1: Quickstart – default settings")
    print("=" * 60)

    # Load and process sample data
    data_path = os.path.join(_SCRIPT_DIR, "sample_data.csv")
    df = load_data(data_path)
    df = validate_data(df)
    df = handle_missing_values(df)
    df = assign_geographic_zone(df)

    # Calculate MEPI
    calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
    results = calc.calculate(df)

    # Generate report (output to ~/energy_poverty_reports/)
    from report_generator_full import FullReportGenerator
    gen = FullReportGenerator(results)
    paths = gen.generate()

    print("\nGenerated files:")
    for key in ("pdf", "docx", "summary"):
        print(f"  {key}: {paths.get(key)}")


# =============================================================================
# EXAMPLE 2 – Custom metadata, Harvard citation style, and custom output folder
# =============================================================================

def example_2_custom_settings():
    """Demonstrate customising report title, author, and citation style."""
    print("\n" + "=" * 60)
    print("  EXAMPLE 2: Custom metadata and Harvard citations")
    print("=" * 60)

    # Override report_config values before importing builders
    import report_config as cfg
    cfg.REPORT_TITLE = "Energy Access and Poverty in Bangladesh: A Spatial Analysis"
    cfg.REPORT_SUBTITLE = "Evidence from the Multidimensional Energy Poverty Index"
    cfg.REPORT_AUTHORS = ["Dr. A. Rahman", "Prof. B. Islam"]
    cfg.REPORT_ORGANIZATION = "Institute of Energy Studies, University of Dhaka"
    cfg.CITATION_STYLE = "Harvard"

    # Load data and calculate MEPI
    data_path = os.path.join(_SCRIPT_DIR, "sample_data.csv")
    df = load_data(data_path)
    df = validate_data(df)
    df = handle_missing_values(df)
    df = assign_geographic_zone(df)
    calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
    results = calc.calculate(df)

    # Custom output directory
    custom_output = os.path.expanduser("~/energy_poverty_reports/custom_example")

    from report_generator_full import FullReportGenerator
    gen = FullReportGenerator(
        results_df=results,
        output_dir=custom_output,
        citation_style="Harvard",
    )
    paths = gen.generate()

    print(f"\nCustom report saved to: {custom_output}")


# =============================================================================
# EXAMPLE 3 – Generate only charts (no full report)
# =============================================================================

def example_3_charts_only():
    """Generate all charts without building the full PDF/DOCX."""
    print("\n" + "=" * 60)
    print("  EXAMPLE 3: Charts only")
    print("=" * 60)

    data_path = os.path.join(_SCRIPT_DIR, "sample_data.csv")
    df = load_data(data_path)
    df = validate_data(df)
    df = handle_missing_values(df)
    df = assign_geographic_zone(df)
    calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
    results = calc.calculate(df)

    from chart_graph_generator import ChartGenerator
    chart_dir = os.path.expanduser("~/energy_poverty_reports/charts_only")
    cg = ChartGenerator(results, output_dir=chart_dir)
    chart_paths = cg.generate_all()

    print(f"\n{len(chart_paths)} charts saved to: {chart_dir}")
    for name, path in chart_paths.items():
        exists = "✓" if os.path.isfile(path) else "✗"
        print(f"  {exists}  {name}: {os.path.basename(path)}")


# =============================================================================
# EXAMPLE 4 – Bibliography management standalone
# =============================================================================

def example_4_bibliography():
    """Demonstrate the BibliographyManager in isolation."""
    print("\n" + "=" * 60)
    print("  EXAMPLE 4: Bibliography management")
    print("=" * 60)

    from bibliography_manager import BibliographyManager

    for style in ("APA", "Harvard", "IEEE"):
        bm = BibliographyManager(style=style)

        # Cite some sources
        c1 = bm.cite("nussbaumer_2011")
        c2 = bm.cite("world_bank_2022")
        c3 = bm.cite("bbs_2022")

        print(f"\n{style} inline citations:")
        print(f"  {c1}  {c2}  {c3}")

        print(f"\n{style} bibliography (first 2 entries):")
        bib_list = bm.bibliography_list()
        for entry in bib_list[:2]:
            print(f"  {entry[:120]}{'…' if len(entry) > 120 else ''}")


# =============================================================================
# EXAMPLE 5 – PDF only (skip DOCX)
# =============================================================================

def example_5_pdf_only():
    """Generate only the PDF report."""
    print("\n" + "=" * 60)
    print("  EXAMPLE 5: PDF only")
    print("=" * 60)

    import report_config as cfg
    cfg.GENERATE_PDF = True
    cfg.GENERATE_DOCX = False

    data_path = os.path.join(_SCRIPT_DIR, "sample_data.csv")
    df = load_data(data_path)
    df = validate_data(df)
    df = handle_missing_values(df)
    df = assign_geographic_zone(df)
    calc = MEPICalculator(weights=DEFAULT_WEIGHTS)
    results = calc.calculate(df)

    from report_generator_full import FullReportGenerator
    gen = FullReportGenerator(
        results_df=results,
        output_dir=os.path.expanduser("~/energy_poverty_reports/pdf_only"),
    )
    paths = gen.generate()
    print(f"PDF: {paths.get('pdf')}")


# =============================================================================
# Run all examples (or choose one)
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run MEPI report generation examples."
    )
    parser.add_argument(
        "--example",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Which example to run (1=quickstart, 2=custom, 3=charts, 4=bibliography, 5=pdf_only)",
    )
    args = parser.parse_args()

    EXAMPLES = {
        1: example_1_quickstart,
        2: example_2_custom_settings,
        3: example_3_charts_only,
        4: example_4_bibliography,
        5: example_5_pdf_only,
    }

    EXAMPLES[args.example]()
