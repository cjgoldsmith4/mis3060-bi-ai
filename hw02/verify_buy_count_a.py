# =============================================================================
# Script:    verify_buy_count_a.py
# Purpose:   Cross-validation Prompt A - count rows in fact_transactions.csv
#            where txn_type equals exactly 'Buy'
# Dataset:   data/raw/fact_transactions.csv
# Author:    Charlie
# Course:    MIS3060 Business Intelligence with AI, Villanova University
#
# Run from the repository root:   python hw02/verify_buy_count_a.py
# =============================================================================

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "raw" / "fact_transactions.csv"

df = pd.read_csv(DATA_PATH)

buy_count = (df["txn_type"] == "Buy").sum()

print(f"Rows where txn_type == 'Buy': {buy_count:,}")
