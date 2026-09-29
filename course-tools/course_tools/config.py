"""Course-wide settings: model IDs, prices, data locations.

Check model IDs and prices against the Anthropic models page before each cohort.
"""
from __future__ import annotations

import os
from pathlib import Path

MODELS = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}

# USD per million tokens: (input, output). Checked 29 Sep 2026.
PRICES_PER_MTOK = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

SEED = 42
# The buyer is one group with two companies. Each purchase order and invoice belongs to one of them.
ENTITIES = {
    "US": {
        "entity_id": "US", "name": "Nilgiri Distributors Inc",
        "address": "2150 Commerce Park Dr, Dallas, TX 75247", "country": "US", "currency": "USD",
        "tax_id": "84-2716093", "tax_id_type": "EIN", "region": "Texas", "region_code": "TX",
        "note": "Resale certificate on file with all product suppliers",
    },
    "IN": {
        "entity_id": "IN", "name": "Nilgiri Distributors Pvt Ltd",
        "address": "14 Industrial Suburb, Yeshwanthpur, Bengaluru 560022", "country": "IN", "currency": "INR",
        "tax_id": "29AAECN4821K1Z6", "tax_id_type": "GSTIN", "region": "Karnataka", "region_code": "29",
        "note": "",
    },
}

# Per-currency settings used by the harness rules. Amounts are never converted between currencies.
SUPPORTED_CURRENCIES = ("USD", "INR")          # EUR is added by learners in the Week 6 stretch
TOLERANCE = {"USD": 0.05, "INR": 1.00, "EUR": 0.05}          # rounding tolerance on totals
APPROVAL_LIMIT = {"USD": 5000, "INR": 400000, "EUR": 4500}   # a person approves above this
# US sales tax, as a teaching simplification: one combined rate per ship-to state.
SALES_TAX_RATES = {"TX": 8.25, "AZ": 5.6, "CA": 7.25}


def in_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def data_dir() -> Path:
    """Where the course dataset lives.

    Colab: Google Drive (survives a runtime reset) if mounted, else /content.
    Elsewhere: ./data in the repository, or $COURSE_DATA_DIR.
    """
    env = os.environ.get("COURSE_DATA_DIR")
    if env:
        return Path(env)
    drive = Path("/content/drive/MyDrive")
    if drive.exists():
        return drive / "harness-course" / "data"
    if in_colab():
        return Path("/content/harness-course/data")
    return Path.cwd() / "data"


def fake_mode() -> bool:
    """True when notebooks should run against the fake model (tests, CI, offline demos)."""
    return os.environ.get("COURSE_FAKE_LLM", "") == "1"
