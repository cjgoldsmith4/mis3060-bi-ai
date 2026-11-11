# Model metadata: Wildcat_Star_Model (hw06.pbix)
MIS3060 Business Intelligence with AI | Charlie Goldsmith

This file gives Claude the structure of the model for Part D. Metadata describes names, types and relationships; it cannot say what a row means, which columns are balances, or how a measure should behave. Those facts go into the prompt in `dax_session.md`.

## Queries (run in DAX query view, one at a time)

```DAX
EVALUATE INFO.VIEW.TABLES ()
```
```DAX
EVALUATE INFO.VIEW.COLUMNS ()
```
```DAX
EVALUATE INFO.VIEW.RELATIONSHIPS ()
```

> **Source of the tables below.** The tables were read from the posted `Wildcat_Star_Model.pbix` with the `pbixray` Python package, which reads the same model metadata the INFO.VIEW functions return (tables, columns with data types, relationships). Auto date/time tables (`LocalDateTable_*`, `DateTableTemplate_*`) are hidden system tables and are left out. **To do in Power BI:** run the three queries above in `hw06.pbix`, select **Copy** under each result, and paste the grids under "INFO.VIEW output" at the end of this file.

## Tables

| Table | Rows |
|---|---:|
| dim_advisor | 25 |
| dim_benchmark | 8 |
| dim_client | 2,500 |
| dim_date | 1,827 |
| dim_security | 500 |
| fact_fees | 122,197 |
| fact_portfolio_snapshot | 129,547 |
| fact_transactions | 298,572 |

## Columns

| Table | Column | Data type | Distinct values |
|---|---|---|---:|
| dim_advisor | advisor_id | Int64 | 25 |
| dim_advisor | first_name | String | 24 |
| dim_advisor | last_name | String | 24 |
| dim_advisor | region | String | 5 |
| dim_advisor | years_experience | Int64 | 17 |
| dim_advisor | aum_target_mm | Int64 | 5 |
| dim_advisor | certifications | String | 5 |
| dim_benchmark | benchmark_id | Int64 | 8 |
| dim_benchmark | name | String | 8 |
| dim_benchmark | asset_class | String | 7 |
| dim_benchmark | ticker_proxy | String | 8 |
| dim_client | client_id | Int64 | 2,500 |
| dim_client | first_name | String | 505 |
| dim_client | last_name | String | 755 |
| dim_client | age | Int64 | 53 |
| dim_client | city | String | 2,291 |
| dim_client | state | String | 20 |
| dim_client | zip_code | String | 2,483 |
| dim_client | risk_profile | String | 6 |
| dim_client | client_tier | String | 3 |
| dim_client | primary_account_type | String | 5 |
| dim_client | initial_aum | Double | 2,500 |
| dim_client | client_since | DateTime | 1,651 |
| dim_client | advisor_id | Int64 | 25 |
| dim_client | is_active | Boolean | 2 |
| dim_date | date_id | Int64 | 1,827 |
| dim_date | date | DateTime | 1,827 |
| dim_date | year | Int64 | 5 |
| dim_date | quarter | Int64 | 4 |
| dim_date | month | Int64 | 12 |
| dim_date | month_name | String | 12 |
| dim_date | week_of_year | Int64 | 53 |
| dim_date | day_of_week | String | 7 |
| dim_date | is_month_end | Int64 | 2 |
| dim_date | is_quarter_end | Int64 | 2 |
| dim_date | is_year_end | Int64 | 2 |
| dim_date | is_trading_day | Int64 | 2 |
| dim_security | security_id | Int64 | 500 |
| dim_security | ticker | String | 500 |
| dim_security | name | String | 497 |
| dim_security | asset_class | String | 4 |
| dim_security | sector | String | 12 |
| dim_security | benchmark_id | Int64 | 6 |
| dim_security | is_etf | Boolean | 2 |
| dim_security | expense_ratio_bps | Int64 | 83 |
| fact_fees | fee_id | Int64 | 122,197 |
| fact_fees | client_id | Int64 | 2,500 |
| fact_fees | advisor_id | Int64 | 25 |
| fact_fees | fee_date | DateTime | 60 |
| fact_fees | fee_type | String | 4 |
| fact_fees | aum_basis | Double | 121,755 |
| fact_fees | bps_charged | Double | 5,217 |
| fact_fees | amount | Double | 81,649 |
| fact_portfolio_snapshot | snapshot_id | Int64 | 129,547 |
| fact_portfolio_snapshot | client_id | Int64 | 2,500 |
| fact_portfolio_snapshot | advisor_id | Int64 | 25 |
| fact_portfolio_snapshot | benchmark_id | Int64 | 3 |
| fact_portfolio_snapshot | snapshot_date | DateTime | 60 |
| fact_portfolio_snapshot | year | Int64 | 5 |
| fact_portfolio_snapshot | month | Int64 | 12 |
| fact_portfolio_snapshot | aum | Double | 129,062 |
| fact_portfolio_snapshot | return_ytd | Double | 112,165 |
| fact_portfolio_snapshot | benchmark_return_ytd | Double | 180 |
| fact_portfolio_snapshot | active_alpha_ytd | Double | 85,397 |
| fact_portfolio_snapshot | cash_pct | Double | 701 |
| fact_portfolio_snapshot | account_type | String | 5 |
| fact_portfolio_snapshot | is_return_suspect | Int64 | 2 |
| fact_transactions | txn_id | Int64 | 298,572 |
| fact_transactions | client_id | Int64 | 2,500 |
| fact_transactions | advisor_id | Int64 | 25 |
| fact_transactions | security_id | Int64 | 500 |
| fact_transactions | txn_date | DateTime | 1,826 |
| fact_transactions | txn_type | String | 6 |
| fact_transactions | shares | Double | 193,225 |
| fact_transactions | price | Double | 48,105 |
| fact_transactions | amount | Double | 292,741 |
| fact_transactions | is_post_departure_txn | Int64 | 2 |

## Relationships

The posted model holds 12 single-direction, many-to-one relationships. `dim_date` is marked as the date table on `dim_date[date]`.

| From (many) | To (one) | Cardinality | Cross-filter | Active |
|---|---|---|---|---|
| fact_transactions[advisor_id] | dim_advisor[advisor_id] | M:1 | Single | Yes |
| fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | M:1 | Single | Yes |
| fact_fees[advisor_id] | dim_advisor[advisor_id] | M:1 | Single | Yes |
| fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | M:1 | Single | Yes |
| fact_transactions[client_id] | dim_client[client_id] | M:1 | Single | Yes |
| fact_portfolio_snapshot[client_id] | dim_client[client_id] | M:1 | Single | Yes |
| fact_fees[client_id] | dim_client[client_id] | M:1 | Single | Yes |
| fact_transactions[security_id] | dim_security[security_id] | M:1 | Single | Yes |
| dim_security[benchmark_id] | dim_benchmark[benchmark_id] | M:1 | Single | Yes |
| fact_fees[fee_date] | dim_date[date] | M:1 | Single | Yes |
| fact_portfolio_snapshot[snapshot_date] | dim_date[date] | M:1 | Single | Yes |
| fact_transactions[txn_date] | dim_date[date] | M:1 | Single | Yes |

## INFO.VIEW output

*(paste INFO.VIEW.TABLES, INFO.VIEW.COLUMNS and INFO.VIEW.RELATIONSHIPS results here)*
