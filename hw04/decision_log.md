# HW4 Decision Log: Wildcat Capital Data Cleaning

**Author:** Charlie Goldsmith | **Source of evidence:** `reports/dq_summary_raw.csv` and `reports/profile_raw.csv` from `scripts/01_profile.py`

I wrote each entry from the audit output before generating the cleaning code for that issue, and I used the entry as the prompt for that step of `scripts/02_clean.py`. The step number (C1 to C8) points to the matching block in the script. Entries marked **leave as is** are issues I investigated and decided not to change.

The log has 26 entries. Eleven are defects I changed or flagged. Fifteen are legitimate structure or known limitations that I left alone.

| # | Table / column | Decision | Step |
|---|---|---|---|
| D01 | dim_client (whole row) | quarantine | C1 |
| D02 | dim_client.state | standardize | C2 |
| D03 | dim_client.risk_profile | flag | C3 |
| D04 | dim_client.zip_code | leave as is | - |
| D05 | dim_client.primary_account_type, client_tier | leave as is | - |
| D06 | dim_advisor.certifications | leave as is | - |
| D07 | dim_security.sector, expense_ratio_bps | leave as is | - |
| D08 | dim_security.name | leave as is | - |
| D09 | dim_benchmark (unused members) | leave as is | - |
| D10 | dim_date.week_of_year, is_trading_day | leave as is | - |
| D11 | fact_transactions.security_id | convert | C4 |
| D12 | fact_transactions.security_id, shares, price (blanks) | leave as is | - |
| D13 | fact_transactions.shares | convert | C5 |
| D14 | fact_transactions.client_id | quarantine | C6 |
| D15 | fact_transactions.txn_date (weekends) | flag | C8 |
| D16 | fact_transactions (inactive clients) | flag | C8 |
| D17 | fact_transactions Advisory Fee vs fact_fees | leave as is | - |
| D18 | fact_transactions.price, shares (history) | leave as is | - |
| D19 | fact_transactions near-duplicates | leave as is | - |
| D20 | fact_portfolio_snapshot.return_ytd (percent text) | convert | C7 |
| D21 | fact_portfolio_snapshot returns (scientific notation) | leave as is | - |
| D22 | fact_portfolio_snapshot.aum | flag | C8 |
| D23 | fact_portfolio_snapshot.return_ytd (> 100%) | flag | C8 |
| D24 | fact_portfolio_snapshot vs fact_fees (missing months) | leave as is | - |
| D25 | fact_fees near-duplicate | leave as is | - |
| D26 | fact_fees (all columns) | leave as is | - |

---

## Defects changed or flagged

### D01. dim_client: near-duplicate client rows
- **Evidence:** 25 rows (client_id 2501 to 2525) match another client on all 12 columns other than client_id and last_name. The last names differ by one trailing letter: 2501 "Taylo" vs 674 "Taylor", 2503 "Jacobso" vs 99 "Jacobson", 2512 "Leen" vs 1193 "Lee". The fact tables reference the lower id in every pair and reference 2501 to 2525 zero times (0 fee rows, 0 snapshot rows, 0 transactions).
- **Dimension violated:** Uniqueness, Accuracy
- **Decision:** quarantine
- **Justification:** These are re-keyed copies of real clients with a typo in the last name. Keeping them inflates the client count by 25 (1.0%) and would show 25 clients with $0 of activity. The fact tables tell me which copy is real, so I keep the copy the facts use. I do not use name length to pick, because two of the copies have an extra letter instead of a missing one.
- **Risk:** If a 2501 to 2525 row is a different person with the same age, city, ZIP, AUM, advisor and start date, I have removed a real client. The chance of a 12-column match by accident is low, and the quarantine file keeps each row next to `duplicate_of_client_id` so it can be restored.

### D02. dim_client.state: full names instead of USPS codes
- **Evidence:** 78 of 2,525 raw rows (77 after D01) store a full name: Pennsylvania 25, New York 14, Florida 15, New Jersey 13, California 5, Illinois 4, Texas 2. The other 2,447 rows use two-letter codes.
- **Dimension violated:** Consistency, Validity
- **Decision:** standardize
- **Justification:** A state slicer or map in Power BI would show "PA" and "Pennsylvania" as two states, splitting Pennsylvania's 439 clients into 414 and 25. A fixed USPS lookup is a lossless mapping, and every code it produces (PA, NY, FL, NJ, CA, IL, TX) already exists in the column.
- **Risk:** Close to none. A wrong lookup entry would move clients to the wrong state, so the script asserts that every new value is already a code used elsewhere in the column.

### D03. dim_client.risk_profile: blank values
- **Evidence:** 76 blanks in raw, 75 after D01. All 75 clients sit on benchmark_id 3 (60/40 Blend) in fact_portfolio_snapshot. Benchmark 3 also serves every Balanced client (38,960 snapshot rows).
- **Dimension violated:** Completeness
- **Decision:** flag (`flag_risk_profile_missing = 1`), leave the value blank
- **Justification:** The benchmark suggests "Balanced," but 60/40 may also be the default the firm assigns when no profile exists. Filling "Balanced" would turn a guess into a suitability record, and risk profile drives compliance reviews. A visible blank plus a flag lets the committee count unprofiled clients.
- **Risk:** Reports that group by risk_profile show a 75-client blank bucket. That is the accurate picture; the risk sits in leaving it unexplained, so README_clean.md documents it.

### D11. fact_transactions.security_id: stored as float text
- **Evidence:** All 197,175 non-blank values look like "45.0". The profile shows 100% of them failing an integer parse, and the text join to dim_security.security_id ("45") matches 0.0000%.
- **Dimension violated:** Validity, Referential Integrity
- **Decision:** convert ("45.0" to "45")
- **Justification:** The ".0" comes from an export that read the column as a float because cash rows are blank. The numeric value does not change, so this is a format fix. Without it, a text-typed relationship in Power BI returns blank security attributes for every trade.
- **Risk:** None to the values. The script asserts the numeric value of every changed key is identical before and after.

### D13. fact_transactions.shares: negative share counts on Buy rows
- **Evidence:** 836 Buy rows (691 clients) have negative shares, for example txn 272: shares -261.9719, price 441.71, amount 115,715.61. No Sell or Dividend row is negative. For all 836, |shares| x price equals amount within $0.005.
- **Dimension violated:** Validity, Consistency
- **Decision:** convert (drop the minus sign) and flag (`flag_shares_sign_corrected = 1`)
- **Justification:** The txn_type already carries direction, and every other row stores a positive share count. The amount column confirms the magnitude, so the sign is the only defect. Left alone, these rows reduce share totals for buys and break any position calculation.
- **Risk:** If the source meant these as sells mislabeled as buys, the fix keeps the wrong direction. I found no evidence of that (amount, price and type agree), and the flag lets me find the 836 rows again.

### D14. fact_transactions.client_id: ids with no client
- **Evidence:** 200 rows (txn_id 298573 to 298772, the last 200 rows of the file) use 200 distinct client_ids from 2702 to 3192 that do not exist in dim_client. All 200 are exact copies of an existing transaction on every other column (advisor, security, date, type, shares, price, amount). Example: orphan txn 298573 copies txn 129498 of client 1088. Total amount: $10,888,495.37.
- **Dimension violated:** Referential Integrity, Uniqueness
- **Decision:** quarantine
- **Justification:** I could reassign each row to the client whose transaction it copies, but that client already has the real row, so reassignment would double count $10.9 million of activity. Keeping the rows with orphan ids would put them under a blank client in every report. Quarantine removes them and keeps a pointer to the original.
- **Risk:** If these are real transactions for clients missing from dim_client, I have removed $10.9 million of activity. The exact-copy evidence makes that unlikely, and the quarantine file lists `copy_of_txn_id` for review.

### D15. fact_transactions.txn_date: trades on weekends
- **Evidence:** 56,146 Buy, Sell and Dividend rows in raw (56,117 after D14) fall on a date where dim_date.is_trading_day = 0. That is 28.5% of trades, close to the 2/7 share you would get from dates assigned at random.
- **Dimension violated:** Accuracy/Plausibility, Consistency (fact vs dim_date)
- **Decision:** flag (`flag_non_trading_day = 1`)
- **Justification:** Markets do not settle trades on Saturday or Sunday, so these dates are wrong, but I have no source for the right date. Moving them to the next Monday would invent a date. Amounts and counts by month stay correct for most rows, so a flag is enough.
- **Risk:** Daily or weekday analysis of trading activity will be wrong. Monthly totals shift only for trades dated on a weekend at a month boundary.

### D16. fact_transactions: activity after an inactive client's last snapshot
- **Evidence:** 175 clients have is_active = False. Their snapshots stop in mid-2023, yet 2,410 of their 21,092 transactions (131 clients) are dated after the month of their final snapshot.
- **Dimension violated:** Consistency (fact vs fact, fact vs dim_client)
- **Decision:** flag (`flag_after_client_exit = 1`)
- **Justification:** Either the exit date or the transaction date is wrong, and the data does not say which. Deleting the rows would lose real money movements if the exit date is the error.
- **Risk:** Flow and fee revenue for departed clients may be overstated by up to 2,410 rows. The flag lets the committee exclude them.

### D20. fact_portfolio_snapshot.return_ytd: percent strings
- **Evidence:** 300 values carry a percent sign, for example snapshot 42: "9.28%". These fail a float parse. For all 300, value / 100 matches benchmark_return_ytd + active_alpha_ytd within 0.00005 (the rounding of a two-decimal percent). Snapshot 42: 0.0928 vs 0.08279 + 0.009966 = 0.092756.
- **Dimension violated:** Validity, Consistency
- **Decision:** convert, using the reconciled value
- **Justification:** alpha = return - benchmark holds to 0.000001 on the other 129,247 rows, so benchmark + alpha is the full-precision return and the percent string is a rounded copy of it. I store benchmark + alpha (6 decimals) after asserting it agrees with the percent. Storing 0.0928 would break the alpha identity by up to 0.00005 on these rows.
- **Risk:** If alpha were the corrupted column, I would copy its error into return_ytd. The agreement with the independent percent string on all 300 rows rules that out.

### D22. fact_portfolio_snapshot.aum: balances of exactly $1,000.00
- **Evidence:** 420 snapshots (92 clients) show aum = 1000.0 exactly. Client 29 falls from $16,704.59 (2021-01) to exactly $1,000.00 for both February and March 2021 while the S&P 500 benchmark moves. The 386 fee rows charged on these balances are $0.80 or less.
- **Dimension violated:** Accuracy/Plausibility
- **Decision:** flag (`flag_aum_floor = 1`)
- **Justification:** The value looks like a floor the source system applies when withdrawals exceed the balance. The true balance is unknown, and $1,000 is closer to the truth than any value I could make up.
- **Risk:** AUM totals are off by at most $420,000 across 420 snapshots, which is immaterial against $566.7 billion of total snapshot AUM. Returns on these rows are distorted (see D23).

### D23. fact_portfolio_snapshot.return_ytd: returns above 100%
- **Evidence:** 977 snapshots (144 clients) report return_ytd above 1.0; the maximum is 94.67 (9,467%). Client 29 jumps from -0.32 to 2.87 in July 2022 when AUM rises from $9,105 to $52,090 while the S&P 500 benchmark is -0.16. The return measures AUM change and counts deposits as gains.
- **Dimension violated:** Accuracy/Plausibility
- **Decision:** flag (`flag_return_implausible = 1`)
- **Justification:** I cannot recompute a time-weighted return without daily cash flows tied to each snapshot, so I cannot correct the value. active_alpha_ytd inherits the same distortion. The flag lets the committee drop these rows before ranking advisors on alpha.
- **Risk:** Any average return or alpha that includes these rows is overstated. The mean return_ytd across all 129,547 snapshots is 0.1143; without the 977 flagged rows it is 0.0320. One snapshot at 94.67 moves an advisor's average on its own.

---

## Investigated and left as is

### D04. dim_client.zip_code: leading zeros
- **Evidence:** 232 ZIPs start with 0 (e.g. client 2: "03897"). All 2,525 values are five digits.
- **Dimension violated:** none (legitimate structure)
- **Decision:** leave as is
- **Justification:** ZIP is an identifier, not a number. Reading the file as text preserves the zero. README_clean.md tells the BI tool to type the column as text.
- **Risk:** A tool that auto-detects the type will turn "03897" into 3897 and break any geographic lookup.

### D05. dim_client.primary_account_type "529" and client_tier bands
- **Evidence:** 523 clients have the account type "529", which looks numeric. client_tier agrees with initial_aum on all 2,525 rows (Retail under $500K, HNW $500K to $5M, UHNW above $5M).
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** A 529 is a college savings plan; "529" is its name. The tier bands confirm client_tier is consistent with AUM.
- **Risk:** A BI tool may type the column as mixed; README_clean.md sets it to text.

### D06. dim_advisor.certifications: the word "None"
- **Evidence:** 6 of 25 advisors have certifications = "None".
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** "None" is an answer (no CFA, CFP or CIMA), not a missing value. Default `pd.read_csv` would turn it into NaN and make six advisors look like missing data, which is why the scripts read every file as text.
- **Risk:** A tool that treats "None" as null would report 6 missing values. README_clean.md calls this out.

### D07. dim_security.sector and expense_ratio_bps: blanks
- **Evidence:** sector is blank on all 219 non-equity securities and filled on all 281 equities. expense_ratio_bps is blank on all 281 non-ETFs and filled on all 219 ETFs. No exceptions in either direction.
- **Dimension violated:** none (legitimate structure)
- **Decision:** leave as is
- **Justification:** Bond, cash and alternative funds have no GICS sector, and individual stocks have no expense ratio. Filling these would invent data. The scorecard counts these cells as not required.
- **Risk:** A sector chart shows a blank bar for funds. Labeling it "Fund (no sector)" belongs in the Power BI model, not in the data.

### D08. dim_security.name: repeated names
- **Evidence:** Three names repeat ("Jones Inc Fund", "Davis PLC Fund", "Graham Group Inc."), each with different tickers, asset classes and benchmarks.
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** One issuer can run several funds. security_id and ticker are unique, so joins are unaffected.
- **Risk:** A visual that groups by name merges two securities. Use ticker as the label.

### D09. dim_benchmark: unused members
- **Evidence:** Snapshots use benchmarks 1, 3 and 8 only. Securities use 1, 2, 3, 4, 5 and 7. Benchmark 6 (MSCI Emerging Markets) is used by neither.
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** A dimension can hold members with no facts yet. Removing one would break a later load that uses it.
- **Risk:** None.

### D10. dim_date.week_of_year and is_trading_day
- **Evidence:** week_of_year matches the ISO week on all 1,827 rows and disagrees with Python's %U week on 788 rows. is_trading_day = 1 on all 1,305 weekdays, including market holidays such as 2020-12-25 and 2024-07-04.
- **Dimension violated:** Accuracy (is_trading_day only, minor)
- **Decision:** leave as is
- **Justification:** ISO weeks are a valid convention; README_clean.md names it so nobody rebuilds the column with a different rule. Adding an NYSE holiday calendar would bring in outside data; the weekday rule is close enough to support D15.
- **Risk:** About 9 to 10 holidays a year count as trading days, so D15 misses trades dated on a holiday.

### D12. fact_transactions: blank security_id, shares and price on cash rows
- **Evidence:** 101,597 rows have all three blank. Every one is a Deposit, Withdrawal or Advisory Fee; every Buy, Sell and Dividend row has all three filled.
- **Dimension violated:** none (legitimate structure)
- **Decision:** leave as is
- **Justification:** Cash movements have no security. The RI check reports these as a 34.0% null-key rate and excludes them from the match rate.
- **Risk:** None.

### D17. Advisory Fee transactions vs fact_fees
- **Evidence:** Advisory Fee transaction totals differ from fact_fees totals by more than 1% in 10,286 of 10,396 client-years (98.9%); the median ratio is 0.796. Transaction fees post on random days; fact_fees posts on the 1st of each month.
- **Dimension violated:** Consistency (fact vs fact)
- **Decision:** leave as is
- **Justification:** fact_fees reconciles to aum_basis x bps / 10,000 / 12 on every row and to snapshot AUM on every row, so it is the reliable fee source. The transaction rows are cash debits from a different system. Forcing them to match would invent amounts.
- **Risk:** Two fee totals exist. README_clean.md tells report builders to use fact_fees for revenue and fact_transactions only for cash flows.

### D18. fact_transactions: price history and position history
- **Evidence:** Every one of the 500 securities trades at prices whose max/min ratio exceeds 10x (median 45.8x). In 15,175 of 38,813 client-security positions, shares sold exceed shares bought, and 7,128 dividends go to clients with no recorded buy.
- **Dimension violated:** Accuracy/Plausibility
- **Decision:** leave as is
- **Justification:** Positions opened before 2020 explain the sell and dividend gaps, since clients date back to 2015 and the extract starts in 2020. The price ranges point to simulated prices; there is no market price feed in the extract to correct them against. Amounts reconcile to shares x price, so dollar totals are internally consistent.
- **Risk:** Do not build holdings, cost basis or price-performance measures from this table. README_clean.md lists this as a known limitation.

### D19. fact_transactions: rows identical except one column
- **Evidence:** 1,050 rows match another row on everything but amount (e.g. client 1 made two deposits on 2024-09-25: $94,893.52 and $26,587.27). 14 rows match on everything but txn_date (small Advisory Fee debits such as $306.32 on two dates). The 400 rows that differ only in client_id are D14.
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** Two deposits on the same day, or the same monthly fee on two dates, are normal account activity. The amounts or dates differ, so these are separate events.
- **Risk:** If any are double-posted, cash flows are overstated by a few rows. The 14 same-amount pairs are small (under $310 each).

### D21. Scientific notation in return_ytd and active_alpha_ytd
- **Evidence:** 135 return_ytd and 756 active_alpha_ytd values look like "1.2e-05".
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** These are valid floats that every parser reads. Rewriting them would create 891 value changes with no change in value.
- **Risk:** None for Power BI or pandas; a text-based tool would show them as text.

### D24. Snapshot months with no fee row
- **Evidence:** 7,350 of 129,547 snapshots (5.7%, 2,261 clients) have no fee row for the same client-month. The gap rate is the same for active (5.7%) and inactive (5.9%) clients. Every fee row has a matching snapshot.
- **Dimension violated:** Completeness (possible)
- **Decision:** leave as is
- **Justification:** Missing fees could be waivers, billing holidays or lost rows. Adding a fee would invent revenue.
- **Risk:** If the rows are lost, fee revenue is understated by roughly 5.7%. README_clean.md lists this.

### D25. fact_fees: one near-duplicate pair
- **Evidence:** fee 57446 (2020-06-01) and fee 57490 (2024-04-01) for client 1169 are identical except the date: aum_basis $1,000.00, 85.65 bps, $0.71.
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** Both months have a matching snapshot at the $1,000 floor (D22), and the fee recomputes correctly, so these are two real charges.
- **Risk:** None.

### D26. fact_fees: no defects found
- **Evidence:** amount = aum_basis x bps / 10,000 / 12 on 122,197 of 122,197 rows (max difference $0.005). aum_basis equals snapshot aum on 122,197 of 122,197 rows. bps_charged ranges from 25.56 to 100.38. All keys and dates join.
- **Dimension violated:** none
- **Decision:** leave as is
- **Justification:** The table passes every check, so it is copied to data/clean unchanged.
- **Risk:** None.
