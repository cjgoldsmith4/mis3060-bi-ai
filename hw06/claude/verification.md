# Part D: Verifying Claude's `AUM-Weighted Alpha`
MIS3060 Business Intelligence with AI | Charlie Goldsmith

Claude's measure is correct for every slice the assignment tests, and I kept its logic. This is because its result matches an independent pandas calculation on all nine `AUM-Weighted Alpha` rows of `reports/measure_reconciliation.csv`, and it handles the two traps in the definition: it picks the last date before dropping suspect rows, and it drops suspects from both the numerator and the weights.

**Did it run as written?** Claude's measure ran in Power BI with no edits. I pasted it, word for word, into DAX query view as a query-scoped measure (`claude/claude_measure_test.dax`), ran Claude's test query against it, and added the final model measure as a second column. The raw result grids are in `claude/claude_measure_test_results.txt`. The year query returns the last snapshot date, the row count on that date, the suspect rows dropped and the measure for each year:

| Year | Last snapshot | Rows on that date | Suspect rows dropped | AUM-Weighted Alpha |
|---|---|---:|---:|---:|
| 2020 | 2020-12-01 | 1,847 | 91 | -0.68% |
| 2021 | 2021-12-01 | 2,157 | 84 | -0.16% |
| 2022 | 2022-12-01 | 2,500 | 79 | 2.85% |
| 2023 | 2023-12-01 | 2,325 | 157 | 1.77% |
| 2024 | 2024-12-01 | 2,325 | 148 | 1.45% |

The tier query returns HNW 1.40%, Retail 2.40% and UHNW 1.41% for 2024, and the grand-total query returns 1.45%. Claude's draft and the final measure agree to every printed digit in all nine slices (2024: 0.014479946800564277 in both columns), and the pandas side in `01_reconcile_measures.py` computes the same values from the CSVs.

**Which reconciliation rows prove it?** Nine rows: `AUM-Weighted Alpha` at `Total`, at `year=2020` through `year=2024`, and at `client_tier=HNW | year=2024`, `client_tier=Retail | year=2024` and `client_tier=UHNW | year=2024`. Each one matches within the 0.0001 ratio tolerance. The `Alpha Signal` rows for the same slices match too, since the label reads directly from this measure.

**Edge cases checked**

1. **Grand total equals 2024.** Claude claimed the card and the 2024 row would show the same number. This holds: both return +1.4480%. This is because with no filter the last snapshot is 2024-12-01, the same date the 2024 filter finds.
2. **`dim_date[year] = 2022`.** 2022 is the one year where every client still has a balance (2,500 rows on 2022-12-01), and the measure returns +2.85%, which reads "Outperforming". This is because the year filter moves the last date to 2022-12-01 and the fact-column date filter stays inside the year filter.
3. **The 2024 tier table.** All three tiers resolve to 2024-12-01, so the tier rows and the total use the same date. All 148 suspect rows on that date belong to Retail; HNW and UHNW have none. The total row (1.45%) is a fresh weighted average over all tiers, not the average of the three tier values (1.74%), as Claude said.
4. **Order of operations.** Filtering out suspects before taking the last date lands on the same December date in every year of this data, so the order does not change any tested number. Dividing clean-row alpha by all December AUM, the other mistake Claude warned about, does change it: 2024 drops from 1.4480% to 1.4462%, a gap of 0.0018 points, which passes the 0.0001 tolerance on a ratio but would read as a different number on a report with more decimals.

**What I changed.** I replaced Claude's date logic and kept everything else. Claude found the last date with `CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )` and filtered the fact column `snapshot_date`. The final measure uses `LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )` and filters through `dim_date`, the same line used in `Ending AUM`, `Ending Clients` and `Top 10 Client Share`. This is because all four measures then define "last snapshot" in one way, so a reader checking any of them sees one pattern, and a later change to the rule happens in one place. The two versions return identical values in all nine reconciled slices.

**A claim I refuted.** Claude closed by saying that because only a small share of rows are suspect, excluding them "should change the result only slightly at the firm level". The pandas check refutes the word "slightly". Suspect rows hold 0.12% of December 2024 AUM, yet including them raises firm alpha from +1.45% to +1.67%, a 15% relative jump. Inside Retail, where all 148 suspect rows sit, they hold 2.91% of the tier's AUM and raise its alpha from +2.40% to +7.62%. This is because one suspect row carries an alpha of 71.34 (+7,134%), so a tiny weight still moves the average. Claude's rule to exclude suspects was right; its estimate of how much they matter was wrong for the tier table, which is where a manager would read this measure.
