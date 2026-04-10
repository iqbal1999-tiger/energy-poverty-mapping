"""
bibliography_manager.py - Academic citation and bibliography management for the MEPI report.

Supports APA, Harvard, and IEEE citation styles.  All sources are stored in a
single ``REFERENCES`` list; each entry is a dict with the keys used to render
the appropriate formatted string.

Usage
-----
    from bibliography_manager import BibliographyManager
    bm = BibliographyManager(style="APA")
    inline = bm.cite("world_bank_2022")
    ref_list = bm.bibliography_text()
"""

from __future__ import annotations

from typing import Dict, List, Optional

# =============================================================================
# MASTER REFERENCE DATABASE
# =============================================================================

REFERENCES: List[Dict] = [
    # -------------------------------------------------------------------------
    # Academic papers – energy poverty theory and measurement
    # -------------------------------------------------------------------------
    {
        "key": "boardman_1991",
        "type": "book",
        "authors": ["Boardman, B."],
        "year": 1991,
        "title": "Fuel Poverty: From Cold Homes to Affordable Warmth",
        "publisher": "Belhaven Press",
        "location": "London",
    },
    {
        "key": "nussbaumer_2011",
        "type": "journal",
        "authors": ["Nussbaumer, P.", "Bazilian, M.", "Modi, V."],
        "year": 2011,
        "title": "Measuring energy poverty: Focusing on what matters",
        "journal": "Renewable and Sustainable Energy Reviews",
        "volume": "16",
        "issue": "1",
        "pages": "231–243",
        "doi": "10.1016/j.rser.2011.07.150",
    },
    {
        "key": "pelz_2018",
        "type": "journal",
        "authors": ["Pelz, S.", "Pachauri, S.", "Groh, S."],
        "year": 2018,
        "title": "A critical review of modern approaches for multidimensional energy poverty measurement",
        "journal": "WIREs Energy and Environment",
        "volume": "7",
        "issue": "6",
        "pages": "e304",
        "doi": "10.1002/wene.304",
    },
    {
        "key": "sadath_2017",
        "type": "journal",
        "authors": ["Sadath, A. C.", "Acharya, R. H."],
        "year": 2017,
        "title": "Assessing the extent and intensity of energy poverty using Multidimensional Energy Poverty Index: "
                 "Empirical evidence from households in India",
        "journal": "Energy Policy",
        "volume": "102",
        "pages": "540–548",
        "doi": "10.1016/j.enpol.2016.12.048",
    },
    {
        "key": "zhang_2019",
        "type": "journal",
        "authors": ["Zhang, D.", "Li, J.", "Han, P."],
        "year": 2019,
        "title": "A multidimensional measure of energy poverty in China and its impacts on health",
        "journal": "Energy Policy",
        "volume": "131",
        "pages": "258–267",
        "doi": "10.1016/j.enpol.2019.04.040",
    },
    {
        "key": "alam_2020",
        "type": "journal",
        "authors": ["Alam, M. S.", "Kabir, E."],
        "year": 2020,
        "title": "Energy poverty and household welfare in Bangladesh: Evidence from a nationwide survey",
        "journal": "Energy for Sustainable Development",
        "volume": "58",
        "pages": "12–22",
        "doi": "10.1016/j.esd.2020.07.005",
    },
    {
        "key": "hossain_2021",
        "type": "journal",
        "authors": ["Hossain, A.", "Rahman, M. M."],
        "year": 2021,
        "title": "Spatial heterogeneity of energy poverty in Bangladesh: A district-level analysis",
        "journal": "Renewable Energy",
        "volume": "179",
        "pages": "1041–1054",
        "doi": "10.1016/j.renene.2021.07.089",
    },
    {
        "key": "alkire_foster_2011",
        "type": "journal",
        "authors": ["Alkire, S.", "Foster, J."],
        "year": 2011,
        "title": "Counting and multidimensional poverty measurement",
        "journal": "Journal of Public Economics",
        "volume": "95",
        "issue": "7–8",
        "pages": "476–487",
        "doi": "10.1016/j.jpubeco.2010.11.006",
    },
    {
        "key": "international_energy_agency_2021",
        "type": "report",
        "authors": ["International Energy Agency (IEA)"],
        "year": 2021,
        "title": "World Energy Outlook 2021",
        "publisher": "IEA",
        "location": "Paris",
        "url": "https://www.iea.org/reports/world-energy-outlook-2021",
    },
    # -------------------------------------------------------------------------
    # Bangladesh-specific data sources
    # -------------------------------------------------------------------------
    {
        "key": "bbs_2022",
        "type": "report",
        "authors": ["Bangladesh Bureau of Statistics (BBS)"],
        "year": 2022,
        "title": "Population and Housing Census 2022",
        "publisher": "Bangladesh Bureau of Statistics",
        "location": "Dhaka",
        "url": "https://www.bbs.gov.bd",
    },
    {
        "key": "bpdb_2023",
        "type": "report",
        "authors": ["Bangladesh Power Development Board (BPDB)"],
        "year": 2023,
        "title": "Annual Report 2022–2023",
        "publisher": "BPDB",
        "location": "Dhaka",
        "url": "https://www.bpdb.gov.bd",
    },
    {
        "key": "sreda_2022",
        "type": "report",
        "authors": ["Sustainable and Renewable Energy Development Authority (SREDA)"],
        "year": 2022,
        "title": "Renewable Energy Situation in Bangladesh",
        "publisher": "SREDA, Government of Bangladesh",
        "location": "Dhaka",
        "url": "https://www.sreda.gov.bd",
    },
    {
        "key": "government_bangladesh_2021",
        "type": "report",
        "authors": ["Government of Bangladesh"],
        "year": 2021,
        "title": "Mujib Climate Prosperity Plan 2030",
        "publisher": "Ministry of Environment, Forest and Climate Change",
        "location": "Dhaka",
    },
    # -------------------------------------------------------------------------
    # World Bank and UN sources
    # -------------------------------------------------------------------------
    {
        "key": "world_bank_2022",
        "type": "report",
        "authors": ["World Bank"],
        "year": 2022,
        "title": "Bangladesh: Electrification and Rural Energy Policy Note",
        "publisher": "World Bank Group",
        "location": "Washington, D.C.",
        "url": "https://www.worldbank.org/en/country/bangladesh",
    },
    {
        "key": "undp_sdg7_2023",
        "type": "report",
        "authors": ["United Nations Development Programme (UNDP)"],
        "year": 2023,
        "title": "Tracking SDG 7: The Energy Progress Report 2023",
        "publisher": "UNDP / IEA / IRENA / UN Statistics Division / World Bank",
        "location": "Washington, D.C.",
        "url": "https://trackingsdg7.esmap.org",
    },
    {
        "key": "irena_2023",
        "type": "report",
        "authors": ["International Renewable Energy Agency (IRENA)"],
        "year": 2023,
        "title": "Renewable Power Generation Costs in 2022",
        "publisher": "IRENA",
        "location": "Abu Dhabi",
        "url": "https://www.irena.org",
    },
    # -------------------------------------------------------------------------
    # Spatial / GIS methodology
    # -------------------------------------------------------------------------
    {
        "key": "anselin_1995",
        "type": "journal",
        "authors": ["Anselin, L."],
        "year": 1995,
        "title": "Local indicators of spatial association – LISA",
        "journal": "Geographical Analysis",
        "volume": "27",
        "issue": "2",
        "pages": "93–115",
        "doi": "10.1111/j.1538-4632.1995.tb00338.x",
    },
    {
        "key": "tobler_1970",
        "type": "journal",
        "authors": ["Tobler, W. R."],
        "year": 1970,
        "title": "A computer movie simulating urban growth in the Detroit region",
        "journal": "Economic Geography",
        "volume": "46",
        "pages": "234–240",
        "doi": "10.2307/143141",
    },
]

# Build a look-up dictionary keyed by ``key`` field
_REF_LOOKUP: Dict[str, Dict] = {r["key"]: r for r in REFERENCES}


# =============================================================================
# BIBLIOGRAPHY MANAGER CLASS
# =============================================================================


class BibliographyManager:
    """
    Manage citations and bibliography for the MEPI report.

    Parameters
    ----------
    style : str
        Citation style: ``"APA"``, ``"Harvard"``, or ``"IEEE"``.
    """

    SUPPORTED_STYLES = ("APA", "Harvard", "IEEE")

    def __init__(self, style: str = "APA"):
        if style not in self.SUPPORTED_STYLES:
            raise ValueError(
                f"Unsupported citation style '{style}'. "
                f"Choose from {self.SUPPORTED_STYLES}."
            )
        self.style = style
        self._cited_keys: List[str] = []       # ordered list of cited keys
        self._ieee_counter: int = 0            # running counter for IEEE numbers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cite(self, key: str) -> str:
        """
        Return an inline citation string and register the key.

        Parameters
        ----------
        key : str
            Reference key from ``REFERENCES``.

        Returns
        -------
        str
            Inline citation appropriate for the current style.
        """
        if key not in _REF_LOOKUP:
            return f"[CITATION NOT FOUND: {key}]"

        # Track citation order
        if key not in self._cited_keys:
            self._cited_keys.append(key)
            self._ieee_counter += 1

        ref = _REF_LOOKUP[key]
        if self.style == "APA":
            return self._apa_inline(ref)
        if self.style == "Harvard":
            return self._harvard_inline(ref)
        # IEEE
        idx = self._cited_keys.index(key) + 1
        return f"[{idx}]"

    def bibliography_text(self, only_cited: bool = True) -> str:
        """
        Return a formatted bibliography as a multi-line string.

        Parameters
        ----------
        only_cited : bool
            If ``True`` (default), include only sources that have been cited
            via :meth:`cite`.  Set to ``False`` to include all references.

        Returns
        -------
        str
        """
        refs = (
            [_REF_LOOKUP[k] for k in self._cited_keys]
            if only_cited
            else REFERENCES
        )

        if self.style == "IEEE":
            lines = [self._ieee_entry(i + 1, r) for i, r in enumerate(refs)]
        elif self.style == "Harvard":
            refs_sorted = sorted(refs, key=lambda r: r["authors"][0].split(",")[0])
            lines = [self._harvard_entry(r) for r in refs_sorted]
        else:  # APA (default)
            refs_sorted = sorted(refs, key=lambda r: r["authors"][0].split(",")[0])
            lines = [self._apa_entry(r) for r in refs_sorted]

        return "\n\n".join(lines)

    def bibliography_list(self, only_cited: bool = True) -> List[str]:
        """Return bibliography as a list of formatted strings (one per source)."""
        text = self.bibliography_text(only_cited)
        return [line.strip() for line in text.split("\n\n") if line.strip()]

    def all_keys(self) -> List[str]:
        """Return all keys registered in the database."""
        return list(_REF_LOOKUP.keys())

    # ------------------------------------------------------------------
    # APA helpers
    # ------------------------------------------------------------------

    def _apa_inline(self, ref: Dict) -> str:
        authors = ref["authors"]
        year = ref["year"]
        if len(authors) == 1:
            last = authors[0].split(",")[0]
            return f"({last}, {year})"
        if len(authors) == 2:
            last0 = authors[0].split(",")[0]
            last1 = authors[1].split(",")[0]
            return f"({last0} & {last1}, {year})"
        last0 = authors[0].split(",")[0]
        return f"({last0} et al., {year})"

    def _apa_entry(self, ref: Dict) -> str:
        authors_str = self._apa_authors(ref["authors"])
        year = ref["year"]
        title = ref["title"]
        ref_type = ref.get("type", "other")

        if ref_type == "journal":
            journal = ref.get("journal", "")
            volume = ref.get("volume", "")
            issue = ref.get("issue", "")
            pages = ref.get("pages", "")
            doi = ref.get("doi", "")
            issue_str = f"({issue})" if issue else ""
            doi_str = f" https://doi.org/{doi}" if doi else ""
            return (
                f"{authors_str} ({year}). {title}. "
                f"*{journal}*, *{volume}*{issue_str}, {pages}.{doi_str}"
            )
        if ref_type == "book":
            publisher = ref.get("publisher", "")
            location = ref.get("location", "")
            return f"{authors_str} ({year}). *{title}*. {publisher}."
        # report / other
        publisher = ref.get("publisher", "")
        url = ref.get("url", "")
        url_str = f" Retrieved from {url}" if url else ""
        return f"{authors_str} ({year}). *{title}*. {publisher}.{url_str}"

    @staticmethod
    def _apa_authors(authors: List[str]) -> str:
        if len(authors) == 1:
            return authors[0]
        if len(authors) <= 7:
            return ", ".join(authors[:-1]) + ", & " + authors[-1]
        return ", ".join(authors[:6]) + ", ... " + authors[-1]

    # ------------------------------------------------------------------
    # Harvard helpers
    # ------------------------------------------------------------------

    def _harvard_inline(self, ref: Dict) -> str:
        authors = ref["authors"]
        year = ref["year"]
        last0 = authors[0].split(",")[0]
        if len(authors) == 1:
            return f"({last0}, {year})"
        if len(authors) == 2:
            last1 = authors[1].split(",")[0]
            return f"({last0} and {last1}, {year})"
        return f"({last0} et al., {year})"

    def _harvard_entry(self, ref: Dict) -> str:
        authors_str = " and ".join(ref["authors"])
        year = ref["year"]
        title = ref["title"]
        ref_type = ref.get("type", "other")

        if ref_type == "journal":
            journal = ref.get("journal", "")
            volume = ref.get("volume", "")
            issue = ref.get("issue", "")
            pages = ref.get("pages", "")
            doi = ref.get("doi", "")
            issue_str = f"({issue})" if issue else ""
            doi_str = f", doi: {doi}" if doi else ""
            return (
                f"{authors_str} ({year}) '{title}', "
                f"{journal}, {volume}{issue_str}, pp. {pages}{doi_str}."
            )
        if ref_type == "book":
            publisher = ref.get("publisher", "")
            location = ref.get("location", "")
            return f"{authors_str} ({year}) {title}. {location}: {publisher}."
        publisher = ref.get("publisher", "")
        url = ref.get("url", "")
        url_str = f" Available at: {url}" if url else ""
        return f"{authors_str} ({year}) {title}. {publisher}.{url_str}"

    # ------------------------------------------------------------------
    # IEEE helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ieee_entry(number: int, ref: Dict) -> str:
        authors = ref["authors"]
        year = ref["year"]
        title = ref["title"]
        ref_type = ref.get("type", "other")

        # Abbreviated author list (IEEE uses initials)
        def _abbrev(name: str) -> str:
            parts = name.split(",")
            if len(parts) >= 2:
                last = parts[0].strip()
                first_initials = "".join(
                    p.strip()[0] + "." for p in parts[1].split() if p.strip()
                )
                return f"{first_initials} {last}"
            return name

        authors_str = ", ".join(_abbrev(a) for a in authors[:3])
        if len(authors) > 3:
            authors_str += " et al."

        if ref_type == "journal":
            journal = ref.get("journal", "")
            volume = ref.get("volume", "")
            issue = ref.get("issue", "")
            pages = ref.get("pages", "")
            doi = ref.get("doi", "")
            doi_str = f", doi: {doi}" if doi else ""
            return (
                f"[{number}] {authors_str}, \"{title}\", "
                f"{journal}, vol. {volume}, no. {issue}, pp. {pages}, {year}{doi_str}."
            )
        if ref_type == "book":
            publisher = ref.get("publisher", "")
            location = ref.get("location", "")
            return (
                f"[{number}] {authors_str}, {title}. "
                f"{location}: {publisher}, {year}."
            )
        publisher = ref.get("publisher", "")
        url = ref.get("url", "")
        url_str = f" [Online]. Available: {url}" if url else ""
        return f"[{number}] {authors_str}, {title}. {publisher}, {year}.{url_str}"
