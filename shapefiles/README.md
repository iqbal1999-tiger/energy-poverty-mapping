# shapefiles/

Place Bangladesh administrative boundary files here before running the mapping scripts.

## Required Files

| File | Description |
|------|-------------|
| `bangladesh_upazilas.geojson` | Upazila-level boundaries (recommended) |
| `bangladesh_upazilas.shp` | Shapefile alternative (+ .dbf, .shx, .prj) |
| `bangladesh_districts.geojson` | District boundaries (optional) |

## Where to Download

- **Bangladesh Bureau of Statistics (BBS):** https://www.bbs.gov.bd/
- **OCHA HDX (Humanitarian Data Exchange):** https://data.humdata.org/dataset/cod-ab-bgd
- **GADM (Global Administrative Areas):** https://gadm.org/download_country.html
  - Select Bangladesh → Level 3 (Upazila)

## Column Requirements

The shapefile / GeoJSON **must** contain an upazila name column so it can be
matched to the MEPI results.  Common column names accepted by the merging
functions: `upazila_name`, `ADM3_EN`, `Name_3`.

Update `data_preparation_spatial.SpatialDataPrep.merge_with_shapefile()` with
the correct `shape_name_col` argument if your file uses a different column.

## Without Shapefiles

All mapping scripts work without shapefiles.  When no shapefile is found the
scripts fall back to proportional-circle maps using the approximate upazila
coordinates stored in `map_config.UPAZILA_COORDINATES`.
