"""
visualization_generator.py - Main script to generate all MEPI visualizations

Loads MEPI results data, creates publication-quality PNG charts, and saves
them to the visualizations/ folder.  Supports batch processing of all 25+
charts in a single call.

Usage:
    from visualization_generator import MEPIVisualizationGenerator
    gen = MEPIVisualizationGenerator(results_df)
    gen.generate_all()
"""

import logging
import warnings

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file output

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

try:
    import seaborn as sns
    _HAS_SEABORN = True
except ImportError:
    _HAS_SEABORN = False
    warnings.warn("seaborn not installed; some charts will use fallback rendering.")

from visualization_config import (
    POVERTY_COLORS,
    DIMENSION_COLORS,
    HEATMAP_CMAP,
    CORRELATION_CMAP,
    FIGURE_SIZES,
    FONT_SIZES,
    DPI,
    OUTPUT_DIR,
    DIMENSIONS,
    POVERTY_THRESHOLD_MODERATE,
    POVERTY_THRESHOLD_SEVERE,
    CHART_TITLES,
)
from visualization_utils import (
    apply_global_style,
    get_name_col,
    dim_score_cols,
    poverty_legend_patches,
    dimension_legend_patches,
    add_poverty_threshold_lines,
    format_score_axis,
    style_axes,
    save_figure,
    ensure_output_dir,
    get_poverty_color,
    get_dimension_color,
    classify_zone,
    map_poverty_colors,
)

logger = logging.getLogger(__name__)


class MEPIVisualizationGenerator:
    """
    Generate and save all MEPI visualization charts as PNG files.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of MEPICalculator.calculate() containing MEPI scores,
        dimension scores, and poverty classifications.
    output_dir : str, optional
        Folder where PNG files will be saved.  Defaults to 'visualizations/'.
    dpi : int, optional
        Resolution of saved figures.  Default 300.
    geographic_zones : dict, optional
        Zone → districts mapping from config.GEOGRAPHIC_ZONES.

    Examples
    --------
    >>> gen = MEPIVisualizationGenerator(results_df)
    >>> paths = gen.generate_all()
    >>> print(f"Generated {len(paths)} visualizations")
    """

    def __init__(self, results_df: pd.DataFrame, output_dir: str = OUTPUT_DIR,
                 dpi: int = DPI, geographic_zones: dict = None):
        self.df = results_df.copy()
        self.output_dir = output_dir
        self.dpi = dpi
        self.geographic_zones = geographic_zones or {}

        apply_global_style()
        ensure_output_dir(self.output_dir)

        self._name_col = get_name_col(self.df)
        self._dim_cols = dim_score_cols(self.df)

        # Add zone column if geographic_zones provided and district column exists
        if self.geographic_zones and "district" in self.df.columns:
            self.df["zone"] = self.df["district"].apply(
                lambda d: classify_zone(d, self.geographic_zones)
            )

    # ------------------------------------------------------------------
    # Batch generation
    # ------------------------------------------------------------------

    def generate_all(self) -> list:
        """
        Generate all visualizations and save as PNG files.

        Returns
        -------
        list of str
            Paths of all saved PNG files.
        """
        generators = [
            # Overview charts
            self.generate_mepi_scores_by_upazila,
            self.generate_mepi_distribution,
            self.generate_poverty_classification_pie,
            self.generate_top10_most_poor,
            self.generate_top10_least_poor,
            # Dimensional analysis
            self.generate_availability_scores,
            self.generate_reliability_scores,
            self.generate_adequacy_scores,
            self.generate_quality_scores,
            self.generate_affordability_scores,
            self.generate_dimension_heatmap,
            self.generate_dimension_boxplots,
            self.generate_dimension_violin_plots,
            # Regional analysis
            self.generate_coastal_analysis,
            self.generate_char_islands_analysis,
            self.generate_haor_analysis,
            self.generate_hill_tract_analysis,
            self.generate_sundarbans_analysis,
            self.generate_urban_rural_comparison,
            # Advanced analysis
            self.generate_dimension_correlation_heatmap,
            self.generate_radar_profiles,
            self.generate_dimension_contribution,
            self.generate_spatial_distribution_map,
            # Summary dashboards
            self.generate_executive_summary,
            self.generate_regional_summary,
        ]

        saved_paths = []
        for generator_fn in generators:
            try:
                path = generator_fn()
                if path:
                    saved_paths.append(path)
                    logger.info("✓ %s", path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("✗ %s failed: %s", generator_fn.__name__, exc)
            finally:
                plt.close("all")

        logger.info("Generated %d / %d visualizations.", len(saved_paths), len(generators))
        return saved_paths

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save(self, fig: plt.Figure, filename: str) -> str:
        return save_figure(fig, filename, self.output_dir, self.dpi)

    def _sorted_df(self, ascending: bool = True) -> pd.DataFrame:
        return self.df.sort_values("mepi_score", ascending=ascending)

    def _zone_df(self, zone_name: str) -> pd.DataFrame:
        """Return rows belonging to a geographic zone."""
        if "zone" in self.df.columns:
            subset = self.df[self.df["zone"] == zone_name]
            if len(subset) > 0:
                return subset
        # Fallback: filter by district names from geographic_zones
        zone_info = self.geographic_zones.get(zone_name, {})
        districts = zone_info.get("districts", [])
        if districts and "district" in self.df.columns:
            return self.df[self.df["district"].isin(districts)]
        return pd.DataFrame()

    def _single_dimension_bar(self, dimension: str, title: str, filename: str) -> str:
        """Horizontal bar chart for a single dimension score."""
        col = f"{dimension}_score"
        if col not in self.df.columns:
            logger.warning("Column %s not found; skipping %s.", col, filename)
            return ""

        df = self.df.sort_values(col, ascending=True)
        figsize = FIGURE_SIZES["bar_chart_all"]
        fig, ax = plt.subplots(figsize=figsize)

        color = get_dimension_color(dimension)
        ax.barh(df[self._name_col], df[col], color=color, edgecolor="white", linewidth=0.4)

        ax.axvline(POVERTY_THRESHOLD_MODERATE, color="#E69F00",
                   linestyle="--", linewidth=1.2, alpha=0.8)
        ax.axvline(POVERTY_THRESHOLD_SEVERE, color="#D55E00",
                   linestyle="--", linewidth=1.2, alpha=0.8)

        ax.set_xlim(0, 1)
        ax.set_xlabel("Deprivation Score (0 = least, 1 = most deprived)",
                      fontsize=FONT_SIZES["axis_label"])
        ax.set_title(title, fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.tick_params(axis="y", labelsize=max(6, FONT_SIZES["tick_label"] - 2))
        fig.tight_layout()
        return self._save(fig, filename)

    # ==================================================================
    # OVERVIEW CHARTS
    # ==================================================================

    def generate_mepi_scores_by_upazila(self) -> str:
        """Bar chart of all MEPI scores sorted from least to most deprived."""
        df = self._sorted_df(ascending=True)
        fig, ax = plt.subplots(figsize=FIGURE_SIZES["bar_chart_all"])

        colors = map_poverty_colors(df["poverty_category"]) \
            if "poverty_category" in df.columns else ["#0072B2"] * len(df)

        ax.barh(df[self._name_col], df["mepi_score"],
                color=colors, edgecolor="white", linewidth=0.4)

        add_poverty_threshold_lines(ax, "vertical")
        ax.set_xlim(0, 1)
        ax.set_xlabel("MEPI Score (0 = least deprived, 1 = most deprived)",
                      fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["mepi_scores_by_upazila"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.tick_params(axis="y", labelsize=max(6, FONT_SIZES["tick_label"] - 2))

        legend = poverty_legend_patches()
        legend += [
            mpatches.Patch(color="#E69F00", label=f"Moderate threshold ({POVERTY_THRESHOLD_MODERATE})"),
            mpatches.Patch(color="#D55E00", label=f"Severe threshold ({POVERTY_THRESHOLD_SEVERE})"),
        ]
        ax.legend(handles=legend, loc="lower right", framealpha=0.9,
                  fontsize=FONT_SIZES["legend"])
        fig.tight_layout()
        return self._save(fig, "mepi_scores_by_upazila.png")

    def generate_mepi_distribution(self) -> str:
        """Histogram of MEPI score distribution with poverty zone shading."""
        fig, ax = plt.subplots(figsize=FIGURE_SIZES["histogram"])
        scores = self.df["mepi_score"].dropna()

        n_bins = max(10, len(scores) // 3)
        ax.hist(scores, bins=n_bins, color="#0072B2", edgecolor="white",
                linewidth=0.6, alpha=0.85)

        ax.axvspan(0, POVERTY_THRESHOLD_MODERATE, alpha=0.08,
                   color=POVERTY_COLORS["Non-Poor"], label="Non-Poor zone")
        ax.axvspan(POVERTY_THRESHOLD_MODERATE, POVERTY_THRESHOLD_SEVERE,
                   alpha=0.08, color=POVERTY_COLORS["Moderately Poor"],
                   label="Moderately Poor zone")
        ax.axvspan(POVERTY_THRESHOLD_SEVERE, 1.0, alpha=0.08,
                   color=POVERTY_COLORS["Severely Poor"], label="Severely Poor zone")

        ax.axvline(scores.mean(), color="#CC0000", linestyle="-",
                   linewidth=1.8, label=f"Mean = {scores.mean():.3f}")
        ax.axvline(scores.median(), color="#555555", linestyle=":",
                   linewidth=1.8, label=f"Median = {scores.median():.3f}")

        ax.set_xlim(0, 1)
        ax.set_xlabel("MEPI Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_ylabel("Number of Upazilas", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["mepi_distribution"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.legend(framealpha=0.9, fontsize=FONT_SIZES["legend"])
        fig.tight_layout()
        return self._save(fig, "mepi_distribution.png")

    def generate_poverty_classification_pie(self) -> str:
        """Pie chart showing proportion of upazilas in each poverty class."""
        if "poverty_category" not in self.df.columns:
            logger.warning("No poverty_category column; skipping pie chart.")
            return ""

        counts = self.df["poverty_category"].value_counts()
        labels = counts.index.tolist()
        sizes = counts.values
        colors = [get_poverty_color(l) for l in labels]

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["pie_chart"])
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        for at in autotexts:
            at.set_fontsize(FONT_SIZES["legend"])
        for t in texts:
            t.set_fontsize(FONT_SIZES["axis_label"])

        ax.set_title(CHART_TITLES["poverty_classification_pie"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=16)
        fig.tight_layout()
        return self._save(fig, "poverty_classification_pie.png")

    def generate_top10_most_poor(self) -> str:
        """Bar chart of top 10 most energy-poor upazilas."""
        df = self._sorted_df(ascending=False).head(10)
        fig, ax = plt.subplots(figsize=FIGURE_SIZES["bar_chart_top10"])

        colors = map_poverty_colors(df["poverty_category"]) \
            if "poverty_category" in df.columns else [POVERTY_COLORS["Severely Poor"]] * 10

        ax.barh(df[self._name_col][::-1], df["mepi_score"][::-1],
                color=colors[::-1], edgecolor="white", linewidth=0.5)
        ax.set_xlim(0, 1)
        ax.set_xlabel("MEPI Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["top10_most_poor"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)

        for i, (val, name) in enumerate(
            zip(df["mepi_score"][::-1], df[self._name_col][::-1])
        ):
            ax.text(val + 0.01, i, f"{val:.3f}",
                    va="center", fontsize=FONT_SIZES["annotation"])

        fig.tight_layout()
        return self._save(fig, "top10_most_poor.png")

    def generate_top10_least_poor(self) -> str:
        """Bar chart of top 10 least energy-poor upazilas."""
        df = self._sorted_df(ascending=True).head(10)
        fig, ax = plt.subplots(figsize=FIGURE_SIZES["bar_chart_top10"])

        colors = map_poverty_colors(df["poverty_category"]) \
            if "poverty_category" in df.columns else [POVERTY_COLORS["Non-Poor"]] * 10

        ax.barh(df[self._name_col], df["mepi_score"],
                color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xlim(0, 1)
        ax.set_xlabel("MEPI Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["top10_least_poor"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)

        for i, (val, name) in enumerate(
            zip(df["mepi_score"], df[self._name_col])
        ):
            ax.text(val + 0.01, i, f"{val:.3f}",
                    va="center", fontsize=FONT_SIZES["annotation"])

        fig.tight_layout()
        return self._save(fig, "top10_least_poor.png")

    # ==================================================================
    # DIMENSIONAL ANALYSIS
    # ==================================================================

    def generate_availability_scores(self) -> str:
        return self._single_dimension_bar(
            "Availability",
            CHART_TITLES["availability_scores"],
            "availability_scores.png",
        )

    def generate_reliability_scores(self) -> str:
        return self._single_dimension_bar(
            "Reliability",
            CHART_TITLES["reliability_scores"],
            "reliability_scores.png",
        )

    def generate_adequacy_scores(self) -> str:
        return self._single_dimension_bar(
            "Adequacy",
            CHART_TITLES["adequacy_scores"],
            "adequacy_scores.png",
        )

    def generate_quality_scores(self) -> str:
        return self._single_dimension_bar(
            "Quality",
            CHART_TITLES["quality_scores"],
            "quality_scores.png",
        )

    def generate_affordability_scores(self) -> str:
        return self._single_dimension_bar(
            "Affordability",
            CHART_TITLES["affordability_scores"],
            "affordability_scores.png",
        )

    def generate_dimension_heatmap(self) -> str:
        """Heatmap: upazila × dimension deprivation scores."""
        if not self._dim_cols:
            logger.warning("No dimension score columns found; skipping heatmap.")
            return ""

        df = self._sorted_df(ascending=False)
        name_col = self._name_col
        heat_data = df.set_index(name_col)[self._dim_cols].copy()
        heat_data.columns = [c.replace("_score", "") for c in heat_data.columns]

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["heatmap"])

        if _HAS_SEABORN:
            sns.heatmap(
                heat_data,
                ax=ax,
                cmap=HEATMAP_CMAP,
                vmin=0, vmax=1,
                annot=len(heat_data) <= 25,
                fmt=".2f",
                linewidths=0.4,
                cbar_kws={"label": "Deprivation Score"},
            )
        else:
            im = ax.imshow(heat_data.values, aspect="auto",
                           cmap=HEATMAP_CMAP, vmin=0, vmax=1)
            ax.set_xticks(range(len(heat_data.columns)))
            ax.set_xticklabels(heat_data.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(heat_data.index)))
            ax.set_yticklabels(heat_data.index)
            fig.colorbar(im, ax=ax, label="Deprivation Score")

        ax.set_title(CHART_TITLES["dimension_heatmap"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.set_xlabel("Dimension", fontsize=FONT_SIZES["axis_label"])
        ax.set_ylabel("Upazila", fontsize=FONT_SIZES["axis_label"])
        ax.tick_params(axis="y", labelsize=max(6, FONT_SIZES["tick_label"] - 2))
        fig.tight_layout()
        return self._save(fig, "dimension_heatmap.png")

    def generate_dimension_boxplots(self) -> str:
        """Box plots comparing the distribution of each dimension score."""
        if not self._dim_cols:
            return ""

        data = [self.df[col].dropna().values for col in self._dim_cols]
        labels = [c.replace("_score", "") for c in self._dim_cols]
        colors = [get_dimension_color(l) for l in labels]

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["boxplot"])
        bp = ax.boxplot(data, patch_artist=True, notch=False,
                        medianprops={"color": "black", "linewidth": 2})
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)

        ax.set_xticklabels(labels, fontsize=FONT_SIZES["tick_label"])
        ax.set_ylim(0, 1)
        ax.set_ylabel("Deprivation Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["dimension_boxplots"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.axhline(POVERTY_THRESHOLD_MODERATE, color="#E69F00",
                   linestyle="--", linewidth=1.2, alpha=0.8)
        ax.axhline(POVERTY_THRESHOLD_SEVERE, color="#D55E00",
                   linestyle="--", linewidth=1.2, alpha=0.8)
        fig.tight_layout()
        return self._save(fig, "dimension_boxplots.png")

    def generate_dimension_violin_plots(self) -> str:
        """Violin plots of dimension score distributions."""
        if not self._dim_cols:
            return ""

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["violin"])

        if _HAS_SEABORN:
            long_df = self.df[self._dim_cols].copy()
            long_df.columns = [c.replace("_score", "") for c in long_df.columns]
            melted = long_df.melt(var_name="Dimension", value_name="Score")
            palette = {d: get_dimension_color(d) for d in melted["Dimension"].unique()}
            sns.violinplot(data=melted, x="Dimension", y="Score",
                           hue="Dimension", palette=palette,
                           ax=ax, inner="box", linewidth=1.2, legend=False)
        else:
            data = [self.df[col].dropna().values for col in self._dim_cols]
            labels = [c.replace("_score", "") for c in self._dim_cols]
            ax.violinplot(data, showmedians=True)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels)

        ax.set_ylim(0, 1)
        ax.set_ylabel("Deprivation Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_xlabel("Dimension", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["dimension_violin_plots"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        fig.tight_layout()
        return self._save(fig, "dimension_violin_plots.png")

    # ==================================================================
    # REGIONAL ANALYSIS
    # ==================================================================

    def _regional_bar(self, zone_name: str, title: str, filename: str) -> str:
        """Generic regional bar chart helper."""
        zone_df = self._zone_df(zone_name)
        if zone_df.empty:
            logger.warning("No data for zone '%s'; generating placeholder.", zone_name)
            fig, ax = plt.subplots(figsize=FIGURE_SIZES["bar_chart_top10"])
            ax.text(0.5, 0.5, f"No data available for {zone_name.replace('_', ' ').title()} zone",
                    ha="center", va="center", fontsize=FONT_SIZES["axis_label"],
                    transform=ax.transAxes, color="#999999")
            ax.set_title(title, fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
            fig.tight_layout()
            return self._save(fig, filename)

        df = zone_df.sort_values("mepi_score", ascending=True)
        colors = map_poverty_colors(df["poverty_category"]) \
            if "poverty_category" in df.columns else ["#0072B2"] * len(df)

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["bar_chart_top10"])
        ax.barh(df[self._name_col], df["mepi_score"],
                color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xlim(0, 1)
        ax.set_xlabel("MEPI Score", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(title, fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.legend(handles=poverty_legend_patches(), loc="lower right",
                  framealpha=0.9, fontsize=FONT_SIZES["legend"])
        fig.tight_layout()
        return self._save(fig, filename)

    def generate_coastal_analysis(self) -> str:
        return self._regional_bar(
            "coastal", CHART_TITLES["coastal_analysis"], "coastal_analysis.png"
        )

    def generate_char_islands_analysis(self) -> str:
        return self._regional_bar(
            "char", CHART_TITLES["char_islands_analysis"], "char_islands_analysis.png"
        )

    def generate_haor_analysis(self) -> str:
        return self._regional_bar(
            "haor", CHART_TITLES["haor_analysis"], "haor_analysis.png"
        )

    def generate_hill_tract_analysis(self) -> str:
        return self._regional_bar(
            "hill_tract", CHART_TITLES["hill_tract_analysis"], "hill_tract_analysis.png"
        )

    def generate_sundarbans_analysis(self) -> str:
        return self._regional_bar(
            "sundarbans", CHART_TITLES["sundarbans_analysis"], "sundarbans_analysis.png"
        )

    def generate_urban_rural_comparison(self) -> str:
        """Grouped bar chart comparing urban vs rural MEPI scores."""
        fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["regional"])

        if "division" in self.df.columns:
            # Proxy: Dhaka/Chittagong divisions → urban; rest → rural
            urban_divisions = ["Dhaka", "Chittagong"]
            urban_mask = self.df["division"].isin(urban_divisions)
            urban_df = self.df[urban_mask]
            rural_df = self.df[~urban_mask]
        else:
            mid = len(self.df) // 2
            urban_df = self.df.iloc[:mid]
            rural_df = self.df.iloc[mid:]

        for ax, subset, label, color in zip(
            axes,
            [urban_df, rural_df],
            ["Urban Areas", "Rural Areas"],
            ["#0072B2", "#009E73"],
        ):
            if subset.empty:
                ax.text(0.5, 0.5, "No data", ha="center", va="center",
                        transform=ax.transAxes)
                ax.set_title(label)
                continue
            df_s = subset.sort_values("mepi_score", ascending=True)
            ax.barh(df_s[self._name_col], df_s["mepi_score"],
                    color=color, edgecolor="white", linewidth=0.4, alpha=0.85)
            ax.set_xlim(0, 1)
            ax.axvline(POVERTY_THRESHOLD_MODERATE, color="#E69F00",
                       linestyle="--", linewidth=1.0)
            ax.set_xlabel("MEPI Score", fontsize=FONT_SIZES["axis_label"])
            ax.set_title(label, fontsize=FONT_SIZES["subtitle"], fontweight="bold")
            mean_val = df_s["mepi_score"].mean()
            ax.axvline(mean_val, color="#CC0000", linestyle="-", linewidth=1.5,
                       label=f"Mean={mean_val:.3f}")
            ax.legend(fontsize=FONT_SIZES["small"])
            ax.tick_params(axis="y", labelsize=max(6, FONT_SIZES["tick_label"] - 2))

        fig.suptitle(CHART_TITLES["urban_rural_comparison"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", y=1.01)
        fig.tight_layout()
        return self._save(fig, "urban_rural_comparison.png")

    # ==================================================================
    # ADVANCED ANALYSIS
    # ==================================================================

    def generate_dimension_correlation_heatmap(self) -> str:
        """Correlation heatmap between all dimension scores."""
        if not self._dim_cols:
            return ""

        corr_data = self.df[self._dim_cols].copy()
        corr_data.columns = [c.replace("_score", "") for c in corr_data.columns]
        corr_matrix = corr_data.corr()

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["correlation"])

        if _HAS_SEABORN:
            mask = np.zeros_like(corr_matrix, dtype=bool)
            np.fill_diagonal(mask, True)
            sns.heatmap(
                corr_matrix,
                ax=ax,
                cmap=CORRELATION_CMAP,
                vmin=-1, vmax=1,
                center=0,
                annot=True,
                fmt=".2f",
                square=True,
                linewidths=0.5,
                mask=mask,
                cbar_kws={"label": "Pearson r"},
            )
        else:
            im = ax.imshow(corr_matrix.values, cmap=CORRELATION_CMAP,
                           vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr_matrix.columns)))
            ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr_matrix.index)))
            ax.set_yticklabels(corr_matrix.index)
            fig.colorbar(im, ax=ax, label="Pearson r")
            for i in range(len(corr_matrix)):
                for j in range(len(corr_matrix)):
                    if i != j:
                        ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}",
                                ha="center", va="center", fontsize=8)

        ax.set_title(CHART_TITLES["dimension_correlation_heatmap"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        fig.tight_layout()
        return self._save(fig, "dimension_correlation_heatmap.png")

    def generate_radar_profiles(self) -> str:
        """Radar charts for top 5 most-poor and top 5 least-poor upazilas."""
        if not self._dim_cols:
            return ""

        top5 = self._sorted_df(ascending=False).head(5)
        bot5 = self._sorted_df(ascending=True).head(5)

        dim_labels = [c.replace("_score", "") for c in self._dim_cols]
        N = len(dim_labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]

        fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["radar"],
                                 subplot_kw={"projection": "polar"})

        palettes = [
            ["#D55E00", "#E69F00", "#CC79A7", "#F0E442", "#56B4E9"],  # warm → most poor
            ["#009E73", "#0072B2", "#56B4E9", "#CC79A7", "#009E73"],  # cool → least poor
        ]

        for ax, subset, subtitle, palette in zip(
            axes,
            [top5, bot5],
            ["Top 5 Most Energy-Poor", "Top 5 Least Energy-Poor"],
            palettes,
        ):
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(dim_labels, size=FONT_SIZES["tick_label"])
            ax.set_ylim(0, 1)
            ax.set_yticks([0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"],
                               size=FONT_SIZES["small"])
            ax.set_title(subtitle, size=FONT_SIZES["subtitle"],
                         fontweight="bold", pad=20)

            for i, (_, row) in enumerate(subset.iterrows()):
                values = [row[col] for col in self._dim_cols]
                values += values[:1]
                color = palette[i % len(palette)]
                name = row[self._name_col] if self._name_col in row.index else f"UZ-{i}"
                ax.plot(angles, values, color=color, linewidth=1.8, label=name)
                ax.fill(angles, values, color=color, alpha=0.12)

            ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1),
                      fontsize=FONT_SIZES["small"])

        fig.suptitle(CHART_TITLES["radar_profiles"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", y=1.02)
        fig.tight_layout()
        return self._save(fig, "radar_profiles.png")

    def generate_dimension_contribution(self) -> str:
        """Stacked bar chart showing each dimension's contribution to MEPI score."""
        if not self._dim_cols:
            return ""

        df = self._sorted_df(ascending=False)
        dim_labels = [c.replace("_score", "") for c in self._dim_cols]
        colors = [get_dimension_color(d) for d in dim_labels]

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["stacked_bar"])
        names = df[self._name_col].tolist()
        x = np.arange(len(names))
        bottom = np.zeros(len(names))

        for col, label, color in zip(self._dim_cols, dim_labels, colors):
            # Contribution = dimension score × its weight (equal weights assumed = 0.2)
            contribution = df[col].values * 0.2
            ax.bar(x, contribution, bottom=bottom, label=label,
                   color=color, edgecolor="white", linewidth=0.3)
            bottom += contribution

        ax.plot(x, df["mepi_score"].values, "ko", markersize=3,
                label="MEPI Score", zorder=5)
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=90,
                           fontsize=max(6, FONT_SIZES["tick_label"] - 2))
        ax.set_ylim(0, 1)
        ax.set_ylabel("Score / Contribution", fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["dimension_contribution"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)
        ax.legend(loc="upper right", framealpha=0.9, fontsize=FONT_SIZES["legend"])
        fig.tight_layout()
        return self._save(fig, "dimension_contribution.png")

    def generate_spatial_distribution_map(self) -> str:
        """
        Scatter-plot spatial distribution of MEPI scores.

        Uses latitude/longitude if available; otherwise uses a structured
        grid layout positioned by division name for visual clarity.
        """
        has_coords = ("latitude" in self.df.columns and
                      "longitude" in self.df.columns)

        fig, ax = plt.subplots(figsize=FIGURE_SIZES["scatter_map"])

        if has_coords:
            x_vals = self.df["longitude"]
            y_vals = self.df["latitude"]
            xlabel = "Longitude"
            ylabel = "Latitude"
        else:
            # Create a structured pseudo-spatial layout
            n = len(self.df)
            cols_grid = max(1, int(np.ceil(np.sqrt(n))))
            x_vals = [i % cols_grid for i in range(n)]
            y_vals = [i // cols_grid for i in range(n)]
            xlabel = "Index (no coordinates available)"
            ylabel = "Index"

        scores = self.df["mepi_score"].values
        scatter = ax.scatter(
            x_vals, y_vals,
            c=scores,
            cmap=HEATMAP_CMAP,
            vmin=0, vmax=1,
            s=80,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.9,
        )
        cbar = fig.colorbar(scatter, ax=ax, label="MEPI Score")
        cbar.ax.tick_params(labelsize=FONT_SIZES["tick_label"])

        ax.set_xlabel(xlabel, fontsize=FONT_SIZES["axis_label"])
        ax.set_ylabel(ylabel, fontsize=FONT_SIZES["axis_label"])
        ax.set_title(CHART_TITLES["spatial_distribution_map"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", pad=12)

        if not has_coords:
            ax.text(0.02, 0.97,
                    "Note: Coordinates not available; positions are illustrative.",
                    transform=ax.transAxes, fontsize=FONT_SIZES["small"],
                    va="top", color="#555555",
                    bbox={"boxstyle": "round,pad=0.3", "fc": "wheat", "alpha": 0.5})

        fig.tight_layout()
        return self._save(fig, "spatial_distribution_map.png")

    # ==================================================================
    # SUMMARY DASHBOARDS
    # ==================================================================

    def generate_executive_summary(self) -> str:
        """One-page summary dashboard with key metrics and overview charts."""
        scores = self.df["mepi_score"].dropna()
        fig = plt.figure(figsize=FIGURE_SIZES["dashboard"])
        gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.4)

        # ── Title ─────────────────────────────────────────────────────
        fig.suptitle(CHART_TITLES["executive_summary"],
                     fontsize=FONT_SIZES["title"] + 4,
                     fontweight="bold", y=0.98)

        # ── 1. Key metrics panel ───────────────────────────────────────
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis("off")
        metrics = [
            ("Upazilas Analysed", str(len(self.df))),
            ("Mean MEPI", f"{scores.mean():.3f}"),
            ("Median MEPI", f"{scores.median():.3f}"),
            ("Std Dev", f"{scores.std():.3f}"),
            ("Min MEPI", f"{scores.min():.3f}"),
            ("Max MEPI", f"{scores.max():.3f}"),
        ]
        if "poverty_category" in self.df.columns:
            counts = self.df["poverty_category"].value_counts()
            for cat, label in [
                ("Non-Poor", "Non-Poor"),
                ("Moderately Poor", "Moderately Poor"),
                ("Severely Poor", "Severely Poor"),
            ]:
                n = counts.get(cat, 0)
                pct = 100 * n / len(self.df) if len(self.df) > 0 else 0
                metrics.append((label, f"{n} ({pct:.0f}%)"))

        x_step = 1.0 / len(metrics)
        for k, (label, value) in enumerate(metrics):
            xc = (k + 0.5) * x_step
            ax_kpi.text(xc, 0.70, value, ha="center", va="center",
                        fontsize=FONT_SIZES["subtitle"] + 2, fontweight="bold",
                        transform=ax_kpi.transAxes,
                        color="#0072B2")
            ax_kpi.text(xc, 0.25, label, ha="center", va="center",
                        fontsize=FONT_SIZES["small"],
                        transform=ax_kpi.transAxes, color="#555555")

        # ── 2. Bar chart (top 15 most poor) ───────────────────────────
        ax_bar = fig.add_subplot(gs[1, :2])
        df_top = self._sorted_df(ascending=False).head(15)
        colors = map_poverty_colors(df_top["poverty_category"]) \
            if "poverty_category" in df_top.columns else ["#D55E00"] * 15
        ax_bar.barh(df_top[self._name_col][::-1],
                    df_top["mepi_score"][::-1],
                    color=colors[::-1], edgecolor="white", linewidth=0.4)
        ax_bar.set_xlim(0, 1)
        ax_bar.set_xlabel("MEPI Score", fontsize=FONT_SIZES["small"])
        ax_bar.set_title("Most Energy-Poor Upazilas",
                         fontsize=FONT_SIZES["subtitle"], fontweight="bold")
        ax_bar.tick_params(axis="y", labelsize=FONT_SIZES["small"])

        # ── 3. Pie chart ───────────────────────────────────────────────
        ax_pie = fig.add_subplot(gs[1, 2])
        if "poverty_category" in self.df.columns:
            counts = self.df["poverty_category"].value_counts()
            labels_p = counts.index.tolist()
            pie_colors = [get_poverty_color(l) for l in labels_p]
            ax_pie.pie(counts.values, labels=labels_p, colors=pie_colors,
                       autopct="%1.0f%%", startangle=140,
                       textprops={"fontsize": FONT_SIZES["small"]},
                       wedgeprops={"edgecolor": "white", "linewidth": 1.5})
        ax_pie.set_title("Poverty Classification",
                         fontsize=FONT_SIZES["subtitle"], fontweight="bold")

        # ── 4. Distribution ────────────────────────────────────────────
        ax_hist = fig.add_subplot(gs[2, 0])
        ax_hist.hist(scores, bins=max(8, len(scores) // 4),
                     color="#0072B2", edgecolor="white", linewidth=0.5)
        ax_hist.set_xlabel("MEPI Score", fontsize=FONT_SIZES["small"])
        ax_hist.set_ylabel("Count", fontsize=FONT_SIZES["small"])
        ax_hist.set_title("Score Distribution",
                           fontsize=FONT_SIZES["subtitle"], fontweight="bold")

        # ── 5. Dimension box plots ─────────────────────────────────────
        ax_box = fig.add_subplot(gs[2, 1:])
        if self._dim_cols:
            data = [self.df[c].dropna().values for c in self._dim_cols]
            labels_b = [c.replace("_score", "") for c in self._dim_cols]
            colors_b = [get_dimension_color(l) for l in labels_b]
            bp = ax_box.boxplot(data, patch_artist=True,
                                medianprops={"color": "black", "linewidth": 1.5})
            for patch, color in zip(bp["boxes"], colors_b):
                patch.set_facecolor(color)
                patch.set_alpha(0.75)
            ax_box.set_xticklabels(labels_b, fontsize=FONT_SIZES["small"])
            ax_box.set_ylim(0, 1)
            ax_box.set_ylabel("Deprivation Score", fontsize=FONT_SIZES["small"])
            ax_box.set_title("Dimension Distributions",
                              fontsize=FONT_SIZES["subtitle"], fontweight="bold")

        return self._save(fig, "executive_summary.png")

    def generate_regional_summary(self) -> str:
        """Multi-panel chart summarising MEPI across geographic zones."""
        zones = list(self.geographic_zones.keys()) if self.geographic_zones else []

        if not zones:
            # Fallback: summarise by division if available
            if "division" in self.df.columns:
                zones_df = (
                    self.df.groupby("division")["mepi_score"]
                    .agg(["mean", "median", "std", "count"])
                    .reset_index()
                    .rename(columns={"division": "zone"})
                )
            else:
                fig, ax = plt.subplots(figsize=FIGURE_SIZES["regional"])
                ax.text(0.5, 0.5, "No regional data available",
                        ha="center", va="center", fontsize=FONT_SIZES["axis_label"],
                        transform=ax.transAxes, color="#999999")
                ax.set_title(CHART_TITLES["regional_summary"],
                             fontsize=FONT_SIZES["title"], fontweight="bold")
                fig.tight_layout()
                return self._save(fig, "regional_summary.png")
        else:
            rows = []
            for zone in zones:
                subset = self._zone_df(zone)
                if not subset.empty:
                    rows.append({
                        "zone": zone.replace("_", " ").title(),
                        "mean": subset["mepi_score"].mean(),
                        "median": subset["mepi_score"].median(),
                        "std": subset["mepi_score"].std(),
                        "count": len(subset),
                    })
            zones_df = pd.DataFrame(rows) if rows else pd.DataFrame()

        if zones_df.empty:
            fig, ax = plt.subplots(figsize=FIGURE_SIZES["regional"])
            ax.text(0.5, 0.5, "No data to display",
                    ha="center", va="center", transform=ax.transAxes)
            fig.tight_layout()
            return self._save(fig, "regional_summary.png")

        fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["regional_summary"])

        # Panel 1: Mean MEPI by region
        ax1 = axes[0]
        region_col = "zone" if "zone" in zones_df.columns else zones_df.columns[0]
        ax1.barh(zones_df[region_col], zones_df["mean"],
                 xerr=zones_df.get("std", None),
                 color="#0072B2", edgecolor="white", linewidth=0.5,
                 error_kw={"elinewidth": 1.2, "capsize": 4})
        ax1.set_xlim(0, 1)
        ax1.set_xlabel("Mean MEPI Score", fontsize=FONT_SIZES["axis_label"])
        ax1.set_title("Mean MEPI by Region",
                      fontsize=FONT_SIZES["subtitle"], fontweight="bold")
        ax1.axvline(POVERTY_THRESHOLD_MODERATE, color="#E69F00",
                    linestyle="--", linewidth=1.2)
        ax1.axvline(POVERTY_THRESHOLD_SEVERE, color="#D55E00",
                    linestyle="--", linewidth=1.2)

        # Panel 2: Sample count by region
        ax2 = axes[1]
        ax2.barh(zones_df[region_col], zones_df["count"],
                 color="#009E73", edgecolor="white", linewidth=0.5)
        ax2.set_xlabel("Number of Upazilas", fontsize=FONT_SIZES["axis_label"])
        ax2.set_title("Upazila Count by Region",
                      fontsize=FONT_SIZES["subtitle"], fontweight="bold")

        fig.suptitle(CHART_TITLES["regional_summary"],
                     fontsize=FONT_SIZES["title"], fontweight="bold", y=1.02)
        fig.tight_layout()
        return self._save(fig, "regional_summary.png")
