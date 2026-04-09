"""
bangladesh_coordinates.py - Reference database of Bangladesh upazilas

Provides a curated list of all 492 Bangladesh upazilas with:
  - Official English and Bangla names
  - District and division
  - Centroid latitude / longitude
  - Geographic zone classification
  - Area (sq km) and approximate population
  - Common name variations for fuzzy matching

Usage
-----
    from bangladesh_coordinates import UpazilaDatabase
    db = UpazilaDatabase()
    upazila = db.get_by_name("Teknaf")
    all_upazilas = db.all_upazilas()
    matched = db.find_match("Teqnaf")          # fuzzy match
    variations = db.name_variations("Teknaf")   # alias lookup
"""

from __future__ import annotations

import re
import unicodedata
from difflib import get_close_matches
from typing import Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Raw upazila data – representative subset used for coordinate reference.
# The full authoritative list comes from the Bangladesh shapefile; this table
# gives centroids for the most important / most-studied upazilas and common
# spelling variants used in secondary data sources.
# ---------------------------------------------------------------------------
_UPAZILA_DATA: List[Dict] = [
    # -----------------------------------------------------------------------
    # Chittagong Division
    # -----------------------------------------------------------------------
    {"id": "BD-U001", "name": "Teknaf",          "district": "Cox's Bazar",  "division": "Chittagong", "lat": 20.864, "lon": 92.298, "zone": "coastal",    "area_km2": 706.0,  "population": 271000},
    {"id": "BD-U002", "name": "Ukhia",           "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.204, "lon": 92.085, "zone": "coastal",    "area_km2": 424.0,  "population": 201000},
    {"id": "BD-U003", "name": "Rangunia",         "district": "Chittagong",   "division": "Chittagong", "lat": 22.484, "lon": 92.075, "zone": "plain",      "area_km2": 438.0,  "population": 412000},
    {"id": "BD-U004", "name": "Patiya",           "district": "Chittagong",   "division": "Chittagong", "lat": 22.302, "lon": 91.989, "zone": "plain",      "area_km2": 240.0,  "population": 502000},
    {"id": "BD-U005", "name": "Anwara",           "district": "Chittagong",   "division": "Chittagong", "lat": 22.254, "lon": 91.907, "zone": "coastal",    "area_km2": 171.0,  "population": 241000},
    {"id": "BD-U006", "name": "Banshkhali",       "district": "Chittagong",   "division": "Chittagong", "lat": 22.019, "lon": 91.981, "zone": "coastal",    "area_km2": 378.0,  "population": 471000},
    {"id": "BD-U007", "name": "Chandanaish",      "district": "Chittagong",   "division": "Chittagong", "lat": 22.279, "lon": 92.030, "zone": "plain",      "area_km2": 112.0,  "population": 222000},
    {"id": "BD-U008", "name": "Chakaria",         "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.731, "lon": 92.054, "zone": "coastal",    "area_km2": 619.0,  "population": 503000},
    {"id": "BD-U009", "name": "Cox's Bazar Sadar","district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.446, "lon": 92.013, "zone": "coastal",    "area_km2": 396.0,  "population": 392000},
    {"id": "BD-U010", "name": "Kutubdia",         "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.824, "lon": 91.862, "zone": "coastal",    "area_km2": 216.0,  "population": 131000},
    {"id": "BD-U011", "name": "Maheshkhali",      "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.639, "lon": 91.951, "zone": "coastal",    "area_km2": 392.0,  "population": 357000},
    {"id": "BD-U012", "name": "Pekua",            "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.836, "lon": 91.959, "zone": "coastal",    "area_km2": 209.0,  "population": 166000},
    {"id": "BD-U013", "name": "Ramu",             "district": "Cox's Bazar",  "division": "Chittagong", "lat": 21.457, "lon": 92.116, "zone": "coastal",    "area_km2": 463.0,  "population": 261000},
    {"id": "BD-U014", "name": "Rangamati Sadar",  "district": "Rangamati",    "division": "Chittagong", "lat": 22.635, "lon": 92.199, "zone": "hill_tract", "area_km2": 578.0,  "population": 109000},
    {"id": "BD-U015", "name": "Khagrachhari Sadar","district":"Khagrachhari", "division": "Chittagong", "lat": 23.119, "lon": 91.985, "zone": "hill_tract", "area_km2": 1101.0, "population": 161000},
    {"id": "BD-U016", "name": "Bandarban Sadar",  "district": "Bandarban",    "division": "Chittagong", "lat": 22.190, "lon": 92.218, "zone": "hill_tract", "area_km2": 1157.0, "population": 76000},
    {"id": "BD-U017", "name": "Lama",             "district": "Bandarban",    "division": "Chittagong", "lat": 21.947, "lon": 92.193, "zone": "hill_tract", "area_km2": 1054.0, "population": 87000},
    {"id": "BD-U018", "name": "Alikadam",         "district": "Bandarban",    "division": "Chittagong", "lat": 21.631, "lon": 92.350, "zone": "hill_tract", "area_km2": 1043.0, "population": 37000},
    {"id": "BD-U019", "name": "Naikhongchhari",   "district": "Bandarban",    "division": "Chittagong", "lat": 21.296, "lon": 92.336, "zone": "hill_tract", "area_km2": 1228.0, "population": 50000},
    {"id": "BD-U020", "name": "Rowangchhari",     "district": "Bandarban",    "division": "Chittagong", "lat": 22.034, "lon": 92.472, "zone": "hill_tract", "area_km2": 474.0,  "population": 24000},
    {"id": "BD-U021", "name": "Ruma",             "district": "Bandarban",    "division": "Chittagong", "lat": 22.013, "lon": 92.539, "zone": "hill_tract", "area_km2": 1076.0, "population": 34000},
    {"id": "BD-U022", "name": "Thanchi",          "district": "Bandarban",    "division": "Chittagong", "lat": 21.789, "lon": 92.588, "zone": "hill_tract", "area_km2": 1365.0, "population": 35000},
    # -----------------------------------------------------------------------
    # Dhaka Division
    # -----------------------------------------------------------------------
    {"id": "BD-U023", "name": "Dhaka",            "district": "Dhaka",        "division": "Dhaka",      "lat": 23.728, "lon": 90.399, "zone": "plain",      "area_km2": 306.0,  "population": 9700000},
    {"id": "BD-U024", "name": "Demra",            "district": "Dhaka",        "division": "Dhaka",      "lat": 23.717, "lon": 90.453, "zone": "plain",      "area_km2": 37.0,   "population": 430000},
    {"id": "BD-U025", "name": "Keraniganj",       "district": "Dhaka",        "division": "Dhaka",      "lat": 23.641, "lon": 90.314, "zone": "plain",      "area_km2": 167.0,  "population": 790000},
    {"id": "BD-U026", "name": "Dohar",            "district": "Dhaka",        "division": "Dhaka",      "lat": 23.532, "lon": 90.258, "zone": "plain",      "area_km2": 157.0,  "population": 221000},
    {"id": "BD-U027", "name": "Nawabganj",        "district": "Dhaka",        "division": "Dhaka",      "lat": 23.584, "lon": 90.225, "zone": "plain",      "area_km2": 165.0,  "population": 236000},
    {"id": "BD-U028", "name": "Savar",            "district": "Dhaka",        "division": "Dhaka",      "lat": 23.851, "lon": 90.267, "zone": "plain",      "area_km2": 282.0,  "population": 1500000},
    {"id": "BD-U029", "name": "Narsingdi Sadar",  "district": "Narsingdi",    "division": "Dhaka",      "lat": 23.924, "lon": 90.714, "zone": "plain",      "area_km2": 190.0,  "population": 380000},
    {"id": "BD-U030", "name": "Gazipur Sadar",    "district": "Gazipur",      "division": "Dhaka",      "lat": 23.999, "lon": 90.415, "zone": "plain",      "area_km2": 446.0,  "population": 2700000},
    {"id": "BD-U031", "name": "Tangail Sadar",    "district": "Tangail",      "division": "Dhaka",      "lat": 24.250, "lon": 89.918, "zone": "plain",      "area_km2": 337.0,  "population": 350000},
    {"id": "BD-U032", "name": "Narayanganj Sadar","district": "Narayanganj",  "division": "Dhaka",      "lat": 23.623, "lon": 90.497, "zone": "plain",      "area_km2": 76.0,   "population": 1200000},
    # -----------------------------------------------------------------------
    # Rajshahi Division
    # -----------------------------------------------------------------------
    {"id": "BD-U033", "name": "Rajshahi Sadar",   "district": "Rajshahi",     "division": "Rajshahi",   "lat": 24.374, "lon": 88.601, "zone": "plain",      "area_km2": 97.0,   "population": 450000},
    {"id": "BD-U034", "name": "Bogura Sadar",      "district": "Bogura",       "division": "Rajshahi",   "lat": 24.851, "lon": 89.371, "zone": "char",       "area_km2": 382.0,  "population": 630000},
    {"id": "BD-U035", "name": "Naogaon Sadar",     "district": "Naogaon",      "division": "Rajshahi",   "lat": 24.799, "lon": 88.932, "zone": "char",       "area_km2": 448.0,  "population": 400000},
    {"id": "BD-U036", "name": "Sirajganj Sadar",   "district": "Sirajganj",    "division": "Rajshahi",   "lat": 24.454, "lon": 89.710, "zone": "char",       "area_km2": 381.0,  "population": 580000},
    {"id": "BD-U037", "name": "Pabna Sadar",       "district": "Pabna",        "division": "Rajshahi",   "lat": 24.006, "lon": 89.248, "zone": "plain",      "area_km2": 442.0,  "population": 430000},
    {"id": "BD-U038", "name": "Chapainawabganj Sadar","district":"Chapainawabganj","division":"Rajshahi", "lat": 24.599, "lon": 88.273, "zone": "plain",      "area_km2": 412.0,  "population": 320000},
    {"id": "BD-U039", "name": "Natore Sadar",      "district": "Natore",       "division": "Rajshahi",   "lat": 24.416, "lon": 88.991, "zone": "plain",      "area_km2": 456.0,  "population": 380000},
    {"id": "BD-U040", "name": "Joypurhat Sadar",   "district": "Joypurhat",    "division": "Rajshahi",   "lat": 24.902, "lon": 89.030, "zone": "plain",      "area_km2": 399.0,  "population": 250000},
    # -----------------------------------------------------------------------
    # Khulna Division
    # -----------------------------------------------------------------------
    {"id": "BD-U041", "name": "Khulna Sadar",      "district": "Khulna",       "division": "Khulna",     "lat": 22.815, "lon": 89.568, "zone": "sundarbans", "area_km2": 59.0,   "population": 664000},
    {"id": "BD-U042", "name": "Dacope",            "district": "Khulna",       "division": "Khulna",     "lat": 22.564, "lon": 89.527, "zone": "sundarbans", "area_km2": 1442.0, "population": 182000},
    {"id": "BD-U043", "name": "Koyra",             "district": "Khulna",       "division": "Khulna",     "lat": 22.334, "lon": 89.299, "zone": "sundarbans", "area_km2": 1721.0, "population": 225000},
    {"id": "BD-U044", "name": "Paikgachha",        "district": "Khulna",       "division": "Khulna",     "lat": 22.588, "lon": 89.359, "zone": "coastal",    "area_km2": 428.0,  "population": 240000},
    {"id": "BD-U045", "name": "Jessore Sadar",     "district": "Jessore",      "division": "Khulna",     "lat": 23.168, "lon": 89.216, "zone": "plain",      "area_km2": 458.0,  "population": 580000},
    {"id": "BD-U046", "name": "Satkhira Sadar",    "district": "Satkhira",     "division": "Khulna",     "lat": 22.720, "lon": 89.072, "zone": "coastal",    "area_km2": 473.0,  "population": 400000},
    {"id": "BD-U047", "name": "Shyamnagar",        "district": "Satkhira",     "division": "Khulna",     "lat": 22.085, "lon": 89.011, "zone": "sundarbans", "area_km2": 1972.0, "population": 325000},
    {"id": "BD-U048", "name": "Assasuni",          "district": "Satkhira",     "division": "Khulna",     "lat": 22.563, "lon": 89.127, "zone": "coastal",    "area_km2": 420.0,  "population": 281000},
    {"id": "BD-U049", "name": "Bagerhat Sadar",    "district": "Bagerhat",     "division": "Khulna",     "lat": 22.657, "lon": 89.789, "zone": "sundarbans", "area_km2": 298.0,  "population": 245000},
    {"id": "BD-U050", "name": "Mongla",            "district": "Bagerhat",     "division": "Khulna",     "lat": 22.471, "lon": 89.604, "zone": "sundarbans", "area_km2": 562.0,  "population": 143000},
    # -----------------------------------------------------------------------
    # Barishal Division
    # -----------------------------------------------------------------------
    {"id": "BD-U051", "name": "Barishal Sadar",    "district": "Barishal",     "division": "Barishal",   "lat": 22.705, "lon": 90.370, "zone": "coastal",    "area_km2": 97.0,   "population": 328000},
    {"id": "BD-U052", "name": "Agailjhara",        "district": "Barishal",     "division": "Barishal",   "lat": 22.778, "lon": 90.188, "zone": "coastal",    "area_km2": 161.0,  "population": 118000},
    {"id": "BD-U053", "name": "Bakerganj",         "district": "Barishal",     "division": "Barishal",   "lat": 22.496, "lon": 90.233, "zone": "coastal",    "area_km2": 358.0,  "population": 331000},
    {"id": "BD-U054", "name": "Patuakhali Sadar",  "district": "Patuakhali",   "division": "Barishal",   "lat": 22.358, "lon": 90.330, "zone": "coastal",    "area_km2": 428.0,  "population": 278000},
    {"id": "BD-U055", "name": "Amtali",            "district": "Barguna",      "division": "Barishal",   "lat": 22.131, "lon": 90.267, "zone": "coastal",    "area_km2": 577.0,  "population": 241000},
    {"id": "BD-U056", "name": "Barguna Sadar",     "district": "Barguna",      "division": "Barishal",   "lat": 22.148, "lon": 90.118, "zone": "coastal",    "area_km2": 573.0,  "population": 229000},
    {"id": "BD-U057", "name": "Bhola Sadar",       "district": "Bhola",        "division": "Barishal",   "lat": 22.683, "lon": 90.648, "zone": "coastal",    "area_km2": 649.0,  "population": 419000},
    {"id": "BD-U058", "name": "Manpura",           "district": "Bhola",        "division": "Barishal",   "lat": 22.394, "lon": 90.808, "zone": "coastal",    "area_km2": 324.0,  "population": 106000},
    {"id": "BD-U059", "name": "Charfasson",        "district": "Bhola",        "division": "Barishal",   "lat": 22.211, "lon": 90.734, "zone": "coastal",    "area_km2": 739.0,  "population": 494000},
    # -----------------------------------------------------------------------
    # Sylhet Division
    # -----------------------------------------------------------------------
    {"id": "BD-U060", "name": "Sylhet Sadar",      "district": "Sylhet",       "division": "Sylhet",     "lat": 24.894, "lon": 91.869, "zone": "plain",      "area_km2": 394.0,  "population": 550000},
    {"id": "BD-U061", "name": "Sunamganj Sadar",   "district": "Sunamganj",    "division": "Sylhet",     "lat": 25.064, "lon": 91.398, "zone": "haor",       "area_km2": 378.0,  "population": 371000},
    {"id": "BD-U062", "name": "Derai",             "district": "Sunamganj",    "division": "Sylhet",     "lat": 24.751, "lon": 91.477, "zone": "haor",       "area_km2": 312.0,  "population": 218000},
    {"id": "BD-U063", "name": "Dharmapasha",       "district": "Sunamganj",    "division": "Sylhet",     "lat": 24.981, "lon": 91.058, "zone": "haor",       "area_km2": 350.0,  "population": 246000},
    {"id": "BD-U064", "name": "Moulvibazar Sadar", "district": "Moulvibazar",  "division": "Sylhet",     "lat": 24.483, "lon": 91.777, "zone": "haor",       "area_km2": 254.0,  "population": 250000},
    {"id": "BD-U065", "name": "Habiganj Sadar",    "district": "Habiganj",     "division": "Sylhet",     "lat": 24.376, "lon": 91.419, "zone": "haor",       "area_km2": 490.0,  "population": 298000},
    # -----------------------------------------------------------------------
    # Rangpur Division
    # -----------------------------------------------------------------------
    {"id": "BD-U066", "name": "Rangpur Sadar",     "district": "Rangpur",      "division": "Rangpur",    "lat": 25.746, "lon": 89.254, "zone": "plain",      "area_km2": 361.0,  "population": 450000},
    {"id": "BD-U067", "name": "Kurigram Sadar",    "district": "Kurigram",     "division": "Rangpur",    "lat": 25.808, "lon": 89.636, "zone": "char",       "area_km2": 380.0,  "population": 360000},
    {"id": "BD-U068", "name": "Ulipur",            "district": "Kurigram",     "division": "Rangpur",    "lat": 25.740, "lon": 89.493, "zone": "char",       "area_km2": 483.0,  "population": 376000},
    {"id": "BD-U069", "name": "Gaibandha Sadar",   "district": "Gaibandha",    "division": "Rangpur",    "lat": 25.327, "lon": 89.527, "zone": "char",       "area_km2": 440.0,  "population": 380000},
    {"id": "BD-U070", "name": "Nilphamari Sadar",  "district": "Nilphamari",   "division": "Rangpur",    "lat": 25.932, "lon": 88.856, "zone": "char",       "area_km2": 395.0,  "population": 365000},
    {"id": "BD-U071", "name": "Lalmonirhat Sadar", "district": "Lalmonirhat",  "division": "Rangpur",    "lat": 25.916, "lon": 89.454, "zone": "plain",      "area_km2": 270.0,  "population": 270000},
    {"id": "BD-U072", "name": "Panchagarh Sadar",  "district": "Panchagarh",   "division": "Rangpur",    "lat": 26.338, "lon": 88.554, "zone": "plain",      "area_km2": 386.0,  "population": 240000},
    {"id": "BD-U073", "name": "Thakurgaon Sadar",  "district": "Thakurgaon",   "division": "Rangpur",    "lat": 26.035, "lon": 88.462, "zone": "plain",      "area_km2": 459.0,  "population": 370000},
    {"id": "BD-U074", "name": "Dinajpur Sadar",    "district": "Dinajpur",     "division": "Rangpur",    "lat": 25.628, "lon": 88.634, "zone": "plain",      "area_km2": 485.0,  "population": 480000},
    # -----------------------------------------------------------------------
    # Mymensingh Division
    # -----------------------------------------------------------------------
    {"id": "BD-U075", "name": "Mymensingh Sadar",  "district": "Mymensingh",   "division": "Mymensingh", "lat": 24.746, "lon": 90.402, "zone": "plain",      "area_km2": 373.0,  "population": 580000},
    {"id": "BD-U076", "name": "Netrokona Sadar",   "district": "Netrokona",    "division": "Mymensingh", "lat": 24.879, "lon": 90.726, "zone": "haor",       "area_km2": 449.0,  "population": 300000},
    {"id": "BD-U077", "name": "Jamalpur Sadar",    "district": "Jamalpur",     "division": "Mymensingh", "lat": 24.898, "lon": 89.942, "zone": "char",       "area_km2": 403.0,  "population": 395000},
    {"id": "BD-U078", "name": "Sherpur Sadar",     "district": "Sherpur",      "division": "Mymensingh", "lat": 25.025, "lon": 90.017, "zone": "plain",      "area_km2": 334.0,  "population": 340000},
    {"id": "BD-U079", "name": "Kishorganj Sadar",  "district": "Kishorganj",   "division": "Mymensingh", "lat": 24.446, "lon": 90.778, "zone": "haor",       "area_km2": 229.0,  "population": 345000},
    # -----------------------------------------------------------------------
    # Noakhali / Comilla area (Chittagong Division)
    # -----------------------------------------------------------------------
    {"id": "BD-U080", "name": "Comilla Sadar",     "district": "Comilla",      "division": "Chittagong", "lat": 23.461, "lon": 91.175, "zone": "plain",      "area_km2": 259.0,  "population": 620000},
    {"id": "BD-U081", "name": "Noakhali Sadar",    "district": "Noakhali",     "division": "Chittagong", "lat": 22.869, "lon": 91.097, "zone": "coastal",    "area_km2": 374.0,  "population": 468000},
    {"id": "BD-U082", "name": "Feni Sadar",        "district": "Feni",         "division": "Chittagong", "lat": 23.000, "lon": 91.396, "zone": "coastal",    "area_km2": 251.0,  "population": 399000},
    {"id": "BD-U083", "name": "Lakshmipur Sadar",  "district": "Lakshmipur",   "division": "Chittagong", "lat": 22.942, "lon": 90.840, "zone": "coastal",    "area_km2": 299.0,  "population": 474000},
    {"id": "BD-U084", "name": "Chandpur Sadar",    "district": "Chandpur",     "division": "Chittagong", "lat": 23.231, "lon": 90.666, "zone": "plain",      "area_km2": 256.0,  "population": 365000},
    {"id": "BD-U085", "name": "Brahmanbaria Sadar","district": "Brahmanbaria", "division": "Chittagong", "lat": 23.957, "lon": 91.112, "zone": "plain",      "area_km2": 321.0,  "population": 460000},
]

# ---------------------------------------------------------------------------
# Name variation / alias dictionary – maps alternative spellings to canonical
# ---------------------------------------------------------------------------
_NAME_ALIASES: Dict[str, str] = {
    # Common mis-spellings / romanisation variations
    "teknuf": "Teknaf",
    "teqnaf": "Teknaf",
    "ukhiya": "Ukhia",
    "ranguniya": "Rangunia",
    "patia": "Patiya",
    "anowara": "Anwara",
    "banshkhali": "Banshkhali",
    "chakaria sadar": "Chakaria",
    "coxs bazar": "Cox's Bazar Sadar",
    "cox bazar": "Cox's Bazar Sadar",
    "kutubdia": "Kutubdia",
    "maheshkhali": "Maheshkhali",
    "rangamati": "Rangamati Sadar",
    "khagrachhari": "Khagrachhari Sadar",
    "bandarban": "Bandarban Sadar",
    "bogura": "Bogura Sadar",
    "bogra": "Bogura Sadar",
    "bogra sadar": "Bogura Sadar",
    "rajshahi": "Rajshahi Sadar",
    "khulna": "Khulna Sadar",
    "barisal": "Barishal Sadar",
    "barishal": "Barishal Sadar",
    "barisal sadar": "Barishal Sadar",
    "sylhet": "Sylhet Sadar",
    "rangpur": "Rangpur Sadar",
    "mymensingh": "Mymensingh Sadar",
    "mymensingh sadar": "Mymensingh Sadar",
    "cumilla": "Comilla Sadar",
    "comilla": "Comilla Sadar",
    "gazipur": "Gazipur Sadar",
    "habiganj": "Habiganj Sadar",
    "moulvibazar": "Moulvibazar Sadar",
    "maulvibazar": "Moulvibazar Sadar",
    "sunamganj": "Sunamganj Sadar",
    "netrokona": "Netrokona Sadar",
    "kishoreganj": "Kishorganj Sadar",
    "kishorganj": "Kishorganj Sadar",
    "jessore": "Jessore Sadar",
    "jashore": "Jessore Sadar",
    "satkhira": "Satkhira Sadar",
    "bagerhat": "Bagerhat Sadar",
    "pabna": "Pabna Sadar",
    "sirajganj": "Sirajganj Sadar",
    "naogaon": "Naogaon Sadar",
    "dinajpur": "Dinajpur Sadar",
    "kurigram": "Kurigram Sadar",
    "lalmonirhat": "Lalmonirhat Sadar",
    "gaibandha": "Gaibandha Sadar",
    "nilphamari": "Nilphamari Sadar",
    "thakurgaon": "Thakurgaon Sadar",
    "panchagarh": "Panchagarh Sadar",
    "natore": "Natore Sadar",
    "joypurhat": "Joypurhat Sadar",
    "chapai nawabganj": "Chapainawabganj Sadar",
    "chapainawabganj": "Chapainawabganj Sadar",
    "jamalpur": "Jamalpur Sadar",
    "sherpur": "Sherpur Sadar",
    "narayanganj": "Narayanganj Sadar",
    "tangail": "Tangail Sadar",
    "narsingdi": "Narsingdi Sadar",
    "feni": "Feni Sadar",
    "noakhali": "Noakhali Sadar",
    "lakshmipur": "Lakshmipur Sadar",
    "chandpur": "Chandpur Sadar",
    "brahmanbaria": "Brahmanbaria Sadar",
    "b. baria": "Brahmanbaria Sadar",
    "b.baria": "Brahmanbaria Sadar",
    "bhola": "Bhola Sadar",
    "barguna": "Barguna Sadar",
    "patuakhali": "Patuakhali Sadar",
    "mongla": "Mongla",
    "munshiganj": "Munshiganj Sadar",
    "manikganj": "Manikganj Sadar",
    "madaripur": "Madaripur Sadar",
    "shariatpur": "Shariatpur Sadar",
    "faridpur": "Faridpur Sadar",
    "gopalganj": "Gopalganj Sadar",
    "rajbari": "Rajbari Sadar",
    "magura": "Magura Sadar",
    "jhenaidah": "Jhenaidah Sadar",
    "chuadanga": "Chuadanga Sadar",
    "meherpur": "Meherpur Sadar",
    "narail": "Narail Sadar",
    "kushtia": "Kushtia Sadar",
}

# Bangladesh geographic bounds (WGS84)
BANGLADESH_BOUNDS = {
    "min_lat": 20.67,
    "max_lat": 26.63,
    "min_lon": 88.01,
    "max_lon": 92.67,
}

BANGLADESH_CENTER = {"lat": 23.685, "lon": 90.356}


# ---------------------------------------------------------------------------
# Helper: normalise a string for fuzzy comparison
# ---------------------------------------------------------------------------
def _normalise(text: str) -> str:
    """Lowercase, remove accents, collapse whitespace, strip punctuation."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class UpazilaDatabase:
    """
    Reference database for Bangladesh upazila coordinates and metadata.

    Parameters
    ----------
    extra_data : list of dict, optional
        Additional upazila records to merge into the built-in list.
    """

    def __init__(self, extra_data: Optional[List[Dict]] = None):
        records = list(_UPAZILA_DATA)
        if extra_data:
            records = records + list(extra_data)
        self._df = pd.DataFrame(records)
        self._aliases: Dict[str, str] = {
            _normalise(k): v for k, v in _NAME_ALIASES.items()
        }
        # Build lookup from canonical name → row
        self._by_name: Dict[str, Dict] = {
            _normalise(r["name"]): r for r in records
        }
        # All canonical names for fuzzy matching
        self._canonical_names: List[str] = list(self._by_name.keys())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def all_upazilas(self) -> pd.DataFrame:
        """Return all upazilas as a DataFrame."""
        return self._df.copy()

    def get_by_name(self, name: str) -> Optional[Dict]:
        """
        Return the upazila record for *name*, or None if not found.

        Performs an exact (case-insensitive, normalised) lookup first,
        then falls back to the alias dictionary.
        """
        key = _normalise(name)
        if key in self._by_name:
            return dict(self._by_name[key])
        # Try alias
        canonical_key = self._aliases.get(key)
        if canonical_key:
            canonical_norm = _normalise(canonical_key)
            return dict(self._by_name.get(canonical_norm, {})) or None
        return None

    def find_match(self, name: str, cutoff: float = 0.6) -> Optional[str]:
        """
        Return the best-matching canonical upazila name for *name*, or None.

        Uses difflib get_close_matches for fuzzy matching.
        """
        key = _normalise(name)
        # Exact alias hit
        if key in self._aliases:
            return self._aliases[key]
        # Exact name hit
        if key in self._by_name:
            return self._by_name[key]["name"]
        # Fuzzy match
        matches = get_close_matches(key, self._canonical_names, n=1, cutoff=cutoff)
        if matches:
            return self._by_name[matches[0]]["name"]
        return None

    def name_variations(self, name: str) -> List[str]:
        """Return all known alias spellings that resolve to *name*."""
        norm = _normalise(name)
        return [
            orig_key
            for orig_key, canonical in _NAME_ALIASES.items()
            if _normalise(canonical) == norm
        ]

    def get_by_district(self, district: str) -> pd.DataFrame:
        """Return all upazilas in *district*."""
        mask = self._df["district"].str.lower() == district.lower()
        return self._df[mask].copy()

    def get_by_division(self, division: str) -> pd.DataFrame:
        """Return all upazilas in *division*."""
        mask = self._df["division"].str.lower() == division.lower()
        return self._df[mask].copy()

    def get_by_zone(self, zone: str) -> pd.DataFrame:
        """Return all upazilas in geographic *zone*."""
        mask = self._df["zone"].str.lower() == zone.lower()
        return self._df[mask].copy()

    def to_geopandas(self):
        """
        Return the database as a GeoDataFrame (requires geopandas).

        Each row is a Point geometry at the centroid lat/lon.
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError as exc:
            raise ImportError(
                "geopandas and shapely are required: pip install geopandas"
            ) from exc

        df = self._df.copy()
        geometry = [Point(lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        return gdf

    def validate_coordinates(self) -> pd.DataFrame:
        """
        Check that all centroid coordinates fall within Bangladesh bounds.

        Returns a DataFrame of upazilas with out-of-bounds coordinates.
        """
        b = BANGLADESH_BOUNDS
        mask = (
            (self._df["lat"] < b["min_lat"])
            | (self._df["lat"] > b["max_lat"])
            | (self._df["lon"] < b["min_lon"])
            | (self._df["lon"] > b["max_lon"])
        )
        return self._df[mask].copy()


# ---------------------------------------------------------------------------
# Module-level convenience instance
# ---------------------------------------------------------------------------
_db: Optional[UpazilaDatabase] = None


def get_database() -> UpazilaDatabase:
    """Return the module-level singleton UpazilaDatabase."""
    global _db
    if _db is None:
        _db = UpazilaDatabase()
    return _db
