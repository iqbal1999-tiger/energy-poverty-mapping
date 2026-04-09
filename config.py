"""
config.py - Configuration settings for the Multidimensional Energy Poverty Index (MEPI)

This module defines the core parameters used in MEPI calculation for Bangladesh,
including dimension definitions, indicator mappings, weights, poverty thresholds,
and regional classifications.
"""

# =============================================================================
# MEPI DIMENSIONS AND INDICATORS
# =============================================================================

# Five core dimensions of energy poverty
DIMENSIONS = [
    "Availability",
    "Reliability",
    "Adequacy",
    "Quality",
    "Affordability",
]

# Indicators for each dimension
# Each indicator entry contains:
#   - column: the column name in the input data
#   - description: human-readable description
#   - higher_is_deprived: True if a higher raw value means MORE deprived
DIMENSION_INDICATORS = {
    "Availability": [
        {
            "column": "electricity_access_rate",
            "description": "Percentage of households with electricity access (%)",
            "higher_is_deprived": False,  # higher access = less deprived
        },
        {
            "column": "clean_cooking_fuel_rate",
            "description": "Percentage of households using clean cooking fuel (%)",
            "higher_is_deprived": False,
        },
        {
            "column": "grid_connection_rate",
            "description": "Percentage of households connected to national grid (%)",
            "higher_is_deprived": False,
        },
    ],
    "Reliability": [
        {
            "column": "hours_supply_per_day",
            "description": "Average hours of electricity supply per day (hours)",
            "higher_is_deprived": False,  # more hours = less deprived
        },
        {
            "column": "outage_frequency_per_month",
            "description": "Average number of outages per month (count)",
            "higher_is_deprived": True,  # more outages = more deprived
        },
        {
            "column": "outage_duration_hours",
            "description": "Average outage duration per event (hours)",
            "higher_is_deprived": True,
        },
    ],
    "Adequacy": [
        {
            "column": "energy_consumption_kwh",
            "description": "Monthly household energy consumption (kWh)",
            "higher_is_deprived": False,  # more consumption = less deprived
        },
        {
            "column": "lighting_hours_per_day",
            "description": "Average hours of lighting service per day (hours)",
            "higher_is_deprived": False,
        },
        {
            "column": "appliance_ownership_index",
            "description": "Index of household appliance ownership (0-1 scale)",
            "higher_is_deprived": False,
        },
    ],
    "Quality": [
        {
            "column": "voltage_fluctuation_rate",
            "description": "Frequency of voltage fluctuations per week (count)",
            "higher_is_deprived": True,  # more fluctuations = more deprived
        },
        {
            "column": "energy_satisfaction_score",
            "description": "Household satisfaction with energy services (1-5 scale)",
            "higher_is_deprived": False,  # higher satisfaction = less deprived
        },
        {
            "column": "indoor_air_quality_index",
            "description": "Indoor air quality index (higher = better air quality)",
            "higher_is_deprived": False,
        },
    ],
    "Affordability": [
        {
            "column": "energy_expenditure_share",
            "description": "Share of household income spent on energy (%)",
            "higher_is_deprived": True,  # higher share = more deprived
        },
        {
            "column": "energy_cost_per_kwh",
            "description": "Effective cost per kWh paid by household (BDT)",
            "higher_is_deprived": True,
        },
        {
            "column": "subsidy_access_rate",
            "description": "Percentage of eligible households accessing energy subsidies (%)",
            "higher_is_deprived": False,  # more subsidy access = less deprived
        },
    ],
}

# =============================================================================
# DIMENSION WEIGHTS
# =============================================================================

# Equal weighting (0.2 each, summing to 1.0) - default scheme
DIMENSION_WEIGHTS_EQUAL = {
    "Availability": 0.2,
    "Reliability": 0.2,
    "Adequacy": 0.2,
    "Quality": 0.2,
    "Affordability": 0.2,
}

# Alternative weighting scheme emphasising availability and affordability
DIMENSION_WEIGHTS_ALT1 = {
    "Availability": 0.30,
    "Reliability": 0.15,
    "Adequacy": 0.20,
    "Quality": 0.10,
    "Affordability": 0.25,
}

# Alternative weighting scheme emphasising reliability and adequacy
DIMENSION_WEIGHTS_ALT2 = {
    "Availability": 0.15,
    "Reliability": 0.25,
    "Adequacy": 0.30,
    "Quality": 0.15,
    "Affordability": 0.15,
}

# Default weight scheme to use
DEFAULT_WEIGHTS = DIMENSION_WEIGHTS_EQUAL

# =============================================================================
# POVERTY THRESHOLDS AND CLASSIFICATION
# =============================================================================

# MEPI score thresholds (0 = no deprivation, 1 = maximum deprivation)
POVERTY_THRESHOLDS = {
    "non_poor": (0.0, 0.33),        # 0.00 – 0.33  non-poor
    "moderate": (0.33, 0.66),       # 0.33 – 0.66  moderately poor
    "severe":   (0.66, 1.0),        # 0.66 – 1.00  severely poor
}

POVERTY_LABELS = {
    "non_poor": "Non-Poor",
    "moderate": "Moderately Poor",
    "severe":   "Severely Poor",
}

# Dimension-level deprivation threshold (score above this = deprived in that dimension)
DIMENSION_DEPRIVATION_THRESHOLD = 0.33

# =============================================================================
# REGIONAL CLASSIFICATIONS FOR BANGLADESH
# =============================================================================

# Administrative divisions
DIVISIONS = [
    "Dhaka",
    "Chittagong",
    "Rajshahi",
    "Khulna",
    "Barishal",
    "Sylhet",
    "Rangpur",
    "Mymensingh",
]

# Special geographic/ecological zones used for sub-national analysis
GEOGRAPHIC_ZONES = {
    "coastal": {
        "description": "Coastal and delta upazilas with tidal flooding risk",
        "districts": [
            "Cox's Bazar", "Noakhali", "Lakshmipur", "Feni", "Chittagong",
            "Bagerhat", "Satkhira", "Khulna", "Barguna", "Patuakhali",
            "Bhola", "Barishal", "Pirojpur", "Jhalokati",
        ],
    },
    "char": {
        "description": "River-island (char) areas prone to erosion and flooding",
        "districts": [
            "Sirajganj", "Gaibandha", "Jamalpur", "Kurigram", "Nilphamari",
            "Bogura", "Naogaon",
        ],
    },
    "haor": {
        "description": "Haor (seasonal wetland) basin areas",
        "districts": [
            "Sunamganj", "Habiganj", "Moulvibazar", "Netrokona", "Kishorganj",
        ],
    },
    "hill_tract": {
        "description": "Chittagong Hill Tracts – forested and mountainous",
        "districts": [
            "Rangamati", "Khagrachhari", "Bandarban",
        ],
    },
    "sundarbans": {
        "description": "Sundarbans mangrove buffer zone",
        "districts": [
            "Satkhira", "Khulna", "Bagerhat",
        ],
    },
    "plain": {
        "description": "General floodplain and agricultural areas",
        "districts": [],   # default zone for districts not listed above
    },
}

# =============================================================================
# DATA CONFIGURATION
# =============================================================================

# Expected column for upazila identifier
UPAZILA_ID_COLUMN = "upazila_id"
UPAZILA_NAME_COLUMN = "upazila_name"
DISTRICT_COLUMN = "district"
DIVISION_COLUMN = "division"

# All indicator columns (auto-derived from DIMENSION_INDICATORS)
INDICATOR_COLUMNS = [
    ind["column"]
    for indicators in DIMENSION_INDICATORS.values()
    for ind in indicators
]

# Missing value handling strategy: "mean", "median", or "drop"
MISSING_VALUE_STRATEGY = "mean"

# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

OUTPUT_COLUMNS_ORDER = [
    UPAZILA_ID_COLUMN,
    UPAZILA_NAME_COLUMN,
    DISTRICT_COLUMN,
    DIVISION_COLUMN,
    "mepi_score",
    "poverty_category",
    "Availability_score",
    "Reliability_score",
    "Adequacy_score",
    "Quality_score",
    "Affordability_score",
    "n_dimensions_deprived",
]
