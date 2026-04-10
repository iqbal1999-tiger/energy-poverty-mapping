"""
regional_maps_external.py - Generate regional analysis maps to external folder

Creates maps broken down by Bangladesh geographic zones (coastal, char islands,
haor wetlands, hill tracts, Sundarbans, urban/rural) and saves them to the
external ``regional_maps/`` subfolder.

Maps produced
-------------
  coastal_analysis_map.png       Coastal zone energy poverty
  char_islands_map.png           Char islands zone
  haor_wetlands_map.png          Haor wetlands zone
  hill_tract_map.png             Chittagong Hill Tracts
  sundarbans_map.png             Sundarbans zone
  urban_rural_comparison.png     Urban vs rural comparison

Usage
-----
    python regional_maps_external.py
    python regional_maps_external.py --data path/to/mepi_results.csv
    python regional_maps_external.py --output-dir /custom/path/
"""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from external_folder_manager import ExternalFolderManager, ensure_external_folders
from map_config_external import DPI, EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Zone definitions (district lists for each geographic zone)
# ---------------------------------------------------------------------------

ZONE_DISTRICTS: Dict[str, Dict[str, object]] = {
    "coastal": {
        "label": "Coastal Zone",
        "color": "#2196F3",
        "districts": [
            "cox's bazar", "chittagong", "feni", "noakhali",
            "lakshmipur", "chandpur", "barisal", "patuakhali",
            "bhola", "barguna", "pirojpur", "jhalokati",
        ],
    },
    "char_islands": {
        "label": "Char Islands",
        "color": "#FF9800",
        "districts": [
            "bhola", "noakhali", "lakshmipur", "chandpur",
            "shariatpur", "madaripur",
        ],
    },
    "haor_wetlands": {
        "label": "Haor Wetlands",
        "color": "#4CAF50",
        "districts": [
            "sunamganj", "sylhet", "moulvibazar", "habiganj",
            "kishoreganj", "netrokona", "mymensingh",
        ],
    },
    "hill_tract": {
        "label": "Hill Tracts",
        "color": "#795548",
        "districts": [
            "rangamati", "khagrachhari", "bandarban",
        ],
    },
    "sundarbans": {
        "label": "Sundarbans",
        "color": "#009688",
        "districts": [
            "satkhira", "khulna", "bagerhat",
        ],
    },
}

BANGLADESH_BOUNDS = {"lon_min": 88.0, "lon_max": 92.7, "lat_min": 20.5, "lat_max": 26.7}
POVERTY_COLORS = {"Non-Poor": "#2ecc71", "Moderately Poor": "#f39c12", "Severely Poor": "#e74c3c"}


# ---------------------------------------------------------------------------
# Regional map generator
# ---------------------------------------------------------------------------

class RegionalMapsExternal:
    """
    Generate regional analysis maps saved to the external ``regional_maps/`` folder.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with columns: upazila_name, mepi_score, lat, lon.
    base_dir : str, optional
        External output root (defaults to EXTERNAL_OUTPUT_BASE).
    """

    def __init__(self, mepi_df: pd.DataFrame, base_dir: Optional[str] = None) -> None:
        self.df = _attach_coords(mepi_df)
        self._mgr = ensure_external_folders(base_dir)

    def _out(self, filename: str) -> str:
        return self._mgr.get_path("regional_maps", filename)

    @staticmethod
    def _normalise_str(series: pd.Series) -> pd.Series:
        """Return a normalised (non-null, string) version of a column."""
        return series.fillna("").astype(str)

    # ------------------------------------------------------------------
    # Zone-specific map
    # ------------------------------------------------------------------

    def _create_zone_map(
        self,
        zone_key: str,
        zone_info: Dict[str, object],
        filename: str,
    ) -> Optional[str]:
        districts = [d.lower() for d in zone_info.get("districts", [])]
        label = zone_info.get("label", zone_key.replace("_", " ").title())
        color = zone_info.get("color", "#3498db")

        if "district" in self.df.columns:
            mask = self._normalise_str(self.df["district"]).str.lower().isin(districts)
        else:
            mask = pd.Series([False] * len(self.df))

        zone_df = self.df[mask]
        all_df = self.df.dropna(subset=["lat", "lon"])
        zone_valid = zone_df.dropna(subset=["lat", "lon"])

        try:
            fig, ax = plt.subplots(figsize=(10, 12))

            if not all_df.empty:
                ax.scatter(
                    all_df["lon"], all_df["lat"],
                    c=all_df["mepi_score"], cmap="YlOrRd",
                    vmin=0, vmax=1, s=40,
                    edgecolors="lightgrey", linewidth=0.2, alpha=0.5,
                    label="Other upazilas",
                )

            if not zone_valid.empty:
                sc = ax.scatter(
                    zone_valid["lon"], zone_valid["lat"],
                    c=zone_valid["mepi_score"], cmap="YlOrRd",
                    vmin=0, vmax=1, s=90,
                    edgecolors=color, linewidth=1.0, alpha=0.9,
                    label=label,
                )
                plt.colorbar(sc, ax=ax, label="MEPI Score", fraction=0.03, pad=0.04)

                mean_score = zone_valid["mepi_score"].mean()
                n = len(zone_valid)
                ax.set_title(
                    f"{label} – Energy Poverty Analysis\n"
                    f"Bangladesh ({n} upazilas, mean MEPI: {mean_score:.3f})",
                    fontsize=13, fontweight="bold",
                )
            else:
                ax.set_title(
                    f"{label} – Energy Poverty Analysis\n(No district data available)",
                    fontsize=13, fontweight="bold",
                )

            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(loc="upper left", fontsize=8)
            ax.grid(True, alpha=0.2)
            plt.tight_layout()

            path = self._out(filename)
            fig.savefig(path, dpi=DPI, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved: {path}")
            return path

        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)
            plt.close("all")
            return None

    # ------------------------------------------------------------------
    # Urban vs rural comparison
    # ------------------------------------------------------------------

    def _create_urban_rural_comparison(self) -> Optional[str]:
        filename = "urban_rural_comparison.png"
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 8))

            if "urban_rural" in self.df.columns:
                for ax_i, category in enumerate(["Urban", "Rural"]):
                    subset = self.df[self._normalise_str(self.df["urban_rural"]).str.title() == category]
                    valid = subset.dropna(subset=["lat", "lon"])
                    if not valid.empty:
                        sc = axes[ax_i].scatter(
                            valid["lon"], valid["lat"],
                            c=valid["mepi_score"], cmap="YlOrRd",
                            vmin=0, vmax=1, s=60,
                            edgecolors="grey", linewidth=0.3,
                        )
                        plt.colorbar(sc, ax=axes[ax_i], label="MEPI Score", fraction=0.03)
                        mean_s = valid["mepi_score"].mean()
                        axes[ax_i].set_title(
                            f"{category} Upazilas\nMean MEPI: {mean_s:.3f}",
                            fontsize=12, fontweight="bold",
                        )
                    else:
                        axes[ax_i].set_title(f"{category} (no data)", fontsize=12)
                    axes[ax_i].set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
                    axes[ax_i].set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
                    axes[ax_i].set_xlabel("Longitude")
                    axes[ax_i].set_ylabel("Latitude")
            else:
                # Show all data side-by-side with threshold split
                all_df = self.df.dropna(subset=["lat", "lon"])
                for ax_i, (threshold, label) in enumerate(
                    [(0.33, "Low Poverty (< 0.33)"), (0.66, "High Poverty (≥ 0.66)")]
                ):
                    if ax_i == 0:
                        subset = all_df[all_df["mepi_score"] < threshold]
                    else:
                        subset = all_df[all_df["mepi_score"] >= threshold]
                    sc = axes[ax_i].scatter(
                        subset["lon"], subset["lat"],
                        c=subset["mepi_score"], cmap="YlOrRd",
                        vmin=0, vmax=1, s=60,
                        edgecolors="grey", linewidth=0.3,
                    )
                    plt.colorbar(sc, ax=axes[ax_i], label="MEPI Score", fraction=0.03)
                    axes[ax_i].set_title(label, fontsize=12, fontweight="bold")
                    axes[ax_i].set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
                    axes[ax_i].set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
                    axes[ax_i].set_xlabel("Longitude")
                    axes[ax_i].set_ylabel("Latitude")

            fig.suptitle(
                "Urban–Rural Energy Poverty Comparison\nBangladesh – Upazila Level",
                fontsize=14, fontweight="bold",
            )
            plt.tight_layout()
            path = self._out(filename)
            fig.savefig(path, dpi=DPI, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved: {path}")
            return path

        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)
            plt.close("all")
            return None

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_maps(self) -> List[str]:
        """Create all regional maps and return list of saved paths."""
        saved: List[str] = []

        zone_file_map = {
            "coastal":      "coastal_analysis_map.png",
            "char_islands": "char_islands_map.png",
            "haor_wetlands":"haor_wetlands_map.png",
            "hill_tract":   "hill_tract_map.png",
            "sundarbans":   "sundarbans_map.png",
        }

        for zone_key, filename in zone_file_map.items():
            print(f"  Creating {filename} ...")
            zone_info = ZONE_DISTRICTS[zone_key]
            p = self._create_zone_map(zone_key, zone_info, filename)
            if p:
                saved.append(p)

        print("  Creating urban_rural_comparison.png ...")
        p = self._create_urban_rural_comparison()
        if p:
            saved.append(p)

        return saved


# ---------------------------------------------------------------------------
# Coordinate helper
# ---------------------------------------------------------------------------

def _attach_coords(df: pd.DataFrame) -> pd.DataFrame:
    if "lat" in df.columns and "lon" in df.columns:
        return df
    try:
        from bangladesh_coordinates import get_database
        db = get_database()
        lats, lons = [], []
        for name in (df["upazila_name"] if "upazila_name" in df.columns else []):
            rec = db.get_by_name(str(name))
            lats.append(rec["lat"] if rec else np.nan)
            lons.append(rec["lon"] if rec else np.nan)
        df = df.copy()
        df["lat"] = lats
        df["lon"] = lons
    except Exception:
        pass
    return df


# ---------------------------------------------------------------------------
# Data loader & CLI
# ---------------------------------------------------------------------------

def _load_data(data_path: str) -> pd.DataFrame:
    if data_path and Path(data_path).exists():
        return pd.read_csv(data_path)
    from data_utils import load_data, validate_data, handle_missing_values
    from mepi_calculator import MEPICalculator
    df = load_data("sample_data.csv")
    df = validate_data(df)
    df = handle_missing_values(df)
    return MEPICalculator().calculate(df)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate regional MEPI maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("REGIONAL MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)
    mapper = RegionalMapsExternal(results, base_dir=args.output_dir)
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} regional map(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('regional_maps')}")


if __name__ == "__main__":
    main()
