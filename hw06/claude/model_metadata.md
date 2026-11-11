# Model metadata: hw06.pbix
MIS3060 Business Intelligence with AI | Charlie Goldsmith

This file gives Claude the structure of the model for Part D. Metadata describes names, types and relationships; it cannot say what a row means, which columns are balances, or how a measure should behave. Those facts go into the prompt in `dax_session.md`.

## Queries

Run in DAX query view in `hw06.pbix` (the file is `powerbi/info_view_queries.dax`). DAX query view shows one result tab per EVALUATE; each grid was copied with **Copy → Entire table**. The full, unedited output (every column) is in `claude/info_view_raw.txt`; the tables below keep the columns Claude needs.

```DAX
EVALUATE INFO.VIEW.TABLES ()

EVALUATE INFO.VIEW.COLUMNS ()

EVALUATE INFO.VIEW.RELATIONSHIPS ()
```

## What the metadata shows

- 12 tables: the 8 Wildcat tables, `_Measures`, and three hidden auto date/time tables (`DateTableTemplate_*`, and `LocalDateTable_*` on `dim_client[client_since]` and on `dim_date[date]`).
- `dim_date` is **not** marked as a date table in the posted model. This is because a table marked as a date table never gets an auto `LocalDateTable`, and `INFO.VIEW.RELATIONSHIPS` lists one on `dim_date[date]`. Time intelligence still works: `fact_portfolio_snapshot`, `fact_fees` and `fact_transactions` join to `dim_date[date]`, a Date column, so `SAMEPERIODLASTYEAR` and `DATEADD` remove the year filter on `dim_date` the same way a marked table would. The `Ending AUM LY`, `AUM YoY %`, `Ending AUM PM` and `AUM MoM %` rows in `reports/measure_reconciliation.csv` all match pandas, which confirms it.
- 12 relationships between the Wildcat tables, all single direction and many-to-one, plus the 2 auto date/time links. `dim_security[benchmark_id] → dim_benchmark` is active in the posted model.

## INFO.VIEW output

### INFO.VIEW.TABLES() (12 rows)

| Name | DataCategory | IsHidden | StorageMode | Expression |
|---|---|---|---|---|
| fact_transactions | Regular | false | Import |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Regular | true | Import | Calendar(Date(2015,1,1), Date(2015,1,1)) |
| fact_portfolio_snapshot | Regular | false | Import |  |
| fact_fees | Regular | false | Import |  |
| dim_advisor | Regular | false | Import |  |
| dim_benchmark | Regular | false | Import |  |
| dim_client | Regular | false | Import |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Regular | true | Import | Calendar(Date(Year(MIN('dim_client'[client_since])), 1, 1), Date(Year(MAX('dim_client'[client_since])), 12, 31)) |
| dim_date | Regular | false | Import |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Regular | true | Import | Calendar(Date(Year(MIN('dim_date'[date])), 1, 1), Date(Year(MAX('dim_date'[date])), 12, 31)) |
| dim_security | Regular | false | Import |  |
| _Measures | Regular | false | Import | {BLANK()} |

### INFO.VIEW.COLUMNS() (111 rows)

| Table | Name | DataType | IsHidden | IsKey | SummarizeBy | Type | FormatString | DisplayFolder |
|---|---|---|---|---|---|---|---|---|
| fact_transactions | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| fact_transactions | txn_id | Integer | false | false | Sum | Data | 0 |  |
| fact_transactions | client_id | Integer | false | false | None | Data | 0 |  |
| fact_transactions | advisor_id | Integer | false | false | None | Data | 0 |  |
| fact_transactions | security_id | Integer | false | false | None | Data | 0 |  |
| fact_transactions | txn_date | Date | false | false | None | Data | Long Date |  |
| fact_transactions | txn_type | Text | false | false | None | Data |  |  |
| fact_transactions | shares | Number | false | false | Sum | Data |  |  |
| fact_transactions | price | Number | false | false | Sum | Data |  |  |
| fact_transactions | amount | Number | false | false | Sum | Data |  |  |
| fact_transactions | is_post_departure_txn | Integer | false | false | Sum | Data | 0 |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Date | Date | true | false | None | CalculatedTableColumn | General Date |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Year | Integer | true | false | None | Calculated | 0 |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | MonthNo | Integer | true | false | None | Calculated | 0 |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Month | Text | true | false | None | Calculated |  |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | QuarterNo | Integer | true | false | None | Calculated | 0 |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Quarter | Text | true | false | None | Calculated |  |  |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Day | Integer | true | false | None | Calculated | 0 |  |
| fact_portfolio_snapshot | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| fact_portfolio_snapshot | snapshot_id | Integer | false | false | Sum | Data | 0 |  |
| fact_portfolio_snapshot | client_id | Integer | false | false | None | Data | 0 |  |
| fact_portfolio_snapshot | advisor_id | Integer | false | false | None | Data | 0 |  |
| fact_portfolio_snapshot | benchmark_id | Integer | false | false | None | Data | 0 |  |
| fact_portfolio_snapshot | snapshot_date | Date | false | false | None | Data | Long Date |  |
| fact_portfolio_snapshot | Year | Integer | false | false | Sum | Data | 0 |  |
| fact_portfolio_snapshot | Month | Integer | false | false | Sum | Data | 0 |  |
| fact_portfolio_snapshot | aum | Number | false | false | Sum | Data |  |  |
| fact_portfolio_snapshot | return_ytd | Number | false | false | Sum | Data |  |  |
| fact_portfolio_snapshot | benchmark_return_ytd | Number | false | false | Sum | Data |  |  |
| fact_portfolio_snapshot | active_alpha_ytd | Number | false | false | Sum | Data |  |  |
| fact_portfolio_snapshot | cash_pct | Number | false | false | Sum | Data |  |  |
| fact_portfolio_snapshot | account_type | Text | false | false | None | Data |  |  |
| fact_portfolio_snapshot | is_return_suspect | Integer | false | false | Sum | Data | 0 |  |
| fact_fees | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| fact_fees | fee_id | Integer | false | false | Sum | Data | 0 |  |
| fact_fees | client_id | Integer | false | false | None | Data | 0 |  |
| fact_fees | advisor_id | Integer | false | false | None | Data | 0 |  |
| fact_fees | fee_date | Date | false | false | None | Data | Long Date |  |
| fact_fees | fee_type | Text | false | false | None | Data |  |  |
| fact_fees | aum_basis | Number | false | false | Sum | Data |  |  |
| fact_fees | bps_charged | Number | false | false | Sum | Data |  |  |
| fact_fees | amount | Number | false | false | Sum | Data |  |  |
| dim_advisor | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| dim_advisor | advisor_id | Integer | false | false | None | Data | 0 |  |
| dim_advisor | first_name | Text | false | false | None | Data |  |  |
| dim_advisor | last_name | Text | false | false | None | Data |  |  |
| dim_advisor | region | Text | false | false | None | Data |  |  |
| dim_advisor | years_experience | Integer | false | false | Sum | Data | 0 |  |
| dim_advisor | aum_target_mm | Integer | false | false | Sum | Data | 0 |  |
| dim_advisor | certifications | Text | false | false | None | Data |  |  |
| dim_benchmark | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| dim_benchmark | benchmark_id | Integer | false | false | None | Data | 0 |  |
| dim_benchmark | name | Text | false | false | None | Data |  |  |
| dim_benchmark | asset_class | Text | false | false | None | Data |  |  |
| dim_benchmark | ticker_proxy | Text | false | false | None | Data |  |  |
| dim_client | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| dim_client | client_id | Integer | false | false | None | Data | 0 |  |
| dim_client | first_name | Text | false | false | None | Data |  |  |
| dim_client | last_name | Text | false | false | None | Data |  |  |
| dim_client | age | Integer | false | false | Sum | Data | 0 |  |
| dim_client | city | Text | false | false | None | Data |  |  |
| dim_client | state | Text | false | false | None | Data |  |  |
| dim_client | zip_code | Text | false | false | None | Data |  |  |
| dim_client | risk_profile | Text | false | false | None | Data |  |  |
| dim_client | client_tier | Text | false | false | None | Data |  |  |
| dim_client | primary_account_type | Text | false | false | None | Data |  |  |
| dim_client | initial_aum | Number | false | false | Sum | Data |  |  |
| dim_client | client_since | Date | false | false | None | Data | Long Date |  |
| dim_client | advisor_id | Integer | false | false | Sum | Data | 0 |  |
| dim_client | is_active | True/False | false | false | None | Data | TRUE;"TRUE";"FALSE" |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Date | Date | true | false | None | CalculatedTableColumn | General Date |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Year | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | MonthNo | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Month | Text | true | false | None | Calculated |  |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | QuarterNo | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Quarter | Text | true | false | None | Calculated |  |  |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Day | Integer | true | false | None | Calculated | 0 |  |
| dim_date | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| dim_date | date_id | Integer | false | false | Sum | Data | 0 |  |
| dim_date | Date | Date | false | false | None | Data | Long Date |  |
| dim_date | Year | Integer | false | false | Sum | Data | 0 |  |
| dim_date | Quarter | Integer | false | false | Sum | Data | 0 |  |
| dim_date | Month | Integer | false | false | Sum | Data | 0 |  |
| dim_date | month_name | Text | false | false | None | Data |  |  |
| dim_date | week_of_year | Integer | false | false | Sum | Data | 0 |  |
| dim_date | day_of_week | Text | false | false | None | Data |  |  |
| dim_date | is_month_end | Integer | false | false | Sum | Data | 0 |  |
| dim_date | is_quarter_end | Integer | false | false | Sum | Data | 0 |  |
| dim_date | is_year_end | Integer | false | false | Sum | Data | 0 |  |
| dim_date | is_trading_day | Integer | false | false | Sum | Data | 0 |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Date | Date | true | false | None | CalculatedTableColumn | General Date |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Year | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | MonthNo | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Month | Text | true | false | None | Calculated |  |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | QuarterNo | Integer | true | false | None | Calculated | 0 |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Quarter | Text | true | false | None | Calculated |  |  |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Day | Integer | true | false | None | Calculated | 0 |  |
| dim_security | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| dim_security | security_id | Integer | false | false | None | Data | 0 |  |
| dim_security | ticker | Text | false | false | None | Data |  |  |
| dim_security | name | Text | false | false | None | Data |  |  |
| dim_security | asset_class | Text | false | false | None | Data |  |  |
| dim_security | sector | Text | false | false | None | Data |  |  |
| dim_security | benchmark_id | Integer | false | false | None | Data | 0 |  |
| dim_security | is_etf | True/False | false | false | None | Data | TRUE;"TRUE";"FALSE" |  |
| dim_security | expense_ratio_bps | Integer | false | false | Sum | Data | 0 |  |
| _Measures | RowNumber-2662979B-1795-4F74-8F37-6A1BA8059B61 | Integer | true | true | Default | RowNumber |  |  |
| _Measures | Value | Integer | true | false | None | CalculatedTableColumn | 0 |  |

### INFO.VIEW.RELATIONSHIPS() (14 rows)

| FromTable | FromColumn | FromCardinality | ToTable | ToColumn | ToCardinality | IsActive | CrossFilteringBehavior |
|---|---|---|---|---|---|---|---|
| fact_transactions | advisor_id | Many | dim_advisor | advisor_id | One | true | OneDirection |
| fact_transactions | client_id | Many | dim_client | client_id | One | true | OneDirection |
| fact_transactions | security_id | Many | dim_security | security_id | One | true | OneDirection |
| fact_transactions | txn_date | Many | dim_date | date | One | true | OneDirection |
| fact_portfolio_snapshot | advisor_id | Many | dim_advisor | advisor_id | One | true | OneDirection |
| fact_portfolio_snapshot | benchmark_id | Many | dim_benchmark | benchmark_id | One | true | OneDirection |
| fact_portfolio_snapshot | client_id | Many | dim_client | client_id | One | true | OneDirection |
| fact_portfolio_snapshot | snapshot_date | Many | dim_date | date | One | true | OneDirection |
| fact_fees | advisor_id | Many | dim_advisor | advisor_id | One | true | OneDirection |
| fact_fees | client_id | Many | dim_client | client_id | One | true | OneDirection |
| fact_fees | fee_date | Many | dim_date | date | One | true | OneDirection |
| dim_client | client_since | Many | LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | date | One | true | OneDirection |
| dim_date | date | Many | LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | date | One | true | OneDirection |
| dim_security | benchmark_id | Many | dim_benchmark | benchmark_id | One | true | OneDirection |
