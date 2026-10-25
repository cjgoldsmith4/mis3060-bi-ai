# HW4: Cleaning the Wildcat Capital Data
MIS3060 Business Intelligence with AI | Charlie Goldsmith

Three Python programs audit, clean, and validate the eight-table Wildcat Capital extract. The clean tables pass all 13 relationship checks, every column rule, and every cross-table reconciliation; the business summary is in `reports/cleaning_report.md`.

## Structure

```
hw04/
├── README.md                    this file
├── decision_log.md              Part B: one entry per issue (26), written before the cleaning code
├── scripts/
│   ├── dq_common.py             shared schema, strict parsers, row rules, cross-table rules
│   ├── 01_profile.py            Part A: generic profiler + four check groups
│   ├── 02_clean.py              Part C: asserted cleaning steps C1-C8 + audit trail
│   └── 03_validate.py           Part D: check_referential_integrity(), rules, reconciliations, IQR, scorecard
├── data/
│   ├── raw/                     the 8 source CSVs (not committed; copy from "Wildcat Capital/")
│   ├── clean/                   8 clean CSVs + README_clean.md
│   └── audit/                   cleaning_log.csv, value_changes.csv, quarantine_*.csv, row_count_proof.csv
└── reports/
    ├── profile_raw.csv          one row per table-column (75 rows)
    ├── dq_summary_raw.csv       159 findings tagged ERROR / WARN / INFO
    ├── ri_results.csv           13 relationships, raw and clean
    ├── rule_checks.csv          every row rule, raw and clean
    ├── reconciliations.csv      recomputed vs stored values, raw and clean
    ├── outliers_iqr.csv         IQR fences and flag counts
    ├── data_quality_scorecard.csv
    └── cleaning_report.md       Part E: report for the portfolio committee
```

## How to run

Requires Python 3.10+ and pandas 2.x (tested on pandas 2.2.3 and 3.0.5; outputs are identical).

1. Copy the eight files listed in the assignment from `Wildcat Capital/` into `hw04/data/raw/`. Use these names: `dim_advisor.csv`, `dim_client.csv`, `dim_date.csv`, `dim_security.csv`, `dim_benchmark.csv`, `fact_fees.csv`, `fact_portfolio_snapshot.csv`, `fact_transactions.csv`.
2. From the `hw04` folder, run the scripts in order:

```
python scripts/01_profile.py     # ~30 s  -> reports/profile_raw.csv, dq_summary_raw.csv
python scripts/02_clean.py       # ~5 s   -> data/clean/, data/audit/
python scripts/03_validate.py    # ~35 s  -> reports/ri_results.csv ... data_quality_scorecard.csv
```

`01_profile.py some_file.csv` profiles any other CSV with an inferred type per column. Every script reads files as text (`dtype=str, keep_default_na=False`). `02_clean.py` and `03_validate.py` stop on the first failed `assert`.

## Results in one table

| Measure | Raw | Clean |
|---|---:|---:|
| fact_transactions referential match | 81.95% | 100.00% |
| fact_transactions type validity | 91.73% | 100.00% |
| dim_client rule pass | 96.91% | 100.00% |
| fact_portfolio_snapshot type validity | 99.98% | 100.00% |
| Rows quarantined | | 225 (25 clients, 200 transactions) |
| Cell values changed | | 198,388 |
| Flag columns added | | 6 |

## Claude Code review findings

Claude drafted each script and a Claude Code review pass checked it before each commit. These are the issues the review raised and what changed in response.

| Script | Claude Code flagged | What I did |
|---|---|---|
| 02_clean.py (C1) | The first draft picked the "real" client in each duplicate pair as the one with the longer last name. Two pairs have an extra letter in the copy ("Leen" vs "Lee", "Pacen" vs "Pace"), so the rule chose two real clients for removal. The fact-reference assert stopped the run: 96 fee, 102 snapshot and 243 transaction rows pointed at them. | Changed the rule to keep the copy the fact tables use, and added asserts that each pair has one used and one unused side and differs by one trailing letter. |
| 02_clean.py (C7) | Storing the converted percent (9.28% -> 0.0928) left a rounding gap of up to 0.00005, which broke active_alpha = return - benchmark on 284 rows. The scorecard showed snapshot rule pass falling from 100% to 99.78% after cleaning. | Stored benchmark_return_ytd + active_alpha_ytd instead, after asserting it agrees with the percent string within 0.00005 on all 300 rows. Added an assert that the alpha identity holds on every row. |
| 02_clean.py (C6) | The merge that finds each orphan's original transaction could return two matches for one orphan, which would duplicate rows in the quarantine file. | Added `drop_duplicates("txn_id")`; the raw = clean + quarantined assert also guards this. |
| 01_profile.py | The "return_ytd > 100%" check stripped the % sign without dividing by 100, so "9.28%" counted as 928%. It reported 1,148 rows instead of 977. | Divided percent rows by 100 before the comparison. |
| 01_profile.py | The mixed-format check flagged every text category (e.g. "Balanced" vs "Moderately Aggressive") and every negative number as a format problem, which buried the real findings. | Dropped the sign from value shapes and limited the check to numeric, date and boolean columns. Allowed-value rules still catch text format problems such as full state names. |
| dq_common.py | Cross-table check names described the passing condition ("on a trading day") while the counts measured failures. | Renamed all twelve checks to describe the defect being counted. |
| 02_clean.py, 03_validate.py | Unused `numpy` imports; `isin(dict.keys())` may not work across pandas versions. | Removed the imports; passed a list to `isin`. Re-ran all three scripts on pandas 2.2.3 and 3.0.5 and confirmed byte-identical outputs. |
| 03_validate.py | The clean-stage assert skipped the signed shares x price reconciliation. | Removed the exception: every clean reconciliation must pass with zero unparseable rows. |

## Commits

One commit per part, each message stating what changed (see `git log -- hw04`).
