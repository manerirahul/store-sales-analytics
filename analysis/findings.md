# Findings — Store Sales, Jul 2025 to Aug 2026

Source: `fact_sales` (131,772 line items, 79,588 transactions, 6 stores).
All figures are net of returns and reproducible with `src/analyze.py`.

## Headline numbers

- Net revenue: **$10,891,492**
- Average transaction value: ~$137 (net revenue / transactions)
- Gross margin: ~49.5% chain-wide

## What the data says

1. **Weekend trading is worth 47% more per day** ($33,041 vs $22,493).
   The December uplift stacks on top of this, so December weekends are
   the highest-value trading days of the year.
2. **Electronics dominates the mix** at 35.5% of revenue; the Smart Watch
   is the single biggest product at $1.92M (17.7% of chain revenue).
   Concentration at that level is a stock-out risk worth a service-level
   agreement with the supplier.
3. **Seasonality is a 47% swing** between the best month (Dec 2025,
   $1.05M) and the worst (Feb 2026, $0.71M). February's dip is demand,
   not execution: transactions per day fall with the same shape in
   every store.
4. **Returns are not a category problem.** Unit return rates sit between
   0.89% (Apparel) and 1.07% (Fitness) — uniform enough that no
   category-level quality investigation is warranted.
5. **No store is broken.** The top three stores finish within $9K of
   each other and margins cluster at 49.4–49.6%. Performance work
   should target chain-wide levers (weekend staffing, December
   readiness), not store turnarounds.

## Recommended next analyses

- Basket analysis on co-purchased categories to test bundle offers
- Store-level December readiness: weekend revenue per labour hour
- Smart Watch supply risk: weeks of cover at December run-rate
