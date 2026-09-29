# HW3 AI Usage Log

**Tool:** Claude Cowork (three separate prompts, one per script)
**Author:** Charlie

---

## Prompt 1: Specification A (earnings pipeline, produced `hw03_earnings.py`)

> ## Specification A: Earnings Pipeline (Item 2.02)
>
> ### What I need
>
> Write one Python script that pulls quarterly earnings figures out of SEC 8-K earnings press releases for five companies and saves them to a CSV. Save it as `hw03/hw03_earnings.py`. The script must run from the repository root with the command `python hw03/hw03_earnings.py`, use only `requests`, `beautifulsoup4`, and the Python standard library, and finish every step below in one execution with no input from me.
>
> Use these five companies and CIK numbers exactly as written. Do not look them up.
>
> | Company | Ticker | SEC CIK |
> |

## Prompt 2: Specification B (executive events pipeline, produced `hw03_executives.py`)

> ## Specification B: Executive Events Pipeline (Item 5.02)
>
> ### What I need
>
> Write one Python script that pulls executive departure and appointment events out of SEC 8-K filings for the same five companies and saves them to a CSV. Save it as `hw03/hw03_executives.py`. The script must run from the repository root with the command `python hw03/hw03_executives.py`, use only `requests`, `beautifulsoup4`, and the Python standard library, and finish in one execution with no input from me.
>
> Use the same five companies, tickers, and CIK numbers listed in Specification A.
>
> ### Steps the script must perform
>
> 1. **User-Agent header.** Set the HTTP `User-Agent` header to `"MIS3060 Villanova cgolds04@villanova.edu"` on every request, through one helper function, with the same quarter-second pause between requests.
>
> 2. **Find the Item 5.02 filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json`. Keep only rows where `form` is `8-K` (include `8-K/A` amendments), the `items` field contains `"5.02"` (Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers), and the `filingDate` falls within the 12 months before the day the script runs.
>
> 3. **Download and extract.** For each matching filing, download the main 8-K document (the `primaryDocument` field from the submissions API) and strip the HTML to plain text. Isolate the Item 5.02 section: the text from the "Item 5.02" heading up to the next "Item" heading or the signature block. From that section, extract:
>    - **Event type:** `"departure"` when the text describes someone retiring, resigning, stepping down, leaving, or not standing for re-election; `"appointment"` when it describes someone being appointed, elected, named, or promoted; `"both"` only when one sentence describes a single person leaving one role and taking another.
>    - **Person's full name:** the name tied to the event, such as "Jeff Williams".
>    - **Title:** the role the person is leaving or taking, such as "Chief Operating Officer" or "member of the Board of Directors".
>    - **Effective date:** the date the change takes effect, such as "effective June 30, 2025". If the text gives no effective date, store `"NOT_FOUND"`.
>
> 4. **One row per event.** If a filing reports more than one event, such as one executive's departure and a successor's appointment, create a separate row for each event. A filing with one departure and one appointment must produce two rows. Do not write the same person and event type twice for one filing.
>
> 5. **Print each event.** As each event is extracted, print one line in this format:
>    `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`
>
> 6. **Zero-event companies.** If a company has no Item 5.02 filings in the past 12 months, print `[Ticker]: No executive events in past 12 months` and move on. This is valid data, not an error, and the script must not crash or skip the message. If a filing matches Item 5.02 but the script cannot pull a name out of it, still write one row with `"NOT_FOUND"` in the fields it could not extract, so the filing stays on record.
>
> 7. **Save the CSV.** Save all events to `hw03/executive_events.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. If no company has any events, still write the file with the header row. Print a confirmation line with the file path and the row count once the file is saved.
>
> ### Rules for the whole script
>
> - Start the script with the same comment block as Specification A.
> - Wrap the work in named functions with short plain-language comments.
> - Catch network and parsing errors per filing, print a warning, and continue.
> - Store `"NOT_FOUND"` for any field the script cannot extract. Never leave a cell blank.

## Prompt 3: Timeline prompt (produced `hw03_timeline.py`)

> Write a Python script that reads `hw03/earnings_history.csv` and `hw03/executive_events.csv`. Do the following:
>
> 1. For each executive event in the events table, calculate the number of days between the executive event's `filing_date` and the nearest earnings filing date for the same company in the earnings table. Call this `days_to_nearest_earnings`.
> 2. Add a column `event_timing` that categorizes each executive event as: `'before earnings'` if the event came before the nearest earnings filing, `'after earnings'` if it came after, or `'same week'` if within 7 days of an earnings filing.
> 3. Save the combined table to `hw03/corporate_events_timeline.csv` with all columns from both source tables plus `days_to_nearest_earnings` and `event_timing`.
> 4. Print a summary: for each company, list any executive events and whether they occurred before or after the nearest earnings announcement.
> 5. Print a final count: how many events occurred before vs. after an earnings announcement across all five companies.

I also asked for one short helper for Part 5C: "Write Python using yfinance to get the most recent quarterly revenue and net income for AAPL." That produced `hw03_yfinance_check.py`, which saves its output to `hw03/yfinance_check.txt`.

---

## Companies that needed iteration

**Earnings pipeline.** The first run produced 20 rows with no `NOT_FOUND` in revenue, EPS, or net income. The `period` field needed three rounds of regex fixes:

- **Walmart:** all 4 periods came back `NOT_FOUND`. Walmart's release headline says "Walmart reports Q4 results" with no year, so I added a `Q([1-4]) results` pattern and a "three months ended <date>" pattern. The first version of the date fix picked up the prior-year date from the comparison column (October 31, 2024), so I changed it to keep the latest date in the release.
- **Apple and NVIDIA:** one quarter each got the wrong period. Apple's Q4 FY2025 read "fourth quarter 2024" from a prior-year comparison, and NVIDIA's Q4 FY2026 read "first quarter fiscal 2027" from its outlook section. Moving the "fiscal 2025 fourth quarter" and "Fourth Quarter and Fiscal 2026" patterns ahead of the general pattern fixed both.
- **Microsoft:** net income came from the income statement table because the headline says "Net income on a GAAP basis was $38.5 billion". I added the optional "on a GAAP basis" phrase so all four Microsoft rows use the headline figure.

**Executive events pipeline.** The first run produced 41 rows, and a large share were wrong. It pulled phrases like "Target Award Opportunity" and "Fiscal Year" out of an NVIDIA compensation filing as names, wrote possessives like "Tim Cook's" as separate people, split "Carmine Di Sibio" into "Carmine Di", and marked most people as `both`. I asked for a rewrite of the name and event logic and ran it against the saved Item 5.02 text for all 21 filings until each row matched the filing. The changes that fixed it:

- Names come only from "Mr./Ms. <surname>" references and fixed 8-K positions ("Name, age 55," / "appointed Name" / "On <date>, Name notified"), with possessives stripped. This dropped the fake names and caught Donald Robertson (NVIDIA) and Chris Kondo (Apple), who the filings never call "Mr."
- Each departure or appointment keyword now goes to the person named just before it in the sentence, and "the appointment of Mr. Furner" goes to the person after the noun. This fixed Walmart's Doug McMillon, who had been marked `both`.
- Sentences that start "In the event of..." are skipped, so a hypothetical retirement clause in Tim Cook's pay terms no longer counts as a departure.
- "Transition from his role as" marks a person as `both`, and defined dates such as "effective on the Transition Date" resolve to the real date. Both fixes came from Apple's April 20, 2026 CEO transition filing, which returned no events on the first run.

The final run produced 35 rows: 32 named events and 3 compensation-only filings kept as `NOT_FOUND`.

---

## One thing the script did that I did not specify

I did not specify how to handle companies whose submissions file does not reach back far enough. The generated scripts check the `filings.files` list in the EDGAR submissions JSON and download the older submission pages when the `recent` block runs short. This matters for JPMorgan, which files large numbers of other forms (prospectus supplements and similar) that can push older 8-Ks out of the `recent` block. I checked this by confirming that JPM returned 4 earnings filings going back to 2025-10-14 and Item 5.02 filings going back to 2025-12-08. The behavior was correct and needed no adjustment.

The generated scripts also save the plain text of every press release and Item 5.02 section to `hw03/raw_text/`. I did not ask for this either, and it turned out to be the most useful part of the build. Every regex fix above was tested against those saved files instead of calling EDGAR again. The folder is excluded from the repository in `.gitignore` because the scripts rebuild it on every run.

---

## Run notes

- The scripts ran from VS Code with the Run Python File button, which uses the interpreter selected in VS Code. Each script calls `os.chdir()` to the repository root, so the relative `hw03/...` paths work no matter which folder the terminal starts in.
- `hw03_yfinance_check.py` installs `yfinance` with pip the first time it runs if the package is missing.
