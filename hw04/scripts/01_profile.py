"""
01_profile.py - HW4 Part A: audit the raw Wildcat Capital tables.

Usage:  python scripts/01_profile.py            (profiles every CSV in data/raw)
        python scripts/01_profile.py some.csv   (profiles any other CSV file)

profile_column() and profile_table() work on any table. If a table has an
entry in dq_common.SCHEMA the expected type comes from there; otherwise the
type is inferred from the dominant value shape.

Outputs
  reports/profile_raw.csv     one row per table-column
  reports/dq_summary_raw.csv  one row per finding, tagged ERROR / WARN / INFO
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_common as dq  # noqa: E402

# reuse the single RI function that lives in 03_validate.py
_spec = importlib.util.spec_from_file_location("validate", Path(__file__).resolve().parent / "03_validate.py")
_validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validate)
check_referential_integrity = _validate.check_referential_integrity



# ---------------------------------------------------------------- generic profiling
def value_shape(v):
    """Collapse a value to its shape: letters -> A, digit runs -> 9, sign dropped.
    '9.28%' -> '9.9%', '-0.0123' -> '9.9', '45.0' -> '9.9', 'New York' -> 'A A'."""
    return re.sub(r"\d+", "9", re.sub(r"[A-Za-z]+", "A", v.lstrip("+-")))


def infer_type(s):
    nb = s[~dq.is_blank(s)]
    if nb.empty:
        return "str"
    for typ in ("int", "float", "date", "bool", "bool01"):
        _, ok = dq.parse(nb, typ)
        if ok.mean() >= 0.95:
            return typ
    return "str"


def profile_column(s, table, column, expected_type=None):
    expected_type = expected_type or infer_type(s)
    blank = dq.is_blank(s)
    nb = s[~blank]
    shapes = Counter(value_shape(v) for v in nb)
    top = shapes.most_common(4)
    vals, ok = dq.parse(s, expected_type)
    fail = (~ok & ~blank)
    ws = (s != s.str.strip()) | s.str.contains(r"\s{2,}", regex=True)
    # text columns legitimately mix shapes ('Balanced' vs 'Moderately Aggressive');
    # their allowed-value and pattern rules catch real format problems instead
    mixed = len(shapes) > 1 and expected_type != "str"
    row = {
        "table": table, "column": column, "expected_type": expected_type, "rows": len(s),
        "blank_count": int(blank.sum()), "blank_pct": round(100 * blank.mean(), 3),
        "distinct_count": int(s.nunique()),
        "dominant_shapes": "; ".join(f"{k} ({v})" for k, v in top),
        "dominant_shape_pct": round(100 * top[0][1] / len(nb), 3) if top else 0.0,
        "n_shapes": len(shapes),
        "nondominant_count": int(len(nb) - top[0][1]) if top else 0,
        "parse_fail_count": int(fail.sum()), "parse_fail_pct": round(100 * fail.sum() / max(len(nb), 1), 3),
        "parse_fail_examples": "; ".join(nb[fail[~blank]].unique()[:3]),
        "whitespace_issues": int(ws.sum()),
        "mixed_formats": bool(mixed),
        "min": "", "max": "",
    }
    if expected_type in ("int", "float", "bool01"):
        row["min"], row["max"] = vals.min(), vals.max()
    elif expected_type == "date":
        row["min"] = vals.min().date() if vals.notna().any() else ""
        row["max"] = vals.max().date() if vals.notna().any() else ""
    return row


def profile_table(df, table):
    spec = dq.SCHEMA.get(table, {}).get("cols", {})
    return [profile_column(df[c], table, c, spec.get(c, {}).get("type")) for c in df.columns]


# ---------------------------------------------------------------- findings
FINDINGS = []


def add(group, table, column, check, severity, n, total, note="", example=""):
    FINDINGS.append({
        "check_group": group, "table": table, "column": column, "check": check,
        "severity": severity if n else "INFO", "rows_affected": int(n), "rows_checked": int(total),
        "pct_affected": round(100 * n / total, 4) if total else 0.0,
        "example": str(example)[:120], "note": note,
    })


def column_level(df, table, prof):
    """Group 1: type, allowed values, ranges, key uniqueness."""
    schema = dq.SCHEMA.get(table)
    for p in prof:
        col = p["column"]
        if p["parse_fail_count"]:
            add("1 column", table, col, f"values fail to parse as {p['expected_type']}", "ERROR",
                p["parse_fail_count"], p["rows"] - p["blank_count"], "will break type conversion in a BI tool",
                p["parse_fail_examples"])
        if p["whitespace_issues"]:
            add("1 column", table, col, "leading/trailing/double whitespace", "WARN", p["whitespace_issues"], p["rows"])
        if p["mixed_formats"]:
            add("1 column", table, col, "mixed value shapes (rows outside the dominant shape)", "WARN",
                p["nondominant_count"], p["rows"] - p["blank_count"], f"shapes: {p['dominant_shapes']}")
        if schema is None:
            continue
        spec = schema["cols"].get(col, {})
        req = dq.required_mask(df, spec)
        blank = dq.is_blank(df[col])
        n_req_blank = (req & blank).sum()
        if n_req_blank:
            add("1 column", table, col, "blank where a value is required", "ERROR" if col == schema["pk"] else "WARN",
                n_req_blank, int(req.sum()), "completeness defect")
        if callable(spec.get("required")) and (~req & blank).sum():
            add("1 column", table, col, "blank by design (not applicable to these rows)", "INFO",
                (~req & blank).sum(), len(df), "legitimate structure, not a defect")
    if schema:
        for name, col, fail in dq.column_rule_masks(df, table):
            ex = df.loc[fail, col].unique()[:3]
            add("1 column", table, col, name, "ERROR", fail.sum(), len(df), "", "; ".join(ex))
        for key in [schema["pk"]] + schema.get("unique", []):
            d = df[key].duplicated(keep=False).sum()
            add("1 column", table, key, "key uniqueness", "ERROR", d, len(df),
                f"{df[key].nunique()} distinct of {len(df)} rows")


def single_table(df, table):
    """Group 2: duplicates, near-duplicates, in-row contradictions."""
    pk = dq.SCHEMA.get(table, {}).get("pk", df.columns[0])
    rest = [c for c in df.columns if c != pk]
    add("2 single-table", table, "*", "exact duplicate rows (ignoring key)", "ERROR",
        df.duplicated(rest).sum(), len(df))
    # near-duplicates: rows identical on every column but one (generic leave-one-out test)
    for col in rest:
        others = [c for c in rest if c != col]
        if len(others) < 3:
            continue
        mask = df.duplicated(others, keep=False) & ~df.duplicated(rest, keep=False)
        if mask.any():
            ex = df.loc[mask].sort_values(others).head(2)
            add("2 single-table", table, col, f"near-duplicate rows: identical except {col}", "WARN",
                mask.sum(), len(df), "pairs that differ in one column",
                " | ".join(f"{r[pk]}:{r[col]}" for _, r in ex.iterrows()))
    if table in dq.SCHEMA:
        for name, col, fail, sev in dq.row_consistency_masks(df, table):
            ex = df.loc[fail, pk].head(3).tolist()
            add("2 single-table", table, col, name, sev, fail.sum(), len(df), "", ex)


def referential(T):
    """Group 3: every foreign key must point to an existing primary key."""
    for fact, fk, dim, dk in dq.RELATIONSHIPS:
        r = check_referential_integrity(T[fact], fk, T[dim], dk)
        add("3 referential", fact, fk, f"{fk} -> {dim}.{dk}", "ERROR", r["orphan_row_count"], r["checked_rows"],
            f"match {r['match_rate']:.4%}; null-key rate {r['null_key_rate']:.4%}; "
            f"{len(r['distinct_orphan_keys'])} distinct orphan keys",
            "; ".join(map(str, r["distinct_orphan_keys"][:5])))
        if r["null_keys"]:
            add("3 referential", fact, fk, "null foreign keys", "INFO", r["null_keys"], r["fact_rows"],
                "check whether nulls are structural (see group 1)")
        used = set(T[fact][fk].str.strip())
        unused = sorted(set(T[dim][dk]) - used, key=lambda x: (len(x), x))
        if unused and dim != "dim_date":
            add("3 referential", dim, dk, f"{dim} members never used by {fact}.{fk}", "INFO", len(unused),
                len(T[dim]), "unused dimension members are fine; listed for awareness", "; ".join(unused[:6]))


def info_notes(T):
    """INFO findings: odd-looking values that are legitimate."""
    c = T["dim_client"]
    n = c["zip_code"].str.startswith("0").sum()
    add("1 column", "dim_client", "zip_code", "ZIPs with a leading zero (kept as text)", "INFO", 0, len(c),
        f"{n} ZIPs start with 0; numeric parsing would drop it")
    a = T["dim_advisor"]
    add("1 column", "dim_advisor", "certifications", "literal 'None' = no certification", "INFO", 0, len(a),
        f"{(a['certifications'] == 'None').sum()} advisors; default pd.read_csv turns this into NaN")
    s = T["fact_portfolio_snapshot"]
    sci = s["return_ytd"].str.contains("e-", regex=False).sum() + s["active_alpha_ytd"].str.contains("e-", regex=False).sum()
    add("1 column", "fact_portfolio_snapshot", "return_ytd / active_alpha_ytd",
        "scientific notation (valid floats, e.g. 1.2e-05)", "INFO", 0, len(s), f"{sci} cells")
    pct = s["return_ytd"].str.endswith("%")
    ry = pd.to_numeric(s["return_ytd"].str.rstrip("%"), errors="coerce").where(~pct, lambda v: v / 100)
    add("1 column", "fact_portfolio_snapshot", "return_ytd", "return_ytd > 100% (implausible YTD return)", "WARN",
        (ry > 1).sum(), len(s), "small accounts with large deposits; return includes cash flows")
    add("1 column", "fact_portfolio_snapshot", "aum", "aum exactly 1000.00 (looks like a floor)", "WARN",
        (pd.to_numeric(s["aum"]) == 1000).sum(), len(s), "source system appears to floor balances at $1,000")
    d = T["dim_date"]
    add("1 column", "dim_date", "is_trading_day", "trading day = weekday only (no market holidays)", "INFO", 0, len(d),
        f"{(d['is_trading_day'] == '1').sum()} trading days; NYSE holidays are marked as trading days")


def main(paths=None):
    dq.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if paths:  # profile arbitrary CSVs (generic mode)
        prof = []
        for p in paths:
            df = dq.read_table(p)
            prof += profile_table(df, Path(p).stem)
        pd.DataFrame(prof).to_csv(dq.REPORTS_DIR / "profile_adhoc.csv", index=False)
        print(pd.DataFrame(prof).to_string())
        return

    T = dq.load_tables(dq.RAW_DIR)
    profile_rows = []
    for t, df in T.items():
        print(f"profiling {t:<26} {len(df):>8,} rows x {df.shape[1]} cols")
        prof = profile_table(df, t)
        profile_rows += prof
        column_level(df, t, prof)
        single_table(df, t)
    referential(T)
    info_notes(T)
    FINDINGS.extend(dq.cross_table_checks(T))

    prof_df = pd.DataFrame(profile_rows)
    prof_df.to_csv(dq.REPORTS_DIR / "profile_raw.csv", index=False)
    fd = pd.DataFrame(FINDINGS)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    fd = fd.sort_values(["severity", "check_group", "table"], key=lambda s: s.map(order) if s.name == "severity" else s)
    fd.to_csv(dq.REPORTS_DIR / "dq_summary_raw.csv", index=False)

    print("\nFindings by severity:", fd["severity"].value_counts().to_dict())
    print("\nERROR and WARN findings with rows affected:")
    show = fd[(fd["severity"] != "INFO")][["severity", "check_group", "table", "column", "check", "rows_affected"]]
    with pd.option_context("display.width", 200, "display.max_colwidth", 70, "display.max_rows", 200):
        print(show.to_string(index=False))
    print(f"\nSaved {dq.REPORTS_DIR / 'profile_raw.csv'} ({len(prof_df)} rows)")
    print(f"Saved {dq.REPORTS_DIR / 'dq_summary_raw.csv'} ({len(fd)} rows)")


if __name__ == "__main__":
    main(sys.argv[1:])
