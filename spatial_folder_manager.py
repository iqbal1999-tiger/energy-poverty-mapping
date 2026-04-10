"""
spatial_folder_manager.py - Create and manage the dedicated spatial maps PNG folder

Handles the lifecycle of ~/spatial_maps_png/: creation, validation,
optional clearing of stale files, status reporting, and README template.

Folder managed
--------------
~/spatial_maps_png/          (completely separate from other map outputs)
├── mepi_spatial_map.png
├── availability_map.png
├── reliability_map.png
├── adequacy_map.png
├── quality_map.png
├── affordability_map.png
├── README.txt
├── index.html
└── map_legend.txt

Usage
-----
    from spatial_folder_manager import SpatialFolderManager
    mgr = SpatialFolderManager()
    mgr.create_folder()
    mgr.print_status()
    path = mgr.get_path("mepi_spatial_map.png")
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from spatial_maps_config import (
    SPATIAL_OUTPUT_FOLDER,
    DIMENSION_MAP_CONFIGS,
    MEPI_MAP_FILENAME,
    get_output_folder,
    validate_write_permissions,
)

# ---------------------------------------------------------------------------
# Expected files (for reporting / README)
# ---------------------------------------------------------------------------

EXPECTED_PNG_FILES: List[str] = [MEPI_MAP_FILENAME] + [
    cfg["filename"] for cfg in DIMENSION_MAP_CONFIGS
]

EXPECTED_DOC_FILES: List[str] = ["README.txt", "index.html", "map_legend.txt"]

ALL_EXPECTED_FILES: List[str] = EXPECTED_PNG_FILES + EXPECTED_DOC_FILES


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------


class SpatialFolderManager:
    """
    Create and manage the dedicated ~/spatial_maps_png/ output folder.

    Parameters
    ----------
    output_dir : str, optional
        Override the default folder path from ``spatial_maps_config``.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        if output_dir is None:
            self.folder = get_output_folder()
        else:
            self.folder = Path(output_dir).expanduser().resolve()

    # ------------------------------------------------------------------
    # Folder creation
    # ------------------------------------------------------------------

    def create_folder(self) -> Path:
        """
        Create the output folder (and any parents) if it does not yet exist.

        Returns
        -------
        Path
            Absolute path of the created/existing folder.
        """
        self.folder.mkdir(parents=True, exist_ok=True)
        print(f"✅ Spatial maps folder: {self.folder}")
        return self.folder

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def exists(self) -> bool:
        """Return True if the folder exists."""
        return self.folder.is_dir()

    def is_writable(self) -> bool:
        """Return True if the folder exists and is writable."""
        if not self.exists():
            return False
        return os.access(str(self.folder), os.W_OK)

    def verify(self) -> bool:
        """
        Ensure the folder exists and is writable.

        Creates the folder if absent.

        Returns
        -------
        bool
            True on success.
        """
        self.create_folder()
        ok = self.is_writable()
        if not ok:
            print(f"❌ Folder is not writable: {self.folder}")
        return ok

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_path(self, filename: str) -> str:
        """
        Return the full string path for a file inside the spatial maps folder.

        Parameters
        ----------
        filename : str
            File basename, e.g. ``"mepi_spatial_map.png"``.
        """
        return str(self.folder / filename)

    # ------------------------------------------------------------------
    # File listing
    # ------------------------------------------------------------------

    def list_files(self) -> List[str]:
        """Return a sorted list of file basenames currently in the folder."""
        if not self.exists():
            return []
        return sorted(f.name for f in self.folder.iterdir() if f.is_file())

    def list_png_files(self) -> List[str]:
        """Return only PNG files currently in the folder."""
        return [f for f in self.list_files() if f.lower().endswith(".png")]

    # ------------------------------------------------------------------
    # Clearing old maps
    # ------------------------------------------------------------------

    def clear_png_files(self) -> int:
        """
        Remove all PNG files from the folder.

        Returns
        -------
        int
            Number of files removed.
        """
        removed = 0
        if not self.exists():
            return 0
        for f in self.folder.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                f.unlink()
                print(f"  Removed: {f.name}")
                removed += 1
        print(f"  {removed} PNG file(s) cleared.")
        return removed

    def clear_all_files(self) -> int:
        """
        Remove all files from the folder (but keep the folder itself).

        Returns
        -------
        int
            Number of files removed.
        """
        removed = 0
        if not self.exists():
            return 0
        for f in self.folder.iterdir():
            if f.is_file():
                f.unlink()
                removed += 1
        print(f"  {removed} file(s) cleared from {self.folder}")
        return removed

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_structure_report(self, output_path: Optional[str] = None) -> str:
        """
        Build a plain-text report of the folder and its current contents.

        Parameters
        ----------
        output_path : str, optional
            If given, the report is also written to this file.

        Returns
        -------
        str
            The report text.
        """
        existing = set(self.list_files())
        lines = [
            "SPATIAL MAPS PNG FOLDER – STRUCTURE REPORT",
            "=" * 50,
            f"Folder  : {self.folder}",
            f"Exists  : {'yes' if self.exists() else 'no'}",
            f"Writable: {'yes' if self.is_writable() else 'no'}",
            f"Created : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Expected PNG maps:",
        ]

        for name in EXPECTED_PNG_FILES:
            status = "✅ present" if name in existing else "⬜ missing"
            lines.append(f"  {status}  {name}")

        lines.append("")
        lines.append("Documentation files:")

        for name in EXPECTED_DOC_FILES:
            status = "✅ present" if name in existing else "⬜ missing"
            lines.append(f"  {status}  {name}")

        extra = sorted(existing - set(ALL_EXPECTED_FILES))
        if extra:
            lines.append("")
            lines.append("Other files:")
            for name in extra:
                lines.append(f"  ℹ️  {name}")

        report = "\n".join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report, encoding="utf-8")
            print(f"Report saved: {output_path}")

        return report

    def print_status(self) -> None:
        """Print a concise status summary of the spatial maps folder."""
        existing = self.list_files()
        png_count = sum(1 for f in existing if f.lower().endswith(".png"))

        print("\n" + "=" * 60)
        print("SPATIAL MAPS PNG FOLDER STATUS")
        print("=" * 60)
        print(f"  Folder   : {self.folder}")
        print(f"  Exists   : {'✅' if self.exists() else '❌'}")
        print(f"  Writable : {'✅' if self.is_writable() else '❌'}")
        print(f"  PNG files: {png_count} / {len(EXPECTED_PNG_FILES)} expected")
        if existing:
            for name in existing:
                print(f"    ├── {name}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # README template
    # ------------------------------------------------------------------

    def create_readme_template(self) -> str:
        """
        Write an empty README template to the spatial maps folder.

        Returns
        -------
        str
            Path to the created README.txt.
        """
        self.create_folder()
        readme_path = self.folder / "README.txt"
        content = (
            "SPATIAL MAPS PNG – README\n"
            "=========================\n"
            "\n"
            "This folder contains spatial choropleth maps for the\n"
            "Multidimensional Energy Poverty Index (MEPI) in Bangladesh.\n"
            "\n"
            "Files\n"
            "-----\n"
        )
        for filename in EXPECTED_PNG_FILES:
            content += f"  {filename}\n"
        content += (
            "\n"
            "Generated by spatial_maps_generator.py\n"
            "Run: python generate_spatial_maps_only.py\n"
        )
        readme_path.write_text(content, encoding="utf-8")
        print(f"  README template: {readme_path}")
        return str(readme_path)


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------


def ensure_spatial_folder(output_dir: Optional[str] = None) -> SpatialFolderManager:
    """
    Create the spatial maps folder and return the manager.

    Example::

        from spatial_folder_manager import ensure_spatial_folder
        mgr = ensure_spatial_folder()
        path = mgr.get_path("mepi_spatial_map.png")
    """
    mgr = SpatialFolderManager(output_dir)
    mgr.create_folder()
    return mgr


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    custom_dir = sys.argv[1] if len(sys.argv) > 1 else None
    print("Setting up spatial maps PNG folder ...")
    mgr = ensure_spatial_folder(custom_dir)
    mgr.print_status()
    report = mgr.generate_structure_report(mgr.get_path("folder_report.txt"))
    print("\n" + report)
    mgr.create_readme_template()
    print(f"\nDone! Spatial maps folder: {mgr.folder}")
    print("Run 'python generate_spatial_maps_only.py' to generate all 6 maps.")
