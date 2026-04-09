"""
mepi_calculator.py - Core engine for Multidimensional Energy Poverty Index (MEPI) calculation

This module implements the full MEPI methodology:
  1. Normalise each indicator to a deprivation score in [0, 1].
  2. Average indicators within each dimension → dimension score.
  3. Take weighted average of dimension scores → MEPI score.
  4. Classify upazilas into poverty categories based on configurable thresholds.

Usage:
    from mepi_calculator import MEPICalculator
    calc = MEPICalculator()
    results = calc.calculate(df)
"""

import numpy as np
import pandas as pd

from config import (
    DIMENSION_INDICATORS,
    DEFAULT_WEIGHTS,
    POVERTY_THRESHOLDS,
    POVERTY_LABELS,
    DIMENSION_DEPRIVATION_THRESHOLD,
    UPAZILA_ID_COLUMN,
    UPAZILA_NAME_COLUMN,
    DISTRICT_COLUMN,
    DIVISION_COLUMN,
)


class MEPICalculator:
    """
    Calculate the Multidimensional Energy Poverty Index (MEPI).

    Parameters
    ----------
    weights : dict, optional
        Mapping of {dimension_name: weight}.  Weights must sum to 1.
        Defaults to equal weights (0.2 each) from config.DEFAULT_WEIGHTS.
    deprivation_threshold : float, optional
        Dimension-level score above which a household/upazila is considered
        deprived in that dimension.  Default: 0.33.
    poverty_thresholds : dict, optional
        Override the poverty classification thresholds from config.

    Examples
    --------
    >>> calc = MEPICalculator()
    >>> results = calc.calculate(df)
    >>> print(results[["upazila_name", "mepi_score", "poverty_category"]])
    """

    def __init__(
        self,
        weights=None,
        deprivation_threshold=None,
        poverty_thresholds=None,
    ):
        self.weights = weights or DEFAULT_WEIGHTS
        self.deprivation_threshold = (
            deprivation_threshold
            if deprivation_threshold is not None
            else DIMENSION_DEPRIVATION_THRESHOLD
        )
        self.poverty_thresholds = poverty_thresholds or POVERTY_THRESHOLDS
        self._validate_weights()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full MEPI pipeline on a DataFrame of upazila indicators.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain the indicator columns defined in config.DIMENSION_INDICATORS.
            Administrative columns (upazila_id, upazila_name, district, division)
            are preserved in the output if present.

        Returns
        -------
        pd.DataFrame
            Original columns plus:
              - ``<Dimension>_score``  for each dimension (0–1, higher = more deprived)
              - ``mepi_score``          overall MEPI score (0–1)
              - ``poverty_category``    text classification
              - ``n_dimensions_deprived``  count of dimensions above threshold
        """
        result = df.copy()

        # Step 1 – normalise indicators and compute dimension scores
        for dimension, indicators in DIMENSION_INDICATORS.items():
            dep_scores = self._normalise_dimension(result, dimension, indicators)
            result[f"{dimension}_score"] = dep_scores.mean(axis=1)

        # Step 2 – weighted MEPI score
        dimension_names = list(DIMENSION_INDICATORS.keys())
        score_cols = [f"{d}_score" for d in dimension_names]
        weight_array = np.array([self.weights[d] for d in dimension_names])
        result["mepi_score"] = result[score_cols].values @ weight_array

        # Step 3 – classify poverty level
        result["poverty_category"] = result["mepi_score"].apply(
            self._classify_poverty
        )

        # Step 4 – count dimensions in which the upazila is deprived
        result["n_dimensions_deprived"] = (
            result[score_cols] > self.deprivation_threshold
        ).sum(axis=1)

        return result

    def calculate_with_sensitivity(
        self, df: pd.DataFrame, weight_schemes: list
    ) -> dict:
        """
        Run MEPI with multiple weight schemes and return all results.

        Parameters
        ----------
        df : pd.DataFrame
            Input data (same format as ``calculate``).
        weight_schemes : list of dict
            Each dict must map dimension names to weights summing to 1.
            Example: [{"Availability": 0.3, "Reliability": 0.2, ...}, ...]

        Returns
        -------
        dict
            Keys are integer indices (0, 1, …); values are DataFrames
            with MEPI results for the corresponding weight scheme.
        """
        results = {}
        original_weights = self.weights
        for i, scheme in enumerate(weight_schemes):
            self.weights = scheme
            self._validate_weights()
            results[i] = self.calculate(df)
        self.weights = original_weights  # restore
        self._validate_weights()
        return results

    def get_dimension_scores(self, result_df: pd.DataFrame) -> pd.DataFrame:
        """Return only the dimension-score columns from a results DataFrame."""
        score_cols = [f"{d}_score" for d in DIMENSION_INDICATORS]
        admin_cols = [
            c
            for c in [
                UPAZILA_ID_COLUMN,
                UPAZILA_NAME_COLUMN,
                DISTRICT_COLUMN,
                DIVISION_COLUMN,
            ]
            if c in result_df.columns
        ]
        return result_df[admin_cols + score_cols].copy()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalise_dimension(
        self, df: pd.DataFrame, dimension: str, indicators: list
    ) -> pd.DataFrame:
        """
        Normalise each indicator in a dimension to a deprivation score [0, 1].

        For indicators where *higher raw value = more deprived*:
            deprivation = (value - min) / (max - min)

        For indicators where *lower raw value = more deprived* (i.e. higher is better):
            deprivation = (max - value) / (max - min)

        Returns a DataFrame with one normalised column per indicator.
        """
        normed = pd.DataFrame(index=df.index)
        for ind in indicators:
            col = ind["column"]
            higher_is_deprived = ind["higher_is_deprived"]

            series = df[col].astype(float)
            col_min = series.min()
            col_max = series.max()

            # Avoid division by zero when all values are identical
            if col_max == col_min:
                normed[col] = 0.0
            elif higher_is_deprived:
                normed[col] = (series - col_min) / (col_max - col_min)
            else:
                normed[col] = (col_max - series) / (col_max - col_min)

        return normed

    def _classify_poverty(self, score: float) -> str:
        """Map a continuous MEPI score to a categorical poverty label."""
        for category, (low, high) in self.poverty_thresholds.items():
            if low <= score <= high:
                return POVERTY_LABELS[category]
        # Edge case: score exactly at upper boundary of last threshold
        return POVERTY_LABELS["severe"]

    def _validate_weights(self):
        """Raise ValueError if weights are invalid."""
        total = sum(self.weights.values())
        if not np.isclose(total, 1.0, atol=1e-6):
            raise ValueError(
                f"Dimension weights must sum to 1.0, but they sum to {total:.6f}."
            )
        missing = set(DIMENSION_INDICATORS.keys()) - set(self.weights.keys())
        if missing:
            raise ValueError(
                f"Weights are missing for dimension(s): {missing}."
            )
