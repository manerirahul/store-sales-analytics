# Store Sales Analytics

End-to-end retail analytics on a synthetic POS extract: raw line items →
cleaned **star schema** → SQL reporting views → written findings. Built the
way I build reporting at work — model first, metric logic in SQL so every
consumer agrees, and a data-quality gate that stops a bad load from shipping.

## The case

| | |
|---|---|
| Scale | 131,772 line items · 79,588 transactions · $10.89M net revenue · 6 stores · 14 months (Jul 2025 – Aug 2026) |
| Model | Kimball star schema: 1 fact (`fact_sales`), 3 dimensions (`dim_store`, `dim_product`, `dim_date`) |
| Quality | 12 automated assertions run on every load, non-zero exit on failure — row counts, key integrity, amount recomputation, return-flag consistency |
| Stack | Python + SQLite (standard library only); SQL views port to PostgreSQL / Snowflake |

All data is synthetic, generated deterministically by `src/generate_data.py`.

## Headline findings

- **Weekends carry the business** — revenue per day is $33,041 on weekends
  vs $22,493 on weekdays (+47%); staffing and promotions should follow that.
- **Electronics is the engine** — 35.5% of net revenue, led by the Smart
  Watch ($1.92M alone, the top product). Footwear is second at 21.6%.
- **December peaks hard** — $1.05M in Dec 2025 vs a $0.71M February low;
  a 47% swing the inventory plan has to absorb.
- **Returns are healthy and uniform** — ~1% unit return rate in every
  category, so no single category has a quality problem hiding in the mix.
- **Store race is tight** — the top three stores sit within $9K of each
  other (~$1.84M each) at ~49.5% gross margin; format (Urban/Mall/Suburban)
  is not deciding performance.

Full numbers: `analysis/findings.md`.

## Run it

```bash
python src/generate_data.py     # regenerate the synthetic extract (seeded)
python src/load_and_model.py    # build the star schema + run 12 DQ assertions
python src/analyze.py           # apply the reporting views, print findings
```

## Layout

```
data/    stores.csv · products.csv · store_sales_raw.csv (synthetic POS extract)
src/     generate_data.py · load_and_model.py · analyze.py
sql/     reporting_views.sql  (monthly KPIs, store performance, category mix,
                               top products, weekend vs weekday)
analysis/ findings.md
```

## License

MIT
