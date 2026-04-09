"""
interactive_folium_maps.py - Interactive HTML maps for Bangladesh MEPI

Creates Folium-based interactive maps with:
  - Upazila choropleth from shapefile (or centroid markers as fallback)
  - Popup details: upazila name, MEPI score, poverty class, dimension scores
  - Color-coded tiles by poverty intensity
  - Layer controls for different dimensions
  - Satellite / street map basemap options
  - Zoom bounds set to Bangladesh

Usage
-----
    from interactive_folium_maps import InteractiveMapper
    mapper = InteractiveMapper(mepi_df)
    mapper.create_mepi_map("map_outputs/interactive_map.html")
    mapper.create_dimension_maps("map_outputs/")
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import folium
    from folium import plugins as folium_plugins
    _HAS_FOLIUM = True
except ImportError:
    _HAS_FOLIUM = False

try:
    import branca.colormap as bcm
    _HAS_BRANCA = True
except ImportError:
    _HAS_BRANCA = False

from bangladesh_coordinates import (
    BANGLADESH_CENTER,
    BANGLADESH_BOUNDS,
    UpazilaDatabase,
    get_database,
)
from config import DIMENSIONS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POVERTY_COLORS = {
    "Non-Poor":          "#2ecc71",
    "Moderately Poor":   "#f39c12",
    "Severely Poor":     "#e74c3c",
}

DIMENSION_PALETTE = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]

BASEMAP_TILES = {
    "CartoDB Positron": "CartoDB positron",
    "OpenStreetMap":    "OpenStreetMap",
    "CartoDB Dark":     "CartoDB dark_matter",
}

OUTPUT_DIR = "map_outputs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_folium() -> None:
    if not _HAS_FOLIUM:
        raise ImportError(
            "folium is required for interactive maps: pip install folium"
        )


def _score_to_color(score: float) -> str:
    """Map a 0–1 score to an HTML colour string (green → red)."""
    if np.isnan(score):
        return "#cccccc"
    r = int(min(255, score * 2 * 255))
    g = int(min(255, (1 - score) * 2 * 255))
    return f"#{r:02x}{g:02x}00"


def _poverty_color(mepi_score: float) -> str:
    if np.isnan(mepi_score):
        return "#cccccc"
    if mepi_score < 0.33:
        return POVERTY_COLORS["Non-Poor"]
    elif mepi_score < 0.66:
        return POVERTY_COLORS["Moderately Poor"]
    else:
        return POVERTY_COLORS["Severely Poor"]


def _build_popup_html(row: pd.Series, dimension_cols: List[str]) -> str:
    """Build an HTML popup string for a given upazila row."""
    name = row.get("upazila_name", row.get("NAME_3", row.get("NAME_2", "Unknown")))
    district = row.get("district", "–")
    division = row.get("division", "–")
    score = row.get("mepi_score", np.nan)
    cat = row.get("poverty_category", "–")

    score_str = f"{score:.3f}" if not (isinstance(score, float) and np.isnan(score)) else "N/A"

    dim_rows = ""
    for col in dimension_cols:
        dim_name = col.replace("_score", "").capitalize()
        val = row.get(col, np.nan)
        val_str = f"{val:.3f}" if not (isinstance(val, float) and np.isnan(val)) else "N/A"
        bar_width = int(float(val) * 100) if not (isinstance(val, float) and np.isnan(val)) else 0
        dim_rows += (
            f"<tr><td style='padding:2px 6px'>{dim_name}</td>"
            f"<td style='padding:2px 6px'>{val_str}</td>"
            f"<td style='padding:2px'><div style='background:#e74c3c;width:{bar_width}px;height:8px'></div></td></tr>"
        )

    html = f"""
    <div style='font-family:Arial,sans-serif;font-size:13px;min-width:220px'>
        <b style='font-size:15px'>{name}</b><br>
        <span style='color:#555'>{district}, {division}</span>
        <hr style='margin:6px 0'>
        <table style='width:100%;border-collapse:collapse'>
            <tr><td><b>MEPI Score</b></td>
                <td><b style='color:{_poverty_color(float(score) if score != 'N/A' else np.nan)}'>{score_str}</b></td></tr>
            <tr><td>Category</td><td>{cat}</td></tr>
        </table>
        <hr style='margin:6px 0'>
        <b>Dimension Scores:</b>
        <table style='width:100%;border-collapse:collapse'>
            {dim_rows}
        </table>
    </div>
    """
    return html


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class InteractiveMapper:
    """
    Create interactive Folium HTML maps of Bangladesh MEPI.

    Parameters
    ----------
    mepi_df : pd.DataFrame
        MEPI results (output of MEPICalculator.calculate()).
    shapefile_path : str, optional
        Path to Bangladesh upazila shapefile.  Auto-detected if not given.
    name_col : str
        Column in *mepi_df* containing upazila names.
    """

    def __init__(
        self,
        mepi_df: pd.DataFrame,
        shapefile_path: Optional[str] = None,
        name_col: str = "upazila_name",
    ):
        _require_folium()
        self.df = mepi_df.copy()
        self.name_col = name_col
        self._db = get_database()
        self._geojson: Optional[Dict] = None
        self._shp_name_col: Optional[str] = None

        # Load shapefile / GeoJSON
        self._try_load_shapefile(shapefile_path)
        # Attach centroid coordinates
        self._attach_coordinates()
        # Determine dimension score columns
        self._dim_cols = [
            f"{d}_score"
            for d in DIMENSIONS
            if f"{d}_score" in self.df.columns
        ]

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _try_load_shapefile(self, path: Optional[str]) -> None:
        try:
            import geopandas as gpd
        except ImportError:
            warnings.warn(
                "geopandas not installed.  Falling back to marker-based maps.",
                UserWarning, stacklevel=3,
            )
            return

        from shapefile_loader import ShapefileLoader, find_shapefile

        if path is None:
            path = find_shapefile(".")
        if path is None or not Path(path).exists():
            warnings.warn(
                "Bangladesh shapefile not found.  Using centroid markers instead. "
                "See instructions_shapefile.md.",
                UserWarning, stacklevel=3,
            )
            return

        try:
            loader = ShapefileLoader(path)
            gdf = loader.load()
            self._shp_name_col = loader.name_col
            # Convert to GeoJSON dict for Folium
            self._geojson = json.loads(gdf.to_json())
            print(f"Shapefile loaded for interactive maps: {path}")
        except Exception as exc:
            warnings.warn(
                f"Failed to load shapefile ({exc}).  Using centroid markers.",
                UserWarning, stacklevel=3,
            )

    def _attach_coordinates(self) -> None:
        if "lat" in self.df.columns and "lon" in self.df.columns:
            return
        lats, lons = [], []
        for name in self.df[self.name_col]:
            rec = self._db.get_by_name(str(name))
            lats.append(rec["lat"] if rec else np.nan)
            lons.append(rec["lon"] if rec else np.nan)
        self.df["lat"] = lats
        self.df["lon"] = lons

    # ------------------------------------------------------------------
    # Base map
    # ------------------------------------------------------------------

    def _base_map(self, zoom_start: int = 7) -> "folium.Map":
        """Create a Folium base map centred on Bangladesh."""
        m = folium.Map(
            location=[BANGLADESH_CENTER["lat"], BANGLADESH_CENTER["lon"]],
            zoom_start=zoom_start,
            tiles=list(BASEMAP_TILES.values())[0],
        )
        # Add alternative basemap layers
        for label, tiles in list(BASEMAP_TILES.items())[1:]:
            folium.TileLayer(tiles, name=label).add_to(m)

        # Constrain zoom to Bangladesh
        b = BANGLADESH_BOUNDS
        m.fit_bounds([
            [b["min_lat"], b["min_lon"]],
            [b["max_lat"], b["max_lon"]],
        ])
        return m

    # ------------------------------------------------------------------
    # Choropleth helpers
    # ------------------------------------------------------------------

    def _build_data_dict(self, score_col: str) -> Dict[str, float]:
        """Return {upazila_name: score} mapping for choropleth."""
        return dict(zip(self.df[self.name_col], self.df[score_col]))

    def _add_choropleth(
        self,
        m: "folium.Map",
        score_col: str,
        name: str = "MEPI Score",
        palette: Optional[List[str]] = None,
    ) -> None:
        """Add a choropleth GeoJSON layer to *m*."""
        if self._geojson is None or self._shp_name_col is None:
            return

        if palette is None:
            palette = DIMENSION_PALETTE

        data = self._build_data_dict(score_col)

        folium.Choropleth(
            geo_data=self._geojson,
            name=name,
            data=self.df,
            columns=[self.name_col, score_col],
            key_on=f"feature.properties.{self._shp_name_col}",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name=f"{name} (0–1)",
            nan_fill_color="#cccccc",
            nan_fill_opacity=0.4,
        ).add_to(m)

    def _add_marker_layer(
        self,
        m: "folium.Map",
        score_col: str,
        layer_name: str = "Upazila Markers",
    ) -> None:
        """Add circle markers to *m* (fallback when no shapefile)."""
        fg = folium.FeatureGroup(name=layer_name)
        df = self.df.dropna(subset=["lat", "lon", score_col])

        for _, row in df.iterrows():
            score = float(row[score_col])
            popup_html = _build_popup_html(row, self._dim_cols)
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=8,
                color="grey",
                weight=0.8,
                fill=True,
                fill_color=_poverty_color(score) if score_col == "mepi_score"
                           else _score_to_color(score),
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"{row.get(self.name_col, '')} – {score:.3f}",
            ).add_to(fg)

        fg.add_to(m)

    def _add_tooltip_layer(self, m: "folium.Map") -> None:
        """Add invisible GeoJSON layer carrying tooltips and popups."""
        if self._geojson is None:
            return

        # Build lookup: normalised name → df row
        data_lookup = {
            str(n).lower(): row
            for n, row in zip(self.df[self.name_col], self.df.to_dict("records"))
        }

        def _style(feature):
            return {
                "fillOpacity": 0.0,
                "weight": 0,
            }

        def _highlight(feature):
            return {
                "weight": 2,
                "color": "#333",
                "fillOpacity": 0.1,
            }

        popup_fg = folium.FeatureGroup(name="Upazila Details (click)", show=True)
        for feature in self._geojson.get("features", []):
            props = feature.get("properties", {})
            raw_name = props.get(self._shp_name_col, "")
            row_data = data_lookup.get(str(raw_name).lower())
            if row_data is None:
                continue

            row_series = pd.Series(row_data)
            html = _build_popup_html(row_series, self._dim_cols)
            score = row_data.get("mepi_score", np.nan)
            score_str = f"{score:.3f}" if not np.isnan(float(score)) else "N/A"

            folium.GeoJson(
                feature,
                style_function=_style,
                highlight_function=_highlight,
                tooltip=folium.Tooltip(f"<b>{raw_name}</b> MEPI: {score_str}"),
                popup=folium.Popup(html, max_width=290),
            ).add_to(popup_fg)

        popup_fg.add_to(m)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def create_mepi_map(
        self,
        output_path: str = "map_outputs/interactive_map.html",
    ) -> str:
        """
        Create the main interactive MEPI map and save as HTML.

        Returns
        -------
        str : path to the saved HTML file.
        """
        _ensure_dir(os.path.dirname(output_path) or ".")
        m = self._base_map()

        if self._geojson is not None:
            self._add_choropleth(m, "mepi_score", name="MEPI Score")
            self._add_tooltip_layer(m)
        else:
            self._add_marker_layer(m, "mepi_score", "MEPI Score Markers")

        # Add fullscreen button
        try:
            folium_plugins.Fullscreen().add_to(m)
        except Exception:
            pass

        folium.LayerControl().add_to(m)

        m.save(output_path)
        print(f"Saved: {output_path}")
        return os.path.abspath(output_path)

    def create_dimension_maps(
        self,
        output_dir: str = "map_outputs",
    ) -> List[str]:
        """
        Create one interactive map per MEPI dimension.

        Returns
        -------
        list of str
        """
        _ensure_dir(output_dir)
        saved = []

        for dim in DIMENSIONS:
            score_col = f"{dim}_score"
            if score_col not in self.df.columns:
                continue

            output_path = os.path.join(
                output_dir,
                f"interactive_{dim.lower()}_map.html",
            )
            m = self._base_map()

            if self._geojson is not None:
                self._add_choropleth(
                    m, score_col, name=f"{dim} Score"
                )
                self._add_tooltip_layer(m)
            else:
                self._add_marker_layer(
                    m, score_col, f"{dim} Score Markers"
                )

            try:
                folium_plugins.Fullscreen().add_to(m)
            except Exception:
                pass

            folium.LayerControl().add_to(m)
            m.save(output_path)
            print(f"Saved: {output_path}")
            saved.append(os.path.abspath(output_path))

        return saved

    def create_all_maps(self, output_dir: str = "map_outputs") -> List[str]:
        """Create all interactive maps (MEPI + all dimensions)."""
        _ensure_dir(output_dir)
        paths = []
        paths.append(
            self.create_mepi_map(os.path.join(output_dir, "interactive_map.html"))
        )
        paths.extend(self.create_dimension_maps(output_dir))
        return paths
