"""
temporal_maps_external.py - Generate temporal analysis maps to external folder

Creates time-series and change maps showing how energy poverty evolved over
multiple years.  All outputs are saved to the external ``temporal_maps/`` folder.

Maps produced
-------------
  temporal_2020_comparison.png   Year 2020 MEPI map
  temporal_2021_comparison.png   Year 2021 MEPI map
  poverty_change_map.png         Change in MEPI between first and last year
  improvement_areas.png          Upazilas with improving poverty scores
  deterioration_areas.png        Upazilas with worsening poverty scores
  temporal_animation.gif         Animated GIF cycling through all years

Usage
-----
    python temporal_maps_external.py
    python temporal_maps_external.py --data path/to/mepi_results.csv
    python temporal_maps_external.py --output-dir /custom/path/

    # With multi-year data (dict of year → CSV paths):
    from temporal_maps_external import TemporalMapsExternal
    mapper = TemporalMapsExternal({2020: df_2020, 2021: df_2021})
    mapper.create_all_maps()
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from external_folder_manager import ensure_external_folders
from map_config_external import DPI, EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)

try:
    from PIL import Image as PilImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

BANGLADESH_BOUNDS = {"lon_min": 88.0, "lon_max": 92.7, "lat_min": 20.5, "lat_max": 26.7}


# ---------------------------------------------------------------------------
# Temporal map generator
# ---------------------------------------------------------------------------

class TemporalMapsExternal:
    """
    Generate temporal comparison maps saved to external ``temporal_maps/`` folder.

    Parameters
    ----------
    yearly_data : dict
        Mapping of year (int or str) to MEPI DataFrame.
        Each DataFrame must have: upazila_name, mepi_score, lat, lon.
    base_dir : str, optional
        External output root (defaults to EXTERNAL_OUTPUT_BASE).
    """

    def __init__(
        self,
        yearly_data: Dict[Union[int, str], pd.DataFrame],
        base_dir: Optional[str] = None,
    ) -> None:
        self.yearly_data = {
            year: _attach_coords(df)
            for year, df in yearly_data.items()
        }
        self._mgr = ensure_external_folders(base_dir)

    def _out(self, filename: str) -> str:
        return self._mgr.get_path("temporal_maps", filename)

    # ------------------------------------------------------------------
    # Per-year comparison map
    # ------------------------------------------------------------------

    def _create_year_map(self, year: Union[int, str], df: pd.DataFrame) -> Optional[str]:
        filename = f"temporal_{year}_comparison.png"
        valid = df.dropna(subset=["lat", "lon"])
        if valid.empty:
            warnings.warn(f"No valid coordinates for year {year}; skipping.", stacklevel=2)
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 12))
            sc = ax.scatter(
                valid["lon"], valid["lat"],
                c=valid["mepi_score"], cmap="YlOrRd",
                vmin=0, vmax=1, s=55,
                edgecolors="grey", linewidth=0.3, alpha=0.9,
            )
            plt.colorbar(sc, ax=ax, label="MEPI Score", fraction=0.03, pad=0.04)
            mean_s = valid["mepi_score"].mean()
            ax.set_title(
                f"Energy Poverty Index – {year}\n"
                f"Bangladesh (mean MEPI: {mean_s:.3f})",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
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
    # Change maps (improvement / deterioration)
    # ------------------------------------------------------------------

    def _compute_change(self) -> Optional[pd.DataFrame]:
        """Compute per-upazila MEPI change between first and last year."""
        years = sorted(self.yearly_data.keys())
        if len(years) < 2:
            return None
        first_df = self.yearly_data[years[0]][["upazila_name", "mepi_score", "lat", "lon"]].copy()
        last_df  = self.yearly_data[years[-1]][["upazila_name", "mepi_score"]].copy()
        first_df = first_df.rename(columns={"mepi_score": "score_first"})
        last_df  = last_df.rename(columns={"mepi_score": "score_last"})
        merged = first_df.merge(last_df, on="upazila_name", how="inner")
        merged["change"] = merged["score_last"] - merged["score_first"]
        return merged

    def _create_change_map(self) -> Optional[str]:
        change_df = self._compute_change()
        if change_df is None:
            return None
        valid = change_df.dropna(subset=["lat", "lon"])
        if valid.empty:
            return None

        filename = "poverty_change_map.png"
        years = sorted(self.yearly_data.keys())
        try:
            fig, ax = plt.subplots(figsize=(10, 12))
            absmax = max(abs(valid["change"].max()), abs(valid["change"].min()), 0.01)
            sc = ax.scatter(
                valid["lon"], valid["lat"],
                c=valid["change"], cmap="RdYlGn_r",
                vmin=-absmax, vmax=absmax, s=55,
                edgecolors="grey", linewidth=0.3, alpha=0.9,
            )
            plt.colorbar(sc, ax=ax, label="MEPI Change (positive = worsening)", fraction=0.03)
            ax.set_title(
                f"Energy Poverty Change {years[0]}–{years[-1]}\n"
                "Red = worsening, Green = improving",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
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

    def _create_improvement_map(self) -> Optional[str]:
        change_df = self._compute_change()
        if change_df is None:
            return None
        improving = change_df[change_df["change"] < 0].dropna(subset=["lat", "lon"])
        filename = "improvement_areas.png"
        try:
            fig, ax = plt.subplots(figsize=(10, 12))
            all_valid = change_df.dropna(subset=["lat", "lon"])
            ax.scatter(
                all_valid["lon"], all_valid["lat"],
                color="lightgrey", s=30, edgecolors="none", alpha=0.5,
            )
            if not improving.empty:
                sc = ax.scatter(
                    improving["lon"], improving["lat"],
                    c=abs(improving["change"]), cmap="Greens",
                    vmin=0, s=70, edgecolors="#1a7a1a", linewidth=0.5, alpha=0.9,
                )
                plt.colorbar(sc, ax=ax, label="Improvement magnitude", fraction=0.03)
            ax.set_title(
                f"Improving Areas ({len(improving)} upazilas)\nEnergy poverty decreased",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
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

    def _create_deterioration_map(self) -> Optional[str]:
        change_df = self._compute_change()
        if change_df is None:
            return None
        worsening = change_df[change_df["change"] > 0].dropna(subset=["lat", "lon"])
        filename = "deterioration_areas.png"
        try:
            fig, ax = plt.subplots(figsize=(10, 12))
            all_valid = change_df.dropna(subset=["lat", "lon"])
            ax.scatter(
                all_valid["lon"], all_valid["lat"],
                color="lightgrey", s=30, edgecolors="none", alpha=0.5,
            )
            if not worsening.empty:
                sc = ax.scatter(
                    worsening["lon"], worsening["lat"],
                    c=worsening["change"], cmap="Reds",
                    vmin=0, s=70, edgecolors="#8b0000", linewidth=0.5, alpha=0.9,
                )
                plt.colorbar(sc, ax=ax, label="Deterioration magnitude", fraction=0.03)
            ax.set_title(
                f"Deteriorating Areas ({len(worsening)} upazilas)\nEnergy poverty increased",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
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
    # Animated GIF
    # ------------------------------------------------------------------

    def _create_animation(self) -> Optional[str]:
        if not _HAS_PIL:
            warnings.warn("Pillow not installed – skipping temporal animation GIF.", stacklevel=2)
            return None

        years = sorted(self.yearly_data.keys())
        frames = []
        filename = "temporal_animation.gif"

        try:
            import io
            for year in years:
                df = self.yearly_data[year].dropna(subset=["lat", "lon"])
                if df.empty:
                    continue
                fig, ax = plt.subplots(figsize=(8, 10))
                sc = ax.scatter(
                    df["lon"], df["lat"],
                    c=df["mepi_score"], cmap="YlOrRd",
                    vmin=0, vmax=1, s=50,
                    edgecolors="grey", linewidth=0.2, alpha=0.9,
                )
                plt.colorbar(sc, ax=ax, label="MEPI Score", fraction=0.03)
                ax.set_title(f"Energy Poverty Index – {year}", fontsize=13, fontweight="bold")
                ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
                ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
                ax.set_xlabel("Longitude")
                ax.set_ylabel("Latitude")
                ax.grid(True, alpha=0.2)
                plt.tight_layout()

                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
                plt.close(fig)
                buf.seek(0)
                frames.append(PilImage.open(buf).copy())

            if not frames:
                return None

            path = self._out(filename)
            frames[0].save(
                path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=1500,
                loop=0,
            )
            print(f"  Saved: {path}")
            return path

        except Exception as exc:
            warnings.warn(f"temporal_animation.gif failed: {exc}", stacklevel=2)
            plt.close("all")
            return None

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_maps(self) -> List[str]:
        """Create all temporal maps and return list of saved paths."""
        saved: List[str] = []

        for year, df in sorted(self.yearly_data.items()):
            print(f"  Creating temporal_{year}_comparison.png ...")
            p = self._create_year_map(year, df)
            if p:
                saved.append(p)

        print("  Creating poverty_change_map.png ...")
        p = self._create_change_map()
        if p:
            saved.append(p)

        print("  Creating improvement_areas.png ...")
        p = self._create_improvement_map()
        if p:
            saved.append(p)

        print("  Creating deterioration_areas.png ...")
        p = self._create_deterioration_map()
        if p:
            saved.append(p)

        print("  Creating temporal_animation.gif ...")
        p = self._create_animation()
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
        description="Generate temporal MEPI maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("TEMPORAL MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)

    # Build synthetic yearly data for demo: add slight variation per year
    rng = np.random.default_rng(42)
    yearly_data: Dict[int, pd.DataFrame] = {}
    for year in [2020, 2021]:
        df_year = results.copy()
        noise = rng.normal(0, 0.03, len(df_year))
        df_year["mepi_score"] = (df_year["mepi_score"] + noise).clip(0, 1)
        yearly_data[year] = df_year

    mapper = TemporalMapsExternal(yearly_data, base_dir=args.output_dir)
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} temporal map(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('temporal_maps')}")


if __name__ == "__main__":
    main()
