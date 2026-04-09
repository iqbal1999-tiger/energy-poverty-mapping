"""
setup_folder_structure.py - Initial setup script for map output directories

Creates the entire map_outputs/ folder hierarchy, verifies all subfolders,
and generates structure documentation.

Run this script once at the start of a new project or after cloning the repo:

    python setup_folder_structure.py

After running, the following structure will exist:

    map_outputs/
    ├── spatial_maps/
    ├── regional_maps/
    ├── temporal_maps/
    ├── hotspot_maps/
    ├── analysis_maps/
    └── interactive_maps/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from map_output_manager import MapOutputManager, BASE_OUTPUT_DIR, SUBFOLDER_DEFINITIONS


def setup(base_dir: str = BASE_OUTPUT_DIR) -> bool:
    """
    Create the full map output directory hierarchy.

    Parameters
    ----------
    base_dir : str
        Top-level output directory (default: ``map_outputs``).

    Returns
    -------
    bool
        True if all folders were created / already exist.
    """
    print("=" * 60)
    print("ENERGY POVERTY MAPPING – FOLDER SETUP")
    print("=" * 60)

    manager = MapOutputManager(base_dir)

    # 1. Create all folders
    print("\n[1/4] Creating folder structure ...")
    manager.create_all_folders()

    # 2. Verify
    print("\n[2/4] Verifying folder structure ...")
    status = manager.validate_structure()
    all_ok = True
    for name, exists in status.items():
        marker = "✅" if exists else "❌"
        print(f"   {marker} {name}/")
        if not exists:
            all_ok = False

    # 3. Check write permissions
    print("\n[3/4] Checking write permissions ...")
    permissions = manager.check_permissions()
    for name, writable in permissions.items():
        marker = "✅" if writable else "⚠  READ-ONLY"
        print(f"   {marker} {name}/")

    # 4. Generate documentation
    print("\n[4/4] Generating folder structure documentation ...")
    doc_path = os.path.join(base_dir, "folder_structure.txt")
    manager.generate_structure_doc(doc_path)

    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ Setup complete!  All folders created successfully.")
        print(f"\nOutput directory: {Path(base_dir).resolve()}")
        print("\nNext steps:")
        print("  python generate_all_maps_organized.py   # generate all maps")
        print("  python map_organizer.py                 # sort any existing PNGs")
    else:
        print("❌ Some folders could not be created. Check permissions.")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else BASE_OUTPUT_DIR
    success = setup(base)
    sys.exit(0 if success else 1)
