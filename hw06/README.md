# HW6: DAX Measure Library for AUM and Performance
MIS3060 Business Intelligence with AI | Charlie Goldsmith

Wildcat Capital manages $12,729,572,078.86 for 2,325 clients at December 2024, up 19.58% on the year, and 0.73 points of that growth came from net new money. Twelve DAX measures in `powerbi/hw06.pbix` produce those numbers, and a pandas script rebuilds every one of them from the CSVs without reading Power BI. The measure write-up and Part C answers are in `powerbi/measures.md`; Part D is in `claude/`.

## Structure

```
hw06/
├── README.md                         this file
├── powerbi/
│   ├── hw06.pbix                     posted model + _Measures table + "Measures" report page
│   ├── measures.md                   Part A documentation and Part C answers
│   ├── measures.tmdl                 every measure with format string and display folder (TMDL view script)
│   └── export_values.dax             one DAX query that returns all 95 (measure, slice, value) rows
├── scripts/
│   ├── 01_reconcile_measures.py      Part B: pandas recompute + comparison
│   └── 02_part_c_evidence.py         Part C: pandas evidence for (a)-(d)
├── reports/
│   ├── powerbi_values.csv            Power BI numbers (measure, slice, value), from export_values.dax
│   ├── measure_reconciliation.csv    95 rows: powerbi_value, pandas_value, abs_diff, match
│   └── part_c_evidence.csv           numbers quoted in Part C
├── claude/
│   ├── model_metadata.md             INFO.VIEW metadata given to Claude
│   ├── dax_session.md                Part D prompt and Claude's full response
│   └── verification.md               Part D test, debug and review
└── data/
    └── clean/                        the 8 course CSVs (not committed; copy from "Wildcat Capital Clean/")
```

## How to run

Requires Python 3.10+ and pandas 2.x (tested on pandas 2.3.3).

1. Copy the eight files from `Wildcat Capital Clean/` into `hw06/data/clean/`.
2. Build the measures in Power BI Desktop: open `hw06.pbix`, go to **TMDL view**, paste `powerbi/measures.tmdl`, and select **Apply**.
3. Export the Power BI numbers: in **DAX query view**, paste `powerbi/export_values.dax`, select **Run**, then **Copy** the result grid and paste it into `reports/powerbi_values.csv`. The script reads either the tab-separated text that Copy produces or a comma CSV from **Export data**.
4. From the `hw06` folder, run:

```
python scripts/01_reconcile_measures.py    # ~5 s -> reports/measure_reconciliation.csv
python scripts/02_part_c_evidence.py       # ~3 s -> reports/part_c_evidence.csv
```

`01_reconcile_measures.py` exits with code 1 and prints every failing row if anything does not match. A clean run prints:

```
Rows reconciled: 95
Rows matching:   95 of 95
All rows match.
```

## Part B: what the reconciliation covers

| Slice | Measures | Rows |
|---|---|---:|
| Grand total | Total Fees, Net Flows, measures 0 to 11 (14 values) | 16 |
| `year=2020` to `year=2024` | AUM (naive SUM), 1, 4, 6, 7, 8, 9, 10 | 45 |
| `client_tier=… \| year=2024` | 1, 3, 4, 7, 8, 9, 10, 11 | 27 |
| `year=2024 \| month=12` | Ending AUM, Ending AUM PM, AUM MoM % | 3 |
| Part C helpers | SUMX by client, alpha incl. suspects, simple mean alpha (total); Effective Fee Rate (2024) | 4 |
| **Total** | | **95** |

Tolerance is 0.01 for currency and counts, and 0.0001 for ratios and bps. `Alpha Signal` must match as text, and a blank on both sides counts as a match (2020 `Ending AUM LY`, `AUM YoY %` and `Organic Growth Rate`).

The pandas side rebuilds each filter context instead of copying DAX. `LASTNONBLANK` becomes "the latest `snapshot_date` inside the window", `SAMEPERIODLASTYEAR` and `DATEADD` become the window shifted back and clipped to the 2020 to 2024 range of `dim_date` (DAX only returns dates that exist in the date column), and `client_tier` comes from a many-to-one join to `dim_client`, the same path the relationship uses. `AUM (naive SUM)` and its pandas twin both return $566,681,084,542.48 at the grand total and $135,459,843,783.73 for 2024, so the two tools make the same mistake.

**Mismatches and fixes.** The pandas logic was checked against a full synthetic export before the Power BI run: one wrong value and one deleted row both failed as expected, and a correct file matched 95 of 95. *(Record here any row that failed on the real Power BI export, which side was wrong, and the fix.)*

## Claude Code review findings

Claude drafted both scripts in this session, and a Claude Code review pass read `01_reconcile_measures.py` before the commit. These are the issues it raised and what changed.

| Flagged | What I did |
|---|---|
| `read_powerbi()` assumed a comma CSV with plain headers. **Copy** in DAX query view pastes tab-separated text with headers `[measure]`, `[slice]`, `[value]`, so a pasted file would fail the column check on the first line. | The reader now picks a tab or comma from the header line, strips the square brackets, and drops a UTF-8 byte-order mark. Tested with a tab-separated, bracket-header file. |
| The "missing from powerbi_values.csv" count included any row where Power BI was blank and pandas was not, so a wrong blank was reported as a missing row. | Missing rows are now tracked by key lookup, separate from value mismatches. Tested by deleting one row and corrupting another: the script reports one missing row and two failed rows. |
| `Top 10 Client Share` in pandas ranked clients at the slice's last date, while the DAX hint ranks on `[Ending AUM]` per client, which uses each client's own last date. | Kept the fixed-date ranking in both tools and documented why in `measures.md`. Checked in pandas that both rankings pick the same 10 clients at the total, in every year and in every 2024 tier. |
| Grand-total `Organic Growth Rate` divides five years of flows (2020 to 2024) by the December 2023 balance. | No code change: the DAX does the same, so the two match. `measures.md` says to read this measure by year. |

## Power BI notes

- `hw06.pbix` is a copy of the posted `Wildcat_Star_Model.pbix` saved on the Apporto virtual desktop. Power BI on Apporto warns that the posted file came from a newer Desktop version; the model opens and all eight tables load.
- All measures sit in `_Measures`, grouped in display folders: `0 Base`, `1 AUM`, `2 Growth`, `3 Revenue and flows`, `4 Performance`, `8 Part C checks`, and `9 Do not use` for the naive SUM.
- The **Measures** page holds four cards (Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share), a table by `dim_date[year]`, and a table by `dim_client[client_tier]` with a visual-level filter `dim_date[year] = 2024`.
