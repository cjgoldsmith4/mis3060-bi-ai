# =============================================================================
# Script:      hw03/hw03_yfinance_check.py
# Purpose:     Part 5C cross-validation. Pulls the most recent quarterly
#              revenue and net income for AAPL from Yahoo Finance (yfinance)
#              and compares them to the 8-K extraction in earnings_history.csv.
# Author:      Charlie
# Course:      MIS3060 Business Intelligence with AI, Villanova University
# Generated:   2026-09-28 (Claude Cowork)
#
# Run from the repository root:
#     python hw03/hw03_yfinance_check.py
# Output:      hw03/yfinance_check.txt
# =============================================================================

import csv
import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Install yfinance into the active environment the first time.
try:
    import yfinance as yf
except ImportError:
    print("yfinance not found; installing it with pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "yfinance"])
    import yfinance as yf

TICKER = "AAPL"
OUT_PATH = os.path.join("hw03", "yfinance_check.txt")

lines = []
def say(text=""):
    print(text)
    lines.append(text)

stmt = yf.Ticker(TICKER).quarterly_income_stmt   # rows = line items, columns = quarter-end dates
latest = stmt.columns[0]
revenue = stmt.loc["Total Revenue", latest]
net_income = stmt.loc["Net Income", latest]

say(f"yfinance quarterly income statement for {TICKER}")
say(f"Most recent quarter end: {latest.date()}")
say(f"Total Revenue: ${revenue / 1e6:,.0f} million")
say(f"Net Income:    ${net_income / 1e6:,.0f} million")
say()
say("Last four quarters from yfinance (millions):")
for col in stmt.columns[:4]:
    rev = stmt.loc["Total Revenue", col]
    ni = stmt.loc["Net Income", col]
    say(f"  {col.date()}  revenue {rev / 1e6:>10,.0f}   net income {ni / 1e6:>10,.0f}")

# Compare against the most recent AAPL row in the 8-K extraction.
with open(os.path.join("hw03", "earnings_history.csv"), newline="", encoding="utf-8") as f:
    rows = [r for r in csv.DictReader(f) if r["ticker"] == TICKER]
rows.sort(key=lambda r: r["filing_date"], reverse=True)
r = rows[0]
say()
say(f"8-K extraction ({r['filing_date']}, {r['period']}):")
say(f"  revenue_reported {r['revenue_reported']}  net_income {r['net_income']}  (millions)")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved {OUT_PATH}")
