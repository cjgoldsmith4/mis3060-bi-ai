# Part D: Claude session for measure 9, `AUM-Weighted Alpha`
MIS3060 Business Intelligence with AI | Charlie Goldsmith

Workflow: **Draft → Test → Debug → Review**. The prompt below went to Claude with the full contents of `model_metadata.md` pasted where marked. Claude's response is copied in full after it. The testing, debugging and review steps are in `verification.md`.

---

## Prompt

> I'm building a DAX measure in Power BI Desktop for a wealth-management star schema (Wildcat Capital). The model metadata from INFO.VIEW.TABLES, INFO.VIEW.COLUMNS and INFO.VIEW.RELATIONSHIPS is below.
>
> *[INFO.VIEW.TABLES, INFO.VIEW.COLUMNS and INFO.VIEW.RELATIONSHIPS output from `claude/model_metadata.md` pasted here: tables, columns with data types, and relationships with cardinality and direction]*
>
> **What the metadata cannot tell you:**
>
> 1. **Grain of `fact_portfolio_snapshot`:** one row = one client's account balance and year-to-date performance for one month, dated on the first of the month (`snapshot_date` = 2020-01-01, 2020-02-01, …, 2024-12-01). 60 snapshot dates, 129,547 rows. `client_id + snapshot_date` is unique. Clients who leave stop getting snapshots, so the client count at each date changes.
> 2. **`aum` is a balance (semi-additive).** It sums across clients for one date, never across dates.
> 3. **`active_alpha_ytd` is year-to-date** (`return_ytd - benchmark_return_ytd`), stored as a decimal (0.02 = 2%). The December value covers the whole year; a January value covers one month. It is non-additive.
> 4. **`is_return_suspect`** is 1 on 3,875 rows whose returns failed a data-quality check. Those rows must be excluded.
> 5. The assignment says `dim_date` is marked as the date table on `dim_date[date]`, and `fact_portfolio_snapshot[snapshot_date]` joins to it. Filters reach the snapshot table through `dim_date`, `dim_client` (e.g. `client_tier`), `dim_advisor` and `dim_benchmark`. All relationships are single direction.
>
> **Business definition (from the assignment):** `AUM-Weighted Alpha` = `active_alpha_ytd` weighted by `aum`, at the last snapshot in the current filter context, excluding `is_return_suspect = 1`.
>
> **Please give me:**
> 1. The measure, for a measures table named `_Measures`.
> 2. An explanation of its filter context: what "last snapshot" resolves to with no filter, with `dim_date[year] = 2022`, and in a table by `dim_client[client_tier]` filtered to 2024, and what happens to the suspect filter inside CALCULATE.
> 3. A DAX test query I can run in DAX query view to check it by year and by tier for 2024.
>
> It will be reconciled to pandas, so tell me anything that could make the two disagree.

---

## Claude's response

Here's a measure that follows your definition exactly, plus the filter-context walkthrough and a test query.

### 1. The measure

```DAX
AUM-Weighted Alpha =
VAR LastSnapshotDate =
    CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX (
                fact_portfolio_snapshot,
                fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd]
            ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        fact_portfolio_snapshot[snapshot_date] = LastSnapshotDate,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```

Format it as a percentage (`0.00%`), since `active_alpha_ytd` is stored as a decimal.

**Why this shape:**

- **`LastSnapshotDate`** is computed *before* the suspect filter is applied, so "last snapshot" means the last month that has any balance in the current context, not the last month that happens to have clean rows. That matches "at the last snapshot in the current filter context, excluding suspects": you pick the date first, then drop bad rows on that date.
- **The weighted average is a ratio of sums**, Σ(aum × alpha) ÷ Σ(aum), rebuilt in every context. That is the recompute-and-weight pattern for a non-additive column. Averaging `active_alpha_ytd` directly would give a $300K account the same say as a $40M account.
- **`SUMX` iterates the snapshot rows that survive both filters.** Both the numerator and the denominator see the same rows, so suspect rows drop out of the weights too, not only out of the numerator.
- **`DIVIDE`** returns BLANK if no rows survive (for example a single client whose only last-month row is suspect), which keeps a downstream label measure from misfiring.

### 2. Filter context

**No filter (card visual).** `CALCULATE ( MAX ( snapshot_date ) )` sees every snapshot, so `LastSnapshotDate` = 2024-12-01. The outer CALCULATE then keeps only December 2024 rows with `is_return_suspect = 0` and returns the weighted alpha for the full year 2024. So **the card and a 2024 row in a year table should show the same number**.

**`dim_date[year] = 2022`.** The year filter flows from `dim_date` to the snapshot table through the `snapshot_date` relationship, so MAX finds 2022-12-01. The outer CALCULATE adds a filter on the fact column `snapshot_date`; it does not remove the `dim_date[year]` filter (that one sits on a different column), and since 2022-12-01 is inside 2022 the two filters agree. Result: full-year 2022 alpha.

**Table by `dim_client[client_tier]`, filtered to 2024.** Each row has two filters: the tier (through `dim_client` → `client_id`) and the year. MAX runs inside both, so each tier gets its own last date. In this data every tier has clients in December 2024, so all three resolve to 2024-12-01. The **total row** of that table ignores the tier filter and equals the 2024 firm-wide figure; it is a fresh weighted average over all tiers, not an average of the three tier values.

**The suspect filter.** `fact_portfolio_snapshot[is_return_suspect] = 0` is a boolean filter, which CALCULATE expands to `FILTER ( ALL ( fact_portfolio_snapshot[is_return_suspect] ), … = 0 )`. It replaces any existing filter on that one column and leaves every other filter (date, tier, advisor) in place. If someone puts `is_return_suspect` in a slicer and selects 1, the measure overrides it and still shows clean rows only. That's intentional here, but worth knowing.

**Grain check.** `client_id + snapshot_date` is unique, so on one date each client appears once and Σ(aum) is that date's real total. No double counting.

### 3. Test query

```DAX
// By year: last snapshot date, row counts and the measure
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[year],
    "Last snapshot", CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) ),
    "Rows at last snapshot",
        VAR d = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
        RETURN CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ), fact_portfolio_snapshot[snapshot_date] = d ),
    "Suspect rows excluded",
        VAR d = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
        RETURN CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ), fact_portfolio_snapshot[snapshot_date] = d, fact_portfolio_snapshot[is_return_suspect] = 1 ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)
ORDER BY dim_date[year]

// By client tier for 2024
EVALUATE
SUMMARIZECOLUMNS (
    dim_client[client_tier],
    TREATAS ( { 2024 }, dim_date[year] ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)

// Grand total (should equal the 2024 row above)
EVALUATE
ROW ( "AUM-Weighted Alpha (no filter)", [AUM-Weighted Alpha] )
```

DAX query view shows each EVALUATE as its own result tab.

### What could make Power BI and pandas disagree

1. **Picking the date after dropping suspects.** If pandas filters `is_return_suspect == 0` first and then takes `max(snapshot_date)`, it could land on a different date in a small slice. Take the max date first, then filter, same order as the measure.
2. **Weighting by all rows vs clean rows.** The denominator must be Σ(aum) over the *clean* rows on the last date. If pandas divides by total December AUM including suspects, it will come out slightly low.
3. **Using `return_ytd` minus `benchmark_return_ytd` instead of the stored `active_alpha_ytd`.** They match to about 1e-6, which is fine at a 0.0001 tolerance, but use the stored column to be safe.
4. **Tier membership.** Pandas has to get `client_tier` from `dim_client` by joining on `client_id`, the same path the model uses.
5. **Pooling months.** Make sure the pandas side does not average all twelve 2024 months; that would mix year-to-date figures of different lengths and give a much smaller number.

Since only a small share of rows are flagged suspect, excluding them should change the result only slightly at the firm level, but it's still the right call: a few extreme values can distort a weighted figure if the accounts are large.
