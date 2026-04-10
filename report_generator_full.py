"""
report_generator_full.py - Complete orchestration of the MEPI report generation pipeline.

This module ties together all report generation components:
  - BibliographyManager  (citation management)
  - ChartGenerator       (charts and graphs)
  - PDFReportBuilder     (PDF output)
  - DOCXReportBuilder    (DOCX output)

It also resolves spatial map paths from the configured directory and writes
a plain-text summary file.

Usage
-----
    from report_generator_full import FullReportGenerator
    gen = FullReportGenerator(results_df)
    paths = gen.generate()
    # paths is a dict: {"pdf": "...", "docx": "...", "summary": "..."}
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from bibliography_manager import BibliographyManager
from chart_graph_generator import ChartGenerator
from report_config import (
    REPORT_TITLE,
    REPORT_OUTPUT_DIR,
    FIGURES_SUBFOLDER,
    SPATIAL_MAPS_DIR,
    CHARTS_OUTPUT_DIR,
    CITATION_STYLE,
    GENERATE_PDF,
    GENERATE_DOCX,
    GENERATE_SUMMARY_TXT,
    REPORT_YEAR,
)


# Known spatial map filenames (keys map to display labels)
_SPATIAL_MAP_FILES = {
    "mepi_spatial_map": "mepi_spatial_map.png",
    "availability_map": "availability_map.png",
    "reliability_map": "reliability_map.png",
    "adequacy_map": "adequacy_map.png",
    "quality_map": "quality_map.png",
    "affordability_map": "affordability_map.png",
    "hotspot_map": "hotspot_map.png",         # optional
}


class FullReportGenerator:
    """
    Orchestrate the complete MEPI report generation pipeline.

    Parameters
    ----------
    results_df : pd.DataFrame
        Full MEPI results from ``MEPICalculator.calculate()``.
    output_dir : str, optional
        Override the report output directory (default: ``REPORT_OUTPUT_DIR``).
    spatial_maps_dir : str, optional
        Override the spatial maps directory (default: ``SPATIAL_MAPS_DIR``).
    citation_style : str, optional
        Override citation style: ``"APA"``, ``"Harvard"``, or ``"IEEE"``
        (default: ``CITATION_STYLE``).
    """

    def __init__(
        self,
        results_df: pd.DataFrame,
        output_dir: Optional[str] = None,
        spatial_maps_dir: Optional[str] = None,
        citation_style: Optional[str] = None,
    ):
        self.df = results_df.copy()
        self.output_dir = output_dir or REPORT_OUTPUT_DIR
        self.spatial_maps_dir = spatial_maps_dir or SPATIAL_MAPS_DIR
        self.citation_style = citation_style or CITATION_STYLE

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, FIGURES_SUBFOLDER), exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1: Resolve spatial map paths
    # ------------------------------------------------------------------

    def _resolve_spatial_maps(self) -> Dict[str, str]:
        """Build a dict of map_key → absolute file path for spatial maps."""
        paths: Dict[str, str] = {}
        for key, filename in _SPATIAL_MAP_FILES.items():
            candidate = os.path.join(self.spatial_maps_dir, filename)
            if os.path.isfile(candidate):
                paths[key] = candidate
                print(f"  ✓  Spatial map found: {filename}")
            else:
                print(f"  –  Spatial map missing (placeholder will be used): {filename}")
        return paths

    # ------------------------------------------------------------------
    # Step 2: Generate charts
    # ------------------------------------------------------------------

    def _generate_charts(self) -> Dict[str, str]:
        """Run the ChartGenerator and return paths dict."""
        chart_dir = CHARTS_OUTPUT_DIR
        cg = ChartGenerator(self.df, output_dir=chart_dir)
        return cg.generate_all()

    # ------------------------------------------------------------------
    # Step 3: Build PDF
    # ------------------------------------------------------------------

    def _build_pdf(
        self,
        chart_paths: Dict[str, str],
        spatial_map_paths: Dict[str, str],
        bib: BibliographyManager,
    ) -> Optional[str]:
        """Build the PDF report and return its path."""
        try:
            from pdf_report_builder import PDFReportBuilder
        except ImportError as exc:
            print(f"  ✗  PDF builder import failed: {exc}")
            return None

        filename = f"Energy_Poverty_Index_Report_{REPORT_YEAR}.pdf"
        output_path = os.path.join(self.output_dir, filename)

        try:
            builder = PDFReportBuilder(
                results_df=self.df,
                chart_paths=chart_paths,
                spatial_map_paths=spatial_map_paths,
                bib_manager=bib,
            )
            return builder.build(output_path)
        except Exception as exc:
            print(f"  ✗  PDF generation failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Step 4: Build DOCX
    # ------------------------------------------------------------------

    def _build_docx(
        self,
        chart_paths: Dict[str, str],
        spatial_map_paths: Dict[str, str],
        bib: BibliographyManager,
    ) -> Optional[str]:
        """Build the DOCX report and return its path."""
        try:
            from docx_report_builder import DOCXReportBuilder
        except ImportError as exc:
            print(f"  ✗  DOCX builder import failed: {exc}")
            return None

        filename = f"Energy_Poverty_Index_Report_{REPORT_YEAR}.docx"
        output_path = os.path.join(self.output_dir, filename)

        try:
            builder = DOCXReportBuilder(
                results_df=self.df,
                chart_paths=chart_paths,
                spatial_map_paths=spatial_map_paths,
                bib_manager=bib,
            )
            return builder.build(output_path)
        except Exception as exc:
            print(f"  ✗  DOCX generation failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Step 5: Write summary text file
    # ------------------------------------------------------------------

    def _write_summary(
        self,
        chart_paths: Dict[str, str],
        spatial_map_paths: Dict[str, str],
        pdf_path: Optional[str],
        docx_path: Optional[str],
    ) -> str:
        """Write a plain-text summary file and return its path."""
        summary_path = os.path.join(self.output_dir, "report_summary.txt")

        mean_mepi = self.df["mepi_score"].mean()
        n = len(self.df)
        worst = self.df.nlargest(1, "mepi_score").iloc[0]
        best = self.df.nsmallest(1, "mepi_score").iloc[0]
        name_col = "upazila_name" if "upazila_name" in self.df.columns else self.df.columns[0]

        lines = [
            "=" * 70,
            REPORT_TITLE,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 70,
            "",
            "REPORT FILES",
            "-" * 40,
            f"PDF:  {pdf_path or 'Not generated'}",
            f"DOCX: {docx_path or 'Not generated'}",
            "",
            "KEY STATISTICS",
            "-" * 40,
            f"Total upazilas analysed: {n}",
            f"Mean MEPI score:         {mean_mepi:.4f}",
            f"Std deviation:           {self.df['mepi_score'].std():.4f}",
            f"Min MEPI score:          {self.df['mepi_score'].min():.4f}",
            f"Max MEPI score:          {self.df['mepi_score'].max():.4f}",
            f"Most deprived:           {worst[name_col]} (MEPI={worst['mepi_score']:.3f})",
            f"Least deprived:          {best[name_col]} (MEPI={best['mepi_score']:.3f})",
        ]

        if "poverty_category" in self.df.columns:
            lines += ["", "POVERTY CATEGORIES", "-" * 40]
            for cat in ["Severely Poor", "Moderately Poor", "Non-Poor"]:
                count = (self.df["poverty_category"] == cat).sum()
                pct = round(count / n * 100, 1)
                lines.append(f"{cat:20s}: {count} upazilas ({pct}%)")

        lines += ["", "SPATIAL MAPS", "-" * 40]
        for key, path in spatial_map_paths.items():
            lines.append(f"{key:25s}: {path}")
        if not spatial_map_paths:
            lines.append("No spatial maps found in: " + self.spatial_maps_dir)

        lines += ["", "CHARTS GENERATED", "-" * 40]
        for key, path in chart_paths.items():
            lines.append(f"{key:25s}: {path}")

        lines += ["", "=" * 70]

        content = "\n".join(lines)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Summary saved: {summary_path}")
        return summary_path

    # ------------------------------------------------------------------
    # Main generate method
    # ------------------------------------------------------------------

    def generate(self) -> Dict[str, Optional[str]]:
        """
        Run the full report generation pipeline.

        Returns
        -------
        dict
            Keys: ``"pdf"``, ``"docx"``, ``"summary"``, ``"charts"``,
            ``"spatial_maps"``.  Values are file paths or dicts of paths.
        """
        print("\n" + "=" * 60)
        print(f"  MEPI FULL REPORT GENERATOR")
        print(f"  {REPORT_TITLE}")
        print("=" * 60)

        # --- Step 1: Resolve spatial maps ---
        print("\n[1/5] Resolving spatial map files …")
        spatial_map_paths = self._resolve_spatial_maps()

        # --- Step 2: Generate charts ---
        print("\n[2/5] Generating charts and graphs …")
        chart_paths = self._generate_charts()

        # --- Step 3: Initialise bibliography ---
        print("\n[3/5] Initialising bibliography …")
        bib = BibliographyManager(style=self.citation_style)

        # --- Step 4: Build PDF ---
        pdf_path: Optional[str] = None
        if GENERATE_PDF:
            print("\n[4/5] Building PDF report …")
            pdf_path = self._build_pdf(chart_paths, spatial_map_paths, bib)
        else:
            print("\n[4/5] PDF generation disabled (set GENERATE_PDF=True in report_config.py)")

        # --- Step 5: Build DOCX ---
        docx_path: Optional[str] = None
        if GENERATE_DOCX:
            print("\n[5/5] Building DOCX report …")
            # Re-initialise bibliography so that DOCX tracks its own citations
            bib_docx = BibliographyManager(style=self.citation_style)
            docx_path = self._build_docx(chart_paths, spatial_map_paths, bib_docx)
        else:
            print("\n[5/5] DOCX generation disabled (set GENERATE_DOCX=True in report_config.py)")

        # --- Summary ---
        print("\nWriting summary file …")
        summary_path = self._write_summary(chart_paths, spatial_map_paths, pdf_path, docx_path)

        print("\n" + "=" * 60)
        print("  REPORT GENERATION COMPLETE")
        print("=" * 60)
        if pdf_path:
            print(f"  PDF  → {pdf_path}")
        if docx_path:
            print(f"  DOCX → {docx_path}")
        print(f"  Summary → {summary_path}")
        print("=" * 60 + "\n")

        return {
            "pdf": pdf_path,
            "docx": docx_path,
            "summary": summary_path,
            "charts": chart_paths,
            "spatial_maps": spatial_map_paths,
        }
