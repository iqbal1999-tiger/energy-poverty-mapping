"""
external_folder_manager.py - Create and manage the external map output folder

Handles the full lifecycle of the external directory structure used to store
all Energy Poverty Index (MEPI) map outputs outside the repository.

Folder created
--------------
~/map_outputs_energy_poverty/           (default, configurable)
├── spatial_maps/
├── regional_maps/
├── temporal_maps/
├── hotspot_maps/
├── analysis_maps/
└── interactive_maps/

Usage
-----
    from external_folder_manager import ExternalFolderManager
    mgr = ExternalFolderManager()
    mgr.create_all_folders()
    mgr.print_status()

    # Get a specific file path
    path = mgr.get_path("spatial_maps", "mepi_spatial_map.png")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from map_config_external import (
    EXTERNAL_OUTPUT_BASE,
    SUBFOLDERS,
    get_base_path,
    get_subfolder_path,
)

# ---------------------------------------------------------------------------
# Descriptions for each subfolder (used in reports and README files)
# ---------------------------------------------------------------------------

SUBFOLDER_DESCRIPTIONS: Dict[str, str] = {
    "spatial_maps":    "Spatial distribution maps – MEPI score and individual dimension maps",
    "regional_maps":   "Regional analysis maps – coastal, char islands, haor, hill tracts, Sundarbans",
    "temporal_maps":   "Temporal comparison maps – year-by-year changes and animated GIF",
    "hotspot_maps":    "Hotspot and cluster analysis maps – vulnerability and poverty intensity",
    "analysis_maps":   "Statistical analysis maps – rankings, heatmaps, correlations, distribution",
    "interactive_maps":"Interactive HTML maps for web-browser exploration (Folium)",
}

# Expected filenames per subfolder (for documentation and validation)
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

class ExternalFolderManager:
    """
    Create and validate the external map-output directory structure.

    Parameters
    ----------
    base_dir : str, optional
        Override the external output root.  Defaults to
        ``EXTERNAL_OUTPUT_BASE`` from ``map_config_external``.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            self.base_dir = get_base_path()
        else:
            self.base_dir = Path(base_dir).expanduser().resolve()

    # ------------------------------------------------------------------
    # Folder creation
    # ------------------------------------------------------------------

    def create_all_folders(self) -> Dict[str, Path]:
        """
        Create the full external directory hierarchy.

        Returns
        -------
        dict
            Mapping of subfolder name → absolute Path.
        """
        created: Dict[str, Path] = {}

        self.base_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ External output directory: {self.base_dir}")

        for name in SUBFOLDERS:
            folder = self.base_dir / name
            folder.mkdir(parents=True, exist_ok=True)
            created[name] = folder
            print(f"   ✅ {name}/")

        return created

    def create_folder(self, subfolder: str) -> Path:
        """Create a single subfolder (and its parent if necessary)."""
        folder = self.base_dir / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_path(self, subfolder: str, filename: str) -> str:
        """
        Return the full string path for a file inside a managed subfolder.

        Parameters
        ----------
        subfolder : str
            One of the keys in SUBFOLDER_DESCRIPTIONS.
        filename : str
            File basename (e.g. ``"mepi_spatial_map.png"``).
        """
        return str(self.base_dir / subfolder / filename)

    def get_subfolder(self, subfolder: str) -> Path:
        """Return the Path of a subfolder (does not create it)."""
        return self.base_dir / subfolder

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_structure(self) -> Dict[str, bool]:
        """
        Check which sub-directories exist.

        Returns
        -------
        dict
            Mapping of subfolder name → bool.
        """
        return {name: (self.base_dir / name).is_dir() for name in SUBFOLDERS}

    def check_permissions(self) -> Dict[str, bool]:
        """
        Check write permission for each subfolder.

        Returns
        -------
        dict
            Mapping of subfolder name → bool (True = writable).
        """
        writable: Dict[str, bool] = {}
        for name in SUBFOLDERS:
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
        for name in SUBFOLDERS:
            folder = self.base_dir / name
            if folder.is_dir():
                files[name] = sorted(f.name for f in folder.iterdir() if f.is_file())
            else:
                files[name] = []
        return files

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_structure_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate a plain-text report of the folder hierarchy and current contents.

        Parameters
        ----------
        output_path : str, optional
            If provided the report is also written to this path.

        Returns
        -------
        str
            The report text.
        """
        existing = self.list_existing_files()
        lines = [
            "EXTERNAL MAP OUTPUT FOLDER STRUCTURE",
            "=" * 50,
            f"Base directory : {self.base_dir}",
            "",
        ]

        for name, description in SUBFOLDER_DESCRIPTIONS.items():
            folder = self.base_dir / name
            exists = folder.is_dir()
            marker = "✅" if exists else "❌"
            lines.append(f"{marker} {name}/")
            lines.append(f"   {description}")

            if exists and existing.get(name):
                for f in existing[name]:
                    lines.append(f"   ├── {f}")
            else:
                for f in EXPECTED_FILES.get(name, []):
                    lines.append(f"   ├── {f}  (expected)")
            lines.append("")

        report = "\n".join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report, encoding="utf-8")
            print(f"Report saved: {output_path}")

        return report

    def print_status(self) -> None:
        """Print a human-readable status summary."""
        status = self.validate_structure()
        permissions = self.check_permissions()
        existing = self.list_existing_files()

        print("\n" + "=" * 60)
        print("EXTERNAL MAP OUTPUT DIRECTORY STATUS")
        print("=" * 60)
        print(f"Base: {self.base_dir}")
        print(f"Base exists: {'✅' if self.base_dir.is_dir() else '❌'}")
        print()

        for name in SUBFOLDERS:
            exists = status[name]
            writable = permissions.get(name, False)
            n_files = len(existing.get(name, []))

            parts = ["✅" if exists else "❌"]
            if exists:
                parts.append("(writable)" if writable else "(read-only!)")
                parts.append(f"{n_files} file(s)")
            print(f"  {name}/ {' '.join(parts)}")

        print("=" * 60)


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------


def ensure_external_folders(base_dir: Optional[str] = None) -> ExternalFolderManager:
    """
    Create the full external folder hierarchy and return the manager.

    Example usage::

        from external_folder_manager import ensure_external_folders
        mgr = ensure_external_folders()
        path = mgr.get_path("spatial_maps", "mepi_spatial_map.png")
    """
    mgr = ExternalFolderManager(base_dir)
    mgr.create_all_folders()
    return mgr


def get_external_path(subfolder: str, filename: str, base_dir: Optional[str] = None) -> str:
    """
    Quick helper: return a file path inside the external folder structure.

    The subfolder is created automatically if it does not exist.
    """
    mgr = ExternalFolderManager(base_dir)
    folder = mgr.create_folder(subfolder)
    return str(folder / filename)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    custom_base = sys.argv[1] if len(sys.argv) > 1 else None
    print("Creating external map output folder structure...")
    mgr = ensure_external_folders(custom_base)
    mgr.print_status()
    mgr.generate_structure_report(str(mgr.base_dir / "folder_structure.txt"))
    print(f"\nDone! External folder: {mgr.base_dir}")
    print("Run 'python generate_all_maps.py' to populate the folders.")
