"""
map_output_manager.py - Folder management for Energy Poverty Index map outputs

Creates and manages the organized directory structure for all MEPI map outputs.

Folder hierarchy
----------------
map_outputs/
├── spatial_maps/       MEPI choropleth + 5 dimension maps
├── regional_maps/      Coastal, char, haor, hill-tract, Sundarbans, urban/rural
├── temporal_maps/      Year comparisons, change maps, animation GIF
├── hotspot_maps/       Cluster, vulnerability, intensity maps
├── analysis_maps/      Top-10 rankings, heatmaps, correlation, distribution
└── interactive_maps/   Folium HTML maps + README

Usage
-----
    from map_output_manager import MapOutputManager
    manager = MapOutputManager()
    manager.create_all_folders()
    path = manager.get_path("spatial_maps", "mepi_spatial_map.png")
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Folder definitions
# ---------------------------------------------------------------------------

#: Top-level output directory
BASE_OUTPUT_DIR = "map_outputs"

#: Sub-directory names and their descriptions
SUBFOLDER_DEFINITIONS: Dict[str, str] = {
    "spatial_maps":    "Spatial distribution maps – MEPI and individual dimensions",
    "regional_maps":   "Regional analysis maps – coastal, char, haor, hill tract, Sundarbans",
    "temporal_maps":   "Time-series and change maps – yearly comparisons and animation",
    "hotspot_maps":    "Clustering and vulnerability maps – hotspots and cluster analysis",
    "analysis_maps":   "Analytical visualisations – rankings, heatmaps, correlations",
    "interactive_maps":"Interactive HTML maps for web-browser exploration",
}

#: Expected file basenames for each sub-directory (informational / for README)
EXPECTED_FILES: Dict[str, List[str]] = {
    "spatial_maps": [
        "mepi_spatial_map.png",
        "availability_map.png",
        "reliability_map.png",
        "adequacy_map.png",
        "quality_map.png",
        "affordability_map.png",
    ],
    "regional_maps": [
        "coastal_analysis_map.png",
        "char_islands_map.png",
        "haor_wetlands_map.png",
        "hill_tract_map.png",
        "sundarbans_map.png",
        "urban_rural_comparison.png",
    ],
    "temporal_maps": [
        "temporal_2020_comparison.png",
        "temporal_2021_comparison.png",
        "temporal_2022_comparison.png",
        "poverty_change_map.png",
        "improvement_areas.png",
        "deterioration_areas.png",
        "temporal_animation.gif",
    ],
    "hotspot_maps": [
        "hotspot_clusters.png",
        "vulnerability_map.png",
        "hotspot_intensity.png",
        "cluster_analysis.png",
    ],
    "analysis_maps": [
        "top10_most_poor.png",
        "top10_least_poor.png",
        "dimension_heatmap.png",
        "dimension_correlation.png",
        "regional_comparison.png",
        "poverty_classification_distribution.png",
    ],
    "interactive_maps": [
        "interactive_map.html",
        "interactive_regional_map.html",
        "interactive_temporal_map.html",
        "README_interactive_maps.txt",
    ],
}


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------

class MapOutputManager:
    """
    Create and validate the organised map-output directory structure.

    Parameters
    ----------
    base_dir : str
        Top-level output directory (default: ``map_outputs``).
    """

    def __init__(self, base_dir: str = BASE_OUTPUT_DIR) -> None:
        self.base_dir = Path(base_dir)

    # ------------------------------------------------------------------
    # Folder creation
    # ------------------------------------------------------------------

    def create_all_folders(self) -> Dict[str, Path]:
        """
        Create the full directory hierarchy.

        Returns
        -------
        dict
            Mapping of subfolder name → absolute Path.
        """
        created: Dict[str, Path] = {}

        # Base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Base directory: {self.base_dir.resolve()}")

        # Sub-directories
        for name in SUBFOLDER_DEFINITIONS:
            folder = self.base_dir / name
            folder.mkdir(parents=True, exist_ok=True)
            created[name] = folder.resolve()
            print(f"   ✅ {name}/")

        return created

    def create_folder(self, subfolder: str) -> Path:
        """Create a single subfolder (and its parent) if it does not exist."""
        folder = self.base_dir / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        return folder.resolve()

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_path(self, subfolder: str, filename: str) -> str:
        """
        Return the full path for a file inside a managed subfolder.

        Parameters
        ----------
        subfolder : str
            One of the keys in SUBFOLDER_DEFINITIONS.
        filename : str
            File basename (e.g. ``"mepi_spatial_map.png"``).

        Returns
        -------
        str
        """
        return str(self.base_dir / subfolder / filename)

    def get_subfolder_path(self, subfolder: str) -> str:
        """Return the absolute path to a subfolder (as a string)."""
        return str((self.base_dir / subfolder).resolve())

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_structure(self) -> Dict[str, bool]:
        """
        Check which sub-directories exist.

        Returns
        -------
        dict
            Mapping of subfolder name → bool (True = exists).
        """
        status: Dict[str, bool] = {}
        for name in SUBFOLDER_DEFINITIONS:
            status[name] = (self.base_dir / name).is_dir()
        return status

    def check_permissions(self) -> Dict[str, bool]:
        """
        Check write permission for each subfolder.

        Returns
        -------
        dict
            Mapping of subfolder name → bool (True = writable).
        """
        writable: Dict[str, bool] = {}
        for name in SUBFOLDER_DEFINITIONS:
            folder = self.base_dir / name
            if folder.is_dir():
                writable[name] = os.access(str(folder), os.W_OK)
            else:
                writable[name] = False
        return writable

    def list_existing_files(self) -> Dict[str, List[str]]:
        """
        List files that already exist in each subfolder.

        Returns
        -------
        dict
            Mapping of subfolder name → list of basenames.
        """
        files: Dict[str, List[str]] = {}
        for name in SUBFOLDER_DEFINITIONS:
            folder = self.base_dir / name
            if folder.is_dir():
                files[name] = sorted(f.name for f in folder.iterdir() if f.is_file())
            else:
                files[name] = []
        return files

    # ------------------------------------------------------------------
    # Documentation generation
    # ------------------------------------------------------------------

    def generate_structure_doc(self, output_path: Optional[str] = None) -> str:
        """
        Generate a plain-text description of the folder hierarchy.

        Parameters
        ----------
        output_path : str, optional
            If given, the document is also written to this path.

        Returns
        -------
        str
            The generated document text.
        """
        lines = [
            "MAP OUTPUT FOLDER STRUCTURE",
            "=" * 50,
            f"Base directory: {self.base_dir.resolve()}",
            "",
        ]

        existing = self.list_existing_files()

        for name, description in SUBFOLDER_DEFINITIONS.items():
            folder = self.base_dir / name
            exists = folder.is_dir()
            status = "✅" if exists else "❌"
            lines.append(f"{status} {name}/")
            lines.append(f"   {description}")
            if exists and existing.get(name):
                for f in existing[name]:
                    lines.append(f"   ├── {f}")
            else:
                expected = EXPECTED_FILES.get(name, [])
                for f in expected:
                    lines.append(f"   ├── {f}  (expected)")
            lines.append("")

        doc = "\n".join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(doc, encoding="utf-8")
            print(f"Structure documentation saved: {output_path}")

        return doc

    def print_status(self) -> None:
        """Print a human-readable status summary to stdout."""
        status = self.validate_structure()
        permissions = self.check_permissions()
        existing = self.list_existing_files()

        print("\n" + "=" * 60)
        print("MAP OUTPUT DIRECTORY STATUS")
        print("=" * 60)
        print(f"Base: {self.base_dir.resolve()}")
        print(f"Base exists: {'✅' if self.base_dir.is_dir() else '❌'}")
        print()

        for name in SUBFOLDER_DEFINITIONS:
            exists = status[name]
            writable = permissions.get(name, False)
            n_files = len(existing.get(name, []))

            markers = []
            markers.append("✅" if exists else "❌")
            if exists:
                markers.append("(writable)" if writable else "(read-only!)")
                markers.append(f"{n_files} file(s)")

            print(f"  {name}/ {' '.join(markers)}")

        print("=" * 60)


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def ensure_all_folders(base_dir: str = BASE_OUTPUT_DIR) -> MapOutputManager:
    """
    Create the complete folder hierarchy and return the manager.

    This is the recommended one-liner for scripts that need the structure
    to exist before saving files::

        from map_output_manager import ensure_all_folders
        mgr = ensure_all_folders()
        path = mgr.get_path("spatial_maps", "mepi_spatial_map.png")
    """
    manager = MapOutputManager(base_dir)
    manager.create_all_folders()
    return manager


def get_output_path(subfolder: str, filename: str, base_dir: str = BASE_OUTPUT_DIR) -> str:
    """
    Quick helper: return a file path inside the organised structure.

    The subfolder is created automatically if it does not exist.
    """
    folder = Path(base_dir) / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Creating map output folder structure...")
    mgr = ensure_all_folders()
    mgr.print_status()
    mgr.generate_structure_doc(str(mgr.base_dir / "folder_structure.txt"))
    print("\nDone! Run 'generate_all_maps_organized.py' to populate the folders.")
