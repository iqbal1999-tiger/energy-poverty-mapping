"""
visualization.py - Visualization module for MEPI results

Provides publication-quality charts for the Multidimensional Energy Poverty
Index (MEPI) including bar charts, heatmaps, box plots, radar/spider charts,
distribution plots, regional comparisons, and stacked bar charts.

All functions accept a MEPI results DataFrame (output of MEPICalculator.calculate())
and return matplotlib Figure objects that can be saved or displayed interactively.

Usage:
    from visualization import MEPIVisualizer
    viz = MEPIVisualizer(results_df)
    fig = viz.plot_mepi_bar_chart()
    fig.savefig("mepi_bar.png", dpi=150, bbox_inches="tight")
"""

import warnings

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": 100,
    }
)

# ---------------------------------------------------------------------------
# Colour palettes (colorblind-friendly)
# ---------------------------------------------------------------------------
# Based on Wong (2011) colorblind-safe palette
POVERTY_COLORS = {
    "Non-Poor": "#009E73",          # green
    "Moderately Poor": "#E69F00",   # amber
    "Severely Poor": "#D55E00",     # vermillion
}

DIMENSION_COLORS = {
    "Availability": "#0072B2",    # blue
    "Reliability": "#56B4E9",     # sky blue
    "Adequacy": "#009E73",        # green
    "Quality": "#F0E442",         # yellow
    "Affordability": "#CC79A7",   # pink/purple
}

DIMENSIONS = ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]


def _get_poverty_color(category: str) -> str:
    return POVERTY_COLORS.get(category, "#999999")


class MEPIVisualizer:
    """
    Create visualizations from MEPI results.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.
    style : str, optional
        Matplotlib style name.  Defaults to ``"seaborn-v0_8-whitegrid"``.
    """

    def __init__(self, results_df: pd.DataFrame, style: str = "seaborn-v0_8-whitegrid"):
        self.df = results_df.copy()
        try:
            plt.style.use(style)
        except OSError:
            try:
                plt.style.use("seaborn-whitegrid")
            except OSError:
                pass  # fall back to default

        self._dim_score_cols = [
            f"{d}_score" for d in DIMENSIONS if f"{d}_score" in self.df.columns
        ]

    # ------------------------------------------------------------------
    # 1. Bar chart – MEPI scores by upazila
    # ------------------------------------------------------------------

    def plot_mepi_bar_chart(
        self,
        top_n: int = None,
        figsize: tuple = (14, 6),
        title: str = "MEPI Scores by Upazila",
    ) -> plt.Figure:
        """
        Horizontal bar chart showing MEPI scores, colour-coded by poverty category.

        Parameters
        ----------
        top_n : int, optional
            Show only the N most energy-poor upazilas.
        figsize : tuple, optional
            Figure size in inches.
        title : str, optional
            Chart title.

        Returns
        -------
        matplotlib.figure.Figure
        """
        df = self.df.copy()
        name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

        df = df.sort_values("mepi_score", ascending=True)
        if top_n is not None:
            df = df.tail(top_n)

        colours = (
            df["poverty_category"].map(_get_poverty_color).fillna("#999999")
            if "poverty_category" in df.columns
            else ["#0072B2"] * len(df)
        )

        fig, ax = plt.subplots(figsize=figsize)
        bars = ax.barh(
            df[name_col],
            df["mepi_score"],
            color=colours,
            edgecolor="white",
            linewidth=0.5,
        )

        # Poverty threshold lines
        ax.axvline(0.33, color="#E69F00", linestyle="--", linewidth=1.2, label="Moderate threshold (0.33)")
        ax.axvline(0.66, color="#D55E00", linestyle="--", linewidth=1.2, label="Severe threshold (0.66)")

        # Legend for poverty categories
        legend_patches = [
            mpatches.Patch(color=c, label=l) for l, c in POVERTY_COLORS.items()
        ]
        legend_patches += [
            mpatches.Patch(color="#E69F00", label="Moderate threshold"),
            mpatches.Patch(color="#D55E00", label="Severe threshold"),
        ]
        ax.legend(handles=legend_patches, loc="lower right", framealpha=0.9)

        ax.set_xlabel("MEPI Score (0 = no deprivation, 1 = maximum deprivation)")
        ax.set_title(title, fontweight="bold")
        ax.set_xlim(0, 1)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 2. Heatmap – dimension scores by upazila
    # ------------------------------------------------------------------

    def plot_dimension_heatmap(
        self,
        top_n: int = 20,
        figsize: tuple = (10, 8),
        title: str = "Energy Poverty Intensity by Dimension",
    ) -> plt.Figure:
        """
        Heatmap showing each dimension's deprivation score for each upazila.

        Parameters
        ----------
        top_n : int, optional
            Show only the N most energy-poor upazilas.
        figsize : tuple, optional
            Figure size in inches.
        title : str, optional
            Chart title.

        Returns
        -------
        matplotlib.figure.Figure
        """
        try:
            import seaborn as sns
        except ImportError:
            warnings.warn("seaborn not installed; using basic heatmap.")
            sns = None

        df = self.df.sort_values("mepi_score", ascending=False).head(top_n)
        name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

        heat_data = df.set_index(name_col)[self._dim_score_cols]
        heat_data.columns = [c.replace("_score", "") for c in heat_data.columns]

        fig, ax = plt.subplots(figsize=figsize)
        if sns is not None:
            sns.heatmap(
                heat_data,
                ax=ax,
                cmap="YlOrRd",
                vmin=0,
                vmax=1,
                annot=True,
                fmt=".2f",
                linewidths=0.5,
                cbar_kws={"label": "Deprivation Score"},
            )
        else:
            im = ax.imshow(heat_data.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
            ax.set_xticks(range(len(heat_data.columns)))
            ax.set_xticklabels(heat_data.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(heat_data.index)))
            ax.set_yticklabels(heat_data.index)
            fig.colorbar(im, ax=ax, label="Deprivation Score")

        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Dimension")
        ax.set_ylabel("Upazila")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 3. Box plots – dimension score distributions
    # ------------------------------------------------------------------

    def plot_dimension_boxplots(
        self,
        figsize: tuple = (10, 6),
        title: str = "Distribution of Dimension Scores",
    ) -> plt.Figure:
        """
        Box plots comparing score distributions across the five MEPI dimensions.

        Returns
        -------
        matplotlib.figure.Figure
        """
        dim_labels = [c.replace("_score", "") for c in self._dim_score_cols]
        data = [self.df[c].dropna().values for c in self._dim_score_cols]
        colours = [DIMENSION_COLORS.get(d, "#0072B2") for d in dim_labels]

        fig, ax = plt.subplots(figsize=figsize)
        bp = ax.boxplot(
            data,
            labels=dim_labels,
            patch_artist=True,
            notch=False,
            medianprops={"color": "black", "linewidth": 2},
        )
        for patch, colour in zip(bp["boxes"], colours):
            patch.set_facecolor(colour)
            patch.set_alpha(0.8)

        ax.axhline(0.33, color="#E69F00", linestyle="--", linewidth=1, label="Moderate threshold (0.33)")
        ax.axhline(0.66, color="#D55E00", linestyle="--", linewidth=1, label="Severe threshold (0.66)")
        ax.set_ylabel("Deprivation Score")
        ax.set_title(title, fontweight="bold")
        ax.legend()
        ax.set_ylim(-0.05, 1.05)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 4. Histogram – MEPI score distribution
    # ------------------------------------------------------------------

    def plot_mepi_histogram(
        self,
        bins: int = 15,
        figsize: tuple = (9, 5),
        title: str = "Distribution of MEPI Scores",
    ) -> plt.Figure:
        """
        Histogram (with KDE overlay if seaborn available) of MEPI scores.

        Returns
        -------
        matplotlib.figure.Figure
        """
        fig, ax = plt.subplots(figsize=figsize)

        try:
            import seaborn as sns
            sns.histplot(
                self.df["mepi_score"],
                bins=bins,
                kde=True,
                color="#0072B2",
                ax=ax,
                edgecolor="white",
            )
        except ImportError:
            ax.hist(
                self.df["mepi_score"],
                bins=bins,
                color="#0072B2",
                edgecolor="white",
            )

        ax.axvline(0.33, color="#E69F00", linestyle="--", linewidth=1.5, label="Moderate threshold (0.33)")
        ax.axvline(0.66, color="#D55E00", linestyle="--", linewidth=1.5, label="Severe threshold (0.66)")
        ax.axvline(self.df["mepi_score"].mean(), color="black", linestyle="-.", linewidth=1.5, label=f"Mean ({self.df['mepi_score'].mean():.3f})")

        # Shade poverty zones
        ax.axvspan(0.0, 0.33, alpha=0.06, color="#009E73")
        ax.axvspan(0.33, 0.66, alpha=0.06, color="#E69F00")
        ax.axvspan(0.66, 1.0, alpha=0.06, color="#D55E00")

        ax.set_xlabel("MEPI Score")
        ax.set_ylabel("Count")
        ax.set_title(title, fontweight="bold")
        ax.legend()
        ax.set_xlim(0, 1)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 5. Radar / spider chart – dimensional profile for selected upazilas
    # ------------------------------------------------------------------

    def plot_radar_chart(
        self,
        upazilas: list = None,
        figsize: tuple = (8, 8),
        title: str = "Dimensional Energy Poverty Profile",
    ) -> plt.Figure:
        """
        Radar chart showing dimension scores for selected (or top-3) upazilas.

        Parameters
        ----------
        upazilas : list, optional
            List of upazila names to include.  Defaults to the three most
            energy-poor upazilas.

        Returns
        -------
        matplotlib.figure.Figure
        """
        name_col = "upazila_name" if "upazila_name" in self.df.columns else self.df.columns[0]

        if upazilas is None:
            upazilas = (
                self.df.sort_values("mepi_score", ascending=False)
                .head(3)[name_col]
                .tolist()
            )

        dims = [c.replace("_score", "") for c in self._dim_score_cols]
        n_dims = len(dims)
        angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
        angles += angles[:1]  # close the polygon

        fig, ax = plt.subplots(figsize=figsize, subplot_kw={"polar": True})
        palette = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]

        for idx, name in enumerate(upazilas):
            row = self.df[self.df[name_col] == name]
            if row.empty:
                warnings.warn(f"Upazila '{name}' not found in data; skipping.")
                continue
            values = row[self._dim_score_cols].values.flatten().tolist()
            values += values[:1]
            colour = palette[idx % len(palette)]
            ax.plot(angles, values, "o-", linewidth=2, color=colour, label=name)
            ax.fill(angles, values, alpha=0.12, color=colour)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dims, size=10)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], size=7)
        ax.set_title(title, fontweight="bold", pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1))
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 6. Regional comparison bar chart
    # ------------------------------------------------------------------

    def plot_regional_comparison(
        self,
        group_col: str = "division",
        figsize: tuple = (10, 6),
        title: str = "Regional MEPI Score Comparison",
    ) -> plt.Figure:
        """
        Grouped bar chart comparing mean MEPI and dimension scores by region.

        Parameters
        ----------
        group_col : str, optional
            Column to group by (``"division"``, ``"district"``,
            or ``"geographic_zone"``).

        Returns
        -------
        matplotlib.figure.Figure
        """
        if group_col not in self.df.columns:
            raise ValueError(f"Column '{group_col}' not found in data.")

        region_means = (
            self.df.groupby(group_col)["mepi_score"].mean().sort_values(ascending=False)
        )
        colours = [
            POVERTY_COLORS["Severely Poor"] if v >= 0.66
            else POVERTY_COLORS["Moderately Poor"] if v >= 0.33
            else POVERTY_COLORS["Non-Poor"]
            for v in region_means.values
        ]

        fig, ax = plt.subplots(figsize=figsize)
        bars = ax.bar(
            region_means.index,
            region_means.values,
            color=colours,
            edgecolor="white",
            linewidth=0.8,
        )
        ax.axhline(0.33, color="#E69F00", linestyle="--", linewidth=1.2, label="Moderate threshold")
        ax.axhline(0.66, color="#D55E00", linestyle="--", linewidth=1.2, label="Severe threshold")

        for bar, val in zip(bars, region_means.values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        ax.set_xlabel(group_col.replace("_", " ").title())
        ax.set_ylabel("Mean MEPI Score")
        ax.set_title(title, fontweight="bold")
        ax.set_ylim(0, 1)
        ax.legend()
        plt.xticks(rotation=30, ha="right")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 7. Stacked bar chart – dimension contributions
    # ------------------------------------------------------------------

    def plot_stacked_dimension_contributions(
        self,
        top_n: int = 20,
        figsize: tuple = (12, 7),
        title: str = "Dimension Contributions to MEPI Score",
    ) -> plt.Figure:
        """
        Stacked bar chart showing how each dimension contributes to the total
        MEPI score for each upazila.

        Returns
        -------
        matplotlib.figure.Figure
        """
        df = self.df.sort_values("mepi_score", ascending=False).head(top_n)
        name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

        dim_labels = [c.replace("_score", "") for c in self._dim_score_cols]
        weight = 1 / len(dim_labels)   # equal-weight assumption for display

        fig, ax = plt.subplots(figsize=figsize)
        bottom = np.zeros(len(df))

        for dim, col in zip(dim_labels, self._dim_score_cols):
            contribution = df[col].values * weight
            ax.barh(
                df[name_col],
                contribution,
                left=bottom,
                label=dim,
                color=DIMENSION_COLORS.get(dim, "#999999"),
                edgecolor="white",
                linewidth=0.4,
            )
            bottom += contribution

        ax.set_xlabel("Weighted Dimension Score (equal weights)")
        ax.set_title(title, fontweight="bold")
        ax.legend(loc="lower right", framealpha=0.9)
        ax.set_xlim(0, 1)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 8. Scatter plot – two dimensions
    # ------------------------------------------------------------------

    def plot_scatter(
        self,
        x_dim: str = "Availability",
        y_dim: str = "Affordability",
        figsize: tuple = (8, 6),
        title: str = None,
    ) -> plt.Figure:
        """
        Scatter plot of two dimension scores, coloured by poverty category.

        Parameters
        ----------
        x_dim : str
            Dimension name for the x-axis.
        y_dim : str
            Dimension name for the y-axis.

        Returns
        -------
        matplotlib.figure.Figure
        """
        x_col = f"{x_dim}_score"
        y_col = f"{y_dim}_score"
        for col in (x_col, y_col):
            if col not in self.df.columns:
                raise ValueError(f"Column '{col}' not found.")

        if title is None:
            title = f"{x_dim} vs {y_dim} Deprivation"

        fig, ax = plt.subplots(figsize=figsize)

        for cat, colour in POVERTY_COLORS.items():
            subset = (
                self.df[self.df["poverty_category"] == cat]
                if "poverty_category" in self.df.columns
                else self.df
            )
            if subset.empty:
                continue
            ax.scatter(
                subset[x_col],
                subset[y_col],
                c=colour,
                label=cat,
                alpha=0.8,
                s=60,
                edgecolors="white",
                linewidths=0.5,
            )

        ax.set_xlabel(f"{x_dim} Score")
        ax.set_ylabel(f"{y_dim} Score")
        ax.set_title(title, fontweight="bold")
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.legend(title="Poverty Category")
        ax.axhline(0.33, color="grey", linestyle=":", linewidth=0.8)
        ax.axvline(0.33, color="grey", linestyle=":", linewidth=0.8)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 9. Violin plot – dimension scores by region
    # ------------------------------------------------------------------

    def plot_violin(
        self,
        group_col: str = "division",
        figsize: tuple = (12, 6),
        title: str = "MEPI Score Distribution by Region",
    ) -> plt.Figure:
        """
        Violin plot of MEPI scores grouped by a regional column.

        Returns
        -------
        matplotlib.figure.Figure
        """
        if group_col not in self.df.columns:
            raise ValueError(f"Column '{group_col}' not found.")

        try:
            import seaborn as sns
        except ImportError:
            warnings.warn("seaborn not available; falling back to box plot.")
            return self._violin_fallback(group_col, figsize, title)

        fig, ax = plt.subplots(figsize=figsize)
        order = (
            self.df.groupby(group_col)["mepi_score"]
            .median()
            .sort_values(ascending=False)
            .index.tolist()
        )
        sns.violinplot(
            data=self.df,
            x=group_col,
            y="mepi_score",
            hue=group_col,
            order=order,
            palette="colorblind",
            ax=ax,
            cut=0,
            inner="quartile",
            legend=False,
        )
        ax.axhline(0.33, color="#E69F00", linestyle="--", linewidth=1.2, label="Moderate threshold")
        ax.axhline(0.66, color="#D55E00", linestyle="--", linewidth=1.2, label="Severe threshold")
        ax.set_xlabel(group_col.replace("_", " ").title())
        ax.set_ylabel("MEPI Score")
        ax.set_title(title, fontweight="bold")
        ax.legend()
        plt.xticks(rotation=30, ha="right")
        fig.tight_layout()
        return fig

    def _violin_fallback(self, group_col, figsize, title):
        groups = self.df.groupby(group_col)["mepi_score"]
        labels = list(groups.groups.keys())
        data = [groups.get_group(g).values for g in labels]
        fig, ax = plt.subplots(figsize=figsize)
        ax.boxplot(data, labels=labels)
        ax.set_title(title, fontweight="bold")
        plt.xticks(rotation=30, ha="right")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 10. Pie chart – poverty category breakdown
    # ------------------------------------------------------------------

    def plot_poverty_pie(
        self,
        figsize: tuple = (7, 7),
        title: str = "Poverty Category Distribution",
    ) -> plt.Figure:
        """
        Pie chart showing the share of upazilas in each poverty category.

        Returns
        -------
        matplotlib.figure.Figure
        """
        if "poverty_category" not in self.df.columns:
            raise ValueError("'poverty_category' column not found.")

        counts = self.df["poverty_category"].value_counts()
        colours = [POVERTY_COLORS.get(c, "#999999") for c in counts.index]

        fig, ax = plt.subplots(figsize=figsize)
        wedges, texts, autotexts = ax.pie(
            counts.values,
            labels=counts.index,
            colors=colours,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.8,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for t in autotexts:
            t.set_fontsize(10)
        ax.set_title(title, fontweight="bold")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # Helper: save figure
    # ------------------------------------------------------------------

    @staticmethod
    def save_figure(fig: plt.Figure, filepath: str, dpi: int = 150):
        """Save a figure to PNG or PDF."""
        import os
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
        print(f"Figure saved: {filepath}")
