"""
hotspot_maps_external.py - Generate hotspot analysis maps to external folder

Creates energy poverty hotspot and vulnerability cluster maps and saves them
to the external ``hotspot_maps/`` subfolder.

Maps produced
-------------
  hotspot_clusters.png      Severe poverty hotspot clusters
  vulnerability_map.png     Multi-factor vulnerability score
  hotspot_intensity.png     Hotspot density / kernel density estimate
  cluster_analysis.png      K-means cluster assignments

Usage
-----
    python hotspot_maps_external.py
    python hotspot_maps_external.py --data path/to/mepi_results.csv
    python hotspot_maps_external.py --output-dir /custom/path/
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from external_folder_manager import ensure_external_folders
from map_config_external import DPI, EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)

BANGLADESH_BOUNDS = {"lon_min": 88.0, "lon_max": 92.7, "lat_min": 20.5, "lat_max": 26.7}


# ---------------------------------------------------------------------------
# Hotspot map generator
# ---------------------------------------------------------------------------

class HotspotMapsExternal:
    """
    Generate hotspot analysis maps saved to external ``hotspot_maps/`` folder.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with columns: upazila_name, mepi_score, lat, lon.
    base_dir : str, optional
        External output root (defaults to EXTERNAL_OUTPUT_BASE).
    hotspot_threshold : float
        MEPI score above which an upazila is considered a hotspot (default: 0.66).
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        base_dir: Optional[str] = None,
        hotspot_threshold: float = 0.66,
    ) -> None:
        self.df = _attach_coords(mepi_df)
        self._mgr = ensure_external_folders(base_dir)
        self.threshold = hotspot_threshold

    def _out(self, filename: str) -> str:
        return self._mgr.get_path("hotspot_maps", filename)

    # ------------------------------------------------------------------
    # Hotspot clusters
    # ------------------------------------------------------------------

    def create_hotspot_clusters(self) -> Optional[str]:
        """Create and save the hotspot clusters map."""
        filename = "hotspot_clusters.png"
        valid = self.df.dropna(subset=["lat", "lon"])
        if valid.empty:
            return None

        hotspots = valid[valid["mepi_score"] >= self.threshold]
        non_hotspots = valid[valid["mepi_score"] < self.threshold]

        try:
            fig, ax = plt.subplots(figsize=(10, 12))

            if not non_hotspots.empty:
                ax.scatter(
                    non_hotspots["lon"], non_hotspots["lat"],
                    color="#95a5a6", s=30, edgecolors="none",
                    alpha=0.5, label="Non-hotspot",
                )

            if not hotspots.empty:
                sc = ax.scatter(
                    hotspots["lon"], hotspots["lat"],
                    c=hotspots["mepi_score"], cmap="hot_r",
                    vmin=self.threshold, vmax=1.0, s=80,
                    edgecolors="#8b0000", linewidth=0.6,
                    alpha=0.9, label=f"Hotspot (MEPI ≥ {self.threshold})",
                )
                plt.colorbar(sc, ax=ax, label="MEPI Score", fraction=0.03, pad=0.04)

            ax.set_title(
                f"Energy Poverty Hotspot Clusters\n"
                f"Bangladesh ({len(hotspots)} hotspot upazilas, threshold: {self.threshold})",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(loc="upper left", fontsize=9)
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
    # Vulnerability map
    # ------------------------------------------------------------------

    def create_vulnerability_map(self) -> Optional[str]:
        """Create a composite vulnerability score map."""
        filename = "vulnerability_map.png"
        dim_cols = [c for c in self.df.columns if c.endswith("_score") and c != "mepi_score"]
        valid = self.df.dropna(subset=["lat", "lon"])
        if valid.empty:
            return None

        try:
            df = valid.copy()
            if dim_cols:
                df["vulnerability"] = df[dim_cols].max(axis=1)
            else:
                df["vulnerability"] = df["mepi_score"]

            fig, ax = plt.subplots(figsize=(10, 12))
            sc = ax.scatter(
                df["lon"], df["lat"],
                c=df["vulnerability"], cmap="RdYlGn_r",
                vmin=0, vmax=1, s=55,
                edgecolors="grey", linewidth=0.3, alpha=0.9,
            )
            plt.colorbar(sc, ax=ax, label="Vulnerability Score", fraction=0.03, pad=0.04)
            ax.set_title(
                "Energy Vulnerability Map\nBangladesh – Maximum Dimension Deprivation",
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
    # Hotspot intensity (kernel density estimate)
    # ------------------------------------------------------------------

    def create_hotspot_intensity(self) -> Optional[str]:
        """Create a kernel density intensity map for hotspot upazilas."""
        filename = "hotspot_intensity.png"
        valid = self.df.dropna(subset=["lat", "lon"])
        hotspots = valid[valid["mepi_score"] >= self.threshold]

        if hotspots.empty:
            warnings.warn("No hotspots found; hotspot_intensity.png skipped.", stacklevel=2)
            return None

        try:
            from scipy.stats import gaussian_kde

            x = hotspots["lon"].values
            y = hotspots["lat"].values
            xy = np.vstack([x, y])
            kde = gaussian_kde(xy)

            lon_range = np.linspace(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"], 150)
            lat_range = np.linspace(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"], 180)
            lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
            z = kde(np.vstack([lon_grid.ravel(), lat_grid.ravel()])).reshape(lon_grid.shape)

            fig, ax = plt.subplots(figsize=(10, 12))
            im = ax.contourf(lon_grid, lat_grid, z, levels=20, cmap="hot_r", alpha=0.75)
            plt.colorbar(im, ax=ax, label="Hotspot Density", fraction=0.03, pad=0.04)
            ax.scatter(
                x, y, color="yellow", s=20, edgecolors="orange",
                linewidth=0.4, alpha=0.7, label=f"Hotspot upazilas (n={len(hotspots)})",
            )
            ax.set_title(
                "Energy Poverty Hotspot Intensity\nKernel Density Estimation",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlim(BANGLADESH_BOUNDS["lon_min"], BANGLADESH_BOUNDS["lon_max"])
            ax.set_ylim(BANGLADESH_BOUNDS["lat_min"], BANGLADESH_BOUNDS["lat_max"])
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(loc="upper left", fontsize=9)
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
    # Cluster analysis (k-means)
    # ------------------------------------------------------------------

    def create_cluster_analysis(self) -> Optional[str]:
        """Create a K-means cluster map for energy poverty patterns."""
        filename = "cluster_analysis.png"
        valid = self.df.dropna(subset=["lat", "lon", "mepi_score"])
        if valid.empty:
            return None

        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            feature_cols = ["mepi_score", "lat", "lon"]
            dim_cols = [c for c in valid.columns if c.endswith("_score") and c != "mepi_score"]
            feature_cols = list(set(feature_cols + dim_cols))
            feature_cols = [c for c in feature_cols if c in valid.columns]

            X = valid[feature_cols].fillna(0).values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            n_clusters = min(4, len(valid))
            km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)

            colors = plt.cm.Set1(np.linspace(0, 1, n_clusters))

            fig, ax = plt.subplots(figsize=(10, 12))
            for cluster_id in range(n_clusters):
                mask = labels == cluster_id
                cluster_df = valid[mask]
                mean_mepi = cluster_df["mepi_score"].mean()
                ax.scatter(
                    cluster_df["lon"], cluster_df["lat"],
                    color=colors[cluster_id], s=60,
                    edgecolors="grey", linewidth=0.3, alpha=0.85,
                    label=f"Cluster {cluster_id + 1} (mean MEPI: {mean_mepi:.3f})",
                )

            ax.set_title(
                f"K-Means Cluster Analysis ({n_clusters} clusters)\nEnergy Poverty Patterns",
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

        except ImportError:
            warnings.warn("scikit-learn not installed; cluster_analysis.png skipped.", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)
            plt.close("all")

        return None

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_maps(self) -> List[str]:
        """Create all hotspot maps and return list of saved paths."""
        saved: List[str] = []

        print("  Creating hotspot_clusters.png ...")
        p = self.create_hotspot_clusters()
        if p:
            saved.append(p)

        print("  Creating vulnerability_map.png ...")
        p = self.create_vulnerability_map()
        if p:
            saved.append(p)

        print("  Creating hotspot_intensity.png ...")
        p = self.create_hotspot_intensity()
        if p:
            saved.append(p)

        print("  Creating cluster_analysis.png ...")
        p = self.create_cluster_analysis()
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
        for name in df.get("upazila_name", []):
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
        description="Generate hotspot MEPI maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.66,
        help="MEPI score threshold for hotspot classification (default: 0.66).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HOTSPOT MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)
    mapper = HotspotMapsExternal(
        results,
        base_dir=args.output_dir,
        hotspot_threshold=args.threshold,
    )
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} hotspot map(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('hotspot_maps')}")


if __name__ == "__main__":
    main()
