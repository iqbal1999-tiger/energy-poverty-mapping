"""
map_organizer.py - Automatically sort map PNG/HTML files into organised subfolders

Monitors the map_outputs/ directory and moves files into the correct category
subfolder based on the filename pattern.

Sorting rules
-------------
  spatial_maps/    ← mepi, availability, reliability, adequacy, quality, affordability
  regional_maps/   ← coastal, char, haor, hill, sundarbans, urban_rural, urban, rural
  temporal_maps/   ← temporal, change, improvement, deterioration, animation
  hotspot_maps/    ← hotspot, vulnerability, cluster
  analysis_maps/   ← top10, dimension, regional_comparison, distribution, correlation
  interactive_maps/← .html files and README_interactive*

Usage
-----
    from map_organizer import MapOrganizer
    organizer = MapOrganizer()
    report = organizer.organize()

    # Or sort a specific file:
    organizer.sort_file("map_outputs/hotspot_clusters.png")
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from map_output_manager import (
    MapOutputManager,
    BASE_OUTPUT_DIR,
    SUBFOLDER_DEFINITIONS,
    EXPECTED_FILES as _EXPECTED_FILES,
)

# ---------------------------------------------------------------------------
# Classification rules: (regex pattern, target subfolder)
# Rules are checked in order; first match wins.
# ---------------------------------------------------------------------------

CLASSIFICATION_RULES: List[Tuple[str, str]] = [
    # Interactive HTML maps
    (r".*\.html$",                        "interactive_maps"),
    (r"readme_interactive.*",             "interactive_maps"),

    # Temporal maps (check before spatial to catch "temporal_*" names)
    (r"temporal.*",                       "temporal_maps"),
    (r".*_temporal.*",                    "temporal_maps"),
    (r"poverty_change.*",                 "temporal_maps"),
    (r"improvement.*",                    "temporal_maps"),
    (r"deterioration.*",                  "temporal_maps"),
    (r".*animation.*",                    "temporal_maps"),
    (r".*change_map.*",                   "temporal_maps"),

    # Hotspot maps
    (r"hotspot.*",                        "hotspot_maps"),
    (r".*hotspot.*",                      "hotspot_maps"),
    (r"vulnerability.*",                  "hotspot_maps"),
    (r".*vulnerability.*",                "hotspot_maps"),
    (r"cluster.*",                        "hotspot_maps"),
    (r".*cluster.*",                      "hotspot_maps"),

    # Regional maps
    (r"coastal.*",                        "regional_maps"),
    (r".*coastal.*",                      "regional_maps"),
    (r"char.*",                           "regional_maps"),
    (r".*char_island.*",                  "regional_maps"),
    (r"haor.*",                           "regional_maps"),
    (r".*haor.*",                         "regional_maps"),
    (r"hill.*",                           "regional_maps"),
    (r".*hill_tract.*",                   "regional_maps"),
    (r"sundarbans.*",                     "regional_maps"),
    (r".*sundarbans.*",                   "regional_maps"),
    (r"urban_rural.*",                    "regional_maps"),
    (r".*urban_rural.*",                  "regional_maps"),
    (r"regional_analysis.*",              "regional_maps"),

    # Analysis maps
    (r"top10.*",                          "analysis_maps"),
    (r".*top10.*",                        "analysis_maps"),
    (r"dimension_heatmap.*",              "analysis_maps"),
    (r"dimension_correlation.*",          "analysis_maps"),
    (r"regional_comparison.*",            "analysis_maps"),
    (r"poverty_classification.*",         "analysis_maps"),
    (r".*distribution.*",                 "analysis_maps"),
    (r".*correlation.*",                  "analysis_maps"),
    (r".*heatmap.*",                      "analysis_maps"),
    (r".*analysis.*",                     "analysis_maps"),

    # Spatial maps (broad – catches mepi, availability, reliability, etc.)
    (r"mepi.*",                           "spatial_maps"),
    (r"spatial.*",                        "spatial_maps"),
    (r"availability.*",                   "spatial_maps"),
    (r"reliability.*",                    "spatial_maps"),
    (r"adequacy.*",                       "spatial_maps"),
    (r"quality.*",                        "spatial_maps"),
    (r"affordability.*",                  "spatial_maps"),
    (r"dimension_.*_map.*",              "spatial_maps"),
    (r"poverty_category.*",              "spatial_maps"),
]


# ---------------------------------------------------------------------------
# Organizer class
# ---------------------------------------------------------------------------

class MapOrganizer:
    """
    Sort map files in map_outputs/ into the correct category subfolders.

    Parameters
    ----------
    base_dir : str
        Top-level output directory (default: ``map_outputs``).
    dry_run : bool
        If True, report what *would* be moved without actually moving files.
    """

    def __init__(
        self,
        base_dir: str = BASE_OUTPUT_DIR,
        dry_run: bool = False,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self._manager = MapOutputManager(base_dir)

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_file(self, filename: str) -> Optional[str]:
        """
        Determine the target subfolder for *filename*.

        Parameters
        ----------
        filename : str
            Basename of the file (e.g. ``"hotspot_clusters.png"``).

        Returns
        -------
        str or None
            Target subfolder name, or None if no rule matched.
        """
        name_lower = filename.lower()
        for pattern, subfolder in CLASSIFICATION_RULES:
            if re.match(pattern, name_lower):
                return subfolder
        return None

    # ------------------------------------------------------------------
    # Moving / sorting
    # ------------------------------------------------------------------

    def sort_file(self, file_path: str) -> Optional[str]:
        """
        Move *file_path* into the appropriate subfolder.

        Parameters
        ----------
        file_path : str
            Path to the file to sort (may be absolute or relative).

        Returns
        -------
        str or None
            Destination path if the file was (or would be) moved, else None.
        """
        src = Path(file_path)
        if not src.exists():
            print(f"   ⚠  File not found: {file_path}")
            return None

        target = self.classify_file(src.name)
        if target is None:
            print(f"   ❓ No rule matched for: {src.name}")
            return None

        dest_dir = self.base_dir / target
        dest = dest_dir / src.name

        if src.resolve() == dest.resolve():
            return str(dest)  # already in the right place

        if self.dry_run:
            print(f"   [dry-run] Would move: {src.name} → {target}/")
            return str(dest)

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        print(f"   Moved: {src.name} → {target}/")
        return str(dest)

    def organize(self, source_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Scan *source_dir* (defaults to base_dir) for unsorted PNG/GIF/HTML
        files and move them into the correct subfolders.

        Parameters
        ----------
        source_dir : str, optional
            Directory to scan.  Files inside subfolders are not touched.

        Returns
        -------
        dict
            Mapping of subfolder name → list of moved file basenames.
        """
        scan_dir = Path(source_dir) if source_dir else self.base_dir
        moved: Dict[str, List[str]] = {k: [] for k in SUBFOLDER_DEFINITIONS}
        skipped: List[str] = []

        # Only look at files directly in scan_dir (not recursively)
        candidates = [
            f for f in scan_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {".png", ".gif", ".html", ".txt"}
        ]

        if not candidates:
            print(f"No unsorted files found in {scan_dir}/")
            return moved

        print(f"Found {len(candidates)} file(s) to sort in {scan_dir}/")
        for f in sorted(candidates):
            target = self.classify_file(f.name)
            if target is None:
                skipped.append(f.name)
                continue

            dest_dir = self.base_dir / target
            dest = dest_dir / f.name

            if f.resolve() == dest.resolve():
                continue  # already in place

            if self.dry_run:
                print(f"   [dry-run] {f.name} → {target}/")
                moved[target].append(f.name)
                continue

            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            print(f"   {f.name} → {target}/")
            moved[target].append(f.name)

        if skipped:
            print(f"\n   ⚠  {len(skipped)} file(s) not matched by any rule:")
            for name in skipped:
                print(f"      - {name}")

        return moved

    # ------------------------------------------------------------------
    # README generation
    # ------------------------------------------------------------------

    def generate_readmes(self) -> None:
        """Generate a README.txt file in each subfolder."""
        for name, description in SUBFOLDER_DEFINITIONS.items():
            folder = self.base_dir / name
            folder.mkdir(parents=True, exist_ok=True)

            expected = _EXPECTED_FILES.get(name, [])
            existing = sorted(
                f.name for f in folder.iterdir() if f.is_file() and f.name != "README.txt"
            )

            lines = [
                f"{'=' * 50}",
                f"FOLDER: {name}/",
                f"{'=' * 50}",
                f"Description: {description}",
                "",
                "Files in this folder:",
            ]

            if existing:
                for f in existing:
                    lines.append(f"  - {f}")
            else:
                lines.append("  (no files yet)")
                lines.append("")
                lines.append("Expected files:")
                for f in expected:
                    lines.append(f"  - {f}")

            lines += [
                "",
                "Naming convention:",
                "  {type}_{dimension/region}_{suffix}.png",
                "",
                "Generated by map_organizer.py",
            ]

            readme_path = folder / "README.txt"
            readme_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"   README.txt written: {name}/")

    def generate_interactive_readme(self) -> None:
        """Generate a detailed README for the interactive_maps/ subfolder."""
        folder = self.base_dir / "interactive_maps"
        folder.mkdir(parents=True, exist_ok=True)

        content = """README - Interactive Maps
========================

This folder contains interactive HTML maps for the Bangladesh Energy Poverty
Mapping project.  Open any .html file in a modern web browser to explore the
maps.

Files
-----
  interactive_map.html          Main MEPI overview map
  interactive_regional_map.html Regional analysis map
  interactive_temporal_map.html Temporal change explorer

Features
--------
  - Click any upazila to see detailed poverty scores
  - Hover for quick tooltip
  - Toggle dimension layers via the Layer Control panel
  - Switch basemaps (street / satellite / dark)
  - Fullscreen button available

Requirements
------------
  An active internet connection is needed for the basemap tiles.
  No installation required – runs in any modern browser.

Generated by updated_interactive_folium_maps.py
"""
        readme_path = folder / "README_interactive_maps.txt"
        readme_path.write_text(content, encoding="utf-8")
        print(f"   Interactive maps README written.")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sort map files in map_outputs/ into organised subfolders."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be moved without actually moving files.",
    )
    parser.add_argument(
        "--base-dir", default=BASE_OUTPUT_DIR,
        help=f"Top-level output directory (default: {BASE_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--readme", action="store_true",
        help="Generate README.txt files in each subfolder.",
    )
    args = parser.parse_args()

    organizer = MapOrganizer(base_dir=args.base_dir, dry_run=args.dry_run)
    organizer.organize()
    if args.readme:
        organizer.generate_readmes()
        organizer.generate_interactive_readme()
