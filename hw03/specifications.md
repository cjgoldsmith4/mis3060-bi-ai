# HW3 Specifications: SEC 8-K Extraction Pipelines

**Course:** MIS3060 Business Intelligence with AI
**Author:** Charlie
**Data source:** SEC EDGAR Form 8-K filings for Apple, Microsoft, NVIDIA, JPMorgan Chase, and Walmart

I wrote both specifications below before generating any code. Each one is the full prompt I sent to Claude Cowork.

---

## Specification A: Earnings Pipeline (Item 2.02)

### What I need

Write one Python script that pulls quarterly earnings figures out of SEC 8-K earnings press releases for five companies and saves them to a CSV. Save it as `hw03/hw03_earnings.py`. The script must run from the repository root with the command `python hw03/hw03_earnings.py`, use only `requests`, `beautifulsoup4`, and the Python standard library, and finish every step below in one execution with no input from me.

Use these five companies and CIK numbers exactly as written. Do not look them up.

| Company | Ticker | SEC CIK |
|---|---|---|
| Apple Inc. | AAPL | 0000320193 |
| Microsoft Corporation | MSFT | 0000789019 |
| NVIDIA Corporation | NVDA | 0001045810 |
| JPMorgan Chase & Co. | JPM | 0000019617 |
| Walmart Inc. | WMT | 0000104169 |

### Steps the script must perform

1. **User-Agent header.** Set the HTTP `User-Agent` header to `"MIS3060 Villanova cgolds04@villanova.edu"` on every request the script makes, not only the first one. Route every download through one helper function that attaches the header, so no `requests.get()` call can go out without it. Pause about a quarter second between requests so the script stays under the SEC limit of 10 requests per second.

2. **Find the earnings filings.** For each company, request the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json`, using the 10-digit CIK. Read the `filings.recent` block, which stores each field as a parallel list. Keep only rows where `form` is `8-K` and the `items` field contains `"2.02"` (Results of Operations and Financial Condition).

3. **Pick four filings per company.** Sort the matching filings by `filingDate`, newest first, and keep the most recent four. That gives one filing per quarter.

4. **Download the press release.** For each filing, build the filing index URL from the CIK (leading zeros removed) and the accession number (dashes removed): `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/`. Read the filing's `index.json` to list its documents. Pick the earnings press release exhibit: the `.htm` file whose name marks it as Exhibit 99.1 (for example `ex99-1`, `ex991`, or `exhibit991`). If no file matches that pattern, fall back to any other `.htm` exhibit that is not the main 8-K document. Download that file and strip the HTML to plain text with BeautifulSoup, collapsing extra whitespace. If the script cannot find or download a press release, print a warning that names the ticker and filing date, write the row with every field set to `"NOT_FOUND"`, and move on to the next filing. The script must never crash on one bad filing.

5. **Extract four fields from the plain text.**
   - **Reporting period**, such as "fourth quarter fiscal 2024" or "second quarter of 2025". Search the first part of the release for the quarter phrase and the fiscal year that follows it.
   - **Quarterly revenue**, stored as a number in millions of dollars. The companies use different words: "revenue", "net sales", "total revenues", or "net revenue". Convert "billion" to millions (multiply by 1,000) so every row uses the same unit.
   - **Diluted EPS**, stored as a dollar amount such as `1.64`.
   - **Net income**, stored as a number in millions of dollars, using the same billion-to-million conversion.

   Try several regex patterns for each field, in order from most specific to most general, and keep the first match. Keep the patterns in lists at the top of the script so I can add a new one without rewriting the logic.

6. **Print each row.** As each filing finishes, print one line in this format:
   `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`

7. **Save the CSV.** Save all rows to `hw03/earnings_history.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`. Keep the CIK as the 10-digit string with leading zeros. Print a confirmation line with the file path and the row count once the file is saved.

8. **Missing values.** When a regex finds no match, store the string `"NOT_FOUND"` in that cell. Never store `None`, `NaN`, or an empty string. A blank cell and a failed extraction mean two different things.

### Rules for the whole script

- Start the script with a comment block that names the script, the data source, the author (Charlie), the course (MIS3060), and the date it was generated.
- Wrap the work in named functions with short plain-language comments.
- Catch network and parsing errors per filing and per company, print a warning, and continue.
- Create the `hw03/` folder if it does not exist before writing the CSV.

---

## Specification B: Executive Events Pipeline (Item 5.02)

### What I need

Write one Python script that pulls executive departure and appointment events out of SEC 8-K filings for the same five companies and saves them to a CSV. Save it as `hw03/hw03_executives.py`. The script must run from the repository root with the command `python hw03/hw03_executives.py`, use only `requests`, `beautifulsoup4`, and the Python standard library, and finish in one execution with no input from me.

Use the same five companies, tickers, and CIK numbers listed in Specification A.

### Steps the script must perform

1. **User-Agent header.** Set the HTTP `User-Agent` header to `"MIS3060 Villanova cgolds04@villanova.edu"` on every request, through one helper function, with the same quarter-second pause between requests.

2. **Find the Item 5.02 filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json`. Keep only rows where `form` is `8-K` (include `8-K/A` amendments), the `items` field contains `"5.02"` (Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers), and the `filingDate` falls within the 12 months before the day the script runs.

3. **Download and extract.** For each matching filing, download the main 8-K document (the `primaryDocument` field from the submissions API) and strip the HTML to plain text. Isolate the Item 5.02 section: the text from the "Item 5.02" heading up to the next "Item" heading or the signature block. From that section, extract:
   - **Event type:** `"departure"` when the text describes someone retiring, resigning, stepping down, leaving, or not standing for re-election; `"appointment"` when it describes someone being appointed, elected, named, or promoted; `"both"` only when one sentence describes a single person leaving one role and taking another.
   - **Person's full name:** the name tied to the event, such as "Jeff Williams".
   - **Title:** the role the person is leaving or taking, such as "Chief Operating Officer" or "member of the Board of Directors".
   - **Effective date:** the date the change takes effect, such as "effective June 30, 2025". If the text gives no effective date, store `"NOT_FOUND"`.

4. **One row per event.** If a filing reports more than one event, such as one executive's departure and a successor's appointment, create a separate row for each event. A filing with one departure and one appointment must produce two rows. Do not write the same person and event type twice for one filing.

5. **Print each event.** As each event is extracted, print one line in this format:
   `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`

6. **Zero-event companies.** If a company has no Item 5.02 filings in the past 12 months, print `[Ticker]: No executive events in past 12 months` and move on. This is valid data, not an error, and the script must not crash or skip the message. If a filing matches Item 5.02 but the script cannot pull a name out of it, still write one row with `"NOT_FOUND"` in the fields it could not extract, so the filing stays on record.

7. **Save the CSV.** Save all events to `hw03/executive_events.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. If no company has any events, still write the file with the header row. Print a confirmation line with the file path and the row count once the file is saved.

### Rules for the whole script

- Start the script with the same comment block as Specification A.
- Wrap the work in named functions with short plain-language comments.
- Catch network and parsing errors per filing, print a warning, and continue.
- Store `"NOT_FOUND"` for any field the script cannot extract. Never leave a cell blank.
