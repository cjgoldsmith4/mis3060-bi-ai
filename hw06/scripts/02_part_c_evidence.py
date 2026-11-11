"""HW6 Part C: pandas evidence for design questions (a) to (d).

Writes reports/part_c_evidence.csv (question, item, value) and prints it.
Run from the hw06 folder:  python scripts/02_part_c_evidence.py
"""
from pathlib import Path

import pandas as pd

HW = Path(__file__).resolve().parents[1]
DATA = HW / "data" / "clean"
OUT = HW / "reports" / "part_c_evidence.csv"

client = pd.read_csv(DATA / "dim_client.csv", usecols=["client_id", "client_tier"])
snap = pd.read_csv(DATA / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
fees = pd.read_csv(DATA / "fact_fees.csv", parse_dates=["fee_date"])
txns = pd.read_csv(DATA / "fact_transactions.csv", usecols=["client_id", "txn_date", "txn_type", "amount"],
                   parse_dates=["txn_date"])
snap = snap.merge(client, on="client_id", validate="many_to_one")
txns = txns.merge(client, on="client_id", validate="many_to_one")

rows = []


def add(question, item, value):
    rows.append({"question": question, "item": item, "value": value})


# (a) Ending AUM vs SUMX of each client's own last balance -----------------------------
last_date = snap["snapshot_date"].max()
ending_aum = snap.loc[snap["snapshot_date"].eq(last_date), "aum"].sum()
own_last = snap.groupby("client_id")["snapshot_date"].transform("max")
last_rows = snap[snap["snapshot_date"].eq(own_last)]
sumx = last_rows["aum"].sum()
departed = last_rows[last_rows["snapshot_date"].lt(last_date)]
add("a", "Ending AUM (last snapshot date)", round(ending_aum, 2))
add("a", "SUMX over clients of each client's own Ending AUM", round(sumx, 2))
add("a", "Difference", round(sumx - ending_aum, 2))
add("a", "Clients whose last snapshot is before the last date", len(departed))
add("a", "Their last balances (sum)", round(departed["aum"].sum(), 2))
add("a", "Earliest last snapshot among them", departed["snapshot_date"].min().date().isoformat())
add("a", "Latest last snapshot among them", departed["snapshot_date"].max().date().isoformat())
assert abs((sumx - ending_aum) - departed["aum"].sum()) < 0.01

# (b) Fee Yield vs Effective Fee Rate ------------------------------------------------------
m = snap.merge(fees[["client_id", "fee_date", "amount", "aum_basis"]],
               left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"],
               how="left", indicator=True)
assert (m["_merge"].eq("both") | m["_merge"].eq("left_only")).all()
assert len(fees) == m["_merge"].eq("both").sum(), "every fee row matches a snapshot"
matched = m[m["_merge"].eq("both")]
assert (matched["aum"] - matched["aum_basis"]).abs().max() < 0.005, "aum_basis = aum where billed"
m["no_fee"] = m["_merge"].eq("left_only")
y = m[m["snapshot_date"].dt.year.eq(2024)]
f24 = fees[fees["fee_date"].dt.year.eq(2024)]
fee_yield = f24["amount"].sum() * 12 * 10_000 / y["aum"].sum()
eff_rate = f24["amount"].sum() * 12 * 10_000 / f24["aum_basis"].sum()
unbilled_share = y.loc[y["no_fee"], "aum"].sum() / y["aum"].sum()
add("b", "2024 Fee Yield (bps): fees / all snapshot aum", round(fee_yield, 4))
add("b", "2024 Effective Fee Rate (bps): fees / billed aum_basis", round(eff_rate, 4))
add("b", "Ratio Fee Yield / Effective Fee Rate", round(fee_yield / eff_rate, 6))
add("b", "2024 share of snapshot aum with no fee row", round(unbilled_share, 6))
add("b", "1 - unbilled share (equals the ratio)", round(1 - unbilled_share, 6))
add("b", "2024 snapshot months with no fee row", int(y["no_fee"].sum()))
add("b", "2024 snapshot months", len(y))
add("b", "All years: snapshot months with no fee row", int(m["no_fee"].sum()))
add("b", "All years: snapshot months", len(m))
add("b", "Fee rows with no snapshot", 0)
add("b", "Clients with at least one unbilled month", int(m.loc[m["no_fee"], "client_id"].nunique()))
for year, share in m.groupby(m["snapshot_date"].dt.year)["no_fee"].mean().items():
    add("b", f"Unbilled month rate {year}", round(share, 4))
for tier, share in m.groupby("client_tier")["no_fee"].mean().items():
    add("b", f"Unbilled month rate {tier}", round(share, 4))
assert abs(fee_yield / eff_rate - (1 - unbilled_share)) < 1e-9

# (c) Alpha at the last snapshot --------------------------------------------------------
last = snap[snap["snapshot_date"].eq(last_date)]
clean = last[last["is_return_suspect"].eq(0)]
sus = last[last["is_return_suspect"].eq(1)]


def wavg(df):
    return (df["aum"] * df["active_alpha_ytd"]).sum() / df["aum"].sum()


add("c", "AUM-weighted alpha, suspects excluded", round(wavg(clean), 6))
add("c", "AUM-weighted alpha, suspects included", round(wavg(last), 6))
add("c", "Simple mean alpha, suspects excluded", round(clean["active_alpha_ytd"].mean(), 6))
add("c", "Suspect rows at last snapshot", len(sus))
add("c", "Suspect share of last-snapshot AUM", round(sus["aum"].sum() / last["aum"].sum(), 6))
add("c", "Suspect alpha max", round(sus["active_alpha_ytd"].max(), 6))
add("c", "Non-suspect alpha max", round(clean["active_alpha_ytd"].max(), 6))
add("c", "Non-suspect alpha min", round(clean["active_alpha_ytd"].min(), 6))
dec24 = snap[snap["snapshot_date"].dt.year.eq(2024) & snap["is_return_suspect"].eq(0)]
add("c", "2024 weighted alpha if all 12 months are pooled", round(wavg(dec24), 6))

# (d) Organic growth vs YoY by tier, 2024 ----------------------------------------------
for tier in ["HNW", "Retail", "UHNW"]:
    s = snap[snap["client_tier"].eq(tier)]
    end = s.loc[s["snapshot_date"].eq(pd.Timestamp("2024-12-01")), "aum"].sum()
    ly = s.loc[s["snapshot_date"].eq(pd.Timestamp("2023-12-01")), "aum"].sum()
    t = txns[txns["client_tier"].eq(tier) & txns["txn_date"].dt.year.eq(2024)]
    flows = (t.loc[t["txn_type"].eq("Deposit"), "amount"].sum()
             - t.loc[t["txn_type"].eq("Withdrawal"), "amount"].sum())
    add("d", f"{tier} Ending AUM 2024", round(end, 2))
    add("d", f"{tier} share of 2024 Ending AUM", None)
    add("d", f"{tier} Net Flows 2024", round(flows, 2))
    add("d", f"{tier} AUM change 2024", round(end - ly, 2))
    add("d", f"{tier} Organic Growth Rate", round(flows / ly, 6))
    add("d", f"{tier} AUM YoY %", round((end - ly) / ly, 6))
    add("d", f"{tier} YoY minus organic (non-flow growth)", round((end - ly) / ly - flows / ly, 6))
total_end = snap.loc[snap["snapshot_date"].eq(pd.Timestamp("2024-12-01")), "aum"].sum()
for r in rows:
    if r["item"].endswith("share of 2024 Ending AUM"):
        tier = r["item"].split()[0]
        r["value"] = round(next(x["value"] for x in rows if x["item"] == f"{tier} Ending AUM 2024") / total_end, 6)

out = pd.DataFrame(rows)
OUT.parent.mkdir(exist_ok=True)
out.to_csv(OUT, index=False)
print(out.to_string(index=False))
