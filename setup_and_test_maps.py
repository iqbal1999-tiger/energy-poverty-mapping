"""
setup_and_test_maps.py - Diagnostic and testing script for the mapping system

Checks:
  1. Required Python packages are installed
  2. Shapefile exists and is valid (if present)
  3. MEPI data loads correctly
  4. Upazilas can be matched to the coordinate database
  5. Sample maps can be generated

Run this script first to verify your environment is configured correctly:

    python setup_and_test_maps.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Package checks
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "scipy": "scipy",
    "geopandas": "geopandas",
    "folium": "folium",
    "branca": "branca",
    "shapely": "shapely",
    "mapclassify": "mapclassify",
}

OPTIONAL_PACKAGES = {
    "plotly": "plotly",
    "PIL": "Pillow",
}


def check_packages() -> bool:
    print("\n[1/5] Checking Python packages ...")
    all_ok = True
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name}  – install with: pip install {pip_name}")
            all_ok = False

    for import_name, pip_name in OPTIONAL_PACKAGES.items():
        try:
            __import__(import_name)
            print(f"  ✅ {pip_name} (optional)")
        except ImportError:
            print(f"  ℹ  {pip_name} (optional) not installed")

    return all_ok


# ---------------------------------------------------------------------------
# 2. Shapefile check
# ---------------------------------------------------------------------------

def check_shapefile() -> bool:
    print("\n[2/5] Checking shapefile ...")
    try:
        from shapefile_loader import ShapefileLoader, find_shapefile
    except ImportError as exc:
        print(f"  ❌ Could not import shapefile_loader: {exc}")
        return False

    path = find_shapefile(".")
    if path is None:
        print(
            "  ⚠  No Bangladesh shapefile found in 'shapefiles/' directory.\n"
            "     Maps will use centroid scatter-plot fallback.\n"
            "     See instructions_shapefile.md for download instructions."
        )
        return False  # not an error – just a warning

    print(f"  Found: {path}")
    try:
        loader = ShapefileLoader(path)
        loader.print_summary()
        valid = loader.check_integrity()
        if valid:
            print("  ✅ Shapefile is valid")
        else:
            report = loader.validate()
            print(f"  ⚠  Issues: {report}")
        return True
    except Exception as exc:
        print(f"  ❌ Error loading shapefile: {exc}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# 3. MEPI data check
# ---------------------------------------------------------------------------

def check_mepi_data() -> bool:
    print("\n[3/5] Checking MEPI sample data ...")
    try:
        from data_utils import load_data, validate_data, handle_missing_values
        from mepi_calculator import MEPICalculator

        df = load_data("sample_data.csv")
        df = validate_data(df)
        df = handle_missing_values(df)
        calc = MEPICalculator()
        results = calc.calculate(df)
        print(f"  ✅ MEPI calculated for {len(results)} upazilas")
        print(f"     Mean MEPI: {results['mepi_score'].mean():.3f}")
        return True
    except Exception as exc:
        print(f"  ❌ Error: {exc}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# 4. Coordinate database check
# ---------------------------------------------------------------------------

def check_coordinates() -> bool:
    print("\n[4/5] Checking upazila coordinate database ...")
    try:
        from bangladesh_coordinates import UpazilaDatabase

        db = UpazilaDatabase()
        df = db.all_upazilas()
        print(f"  ✅ Database loaded: {len(df)} reference upazilas")

        # Validate bounds
        out_of_bounds = db.validate_coordinates()
        if len(out_of_bounds):
            print(f"  ⚠  {len(out_of_bounds)} upazilas have out-of-bounds coordinates")
        else:
            print("  ✅ All coordinates within Bangladesh bounds")

        # Test fuzzy matching
        test_names = ["Teknuf", "Bogra", "Barisal", "Cumilla"]
        for n in test_names:
            match = db.find_match(n)
            print(f"     '{n}' → '{match}'")

        return True
    except Exception as exc:
        print(f"  ❌ Error: {exc}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# 5. Map generation test
# ---------------------------------------------------------------------------

def check_map_generation() -> bool:
    print("\n[5/5] Testing map generation ...")
    try:
        from data_utils import load_data, validate_data, handle_missing_values
        from mepi_calculator import MEPICalculator
        from correct_spatial_mapping import SpatialMapper

        df = load_data("sample_data.csv")
        df = validate_data(df)
        df = handle_missing_values(df)
        calc = MEPICalculator()
        results = calc.calculate(df)

        os.makedirs("map_outputs", exist_ok=True)
        mapper = SpatialMapper(results)

        # MEPI map
        path = mapper.create_mepi_map("map_outputs/test_mepi_map.png")
        print(f"  ✅ MEPI map saved: {path}")

        # Hotspot map
        path = mapper.create_hotspot_map("map_outputs/test_hotspot_map.png")
        print(f"  ✅ Hotspot map saved: {path}")

        # Category map
        path = mapper.create_poverty_category_map(
            "map_outputs/test_category_map.png"
        )
        print(f"  ✅ Category map saved: {path}")

        return True
    except Exception as exc:
        print(f"  ❌ Error generating maps: {exc}")
        traceback.print_exc()
        return False


def check_interactive_map() -> bool:
    print("\n[+] Testing interactive map generation ...")
    try:
        from data_utils import load_data, validate_data, handle_missing_values
        from mepi_calculator import MEPICalculator
        from interactive_folium_maps import InteractiveMapper

        df = load_data("sample_data.csv")
        df = validate_data(df)
        df = handle_missing_values(df)
        calc = MEPICalculator()
        results = calc.calculate(df)

        mapper = InteractiveMapper(results)
        path = mapper.create_mepi_map("map_outputs/test_interactive_map.html")
        print(f"  ✅ Interactive map saved: {path}")
        return True
    except Exception as exc:
        print(f"  ❌ Error generating interactive map: {exc}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("BANGLADESH ENERGY POVERTY MAPPING – SETUP & TEST")
    print("=" * 60)

    results = {
        "packages": check_packages(),
        "shapefile": check_shapefile(),
        "mepi_data": check_mepi_data(),
        "coordinates": check_coordinates(),
        "maps": check_map_generation(),
    }
    check_interactive_map()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    icons = {True: "✅", False: "❌"}
    for check, ok in results.items():
        print(f"  {icons[ok]} {check}")

    critical_ok = results["packages"] and results["mepi_data"] and results["maps"]
    if critical_ok:
        print(
            "\n✅ Setup complete!  Run example_correct_mapping.py to generate "
            "all maps."
        )
    else:
        print(
            "\n⚠  Some checks failed.  Review the errors above and install "
            "missing packages or fix data issues before running maps."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
