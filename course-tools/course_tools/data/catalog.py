"""Master data for the fictional distributor group: suppliers and SKUs.

Everything here is synthetic. Names, tax IDs and bank details are invented and
only follow the shape of real ones.

Suppliers bill in one currency each:
  USD  US suppliers of Nilgiri Distributors Inc (Dallas, Texas)
  INR  Indian suppliers of Nilgiri Distributors Pvt Ltd (Bengaluru)
  EUR  one German supplier (unsupported until the Week 6 stretch)
  USD  one Canadian supplier that agreed to bill in USD
"""
from __future__ import annotations

import random

SUPPLIERS = [
    # id, name, country, currency, region, region_code, city
    ("S01", "Pinecrest Beverage Co", "US", "USD", "North Carolina", "NC", "Asheville"),
    ("S02", "Wheatland Mills LLC", "US", "USD", "Kansas", "KS", "Wichita"),
    ("S03", "Bayou Crunch Snacks Inc", "US", "USD", "Louisiana", "LA", "Baton Rouge"),
    ("S04", "Harborview Home Care Co", "US", "USD", "Wisconsin", "WI", "Milwaukee"),
    ("S05", "Redwood Personal Care Inc", "US", "USD", "California", "CA", "Sacramento"),
    ("S06", "Redrock Packaging Supply LLC", "US", "USD", "Arizona", "AZ", "Phoenix"),
    ("S07", "Sahyadri Beverages Pvt Ltd", "IN", "INR", "Karnataka", "29", "Mysuru"),
    ("S08", "Kaveri Foods LLP", "IN", "INR", "Karnataka", "29", "Mandya"),
    ("S09", "Coromandel Snacks Pvt Ltd", "IN", "INR", "Tamil Nadu", "33", "Hosur"),
    ("S10", "Deccan Personal Care Ltd", "IN", "INR", "Maharashtra", "27", "Pune"),
    ("S11", "Malabar Spices and Staples", "IN", "INR", "Kerala", "32", "Kochi"),
    ("S12", "Godavari Packaged Foods", "IN", "INR", "Andhra Pradesh", "37", "Rajahmundry"),
    ("S13", "Rheinland Feinkost GmbH", "DE", "EUR", "Nordrhein-Westfalen", "NW", "Koeln"),
    ("S14", "Maple Grove Foods Ltd", "CA", "USD", "Ontario", "ON", "Toronto"),
]

# Which buyer company each supplier sells to.
ENTITY_OF = {"US": "US", "IN": "IN", "DE": "US", "CA": "US"}

TAX_ID_TYPE = {"US": "EIN", "IN": "GSTIN", "DE": "VAT ID", "CA": "Business Number"}

# Product families: (description template, tax rate %, base price per case in the supplier's currency).
# US product suppliers sell for resale (0% sales tax: resale certificate on file). S06 sells packaging
# the buyer uses itself, so it is taxable at the Dallas, Texas rate (8.25%).
FAMILIES = {
    "S01": [("Instant Coffee {s} (case of 24)", 0, 96), ("Black Tea {s} (case of 24)", 0, 62),
            ("Mango Juice {s} (case of 24)", 0, 28), ("Sparkling Water {s} (case of 24)", 0, 12)],
    "S02": [("Butter Crackers {s} (case of 24)", 0, 54), ("Rolled Oats {s} (case of 12)", 0, 38),
            ("Spaghetti {s} (case of 20)", 0, 26), ("Corn Flakes {s} (case of 14)", 0, 44)],
    "S03": [("Kettle Chips {s} (case of 24)", 0, 36), ("Salted Peanuts {s} (case of 24)", 0, 42),
            ("Pretzel Twists {s} (case of 24)", 0, 31), ("Popcorn {s} (case of 24)", 0, 29)],
    "S04": [("Floor Cleaner {s} (case of 12)", 0, 48), ("Dish Soap {s} (case of 12)", 0, 34),
            ("Laundry Detergent {s} (case of 6)", 0, 72), ("Toilet Cleaner {s} (case of 12)", 0, 40)],
    "S05": [("Herbal Shampoo {s} (case of 12)", 0, 58), ("Toothpaste {s} (case of 24)", 0, 66),
            ("Bar Soap {s} (case of 48)", 0, 52), ("Body Lotion {s} (case of 12)", 0, 61)],
    "S06": [("Stretch Wrap {s} (case of 4 rolls)", 8.25, 88), ("Corrugated Cartons {s} (bundle of 25)", 8.25, 46),
            ("Packing Tape {s} (case of 36)", 8.25, 54), ("Wood Pallet {s} (each)", 8.25, 14)],
    # India: GST rates, prices in Rs.
    "S07": [("Instant Coffee {s} (case of 24)", 18, 450), ("Assam Tea {s} (case of 24)", 5, 380),
            ("Mango Drink {s} (case of 24)", 12, 290), ("Soda Water {s} (case of 24)", 18, 180)],
    "S08": [("Cream Biscuits {s} (case of 60)", 18, 300), ("Rice Flakes {s} (case of 20)", 12, 260),
            ("Wheat Vermicelli {s} (case of 30)", 12, 240), ("Ragi Malt {s} (case of 24)", 18, 420)],
    "S09": [("Potato Chips {s} (case of 48)", 12, 310), ("Masala Peanuts {s} (case of 40)", 12, 280),
            ("Banana Chips {s} (case of 40)", 12, 330), ("Murukku {s} (case of 36)", 12, 270)],
    "S10": [("Herbal Shampoo {s} (case of 24)", 18, 690), ("Toothpaste {s} (case of 48)", 18, 720),
            ("Bath Soap {s} (case of 72)", 18, 540), ("Coconut Hair Oil {s} (case of 24)", 18, 610)],
    "S11": [("Black Pepper {s} (case of 20)", 5, 880), ("Turmeric Powder {s} (case of 40)", 5, 460),
            ("Coconut Oil {s} (case of 12)", 5, 1450), ("Sambar Powder {s} (case of 40)", 5, 520)],
    "S12": [("Instant Noodles {s} (case of 48)", 12, 390), ("Tomato Ketchup {s} (case of 24)", 12, 560),
            ("Pickle {s} (case of 24)", 12, 610), ("Pasta {s} (case of 24)", 12, 470)],
    # Germany: export to the US, 0% VAT. Prices in EUR.
    "S13": [("Dark Chocolate {s} (case of 20)", 0, 38), ("Mustard {s} (case of 12)", 0, 22),
            ("Pretzel Sticks {s} (case of 24)", 0, 27), ("Rye Crispbread {s} (case of 12)", 0, 30)],
    # Canada: zero-rated export. Prices agreed in USD.
    "S14": [("Maple Syrup {s} (case of 12)", 0, 84), ("Wild Blueberry Jam {s} (case of 12)", 0, 46),
            ("Oat Cookies {s} (case of 24)", 0, 39), ("Smoked Salmon {s} (case of 12)", 0, 118)],
}

METRIC_SIZES = ["20g", "50g", "75g", "100g", "150g", "200g", "250g", "400g", "500g", "750g", "1kg", "2kg",
                "5kg", "Family Pack", "Value Pack", "Mini Pack", "Party Pack"]
METRIC_LIQUID = ["65ml", "100ml", "150ml", "180ml", "200ml", "250ml", "300ml", "400ml", "500ml", "600ml",
                 "750ml", "1L", "1.5L", "2L", "5L", "Family Pack", "Value Pack"]
US_SIZES = ["1 oz", "2 oz", "3.5 oz", "5 oz", "7 oz", "8 oz", "10 oz", "12 oz", "14 oz", "16 oz", "18 oz",
            "24 oz", "32 oz", "2 lb", "Family Size", "Value Pack", "Snack Size"]
US_LIQUID = ["8 fl oz", "10 fl oz", "12 fl oz", "16 fl oz", "16.9 fl oz", "20 fl oz", "24 fl oz", "28 fl oz",
             "32 fl oz", "48 fl oz", "64 fl oz", "1 gal", "Travel Size", "Family Size", "Value Pack", "Refill",
             "Twin Pack"]
PACKAGING = ["12 in", "15 in", "18 in", "20 in", "24 in", "Small", "Medium", "Large", "X-Large", "Heavy Duty",
             "Standard", "Light Duty", "Clear", "Brown", "Printed", "Recycled", "48 x 40"]
LIQUIDS = ("Juice", "Drink", "Water", "Oil", "Milk", "Shampoo", "Cleaner", "Soap", "Ketchup", "Lotion",
           "Detergent", "Syrup", "Mustard")

_LETTERS = "ABCDEFGHJKLMNPRSTUVWXYZ"


def _digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def _tax_id(rng: random.Random, country: str, region_code: str) -> str:
    if country == "IN":  # GSTIN: state code, PAN, entity number, Z, check character
        pan = "".join(rng.choice(_LETTERS) for _ in range(5)) + f"{rng.randint(1000, 9999)}" + rng.choice(_LETTERS)
        return f"{region_code}{pan}1Z{rng.choice('0123456789ABCDEFGHJK')}"
    if country == "US":  # EIN: NN-NNNNNNN
        return f"{rng.randint(10, 88)}-{_digits(rng, 7)}"
    if country == "DE":  # VAT ID: DE + 9 digits
        return f"DE{_digits(rng, 9)}"
    return f"{_digits(rng, 9)} RT0001"  # Canadian Business Number with GST/HST program account


def fake_routing(rng: random.Random) -> str:
    """A 9-digit ABA-style number that fails the ABA checksum, so it can never be a real bank's."""
    while True:
        d = "0" + _digits(rng, 8)
        n = [int(ch) for ch in d]
        if (3 * (n[0] + n[3] + n[6]) + 7 * (n[1] + n[4] + n[7]) + (n[2] + n[5] + n[8])) % 10:
            return d


def _bank(rng: random.Random, country: str) -> tuple[str, str]:
    """(account, bank code). Bank code is the IFSC, ABA routing number, BIC or transit/institution number."""
    if country == "IN":
        bank = rng.choice(["HDFC", "ICIC", "SBIN", "UTIB", "KKBK", "CNRB"])
        return _digits(rng, 12), f"{bank}0{rng.randint(100000, 999999)}"
    if country == "US":
        return _digits(rng, 10), fake_routing(rng)
    if country == "DE":
        return f"DE{_digits(rng, 2)} {_digits(rng, 4)} {_digits(rng, 4)} {_digits(rng, 4)} {_digits(rng, 4)} {_digits(rng, 2)}", "RHLFDEK1XXX"
    return _digits(rng, 7), f"{_digits(rng, 5)}-{_digits(rng, 3)}"


def build_suppliers(rng: random.Random) -> list[dict]:
    out = []
    for sid, name, country, currency, region, code, city in SUPPLIERS:
        account, bank_code = _bank(rng, country)
        out.append({
            "supplier_id": sid, "name": name, "country": country, "currency": currency,
            "entity_id": ENTITY_OF[country], "tax_id": _tax_id(rng, country, code),
            "tax_id_type": TAX_ID_TYPE[country], "region": region, "region_code": code, "city": city,
            "bank_account": account, "bank_code": bank_code,
            "email": f"accounts@{name.split()[0].lower()}.example",
        })
    return out


def _sizes(sid: str, template: str, country: str) -> list[str]:
    if sid == "S06":
        return PACKAGING
    liquid = any(w in template for w in LIQUIDS)
    if country in ("US", "CA"):
        return US_LIQUID if liquid else US_SIZES
    return METRIC_LIQUID if liquid else METRIC_SIZES


def build_skus(rng: random.Random) -> list[dict]:
    country = {s[0]: s[2] for s in SUPPLIERS}
    skus, n = [], 1
    for sid in [s[0] for s in SUPPLIERS]:
        for f_no, (template, rate, base) in enumerate(FAMILIES[sid], start=1):
            sizes = rng.sample(_sizes(sid, template, country[sid]), 16)
            for k, size in enumerate(sizes[: 15 + (1 if n % 2 else 0)], start=1):
                price = base * rng.uniform(0.7, 1.6)
                # Rs. prices round to 10; USD and EUR prices to 0.25
                price = round(price / 10) * 10 if country[sid] == "IN" else round(price * 4) / 4
                code = "" if country[sid] == "IN" else f"{sid[1:]}{f_no}{k:02d}"
                skus.append({"sku_id": f"SKU-{n:04d}", "supplier_id": sid,
                             "description": template.format(s=size), "item_code": code,
                             "tax_rate": float(rate), "unit": "case", "list_price": float(price)})
                n += 1
    assign_hsn(skus)
    return skus


# HSN codes for Indian SKUs (printed on GST invoices), by product family.
HSN = {"Instant Coffee": "2101", "Assam Tea": "0902", "Mango Drink": "2202", "Soda Water": "2201",
       "Cream Biscuits": "1905", "Rice Flakes": "1904", "Wheat Vermicelli": "1902", "Ragi Malt": "1901",
       "Potato Chips": "2005", "Masala Peanuts": "2008", "Banana Chips": "2008", "Murukku": "2106",
       "Herbal Shampoo": "3305", "Toothpaste": "3306", "Bath Soap": "3401", "Coconut Hair Oil": "3305",
       "Black Pepper": "0904", "Turmeric Powder": "0910", "Coconut Oil": "1513", "Sambar Powder": "0910",
       "Instant Noodles": "1902", "Tomato Ketchup": "2103", "Pickle": "2001", "Pasta": "1902"}


def assign_hsn(skus: list[dict]) -> None:
    """Indian SKUs carry an HSN code as their item code."""
    for s in skus:
        if not s["item_code"]:
            s["item_code"] = next(v for k, v in HSN.items() if s["description"].startswith(k))
