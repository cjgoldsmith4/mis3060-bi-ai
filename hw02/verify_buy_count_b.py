# =============================================================================
# Script:    verify_buy_count_b.py
# Purpose:   Cross-validation Prompt B - count the total rows in
#            fact_transactions.csv, then subtract the count of rows where
#            txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee.
#            The remainder should equal the Buy count, verified independently
#            of directly filtering for txn_type == 'Buy' (see Prompt A).
# Dataset:   data/raw/fact_transactions.csv
# Author:    Charlie
# Course:    MIS3060 Business Intelligence with AI, Villanova University
#
# Run from the repository root:   python hw02/verify_buy_count_b.py
# =============================================================================

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "raw" / "fact_transactions.csv"

df = pd.read_csv(DATA_PATH)

total_rows = len(df)
non_buy_types = ["Sell", "Deposit", "Withdrawal", "Dividend", "Advisory Fee"]
non_buy_count = df["txn_type"].isin(non_buy_types).sum()

buy_count_by_subtraction = total_rows - non_buy_count

print(f"Total rows:                         {total_rows:,}")
print(f"Rows where txn_type is one of {non_buy_types}: {non_buy_count:,}")
print(f"Buy count by subtraction (total - non-Buy): {buy_count_by_subtraction:,}")
