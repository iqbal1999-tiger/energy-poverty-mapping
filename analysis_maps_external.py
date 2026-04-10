"""
analysis_maps_external.py - Generate statistical analysis maps to external folder

Creates ranking charts, heatmaps, correlation matrices, and distribution plots
and saves them to the external ``analysis_maps/`` subfolder.

Maps produced
-------------
  top10_most_poor.png                    Bar chart: 10 most energy-poor upazilas
  top10_least_poor.png                   Bar chart: 10 least energy-poor upazilas
  dimension_heatmap.png                  Heatmap of all dimension scores
  dimension_correlation.png             Correlation matrix of dimensions
  regional_comparison.png               Mean MEPI by division/region
  poverty_classification_distribution.png  Poverty category counts

Usage
-----
    python analysis_maps_external.py
    python analysis_maps_external.py --data path/to/mepi_results.csv
    python analysis_maps_external.py --output-dir /custom/path/
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from external_folder_manager import ensure_external_folders
from map_config_external import DPI, EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Analysis map generator
# ---------------------------------------------------------------------------

class AnalysisMapsExternal:
    """
    Generate statistical analysis maps saved to external ``analysis_maps/`` folder.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with columns: upazila_name, mepi_score, [dimension_score cols].
    base_dir : str, optional
        External output root (defaults to EXTERNAL_OUTPUT_BASE).
    """

    def __init__(self, mepi_df: pd.DataFrame, base_dir: Optional[str] = None) -> None:
        self.df = mepi_df
        self._mgr = ensure_external_folders(base_dir)

    def _out(self, filename: str) -> str:
        return self._mgr.get_path("analysis_maps", filename)

    @property
    def _dim_cols(self) -> List[str]:
        return [c for c in self.df.columns if c.endswith("_score") and c != "mepi_score"]

    # ------------------------------------------------------------------
    # Top-10 most energy poor
    # ------------------------------------------------------------------

    def create_top10_most_poor(self) -> Optional[str]:
        filename = "top10_most_poor.png"
        try:
            top = self.df.nlargest(10, "mepi_score")
            fig, ax = plt.subplots(figsize=(10, 7))
            bars = ax.barh(top["upazila_name"], top["mepi_score"], color="#e74c3c", alpha=0.85)
            ax.set_xlabel("MEPI Score", fontsize=11)
            ax.set_title("Top 10 Most Energy-Poor Upazilas", fontsize=14, fontweight="bold")
            ax.set_xlim(0, 1)
            ax.invert_yaxis()
            ax.grid(True, axis="x", alpha=0.3)
            for bar, score in zip(bars, top["mepi_score"]):
                ax.text(
                    bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{score:.3f}", va="center", fontsize=9,
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
    # Top-10 least energy poor
    # ------------------------------------------------------------------

    def create_top10_least_poor(self) -> Optional[str]:
        filename = "top10_least_poor.png"
        try:
            top = self.df.nsmallest(10, "mepi_score")
            fig, ax = plt.subplots(figsize=(10, 7))
            bars = ax.barh(top["upazila_name"], top["mepi_score"], color="#2ecc71", alpha=0.85)
            ax.set_xlabel("MEPI Score", fontsize=11)
            ax.set_title("Top 10 Least Energy-Poor Upazilas", fontsize=14, fontweight="bold")
            ax.set_xlim(0, 1)
            ax.invert_yaxis()
            ax.grid(True, axis="x", alpha=0.3)
            for bar, score in zip(bars, top["mepi_score"]):
                ax.text(
                    bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{score:.3f}", va="center", fontsize=9,
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
    # Dimension heatmap
    # ------------------------------------------------------------------

    def create_dimension_heatmap(self) -> Optional[str]:
        filename = "dimension_heatmap.png"
        if not self._dim_cols:
            warnings.warn("No dimension score columns; skipping dimension_heatmap.", stacklevel=2)
            return None
        try:
            import seaborn as sns
            heat_data = self.df[self._dim_cols].copy()
            heat_data.columns = [c.replace("_score", "").capitalize() for c in self._dim_cols]
            fig, ax = plt.subplots(figsize=(10, max(6, len(self.df) * 0.10)))
            sns.heatmap(
                heat_data.T,
                cmap="YlOrRd", vmin=0, vmax=1,
                xticklabels=False, yticklabels=True,
                ax=ax,
                cbar_kws={"label": "Deprivation Score"},
            )
            ax.set_title(
                "Energy Poverty Dimension Scores – All Upazilas",
                fontsize=13, fontweight="bold",
            )
            ax.set_xlabel("Upazilas", fontsize=10)
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
    # Dimension correlation matrix
    # ------------------------------------------------------------------

    def create_dimension_correlation(self) -> Optional[str]:
        filename = "dimension_correlation.png"
        if len(self._dim_cols) < 2:
            warnings.warn("Need ≥2 dimension columns; skipping dimension_correlation.", stacklevel=2)
            return None
        try:
            import seaborn as sns
            cols = self._dim_cols + ["mepi_score"]
            corr = self.df[cols].corr()
            labels = [c.replace("_score", "").capitalize() for c in corr.columns]
            fig, ax = plt.subplots(figsize=(8, 7))
            sns.heatmap(
                corr, annot=True, fmt=".2f", cmap="coolwarm",
                vmin=-1, vmax=1, ax=ax,
                xticklabels=labels, yticklabels=labels,
            )
            ax.set_title("Dimension Score Correlation Matrix", fontsize=13, fontweight="bold")
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
    # Regional comparison (by division)
    # ------------------------------------------------------------------

    def create_regional_comparison(self) -> Optional[str]:
        filename = "regional_comparison.png"
        if "division" not in self.df.columns:
            warnings.warn("No 'division' column; skipping regional_comparison.", stacklevel=2)
            return None
        try:
            from config import POVERTY_THRESHOLDS

            div_means = (
                self.df.groupby("division")["mepi_score"]
                .mean()
                .sort_values(ascending=False)
            )
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(div_means.index, div_means.values, color="#3498db", alpha=0.8)
            ax.set_xlabel("Mean MEPI Score", fontsize=11)
            ax.set_title("Mean Energy Poverty by Division", fontsize=14, fontweight="bold")
            ax.set_xlim(0, 1)
            moderate_lo = POVERTY_THRESHOLDS.get("moderate", (0.33, 0.66))[0]
            severe_lo   = POVERTY_THRESHOLDS.get("severe",   (0.66, 1.00))[0]
            ax.axvline(moderate_lo, color="#f39c12", linestyle="--", linewidth=1, label="Moderate threshold")
            ax.axvline(severe_lo,   color="#e74c3c", linestyle="--", linewidth=1, label="Severe threshold")
            ax.legend(fontsize=9)
            ax.grid(True, axis="x", alpha=0.3)
            for bar, val in zip(bars, div_means.values):
                ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
                        f"{val:.3f}", va="center", fontsize=8)
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
    # Poverty classification distribution
    # ------------------------------------------------------------------

    def create_poverty_classification_distribution(self) -> Optional[str]:
        filename = "poverty_classification_distribution.png"
        try:
            from config import POVERTY_THRESHOLDS, POVERTY_LABELS

            if "poverty_category" in self.df.columns:
                counts = self.df["poverty_category"].value_counts()
            else:
                moderate_lo = POVERTY_THRESHOLDS.get("moderate", (0.33, 0.66))[0]
                severe_lo   = POVERTY_THRESHOLDS.get("severe",   (0.66, 1.00))[0]
                bins = [0, moderate_lo, severe_lo, 1.01]
                label_list = [
                    POVERTY_LABELS.get("non_poor",  "Non-Poor"),
                    POVERTY_LABELS.get("moderate",  "Moderately Poor"),
                    POVERTY_LABELS.get("severe",    "Severely Poor"),
                ]
                cats = pd.cut(
                    self.df["mepi_score"], bins=bins,
                    labels=label_list, include_lowest=True,
                )
                counts = cats.value_counts()

            color_map = {
                "Non-Poor": "#2ecc71",
                "Moderately Poor": "#f39c12",
                "Severely Poor": "#e74c3c",
            }
            bar_colors = [color_map.get(c, "#3498db") for c in counts.index]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(
                counts.index, counts.values,
                color=bar_colors, alpha=0.85, edgecolor="white",
            )
            ax.set_ylabel("Number of Upazilas", fontsize=11)
            ax.set_title(
                "Poverty Classification Distribution", fontsize=14, fontweight="bold",
            )
            ax.grid(True, axis="y", alpha=0.3)
            for bar, val in zip(bars, counts.values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    str(val), ha="center", va="bottom", fontsize=11,
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
        """Create all analysis maps and return list of saved paths."""
        saved: List[str] = []

        for method_name, label in [
            ("create_top10_most_poor",                   "top10_most_poor.png"),
            ("create_top10_least_poor",                  "top10_least_poor.png"),
            ("create_dimension_heatmap",                 "dimension_heatmap.png"),
            ("create_dimension_correlation",             "dimension_correlation.png"),
            ("create_regional_comparison",               "regional_comparison.png"),
            ("create_poverty_classification_distribution","poverty_classification_distribution.png"),
        ]:
            print(f"  Creating {label} ...")
            p = getattr(self, method_name)()
            if p:
                saved.append(p)

        return saved


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
        description="Generate statistical analysis maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ANALYSIS MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)
    mapper = AnalysisMapsExternal(results, base_dir=args.output_dir)
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} analysis map(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('analysis_maps')}")


if __name__ == "__main__":
    main()
