"""
visualization_config.py - Configuration for Energy Poverty Index visualizations

Defines color schemes, figure sizes, DPI settings, font sizes, and other
styling parameters used consistently across all MEPI visualizations.
"""

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================

# Output directory for PNG files (relative to script location)
OUTPUT_DIR = "visualizations"

# Resolution for saved figures (publication quality)
DPI = 300

# Default image format
IMAGE_FORMAT = "png"

# =============================================================================
# COLORBLIND-FRIENDLY COLOR PALETTES
# =============================================================================
# Based on Wong (2011) Nature Methods colorblind-safe palette

# Poverty category colors
POVERTY_COLORS = {
    "Non-Poor": "#009E73",          # green
    "Moderately Poor": "#E69F00",   # amber
    "Severely Poor": "#D55E00",     # vermillion
}

# Energy dimension colors
DIMENSION_COLORS = {
    "Availability": "#0072B2",    # blue
    "Reliability": "#56B4E9",     # sky blue
    "Adequacy": "#009E73",        # green
    "Quality": "#F0E442",         # yellow
    "Affordability": "#CC79A7",   # pink/purple
}

# Regional zone colors
ZONE_COLORS = {
    "coastal": "#0072B2",
    "char": "#E69F00",
    "haor": "#009E73",
    "hill_tract": "#D55E00",
    "sundarbans": "#56B4E9",
    "plain": "#999999",
    "urban": "#CC79A7",
    "rural": "#F0E442",
}

# Sequential colormap for heatmaps
HEATMAP_CMAP = "YlOrRd"

# Diverging colormap for correlation plots
CORRELATION_CMAP = "RdBu_r"

# =============================================================================
# FIGURE SIZES (width, height) IN INCHES
# =============================================================================

FIGURE_SIZES = {
    "bar_chart_all": (16, 10),
    "bar_chart_top10": (12, 7),
    "histogram": (10, 7),
    "pie_chart": (10, 8),
    "heatmap": (12, 9),
    "boxplot": (12, 7),
    "violin": (12, 7),
    "correlation": (10, 9),
    "radar": (14, 10),
    "stacked_bar": (14, 8),
    "regional": (12, 7),
    "scatter_map": (12, 9),
    "dashboard": (20, 14),
    "regional_summary": (18, 12),
}

# =============================================================================
# FONT SETTINGS
# =============================================================================

FONT_FAMILY = "DejaVu Sans"

FONT_SIZES = {
    "title": 16,
    "subtitle": 13,
    "axis_label": 12,
    "tick_label": 10,
    "legend": 10,
    "annotation": 9,
    "small": 8,
}

# =============================================================================
# MATPLOTLIB STYLE
# =============================================================================

# Style name to apply (tries modern names with fallback)
PLOT_STYLE = "seaborn-v0_8-whitegrid"
PLOT_STYLE_FALLBACK = "seaborn-whitegrid"

# Grid settings
GRID_ALPHA = 0.3
GRID_COLOR = "#cccccc"

# =============================================================================
# CHART LABELS AND TITLES
# =============================================================================

CHART_TITLES = {
    "mepi_scores_by_upazila": "MEPI Scores by Upazila",
    "mepi_distribution": "Distribution of MEPI Scores",
    "poverty_classification_pie": "Energy Poverty Classification",
    "top10_most_poor": "Top 10 Most Energy-Poor Upazilas",
    "top10_least_poor": "Top 10 Least Energy-Poor Upazilas",
    "availability_scores": "Availability Dimension Scores by Upazila",
    "reliability_scores": "Reliability Dimension Scores by Upazila",
    "adequacy_scores": "Adequacy Dimension Scores by Upazila",
    "quality_scores": "Quality Dimension Scores by Upazila",
    "affordability_scores": "Affordability Dimension Scores by Upazila",
    "dimension_heatmap": "Energy Poverty Intensity by Dimension",
    "dimension_boxplots": "Distribution of Dimension Scores",
    "dimension_violin_plots": "Dimension Score Distributions by Region",
    "coastal_analysis": "Coastal Zone – Energy Poverty Analysis",
    "char_islands_analysis": "Char Islands – Energy Poverty Analysis",
    "haor_analysis": "Haor Wetlands – Energy Poverty Analysis",
    "hill_tract_analysis": "Hill Tracts – Energy Poverty Analysis",
    "sundarbans_analysis": "Sundarbans Fringe – Energy Poverty Analysis",
    "urban_rural_comparison": "Urban vs Rural Energy Poverty Comparison",
    "dimension_correlation_heatmap": "Correlation Between Energy Poverty Dimensions",
    "radar_profiles": "Dimensional Energy Poverty Profiles",
    "dimension_contribution": "Dimension Contributions to MEPI Score",
    "spatial_distribution_map": "Spatial Distribution of MEPI Scores",
    "executive_summary": "Energy Poverty Index – Executive Summary",
    "regional_summary": "Regional Energy Poverty Overview",
}

# Axis labels
AXIS_LABELS = {
    "mepi_score": "MEPI Score (0 = least deprived, 1 = most deprived)",
    "upazila": "Upazila",
    "count": "Number of Upazilas",
    "dimension_score": "Deprivation Score (0–1)",
    "frequency": "Frequency",
}

# =============================================================================
# POVERTY THRESHOLD LINES
# =============================================================================

POVERTY_THRESHOLD_MODERATE = 0.33
POVERTY_THRESHOLD_SEVERE = 0.66
THRESHOLD_LINE_STYLE = "--"
THRESHOLD_LINE_WIDTH = 1.5

# =============================================================================
# WATERMARK / ATTRIBUTION
# =============================================================================

FIGURE_ATTRIBUTION = "Energy Poverty Mapping – Bangladesh MEPI Study"

# =============================================================================
# DIMENSIONS LIST
# =============================================================================

DIMENSIONS = ["Availability", "Reliability", "Adequacy", "Quality", "Affordability"]
