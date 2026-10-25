"""
02_clean.py - HW4 Part C: build a clean copy of the eight Wildcat Capital tables.

Reads data/raw/*.csv (never modified) and writes:
  data/clean/<same 8 file names>       same columns, plus 0/1 flag columns
  data/audit/cleaning_log.csv          table, issue, action, rows affected, note
  data/audit/value_changes.csv         table, key column, key, column, old, new
  data/audit/quarantine_*.csv          one file per quarantined set

Order of the steps (and why):
  1. dim_client de-duplication first: every fact check below joins to dim_client,
     so the dimension has to be right before the facts are judged against it.
  2. Format fixes (state codes, security_id text) before referential checks,
     because a '45.0' key never matches '45'.
  3. Value repairs that can be reconciled against other columns
     (shares sign, percent returns).
  4. Quarantine of rows that cannot be repaired (orphan transactions).
  5. Flags last, so they describe the final clean rows.
After every step the script prints rows affected and a before/after check,
and asserts the after-state. Any failed assert stops the run.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_common as dq  # noqa: E402

LOG, CHANGES, QUARANTINE = [], [], {}


def log(table, issue, action, rows, note=""):
    LOG.append({"table": table, "issue": issue, "action": action, "rows_affected": int(rows), "note": note})
    print(f"  [{table}] {issue} -> {action}: {rows:,} rows. {note}")


def record_changes(table, key_col, df_before, df_after, col, mask):
    idx = mask[mask].index
    CHANGES.append(pd.DataFrame({
        "table": table, "key_column": key_col, "key": df_before.loc[idx, key_col].values,
        "column": col, "old_value": df_before.loc[idx, col].values, "new_value": df_after.loc[idx, col].values,
    }))


def quarantine(table, name, rows, reason):
    q = rows.copy()
    q.insert(0, "quarantine_reason", reason)
    q.insert(0, "source_table", table)
    QUARANTINE.setdefault(table, []).append((name, q))


def header(text):
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)


def main():
    raw = dq.load_tables(dq.RAW_DIR)
    T = {t: df.copy() for t, df in raw.items()}
    raw_rows = {t: len(df) for t, df in raw.items()}
    for t in dq.TABLES:
        print(f"read {t:<26} {raw_rows[t]:>8,} rows")

    # ------------------------------------------------------------------ C1
    header("C1 dim_client: near-duplicate clients (last_name off by one letter)")
    c = T["dim_client"]
    compare = [x for x in c.columns if x not in ("client_id", "last_name")]
    pairs = c.merge(c, on=compare, suffixes=("_dup", "_orig"))
    pairs = pairs[pairs["client_id_dup"] != pairs["client_id_orig"]]
    # which copy is real? the one the fact tables use. A pair must have exactly one active side.
    used = set(T["fact_portfolio_snapshot"]["client_id"]) | set(T["fact_fees"]["client_id"]) \
        | set(T["fact_transactions"]["client_id"])
    pairs = pairs[~pairs["client_id_dup"].isin(used) & pairs["client_id_orig"].isin(used)]
    one_letter = (pairs["last_name_dup"].str.len() - pairs["last_name_orig"].str.len()).abs() == 1
    prefix = pairs.apply(lambda r: r["last_name_orig"].startswith(r["last_name_dup"])
                         or r["last_name_dup"].startswith(r["last_name_orig"]), axis=1)
    assert (one_letter & prefix).all(), "a pair differs by more than one trailing letter; review by hand"
    dup_ids = set(pairs["client_id_dup"])
    assert len(dup_ids) == len(pairs), "a duplicate matched more than one original"
    print(f"  before: {len(c):,} rows; {len(dup_ids)} rows match another client on all 12 other columns, "
          f"differ by one trailing letter of last_name, and have no fact rows")
    print(f"  examples: {pairs[['client_id_dup', 'last_name_dup', 'client_id_orig', 'last_name_orig']].head(3).values.tolist()}")
    # verify: no fact row references a duplicate id (so removal loses no activity)
    refs = {f: int(T[f]["client_id"].isin(dup_ids).sum()) for f in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions")}
    print(f"  fact rows referencing the duplicate ids: {refs}")
    assert sum(refs.values()) == 0, "a duplicate client id has fact activity; removal would orphan rows"
    orig_ids = set(pairs["client_id_orig"])
    assert orig_ids <= set(T["fact_portfolio_snapshot"]["client_id"]), "an original client has no snapshots"
    qrows = c[c["client_id"].isin(dup_ids)].merge(
        pairs[["client_id_dup", "client_id_orig", "last_name_orig"]].rename(
            columns={"client_id_dup": "client_id", "client_id_orig": "duplicate_of_client_id",
                     "last_name_orig": "duplicate_of_last_name"}), on="client_id")
    quarantine("dim_client", "dim_client_near_duplicates", qrows,
               "near-duplicate of an existing client: all other columns equal, last_name off by one letter, no fact rows")
    T["dim_client"] = c[~c["client_id"].isin(dup_ids)].copy()
    after = T["dim_client"]
    assert len(after) == len(c) - len(dup_ids)
    assert not after.duplicated(compare).any(), "near-duplicates remain"
    assert after["client_id"].is_unique
    print(f"  after: {len(after):,} rows; leave-last-name-out duplicates = {after.duplicated(compare).sum()}")
    log("dim_client", "near-duplicate client rows (ids 2501-2525, last_name off by one letter)", "quarantine",
        len(dup_ids), "each matched one original client on all 12 other columns; 0 fact rows referenced them")

    # ------------------------------------------------------------------ C2
    header("C2 dim_client.state: full state names -> USPS codes")
    c = T["dim_client"]
    before = c.copy()
    full = c["state"].isin(list(dq.US_STATES))
    print(f"  before: {full.sum()} full names {c.loc[full, 'state'].value_counts().to_dict()}")
    c.loc[full, "state"] = c.loc[full, "state"].map(dq.US_STATES)
    changed = before["state"] != c["state"]
    record_changes("dim_client", "client_id", before, c, "state", changed)
    assert c["state"].isin(dq.STATE_CODES).all(), "a state is still not a USPS code"
    assert changed.sum() == full.sum()
    # every replacement code already exists in the column, so no new states were invented
    assert set(c.loc[changed, "state"]) <= set(before.loc[~full, "state"])
    print(f"  after: {c['state'].nunique()} distinct values, all two-letter codes")
    log("dim_client", "state stored as full name in some rows", "standardize", changed.sum(),
        "mapped with a fixed USPS lookup; each code already used elsewhere in the column")

    # ------------------------------------------------------------------ C3
    header("C3 dim_client.risk_profile: blanks -> flag, no fill")
    c = T["dim_client"]
    blank = dq.is_blank(c["risk_profile"])
    sn = T["fact_portfolio_snapshot"]
    bench = sn[sn["client_id"].isin(c.loc[blank, "client_id"])].drop_duplicates("client_id")["benchmark_id"]
    print(f"  before: {blank.sum()} blank risk profiles; benchmark of those clients: {bench.value_counts().to_dict()}")
    c["flag_risk_profile_missing"] = blank.astype(int)
    assert c["flag_risk_profile_missing"].sum() == blank.sum()
    assert (c.loc[blank, "risk_profile"] == "").all()
    log("dim_client", "risk_profile blank", "flag (leave blank)", blank.sum(),
        "all sit on benchmark 3 (60/40), which also serves Balanced clients; benchmark is not proof of the profile")

    # ------------------------------------------------------------------ C4
    header("C4 fact_transactions.security_id: '45.0' -> '45'")
    t = T["fact_transactions"]
    before = t.copy()
    has = ~dq.is_blank(t["security_id"])
    floaty = has & t["security_id"].str.match(r"^\d+\.0$")
    print(f"  before: {has.sum():,} non-blank keys, {floaty.sum():,} stored as N.0")
    t.loc[floaty, "security_id"] = t.loc[floaty, "security_id"].str.replace(r"\.0$", "", regex=True)
    changed = before["security_id"] != t["security_id"]
    assert (pd.to_numeric(before.loc[changed, "security_id"]) == pd.to_numeric(t.loc[changed, "security_id"])).all(), \
        "numeric value changed"
    assert t.loc[has, "security_id"].str.match(r"^\d+$").all()
    record_changes("fact_transactions", "txn_id", before, t, "security_id", changed)
    print(f"  after: non-integer keys = {(~t.loc[has, 'security_id'].str.match(r'^[0-9]+$')).sum()}")
    log("fact_transactions", "security_id stored as float text (45.0)", "convert", changed.sum(),
        "format only; numeric value identical, now joins to dim_security")

    # ------------------------------------------------------------------ C5
    header("C5 fact_transactions.shares: negative share counts on Buy rows")
    before = t.copy()
    sh = pd.to_numeric(t["shares"], errors="coerce")
    pr = pd.to_numeric(t["price"], errors="coerce")
    am = pd.to_numeric(t["amount"], errors="coerce")
    neg = sh < 0
    rec_ok = ((sh.abs() * pr - am).abs() <= 0.011)
    print(f"  before: {neg.sum()} negative shares {t.loc[neg, 'txn_type'].value_counts().to_dict()}; "
          f"of these, |shares| x price reconciles to amount: {(neg & rec_ok).sum()}")
    assert (neg <= rec_ok).all(), "a negative-share row does not reconcile; cannot repair by sign flip"
    t.loc[neg, "shares"] = t.loc[neg, "shares"].str.lstrip("-")
    t["flag_shares_sign_corrected"] = neg.astype(int)
    changed = before["shares"] != t["shares"]
    record_changes("fact_transactions", "txn_id", before, t, "shares", changed)
    sh2 = pd.to_numeric(t["shares"], errors="coerce")
    assert (sh2.dropna() > 0).all()
    assert (((sh2 * pr - am).abs() <= 0.011) | sh2.isna()).all(), "shares x price no longer reconciles"
    print(f"  after: negative shares = {(sh2 < 0).sum()}; shares x price = amount on every trade row")
    log("fact_transactions", "negative shares on Buy rows", "convert (sign flip)", changed.sum(),
        "verified: |shares| x price = amount within $0.01 on every changed row")

    # ------------------------------------------------------------------ C6
    header("C6 fact_transactions: client_id not in dim_client")
    valid = set(T["dim_client"]["client_id"])
    orphan = ~t["client_id"].isin(valid)
    rest = [x for x in t.columns if x not in ("txn_id", "client_id", "flag_shares_sign_corrected")]
    twins = t[orphan].merge(t[~orphan][rest + ["txn_id", "client_id"]], on=rest, how="left",
                            suffixes=("", "_twin")).drop_duplicates("txn_id")
    has_twin = twins["txn_id_twin"].notna().sum()
    print(f"  before: {orphan.sum()} orphan rows, {t.loc[orphan, 'client_id'].nunique()} distinct ids "
          f"({t.loc[orphan, 'client_id'].astype(int).min()}-{t.loc[orphan, 'client_id'].astype(int).max()}); "
          f"rows that are exact copies of a valid transaction except client_id/txn_id: {has_twin}")
    q = twins.rename(columns={"txn_id_twin": "copy_of_txn_id", "client_id_twin": "copy_of_client_id"})
    quarantine("fact_transactions", "fact_transactions_orphan_client", q,
               "client_id not in dim_client; row duplicates an existing transaction of another client")
    T["fact_transactions"] = t = t[~orphan].copy()
    assert t["client_id"].isin(valid).all()
    assert len(t) == raw_rows["fact_transactions"] - orphan.sum()
    print(f"  after: {len(t):,} rows, orphan client_ids = 0")
    log("fact_transactions", "client_id with no dim_client row", "quarantine", orphan.sum(),
        f"{has_twin} of {orphan.sum()} are copies of another client's transaction; reassigning would double count")

    # ------------------------------------------------------------------ C7
    header("C7 fact_portfolio_snapshot.return_ytd: percent strings -> decimals")
    s = T["fact_portfolio_snapshot"]
    before = s.copy()
    pct = s["return_ytd"].str.endswith("%")
    conv = pd.to_numeric(s.loc[pct, "return_ytd"].str.rstrip("%"), errors="coerce") / 100
    implied = (pd.to_numeric(s.loc[pct, "benchmark_return_ytd"]) + pd.to_numeric(s.loc[pct, "active_alpha_ytd"]))
    gap = (conv - implied).abs()
    print(f"  before: {pct.sum()} values with '%'; max |converted - (benchmark + alpha)| = {gap.max():.6f}")
    # a 2-decimal percent carries +/- 0.005% = 0.00005 of rounding
    assert (gap <= 0.0000501).all(), "a converted percent does not reconcile to benchmark + alpha"
    # write the reconciled value (benchmark + alpha, 6 decimals) instead of the 2-decimal percent:
    # it agrees with the stated percent within rounding and keeps the alpha identity exact
    s.loc[pct, "return_ytd"] = implied.round(6).map(lambda v: f"{v:.6f}")
    changed = before["return_ytd"] != s["return_ytd"]
    record_changes("fact_portfolio_snapshot", "snapshot_id", before, s, "return_ytd", changed)
    _, ok = dq.parse(s["return_ytd"], "float")
    assert ok.all(), "return_ytd still has unparseable values"
    print(f"  after: unparseable return_ytd = {(~ok).sum()}")
    r2 = pd.to_numeric(s["return_ytd"])
    alpha_gap = (r2 - pd.to_numeric(s["benchmark_return_ytd"]) - pd.to_numeric(s["active_alpha_ytd"])).abs()
    assert (alpha_gap <= 2e-6).all(), "alpha identity broken after conversion"
    print(f"  after: max |return - benchmark - alpha| on all rows = {alpha_gap.max():.7f}")
    log("fact_portfolio_snapshot", "return_ytd stored as percent text (9.28%)", "convert (reconciled)", changed.sum(),
        "value/100 agrees with benchmark_return_ytd + active_alpha_ytd within 0.00005; stored the 6-decimal sum")

    # ------------------------------------------------------------------ C8
    header("C8 flags: suspicious values that cannot be corrected without inventing data")
    s = T["fact_portfolio_snapshot"]
    aum = pd.to_numeric(s["aum"])
    ry = pd.to_numeric(s["return_ytd"])
    s["flag_aum_floor"] = (aum == 1000).astype(int)
    s["flag_return_implausible"] = (ry > 1).astype(int)
    log("fact_portfolio_snapshot", "aum exactly $1,000.00", "flag", s["flag_aum_floor"].sum(),
        "looks like a source-system floor after withdrawals; true balance unknown")
    log("fact_portfolio_snapshot", "return_ytd above 100%", "flag", s["flag_return_implausible"].sum(),
        "return includes deposits on small accounts; alpha uses the same figure, so alpha is distorted too")
    assert s["flag_aum_floor"].sum() == (aum == 1000).sum()

    t = T["fact_transactions"]
    dd = T["dim_date"].set_index("date")["is_trading_day"]
    trade = t["txn_type"].isin(dq.TRADE_TYPES)
    t["flag_non_trading_day"] = (trade & (t["txn_date"].map(dd) == "0")).astype(int)
    log("fact_transactions", "Buy/Sell/Dividend dated on a weekend", "flag", t["flag_non_trading_day"].sum(),
        "true trade date unknown; amounts are unaffected")

    cl = T["dim_client"]
    last = T["fact_portfolio_snapshot"].groupby("client_id")["snapshot_date"].max()
    inactive = set(cl.loc[cl["is_active"] == "False", "client_id"])
    month_end = pd.to_datetime(t["client_id"].map(last)) + pd.offsets.MonthEnd(0)
    after_exit = t["client_id"].isin(inactive) & (pd.to_datetime(t["txn_date"]) > month_end)
    t["flag_after_client_exit"] = after_exit.astype(int)
    log("fact_transactions", "inactive client activity after final snapshot month", "flag", after_exit.sum(),
        "either the exit date or the transaction date is wrong; cannot tell which")
    assert t["flag_non_trading_day"].isin([0, 1]).all() and t["flag_after_client_exit"].isin([0, 1]).all()

    # ------------------------------------------------------------------ pass-through tables
    header("Tables with no defects that need a change")
    for name in ("dim_advisor", "dim_benchmark", "dim_date", "dim_security", "fact_fees"):
        assert T[name].equals(raw[name])
        log(name, "no correctable defect found", "leave as is", 0, "copied unchanged; see decision_log.md")

    # ------------------------------------------------------------------ write + prove row counts
    header("Write outputs and prove raw = clean + quarantined")
    dq.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    dq.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    proof = []
    for name in dq.TABLES:
        df = T[name]
        # same columns, same order; flags only appended at the end
        assert list(df.columns[: raw[name].shape[1]]) == list(raw[name].columns), f"{name} columns changed"
        extra = [x for x in df.columns[raw[name].shape[1]:]]
        assert all(x.startswith("flag_") for x in extra)
        df.to_csv(dq.CLEAN_DIR / f"{name}.csv", index=False)
        nq = 0
        for qname, q in QUARANTINE.get(name, []):
            q.to_csv(dq.AUDIT_DIR / f"quarantine_{qname}.csv", index=False)
            nq += len(q)
        assert raw_rows[name] == len(df) + nq, f"{name}: raw {raw_rows[name]} != clean {len(df)} + quarantined {nq}"
        # a quarantined key must not also appear in clean
        pk = dq.SCHEMA[name]["pk"]
        for _, q in QUARANTINE.get(name, []):
            assert not q[pk].isin(df[pk]).any()
        proof.append({"table": name, "raw_rows": raw_rows[name], "clean_rows": len(df), "quarantined_rows": nq,
                      "flag_columns_added": ", ".join(extra)})
    proof = pd.DataFrame(proof)
    print(proof.to_string(index=False))
    proof.to_csv(dq.AUDIT_DIR / "row_count_proof.csv", index=False)

    pd.DataFrame(LOG).to_csv(dq.AUDIT_DIR / "cleaning_log.csv", index=False)
    vc = pd.concat(CHANGES, ignore_index=True)
    vc.to_csv(dq.AUDIT_DIR / "value_changes.csv", index=False)
    print(f"\ncleaning_log.csv: {len(LOG)} entries")
    print(f"value_changes.csv: {len(vc):,} cell changes {vc.groupby(['table', 'column']).size().to_dict()}")
    print("Clean files written to", dq.CLEAN_DIR)


if __name__ == "__main__":
    main()
