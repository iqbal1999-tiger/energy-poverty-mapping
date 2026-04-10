"""
example_spatial_maps.py - Usage examples for the spatial maps system

Demonstrates how to use spatial_maps_generator.py to create spatial
choropleth maps of the MEPI index for Bangladesh, with examples of:

  1. Basic usage – generate all 6 maps with default settings
  2. Custom output folder
  3. Custom colour scheme (via matplotlib colormaps)
  4. Loading custom MEPI data from a CSV file
  5. Generating individual maps (not all at once)

Run any example:
    python example_spatial_maps.py
    python example_spatial_maps.py --example 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Example 1: Basic usage – generate all 6 maps with default settings
# ---------------------------------------------------------------------------

def example_basic() -> None:
    """
    Example 1 – Basic usage.

    Generates all 6 spatial maps using sample data and saves them to
    the default ~/spatial_maps_png/ folder.
    """
    print("=" * 60)
    print("EXAMPLE 1: Basic usage – all 6 maps to ~/spatial_maps_png/")
    print("=" * 60)

    # Load sample data and compute MEPI
    from data_utils import load_data, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator

    df = load_data("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    results = MEPICalculator().calculate(df)

    # Create the generator (uses default ~/spatial_maps_png/)
    from spatial_maps_generator import SpatialMapsGenerator
    generator = SpatialMapsGenerator(results)

    # Generate all 6 maps
    saved = generator.create_all_maps()

    print(f"\n✅ {len(saved)} maps saved to: {generator._mgr.folder}")
    for p in saved:
        print(f"   ├── {Path(p).name}")


# ---------------------------------------------------------------------------
# Example 2: Custom output folder
# ---------------------------------------------------------------------------

def example_custom_folder() -> None:
    """
    Example 2 – Custom output folder.

    Save maps to a custom directory instead of ~/spatial_maps_png/.
    """
    print("=" * 60)
    print("EXAMPLE 2: Custom output folder")
    print("=" * 60)

    import tempfile
    custom_dir = str(Path(tempfile.gettempdir()) / "my_spatial_maps")
    print(f"Output folder: {custom_dir}")

    from data_utils import load_data, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator

    df = load_data("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    results = MEPICalculator().calculate(df)

    from spatial_maps_generator import SpatialMapsGenerator
    generator = SpatialMapsGenerator(results, output_dir=custom_dir)
    saved = generator.create_all_maps()

    print(f"\n✅ {len(saved)} maps saved to: {custom_dir}")


# ---------------------------------------------------------------------------
# Example 3: Custom colour scheme
# ---------------------------------------------------------------------------

def example_custom_colormap() -> None:
    """
    Example 3 – Custom colour scheme.

    Temporarily override the COLORMAP setting to use a different palette,
    then generate maps with that palette.
    """
    print("=" * 60)
    print("EXAMPLE 3: Custom colour scheme (viridis)")
    print("=" * 60)

    import tempfile
    import spatial_maps_config as cfg

    # Override the colormap setting (temporary for this example)
    original_cmap = cfg.COLORMAP
    cfg.COLORMAP = "viridis"

    custom_dir = str(Path(tempfile.gettempdir()) / "spatial_maps_viridis")

    try:
        from data_utils import load_data, validate_data, handle_missing_values
        from mepi_calculator import MEPICalculator

        df = load_data("sample_data.csv")
        df = validate_data(df)
        df = handle_missing_values(df)
        results = MEPICalculator().calculate(df)

        from spatial_maps_generator import SpatialMapsGenerator
        generator = SpatialMapsGenerator(results, output_dir=custom_dir)

        # Generate only the MEPI overview map with the custom colormap
        path = generator.create_mepi_map()
        print(f"\n✅ MEPI map with viridis colormap saved: {path}")
    finally:
        cfg.COLORMAP = original_cmap  # restore original


# ---------------------------------------------------------------------------
# Example 4: Custom CSV data
# ---------------------------------------------------------------------------

def example_custom_csv(csv_path: Optional[str] = None) -> None:
    """
    Example 4 – Custom MEPI results from a CSV file.

    Loads MEPI data from a user-provided CSV and generates all 6 maps.

    CSV must have columns:
      upazila_name, mepi_score, availability, reliability,
      adequacy, quality, affordability
    """
    print("=" * 60)
    print("EXAMPLE 4: Custom CSV data")
    print("=" * 60)

    import pandas as pd
    import tempfile

    if csv_path and Path(csv_path).exists():
        df = pd.read_csv(csv_path)
        print(f"Loaded: {csv_path} ({len(df)} rows)")
    else:
        # Create a minimal synthetic CSV for demonstration
        import numpy as np

        rng = np.random.default_rng(99)
        n = 50
        df = pd.DataFrame({
            "upazila_name":  [f"Upazila_{i:03d}" for i in range(n)],
            "mepi_score":    rng.uniform(0.1, 0.9, n).round(3),
            "availability":  rng.uniform(0.0, 1.0, n).round(3),
            "reliability":   rng.uniform(0.0, 1.0, n).round(3),
            "adequacy":      rng.uniform(0.0, 1.0, n).round(3),
            "quality":       rng.uniform(0.0, 1.0, n).round(3),
            "affordability": rng.uniform(0.0, 1.0, n).round(3),
        })
        tmp_csv = Path(tempfile.gettempdir()) / "synthetic_mepi.csv"
        df.to_csv(tmp_csv, index=False)
        print(f"No CSV provided – created synthetic data: {tmp_csv}")

    custom_dir = str(Path(tempfile.gettempdir()) / "spatial_maps_custom_csv")

    from spatial_maps_generator import SpatialMapsGenerator
    generator = SpatialMapsGenerator(df, output_dir=custom_dir)
    saved = generator.create_all_maps()

    print(f"\n✅ {len(saved)} maps saved to: {custom_dir}")


# ---------------------------------------------------------------------------
# Example 5: Individual maps
# ---------------------------------------------------------------------------

def example_individual_maps() -> None:
    """
    Example 5 – Generate individual maps instead of all at once.

    Shows how to call create_mepi_map() and create_dimension_maps()
    separately for fine-grained control.
    """
    print("=" * 60)
    print("EXAMPLE 5: Individual maps")
    print("=" * 60)

    import tempfile
    custom_dir = str(Path(tempfile.gettempdir()) / "spatial_maps_individual")

    from data_utils import load_data, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator

    df = load_data("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    results = MEPICalculator().calculate(df)

    from spatial_maps_generator import SpatialMapsGenerator
    generator = SpatialMapsGenerator(results, output_dir=custom_dir)

    # Only the overall MEPI map
    print("\n--- Generating overall MEPI map only ---")
    mepi_path = generator.create_mepi_map()
    print(f"Saved: {mepi_path}")

    # Only the dimension maps
    print("\n--- Generating dimension maps only ---")
    dim_paths = generator.create_dimension_maps()
    for p in dim_paths:
        print(f"Saved: {Path(p).name}")

    print(f"\n✅ All done. Output: {custom_dir}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

EXAMPLES = {
    1: ("Basic usage – all 6 maps to ~/spatial_maps_png/", example_basic),
    2: ("Custom output folder",                             example_custom_folder),
    3: ("Custom colour scheme (viridis)",                   example_custom_colormap),
    4: ("Custom CSV data",                                  example_custom_csv),
    5: ("Individual maps (one at a time)",                  example_individual_maps),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Usage examples for spatial_maps_generator.py"
    )
    parser.add_argument(
        "--example", type=int, choices=list(EXAMPLES), default=1,
        help="Which example to run (1–5). Default: 1 (basic usage).",
    )
    parser.add_argument(
        "--csv", default=None,
        help="Path to custom MEPI CSV file (used by example 4).",
    )
    args = parser.parse_args()

    print("\nAvailable examples:")
    for num, (desc, _) in EXAMPLES.items():
        marker = "▶" if num == args.example else " "
        print(f"  {marker} {num}. {desc}")
    print()

    _, fn = EXAMPLES[args.example]
    if args.example == 4:
        fn(args.csv)
    else:
        fn()


if __name__ == "__main__":
    main()
