"""Load the raw POS-style extract into a Kimball star schema (SQLite).

Build steps:
  1. Create dim_date, dim_store, dim_product and fact_sales
  2. Load dimensions from the reference CSVs; generate the date spine
  3. Load the fact from the raw extract, deriving line amounts and a
     sale/return flag (returns arrive as negative quantities)
  4. Run the data-quality assertion suite; exit non-zero if any
     assertion fails, so a bad load never ships silently

SQLite keeps the project runnable anywhere; the DDL and views use
standard SQL that ports to PostgreSQL/Snowflake with minor changes.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys
from datetime import date, timedelta

BASE = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE, "store_sales.db")

DDL = """
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_store (
    store_key   INTEGER PRIMARY KEY,
    store_id    TEXT UNIQUE NOT NULL,
    store_name  TEXT NOT NULL,
    state       TEXT NOT NULL,
    store_format TEXT NOT NULL
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    product_id  TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category    TEXT NOT NULL,
    unit_cost   REAL NOT NULL
);

CREATE TABLE dim_date (
    date_key   INTEGER PRIMARY KEY,          -- yyyymmdd
    full_date  TEXT UNIQUE NOT NULL,          -- ISO date
    year       INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE fact_sales (
    sale_key      INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    date_key      INTEGER NOT NULL REFERENCES dim_date(date_key),
    store_key     INTEGER NOT NULL REFERENCES dim_store(store_key),
    product_key   INTEGER NOT NULL REFERENCES dim_product(product_key),
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL,
    line_amount   REAL NOT NULL,
    is_return     INTEGER NOT NULL DEFAULT 0
);
"""

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def read_csv(name: str) -> list[dict]:
    with open(os.path.join(BASE, "data", name), newline="") as fh:
        return list(csv.DictReader(fh))


def build(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.executescript(DDL)

    stores = read_csv("stores.csv")
    cur.executemany(
        "INSERT INTO dim_store VALUES (?,?,?,?,?)",
        [(i + 1, s["store_id"], s["store_name"], s["state"], s["store_format"])
         for i, s in enumerate(stores)])
    store_key = {s["store_id"]: i + 1 for i, s in enumerate(stores)}

    products = read_csv("products.csv")
    cur.executemany(
        "INSERT INTO dim_product VALUES (?,?,?,?,?)",
        [(i + 1, p["product_id"], p["product_name"], p["category"],
          float(p["unit_cost"])) for i, p in enumerate(products)])
    product_key = {p["product_id"]: i + 1 for i, p in enumerate(products)}

    sales = read_csv("store_sales_raw.csv")
    dates = sorted({r["sale_date"] for r in sales})
    date_rows = []
    for iso in dates:
        y, m, d = (int(x) for x in iso.split("-"))
        wd = date(y, m, d).weekday()
        date_rows.append((y * 10000 + m * 100 + d, iso, y, m, MONTHS[m - 1],
                          DOW[wd], 1 if wd >= 5 else 0))
    cur.executemany("INSERT INTO dim_date VALUES (?,?,?,?,?,?,?)", date_rows)
    date_key = {r[1]: r[0] for r in date_rows}

    fact_rows = []
    for i, r in enumerate(sales, start=1):
        qty = int(r["quantity"])
        price = float(r["unit_price"])
        fact_rows.append((i, r["transaction_id"], date_key[r["sale_date"]],
                          store_key[r["store_id"]], product_key[r["product_id"]],
                          qty, price, round(qty * price, 2), 1 if qty < 0 else 0))
    cur.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?)", fact_rows)
    conn.commit()
    return {"stores": len(stores), "products": len(products),
            "dates": len(date_rows), "fact_rows": len(fact_rows)}


ASSERTIONS = [
    ("fact row count equals raw extract rows",
     "SELECT (SELECT COUNT(*) FROM fact_sales) = {fact_rows}"),
    ("no orphan store keys in fact",
     "SELECT COUNT(*) = 0 FROM fact_sales f LEFT JOIN dim_store s "
     "ON s.store_key = f.store_key WHERE s.store_key IS NULL"),
    ("no orphan product keys in fact",
     "SELECT COUNT(*) = 0 FROM fact_sales f LEFT JOIN dim_product p "
     "ON p.product_key = f.product_key WHERE p.product_key IS NULL"),
    ("no orphan date keys in fact",
     "SELECT COUNT(*) = 0 FROM fact_sales f LEFT JOIN dim_date d "
     "ON d.date_key = f.date_key WHERE d.date_key IS NULL"),
    ("line_amount equals quantity * unit_price on every row",
     "SELECT COUNT(*) = 0 FROM fact_sales "
     "WHERE ABS(line_amount - quantity * unit_price) > 0.011"),
    ("returns are exactly the negative-quantity rows",
     "SELECT COUNT(*) = 0 FROM fact_sales "
     "WHERE (quantity < 0 AND is_return = 0) OR (quantity > 0 AND is_return = 1)"),
    ("no zero-quantity rows",
     "SELECT COUNT(*) = 0 FROM fact_sales WHERE quantity = 0"),
    ("no null unit prices",
     "SELECT COUNT(*) = 0 FROM fact_sales WHERE unit_price IS NULL"),
    ("every store has sales",
     "SELECT COUNT(*) = (SELECT COUNT(*) FROM dim_store) FROM "
     "(SELECT DISTINCT store_key FROM fact_sales)"),
    ("every product has sales",
     "SELECT COUNT(*) = (SELECT COUNT(*) FROM dim_product) FROM "
     "(SELECT DISTINCT product_key FROM fact_sales)"),
    ("date spine covers the full sales range without gaps in keys",
     "SELECT COUNT(*) = CAST(julianday(MAX(full_date)) - julianday(MIN(full_date)) AS INTEGER) + 1 "
     "FROM dim_date"),
    ("net revenue is positive",
     "SELECT SUM(line_amount) > 0 FROM fact_sales"),
]


def run_assertions(conn: sqlite3.Connection, stats: dict) -> int:
    failures = 0
    cur = conn.cursor()
    for name, sql in ASSERTIONS:
        result = cur.execute(sql.format(**stats)).fetchone()[0]
        ok = bool(result)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        failures += 0 if ok else 1
    print(f"\n{len(ASSERTIONS) - failures}/{len(ASSERTIONS)} assertions passed")
    return failures


def main() -> int:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        stats = build(conn)
        print(f"Loaded: {stats['fact_rows']} fact rows, {stats['stores']} stores, "
              f"{stats['products']} products, {stats['dates']} dates")
        failures = run_assertions(conn, stats)
        return 1 if failures else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
