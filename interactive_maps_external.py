"""
interactive_maps_external.py - Generate interactive HTML maps to external folder

Creates Folium-based interactive maps and saves them to the external
``interactive_maps/`` subfolder.

Maps produced
-------------
  interactive_map.html            Main MEPI interactive map
  interactive_regional_map.html   Regional zone overlay map
  interactive_temporal_map.html   Temporal slider map (if multi-year data)
  README_interactive_maps.txt     Instructions for viewing the maps

Usage
-----
    python interactive_maps_external.py
    python interactive_maps_external.py --data path/to/mepi_results.csv
    python interactive_maps_external.py --output-dir /custom/path/
"""

from __future__ import annotations

import argparse
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from external_folder_manager import ensure_external_folders
from map_config_external import EXTERNAL_OUTPUT_BASE

warnings.filterwarnings("ignore", category=UserWarning)

# Bangladesh center coordinates
BANGLADESH_CENTER = [23.685, 90.356]

# Poverty colour thresholds
POVERTY_COLORS = {
    "Non-Poor":       "#2ecc71",
    "Moderately Poor":"#f39c12",
    "Severely Poor":  "#e74c3c",
}


def _classify(score: float) -> str:
    if score >= 0.66:
        return "Severely Poor"
    if score >= 0.33:
        return "Moderately Poor"
    return "Non-Poor"


# ---------------------------------------------------------------------------
# Interactive map generator
# ---------------------------------------------------------------------------

class InteractiveMapsExternal:
    """
    Generate Folium interactive HTML maps saved to external ``interactive_maps/``.

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
        return self._mgr.get_path("interactive_maps", filename)

    # ------------------------------------------------------------------
    # Main interactive map
    # ------------------------------------------------------------------

    def create_interactive_map(self) -> Optional[str]:
        """Create the main MEPI choropleth / marker interactive map."""
        filename = "interactive_map.html"
        try:
            import folium
            from folium.plugins import MarkerCluster

            m = folium.Map(
                location=BANGLADESH_CENTER,
                zoom_start=7,
                tiles="OpenStreetMap",
            )

            cluster = MarkerCluster(name="Upazilas").add_to(m)

            valid = self.df.dropna(subset=["lat", "lon", "mepi_score"])
            for _, row in valid.iterrows():
                category = _classify(row["mepi_score"])
                color = POVERTY_COLORS.get(category, "#3498db")

                popup_lines = [
                    f"<b>{row.get('upazila_name', 'Unknown')}</b>",
                    f"MEPI: {row['mepi_score']:.3f}",
                    f"Category: {category}",
                ]
                dim_cols = [c for c in valid.columns if c.endswith("_score") and c != "mepi_score"]
                for col in dim_cols:
                    dim_name = col.replace("_score", "").capitalize()
                    popup_lines.append(f"{dim_name}: {row[col]:.3f}")
                if "division" in row.index:
                    popup_lines.append(f"Division: {row['division']}")
                if "district" in row.index:
                    popup_lines.append(f"District: {row['district']}")

                popup_html = "<br>".join(popup_lines)

                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=f"{row.get('upazila_name', '')}: {row['mepi_score']:.3f}",
                ).add_to(cluster)

            # Legend
            legend_html = """
            <div style="position:fixed; bottom:50px; left:50px; background:white;
                        padding:12px; border:2px solid grey; border-radius:8px;
                        z-index:9999; font-size:13px;">
              <b>Energy Poverty Level</b><br>
              <span style="color:#2ecc71;">●</span> Non-Poor (&lt;0.33)<br>
              <span style="color:#f39c12;">●</span> Moderately Poor (0.33–0.66)<br>
              <span style="color:#e74c3c;">●</span> Severely Poor (&gt;0.66)
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            path = self._out(filename)
            m.save(path)
            print(f"  Saved: {path}")
            return path

        except ImportError:
            warnings.warn("folium not installed; interactive_map.html skipped.", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)

        return None

    # ------------------------------------------------------------------
    # Regional interactive map
    # ------------------------------------------------------------------

    def create_interactive_regional_map(self) -> Optional[str]:
        """Create a regional zone overlay interactive map."""
        filename = "interactive_regional_map.html"

        # District-to-zone mapping for filtering
        _ZONE_DISTRICTS = {
            "Coastal":      ["cox's bazar", "chittagong", "feni", "noakhali", "lakshmipur",
                             "chandpur", "barisal", "patuakhali", "bhola", "barguna",
                             "pirojpur", "jhalokati"],
            "Char Islands": ["bhola", "noakhali", "lakshmipur", "chandpur", "shariatpur",
                             "madaripur"],
            "Haor Wetlands":["sunamganj", "sylhet", "moulvibazar", "habiganj",
                             "kishoreganj", "netrokona", "mymensingh"],
            "Hill Tracts":  ["rangamati", "khagrachhari", "bandarban"],
            "Sundarbans":   ["satkhira", "khulna", "bagerhat"],
        }

        try:
            import folium

            m = folium.Map(
                location=BANGLADESH_CENTER,
                zoom_start=7,
                tiles="CartoDB positron",
            )

            zone_colors = {
                "Coastal":      "#2196F3",
                "Char Islands": "#FF9800",
                "Haor Wetlands":"#4CAF50",
                "Hill Tracts":  "#795548",
                "Sundarbans":   "#009688",
            }

            valid = self.df.dropna(subset=["lat", "lon", "mepi_score"])

            for zone_name, color in zone_colors.items():
                layer = folium.FeatureGroup(name=zone_name, show=True)

                # Filter to zone districts if district column is available
                districts = [d.lower() for d in _ZONE_DISTRICTS.get(zone_name, [])]
                if "district" in valid.columns and districts:
                    subset = valid[valid["district"].fillna("").str.lower().isin(districts)]
                else:
                    # Fallback: show a representative sample from all upazilas
                    subset = valid.iloc[::max(1, len(valid) // 10)]  # every Nth row

                for _, row in subset.iterrows():
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=5,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.6,
                        tooltip=(
                            f"{row.get('upazila_name', '')} [{zone_name}]"
                            f" – MEPI: {row['mepi_score']:.3f}"
                        ),
                    ).add_to(layer)
                layer.add_to(m)

            folium.LayerControl().add_to(m)

            path = self._out(filename)
            m.save(path)
            print(f"  Saved: {path}")
            return path

        except ImportError:
            warnings.warn("folium not installed; interactive_regional_map.html skipped.", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)

        return None

    # ------------------------------------------------------------------
    # Temporal interactive map (simple layer toggle)
    # ------------------------------------------------------------------

    def create_interactive_temporal_map(
        self,
        yearly_data: Optional[Dict[Union[int, str], pd.DataFrame]] = None,
    ) -> Optional[str]:
        """Create a temporal layer-toggle interactive map."""
        filename = "interactive_temporal_map.html"
        try:
            import folium

            m = folium.Map(
                location=BANGLADESH_CENTER,
                zoom_start=7,
                tiles="CartoDB positron",
            )

            datasets: Dict[Union[int, str], pd.DataFrame]
            if yearly_data:
                datasets = yearly_data
            else:
                datasets = {"Current": self.df}

            cmap_steps = ["#2ecc71", "#f39c12", "#e74c3c"]

            for year, df in datasets.items():
                layer_df = _attach_coords(df).dropna(subset=["lat", "lon", "mepi_score"])
                layer = folium.FeatureGroup(name=str(year), show=(year == list(datasets.keys())[-1]))
                for _, row in layer_df.iterrows():
                    score = row["mepi_score"]
                    if score >= 0.66:
                        color = "#e74c3c"
                    elif score >= 0.33:
                        color = "#f39c12"
                    else:
                        color = "#2ecc71"
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=5,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.75,
                        tooltip=f"{row.get('upazila_name', '')} – MEPI: {score:.3f}",
                    ).add_to(layer)
                layer.add_to(m)

            folium.LayerControl().add_to(m)

            path = self._out(filename)
            m.save(path)
            print(f"  Saved: {path}")
            return path

        except ImportError:
            warnings.warn("folium not installed; interactive_temporal_map.html skipped.", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"{filename} failed: {exc}", stacklevel=2)

        return None

    # ------------------------------------------------------------------
    # README for interactive maps
    # ------------------------------------------------------------------

    def create_readme(self) -> str:
        """Write README_interactive_maps.txt with viewing instructions."""
        filename = "README_interactive_maps.txt"
        path = self._out(filename)
        lines = [
            "=" * 60,
            "INTERACTIVE MAPS – VIEWING INSTRUCTIONS",
            "=" * 60,
            "",
            "Files in this folder:",
            "  interactive_map.html         – Main MEPI marker map",
            "  interactive_regional_map.html – Regional zone overlay",
            "  interactive_temporal_map.html – Temporal comparison layers",
            "",
            "How to view:",
            "  1. Open any .html file in a web browser (Chrome, Firefox, Edge).",
            "  2. The map will load automatically from OpenStreetMap tiles.",
            "  3. Click any upazila marker to see its MEPI score and details.",
            "  4. Use the layer toggle (top right) to switch between zones/years.",
            "",
            "Legend – Energy Poverty Levels:",
            "  Green  (●) – Non-Poor           (MEPI < 0.33)",
            "  Amber  (●) – Moderately Poor    (0.33 ≤ MEPI < 0.66)",
            "  Red    (●) – Severely Poor      (MEPI ≥ 0.66)",
            "",
            "Notes:",
            "  * An internet connection is required to load map tiles.",
            "  * If tiles do not appear, try a different browser.",
            "  * Data reflects Bangladesh upazila-level energy poverty.",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "Bangladesh Energy Poverty Mapping Project",
        ]
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        print(f"  Saved: {path}")
        return path

    # ------------------------------------------------------------------
    # Master method
    # ------------------------------------------------------------------

    def create_all_maps(self) -> List[str]:
        """Create all interactive maps and return list of saved paths."""
        saved: List[str] = []

        print("  Creating interactive_map.html ...")
        p = self.create_interactive_map()
        if p:
            saved.append(p)

        print("  Creating interactive_regional_map.html ...")
        p = self.create_interactive_regional_map()
        if p:
            saved.append(p)

        print("  Creating interactive_temporal_map.html ...")
        p = self.create_interactive_temporal_map()
        if p:
            saved.append(p)

        print("  Creating README_interactive_maps.txt ...")
        saved.append(self.create_readme())

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
        description="Generate interactive HTML maps to external folder."
    )
    parser.add_argument("--data", default="", help="Path to MEPI results CSV.")
    parser.add_argument(
        "--output-dir", default=EXTERNAL_OUTPUT_BASE,
        help=f"External output base directory (default: {EXTERNAL_OUTPUT_BASE}).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("INTERACTIVE MAPS – EXTERNAL FOLDER")
    print("=" * 60)

    results = _load_data(args.data)
    mapper = InteractiveMapsExternal(results, base_dir=args.output_dir)
    saved = mapper.create_all_maps()

    print(f"\n✅ {len(saved)} interactive map file(s) saved to:")
    print(f"   {mapper._mgr.get_subfolder('interactive_maps')}")
    print("\nOpen any .html file in a web browser to view.")


if __name__ == "__main__":
    main()
