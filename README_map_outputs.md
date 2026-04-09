# README – Map Outputs Directory

This document describes the organised folder structure used for all Energy
Poverty Index (MEPI) map outputs in the Bangladesh Energy Poverty Mapping project.

---

## Folder Structure

```
map_outputs/
├── spatial_maps/          Spatial distribution maps
│   ├── mepi_spatial_map.png
│   ├── availability_map.png
│   ├── reliability_map.png
│   ├── adequacy_map.png
│   ├── quality_map.png
│   └── affordability_map.png
│
├── regional_maps/         Regional analysis maps
│   ├── coastal_analysis_map.png
│   ├── char_analysis_map.png
│   ├── haor_analysis_map.png
│   ├── hill_tract_analysis_map.png
│   ├── sundarbans_analysis_map.png
│   └── urban_rural_comparison.png
│
├── temporal_maps/         Time-series and change maps
│   ├── temporal_2020_comparison.png
│   ├── temporal_2021_comparison.png
│   ├── temporal_2022_comparison.png
│   ├── poverty_change_map.png
│   ├── improvement_areas.png
│   ├── deterioration_areas.png
│   └── temporal_animation.gif
│
├── hotspot_maps/          Clustering and vulnerability maps
│   ├── hotspot_clusters.png
│   ├── vulnerability_map.png
│   ├── hotspot_intensity.png
│   └── cluster_analysis.png
│
├── analysis_maps/         Analytical visualisations
│   ├── top10_most_poor.png
│   ├── top10_least_poor.png
│   ├── dimension_heatmap.png
│   ├── dimension_correlation.png
│   ├── regional_comparison.png
│   └── poverty_classification_distribution.png
│
└── interactive_maps/      Interactive HTML maps
    ├── interactive_map.html
    ├── interactive_availability_map.html
    ├── interactive_reliability_map.html
    ├── interactive_adequacy_map.html
    ├── interactive_quality_map.html
    ├── interactive_affordability_map.html
    ├── index.html
    └── README_interactive_maps.txt
```

---

## What Is in Each Subfolder

### `spatial_maps/`
Choropleth or scatter-plot maps showing the geographical distribution of energy
poverty across all 492 Bangladesh upazilas.

| File | Description |
|------|-------------|
| `mepi_spatial_map.png` | Overall MEPI score – composite energy poverty index |
| `*_map.png` (dimensions) | Score for each of the 5 dimensions (availability, reliability, adequacy, quality, affordability) |
| `poverty_category_map.png` | Categorical map: Non-Poor / Moderately Poor / Severely Poor |

### `regional_maps/`
Maps focused on specific geographic zones of Bangladesh.

| File | Description |
|------|-------------|
| `coastal_analysis_map.png` | Coastal and delta upazilas |
| `char_analysis_map.png` | River-island (char) areas |
| `haor_analysis_map.png` | Seasonal wetland (haor) basin |
| `hill_tract_analysis_map.png` | Chittagong Hill Tracts |
| `sundarbans_analysis_map.png` | Sundarbans mangrove buffer zone |
| `urban_rural_comparison.png` | Urban vs rural energy poverty comparison |

### `temporal_maps/`
Year-by-year and change maps showing how energy poverty has evolved over time.

| File | Description |
|------|-------------|
| `temporal_{year}_comparison.png` | MEPI distribution for a given year |
| `poverty_change_map.png` | Net MEPI change from first to last data year |
| `improvement_areas.png` | Upazilas with improving energy poverty |
| `deterioration_areas.png` | Upazilas with worsening energy poverty |
| `temporal_animation.gif` | Animated GIF cycling through all data years |

### `hotspot_maps/`
Maps identifying spatial clusters of severe energy poverty.

| File | Description |
|------|-------------|
| `hotspot_clusters.png` | Upazilas above the hotspot threshold (MEPI ≥ 0.66) |
| `vulnerability_map.png` | Number of dimensions with high deprivation |
| `hotspot_intensity.png` | Kernel density heat map of hotspot concentration |
| `cluster_analysis.png` | Spatial map + bar chart of top hotspot upazilas |

### `analysis_maps/`
Statistical and comparative visualisations for presentations and reports.

| File | Description |
|------|-------------|
| `top10_most_poor.png` | 10 upazilas with the highest MEPI scores |
| `top10_least_poor.png` | 10 upazilas with the lowest MEPI scores |
| `dimension_heatmap.png` | All upazilas × all dimensions heatmap |
| `dimension_correlation.png` | Pearson correlation between dimension scores |
| `regional_comparison.png` | Mean MEPI by administrative division |
| `poverty_classification_distribution.png` | Count of upazilas by poverty category |

### `interactive_maps/`
Folium-based interactive maps.  Open any `.html` file in a modern browser.

| File | Description |
|------|-------------|
| `interactive_map.html` | Main MEPI overview – click upazilas for details |
| `interactive_*_map.html` | Per-dimension interactive maps |
| `index.html` | Gallery page linking all interactive maps |
| `README_interactive_maps.txt` | Usage instructions |

---

## Naming Convention

All map files follow the pattern:

```
{type}_{dimension/region/year}_{suffix}.{ext}
```

Examples:
- `spatial_mepi_map.png` → `spatial_maps/`
- `dimension_availability_map.png` → `spatial_maps/`
- `coastal_analysis_map.png` → `regional_maps/`
- `temporal_2021_comparison.png` → `temporal_maps/`
- `hotspot_clusters.png` → `hotspot_maps/`
- `top10_most_poor.png` → `analysis_maps/`
- `interactive_map.html` → `interactive_maps/`

---

## Map Production Workflow

### First-time Setup

```bash
# 1. Create folder structure
python setup_folder_structure.py
```

### Generate All Maps

```bash
# 2. Generate everything (uses sample_data.csv by default)
python generate_all_maps_organized.py

# Or supply your own MEPI results CSV:
python generate_all_maps_organized.py --data path/to/mepi_results.csv

# Skip interactive maps (if folium is not installed):
python generate_all_maps_organized.py --no-interactive
```

### Organise Existing PNG Files

If you already have PNG files in `map_outputs/` and want to sort them:

```bash
python map_organizer.py
python map_organizer.py --dry-run    # preview without moving
python map_organizer.py --readme     # also generate README.txt files
```

### Regenerate Index Files

```bash
python map_index_generator.py
```

---

## Using Individual Mapping Modules

```python
from updated_correct_spatial_mapping import OrganisedSpatialMapper
import pandas as pd

results = pd.read_csv("mepi_results.csv")

# Spatial maps → map_outputs/spatial_maps/
# Hotspot maps → map_outputs/hotspot_maps/
mapper = OrganisedSpatialMapper(results)
mapper.create_all_maps()
mapper.create_regional_maps()   # → map_outputs/regional_maps/
```

```python
from updated_temporal_maps import TemporalMapper

yearly = {
    2020: pd.read_csv("mepi_2020.csv"),
    2021: pd.read_csv("mepi_2021.csv"),
    2022: pd.read_csv("mepi_2022.csv"),
}
mapper = TemporalMapper(yearly)
mapper.create_all_temporal_maps()   # → map_outputs/temporal_maps/
```

```python
from updated_spatio_temporal_hotspot import HotspotAnalyser

analyser = HotspotAnalyser(results)
analyser.create_all_hotspot_maps()  # → map_outputs/hotspot_maps/
```

```python
from updated_interactive_folium_maps import OrganisedInteractiveMapper

mapper = OrganisedInteractiveMapper(results)
mapper.create_all_maps()            # → map_outputs/interactive_maps/
```

---

## Quality Standards

All static PNG maps are saved at **300 DPI** with `bbox_inches="tight"` for
publication-quality output.  Interactive HTML maps are self-contained and
require only an internet connection for the basemap tiles.

---

## Notes

- `map_outputs/` is listed in `.gitignore` so generated maps are not committed
  to the repository.  Commit only the scripts and data files.
- Bangladesh upazila shapefiles (for proper choropleth maps) should be placed
  in the `shapefiles/` directory.  See `instructions_shapefile.md` for details.
- If no shapefile is found, scatter-plot maps using centroid coordinates are
  generated automatically as a fallback.
