"""Run the reporting views and print the headline findings.

Requires the database and views to exist:
    python src/load_and_model.py
    sqlite3 store_sales.db < sql/reporting_views.sql   (or run apply_views here)
"""
from __future__ import annotations

import os
import sqlite3

BASE = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE, "store_sales.db")
VIEWS = os.path.join(BASE, "sql", "reporting_views.sql")


def apply_views(conn: sqlite3.Connection) -> None:
    with open(VIEWS) as fh:
        conn.executescript(fh.read())


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        apply_views(conn)
        cur = conn.cursor()

        total_rev, total_txn, total_rows = cur.execute(
            "SELECT ROUND(SUM(line_amount),2), COUNT(DISTINCT transaction_id), "
            "COUNT(*) FROM fact_sales").fetchone()
        print(f"Net revenue ${total_rev:,.2f} across {total_txn:,} transactions "
              f"({total_rows:,} line items)")

        print("\nTop 3 stores by net revenue:")
        for row in cur.execute("SELECT store_name, net_revenue, margin_pct "
                               "FROM v_store_performance ORDER BY net_revenue DESC LIMIT 3"):
            print(f"  {row[0]}: ${row[1]:,.2f} (margin {row[2]}%)")

        print("\nCategory mix (revenue share, return rate):")
        for row in cur.execute("SELECT category, revenue_share_pct, return_rate_pct "
                               "FROM v_category_mix ORDER BY revenue_share_pct DESC"):
            print(f"  {row[0]}: {row[1]}% of revenue, {row[2]}% return rate")

        print("\nTop product:")
        row = cur.execute("SELECT product_name, net_revenue FROM v_top_products "
                          "ORDER BY net_revenue DESC LIMIT 1").fetchone()
        print(f"  {row[0]}: ${row[1]:,.2f}")

        print("\nWeekend vs weekday revenue per day:")
        for row in cur.execute("SELECT day_type, revenue_per_day FROM v_daytype"):
            print(f"  {row[0]}: ${row[1]:,.2f}")

        print("\nBest and worst month:")
        for label, ordering in (("Best", "DESC"), ("Worst", "ASC")):
            row = cur.execute(
                f"SELECT month_name, year, net_revenue FROM v_monthly_kpis "
                f"ORDER BY net_revenue {ordering} LIMIT 1").fetchone()
            print(f"  {label}: {row[0]} {row[1]} — ${row[2]:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
