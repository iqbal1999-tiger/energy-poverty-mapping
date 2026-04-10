"""
chart_graph_generator.py - Generate charts and graphs for the MEPI report.

Creates and saves PNG figures that are later embedded in the PDF and DOCX
reports.  All charts are saved to the directory defined in report_config.py
(``CHARTS_OUTPUT_DIR``).

Generates
---------
- bar_top10_most_poor.png       – top 10 most energy-poor upazilas
- bar_top10_least_poor.png      – top 10 least energy-poor upazilas
- dimension_comparison.png      – bar chart of mean dimension scores
- dimension_heatmap.png         – heatmap of all upazilas × dimensions
- regional_comparison.png       – grouped bar chart by geographic zone
- distribution_mepi.png         – histogram + KDE of MEPI scores
- scatter_dimensions.png        – scatter matrix of dimension scores
- poverty_category_pie.png      – pie chart of poverty categories
- correlation_heatmap.png       – dimension correlation heatmap
- temporal_trend.png            – placeholder temporal trend line chart

Usage
-----
    from chart_graph_generator import ChartGenerator
    cg = ChartGenerator(results_df)
    paths = cg.generate_all()
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")           # non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

from report_config import (
    CHARTS_OUTPUT_DIR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_ACCENT,
    COLOR_SEVERE,
    COLOR_MODERATE,
    COLOR_NON_POOR,
    IMAGE_DPI,
)

# Dimension score column names (lowercase, with _score suffix)
_DIM_COLS = [
    "Availability_score",
    "Reliability_score",
    "Adequacy_score",
    "Quality_score",
    "Affordability_score",
]
_DIM_LABELS = ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]

# Colour palette for the 5 dimensions
_DIM_COLORS = ["#1F4E79", "#2E75B6", "#ED7D31", "#A9D18E", "#FF0000"]

# Poverty-category colours
_CAT_COLORS = {
    "Non-Poor": "#2ECC71",
    "Moderately Poor": "#F39C12",
    "Severely Poor": "#E74C3C",
}


class ChartGenerator:
    """
    Generate charts and graphs for embedding in the MEPI report.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.
    output_dir : str, optional
        Directory to save PNG files.  Defaults to ``CHARTS_OUTPUT_DIR``.
    """

    def __init__(
        self,
        results_df: pd.DataFrame,
        output_dir: Optional[str] = None,
    ):
        self.df = results_df.copy()
        self.output_dir = output_dir or CHARTS_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        # Resolve available dimension columns
        self._dim_cols = [c for c in _DIM_COLS if c in self.df.columns]
        self._dim_labels = [c.replace("_score", "") for c in self._dim_cols]

        self._name_col = (
            "upazila_name" if "upazila_name" in self.df.columns else self.df.columns[0]
        )

        if HAS_SEABORN:
            sns.set_theme(style="whitegrid", palette="muted", font_scale=1.0)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _save(self, fig: plt.Figure, filename: str) -> str:
        path = os.path.join(self.output_dir, filename)
        fig.savefig(path, dpi=IMAGE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # ------------------------------------------------------------------
    # Individual chart methods
    # ------------------------------------------------------------------

    def bar_top10_most_poor(self) -> str:
        """Horizontal bar chart – top 10 most energy-poor upazilas."""
        top10 = self.df.nlargest(10, "mepi_score")[
            [self._name_col, "mepi_score"]
        ].iloc[::-1]  # reverse so worst is at top

        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.barh(
            top10[self._name_col],
            top10["mepi_score"],
            color=COLOR_ACCENT,
            edgecolor="white",
        )
        ax.set_xlabel("MEPI Score (0 = no poverty, 1 = maximum poverty)", fontsize=10)
        ax.set_title(
            "Top 10 Most Energy-Poor Upazilas", fontsize=13, fontweight="bold",
            color=COLOR_PRIMARY,
        )
        ax.set_xlim(0, 1)
        for bar, val in zip(bars, top10["mepi_score"]):
            ax.text(
                val + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9,
            )
        ax.axvline(0.66, color="red", linestyle="--", linewidth=1, label="Severe threshold (0.66)")
        ax.axvline(0.33, color="orange", linestyle="--", linewidth=1, label="Moderate threshold (0.33)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        return self._save(fig, "bar_top10_most_poor.png")

    def bar_top10_least_poor(self) -> str:
        """Horizontal bar chart – top 10 least energy-poor upazilas."""
        bot10 = self.df.nsmallest(10, "mepi_score")[
            [self._name_col, "mepi_score"]
        ].iloc[::-1]

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(
            bot10[self._name_col],
            bot10["mepi_score"],
            color=COLOR_SECONDARY,
            edgecolor="white",
        )
        ax.set_xlabel("MEPI Score (0 = no poverty, 1 = maximum poverty)", fontsize=10)
        ax.set_title(
            "Top 10 Least Energy-Poor Upazilas", fontsize=13, fontweight="bold",
            color=COLOR_PRIMARY,
        )
        ax.set_xlim(0, 1)
        ax.axvline(0.33, color="orange", linestyle="--", linewidth=1, label="Moderate threshold (0.33)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        return self._save(fig, "bar_top10_least_poor.png")

    def dimension_comparison(self) -> str:
        """Bar chart comparing mean scores across the 5 dimensions."""
        means = [self.df[c].mean() for c in self._dim_cols]

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(
            self._dim_labels, means,
            color=_DIM_COLORS[: len(self._dim_labels)],
            edgecolor="white", width=0.6,
        )
        ax.set_ylabel("Mean Dimension Score", fontsize=10)
        ax.set_title(
            "Mean MEPI Dimension Scores Across All Upazilas",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.set_ylim(0, 1)
        for bar, val in zip(bars, means):
            ax.text(
                bar.get_x() + bar.get_width() / 2, val + 0.01,
                f"{val:.3f}", ha="center", va="bottom", fontsize=10,
            )
        ax.axhline(0.66, color="red", linestyle="--", linewidth=1, label="Severe (0.66)")
        ax.axhline(0.33, color="orange", linestyle="--", linewidth=1, label="Moderate (0.33)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        return self._save(fig, "dimension_comparison.png")

    def dimension_heatmap(self) -> str:
        """Heatmap of dimension scores for all upazilas."""
        plot_df = self.df[[self._name_col] + self._dim_cols].copy()
        plot_df = plot_df.set_index(self._name_col)
        plot_df.columns = self._dim_labels

        fig, ax = plt.subplots(figsize=(10, max(6, len(plot_df) * 0.35)))
        if HAS_SEABORN:
            sns.heatmap(
                plot_df, annot=True, fmt=".2f", cmap="RdYlGn_r",
                vmin=0, vmax=1, linewidths=0.5, ax=ax,
                annot_kws={"size": 8},
            )
        else:
            im = ax.imshow(plot_df.values, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
            ax.set_xticks(range(len(self._dim_labels)))
            ax.set_xticklabels(self._dim_labels)
            ax.set_yticks(range(len(plot_df)))
            ax.set_yticklabels(plot_df.index)
            plt.colorbar(im, ax=ax)

        ax.set_title(
            "Dimension Score Heatmap by Upazila",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.set_xlabel("Dimension", fontsize=10)
        ax.set_ylabel("Upazila", fontsize=10)
        fig.tight_layout()
        return self._save(fig, "dimension_heatmap.png")

    def regional_comparison(self) -> str:
        """Grouped bar chart comparing MEPI dimensions across geographic zones."""
        zone_col = "geographic_zone" if "geographic_zone" in self.df.columns else None
        if zone_col is None or self.df[zone_col].nunique() < 2:
            # Fallback: use division column
            zone_col = "division" if "division" in self.df.columns else None
        if zone_col is None:
            return self._placeholder_chart("regional_comparison.png", "Regional Comparison")

        grouped = self.df.groupby(zone_col)[self._dim_cols].mean()
        grouped.columns = self._dim_labels

        fig, ax = plt.subplots(figsize=(12, 6))
        n_zones = len(grouped)
        n_dims = len(self._dim_labels)
        x = np.arange(n_zones)
        width = 0.8 / n_dims

        for i, (dim, color) in enumerate(zip(self._dim_labels, _DIM_COLORS)):
            offset = (i - n_dims / 2 + 0.5) * width
            ax.bar(x + offset, grouped[dim], width=width, label=dim, color=color, edgecolor="white")

        ax.set_xticks(x)
        ax.set_xticklabels(grouped.index, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Mean Dimension Score", fontsize=10)
        ax.set_title(
            "Regional Comparison of MEPI Dimensions",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.set_ylim(0, 1)
        ax.legend(title="Dimension", fontsize=8, title_fontsize=9)
        fig.tight_layout()
        return self._save(fig, "regional_comparison.png")

    def distribution_mepi(self) -> str:
        """Histogram with KDE of MEPI scores."""
        scores = self.df["mepi_score"].dropna()

        fig, ax = plt.subplots(figsize=(8, 5))
        n_bins = min(20, max(10, len(scores) // 3))

        ax.hist(scores, bins=n_bins, color=COLOR_SECONDARY, edgecolor="white", density=True, alpha=0.75)

        if HAS_SEABORN:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(scores)
            x_range = np.linspace(scores.min(), scores.max(), 200)
            ax.plot(x_range, kde(x_range), color=COLOR_PRIMARY, linewidth=2, label="KDE")

        ax.axvline(0.33, color="orange", linestyle="--", linewidth=1.5, label="Moderate (0.33)")
        ax.axvline(0.66, color="red", linestyle="--", linewidth=1.5, label="Severe (0.66)")
        ax.set_xlabel("MEPI Score", fontsize=10)
        ax.set_ylabel("Density", fontsize=10)
        ax.set_title(
            "Distribution of MEPI Scores Across Upazilas",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.legend(fontsize=9)
        fig.tight_layout()
        return self._save(fig, "distribution_mepi.png")

    def poverty_category_pie(self) -> str:
        """Pie chart showing proportion of upazilas in each poverty category."""
        if "poverty_category" not in self.df.columns:
            return self._placeholder_chart("poverty_category_pie.png", "Poverty Category Distribution")

        counts = self.df["poverty_category"].value_counts()
        labels = counts.index.tolist()
        colors = [_CAT_COLORS.get(l, "#AAAAAA") for l in labels]

        fig, ax = plt.subplots(figsize=(7, 5))
        wedges, texts, autotexts = ax.pie(
            counts, labels=labels, autopct="%1.1f%%",
            colors=colors, startangle=140,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_fontsize(10)
            at.set_fontweight("bold")
        ax.set_title(
            "Poverty Category Distribution",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        fig.tight_layout()
        return self._save(fig, "poverty_category_pie.png")

    def correlation_heatmap(self) -> str:
        """Heatmap of pairwise correlations between dimension scores."""
        corr_df = self.df[self._dim_cols].rename(
            columns={c: c.replace("_score", "") for c in self._dim_cols}
        ).corr()

        fig, ax = plt.subplots(figsize=(7, 6))
        if HAS_SEABORN:
            mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1)
            sns.heatmap(
                corr_df, annot=True, fmt=".2f", cmap="coolwarm",
                vmin=-1, vmax=1, mask=mask, ax=ax,
                linewidths=0.5, annot_kws={"size": 10},
            )
        else:
            im = ax.imshow(corr_df.values, cmap="coolwarm", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr_df.columns)))
            ax.set_xticklabels(corr_df.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr_df.index)))
            ax.set_yticklabels(corr_df.index)
            plt.colorbar(im, ax=ax)

        ax.set_title(
            "Dimension Score Correlation Matrix",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        fig.tight_layout()
        return self._save(fig, "correlation_heatmap.png")

    def temporal_trend(self) -> str:
        """
        Placeholder temporal trend chart.

        In the absence of multi-year data, this chart shows a hypothetical
        trend using randomly perturbed values for illustration purposes.
        """
        years = [2018, 2019, 2020, 2021, 2022, 2023]
        rng = np.random.default_rng(42)
        mean_score = self.df["mepi_score"].mean()

        # Simulate a declining trend with noise
        trend = [min(1.0, mean_score + 0.05 * (2022 - y) + rng.normal(0, 0.01)) for y in years]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(years, trend, marker="o", color=COLOR_PRIMARY, linewidth=2, markersize=7)
        ax.fill_between(
            years,
            [v - 0.02 for v in trend],
            [v + 0.02 for v in trend],
            alpha=0.25, color=COLOR_SECONDARY,
        )
        ax.set_xlabel("Year", fontsize=10)
        ax.set_ylabel("Mean MEPI Score", fontsize=10)
        ax.set_title(
            "Temporal Trend of Mean MEPI Score (Illustrative)",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.set_ylim(0, 1)
        ax.set_xticks(years)
        ax.annotate(
            "* Simulated trend for illustration",
            xy=(0.02, 0.04), xycoords="axes fraction",
            fontsize=8, color="grey",
        )
        fig.tight_layout()
        return self._save(fig, "temporal_trend.png")

    def box_plot_by_zone(self) -> str:
        """Box plot of MEPI score distribution by geographic zone or division."""
        group_col = None
        for col in ("geographic_zone", "division", "district"):
            if col in self.df.columns and self.df[col].nunique() > 1:
                group_col = col
                break
        if group_col is None:
            return self._placeholder_chart("box_plot_by_zone.png", "Regional MEPI Distribution")

        fig, ax = plt.subplots(figsize=(10, 5))
        groups = self.df.groupby(group_col)["mepi_score"].apply(list)
        labels = groups.index.tolist()
        data = [groups[l] for l in labels]

        bp = ax.boxplot(data, labels=labels, patch_artist=True, notch=False)
        colors = plt.cm.Set2(np.linspace(0, 1, len(labels)))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)

        ax.set_xlabel(group_col.replace("_", " ").title(), fontsize=10)
        ax.set_ylabel("MEPI Score", fontsize=10)
        ax.set_title(
            f"MEPI Score Distribution by {group_col.replace('_', ' ').title()}",
            fontsize=13, fontweight="bold", color=COLOR_PRIMARY,
        )
        ax.set_ylim(0, 1)
        plt.xticks(rotation=30, ha="right", fontsize=9)
        fig.tight_layout()
        return self._save(fig, "box_plot_by_zone.png")

    # ------------------------------------------------------------------
    # Placeholder helper
    # ------------------------------------------------------------------

    def _placeholder_chart(self, filename: str, title: str) -> str:
        """Create a placeholder figure when data is insufficient."""
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5, 0.5,
            f"[PLACEHOLDER]\n{title}\n\nInsert actual chart here",
            ha="center", va="center", fontsize=14, color="grey",
            transform=ax.transAxes,
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F0F0F0", "edgecolor": "#CCCCCC"},
        )
        ax.set_title(title, fontsize=13, fontweight="bold", color=COLOR_PRIMARY)
        ax.axis("off")
        fig.tight_layout()
        return self._save(fig, filename)

    # ------------------------------------------------------------------
    # Master generate_all
    # ------------------------------------------------------------------

    def generate_all(self) -> Dict[str, str]:
        """
        Generate all charts and return a dict mapping chart name → file path.

        Returns
        -------
        dict
            Keys are descriptive chart names; values are absolute file paths.
        """
        print("Generating charts and graphs …")
        charts: Dict[str, str] = {}

        _generators = [
            ("top10_most_poor", self.bar_top10_most_poor),
            ("top10_least_poor", self.bar_top10_least_poor),
            ("dimension_comparison", self.dimension_comparison),
            ("dimension_heatmap", self.dimension_heatmap),
            ("regional_comparison", self.regional_comparison),
            ("distribution_mepi", self.distribution_mepi),
            ("poverty_category_pie", self.poverty_category_pie),
            ("correlation_heatmap", self.correlation_heatmap),
            ("temporal_trend", self.temporal_trend),
            ("box_plot_by_zone", self.box_plot_by_zone),
        ]

        for name, fn in _generators:
            try:
                path = fn()
                charts[name] = path
                print(f"  ✓  {os.path.basename(path)}")
            except Exception as exc:
                print(f"  ✗  {name}: {exc}")
                charts[name] = self._placeholder_chart(f"{name}.png", name.replace("_", " ").title())

        print(f"\nAll charts saved to: {self.output_dir}")
        return charts
