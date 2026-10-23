"""Generate the synthetic retail dataset (deterministic, seeded).

Creates data/stores.csv, data/products.csv and data/store_sales_raw.csv:
one row per sold line item across 6 stores and 14 months, with a small
share of returns (negative quantities) exactly as a POS extract shows
them. Run once; the CSVs are committed so the project is reproducible
without re-generating.
"""
from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "..", "data")

STORES = [
    ("ST-01", "Austin Downtown", "TX", "Urban"),
    ("ST-02", "Houston Galleria", "TX", "Mall"),
    ("ST-03", "Dallas North", "TX", "Suburban"),
    ("ST-04", "Seattle Central", "WA", "Urban"),
    ("ST-05", "Phoenix East", "AZ", "Suburban"),
    ("ST-06", "Miami Beach", "FL", "Mall"),
]

PRODUCTS = [
    ("P-100", "Wireless Headphones", "Electronics", 79.99, 42.00),
    ("P-101", "Bluetooth Speaker", "Electronics", 49.99, 26.50),
    ("P-102", "Smart Watch", "Electronics", 199.99, 118.00),
    ("P-103", "Running Shoes", "Footwear", 89.95, 47.00),
    ("P-104", "Trail Boots", "Footwear", 129.95, 71.00),
    ("P-105", "Cotton T-Shirt", "Apparel", 24.99, 9.50),
    ("P-106", "Denim Jacket", "Apparel", 69.99, 31.00),
    ("P-107", "Yoga Mat", "Fitness", 34.99, 14.00),
    ("P-108", "Dumbbell Set 20lb", "Fitness", 59.99, 33.00),
    ("P-109", "Coffee Maker", "Home", 89.99, 48.00),
    ("P-110", "Ceramic Dinner Set", "Home", 64.99, 30.00),
    ("P-111", "LED Desk Lamp", "Home", 39.99, 17.50),
    ("P-112", "Backpack 25L", "Accessories", 54.99, 24.00),
    ("P-113", "Sunglasses", "Accessories", 44.99, 15.00),
    ("P-114", "Water Bottle 1L", "Accessories", 19.99, 7.00),
]

# Category popularity weights, so the mix looks like a real store
WEIGHTS = [10, 8, 6, 9, 5, 12, 6, 5, 4, 6, 4, 5, 7, 5, 8]
START = date(2025, 7, 1)
DAYS = 427  # 14 months: Jul 2025 - Aug 2026


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stores.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["store_id", "store_name", "state", "store_format"])
        w.writerows(STORES)
    with open(os.path.join(OUT, "products.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["product_id", "product_name", "category", "unit_price", "unit_cost"])
        w.writerows(PRODUCTS)

    rows = []
    txn = 100000
    price = {p[0]: p[3] for p in PRODUCTS}
    for day_offset in range(DAYS):
        d = START + timedelta(days=day_offset)
        weekend_boost = 1.5 if d.weekday() >= 5 else 1.0
        december_boost = 1.4 if d.month == 12 else 1.0
        for store_id, *_ in STORES:
            n_txn = int(random.randint(18, 34) * weekend_boost * december_boost)
            for _ in range(n_txn):
                txn += 1
                items = random.choices(PRODUCTS, weights=WEIGHTS,
                                       k=random.choice([1, 1, 1, 2, 2, 3]))
                for p in items:
                    qty = random.choice([1, 1, 1, 2])
                    rows.append([f"T{txn}", d.isoformat(), store_id, p[0],
                                 qty, price[p[0]]])
                    if random.random() < 0.012:  # ~1.2% returns
                        rows.append([f"T{txn}-R", d.isoformat(), store_id,
                                     p[0], -1, price[p[0]]])
    with open(os.path.join(OUT, "store_sales_raw.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["transaction_id", "sale_date", "store_id", "product_id",
                    "quantity", "unit_price"])
        w.writerows(rows)
    print(f"{len(rows)} line items written across {DAYS} days, {len(STORES)} stores")


if __name__ == "__main__":
    main()
