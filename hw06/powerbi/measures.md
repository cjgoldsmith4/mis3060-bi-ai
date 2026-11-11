# HW6 Measure Library: AUM and Performance
MIS3060 Business Intelligence with AI | Charlie Goldsmith

Every measure lives in the `_Measures` table of `hw06.pbix`. The full model script, with format strings and display folders, is in `measures.tmdl`; paste it into TMDL view and select **Apply** to rebuild the table. Every value below comes from `reports/measure_reconciliation.csv`, where the Power BI number and an independent pandas number sit side by side.

Three additivity patterns appear in this library, matching the classes from Assignment 5 Part C:

- **SUM:** the column is additive, so a plain SUM is correct in every filter context (`fact_fees[amount]`, `fact_transactions[amount]`).
- **Last balance:** the column is semi-additive over time, so the measure sums across clients but keeps only the last snapshot date in the filter (`aum`).
- **Recompute and weight:** the column is a ratio or a non-additive figure, so the measure rebuilds it from its parts or weights it by `aum` (`active_alpha_ytd`, fee yield, growth rates).

The last-snapshot logic used by measures 1, 2, 9 and 11 is the same line each time:

```DAX
LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )
```

It walks the dates left in the filter context and returns the latest one that has a snapshot. With no filter that date is 2024-12-01. Inside a 2024 tier filter it is still 2024-12-01, and inside a single client it is that client's own last month.

---

## Part A: Measure library

### Base measures

**Total Fees** · SUM · `$#,0.00`
```DAX
Total Fees = SUM ( fact_fees[amount] )
```
Fee revenue charged in the filter context. For a Wildcat manager, this is the top line: $204,675,583.12 across 2020 to 2024.

**Net Flows** · SUM · `$#,0.00`
```DAX
Net Flows =
CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
    - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
```
Deposits minus withdrawals. For a manager, this is new money clients brought in, net of money they took out: $327,439,026.62 across 2020 to 2024.

### 0. AUM (naive SUM) · WRONG ON PURPOSE · `$#,0.00`
```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
This measure adds every monthly balance in the filter, so it never belongs on a report. It sits in the display folder `9 Do not use`. With no filters it returns $566,681,084,542.48, which is 44.5 times the real $12,729,572,078.86 the firm manages. The pandas twin (`snap["aum"].sum()`) returns the same wrong number, which shows the error comes from the pattern and not from the tool.

### 1. Ending AUM · Last balance · `$#,0.00`
```DAX
Ending AUM =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )
RETURN
    CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot )
```
The balance at the last snapshot in the filter. For a manager, this answers "How much do we manage?": $12,729,572,078.86 at December 2024.

### 2. Ending Clients · Last balance (count) · `#,0`
```DAX
Ending Clients =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )
RETURN
    CALCULATE ( DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ), LastSnapshot )
```
Clients holding a balance at that same snapshot. For a manager, this is the current book of 2,325 clients, which leaves out the 175 who left before December 2024.

### 3. Avg AUM per Client · Recompute · `$#,0.00`
```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
Ending AUM divided by Ending Clients, rebuilt from both parts in every context. For a manager, this sizes the typical relationship: $5,475,084.77 firm-wide, $382,677.55 for Retail and $39,539,337.81 for UHNW.

### 4. Ending AUM LY and AUM YoY % · Last balance, then recompute · `$#,0.00` and `0.00%`
```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )

AUM YoY % =
VAR CurrentAUM = [Ending AUM]
VAR PriorAUM = [Ending AUM LY]
RETURN
    IF ( ISBLANK ( CurrentAUM ) || ISBLANK ( PriorAUM ), BLANK (), DIVIDE ( CurrentAUM - PriorAUM, PriorAUM ) )
```
The balance one year earlier, and the growth from it. For a manager, this is the headline growth figure: 19.58% in 2024, from $10,644,971,737.00 to $12,729,572,078.86. 2020 shows blank because `dim_date` starts in 2020. The `ISBLANK` guard stops a context with no current balance from showing a false -100%.

### 5. Ending AUM PM and AUM MoM % · Last balance, then recompute · `$#,0.00` and `0.00%`
```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )

AUM MoM % =
VAR CurrentAUM = [Ending AUM]
VAR PriorAUM = [Ending AUM PM]
RETURN
    IF ( ISBLANK ( CurrentAUM ) || ISBLANK ( PriorAUM ), BLANK (), DIVIDE ( CurrentAUM - PriorAUM, PriorAUM ) )
```
The balance one month earlier, and the growth from it. For a manager, this tracks the latest month: December 2024 grew 4.25%, from $12,211,162,447.94 in November.

### 6. Avg Monthly AUM · Recompute (average of balances) · `$#,0.00`
```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
The sum of balances divided by the number of months that produced them. For a manager, this is the balance that earned fees across the period: $11,288,320,315.31 in 2024, $1.44 billion below the December balance because AUM grew through the year.

### 7. Fee Yield (bps) · Recompute across two fact tables · `#,0.00`
```DAX
Fee Yield (bps) = DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```
Annualized fees per dollar of AUM. `[Total Fees]` comes from fact_fees and `SUM(aum)` comes from fact_portfolio_snapshot; both respond to the same `dim_date` and `dim_client` filters, so they always cover the same months and clients. The summed monthly balances in the denominator pair with the summed monthly fees in the numerator, and the ×12 turns monthly fees into an annual rate. For a manager, this is pricing: 43.15 bps in 2024, ranging from 82.81 bps on Retail to 36.14 bps on UHNW.

### 8. Organic Growth Rate · Recompute · `0.00%`
```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
Net new money as a share of last year's ending balance. For a manager, this separates growth the firm won from growth the market gave: 0.73% in 2024, against 19.58% total growth. At the grand total the numerator holds five years of flows and the denominator holds the December 2023 balance, so read this measure by year.

### 9. AUM-Weighted Alpha · Recompute and weight · `0.00%`
```DAX
AUM-Weighted Alpha =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnapshot,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```
Year-to-date alpha at the last snapshot, weighted by each client's balance, with suspect returns removed. For a manager, this is the dollar-weighted answer to "Did we beat the benchmarks?": +1.45% for 2024, and +2.85% for 2022.

### 10. Alpha Signal · Text from measure 9
```DAX
Alpha Signal =
VAR Alpha = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Alpha ), BLANK (),
        Alpha >= 0.02, "Outperforming",
        Alpha <= -0.02, "Lagging",
        "In line"
    )
```
A label for measure 9: "Outperforming" at +2% or more, "Lagging" at -2% or less, blank when alpha is blank. For a manager, this flags where to look: 2022 and the 2024 Retail tier read "Outperforming", and every other year and tier reads "In line".

### 11. Top 10 Client Share · Last balance with TOPN · `0.00%`
```DAX
Top 10 Client Share =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ) ) )
VAR TopClients =
    TOPN (
        10,
        VALUES ( dim_client[client_id] ),
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot ),
        DESC
    )
RETURN
    DIVIDE (
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot, TopClients ),
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot )
    )
```
The share of Ending AUM held by the 10 largest clients inside the current filter. `LastSnapshot` is fixed once in the outer context, so every client is ranked on the same date as the denominator. Ranking on `[Ending AUM]` per client would rank a departed client on an older balance; the result here is the same either way (checked in pandas for the total, each year and each 2024 tier), but the fixed date keeps the numerator and denominator on one date by construction. For a manager, this is concentration risk: the top 10 clients hold 6.16% of the firm, and 8.13% of UHNW.

### Part C helper measures (display folder `8 Part C checks`)

| Measure | DAX | Used in |
|---|---|---|
| Ending AUM SUMX by Client | `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` | (a) |
| Effective Fee Rate (bps) | `DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_fees[aum_basis] ) )` | (b) |
| AUM-Weighted Alpha incl. Suspects | measure 9 without the `is_return_suspect = 0` filter | (c) |
| Simple Mean Alpha | `AVERAGE ( active_alpha_ytd )` on the same rows as measure 9 | (c) |

### Results at a glance

| Measure | Grand total | 2024 | HNW 2024 | Retail 2024 | UHNW 2024 |
|---|---:|---:|---:|---:|---:|
| Ending AUM | $12,729,572,078.86 | $12,729,572,078.86 | $2,548,521,154.33 | $533,452,497.89 | $9,647,598,426.64 |
| Avg AUM per Client | $5,475,084.77 | | $3,709,637.78 | $382,677.55 | $39,539,337.81 |
| AUM YoY % | 19.58% | 19.58% | 19.64% | 19.13% | 19.59% |
| Fee Yield (bps) | 43.34 | 43.15 | 61.39 | 82.81 | 36.14 |
| Organic Growth Rate | 3.08% | 0.73% | 1.18% | 9.87% | 0.10% |
| AUM-Weighted Alpha | 1.45% | 1.45% | 1.40% | 2.40% | 1.41% |
| Alpha Signal | In line | In line | In line | Outperforming | In line |
| Top 10 Client Share | 6.16% | | 3.14% | 1.83% | 8.13% |

| Year | Ending AUM | AUM YoY % | Avg Monthly AUM | Fee Yield (bps) | Organic Growth | Weighted Alpha | Signal |
|---|---:|---:|---:|---:|---:|---:|---|
| 2020 | $8,130,190,789.37 | (blank) | $7,379,299,895.30 | 43.33 | (blank) | -0.68% | In line |
| 2021 | $10,010,301,949.11 | 23.13% | $9,135,353,821.89 | 42.96 | 0.62% | -0.16% | In line |
| 2022 | $9,308,159,286.53 | -7.01% | $9,591,147,070.37 | 44.17 | 0.75% | 2.85% | Outperforming |
| 2023 | $10,644,971,737.00 | 14.36% | $9,829,302,609.00 | 43.11 | 0.83% | 1.77% | In line |
| 2024 | $12,729,572,078.86 | 19.58% | $11,288,320,315.31 | 43.15 | 0.73% | 1.45% | In line |

---

## Part C: Design questions

### (a) `Ending AUM` vs `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )`

`Ending AUM` answers "How much do we manage today?", and the SUMX version overstates it by $419,725,634.94. This is because SUMX evaluates `[Ending AUM]` once per client, and inside one client `LASTNONBLANK` finds that client's own last snapshot instead of the firm's. With no filters, `Ending AUM` returns $12,729,572,078.86, the total at 2024-12-01. The SUMX version returns $13,149,297,713.80. The $419,725,634.94 gap equals the last balances of the 175 clients whose final snapshot falls between 2022-12-01 and 2023-11-01. Those clients have left Wildcat, so SUMX adds money the firm no longer manages. The same pattern shows up in Ending Clients, which counts 2,325 clients at December 2024, while the client table holds 2,500.

### (b) `Fee Yield (bps)` below the ICE 9 `Effective Fee Rate (bps)` for 2024

`Fee Yield (bps)` is 43.15 bps for 2024 and the ICE 9 `Effective Fee Rate (bps)` is 45.53 bps, because fact_fees has no fee row for 5.22% of the 2024 AUM that fact_portfolio_snapshot holds. This is because the two measures share a numerator and differ in the denominator. Effective Fee Rate divides fees by `fact_fees[aum_basis]`, which only exists for client-months that were billed. Fee Yield divides the same fees by `fact_portfolio_snapshot[aum]`, which covers every client-month with a balance. The pandas join in `02_part_c_evidence.py` shows the gap:

- 1,684 of the 27,900 snapshot months in 2024 have no matching fee row, and those months hold 5.22% of 2024 AUM.
- Where a fee row does exist, `aum_basis` equals `aum` on every row, and 0 fee rows lack a snapshot.
- The ratio 43.1543 ÷ 45.5323 = 0.947774 equals 1 − 0.052226 exactly, so the unbilled months explain the whole difference.

The data limitation is incomplete fee coverage. 7,350 of 129,547 client-months (5.67%) across 2020 to 2024 have a balance but no fee, spread across 2,261 of 2,500 clients, every year (4.85% to 6.22%) and every tier (5.09% to 5.95%). The data cannot say whether Wildcat waived those fees, billed them late, or lost the records. Because the gaps fall evenly, they look like missing records more than a pricing policy, which means Effective Fee Rate describes the price on billed accounts and Fee Yield describes what the firm earned on everything it managed.

### (c) Reading `AUM-Weighted Alpha` at the last snapshot, without suspects

`AUM-Weighted Alpha` must be read at the last snapshot because `active_alpha_ytd` is cumulative from January. This is because each month's value already contains every earlier month of the year, so a January value covers one month and a December value covers twelve. Pooling all twelve 2024 months gives +0.32%, which averages a set of partial-year figures and describes no real period. The December 2024 rows give +1.45%, which is the full-year result.

Suspect rows must be excluded because their alpha values are not real returns. This is because the 148 suspect rows at December 2024 reach an alpha of 71.337772 (+7,133.78%), while every non-suspect row stays between -49.82% and +49.53%. The suspect rows hold 0.12% of December AUM, yet they move the weighted figure:

| Same rows (December 2024) | Value |
|---|---:|
| AUM-weighted alpha, suspects excluded (measure 9) | +1.45% |
| AUM-weighted alpha, suspects included | +1.67% |
| Simple mean alpha, suspects excluded | +0.88% |

The simple mean is 0.57 points below the weighted figure. This is because larger accounts beat their benchmarks by more than small accounts did, and a simple mean gives a $300,000 Retail account the same vote as a $40 million UHNW account. Measure 9 weights by `aum`, so it reports alpha on the dollars Wildcat manages.

### (d) Organic Growth Rate by client tier, 2024

Wildcat's 2024 growth came from markets, and the only tier winning meaningful new money is Retail. This is because Organic Growth Rate sits far below AUM YoY % in every tier:

| Tier | Share of Ending AUM | Net Flows 2024 | Organic Growth Rate | AUM YoY % | YoY minus organic |
|---|---:|---:|---:|---:|---:|
| HNW | 20.0% | $25,227,406.26 | 1.18% | 19.64% | 18.46 pts |
| Retail | 4.2% | $44,184,047.61 | 9.87% | 19.13% | 9.26 pts |
| UHNW | 75.8% | $8,101,601.39 | 0.10% | 19.59% | 19.49 pts |

All three tiers grew about 19% for the year. Retail brought in more net new money than HNW and UHNW combined, and it funded about half of its own growth with flows. UHNW holds three quarters of the firm's AUM but added $8.1 million of net new money on an $8.07 billion starting balance, so its 19.59% growth is almost all market return.

Organic Growth Rate does not tell you three things. First, the gap between YoY and organic is not pure market return: it also absorbs dividends kept in the account, fee debits and balances lost when clients leave, and the model has no column that separates them. Second, it does not say whether flows came from new clients or existing ones, or whether the firm lost clients during the year. Third, it says nothing about profit: Retail's 9.87% organic rate sits on the firm's smallest tier, but Retail also pays the highest Fee Yield (82.81 bps vs 36.14 bps for UHNW), so a dollar of Retail growth earns more than twice the fee of a UHNW dollar.
