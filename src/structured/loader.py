"""
src/structured/loader.py

Lazy loaders for structured zoning/site datasets.
"""

import os

import pandas as pd

from pathlib import Path


# ─────────────────────────────────────────────────────
# PROJECT ROOT
# ─────────────────────────────────────────────────────

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

# ─────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────

STRUCTURED_DIR = (
    PROJECT_ROOT / "corpus" / "structured"
)

SITE_RECORDS_PATH = (
    STRUCTURED_DIR / "site_records.csv"
)

PLUTO_PATH = (
    STRUCTURED_DIR / "pluto_25v4.csv"
)

# ─────────────────────────────────────────────────────
# SINGLETON DATAFRAMES
# ─────────────────────────────────────────────────────

_site_records_df = None

_pluto_df = None


# ─────────────────────────────────────────────────────
# LOAD SITE RECORDS
# ─────────────────────────────────────────────────────

def get_site_records():

    global _site_records_df

    if _site_records_df is None:

        # print(
        #     f"[INFO] Loading site records from:\n"
        #     f"{SITE_RECORDS_PATH}\n"
        # )

        _site_records_df = pd.read_csv(
            SITE_RECORDS_PATH,
            dtype=str
        )

        _site_records_df.fillna(
            "",
            inplace=True
        )

        # print(
        #     f"[INFO] Loaded "
        #     f"{len(_site_records_df)} "
        #     f"site records"
        # )

    return _site_records_df


# ─────────────────────────────────────────────────────
# LOAD PLUTO
# ─────────────────────────────────────────────────────

def get_pluto():

    global _pluto_df

    # PLUTO is supplementary (large citywide file, gitignored) —
    # the 5 test BBLs are fully defined in site_records.csv, so a
    # missing PLUTO file should degrade gracefully, not crash.
    if _pluto_df is None and not os.path.exists(PLUTO_PATH):

        return None

    if _pluto_df is None:

        # print(
        #     f"[INFO] Loading PLUTO from:\n"
        #     f"{PLUTO_PATH}\n"
        # )

        _pluto_df = pd.read_csv(
            PLUTO_PATH,
            dtype=str,
            low_memory=False
        )

        _pluto_df.fillna(
            "",
            inplace=True
        )

        # print(
        #     f"[INFO] Loaded "
        #     f"{len(_pluto_df)} "
        #     f"PLUTO records"
        # )

    return _pluto_df