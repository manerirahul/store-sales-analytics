-- =====================================================================
-- Reporting views over the star schema (SQLite dialect).
-- Apply after load_and_model.py:  sqlite3 store_sales.db < sql/reporting_views.sql
-- Every view states the business question it answers.
-- =====================================================================

-- Q1. Monthly revenue trend: net revenue, transactions, units, AOV
DROP VIEW IF EXISTS v_monthly_kpis;
CREATE VIEW v_monthly_kpis AS
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.transaction_id)              AS transactions,
    SUM(f.quantity)                               AS units_net,
    ROUND(SUM(f.line_amount), 2)                  AS net_revenue,
    ROUND(SUM(f.line_amount)
        / COUNT(DISTINCT f.transaction_id), 2)    AS avg_transaction_value
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year, d.month, d.month_name;

-- Q2. Store performance ranking with gross margin (price less cost on
--     units actually kept, i.e. sales minus returns)
DROP VIEW IF EXISTS v_store_performance;
CREATE VIEW v_store_performance AS
SELECT
    s.store_name,
    s.state,
    s.store_format,
    COUNT(DISTINCT f.transaction_id)                       AS transactions,
    ROUND(SUM(f.line_amount), 2)                           AS net_revenue,
    ROUND(SUM(f.line_amount - f.quantity * p.unit_cost), 2) AS gross_margin,
    ROUND(100.0 * SUM(f.line_amount - f.quantity * p.unit_cost)
        / SUM(f.line_amount), 1)                           AS margin_pct
FROM fact_sales f
JOIN dim_store s   ON s.store_key   = f.store_key
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY s.store_name, s.state, s.store_format;

-- Q3. Category mix: revenue share and return rate by category
DROP VIEW IF EXISTS v_category_mix;
CREATE VIEW v_category_mix AS
SELECT
    p.category,
    SUM(CASE WHEN f.is_return = 0 THEN f.quantity ELSE 0 END)  AS units_sold,
    SUM(CASE WHEN f.is_return = 1 THEN -f.quantity ELSE 0 END) AS units_returned,
    ROUND(100.0 * SUM(CASE WHEN f.is_return = 1 THEN -f.quantity ELSE 0 END)
        / SUM(CASE WHEN f.is_return = 0 THEN f.quantity ELSE 0 END), 2)
        AS return_rate_pct,
    ROUND(SUM(f.line_amount), 2)                              AS net_revenue,
    ROUND(100.0 * SUM(f.line_amount)
        / (SELECT SUM(line_amount) FROM fact_sales), 1)       AS revenue_share_pct
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category;

-- Q4. Top products by net revenue
DROP VIEW IF EXISTS v_top_products;
CREATE VIEW v_top_products AS
SELECT
    p.product_name,
    p.category,
    SUM(f.quantity)               AS units_net,
    ROUND(SUM(f.line_amount), 2)  AS net_revenue
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_name, p.category;

-- Q5. Weekend vs weekday behaviour
DROP VIEW IF EXISTS v_daytype;
CREATE VIEW v_daytype AS
SELECT
    CASE WHEN d.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(DISTINCT d.full_date)                                  AS days,
    ROUND(SUM(f.line_amount) / COUNT(DISTINCT d.full_date), 2)   AS revenue_per_day,
    ROUND(1.0 * COUNT(DISTINCT f.transaction_id)
        / COUNT(DISTINCT d.full_date), 1)                        AS transactions_per_day
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY day_type;
