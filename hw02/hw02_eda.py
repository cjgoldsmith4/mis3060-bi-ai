# =============================================================================
# Script:    hw02_eda.py
# Purpose:   Exploratory data analysis (EDA) of the Wildcat Capital
#            transaction portfolio
# Dataset:   data/raw/fact_transactions.csv
#            (client transactions, January 2020 - December 2024)
# Author:    Charlie
# Course:    MIS3060 Business Intelligence with AI, Villanova University
# Generated: 2026-09-21 (with Claude, from hw02/specification.md)
#
# Run from the repository root:   python hw02/hw02_eda.py
# Outputs:   hw02/hw02_profile.txt
#            hw02/charts/hist_amount.png
#            hw02/charts/box_amount_by_type.png
#            hw02/charts/scatter_shares_amount.png
# =============================================================================

from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # save charts to files; never open a window
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to the repository root, found from this file's location so
# the script also works when started from another folder)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "raw" / "fact_transactions.csv"
HW02_DIR = REPO_ROOT / "hw02"
CHARTS_DIR = HW02_DIR / "charts"
PROFILE_PATH = HW02_DIR / "hw02_profile.txt"

EXPECTED_SHAPE = (298772, 9)

# Everything printed for items 2-13 is also collected here for the profile file
profile_lines = []


def emit(text="", to_profile=True):
    """Print a line to the terminal and, for items 2-13, keep it for the profile."""
    print(text)
    if to_profile:
        profile_lines.append(text)


def heading(title):
    """Print a numbered section heading."""
    emit()
    emit("=" * 78)
    emit(title)
    emit("=" * 78)


def money(value):
    return f"${value:,.2f}"


# ---------------------------------------------------------------------------
# Item 1: load the data. No type conversion, so pandas shows its own types.
# ---------------------------------------------------------------------------
if not DATA_PATH.exists():
    raise SystemExit(f"Data file not found: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
print(f"Loaded {DATA_PATH}")

emit("WILDCAT CAPITAL TRANSACTION PORTFOLIO - EDA PROFILE")
emit("Dataset: data/raw/fact_transactions.csv")

# ---------------------------------------------------------------------------
# Item 2: shape
# ---------------------------------------------------------------------------
heading("2. Shape (rows x columns)")
emit(f"Rows:    {df.shape[0]:,}")
emit(f"Columns: {df.shape[1]:,}")
emit(f"Shape:   {df.shape}")

# ---------------------------------------------------------------------------
# Item 3: column names and data types
# ---------------------------------------------------------------------------
heading("3. Column names and data types")
for column, dtype in df.dtypes.items():
    emit(f"{column:<15} {dtype}")

# ---------------------------------------------------------------------------
# Item 4: missing values
# ---------------------------------------------------------------------------
heading("4. Missing values per column")
for column, count in df.isna().sum().items():
    emit(f"{column:<15} {count:>10,}")

# ---------------------------------------------------------------------------
# Item 5: descriptive statistics for all numeric columns
# ---------------------------------------------------------------------------
heading("5. Descriptive statistics (numeric columns)")
stats = df.describe().rename(index={"50%": "median"})
with pd.option_context("display.float_format", "{:,.2f}".format,
                       "display.width", 200,
                       "display.max_columns", None):
    emit(stats.to_string())

# ---------------------------------------------------------------------------
# Item 6: txn_type value counts and percentages
# ---------------------------------------------------------------------------
heading("6. Transaction type counts and percentages")
type_counts = df["txn_type"].value_counts()  # sorted most to least frequent
type_pct = df["txn_type"].value_counts(normalize=True) * 100
emit(f"{'txn_type':<15} {'count':>10} {'percent':>9}")
for txn_type, count in type_counts.items():
    emit(f"{txn_type:<15} {count:>10,} {type_pct[txn_type]:>8.2f}%")
emit(f"{'Total':<15} {type_counts.sum():>10,} {type_pct.sum():>8.2f}%")

# ---------------------------------------------------------------------------
# Item 7: unique clients, advisors, securities (missing values not counted)
# ---------------------------------------------------------------------------
heading("7. Unique counts")
emit(f"Unique clients (client_id):       {df['client_id'].nunique():,}")
emit(f"Unique advisors (advisor_id):     {df['advisor_id'].nunique():,}")
emit(f"Unique securities (security_id):  {df['security_id'].nunique():,}")

# ---------------------------------------------------------------------------
# Item 8: date range. Work on a temporary converted copy so the DataFrame
# column stays as text (object).
# ---------------------------------------------------------------------------
heading("8. Date range (txn_date)")
dates = pd.to_datetime(df["txn_date"])
emit(f"Earliest txn_date: {dates.min():%Y-%m-%d}")
emit(f"Latest txn_date:   {dates.max():%Y-%m-%d}")
emit(f"Column type in the DataFrame remains: {df['txn_date'].dtype}")

# ---------------------------------------------------------------------------
# Item 9: duplicate txn_id values
# ---------------------------------------------------------------------------
heading("9. Duplicate txn_id check")
duplicate_count = int(df["txn_id"].duplicated().sum())
emit(f"Duplicate txn_id values: {duplicate_count:,}")

# ---------------------------------------------------------------------------
# Item 10: mean, median, skewness of amount
# ---------------------------------------------------------------------------
heading("10. Amount: mean, median, and skewness")
amount_mean = df["amount"].mean()
amount_median = df["amount"].median()
amount_skew = df["amount"].skew()
if amount_skew > 0.5:
    skew_note = "skewed right (a few very large amounts pull the mean up)"
elif amount_skew < -0.5:
    skew_note = "skewed left (a few very small amounts pull the mean down)"
else:
    skew_note = "roughly symmetric"
emit(f"Mean amount:   {money(amount_mean)}")
emit(f"Median amount: {money(amount_median)}")
emit(f"Skewness:      {amount_skew:.2f}  -> {skew_note}")

# ---------------------------------------------------------------------------
# Item 11: amount by txn_type, sorted by mean descending
# ---------------------------------------------------------------------------
heading("11. Amount by transaction type (sorted by mean amount, high to low)")
by_type = (
    df.groupby("txn_type")["amount"]
    .agg(count="count", mean="mean", median="median")
    .round(2)
    .sort_values("mean", ascending=False)
)
emit(f"{'txn_type':<15} {'count':>10} {'mean amount':>16} {'median amount':>16}")
for txn_type, row in by_type.iterrows():
    emit(f"{txn_type:<15} {int(row['count']):>10,} "
         f"{money(row['mean']):>16} {money(row['median']):>16}")

# ---------------------------------------------------------------------------
# Item 12: correlation matrix and the three strongest pairs
# ---------------------------------------------------------------------------
heading("12. Correlations: shares, price, amount")
corr = df[["shares", "price", "amount"]].corr().round(2)
emit(corr.to_string())
emit()
emit("Three strongest correlations (by absolute value, excluding self-correlation):")
pairs = [(a, b, corr.loc[a, b]) for a, b in combinations(corr.columns, 2)]
pairs.sort(key=lambda item: abs(item[2]), reverse=True)
for rank, (a, b, value) in enumerate(pairs[:3], start=1):
    emit(f"  {rank}. {a} vs {b}: {value:.2f}")

# ---------------------------------------------------------------------------
# Item 13: shares min, max, and negative count by txn_type
# ---------------------------------------------------------------------------
heading("13. Shares by transaction type: min, max, negative count")
shares_by_type = df.groupby("txn_type")["shares"].agg(
    min="min",
    max="max",
    negative_count=lambda s: int((s < 0).sum()),
    non_null_count="count",
)
# Keep every transaction type in the table, even those with no share values
shares_by_type = shares_by_type.reindex(type_counts.index)
emit(f"{'txn_type':<15} {'min':>12} {'max':>12} {'negative':>10} {'non-null':>10}")
for txn_type, row in shares_by_type.iterrows():
    min_text = "n/a" if pd.isna(row["min"]) else f"{row['min']:,.2f}"
    max_text = "n/a" if pd.isna(row["max"]) else f"{row['max']:,.2f}"
    emit(f"{txn_type:<15} {min_text:>12} {max_text:>12} "
         f"{int(row['negative_count']):>10,} {int(row['non_null_count']):>10,}")
emit(f"{'All types':<15} {df['shares'].min():>12,.2f} {df['shares'].max():>12,.2f} "
     f"{int((df['shares'] < 0).sum()):>10,} {int(df['shares'].count()):>10,}")

# ---------------------------------------------------------------------------
# Item 14: shape warning (terminal only)
# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("14. Shape check")
print("=" * 78)
if df.shape != EXPECTED_SHAPE:
    print(f"WARNING: shape is {df.shape}, expected {EXPECTED_SHAPE}. "
          "The file may not have loaded correctly.")
else:
    print(f"OK: shape {df.shape} matches the expected {EXPECTED_SHAPE}.")

# ---------------------------------------------------------------------------
# Item 15: charts
# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("15. Charts")
print("=" * 78)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

dollar_axis = mticker.FuncFormatter(lambda value, _: f"${value:,.0f}")
type_order = list(by_type.index)  # highest mean amount first
palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
type_colors = {t: palette[i % len(palette)] for i, t in enumerate(type_order)}

# Chart 1: histogram of amount with mean and median lines
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["amount"], bins=100, color="#7aa6c9", edgecolor="white")
ax.axvline(amount_mean, color="#d62728", linestyle="--", linewidth=2,
           label=f"Mean: {money(amount_mean)}")
ax.axvline(amount_median, color="#2ca02c", linestyle="-", linewidth=2,
           label=f"Median: {money(amount_median)}")
ax.set_title("Distribution of Transaction Amount")
ax.set_xlabel("Transaction amount")
ax.set_ylabel("Number of transactions")
ax.xaxis.set_major_formatter(dollar_axis)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.legend()
fig.tight_layout()
hist_path = CHARTS_DIR / "hist_amount.png"
fig.savefig(hist_path, dpi=150)
plt.close(fig)
print(f"Saved {hist_path.relative_to(REPO_ROOT)}")

# Chart 2: horizontal box plot of amount by txn_type
fig, ax = plt.subplots(figsize=(10, 6))
box_data = [df.loc[df["txn_type"] == t, "amount"].dropna() for t in type_order]
ax.boxplot(box_data, vert=False, patch_artist=True,
           boxprops={"facecolor": "#c9dcec"},
           medianprops={"color": "#d62728", "linewidth": 2},
           flierprops={"marker": ".", "markersize": 2, "alpha": 0.3})
ax.set_yticks(range(1, len(type_order) + 1))
ax.set_yticklabels(type_order)
ax.invert_yaxis()  # highest mean amount at the top
ax.set_title("Transaction Amount by Transaction Type")
ax.set_xlabel("Transaction amount")
ax.set_ylabel("Transaction type")
ax.xaxis.set_major_formatter(dollar_axis)
fig.tight_layout()
box_path = CHARTS_DIR / "box_amount_by_type.png"
fig.savefig(box_path, dpi=150)
plt.close(fig)
print(f"Saved {box_path.relative_to(REPO_ROOT)}")

# Chart 3: scatter of shares vs amount, colored by txn_type
fig, ax = plt.subplots(figsize=(10, 6))
scatter_df = df.dropna(subset=["shares", "amount"])
for txn_type in type_order:
    subset = scatter_df[scatter_df["txn_type"] == txn_type]
    if subset.empty:
        continue
    ax.scatter(subset["shares"], subset["amount"], s=4, alpha=0.25,
               color=type_colors[txn_type], label=txn_type, rasterized=True)
ax.set_title("Shares vs. Transaction Amount")
ax.set_xlabel("Shares")
ax.set_ylabel("Transaction amount")
ax.yaxis.set_major_formatter(dollar_axis)
ax.legend(title="Transaction type", markerscale=4)
fig.tight_layout()
scatter_path = CHARTS_DIR / "scatter_shares_amount.png"
fig.savefig(scatter_path, dpi=150)
plt.close(fig)
print(f"Saved {scatter_path.relative_to(REPO_ROOT)}")

# ---------------------------------------------------------------------------
# Item 16: save the plain-text profile (items 2-13)
# ---------------------------------------------------------------------------
PROFILE_PATH.write_text("\n".join(profile_lines) + "\n", encoding="utf-8")
print()
print(f"Saved profile summary to {PROFILE_PATH.relative_to(REPO_ROOT)}")

print()
print("Run finished. Output files created:")
for path in (PROFILE_PATH, hist_path, box_path, scatter_path):
    print(f"  {path.relative_to(REPO_ROOT)}")
