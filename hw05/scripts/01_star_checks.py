"""
01_star_checks.py - HW5 Parts A to C: prove the keys, grains and measure
behaviour of the eight clean Wildcat Capital tables before modeling them
in Power BI.

Reads data/clean/*.csv as text (dtype=str, keep_default_na=False), so a key
such as '45.0' never silently matches '45'. Stops on the first failed assert.

Outputs (reports/)
  row_counts.csv        rows and columns per table vs the HW5 handout
  pk_checks.csv         one row per table: primary key unique and never blank
  fk_checks.csv         one row per foreign key: blanks, orphans, match rate
  grain_checks.csv      one row per fact: the grain columns are unique
  measure_checks.csv    numbers that show why each measure is (semi/non-)additive
  powerbi_types.csv     the Power Query type to set for every column (Part D)
"""
from pathlib import Path

import pandas as pd

HW = Path(__file__).resolve().parent.parent
CLEAN = HW / "data" / "clean"
REPORTS = HW / "reports"
REPORTS.mkdir(exist_ok=True)

# Row and column counts from the HW5 handout
EXPECTED = {
    "dim_advisor": (25, 7),
    "dim_benchmark": (8, 4),
    "dim_client": (2500, 14),
    "dim_date": (1827, 12),
    "dim_security": (500, 8),
    "fact_fees": (122197, 8),
    "fact_portfolio_snapshot": (129547, 14),
    "fact_transactions": (298572, 10),
}

PRIMARY_KEYS = {
    "dim_advisor": "advisor_id",
    "dim_benchmark": "benchmark_id",
    "dim_client": "client_id",
    "dim_date": "date_id",
    "dim_security": "security_id",
    "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id",
    "fact_transactions": "txn_id",
}

# (table, column, target table, target column, blank allowed?)
FOREIGN_KEYS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
]

GRAINS = {
    "fact_transactions": ["txn_id"],
    "fact_fees": ["client_id", "fee_date"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
}

# Power Query types (powerbi_guide.md section 1)
TEXT_COLS = {
    "dim_advisor": ["first_name", "last_name", "region", "certifications"],
    "dim_benchmark": ["name", "asset_class", "ticker_proxy"],
    "dim_client": ["first_name", "last_name", "city", "state", "zip_code",
                   "risk_profile", "client_tier", "primary_account_type"],
    "dim_date": ["month_name", "day_of_week"],
    "dim_security": ["ticker", "name", "asset_class", "sector"],
    "fact_fees": ["fee_type"],
    "fact_portfolio_snapshot": ["account_type"],
    "fact_transactions": ["txn_type"],
}
DATE_COLS = {"date", "txn_date", "fee_date", "snapshot_date", "client_since"}
BOOL_COLS = {"is_active", "is_etf"}
DECIMAL_COLS = {"initial_aum", "expense_ratio_bps", "aum_basis", "bps_charged",
                "amount", "aum", "return_ytd", "benchmark_return_ytd",
                "active_alpha_ytd", "cash_pct", "shares", "price"}


def load(name):
    return pd.read_csv(CLEAN / f"{name}.csv", dtype=str, keep_default_na=False)


def num(s):
    return pd.to_numeric(s, errors="raise")


t = {name: load(name) for name in EXPECTED}

# ----------------------------------------------------------------------
# Row counts
# ----------------------------------------------------------------------
rows = []
for name, (exp_r, exp_c) in EXPECTED.items():
    r, c = t[name].shape
    rows.append({"table": name, "rows": r, "expected_rows": exp_r,
                 "cols": c, "expected_cols": exp_c,
                 "match": r == exp_r and c == exp_c})
row_counts = pd.DataFrame(rows)
assert row_counts["match"].all(), row_counts[~row_counts["match"]]
row_counts.to_csv(REPORTS / "row_counts.csv", index=False)

# ----------------------------------------------------------------------
# Part A: primary keys
# ----------------------------------------------------------------------
rows = []
for name, pk in PRIMARY_KEYS.items():
    s = t[name][pk]
    rows.append({"table": name, "primary_key": pk, "rows": len(s),
                 "distinct": s.nunique(), "blank": int((s == "").sum()),
                 "whole_number": bool(s.str.fullmatch(r"\d+").all()),
                 "unique": s.is_unique and (s != "").all()})
pk_checks = pd.DataFrame(rows)
assert pk_checks["unique"].all() and pk_checks["whole_number"].all(), pk_checks

# dim_date[date] is the column the facts join on, so it must be unique too
assert t["dim_date"]["date"].is_unique
pk_checks.to_csv(REPORTS / "pk_checks.csv", index=False)

# ----------------------------------------------------------------------
# Part A: foreign keys
# ----------------------------------------------------------------------
rows = []
for table, col, target, tcol, blank_ok in FOREIGN_KEYS:
    s = t[table][col]
    blank = s == ""
    valid = set(t[target][tcol])
    orphan = ~blank & ~s.isin(valid)
    checked = int((~blank).sum())
    rows.append({"table": table, "foreign_key": col,
                 "references": f"{target}[{tcol}]", "rows": len(s),
                 "blank": int(blank.sum()), "blank_allowed": blank_ok,
                 "orphans": int(orphan.sum()),
                 "match_rate": round(1 - orphan.sum() / checked, 6) if checked else 1.0})
    assert orphan.sum() == 0, f"{table}.{col}: {orphan.sum()} orphans"
    assert blank_ok or blank.sum() == 0, f"{table}.{col}: unexpected blanks"
fk_checks = pd.DataFrame(rows)
fk_checks.to_csv(REPORTS / "fk_checks.csv", index=False)

# Blank security_id: only cash rows, and every cash row is blank
txn = t["fact_transactions"]
cash_types = {"Deposit", "Withdrawal", "Advisory Fee"}
no_sec = txn["security_id"] == ""
assert set(txn.loc[no_sec, "txn_type"]) == cash_types
assert (txn.loc[txn["txn_type"].isin(cash_types), "security_id"] == "").all()
assert (txn.loc[no_sec, "shares"] == "").all() and (txn.loc[no_sec, "price"] == "").all()

# Fact dates match dim_date[date], never dim_date[date_id]
for table, col in [("fact_transactions", "txn_date"), ("fact_fees", "fee_date"),
                   ("fact_portfolio_snapshot", "snapshot_date")]:
    assert t[table][col].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
    assert not t[table][col].isin(set(t["dim_date"]["date_id"])).any()

# advisor_id on every fact row equals the client's advisor in dim_client,
# so the direct path and the path through dim_client give the same answer
client_adv = t["dim_client"].set_index("client_id")["advisor_id"]
advisor_mismatch = {}
for table in GRAINS:
    df = t[table]
    advisor_mismatch[table] = int((df["advisor_id"] != df["client_id"].map(client_adv)).sum())
assert sum(advisor_mismatch.values()) == 0, advisor_mismatch

# ----------------------------------------------------------------------
# Part B: grain
# ----------------------------------------------------------------------
rows = []
for table, cols in GRAINS.items():
    dupes = int(t[table].duplicated(cols).sum())
    rows.append({"table": table, "grain_columns": " + ".join(cols),
                 "rows": len(t[table]), "duplicate_grain_rows": dupes,
                 "unique": dupes == 0})
    assert dupes == 0, f"{table}: {dupes} rows repeat the grain {cols}"
# A txn_id check alone proves nothing new (it is the primary key), so also
# test the business columns: same-day repeat trades exist, which makes
# txn_id the only column set that identifies a transaction
natural = ["client_id", "txn_date", "txn_type", "security_id"]
nat_dupes = int(txn.duplicated(natural).sum())
assert nat_dupes > 0
rows.append({"table": "fact_transactions", "grain_columns": " + ".join(natural),
             "rows": len(txn), "duplicate_grain_rows": nat_dupes, "unique": False})
grain_checks = pd.DataFrame(rows)

# Monthly facts sit on the first of the month, but dim_date flags the LAST
# day as is_month_end, so an is_month_end = 1 filter removes every row
month_end_dates = set(t["dim_date"].loc[t["dim_date"]["is_month_end"] == "1", "date"])
for table, col in [("fact_fees", "fee_date"), ("fact_portfolio_snapshot", "snapshot_date")]:
    assert t[table][col].str.endswith("-01").all()
    assert not t[table][col].isin(month_end_dates).any()
grain_checks.to_csv(REPORTS / "grain_checks.csv", index=False)

# ----------------------------------------------------------------------
# Part C: measure behaviour
# ----------------------------------------------------------------------
snap = t["fact_portfolio_snapshot"]
fees = t["fact_fees"]
aum = num(snap["aum"])
checks = []


def add(check, value, note):
    checks.append({"check": check, "value": value, "note": note})


# Semi-additive: AUM is a balance
dec24 = aum[snap["snapshot_date"] == "2024-12-01"].sum()
all24 = aum[snap["year"] == "2024"].sum()
add("snapshot aum, Dec 2024 total", round(dec24, 2), "valid: one month, summed across clients")
add("snapshot aum, all 2024 rows summed", round(all24, 2), "invalid: twelve balances stacked")
add("snapshot aum, 2024 sum / Dec 2024", round(all24 / dec24, 3), "how far a yearly SUM overstates AUM")
add("snapshot aum, all rows summed", round(aum.sum(), 2), "invalid: sixty balances stacked")

fee_basis = num(fees["aum_basis"])
merged = fees.merge(snap[["client_id", "snapshot_date", "aum"]],
                    left_on=["client_id", "fee_date"],
                    right_on=["client_id", "snapshot_date"], how="left")
assert merged["aum"].notna().all()
basis_match = (merged["aum_basis"] == merged["aum"]).mean()
assert basis_match == 1.0
add("fees aum_basis equals snapshot aum, same client-month", basis_match,
    "aum_basis is the same balance, so it is semi-additive too")

# Additive: fee amount = aum_basis x bps / 10,000 / 12
fee_calc = fee_basis * num(fees["bps_charged"]) / 10000 / 12
fee_gap = (fee_calc - num(fees["amount"])).abs().max()
assert fee_gap <= 0.0051
add("fees amount vs aum_basis x bps / 10000 / 12, max gap", round(fee_gap, 4),
    "amount is a monthly charge; rounding to cents only")
add("fees amount, all rows summed", round(num(fees["amount"]).sum(), 2),
    "valid: total fees charged 2020-2024")

# Non-additive: bps is a rate, so the right average weights by aum_basis
bps = num(fees["bps_charged"])
add("fees bps_charged, simple average", round(bps.mean(), 4), "unweighted")
add("fees bps_charged, aum-weighted average", round((bps * fee_basis).sum() / fee_basis.sum(), 4),
    "weighted by aum_basis; the rate the firm earned")
add("fees bps_charged, all rows summed", round(bps.sum(), 2), "meaningless")

# Non-additive: return_ytd is a cumulative ratio
ret = num(snap["return_ytd"])
bench = num(snap["benchmark_return_ytd"])
alpha = num(snap["active_alpha_ytd"])
alpha_gap = (ret - bench - alpha).abs().max()
assert alpha_gap <= 0.0000011
add("snapshot return_ytd - benchmark_return_ytd - active_alpha_ytd, max gap",
    round(alpha_gap, 7), "alpha is derived from two ratios")
c1 = snap[snap["client_id"] == "1"].copy()
c1_2024 = c1[c1["year"] == "2024"].sort_values("snapshot_date")
add("client 1 return_ytd, Dec 2024", float(c1_2024["return_ytd"].iloc[-1]),
    "the 2024 return to date")
add("client 1 return_ytd, 2024 rows summed", round(num(c1_2024["return_ytd"]).sum(), 6),
    "invalid: YTD values already include earlier months")

cash = num(snap["cash_pct"])
add("snapshot cash_pct range", f"{cash.min()} to {cash.max()}", "a share of AUM")
add("snapshot cash_pct, Dec 2024 aum-weighted average",
    round((cash * aum)[snap["snapshot_date"] == "2024-12-01"].sum() / dec24, 6),
    "weighted by aum; summing shares of different balances is meaningless")

# Additive with a caveat: amount is unsigned, so txn_type must be on the visual
amt = num(txn["amount"])
assert (amt > 0).all()
by_type = amt.groupby(txn["txn_type"]).sum().round(2)
for k, v in by_type.items():
    add(f"transactions amount, {k}", v, "")
add("transactions amount, all types summed", round(amt.sum(), 2),
    "gross activity; deposits and withdrawals both count as positive")
add("transactions net new money (Deposit - Withdrawal)",
    round(by_type["Deposit"] - by_type["Withdrawal"], 2), "needs a sign by txn_type")

trades = txn[~no_sec]
shares = num(trades["shares"])
assert (shares > 0).all()
recon = (shares * num(trades["price"]) - num(trades["amount"])).abs().max()
assert recon < 0.05
add("transactions shares x price vs amount, max gap", round(recon, 4),
    "shares and amount are unsigned on Buy and Sell rows")
add("transactions distinct securities", trades["security_id"].nunique(),
    "shares only add up inside one security")

# Two sources of fee dollars: fact_fees (charged) and Advisory Fee rows in
# fact_transactions (debited). They do not agree, so fee questions use fact_fees
fees_charged = num(fees["amount"]).sum()
fees_debited = by_type["Advisory Fee"]
add("fact_fees amount minus Advisory Fee debits in fact_transactions",
    round(fees_charged - fees_debited, 2), "negative: debits exceed charges")

measure_checks = pd.DataFrame(checks)
measure_checks.to_csv(REPORTS / "measure_checks.csv", index=False)

# ----------------------------------------------------------------------
# Part D helper: Power Query type for every column
# ----------------------------------------------------------------------
rows = []
for name, df in t.items():
    for col in df.columns:
        if col.endswith("_id"):
            ptype = "Whole Number"
        elif col in DATE_COLS:
            ptype = "Date"
        elif col in BOOL_COLS:
            ptype = "True/False"
        elif col in DECIMAL_COLS:
            ptype = "Decimal Number"
        elif col in TEXT_COLS[name]:
            ptype = "Text"
        else:
            ptype = "Whole Number"
        if ptype == "Whole Number":
            vals = df.loc[df[col] != "", col]
            assert vals.str.fullmatch(r"\d+").all(), f"{name}.{col} is not whole"
        rows.append({"table": name, "column": col, "power_query_type": ptype,
                     "blank": int((df[col] == "").sum())})
types = pd.DataFrame(rows)
assert len(types) == sum(c for _, c in EXPECTED.values())
types.to_csv(REPORTS / "powerbi_types.csv", index=False)

print("Row counts match the handout:", int(row_counts["match"].sum()), "of 8 tables")
print("Primary keys unique:", int(pk_checks["unique"].sum()), "of 8")
print("Foreign keys with zero orphans:", len(fk_checks), "of", len(FOREIGN_KEYS))
print("Blank security_id rows (cash only):", int(no_sec.sum()))
print("Fact rows whose advisor differs from dim_client:", sum(advisor_mismatch.values()))
print("Fact grains unique:", int(grain_checks["unique"].sum()), "of 3;",
      "client + date + type + security repeats on", nat_dupes, "transaction rows")
print(f"2024 AUM summed across months overstates Dec 2024 AUM by {all24 / dec24:.2f}x")
print("All asserts passed. Reports written to", REPORTS)
