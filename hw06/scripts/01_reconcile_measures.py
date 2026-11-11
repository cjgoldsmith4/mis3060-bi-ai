"""HW6 Part B: reconcile every Power BI measure to an independent pandas calculation.

Reads the eight clean Wildcat Capital CSVs from data/clean/, recomputes each
measure for every required slice, reads the Power BI numbers from
reports/powerbi_values.csv (columns: measure, slice, value) and writes
reports/measure_reconciliation.csv.

The pandas side never reads anything from Power BI. Each DAX filter context is
rebuilt as a date window plus an optional client_tier filter:
    - LASTNONBLANK(dim_date[date], ...)  -> latest snapshot_date inside the window
    - SAMEPERIODLASTYEAR / DATEADD       -> the window shifted back, clipped to the
                                            dim_date range (DAX returns only dates
                                            that exist in the date column)
    - DIVIDE                             -> NaN (blank) when the denominator is 0 or blank

Run from the hw06 folder:  python scripts/01_reconcile_measures.py
Exit code 1 if any row fails to match.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HW = Path(__file__).resolve().parents[1]
DATA = HW / "data" / "clean"
REPORTS = HW / "reports"
PBI_FILE = REPORTS / "powerbi_values.csv"
OUT_FILE = REPORTS / "measure_reconciliation.csv"

# dim_date covers 2020-01-01 to 2024-12-31; time-intelligence shifts are clipped to it.
DATE_MIN = pd.Timestamp("2020-01-01")
DATE_MAX = pd.Timestamp("2024-12-31")

# Tolerance by measure kind (handout: 0.01 for currency, 0.0001 for ratios).
TOLERANCE = {"currency": 0.01, "count": 0.01, "ratio": 0.0001, "bps": 0.0001}
KIND = {
    "Total Fees": "currency",
    "Net Flows": "currency",
    "AUM (naive SUM)": "currency",
    "Ending AUM": "currency",
    "Ending Clients": "count",
    "Avg AUM per Client": "currency",
    "Ending AUM LY": "currency",
    "AUM YoY %": "ratio",
    "Ending AUM PM": "currency",
    "AUM MoM %": "ratio",
    "Avg Monthly AUM": "currency",
    "Fee Yield (bps)": "bps",
    "Organic Growth Rate": "ratio",
    "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text",
    "Top 10 Client Share": "ratio",
    # Part C helper measures (display folder "Part C checks" in Power BI)
    "Ending AUM SUMX by Client": "currency",
    "AUM-Weighted Alpha incl. Suspects": "ratio",
    "Simple Mean Alpha": "ratio",
    "Effective Fee Rate (bps)": "bps",
}


# --------------------------------------------------------------------------- data
def load() -> dict[str, pd.DataFrame]:
    client = pd.read_csv(DATA / "dim_client.csv", usecols=["client_id", "client_tier"])
    snap = pd.read_csv(DATA / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    fees = pd.read_csv(DATA / "fact_fees.csv", parse_dates=["fee_date"])
    txns = pd.read_csv(
        DATA / "fact_transactions.csv",
        usecols=["client_id", "txn_date", "txn_type", "amount"],
        parse_dates=["txn_date"],
    )
    # Attach the tier the way the dim_client relationship does (many-to-one on client_id).
    snap = snap.merge(client, on="client_id", how="left", validate="many_to_one")
    fees = fees.merge(client, on="client_id", how="left", validate="many_to_one")
    txns = txns.merge(client, on="client_id", how="left", validate="many_to_one")
    for name, df in {"snapshot": snap, "fees": fees, "transactions": txns}.items():
        assert df["client_tier"].notna().all(), f"{name}: client_id missing from dim_client"
    return {
        "snap": snap.rename(columns={"snapshot_date": "date"}),
        "fees": fees.rename(columns={"fee_date": "date"}),
        "txns": txns.rename(columns={"txn_date": "date"}),
    }


# ------------------------------------------------------------------ filter context
@dataclass(frozen=True)
class Context:
    """A DAX filter context: a date window on dim_date[date] plus an optional tier."""

    start: pd.Timestamp
    end: pd.Timestamp
    tier: str | None = None

    def shift(self, offset: pd.DateOffset) -> "Context":
        start = max(self.start + offset, DATE_MIN)
        end = min(self.end + offset, DATE_MAX)
        return Context(start, end, self.tier)

    def ly(self) -> "Context":  # SAMEPERIODLASTYEAR
        return self.shift(pd.DateOffset(years=-1))

    def pm(self) -> "Context":  # DATEADD(..., -1, MONTH)
        return self.shift(pd.DateOffset(months=-1))


def rows(df: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    if ctx.start > ctx.end:
        return df.iloc[0:0]
    mask = df["date"].between(ctx.start, ctx.end)
    if ctx.tier is not None:
        mask &= df["client_tier"].eq(ctx.tier)
    return df[mask]


def divide(num: float, den: float) -> float:
    if pd.isna(num) or pd.isna(den) or den == 0:
        return np.nan
    return num / den


# --------------------------------------------------------------------- measures
class Measures:
    def __init__(self, d: dict[str, pd.DataFrame]):
        self.snap, self.fees, self.txns = d["snap"], d["fees"], d["txns"]

    def last_snapshot(self, ctx: Context) -> pd.DataFrame:
        """Rows at the latest snapshot date in the context (LASTNONBLANK pattern)."""
        s = rows(self.snap, ctx)
        if s.empty:
            return s
        return s[s["date"].eq(s["date"].max())]

    def total_fees(self, ctx):
        f = rows(self.fees, ctx)
        return f["amount"].sum() if len(f) else np.nan

    def net_flows(self, ctx):
        t = rows(self.txns, ctx)
        if t.empty:
            return np.nan
        dep = t.loc[t["txn_type"].eq("Deposit"), "amount"].sum()
        wdr = t.loc[t["txn_type"].eq("Withdrawal"), "amount"].sum()
        return dep - wdr

    def naive_sum(self, ctx):
        s = rows(self.snap, ctx)
        return s["aum"].sum() if len(s) else np.nan

    def ending_aum(self, ctx):
        s = self.last_snapshot(ctx)
        return s["aum"].sum() if len(s) else np.nan

    def ending_clients(self, ctx):
        s = self.last_snapshot(ctx)
        return float(s["client_id"].nunique()) if len(s) else np.nan

    def avg_aum_per_client(self, ctx):
        return divide(self.ending_aum(ctx), self.ending_clients(ctx))

    def ending_aum_ly(self, ctx):
        return self.ending_aum(ctx.ly())

    def aum_yoy(self, ctx):
        ly = self.ending_aum_ly(ctx)
        return divide(self.ending_aum(ctx) - ly, ly)

    def ending_aum_pm(self, ctx):
        return self.ending_aum(ctx.pm())

    def aum_mom(self, ctx):
        pm = self.ending_aum_pm(ctx)
        return divide(self.ending_aum(ctx) - pm, pm)

    def avg_monthly_aum(self, ctx):
        s = rows(self.snap, ctx)
        return divide(s["aum"].sum(), s["date"].nunique()) if len(s) else np.nan

    def fee_yield(self, ctx):
        fees = self.total_fees(ctx)
        aum = self.naive_sum(ctx)
        return divide(fees * 12 * 10_000, aum)

    def organic_growth(self, ctx):
        return divide(self.net_flows(ctx), self.ending_aum_ly(ctx))

    def weighted_alpha(self, ctx, include_suspect: bool = False):
        s = self.last_snapshot(ctx)
        if not include_suspect:
            s = s[s["is_return_suspect"].eq(0)]
        if s.empty:
            return np.nan
        return divide((s["aum"] * s["active_alpha_ytd"]).sum(), s["aum"].sum())

    def alpha_signal(self, ctx):
        a = self.weighted_alpha(ctx)
        if pd.isna(a):
            return ""
        if a >= 0.02:
            return "Outperforming"
        if a <= -0.02:
            return "Lagging"
        return "In line"

    def top10_share(self, ctx):
        s = self.last_snapshot(ctx)
        if s.empty:
            return np.nan
        by_client = s.groupby("client_id")["aum"].sum()
        return divide(by_client.nlargest(10).sum(), by_client.sum())

    # ---- Part C helpers
    def sumx_by_client(self, ctx):
        """SUMX(VALUES(dim_client[client_id]), [Ending AUM]): each client's own last balance."""
        s = rows(self.snap, ctx)
        if s.empty:
            return np.nan
        last = s.groupby("client_id")["date"].transform("max")
        return s.loc[s["date"].eq(last), "aum"].sum()

    def weighted_alpha_incl_suspects(self, ctx):
        return self.weighted_alpha(ctx, include_suspect=True)

    def simple_mean_alpha(self, ctx):
        s = self.last_snapshot(ctx)
        s = s[s["is_return_suspect"].eq(0)]
        return s["active_alpha_ytd"].mean() if len(s) else np.nan

    def effective_fee_rate(self, ctx):
        """ICE 9 measure: annualized fees per dollar of the aum_basis that was billed."""
        f = rows(self.fees, ctx)
        if f.empty:
            return np.nan
        return divide(f["amount"].sum() * 12 * 10_000, f["aum_basis"].sum())


MEASURE_FUNCS = {
    "Total Fees": Measures.total_fees,
    "Net Flows": Measures.net_flows,
    "AUM (naive SUM)": Measures.naive_sum,
    "Ending AUM": Measures.ending_aum,
    "Ending Clients": Measures.ending_clients,
    "Avg AUM per Client": Measures.avg_aum_per_client,
    "Ending AUM LY": Measures.ending_aum_ly,
    "AUM YoY %": Measures.aum_yoy,
    "Ending AUM PM": Measures.ending_aum_pm,
    "AUM MoM %": Measures.aum_mom,
    "Avg Monthly AUM": Measures.avg_monthly_aum,
    "Fee Yield (bps)": Measures.fee_yield,
    "Organic Growth Rate": Measures.organic_growth,
    "AUM-Weighted Alpha": Measures.weighted_alpha,
    "Alpha Signal": Measures.alpha_signal,
    "Top 10 Client Share": Measures.top10_share,
    "Ending AUM SUMX by Client": Measures.sumx_by_client,
    "AUM-Weighted Alpha incl. Suspects": Measures.weighted_alpha_incl_suspects,
    "Simple Mean Alpha": Measures.simple_mean_alpha,
    "Effective Fee Rate (bps)": Measures.effective_fee_rate,
}
CORE = list(MEASURE_FUNCS)[:16]  # base measures + measures 0-11


# ------------------------------------------------------------------------ slices
def required_slices() -> list[tuple[str, str, Context]]:
    """(measure, slice label, context) for every row the handout requires."""
    out: list[tuple[str, str, Context]] = []
    total = Context(DATE_MIN, DATE_MAX)

    # Every measure at the grand total (plus the two base measures).
    for m in CORE:
        out.append((m, "Total", total))

    # Measures 1, 4, 6-10 by year, plus the naive SUM to show the trap year by year.
    by_year = ["AUM (naive SUM)", "Ending AUM", "Ending AUM LY", "AUM YoY %",
               "Avg Monthly AUM", "Fee Yield (bps)", "Organic Growth Rate",
               "AUM-Weighted Alpha", "Alpha Signal"]
    for year in range(2020, 2025):
        ctx = Context(pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31))
        out += [(m, f"year={year}", ctx) for m in by_year]

    # Measures 1, 3, 4, 7-11 by client tier, filtered to 2024.
    by_tier = ["Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %",
               "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha",
               "Alpha Signal", "Top 10 Client Share"]
    for tier in ["HNW", "Retail", "UHNW"]:
        ctx = Context(pd.Timestamp(2024, 1, 1), pd.Timestamp(2024, 12, 31), tier)
        out += [(m, f"client_tier={tier} | year=2024", ctx) for m in by_tier]

    # Measure 5 for December 2024.
    dec = Context(pd.Timestamp(2024, 12, 1), pd.Timestamp(2024, 12, 31))
    out += [(m, "year=2024 | month=12", dec) for m in ["Ending AUM", "Ending AUM PM", "AUM MoM %"]]

    # Part C evidence: (a) and (c) at the grand total, (b) for 2024.
    out += [(m, "Total", total) for m in ["Ending AUM SUMX by Client",
                                          "AUM-Weighted Alpha incl. Suspects",
                                          "Simple Mean Alpha"]]
    y2024 = Context(pd.Timestamp(2024, 1, 1), pd.Timestamp(2024, 12, 31))
    out.append(("Effective Fee Rate (bps)", "year=2024", y2024))
    return out


# ------------------------------------------------------------------ reconcile
def read_powerbi() -> pd.DataFrame:
    # DAX query view "Copy" pastes tab-separated text with headers such as "[measure]";
    # Export data writes a comma CSV. Accept both, and drop a UTF-8 byte-order mark.
    header = PBI_FILE.read_text(encoding="utf-8-sig").splitlines()[0]
    sep = "\t" if "\t" in header else ","
    pbi = pd.read_csv(PBI_FILE, dtype=str, keep_default_na=False, sep=sep, encoding="utf-8-sig")
    pbi.columns = [c.strip().strip("[]").lower() for c in pbi.columns]
    assert list(pbi.columns) == ["measure", "slice", "value"], f"bad columns: {list(pbi.columns)}"
    for col in pbi.columns:
        pbi[col] = pbi[col].str.strip()
    dupes = pbi.duplicated(["measure", "slice"])
    assert not dupes.any(), f"duplicate Power BI rows:\n{pbi[dupes]}"
    return pbi


def to_number(text: str) -> float:
    return np.nan if text == "" else float(text.replace(",", ""))


def compare(measure: str, pbi_text: str | None, pandas_value) -> tuple[str, str, float, bool]:
    kind = KIND[measure]
    if pbi_text is None:  # row missing from the Power BI export
        return "", fmt(pandas_value, kind), np.nan, False
    if kind == "text":
        return pbi_text, pandas_value, np.nan, pbi_text == pandas_value
    pbi_value = to_number(pbi_text)
    if pd.isna(pbi_value) and pd.isna(pandas_value):
        return "", "", np.nan, True
    if pd.isna(pbi_value) or pd.isna(pandas_value):
        return pbi_text, fmt(pandas_value, kind), np.nan, False
    diff = abs(pbi_value - pandas_value)
    return pbi_text, fmt(pandas_value, kind), diff, diff <= TOLERANCE[kind]


def fmt(value, kind: str) -> str:
    if kind == "text":
        return value
    if pd.isna(value):
        return ""
    return f"{value:.2f}" if kind in ("currency", "count") else f"{value:.10f}"


def main() -> int:
    measures = Measures(load())
    pbi = read_powerbi()
    lookup = {(m, s): v for m, s, v in pbi.itertuples(index=False)}

    records = []
    missing = []
    for measure, label, ctx in required_slices():
        pandas_value = MEASURE_FUNCS[measure](measures, ctx)
        if (measure, label) not in lookup:
            missing.append((measure, label))
        pbi_text, pandas_text, diff, match = compare(measure, lookup.get((measure, label)), pandas_value)
        records.append({
            "measure": measure,
            "slice": label,
            "powerbi_value": pbi_text,
            "pandas_value": pandas_text,
            "abs_diff": "" if pd.isna(diff) else f"{diff:.10f}",
            "match": match,
        })

    out = pd.DataFrame(records)
    REPORTS.mkdir(exist_ok=True)
    out.to_csv(OUT_FILE, index=False)

    extra = set(lookup) - {(r["measure"], r["slice"]) for r in records}
    print(f"Rows reconciled: {len(out)}")
    print(f"Rows matching:   {int(out['match'].sum())} of {len(out)}")
    if missing:
        print(f"Missing from powerbi_values.csv: {len(missing)}")
    if extra:
        print(f"Power BI rows not required (ignored): {len(extra)}")
    bad = out[~out["match"]]
    if not bad.empty:
        print("\nMISMATCHES:")
        print(bad.to_string(index=False))
        return 1
    print("All rows match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
