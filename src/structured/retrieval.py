"""
src/structured/retrieval.py

Structured retrieval for:
- BBL lookups
- zoning district lookup
- flood zone lookup
- PLUTO enrichment
"""

from src.structured.loader import (
    get_site_records,
    get_pluto
)

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────
# NORMALIZATION
# ─────────────────────────────────────────────────────

def normalize_bbl(
    bbl
):

    return str(bbl).strip().replace(".0", "")

# ─────────────────────────────────────────────────────
# SITE RECORD LOOKUP
# ─────────────────────────────────────────────────────

def lookup_site_by_bbl(
    bbl: str
):

    df = get_site_records()

    normalized = normalize_bbl(bbl)

    matches = df[
        df["bbl"].apply(normalize_bbl)
        == normalized
    ]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()

# ─────────────────────────────────────────────────────
# PLUTO LOOKUP
# ─────────────────────────────────────────────────────

def lookup_pluto_by_bbl(
    bbl: str
):

    df = get_pluto()

    if df is None:
        return None

    normalized = normalize_bbl(bbl)

    matches = df[
        df["BBL"].apply(normalize_bbl)
        == normalized
    ]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()

# ─────────────────────────────────────────────────────
# COMBINED SITE PROFILE
# ─────────────────────────────────────────────────────

def get_complete_site_profile(
    bbl: str
):

    site_record = lookup_site_by_bbl(bbl)

    pluto_record = lookup_pluto_by_bbl(bbl)

    return {

        "bbl": bbl,

        "site_record": site_record,

        "pluto_record": pluto_record
    }

# ─────────────────────────────────────────────────────
# QUICK SUMMARY
# ─────────────────────────────────────────────────────

def summarize_site_profile(
    profile: dict
):

    site = profile.get(
        "site_record"
    ) or {}

    pluto = profile.get(
        "pluto_record"
    ) or {}

    summary = {

        # -------------------------------------------------
        # CORE
        # -------------------------------------------------

        "bbl": profile.get("bbl"),

        "address": (
            site.get("address")
            or pluto.get("address")
        ),

        "borough": (
            site.get("borough")
            or pluto.get("borough")
        ),

        # -------------------------------------------------
        # ZONING
        # -------------------------------------------------

        "zoning_district": (
            site.get("zoning_district")
            or pluto.get("zonedist1")
        ),

        "overlay": (
            site.get("overlay")
            or pluto.get("overlay1")
        ),

        "special_district": (
            site.get("special_district")
            or pluto.get("spdist1")
        ),

        "zoning_map": (
            pluto.get("zonemap")
        ),

        # -------------------------------------------------
        # FAR
        # -------------------------------------------------

        "built_far": (
            pluto.get("builtfar")
        ),

        "residential_far": (
            pluto.get("residfar")
        ),

        "commercial_far": (
            pluto.get("commfar")
        ),

        "facility_far": (
            pluto.get("facilfar")
        ),

        # -------------------------------------------------
        # LOT / BUILDING
        # -------------------------------------------------

        "lot_area_sqft": (
            site.get("lot_area_sqft")
            or pluto.get("lotarea")
        ),

        "building_area_sqft": (
            site.get("building_area_sqft")
            or pluto.get("bldgarea")
        ),

        "lot_front_ft": (
            pluto.get("lotfront")
        ),

        "lot_depth_ft": (
            pluto.get("lotdepth")
        ),

        "building_front_ft": (
            pluto.get("bldgfront")
        ),

        "building_depth_ft": (
            pluto.get("bldgdepth")
        ),

        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        "year_built": (
            site.get("year_built")
            or pluto.get("yearbuilt")
        ),

        "year_altered_1": (
            pluto.get("yearalter1")
        ),

        "year_altered_2": (
            pluto.get("yearalter2")
        ),

        "num_floors": (
            pluto.get("numfloors")
        ),

        "land_use": (
            pluto.get("landuse")
        ),

        # -------------------------------------------------
        # ENVIRONMENT
        # -------------------------------------------------

        "flood_zone": (
            site.get("flood_zone_fema")
        ),

        "e_designation": (
            site.get("e_designation")
        ),

        "e_designation_type": (
            site.get("e_designation_type")
        ),

        "landmark": (
            pluto.get("landmark")
        ),

        "historic_district": (
            pluto.get("histdist")
        ),

        # -------------------------------------------------
        # NOTES
        # -------------------------------------------------

        "notes": (
            site.get("notes")
        )
    }

    return summary