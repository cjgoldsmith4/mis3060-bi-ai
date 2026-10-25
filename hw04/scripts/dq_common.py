"""
dq_common.py - shared schema, parsers, and rule definitions for HW4.

01_profile.py, 02_clean.py and 03_validate.py all import this module so the
three scripts judge the data against the same definitions. Nothing in here
reads or writes files except read_table() / load_tables().

Rule for this assignment: every file is read as text (dtype=str,
keep_default_na=False) and each column is converted on purpose.
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- paths
HW_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = HW_DIR / "data" / "raw"
CLEAN_DIR = HW_DIR / "data" / "clean"
AUDIT_DIR = HW_DIR / "data" / "audit"
REPORTS_DIR = HW_DIR / "reports"

TABLES = [
    "dim_advisor", "dim_client", "dim_date", "dim_security", "dim_benchmark",
    "fact_fees", "fact_portfolio_snapshot", "fact_transactions",
]


def read_table(path):
    """Read one CSV as text. Blank cells stay '' and the word None stays 'None'."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def load_tables(folder):
    return {t: read_table(Path(folder) / f"{t}.csv") for t in TABLES}


# ---------------------------------------------------------------- reference lists
US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
STATE_CODES = sorted(US_STATES.values())
TRADE_TYPES = ["Buy", "Sell", "Dividend"]          # rows that carry a security
CASH_TYPES = ["Deposit", "Withdrawal", "Advisory Fee"]  # rows that do not
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _trade(df):
    return df["txn_type"].isin(TRADE_TYPES)


def _equity(df):
    return df["asset_class"] == "Equity"


def _etf(df):
    return df["is_etf"] == "True"


# ---------------------------------------------------------------- schema
# type: int | float | date | bool | bool01 | str
# required: True (always), False (optional), or a function(raw_df) -> bool mask
#           for structural nulls (the value is required only on those rows and
#           must be blank on the others).
SCHEMA = {
    "dim_advisor": {
        "pk": "advisor_id",
        "cols": {
            "advisor_id": {"type": "int", "required": True, "min": 1},
            "first_name": {"type": "str", "required": True},
            "last_name": {"type": "str", "required": True},
            "region": {"type": "str", "required": True,
                       "allowed": ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West"]},
            "years_experience": {"type": "int", "required": True, "min": 0, "max": 60},
            "aum_target_mm": {"type": "int", "required": True, "min": 1, "max": 1000},
            # 'None' is a real answer here (no certification), not a missing value
            "certifications": {"type": "str", "required": True,
                               "pattern": r"^(None|(CFA|CFP|CIMA)(, (CFA|CFP|CIMA))*)$"},
        },
    },
    "dim_benchmark": {
        "pk": "benchmark_id",
        "cols": {
            "benchmark_id": {"type": "int", "required": True, "min": 1},
            "name": {"type": "str", "required": True},
            "asset_class": {"type": "str", "required": True},
            "ticker_proxy": {"type": "str", "required": True},
        },
    },
    "dim_client": {
        "pk": "client_id",
        "cols": {
            "client_id": {"type": "int", "required": True, "min": 1},
            "first_name": {"type": "str", "required": True},
            "last_name": {"type": "str", "required": True},
            "age": {"type": "int", "required": True, "min": 18, "max": 110},
            "city": {"type": "str", "required": True},
            "state": {"type": "str", "required": True, "allowed": STATE_CODES},
            "zip_code": {"type": "str", "required": True, "pattern": r"^\d{5}$"},
            "risk_profile": {"type": "str", "required": True,
                             "allowed": ["Conservative", "Moderately Conservative", "Balanced",
                                         "Moderately Aggressive", "Aggressive"]},
            "client_tier": {"type": "str", "required": True, "allowed": ["Retail", "HNW", "UHNW"]},
            "primary_account_type": {"type": "str", "required": True,
                                     "allowed": ["Taxable", "IRA", "Roth IRA", "Trust", "529"]},
            "initial_aum": {"type": "float", "required": True, "gt": 0},
            "client_since": {"type": "date", "required": True, "min": "2000-01-01", "max": "2024-12-31"},
            "advisor_id": {"type": "int", "required": True},
            "is_active": {"type": "bool", "required": True},
        },
    },
    "dim_date": {
        "pk": "date_id",
        "cols": {
            "date_id": {"type": "int", "required": True, "min": 1},
            "date": {"type": "date", "required": True, "min": "2020-01-01", "max": "2024-12-31"},
            "year": {"type": "int", "required": True, "min": 2020, "max": 2024},
            "quarter": {"type": "int", "required": True, "min": 1, "max": 4},
            "month": {"type": "int", "required": True, "min": 1, "max": 12},
            "month_name": {"type": "str", "required": True, "allowed": MONTHS},
            "week_of_year": {"type": "int", "required": True, "min": 1, "max": 53},
            "day_of_week": {"type": "str", "required": True, "allowed": WEEKDAYS},
            "is_month_end": {"type": "bool01", "required": True},
            "is_quarter_end": {"type": "bool01", "required": True},
            "is_year_end": {"type": "bool01", "required": True},
            "is_trading_day": {"type": "bool01", "required": True},
        },
        "unique": ["date"],
    },
    "dim_security": {
        "pk": "security_id",
        "cols": {
            "security_id": {"type": "int", "required": True, "min": 1},
            "ticker": {"type": "str", "required": True, "pattern": r"^[A-Z]{1,5}$"},
            "name": {"type": "str", "required": True},
            "asset_class": {"type": "str", "required": True,
                            "allowed": ["Equity", "Fixed Income", "Alternative", "Cash Equivalent"]},
            "sector": {"type": "str", "required": _equity},          # only equities have a sector
            "benchmark_id": {"type": "int", "required": True},
            "is_etf": {"type": "bool", "required": True},
            "expense_ratio_bps": {"type": "float", "required": _etf, "min": 0, "max": 300},
        },
        "unique": ["ticker"],
    },
    "fact_fees": {
        "pk": "fee_id",
        "cols": {
            "fee_id": {"type": "int", "required": True, "min": 1},
            "client_id": {"type": "int", "required": True},
            "advisor_id": {"type": "int", "required": True},
            "fee_date": {"type": "date", "required": True},
            "fee_type": {"type": "str", "required": True,
                         "allowed": ["Management", "Advisory", "Custodial", "Performance"]},
            "aum_basis": {"type": "float", "required": True, "gt": 0},
            "bps_charged": {"type": "float", "required": True, "gt": 0, "max": 300},
            "amount": {"type": "float", "required": True, "gt": 0},
        },
    },
    "fact_portfolio_snapshot": {
        "pk": "snapshot_id",
        "cols": {
            "snapshot_id": {"type": "int", "required": True, "min": 1},
            "client_id": {"type": "int", "required": True},
            "advisor_id": {"type": "int", "required": True},
            "benchmark_id": {"type": "int", "required": True},
            "snapshot_date": {"type": "date", "required": True},
            "year": {"type": "int", "required": True, "min": 2020, "max": 2024},
            "month": {"type": "int", "required": True, "min": 1, "max": 12},
            "aum": {"type": "float", "required": True, "gt": 0},
            "return_ytd": {"type": "float", "required": True, "min": -1},   # cannot lose more than 100%
            "benchmark_return_ytd": {"type": "float", "required": True, "min": -1},
            "active_alpha_ytd": {"type": "float", "required": True},
            "cash_pct": {"type": "float", "required": True, "min": 0, "max": 1},
            "account_type": {"type": "str", "required": True,
                             "allowed": ["Taxable", "IRA", "Roth IRA", "Trust", "529"]},
        },
    },
    "fact_transactions": {
        "pk": "txn_id",
        "cols": {
            "txn_id": {"type": "int", "required": True, "min": 1},
            "client_id": {"type": "int", "required": True},
            "advisor_id": {"type": "int", "required": True},
            "security_id": {"type": "int", "required": _trade},     # cash flows have no security
            "txn_date": {"type": "date", "required": True},
            "txn_type": {"type": "str", "required": True,
                         "allowed": ["Buy", "Sell", "Dividend", "Deposit", "Withdrawal", "Advisory Fee"]},
            "shares": {"type": "float", "required": _trade, "gt": 0},
            "price": {"type": "float", "required": _trade, "gt": 0},
            "amount": {"type": "float", "required": True, "gt": 0},
        },
    },
}

# ten ID-based relationships + three date relationships
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]

# ---------------------------------------------------------------- parsing
INT_RE = re.compile(r"^[+-]?\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_blank(s):
    return s.str.strip() == ""


def parse(s, typ):
    """Strict conversion of a text column.

    Returns (values, valid) where valid is True only for non-blank cells that
    parse as `typ` without any repair. Blank cells are valid=False and value=NaN.
    """
    blank = is_blank(s)
    if typ == "int":
        ok = s.str.match(INT_RE) & ~blank
        vals = pd.to_numeric(s.where(ok), errors="coerce")
    elif typ == "float":
        # to_numeric accepts 1.5, -0.2, 1e-05; it rejects 9.28%, $5, 1,000
        vals = pd.to_numeric(s.where(~blank), errors="coerce")
        ok = vals.notna() & ~blank
    elif typ == "date":
        fmt = s.str.match(DATE_RE) & ~blank
        vals = pd.to_datetime(s.where(fmt), format="%Y-%m-%d", errors="coerce")
        ok = vals.notna()
    elif typ == "bool":
        ok = s.isin(["True", "False"])
        vals = s.map({"True": True, "False": False})
    elif typ == "bool01":
        ok = s.isin(["0", "1"])
        vals = pd.to_numeric(s.where(ok), errors="coerce")
    else:  # str
        ok = ~blank
        vals = s.where(ok)
    return vals, ok.fillna(False).astype(bool)


def typed(df, table):
    """Typed copy of a table using SCHEMA (invalid / blank cells become NaN)."""
    out = pd.DataFrame(index=df.index)
    for col, spec in SCHEMA[table]["cols"].items():
        out[col], _ = parse(df[col], spec["type"])
    return out


def required_mask(df, spec):
    req = spec.get("required", True)
    if callable(req):
        return req(df).astype(bool)
    return pd.Series(bool(req), index=df.index)


# ---------------------------------------------------------------- row rules
def column_rule_masks(df, table):
    """Column-level rules from SCHEMA. Returns list of (rule_name, column, fail_mask).

    A rule only judges cells that are present and parse; blanks are a
    completeness problem and bad formats are a type problem, scored separately.
    """
    rules = []
    for col, spec in SCHEMA[table]["cols"].items():
        vals, ok = parse(df[col], spec["type"])
        if "allowed" in spec:
            rules.append((f"{col} in allowed list", col, ok & ~df[col].isin(spec["allowed"])))
        if "pattern" in spec:
            rules.append((f"{col} matches pattern", col, ok & ~df[col].str.match(spec["pattern"])))
        for key, label in (("min", ">="), ("max", "<="), ("gt", ">")):
            if key in spec:
                bound = spec[key]
                if spec["type"] == "date":
                    bound = pd.Timestamp(bound)
                if key == "min":
                    fail = ok & (vals < bound)
                elif key == "max":
                    fail = ok & (vals > bound)
                else:
                    fail = ok & (vals <= bound)
                rules.append((f"{col} {label} {spec[key]}", col, fail.fillna(False)))
        # structural nulls: must be blank where not required
        req = spec.get("required", True)
        if callable(req):
            rules.append((f"{col} blank when not applicable", col, ~req(df) & ~is_blank(df[col])))
    return rules


def row_consistency_masks(df, table):
    """Single-table rules where one column contradicts another in the same row.
    Returns list of (rule_name, column, fail_mask, severity)."""
    T = typed(df, table)
    out = []
    if table == "dim_client":
        aum = T["initial_aum"]
        band = np.select([aum < 500_000, aum < 5_000_000], ["Retail", "HNW"], "UHNW")
        out.append(("client_tier matches initial_aum band", "client_tier",
                    aum.notna() & (df["client_tier"] != band), "WARN"))
    elif table == "dim_date":
        d = T["date"]
        checks = {
            "year": d.dt.year, "quarter": d.dt.quarter, "month": d.dt.month,
            "week_of_year": d.dt.isocalendar().week.astype("float"),
            "is_month_end": d.dt.is_month_end.astype(int),
            "is_quarter_end": d.dt.is_quarter_end.astype(int),
            "is_year_end": d.dt.is_year_end.astype(int),
            "is_trading_day": (d.dt.dayofweek < 5).astype(int),
        }
        for col, exp in checks.items():
            out.append((f"{col} matches date", col, d.notna() & (T[col] != exp), "ERROR"))
        out.append(("month_name matches date", "month_name", d.notna() & (df["month_name"] != d.dt.month_name()), "ERROR"))
        out.append(("day_of_week matches date", "day_of_week", d.notna() & (df["day_of_week"] != d.dt.day_name()), "ERROR"))
    elif table == "dim_security":
        out.append(("is_etf True for every non-equity fund", "is_etf",
                    (df["asset_class"] != "Equity") != (df["is_etf"] == "True"), "WARN"))
    elif table == "fact_fees":
        exp = (T["aum_basis"] * T["bps_charged"] / 10000 / 12).round(2)
        out.append(("amount = aum_basis x bps / 10000 / 12", "amount",
                    T["amount"].notna() & exp.notna() & ((T["amount"] - exp).abs() > 0.011), "ERROR"))
    elif table == "fact_portfolio_snapshot":
        d = T["snapshot_date"]
        out.append(("year/month match snapshot_date", "snapshot_date",
                    d.notna() & ((T["year"] != d.dt.year) | (T["month"] != d.dt.month)), "ERROR"))
        out.append(("snapshot_date is first of month", "snapshot_date", d.notna() & (d.dt.day != 1), "WARN"))
        diff = (T["return_ytd"] - T["benchmark_return_ytd"] - T["active_alpha_ytd"]).abs()
        out.append(("active_alpha = return - benchmark_return", "active_alpha_ytd",
                    diff.notna() & (diff > 2e-6), "ERROR"))
    elif table == "fact_transactions":
        trade = _trade(df)
        diff = (T["shares"].abs() * T["price"] - T["amount"]).abs()
        out.append(("amount = |shares| x price (trades)", "amount", trade & diff.notna() & (diff > 0.011), "ERROR"))
    return out


def row_rule_table(df, table):
    """All row rules (column + consistency) as a DataFrame of fail masks."""
    masks = {}
    for name, col, fail in column_rule_masks(df, table):
        masks[f"{name}"] = fail
    for name, col, fail, sev in row_consistency_masks(df, table):
        masks[f"{name}"] = fail
    return pd.DataFrame(masks, index=df.index)


# ---------------------------------------------------------------- cross-table rules
def cross_table_checks(T):
    """Group 4: facts that disagree with dimensions or with each other.
    T is a dict of raw-text DataFrames. Returns a list of finding dicts."""
    out = []
    cl = T["dim_client"]
    sn = T["fact_portfolio_snapshot"]
    fe = T["fact_fees"]
    tx = T["fact_transactions"]
    dd = T["dim_date"]

    def add(check, table, column, n, total, severity, note, example=""):
        out.append({"check_group": "4 cross-table", "table": table, "column": column, "check": check,
                    "severity": severity if n else "INFO", "rows_affected": int(n), "rows_checked": int(total),
                    "pct_affected": round(100 * n / total, 4) if total else 0.0, "example": example, "note": note})

    # 1. fact advisor_id must equal the client's advisor in dim_client
    for name, f in (("fact_fees", fe), ("fact_portfolio_snapshot", sn), ("fact_transactions", tx)):
        m = f[["client_id", "advisor_id"]].merge(cl[["client_id", "advisor_id"]].drop_duplicates("client_id"),
                                                 on="client_id", how="inner", suffixes=("", "_dim"))
        n = (m["advisor_id"] != m["advisor_id_dim"]).sum()
        add("advisor_id differs from dim_client.advisor_id", name, "advisor_id", n, len(m), "ERROR",
            "a client's fact rows should carry the client's assigned advisor")

    # 2. snapshot account_type must equal client's primary_account_type
    m = sn[["client_id", "account_type"]].merge(cl[["client_id", "primary_account_type"]].drop_duplicates("client_id"), on="client_id")
    n = (m["account_type"] != m["primary_account_type"]).sum()
    add("account_type differs from dim_client.primary_account_type", "fact_portfolio_snapshot", "account_type", n, len(m),
        "WARN", "snapshot account type vs client master")

    # 3. one benchmark per client, and benchmark agrees with risk profile
    nb = (sn.groupby("client_id")["benchmark_id"].nunique() > 1).sum()
    add("clients with more than one benchmark_id", "fact_portfolio_snapshot", "benchmark_id", nb, sn["client_id"].nunique(),
        "WARN", "clients whose benchmark changes across snapshots")
    m = sn[["client_id", "benchmark_id"]].drop_duplicates("client_id").merge(
        cl[["client_id", "risk_profile"]].drop_duplicates("client_id"), on="client_id")
    expected = m["risk_profile"].map({"Aggressive": "1", "Moderately Aggressive": "1", "Balanced": "3",
                                      "Moderately Conservative": "8", "Conservative": "8"})
    n = (expected.notna() & (expected != m["benchmark_id"])).sum()
    add("benchmark_id disagrees with risk_profile (Agg->1, Bal->3, Cons->8)", "fact_portfolio_snapshot", "benchmark_id",
        n, len(m), "WARN", "mapping observed in the data; clients with blank risk_profile are excluded")
    blank_rp = m[m["risk_profile"].str.strip() == ""]
    add("clients with blank risk_profile (benchmark they sit on)", "dim_client", "risk_profile", len(blank_rp),
        len(m), "WARN", f"benchmark_id values for these clients: {blank_rp['benchmark_id'].value_counts().to_dict()}")

    # 4. fee aum_basis equals snapshot aum for the same client-month
    m = fe[["client_id", "fee_date", "aum_basis"]].merge(sn[["client_id", "snapshot_date", "aum"]],
                                                        left_on=["client_id", "fee_date"],
                                                        right_on=["client_id", "snapshot_date"], how="left")
    no_snap = m["aum"].isna().sum()
    add("fee row with no snapshot for the same client-month", "fact_fees", "fee_date", no_snap, len(m), "ERROR",
        "fees should be charged on a month the account existed")
    both = m.dropna(subset=["aum"])
    diff = (pd.to_numeric(both["aum_basis"], errors="coerce") - pd.to_numeric(both["aum"], errors="coerce")).abs()
    add("fee aum_basis differs from snapshot aum (same client-month)", "fact_fees", "aum_basis", (diff > 0.01).sum(), len(both),
        "ERROR", "two systems describing the same balance")
    m = sn[["client_id", "snapshot_date"]].merge(fe[["client_id", "fee_date"]], left_on=["client_id", "snapshot_date"],
                                                 right_on=["client_id", "fee_date"], how="left")
    add("snapshot month with no fee row", "fact_portfolio_snapshot", "snapshot_date", m["fee_date"].isna().sum(), len(m),
        "WARN", "missing fee months: waiver, billing gap, or lost rows")

    # 5. Advisory Fee transactions vs fact_fees totals (client-year)
    af = tx[tx["txn_type"] == "Advisory Fee"].assign(y=lambda d: d["txn_date"].str[:4],
                                                    a=lambda d: pd.to_numeric(d["amount"], errors="coerce"))
    ff = fe.assign(y=fe["fee_date"].str[:4], a=pd.to_numeric(fe["amount"], errors="coerce"))
    j = pd.concat([af.groupby(["client_id", "y"])["a"].sum(), ff.groupby(["client_id", "y"])["a"].sum()],
                  axis=1, keys=["txn", "fee"]).dropna()
    off = ((j["txn"] - j["fee"]).abs() > 0.01 * j["fee"]).sum()
    add("Advisory Fee txn total differs from fact_fees total (client-year, >1%)", "fact_transactions", "amount", off, len(j),
        "WARN", f"median txn/fee ratio {round(float((j['txn'] / j['fee']).median()), 3)}")

    # 6. no activity before the client relationship started
    for name, f, col in (("fact_transactions", tx, "txn_date"), ("fact_portfolio_snapshot", sn, "snapshot_date"),
                         ("fact_fees", fe, "fee_date")):
        m = f[["client_id", col]].merge(cl[["client_id", "client_since"]].drop_duplicates("client_id"), on="client_id")
        n = (m[col].str[:7] < m["client_since"].str[:7]).sum()
        add(f"{col} before client_since month", name, col, n, len(m), "ERROR", "activity before onboarding")

    # 7. inactive clients: transactions after their final snapshot month
    last = sn.groupby("client_id")["snapshot_date"].max()
    inactive = set(cl.loc[cl["is_active"] == "False", "client_id"])
    t2 = tx[tx["client_id"].isin(inactive)]
    month_end = (pd.to_datetime(t2["client_id"].map(last), errors="coerce") + pd.offsets.MonthEnd(0))
    n = (pd.to_datetime(t2["txn_date"], errors="coerce") > month_end).sum()
    add("inactive client txn after final snapshot month", "fact_transactions", "txn_date", n, len(t2), "WARN",
        "activity after the account appears to have closed")
    active = set(cl.loc[cl["is_active"] == "True", "client_id"])
    n = sum(1 for c, d in last.items() if c in active and d < last.max())
    add("active client whose snapshots stop before the last month", "fact_portfolio_snapshot", "snapshot_date", n,
        len([c for c in last.index if c in active]), "WARN", "is_active vs snapshot coverage")

    # 8. trades and dividends dated on non-trading days
    m = tx.loc[_trade(tx), ["txn_date"]].merge(dd[["date", "is_trading_day"]], left_on="txn_date", right_on="date", how="left")
    n = (m["is_trading_day"] == "0").sum()
    add("Buy/Sell/Dividend dated on a non-trading day", "fact_transactions", "txn_date", n, len(m), "WARN",
        "markets are closed on weekends")

    # 9. sells larger than buys (inside the 2020-2024 window)
    sh = pd.to_numeric(tx["shares"], errors="coerce").abs()
    p = tx.assign(sh=sh)[tx["txn_type"].isin(["Buy", "Sell"])].pivot_table(
        index=["client_id", "security_id"], columns="txn_type", values="sh", aggfunc="sum", fill_value=0)
    n = (p.get("Sell", 0) > p.get("Buy", 0) + 1e-6).sum()
    add("positions where shares sold exceed shares bought", "fact_transactions", "shares", n, len(p), "INFO",
        "positions opened before 2020 would explain this; extract starts 2020-01-01")

    # 10. price consistency for one security
    tr = tx[_trade(tx)].assign(p=pd.to_numeric(tx["price"], errors="coerce"))
    g = tr.groupby("security_id")["p"].agg(["min", "max"])
    ratio = g["max"] / g["min"]
    add("security price range max/min > 10x", "fact_transactions", "price", (ratio > 10).sum(), len(g), "WARN",
        f"median max/min ratio {round(float(ratio.median()), 1)}; real prices rarely move 10x in five years")
    return out
