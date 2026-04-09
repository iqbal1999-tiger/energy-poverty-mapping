"""
statistical_analysis.py - Statistical analysis for MEPI results

Provides:
  - Descriptive statistics (mean, median, std, quartiles)
  - Correlation analysis between dimensions
  - Vulnerability assessment
  - Dimension contribution analysis
  - Inequality measures (Gini coefficient, Theil index)
  - Summary tables suitable for reporting

Usage:
    from statistical_analysis import StatisticalAnalyzer
    sa = StatisticalAnalyzer(results_df)
    print(sa.descriptive_statistics())
    print(sa.correlation_matrix())
    print(sa.gini_coefficient())
"""

import warnings

import numpy as np
import pandas as pd

from config import DIMENSIONS


class StatisticalAnalyzer:
    """
    Statistical analysis of MEPI results.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of ``MEPICalculator.calculate()``.
    """

    def __init__(self, results_df: pd.DataFrame):
        self.df = results_df.copy()
        self._dim_score_cols = [
            f"{d}_score" for d in DIMENSIONS if f"{d}_score" in self.df.columns
        ]
        self._dim_labels = [c.replace("_score", "") for c in self._dim_score_cols]

    # ------------------------------------------------------------------
    # 1. Descriptive statistics
    # ------------------------------------------------------------------

    def descriptive_statistics(self, include_dimensions: bool = True) -> pd.DataFrame:
        """
        Compute descriptive statistics for MEPI scores (and dimension scores).

        Parameters
        ----------
        include_dimensions : bool, optional
            If True, include dimension-level statistics.  Default: True.

        Returns
        -------
        pd.DataFrame
            Columns: count, mean, std, min, 25%, 50%, 75%, max for each score column.
        """
        cols = ["mepi_score"]
        if include_dimensions:
            cols += self._dim_score_cols

        desc = self.df[cols].describe().T
        desc.index = [
            c.replace("_score", "").replace("mepi", "MEPI") for c in desc.index
        ]
        desc = desc.round(4)
        return desc

    # ------------------------------------------------------------------
    # 2. Correlation analysis
    # ------------------------------------------------------------------

    def correlation_matrix(self, method: str = "pearson") -> pd.DataFrame:
        """
        Compute pairwise correlations between MEPI and dimension scores.

        Parameters
        ----------
        method : str, optional
            Correlation method: ``"pearson"`` (default), ``"spearman"``, or ``"kendall"``.

        Returns
        -------
        pd.DataFrame
            Correlation matrix (dimensions × dimensions + MEPI).
        """
        cols = ["mepi_score"] + self._dim_score_cols
        corr = self.df[cols].corr(method=method).round(4)
        labels = ["MEPI"] + self._dim_labels
        corr.index = labels
        corr.columns = labels
        return corr

    def plot_correlation_heatmap(
        self,
        method: str = "pearson",
        figsize: tuple = (8, 7),
        title: str = "Dimension Correlation Matrix",
    ):
        """
        Plot the correlation matrix as a heatmap.

        Returns
        -------
        matplotlib.figure.Figure
        """
        import matplotlib.pyplot as plt

        corr = self.correlation_matrix(method=method)

        fig, ax = plt.subplots(figsize=figsize)
        try:
            import seaborn as sns
            mask = np.zeros_like(corr.values, dtype=bool)
            np.fill_diagonal(mask, True)
            sns.heatmap(
                corr,
                ax=ax,
                cmap="RdBu_r",
                vmin=-1,
                vmax=1,
                annot=True,
                fmt=".2f",
                linewidths=0.5,
                mask=mask,
                cbar_kws={"label": f"{method.capitalize()} r"},
            )
        except ImportError:
            im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
            ax.set_xticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr.index)))
            ax.set_yticklabels(corr.index)
            fig.colorbar(im, ax=ax, label=f"{method.capitalize()} r")

        ax.set_title(title, fontweight="bold")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 3. Vulnerability assessment
    # ------------------------------------------------------------------

    def vulnerability_assessment(
        self,
        deprivation_threshold: float = 0.33,
    ) -> pd.DataFrame:
        """
        Classify upazilas by multi-dimensional vulnerability.

        An upazila is *vulnerable* in a dimension if its score exceeds
        ``deprivation_threshold``.  This method summarises how many dimensions
        each upazila is deprived in and assigns a vulnerability class.

        Vulnerability classes:
          - ``"Low"``      – 0 dimensions deprived
          - ``"Moderate"`` – 1–2 dimensions deprived
          - ``"High"``     – 3–4 dimensions deprived
          - ``"Extreme"``  – 5 dimensions deprived

        Parameters
        ----------
        deprivation_threshold : float, optional
            Score above which a dimension is considered deprived.  Default: 0.33.

        Returns
        -------
        pd.DataFrame
            Original data with added columns ``n_deprived_dims`` and
            ``vulnerability_class``.
        """
        df = self.df.copy()
        dep_flags = df[self._dim_score_cols] > deprivation_threshold
        df["n_deprived_dims"] = dep_flags.sum(axis=1)

        def _classify(n: int) -> str:
            if n == 0:
                return "Low"
            elif n <= 2:
                return "Moderate"
            elif n <= 4:
                return "High"
            return "Extreme"

        df["vulnerability_class"] = df["n_deprived_dims"].apply(_classify)

        name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]
        keep = [name_col, "mepi_score", "n_deprived_dims", "vulnerability_class"] + self._dim_score_cols
        keep = [c for c in keep if c in df.columns]
        return df[keep].sort_values("n_deprived_dims", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 4. Dimension contribution analysis
    # ------------------------------------------------------------------

    def dimension_contribution(self, weights: dict = None) -> pd.DataFrame:
        """
        Analyse which dimensions contribute most to overall energy poverty.

        Parameters
        ----------
        weights : dict, optional
            Mapping of {dimension: weight}.  If None, equal weights (0.2) are used.

        Returns
        -------
        pd.DataFrame
            Columns: Dimension, MeanScore, Weight, WeightedContribution, ContributionShare (%).
        """
        if weights is None:
            equal_w = 1 / len(self._dim_score_cols) if self._dim_score_cols else 0.2
            weights = {d: equal_w for d in self._dim_labels}

        rows = []
        for dim, col in zip(self._dim_labels, self._dim_score_cols):
            mean_score = self.df[col].mean()
            weight = weights.get(dim, 0.0)
            weighted_contrib = mean_score * weight
            rows.append(
                {
                    "Dimension": dim,
                    "Mean Score": round(mean_score, 4),
                    "Weight": weight,
                    "Weighted Contribution": round(weighted_contrib, 4),
                }
            )

        result = pd.DataFrame(rows)
        total = result["Weighted Contribution"].sum()
        result["Contribution Share (%)"] = (
            result["Weighted Contribution"] / total * 100
        ).round(2) if total > 0 else 0.0
        return result.sort_values("Contribution Share (%)", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 5. Inequality measures
    # ------------------------------------------------------------------

    def gini_coefficient(self, column: str = "mepi_score") -> float:
        """
        Calculate the Gini coefficient for MEPI or dimension scores.

        The Gini coefficient measures inequality in energy poverty scores
        across upazilas.  A value of 0 means perfect equality; 1 means
        maximum inequality.

        Parameters
        ----------
        column : str, optional
            Column to compute the Gini coefficient for.  Default: ``"mepi_score"``.

        Returns
        -------
        float
            Gini coefficient in [0, 1].
        """
        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found.")

        values = self.df[column].dropna().values
        if len(values) == 0:
            return float("nan")

        values = np.sort(values)
        n = len(values)
        cumulative = np.cumsum(values)
        # Gini = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1) / n
        numerator = 2 * np.sum((np.arange(1, n + 1)) * values)
        denominator = n * cumulative[-1]
        if denominator == 0:
            return 0.0
        return round(numerator / denominator - (n + 1) / n, 4)

    def theil_index(self, column: str = "mepi_score") -> float:
        """
        Calculate the Theil T index (GE(1)) for a score column.

        The Theil index is another inequality measure; higher values indicate
        greater inequality across upazilas.

        Parameters
        ----------
        column : str, optional
            Column to compute.  Default: ``"mepi_score"``.

        Returns
        -------
        float
            Theil T index.
        """
        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found.")

        values = self.df[column].dropna().values
        values = values[values > 0]  # Theil requires strictly positive values
        if len(values) == 0:
            warnings.warn("No positive values; cannot compute Theil index.", UserWarning, stacklevel=2)
            return float("nan")

        mu = values.mean()
        theil = np.mean((values / mu) * np.log(values / mu))
        return round(theil, 4)

    def inequality_summary(self) -> pd.DataFrame:
        """
        Summarise inequality measures for MEPI and each dimension.

        Returns
        -------
        pd.DataFrame
            Columns: Score, Gini, Theil.
        """
        cols = ["mepi_score"] + self._dim_score_cols
        labels = ["MEPI"] + self._dim_labels

        rows = []
        for label, col in zip(labels, cols):
            try:
                gini = self.gini_coefficient(col)
            except Exception:
                gini = float("nan")
            try:
                theil = self.theil_index(col)
            except Exception:
                theil = float("nan")
            rows.append({"Score": label, "Gini": gini, "Theil T": theil})

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 6. Summary report
    # ------------------------------------------------------------------

    def print_report(self):
        """Print a comprehensive statistical summary to the console."""
        print("=" * 65)
        print("MEPI STATISTICAL ANALYSIS REPORT")
        print("=" * 65)

        print("\n── Descriptive Statistics ──")
        print(self.descriptive_statistics().to_string())

        print("\n── Dimension Contribution Analysis ──")
        print(self.dimension_contribution().to_string(index=False))

        print("\n── Inequality Measures ──")
        print(self.inequality_summary().to_string(index=False))

        print("\n── Vulnerability Assessment (summary) ──")
        vuln = self.vulnerability_assessment()
        if "vulnerability_class" in vuln.columns:
            vc = vuln["vulnerability_class"].value_counts()
            for cls, n in vc.items():
                pct = round(n / len(vuln) * 100, 1)
                print(f"  {cls:<10}: {n:>4} upazilas ({pct}%)")

        print("\n── Correlation Matrix (Pearson) ──")
        print(self.correlation_matrix().to_string())

        print("=" * 65)
