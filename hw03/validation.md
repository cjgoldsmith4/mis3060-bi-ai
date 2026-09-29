# HW3 Validation Record: SEC 8-K Extraction Pipelines

**Scripts:** `hw03/hw03_earnings.py`, `hw03/hw03_executives.py`, `hw03/hw03_timeline.py`, `hw03/hw03_yfinance_check.py`
**Output checked:** `earnings_history.csv`, `executive_events.csv`, `corporate_events_timeline.csv`, and `yfinance_check.txt` from the run on 2026-09-28

All revenue and net income values in the CSVs are in millions of USD.

---

## 5A: Known-Answer Check: Earnings

**Company and quarter:** Apple, third quarter of fiscal 2026 (quarter ended June 27, 2026), 8-K filed 2026-07-30.

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion ([Apple Newsroom, July 30, 2026](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)) | 109400.0 ($109.4 billion) | Yes |
| Apple Q3 FY2026 EPS Diluted | $2.02 ([Apple Newsroom, July 30, 2026](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)) | 2.02 | Yes |

Both values match. The revenue figure in the CSV comes from the headline sentence, which rounds to one decimal in billions. The income statement in the same exhibit shows total net sales of $109,417 million, which rounds to the same $109.4 billion.

No value in `earnings_history.csv` shows `NOT_FOUND`, so no regex fix was needed for the checked quarter. I did fix three extraction problems during the build, documented below so the before/after patterns are on record.

| Problem | Before | After | Result |
|---|---|---|---|
| Walmart `period` returned `NOT_FOUND` for all 4 rows | Only matched "second quarter fiscal 2026" style text. Walmart writes "Walmart reports Q4 results" with no year. | Added `Q([1-4])\s+results` for the quarter and `three\s+(?:and\s+\w+\s+)?months\s+ended\s+(<date>)` for the date, keeping the latest date in the release. | All 4 Walmart rows now read, for example, "third quarter, quarter ended October 31, 2025". Fixed. |
| Apple Q4 FY2025 and NVIDIA Q4 FY2026 had the wrong period | `quarter_year` pattern ran first and grabbed "fourth quarter 2024" (Apple's prior-year comparison) and "first quarter fiscal 2027" (NVIDIA's outlook). | Moved `fiscal\s+(\d{4})\s+(first\|...\|fourth)\s+quarter` and `(first\|...\|fourth)\s+quarter\s+and\s+fiscal\s+(\d{4})` ahead of it. | Apple reads "fourth quarter fiscal 2025" and NVIDIA reads "fourth quarter fiscal 2026". Fixed. |
| Microsoft `net_income` came from the table instead of the headline | `net\s+income\s+(?:was\|of)\s+\$...` missed "Net income on a GAAP basis was $38.5 billion". | `net\s+income,?\s+(?:on\s+a\s+GAAP\s+basis,?\s+)?(?:was\|of)\s+\$...` | Microsoft rows now use the GAAP headline figure. The value was already correct in dollars; the fix makes the source consistent with the other companies. |

---

## 5B: Known-Answer Check: Executive Events

**Event checked:** Apple, 8-K filed 2026-04-20: `appointment | John Ternus | Chief Executive Officer | September 1, 2026`. The same filing also produced `both | Tim Cook | Chief Executive Officer | September 1, 2026`.

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Yes | [Apple Newsroom (April 20, 2026)](https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/) names John Ternus, Senior Vice President of Hardware Engineering, as the next CEO. [CNBC](https://www.cnbc.com/2026/04/20/apple-names-john-ternus-ceo-replacing-tim-cook-who-becomes-chairman.html) reports the same. |
| Event type (departure/appointment) | Yes | Ternus is an appointment. Tim Cook's row is `both` because he leaves the CEO role and becomes executive chairman of the board, which the newsroom release confirms. |
| Effective date | Yes | The newsroom release gives September 1, 2026, which matches the CSV. The script resolved the filing's defined term "the Transition Date" back to September 1, 2026. |

---

## 5C: Cross-Validation: Earnings via Yahoo Finance

`hw03/hw03_yfinance_check.py` pulled `quarterly_income_stmt` for AAPL with yfinance. The full output is saved in `hw03/yfinance_check.txt`.

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $109,400 million | $109,417 million | Yes, within rounding |
| Net Income | $29,789 million | $29,789 million | Yes |

The revenue gap is $17 million. This is because the 8-K pipeline reads the headline sentence ("quarterly revenue of $109.4 billion"), which rounds to the nearest $100 million, while yfinance reports the exact income statement line. The same exhibit lists total net sales of $109,417 million, so the two sources agree on the underlying figure. Net income matches to the million because the pipeline read that value from the income statement table, the same source yfinance uses. yfinance labels the quarter 2026-06-30 while Apple's fiscal quarter ended June 27, 2026; this is a label convention in Yahoo's data and not a period mismatch.

---

## 5D: Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | 20 | Pass |
| `executive_events.csv` row count | At least 0 (document actual) | 35 rows from 21 Item 5.02 filings (32 named events + 3 filings with no departure or appointment) | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes, 35 rows, 16 columns | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 | Pass |

The three `NOT_FOUND` rows in `executive_events.csv` are Item 5.02 filings that cover compensation only: Microsoft 2025-12-08 (shareholder approval of the 2026 Stock Plan), NVIDIA 2026-03-06 (fiscal 2027 executive pay targets), and JPMorgan 2026-01-22 (James Dimon's 2025 compensation). Item 5.02(e) covers compensatory arrangements, so these filings carry the item code without any person joining or leaving. The script keeps each one on record with `NOT_FOUND` instead of dropping it.

Every company had at least one Item 5.02 filing in the past 12 months, so the "No executive events in past 12 months" message did not print on this run. The zero-event branch is in `main()` of `hw03_executives.py` and prints before moving to the next company.

Two rows need a note. Walmart 2026-01-16 lists John Furner as an appointment because that filing restates his November 2025 promotion while naming David Guggina as his successor at Walmart U.S. Walmart 2026-01-30 repeats Kathryn McLay's departure because that filing is a follow-up that adds her separation date (April 30, 2026).
