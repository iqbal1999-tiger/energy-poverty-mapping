"""
generate_all_visualizations.py - Run all MEPI visualizations in one command

Loads MEPI results from sample_data.csv (or a custom path), calculates MEPI
scores, generates all 25+ PNG visualizations, and saves them to the
visualizations/ folder.

Usage:
    python generate_all_visualizations.py
    python generate_all_visualizations.py --data my_data.csv
    python generate_all_visualizations.py --data my_data.csv --output output_charts/
"""

import argparse
import logging
import os
import sys
import time

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate all MEPI energy poverty visualizations as PNG files."
    )
    parser.add_argument(
        "--data",
        default="sample_data.csv",
        help="Path to input CSV/Excel file (default: sample_data.csv)",
    )
    parser.add_argument(
        "--output",
        default="visualizations",
        help="Output directory for PNG files (default: visualizations/)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution in DPI for saved figures (default: 300)",
    )
    return parser.parse_args()


def load_data(data_path: str):
    """Load raw indicator data from CSV or Excel file."""
    import pandas as pd

    if not os.path.exists(data_path):
        logger.error("Data file not found: %s", data_path)
        sys.exit(1)

    ext = os.path.splitext(data_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(data_path)
    else:
        df = pd.read_csv(data_path)

    logger.info("Loaded %d rows from %s", len(df), data_path)
    return df


def run(data_path: str = "sample_data.csv", output_dir: str = "visualizations",
        dpi: int = 300):
    """
    Full pipeline: load data → calculate MEPI → generate all PNG charts.

    Parameters
    ----------
    data_path : str
        Path to the raw indicator data CSV/Excel file.
    output_dir : str
        Directory where PNG files will be saved.
    dpi : int
        Resolution for saved figures.

    Returns
    -------
    list of str
        Paths of all generated PNG files.
    """
    start = time.time()

    # ── 1. Load raw data ────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("Energy Poverty Index – Visualization Generator")
    logger.info("═" * 60)
    logger.info("Step 1/3 – Loading data from: %s", data_path)
    df = load_data(data_path)

    # ── 2. Calculate MEPI ────────────────────────────────────────────────
    logger.info("Step 2/3 – Calculating MEPI scores …")
    try:
        from mepi_calculator import MEPICalculator
        from config import GEOGRAPHIC_ZONES
        calc = MEPICalculator()
        results = calc.calculate(df)
        logger.info(
            "  MEPI calculated for %d upazilas  (mean=%.3f)",
            len(results),
            results["mepi_score"].mean(),
        )
    except Exception as exc:
        logger.error("MEPI calculation failed: %s", exc)
        logger.info("Attempting to use pre-computed data as-is …")
        results = df
        GEOGRAPHIC_ZONES = {}

    # ── 3. Generate visualizations ───────────────────────────────────────
    logger.info("Step 3/3 – Generating visualizations → %s/", output_dir)
    from visualization_generator import MEPIVisualizationGenerator

    try:
        geo_zones = GEOGRAPHIC_ZONES
    except NameError:
        geo_zones = {}

    gen = MEPIVisualizationGenerator(
        results,
        output_dir=output_dir,
        dpi=dpi,
        geographic_zones=geo_zones,
    )
    saved_paths = gen.generate_all()

    elapsed = time.time() - start
    logger.info("═" * 60)
    logger.info(
        "Done! %d visualizations saved to '%s/' in %.1fs",
        len(saved_paths), output_dir, elapsed,
    )
    logger.info("═" * 60)

    for path in sorted(saved_paths):
        logger.info("  • %s", path)

    return saved_paths


def main():
    args = parse_args()
    run(data_path=args.data, output_dir=args.output, dpi=args.dpi)


if __name__ == "__main__":
    main()
