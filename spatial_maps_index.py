"""
spatial_maps_index.py - Create README.txt, map_legend.txt, and index.html for
                        the ~/spatial_maps_png/ folder

Generates three documentation files:
  README.txt      – what each map shows, data requirements, usage instructions
  map_legend.txt  – colour-scale guide and poverty classification explanation
  index.html      – browse all six PNG maps in a web browser

Usage
-----
    python spatial_maps_index.py
    python spatial_maps_index.py --output-dir /custom/spatial_maps_png/
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from spatial_maps_config import (
    SPATIAL_OUTPUT_FOLDER,
    DIMENSION_MAP_CONFIGS,
    MEPI_MAP_FILENAME,
    POVERTY_LABELS,
    POVERTY_COLORS,
    POVERTY_THRESHOLDS,
    PNG_DPI,
    FIGURE_SIZE,
)
from spatial_folder_manager import SpatialFolderManager, ensure_spatial_folder, EXPECTED_PNG_FILES

# ---------------------------------------------------------------------------
# README content
# ---------------------------------------------------------------------------

_README_TEMPLATE = """\
SPATIAL MAPS PNG – README
==========================
Generated : {timestamp}
Folder    : {folder}

OVERVIEW
--------
This folder contains 6 high-resolution spatial choropleth maps for the
Multidimensional Energy Poverty Index (MEPI) in Bangladesh, generated at
the upazila (sub-district) level.

This folder is COMPLETELY SEPARATE from all other map output locations.
It contains ONLY spatial PNG maps.

FILES
-----
{file_list}

MAP DESCRIPTIONS
----------------
mepi_spatial_map.png
  Overall MEPI score for each upazila.  Colour shows the composite
  deprivation index (0 = non-poor, 1 = severely poor).

availability_map.png
  Energy Availability dimension score.
  Measures physical access to electricity and modern cooking fuels.

reliability_map.png
  Energy Reliability dimension score.
  Measures consistency of electricity supply (hours/day, interruptions).

adequacy_map.png
  Energy Adequacy dimension score.
  Measures whether households have sufficient energy for all needs.

quality_map.png
  Energy Quality dimension score.
  Measures quality of energy services (voltage stability, clean fuels).

affordability_map.png
  Energy Affordability dimension score.
  Measures share of household income spent on energy.

COLOUR SCALE
------------
  Green  (0.00 – 0.33)  → Non-poor
  Yellow (0.33 – 0.66)  → Moderate poverty
  Red    (0.66 – 1.00)  → Severe poverty

MAP SPECIFICATIONS
------------------
  Resolution  : {dpi} DPI
  Format      : PNG
  Size        : {width}" × {height}" (inches)
  Projection  : WGS 84 Geographic Coordinates
  Coverage    : Bangladesh, all upazilas

HOW TO VIEW
-----------
  1. Open index.html in a web browser to browse all maps interactively.
  2. Or open any .png file directly in an image viewer.
  3. For GIS software (QGIS/ArcGIS): import as raster layer.

HOW TO REGENERATE
-----------------
  cd energy-poverty-mapping/
  python generate_spatial_maps_only.py

  Or for custom data:
  python generate_spatial_maps_only.py --data path/to/mepi_results.csv

DATA REQUIREMENTS
-----------------
  MEPI results CSV columns required:
    upazila_name   – upazila identifier
    mepi_score     – composite MEPI deprivation score (0–1)
    availability   – energy availability dimension score
    reliability    – energy reliability dimension score
    adequacy       – energy adequacy dimension score
    quality        – energy quality dimension score
    affordability  – energy affordability dimension score

  Bangladesh upazila shapefile (optional, for boundary maps):
    shapefiles/bgd_adm2.shp   (+ .dbf, .shx, .prj)

CONTACT
-------
  Energy Poverty Mapping Project
  Repository: https://github.com/iqbal1999-tiger/energy-poverty-mapping
"""

# ---------------------------------------------------------------------------
# Legend content
# ---------------------------------------------------------------------------

_LEGEND_TEMPLATE = """\
SPATIAL MAPS – MAP LEGEND & COLOUR SCALE GUIDE
================================================

COLOUR SCALE (Deprivation Score 0.0 – 1.0)
-------------------------------------------

  ■ GREEN   (0.00 – 0.33)   Non-Poor
    Upazilas where households have adequate access to energy services.
    Less than one-third of indicators show deprivation.

  ■ YELLOW  (0.33 – 0.66)   Moderate Poverty
    Upazilas with moderate energy poverty.
    Between one-third and two-thirds of indicators show deprivation.

  ■ RED     (0.66 – 1.00)   Severe Poverty
    Upazilas with high energy poverty.
    More than two-thirds of indicators show deprivation.

  □ GREY                    No Data
    Upazilas with no matching MEPI data.

SCORE INTERPRETATION
--------------------
  0.00  →  No deprivation (fully energy-sufficient)
  0.33  →  Threshold between non-poor and moderate poverty
  0.50  →  Median (half the indicators show deprivation)
  0.66  →  Threshold between moderate and severe poverty
  1.00  →  Full deprivation (no energy access in any dimension)

DIMENSION SCORES
----------------
  Each dimension score follows the same 0–1 scale.
  Lower is better (less deprived).

  Availability  – Physical access to electricity / modern fuels
  Reliability   – Consistency of electricity supply
  Adequacy      – Sufficient energy for all household needs
  Quality       – Quality of energy services (voltage, clean fuels)
  Affordability – Share of household income spent on energy

MEPI FORMULA
------------
  MEPI = weighted average of 5 dimension scores
  Default weights: each dimension contributes equally (0.20 each)

COLOUR PALETTE
--------------
  Continuous colormap : RdYlGn_r (Red → Yellow → Green reversed)
  Legend categories   : Discretised into 3 poverty bands
  Colorblind-friendly : Yes (avoids green/red confusion via labelling)
"""

# ---------------------------------------------------------------------------
# HTML index
# ---------------------------------------------------------------------------

def _build_index_html(folder: Path, timestamp: str) -> str:
    map_configs = [
        {"file": MEPI_MAP_FILENAME,
         "title": "Overall MEPI Score",
         "desc": "Composite Multidimensional Energy Poverty Index for all upazilas."},
    ] + [
        {
            "file": cfg["filename"],
            "title": cfg["title"].split("–")[0].strip(),
            "desc": cfg["title"],
        }
        for cfg in DIMENSION_MAP_CONFIGS
    ]

    cards_html = ""
    for m in map_configs:
        cards_html += f"""
        <div class="card">
            <h3>{m['title']}</h3>
            <p class="desc">{m['desc']}</p>
            <a href="{m['file']}" target="_blank">
                <img src="{m['file']}" alt="{m['title']}" loading="lazy"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
                <p class="missing" style="display:none">⬜ Image not yet generated.<br>
                   Run: <code>python generate_spatial_maps_only.py</code></p>
            </a>
            <a class="btn" href="{m['file']}" download>⬇ Download PNG</a>
        </div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spatial Maps – Energy Poverty Bangladesh</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f4f6f9;
      color: #333;
    }}
    header {{
      background: linear-gradient(135deg, #1a5276, #2e86c1);
      color: white;
      padding: 30px 40px;
    }}
    header h1 {{ font-size: 1.8em; margin-bottom: 6px; }}
    header p  {{ font-size: 0.95em; opacity: 0.85; }}
    .meta {{
      background: #eaf2ff;
      border-left: 4px solid #2e86c1;
      padding: 12px 20px;
      margin: 20px 40px;
      border-radius: 4px;
      font-size: 0.9em;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 24px;
      padding: 20px 40px 40px;
    }}
    .card {{
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card h3 {{
      padding: 14px 16px 6px;
      font-size: 1.05em;
      color: #1a5276;
    }}
    .card .desc {{
      padding: 0 16px 10px;
      font-size: 0.82em;
      color: #555;
      min-height: 36px;
    }}
    .card a img {{
      width: 100%;
      display: block;
      border-top: 1px solid #eee;
      max-height: 260px;
      object-fit: cover;
      transition: opacity 0.2s;
    }}
    .card a img:hover {{ opacity: 0.88; }}
    .card .missing {{
      padding: 20px;
      color: #888;
      font-size: 0.85em;
      text-align: center;
    }}
    .card code {{
      background: #f0f0f0;
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 0.85em;
    }}
    .btn {{
      display: block;
      text-align: center;
      background: #2e86c1;
      color: white;
      text-decoration: none;
      padding: 10px;
      font-size: 0.88em;
      transition: background 0.2s;
    }}
    .btn:hover {{ background: #1a5276; }}
    .legend {{
      margin: 0 40px 30px;
      background: white;
      border-radius: 8px;
      padding: 20px 24px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .legend h2 {{ margin-bottom: 12px; color: #1a5276; }}
    .legend-items {{ display: flex; gap: 20px; flex-wrap: wrap; }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.9em; }}
    .swatch {{
      width: 24px; height: 24px;
      border-radius: 4px;
      border: 1px solid #ccc;
      flex-shrink: 0;
    }}
    footer {{
      text-align: center;
      padding: 20px;
      font-size: 0.8em;
      color: #888;
    }}
  </style>
</head>
<body>
<header>
  <h1>🗺 Spatial Maps – Energy Poverty Index (MEPI) – Bangladesh</h1>
  <p>Choropleth maps at the Upazila level &nbsp;|&nbsp; 300 DPI PNG &nbsp;|&nbsp;
     Generated: {timestamp}</p>
</header>

<div class="meta">
  📁 Folder: <code>{folder}</code> &nbsp;&nbsp;
  📊 6 PNG maps &nbsp;&nbsp;
  🔍 Click any map to view full size &nbsp;&nbsp;
  ⬇ Use the Download button to save a copy
</div>

<div class="legend">
  <h2>Colour Scale – Poverty Level</h2>
  <div class="legend-items">
    <div class="legend-item">
      <div class="swatch" style="background:#1a9850"></div>
      <span><strong>Non-Poor</strong> (0.00 – 0.33)</span>
    </div>
    <div class="legend-item">
      <div class="swatch" style="background:#fee08b"></div>
      <span><strong>Moderate Poverty</strong> (0.33 – 0.66)</span>
    </div>
    <div class="legend-item">
      <div class="swatch" style="background:#d73027"></div>
      <span><strong>Severe Poverty</strong> (0.66 – 1.00)</span>
    </div>
    <div class="legend-item">
      <div class="swatch" style="background:#cccccc"></div>
      <span>No Data</span>
    </div>
  </div>
</div>

<div class="grid">
{cards_html}
</div>

<footer>
  Energy Poverty Mapping Project &nbsp;|&nbsp;
  <a href="README.txt">README.txt</a> &nbsp;|&nbsp;
  <a href="map_legend.txt">Colour Legend Guide</a>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Index / documentation generator class
# ---------------------------------------------------------------------------


class SpatialMapsIndex:
    """
    Generate README.txt, map_legend.txt, and index.html in ~/spatial_maps_png/.

    Parameters
    ----------
    output_dir : str, optional
        Override the default output folder (~/spatial_maps_png/).
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self._mgr = ensure_spatial_folder(output_dir)
        self.folder = self._mgr.folder

    # ------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------

    def create_readme(self) -> str:
        """Write README.txt to the spatial maps folder."""
        file_list = ""
        for name in EXPECTED_PNG_FILES:
            file_list += f"  {name}\n"
        file_list += "  README.txt\n"
        file_list += "  index.html\n"
        file_list += "  map_legend.txt\n"

        content = _README_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            folder=self.folder,
            file_list=file_list,
            dpi=PNG_DPI,
            width=FIGURE_SIZE[0],
            height=FIGURE_SIZE[1],
        )

        path = self.folder / "README.txt"
        path.write_text(content, encoding="utf-8")
        print(f"  Created: {path}")
        return str(path)

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------

    def create_legend(self) -> str:
        """Write map_legend.txt to the spatial maps folder."""
        path = self.folder / "map_legend.txt"
        path.write_text(_LEGEND_TEMPLATE, encoding="utf-8")
        print(f"  Created: {path}")
        return str(path)

    # ------------------------------------------------------------------
    # HTML index
    # ------------------------------------------------------------------

    def create_index_html(self) -> str:
        """Write index.html to the spatial maps folder."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = _build_index_html(self.folder, timestamp)
        path = self.folder / "index.html"
        path.write_text(html, encoding="utf-8")
        print(f"  Created: {path}")
        return str(path)

    # ------------------------------------------------------------------
    # Generate all
    # ------------------------------------------------------------------

    def generate_all(self) -> List[str]:
        """Generate README.txt, map_legend.txt, and index.html."""
        paths: List[str] = []
        paths.append(self.create_readme())
        paths.append(self.create_legend())
        paths.append(self.create_index_html())
        return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate README, legend, and index.html for ~/spatial_maps_png/"
    )
    parser.add_argument(
        "--output-dir", default=SPATIAL_OUTPUT_FOLDER,
        help=f"Spatial maps folder (default: {SPATIAL_OUTPUT_FOLDER}).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SPATIAL MAPS – DOCUMENTATION GENERATOR")
    print("=" * 60)

    gen = SpatialMapsIndex(output_dir=args.output_dir)
    created = gen.generate_all()

    print(f"\n✅ {len(created)} documentation file(s) created in:")
    print(f"   {gen.folder}")
    for p in created:
        print(f"   ├── {Path(p).name}")
    print(f"\n   Open in browser: file://{gen.folder / 'index.html'}")


if __name__ == "__main__":
    main()
