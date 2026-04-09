# Instructions: Download Bangladesh Upazila Shapefile

This guide explains how to download the official Bangladesh upazila boundary
shapefile and configure it for use with the energy-poverty-mapping scripts.

---

## Why You Need a Shapefile

A **shapefile** (or GeoJSON file) contains the precise boundary polygons for
every upazila in Bangladesh.  Without it, maps show only scatter dots at
upazila centroids instead of filled administrative regions.

---

## Option 1 – GADM (Recommended)

[GADM](https://gadm.org/) provides free, high-quality administrative boundary
data for every country.

### Steps

1. Open your browser and go to:  
   **https://gadm.org/download_country.html**

2. In the search box type **Bangladesh** and click **Download**.

3. Choose **Shapefile** format.  You will download a `.zip` file called
   something like `gadm41_BGD_shp.zip`.

4. Extract the ZIP.  You will find several files at different administrative
   levels:

   | File | Level | Description |
   |------|-------|-------------|
   | `gadm41_BGD_0.*` | Country | National boundary |
   | `gadm41_BGD_1.*` | Division | 8 divisions |
   | `gadm41_BGD_2.*` | District | 64 districts |
   | `gadm41_BGD_3.*` | Upazila | ~492 upazilas ✅ |

5. Copy **all four** upazila-level files into the `shapefiles/` folder:

   ```
   energy-poverty-mapping/
   └── shapefiles/
       ├── gadm41_BGD_3.shp
       ├── gadm41_BGD_3.dbf
       ├── gadm41_BGD_3.shx
       └── gadm41_BGD_3.prj
   ```

6. The scripts will auto-detect the file automatically.

---

## Option 2 – Natural Earth Data

[Natural Earth](https://www.naturalearthdata.com/) provides lower-resolution
administrative boundaries (suitable for overview maps).

1. Go to **https://www.naturalearthdata.com/downloads/10m-cultural-vectors/**
2. Download **Admin 2 – Countries** (10 m scale).
3. Extract and filter features where `ADM0_A3 == "BGD"`.
4. Save the filtered file to `shapefiles/bgd_adm2.shp`.

> **Note**: Natural Earth data has fewer upazilas (uses districts in places).
> GADM is recommended for upazila-level analysis.

---

## Option 3 – Bangladesh Bureau of Statistics (BBS)

The Bangladesh Bureau of Statistics publishes official GIS boundary data.

1. Visit **https://www.bbs.gov.bd/**
2. Navigate to *GIS / Geospatial Data* (look under Publications or Data).
3. Download the **Upazila-level** shapefile.
4. Place the extracted files in `shapefiles/`.

---

## Option 4 – Humanitarian Data Exchange (HDX)

HDX hosts the OCHA Bangladesh Administrative Boundaries dataset.

1. Go to **https://data.humdata.org/dataset/cod-ab-bgd**
2. Download the **Admin Level 3** (Upazila) shapefile or GeoJSON.
3. Place in `shapefiles/` folder.

---

## Validate the Shapefile

After placing the files, run the validation script:

```bash
python setup_and_test_maps.py
```

This will:
- Detect the shapefile automatically
- Check all geometries are valid
- Confirm all upazilas fall within Bangladesh bounds
- Generate test maps to verify everything works

---

## Troubleshooting

### "Shapefile not found"
- Make sure the `.shp`, `.dbf`, `.shx`, and `.prj` files are all in the
  `shapefiles/` folder (not in a subfolder inside it).
- The file name must contain `bgd`, `bangladesh`, `gadm`, or similar.

### "CRS mismatch" warning
- The scripts automatically reproject to WGS84 (EPSG:4326).
- You can ignore this warning.

### "Invalid geometries"
- Run `shapefile_loader.py` to identify problematic features.
- Use `geopandas.make_valid()` or QGIS to fix geometries.

### Maps still show scatter dots
- The shapefile was not detected.  Check the file is in `shapefiles/`.
- Re-run `python setup_and_test_maps.py` to see the exact path being searched.

### "Module not found: geopandas"
```bash
pip install geopandas
```

---

## Required Python Packages

```bash
pip install geopandas folium branca mapclassify
```

---

## File Structure After Setup

```
energy-poverty-mapping/
├── shapefiles/
│   ├── gadm41_BGD_3.shp     ← upazila geometry
│   ├── gadm41_BGD_3.dbf     ← attributes
│   ├── gadm41_BGD_3.shx     ← index
│   └── gadm41_BGD_3.prj     ← projection
├── correct_spatial_mapping.py
├── interactive_folium_maps.py
├── setup_and_test_maps.py
└── example_correct_mapping.py
```

---

## Quick Start (After Downloading Shapefile)

```bash
# 1. Validate setup
python setup_and_test_maps.py

# 2. Generate all maps
python example_correct_mapping.py

# 3. View maps
# Open map_outputs/interactive_map.html in your browser
# PNG maps are in map_outputs/
```
