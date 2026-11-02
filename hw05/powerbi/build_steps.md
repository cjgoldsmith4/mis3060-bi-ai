# Part D build steps (Power BI Desktop on Apporto)

The model takes about 20 minutes to build. Column types come from `../reports/powerbi_types.csv`; relationships come from the Part D table in `../star_design.md`.

## 1. Upload and load

1. Upload the eight CSVs from `hw05/data/clean/` to your Apporto persistent drive.
2. In Power BI Desktop: **Home → Get data → Text/CSV**, pick a file, click **Transform Data**. Repeat for all eight (or load one, then **New Source** inside Power Query for the rest).

## 2. Set types in Power Query

Set these on every table, then **Close & Apply**:

| Type | Columns |
|---|---|
| Whole Number | every `*_id` column (keep `fact_transactions[security_id]` Whole Number with its blanks), `age`, `years_experience`, `aum_target_mm`, `year`, `quarter`, `month`, `week_of_year`, all `is_*` flags except the two below |
| Date | `dim_date[date]`, `txn_date`, `fee_date`, `snapshot_date`, `client_since` |
| Decimal Number | `amount`, `shares`, `price`, `aum`, `aum_basis`, `bps_charged`, `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct`, `initial_aum`, `expense_ratio_bps` |
| True/False | `dim_client[is_active]`, `dim_security[is_etf]` |
| Text | `dim_client[zip_code]` (keeps leading zeros such as `03897`), `fact_portfolio_snapshot[account_type]`, and every name or category column |

## 3. Relationships (Model view)

1. Delete every relationship Power BI detected on its own.
2. Drag each foreign key onto its primary key. Every relationship is **Many to one (\*:1)**, cross-filter **Single**.

| # | Drag this | Onto this | Active |
|---|---|---|---|
| 1 | fact_transactions[client_id] | dim_client[client_id] | Yes |
| 2 | fact_transactions[advisor_id] | dim_advisor[advisor_id] | Yes |
| 3 | fact_transactions[security_id] | dim_security[security_id] | Yes |
| 4 | fact_transactions[txn_date] | dim_date[date] | Yes |
| 5 | fact_fees[client_id] | dim_client[client_id] | Yes |
| 6 | fact_fees[advisor_id] | dim_advisor[advisor_id] | Yes |
| 7 | fact_fees[fee_date] | dim_date[date] | Yes |
| 8 | fact_portfolio_snapshot[client_id] | dim_client[client_id] | Yes |
| 9 | fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | Yes |
| 10 | fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | Yes |
| 11 | fact_portfolio_snapshot[snapshot_date] | dim_date[date] | Yes |
| 12 | dim_client[advisor_id] | dim_advisor[advisor_id] | No (Power BI makes it dashed on its own) |
| 13 | dim_security[benchmark_id] | dim_benchmark[benchmark_id] | No (untick "Make this relationship active") |

3. Lay it out as a star: dim_date at the top center, the three facts in a row under it, dim_client and dim_advisor between the facts, dim_security beside fact_transactions, dim_benchmark beside fact_portfolio_snapshot.

## 4. Mark the date table

Select `dim_date` → **Table tools → Mark as date table** → column `date`.

## 5. Check the model

1. On a report page, add one **Card** per table showing **Count** of its primary key. The cards must read 25, 8, 2,500, 1,827, 500, 122,197, 129,547 and 298,572.
2. Add a **Table** visual with `dim_security[ticker]` and Sum of `fact_transactions[amount]`. One `(Blank)` row appears for the 101,528 cash rows; any other `(Blank)` means a type mismatch.
3. Add a **Slicer** on `dim_advisor[last_name]` and confirm it filters cards built on all three facts.

## 6. Save and screenshot

1. **File → Save as** `hw05.pbix` on the persistent drive, then download it to `hw05/powerbi/` in the repo.
2. In Model view, fit everything on screen (**Fit to page**), take a screenshot, and save it as `hw05/powerbi/model_view.png`.
3. In VS Code: stage both files, commit "HW5 Part D: Power BI star model and Model view screenshot", and push.
