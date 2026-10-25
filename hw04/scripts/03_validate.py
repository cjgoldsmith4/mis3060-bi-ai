"""
03_validate.py - HW4 Part D: referential integrity, rule checks,
cross-table reconciliations, IQR outliers, and the before/after scorecard.

Runs every check on both data/raw and data/clean.

Outputs (reports/)
  ri_results.csv               13 relationships x 2 stages
  rule_checks.csv              every row rule x table x stage
  reconciliations.csv          recomputed vs stored values, raw and clean
  outliers_iqr.csv             IQR fences and flag counts
  data_quality_scorecard.csv   one row per table per stage
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_common as dq  # noqa: E402


# ======================================================================
# Reusable referential-integrity check (keep for Assignment 5)
# ======================================================================
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key):
    """Check that every non-null fact_df[fact_key] exists in dim_df[dim_key].

    Keys are compared as stripped text, exactly as a BI tool joins two text
    columns, so '45.0' does NOT match '45'. Blank keys count as nulls and are
    excluded from the match rate (a null key is a completeness question, not
    an orphan).

    Returns a dict:
      fact_rows, null_keys, null_key_rate, checked_rows, matched_rows,
      match_rate (share of non-null keys found in the dimension),
      orphan_row_count, orphan_rows (DataFrame), distinct_orphan_keys (list)
    """
    fk = fact_df[fact_key].astype(str).str.strip()
    null = fk.isin(["", "nan", "None", "NaN"])
    dim_keys = set(dim_df[dim_key].astype(str).str.strip())
    present = fk[~null]
    matched = present.isin(dim_keys)
    orphans = fact_df.loc[present.index[~matched.to_numpy()]]
    n = len(fact_df)
    return {
        "fact_rows": n,
        "null_keys": int(null.sum()),
        "null_key_rate": float(null.mean()) if n else 0.0,
        "checked_rows": int(len(present)),
        "matched_rows": int(matched.sum()),
        "match_rate": float(matched.mean()) if len(present) else 1.0,
        "orphan_row_count": int(len(orphans)),
        "orphan_rows": orphans,
        "distinct_orphan_keys": sorted(present[~matched].unique().tolist(), key=lambda x: (len(x), x)),
    }


# ======================================================================
# Checks
# ======================================================================
def run_ri(T, stage):
    rows = []
    for fact, fk, dim, dk in dq.RELATIONSHIPS:
        r = check_referential_integrity(T[fact], fk, T[dim], dk)
        rows.append({
            "stage": stage, "relationship": f"{fact}.{fk} -> {dim}.{dk}", "fact_table": fact,
            "fact_rows": r["fact_rows"], "null_keys": r["null_keys"], "null_key_rate_pct": round(100 * r["null_key_rate"], 4),
            "checked_rows": r["checked_rows"], "matched_rows": r["matched_rows"],
            "match_rate_pct": round(100 * r["match_rate"], 4), "orphan_rows": r["orphan_row_count"],
            "distinct_orphan_keys": len(r["distinct_orphan_keys"]),
            "orphan_key_examples": "; ".join(r["distinct_orphan_keys"][:5]),
        })
    return rows


def run_rules(T, stage):
    rows = []
    for t in dq.TABLES:
        df = T[t]
        for name, col, fail in dq.column_rule_masks(df, t):
            rows.append({"stage": stage, "table": t, "column": col, "rule": name, "kind": "column bound / code list",
                         "rows": len(df), "failures": int(fail.sum()), "pass_pct": round(100 * (1 - fail.mean()), 4)})
        for name, col, fail, sev in dq.row_consistency_masks(df, t):
            rows.append({"stage": stage, "table": t, "column": col, "rule": name, "kind": "in-row consistency",
                         "rows": len(df), "failures": int(fail.sum()), "pass_pct": round(100 * (1 - fail.mean()), 4)})
    return rows


def run_reconciliations(T, stage):
    out = []
    tx, fe, sn = T["fact_transactions"], T["fact_fees"], T["fact_portfolio_snapshot"]

    def rec(name, stored, recomputed, tol, note):
        both = stored.notna() & recomputed.notna()
        diff = (stored - recomputed).abs()
        fails = int((both & (diff > tol)).sum())
        out.append({"stage": stage, "reconciliation": name, "rows_compared": int(both.sum()),
                    "rows_unparseable": int((~both).sum()), "rows_failed": fails,
                    "pass_pct": round(100 * (1 - fails / both.sum()), 4) if both.sum() else 0.0,
                    "max_abs_diff": round(float(diff[both].max()), 6) if both.any() else None,
                    "tolerance": tol, "note": note})

    tr = tx[tx["txn_type"].isin(dq.TRADE_TYPES)]
    sh = pd.to_numeric(tr["shares"], errors="coerce")
    pr = pd.to_numeric(tr["price"], errors="coerce")
    am = pd.to_numeric(tr["amount"], errors="coerce")
    rec("txn amount = shares x price (signed)", am, sh * pr, 0.011,
        "signed shares: a negative share count makes the product negative")
    rec("txn amount = |shares| x price", am, sh.abs() * pr, 0.011, "sign ignored")

    ab, bp, fa = (pd.to_numeric(fe[c], errors="coerce") for c in ("aum_basis", "bps_charged", "amount"))
    rec("fee amount = aum_basis x bps / 10000 / 12", fa, (ab * bp / 10000 / 12).round(2), 0.011, "monthly fee")

    m = fe.merge(sn[["client_id", "snapshot_date", "aum"]], left_on=["client_id", "fee_date"],
                 right_on=["client_id", "snapshot_date"], how="left")
    rec("fee aum_basis = snapshot aum (client-month)", pd.to_numeric(m["aum_basis"], errors="coerce"),
        pd.to_numeric(m["aum"], errors="coerce"), 0.011, "fact_fees vs fact_portfolio_snapshot")

    ry = pd.to_numeric(sn["return_ytd"], errors="coerce")
    by = pd.to_numeric(sn["benchmark_return_ytd"], errors="coerce")
    al = pd.to_numeric(sn["active_alpha_ytd"], errors="coerce")
    rec("return_ytd = benchmark_return_ytd + active_alpha_ytd", ry, by + al, 5.1e-5,
        "tolerance covers 2-decimal percent strings converted in cleaning")

    cl = T["dim_client"][["client_id", "advisor_id"]].drop_duplicates("client_id")
    for name, f in (("fact_fees", fe), ("fact_portfolio_snapshot", sn), ("fact_transactions", tx)):
        m = f[["client_id", "advisor_id"]].merge(cl, on="client_id", how="left", suffixes=("", "_dim"))
        a1 = pd.to_numeric(m["advisor_id"], errors="coerce")
        a2 = pd.to_numeric(m["advisor_id_dim"], errors="coerce")
        rec(f"{name}.advisor_id = dim_client.advisor_id", a1, a2, 0, "unmatched clients count as unparseable")
    return out


def iqr_flags(series):
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return lo, hi, (series < lo) | (series > hi)


def run_iqr(T, stage):
    out = []
    targets = [
        ("fact_portfolio_snapshot", "aum", None),
        ("fact_fees", "amount", None),
        ("fact_transactions", "amount", "txn_type"),
        ("dim_client", "initial_aum", "client_tier"),
    ]
    for t, col, by in targets:
        df = T[t]
        vals = pd.to_numeric(df[col], errors="coerce")
        groups = [("all", vals)] if by is None else [(g, vals[df[by] == g]) for g in sorted(df[by].unique())]
        for g, v in groups:
            v = v.dropna()
            lo, hi, flag = iqr_flags(v)
            out.append({"stage": stage, "table": t, "column": col, "group": g, "rows": len(v),
                        "q1": round(v.quantile(.25), 2), "q3": round(v.quantile(.75), 2),
                        "lower_fence": round(lo, 2), "upper_fence": round(hi, 2),
                        "flagged_low": int((v < lo).sum()), "flagged_high": int((v > hi).sum()),
                        "flagged_pct": round(100 * flag.mean(), 3), "max_value": round(v.max(), 2)})
    return out


def scorecard(T, stage):
    rows = []
    for t in dq.TABLES:
        df = T[t]
        spec = dq.SCHEMA[t]
        req_cells = filled = nonblank = valid = 0
        for col, cs in spec["cols"].items():
            req = dq.required_mask(df, cs)
            blank = dq.is_blank(df[col])
            req_cells += int(req.sum())
            filled += int((req & ~blank).sum())
            _, ok = dq.parse(df[col], cs["type"])
            nonblank += int((~blank).sum())
            valid += int(ok.sum())
        pk = spec["pk"]
        rules = dq.row_rule_table(df, t)
        row_pass = (~rules.any(axis=1)).mean() if rules.shape[1] else 1.0
        fks = [r for r in dq.RELATIONSHIPS if r[0] == t]
        chk = mat = 0
        for fact, fk, dim, dk in fks:
            r = check_referential_integrity(df, fk, T[dim], dk)
            chk += r["checked_rows"]
            mat += r["matched_rows"]
        rows.append({
            "table": t, "stage": stage, "rows": len(df),
            "pct_completeness": round(100 * filled / req_cells, 4),
            "pct_key_uniqueness": round(100 * df[pk].nunique() / len(df), 4),
            "pct_type_validity": round(100 * valid / nonblank, 4),
            "pct_rule_pass": round(100 * row_pass, 4),
            "pct_referential_match": round(100 * mat / chk, 4) if fks else "n/a (no FK)",
        })
    return rows


def main():
    raw = dq.load_tables(dq.RAW_DIR)
    clean = dq.load_tables(dq.CLEAN_DIR)
    dq.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    ri, rules, recs, iqr, score = [], [], [], [], []
    for stage, T in (("raw", raw), ("clean", clean)):
        print(f"validating {stage} ...")
        ri += run_ri(T, stage)
        rules += run_rules(T, stage)
        recs += run_reconciliations(T, stage)
        iqr += run_iqr(T, stage)
        score += scorecard(T, stage)

    ri, rules, recs, iqr, score = map(pd.DataFrame, (ri, rules, recs, iqr, score))
    ri.to_csv(dq.REPORTS_DIR / "ri_results.csv", index=False)
    rules.to_csv(dq.REPORTS_DIR / "rule_checks.csv", index=False)
    recs.to_csv(dq.REPORTS_DIR / "reconciliations.csv", index=False)
    iqr.to_csv(dq.REPORTS_DIR / "outliers_iqr.csv", index=False)
    score = score.sort_values(["table", "stage"], ascending=[True, False])
    score.to_csv(dq.REPORTS_DIR / "data_quality_scorecard.csv", index=False)

    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 60)
    print("\n=== Referential integrity (13 relationships) ===")
    print(ri[["stage", "relationship", "match_rate_pct", "orphan_rows", "distinct_orphan_keys",
              "null_key_rate_pct"]].to_string(index=False))
    print("\n=== Rules with failures ===")
    piv = rules.pivot_table(index=["table", "rule"], columns="stage", values="failures", aggfunc="sum")
    print(piv[(piv.fillna(0) > 0).any(axis=1)][["raw", "clean"]].to_string())
    print("\n=== Cross-table reconciliations ===")
    print(recs[["stage", "reconciliation", "rows_compared", "rows_unparseable", "rows_failed", "pass_pct"]].to_string(index=False))
    print("\n=== IQR outlier flags (clean) ===")
    print(iqr[iqr.stage == "clean"][["table", "column", "group", "upper_fence", "flagged_high", "flagged_pct"]].to_string(index=False))
    print("IQR flags mark values far from the middle of the distribution; a flagged amount is "
          "unusual, not wrong, unless another rule or reconciliation also fails for that row.")
    print("\n=== Data quality scorecard ===")
    print(score.to_string(index=False))

    # the clean stage must hold its promises
    c = ri[ri.stage == "clean"]
    assert (c["orphan_rows"] == 0).all(), "clean data still has orphan foreign keys"
    cr = rules[rules.stage == "clean"]
    assert cr["failures"].sum() == 0, "clean data still fails a row rule"
    cc = recs[recs.stage == "clean"]
    assert (cc["rows_failed"] == 0).all() and (cc["rows_unparseable"] == 0).all(), "a clean reconciliation failed"
    print("\nAll clean-stage assertions passed.")


if __name__ == "__main__":
    main()
