# =============================================================================
# Script:      hw03/hw03_earnings.py
# Data source: SEC EDGAR Form 8-K filings, Item 2.02 (Results of Operations)
#              Earnings press release exhibits (Exhibit 99.1)
# Companies:   AAPL, MSFT, NVDA, JPM, WMT
# Author:      Charlie
# Course:      MIS3060 Business Intelligence with AI, Villanova University
# Generated:   2026-09-28 (Claude Cowork, from Specification A)
#
# Run from the repository root:
#     python hw03/hw03_earnings.py
# Output:
#     hw03/earnings_history.csv
#     hw03/raw_text/<TICKER>_<filing_date>_earnings.txt  (plain text of each
#     press release, kept for validation and regex debugging)
# =============================================================================

import csv
import datetime as dt
import os
import re
import time

import requests
from bs4 import BeautifulSoup

# Run from the repository root no matter where the script is launched
# (terminal command or the VS Code Run button).
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
HEADERS = {"User-Agent": "MIS3060 Villanova cgolds04@villanova.edu"}
REQUEST_PAUSE = 0.25          # seconds between requests (SEC limit is 10/sec)
FILINGS_PER_COMPANY = 4       # one per quarter
NOT_FOUND = "NOT_FOUND"

OUTPUT_DIR = "hw03"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "earnings_history.csv")
RAW_TEXT_DIR = os.path.join(OUTPUT_DIR, "raw_text")

COMPANIES = [
    {"company": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"company": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]

CSV_COLUMNS = ["company", "ticker", "cik", "filing_date", "period",
               "revenue_reported", "eps_diluted", "net_income"]

# -----------------------------------------------------------------------------
# Regex patterns. Each list runs in order, most specific first. The first
# pattern that matches wins. Add a new pattern to a list to fix a company
# without touching the extraction logic.
# -----------------------------------------------------------------------------
MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
QUARTER_WORD = r"(first|second|third|fourth)"

# Reporting period. Each pattern builds its own label in extract_period().
PERIOD_PATTERNS = [
    # "fiscal 2025 fourth quarter", "fiscal year 2026 second quarter"
    ("year_quarter", re.compile(
        r"(fiscal\s+(?:year\s+)?)(\d{4})\s+" + QUARTER_WORD + r"[\s\-]+quarter", re.I)),
    # "Fourth Quarter and Fiscal 2026"
    ("quarter_and_fiscal", re.compile(
        QUARTER_WORD + r"[\s\-]+quarter\s+and\s+fiscal\s+(?:year\s+)?(\d{4})", re.I)),
    # "fourth quarter fiscal 2025", "second quarter of fiscal 2026",
    # "Second-Quarter 2025", "third quarter of fiscal year 2025"
    ("quarter_year", re.compile(
        QUARTER_WORD + r"[\s\-]+quarter\s+(?:of\s+)?(fiscal\s+(?:year\s+)?)?(\d{4})",
        re.I)),
    # "Q2 FY26", "Q2 fiscal year 2026"
    ("q_fy", re.compile(
        r"\bQ([1-4])\s*(?:FY|fiscal\s+(?:year\s+)?)\s*'?(\d{2,4})\b", re.I)),
    # "quarter ended June 30, 2025"
    ("quarter_ended", re.compile(
        r"quarter\s+ended\s+(" + MONTHS + r"\s+\d{1,2},\s+\d{4})", re.I)),
    # Walmart: "three and nine months ended October 31, 2025"
    ("quarter_ended", re.compile(
        r"three\s+(?:and\s+\w+\s+)?months\s+ended\s+(" + MONTHS + r"\s+\d{1,2},\s+\d{4})",
        re.I)),
]

# Revenue stated in prose with a unit ("$94.9 billion").
REVENUE_PROSE_PATTERNS = [
    # "quarterly revenue of $94.9 billion", "Revenue was $76.4 billion",
    # "Total revenue was $177.4 billion", "Reported revenue of $44.9 billion",
    # "Consolidated revenue of $177.4 billion"
    re.compile(r"(?:quarterly|total|consolidated|reported|record)?\s*"
               r"(?:net\s+)?(?:revenues?|net\s+sales)\s+"
               r"(?:was|were|of|totaled|reached|grew\s+to|increased\s+to|rose\s+to)\s+"
               r"(?:a\s+)?(?:record\s+)?\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million)", re.I),
    # "revenue for the second quarter ended July 27, 2025, of $46.7 billion"
    re.compile(r"\brevenues?\b[^$]{0,120}?\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million)", re.I),
]
# Revenue from the income statement table (amounts in millions).
REVENUE_TABLE_PATTERNS = [
    re.compile(r"\bTotal\s+net\s+sales\s*\$?\s*([\d,]{4,}(?:\.\d+)?)", re.I),
    re.compile(r"\bTotal\s+revenues?\b(?:,\s*net\s+of\s+interest\s+expense)?\s*\$?\s*([\d,]{4,}(?:\.\d+)?)", re.I),
    re.compile(r"\bRevenues?\s*\$\s*([\d,]{4,}(?:\.\d+)?)", re.I),
]

EPS_PATTERNS = [
    # "diluted earnings per share of $1.57", "Diluted earnings per share was $3.65"
    re.compile(r"diluted\s+(?:earnings|net\s+income)\s+per\s+(?:common\s+)?share,?\s+(?:on\s+a\s+GAAP\s+basis,?\s+)?"
               r"(?:was|were|of|is)?\s*(?:a\s+record\s+)?\$\s?(\(?-?\d+\.\d{2})", re.I),
    # "earnings per diluted share for the quarter were $1.08"
    re.compile(r"earnings\s+per\s+diluted\s+share[^$]{0,80}?\$\s?(\(?-?\d+\.\d{2})", re.I),
    # "GAAP EPS of $0.88"
    re.compile(r"\bGAAP\s+(?:diluted\s+)?EPS\s+(?:of|was)\s+\$\s?(-?\d+\.\d{2})", re.I),
    # "net income of $15.0 billion, or $5.24 per share"
    re.compile(r"\$\s?(\d+\.\d{2})\s+per\s+(?:diluted\s+)?share", re.I),
    # "Diluted EPS of $2.10"
    re.compile(r"\bdiluted\s+EPS\s+(?:of|was)?\s*\$\s?(-?\d+\.\d{2})", re.I),
    # Table fallback: "Earnings per share: Basic $ 1.57 Diluted $ 1.57"
    re.compile(r"\bDiluted\s*\$\s*(\d+\.\d{2})\b"),
]

# Net income stated in prose with a unit.
NET_INCOME_PROSE_PATTERNS = [
    # "Net income was $27.2 billion", "reported net income of $15.0 billion"
    re.compile(r"(?<!adjusted\s)\bnet\s+income,?\s+(?:on\s+a\s+GAAP\s+basis,?\s+)?(?:was|of|totaled|reached)\s+"
               r"(?:a\s+record\s+)?\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million)", re.I),
]
# Net income from the income statement table (amounts in millions).
NET_INCOME_TABLE_PATTERNS = [
    re.compile(r"\bConsolidated\s+net\s+income\s+attributable\s+to\s+Walmart\s*\$?\s*([\d,]{3,}(?:\.\d+)?)", re.I),
    re.compile(r"\bNet\s+income\s*\$\s*([\d,]{3,}(?:\.\d+)?)", re.I),
    re.compile(r"\bNet\s+income\s+([\d,]{4,}(?:\.\d+)?)", re.I),
]


# -----------------------------------------------------------------------------
# HTTP helper: every request goes through here, so every request carries
# the SEC User-Agent header and the rate-limit pause.
# -----------------------------------------------------------------------------
def sec_get(url):
    """Download a URL from SEC with the required User-Agent. Returns the
    response, or None if the request failed."""
    time.sleep(REQUEST_PAUSE)
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response
    except requests.RequestException as err:
        print(f"    WARNING: request failed for {url}: {err}")
        return None


# -----------------------------------------------------------------------------
# Step 2: find Item 2.02 8-K filings in the submissions API
# -----------------------------------------------------------------------------
def rows_from_block(block):
    """Turn the parallel-list block from the submissions API into a list of
    dicts, one per filing."""
    keys = ["accessionNumber", "filingDate", "form", "items", "primaryDocument"]
    count = len(block.get("accessionNumber", []))
    return [{k: block.get(k, [""] * count)[i] for k in keys} for i in range(count)]


def get_filings(cik, item_code, needed):
    """Return 8-K filings whose items field contains item_code, newest first.
    Large filers (JPM) push older 8-Ks out of the 'recent' block, so the
    function also reads the older submission files until it has enough."""
    response = sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if response is None:
        return []
    data = response.json()
    filings = rows_from_block(data.get("filings", {}).get("recent", {}))

    def matches(rows):
        return [r for r in rows
                if r["form"] in ("8-K", "8-K/A") and item_code in (r["items"] or "")]

    found = matches(filings)
    # Read older submission files only when the recent block is short.
    for extra in data.get("filings", {}).get("files", []):
        if len(found) >= needed:
            break
        more = sec_get("https://data.sec.gov/submissions/" + extra["name"])
        if more is None:
            break
        found += matches(rows_from_block(more.json()))

    found.sort(key=lambda r: r["filingDate"], reverse=True)
    return found


# -----------------------------------------------------------------------------
# Step 4: locate and download the press release exhibit
# -----------------------------------------------------------------------------
def find_press_release_url(cik, accession, primary_doc):
    """Read the filing index page and return the URL of the Exhibit 99.1
    press release (.htm). Returns None if no exhibit can be found."""
    cik_int = str(int(cik))
    acc_nodash = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
    index = sec_get(base + f"{accession}-index.htm")
    if index is None:
        return None

    soup = BeautifulSoup(index.text, "html.parser")
    docs = []  # (document name, exhibit type)
    for table in soup.find_all("table", class_="tableFile"):
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) >= 4:
                link = tr.find("a")
                name = link["href"].split("/")[-1] if link else cells[2].split(" ")[0]
                docs.append((name, cells[3].upper()))

    htm_docs = [(n, t) for n, t in docs if n.lower().endswith((".htm", ".html"))]

    # 1st choice: document typed EX-99.1
    for name, doc_type in htm_docs:
        if doc_type in ("EX-99.1", "EX-99.01", "EX-99"):
            return base + name
    # 2nd choice: file name that looks like Exhibit 99.1
    for name, _ in htm_docs:
        if re.search(r"(ex|exhibit)[\-_]?99[\-_.]?0?1(?!\d)", name, re.I):
            return base + name
    # 3rd choice: any EX-99.x exhibit
    for name, doc_type in htm_docs:
        if doc_type.startswith("EX-99"):
            return base + name
    # Last resort: any .htm that is not the main 8-K form
    for name, _ in htm_docs:
        if name != primary_doc and "index" not in name.lower():
            return base + name
    return None


def html_to_text(html):
    """Strip HTML tags and collapse whitespace into one plain-text string."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = text.replace("\xa0", " ").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


# -----------------------------------------------------------------------------
# Step 5: extraction helpers
# -----------------------------------------------------------------------------
def to_millions(number_text, unit):
    """Convert '94.9' + 'billion' to 94900.0 (millions)."""
    value = float(number_text.replace(",", ""))
    if unit.lower() == "billion":
        value *= 1000
    return round(value, 1)


def extract_period(text):
    head = text[:4000]
    for kind, pattern in PERIOD_PATTERNS:
        # The Walmart three-months pattern lives in the statements further down.
        m = pattern.search(head) or (pattern.search(text) if kind == "quarter_ended" else None)
        if not m:
            continue
        if kind == "quarter_year":
            fiscal = "fiscal " if m.group(2) else ""
            return f"{m.group(1).lower()} quarter {fiscal}{m.group(3)}"
        if kind == "year_quarter":
            return f"{m.group(3).lower()} quarter fiscal {m.group(2)}"
        if kind == "quarter_and_fiscal":
            return f"{m.group(1).lower()} quarter fiscal {m.group(2)}"
        if kind == "q_fy":
            year = m.group(2)
            year = "20" + year if len(year) == 2 else year
            word = ["first", "second", "third", "fourth"][int(m.group(1)) - 1]
            return f"{word} quarter fiscal {year}"
        if kind == "quarter_ended":
            # Statements list the prior-year quarter too; keep the latest date.
            dates = []
            all_ended = [p for k, p in PERIOD_PATTERNS if k == "quarter_ended"]
            for d in (d for p in all_ended for d in p.finditer(text)):
                try:
                    dates.append(dt.datetime.strptime(d.group(1).replace(",", ""), "%B %d %Y"))
                except ValueError:
                    pass
            latest = max(dates).strftime("%B %d, %Y").replace(" 0", " ") if dates else m.group(1)
            # Add the ordinal quarter from the headline when one is present.
            q = re.search(QUARTER_WORD + r"[\s\-]+quarter", head, re.I)
            qn = re.search(r"\bQ([1-4])\s+results", head)
            if q:
                prefix = f"{q.group(1).lower()} quarter, "
            elif qn:
                prefix = ["first", "second", "third", "fourth"][int(qn.group(1)) - 1] + " quarter, "
            else:
                prefix = ""
            return f"{prefix}quarter ended {latest}"
    return NOT_FOUND


def extract_money(text, prose_patterns, table_patterns):
    """Try prose patterns (with a billion/million unit) first, then the
    income statement table (already in millions)."""
    for pattern in prose_patterns:
        m = pattern.search(text)
        if m:
            return to_millions(m.group(1), m.group(2))
    for pattern in table_patterns:
        m = pattern.search(text)
        if m:
            return round(float(m.group(1).replace(",", "")), 1)
    return NOT_FOUND


def extract_eps(text):
    for pattern in EPS_PATTERNS:
        m = pattern.search(text)
        if m:
            raw = m.group(1)
            negative = raw.startswith("(") or raw.startswith("-")
            value = float(raw.strip("(-"))
            return -value if negative else value
    return NOT_FOUND


def fmt_money(value):
    """Format a millions figure for the console line."""
    if value == NOT_FOUND:
        return NOT_FOUND
    if value >= 1000:
        return f"${value / 1000:,.2f}B"
    return f"${value:,.1f}M"


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------
def process_filing(company, filing):
    """Download one filing's press release and return one CSV row."""
    row = {
        "company": company["company"],
        "ticker": company["ticker"],
        "cik": company["cik"],
        "filing_date": filing["filingDate"],
        "period": NOT_FOUND,
        "revenue_reported": NOT_FOUND,
        "eps_diluted": NOT_FOUND,
        "net_income": NOT_FOUND,
    }
    url = find_press_release_url(company["cik"], filing["accessionNumber"],
                                 filing["primaryDocument"])
    if url is None:
        print(f"    WARNING: {company['ticker']} {filing['filingDate']}: "
              f"press release exhibit not found, skipping to next filing")
        return row

    response = sec_get(url)
    if response is None:
        print(f"    WARNING: {company['ticker']} {filing['filingDate']}: "
              f"could not download {url}")
        return row

    text = html_to_text(response.text)

    # Save the plain text so extractions can be checked by hand later.
    os.makedirs(RAW_TEXT_DIR, exist_ok=True)
    raw_path = os.path.join(RAW_TEXT_DIR,
                            f"{company['ticker']}_{filing['filingDate']}_earnings.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(url + "\n\n" + text)

    row["period"] = extract_period(text)
    row["revenue_reported"] = extract_money(text, REVENUE_PROSE_PATTERNS,
                                            REVENUE_TABLE_PATTERNS)
    row["eps_diluted"] = extract_eps(text)
    row["net_income"] = extract_money(text, NET_INCOME_PROSE_PATTERNS,
                                      NET_INCOME_TABLE_PATTERNS)
    return row


def main():
    all_rows = []
    for company in COMPANIES:
        print(f"\n=== {company['ticker']} ({company['company']}) ===")
        try:
            filings = get_filings(company["cik"], "2.02", FILINGS_PER_COMPANY)
        except Exception as err:  # keep going if one company fails
            print(f"    WARNING: could not read submissions for {company['ticker']}: {err}")
            continue
        filings = filings[:FILINGS_PER_COMPANY]
        if not filings:
            print(f"    WARNING: no Item 2.02 8-K filings found for {company['ticker']}")
            continue

        for filing in filings:
            try:
                row = process_filing(company, filing)
            except Exception as err:
                print(f"    WARNING: {company['ticker']} {filing['filingDate']}: "
                      f"unexpected error ({err}); storing NOT_FOUND")
                row = {c: NOT_FOUND for c in CSV_COLUMNS}
                row.update({"company": company["company"], "ticker": company["ticker"],
                            "cik": company["cik"], "filing_date": filing["filingDate"]})
            all_rows.append(row)
            eps = row["eps_diluted"]
            eps_text = f"${eps:.2f}" if eps != NOT_FOUND else NOT_FOUND
            print(f"{row['ticker']} | {row['period']} | "
                  f"Revenue: {fmt_money(row['revenue_reported'])} | "
                  f"EPS: {eps_text} | "
                  f"Net Income: {fmt_money(row['net_income'])}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nSaved {len(all_rows)} rows to {OUTPUT_CSV} "
          f"(revenue_reported and net_income are in millions of USD)")


if __name__ == "__main__":
    main()
