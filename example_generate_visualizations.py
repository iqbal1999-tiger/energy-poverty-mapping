"""
example_generate_visualizations.py - Example script for MEPI visualization

Demonstrates how to:
  1. Run the full visualization pipeline with default settings
  2. Generate only specific charts
  3. Customise output directory, DPI, and data source
  4. Work with pre-calculated MEPI results

Run from the repository root:
    python example_generate_visualizations.py
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Example 1: One-command – generate everything
# ─────────────────────────────────────────────────────────────────────────────

def example_1_generate_all():
    """Generate all 25+ visualizations from sample_data.csv with one call."""
    print("\n" + "=" * 60)
    print("Example 1: Generate ALL visualizations")
    print("=" * 60)

    from generate_all_visualizations import run

    saved = run(
        data_path="sample_data.csv",
        output_dir="visualizations",
        dpi=300,
    )
    print(f"✓ Saved {len(saved)} PNG files to visualizations/")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Example 2: Generate specific charts only
# ─────────────────────────────────────────────────────────────────────────────

def example_2_specific_charts():
    """Generate only a subset of charts (e.g., for a quick preview)."""
    print("\n" + "=" * 60)
    print("Example 2: Generate specific charts")
    print("=" * 60)

    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")

    from mepi_calculator import MEPICalculator
    from config import GEOGRAPHIC_ZONES
    from visualization_generator import MEPIVisualizationGenerator

    # Load and calculate
    df = pd.read_csv("sample_data.csv")
    calc = MEPICalculator()
    results = calc.calculate(df)

    gen = MEPIVisualizationGenerator(
        results,
        output_dir="visualizations",
        dpi=300,
        geographic_zones=GEOGRAPHIC_ZONES,
    )

    # Call individual methods
    paths = []
    for method_name in [
        "generate_mepi_scores_by_upazila",
        "generate_poverty_classification_pie",
        "generate_top10_most_poor",
        "generate_dimension_heatmap",
        "generate_radar_profiles",
    ]:
        method = getattr(gen, method_name)
        try:
            path = method()
            if path:
                paths.append(path)
                print(f"  ✓ {path}")
        except Exception as exc:
            print(f"  ✗ {method_name}: {exc}")

    print(f"✓ Saved {len(paths)} targeted charts.")
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# Example 3: Custom output folder and DPI
# ─────────────────────────────────────────────────────────────────────────────

def example_3_custom_output():
    """Save visualizations to a custom folder at a different DPI."""
    print("\n" + "=" * 60)
    print("Example 3: Custom output folder and DPI")
    print("=" * 60)

    from generate_all_visualizations import run

    saved = run(
        data_path="sample_data.csv",
        output_dir="visualizations",   # same folder; change to taste
        dpi=150,                        # lower DPI for faster preview
    )
    print(f"✓ Saved {len(saved)} files at 150 DPI.")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Example 4: Use a custom data file
# ─────────────────────────────────────────────────────────────────────────────

def example_4_custom_data(data_path: str):
    """Load a custom data file and generate visualizations."""
    print("\n" + "=" * 60)
    print(f"Example 4: Custom data file ({data_path})")
    print("=" * 60)

    if not os.path.exists(data_path):
        print(f"  ✗ File not found: {data_path}; skipping example 4.")
        return []

    from generate_all_visualizations import run

    saved = run(
        data_path=data_path,
        output_dir="visualizations",
        dpi=300,
    )
    print(f"✓ Generated {len(saved)} visualizations from {data_path}")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Example 5: Access individual figure objects without saving
# ─────────────────────────────────────────────────────────────────────────────

def example_5_figure_objects():
    """
    Obtain matplotlib Figure objects directly for further customisation
    before saving (e.g., add annotations, change title, etc.).
    """
    print("\n" + "=" * 60)
    print("Example 5: Manipulate figure objects before saving")
    print("=" * 60)

    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from mepi_calculator import MEPICalculator
    from visualization import MEPIVisualizer   # existing module

    df = pd.read_csv("sample_data.csv")
    calc = MEPICalculator()
    results = calc.calculate(df)

    viz = MEPIVisualizer(results)
    fig = viz.plot_mepi_bar_chart(top_n=10, title="My Custom Title")

    # Add a custom annotation
    fig.axes[0].text(
        0.5, -0.15,
        "Source: Bangladesh Energy Poverty Survey",
        ha="center", transform=fig.axes[0].transAxes,
        fontsize=9, color="#555555",
    )

    output_path = os.path.join("visualizations", "custom_bar_chart.png")
    os.makedirs("visualizations", exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved customised figure to {output_path}")
    return [output_path]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MEPI Visualization Generator – Examples")
    print("=" * 60)
    print("Running Example 1 (full generation) by default.")
    print("Edit this file to run other examples.\n")

    example_1_generate_all()
