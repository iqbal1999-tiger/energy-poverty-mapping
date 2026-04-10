"""
report_template.py - Professional report template definitions for the MEPI report.

Defines paragraph styles, table styles, colour constants, and helper utilities
used by ``pdf_report_builder.py`` and ``docx_report_builder.py``.

All styling decisions are centralised here so that the look-and-feel of the
report can be changed from a single file.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# ReportLab styles (used by pdf_report_builder.py)
# ---------------------------------------------------------------------------
try:
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import TableStyle

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ---------------------------------------------------------------------------
# python-docx styles (used by docx_report_builder.py)
# ---------------------------------------------------------------------------
try:
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ---------------------------------------------------------------------------
# Colour palette (mirrored from report_config.py to avoid circular imports)
# ---------------------------------------------------------------------------

COLOR_PRIMARY_HEX = "#1F4E79"
COLOR_SECONDARY_HEX = "#2E75B6"
COLOR_ACCENT_HEX = "#ED7D31"
COLOR_LIGHT_HEX = "#D6E4F0"
COLOR_WHITE_HEX = "#FFFFFF"

def _hex_to_rgb(hex_str: str):
    """Convert a hex colour string to an (R, G, B) tuple of ints 0–255."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


if HAS_REPORTLAB:
    _RL_PRIMARY = colors.HexColor(COLOR_PRIMARY_HEX)
    _RL_SECONDARY = colors.HexColor(COLOR_SECONDARY_HEX)
    _RL_ACCENT = colors.HexColor(COLOR_ACCENT_HEX)
    _RL_LIGHT = colors.HexColor(COLOR_LIGHT_HEX)


# =============================================================================
# ReportLab paragraph styles
# =============================================================================

def get_pdf_styles():
    """
    Return a dict of ReportLab ``ParagraphStyle`` objects keyed by name.

    Raises
    ------
    ImportError
        If ``reportlab`` is not installed.
    """
    if not HAS_REPORTLAB:
        raise ImportError("reportlab is required for PDF generation. Run: pip install reportlab")

    base = getSampleStyleSheet()

    styles = {}

    # ------------------------------------------------------------------
    # Title page styles
    # ------------------------------------------------------------------
    styles["ReportTitle"] = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontSize=28,
        textColor=_RL_PRIMARY,
        spaceAfter=12,
        leading=34,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    styles["ReportSubtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base["Normal"],
        fontSize=16,
        textColor=_RL_SECONDARY,
        spaceAfter=8,
        leading=22,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    styles["ReportMetadata"] = ParagraphStyle(
        "ReportMetadata",
        parent=base["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceBefore=4,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    # ------------------------------------------------------------------
    # Chapter and section headings
    # ------------------------------------------------------------------
    styles["ChapterHeading"] = ParagraphStyle(
        "ChapterHeading",
        parent=base["Heading1"],
        fontSize=18,
        textColor=_RL_PRIMARY,
        spaceBefore=18,
        spaceAfter=8,
        leading=22,
        fontName="Helvetica-Bold",
        borderPad=(0, 0, 4, 0),
    )

    styles["SectionHeading"] = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontSize=14,
        textColor=_RL_SECONDARY,
        spaceBefore=12,
        spaceAfter=6,
        leading=18,
        fontName="Helvetica-Bold",
    )

    styles["SubsectionHeading"] = ParagraphStyle(
        "SubsectionHeading",
        parent=base["Heading3"],
        fontSize=12,
        textColor=_RL_SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
        leading=16,
        fontName="Helvetica-BoldOblique",
    )

    # ------------------------------------------------------------------
    # Body text
    # ------------------------------------------------------------------
    styles["BodyText"] = ParagraphStyle(
        "BodyText",
        parent=base["Normal"],
        fontSize=11,
        leading=16,
        spaceBefore=4,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
    )

    styles["BodyTextIndented"] = ParagraphStyle(
        "BodyTextIndented",
        parent=styles["BodyText"],
        leftIndent=18,
    )

    # ------------------------------------------------------------------
    # Captions
    # ------------------------------------------------------------------
    styles["FigureCaption"] = ParagraphStyle(
        "FigureCaption",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceBefore=4,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique",
    )

    styles["TableCaption"] = ParagraphStyle(
        "TableCaption",
        parent=styles["FigureCaption"],
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=4,
    )

    # ------------------------------------------------------------------
    # TOC styles
    # ------------------------------------------------------------------
    styles["TOCEntry1"] = ParagraphStyle(
        "TOCEntry1",
        parent=base["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        spaceBefore=4,
        spaceAfter=2,
    )

    styles["TOCEntry2"] = ParagraphStyle(
        "TOCEntry2",
        parent=base["Normal"],
        fontSize=10,
        leftIndent=18,
        spaceBefore=2,
        spaceAfter=1,
    )

    # ------------------------------------------------------------------
    # Executive summary box
    # ------------------------------------------------------------------
    styles["ExecSummaryBox"] = ParagraphStyle(
        "ExecSummaryBox",
        parent=base["Normal"],
        fontSize=11,
        leading=16,
        spaceBefore=4,
        spaceAfter=6,
        leftIndent=12,
        rightIndent=12,
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
        textColor=colors.HexColor("#1A1A1A"),
    )

    # ------------------------------------------------------------------
    # Bullet / list
    # ------------------------------------------------------------------
    styles["BulletText"] = ParagraphStyle(
        "BulletText",
        parent=base["Normal"],
        fontSize=11,
        leading=16,
        spaceBefore=2,
        spaceAfter=2,
        leftIndent=18,
        bulletIndent=6,
        fontName="Helvetica",
    )

    # ------------------------------------------------------------------
    # Footer / header
    # ------------------------------------------------------------------
    styles["FooterText"] = ParagraphStyle(
        "FooterText",
        parent=base["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    styles["Placeholder"] = ParagraphStyle(
        "Placeholder",
        parent=base["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#AAAAAA"),
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique",
        spaceBefore=12,
        spaceAfter=12,
        borderColor=colors.HexColor("#CCCCCC"),
        borderWidth=1,
        borderPad=8,
    )

    return styles


# =============================================================================
# ReportLab table styles
# =============================================================================

def get_standard_table_style():
    """
    Return a ``TableStyle`` for data tables with alternating row shading.

    Raises
    ------
    ImportError
        If ``reportlab`` is not installed.
    """
    if not HAS_REPORTLAB:
        raise ImportError("reportlab is required. Run: pip install reportlab")

    return TableStyle(
        [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), _RL_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Body rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            # Alternating rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(COLOR_LIGHT_HEX)]),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, _RL_SECONDARY),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def get_summary_table_style():
    """
    Return a ``TableStyle`` for summary / key-stats tables (no alternating rows,
    bolder appearance).
    """
    if not HAS_REPORTLAB:
        raise ImportError("reportlab is required. Run: pip install reportlab")

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), _RL_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (0, -1), _RL_LIGHT),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#AAAAAA")),
            ("LINEBELOW", (0, 0), (-1, 0), 2, _RL_SECONDARY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]
    )


# =============================================================================
# python-docx helper functions
# =============================================================================

def apply_docx_heading_style(paragraph, level: int = 1):
    """
    Apply chapter/section heading styling to a python-docx paragraph.

    Parameters
    ----------
    paragraph :
        A ``docx.text.paragraph.Paragraph`` object.
    level : int
        Heading level (1 = chapter, 2 = section, 3 = subsection).
    """
    if not HAS_DOCX:
        return

    rgb_map = {
        1: _hex_to_rgb(COLOR_PRIMARY_HEX),
        2: _hex_to_rgb(COLOR_SECONDARY_HEX),
        3: _hex_to_rgb(COLOR_SECONDARY_HEX),
    }
    size_map = {1: 18, 2: 14, 3: 12}
    color = rgb_map.get(level, _hex_to_rgb(COLOR_PRIMARY_HEX))
    size = size_map.get(level, 12)

    for run in paragraph.runs:
        run.bold = True
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(*color)


def apply_docx_body_style(paragraph):
    """Apply body text styling to a python-docx paragraph."""
    if not HAS_DOCX:
        return
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in paragraph.runs:
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(30, 30, 30)


def apply_docx_caption_style(paragraph):
    """Apply figure/table caption styling to a python-docx paragraph."""
    if not HAS_DOCX:
        return
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in paragraph.runs:
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(100, 100, 100)
