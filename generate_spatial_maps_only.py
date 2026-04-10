"""
generate_spatial_maps_only.py - Master script: generate ALL 6 spatial maps
                                to ~/spatial_maps_png/ with one command

Steps
-----
  1. Create ~/spatial_maps_png/ folder
  2. Load MEPI data (from CSV or computed from sample_data.csv)
  3. Validate shapefile availability
  4. Generate 6 spatial choropleth maps (with progress output)
  5. Generate README.txt, map_legend.txt, index.html
  6. Print summary report with output folder location

Usage
-----
    python generate_spatial_maps_only.py
    python generate_spatial_maps_only.py --data path/to/mepi_results.csv
    python generate_spatial_maps_only.py --output-dir /custom/spatial_maps_png/
    python generate_spatial_maps_only.py --shapefile shapefiles/bgd_adm2.shp
    python generate_spatial_maps_only.py --clear   (remove old PNGs first)
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path
from typing import List, Optional

import pandas as pd

from spatial_maps_config import SPATIAL_OUTPUT_FOLDER, find_shapefile, print_config
from spatial_folder_manager import SpatialFolderManager, ensure_spatial_folder
from spatial_maps_generator import SpatialMapsGenerator, _load_mepi_data
from spatial_maps_index import SpatialMapsIndex

warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def _section(title: str, step: int, total: int) -> None:
    print(f"\n[{step}/{total}] {title}")
    print("-" * 55)


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def _print_summary(
    saved_maps: List[str],
    doc_files: List[str],
    folder: Path,
    df: pd.DataFrame,
    elapsed: float,
) -> None:
    print("\n" + "=" * 60)
    print("SPATIAL MAPS GENERATION – SUMMARY")
    print("=" * 60)

    print(f"\n  Upazilas processed : {len(df)}")
    if "mepi_score" in df.columns:
        print(f"  Mean MEPI score    : {df['mepi_score'].mean():.3f}")
        print(f"  Std Dev            : {df['mepi_score'].std():.3f}")
        print(f"  Min MEPI           : {df['mepi_score'].min():.3f}")
        print(f"  Max MEPI           : {df['mepi_score'].max():.3f}")

    print(f"\n  PNG maps generated : {len(saved_maps)}")
    for p in saved_maps:
        print(f"    ├── {Path(p).name}")

    print(f"\n  Documentation files: {len(doc_files)}")
    for p in doc_files:
        print(f"    ├── {Path(p).name}")

    print(f"\n  Output folder      : {folder}")
    print(f"  Browse maps at     : file://{folder / 'index.html'}")
    print(f"  Time elapsed       : {elapsed:.1f} seconds")
    print("\n" + "=" * 60)
    print("✅ All spatial maps generated successfully!")
    print(f"\n  Open in browser:")
    print(f"  file://{folder / 'index.html'}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate 6 spatial MEPI choropleth maps to a dedicated folder. "
            f"Default output: {SPATIAL_OUTPUT_FOLDER}"
        )
    )
    parser.add_argument(
        "--data", default="",
        help="Path to MEPI results CSV. If omitted, uses sample_data.csv.",
    )
    parser.add_argument(
        "--output-dir", default=SPATIAL_OUTPUT_FOLDER,
        help=f"Output folder for PNG maps (default: {SPATIAL_OUTPUT_FOLDER}).",
    )
    parser.add_argument(
        "--shapefile", default=None,
        help="Path to Bangladesh upazila shapefile.",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Remove existing PNG files from the output folder before generating.",
    )
    args = parser.parse_args()

    start = time.time()
    total_steps = 5

    print("=" * 60)
    print("ENERGY POVERTY MAPPING – SPATIAL MAPS ONLY")
    print("=" * 60)
    print_config()

    # ------------------------------------------------------------------
    # Step 1: Create output folder
    # ------------------------------------------------------------------
    _section("Creating spatial maps folder", 1, total_steps)
    mgr = ensure_spatial_folder(args.output_dir)
    mgr.print_status()

    if args.clear:
        print("\n  Clearing old PNG files ...")
        mgr.clear_png_files()

    # ------------------------------------------------------------------
    # Step 2: Load MEPI data
    # ------------------------------------------------------------------
    _section("Loading MEPI data", 2, total_steps)
    try:
        df = _load_mepi_data(args.data)
        print(f"   {len(df)} upazilas loaded.")
    except Exception as exc:
        print(f"❌ Failed to load data: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3: Validate shapefile
    # ------------------------------------------------------------------
    _section("Validating shapefile", 3, total_steps)
    shapefile = args.shapefile or find_shapefile()
    if shapefile:
        print(f"  ✅ Shapefile found: {shapefile}")
    else:
        print("  ⚠  No shapefile found – maps will use scatter-plot approximation.")
        print("     To get boundary maps, add a .shp file to the shapefiles/ folder.")
        print("     (See instructions_shapefile.md for download instructions.)")

    # ------------------------------------------------------------------
    # Step 4: Generate maps
    # ------------------------------------------------------------------
    _section("Generating 6 spatial choropleth maps", 4, total_steps)
    try:
        generator = SpatialMapsGenerator(
            df,
            output_dir=args.output_dir,
            shapefile_path=shapefile,
        )
        saved_maps = generator.create_all_maps()
    except Exception as exc:
        print(f"❌ Map generation failed: {exc}")
        raise

    # ------------------------------------------------------------------
    # Step 5: Generate documentation
    # ------------------------------------------------------------------
    _section("Generating documentation (README, legend, index.html)", 5, total_steps)
    try:
        indexer = SpatialMapsIndex(output_dir=args.output_dir)
        doc_files = indexer.generate_all()
    except Exception as exc:
        print(f"⚠  Documentation generation failed: {exc}")
        doc_files = []

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - start
    _print_summary(saved_maps, doc_files, mgr.folder, df, elapsed)


if __name__ == "__main__":
    main()
