# Wildcat Capital: Clean Data (HW4)

`scripts/02_clean.py` produced these eight files from `data/raw/`. File names and columns match the raw extract. The only additions are 0/1 flag columns at the end of three tables. `scripts/03_validate.py` checks every file in this folder.

| File | Rows | Change from raw |
|---|---:|---|
| dim_advisor.csv | 25 | none |
| dim_benchmark.csv | 8 | none |
| dim_client.csv | 2,500 | 25 near-duplicate rows quarantined; 77 states standardized; 1 flag added |
| dim_date.csv | 1,827 | none |
| dim_security.csv | 500 | none |
| fact_fees.csv | 122,197 | none |
| fact_portfolio_snapshot.csv | 129,547 | 300 percent returns converted; 2 flags added |
| fact_transactions.csv | 298,572 | 200 orphan rows quarantined; 197,175 security_id formats fixed; 836 share signs fixed; 3 flags added |

Row-count proof: `data/audit/row_count_proof.csv` (raw = clean + quarantined for all eight tables).

## Relationships

Star schema with three fact tables. Every relationship is many-to-one from the fact (or child dimension) to the dimension, single direction. All 13 match at 100.0000% in the clean data.

| From (many) | To (one) | Notes |
|---|---|---|
| fact_fees.client_id | dim_client.client_id | |
| fact_fees.advisor_id | dim_advisor.advisor_id | |
| fact_fees.fee_date | dim_date.date | always the 1st of the month |
| fact_portfolio_snapshot.client_id | dim_client.client_id | |
| fact_portfolio_snapshot.advisor_id | dim_advisor.advisor_id | |
| fact_portfolio_snapshot.benchmark_id | dim_benchmark.benchmark_id | |
| fact_portfolio_snapshot.snapshot_date | dim_date.date | always the 1st of the month |
| fact_transactions.client_id | dim_client.client_id | |
| fact_transactions.advisor_id | dim_advisor.advisor_id | |
| fact_transactions.security_id | dim_security.security_id | blank on 101,528 cash rows (34.0%) by design |
| fact_transactions.txn_date | dim_date.date | |
| dim_client.advisor_id | dim_advisor.advisor_id | snowflake link; matches the advisor_id on every fact row |
| dim_security.benchmark_id | dim_benchmark.benchmark_id | snowflake link |

Each fact table carries advisor_id, and it equals dim_client.advisor_id on every row. In Power BI, keep one active path to dim_advisor (fact to dim_advisor) and leave dim_client to dim_advisor inactive, or the model has two routes to the same table. The same applies to dim_benchmark (snapshot path active, security path inactive).

The three date relationships join on dim_date.date, not date_id. No fact table stores date_id.

## Column-type settings for a BI tool

Turn off automatic type detection and set these by hand:

| Type | Columns |
|---|---|
| Whole number | all `*_id` columns, dim_client.age, dim_advisor.years_experience, dim_advisor.aum_target_mm, dim_date.year/quarter/month/week_of_year, fact_portfolio_snapshot.year/month, all `flag_*` columns |
| Decimal | initial_aum, aum, aum_basis, amount, price, shares (4 decimals), bps_charged, expense_ratio_bps |
| Decimal, percent format | return_ytd, benchmark_return_ytd, active_alpha_ytd, cash_pct (stored as decimals: 0.0928 = 9.28%; some values use scientific notation such as 1.2e-05) |
| Currency | initial_aum, aum, aum_basis, fact_fees.amount, fact_transactions.amount |
| Date (yyyy-mm-dd) | dim_date.date, dim_client.client_since, fee_date, snapshot_date, txn_date |
| Text | dim_client.zip_code (232 ZIPs start with 0), primary_account_type and account_type ("529" is a plan name), dim_advisor.certifications ("None" is a value, not a null) |
| True/False | dim_client.is_active, dim_security.is_etf (stored as the text True/False) |
| 0/1 | dim_date.is_month_end, is_quarter_end, is_year_end, is_trading_day |

Other settings:
- Do not let the tool treat the text "None" as null (dim_advisor.certifications).
- Blank cells are empty strings. sector, expense_ratio_bps, security_id, shares and price are blank by design on the rows where they do not apply (see below).
- dim_date.week_of_year is the ISO week (weeks start Monday; week 1 contains the first Thursday). dim_date.is_trading_day = 1 on every weekday, holidays included.
- fact_transactions.amount is always positive. Direction comes from txn_type: Buy, Withdrawal and Advisory Fee reduce cash; Sell, Dividend and Deposit add to it.

## Flag columns added

| Table | Column | 1 means | Rows = 1 |
|---|---|---|---:|
| dim_client | flag_risk_profile_missing | risk_profile is blank; not filled (all 75 sit on benchmark 3) | 75 |
| fact_transactions | flag_shares_sign_corrected | shares was negative on a Buy; minus sign removed after confirming abs(shares) x price = amount | 836 |
| fact_transactions | flag_non_trading_day | Buy, Sell or Dividend dated on a Saturday or Sunday | 56,117 |
| fact_transactions | flag_after_client_exit | client is inactive and the transaction is after the month of their last snapshot | 2,410 |
| fact_portfolio_snapshot | flag_aum_floor | aum is exactly 1000.00, which looks like a source-system floor | 420 |
| fact_portfolio_snapshot | flag_return_implausible | return_ytd above 1.0 (100%); return counts deposits as gains | 977 |

Suggested use: exclude `flag_return_implausible = 1` from any return or alpha average, and filter `flag_after_client_exit = 1` out of revenue and flow measures for departed clients.

## Legitimate blanks (not defects)

- dim_security.sector: blank on all 219 non-equity funds.
- dim_security.expense_ratio_bps: blank on all 281 individual stocks (non-ETFs).
- fact_transactions.security_id, shares, price: blank on all 101,528 Deposit, Withdrawal and Advisory Fee rows.

## Known limitations (not fixed)

1. **75 clients have no risk profile.** Filling "Balanced" from their benchmark would be a guess on a compliance field. Reason: no source states the profile.
2. **Weekend trade dates (56,117 rows).** The true trade date is unknown. Reason: moving dates would invent them; monthly totals are mostly unaffected.
3. **Activity after client exit (2,410 rows, 131 clients).** Either is_active/the last snapshot or the transaction date is wrong. Reason: the data cannot tell which.
4. **Returns include cash flows.** return_ytd and active_alpha_ytd measure AUM change, so deposits count as gains (977 rows above 100%, max 94.67). Reason: a time-weighted return needs cash-flow timing per snapshot, which the extract lacks.
5. **$1,000 AUM floor (420 snapshots).** The true balance is unknown. Reason: any replacement would be invented.
6. **Two fee sources disagree.** Advisory Fee rows in fact_transactions differ from fact_fees in 98.9% of client-years (median ratio 0.796). Use fact_fees for fee revenue; it reconciles to AUM x bps on every row. Reason: forcing agreement would invent amounts.
7. **7,350 snapshot months (5.7%) have no fee row.** Could be waivers or lost rows. Reason: adding fees would invent revenue.
8. **Prices and holdings are not market-realistic.** Every security's price range exceeds 10x (median 45.8x), and sells exceed buys in 15,175 of 38,813 positions because holdings before 2020 are not in the extract. Reason: no market price feed or opening positions to reconcile against. Do not build cost basis or holdings from fact_transactions.
9. **is_trading_day ignores market holidays.** Reason: correcting it needs an outside holiday calendar.

## Audit trail

| File | Contents |
|---|---|
| data/audit/cleaning_log.csv | 16 entries: table, issue, action, rows affected, note |
| data/audit/value_changes.csv | 198,388 cell changes: table, key column, key, column, old value, new value |
| data/audit/quarantine_dim_client_near_duplicates.csv | 25 rows + duplicate_of_client_id, duplicate_of_last_name |
| data/audit/quarantine_fact_transactions_orphan_client.csv | 200 rows + copy_of_txn_id, copy_of_client_id |
| data/audit/row_count_proof.csv | raw, clean and quarantined rows per table |
