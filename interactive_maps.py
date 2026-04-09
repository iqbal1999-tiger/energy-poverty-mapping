"""
interactive_maps.py - Interactive Folium HTML maps for MEPI

Creates interactive web maps using Folium:
  - Choropleth-style circle maps with popups and tooltips
  - Layer toggles for different MEPI dimensions
  - Colour-coded poverty classifications
  - Hotspot highlighting
  - Saved as HTML for use in browsers or Jupyter/Colab notebooks

Public API:
    create_interactive_map(df, output_path)
    create_dimension_layer_map(df, output_path)
    create_hotspot_interactive_map(df, output_path)
"""

import os

import pandas as pd

from map_config import (
    BANGLADESH_CENTER,
    FOLIUM_MAX_ZOOM,
    FOLIUM_MIN_ZOOM,
    FOLIUM_TILES,
    FOLIUM_ZOOM_START,
    MARKER_FILL_OPACITY,
    MARKER_RADIUS,
    MARKER_WEIGHT,
    MAP_OUTPUTS_DIR,
    OUTPUT_FILES,
    POVERTY_COLORS,
    THRESHOLD_MODERATE,
    THRESHOLD_SEVERE,
    DIMENSION_LABELS,
    HOTSPOT_COLOR,
)
from data_preparation_spatial import SpatialDataPrep
from spatial_mapping import _ensure_output_dir

try:
    import folium
    from folium.plugins import MarkerCluster, MiniMap
    HAS_FOLIUM = True
except ImportError:  # pragma: no cover
    HAS_FOLIUM = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_folium():
    if not HAS_FOLIUM:
        raise ImportError(
            "Folium is required for interactive maps. "
            "Install with: pip install folium"
        )


def _ensure_coords(df: pd.DataFrame) -> pd.DataFrame:
    if "latitude" not in df.columns or "longitude" not in df.columns:
        prep = SpatialDataPrep(df)
        df = prep.add_coordinates()
    return df


def _poverty_color(score: float) -> str:
    if score >= THRESHOLD_SEVERE:
        return POVERTY_COLORS["Severely Poor"]
    elif score >= THRESHOLD_MODERATE:
        return POVERTY_COLORS["Moderately Poor"]
    return POVERTY_COLORS["Non-Poor"]


def _dimension_score_str(row: pd.Series) -> str:
    lines = []
    for dim in ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]:
        col = f"{dim}_score"
        if col in row.index:
            lines.append(f"  <b>{dim}:</b> {row[col]:.3f}")
    return "<br>".join(lines)


def _build_popup_html(row: pd.Series, name_col: str) -> str:
    name = row.get(name_col, "Upazila")
    district = row.get("district", "—")
    division = row.get("division", "—")
    mepi = row.get("mepi_score", float("nan"))
    category = row.get("poverty_category", "—")
    zone = row.get("geographic_zone", "—")
    dim_str = _dimension_score_str(row)
    return f"""
    <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px;'>
      <h4 style='margin: 4px 0; color: #2c3e50;'>{name}</h4>
      <hr style='margin: 4px 0;'>
      <b>District:</b> {district}<br>
      <b>Division:</b> {division}<br>
      <b>Zone:</b> {zone}<br>
      <hr style='margin: 4px 0;'>
      <b>MEPI Score:</b> {mepi:.3f}<br>
      <b>Category:</b> <span style='color:{_poverty_color(mepi)};font-weight:bold;'>{category}</span><br>
      <hr style='margin: 4px 0;'>
      <b>Dimension Scores:</b><br>
      {dim_str}
    </div>
    """


# ---------------------------------------------------------------------------
# 1. Main interactive MEPI map
# ---------------------------------------------------------------------------

def create_interactive_map(
    df: pd.DataFrame,
    output_path: str = None,
    title: str = "Bangladesh Energy Poverty Index (MEPI) – Interactive Map",
) -> str:
    """
    Create an interactive Folium HTML map of MEPI scores.

    Each upazila is shown as a circle marker coloured by poverty category.
    Clicking opens a popup with full MEPI and dimension details.
    Hovering shows the upazila name and MEPI score as a tooltip.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    output_path : str, optional
        HTML output path.  Defaults to ``map_outputs/interactive_map.html``.
    title : str
        Map title shown at the top.

    Returns
    -------
    str
        Path to the saved HTML file.
    """
    _require_folium()

    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, OUTPUT_FILES["interactive_map"])

    df = _ensure_coords(df)
    name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

    # Ensure geographic_zone column exists
    if "geographic_zone" not in df.columns:
        try:
            from spatial_analysis import SpatialAnalyzer
            sa = SpatialAnalyzer(df)
            df = sa.df
        except Exception:
            df = df.copy()
            df["geographic_zone"] = "unknown"

    m = folium.Map(
        location=BANGLADESH_CENTER,
        zoom_start=FOLIUM_ZOOM_START,
        min_zoom=FOLIUM_MIN_ZOOM,
        max_zoom=FOLIUM_MAX_ZOOM,
        tiles=FOLIUM_TILES,
    )

    # Add minimap
    MiniMap(toggle_display=True).add_to(m)

    # Add title
    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
         background: white; padding: 8px 16px; border-radius: 6px;
         font-size: 14px; font-weight: bold; font-family: Arial;
         box-shadow: 2px 2px 6px rgba(0,0,0,0.3); z-index: 9999;">
      {title}
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # Feature group for MEPI circles
    fg = folium.FeatureGroup(name="MEPI Scores", show=True)

    for _, row in df.iterrows():
        color = _poverty_color(row["mepi_score"])
        popup_html = _build_popup_html(row, name_col)
        tooltip_text = f"{row[name_col]}: MEPI = {row['mepi_score']:.3f}"

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=MARKER_RADIUS + row["mepi_score"] * 6,  # larger = worse
            color="black",
            weight=MARKER_WEIGHT,
            fill=True,
            fill_color=color,
            fill_opacity=MARKER_FILL_OPACITY,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=tooltip_text,
        ).add_to(fg)

    fg.add_to(m)

    # Add legend
    _add_folium_legend(m)

    folium.LayerControl(collapsed=False).add_to(m)

    m.save(output_path)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 2. Dimension layer map
# ---------------------------------------------------------------------------

def create_dimension_layer_map(
    df: pd.DataFrame,
    output_path: str = None,
) -> str:
    """
    Create an interactive map with layer toggles for each MEPI dimension.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    output_path : str, optional
        HTML output path.

    Returns
    -------
    str
        Saved file path.
    """
    _require_folium()

    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, "dimension_layer_map.html")

    df = _ensure_coords(df)
    name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

    import matplotlib.cm as cm
    import matplotlib.colors as mcolors

    m = folium.Map(
        location=BANGLADESH_CENTER,
        zoom_start=FOLIUM_ZOOM_START,
        tiles=FOLIUM_TILES,
    )
    MiniMap(toggle_display=True).add_to(m)

    dimensions = ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]
    cmaps = {
        "Availability": cm.Reds,
        "Reliability": cm.Oranges,
        "Adequacy": cm.Purples,
        "Quality": cm.Blues,
        "Affordability": cm.YlOrRd,
    }

    for dim in dimensions:
        col = f"{dim}_score"
        if col not in df.columns:
            continue
        fg = folium.FeatureGroup(name=DIMENSION_LABELS.get(dim, dim), show=(dim == "Availability"))
        colormap = cmaps.get(dim, cm.Reds)
        for _, row in df.iterrows():
            score = row[col]
            rgba = colormap(score)
            hex_color = mcolors.to_hex(rgba)
            tooltip_text = f"{row[name_col]} | {dim}: {score:.3f}"
            popup_html = (
                f"<b>{row[name_col]}</b><br>"
                f"<b>{DIMENSION_LABELS.get(dim, dim)} Score:</b> {score:.3f}<br>"
                f"<b>Overall MEPI:</b> {row['mepi_score']:.3f}"
            )
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=MARKER_RADIUS,
                color="black", weight=0.5,
                fill=True, fill_color=hex_color,
                fill_opacity=MARKER_FILL_OPACITY,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=tooltip_text,
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_path)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 3. Hotspot interactive map
# ---------------------------------------------------------------------------

def create_hotspot_interactive_map(
    df: pd.DataFrame,
    output_path: str = None,
    threshold: float = None,
) -> str:
    """
    Create an interactive map highlighting energy poverty hotspots.

    Parameters
    ----------
    df : pd.DataFrame
        MEPI results.
    output_path : str, optional
        HTML output path.
    threshold : float, optional
        MEPI threshold for hotspot classification.  Defaults to THRESHOLD_SEVERE.

    Returns
    -------
    str
        Saved file path.
    """
    _require_folium()

    threshold = threshold if threshold is not None else THRESHOLD_SEVERE
    if output_path is None:
        _ensure_output_dir(MAP_OUTPUTS_DIR)
        output_path = os.path.join(MAP_OUTPUTS_DIR, "hotspot_interactive_map.html")

    df = _ensure_coords(df)
    name_col = "upazila_name" if "upazila_name" in df.columns else df.columns[0]

    m = folium.Map(
        location=BANGLADESH_CENTER,
        zoom_start=FOLIUM_ZOOM_START,
        tiles=FOLIUM_TILES,
    )
    MiniMap(toggle_display=True).add_to(m)

    hotspot_fg = folium.FeatureGroup(name=f"Hotspots (MEPI ≥ {threshold})", show=True)
    normal_fg = folium.FeatureGroup(name="Non-Hotspots", show=True)

    for _, row in df.iterrows():
        is_hot = row["mepi_score"] >= threshold
        fg = hotspot_fg if is_hot else normal_fg
        color = HOTSPOT_COLOR if is_hot else "#27ae60"
        popup_html = _build_popup_html(row, name_col)
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=MARKER_RADIUS + (4 if is_hot else 0),
            color="black", weight=MARKER_WEIGHT,
            fill=True, fill_color=color,
            fill_opacity=MARKER_FILL_OPACITY,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{row[name_col]}: MEPI={row['mepi_score']:.3f}",
        ).add_to(fg)

    hotspot_fg.add_to(m)
    normal_fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(output_path)
    print(f"Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 4. Legend helper
# ---------------------------------------------------------------------------

def _add_folium_legend(m):
    legend_html = """
    <div style="position: fixed; bottom: 40px; left: 10px; z-index: 9999;
         background: white; padding: 10px 14px; border-radius: 8px;
         font-size: 12px; font-family: Arial; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
      <b>MEPI Category</b><br>
      <span style="background:#e74c3c; border-radius:50%; display:inline-block;
             width:12px; height:12px; margin-right:5px;"></span>Severely Poor (≥ 0.66)<br>
      <span style="background:#f39c12; border-radius:50%; display:inline-block;
             width:12px; height:12px; margin-right:5px;"></span>Moderately Poor (0.33–0.66)<br>
      <span style="background:#2ecc71; border-radius:50%; display:inline-block;
             width:12px; height:12px; margin-right:5px;"></span>Non-Poor (&lt; 0.33)<br>
      <br><i style="font-size:10px;">Circle size reflects MEPI score.<br>Click circles for details.</i>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
