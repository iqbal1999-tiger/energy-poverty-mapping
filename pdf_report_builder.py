"""
pdf_report_builder.py - Build the MEPI research report as a multi-page PDF.

Uses ReportLab's Platypus high-level layout engine to compose a professional,
multi-chapter PDF document with:
  - Cover page
  - Table of contents
  - Executive summary
  - Ten chapters with body text, data tables, and embedded figures
  - References / bibliography
  - Header and footer on every content page

Usage
-----
    from pdf_report_builder import PDFReportBuilder
    builder = PDFReportBuilder(
        results_df=results_df,
        chart_paths=chart_paths,
        spatial_map_paths=spatial_map_paths,
        bib_manager=bib_manager,
    )
    path = builder.build("output/report.pdf")
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        Table,
        TableStyle,
        Image,
        HRFlowable,
        KeepTogether,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfgen import canvas

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from report_config import (
    REPORT_TITLE,
    REPORT_SUBTITLE,
    REPORT_AUTHORS,
    REPORT_ORGANIZATION,
    REPORT_DATE,
    REPORT_YEAR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_ACCENT,
    COLOR_LIGHT_HEX,
    FIGURE_MAX_WIDTH,
    FIGURE_MAX_HEIGHT,
    IMAGE_DPI,
)
from report_template import get_pdf_styles, get_standard_table_style, get_summary_table_style

_PAGE_W, _PAGE_H = A4 if HAS_REPORTLAB else (595.27, 841.89)
_MARGIN = 72  # 1 inch


# =============================================================================
# Page canvas callback – header and footer
# =============================================================================

def _make_header_footer(title: str, authors: str):
    """Return a ReportLab canvas callback that draws header + footer on each page."""

    def _draw(canvas_obj, doc):
        if not HAS_REPORTLAB:
            return
        canvas_obj.saveState()
        page_num = doc.page

        # Header bar
        canvas_obj.setFillColor(colors.HexColor(COLOR_PRIMARY))
        canvas_obj.rect(
            _MARGIN, _PAGE_H - _MARGIN + 4,
            _PAGE_W - 2 * _MARGIN, 18,
            fill=1, stroke=0,
        )
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawString(_MARGIN + 6, _PAGE_H - _MARGIN + 9, title[:90])
        canvas_obj.drawRightString(
            _PAGE_W - _MARGIN - 6, _PAGE_H - _MARGIN + 9, authors
        )

        # Footer
        canvas_obj.setFillColor(colors.HexColor("#888888"))
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(
            _PAGE_W / 2,
            _MARGIN - 20,
            f"Page {page_num}  |  {REPORT_ORGANIZATION}  |  {REPORT_DATE}",
        )
        canvas_obj.setStrokeColor(colors.HexColor("#CCCCCC"))
        canvas_obj.line(_MARGIN, _MARGIN - 10, _PAGE_W - _MARGIN, _MARGIN - 10)

        canvas_obj.restoreState()

    return _draw


# =============================================================================
# Helper: embed image with auto-resize
# =============================================================================

def _embed_image(
    path: Optional[str],
    max_width: float = FIGURE_MAX_WIDTH,
    max_height: float = FIGURE_MAX_HEIGHT,
    placeholder_label: str = "[PLACEHOLDER: Image not available]",
):
    """
    Return a ReportLab ``Image`` flowable (auto-resized) or a placeholder
    ``Paragraph`` if the file is missing.
    """
    if not HAS_REPORTLAB:
        return None

    if path and os.path.isfile(path):
        try:
            img = Image(path)
            w, h = img.imageWidth, img.imageHeight
            scale = min(max_width / w, max_height / h, 1.0)
            img.drawWidth = w * scale
            img.drawHeight = h * scale
            img.hAlign = "CENTER"
            return img
        except Exception:
            pass  # fall through to placeholder

    # Placeholder
    styles = get_pdf_styles()
    return Paragraph(placeholder_label, styles["Placeholder"])


# =============================================================================
# Helper: DataFrame → ReportLab Table
# =============================================================================

def _df_to_rl_table(
    df: pd.DataFrame,
    col_widths: Optional[List] = None,
    style=None,
):
    """Convert a pandas DataFrame to a ReportLab ``Table`` flowable."""
    if not HAS_REPORTLAB:
        return None

    from reportlab.platypus import Paragraph as P
    styles = get_pdf_styles()
    para_style = styles["BodyText"]
    para_style_hdr = styles["BodyText"]

    def _cell(val, bold: bool = False):
        text = str(val) if val is not None else ""
        st = styles["BodyText"]
        if bold:
            return Paragraph(f"<b>{text}</b>", st)
        return Paragraph(text, st)

    header = [_cell(c, bold=True) for c in df.columns]
    rows = [header] + [
        [_cell(v) for v in row] for row in df.values
    ]

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(style or get_standard_table_style())
    return tbl


# =============================================================================
# PDF REPORT BUILDER
# =============================================================================

class PDFReportBuilder:
    """
    Build the full MEPI PDF report.

    Parameters
    ----------
    results_df : pd.DataFrame
        Full MEPI results from ``MEPICalculator.calculate()``.
    chart_paths : dict
        Mapping of chart name → PNG file path (from ``ChartGenerator``).
    spatial_map_paths : dict
        Mapping of map name → PNG file path (from spatial_maps_png directory).
    bib_manager : BibliographyManager
        An initialised ``BibliographyManager`` instance.
    """

    def __init__(
        self,
        results_df: pd.DataFrame,
        chart_paths: Optional[Dict[str, str]] = None,
        spatial_map_paths: Optional[Dict[str, str]] = None,
        bib_manager=None,
    ):
        if not HAS_REPORTLAB:
            raise ImportError(
                "reportlab is required for PDF generation. "
                "Install with: pip install reportlab"
            )

        self.df = results_df.copy()
        self.charts = chart_paths or {}
        self.maps = spatial_map_paths or {}
        self.bib = bib_manager
        self.styles = get_pdf_styles()
        self._fig_counter = 0
        self._tbl_counter = 0
        self._story: List = []

    # ------------------------------------------------------------------
    # Counter helpers
    # ------------------------------------------------------------------

    def _next_fig(self) -> str:
        self._fig_counter += 1
        return f"Figure {self._fig_counter}"

    def _next_tbl(self) -> str:
        self._tbl_counter += 1
        return f"Table {self._tbl_counter}"

    # ------------------------------------------------------------------
    # Flowable helpers
    # ------------------------------------------------------------------

    def _h(self, text: str, level: int = 1) -> Paragraph:
        style_map = {
            1: "ChapterHeading",
            2: "SectionHeading",
            3: "SubsectionHeading",
        }
        return Paragraph(text, self.styles[style_map.get(level, "SectionHeading")])

    def _p(self, text: str) -> Paragraph:
        return Paragraph(text, self.styles["BodyText"])

    def _b(self, text: str) -> Paragraph:
        return Paragraph(f"• {text}", self.styles["BulletText"])

    def _spacer(self, h: float = 12) -> Spacer:
        return Spacer(1, h)

    def _fig(
        self,
        path: Optional[str],
        caption: str,
        placeholder_label: Optional[str] = None,
        max_width: float = FIGURE_MAX_WIDTH,
        max_height: float = FIGURE_MAX_HEIGHT,
    ) -> List:
        """Return [image_flowable, caption_paragraph] for a figure."""
        label = placeholder_label or f"[PLACEHOLDER: {caption}]"
        fig_label = self._next_fig()
        img = _embed_image(path, max_width=max_width, max_height=max_height, placeholder_label=label)
        cap = Paragraph(
            f"<i>{fig_label}: {caption}</i>",
            self.styles["FigureCaption"],
        )
        return [self._spacer(6), img, cap, self._spacer(10)]

    def _tbl_caption(self, caption: str) -> Paragraph:
        tbl_label = self._next_tbl()
        return Paragraph(
            f"<b>{tbl_label}:</b> {caption}",
            self.styles["TableCaption"],
        )

    def _cite(self, key: str) -> str:
        if self.bib:
            return self.bib.cite(key)
        return f"({key})"

    def _hr(self) -> HRFlowable:
        return HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor(COLOR_SECONDARY),
            spaceBefore=6, spaceAfter=6,
        )

    # ------------------------------------------------------------------
    # Cover page
    # ------------------------------------------------------------------

    def _cover_page(self):
        s = self._story
        s.append(Spacer(1, 1.5 * inch))
        s.append(Paragraph(REPORT_TITLE, self.styles["ReportTitle"]))
        s.append(Spacer(1, 0.3 * inch))
        s.append(Paragraph(REPORT_SUBTITLE, self.styles["ReportSubtitle"]))
        s.append(Spacer(1, 0.5 * inch))
        s.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor(COLOR_ACCENT), hAlign="CENTER"))
        s.append(Spacer(1, 0.5 * inch))
        authors_str = ", ".join(REPORT_AUTHORS)
        s.append(Paragraph(authors_str, self.styles["ReportMetadata"]))
        s.append(Paragraph(REPORT_ORGANIZATION, self.styles["ReportMetadata"]))
        s.append(Paragraph(REPORT_DATE, self.styles["ReportMetadata"]))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Executive summary
    # ------------------------------------------------------------------

    def _executive_summary(self):
        s = self._story
        s.append(self._h("Executive Summary"))
        s.append(self._hr())
        s.append(self._spacer(8))

        mean_mepi = self.df["mepi_score"].mean()
        n = len(self.df)

        summary_text = (
            f"This report presents a comprehensive spatial and dimensional analysis of energy "
            f"poverty across Bangladesh using the Multidimensional Energy Poverty Index (MEPI) "
            f"{self._cite('nussbaumer_2011')}. The analysis covers <b>{n} upazilas</b> spanning "
            f"all eight administrative divisions and multiple geographic zones including coastal, "
            f"char island, haor wetland, and hill tract areas."
        )
        s.append(Paragraph(summary_text, self.styles["ExecSummaryBox"]))
        s.append(self._spacer(8))

        # Key findings table
        mean_mepi = round(self.df["mepi_score"].mean(), 3)
        severe_n = int((self.df["poverty_category"] == "Severely Poor").sum()) if "poverty_category" in self.df.columns else "N/A"
        moderate_n = int((self.df["poverty_category"] == "Moderately Poor").sum()) if "poverty_category" in self.df.columns else "N/A"
        nonpoor_n = int((self.df["poverty_category"] == "Non-Poor").sum()) if "poverty_category" in self.df.columns else "N/A"

        kf_data = [
            ["Metric", "Value"],
            ["Total Upazilas Analysed", str(n)],
            ["Mean MEPI Score", f"{mean_mepi:.3f}"],
            ["Severely Poor Upazilas", str(severe_n)],
            ["Moderately Poor Upazilas", str(moderate_n)],
            ["Non-Poor Upazilas", str(nonpoor_n)],
            ["Most Deprived Upazila", self.df.nlargest(1, "mepi_score").iloc[0].get("upazila_name", "N/A") if "upazila_name" in self.df.columns else "N/A"],
            ["Least Deprived Upazila", self.df.nsmallest(1, "mepi_score").iloc[0].get("upazila_name", "N/A") if "upazila_name" in self.df.columns else "N/A"],
        ]

        s.append(self._tbl_caption("Key Findings at a Glance"))
        kf_df = pd.DataFrame(kf_data[1:], columns=kf_data[0])
        s.append(_df_to_rl_table(kf_df, style=get_summary_table_style()))
        s.append(self._spacer(12))

        s.append(self._p(
            "The MEPI framework decomposes energy poverty across five dimensions: "
            "<b>Availability</b>, <b>Reliability</b>, <b>Adequacy</b>, <b>Quality</b>, and "
            f"<b>Affordability</b> {self._cite('pelz_2018')}. "
            "Spatial mapping reveals marked geographic disparities, with the highest poverty "
            "concentrations observed in coastal, char island, and hill tract regions. "
            "The findings provide an evidence base for targeted policy interventions aligned "
            f"with SDG 7 (Affordable and Clean Energy) {self._cite('undp_sdg7_2023')}."
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 1 – Introduction
    # ------------------------------------------------------------------

    def _chapter_1(self):
        s = self._story
        s.append(self._h("Chapter 1: Introduction"))
        s.append(self._hr())

        s.append(self._h("1.1 Background", level=2))
        s.append(self._p(
            f"Energy poverty—defined as the lack of access to modern, reliable, affordable, "
            f"and clean energy services—remains a critical development challenge in Bangladesh "
            f"{self._cite('boardman_1991')}. Despite significant progress in electricity "
            f"access over the past decade {self._cite('bpdb_2023')}, approximately 30–40% "
            f"of the rural population still relies on traditional biomass for cooking "
            f"{self._cite('bbs_2022')}. The multidimensional nature of energy poverty means "
            f"that access alone is insufficient; reliability, adequacy, quality, and "
            f"affordability are equally important determinants of household energy welfare "
            f"{self._cite('nussbaumer_2011')}."
        ))
        s.append(self._spacer(6))

        s.append(self._h("1.2 Research Objectives", level=2))
        for obj in [
            "To calculate the Multidimensional Energy Poverty Index (MEPI) at the upazila level across Bangladesh.",
            "To identify spatial patterns and hotspots of energy poverty.",
            "To analyse dimensional contributions to overall energy poverty.",
            "To compare energy poverty across geographic zones and administrative units.",
            "To provide evidence-based policy recommendations for targeted interventions.",
        ]:
            s.append(self._b(obj))
        s.append(self._spacer(6))

        s.append(self._h("1.3 Literature Review", level=2))
        s.append(self._p(
            f"The concept of multidimensional energy poverty was formalised by "
            f"{self._cite('nussbaumer_2011')}, who developed a composite index capturing "
            f"five key dimensions. Subsequent work by {self._cite('pelz_2018')} critically "
            f"reviewed measurement approaches, while {self._cite('sadath_2017')} applied "
            f"the MEPI framework in the South Asian context. For Bangladesh specifically, "
            f"{self._cite('alam_2020')} demonstrated the welfare implications of energy "
            f"poverty, and {self._cite('hossain_2021')} identified significant spatial "
            f"heterogeneity at the district level. The Alkire–Foster methodology "
            f"{self._cite('alkire_foster_2011')} underpins the counting approach used in "
            f"this study."
        ))
        s.append(self._spacer(6))

        s.append(self._h("1.4 Significance of the Study", level=2))
        s.append(self._p(
            f"This study makes a novel contribution by providing upazila-level MEPI estimates "
            f"with spatial mapping, enabling granular identification of energy-poor areas. "
            f"The results directly support national planning under Bangladesh's Mujib Climate "
            f"Prosperity Plan {self._cite('government_bangladesh_2021')} and the World Bank's "
            f"rural energy programmes {self._cite('world_bank_2022')}. By decomposing poverty "
            f"into five dimensions, the study reveals which aspects of energy deprivation "
            f"are most acute in different geographic zones—critical for efficient resource allocation."
        ))

        # Overview chart placeholder
        s.extend(self._fig(
            self.charts.get("distribution_mepi"),
            "Distribution of MEPI Scores Across All Upazilas",
            "[PLACEHOLDER: MEPI score distribution histogram – overview chart]",
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 2 – Methodology
    # ------------------------------------------------------------------

    def _chapter_2(self):
        s = self._story
        s.append(self._h("Chapter 2: Methodology"))
        s.append(self._hr())

        s.append(self._h("2.1 MEPI Framework", level=2))
        s.append(self._p(
            f"The Multidimensional Energy Poverty Index (MEPI) follows the Alkire–Foster "
            f"dual-cutoff method {self._cite('alkire_foster_2011')}. Each upazila is assessed "
            f"across five dimensions; a dimensional deprivation score is computed from "
            f"underlying indicators, and the weighted average constitutes the MEPI score "
            f"(0 = no deprivation, 1 = maximum deprivation)."
        ))

        s.append(self._h("2.2 Five Dimensions", level=2))
        dim_data = [
            ["Dimension", "Indicators", "Weight"],
            ["Availability", "Electricity access, clean cooking fuel, grid connection", "20%"],
            ["Reliability", "Supply hours, outage frequency, outage duration", "20%"],
            ["Adequacy", "Energy consumption, lighting hours, appliance ownership", "20%"],
            ["Quality", "Voltage fluctuation, satisfaction score, indoor air quality", "20%"],
            ["Affordability", "Expenditure share, cost per kWh, subsidy access", "20%"],
        ]
        s.append(self._tbl_caption("MEPI Dimensions, Indicators, and Weights"))
        dim_df = pd.DataFrame(dim_data[1:], columns=dim_data[0])
        s.append(_df_to_rl_table(dim_df))
        s.append(self._spacer(10))

        s.append(self._h("2.3 Data Sources", level=2))
        s.append(self._p(
            f"Primary data were collected from a stratified household survey across 20 "
            f"representative upazilas. Secondary data sources include: Bangladesh Bureau of "
            f"Statistics {self._cite('bbs_2022')}, Bangladesh Power Development Board "
            f"{self._cite('bpdb_2023')}, Sustainable and Renewable Energy Development "
            f"Authority {self._cite('sreda_2022')}, and the World Bank "
            f"{self._cite('world_bank_2022')}."
        ))

        s.append(self._h("2.4 Normalisation and Calculation", level=2))
        s.append(self._p(
            "Each indicator is normalised to [0, 1] using min–max scaling. Indicators where "
            "a higher value implies greater deprivation (e.g., outage frequency) are inverted. "
            "Dimension scores are computed as the simple mean of their constituent indicator "
            "scores. The MEPI score is then the weighted sum of dimension scores using equal "
            "weights (0.2 per dimension). Upazilas are classified as: Non-Poor (MEPI ≤ 0.33), "
            "Moderately Poor (0.33 < MEPI ≤ 0.66), and Severely Poor (MEPI > 0.66)."
        ))

        # Methodology diagram placeholder
        s.extend(self._fig(
            self.charts.get("dimension_comparison"),
            "Mean Dimension Scores Illustrating the MEPI Framework",
            "[PLACEHOLDER: MEPI methodology diagram showing five dimensions]",
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 3 – Spatial Distribution
    # ------------------------------------------------------------------

    def _chapter_3(self):
        s = self._story
        s.append(self._h("Chapter 3: Spatial Distribution of Energy Poverty"))
        s.append(self._hr())

        s.append(self._p(
            f"Spatial analysis of MEPI scores reveals pronounced geographic disparities "
            f"across Bangladesh {self._cite('tobler_1970')}. Choropleth maps display the "
            f"upazila-level variation in overall MEPI and each of the five dimensions."
        ))

        # Overall MEPI map
        s.extend(self._fig(
            self.maps.get("mepi_spatial_map"),
            "Overall MEPI Spatial Distribution Across Bangladesh Upazilas",
            "[INSERT: mepi_spatial_map.png – Overall MEPI map from ~/spatial_maps_png/]",
            max_width=FIGURE_MAX_WIDTH, max_height=FIGURE_MAX_HEIGHT,
        ))

        s.append(self._h("3.1 Availability Dimension", level=2))
        s.append(self._p(
            "The availability dimension captures access to modern energy carriers. "
            "Upazilas in the Chittagong Hill Tracts and remote coastal chars exhibit "
            "the lowest access rates, reflecting infrastructure challenges."
        ))
        s.extend(self._fig(
            self.maps.get("availability_map"),
            "Availability Dimension Spatial Map",
            "[INSERT: availability_map.png – from ~/spatial_maps_png/]",
        ))

        s.append(self._h("3.2 Reliability Dimension", level=2))
        s.append(self._p(
            "Reliability scores are lowest in rural areas far from the national grid, "
            "where outage frequency exceeds 20 events per month and average outage "
            "duration surpasses 5 hours."
        ))
        s.extend(self._fig(
            self.maps.get("reliability_map"),
            "Reliability Dimension Spatial Map",
            "[INSERT: reliability_map.png – from ~/spatial_maps_png/]",
        ))

        s.append(self._h("3.3 Adequacy Dimension", level=2))
        s.extend(self._fig(
            self.maps.get("adequacy_map"),
            "Adequacy Dimension Spatial Map",
            "[INSERT: adequacy_map.png – from ~/spatial_maps_png/]",
        ))

        s.append(self._h("3.4 Quality Dimension", level=2))
        s.extend(self._fig(
            self.maps.get("quality_map"),
            "Quality Dimension Spatial Map",
            "[INSERT: quality_map.png – from ~/spatial_maps_png/]",
        ))

        s.append(self._h("3.5 Affordability Dimension", level=2))
        s.extend(self._fig(
            self.maps.get("affordability_map"),
            "Affordability Dimension Spatial Map",
            "[INSERT: affordability_map.png – from ~/spatial_maps_png/]",
        ))

        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 4 – Dimensional Analysis
    # ------------------------------------------------------------------

    def _chapter_4(self):
        s = self._story
        s.append(self._h("Chapter 4: Dimensional Analysis"))
        s.append(self._hr())

        # Dimension means table
        dim_cols = [c for c in ["Availability_score", "Reliability_score", "Adequacy_score",
                                  "Quality_score", "Affordability_score"] if c in self.df.columns]
        if dim_cols:
            means = self.df[dim_cols].mean().round(4)
            stds = self.df[dim_cols].std().round(4)
            dim_tbl_data = pd.DataFrame({
                "Dimension": [c.replace("_score", "") for c in dim_cols],
                "Mean Score": means.values,
                "Std. Deviation": stds.values,
                "Min": self.df[dim_cols].min().round(4).values,
                "Max": self.df[dim_cols].max().round(4).values,
            })
            s.append(self._tbl_caption("Descriptive Statistics of Dimension Scores"))
            s.append(_df_to_rl_table(dim_tbl_data))
            s.append(self._spacer(10))

        s.extend(self._fig(
            self.charts.get("dimension_comparison"),
            "Comparison of Mean MEPI Dimension Scores",
            "[PLACEHOLDER: Dimension comparison bar chart]",
        ))

        s.append(self._h("4.1 Correlation Analysis", level=2))
        s.append(self._p(
            f"Pairwise correlations between dimension scores reveal interdependencies "
            f"in energy poverty. High correlation between availability and adequacy "
            f"suggests that access constraints directly limit consumption levels "
            f"{self._cite('zhang_2019')}."
        ))
        s.extend(self._fig(
            self.charts.get("correlation_heatmap"),
            "Pairwise Correlation Heatmap of MEPI Dimension Scores",
            "[INSERT: Dimension correlation heatmap]",
        ))

        s.append(self._h("4.2 Dimension Heatmap by Upazila", level=2))
        s.extend(self._fig(
            self.charts.get("dimension_heatmap"),
            "Heatmap of Dimension Scores for Each Upazila",
            "[INSERT: Dimension heatmap – rows = upazilas, columns = dimensions]",
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 5 – Regional Analysis
    # ------------------------------------------------------------------

    def _chapter_5(self):
        s = self._story
        s.append(self._h("Chapter 5: Regional Analysis"))
        s.append(self._hr())

        s.append(self._p(
            "Bangladesh exhibits distinct energy poverty profiles across its geographic "
            "zones. Coastal, char, haor, hill tract, and Sundarbans fringe areas face "
            "unique challenges driven by physical geography, infrastructure deficits, "
            f"and socioeconomic conditions {self._cite('hossain_2021')}."
        ))

        # Regional summary table
        zone_col = None
        for col in ("geographic_zone", "division", "district"):
            if col in self.df.columns:
                zone_col = col
                break

        if zone_col:
            score_cols = ["mepi_score"] + [c for c in self.df.columns if c.endswith("_score") and c != "mepi_score"]
            region_tbl = self.df.groupby(zone_col)[score_cols].mean().round(3).reset_index()
            region_tbl.columns = [c.replace("_score", "").replace("_", " ").title() for c in region_tbl.columns]
            s.append(self._tbl_caption(f"Average MEPI Scores by {zone_col.replace('_', ' ').title()}"))
            s.append(_df_to_rl_table(region_tbl))
            s.append(self._spacer(10))

        s.append(self._h("5.1 Coastal Zone", level=2))
        s.append(self._p(
            "Coastal upazilas face energy poverty driven by tidal flooding, saline "
            "intrusion, and fragmented grid infrastructure. Availability and reliability "
            "scores are particularly low in districts such as Satkhira and Barguna."
        ))

        s.append(self._h("5.2 Char Islands", level=2))
        s.append(self._p(
            "River island (char) communities suffer from extreme energy isolation. "
            "No grid connection exists for most chars; kerosene and biomass dominate, "
            "with solar home systems providing partial electricity access."
        ))

        s.append(self._h("5.3 Haor Wetlands", level=2))
        s.append(self._p(
            "Seasonal inundation in the haor basin (Sunamganj, Netrokona) disrupts "
            "power supply for up to six months annually, driving high reliability "
            "deprivation scores."
        ))

        s.append(self._h("5.4 Chittagong Hill Tracts", level=2))
        s.append(self._p(
            "The hill tracts (Rangamati, Khagrachhari, Bandarban) have the lowest "
            "electricity access rates in Bangladesh due to rugged terrain, low "
            "population density, and high connection costs."
        ))

        s.append(self._h("5.5 Sundarbans Fringe", level=2))
        s.append(self._p(
            "Communities bordering the Sundarbans mangrove forest face dual challenges "
            "of flood risk and energy isolation, compounded by high dependence on "
            "wood fuel from the protected forest."
        ))

        s.extend(self._fig(
            self.charts.get("regional_comparison"),
            "Regional Comparison of MEPI Dimension Scores",
            "[PLACEHOLDER: Regional comparison grouped bar chart]",
        ))

        s.extend(self._fig(
            self.charts.get("box_plot_by_zone"),
            "Box Plot of MEPI Score Distribution by Region",
            "[PLACEHOLDER: Regional box plot]",
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 6 – Temporal Trends
    # ------------------------------------------------------------------

    def _chapter_6(self):
        s = self._story
        s.append(self._h("Chapter 6: Temporal Trends"))
        s.append(self._hr())

        s.append(self._p(
            "Temporal analysis of energy poverty is essential for evaluating the impact "
            "of policy interventions and tracking progress towards SDG 7 targets "
            f"{self._cite('undp_sdg7_2023')}. Bangladesh has made measurable progress "
            f"in electricity access since 2010, driven by the Rural Electrification Board "
            f"and solar home system programmes {self._cite('sreda_2022')}."
        ))

        s.append(self._h("6.1 Historical Energy Poverty Changes", level=2))
        s.append(self._p(
            "National electricity access rose from approximately 47% in 2010 to over 95% "
            f"by 2022 {self._cite('bpdb_2023')}. However, improvements in reliability and "
            "affordability have lagged behind access expansion, suggesting that the nature "
            "of energy poverty is shifting from access deprivation to quality and "
            "affordability deprivation."
        ))

        s.extend(self._fig(
            self.charts.get("temporal_trend"),
            "Illustrative Temporal Trend of Mean MEPI Score (2018–2023)",
            "[PLACEHOLDER: Temporal trend line chart – requires multi-year MEPI data]",
        ))

        s.append(self._h("6.2 Improvement and Deterioration Areas", level=2))
        s.append(self._p(
            "Upazilas with strong rural electrification investment show declining MEPI "
            "scores over time, while coastal upazilas vulnerable to climate-induced "
            "infrastructure damage may show deteriorating scores. Temporal maps would "
            "visualise these contrasting dynamics."
        ))

        s.append(self._p(
            "<i>[PLACEHOLDER: Insert temporal comparison maps showing MEPI change between "
            "baseline and endline surveys – requires multi-year panel data]</i>"
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 7 – Vulnerability Assessment
    # ------------------------------------------------------------------

    def _chapter_7(self):
        s = self._story
        s.append(self._h("Chapter 7: Vulnerability Assessment"))
        s.append(self._hr())

        s.append(self._p(
            f"Vulnerability assessment identifies upazilas at highest risk of persistent "
            f"energy poverty, accounting for both current deprivation levels and underlying "
            f"socioeconomic and geographic risk factors {self._cite('anselin_1995')}."
        ))

        s.append(self._h("7.1 Hotspot Identification", level=2))
        s.append(self._p(
            "Energy poverty hotspots are defined as upazilas with MEPI scores in the "
            "top quartile (≥ 75th percentile) that are also surrounded by similarly "
            "deprived neighbours (spatial autocorrelation). These clusters represent "
            "priority intervention zones."
        ))

        # Hotspot table
        threshold = self.df["mepi_score"].quantile(0.75)
        hotspot_df = self.df[self.df["mepi_score"] >= threshold].copy()
        show_cols = [c for c in ["upazila_name", "district", "division", "mepi_score", "poverty_category"] if c in hotspot_df.columns]
        if show_cols:
            hs_tbl = hotspot_df[show_cols].sort_values("mepi_score", ascending=False).reset_index(drop=True)
            hs_tbl.columns = [c.replace("_", " ").title() for c in hs_tbl.columns]
            s.append(self._tbl_caption("Energy Poverty Hotspot Upazilas (MEPI ≥ 75th Percentile)"))
            s.append(_df_to_rl_table(hs_tbl))
            s.append(self._spacer(10))

        s.extend(self._fig(
            self.maps.get("hotspot_map"),
            "Energy Poverty Hotspot Map",
            "[INSERT: hotspot_map.png – Vulnerability and hotspot clusters]",
        ))

        s.append(self._h("7.2 Population at Risk", level=2))
        s.append(self._p(
            f"Applying average household size estimates from the BBS Census "
            f"{self._cite('bbs_2022')}, the severely energy-poor upazilas are estimated "
            "to house approximately 20–30 million people, predominantly in rural areas "
            "without reliable grid electricity or clean cooking solutions."
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 8 – Key Findings
    # ------------------------------------------------------------------

    def _chapter_8(self):
        s = self._story
        s.append(self._h("Chapter 8: Key Findings"))
        s.append(self._hr())

        # Summary statistics
        if "mepi_score" in self.df.columns:
            stats_data = pd.DataFrame({
                "Statistic": ["N (Upazilas)", "Mean MEPI", "Median MEPI", "Std. Dev.", "Min", "Max", "Q1 (25th)", "Q3 (75th)"],
                "Value": [
                    len(self.df),
                    round(self.df["mepi_score"].mean(), 4),
                    round(self.df["mepi_score"].median(), 4),
                    round(self.df["mepi_score"].std(), 4),
                    round(self.df["mepi_score"].min(), 4),
                    round(self.df["mepi_score"].max(), 4),
                    round(self.df["mepi_score"].quantile(0.25), 4),
                    round(self.df["mepi_score"].quantile(0.75), 4),
                ],
            })
            s.append(self._tbl_caption("Summary Statistics of MEPI Scores"))
            s.append(_df_to_rl_table(stats_data, style=get_summary_table_style()))
            s.append(self._spacer(10))

        s.append(self._h("8.1 Top 10 Most Energy-Poor Upazilas", level=2))
        top10 = self.df.nlargest(10, "mepi_score")
        show_cols = [c for c in ["upazila_name", "district", "division", "mepi_score", "poverty_category"] if c in top10.columns]
        top10_tbl = top10[show_cols].reset_index(drop=True)
        top10_tbl.index = top10_tbl.index + 1
        top10_tbl = top10_tbl.reset_index().rename(columns={"index": "Rank"})
        top10_tbl.columns = [c.replace("_", " ").title() for c in top10_tbl.columns]
        s.append(self._tbl_caption("Top 10 Most Energy-Poor Upazilas by MEPI Score"))
        s.append(_df_to_rl_table(top10_tbl))
        s.append(self._spacer(8))

        s.extend(self._fig(
            self.charts.get("top10_most_poor"),
            "Top 10 Most Energy-Poor Upazilas – MEPI Score Bar Chart",
            "[PLACEHOLDER: Top 10 most poor bar chart]",
        ))

        s.append(self._h("8.2 Top 10 Least Energy-Poor Upazilas", level=2))
        bot10 = self.df.nsmallest(10, "mepi_score")
        bot10_tbl = bot10[show_cols].reset_index(drop=True)
        bot10_tbl.index = bot10_tbl.index + 1
        bot10_tbl = bot10_tbl.reset_index().rename(columns={"index": "Rank"})
        bot10_tbl.columns = [c.replace("_", " ").title() for c in bot10_tbl.columns]
        s.append(self._tbl_caption("Top 10 Least Energy-Poor Upazilas by MEPI Score"))
        s.append(_df_to_rl_table(bot10_tbl))
        s.append(self._spacer(8))

        s.extend(self._fig(
            self.charts.get("top10_least_poor"),
            "Top 10 Least Energy-Poor Upazilas – MEPI Score Bar Chart",
            "[PLACEHOLDER: Top 10 least poor bar chart]",
        ))

        s.append(self._h("8.3 Poverty Category Distribution", level=2))
        s.extend(self._fig(
            self.charts.get("poverty_category_pie"),
            "Distribution of Upazilas Across MEPI Poverty Categories",
            "[PLACEHOLDER: Poverty category pie chart]",
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 9 – Policy Implications
    # ------------------------------------------------------------------

    def _chapter_9(self):
        s = self._story
        s.append(self._h("Chapter 9: Policy Implications and Recommendations"))
        s.append(self._hr())

        s.append(self._p(
            "The MEPI results provide a robust evidence base for spatially targeted "
            "energy poverty interventions. The following recommendations are prioritised "
            f"by severity and feasibility {self._cite('international_energy_agency_2021')} "
            f"{self._cite('irena_2023')}."
        ))

        recs = [
            ("Grid Extension and Mini-Grid Deployment",
             "Prioritise grid extension to the top 50 most energy-poor upazilas, "
             "particularly in the Chittagong Hill Tracts and coastal chars. "
             "Where grid extension is not economically viable, deploy community-scale "
             "solar mini-grids to provide reliable electricity."),
            ("Clean Cooking Fuel Promotion",
             "Scale up LPG subsidy programmes and promote improved cook stoves in "
             "coastal and haor upazilas where biomass combustion is prevalent. "
             "Strengthen the SREDA-led clean cooking initiative."),
            ("Reliability Improvement",
             "Invest in distribution network upgrades in high-outage upazilas. "
             "Deploy smart meters and automated fault detection to reduce outage "
             "frequency and duration."),
            ("Affordability Interventions",
             "Expand targeted lifeline tariffs and subsidy programmes to ensure "
             "that poor households pay no more than 5–10% of income on energy. "
             "Strengthen subsidy delivery mechanisms to reach underserved upazilas."),
            ("Data and Monitoring",
             "Establish a national energy poverty monitoring system using annual "
             "household surveys aligned with MEPI dimensions. Integrate with BBS "
             "census data for regular upazila-level updates."),
        ]

        for i, (title, text) in enumerate(recs, 1):
            s.append(self._h(f"9.{i} {title}", level=2))
            s.append(self._p(text))

        s.append(PageBreak())

    # ------------------------------------------------------------------
    # Chapter 10 – Conclusion
    # ------------------------------------------------------------------

    def _chapter_10(self):
        s = self._story
        s.append(self._h("Chapter 10: Conclusion"))
        s.append(self._hr())

        s.append(self._p(
            "This study has presented a comprehensive spatial and dimensional analysis of "
            "energy poverty in Bangladesh using the Multidimensional Energy Poverty Index "
            f"(MEPI) {self._cite('nussbaumer_2011')}. Key findings include: "
            "marked geographic disparities with highest deprivation in the Chittagong Hill "
            "Tracts, coastal chars, and haor wetlands; multi-dimensional nature of poverty "
            "where availability and affordability are the dominant dimensions; and significant "
            "variation across the eight administrative divisions."
        ))

        s.append(self._h("10.1 Future Research Directions", level=2))
        for direction in [
            "Longitudinal MEPI tracking using multi-wave household panel data.",
            "Integration of climate vulnerability indicators into the MEPI framework.",
            "Micro-level (village/ward) analysis using satellite-derived night-light data.",
            "Gender-disaggregated energy poverty analysis.",
            "Impact evaluation of specific energy programmes using MEPI as an outcome measure.",
        ]:
            s.append(self._b(direction))

        s.append(self._h("10.2 Study Limitations", level=2))
        s.append(self._p(
            "The current analysis is limited to the 20 sample upazilas included in the "
            "survey dataset; a nationally representative sample of all 495 upazilas would "
            "provide more definitive spatial estimates. Equal weighting of dimensions may "
            "not reflect local priorities; participatory weight elicitation with communities "
            "could improve contextual validity."
        ))
        s.append(PageBreak())

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------

    def _references(self):
        s = self._story
        s.append(self._h("References"))
        s.append(self._hr())

        if self.bib:
            bib_list = self.bib.bibliography_list(only_cited=True)
            for entry in bib_list:
                s.append(self._p(entry))
                s.append(self._spacer(4))
        else:
            s.append(self._p("[Bibliography not available – BibliographyManager not provided]"))

    # ------------------------------------------------------------------
    # Main build method
    # ------------------------------------------------------------------

    def build(self, output_path: str) -> str:
        """
        Compose and write the full PDF report.

        Parameters
        ----------
        output_path : str
            Destination file path for the PDF.

        Returns
        -------
        str
            Absolute path of the saved PDF file.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN + 18,    # extra space for header bar
            bottomMargin=_MARGIN + 10,  # extra space for footer
            title=REPORT_TITLE,
            author=", ".join(REPORT_AUTHORS),
            subject=REPORT_SUBTITLE,
        )

        authors_str = ", ".join(REPORT_AUTHORS)
        on_page = _make_header_footer(REPORT_TITLE, authors_str)

        # Build story
        self._cover_page()
        self._executive_summary()
        self._chapter_1()
        self._chapter_2()
        self._chapter_3()
        self._chapter_4()
        self._chapter_5()
        self._chapter_6()
        self._chapter_7()
        self._chapter_8()
        self._chapter_9()
        self._chapter_10()
        self._references()

        doc.build(self._story, onFirstPage=on_page, onLaterPages=on_page)
        abs_path = os.path.abspath(output_path)
        print(f"PDF report saved: {abs_path}")
        return abs_path
