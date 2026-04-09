"""
map_config.py - Configuration for spatio-temporal MEPI mapping

Defines colour scales, map projection settings, file paths for shapefiles,
animation parameters, and all shared constants for the mapping pipeline.
"""

import os

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_OUTPUTS_DIR = os.path.join(BASE_DIR, "map_outputs")
SHAPEFILES_DIR = os.path.join(BASE_DIR, "shapefiles")

# Expected shapefile / GeoJSON paths (place your files here)
UPAZILA_SHAPEFILE = os.path.join(SHAPEFILES_DIR, "bangladesh_upazilas.shp")
UPAZILA_GEOJSON = os.path.join(SHAPEFILES_DIR, "bangladesh_upazilas.geojson")
DISTRICT_GEOJSON = os.path.join(SHAPEFILES_DIR, "bangladesh_districts.geojson")

# Output file names
OUTPUT_FILES = {
    "spatial_mepi": "spatial_mepi_map.png",
    "availability": "availability_map.png",
    "reliability": "reliability_map.png",
    "adequacy": "adequacy_map.png",
    "quality": "quality_map.png",
    "affordability": "affordability_map.png",
    "hotspot": "hotspot_map.png",
    "regional_classification": "regional_classification_map.png",
    "temporal_comparison": "temporal_comparison_2020_2025.png",
    "poverty_change": "poverty_change_map.png",
    "interactive_map": "interactive_map.html",
    "temporal_animation": "temporal_animation.gif",
}

# =============================================================================
# MAP PROJECTION
# =============================================================================

# WGS84 geographic coordinate system (EPSG:4326) used throughout
CRS_WGS84 = "EPSG:4326"

# Bangladesh bounding box [min_lon, min_lat, max_lon, max_lat]
BANGLADESH_BOUNDS = [88.0, 20.5, 92.7, 26.7]

# Map centre for Bangladesh
BANGLADESH_CENTER = [23.7, 90.4]  # [lat, lon]

# Default figure DPI for PNG outputs
MAP_DPI = 300

# Figure size (width, height) in inches for full-page map
MAP_FIGURE_SIZE = (12, 10)
MAP_FIGURE_SIZE_WIDE = (16, 10)

# =============================================================================
# COLOUR SCALES
# =============================================================================

# Primary MEPI choropleth colour map
# Red = high deprivation (severe poverty), Green = low deprivation (non-poor)
MEPI_COLORMAP = "RdYlGn_r"

# Discrete colours for poverty categories
POVERTY_COLORS = {
    "Non-Poor": "#2ecc71",          # green
    "Moderately Poor": "#f39c12",   # amber
    "Severely Poor": "#e74c3c",     # red
}

# Geographic zone colours
ZONE_COLORS = {
    "coastal": "#3498db",       # blue
    "char": "#e67e22",          # orange
    "haor": "#9b59b6",          # purple
    "hill_tract": "#1abc9c",    # teal
    "sundarbans": "#27ae60",    # dark green
    "plain": "#95a5a6",         # grey
    "unknown": "#bdc3c7",       # light grey
}

# Hotspot colour
HOTSPOT_COLOR = "#c0392b"   # dark red
NON_HOTSPOT_COLOR = "#ecf0f1"  # near-white

# Change map colours
IMPROVING_COLOR = "#27ae60"    # green – poverty decreasing
WORSENING_COLOR = "#c0392b"    # red   – poverty increasing
STABLE_COLOR = "#f39c12"       # amber – little change

# Dimension colormaps (sequential, suited for deprivation scores)
DIMENSION_COLORMAPS = {
    "Availability": "Reds",
    "Reliability": "Oranges",
    "Adequacy": "Purples",
    "Quality": "Blues",
    "Affordability": "YlOrRd",
}

# =============================================================================
# POVERTY THRESHOLDS (must match config.py)
# =============================================================================

THRESHOLD_MODERATE = 0.33
THRESHOLD_SEVERE = 0.66

# =============================================================================
# LEGEND & LABELS
# =============================================================================

POVERTY_LABELS = {
    "Non-Poor": f"Non-Poor (MEPI < {THRESHOLD_MODERATE})",
    "Moderately Poor": f"Moderately Poor ({THRESHOLD_MODERATE}–{THRESHOLD_SEVERE})",
    "Severely Poor": f"Severely Poor (MEPI > {THRESHOLD_SEVERE})",
}

DIMENSION_LABELS = {
    "Availability": "Energy Availability",
    "Reliability": "Energy Reliability",
    "Adequacy": "Energy Adequacy",
    "Quality": "Energy Quality",
    "Affordability": "Energy Affordability",
}

# =============================================================================
# ANIMATION PARAMETERS
# =============================================================================

ANIMATION_FPS = 1           # frames per second for GIF
ANIMATION_LOOP = 0        # 0 = infinite loop
ANIMATION_DURATION_S = 1  # seconds per frame (used directly in imageio.mimsave)

# =============================================================================
# INTERACTIVE MAP SETTINGS
# =============================================================================

FOLIUM_TILES = "CartoDB positron"
FOLIUM_ZOOM_START = 7
FOLIUM_MIN_ZOOM = 6
FOLIUM_MAX_ZOOM = 14

# Marker style for scatter/circle maps
MARKER_RADIUS = 8
MARKER_WEIGHT = 1
MARKER_FILL_OPACITY = 0.8

# =============================================================================
# APPROXIMATE UPAZILA COORDINATES (latitude, longitude)
# Covers the 20 upazilas in sample_data.csv plus common Bangladesh locations.
# Add or update entries as required when real shapefile data is available.
# =============================================================================

UPAZILA_COORDINATES = {
    # Cox's Bazar / Chittagong coastal
    "Teknaf": (20.86, 92.30),
    "Ukhia": (21.22, 92.11),
    "Rangunia": (22.49, 92.03),
    "Patiya": (22.30, 91.98),
    # Dhaka
    "Dohar": (23.59, 90.14),
    "Nawabganj": (23.61, 90.02),
    "Savar": (23.84, 90.27),
    "Keraniganj": (23.71, 90.38),
    # Khulna / Sundarbans
    "Kaliganj": (22.41, 89.11),
    "Shyamnagar": (22.15, 89.03),
    # Sylhet / Haor
    "Sunamganj Sadar": (25.07, 91.40),
    "Tahirpur": (25.10, 91.20),
    # Rangpur / Char
    "Fulchhari": (25.16, 89.65),
    "Saghata": (25.09, 89.85),
    # Rajshahi
    "Rajshahi Sadar": (24.37, 88.60),
    "Godagari": (24.52, 88.42),
    # Bandarban Hill Tracts
    "Bandarban Sadar": (22.19, 92.22),
    "Rowangchhari": (22.08, 92.28),
    # Barishal
    "Barishal Sadar": (22.70, 90.37),
    "Muladi": (22.61, 90.51),
}

# =============================================================================
# GEOGRAPHIC ZONE METADATA (for legend and classification maps)
# =============================================================================

ZONE_METADATA = {
    "coastal": {
        "label": "Coastal Zone",
        "description": "Low-lying areas along the Bay of Bengal coast",
        "color": ZONE_COLORS["coastal"],
    },
    "char": {
        "label": "Char Islands",
        "description": "River chars and floodplain islands",
        "color": ZONE_COLORS["char"],
    },
    "haor": {
        "label": "Haor Basin",
        "description": "Northeast wetland / haor region",
        "color": ZONE_COLORS["haor"],
    },
    "hill_tract": {
        "label": "Hill Tracts",
        "description": "Chittagong Hill Tracts (CHT)",
        "color": ZONE_COLORS["hill_tract"],
    },
    "sundarbans": {
        "label": "Sundarbans",
        "description": "Mangrove forest fringe zone",
        "color": ZONE_COLORS["sundarbans"],
    },
    "plain": {
        "label": "Plain",
        "description": "Mainland agricultural plains",
        "color": ZONE_COLORS["plain"],
    },
}
