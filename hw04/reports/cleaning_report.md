# Wildcat Capital Data Cleaning Report
**To:** Portfolio Committee | **From:** Charlie Goldsmith | **Date:** October 25, 2026

## Executive summary

The Wildcat Capital extract is usable for reporting after cleaning, with six flagged limitations. This is because the audit tagged six findings as ERROR (wrong, or will break a join or calculation), and the cleaning program fixed every one without inventing a value. fact_transactions had 197,175 security keys stored as "45.0," which matched 0.0000% of dim_security. fact_transactions had 200 rows for clients that do not exist, which held $10,888,495.37 of activity. fact_transactions had 836 Buy rows with negative share counts. fact_portfolio_snapshot had 300 returns stored as percent text, which failed to load as numbers. dim_client had 25 duplicate clients and 78 states spelled out in full. Because every repair was confirmed against a second column or a second table, the clean data now passes all 13 relationship checks, every column rule, and every reconciliation.

| Table | Stage | Rows | Completeness | Key uniqueness | Type validity | Rule pass | Referential match |
|---|---|---:|---:|---:|---:|---:|---:|
| dim_client | raw | 2,525 | 99.79% | 100.00% | 100.00% | 96.91% | 100.00% |
| dim_client | clean | 2,500 | 99.79% | 100.00% | 100.00% | 100.00% | 100.00% |
| fact_portfolio_snapshot | raw | 129,547 | 100.00% | 100.00% | 99.98% | 100.00% | 100.00% |
| fact_portfolio_snapshot | clean | 129,547 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| fact_transactions | raw | 298,772 | 100.00% | 100.00% | 91.73% | 99.72% | 81.95% |
| fact_transactions | clean | 298,572 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |

The other five tables scored 100% on every measure in both stages (`reports/data_quality_scorecard.csv`). dim_client completeness stays at 99.79% because I chose to leave 75 risk profiles blank (judgment call 3).

## Cleaning summary

| Table | Issue | Action | Rows |
|---|---|---|---:|
| dim_client | Duplicate clients (ids 2501 to 2525), last name off by one letter | Quarantine | 25 |
| dim_client | State stored as full name | Standardize to USPS code | 77 |
| dim_client | Blank risk_profile | Flag, leave blank | 75 |
| fact_transactions | security_id stored as "45.0" | Convert to "45" | 197,175 |
| fact_transactions | Negative shares on Buy rows | Remove sign, flag | 836 |
| fact_transactions | client_id not in dim_client | Quarantine | 200 |
| fact_transactions | Trade dated on a weekend | Flag | 56,117 |
| fact_transactions | Activity after an inactive client's last snapshot | Flag | 2,410 |
| fact_portfolio_snapshot | return_ytd stored as "9.28%" | Convert (reconciled) | 300 |
| fact_portfolio_snapshot | AUM exactly $1,000.00 | Flag | 420 |
| fact_portfolio_snapshot | return_ytd above 100% | Flag | 977 |
| dim_advisor, dim_benchmark, dim_date, dim_security, fact_fees | No correctable defect | Leave as is | 0 |

Raw rows equal clean rows plus quarantined rows for all eight tables. dim_client has 2,525 raw rows, 2,500 clean rows, and 25 quarantined rows. fact_transactions has 298,772 raw rows, 298,572 clean rows, and 200 quarantined rows. The other six tables have the same row count in both stages. The audit trail records 198,388 cell changes in `data/audit/value_changes.csv`.

## Key judgment calls

**1. Quarantine the 200 orphan transactions instead of reassigning them.** The 200 rows cannot stay in the data. This is because all 200 are exact copies of another client's real transaction on every column except client_id and txn_id. Orphan txn 298573 copies txn 129498 of client 1088. Reassigning each row to the client it copies would double count $10,888,495.37, because that client already has the original row. *Risk:* if these are real trades for clients missing from dim_client, I have removed $10.9 million of activity. The quarantine file keeps a pointer to each original so the rows can be restored.

**2. Store benchmark + alpha for the 300 percent returns.** The percent strings are rounded copies of a value the data already holds. This is because return_ytd minus benchmark_return_ytd equals active_alpha_ytd within 0.000001 on the other 129,247 rows. Snapshot 42 stores "9.28%," and its benchmark plus alpha is 0.092756. All 300 converted values agree with benchmark plus alpha within 0.00005, the rounding of a two-decimal percent. Storing 0.0928 would have broken the alpha formula on 284 rows, so I stored the six-decimal sum. *Risk:* if alpha were the corrupted column, this copies its error into return. The agreement with the independent percent string on all 300 rows rules that out.

**3. Flag the 75 blank risk profiles instead of filling them.** The blank profiles stay blank. This is because all 75 clients sit on the 60/40 benchmark, and that benchmark also serves every Balanced client, so the data suggests "Balanced" without proving it. Risk profile drives suitability reviews, and a guessed profile looks the same as a real one in a compliance report. *Risk:* risk-profile reports show a 75-client blank group. The committee should treat that group as a to-do list for advisors.

**4. Pick the real duplicate client by fact activity, not by name.** I kept the client record the fact tables use and quarantined the other. This is because the 25 duplicate pairs differ by one trailing letter, but in two pairs the copy has an extra letter ("Leen" vs "Lee") instead of a missing one. A rule based on the longer name would have deleted two real clients with 243 transactions. The 25 removed ids have zero fee, snapshot or transaction rows. *Risk:* if a removed row is a different person who matches on all 12 other columns, I removed a real client. That match by chance is unlikely.

## Limitations

1. **Returns count deposits as gains.** 977 snapshots report a year-to-date return above 100%, with a maximum of 9,467%. The mean return_ytd is 0.1143 with these rows and 0.0320 without them. Exclude `flag_return_implausible = 1` before ranking advisors on return or alpha.
2. **Two fee sources disagree.** Advisory Fee transactions differ from fact_fees by more than 1% in 10,286 of 10,396 client-years. fact_fees reconciles to AUM x bps on all 122,197 rows, so use fact_fees for revenue.
3. **Trade dates are unreliable.** 56,117 trades fall on a weekend (28.5% of trades), and 2,410 transactions post after a client's exit. Daily analysis and departed-client revenue need the flags.
4. **7,350 snapshot months (5.7%) have no fee row.** Fee revenue may be understated by that share if the rows were lost rather than waived.
5. **Prices and holdings are not market-realistic.** Every security's price range exceeds 10x, and holdings before 2020 are missing, so the data cannot support cost basis or position reporting.

IQR fences flag 13,261 snapshot AUM values (10.2%), but 13,121 of them belong to UHNW clients. A flagged value is unusual, not wrong, unless another rule or reconciliation also fails on that row.

---
AI-assisted report — reviewed for factual accuracy on October 25, 2026 by Charlie Goldsmith
