# Energy Poverty Mapping – Bangladesh MEPI Calculation Scripts

> **Spatial Mapping of Energy Poverty in Bangladesh**  
> Python scripts for calculating the **Multidimensional Energy Poverty Index (MEPI)** at the upazila level.

---

## Table of Contents

1. [Overview](#overview)
2. [Methodology](#methodology)
3. [Project Structure](#project-structure)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Sample Data](#sample-data)
7. [Output](#output)
8. [Customisation](#customisation)
9. [Requirements](#requirements)

---

## Overview

This toolkit calculates the Multidimensional Energy Poverty Index (MEPI) for
Bangladesh upazilas across **five dimensions** of energy poverty:

| Dimension | What it measures |
|-----------|-----------------|
| **Availability** | Household access to electricity and clean cooking fuel |
| **Reliability** | Hours of supply, frequency and duration of outages |
| **Adequacy** | Energy consumption, lighting hours, appliance ownership |
| **Quality** | Voltage stability, indoor air quality, satisfaction |
| **Affordability** | Energy expenditure share, cost per kWh, subsidy access |

Each dimension is scored from **0** (no deprivation) to **1** (maximum deprivation),
and upazilas are classified as:

| Category | MEPI Score |
|----------|-----------|
| **Non-Poor** | 0.00 – 0.33 |
| **Moderately Poor** | 0.33 – 0.66 |
| **Severely Poor** | 0.66 – 1.00 |

---

## Methodology

### Step 1 – Indicator Normalisation

Each indicator is normalised to a **deprivation score** in [0, 1] using min-max scaling.
The direction of deprivation is accounted for:

- *Higher raw value = more deprived* (e.g. outage frequency) → score = (value - min) / (max - min)  
- *Lower raw value = more deprived* (e.g. electricity access rate) → score = (max - value) / (max - min)

### Step 2 – Dimension Score

The dimension score is the **unweighted mean** of the normalised indicator scores within that dimension.

### Step 3 – MEPI Score

The overall MEPI is the **weighted average** of dimension scores:

```
MEPI = Σ (weight_d × dimension_score_d)   for d in {Availability, Reliability, Adequacy, Quality, Affordability}
```

Default weights are **equal (0.2 each)**.  Alternative schemes are provided in `config.py`.

### Step 4 – Classification

Upazilas are classified into poverty categories based on configurable thresholds (default: 0.33 / 0.66).

---

## Project Structure

```
energy-poverty-mapping/
├── config.py                  # Dimensions, weights, thresholds, regional settings
├── mepi_calculator.py         # Core MEPI calculation engine
├── data_utils.py              # Data loading, validation, normalisation, aggregation
├── analysis.py                # Statistics, ranking, and export functions
├── example_mepi_analysis.py   # End-to-end worked example
├── sample_data.csv            # 20 sample Bangladesh upazilas
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the example

```bash
python example_mepi_analysis.py
```

This will:
- Load `sample_data.csv`
- Validate and pre-process the data
- Calculate MEPI scores with equal weights
- Print a summary report to the console
- Export results to `output/mepi_results.csv` and `output/mepi_results.xlsx`
- Run a sensitivity analysis with two alternative weighting schemes

### 3. Use with your own data

```python
from data_utils import load_data, validate_data, handle_missing_values
from mepi_calculator import MEPICalculator
from analysis import export_results

# Load your data (CSV or Excel)
df = load_data("your_data.csv")

# Validate and clean
df = validate_data(df)
df = handle_missing_values(df)

# Calculate MEPI
calc = MEPICalculator()
results = calc.calculate(df)

# Export
export_results(results, "output/my_results.xlsx")
```

---

## Configuration

All parameters are in **`config.py`**:

| Parameter | Description |
|-----------|-------------|
| `DIMENSIONS` | List of five dimension names |
| `DIMENSION_INDICATORS` | Indicator definitions per dimension |
| `DEFAULT_WEIGHTS` | Equal weights (0.2 each) |
| `DIMENSION_WEIGHTS_ALT1` | Alternative weights (availability + affordability focus) |
| `DIMENSION_WEIGHTS_ALT2` | Alternative weights (reliability + adequacy focus) |
| `POVERTY_THRESHOLDS` | Score cutoffs for poverty classification |
| `MISSING_VALUE_STRATEGY` | `"mean"`, `"median"`, or `"drop"` |
| `GEOGRAPHIC_ZONES` | Coastal, char, haor, hill tract, Sundarbans zone definitions |

### Adding a custom indicator

1. Add your column name to the appropriate dimension in `DIMENSION_INDICATORS`:

```python
DIMENSION_INDICATORS["Reliability"].append({
    "column": "my_new_indicator",
    "description": "Description of my indicator",
    "higher_is_deprived": True,
})
```

2. Ensure the column exists in your input data.

### Custom weights

```python
from mepi_calculator import MEPICalculator

my_weights = {
    "Availability":   0.30,
    "Reliability":    0.20,
    "Adequacy":       0.20,
    "Quality":        0.10,
    "Affordability":  0.20,
}
calc = MEPICalculator(weights=my_weights)
results = calc.calculate(df)
```

---

## Sample Data

`sample_data.csv` contains **20 fictional Bangladesh upazilas** spanning all eight divisions
and multiple geographic zones (coastal, char, haor, hill tract, plain).

Required columns in your own data:

| Column | Type | Description |
|--------|------|-------------|
| `upazila_id` | str | Unique identifier |
| `upazila_name` | str | Name of the upazila |
| `district` | str | District name |
| `division` | str | Division name |
| `electricity_access_rate` | float | % households with electricity |
| `clean_cooking_fuel_rate` | float | % using clean cooking fuel |
| `grid_connection_rate` | float | % connected to national grid |
| `hours_supply_per_day` | float | Avg. electricity supply hours/day |
| `outage_frequency_per_month` | float | Avg. outages per month |
| `outage_duration_hours` | float | Avg. outage duration (hours) |
| `energy_consumption_kwh` | float | Monthly household kWh |
| `lighting_hours_per_day` | float | Avg. lighting hours/day |
| `appliance_ownership_index` | float | Appliance ownership index (0–1) |
| `voltage_fluctuation_rate` | float | Voltage fluctuations per week |
| `energy_satisfaction_score` | float | Satisfaction score (1–5) |
| `indoor_air_quality_index` | float | Air quality index (higher = better) |
| `energy_expenditure_share` | float | % income spent on energy |
| `energy_cost_per_kwh` | float | Effective cost per kWh (BDT) |
| `subsidy_access_rate` | float | % eligible households with subsidy |

---

## Output

Running `example_mepi_analysis.py` creates an `output/` directory with:

| File | Contents |
|------|----------|
| `mepi_results.csv` | Full results for all upazilas |
| `mepi_results.xlsx` | Multi-sheet workbook: results + district + division summaries |
| `mepi_summary_table.csv` | Publication-ready ranked table |
| `sensitivity_comparison.csv` | MEPI scores under three weighting schemes |

---

## Customisation

- **Regional analysis**: Use `data_utils.assign_geographic_zone()` and `analysis.aggregate_by_zone()`.
- **Aggregation**: If you have household-level data, use `data_utils.aggregate_to_upazila()` first.
- **Sensitivity analysis**: Use `MEPICalculator.calculate_with_sensitivity()` with a list of weight schemes.

---

## Requirements

- Python 3.9+
- `numpy >= 1.24`
- `pandas >= 2.0`
- `openpyxl >= 3.1` (for Excel export)

Install with:

```bash
pip install -r requirements.txt
```

---

## Citation

If you use these scripts in your research, please cite appropriately and acknowledge
the data sources (World Bank, IEA, BBS, BPDB, etc.) used to populate the indicators.

