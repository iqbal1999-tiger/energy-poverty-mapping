"""
upazila_validator.py - Validate MEPI data against Bangladesh upazila shapefile

Checks:
  - All MEPI upazilas can be matched to the shapefile
  - All shapefile upazilas have a corresponding MEPI record
  - Coordinate validity
  - Name standardisation

Usage
-----
    from upazila_validator import UpazilaValidator
    validator = UpazilaValidator(mepi_df, shapefile_gdf, name_col="NAME_3")
    report = validator.validate()
    validator.print_report()
    merged = validator.merge()
"""

from __future__ import annotations

import re
import unicodedata
import warnings
from typing import Dict, List, Optional, Tuple

import pandas as pd

from bangladesh_coordinates import UpazilaDatabase, _normalise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_name(name: str) -> str:
    """Normalise a name: lowercase, remove accents, collapse whitespace."""
    return _normalise(str(name))


def _build_name_map(names: List[str]) -> Dict[str, str]:
    """Map normalised → original for a list of names."""
    return {_clean_name(n): n for n in names}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class UpazilaValidator:
    """
    Validate and reconcile MEPI data with shapefile upazila names.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results with at least an upazila name column.
    shapefile_gdf : GeoDataFrame or pd.DataFrame
        Shapefile data (or None to use coordinate database only).
    mepi_name_col : str
        Column in *mepi_df* containing upazila names.
    shapefile_name_col : str
        Column in *shapefile_gdf* containing upazila names.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        shapefile_gdf=None,
        mepi_name_col: str = "upazila_name",
        shapefile_name_col: Optional[str] = None,
    ):
        self.mepi_df = mepi_df.copy()
        self.shapefile_gdf = shapefile_gdf
        self.mepi_name_col = mepi_name_col
        self.shapefile_name_col = shapefile_name_col
        self._db = UpazilaDatabase()

        # Auto-detect shapefile name column if not provided
        if self.shapefile_gdf is not None and self.shapefile_name_col is None:
            from shapefile_loader import NAME_COLUMN_CANDIDATES, _find_column
            self.shapefile_name_col = _find_column(
                self.shapefile_gdf, NAME_COLUMN_CANDIDATES
            )
            if self.shapefile_name_col is None:
                warnings.warn(
                    "Could not auto-detect upazila name column in shapefile. "
                    "Set shapefile_name_col explicitly.",
                    UserWarning,
                    stacklevel=2,
                )

        self._report: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Core validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict:
        """
        Run all validation checks.

        Returns
        -------
        dict with keys:
          - mepi_count, shapefile_count
          - matched, unmatched_mepi, unmatched_shapefile
          - name_mapping (dict: MEPI name → shapefile name)
          - issues (list of strings)
        """
        mepi_names: List[str] = self.mepi_df[self.mepi_name_col].dropna().tolist()

        if self.shapefile_gdf is not None and self.shapefile_name_col:
            shp_names: List[str] = (
                self.shapefile_gdf[self.shapefile_name_col].dropna().tolist()
            )
        else:
            # Fall back to the built-in coordinate database
            shp_names = [r["name"] for r in self._db._df.to_dict("records")]

        shp_map = _build_name_map(shp_names)
        mepi_map = _build_name_map(mepi_names)

        matched: Dict[str, str] = {}        # MEPI name → shapefile name
        unmatched_mepi: List[str] = []      # MEPI names with no shapefile match
        unmatched_shp: List[str] = []       # Shapefile names with no MEPI match
        issues: List[str] = []

        # Match each MEPI name to a shapefile name
        for m_name in mepi_names:
            m_key = _clean_name(m_name)
            if m_key in shp_map:
                matched[m_name] = shp_map[m_key]
            else:
                # Fuzzy match via the database
                best = self._db.find_match(m_name)
                if best and _clean_name(best) in shp_map:
                    matched[m_name] = shp_map[_clean_name(best)]
                    issues.append(
                        f"Fuzzy match: MEPI '{m_name}' → shapefile '{shp_map[_clean_name(best)]}'"
                    )
                else:
                    # Try direct fuzzy on shapefile names
                    from difflib import get_close_matches
                    close = get_close_matches(m_key, shp_map.keys(), n=1, cutoff=0.7)
                    if close:
                        matched[m_name] = shp_map[close[0]]
                        issues.append(
                            f"Fuzzy match: MEPI '{m_name}' → shapefile '{shp_map[close[0]]}'"
                        )
                    else:
                        unmatched_mepi.append(m_name)

        # Shapefile names with no MEPI record
        matched_shp_keys = {_clean_name(v) for v in matched.values()}
        for s_name in shp_names:
            if _clean_name(s_name) not in matched_shp_keys:
                if _clean_name(s_name) not in mepi_map:
                    unmatched_shp.append(s_name)

        if unmatched_mepi:
            issues.append(
                f"{len(unmatched_mepi)} MEPI upazila(s) could not be matched to the shapefile."
            )
        if unmatched_shp:
            issues.append(
                f"{len(unmatched_shp)} shapefile upazila(s) have no MEPI record."
            )

        self._report = {
            "mepi_count": len(mepi_names),
            "shapefile_count": len(shp_names),
            "matched_count": len(matched),
            "unmatched_mepi": unmatched_mepi,
            "unmatched_shapefile": unmatched_shp,
            "name_mapping": matched,
            "issues": issues,
            "match_rate": (
                round(len(matched) / len(mepi_names) * 100, 1)
                if mepi_names else 0.0
            ),
        }
        return self._report

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    def merge(
        self,
        how: str = "left",
    ) -> pd.DataFrame:
        """
        Merge MEPI data with shapefile using the validated name mapping.

        Parameters
        ----------
        how : str
            Merge type: 'left', 'inner', or 'outer'.

        Returns
        -------
        pd.DataFrame (or GeoDataFrame if shapefile_gdf is a GeoDataFrame)
        """
        if self._report is None:
            self.validate()

        mapping = self._report["name_mapping"]  # type: ignore[index]

        # Add standardised name column to MEPI data
        mepi = self.mepi_df.copy()
        mepi["_shp_name"] = mepi[self.mepi_name_col].map(
            lambda n: mapping.get(n, n)
        )

        if self.shapefile_gdf is None or self.shapefile_name_col is None:
            return mepi

        shp = self.shapefile_gdf.copy()
        shp["_shp_name"] = shp[self.shapefile_name_col]

        merged = shp.merge(mepi, on="_shp_name", how=how)
        merged = merged.drop(columns=["_shp_name"], errors="ignore")
        return merged

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print the validation report to stdout."""
        if self._report is None:
            self.validate()
        r = self._report  # type: ignore[index]

        print("=" * 60)
        print("UPAZILA VALIDATION REPORT")
        print("=" * 60)
        print(f"  MEPI upazilas      : {r['mepi_count']}")
        print(f"  Shapefile upazilas : {r['shapefile_count']}")
        print(f"  Matched            : {r['matched_count']} ({r['match_rate']}%)")
        print(f"  Unmatched (MEPI)   : {len(r['unmatched_mepi'])}")
        print(f"  Unmatched (shapefile): {len(r['unmatched_shapefile'])}")

        if r["unmatched_mepi"]:
            print("\n  ⚠  MEPI names not found in shapefile:")
            for name in r["unmatched_mepi"][:20]:
                print(f"      - {name}")
            if len(r["unmatched_mepi"]) > 20:
                print(f"      ... and {len(r['unmatched_mepi']) - 20} more")

        if r["issues"]:
            print("\n  ℹ  Notes:")
            for issue in r["issues"][:10]:
                print(f"      - {issue}")

        status = "✅ All matched" if not r["unmatched_mepi"] else "⚠️  Some unmatched"
        print(f"\n  Status: {status}")
        print("=" * 60)

    def generate_mapping_dict(self) -> Dict[str, str]:
        """
        Return a dictionary mapping MEPI upazila names to shapefile names.

        Useful for manual correction of remaining mismatches.
        """
        if self._report is None:
            self.validate()
        return dict(self._report["name_mapping"])  # type: ignore[index]

    def export_report(self, output_path: str) -> None:
        """Save validation report as a CSV file."""
        if self._report is None:
            self.validate()
        r = self._report  # type: ignore[index]

        rows = []
        for mepi_name, shp_name in r["name_mapping"].items():
            rows.append({
                "mepi_name": mepi_name,
                "shapefile_name": shp_name,
                "status": "matched",
            })
        for name in r["unmatched_mepi"]:
            rows.append({
                "mepi_name": name,
                "shapefile_name": "",
                "status": "unmatched",
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        print(f"Validation report saved to: {output_path}")
