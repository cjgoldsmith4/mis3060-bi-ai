# =============================================================================
# Script:      hw03/hw03_timeline.py
# Inputs:      hw03/earnings_history.csv   (from hw03_earnings.py)
#              hw03/executive_events.csv   (from hw03_executives.py)
# Output:      hw03/corporate_events_timeline.csv
# Author:      Charlie
# Course:      MIS3060 Business Intelligence with AI, Villanova University
# Generated:   2026-09-28 (Claude Cowork, from the Part 4 timeline prompt)
#
# Run from the repository root:
#     python hw03/hw03_timeline.py
#
# For each executive event, finds the nearest earnings filing for the same
# company, measures the gap in days, and labels the timing.
# =============================================================================

import os

import pandas as pd

# Run from the repository root no matter where the script is launched
# (terminal command or the VS Code Run button).
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EARNINGS_CSV = os.path.join("hw03", "earnings_history.csv")
EVENTS_CSV = os.path.join("hw03", "executive_events.csv")
OUTPUT_CSV = os.path.join("hw03", "corporate_events_timeline.csv")
SAME_WEEK_DAYS = 7


def load_tables():
    # Read everything as text so "NOT_FOUND" and the 10-digit CIK survive.
    earnings = pd.read_csv(EARNINGS_CSV, dtype=str)
    events = pd.read_csv(EVENTS_CSV, dtype=str)
    earnings["filing_date"] = pd.to_datetime(earnings["filing_date"])
    events["filing_date"] = pd.to_datetime(events["filing_date"])
    return earnings, events


def label_timing(signed_days):
    """signed_days = event filing date minus nearest earnings filing date."""
    if abs(signed_days) <= SAME_WEEK_DAYS:
        return "same week"
    return "before earnings" if signed_days < 0 else "after earnings"


def build_timeline(earnings, events):
    # Prefix earnings columns so both tables' columns fit side by side.
    earn = earnings.rename(columns={
        "filing_date": "earnings_filing_date",
        "period": "earnings_period",
        "revenue_reported": "earnings_revenue_reported",
        "eps_diluted": "earnings_eps_diluted",
        "net_income": "earnings_net_income",
    })[["ticker", "earnings_filing_date", "earnings_period",
        "earnings_revenue_reported", "earnings_eps_diluted", "earnings_net_income"]]

    rows = []
    for _, event in events.iterrows():
        company_earn = earn[earn["ticker"] == event["ticker"]]
        out = event.to_dict()
        if company_earn.empty:
            out.update({c: "NOT_FOUND" for c in earn.columns if c != "ticker"})
            out["days_to_nearest_earnings"] = "NOT_FOUND"
            out["event_timing"] = "NOT_FOUND"
            rows.append(out)
            continue
        # Nearest earnings filing by absolute day gap.
        gaps = (event["filing_date"] - company_earn["earnings_filing_date"]).dt.days
        idx = gaps.abs().idxmin()
        signed = int(gaps.loc[idx])
        nearest = company_earn.loc[idx]
        out.update({c: nearest[c] for c in earn.columns if c != "ticker"})
        out["days_to_nearest_earnings"] = abs(signed)
        out["days_signed"] = signed
        out["event_timing"] = label_timing(signed)
        rows.append(out)

    columns = (list(events.columns)
               + [c for c in earn.columns if c != "ticker"]
               + ["days_to_nearest_earnings", "days_signed", "event_timing"])
    timeline = pd.DataFrame(rows, columns=columns)
    if not timeline.empty:
        timeline["filing_date"] = pd.to_datetime(timeline["filing_date"]).dt.date
        timeline["earnings_filing_date"] = pd.to_datetime(
            timeline["earnings_filing_date"], errors="coerce").dt.date
        timeline = timeline.sort_values(["ticker", "filing_date"])
    return timeline


def print_summary(timeline, earnings):
    print("=" * 70)
    print("CORPORATE EVENTS TIMELINE: executive events vs. nearest earnings filing")
    print("=" * 70)
    for ticker in earnings["ticker"].drop_duplicates():
        company = earnings.loc[earnings["ticker"] == ticker, "company"].iloc[0]
        print(f"\n{ticker} ({company})")
        subset = timeline[timeline["ticker"] == ticker] if not timeline.empty else timeline
        if subset.empty:
            print("  No executive events in past 12 months")
            continue
        for _, r in subset.iterrows():
            signed = r["days_signed"]
            direction = ("before" if signed < 0 else "after") if signed != 0 else "on"
            print(f"  {r['filing_date']} | {r['event_type']:<11} | {r['person_name']} "
                  f"({r['title']})")
            print(f"      -> {r['event_timing']}: {abs(signed)} days {direction} the "
                  f"earnings filing of {r['earnings_filing_date']} ({r['earnings_period']})")

    print("\n" + "=" * 70)
    print("FINAL COUNT (all five companies)")
    print("=" * 70)
    counts = timeline["event_timing"].value_counts() if not timeline.empty else pd.Series(dtype=int)
    for label in ["before earnings", "after earnings", "same week"]:
        print(f"  {label:<16}: {int(counts.get(label, 0))}")
    print(f"  {'total events':<16}: {len(timeline)}")


def main():
    earnings, events = load_tables()
    timeline = build_timeline(earnings, events)
    timeline.to_csv(OUTPUT_CSV, index=False)
    print_summary(timeline, earnings)
    print(f"\nSaved {len(timeline)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
