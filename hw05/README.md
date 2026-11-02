# HW5: Modeling the Wildcat Capital Data as a Star Schema in Power BI
MIS3060 Business Intelligence with AI | Charlie Goldsmith

The eight clean Wildcat Capital tables form a star with three fact tables, five dimensions and 11 active relationships. A Python check script proves every primary key, foreign key and grain before the Power BI build; the design write-up for Parts A, B, C, E and F is in `star_design.md`.

## Structure

```
hw05/
├── README.md                  this file
├── star_design.md             Parts A, B, C, E and F, plus the Part D relationship table
├── scripts/
│   └── 01_star_checks.py      Parts A-C: asserts for keys, grains and measure behaviour
├── reports/
│   ├── row_counts.csv         rows and columns per table vs the handout (8 of 8 match)
│   ├── pk_checks.csv          8 primary keys: unique, never blank, whole numbers
│   ├── fk_checks.csv          13 foreign keys: blanks, orphans, match rate
│   ├── grain_checks.csv       fact grains, plus the transaction business key that repeats
│   ├── measure_checks.csv     the numbers behind each additive / semi / non-additive call
│   └── powerbi_types.csv      Power Query type for all 77 columns (Part D)
├── powerbi/
│   ├── build_steps.md         the click-by-click Part D build used in Apporto
│   ├── hw05.pbix              Part D: the saved model
│   └── model_view.png         Part D: Model view, every table and relationship visible
└── data/
    └── clean/                 the 8 course CSVs (not committed; copy from "Wildcat Capital Clean/")
```

## How to run

Requires Python 3.10+ and pandas 2.x (tested on pandas 2.3.3 and 3.0.5).

1. Copy the eight files from `Wildcat Capital Clean/` into `hw05/data/clean/` with these names: `dim_advisor.csv`, `dim_benchmark.csv`, `dim_client.csv`, `dim_date.csv`, `dim_security.csv`, `fact_fees.csv`, `fact_portfolio_snapshot.csv`, `fact_transactions.csv`.
2. From the `hw05` folder, run:

```
python scripts/01_star_checks.py     # ~5 s -> reports/*.csv
```

The script reads every file as text (`dtype=str, keep_default_na=False`) so a key such as `45.0` never matches `45` by accident, and it stops on the first failed `assert`. A clean run prints:

```
Row counts match the handout: 8 of 8 tables
Primary keys unique: 8 of 8
Foreign keys with zero orphans: 13 of 13
Blank security_id rows (cash only): 101528
Fact rows whose advisor differs from dim_client: 0
Fact grains unique: 3 of 3; client + date + type + security repeats on 622 transaction rows
2024 AUM summed across months overstates Dec 2024 AUM by 10.64x
All asserts passed.
```

3. Build the Power BI model in Power BI Desktop on the Apporto virtual desktop with `powerbi/build_steps.md`, and save it as `powerbi/hw05.pbix`.

## Results in one table

| Check | Result |
|---|---:|
| Tables matching handout row and column counts | 8 of 8 |
| Primary keys unique and never blank | 8 of 8 |
| Foreign keys with zero orphans | 13 of 13 |
| Blank `security_id` rows (all Deposit, Withdrawal, Advisory Fee) | 101,528 |
| Fact rows whose `advisor_id` differs from dim_client | 0 of 550,316 |
| Active / inactive relationships in the model | 11 / 2 |
| 2024 AUM summed across months vs December 2024 AUM | 10.64x |

## Claude Code review findings

Claude drafted the script and a Claude Code review pass checked it before the commit. These are the issues the review raised and what changed in response.

| Script | Claude Code flagged | What I did |
|---|---|---|
| 01_star_checks.py (Part B) | The first draft proved the transaction grain by checking `txn_id` for duplicates. `txn_id` is the primary key, so that check repeated Part A and said nothing about the grain. | Added a check on the business columns `client_id + txn_date + txn_type + security_id`. It repeats on 622 same-day repeat trades, which shows `txn_id` is the only column set that identifies a transaction. The Part B sentence now says so. |
| 01_star_checks.py (Part A) | The foreign-key match rate divided by the count of non-blank keys, which would crash with a division by zero on a key column that is blank on every row. | Guarded the division and reported a match rate of 1.0 when no keys need checking. |
| 01_star_checks.py (Part B) | The draft asserted that fee and snapshot dates fall on the first of the month but never compared them with `dim_date[is_month_end]`, which flags the last day. A month-end filter in Power BI would remove every fee and snapshot row. | Added an assert that no fee or snapshot date is a month-end date, and documented the effect in Part E (c) and Part F question 2. |
| 01_star_checks.py (Part C) | Fee dollars appear twice: `fact_fees[amount]` and the Advisory Fee rows in `fact_transactions`. The draft never compared them, and Part F needed to say which one answers a fee question. | Added the comparison to `measure_checks.csv`. The debits exceed the charges by $59,034,154.01, so Part F uses fact_fees for fee revenue. |

## Part D note

`hw05.pbix` and `model_view.png` come from Power BI Desktop on the Apporto virtual desktop. If the `.pbix` exceeds GitHub's 100 MB limit, it goes to Brightspace instead and this line will say so.

## Commits

See `git log -- hw05`.
